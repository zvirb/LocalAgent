"""
Enhanced Plugin Discovery System
Entry points discovery and dynamic plugin registration for LocalAgent CLI
"""

import pkg_resources
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class PluginEntry:
    """Plugin entry point information"""
    name: str
    group: str
    module_name: str
    class_name: str
    version: str
    description: str
    entry_point: Optional[str] = None
    file_path: Optional[Path] = None
    metadata: Dict[str, Any] = None

class EntryPointDiscoveryEngine:
    """Advanced entry point discovery for LocalAgent plugins"""
    
    PLUGIN_ENTRY_POINTS = {
        'localagent.plugins.commands': 'Command plugins',
        'localagent.plugins.providers': 'LLM provider plugins', 
        'localagent.plugins.ui': 'UI extension plugins',
        'localagent.plugins.workflow': 'Workflow phase plugins',
        'localagent.plugins.tools': 'Tool plugins',
        'localagent.plugins.integrations': 'External integration plugins'
    }
    
    def __init__(self):
        self.discovered_entries: List[PluginEntry] = []
        self.entry_point_cache: Dict[str, List[PluginEntry]] = {}
        
    async def discover_all_entry_points(self) -> List[PluginEntry]:
        """Discover all plugin entry points across all groups"""
        self.discovered_entries.clear()
        
        for group_name, description in self.PLUGIN_ENTRY_POINTS.items():
            try:
                group_entries = await self._discover_entry_point_group(group_name)
                self.discovered_entries.extend(group_entries)
                logger.info(f"Discovered {len(group_entries)} plugins in {group_name}")
                
            except Exception as e:
                logger.error(f"Error discovering plugins in {group_name}: {e}")
        
        # Cache results
        self._cache_discoveries()
        
        return self.discovered_entries
    
    async def _discover_entry_point_group(self, group_name: str) -> List[PluginEntry]:
        """Discover plugins in a specific entry point group"""
        entries = []
        
        try:
            for entry_point in pkg_resources.iter_entry_points(group_name):
                try:
                    plugin_entry = await self._create_plugin_entry(entry_point, group_name)
                    if plugin_entry:
                        entries.append(plugin_entry)
                        
                except Exception as e:
                    logger.warning(f"Failed to process entry point {entry_point.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error iterating entry points for {group_name}: {e}")
            
        return entries
    
    async def _create_plugin_entry(self, entry_point, group_name: str) -> Optional[PluginEntry]:
        """Create plugin entry from setuptools entry point"""
        try:
            # Load the plugin class without instantiating
            plugin_class = entry_point.load()
            
            if not inspect.isclass(plugin_class):
                logger.warning(f"Entry point {entry_point.name} does not point to a class")
                return None
            
            # Get plugin metadata
            name = getattr(plugin_class, 'name', entry_point.name)
            version = getattr(plugin_class, 'version', '1.0.0')
            description = getattr(plugin_class, 'description', 'No description')
            
            # Create plugin entry
            plugin_entry = PluginEntry(
                name=name,
                group=group_name,
                module_name=plugin_class.__module__,
                class_name=plugin_class.__name__,
                version=version,
                description=description,
                entry_point=f"{group_name}:{entry_point.name}",
                metadata={
                    'dependencies': getattr(plugin_class, 'dependencies', []),
                    'requires_config': getattr(plugin_class, 'requires_config', False),
                    'plugin_type': getattr(plugin_class, 'plugin_type', 'generic')
                }
            )
            
            return plugin_entry
            
        except Exception as e:
            logger.error(f"Failed to create plugin entry for {entry_point.name}: {e}")
            return None
    
    def _cache_discoveries(self):
        """Cache discovered entries by group"""
        self.entry_point_cache.clear()
        
        for entry in self.discovered_entries:
            if entry.group not in self.entry_point_cache:
                self.entry_point_cache[entry.group] = []
            self.entry_point_cache[entry.group].append(entry)
    
    def get_entries_by_group(self, group_name: str) -> List[PluginEntry]:
        """Get all plugin entries for a specific group"""
        return self.entry_point_cache.get(group_name, [])
    
    def get_entry_by_name(self, name: str) -> Optional[PluginEntry]:
        """Get plugin entry by name"""
        for entry in self.discovered_entries:
            if entry.name == name:
                return entry
        return None
    
    def export_discovery_manifest(self, file_path: Path) -> None:
        """Export discovered plugins to a manifest file"""
        manifest = {
            'discovery_timestamp': '',
            'total_plugins': len(self.discovered_entries),
            'groups': {},
            'plugins': []
        }
        
        # Group statistics
        for group_name, entries in self.entry_point_cache.items():
            manifest['groups'][group_name] = {
                'count': len(entries),
                'plugins': [entry.name for entry in entries]
            }
        
        # Plugin details
        for entry in self.discovered_entries:
            manifest['plugins'].append({
                'name': entry.name,
                'group': entry.group,
                'version': entry.version,
                'description': entry.description,
                'module': entry.module_name,
                'class': entry.class_name,
                'entry_point': entry.entry_point,
                'metadata': entry.metadata
            })
        
        # Write manifest
        with open(file_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Plugin discovery manifest exported to {file_path}")

class DynamicPluginLoader:
    """Dynamic plugin loading and registration system"""
    
    def __init__(self):
        self.loaded_plugins: Dict[str, Any] = {}
        self.plugin_registry: Dict[str, PluginEntry] = {}
        
    async def load_plugin_from_entry(self, plugin_entry: PluginEntry) -> bool:
        """Load a plugin from a plugin entry"""
        try:
            # Import the module
            module = importlib.import_module(plugin_entry.module_name)
            
            # Get the plugin class
            plugin_class = getattr(module, plugin_entry.class_name)
            
            # Instantiate the plugin
            plugin_instance = plugin_class()
            
            # Store in registry
            self.loaded_plugins[plugin_entry.name] = plugin_instance
            self.plugin_registry[plugin_entry.name] = plugin_entry
            
            logger.info(f"Successfully loaded plugin: {plugin_entry.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_entry.name}: {e}")
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        if plugin_name not in self.loaded_plugins:
            return True  # Already unloaded
        
        try:
            plugin = self.loaded_plugins[plugin_name]
            
            # Call cleanup if available
            if hasattr(plugin, 'cleanup'):
                await plugin.cleanup()
            
            # Remove from registry
            del self.loaded_plugins[plugin_name]
            if plugin_name in self.plugin_registry:
                del self.plugin_registry[plugin_name]
            
            logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
    
    def get_loaded_plugin(self, plugin_name: str) -> Optional[Any]:
        """Get a loaded plugin instance"""
        return self.loaded_plugins.get(plugin_name)
    
    def get_plugins_by_group(self, group_name: str) -> List[Any]:
        """Get all loaded plugins from a specific group"""
        plugins = []
        for plugin_name, plugin_entry in self.plugin_registry.items():
            if plugin_entry.group == group_name and plugin_name in self.loaded_plugins:
                plugins.append(self.loaded_plugins[plugin_name])
        return plugins
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a plugin"""
        if plugin_name not in self.plugin_registry:
            return None
        
        entry = self.plugin_registry[plugin_name]
        plugin = self.loaded_plugins.get(plugin_name)
        
        info = {
            'name': entry.name,
            'group': entry.group,
            'version': entry.version,
            'description': entry.description,
            'loaded': plugin is not None,
            'metadata': entry.metadata
        }
        
        if plugin:
            # Get runtime info from plugin
            info['runtime_info'] = {
                'class': plugin.__class__.__name__,
                'module': plugin.__class__.__module__,
                'methods': [method for method in dir(plugin) if not method.startswith('_')]
            }
        
        return info