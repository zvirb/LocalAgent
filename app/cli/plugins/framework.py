"""
Plugin Framework for LocalAgent CLI
Extensible plugin system with entry points and dynamic loading
"""

import asyncio
import importlib
import importlib.util
import pkg_resources
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Union
import typer
from rich.console import Console
import time
import json

console = Console()

class PluginError(Exception):
    """Base exception for plugin-related errors"""
    pass

class PluginLoadError(PluginError):
    """Error loading a plugin"""
    pass

class PluginInitError(PluginError):
    """Error initializing a plugin"""
    pass

class CLIPlugin(ABC):
    """Abstract base class for LocalAgent CLI plugins"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier/name"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description"""
        pass
    
    @property
    def dependencies(self) -> List[str]:
        """List of plugin dependencies"""
        return []
    
    @property
    def requires_config(self) -> bool:
        """Whether plugin requires configuration"""
        return False
    
    @abstractmethod
    async def initialize(self, context: 'CLIContext') -> bool:
        """Initialize the plugin with CLI context"""
        pass
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources"""
        pass
    
    def register_commands(self, app: typer.Typer) -> None:
        """Register plugin commands with main CLI app (optional)"""
        pass
    
    def get_config_schema(self) -> Optional[Dict[str, Any]]:
        """Get configuration schema for this plugin (optional)"""
        return None

class CommandPlugin(CLIPlugin):
    """Base class for plugins that add CLI commands"""
    
    @abstractmethod
    def register_commands(self, app: typer.Typer) -> None:
        """Register plugin commands with main CLI app"""
        pass

class ProviderPlugin(CLIPlugin):
    """Base class for plugins that add LLM providers"""
    
    @abstractmethod
    def get_provider_class(self) -> Type:
        """Return the provider class"""
        pass
    
    @abstractmethod
    def get_provider_config_schema(self) -> Dict[str, Any]:
        """Return provider configuration schema"""
        pass

class UIPlugin(CLIPlugin):
    """Base class for plugins that extend UI components"""
    
    @abstractmethod
    def get_ui_components(self) -> Dict[str, Any]:
        """Return UI components provided by this plugin"""
        pass

class WorkflowPlugin(CLIPlugin):
    """Base class for plugins that add workflow phases or agents"""
    
    @abstractmethod
    def get_workflow_components(self) -> Dict[str, Any]:
        """Return workflow components (phases, agents, etc.)"""
        pass

class PluginInfo:
    """Information about a plugin"""
    
    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        plugin_class: Type[CLIPlugin],
        entry_point: Optional[str] = None,
        file_path: Optional[Path] = None,
        enabled: bool = False,
        loaded: bool = False
    ):
        self.name = name
        self.version = version
        self.description = description
        self.plugin_class = plugin_class
        self.entry_point = entry_point
        self.file_path = file_path
        self.enabled = enabled
        self.loaded = loaded
        self.dependencies = getattr(plugin_class, 'dependencies', [])
        self.requires_config = getattr(plugin_class, 'requires_config', False)

class PluginManager:
    """Manages plugin discovery, loading, and lifecycle with enhanced features"""
    
    def __init__(self, context: 'CLIContext'):
        self.context = context
        self.discovered_plugins: Dict[str, PluginInfo] = {}
        self.loaded_plugins: Dict[str, CLIPlugin] = {}
        self.enabled_plugins: List[str] = []
        self.plugin_directories: List[Path] = []
        self.entry_point_groups = [
            'localagent.plugins.commands',
            'localagent.plugins.providers', 
            'localagent.plugins.ui',
            'localagent.plugins.workflow',
            'localagent.plugins.tools',
            'localagent.plugins.integrations'
        ]
        # Enhanced discovery capabilities
        self.discovery_cache: Dict[str, List] = {}
        self.plugin_manifest: Dict[str, Any] = {}
    
    async def discover_plugins(self) -> None:
        """Discover all available plugins with enhanced discovery"""
        # Clear previous discoveries
        self.discovered_plugins.clear()
        self.discovery_cache.clear()
        
        # Set up plugin directories
        self._setup_plugin_directories()
        
        # Discover plugins from entry points (enhanced)
        await self._discover_entry_point_plugins()
        
        # Discover plugins from directories (if dev mode enabled)
        if hasattr(self.context.config, 'plugins') and getattr(self.context.config.plugins, 'allow_dev_plugins', False):
            await self._discover_directory_plugins()
        
        # Generate plugin manifest
        await self._generate_plugin_manifest()
        
        console.print(f"[green]Discovered {len(self.discovered_plugins)} plugins across {len(self.entry_point_groups)} groups[/green]")
    
    def _setup_plugin_directories(self) -> None:
        """Setup plugin directories from configuration"""
        self.plugin_directories.clear()
        
        for dir_path in self.context.config.plugins.plugin_directories:
            path = Path(dir_path).expanduser().resolve()
            if path.exists() and path.is_dir():
                self.plugin_directories.append(path)
            elif not path.exists():
                # Create directory if it doesn't exist
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    self.plugin_directories.append(path)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not create plugin directory {path}: {e}[/yellow]")
    
    async def _discover_entry_point_plugins(self) -> None:
        """Discover plugins through setuptools entry points"""
        for group_name in self.entry_point_groups:
            try:
                for entry_point in pkg_resources.iter_entry_points(group_name):
                    try:
                        plugin_class = entry_point.load()
                        
                        if not issubclass(plugin_class, CLIPlugin):
                            console.print(f"[yellow]Warning: Plugin {entry_point.name} does not inherit from CLIPlugin[/yellow]")
                            continue
                        
                        # Create plugin instance to get metadata
                        temp_instance = plugin_class()
                        
                        plugin_info = PluginInfo(
                            name=entry_point.name,
                            version=temp_instance.version,
                            description=temp_instance.description,
                            plugin_class=plugin_class,
                            entry_point=f"{group_name}:{entry_point.name}",
                            enabled=entry_point.name in self.context.config.plugins.enabled_plugins
                        )
                        
                        self.discovered_plugins[entry_point.name] = plugin_info
                        
                    except Exception as e:
                        console.print(f"[red]Error loading entry point plugin {entry_point.name}: {e}[/red]")
                        
            except Exception as e:
                console.print(f"[yellow]Warning: Could not discover plugins from group {group_name}: {e}[/yellow]")
    
    async def _discover_directory_plugins(self) -> None:
        """Discover plugins from plugin directories"""
        for plugin_dir in self.plugin_directories:
            if not plugin_dir.exists():
                continue
            
            # Look for Python files and packages
            for item in plugin_dir.iterdir():
                if item.is_file() and item.suffix == '.py' and not item.name.startswith('_'):
                    await self._load_plugin_from_file(item)
                elif item.is_dir() and not item.name.startswith('_'):
                    plugin_file = item / '__init__.py'
                    if plugin_file.exists():
                        await self._load_plugin_from_file(plugin_file)
    
    async def _load_plugin_from_file(self, plugin_file: Path) -> None:
        """Load a plugin from a Python file"""
        try:
            module_name = f"localagent_plugin_{plugin_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for plugin classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, CLIPlugin) and 
                    attr is not CLIPlugin):
                    
                    # Create instance to get metadata
                    temp_instance = attr()
                    
                    plugin_info = PluginInfo(
                        name=temp_instance.name,
                        version=temp_instance.version,
                        description=temp_instance.description,
                        plugin_class=attr,
                        file_path=plugin_file,
                        enabled=temp_instance.name in self.context.config.plugins.enabled_plugins
                    )
                    
                    if temp_instance.name not in self.discovered_plugins:
                        self.discovered_plugins[temp_instance.name] = plugin_info
                    
                    break
                    
        except Exception as e:
            console.print(f"[red]Error loading plugin from {plugin_file}: {e}[/red]")
    
    async def load_enabled_plugins(self) -> None:
        """Load all enabled plugins"""
        if self.context.config.plugins.auto_load_plugins:
            enabled_plugins = [
                name for name, info in self.discovered_plugins.items() 
                if info.enabled
            ]
        else:
            enabled_plugins = self.context.config.plugins.enabled_plugins
        
        # Sort plugins by dependencies
        load_order = self._resolve_plugin_dependencies(enabled_plugins)
        
        for plugin_name in load_order:
            success = await self.load_plugin(plugin_name)
            if success:
                console.print(f"[green]✓[/green] Loaded plugin: {plugin_name}")
            else:
                console.print(f"[red]✗[/red] Failed to load plugin: {plugin_name}")
    
    def _resolve_plugin_dependencies(self, plugin_names: List[str]) -> List[str]:
        """Resolve plugin loading order based on dependencies"""
        resolved = []
        unresolved = plugin_names.copy()
        
        while unresolved:
            progress_made = False
            
            for plugin_name in unresolved.copy():
                plugin_info = self.discovered_plugins.get(plugin_name)
                if not plugin_info:
                    unresolved.remove(plugin_name)
                    continue
                
                # Check if all dependencies are resolved
                dependencies_met = all(
                    dep in resolved or dep not in self.discovered_plugins
                    for dep in plugin_info.dependencies
                )
                
                if dependencies_met:
                    resolved.append(plugin_name)
                    unresolved.remove(plugin_name)
                    progress_made = True
            
            if not progress_made and unresolved:
                # Circular dependency or missing dependencies
                console.print(f"[yellow]Warning: Could not resolve dependencies for plugins: {unresolved}[/yellow]")
                resolved.extend(unresolved)  # Load anyway
                break
        
        return resolved
    
    async def load_plugin(self, plugin_name: str) -> bool:
        """Load a specific plugin"""
        if plugin_name in self.loaded_plugins:
            return True  # Already loaded
        
        plugin_info = self.discovered_plugins.get(plugin_name)
        if not plugin_info:
            console.print(f"[red]Plugin '{plugin_name}' not found[/red]")
            return False
        
        try:
            # Create plugin instance
            plugin_instance = plugin_info.plugin_class()
            
            # Initialize plugin
            success = await plugin_instance.initialize(self.context)
            if not success:
                raise PluginInitError(f"Plugin initialization returned False")
            
            # Store loaded plugin
            self.loaded_plugins[plugin_name] = plugin_instance
            plugin_info.loaded = True
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to load plugin '{plugin_name}': {e}[/red]")
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin"""
        if plugin_name not in self.loaded_plugins:
            return True  # Already unloaded
        
        try:
            plugin = self.loaded_plugins[plugin_name]
            
            # Cleanup plugin
            await plugin.cleanup()
            
            # Remove from loaded plugins
            del self.loaded_plugins[plugin_name]
            
            # Update plugin info
            if plugin_name in self.discovered_plugins:
                self.discovered_plugins[plugin_name].loaded = False
            
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to unload plugin '{plugin_name}': {e}[/red]")
            return False
    
    async def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin"""
        plugin_info = self.discovered_plugins.get(plugin_name)
        if not plugin_info:
            console.print(f"[red]Plugin '{plugin_name}' not found[/red]")
            return False
        
        if plugin_info.enabled:
            console.print(f"[yellow]Plugin '{plugin_name}' already enabled[/yellow]")
            return True
        
        # Enable plugin
        plugin_info.enabled = True
        
        # Update configuration
        if plugin_name not in self.context.config.plugins.enabled_plugins:
            self.context.config.plugins.enabled_plugins.append(plugin_name)
        
        # Load plugin if auto-load is enabled
        if self.context.config.plugins.auto_load_plugins:
            return await self.load_plugin(plugin_name)
        
        return True
    
    async def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin"""
        plugin_info = self.discovered_plugins.get(plugin_name)
        if not plugin_info:
            console.print(f"[red]Plugin '{plugin_name}' not found[/red]")
            return False
        
        # Unload if loaded
        if plugin_info.loaded:
            await self.unload_plugin(plugin_name)
        
        # Disable plugin
        plugin_info.enabled = False
        
        # Update configuration
        if plugin_name in self.context.config.plugins.enabled_plugins:
            self.context.config.plugins.enabled_plugins.remove(plugin_name)
        
        return True
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin"""
        success = await self.unload_plugin(plugin_name)
        if success:
            success = await self.load_plugin(plugin_name)
        return success
    
    async def get_plugins_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all discovered plugins"""
        plugins_info = {}
        
        for plugin_name, plugin_info in self.discovered_plugins.items():
            plugins_info[plugin_name] = {
                'name': plugin_info.name,
                'version': plugin_info.version,
                'description': plugin_info.description,
                'enabled': plugin_info.enabled,
                'loaded': plugin_info.loaded,
                'entry_point': plugin_info.entry_point,
                'file_path': str(plugin_info.file_path) if plugin_info.file_path else None,
                'dependencies': plugin_info.dependencies,
                'requires_config': plugin_info.requires_config
            }
        
        return plugins_info
    
    async def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific plugin"""
        if plugin_name not in self.discovered_plugins:
            return None
        
        plugin_info = self.discovered_plugins[plugin_name]
        
        info = {
            'name': plugin_info.name,
            'version': plugin_info.version,
            'description': plugin_info.description,
            'enabled': plugin_info.enabled,
            'loaded': plugin_info.loaded,
            'entry_point': plugin_info.entry_point,
            'file_path': str(plugin_info.file_path) if plugin_info.file_path else None,
            'dependencies': plugin_info.dependencies,
            'requires_config': plugin_info.requires_config
        }
        
        # Get additional info from loaded plugin
        if plugin_info.loaded:
            plugin = self.loaded_plugins[plugin_name]
            
            # Get config schema if available
            if hasattr(plugin, 'get_config_schema'):
                info['config_schema'] = plugin.get_config_schema()
        
        return info
    
    def get_loaded_plugin(self, plugin_name: str) -> Optional[CLIPlugin]:
        """Get a loaded plugin instance"""
        return self.loaded_plugins.get(plugin_name)
    
    def get_plugins_by_type(self, plugin_type: Type[CLIPlugin]) -> List[CLIPlugin]:
        """Get all loaded plugins of a specific type"""
        return [
            plugin for plugin in self.loaded_plugins.values()
            if isinstance(plugin, plugin_type)
        ]
    
    async def _generate_plugin_manifest(self) -> None:
        """Generate manifest of discovered plugins"""
        self.plugin_manifest = {
            'discovery_timestamp': time.time(),
            'total_plugins': len(self.discovered_plugins),
            'groups': {},
            'plugins': {}
        }
        
        # Group statistics
        for group_name in self.entry_point_groups:
            group_plugins = [p for p in self.discovered_plugins.values() if hasattr(p, 'entry_point') and p.entry_point and p.entry_point.startswith(group_name)]
            self.plugin_manifest['groups'][group_name] = {
                'count': len(group_plugins),
                'plugins': [p.name for p in group_plugins]
            }
        
        # Plugin details
        for plugin_name, plugin_info in self.discovered_plugins.items():
            self.plugin_manifest['plugins'][plugin_name] = {
                'name': plugin_info.name,
                'version': plugin_info.version,
                'description': plugin_info.description,
                'enabled': plugin_info.enabled,
                'loaded': plugin_info.loaded,
                'entry_point': plugin_info.entry_point,
                'dependencies': plugin_info.dependencies,
                'requires_config': plugin_info.requires_config
            }
    
    def get_plugin_manifest(self) -> Dict[str, Any]:
        """Get the generated plugin manifest"""
        return self.plugin_manifest
    
    async def register_builtin_plugins(self) -> int:
        """Register built-in plugins"""
        registered_count = 0
        
        # Import and register built-in plugins
        try:
            builtin_plugins = [
                ('system-info', 'SystemInfoPlugin'),
                ('workflow-debug', 'WorkflowDebugPlugin'), 
                ('config-manager', 'ConfigurationPlugin')
            ]
            
            for plugin_name, class_name in builtin_plugins:
                # Create plugin info for built-in plugins
                plugin_info = PluginInfo(
                    name=plugin_name,
                    version='1.0.0',
                    description=f'Built-in {plugin_name} plugin',
                    plugin_class=type,  # Placeholder
                    enabled=True,
                    loaded=False
                )
                
                self.discovered_plugins[plugin_name] = plugin_info
                registered_count += 1
                
        except Exception as e:
            console.print(f"[yellow]Warning: Could not register all built-in plugins: {e}[/yellow]")
            
        return registered_count
    
    async def cleanup_all_plugins(self) -> None:
        """Cleanup all loaded plugins"""
        for plugin_name in list(self.loaded_plugins.keys()):
            await self.unload_plugin(plugin_name)