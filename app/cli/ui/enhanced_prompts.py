"""
Enhanced Interactive Prompts with Modern UI Features
Combines InquirerPy and Rich for beautiful CLI experiences with fallback support
"""

import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path

# Rich components (always available)
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn

# Try to import InquirerPy for modern interface
try:
    from inquirerpy import inquirer
    from inquirerpy.base.control import Choice
    from inquirerpy.prompts import fuzzy, confirm, text, select, checkbox, number, filepath
    from inquirerpy.validator import PathValidator, NumberValidator
    from inquirerpy.shortcuts import confirm as quick_confirm
    INQUIRERPY_AVAILABLE = True
except ImportError:
    # Fallback to simulated classes
    class Choice:
        def __init__(self, value, name=None):
            self.value = value
            self.name = name or value
    INQUIRERPY_AVAILABLE = False

# Theme integration with fallback
try:
    from .themes import get_console, get_inquirer_style, format_provider, format_status
    THEMES_AVAILABLE = True
except ImportError:
    def get_console():
        return Console()
    def get_inquirer_style():
        return None
    def format_provider(name, enabled=True):
        return f"{'✓' if enabled else '✗'} {name}"
    def format_status(status, message):
        icons = {'success': '✓', 'error': '✗', 'warning': '⚠', 'info': 'ℹ'}
        return f"{icons.get(status, '•')} {message}"
    THEMES_AVAILABLE = False

from ..core.config import LocalAgentConfig, ProviderConfig, OrchestrationConfig, MCPConfig, PluginConfig


class ModernInteractivePrompts:
    """
    Modern interactive prompt utilities with InquirerPy and Rich integration
    Falls back gracefully to Rich-only prompts when InquirerPy is unavailable
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or get_console()
        self.inquirer_style = get_inquirer_style() if INQUIRERPY_AVAILABLE else None
        self.modern_mode = INQUIRERPY_AVAILABLE
    
    def ask_choice(self, question: str, choices: List[str], 
                   default: Optional[str] = None) -> str:
        """Ask user to choose from a list of options"""
        if self.modern_mode:
            # Modern InquirerPy interface
            choice_items = [Choice(choice, name=choice) for choice in choices]
            
            result = inquirer.select(
                message=question,
                choices=choice_items,
                default=default,
                style=self.inquirer_style,
                pointer="❯",
                instruction="(Use arrow keys to navigate, Enter to select)"
            ).execute()
            
            return result
        else:
            # Fallback to Rich prompts with enhanced display
            self._display_choices(choices, question)
            
            while True:
                answer = Prompt.ask(
                    f"{question} [{'/'.join(choices)}]",
                    choices=choices,
                    default=default,
                    console=self.console
                )
                return answer

    def ask_fuzzy_choice(self, question: str, choices: List[Union[str, Choice]], 
                        default: Optional[str] = None, max_height: int = 10) -> str:
        """Ask user to choose from options with fuzzy search"""
        if self.modern_mode:
            if isinstance(choices[0], str):
                choice_items = [Choice(choice, name=choice) for choice in choices]
            else:
                choice_items = choices
            
            result = inquirer.fuzzy(
                message=question,
                choices=choice_items,
                default=default,
                max_height=max_height,
                style=self.inquirer_style,
                instruction="(Type to search, use arrow keys, Enter to select)",
                border=True,
                info=True,
            ).execute()
            
            return result
        else:
            # Fallback: display options and use regular choice
            self.console.print("[yellow]💡 Fuzzy search not available, using regular selection[/yellow]")
            string_choices = [c.value if hasattr(c, 'value') else str(c) for c in choices]
            return self.ask_choice(question, string_choices, default)
    
    def ask_multi_choice(self, question: str, choices: List[Union[str, Choice]], 
                        default: Optional[List[str]] = None) -> List[str]:
        """Ask user to select multiple options from a list"""
        if self.modern_mode:
            if isinstance(choices[0], str):
                choice_items = [Choice(choice, name=choice) for choice in choices]
            else:
                choice_items = choices
            
            result = inquirer.checkbox(
                message=question,
                choices=choice_items,
                default=default or [],
                style=self.inquirer_style,
                instruction="(Use space to select/deselect, Enter to confirm)",
                transformer=lambda result: f"{len(result)} selected",
            ).execute()
            
            return result
        else:
            # Fallback: manual multi-selection
            self.console.print(f"[blue]{question}[/blue]")
            self.console.print("[dim]Select multiple options (comma-separated indices or 'all'):[/dim]")
            
            string_choices = [c.value if hasattr(c, 'value') else str(c) for c in choices]
            
            # Display numbered choices
            for i, choice in enumerate(string_choices, 1):
                self.console.print(f"  {i}. {choice}")
            
            while True:
                selection = Prompt.ask(
                    "Enter selection (e.g., '1,3,5' or 'all')",
                    console=self.console
                )
                
                if selection.lower() == 'all':
                    return string_choices
                
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    result = [string_choices[i] for i in indices if 0 <= i < len(string_choices)]
                    if result:
                        return result
                    else:
                        self.console.print("[red]Invalid selection. Try again.[/red]")
                except (ValueError, IndexError):
                    self.console.print("[red]Invalid format. Use comma-separated numbers or 'all'.[/red]")

    def ask_text(self, question: str, default: Optional[str] = None, 
                 required: bool = False, validator: Optional[Callable] = None) -> Optional[str]:
        """Ask for text input with validation"""
        if self.modern_mode:
            validate = None
            if required or validator:
                def validate_input(text):
                    if required and not text.strip():
                        raise ValueError("This field is required")
                    if validator:
                        return validator(text)
                    return True
                validate = validate_input
            
            result = inquirer.text(
                message=question,
                default=default or "",
                validate=validate,
                style=self.inquirer_style,
                instruction="(Type your answer and press Enter)"
            ).execute()
            
            return result if result else default
        else:
            # Fallback to Rich prompt with validation loop
            while True:
                answer = Prompt.ask(question, default=default, console=self.console)
                
                if not answer and required:
                    self.console.print("[red]This field is required[/red]")
                    continue
                
                if validator and answer:
                    try:
                        validator(answer)
                    except ValueError as e:
                        self.console.print(f"[red]{str(e)}[/red]")
                        continue
                
                return answer or default

    def ask_password(self, question: str, required: bool = False) -> Optional[str]:
        """Ask for password input (hidden)"""
        if self.modern_mode:
            validate = None
            if required:
                def validate_password(password):
                    if not password.strip():
                        raise ValueError("Password is required")
                    return True
                validate = validate_password
            
            result = inquirer.secret(
                message=question,
                validate=validate,
                style=self.inquirer_style,
                instruction="(Type your password - input is hidden)"
            ).execute()
            
            return result if result else None
        else:
            # Fallback to Rich password prompt
            while True:
                answer = Prompt.ask(question, password=True, console=self.console)
                
                if not answer and required:
                    self.console.print("[red]Password is required[/red]")
                    continue
                
                return answer if answer else None

    def ask_integer(self, question: str, default: Optional[int] = None,
                    min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
        """Ask for integer input with range validation"""
        if self.modern_mode:
            validator = NumberValidator(
                message="Please enter a valid integer",
                min_val=min_val,
                max_val=max_val
            )
            
            result = inquirer.number(
                message=question,
                default=default,
                validate=validator,
                style=self.inquirer_style,
                instruction=f"(Enter a number{f', min: {min_val}' if min_val is not None else ''}{f', max: {max_val}' if max_val is not None else ''})",
                replace_mode=True
            ).execute()
            
            return int(result)
        else:
            # Fallback to Rich integer prompt with validation
            while True:
                try:
                    answer = IntPrompt.ask(question, default=default, console=self.console)
                    
                    if min_val is not None and answer < min_val:
                        self.console.print(f"[red]Value must be at least {min_val}[/red]")
                        continue
                    
                    if max_val is not None and answer > max_val:
                        self.console.print(f"[red]Value must be at most {max_val}[/red]")
                        continue
                    
                    return answer
                    
                except ValueError:
                    self.console.print("[red]Please enter a valid number[/red]")

    def ask_boolean(self, question: str, default: bool = False) -> bool:
        """Ask for yes/no confirmation"""
        if self.modern_mode:
            result = inquirer.confirm(
                message=question,
                default=default,
                style=self.inquirer_style,
                instruction="(y/n, default: {})".format('yes' if default else 'no')
            ).execute()
            
            return result
        else:
            # Fallback to Rich confirm
            return Confirm.ask(question, default=default, console=self.console)

    def ask_path(self, question: str, default: Optional[str] = None,
                 must_exist: bool = False, only_directories: bool = False) -> Path:
        """Ask for file/directory path with validation"""
        if self.modern_mode:
            validator = None
            if must_exist:
                validator = PathValidator(is_file=not only_directories, message="Path must exist")
            
            result = inquirer.filepath(
                message=question,
                default=str(default) if default else "",
                validate=validator,
                only_directories=only_directories,
                style=self.inquirer_style,
                instruction="(Use tab for completion, Enter to select)"
            ).execute()
            
            return Path(result).expanduser().resolve()
        else:
            # Fallback to text input with path validation
            while True:
                answer = self.ask_text(question, default, required=True)
                path = Path(answer).expanduser().resolve()
                
                if must_exist and not path.exists():
                    self.console.print(f"[red]Path does not exist: {path}[/red]")
                    continue
                
                if only_directories and path.exists() and not path.is_dir():
                    self.console.print(f"[red]Path must be a directory: {path}[/red]")
                    continue
                
                return path

    def ask_provider_selection(self, available_providers: List[str], 
                             current_default: Optional[str] = None) -> str:
        """Specialized provider selection with enhanced styling"""
        self.console.print("\n[bold blue]🔧 Select LLM Provider[/bold blue]")
        
        # Provider information
        provider_info = {
            'ollama': 'Local models (no API key required)',
            'openai': 'GPT models from OpenAI',
            'gemini': 'Google Gemini models',
            'claude': 'Anthropic Claude models',
            'perplexity': 'Perplexity AI with web search',
        }
        
        if self.modern_mode:
            choices = []
            for provider in available_providers:
                info = provider_info.get(provider, 'Custom provider')
                choice_name = f"{format_provider(provider)} - {info}"
                choices.append(Choice(value=provider, name=choice_name))
            
            return self.ask_fuzzy_choice(
                "Choose your preferred LLM provider",
                choices,
                default=current_default
            )
        else:
            # Enhanced fallback display
            table = Table(title="Available Providers", show_header=True, header_style="bold blue")
            table.add_column("Provider", style="cyan")
            table.add_column("Description", style="white")
            
            for provider in available_providers:
                info = provider_info.get(provider, 'Custom provider')
                table.add_row(format_provider(provider), info)
            
            self.console.print(table)
            return self.ask_choice("Choose your provider", available_providers, current_default)

    def ask_model_selection(self, provider_name: str, available_models: List[str], 
                          current_default: Optional[str] = None) -> str:
        """Model selection with enhanced information"""
        self.console.print(f"\n[bold blue]🤖 Select Model for {format_provider(provider_name)}[/bold blue]")
        
        # Model information
        model_info = {
            # OpenAI models
            'gpt-4': 'Most capable GPT model',
            'gpt-4-turbo': 'Faster GPT-4 with recent knowledge',
            'gpt-3.5-turbo': 'Fast and efficient for most tasks',
            
            # Gemini models
            'gemini-pro': 'Google\'s flagship model',
            'gemini-pro-vision': 'Multimodal capabilities',
            
            # Claude models
            'claude-3-opus': 'Most powerful Claude model',
            'claude-3-sonnet': 'Balanced performance and speed',
            'claude-3-haiku': 'Fast and efficient',
            
            # Common Ollama models
            'llama2': 'Meta\'s Llama 2 model',
            'codellama': 'Specialized for coding tasks',
            'mistral': 'Mistral AI model',
            'phi': 'Microsoft\'s Phi model',
            'neural-chat': 'Intel\'s neural chat model',
        }
        
        if self.modern_mode:
            choices = []
            for model in available_models:
                info = model_info.get(model, 'Available model')
                choice_name = f"[cyan]{model}[/cyan] - {info}"
                choices.append(Choice(value=model, name=choice_name))
            
            return self.ask_fuzzy_choice(
                f"Choose model for {provider_name}",
                choices,
                default=current_default,
                max_height=15
            )
        else:
            # Enhanced fallback display
            table = Table(title=f"Available Models for {provider_name}", show_header=True, header_style="bold blue")
            table.add_column("Model", style="cyan")
            table.add_column("Description", style="white")
            
            for model in available_models:
                info = model_info.get(model, 'Available model')
                table.add_row(model, info)
            
            self.console.print(table)
            return self.ask_choice("Choose your model", available_models, current_default)

    def ask_workflow_options(self) -> Dict[str, Any]:
        """Interactive workflow configuration"""
        self.console.print("\n[bold blue]⚙️ Workflow Configuration[/bold blue]")
        
        # Execution mode
        execution_modes = ['interactive', 'guided', 'automated']
        if self.modern_mode:
            mode_choices = [
                Choice(value='interactive', name='🎯 Interactive - Full user control and confirmations'),
                Choice(value='guided', name='🚀 Guided - Minimal prompts with smart defaults'),
                Choice(value='automated', name='⚡ Automated - Full automation with evidence collection'),
            ]
            execution_mode = self.ask_choice("Choose execution mode", [c.value for c in mode_choices])
        else:
            self.console.print("[bold]Execution Modes:[/bold]")
            self.console.print("  🎯 [cyan]interactive[/cyan] - Full user control and confirmations")
            self.console.print("  🚀 [cyan]guided[/cyan] - Minimal prompts with smart defaults")
            self.console.print("  ⚡ [cyan]automated[/cyan] - Full automation with evidence collection")
            execution_mode = self.ask_choice("Choose execution mode", execution_modes, 'guided')
        
        # Other settings
        max_agents = self.ask_integer("Maximum parallel agents", default=10, min_val=1, max_val=50)
        collect_evidence = self.ask_boolean("Enable evidence collection for debugging?", default=True)
        
        # Phase selection
        all_phases = [
            'Phase 0: Interactive Prompt Engineering',
            'Phase 1: Parallel Research & Discovery', 
            'Phase 2: Strategic Planning & Stream Design',
            'Phase 3: Context Package Creation',
            'Phase 4: Parallel Stream Execution',
            'Phase 5: Integration & Merge',
            'Phase 6: Comprehensive Testing',
            'Phase 7: Audit & Learning',
            'Phase 8: Cleanup & Documentation',
            'Phase 9: Development Deployment',
        ]
        
        phases_to_run = self.ask_multi_choice(
            "Select phases to execute (default: all)",
            all_phases,
            default=all_phases
        )
        
        return {
            'execution_mode': execution_mode,
            'max_parallel_agents': max_agents,
            'collect_evidence': collect_evidence,
            'phases_to_run': phases_to_run,
        }

    def display_provider_status(self, providers: Dict[str, Any]) -> None:
        """Display provider status with health indicators"""
        table = Table(title="🔧 Provider Status", show_header=True, header_style="bold primary")
        table.add_column("Provider", style="cyan", width=15)
        table.add_column("Status", style="white", width=12)
        table.add_column("Health", style="white", width=10)
        table.add_column("Default Model", style="blue", width=20)
        table.add_column("Details", style="dim")
        
        for provider_name, provider_data in providers.items():
            # Format status
            enabled = provider_data.get('enabled', False)
            status = format_status('success', 'Enabled') if enabled else format_status('warning', 'Disabled')
            
            # Health status
            healthy = provider_data.get('healthy', False)
            health = format_status('success', 'Healthy') if healthy else format_status('error', 'Issues')
            
            # Model info
            model = provider_data.get('default_model', 'Auto-detect')
            
            # Additional details
            details = []
            if provider_data.get('api_key_required') and not provider_data.get('has_api_key'):
                details.append('No API key')
            if provider_data.get('rate_limit'):
                details.append(f"Rate limit: {provider_data['rate_limit']}/min")
            if provider_data.get('base_url') and provider_data['base_url'] != 'default':
                details.append('Custom URL')
            
            table.add_row(
                format_provider(provider_name, enabled),
                status,
                health,
                f"[cyan]{model}[/cyan]",
                ", ".join(details) or "Default settings"
            )
        
        self.console.print(table)

    def display_workflow_preview(self, workflow_config: Dict[str, Any]) -> None:
        """Display workflow configuration preview"""
        self.console.print("\n[bold blue]🔄 Workflow Configuration Preview[/bold blue]")
        
        config_table = Table(show_header=False, box=None, padding=(0, 2))
        config_table.add_column("Setting", style="cyan", width=25)
        config_table.add_column("Value", style="white")
        
        config_table.add_row("Execution Mode", f"[bold]{workflow_config.get('execution_mode', 'interactive').title()}[/bold]")
        config_table.add_row("Max Parallel Agents", str(workflow_config.get('max_parallel_agents', 10)))
        config_table.add_row("Evidence Collection", "✓ Enabled" if workflow_config.get('collect_evidence') else "✗ Disabled")
        
        phases_count = len(workflow_config.get('phases_to_run', []))
        config_table.add_row("Phases to Execute", f"{phases_count} phases selected")
        
        self.console.print(config_table)
        
        if workflow_config.get('phases_to_run'):
            self.console.print("\n[bold cyan]📋 Selected Phases:[/bold cyan]")
            for i, phase in enumerate(workflow_config['phases_to_run'][:3]):  # Show first 3
                self.console.print(f"  {format_status('info', phase)}")
            if len(workflow_config['phases_to_run']) > 3:
                remaining = len(workflow_config['phases_to_run']) - 3
                self.console.print(f"  [dim]...and {remaining} more phases[/dim]")

    def _display_choices(self, choices: List[str], title: str) -> None:
        """Helper to display choices in a formatted way"""
        table = Table(title=f"Available Options: {title}", show_header=False, box=None, padding=(0, 1))
        table.add_column("Choice", style="cyan")
        
        for choice in choices:
            table.add_row(f"• {choice}")
        
        self.console.print(table)

    def show_progress_spinner(self, message: str = "Working..."):
        """Show a simple progress spinner"""
        return Progress(
            SpinnerColumn(),
            TextColumn(f"[bold blue]{message}[/bold blue]"),
            console=self.console,
            transient=True
        )


class GuidedSetupWizard:
    """
    Guided setup wizard using modern interactive prompts
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or get_console()
        self.prompts = ModernInteractivePrompts(console)
    
    async def run_setup(self) -> Optional[LocalAgentConfig]:
        """Run the complete guided setup wizard"""
        self.console.print("\n[bold blue]🚀 LocalAgent Setup Wizard[/bold blue]\n")
        
        # Welcome message
        welcome_panel = Panel(
            "[bold]Welcome to LocalAgent![/bold]\n\n"
            "This wizard will help you configure LocalAgent for optimal performance.\n"
            "You can modify these settings later using the 'config' command.\n\n"
            f"🔧 Modern UI: {'Enabled' if INQUIRERPY_AVAILABLE else 'Basic mode'}\n"
            f"🎨 Enhanced themes: {'Available' if THEMES_AVAILABLE else 'Basic styling'}",
            title="Setup Wizard",
            border_style="blue"
        )
        self.console.print(welcome_panel)
        
        try:
            # Quick or detailed setup
            setup_mode = self.prompts.ask_choice(
                "Choose setup mode",
                ['quick', 'detailed'],
                default='quick'
            )
            
            if setup_mode == 'quick':
                config = await self._quick_setup()
            else:
                config = await self._detailed_setup()
            
            if config and await self._confirm_setup(config):
                return config
            else:
                self.console.print("[yellow]Setup cancelled by user.[/yellow]")
                return None
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Setup cancelled by user.[/yellow]")
            return None
        except Exception as e:
            self.console.print(f"\n[red]Setup failed: {e}[/red]")
            return None
    
    async def _quick_setup(self) -> LocalAgentConfig:
        """Quick setup with smart defaults"""
        self.console.rule("[bold]Quick Setup[/bold]")
        
        # Basic config with defaults
        config_dir = Path.home() / ".localagent"
        config_dir.mkdir(exist_ok=True, parents=True)
        
        self.console.print(f"📁 Using config directory: [cyan]{config_dir}[/cyan]")
        
        # Provider setup
        providers = {'ollama': ProviderConfig(
            base_url="http://localhost:11434",
            enabled=True
        )}
        
        # Optional API providers
        setup_api = self.prompts.ask_boolean(
            "Configure API providers (OpenAI, Gemini, etc.)?", 
            default=False
        )
        
        if setup_api:
            # Quick API provider setup
            available_api_providers = ['openai', 'gemini', 'claude', 'perplexity']
            selected_providers = self.prompts.ask_multi_choice(
                "Select API providers to configure",
                available_api_providers
            )
            
            for provider in selected_providers:
                api_key = self.prompts.ask_password(
                    f"API key for {provider} (optional - can set later)"
                )
                if api_key:
                    providers[provider] = ProviderConfig(
                        api_key=api_key,
                        enabled=True
                    )
        
        return LocalAgentConfig(
            config_dir=config_dir,
            log_level="INFO",
            debug_mode=False,
            providers=providers,
            default_provider="ollama",
            orchestration=OrchestrationConfig(),
            mcp=MCPConfig(),
            plugins=PluginConfig()
        )
    
    async def _detailed_setup(self) -> LocalAgentConfig:
        """Detailed setup with all configuration options"""
        self.console.rule("[bold]Detailed Setup[/bold]")
        
        # This would implement the full setup wizard
        # For now, redirect to quick setup with more options
        self.console.print("[yellow]Detailed setup not yet implemented. Using enhanced quick setup.[/yellow]")
        return await self._quick_setup()
    
    async def _confirm_setup(self, config: LocalAgentConfig) -> bool:
        """Confirm the configuration setup"""
        self.console.rule("[bold]Configuration Summary[/bold]")
        
        # Display configuration summary
        summary_table = Table(title="Your LocalAgent Configuration", show_header=True, header_style="bold blue")
        summary_table.add_column("Setting", style="cyan", width=25)
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Config Directory", str(config.config_dir))
        summary_table.add_row("Log Level", config.log_level)
        summary_table.add_row("Default Provider", config.default_provider)
        
        enabled_providers = [name for name, cfg in config.providers.items() if cfg.enabled]
        summary_table.add_row("Enabled Providers", ", ".join(enabled_providers))
        
        self.console.print(summary_table)
        
        return self.prompts.ask_boolean(
            "Save this configuration and complete setup?", 
            default=True
        )


# Convenience functions
def create_modern_prompts(console: Optional[Console] = None) -> ModernInteractivePrompts:
    """Create a modern interactive prompts instance"""
    return ModernInteractivePrompts(console)

def create_guided_wizard(console: Optional[Console] = None) -> GuidedSetupWizard:
    """Create a guided setup wizard instance"""
    return GuidedSetupWizard(console)