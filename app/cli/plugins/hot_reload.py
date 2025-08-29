"""
Plugin Hot-Reload System for LocalAgent CLI
Enables runtime plugin reloading without CLI restart
"""

import asyncio
import importlib
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
from rich.console import Console

console = Console()

class PluginHotReloadManager:
    """Manages hot-reloading of plugins at runtime"""
    
    def __init__(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.file_hashes: Dict[str, str] = {}
        self.reload_history: List[Dict[str, Any]] = []
        self.watch_task: Optional[asyncio.Task] = None
        self.reload_callbacks: List[callable] = []
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of a file for change detection"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    async def start_watching(self, interval: float = 2.0):
        """Start watching for plugin changes"""
        if self.watch_task:
            return
            
        self.watch_task = asyncio.create_task(self._watch_loop(interval))
        console.print("[green]Plugin hot-reload watcher started[/green]")
    
    async def stop_watching(self):
        """Stop watching for plugin changes"""
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
            self.watch_task = None
            console.print("[yellow]Plugin hot-reload watcher stopped[/yellow]")
    
    async def _watch_loop(self, interval: float):
        """Main watch loop for detecting plugin changes"""
        while True:
            try:
                await self._check_for_changes()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                console.print(f"[red]Error in hot-reload watcher: {e}[/red]")
                await asyncio.sleep(interval)
    
    async def _check_for_changes(self):
        """Check if any plugin files have changed"""
        changed_plugins = []
        
        for plugin_name, plugin_info in self.plugin_manager.discovered_plugins.items():
            if plugin_info.file_path and plugin_info.file_path.exists():
                current_hash = self.calculate_file_hash(plugin_info.file_path)
                
                if plugin_name not in self.file_hashes:
                    self.file_hashes[plugin_name] = current_hash
                elif self.file_hashes[plugin_name] != current_hash:
                    changed_plugins.append(plugin_name)
                    self.file_hashes[plugin_name] = current_hash
        
        if changed_plugins:
            for plugin_name in changed_plugins:
                await self.reload_plugin(plugin_name)
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a specific plugin"""
        try:
            console.print(f"[yellow]Reloading plugin: {plugin_name}[/yellow]")
            
            # Get plugin info
            plugin_info = self.plugin_manager.discovered_plugins.get(plugin_name)
            if not plugin_info:
                console.print(f"[red]Plugin {plugin_name} not found[/red]")
                return False
            
            # Cleanup existing plugin if loaded
            if plugin_name in self.plugin_manager.loaded_plugins:
                plugin_instance = self.plugin_manager.loaded_plugins[plugin_name]
                await plugin_instance.cleanup()
                del self.plugin_manager.loaded_plugins[plugin_name]
            
            # Reload module if it's a file-based plugin
            if plugin_info.file_path:
                module_name = f"localagent_plugin_{plugin_name}"
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
            
            # Re-discover and load the plugin
            await self.plugin_manager._load_plugin(plugin_name)
            
            # Record reload history
            self.reload_history.append({
                'plugin': plugin_name,
                'timestamp': datetime.now().isoformat(),
                'success': True
            })
            
            # Trigger callbacks
            for callback in self.reload_callbacks:
                await callback(plugin_name, True)
            
            console.print(f"[green]Successfully reloaded plugin: {plugin_name}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to reload plugin {plugin_name}: {e}[/red]")
            
            self.reload_history.append({
                'plugin': plugin_name,
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            })
            
            for callback in self.reload_callbacks:
                await callback(plugin_name, False)
            
            return False
    
    def register_reload_callback(self, callback: callable):
        """Register a callback for plugin reload events"""
        if callback not in self.reload_callbacks:
            self.reload_callbacks.append(callback)
    
    def unregister_reload_callback(self, callback: callable):
        """Unregister a reload callback"""
        if callback in self.reload_callbacks:
            self.reload_callbacks.remove(callback)
    
    def get_reload_history(self) -> List[Dict[str, Any]]:
        """Get plugin reload history"""
        return self.reload_history.copy()
    
    async def reload_all_plugins(self) -> Dict[str, bool]:
        """Reload all loaded plugins"""
        results = {}
        for plugin_name in list(self.plugin_manager.loaded_plugins.keys()):
            results[plugin_name] = await self.reload_plugin(plugin_name)
        return results