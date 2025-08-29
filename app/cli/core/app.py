"""
LocalAgent CLI Application Foundation
Modern Typer-based CLI with Rich integration and plugin support
"""

import typer
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Annotated
from rich.console import Console
from rich.traceback import install as install_rich_traceback

from .config import ConfigurationManager, LocalAgentConfig
from .context import CLIContext
from ..plugins.framework import PluginManager
from ..ui.display import create_display_manager
from ..ui.ui_config_manager import get_ui_config_manager, initialize_ui_config_system
from ..error.recovery import ErrorRecoveryManager
from ..tools.commands import register_tools_commands
from ..commands import mangle as mangle_commands
from ..commands import agent_tools as agent_tools_commands

# Import new UI components
try:
    from ..ui import (
        PERFORMANCE_OPTIMIZATION_AVAILABLE,
        get_rendering_optimizer, create_optimized_console, optimized_rendering,
        get_animation_manager, create_typewriter_effect,
        WHIMSY_AVAILABLE
    )
    from ..ui.whimsy_animations import WhimsicalUIOrchestrator, WhimsyConfig
    ADVANCED_UI_AVAILABLE = True
except ImportError:
    ADVANCED_UI_AVAILABLE = False
    PERFORMANCE_OPTIMIZATION_AVAILABLE = False
    WHIMSY_AVAILABLE = False

# Import AI intelligence if available
try:
    from ..intelligence import (
        BehaviorTracker, IntelligentCommandProcessor,
        AdaptiveInterfaceManager, PersonalizationEngine
    )
    AI_INTELLIGENCE_AVAILABLE = True
except ImportError:
    AI_INTELLIGENCE_AVAILABLE = False

# Install rich traceback handling
install_rich_traceback()

console = Console()

class LocalAgentApp:
    """Main CLI application with modern architecture and enhanced UI/UX"""
    
    def __init__(self):
        self.app = typer.Typer(
            name="localagent",
            help="LocalAgent - Modern Multi-provider LLM Orchestration CLI with Enhanced UI/UX",
            no_args_is_help=True,
            rich_markup_mode="rich",
            context_settings={"help_option_names": ["-h", "--help"]}
        )
        
        # Core components
        self.config_manager: Optional[ConfigurationManager] = None
        self.config: Optional[LocalAgentConfig] = None
        self.context: Optional[CLIContext] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.display_manager = None
        self.error_recovery: Optional[ErrorRecoveryManager] = None
        self.initialized = False
        
        # Enhanced UI/UX components
        self.ui_config_manager = None
        self.whimsical_orchestrator = None
        self.performance_optimizer = None
        self.animation_manager = None
        self.behavior_tracker = None
        self.intelligent_processor = None
        self.adaptive_interface = None
        self.personalization_engine = None
        
        # Feature availability flags
        self.features = {
            'advanced_ui': ADVANCED_UI_AVAILABLE,
            'performance_optimization': PERFORMANCE_OPTIMIZATION_AVAILABLE,
            'whimsy_animations': WHIMSY_AVAILABLE,
            'ai_intelligence': AI_INTELLIGENCE_AVAILABLE
        }
        
        # Register core commands
        self._register_core_commands()
        
        # Register tools commands
        register_tools_commands(self.app)
        
        # Register Mangle analysis commands
        self.app.add_typer(mangle_commands.app, name="mangle", help="Google Mangle deductive analysis")
        
        # Register agent tools commands
        self.app.add_typer(agent_tools_commands.app, name="agent-tools", help="Agent tools and MCP services")
        
        # Register enhanced UI commands
        self._register_ui_commands()
    
    def _register_core_commands(self):
        """Register core CLI commands"""
        
        @self.app.command()
        def init(
            force: Annotated[bool, typer.Option("--force", "-f", help="Force reinitialize")] = False
        ):
            """Initialize LocalAgent configuration interactively"""
            asyncio.run(self._cmd_init(force))
        
        @self.app.command()
        def config(
            show: Annotated[bool, typer.Option("--show", help="Show current configuration")] = False,
            validate: Annotated[bool, typer.Option("--validate", help="Validate configuration")] = False,
            export: Annotated[Optional[str], typer.Option("--export", help="Export config to file")] = None
        ):
            """Manage LocalAgent configuration"""
            asyncio.run(self._cmd_config(show, validate, export))
        
        @self.app.command()
        def providers(
            list_all: Annotated[bool, typer.Option("--list", "-l", help="List all providers")] = False,
            health_check: Annotated[bool, typer.Option("--health", help="Check provider health")] = False,
            provider: Annotated[Optional[str], typer.Option("--provider", "-p", help="Specific provider")] = None
        ):
            """Manage LLM providers"""
            asyncio.run(self._cmd_providers(list_all, health_check, provider))
        
        @self.app.command()
        def workflow(
            prompt: Annotated[str, typer.Argument(help="Workflow prompt")],
            provider: Annotated[Optional[str], typer.Option("--provider", "-p", help="LLM provider to use")] = None,
            phases: Annotated[Optional[str], typer.Option("--phases", help="Specific phases to run (e.g., '1,2,3')")] = None,
            parallel: Annotated[bool, typer.Option("--parallel/--sequential", help="Run agents in parallel")] = True,
            max_agents: Annotated[int, typer.Option("--max-agents", help="Maximum parallel agents")] = 10,
            output_format: Annotated[str, typer.Option("--format", help="Output format")] = "rich",
            save_report: Annotated[Optional[str], typer.Option("--save", help="Save report to file")] = None
        ):
            """Execute 12-phase workflow"""
            asyncio.run(self._cmd_workflow(prompt, provider, phases, parallel, max_agents, output_format, save_report))
        
        @self.app.command()
        def chat(
            provider: Annotated[Optional[str], typer.Option("--provider", "-p", help="LLM provider to use")] = None,
            model: Annotated[Optional[str], typer.Option("--model", "-m", help="Specific model")] = None,
            session: Annotated[Optional[str], typer.Option("--session", help="Session name for history")] = None
        ):
            """Start interactive chat session"""
            asyncio.run(self._cmd_chat(provider, model, session))
        
        @self.app.command()
        def plugins(
            list_all: Annotated[bool, typer.Option("--list", "-l", help="List available plugins")] = False,
            enable: Annotated[Optional[str], typer.Option("--enable", help="Enable plugin")] = None,
            disable: Annotated[Optional[str], typer.Option("--disable", help="Disable plugin")] = None,
            info: Annotated[Optional[str], typer.Option("--info", help="Show plugin info")] = None
        ):
            """Manage CLI plugins"""
            asyncio.run(self._cmd_plugins(list_all, enable, disable, info))
        
        @self.app.command()
        def health():
            """System health check and diagnostics"""
            asyncio.run(self._cmd_health())
        
        @self.app.callback()
        def main_callback(
            config_path: Annotated[Optional[str], typer.Option("--config", help="Configuration file path")] = None,
            log_level: Annotated[str, typer.Option("--log-level", help="Log level")] = "INFO",
            no_plugins: Annotated[bool, typer.Option("--no-plugins", help="Disable plugin loading")] = False,
            debug: Annotated[bool, typer.Option("--debug", help="Enable debug mode")] = False
        ):
            """LocalAgent CLI callback for global options"""
            asyncio.run(self._initialize_app(config_path, log_level, no_plugins, debug))
    
    def _register_ui_commands(self):
        """Register enhanced UI/UX commands"""
        
        @self.app.command()
        def ui_status():
            """Show UI system status and available features"""
            asyncio.run(self._cmd_ui_status())
        
        @self.app.command()
        def ui_config(
            show: Annotated[bool, typer.Option("--show", help="Show current UI configuration")] = False,
            feature: Annotated[Optional[str], typer.Option("--feature", help="Configure specific feature")] = None,
            reset: Annotated[bool, typer.Option("--reset", help="Reset to default configuration")] = False
        ):
            """Manage UI configuration and features"""
            asyncio.run(self._cmd_ui_config(show, feature, reset))
        
        @self.app.command()
        def ui_performance():
            """Show UI performance metrics and optimization status"""
            asyncio.run(self._cmd_ui_performance())
        
        @self.app.command()
        def ui_demo(
            component: Annotated[Optional[str], typer.Option("--component", help="Demo specific component")] = None,
            interactive: Annotated[bool, typer.Option("--interactive", help="Interactive demo mode")] = False
        ):
            """Demonstrate UI features and animations"""
            asyncio.run(self._cmd_ui_demo(component, interactive))
        
        @self.app.command()
        def web_terminal(
            port: Annotated[int, typer.Option("--port", "-p", help="Web server port")] = 3000,
            host: Annotated[str, typer.Option("--host", help="Web server host")] = "localhost",
            auto_open: Annotated[bool, typer.Option("--open", help="Auto-open browser")] = True
        ):
            """Launch CLIX web terminal interface"""
            asyncio.run(self._cmd_web_terminal(port, host, auto_open))
    
    async def _initialize_app(self, config_path: Optional[str], log_level: str, no_plugins: bool, debug: bool):
        """Initialize the CLI application with enhanced UI/UX"""
        try:
            # Initialize UI configuration system first
            if ADVANCED_UI_AVAILABLE:
                self.ui_config_manager = await initialize_ui_config_system()
                await self._initialize_enhanced_ui_components(debug)
            
            # Initialize configuration manager
            self.config_manager = ConfigurationManager(config_path)
            self.config = await self.config_manager.load_configuration()
            
            # Initialize CLI context
            self.context = CLIContext(
                config=self.config,
                debug_mode=debug,
                log_level=log_level
            )
            
            # Initialize display manager (with enhanced features if available)
            if PERFORMANCE_OPTIMIZATION_AVAILABLE:
                optimized_console = create_optimized_console()
                self.display_manager = create_display_manager(optimized_console, debug)
            else:
                self.display_manager = create_display_manager(console, debug)
            
            # Initialize error recovery
            self.error_recovery = ErrorRecoveryManager(self.config)
            
            # Initialize plugin manager (unless disabled)
            if not no_plugins:
                self.plugin_manager = PluginManager(self.context)
                await self.plugin_manager.discover_plugins()
                await self.plugin_manager.load_enabled_plugins()
                
                # Register plugin commands
                for plugin_name, plugin in self.plugin_manager.loaded_plugins.items():
                    if hasattr(plugin, 'register_commands'):
                        plugin.register_commands(self.app)
            
            # Show startup animation if whimsy is available
            if self.whimsical_orchestrator:
                await self.whimsical_orchestrator.startup_sequence(
                    "LocalAgent Enhanced UI",
                    "Advanced features initialized"
                )
            
            self.initialized = True
            
        except Exception as e:
            console.print(f"[red]Failed to initialize LocalAgent: {e}[/red]")
            if debug:
                raise
            sys.exit(1)
    
    async def _initialize_enhanced_ui_components(self, debug_mode: bool):
        """Initialize enhanced UI/UX components"""
        try:
            # Initialize performance optimization
            if PERFORMANCE_OPTIMIZATION_AVAILABLE:
                self.performance_optimizer = get_rendering_optimizer()
                self.animation_manager = get_animation_manager()
                console.print("[green]✓[/green] Performance optimization enabled")
            
            # Initialize whimsical UI orchestrator
            if WHIMSY_AVAILABLE:
                whimsy_config = WhimsyConfig(
                    theme_primary="#58a6ff",
                    theme_success="#3fb950",
                    theme_warning="#d29922",
                    theme_error="#f85149",
                    animation_speed="medium",
                    particle_density="high" if not debug_mode else "low"
                )
                self.whimsical_orchestrator = WhimsicalUIOrchestrator(whimsy_config)
                console.print("[green]✓[/green] Whimsical animations enabled")
            
            # Initialize AI intelligence components
            if AI_INTELLIGENCE_AVAILABLE:
                self.behavior_tracker = BehaviorTracker()
                self.intelligent_processor = IntelligentCommandProcessor(
                    behavior_tracker=self.behavior_tracker,
                    model_manager=None  # Will be initialized with proper model manager
                )
                self.adaptive_interface = AdaptiveInterfaceManager(self.behavior_tracker)
                self.personalization_engine = PersonalizationEngine(self.behavior_tracker)
                console.print("[green]✓[/green] AI intelligence features enabled")
            
        except Exception as e:
            console.print(f"[yellow]Warning: Enhanced UI initialization failed: {e}[/yellow]")
            if debug_mode:
                raise
    
    # Command Implementations
    
    async def _cmd_init(self, force: bool):
        """Initialize LocalAgent configuration interactively"""
        from ..ui.prompts import ConfigurationWizard
        
        if not force and self.config and self.config.is_configured():
            console.print("[yellow]LocalAgent already configured. Use --force to reconfigure.[/yellow]")
            return
        
        wizard = ConfigurationWizard(console)
        config = await wizard.run_setup()
        
        if config:
            await self.config_manager.save_configuration(config)
            console.print("[green]✅ Configuration saved successfully![/green]")
        else:
            console.print("[red]Configuration setup cancelled.[/red]")
    
    async def _cmd_config(self, show: bool, validate: bool, export: Optional[str]):
        """Manage LocalAgent configuration"""
        if show:
            self.display_manager.display_config(self.config)
        
        if validate:
            validation_result = await self.config_manager.validate_configuration()
            self.display_manager.display_validation_results(validation_result)
        
        if export:
            await self.config_manager.export_configuration(Path(export))
            console.print(f"[green]Configuration exported to {export}[/green]")
    
    async def _cmd_providers(self, list_all: bool, health_check: bool, provider: Optional[str]):
        """Manage LLM providers"""
        # This would integrate with the existing provider system
        from ...orchestration.orchestration_integration import create_orchestrator
        
        orchestrator = await create_orchestrator(self.config.config_file)
        provider_manager = orchestrator.provider_manager
        
        if list_all or provider:
            providers_data = await provider_manager.get_provider_info(provider)
            self.display_manager.display_providers(providers_data)
        
        if health_check:
            health_data = await provider_manager.health_check_all()
            self.display_manager.display_provider_health(health_data)
    
    async def _cmd_workflow(
        self, 
        prompt: str, 
        provider: Optional[str], 
        phases: Optional[str], 
        parallel: bool, 
        max_agents: int, 
        output_format: str, 
        save_report: Optional[str]
    ):
        """Execute 12-phase workflow"""
        from ...orchestration.orchestration_integration import create_orchestrator
        
        try:
            # Create orchestrator
            orchestrator = await create_orchestrator(self.config.config_file)
            
            # Initialize with provider manager
            if not orchestrator.provider_manager:
                # This would be injected from the main provider system
                pass
            
            await orchestrator.initialize(orchestrator.provider_manager)
            
            # Configure execution parameters
            execution_context = {
                'provider_preference': provider,
                'parallel_execution': parallel,
                'max_agents': max_agents,
                'phases_filter': phases.split(',') if phases else None
            }
            
            # Execute workflow with rich progress display
            with self.display_manager.create_workflow_progress() as progress:
                result = await orchestrator.execute_12_phase_workflow(
                    prompt, 
                    execution_context
                )
            
            # Display results
            self.display_manager.display_workflow_results(result, output_format)
            
            # Save report if requested
            if save_report:
                await self._save_workflow_report(result, save_report)
                console.print(f"[green]Report saved to {save_report}[/green]")
            
        except Exception as e:
            await self.error_recovery.handle_workflow_error(e)
    
    async def _cmd_chat(self, provider: Optional[str], model: Optional[str], session: Optional[str]):
        """Start interactive chat session"""
        from ..ui.chat import InteractiveChatSession
        
        chat_session = InteractiveChatSession(
            config=self.config,
            provider=provider,
            model=model,
            session_name=session,
            display_manager=self.display_manager
        )
        
        await chat_session.start()
    
    async def _cmd_plugins(self, list_all: bool, enable: Optional[str], disable: Optional[str], info: Optional[str]):
        """Manage CLI plugins"""
        if not self.plugin_manager:
            console.print("[yellow]Plugin system disabled[/yellow]")
            return
        
        if list_all:
            plugins_info = await self.plugin_manager.get_plugins_info()
            self.display_manager.display_plugins(plugins_info)
        
        if enable:
            success = await self.plugin_manager.enable_plugin(enable)
            status = "enabled" if success else "failed to enable"
            console.print(f"Plugin '{enable}' {status}")
        
        if disable:
            success = await self.plugin_manager.disable_plugin(disable)
            status = "disabled" if success else "failed to disable"
            console.print(f"Plugin '{disable}' {status}")
        
        if info:
            plugin_info = await self.plugin_manager.get_plugin_info(info)
            self.display_manager.display_plugin_info(plugin_info)
    
    async def _cmd_health(self):
        """System health check and diagnostics"""
        health_data = {
            'cli_initialized': self.initialized,
            'config_valid': self.config and self.config.is_valid(),
            'plugins_loaded': len(self.plugin_manager.loaded_plugins) if self.plugin_manager else 0
        }
        
        # Add provider health if available
        if hasattr(self, 'orchestrator') and self.orchestrator:
            system_health = await self.orchestrator.get_system_health()
            health_data.update(system_health)
        
        self.display_manager.display_system_health(health_data)
    
    async def _save_workflow_report(self, result: Dict[str, Any], file_path: str):
        """Save workflow execution report"""
        from ..io.atomic import AtomicWriter
        import json
        
        async with AtomicWriter(Path(file_path)) as writer:
            if file_path.endswith('.json'):
                await writer.write_json(result)
            elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
                await writer.write_yaml(result)
            else:
                await writer.write_text(str(result))
    
    # Enhanced UI Command Implementations
    
    async def _cmd_ui_status(self):
        """Show UI system status and available features"""
        from rich.table import Table
        from rich.panel import Panel
        
        if not self.ui_config_manager:
            console.print("[yellow]UI configuration system not initialized[/yellow]")
            return
        
        # Feature status table
        status_table = Table(title="UI System Status", show_header=True, header_style="bold blue")
        status_table.add_column("Component", style="cyan", width=20)
        status_table.add_column("Status", style="white", width=12)
        status_table.add_column("Description", style="dim")
        
        feature_status = self.ui_config_manager.get_feature_status()
        
        for component, info in feature_status.items():
            status_icon = "✅ Available" if info['available'] and info['enabled'] else "❌ Disabled"
            if info['available'] and not info['enabled']:
                status_icon = "⏸️ Available"
            elif not info['available']:
                status_icon = "❌ Unavailable"
            
            description = f"{'Enabled' if info['enabled'] else 'Disabled'}"
            if 'quality' in info:
                description += f" ({info['quality']})"
            if 'profile' in info:
                description += f" ({info['profile']})"
            
            status_table.add_row(
                component.replace('_', ' ').title(),
                status_icon,
                description
            )
        
        # Performance status
        perf_status = self.ui_config_manager.get_performance_status()
        perf_panel = Panel(
            f"[bold]Performance Grade:[/bold] {perf_status['performance_grade'].title()}\n"
            f"[bold]Target FPS:[/bold] {perf_status['targets']['fps']} | [bold]Current:[/bold] {perf_status['current']['fps']:.1f}\n"
            f"[bold]Memory Target:[/bold] {perf_status['targets']['memory_mb']}MB | [bold]Current:[/bold] {perf_status['current']['memory_mb']:.1f}MB",
            title="Performance Status",
            border_style="green" if perf_status['performance_grade'] in ['excellent', 'good'] else "yellow"
        )
        
        console.print(Panel(status_table, title="🎨 LocalAgent Enhanced UI System"))
        console.print(perf_panel)
    
    async def _cmd_ui_config(self, show: bool, feature: Optional[str], reset: bool):
        """Manage UI configuration and features"""
        if not self.ui_config_manager:
            console.print("[red]UI configuration system not available[/red]")
            return
        
        if reset:
            # Reset to default configuration
            from ..ui.ui_config_manager import UnifiedUIConfig
            self.ui_config_manager.config = UnifiedUIConfig()
            await self.ui_config_manager.save_configuration()
            console.print("[green]UI configuration reset to defaults[/green]")
            return
        
        if show:
            # Show current configuration
            from rich.tree import Tree
            
            config_tree = Tree("🎨 UI Configuration")
            
            # Add whimsy animations
            whimsy_node = config_tree.add("🎭 Whimsical Animations")
            whimsy_config = self.ui_config_manager.config.whimsy_animations
            whimsy_node.add(f"Enabled: {whimsy_config.enabled}")
            whimsy_node.add(f"Quality: {whimsy_config.quality.value}")
            whimsy_node.add(f"Particle Effects: {whimsy_config.particle_effects}")
            
            console.print(config_tree)
            return
        
        # Show help
        console.print("[blue]Available UI configuration options:[/blue]")
        console.print("  --show: Show current configuration")
        console.print("  --feature <name>: Configure specific feature")
        console.print("  --reset: Reset to default configuration")
    
    async def _cmd_ui_performance(self):
        """Show UI performance metrics and optimization status"""
        if not self.performance_optimizer:
            console.print("[yellow]Performance optimization not available[/yellow]")
            return
        
        # Display performance dashboard
        if hasattr(self.performance_optimizer, 'display_performance_dashboard'):
            self.performance_optimizer.display_performance_dashboard()
        else:
            console.print("[blue]Performance monitoring active[/blue]")
    
    async def _cmd_ui_demo(self, component: Optional[str], interactive: bool):
        """Demonstrate UI features and animations"""
        if component == "whimsy" and self.whimsical_orchestrator:
            # Demo whimsical animations
            await self.whimsical_orchestrator.show_progress_magic("Demo Progress", 10)
            await self.whimsical_orchestrator.handle_success("Demo Success", "Whimsical animations working!")
        else:
            # General demo
            console.print("[blue]🎨 LocalAgent Enhanced UI Demo[/blue]")
            
            if self.whimsical_orchestrator:
                await self.whimsical_orchestrator.startup_sequence("Demo Mode", "All systems operational")
            
            # Show feature availability
            await self._cmd_ui_status()
    
    async def _cmd_web_terminal(self, port: int, host: str, auto_open: bool):
        """Launch CLIX web terminal interface"""
        console.print(f"[blue]Starting CLIX web terminal on {host}:{port}[/blue]")
        console.print("[yellow]Web terminal integration in progress...[/yellow]")

def create_app() -> typer.Typer:
    """Create and configure the main CLI application"""
    app = LocalAgentApp()
    return app.app

def main():
    """Entry point for the CLI application"""
    app = create_app()
    app()

if __name__ == "__main__":
    main()