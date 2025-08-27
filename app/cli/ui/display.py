"""
Display Management for LocalAgent CLI
Rich-based formatting and progress displays
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, ContextManager, Callable
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, 
    TaskProgressColumn, TimeRemainingColumn, MofNCompleteColumn
)
from rich.syntax import Syntax
from rich.tree import Tree
from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.columns import Columns
from rich.json import JSON
from rich.markdown import Markdown
from rich.text import Text
from rich.box import ROUNDED, DOUBLE
from contextlib import contextmanager

# Import whimsical UI components (graceful fallback if not available)
try:
    from .whimsy_animations import (
        WhimsicalUIOrchestrator, WhimsyConfig, AnimationSpeed,
        AdvancedProgressSystem, ParticleEffectPresets,
        AnimatedCelebration, AdvancedNotificationSystem,
        NotificationType, ASCIIArtGenerator, BannerStyle,
        WHIMSY_AVAILABLE
    )
except ImportError:
    # Graceful fallback - whimsical UI components not available
    WHIMSY_AVAILABLE = False
    class MockWhimsySystem:
        def __init__(self, *args, **kwargs):
            pass
        async def startup_sequence(self, *args, **kwargs):
            pass
        async def handle_success(self, *args, **kwargs):
            pass
        async def show_progress_magic(self, *args, **kwargs):
            return lambda *a, **k: None
    
    WhimsicalUIOrchestrator = MockWhimsySystem
    WhimsyConfig = dict
    AnimationSpeed = type('AnimationSpeed', (), {'NORMAL': 0.1})

# Enhanced theme integration
try:
    from .themes import (
        get_console, get_theme_manager, format_provider, format_status, 
        format_phase, CLAUDE_COLORS, STATUS_ICONS
    )
    THEMES_AVAILABLE = True
except ImportError:
    def get_console():
        return Console()
    def get_theme_manager():
        return None
    def format_provider(name, enabled=True):
        return f"{'✓' if enabled else '✗'} {name}"
    def format_status(status, message):
        return f"• {message}"
    def format_phase(phase_num, name, status='pending'):
        return f"Phase {phase_num}: {name}"
    CLAUDE_COLORS = {}
    STATUS_ICONS = {}
    THEMES_AVAILABLE = False

from ..core.config import LocalAgentConfig

# Import rendering optimization system
try:
    from .rendering_system import get_rendering_system, optimized_rendering
    RENDERING_OPTIMIZATION_AVAILABLE = True
except ImportError:
    RENDERING_OPTIMIZATION_AVAILABLE = False
    def optimized_rendering():
        from contextlib import nullcontext
        return nullcontext()


class DisplayManager:
    """
    Centralized display management with Rich integration
    Handles all CLI output formatting and progress displays
    Enhanced with whimsical UI capabilities when available
    """
    
    def __init__(self, console: Optional[Console] = None, debug_mode: bool = False, 
                 enable_whimsy: bool = False, magic_level: int = 5):
        # Use optimized console if available
        if RENDERING_OPTIMIZATION_AVAILABLE and console is None:
            self.console = get_rendering_system().create_optimized_console()
        else:
            self.console = console or get_console()
        
        self.debug_mode = debug_mode
        self.current_progress: Optional[Progress] = None
        self.theme_manager = get_theme_manager() if THEMES_AVAILABLE else None
        
        # Whimsical UI integration
        self.enable_whimsy = enable_whimsy and WHIMSY_AVAILABLE
        self.magic_level = magic_level
        
        if self.enable_whimsy:
            whimsy_config = WhimsyConfig(
                magic_level=magic_level,
                enable_sparkles=True,
                enable_rainbow_effects=magic_level > 7,
                personality_quips=True,
                animation_speed=AnimationSpeed.NORMAL if hasattr(AnimationSpeed, 'NORMAL') else 0.1
            )
            self.whimsy_ui = WhimsicalUIOrchestrator(self.console, whimsy_config)
        else:
            self.whimsy_ui = None
        
        # Rendering system integration
        self.rendering_system = get_rendering_system() if RENDERING_OPTIMIZATION_AVAILABLE else None
        
    def print(self, content: Any, style: Optional[str] = None) -> None:
        """Print content with optional styling and optimization"""
        if RENDERING_OPTIMIZATION_AVAILABLE:
            # Use optimized rendering
            if hasattr(content, '__rich__') or hasattr(content, '__rich_console__'):
                self.rendering_system.render_content(content, self.console)
            else:
                # Convert to optimized text
                optimized_content = self.rendering_system.optimize_text_content(str(content), style or "")
                self.rendering_system.render_content(optimized_content, self.console)
        else:
            self.console.print(content, style=style)
    
    def print_error(self, message: str) -> None:
        """Print error message with consistent formatting"""
        self.console.print(f"[bold red]✗ Error:[/bold red] {message}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message with consistent formatting"""
        self.console.print(f"[bold yellow]⚠ Warning:[/bold yellow] {message}")
    
    def print_success(self, message: str, celebrate: bool = False) -> None:
        """Print success message with consistent formatting and optional celebration"""
        if self.enable_whimsy and celebrate:
            # Use whimsical success with celebration
            try:
                asyncio.run(self.whimsy_ui.handle_success(message, True))
            except Exception:
                # Fallback to normal success if whimsy fails
                self.console.print(f"[bold green]✓ Success:[/bold green] {message}")
        elif self.enable_whimsy:
            # Simple whimsical success without full celebration
            sparkle = "✨ " if self.magic_level > 5 else ""
            self.console.print(f"[bold green]{sparkle}✓ Success:[/bold green] {message}")
        else:
            self.console.print(f"[bold green]✓ Success:[/bold green] {message}")
    
    def print_info(self, message: str) -> None:
        """Print info message with consistent formatting"""
        self.console.print(f"[bold blue]ℹ Info:[/bold blue] {message}")
    
    def print_debug(self, message: str) -> None:
        """Print debug message if debug mode is enabled"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.console.print(f"[dim][{timestamp}] DEBUG: {message}[/dim]")
    
    def display_config(self, config: LocalAgentConfig) -> None:
        """Display LocalAgent configuration in formatted table"""
        table = Table(title="LocalAgent Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Value", style="white")
        
        # Basic settings
        table.add_row("Config Directory", str(config.config_dir))
        table.add_row("Log Level", config.log_level)
        table.add_row("Debug Mode", "✓" if config.debug_mode else "✗")
        table.add_row("Default Provider", config.default_provider)
        
        # Providers
        enabled_providers = ", ".join(config.get_enabled_providers())
        table.add_row("Enabled Providers", enabled_providers)
        
        # Orchestration settings
        table.add_row("Max Parallel Agents", str(config.orchestration.max_parallel_agents))
        table.add_row("Max Workflow Iterations", str(config.orchestration.max_workflow_iterations))
        table.add_row("Evidence Collection", "✓" if config.orchestration.enable_evidence_collection else "✗")
        
        # MCP settings
        table.add_row("Redis URL", config.mcp.redis_url)
        table.add_row("Memory Retention (days)", str(config.mcp.memory_retention_days))
        
        # Plugin settings
        enabled_plugins = ", ".join(config.plugins.enabled_plugins) if config.plugins.enabled_plugins else "None"
        table.add_row("Enabled Plugins", enabled_plugins)
        
        self.console.print(table)
    
    def display_validation_results(self, validation_result: Dict[str, Any]) -> None:
        """Display configuration validation results"""
        if validation_result['valid']:
            self.print_success("Configuration validation passed")
        else:
            self.print_error("Configuration validation failed")
        
        # Show errors
        if validation_result['errors']:
            error_table = Table(title="Validation Errors", show_header=False, 
                               box=None, padding=(0, 1))
            error_table.add_column("Error", style="red")
            for error in validation_result['errors']:
                error_table.add_row(f"• {error}")
            self.console.print(error_table)
        
        # Show warnings
        if validation_result['warnings']:
            warning_table = Table(title="Validation Warnings", show_header=False, 
                                 box=None, padding=(0, 1))
            warning_table.add_column("Warning", style="yellow")
            for warning in validation_result['warnings']:
                warning_table.add_row(f"• {warning}")
            self.console.print(warning_table)
        
        # Show provider status
        if validation_result.get('provider_status'):
            provider_table = Table(title="Provider Status", show_header=True, header_style="bold magenta")
            provider_table.add_column("Provider", style="cyan")
            provider_table.add_column("Status", style="white")
            provider_table.add_column("API Key", style="white")
            provider_table.add_column("Issues", style="red")
            
            for provider_name, status in validation_result['provider_status'].items():
                status_text = "✓ Valid" if status['valid'] else "✗ Invalid"
                api_key_status = "✓" if status.get('has_api_key') else ("Required" if status.get('requires_api_key') else "N/A")
                issues = ", ".join(status.get('errors', []))
                
                provider_table.add_row(provider_name, status_text, api_key_status, issues)
            
            self.console.print(provider_table)
    
    def display_providers(self, providers_data: Dict[str, Any]) -> None:
        """Display available providers information"""
        table = Table(title="LLM Providers", show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="cyan", width=15)
        table.add_column("Status", style="white", width=12)
        table.add_column("Base URL", style="blue", width=30)
        table.add_column("Default Model", style="green", width=20)
        table.add_column("Rate Limit", style="yellow", width=12)
        
        for name, data in providers_data.items():
            status = "✓ Enabled" if data.get('enabled', False) else "✗ Disabled"
            base_url = data.get('base_url', 'Default') 
            model = data.get('default_model', 'Auto')
            rate_limit = str(data.get('rate_limit', 'None'))
            
            table.add_row(name, status, base_url, model, rate_limit)
        
        self.console.print(table)
    
    def display_provider_health(self, health_data: Dict[str, Any]) -> None:
        """Display provider health check results"""
        table = Table(title="Provider Health Status", show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="cyan")
        table.add_column("Health", style="white")
        table.add_column("Response Time", style="blue")
        table.add_column("Last Check", style="dim")
        table.add_column("Issues", style="red")
        
        for provider_name, health in health_data.items():
            health_status = "🟢 Healthy" if health.get('healthy', False) else "🔴 Unhealthy"
            response_time = f"{health.get('response_time', 0):.2f}ms"
            last_check = health.get('last_check', 'Never')
            issues = ", ".join(health.get('issues', []))
            
            table.add_row(provider_name, health_status, response_time, last_check, issues)
        
        self.console.print(table)
    
    def display_workflow_results(self, result: Dict[str, Any], output_format: str = "rich") -> None:
        """Display workflow execution results"""
        if output_format == "json":
            self.console.print(JSON.from_data(result))
            return
        
        # Rich formatted output
        layout = Layout()
        
        # Summary panel
        summary_data = result.get('summary', {})
        summary_text = f"""
[bold]Workflow Execution Summary[/bold]

[green]✓ Phases Completed:[/green] {summary_data.get('phases_completed', 0)}/12
[blue]📊 Total Agents:[/blue] {summary_data.get('total_agents', 0)}
[yellow]⏱️ Duration:[/yellow] {summary_data.get('duration', 0):.2f}s
[cyan]🎯 Success Rate:[/cyan] {summary_data.get('success_rate', 0):.1f}%
        """
        
        summary_panel = Panel(summary_text, title="Summary", border_style="green")
        
        # Results panel
        if result.get('phases'):
            phases_table = Table(show_header=True, header_style="bold blue")
            phases_table.add_column("Phase", style="cyan", width=20)
            phases_table.add_column("Status", style="white", width=12)
            phases_table.add_column("Duration", style="yellow", width=10)
            phases_table.add_column("Agents", style="green", width=8)
            phases_table.add_column("Results", style="blue")
            
            for phase_name, phase_data in result['phases'].items():
                status = "✓ Success" if phase_data.get('success', False) else "✗ Failed"
                duration = f"{phase_data.get('duration', 0):.1f}s"
                agent_count = str(len(phase_data.get('agents', [])))
                results_summary = phase_data.get('summary', 'No summary')
                
                phases_table.add_row(phase_name, status, duration, agent_count, results_summary)
            
            results_panel = Panel(phases_table, title="Phase Results", border_style="blue")
        else:
            results_panel = Panel("[yellow]No phase results available[/yellow]", 
                                 title="Phase Results", border_style="yellow")
        
        # Layout arrangement
        layout.split_column(
            Layout(summary_panel, size=8),
            Layout(results_panel)
        )
        
        self.console.print(layout)
        
        # Display any errors
        if result.get('errors'):
            error_panel = Panel(
                "\n".join([f"• {error}" for error in result['errors']]),
                title="Errors",
                border_style="red"
            )
            self.console.print(error_panel)
    
    def display_plugins(self, plugins_info: Dict[str, Any]) -> None:
        """Display available plugins information"""
        table = Table(title="Available Plugins", show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Version", style="blue", width=10)
        table.add_column("Status", style="white", width=12)
        table.add_column("Type", style="green", width=15)
        table.add_column("Description", style="white")
        
        for plugin_name, plugin_data in plugins_info.items():
            status_text = []
            if plugin_data.get('enabled'):
                status_text.append("✓ Enabled")
            if plugin_data.get('loaded'):
                status_text.append("⚡ Loaded")
            if not status_text:
                status_text.append("✗ Disabled")
            
            status = ", ".join(status_text)
            
            # Determine plugin type from entry point or class name
            plugin_type = "Unknown"
            if plugin_data.get('entry_point'):
                if 'commands' in plugin_data['entry_point']:
                    plugin_type = "Command"
                elif 'providers' in plugin_data['entry_point']:
                    plugin_type = "Provider"
                elif 'ui' in plugin_data['entry_point']:
                    plugin_type = "UI"
                elif 'workflow' in plugin_data['entry_point']:
                    plugin_type = "Workflow"
            
            table.add_row(
                plugin_name,
                plugin_data.get('version', 'Unknown'),
                status,
                plugin_type,
                plugin_data.get('description', 'No description')
            )
        
        self.console.print(table)
    
    def display_plugin_info(self, plugin_info: Optional[Dict[str, Any]]) -> None:
        """Display detailed plugin information"""
        if not plugin_info:
            self.print_error("Plugin not found")
            return
        
        # Main info panel
        info_text = f"""
[bold]Name:[/bold] {plugin_info['name']}
[bold]Version:[/bold] {plugin_info['version']}
[bold]Description:[/bold] {plugin_info['description']}
[bold]Enabled:[/bold] {'✓' if plugin_info['enabled'] else '✗'}
[bold]Loaded:[/bold] {'✓' if plugin_info['loaded'] else '✗'}
[bold]Entry Point:[/bold] {plugin_info.get('entry_point', 'File-based')}
[bold]File Path:[/bold] {plugin_info.get('file_path', 'N/A')}
        """
        
        if plugin_info.get('dependencies'):
            deps = ", ".join(plugin_info['dependencies'])
            info_text += f"\n[bold]Dependencies:[/bold] {deps}"
        
        info_panel = Panel(info_text, title=f"Plugin: {plugin_info['name']}", border_style="cyan")
        self.console.print(info_panel)
        
        # Config schema if available
        if plugin_info.get('config_schema'):
            schema_json = JSON.from_data(plugin_info['config_schema'])
            schema_panel = Panel(schema_json, title="Configuration Schema", border_style="blue")
            self.console.print(schema_panel)
    
    def display_system_health(self, health_data: Dict[str, Any]) -> None:
        """Display system health information"""
        # Overall status
        overall_healthy = all([
            health_data.get('cli_initialized', False),
            health_data.get('config_valid', False)
        ])
        
        status_text = "🟢 Healthy" if overall_healthy else "🔴 Issues Detected"
        
        health_table = Table(title=f"System Health - {status_text}", 
                           show_header=True, header_style="bold magenta")
        health_table.add_column("Component", style="cyan", width=25)
        health_table.add_column("Status", style="white", width=15)
        health_table.add_column("Details", style="blue")
        
        # CLI Status
        cli_status = "✓ Initialized" if health_data.get('cli_initialized') else "✗ Not Initialized"
        health_table.add_row("CLI Framework", cli_status, "Core CLI components")
        
        # Configuration Status
        config_status = "✓ Valid" if health_data.get('config_valid') else "✗ Invalid"
        health_table.add_row("Configuration", config_status, "LocalAgent configuration")
        
        # Plugin Status
        plugins_loaded = health_data.get('plugins_loaded', 0)
        plugin_status = f"✓ {plugins_loaded} loaded" if plugins_loaded > 0 else "⚠ None loaded"
        health_table.add_row("Plugins", plugin_status, f"{plugins_loaded} plugins active")
        
        # Provider Health (if available)
        if health_data.get('providers'):
            healthy_providers = sum(1 for p in health_data['providers'].values() if p.get('healthy'))
            total_providers = len(health_data['providers'])
            provider_status = f"✓ {healthy_providers}/{total_providers} healthy"
            health_table.add_row("Providers", provider_status, "LLM provider connections")
        
        # Orchestration System (if available)
        if 'orchestration_healthy' in health_data:
            orch_status = "✓ Running" if health_data['orchestration_healthy'] else "✗ Issues"
            health_table.add_row("Orchestration", orch_status, "Workflow orchestration system")
        
        # MCP Integration (if available)
        if 'mcp_connected' in health_data:
            mcp_status = "✓ Connected" if health_data['mcp_connected'] else "✗ Disconnected"
            health_table.add_row("MCP Integration", mcp_status, "Memory/Context/Protocol services")
        
        self.console.print(health_table)
    
    @contextmanager
    def create_workflow_progress(self) -> ContextManager[Progress]:
        """Create a progress display for workflow execution"""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        
        try:
            with progress:
                self.current_progress = progress
                yield progress
        finally:
            self.current_progress = None
    
    def create_simple_progress(self, description: str = "Working...", style: str = "default") -> Progress:
        """Create a simple spinner progress for operations with theming"""
        spinner_style = "secondary" if THEMES_AVAILABLE else "cyan"
        text_style = "text.primary" if THEMES_AVAILABLE else "white"
        
        return Progress(
            SpinnerColumn(spinner_style=spinner_style),
            TextColumn(f"[{text_style}]{description}[/{text_style}]"),
            console=self.console,
            transient=True
        )
    
    def create_phase_progress(self, total_phases: int = 10) -> Progress:
        """Create a specialized progress display for workflow phases"""
        return Progress(
            TextColumn("[bold blue]Phase:[/bold blue]"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(
                complete_style="phase.completed" if THEMES_AVAILABLE else "green",
                finished_style="phase.active" if THEMES_AVAILABLE else "blue"
            ),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
    
    def create_provider_progress(self, provider_name: str) -> Progress:
        """Create a provider-specific progress display"""
        provider_color = self.theme_manager.get_provider_color(provider_name) if THEMES_AVAILABLE else "cyan"
        
        return Progress(
            SpinnerColumn(),
            TextColumn(f"[{provider_color}]{provider_name.title()}:[/{provider_color}]"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style=provider_color),
            console=self.console,
            transient=True
        )
    
    def display_tree_structure(self, tree_data: Dict[str, Any], title: str = "Structure") -> None:
        """Display hierarchical data as a tree"""
        tree = Tree(title)
        
        def add_items(parent_node, items):
            if isinstance(items, dict):
                for key, value in items.items():
                    node = parent_node.add(f"[bold]{key}[/bold]")
                    if isinstance(value, (dict, list)):
                        add_items(node, value)
                    else:
                        node.add(str(value))
            elif isinstance(items, list):
                for i, item in enumerate(items):
                    if isinstance(item, (dict, list)):
                        node = parent_node.add(f"[dim]Item {i}[/dim]")
                        add_items(node, item)
                    else:
                        parent_node.add(str(item))
        
        add_items(tree, tree_data)
        self.console.print(tree)
    
    def display_code(self, code: str, language: str = "python", title: Optional[str] = None) -> None:
        """Display syntax-highlighted code"""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        if title:
            panel = Panel(syntax, title=title, border_style="blue")
            self.console.print(panel)
        else:
            self.console.print(syntax)
    
    def display_markdown(self, content: str) -> None:
        """Display markdown content"""
        markdown = Markdown(content)
        self.console.print(markdown)
    
    def create_columns(self, items: List[Any], column_count: int = 2) -> None:
        """Display items in columns"""
        columns = Columns(items, equal=True, expand=True, padding=(0, 2))
        self.console.print(columns)
    
    def clear_screen(self) -> None:
        """Clear the console screen"""
        self.console.clear()
    
    def rule(self, title: str = "", style: str = "blue") -> None:
        """Print a horizontal rule with optional title"""
        self.console.rule(title, style=style)


    def display_phase_status(self, phases_data: Dict[str, Any]) -> None:
        """Display workflow phases with enhanced status indicators"""
        table = Table(title="🔄 Workflow Phases", show_header=True, header_style="bold primary")
        table.add_column("Phase", style="secondary", width=30)
        table.add_column("Status", style="text.primary", width=15)
        table.add_column("Duration", style="info", width=10)
        table.add_column("Agents", style="success", width=8)
        table.add_column("Progress", style="text.secondary")
        
        for phase_num, (phase_name, phase_data) in enumerate(phases_data.items()):
            status = phase_data.get('status', 'pending')
            duration = f"{phase_data.get('duration', 0):.1f}s"
            agent_count = len(phase_data.get('agents', []))
            progress = phase_data.get('progress', 0)
            
            # Format phase name with theming
            formatted_phase = format_phase(phase_num, phase_name, status) if THEMES_AVAILABLE else f"Phase {phase_num}: {phase_name}"
            
            # Status with icon
            status_text = format_status(status, status.title()) if THEMES_AVAILABLE else status.title()
            
            # Progress bar
            if progress > 0:
                progress_bar = f"[{'█' * int(progress/10)}{'░' * (10-int(progress/10))}] {progress}%"
            else:
                progress_bar = "Not started"
            
            table.add_row(
                formatted_phase,
                status_text,
                duration,
                str(agent_count),
                progress_bar
            )
        
        self.console.print(table)
    
    def display_agent_activity(self, agents_data: Dict[str, Any]) -> None:
        """Display real-time agent activity"""
        table = Table(title="🤖 Agent Activity", show_header=True, header_style="bold primary")
        table.add_column("Agent", style="secondary", width=25)
        table.add_column("Status", style="text.primary", width=12)
        table.add_column("Task", style="text.secondary", width=30)
        table.add_column("Progress", style="info", width=15)
        
        for agent_name, agent_data in agents_data.items():
            status = agent_data.get('status', 'idle')
            current_task = agent_data.get('current_task', 'No active task')
            progress = agent_data.get('progress', 0)
            
            # Format agent name by type if available
            agent_type = agent_data.get('type', 'general')
            formatted_agent = self.theme_manager.format_agent_name(agent_type, agent_name) if THEMES_AVAILABLE else agent_name
            
            status_text = format_status(status, status.title()) if THEMES_AVAILABLE else status.title()
            progress_text = f"{progress}%" if progress > 0 else "—"
            
            table.add_row(
                formatted_agent,
                status_text,
                current_task,
                progress_text
            )
        
        self.console.print(table)
    
    def display_quick_status(self, status_data: Dict[str, Any]) -> None:
        """Display a compact status overview"""
        # Status cards in columns
        cards = []
        
        # System status
        system_healthy = status_data.get('system_healthy', False)
        system_card = Panel(
            f"Status: {format_status('success' if system_healthy else 'error', 'Healthy' if system_healthy else 'Issues')}",
            title="🖥️ System",
            border_style="success" if system_healthy else "error"
        )
        cards.append(system_card)
        
        # Active workflows
        active_workflows = status_data.get('active_workflows', 0)
        workflow_card = Panel(
            f"Active: [bold]{active_workflows}[/bold]",
            title="🔄 Workflows",
            border_style="info"
        )
        cards.append(workflow_card)
        
        # Provider status
        healthy_providers = status_data.get('healthy_providers', 0)
        total_providers = status_data.get('total_providers', 0)
        provider_card = Panel(
            f"Healthy: [bold]{healthy_providers}/{total_providers}[/bold]",
            title="🔧 Providers",
            border_style="success" if healthy_providers == total_providers else "warning"
        )
        cards.append(provider_card)
        
        self.create_columns(cards, column_count=3)
    
    def create_live_dashboard(self, update_callback: Callable) -> Live:
        """Create a live updating dashboard"""
        layout = Layout()
        layout.split_column(
            Layout(Panel("[bold]LocalAgent Live Dashboard[/bold]", border_style="blue"), size=3),
            Layout(name="main")
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        return Live(
            layout,
            console=self.console,
            refresh_per_second=2,
            transient=False
        )


def create_display_manager(console: Optional[Console] = None, debug_mode: bool = False,
                          enable_whimsy: bool = False, magic_level: int = 5) -> DisplayManager:
    """Factory function to create DisplayManager instance with optional whimsical enhancements"""
    return DisplayManager(console, debug_mode, enable_whimsy, magic_level)

def create_whimsical_display_manager(console: Optional[Console] = None, 
                                   magic_level: int = 8) -> DisplayManager:
    """Create DisplayManager with whimsical UI enhancements enabled"""
    return DisplayManager(console, False, True, magic_level)

def enable_whimsy_mode(display_manager: DisplayManager, magic_level: int = 7) -> DisplayManager:
    """Enable whimsy mode on an existing DisplayManager (creates new instance)"""
    return DisplayManager(
        display_manager.console, 
        display_manager.debug_mode, 
        True, 
        magic_level
    )

def create_themed_console() -> Console:
    """Create a console with Claude theming"""
    return get_console() if THEMES_AVAILABLE else Console()