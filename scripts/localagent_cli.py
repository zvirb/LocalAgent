#!/usr/bin/env python3
"""
LocalAgent Interactive CLI - Claude Code Style
Modern interactive CLI with Rich theming and InquirerPy prompts
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

# Import CLI components
try:
    from app.cli.ui.themes import get_console, format_provider, format_status, showcase_theme
    from app.cli.ui.enhanced_prompts import ModernInteractivePrompts, GuidedSetupWizard
    from app.cli.core.app import LocalAgentApp, create_app
    from app.cli.core.config import LocalAgentConfig
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some CLI components not available: {e}")
    from rich.console import Console
    get_console = Console
    COMPONENTS_AVAILABLE = False
    
    # Create fallback functions
    def format_provider(name, enabled=True):
        return f"{'✓' if enabled else '✗'} {name}"
    
    def format_status(status, message):
        icons = {'success': '✓', 'error': '✗', 'warning': '⚠', 'info': 'ℹ', 'completed': '🎉'}
        icon = icons.get(status, '•')
        colors = {'success': 'green', 'error': 'red', 'warning': 'yellow', 'info': 'blue', 'completed': 'green'}
        color = colors.get(status, 'white')
        return f"[{color}]{icon} {message}[/{color}]"
    
    def showcase_theme():
        console = Console()
        console.print("[bold blue]🎨 Basic Theme Showcase[/bold blue]")
        console.print("[green]✓ Success message[/green]")
        console.print("[red]✗ Error message[/red]")
        console.print("[yellow]⚠ Warning message[/yellow]")
        console.print("[blue]ℹ Info message[/blue]")
    
    # Create fallback classes
    class ModernInteractivePrompts:
        def __init__(self, console):
            self.console = console
        def ask_choice(self, question, choices, default=None):
            return default or choices[0]
        def ask_text(self, question, required=False):
            return "demo input"
        def ask_boolean(self, question, default=False):
            return default
        def ask_provider_selection(self, providers, default=None):
            return default or providers[0]
        def ask_workflow_options(self):
            return {"execution_mode": "guided", "max_parallel_agents": 10}
        def display_workflow_preview(self, config):
            pass
        def display_provider_status(self, providers):
            pass
    
    class GuidedSetupWizard:
        def __init__(self, console):
            self.console = console
        async def run_setup(self):
            return None

# Create the main Typer app
app = typer.Typer(
    name="localagent",
    help="🤖 LocalAgent - Interactive Multi-provider LLM Orchestration CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]}
)

console = get_console()

@app.command()
def interactive(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM provider to use"),
    setup: bool = typer.Option(False, "--setup", help="Run setup wizard first"),
):
    """🚀 Start interactive LocalAgent CLI session"""
    asyncio.run(_interactive_session(provider, setup))

@app.command() 
def workflow(
    prompt: str = typer.Argument(help="Workflow prompt to execute"),
    provider: Optional[str] = typer.Option("ollama", "--provider", "-p", help="LLM provider to use"),
    phases: Optional[str] = typer.Option(None, "--phases", help="Specific phases to run (e.g., '1,2,3')"),
    parallel: bool = typer.Option(True, "--parallel/--sequential", help="Run agents in parallel"),
    max_agents: int = typer.Option(10, "--max-agents", help="Maximum parallel agents"),
):
    """⚡ Execute 12-phase UnifiedWorkflow"""
    console.print(f"\n[bold blue]🔄 Executing Workflow:[/bold blue] {prompt}")
    console.print(f"[cyan]Provider:[/cyan] {format_provider(provider)}")
    console.print(f"[cyan]Parallel:[/cyan] {'✓' if parallel else '✗'}")
    console.print(f"[cyan]Max Agents:[/cyan] {max_agents}")
    
    if phases:
        console.print(f"[cyan]Phases:[/cyan] {phases}")
    
    # This would integrate with the actual orchestration system
    asyncio.run(_execute_workflow(prompt, provider, phases, parallel, max_agents))

@app.command()
def setup():
    """🛠️ Run guided setup wizard"""
    asyncio.run(_run_setup_wizard())

@app.command()
def theme():
    """🎨 Display theme showcase"""
    showcase_theme()

@app.command()  
def health():
    """🏥 System health check and diagnostics"""
    console.print("\n[bold blue]🏥 LocalAgent Health Check[/bold blue]")
    
    # Check components
    health_table = Table(title="Component Health", show_header=True, header_style="bold blue")
    health_table.add_column("Component", style="cyan", width=25)
    health_table.add_column("Status", style="white", width=15)
    health_table.add_column("Details", style="dim")
    
    # CLI Components
    cli_status = format_status('success', 'Available') if COMPONENTS_AVAILABLE else format_status('warning', 'Limited')
    health_table.add_row("CLI Components", cli_status, "Core CLI functionality")
    
    # Dependencies
    try:
        import rich, typer, inquirerpy
        deps_status = format_status('success', 'All Available')
        deps_details = f"Rich {rich.__version__}, Typer {typer.__version__}, InquirerPy available"
    except ImportError as e:
        deps_status = format_status('error', 'Missing')
        deps_details = f"Missing: {e}"
    
    health_table.add_row("Dependencies", deps_status, deps_details)
    
    # Virtual Environment
    venv_active = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    venv_status = format_status('success', 'Active') if venv_active else format_status('warning', 'Not Active')
    health_table.add_row("Virtual Environment", venv_status, f"Python {sys.version_info.major}.{sys.version_info.minor}")
    
    console.print(health_table)

@app.command()
def chat(
    provider: Optional[str] = typer.Option("ollama", "--provider", "-p", help="LLM provider to use"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Specific model"),
    session: Optional[str] = typer.Option(None, "--session", help="Session name for history"),
):
    """💬 Start interactive chat session"""
    console.print(f"\n[bold blue]💬 Starting Chat Session[/bold blue]")
    console.print(f"[cyan]Provider:[/cyan] {format_provider(provider)}")
    if model:
        console.print(f"[cyan]Model:[/cyan] {model}")
    if session:
        console.print(f"[cyan]Session:[/cyan] {session}")
    
    asyncio.run(_start_chat_session(provider, model, session))

@app.command()
def providers(
    list_all: bool = typer.Option(False, "--list", "-l", help="List all providers"),
    health_check: bool = typer.Option(False, "--health", help="Check provider health"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Specific provider"),
):
    """🔧 Manage LLM providers"""
    asyncio.run(_manage_providers(list_all, health_check, provider))

# Implementation functions

async def _interactive_session(provider: Optional[str], setup: bool):
    """Main interactive session"""
    console.print(Panel(
        "[bold]🤖 Welcome to LocalAgent Interactive CLI![/bold]\n\n"
        f"🎨 Modern UI: {'Enabled' if COMPONENTS_AVAILABLE else 'Basic mode'}\n"
        f"🔧 Components: {'Full' if COMPONENTS_AVAILABLE else 'Limited'}\n"
        f"⚡ Ready for interactive workflow orchestration",
        title="LocalAgent CLI",
        border_style="blue"
    ))
    
    if not COMPONENTS_AVAILABLE:
        console.print("[yellow]⚠️ Some advanced features may be limited. Run setup to install dependencies.[/yellow]")
        return
    
    if setup:
        await _run_setup_wizard()
        return
    
    try:
        prompts = ModernInteractivePrompts(console)
        
        # Main menu loop
        while True:
            action = prompts.ask_choice(
                "What would you like to do?",
                [
                    "Execute workflow",
                    "Chat with LLM",
                    "Manage providers", 
                    "Setup configuration",
                    "System health check",
                    "Exit"
                ],
                default="Execute workflow"
            )
            
            if action == "Execute workflow":
                await _interactive_workflow(prompts)
            elif action == "Chat with LLM":
                await _interactive_chat(prompts)
            elif action == "Manage providers":
                await _interactive_providers(prompts)
            elif action == "Setup configuration":
                await _run_setup_wizard()
            elif action == "System health check":
                await _interactive_health_check()
            elif action == "Exit":
                console.print("[green]👋 Goodbye![/green]")
                break
                
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Session interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")

async def _interactive_workflow(prompts: ModernInteractivePrompts):
    """Interactive workflow execution"""
    console.print("\n[bold blue]⚡ Workflow Execution[/bold blue]")
    
    # Get workflow prompt
    prompt = prompts.ask_text(
        "Enter your workflow prompt",
        required=True
    )
    
    # Provider selection
    available_providers = ["ollama", "openai", "gemini", "claude", "perplexity"]
    provider = prompts.ask_provider_selection(available_providers, "ollama")
    
    # Workflow options
    workflow_config = prompts.ask_workflow_options()
    
    # Preview and confirm
    prompts.display_workflow_preview(workflow_config)
    
    if prompts.ask_boolean("Execute this workflow?", default=True):
        await _execute_workflow(
            prompt, 
            provider, 
            None,  # phases
            workflow_config.get('max_parallel_agents', 10) > 1,  # parallel
            workflow_config.get('max_parallel_agents', 10)
        )

async def _interactive_chat(prompts: ModernInteractivePrompts):
    """Interactive chat session setup"""
    console.print("\n[bold blue]💬 Chat Session Setup[/bold blue]")
    
    # Provider selection
    available_providers = ["ollama", "openai", "gemini", "claude", "perplexity"] 
    provider = prompts.ask_provider_selection(available_providers, "ollama")
    
    # Optional model selection
    if prompts.ask_boolean("Select specific model?", default=False):
        # This would get actual models from provider
        available_models = ["auto-detect", "gpt-4", "llama2", "gemini-pro"]
        model = prompts.ask_model_selection(provider, available_models)
    else:
        model = None
    
    # Session name
    session = prompts.ask_text("Session name (optional)")
    
    await _start_chat_session(provider, model, session)

async def _interactive_providers(prompts: ModernInteractivePrompts):
    """Interactive provider management"""
    console.print("\n[bold blue]🔧 Provider Management[/bold blue]")
    
    # Mock provider data for demo
    providers_data = {
        "ollama": {"enabled": True, "healthy": True, "default_model": "llama2"},
        "openai": {"enabled": False, "healthy": False, "api_key_required": True, "has_api_key": False},
        "gemini": {"enabled": False, "healthy": False, "api_key_required": True, "has_api_key": False},
    }
    
    prompts.display_provider_status(providers_data)
    
    action = prompts.ask_choice(
        "Provider action",
        ["Configure provider", "Test provider", "Enable/disable provider", "Back"],
        default="Back"
    )
    
    if action == "Back":
        return
    
    provider = prompts.ask_choice(
        "Select provider",
        list(providers_data.keys())
    )
    
    console.print(f"[cyan]Selected action:[/cyan] {action} for {format_provider(provider)}")

async def _interactive_health_check():
    """Interactive health check with details"""
    console.print("\n[bold blue]🏥 Detailed Health Check[/bold blue]")
    
    with console.status("[bold green]Running health checks...") as status:
        import time
        time.sleep(1)  # Simulate health check
        
        status.update("[bold green]Checking dependencies...")
        time.sleep(0.5)
        
        status.update("[bold green]Testing providers...")
        time.sleep(0.5)
        
        status.update("[bold green]Validating configuration...")
        time.sleep(0.5)
    
    console.print(format_status('success', 'Health check completed'))

async def _execute_workflow(prompt: str, provider: str, phases: Optional[str], parallel: bool, max_agents: int):
    """Execute workflow (placeholder)"""
    console.print(f"\n[bold green]🚀 Starting workflow execution...[/bold green]")
    
    with console.status("[bold blue]Executing 12-phase workflow...") as status:
        import time
        
        phases_list = [
            "Interactive Prompt Engineering",
            "Parallel Research & Discovery", 
            "Strategic Planning & Stream Design",
            "Context Package Creation",
            "Parallel Stream Execution",
            "Integration & Merge",
            "Comprehensive Testing",
            "Audit & Learning",
            "Cleanup & Documentation",
            "Development Deployment"
        ]
        
        for i, phase_name in enumerate(phases_list):
            status.update(f"[bold blue]Phase {i}: {phase_name}...")
            time.sleep(0.3)
            console.print(format_status('success', f"Phase {i}: {phase_name}"))
    
    console.print(format_status('completed', 'Workflow execution completed successfully!'))

async def _start_chat_session(provider: str, model: Optional[str], session: Optional[str]):
    """Start chat session (placeholder)"""
    console.print(f"\n[bold green]💬 Chat session started with {format_provider(provider)}[/bold green]")
    if model:
        console.print(f"[cyan]Model:[/cyan] {model}")
    
    console.print("\n[dim]Type '/help' for commands, '/quit' to exit[/dim]")
    
    # Simple chat loop for demo
    while True:
        try:
            user_input = console.input("[bold blue]You:[/bold blue] ")
            if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                console.print("[green]Chat session ended[/green]")
                break
            elif user_input.lower() == '/help':
                console.print("[cyan]Available commands:[/cyan] /help, /quit, /provider, /model")
            else:
                console.print(f"[bold green]Assistant:[/bold green] Echo: {user_input}")
                console.print("[dim]This is a demo response. Actual LLM integration would go here.[/dim]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Chat session interrupted[/yellow]")
            break

async def _manage_providers(list_all: bool, health_check: bool, provider: Optional[str]):
    """Manage providers (placeholder)"""
    console.print(f"\n[bold blue]🔧 Provider Management[/bold blue]")
    
    if list_all:
        providers = ["ollama", "openai", "gemini", "claude", "perplexity"]
        console.print("[bold]Available providers:[/bold]")
        for p in providers:
            console.print(f"  {format_provider(p, p == 'ollama')}")
    
    if health_check:
        console.print("\n[bold]Provider Health Status:[/bold]")
        console.print(f"  {format_status('success', 'Ollama: Running on localhost:11434')}")
        console.print(f"  {format_status('error', 'OpenAI: No API key configured')}")
        console.print(f"  {format_status('warning', 'Gemini: API key configured but not tested')}")

async def _run_setup_wizard():
    """Run the guided setup wizard"""
    if not COMPONENTS_AVAILABLE:
        console.print("[red]Setup wizard requires full CLI components[/red]")
        return
    
    try:
        wizard = GuidedSetupWizard(console)
        config = await wizard.run_setup()
        
        if config:
            console.print(format_status('success', 'Setup completed successfully!'))
        else:
            console.print(format_status('warning', 'Setup was cancelled'))
            
    except Exception as e:
        console.print(format_status('error', f'Setup failed: {e}'))

def main():
    """Main entry point"""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()