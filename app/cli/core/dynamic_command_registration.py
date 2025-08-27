"""
Dynamic Command Registration System
Advanced system for runtime discovery and registration of CLI commands
"""

import inspect
import importlib
import pkgutil
from typing import Dict, Any, List, Optional, Callable, Type
from pathlib import Path
import typer
from rich.console import Console
import logging
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)
console = Console()

@dataclass
class CommandInfo:
    """Information about a registered command"""
    name: str
    group: Optional[str]
    function: Callable
    help_text: str
    parameters: List[Dict[str, Any]]
    plugin_source: Optional[str] = None
    command_type: str = "standard"  # standard, workflow, agent, provider

@dataclass
class CommandGroup:
    """Information about a command group"""
    name: str
    description: str
    commands: List[CommandInfo]
    parent_group: Optional[str] = None

class DynamicCommandRegistry:
    """Registry for dynamically discovered and registered commands"""
    
    def __init__(self):
        self.commands: Dict[str, CommandInfo] = {}
        self.groups: Dict[str, CommandGroup] = {}
        self.app_instances: Dict[str, typer.Typer] = {}
        self.command_handlers: Dict[str, Callable] = {}
        
    def register_command(
        self,
        name: str,
        function: Callable,
        group: Optional[str] = None,
        help_text: str = "",
        plugin_source: Optional[str] = None,
        command_type: str = "standard"
    ) -> bool:
        """Register a new command"""
        try:
            # Extract parameter information
            parameters = self._extract_parameters(function)
            
            command_info = CommandInfo(
                name=name,
                group=group,
                function=function,
                help_text=help_text or function.__doc__ or "No description",
                parameters=parameters,
                plugin_source=plugin_source,
                command_type=command_type
            )
            
            self.commands[name] = command_info
            
            # Add to group
            if group:
                self._add_to_group(command_info, group)
            
            logger.info(f"Registered command: {name} (group: {group}, source: {plugin_source})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register command {name}: {e}")
            return False
    
    def _extract_parameters(self, function: Callable) -> List[Dict[str, Any]]:
        """Extract parameter information from function signature"""
        parameters = []
        
        try:
            signature = inspect.signature(function)
            
            for param_name, param in signature.parameters.items():
                param_info = {
                    'name': param_name,
                    'type': param.annotation if param.annotation != inspect.Parameter.empty else str,
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty
                }
                parameters.append(param_info)
                
        except Exception as e:
            logger.warning(f"Failed to extract parameters for function {function.__name__}: {e}")
            
        return parameters
    
    def _add_to_group(self, command_info: CommandInfo, group_name: str):
        """Add command to a group"""
        if group_name not in self.groups:
            self.groups[group_name] = CommandGroup(
                name=group_name,
                description=f"Commands for {group_name}",
                commands=[]
            )
        
        self.groups[group_name].commands.append(command_info)
    
    def unregister_command(self, name: str) -> bool:
        """Unregister a command"""
        if name not in self.commands:
            return False
        
        command = self.commands[name]
        
        # Remove from group
        if command.group and command.group in self.groups:
            self.groups[command.group].commands = [
                c for c in self.groups[command.group].commands if c.name != name
            ]
        
        # Remove from registry
        del self.commands[name]
        
        logger.info(f"Unregistered command: {name}")
        return True
    
    def get_command(self, name: str) -> Optional[CommandInfo]:
        """Get command information"""
        return self.commands.get(name)
    
    def get_commands_by_group(self, group_name: str) -> List[CommandInfo]:
        """Get all commands in a group"""
        group = self.groups.get(group_name)
        return group.commands if group else []
    
    def get_commands_by_type(self, command_type: str) -> List[CommandInfo]:
        """Get all commands of a specific type"""
        return [cmd for cmd in self.commands.values() if cmd.command_type == command_type]
    
    def get_all_groups(self) -> Dict[str, CommandGroup]:
        """Get all command groups"""
        return self.groups
    
    def generate_command_manifest(self) -> Dict[str, Any]:
        """Generate a manifest of all registered commands"""
        manifest = {
            'total_commands': len(self.commands),
            'total_groups': len(self.groups),
            'groups': {},
            'commands': {}
        }
        
        # Group information
        for group_name, group in self.groups.items():
            manifest['groups'][group_name] = {
                'description': group.description,
                'command_count': len(group.commands),
                'commands': [cmd.name for cmd in group.commands]
            }
        
        # Command information
        for cmd_name, cmd in self.commands.items():
            manifest['commands'][cmd_name] = {
                'group': cmd.group,
                'help': cmd.help_text,
                'type': cmd.command_type,
                'source': cmd.plugin_source,
                'parameters': cmd.parameters
            }
        
        return manifest

class DynamicCommandBuilder:
    """Build Typer commands dynamically from registered commands"""
    
    def __init__(self, registry: DynamicCommandRegistry):
        self.registry = registry
        
    def build_typer_app_from_group(self, group_name: str) -> Optional[typer.Typer]:
        """Build a Typer app from a command group"""
        if group_name not in self.registry.groups:
            return None
        
        group = self.registry.groups[group_name]
        app = typer.Typer(name=group_name, help=group.description)
        
        # Add commands to app
        for command in group.commands:
            self._add_command_to_app(app, command)
        
        return app
    
    def build_main_app_with_groups(self) -> typer.Typer:
        """Build main Typer app with all command groups"""
        main_app = typer.Typer(
            name="localagent",
            help="LocalAgent - Dynamic Multi-provider LLM CLI"
        )
        
        # Add standalone commands (no group)
        standalone_commands = [cmd for cmd in self.registry.commands.values() if not cmd.group]
        for command in standalone_commands:
            self._add_command_to_app(main_app, command)
        
        # Add grouped commands as sub-apps
        for group_name, group in self.registry.groups.items():
            if group.commands:  # Only add groups with commands
                group_app = self.build_typer_app_from_group(group_name)
                if group_app:
                    main_app.add_typer(group_app, name=group_name)
        
        return main_app
    
    def _add_command_to_app(self, app: typer.Typer, command_info: CommandInfo):
        """Add a command to a Typer app"""
        try:
            # Create wrapper function that handles the command execution
            def command_wrapper(*args, **kwargs):
                return command_info.function(*args, **kwargs)
            
            # Set function metadata
            command_wrapper.__name__ = command_info.name
            command_wrapper.__doc__ = command_info.help_text
            
            # Add command to app
            app.command(name=command_info.name, help=command_info.help_text)(command_wrapper)
            
        except Exception as e:
            logger.error(f"Failed to add command {command_info.name} to app: {e}")

class AutoCommandDiscovery:
    """Automatic discovery of commands from modules and plugins"""
    
    def __init__(self, registry: DynamicCommandRegistry):
        self.registry = registry
        
    async def discover_commands_in_module(
        self, 
        module_path: str,
        command_prefix: str = "",
        group_name: Optional[str] = None
    ) -> int:
        """Discover commands in a Python module"""
        discovered_count = 0
        
        try:
            module = importlib.import_module(module_path)
            
            # Look for functions with command decorators or naming conventions
            for name, obj in inspect.getmembers(module):
                if self._is_command_function(obj):
                    command_name = f"{command_prefix}{name}" if command_prefix else name
                    
                    success = self.registry.register_command(
                        name=command_name,
                        function=obj,
                        group=group_name,
                        plugin_source=module_path,
                        command_type="discovered"
                    )
                    
                    if success:
                        discovered_count += 1
                        
        except Exception as e:
            logger.error(f"Failed to discover commands in module {module_path}: {e}")
            
        return discovered_count
    
    async def discover_commands_in_directory(
        self,
        directory_path: Path,
        recursive: bool = True,
        group_name: Optional[str] = None
    ) -> int:
        """Discover commands in a directory of Python files"""
        discovered_count = 0
        
        if not directory_path.exists() or not directory_path.is_dir():
            return 0
        
        # Find Python files
        pattern = "**/*.py" if recursive else "*.py"
        for py_file in directory_path.glob(pattern):
            if py_file.name.startswith('_'):  # Skip private files
                continue
                
            try:
                # Convert to module path
                relative_path = py_file.relative_to(directory_path)
                module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
                module_path = ".".join(module_parts)
                
                count = await self.discover_commands_in_module(
                    module_path, 
                    group_name=group_name
                )
                discovered_count += count
                
            except Exception as e:
                logger.warning(f"Failed to process file {py_file}: {e}")
                
        return discovered_count
    
    def _is_command_function(self, obj: Any) -> bool:
        """Check if an object is a command function"""
        if not inspect.isfunction(obj):
            return False
        
        # Check for command naming conventions
        if obj.__name__.startswith('cmd_') or obj.__name__.endswith('_command'):
            return True
        
        # Check for command decorators (if any)
        if hasattr(obj, '_is_command'):
            return obj._is_command
        
        # Check for typer annotations
        if hasattr(obj, '__annotations__'):
            for annotation in obj.__annotations__.values():
                if 'typer' in str(annotation):
                    return True
        
        return False

# Command decorators for manual registration
def command(
    name: Optional[str] = None,
    group: Optional[str] = None,
    help_text: Optional[str] = None,
    command_type: str = "manual"
):
    """Decorator to mark a function as a command"""
    def decorator(func):
        func._is_command = True
        func._command_name = name or func.__name__
        func._command_group = group
        func._command_help = help_text
        func._command_type = command_type
        return func
    return decorator

def workflow_command(name: Optional[str] = None, phase: Optional[str] = None):
    """Decorator for workflow-related commands"""
    return command(name=name, group="workflow", command_type="workflow")

def agent_command(name: Optional[str] = None, agent_type: Optional[str] = None):
    """Decorator for agent-related commands"""
    return command(name=name, group="agents", command_type="agent")

def provider_command(name: Optional[str] = None, provider: Optional[str] = None):
    """Decorator for provider-related commands"""  
    return command(name=name, group="providers", command_type="provider")

# Example usage and testing
async def demo_dynamic_commands():
    """Demonstrate dynamic command registration"""
    
    # Create registry
    registry = DynamicCommandRegistry()
    
    # Register some example commands
    @command(name="hello", group="demo", help_text="Say hello")
    def hello_command(name: str = "World"):
        console.print(f"Hello, {name}!")
    
    @workflow_command(name="status", phase="all")
    def workflow_status():
        console.print("Workflow status: Active")
    
    @agent_command(name="list", agent_type="all")
    def list_agents():
        console.print("Available agents: 5")
    
    # Register commands
    registry.register_command("hello", hello_command, "demo", "Say hello", "manual")
    registry.register_command("workflow-status", workflow_status, "workflow", "Get workflow status", "manual")
    registry.register_command("list-agents", list_agents, "agents", "List agents", "manual")
    
    # Build Typer app
    builder = DynamicCommandBuilder(registry)
    app = builder.build_main_app_with_groups()
    
    # Generate manifest
    manifest = registry.generate_command_manifest()
    console.print("Command Manifest:", manifest)
    
    return app, registry

if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_dynamic_commands())