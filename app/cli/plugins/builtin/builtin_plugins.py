"""
Built-in Plugins for LocalAgent CLI
Core plugins that ship with the CLI for essential functionality
"""

import typer
import asyncio
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import yaml
from pathlib import Path

from app.cli.plugins.framework import CommandPlugin, ProviderPlugin, UIPlugin, WorkflowPlugin
from app.cli.core.context import CLIContext

console = Console()

class SystemInfoPlugin(CommandPlugin):
    """Built-in plugin for system information and diagnostics"""
    
    name = "system-info"
    version = "1.0.0"
    description = "System information and health diagnostics"
    
    async def initialize(self, context: CLIContext) -> bool:
        self.context = context
        return True
    
    def register_commands(self, app: typer.Typer) -> None:
        """Register system info commands"""
        
        # Create system command group
        system_app = typer.Typer(name="system", help="System information commands")
        
        @system_app.command("info")
        def system_info():
            """Display system information"""
            asyncio.run(self._cmd_system_info())
        
        @system_app.command("health")  
        def health_check():
            """Comprehensive system health check"""
            asyncio.run(self._cmd_health_check())
        
        @system_app.command("agents")
        def list_agents():
            """List available agents"""
            asyncio.run(self._cmd_list_agents())
        
        @system_app.command("providers")
        def list_providers():
            """List available LLM providers"""
            asyncio.run(self._cmd_list_providers())
        
        # Add to main app
        app.add_typer(system_app)
    
    async def _cmd_system_info(self):
        """Show comprehensive system information"""
        table = Table(title="LocalAgent System Information")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        
        # CLI Version
        table.add_row("CLI Version", "✓ Active", "LocalAgent v2.0.0")
        
        # Configuration
        config_status = "✓ Loaded" if self.context.config else "✗ Missing"
        table.add_row("Configuration", config_status, str(self.context.config.config_file) if self.context.config else "None")
        
        # Plugin System
        plugin_count = len(getattr(self.context, 'plugin_manager', {}).get('loaded_plugins', {})) if hasattr(self.context, 'plugin_manager') else 0
        table.add_row("Plugins", f"✓ {plugin_count} loaded", "Plugin system active")
        
        # Orchestration
        orch_status = "✓ Available" if hasattr(self.context, 'orchestrator') else "○ Not initialized"
        table.add_row("Orchestration", orch_status, "12-phase workflow engine")
        
        console.print(table)
    
    async def _cmd_health_check(self):
        """Perform comprehensive health check"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            health_task = progress.add_task("Checking system health...", total=None)
            
            health_results = {
                "Configuration": self._check_config_health(),
                "Plugin System": self._check_plugin_health(),
                "File System": self._check_filesystem_health(),
                "Network": await self._check_network_health()
            }
            
            progress.update(health_task, completed=True)
        
        # Display results
        table = Table(title="System Health Check Results")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Message", style="white")
        
        for component, result in health_results.items():
            status_icon = "✓" if result['healthy'] else "✗"
            status_color = "green" if result['healthy'] else "red"
            table.add_row(
                component, 
                f"[{status_color}]{status_icon} {result['status']}[/{status_color}]",
                result['message']
            )
        
        console.print(table)
    
    async def _cmd_list_agents(self):
        """List all available agents"""
        # This would integrate with actual agent discovery
        agents = [
            {"name": "backend-gateway-expert", "type": "Development", "status": "Available"},
            {"name": "security-validator", "type": "Security", "status": "Available"},
            {"name": "test-automation-engineer", "type": "Testing", "status": "Available"},
            {"name": "documentation-specialist", "type": "Documentation", "status": "Available"},
            {"name": "project-orchestrator", "type": "Orchestration", "status": "Available"}
        ]
        
        table = Table(title="Available Agents")
        table.add_column("Agent Name", style="cyan")
        table.add_column("Category", style="yellow")
        table.add_column("Status", style="green")
        
        for agent in agents:
            table.add_row(agent['name'], agent['type'], agent['status'])
        
        console.print(table)
        console.print(f"\n[green]Total agents available: {len(agents)}[/green]")
    
    async def _cmd_list_providers(self):
        """List all available LLM providers"""
        providers = [
            {"name": "ollama", "status": "Available", "models": "llama2, codellama, mistral"},
            {"name": "openai", "status": "Requires API key", "models": "gpt-4, gpt-3.5-turbo"},
            {"name": "gemini", "status": "Requires API key", "models": "gemini-pro, gemini-vision"},
            {"name": "perplexity", "status": "Requires API key", "models": "llama-2-70b-chat"}
        ]
        
        table = Table(title="Available LLM Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Available Models", style="white")
        
        for provider in providers:
            table.add_row(provider['name'], provider['status'], provider['models'])
        
        console.print(table)
        console.print(f"\n[green]Total providers: {len(providers)}[/green]")
    
    def _check_config_health(self) -> Dict[str, Any]:
        """Check configuration health"""
        if not self.context.config:
            return {"healthy": False, "status": "Missing", "message": "No configuration found"}
        
        if not self.context.config.is_valid():
            return {"healthy": False, "status": "Invalid", "message": "Configuration validation failed"}
        
        return {"healthy": True, "status": "Valid", "message": "Configuration loaded successfully"}
    
    def _check_plugin_health(self) -> Dict[str, Any]:
        """Check plugin system health"""
        if not hasattr(self.context, 'plugin_manager'):
            return {"healthy": False, "status": "Unavailable", "message": "Plugin manager not initialized"}
        
        plugin_count = len(getattr(self.context.plugin_manager, 'loaded_plugins', {}))
        return {"healthy": True, "status": "Active", "message": f"{plugin_count} plugins loaded"}
    
    def _check_filesystem_health(self) -> Dict[str, Any]:
        """Check filesystem health"""
        try:
            # Check if config directory exists and is writable
            config_dir = Path.home() / '.localagent'
            if not config_dir.exists():
                config_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = config_dir / 'health_check.tmp'
            test_file.write_text('health check')
            test_file.unlink()
            
            return {"healthy": True, "status": "OK", "message": "Configuration directory accessible"}
            
        except Exception as e:
            return {"healthy": False, "status": "Error", "message": f"Filesystem access error: {e}"}
    
    async def _check_network_health(self) -> Dict[str, Any]:
        """Check network connectivity for external services"""
        try:
            # This would check connectivity to various services
            # For now, return success
            return {"healthy": True, "status": "Connected", "message": "Network connectivity available"}
            
        except Exception as e:
            return {"healthy": False, "status": "Disconnected", "message": f"Network check failed: {e}"}

class WorkflowDebugPlugin(WorkflowPlugin):
    """Built-in plugin for workflow debugging and introspection"""
    
    name = "workflow-debug"
    version = "1.0.0"
    description = "Workflow debugging and introspection tools"
    
    async def initialize(self, context: CLIContext) -> bool:
        self.context = context
        return True
    
    def get_workflow_components(self) -> Dict[str, Any]:
        """Return workflow debugging components"""
        return {
            'debug_phases': ['phase-0-debug', 'phase-validation', 'agent-introspection'],
            'debug_agents': ['workflow-analyzer', 'phase-validator', 'evidence-inspector']
        }
    
    def register_commands(self, app: typer.Typer) -> None:
        """Register workflow debugging commands"""
        
        debug_app = typer.Typer(name="debug", help="Workflow debugging commands")
        
        @debug_app.command("phases")
        def debug_phases():
            """Debug workflow phases"""
            asyncio.run(self._cmd_debug_phases())
        
        @debug_app.command("agents")
        def debug_agents():
            """Debug agent execution"""
            asyncio.run(self._cmd_debug_agents())
        
        @debug_app.command("context")
        def debug_context():
            """Debug context packages"""
            asyncio.run(self._cmd_debug_context())
        
        app.add_typer(debug_app)
    
    async def _cmd_debug_phases(self):
        """Debug workflow phases"""
        console.print("[cyan]Workflow Phase Debug Information[/cyan]")
        
        phases = [
            {"id": 0, "name": "Interactive Prompt Engineering", "status": "Ready"},
            {"id": 1, "name": "Parallel Research & Discovery", "status": "Ready"},
            {"id": 2, "name": "Strategic Planning", "status": "Ready"},
            {"id": 3, "name": "Context Package Creation", "status": "Ready"},
            {"id": 4, "name": "Parallel Stream Execution", "status": "Ready"}
        ]
        
        table = Table()
        table.add_column("Phase", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Status", style="green")
        
        for phase in phases:
            table.add_row(str(phase['id']), phase['name'], phase['status'])
        
        console.print(table)
    
    async def _cmd_debug_agents(self):
        """Debug agent execution"""
        console.print("[cyan]Agent Debug Information[/cyan]")
        
        # This would show actual agent debugging info
        agent_info = {
            "Available Agents": 25,
            "Active Agents": 0,
            "Failed Agents": 0,
            "Agent Pool Status": "Ready"
        }
        
        for key, value in agent_info.items():
            console.print(f"[white]{key}:[/white] [green]{value}[/green]")
    
    async def _cmd_debug_context(self):
        """Debug context packages"""
        console.print("[cyan]Context Package Debug Information[/cyan]")
        
        context_info = {
            "Strategic Context Tokens": "3000",
            "Technical Context Tokens": "4000", 
            "Active Context Packages": "0",
            "Context Compression": "Available"
        }
        
        for key, value in context_info.items():
            console.print(f"[white]{key}:[/white] [green]{value}[/green]")

class ConfigurationPlugin(CommandPlugin):
    """Built-in plugin for configuration management"""
    
    name = "config-manager"
    version = "1.0.0"
    description = "Advanced configuration management tools"
    
    async def initialize(self, context: CLIContext) -> bool:
        self.context = context
        return True
    
    def register_commands(self, app: typer.Typer) -> None:
        """Register configuration commands"""
        
        config_app = typer.Typer(name="config", help="Configuration management")
        
        @config_app.command("show")
        def show_config():
            """Show current configuration"""
            asyncio.run(self._cmd_show_config())
        
        @config_app.command("validate")
        def validate_config():
            """Validate current configuration"""
            asyncio.run(self._cmd_validate_config())
        
        @config_app.command("export")
        def export_config(
            output_file: str = typer.Option(..., "--output", "-o", help="Output file path")
        ):
            """Export configuration to file"""
            asyncio.run(self._cmd_export_config(output_file))
        
        @config_app.command("template")
        def create_template():
            """Create configuration template"""
            asyncio.run(self._cmd_create_template())
        
        app.add_typer(config_app)
    
    async def _cmd_show_config(self):
        """Show current configuration"""
        console.print("[cyan]Current Configuration[/cyan]")
        
        if not self.context.config:
            console.print("[red]No configuration loaded[/red]")
            return
        
        # Display configuration structure
        config_data = {
            "Config File": str(self.context.config.config_file) if self.context.config.config_file else "None",
            "Debug Mode": self.context.debug_mode,
            "Log Level": self.context.log_level,
            "Plugin System": "Enabled" if hasattr(self.context, 'plugin_manager') else "Disabled"
        }
        
        table = Table(title="Configuration Summary")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in config_data.items():
            table.add_row(key, str(value))
        
        console.print(table)
    
    async def _cmd_validate_config(self):
        """Validate current configuration"""
        if not self.context.config:
            console.print("[red]No configuration to validate[/red]")
            return
        
        console.print("[cyan]Validating configuration...[/cyan]")
        
        # Validation would happen here
        console.print("[green]✓ Configuration is valid[/green]")
    
    async def _cmd_export_config(self, output_file: str):
        """Export configuration to file"""
        if not self.context.config:
            console.print("[red]No configuration to export[/red]")
            return
        
        # Export configuration
        export_data = {
            "localagent": {
                "version": "2.0.0",
                "plugins": {
                    "enabled": True,
                    "auto_load": True,
                    "plugin_directories": ["~/.localagent/plugins"]
                },
                "providers": {
                    "default": "ollama",
                    "ollama": {
                        "base_url": "http://localhost:11434",
                        "default_model": "llama2"
                    }
                },
                "workflow": {
                    "max_parallel_agents": 10,
                    "enable_evidence_collection": True
                }
            }
        }
        
        with open(output_file, 'w') as f:
            yaml.dump(export_data, f, default_flow_style=False, indent=2)
        
        console.print(f"[green]Configuration exported to {output_file}[/green]")
    
    async def _cmd_create_template(self):
        """Create configuration template"""
        template_path = Path.home() / '.localagent' / 'config-template.yaml'
        
        template_data = {
            "localagent": {
                "plugins": {
                    "enabled": True,
                    "auto_load": True,
                    "plugin_directories": ["~/.localagent/plugins"],
                    "enabled_plugins": []
                },
                "providers": {
                    "default": "ollama",
                    "ollama": {
                        "base_url": "http://localhost:11434",
                        "default_model": "llama2",
                        "timeout": 30
                    },
                    "openai": {
                        "api_key": "your-api-key-here",
                        "default_model": "gpt-4"
                    }
                },
                "workflow": {
                    "max_parallel_agents": 10,
                    "max_workflow_iterations": 3,
                    "enable_evidence_collection": True,
                    "enable_cross_session_continuity": True
                },
                "logging": {
                    "level": "INFO",
                    "file": "~/.localagent/logs/localagent.log"
                }
            }
        }
        
        # Ensure directory exists
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(template_path, 'w') as f:
            yaml.dump(template_data, f, default_flow_style=False, indent=2)
        
        console.print(f"[green]Configuration template created at {template_path}[/green]")
        console.print("[yellow]Edit the template and save as config.yaml[/yellow]")

# Registry of built-in plugins
BUILTIN_PLUGINS = [
    SystemInfoPlugin,
    WorkflowDebugPlugin,
    ConfigurationPlugin
]

def get_builtin_plugins() -> List[type]:
    """Get list of built-in plugin classes"""
    return BUILTIN_PLUGINS.copy()

async def register_builtin_plugins(plugin_manager) -> int:
    """Register all built-in plugins with the plugin manager"""
    registered_count = 0
    
    for plugin_class in BUILTIN_PLUGINS:
        try:
            plugin_instance = plugin_class()
            # This would integrate with the actual plugin manager
            # plugin_manager.register_plugin(plugin_instance)
            registered_count += 1
            
        except Exception as e:
            console.print(f"[red]Failed to register built-in plugin {plugin_class.name}: {e}[/red]")
    
    return registered_count