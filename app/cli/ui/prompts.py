"""
Interactive Prompts and Configuration Wizards
Rich-based interactive user input components
"""

import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path

# Rich components (keeping existing)
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.columns import Columns

# Fallback to Rich prompts for simpler implementation
# TODO: Re-enable inquirerpy when properly installed
# from inquirerpy import inquirer
# from inquirerpy.base.control import Choice
# from inquirerpy.prompts import fuzzy, confirm, text, select, checkbox, number, filepath
# from inquirerpy.validator import PathValidator, NumberValidator
# from inquirerpy.shortcuts import confirm as quick_confirm

# Theme integration (fallback to basic console)
# from .themes import get_console, get_inquirer_style, format_provider, format_status

from ..core.config import LocalAgentConfig, ProviderConfig, OrchestrationConfig, MCPConfig, PluginConfig
from ...llm_providers.provider_manager import ProviderManager


class InteractivePrompts:
    """
    Collection of interactive prompt utilities using InquirerPy for modern CLI experience
    """
    
    def __init__(self, console: Console):
        self.console = console
    
    def ask_choice(self, question: str, choices: List[str], 
                   default: Optional[str] = None) -> str:
        """Ask user to choose from a list of options using Rich prompts"""
        self.console.print(f"\n[bold cyan]{question}[/bold cyan]")
        for i, choice in enumerate(choices, 1):
            marker = "›" if choice == default else " "
            self.console.print(f"{marker} {i}. {choice}")
        
        while True:
            try:
                selection = IntPrompt.ask("Select option (number)", default=1 if not default else choices.index(default) + 1)
                if 1 <= selection <= len(choices):
                    return choices[selection - 1]
                else:
                    self.console.print("[red]Invalid selection. Please try again.[/red]")
            except (ValueError, KeyboardInterrupt):
                self.console.print("[red]Invalid input. Please enter a number.[/red]")
    
    def ask_text(self, question: str, default: Optional[str] = None, 
                 required: bool = False, validator: Optional[Callable] = None) -> Optional[str]:
        """Ask for text input with optional validation using Rich prompts"""
        while True:
            try:
                result = Prompt.ask(question, default=default)
                if required and not result.strip():
                    self.console.print("[red]This field is required[/red]")
                    continue
                if validator and not validator(result):
                    self.console.print("[red]Invalid input[/red]")
                    continue
                return result
            except KeyboardInterrupt:
                return None
    
    def ask_password(self, question: str, required: bool = False) -> Optional[str]:
        """Ask for password input (hidden) using modern secret interface"""
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
    
    def ask_integer(self, question: str, default: Optional[int] = None,
                    min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
        """Ask for integer input with range validation using modern number interface"""
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
    
    def ask_boolean(self, question: str, default: bool = False) -> bool:
        """Ask for yes/no confirmation using modern confirm interface"""
        result = inquirer.confirm(
            message=question,
            default=default,
            style=self.inquirer_style,
            instruction="(y/n, default: {})".format('yes' if default else 'no')
        ).execute()
        
        return result
    
    def ask_path(self, question: str, default: Optional[str] = None,
                 must_exist: bool = False, only_directories: bool = False) -> Path:
        """Ask for file/directory path with validation using modern filepath interface"""
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
    
    def ask_url(self, question: str, default: Optional[str] = None) -> Optional[str]:
        """Ask for URL input with basic validation"""
        while True:
            answer = self.ask_text(question, default)
            
            if not answer:
                return None
            
            if not (answer.startswith('http://') or answer.startswith('https://')):
                self.console.print("[red]URL must start with http:// or https://[/red]")
                continue
            
            return answer
    
    def display_info(self, title: str, content: str, style: str = "blue") -> None:
        """Display information panel"""
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)
    
    def display_choices_table(self, title: str, choices: Dict[str, str]) -> None:
        """Display choices in a formatted table"""
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan", width=15)
        table.add_column("Description", style="white")
        
        for option, description in choices.items():
            table.add_row(option, description)
        
        self.console.print(table)


class ConfigurationWizard:
    """
    Interactive configuration wizard for LocalAgent setup
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.prompts = InteractivePrompts(console)
    
    async def run_setup(self) -> Optional[LocalAgentConfig]:
        """Run the complete configuration setup wizard"""
        self.console.print("\n[bold blue]🚀 LocalAgent Configuration Wizard[/bold blue]\n")
        
        self.prompts.display_info(
            "Welcome",
            "This wizard will help you set up LocalAgent for the first time.\n"
            "You can modify these settings later using the 'config' command."
        )
        
        try:
            # Basic configuration
            config_data = await self._setup_basic_config()
            
            # Provider configuration
            providers = await self._setup_providers()
            config_data['providers'] = providers
            
            # Orchestration configuration
            orchestration = await self._setup_orchestration()
            config_data['orchestration'] = orchestration
            
            # MCP configuration
            mcp = await self._setup_mcp()
            config_data['mcp'] = mcp
            
            # Plugin configuration
            plugins = await self._setup_plugins()
            config_data['plugins'] = plugins
            
            # Create and validate configuration
            config = LocalAgentConfig(**config_data)
            
            # Final review
            if await self._review_configuration(config):
                return config
            else:
                self.console.print("[yellow]Configuration setup cancelled.[/yellow]")
                return None
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Configuration setup cancelled by user.[/yellow]")
            return None
        except Exception as e:
            self.console.print(f"\n[red]Configuration setup failed: {e}[/red]")
            return None
    
    async def _setup_basic_config(self) -> Dict[str, Any]:
        """Setup basic configuration options"""
        self.console.rule("[bold]Basic Configuration[/bold]")
        
        config = {}
        
        # Config directory
        default_config_dir = Path.home() / ".localagent"
        self.console.print(f"Configuration will be stored in: [cyan]{default_config_dir}[/cyan]")
        
        config['config_dir'] = default_config_dir
        
        # Log level
        log_level_choices = {
            "INFO": "Standard logging (recommended)",
            "DEBUG": "Detailed logging for troubleshooting",
            "WARNING": "Only warnings and errors",
            "ERROR": "Only errors"
        }
        
        self.prompts.display_choices_table("Log Level Options", log_level_choices)
        log_level = self.prompts.ask_choice("Select log level", list(log_level_choices.keys()), "INFO")
        config['log_level'] = log_level
        
        # Debug mode
        config['debug_mode'] = self.prompts.ask_boolean("Enable debug mode?", False)
        
        return config
    
    async def _setup_providers(self) -> Dict[str, ProviderConfig]:
        """Setup LLM provider configurations"""
        self.console.rule("[bold]LLM Provider Configuration[/bold]")
        
        providers = {}
        
        # Available providers info
        provider_info = {
            "ollama": "Local LLM provider (no API key required)",
            "openai": "OpenAI GPT models (requires API key)",
            "gemini": "Google Gemini models (requires API key)", 
            "perplexity": "Perplexity AI models (requires API key)"
        }
        
        self.prompts.display_choices_table("Available Providers", provider_info)
        
        # Always setup Ollama as it's the default
        self.console.print("\n[bold cyan]Setting up Ollama (default provider)...[/bold cyan]")
        ollama_config = await self._setup_ollama_provider()
        providers['ollama'] = ollama_config
        
        # Ask about other providers
        setup_others = self.prompts.ask_boolean(
            "Would you like to configure additional providers now?", False
        )
        
        if setup_others:
            for provider_name in ['openai', 'gemini', 'perplexity']:
                setup_provider = self.prompts.ask_boolean(
                    f"Configure {provider_name}?", False
                )
                
                if setup_provider:
                    provider_config = await self._setup_api_provider(provider_name)
                    if provider_config:
                        providers[provider_name] = provider_config
        
        return providers
    
    async def _setup_ollama_provider(self) -> ProviderConfig:
        """Setup Ollama provider configuration"""
        base_url = self.prompts.ask_url(
            "Ollama base URL", 
            "http://localhost:11434"
        )
        
        default_model = self.prompts.ask_text(
            "Default model (leave empty for auto-detection)",
            None
        )
        
        timeout = self.prompts.ask_integer(
            "Request timeout (seconds)",
            120,
            min_val=10,
            max_val=600
        )
        
        return ProviderConfig(
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
            enabled=True
        )
    
    async def _setup_api_provider(self, provider_name: str) -> Optional[ProviderConfig]:
        """Setup API-based provider configuration"""
        self.console.print(f"\n[bold cyan]Setting up {provider_name}...[/bold cyan]")
        
        # API Key
        api_key = self.prompts.ask_password(
            f"{provider_name.title()} API key", 
            required=True
        )
        
        if not api_key:
            self.console.print(f"[yellow]Skipping {provider_name} setup (no API key provided)[/yellow]")
            return None
        
        # Base URL (optional for some providers)
        base_url = None
        if provider_name in ['openai', 'perplexity']:
            custom_url = self.prompts.ask_boolean(
                f"Use custom base URL for {provider_name}?", False
            )
            
            if custom_url:
                base_url = self.prompts.ask_url(
                    f"{provider_name.title()} base URL",
                    None
                )
        
        # Default model
        default_models = {
            'openai': 'gpt-4',
            'gemini': 'gemini-pro',
            'perplexity': 'llama-3-sonar-large-32k-online'
        }
        
        default_model = self.prompts.ask_text(
            f"Default model for {provider_name}",
            default_models.get(provider_name)
        )
        
        # Rate limiting
        rate_limit = None
        setup_rate_limit = self.prompts.ask_boolean(
            f"Set up rate limiting for {provider_name}?", False
        )
        
        if setup_rate_limit:
            rate_limit = self.prompts.ask_integer(
                "Requests per minute",
                60,
                min_val=1,
                max_val=1000
            )
        
        return ProviderConfig(
            base_url=base_url,
            api_key=api_key,
            default_model=default_model,
            rate_limit=rate_limit,
            timeout=120,
            enabled=True
        )
    
    async def _setup_orchestration(self) -> OrchestrationConfig:
        """Setup orchestration configuration"""
        self.console.rule("[bold]Orchestration Configuration[/bold]")
        
        self.prompts.display_info(
            "Orchestration Settings",
            "These settings control how LocalAgent manages workflow execution and agent coordination."
        )
        
        max_parallel_agents = self.prompts.ask_integer(
            "Maximum parallel agents",
            10,
            min_val=1,
            max_val=50
        )
        
        max_workflow_iterations = self.prompts.ask_integer(
            "Maximum workflow iterations (for error recovery)",
            3,
            min_val=1,
            max_val=10
        )
        
        enable_evidence_collection = self.prompts.ask_boolean(
            "Enable evidence collection for debugging?", True
        )
        
        enable_cross_session_continuity = self.prompts.ask_boolean(
            "Enable cross-session continuity?", True
        )
        
        default_timeout = self.prompts.ask_integer(
            "Default operation timeout (seconds)",
            300,
            min_val=30,
            max_val=3600
        )
        
        return OrchestrationConfig(
            max_parallel_agents=max_parallel_agents,
            max_workflow_iterations=max_workflow_iterations,
            enable_evidence_collection=enable_evidence_collection,
            enable_cross_session_continuity=enable_cross_session_continuity,
            default_timeout=default_timeout
        )
    
    async def _setup_mcp(self) -> MCPConfig:
        """Setup MCP (Memory/Context/Protocol) configuration"""
        self.console.rule("[bold]MCP Configuration[/bold]")
        
        self.prompts.display_info(
            "MCP (Memory/Context/Protocol)",
            "MCP manages memory, context, and communication between agents.\n"
            "It uses Redis for storage and coordination."
        )
        
        redis_url = self.prompts.ask_text(
            "Redis URL",
            "redis://localhost:6379"
        )
        
        memory_retention_days = self.prompts.ask_integer(
            "Memory retention period (days)",
            7,
            min_val=1,
            max_val=365
        )
        
        enable_timeline = self.prompts.ask_boolean(
            "Enable timeline tracking?", True
        )
        
        enable_context_compression = self.prompts.ask_boolean(
            "Enable context compression?", True
        )
        
        return MCPConfig(
            redis_url=redis_url,
            memory_retention_days=memory_retention_days,
            enable_timeline=enable_timeline,
            enable_context_compression=enable_context_compression
        )
    
    async def _setup_plugins(self) -> PluginConfig:
        """Setup plugin configuration"""
        self.console.rule("[bold]Plugin Configuration[/bold]")
        
        self.prompts.display_info(
            "Plugin System",
            "LocalAgent supports plugins to extend functionality.\n"
            "Plugins can add new commands, providers, UI components, and workflow phases."
        )
        
        auto_load_plugins = self.prompts.ask_boolean(
            "Auto-load enabled plugins on startup?", True
        )
        
        allow_dev_plugins = self.prompts.ask_boolean(
            "Allow loading development plugins from directories?", False
        )
        
        # Plugin directories
        default_plugin_dir = Path.home() / ".localagent" / "plugins"
        plugin_directories = [str(default_plugin_dir)]
        
        add_more_dirs = self.prompts.ask_boolean(
            f"Add additional plugin directories? (default: {default_plugin_dir})", False
        )
        
        if add_more_dirs:
            while True:
                additional_dir = self.prompts.ask_path(
                    "Additional plugin directory (or press Enter to finish)",
                    None
                )
                
                if additional_dir:
                    plugin_directories.append(str(additional_dir))
                else:
                    break
        
        return PluginConfig(
            enabled_plugins=[],  # Will be populated as plugins are installed
            auto_load_plugins=auto_load_plugins,
            plugin_directories=plugin_directories,
            allow_dev_plugins=allow_dev_plugins
        )
    
    async def _review_configuration(self, config: LocalAgentConfig) -> bool:
        """Review and confirm configuration before saving"""
        self.console.rule("[bold]Configuration Review[/bold]")
        
        # Display summary
        summary_table = Table(title="Configuration Summary", show_header=True, header_style="bold magenta")
        summary_table.add_column("Setting", style="cyan", width=25)
        summary_table.add_column("Value", style="white")
        
        # Basic settings
        summary_table.add_row("Config Directory", str(config.config_dir))
        summary_table.add_row("Log Level", config.log_level)
        summary_table.add_row("Debug Mode", "✓" if config.debug_mode else "✗")
        
        # Providers
        enabled_providers = ", ".join(config.get_enabled_providers())
        summary_table.add_row("Enabled Providers", enabled_providers)
        summary_table.add_row("Default Provider", config.default_provider)
        
        # Orchestration
        summary_table.add_row("Max Parallel Agents", str(config.orchestration.max_parallel_agents))
        summary_table.add_row("Max Iterations", str(config.orchestration.max_workflow_iterations))
        
        # MCP
        summary_table.add_row("Redis URL", config.mcp.redis_url)
        summary_table.add_row("Memory Retention", f"{config.mcp.memory_retention_days} days")
        
        # Plugins
        summary_table.add_row("Auto-load Plugins", "✓" if config.plugins.auto_load_plugins else "✗")
        summary_table.add_row("Allow Dev Plugins", "✓" if config.plugins.allow_dev_plugins else "✗")
        
        self.console.print(summary_table)
        
        # Confirmation
        return self.prompts.ask_boolean(
            "\nSave this configuration?", True
        )


class ProviderConfigurationWizard:
    """
    Specialized wizard for configuring LLM providers
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.prompts = InteractivePrompts(console)
    
    async def configure_provider(self, provider_name: str) -> Optional[ProviderConfig]:
        """Configure a specific provider interactively"""
        self.console.print(f"\n[bold blue]Configuring {provider_name} Provider[/bold blue]\n")
        
        if provider_name == 'ollama':
            return await self._configure_ollama()
        elif provider_name in ['openai', 'gemini', 'perplexity']:
            return await self._configure_api_provider(provider_name)
        else:
            self.console.print(f"[red]Unknown provider: {provider_name}[/red]")
            return None
    
    async def _configure_ollama(self) -> ProviderConfig:
        """Configure Ollama provider"""
        self.prompts.display_info(
            "Ollama Configuration",
            "Ollama runs local LLM models and doesn't require an API key.\n"
            "Make sure Ollama is installed and running on your system."
        )
        
        base_url = self.prompts.ask_url(
            "Ollama base URL",
            "http://localhost:11434"
        )
        
        # Test connection
        test_connection = self.prompts.ask_boolean(
            "Test connection to Ollama?", True
        )
        
        if test_connection:
            # This would integrate with actual provider testing
            self.console.print("[yellow]Connection test would be performed here...[/yellow]")
        
        default_model = self.prompts.ask_text(
            "Default model (leave empty for auto-detection)",
            None
        )
        
        timeout = self.prompts.ask_integer(
            "Request timeout (seconds)",
            120,
            min_val=10,
            max_val=600
        )
        
        return ProviderConfig(
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
            enabled=True
        )
    
    async def _configure_api_provider(self, provider_name: str) -> Optional[ProviderConfig]:
        """Configure API-based provider"""
        provider_info = {
            'openai': {
                'name': 'OpenAI',
                'description': 'Access to GPT models including GPT-4',
                'api_docs': 'https://platform.openai.com/docs',
                'default_model': 'gpt-4'
            },
            'gemini': {
                'name': 'Google Gemini', 
                'description': 'Google\'s advanced AI models',
                'api_docs': 'https://ai.google.dev/docs',
                'default_model': 'gemini-pro'
            },
            'perplexity': {
                'name': 'Perplexity AI',
                'description': 'AI models with web search capabilities',
                'api_docs': 'https://docs.perplexity.ai',
                'default_model': 'llama-3-sonar-large-32k-online'
            }
        }
        
        info = provider_info.get(provider_name, {})
        
        self.prompts.display_info(
            f"{info.get('name', provider_name)} Configuration",
            f"{info.get('description', '')}\n\n"
            f"API Documentation: {info.get('api_docs', 'N/A')}\n\n"
            "You'll need an API key from the provider to use this service."
        )
        
        # API Key
        api_key = self.prompts.ask_password(
            f"{info.get('name', provider_name)} API key",
            required=True
        )
        
        if not api_key:
            self.console.print("[yellow]Configuration cancelled (no API key provided)[/yellow]")
            return None
        
        # Base URL (optional for some providers)
        base_url = None
        if provider_name in ['openai', 'perplexity']:
            custom_url = self.prompts.ask_boolean(
                f"Use custom base URL for {info.get('name', provider_name)}?", False
            )
            
            if custom_url:
                base_url = self.prompts.ask_url(
                    f"{info.get('name', provider_name)} base URL",
                    None
                )
        
        # Default model
        default_model = self.prompts.ask_text(
            f"Default model",
            info.get('default_model')
        )
        
        # Advanced settings
        setup_advanced = self.prompts.ask_boolean(
            "Configure advanced settings?", False
        )
        
        timeout = 120
        rate_limit = None
        
        if setup_advanced:
            timeout = self.prompts.ask_integer(
                "Request timeout (seconds)",
                120,
                min_val=10,
                max_val=600
            )
            
            setup_rate_limit = self.prompts.ask_boolean(
                "Set up rate limiting?", False
            )
            
            if setup_rate_limit:
                rate_limit = self.prompts.ask_integer(
                    "Requests per minute",
                    60,
                    min_val=1,
                    max_val=1000
                )
        
        return ProviderConfig(
            base_url=base_url,
            api_key=api_key,
            default_model=default_model,
            timeout=timeout,
            rate_limit=rate_limit,
            enabled=True
        )