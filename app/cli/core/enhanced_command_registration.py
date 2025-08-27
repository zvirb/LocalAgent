"""
Enhanced Dynamic Command Registration System
Advanced system for runtime discovery, registration, and management of CLI commands
with comprehensive plugin integration and performance optimization
"""

import inspect
import importlib
import pkgutil
from typing import Dict, Any, List, Optional, Callable, Type, Union, Set
from pathlib import Path
import typer
from rich.console import Console
import logging
from dataclasses import dataclass, field
from functools import wraps
import asyncio
import threading
import weakref
from enum import Enum
import uuid
import time

logger = logging.getLogger(__name__)
console = Console()

class CommandPriority(Enum):
    """Command priority levels for loading order"""
    SYSTEM = 0      # Core system commands (highest priority)
    BUILTIN = 1     # Built-in plugin commands
    PLUGIN = 2      # Third-party plugin commands  
    USER = 3        # User-defined commands
    DYNAMIC = 4     # Dynamically discovered commands (lowest priority)

class CommandScope(Enum):
    """Command scope definitions"""
    GLOBAL = "global"           # Available in all contexts
    WORKFLOW = "workflow"       # Only during workflow execution
    PROJECT = "project"         # Only within project contexts
    DEBUG = "debug"            # Only in debug mode
    DEVELOPMENT = "development" # Only in development mode

@dataclass
class CommandMetadata:
    """Extended metadata for registered commands"""
    name: str
    group: Optional[str]
    function: Callable
    help_text: str
    parameters: List[Dict[str, Any]]
    plugin_source: Optional[str] = None
    command_type: str = "standard"
    priority: CommandPriority = CommandPriority.USER
    scope: CommandScope = CommandScope.GLOBAL
    aliases: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    version: str = "1.0.0"
    author: Optional[str] = None
    requires_auth: bool = False
    requires_config: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    experimental: bool = False
    deprecated: bool = False
    replacement_command: Optional[str] = None
    
    # Performance metrics
    call_count: int = field(default=0, init=False)
    total_execution_time: float = field(default=0.0, init=False)
    last_called: Optional[float] = field(default=None, init=False)
    
    # Registration metadata
    registration_time: float = field(default_factory=time.time, init=False)
    registration_id: str = field(default_factory=lambda: uuid.uuid4().hex, init=False)

@dataclass
class CommandGroup:
    """Enhanced command group with metadata and organization"""
    name: str
    description: str
    commands: List[CommandMetadata]
    parent_group: Optional[str] = None
    priority: CommandPriority = CommandPriority.USER
    scope: CommandScope = CommandScope.GLOBAL
    hidden: bool = False
    requires_auth: bool = False
    icon: Optional[str] = None
    
    # Organization
    subgroups: Dict[str, 'CommandGroup'] = field(default_factory=dict)
    
    # Statistics
    total_calls: int = field(default=0, init=False)
    creation_time: float = field(default_factory=time.time, init=False)

class EnhancedCommandRegistry:
    """Advanced registry for dynamically discovered and registered commands with comprehensive management"""
    
    def __init__(self):
        self.commands: Dict[str, CommandMetadata] = {}
        self.groups: Dict[str, CommandGroup] = {}
        self.aliases: Dict[str, str] = {}  # alias -> command_name mapping
        self.app_instances: Dict[str, typer.Typer] = {}
        self.command_handlers: Dict[str, Callable] = {}
        
        # Advanced features
        self.middleware: List[Callable] = []
        self.validators: Dict[str, List[Callable]] = {}
        self.hooks = {
            'before_register': [],
            'after_register': [],
            'before_execute': [],
            'after_execute': [],
            'on_error': []
        }
        
        # Performance optimization
        self._command_cache: Dict[str, CommandMetadata] = {}
        self._resolution_cache: Dict[str, str] = {}
        self._cache_lock = threading.RLock()
        
        # Statistics and monitoring
        self.registry_stats = {
            'total_commands': 0,
            'total_groups': 0,
            'commands_by_priority': {p: 0 for p in CommandPriority},
            'commands_by_scope': {s: 0 for s in CommandScope},
            'total_calls': 0,
            'total_execution_time': 0.0,
            'most_used_commands': {},
            'error_count': 0
        }
        
        # Weak references for memory management
        self._weak_refs: Dict[str, weakref.ref] = {}
    
    def register_command(
        self,
        name: str,
        function: Callable,
        group: Optional[str] = None,
        help_text: str = "",
        plugin_source: Optional[str] = None,
        command_type: str = "standard",
        priority: CommandPriority = CommandPriority.USER,
        scope: CommandScope = CommandScope.GLOBAL,
        aliases: List[str] = None,
        tags: Set[str] = None,
        **metadata_kwargs
    ) -> bool:
        """Register a new command with comprehensive metadata"""
        
        # Execute before_register hooks
        for hook in self.hooks['before_register']:
            try:
                hook(name, function, locals())
            except Exception as e:
                logger.warning(f"Before register hook failed: {e}")
        
        try:
            # Validate command name
            if not self._validate_command_name(name):
                logger.error(f"Invalid command name: {name}")
                return False
            
            # Check for conflicts
            if name in self.commands:
                logger.warning(f"Command {name} already registered, overriding")
            
            # Extract parameter information
            parameters = self._extract_parameters(function)
            
            # Create command metadata
            command_metadata = CommandMetadata(
                name=name,
                group=group,
                function=function,
                help_text=help_text or function.__doc__ or "No description",
                parameters=parameters,
                plugin_source=plugin_source,
                command_type=command_type,
                priority=priority,
                scope=scope,
                aliases=aliases or [],
                tags=tags or set(),
                **metadata_kwargs
            )
            
            # Register command
            self.commands[name] = command_metadata
            
            # Register aliases
            if aliases:
                for alias in aliases:
                    if alias in self.aliases:
                        logger.warning(f"Alias {alias} already exists, overriding")
                    self.aliases[alias] = name
            
            # Add to group
            if group:
                self._add_to_group(command_metadata, group)
            
            # Update cache
            with self._cache_lock:
                self._command_cache[name] = command_metadata
                self._resolution_cache.clear()  # Clear resolution cache
            
            # Update statistics
            self._update_registration_stats(command_metadata)
            
            # Execute after_register hooks
            for hook in self.hooks['after_register']:
                try:
                    hook(name, command_metadata)
                except Exception as e:
                    logger.warning(f"After register hook failed: {e}")
            
            logger.info(f"Registered command: {name} (group: {group}, priority: {priority.name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register command {name}: {e}")
            return False
    
    def _validate_command_name(self, name: str) -> bool:
        """Validate command name meets requirements"""
        if not name or not isinstance(name, str):
            return False
        
        # Check for reserved names
        reserved_names = {'help', 'version', '__init__', '__call__'}
        if name in reserved_names:
            return False
        
        # Check for valid characters
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
            return False
        
        return True
    
    def _extract_parameters(self, function: Callable) -> List[Dict[str, Any]]:
        """Extract enhanced parameter information from function signature"""
        parameters = []
        
        try:
            signature = inspect.signature(function)
            
            for param_name, param in signature.parameters.items():
                param_info = {
                    'name': param_name,
                    'type': param.annotation if param.annotation != inspect.Parameter.empty else str,
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty,
                    'kind': param.kind.name,
                    'description': self._extract_param_description(function, param_name)
                }
                parameters.append(param_info)
                
        except Exception as e:
            logger.warning(f"Failed to extract parameters for function {function.__name__}: {e}")
            
        return parameters
    
    def _extract_param_description(self, function: Callable, param_name: str) -> Optional[str]:
        """Extract parameter description from docstring"""
        try:
            docstring = function.__doc__ or ""
            # Simple docstring parsing - could be enhanced with proper parsers
            lines = docstring.split('\n')
            for line in lines:
                if param_name in line and ':' in line:
                    return line.split(':', 1)[1].strip()
        except Exception:
            pass
        return None
    
    def _add_to_group(self, command_metadata: CommandMetadata, group_name: str):
        """Add command to a group with enhanced organization"""
        if group_name not in self.groups:
            # Create new group with intelligent defaults
            self.groups[group_name] = CommandGroup(
                name=group_name,
                description=f"Commands for {group_name}",
                commands=[],
                priority=command_metadata.priority,
                scope=command_metadata.scope
            )
        
        # Add command to group
        group = self.groups[group_name]
        
        # Remove from existing group if present
        for existing_group in self.groups.values():
            existing_group.commands = [c for c in existing_group.commands if c.name != command_metadata.name]
        
        group.commands.append(command_metadata)
        
        # Sort commands by priority within group
        group.commands.sort(key=lambda c: c.priority.value)
    
    def _update_registration_stats(self, command_metadata: CommandMetadata):
        """Update registry statistics"""
        self.registry_stats['total_commands'] = len(self.commands)
        self.registry_stats['total_groups'] = len(self.groups)
        self.registry_stats['commands_by_priority'][command_metadata.priority] += 1
        self.registry_stats['commands_by_scope'][command_metadata.scope] += 1
    
    def unregister_command(self, name: str) -> bool:
        """Unregister a command and clean up all references"""
        if name not in self.commands:
            return False
        
        command_metadata = self.commands[name]
        
        try:
            # Remove from group
            if command_metadata.group and command_metadata.group in self.groups:
                self.groups[command_metadata.group].commands = [
                    c for c in self.groups[command_metadata.group].commands 
                    if c.name != name
                ]
            
            # Remove aliases
            aliases_to_remove = [alias for alias, cmd_name in self.aliases.items() if cmd_name == name]
            for alias in aliases_to_remove:
                del self.aliases[alias]
            
            # Clear caches
            with self._cache_lock:
                self._command_cache.pop(name, None)
                self._resolution_cache.clear()
            
            # Remove from registry
            del self.commands[name]
            
            # Update statistics
            self.registry_stats['commands_by_priority'][command_metadata.priority] -= 1
            self.registry_stats['commands_by_scope'][command_metadata.scope] -= 1
            self.registry_stats['total_commands'] = len(self.commands)
            
            logger.info(f"Unregistered command: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister command {name}: {e}")
            return False
    
    def resolve_command(self, name_or_alias: str) -> Optional[CommandMetadata]:
        """Resolve command name or alias to command metadata with caching"""
        
        # Check cache first
        with self._cache_lock:
            if name_or_alias in self._resolution_cache:
                cached_name = self._resolution_cache[name_or_alias]
                return self._command_cache.get(cached_name)
        
        # Direct command lookup
        if name_or_alias in self.commands:
            command_metadata = self.commands[name_or_alias]
            with self._cache_lock:
                self._resolution_cache[name_or_alias] = name_or_alias
                self._command_cache[name_or_alias] = command_metadata
            return command_metadata
        
        # Alias lookup
        if name_or_alias in self.aliases:
            actual_name = self.aliases[name_or_alias]
            if actual_name in self.commands:
                command_metadata = self.commands[actual_name]
                with self._cache_lock:
                    self._resolution_cache[name_or_alias] = actual_name
                    self._command_cache[actual_name] = command_metadata
                return command_metadata
        
        return None
    
    def get_command(self, name: str) -> Optional[CommandMetadata]:
        """Get command metadata by name"""
        return self.resolve_command(name)
    
    def get_commands_by_group(self, group_name: str) -> List[CommandMetadata]:
        """Get all commands in a group"""
        group = self.groups.get(group_name)
        return group.commands if group else []
    
    def get_commands_by_type(self, command_type: str) -> List[CommandMetadata]:
        """Get all commands of a specific type"""
        return [cmd for cmd in self.commands.values() if cmd.command_type == command_type]
    
    def get_commands_by_priority(self, priority: CommandPriority) -> List[CommandMetadata]:
        """Get all commands with specific priority"""
        return [cmd for cmd in self.commands.values() if cmd.priority == priority]
    
    def get_commands_by_scope(self, scope: CommandScope) -> List[CommandMetadata]:
        """Get all commands with specific scope"""
        return [cmd for cmd in self.commands.values() if cmd.scope == scope]
    
    def get_commands_by_tags(self, tags: Set[str], match_all: bool = False) -> List[CommandMetadata]:
        """Get commands matching specified tags"""
        results = []
        for cmd in self.commands.values():
            if match_all:
                if tags.issubset(cmd.tags):
                    results.append(cmd)
            else:
                if tags.intersection(cmd.tags):
                    results.append(cmd)
        return results
    
    def search_commands(self, query: str, search_help: bool = True) -> List[CommandMetadata]:
        """Search commands by name, aliases, or help text"""
        query = query.lower()
        results = []
        
        for cmd in self.commands.values():
            # Search in name
            if query in cmd.name.lower():
                results.append(cmd)
                continue
            
            # Search in aliases
            if any(query in alias.lower() for alias in cmd.aliases):
                results.append(cmd)
                continue
            
            # Search in help text
            if search_help and query in cmd.help_text.lower():
                results.append(cmd)
                continue
        
        return results
    
    def get_all_groups(self) -> Dict[str, CommandGroup]:
        """Get all command groups"""
        return self.groups
    
    def add_middleware(self, middleware: Callable):
        """Add middleware for command execution"""
        self.middleware.append(middleware)
    
    def add_validator(self, command_name: str, validator: Callable):
        """Add validator for specific command"""
        if command_name not in self.validators:
            self.validators[command_name] = []
        self.validators[command_name].append(validator)
    
    def add_hook(self, hook_name: str, hook_function: Callable):
        """Add hook function"""
        if hook_name in self.hooks:
            self.hooks[hook_name].append(hook_function)
        else:
            logger.warning(f"Unknown hook type: {hook_name}")
    
    async def execute_command(self, command_name: str, *args, **kwargs) -> Any:
        """Execute a command with full middleware and monitoring"""
        
        # Resolve command
        command_metadata = self.resolve_command(command_name)
        if not command_metadata:
            raise ValueError(f"Command '{command_name}' not found")
        
        # Update execution statistics
        command_metadata.call_count += 1
        command_metadata.last_called = time.time()
        self.registry_stats['total_calls'] += 1
        
        start_time = time.time()
        
        try:
            # Execute before_execute hooks
            for hook in self.hooks['before_execute']:
                try:
                    await hook(command_metadata, args, kwargs) if asyncio.iscoroutinefunction(hook) else hook(command_metadata, args, kwargs)
                except Exception as e:
                    logger.warning(f"Before execute hook failed: {e}")
            
            # Run validators
            if command_name in self.validators:
                for validator in self.validators[command_name]:
                    if not validator(*args, **kwargs):
                        raise ValueError(f"Validation failed for command {command_name}")
            
            # Apply middleware
            execution_context = {
                'command': command_metadata,
                'args': args,
                'kwargs': kwargs,
                'start_time': start_time
            }
            
            for middleware in self.middleware:
                execution_context = middleware(execution_context) or execution_context
            
            # Execute the actual command
            function = command_metadata.function
            if asyncio.iscoroutinefunction(function):
                result = await function(*args, **kwargs)
            else:
                result = function(*args, **kwargs)
            
            # Update performance metrics
            execution_time = time.time() - start_time
            command_metadata.total_execution_time += execution_time
            self.registry_stats['total_execution_time'] += execution_time
            
            # Execute after_execute hooks
            for hook in self.hooks['after_execute']:
                try:
                    await hook(command_metadata, result, execution_time) if asyncio.iscoroutinefunction(hook) else hook(command_metadata, result, execution_time)
                except Exception as e:
                    logger.warning(f"After execute hook failed: {e}")
            
            return result
            
        except Exception as e:
            # Update error statistics
            self.registry_stats['error_count'] += 1
            
            # Execute error hooks
            for hook in self.hooks['on_error']:
                try:
                    await hook(command_metadata, e) if asyncio.iscoroutinefunction(hook) else hook(command_metadata, e)
                except Exception as hook_error:
                    logger.warning(f"Error hook failed: {hook_error}")
            
            raise
    
    def generate_command_manifest(self) -> Dict[str, Any]:
        """Generate comprehensive manifest of all registered commands"""
        manifest = {
            'metadata': {
                'version': '2.0.0',
                'generated_at': time.time(),
                'total_commands': len(self.commands),
                'total_groups': len(self.groups),
                'total_aliases': len(self.aliases)
            },
            'statistics': self.registry_stats.copy(),
            'groups': {},
            'commands': {},
            'aliases': dict(self.aliases),
            'command_hierarchy': self._build_command_hierarchy()
        }
        
        # Group information
        for group_name, group in self.groups.items():
            manifest['groups'][group_name] = {
                'description': group.description,
                'command_count': len(group.commands),
                'commands': [cmd.name for cmd in group.commands],
                'priority': group.priority.name,
                'scope': group.scope.value,
                'hidden': group.hidden,
                'requires_auth': group.requires_auth,
                'total_calls': group.total_calls,
                'creation_time': group.creation_time
            }
        
        # Command information
        for cmd_name, cmd in self.commands.items():
            manifest['commands'][cmd_name] = {
                'group': cmd.group,
                'help': cmd.help_text,
                'type': cmd.command_type,
                'source': cmd.plugin_source,
                'parameters': cmd.parameters,
                'priority': cmd.priority.name,
                'scope': cmd.scope.value,
                'aliases': cmd.aliases,
                'tags': list(cmd.tags),
                'version': cmd.version,
                'author': cmd.author,
                'requires_auth': cmd.requires_auth,
                'requires_config': cmd.requires_config,
                'dependencies': cmd.dependencies,
                'experimental': cmd.experimental,
                'deprecated': cmd.deprecated,
                'replacement_command': cmd.replacement_command,
                'statistics': {
                    'call_count': cmd.call_count,
                    'total_execution_time': cmd.total_execution_time,
                    'last_called': cmd.last_called,
                    'avg_execution_time': cmd.total_execution_time / cmd.call_count if cmd.call_count > 0 else 0
                },
                'registration_time': cmd.registration_time,
                'registration_id': cmd.registration_id
            }
        
        return manifest
    
    def _build_command_hierarchy(self) -> Dict[str, Any]:
        """Build hierarchical command structure"""
        hierarchy = {}
        
        for group_name, group in self.groups.items():
            if group.parent_group:
                # Nested group structure
                if group.parent_group not in hierarchy:
                    hierarchy[group.parent_group] = {'subgroups': {}, 'commands': []}
                hierarchy[group.parent_group]['subgroups'][group_name] = {
                    'commands': [cmd.name for cmd in group.commands]
                }
            else:
                # Top-level group
                hierarchy[group_name] = {
                    'commands': [cmd.name for cmd in group.commands],
                    'subgroups': {}
                }
        
        return hierarchy
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report for commands"""
        report = {
            'overview': self.registry_stats.copy(),
            'top_commands_by_usage': [],
            'top_commands_by_execution_time': [],
            'slow_commands': [],
            'error_prone_commands': [],
            'cache_statistics': {
                'command_cache_size': len(self._command_cache),
                'resolution_cache_size': len(self._resolution_cache)
            }
        }
        
        # Sort commands by usage
        commands_by_usage = sorted(
            self.commands.values(),
            key=lambda c: c.call_count,
            reverse=True
        )
        report['top_commands_by_usage'] = [
            {
                'name': cmd.name,
                'call_count': cmd.call_count,
                'total_time': cmd.total_execution_time,
                'avg_time': cmd.total_execution_time / cmd.call_count if cmd.call_count > 0 else 0
            }
            for cmd in commands_by_usage[:10]
        ]
        
        # Sort commands by execution time
        commands_by_time = sorted(
            [cmd for cmd in self.commands.values() if cmd.call_count > 0],
            key=lambda c: c.total_execution_time,
            reverse=True
        )
        report['top_commands_by_execution_time'] = [
            {
                'name': cmd.name,
                'total_time': cmd.total_execution_time,
                'call_count': cmd.call_count,
                'avg_time': cmd.total_execution_time / cmd.call_count
            }
            for cmd in commands_by_time[:10]
        ]
        
        # Identify slow commands (average execution time > 1 second)
        slow_commands = [
            cmd for cmd in self.commands.values()
            if cmd.call_count > 0 and (cmd.total_execution_time / cmd.call_count) > 1.0
        ]
        report['slow_commands'] = [
            {
                'name': cmd.name,
                'avg_time': cmd.total_execution_time / cmd.call_count,
                'call_count': cmd.call_count
            }
            for cmd in slow_commands
        ]
        
        return report
    
    def cleanup(self):
        """Cleanup registry resources"""
        with self._cache_lock:
            self._command_cache.clear()
            self._resolution_cache.clear()
        
        self.middleware.clear()
        self.validators.clear()
        
        for hook_list in self.hooks.values():
            hook_list.clear()
        
        # Clear weak references
        self._weak_refs.clear()
        
        logger.info("Command registry cleaned up")

# Enhanced Command Builder with Modern Features
class EnhancedCommandBuilder:
    """Build Typer commands dynamically with advanced features"""
    
    def __init__(self, registry: EnhancedCommandRegistry):
        self.registry = registry
        self.built_apps: Dict[str, typer.Typer] = {}
        
    def build_typer_app_from_group(
        self, 
        group_name: str,
        include_subgroups: bool = True
    ) -> Optional[typer.Typer]:
        """Build enhanced Typer app from a command group"""
        if group_name not in self.registry.groups:
            return None
        
        group = self.registry.groups[group_name]
        
        # Check if already built and cached
        if group_name in self.built_apps:
            return self.built_apps[group_name]
        
        app = typer.Typer(
            name=group_name,
            help=group.description,
            no_args_is_help=True,
            rich_markup_mode="rich"
        )
        
        # Add commands to app sorted by priority
        sorted_commands = sorted(group.commands, key=lambda c: c.priority.value)
        for command_metadata in sorted_commands:
            if not command_metadata.deprecated:  # Skip deprecated commands
                self._add_command_to_app(app, command_metadata)
        
        # Add subgroups if requested
        if include_subgroups:
            for subgroup_name, subgroup in group.subgroups.items():
                subgroup_app = self.build_typer_app_from_group(subgroup_name, include_subgroups)
                if subgroup_app:
                    app.add_typer(subgroup_app, name=subgroup_name)
        
        # Cache the built app
        self.built_apps[group_name] = app
        
        return app
    
    def build_main_app_with_groups(self, include_hidden: bool = False) -> typer.Typer:
        """Build comprehensive main Typer app with all command groups"""
        main_app = typer.Typer(
            name="localagent",
            help="LocalAgent - Advanced Multi-provider LLM CLI with Dynamic Command System",
            no_args_is_help=True,
            rich_markup_mode="rich",
            context_settings={"help_option_names": ["-h", "--help"]}
        )
        
        # Add standalone commands (no group) sorted by priority
        standalone_commands = [
            cmd for cmd in self.registry.commands.values()
            if not cmd.group and (include_hidden or not cmd.deprecated)
        ]
        standalone_commands.sort(key=lambda c: c.priority.value)
        
        for command_metadata in standalone_commands:
            self._add_command_to_app(main_app, command_metadata)
        
        # Add grouped commands as sub-apps
        # Sort groups by priority
        sorted_groups = sorted(
            self.registry.groups.items(),
            key=lambda item: item[1].priority.value
        )
        
        for group_name, group in sorted_groups:
            if group.commands and (include_hidden or not group.hidden):
                group_app = self.build_typer_app_from_group(group_name)
                if group_app:
                    main_app.add_typer(group_app, name=group_name)
        
        return main_app
    
    def _add_command_to_app(self, app: typer.Typer, command_metadata: CommandMetadata):
        """Add a command to a Typer app with comprehensive enhancement"""
        try:
            # Create enhanced wrapper function
            @wraps(command_metadata.function)
            async def enhanced_command_wrapper(*args, **kwargs):
                return await self.registry.execute_command(command_metadata.name, *args, **kwargs)
            
            # Set function metadata
            enhanced_command_wrapper.__name__ = command_metadata.name
            enhanced_command_wrapper.__doc__ = command_metadata.help_text
            
            # Build help text with additional metadata
            help_parts = [command_metadata.help_text]
            
            if command_metadata.experimental:
                help_parts.append("[red bold]⚠ EXPERIMENTAL[/red bold]")
            
            if command_metadata.deprecated:
                help_parts.append("[yellow]⚠ DEPRECATED[/yellow]")
                if command_metadata.replacement_command:
                    help_parts.append(f"Use '{command_metadata.replacement_command}' instead")
            
            if command_metadata.requires_auth:
                help_parts.append("[cyan]🔒 Requires Authentication[/cyan]")
            
            if command_metadata.aliases:
                help_parts.append(f"[dim]Aliases: {', '.join(command_metadata.aliases)}[/dim]")
            
            enhanced_help = "\n".join(help_parts)
            
            # Add command with enhanced help
            decorator = app.command(
                name=command_metadata.name,
                help=enhanced_help,
                hidden=command_metadata.deprecated
            )
            
            # Apply the decorator
            decorated_command = decorator(enhanced_command_wrapper)
            
        except Exception as e:
            logger.error(f"Failed to add command {command_metadata.name} to app: {e}")
    
    def rebuild_apps(self):
        """Rebuild all cached apps"""
        self.built_apps.clear()
        
        for group_name in self.registry.groups.keys():
            self.build_typer_app_from_group(group_name)

# Factory and utility functions
def create_enhanced_registry() -> EnhancedCommandRegistry:
    """Create and configure enhanced command registry"""
    registry = EnhancedCommandRegistry()
    
    # Add default middleware for logging
    def logging_middleware(context):
        logger.debug(f"Executing command: {context['command'].name}")
        return context
    
    registry.add_middleware(logging_middleware)
    
    # Add performance monitoring hook
    async def performance_monitor_hook(command_metadata, result, execution_time):
        if execution_time > 5.0:  # Log slow commands
            logger.warning(f"Slow command execution: {command_metadata.name} took {execution_time:.2f}s")
    
    registry.add_hook('after_execute', performance_monitor_hook)
    
    return registry

# Command decorators for enhanced registration
def enhanced_command(
    name: Optional[str] = None,
    group: Optional[str] = None,
    help_text: Optional[str] = None,
    command_type: str = "enhanced",
    priority: CommandPriority = CommandPriority.USER,
    scope: CommandScope = CommandScope.GLOBAL,
    aliases: List[str] = None,
    tags: Set[str] = None,
    **metadata_kwargs
):
    """Enhanced decorator to mark a function as a command with full metadata"""
    def decorator(func):
        func._is_enhanced_command = True
        func._command_metadata = {
            'name': name or func.__name__,
            'group': group,
            'help_text': help_text,
            'command_type': command_type,
            'priority': priority,
            'scope': scope,
            'aliases': aliases or [],
            'tags': tags or set(),
            **metadata_kwargs
        }
        return func
    return decorator

def workflow_command(
    name: Optional[str] = None,
    phase: Optional[str] = None,
    priority: CommandPriority = CommandPriority.BUILTIN
):
    """Enhanced decorator for workflow-related commands"""
    tags = {'workflow'}
    if phase:
        tags.add(f'phase-{phase}')
    
    return enhanced_command(
        name=name,
        group="workflow",
        command_type="workflow",
        priority=priority,
        scope=CommandScope.WORKFLOW,
        tags=tags
    )

def agent_command(
    name: Optional[str] = None,
    agent_type: Optional[str] = None,
    priority: CommandPriority = CommandPriority.BUILTIN
):
    """Enhanced decorator for agent-related commands"""
    tags = {'agent'}
    if agent_type:
        tags.add(f'agent-{agent_type}')
    
    return enhanced_command(
        name=name,
        group="agents",
        command_type="agent",
        priority=priority,
        tags=tags
    )

def provider_command(
    name: Optional[str] = None,
    provider: Optional[str] = None,
    priority: CommandPriority = CommandPriority.BUILTIN
):
    """Enhanced decorator for provider-related commands"""
    tags = {'provider'}
    if provider:
        tags.add(f'provider-{provider}')
    
    return enhanced_command(
        name=name,
        group="providers",
        command_type="provider",
        priority=priority,
        tags=tags
    )

def debug_command(
    name: Optional[str] = None,
    priority: CommandPriority = CommandPriority.SYSTEM
):
    """Enhanced decorator for debug-only commands"""
    return enhanced_command(
        name=name,
        group="debug",
        command_type="debug",
        priority=priority,
        scope=CommandScope.DEBUG,
        tags={'debug', 'development'}
    )

# Example usage and demonstration
async def demo_enhanced_command_system():
    """Demonstrate enhanced command registration system"""
    
    console.print("[cyan]Enhanced Command Registration System Demo[/cyan]")
    
    # Create registry and builder
    registry = create_enhanced_registry()
    builder = EnhancedCommandBuilder(registry)
    
    # Register example commands with different priorities and features
    @enhanced_command(
        name="hello",
        group="demo",
        help_text="Say hello with enhanced features",
        priority=CommandPriority.USER,
        aliases=["hi", "greet"],
        tags={"greeting", "demo"},
        author="LocalAgent Team",
        version="1.1.0"
    )
    async def hello_command(name: str = "World"):
        console.print(f"Enhanced Hello, {name}!")
        return f"Hello, {name}!"
    
    @workflow_command(name="status", phase="all")
    async def workflow_status():
        console.print("Enhanced Workflow status: Active")
        return {"status": "active", "phase": "all"}
    
    @agent_command(name="list", agent_type="all")
    async def list_agents():
        console.print("Enhanced Available agents: 25")
        return {"agent_count": 25}
    
    @debug_command(name="inspect")
    async def inspect_system():
        console.print("System inspection complete")
        return {"system_health": "good"}
    
    # Register commands
    registry.register_command(
        "hello", hello_command, "demo", "Enhanced hello command",
        priority=CommandPriority.USER, aliases=["hi", "greet"],
        tags={"greeting", "demo"}
    )
    
    registry.register_command(
        "workflow-status", workflow_status, "workflow", "Get enhanced workflow status",
        priority=CommandPriority.BUILTIN, command_type="workflow"
    )
    
    registry.register_command(
        "list-agents", list_agents, "agents", "List enhanced agents",
        priority=CommandPriority.BUILTIN, command_type="agent"
    )
    
    registry.register_command(
        "inspect-system", inspect_system, "debug", "Inspect system internals",
        priority=CommandPriority.SYSTEM, scope=CommandScope.DEBUG
    )
    
    # Test command execution
    console.print("\n[yellow]Testing command execution:[/yellow]")
    result1 = await registry.execute_command("hello", "Enhanced World")
    result2 = await registry.execute_command("hi", "Alias Test")  # Using alias
    
    # Generate and display manifest
    manifest = registry.generate_command_manifest()
    console.print(f"\n[green]Registry Statistics:[/green]")
    console.print(f"Total Commands: {manifest['metadata']['total_commands']}")
    console.print(f"Total Groups: {manifest['metadata']['total_groups']}")
    console.print(f"Total Aliases: {manifest['metadata']['total_aliases']}")
    
    # Performance report
    perf_report = registry.get_performance_report()
    console.print(f"\n[blue]Performance Overview:[/blue]")
    console.print(f"Total Calls: {perf_report['overview']['total_calls']}")
    console.print(f"Total Execution Time: {perf_report['overview']['total_execution_time']:.3f}s")
    
    # Build Typer app
    app = builder.build_main_app_with_groups()
    
    return app, registry, manifest

if __name__ == "__main__":
    # Run demonstration
    asyncio.run(demo_enhanced_command_system())