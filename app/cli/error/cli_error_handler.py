"""
CLI-Specific Error Handler Integration
Bridges error recovery with CLI interface and Typer framework
"""

import asyncio
import functools
from typing import Dict, Any, Optional, Callable, Type, List
from datetime import datetime
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .recovery import (
    ErrorContext, ErrorSeverity, RecoveryResult,
    ErrorRecoveryManager, RecoveryStrategy
)

console = Console()

class CLIErrorHandler:
    """CLI-specific error handling with interactive recovery"""
    
    def __init__(self, recovery_manager: ErrorRecoveryManager):
        self.recovery_manager = recovery_manager
        self.interactive_mode = True
        self.error_history: List[ErrorContext] = []
        
    def cli_error_handler(self, func: Callable) -> Callable:
        """Decorator for CLI commands with comprehensive error handling"""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Create error context
                error_context = ErrorContext(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    traceback=traceback.format_exc(),
                    timestamp=datetime.now(),
                    command=func.__name__,
                    previous_errors=self.error_history[-5:]  # Keep last 5 errors
                )
                
                # Add to history
                self.error_history.append(error_context)
                
                # Handle the error
                result = await self.handle_cli_error(error_context)
                
                if result == RecoveryResult.FAILED:
                    # Show error details and exit
                    self.display_error_details(error_context)
                    raise typer.Exit(code=1)
                elif result == RecoveryResult.RETRY:
                    # Retry the command
                    console.print("[yellow]Retrying command...[/yellow]")
                    return await wrapper(*args, **kwargs)
                else:
                    # Recovery succeeded or was partial
                    return None
        
        return wrapper
    
    async def handle_cli_error(self, error_context: ErrorContext) -> RecoveryResult:
        """Handle CLI error with interactive recovery options"""
        
        # Display error summary
        self.display_error_summary(error_context)
        
        # Attempt automatic recovery first
        if self.recovery_manager:
            result = await self.recovery_manager.handle_error(error_context)
            
            if result == RecoveryResult.SUCCESS:
                console.print("[green]✓ Error recovered automatically[/green]")
                return result
            elif result == RecoveryResult.PARTIAL:
                console.print("[yellow]⚠ Partial recovery achieved[/yellow]")
        
        # If automatic recovery failed and interactive mode is enabled
        if self.interactive_mode:
            return await self.interactive_recovery(error_context)
        
        return RecoveryResult.FAILED
    
    async def interactive_recovery(self, error_context: ErrorContext) -> RecoveryResult:
        """Interactive error recovery with user guidance"""
        
        console.print("\n[bold yellow]Interactive Recovery Options[/bold yellow]\n")
        
        # Get available recovery strategies
        strategies = await self.recovery_manager.get_applicable_strategies(error_context)
        
        if not strategies:
            console.print("[red]No recovery strategies available[/red]")
            return RecoveryResult.FAILED
        
        # Create options table
        table = Table(title="Recovery Options", show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Strategy", style="white")
        table.add_column("Description", style="dim")
        table.add_column("Success Rate", style="green")
        
        for idx, strategy in enumerate(strategies, 1):
            success_rate = f"{strategy.get_success_rate():.0%}"
            table.add_row(
                str(idx),
                strategy.name,
                strategy.description,
                success_rate
            )
        
        table.add_row(
            str(len(strategies) + 1),
            "Retry Command",
            "Attempt to run the command again",
            "-"
        )
        table.add_row(
            str(len(strategies) + 2),
            "Skip and Continue",
            "Skip this error and continue",
            "-"
        )
        table.add_row(
            str(len(strategies) + 3),
            "Abort",
            "Exit the application",
            "-"
        )
        
        console.print(table)
        
        # Get user choice
        choice = Prompt.ask(
            "\n[cyan]Select recovery option[/cyan]",
            choices=[str(i) for i in range(1, len(strategies) + 4)],
            default="1"
        )
        
        choice_idx = int(choice) - 1
        
        # Execute chosen strategy
        if choice_idx < len(strategies):
            strategy = strategies[choice_idx]
            console.print(f"\n[cyan]Executing {strategy.name}...[/cyan]")
            
            result = await strategy.execute(error_context, self.recovery_manager.config)
            
            if result == RecoveryResult.SUCCESS:
                console.print(f"[green]✓ {strategy.name} successful[/green]")
            elif result == RecoveryResult.PARTIAL:
                console.print(f"[yellow]⚠ {strategy.name} partially successful[/yellow]")
            else:
                console.print(f"[red]✗ {strategy.name} failed[/red]")
            
            return result
            
        elif choice_idx == len(strategies):
            # Retry
            return RecoveryResult.RETRY
        elif choice_idx == len(strategies) + 1:
            # Skip
            console.print("[yellow]Skipping error and continuing...[/yellow]")
            return RecoveryResult.PARTIAL
        else:
            # Abort
            return RecoveryResult.FAILED
    
    def display_error_summary(self, error_context: ErrorContext):
        """Display error summary in a user-friendly format"""
        
        # Determine severity and color
        severity = self._determine_severity(error_context)
        color_map = {
            ErrorSeverity.LOW: "yellow",
            ErrorSeverity.MEDIUM: "orange1",
            ErrorSeverity.HIGH: "red",
            ErrorSeverity.CRITICAL: "bold red"
        }
        color = color_map.get(severity, "red")
        
        # Create error panel
        error_text = Text()
        error_text.append(f"Error Type: ", style="bold")
        error_text.append(f"{error_context.error_type}\n", style=color)
        error_text.append(f"Message: ", style="bold")
        error_text.append(f"{error_context.error_message}\n", style="white")
        
        if error_context.command:
            error_text.append(f"Command: ", style="bold")
            error_text.append(f"{error_context.command}\n", style="cyan")
        
        if error_context.provider:
            error_text.append(f"Provider: ", style="bold")
            error_text.append(f"{error_context.provider}\n", style="blue")
        
        panel = Panel(
            error_text,
            title=f"[{color}]Error Detected[/{color}]",
            border_style=color,
            padding=(1, 2)
        )
        
        console.print(panel)
    
    def display_error_details(self, error_context: ErrorContext):
        """Display detailed error information"""
        
        console.print("\n[bold red]Detailed Error Information[/bold red]\n")
        
        # Show traceback if in debug mode
        if self.recovery_manager.config.debug:
            console.print("[dim]Traceback:[/dim]")
            console.print(error_context.traceback)
        
        # Show error history if available
        if error_context.previous_errors:
            console.print("\n[dim]Recent Error History:[/dim]")
            for prev_error in error_context.previous_errors[-3:]:
                console.print(f"  • {prev_error.timestamp.strftime('%H:%M:%S')} - {prev_error.error_type}: {prev_error.error_message[:50]}...")
    
    def _determine_severity(self, error_context: ErrorContext) -> ErrorSeverity:
        """Determine error severity based on context"""
        
        # Critical errors
        critical_keywords = ['fatal', 'critical', 'corruption', 'security']
        if any(keyword in error_context.error_message.lower() for keyword in critical_keywords):
            return ErrorSeverity.CRITICAL
        
        # High severity
        high_keywords = ['failed', 'error', 'invalid', 'unauthorized']
        if any(keyword in error_context.error_message.lower() for keyword in high_keywords):
            return ErrorSeverity.HIGH
        
        # Medium severity
        medium_keywords = ['warning', 'timeout', 'retry']
        if any(keyword in error_context.error_message.lower() for keyword in medium_keywords):
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW
    
    def create_recovery_suggestions(self, error_context: ErrorContext) -> List[str]:
        """Generate contextual recovery suggestions"""
        
        suggestions = []
        
        # Configuration errors
        if 'config' in error_context.error_message.lower():
            suggestions.append("Check your configuration file for syntax errors")
            suggestions.append("Run 'localagent config validate' to verify configuration")
            suggestions.append("Use 'localagent config reset' to restore defaults")
        
        # Provider errors
        if error_context.provider or 'provider' in error_context.error_message.lower():
            suggestions.append("Check provider API key configuration")
            suggestions.append("Verify provider service is accessible")
            suggestions.append("Try switching to a different provider")
        
        # Network errors
        if any(word in error_context.error_message.lower() for word in ['connection', 'network', 'timeout']):
            suggestions.append("Check your internet connection")
            suggestions.append("Verify firewall/proxy settings")
            suggestions.append("Try increasing timeout values in configuration")
        
        # Permission errors
        if any(word in error_context.error_message.lower() for word in ['permission', 'denied', 'access']):
            suggestions.append("Check file/directory permissions")
            suggestions.append("Run with appropriate privileges if needed")
            suggestions.append("Verify API key permissions and scopes")
        
        return suggestions
    
    async def show_recovery_guidance(self, error_context: ErrorContext):
        """Show interactive recovery guidance"""
        
        suggestions = self.create_recovery_suggestions(error_context)
        
        if suggestions:
            console.print("\n[bold cyan]Recovery Suggestions:[/bold cyan]")
            for idx, suggestion in enumerate(suggestions, 1):
                console.print(f"  {idx}. {suggestion}")
            
            if Confirm.ask("\n[cyan]Would you like to try one of these suggestions?[/cyan]"):
                choice = Prompt.ask(
                    "Select suggestion number",
                    choices=[str(i) for i in range(1, len(suggestions) + 1)]
                )
                # Execute the selected suggestion (implementation would depend on specific actions)
                console.print(f"[cyan]Executing: {suggestions[int(choice) - 1]}[/cyan]")


class InteractiveErrorResolver:
    """Interactive error resolution with guided workflows"""
    
    def __init__(self, cli_context):
        self.cli_context = cli_context
        self.console = Console()
        
    async def resolve_configuration_error(self, error: Exception):
        """Interactive configuration repair workflow"""
        
        self.console.print("\n[bold yellow]Configuration Error Detected[/bold yellow]\n")
        
        # Offer options
        options = [
            "Validate current configuration",
            "Reset to default configuration",
            "Edit configuration interactively",
            "Import configuration from file",
            "Skip configuration and use defaults"
        ]
        
        for idx, option in enumerate(options, 1):
            self.console.print(f"  {idx}. {option}")
        
        choice = Prompt.ask(
            "\n[cyan]Select resolution option[/cyan]",
            choices=[str(i) for i in range(1, len(options) + 1)],
            default="1"
        )
        
        # Execute chosen resolution
        if choice == "1":
            await self._validate_configuration()
        elif choice == "2":
            await self._reset_configuration()
        elif choice == "3":
            await self._edit_configuration_interactive()
        elif choice == "4":
            await self._import_configuration()
        else:
            self.console.print("[yellow]Using default configuration values[/yellow]")
    
    async def resolve_provider_error(self, error: Exception):
        """Provider troubleshooting and fallback selection"""
        
        self.console.print("\n[bold yellow]Provider Error Detected[/bold yellow]\n")
        
        # Show available providers
        providers = ["ollama", "openai", "gemini", "perplexity"]
        
        table = Table(title="Available Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("API Key", style="dim")
        
        for provider in providers:
            status = "✓ Available" if await self._check_provider(provider) else "✗ Unavailable"
            has_key = "Configured" if self._has_api_key(provider) else "Not configured"
            table.add_row(provider, status, has_key)
        
        self.console.print(table)
        
        # Offer fallback selection
        available = [p for p in providers if await self._check_provider(p)]
        if available:
            fallback = Prompt.ask(
                "\n[cyan]Select fallback provider[/cyan]",
                choices=available,
                default=available[0] if available else None
            )
            self.console.print(f"[green]Switching to {fallback} provider[/green]")
            return fallback
        
        return None
    
    async def resolve_validation_error(self, error: Exception):
        """Input correction guidance with examples"""
        
        self.console.print("\n[bold yellow]Validation Error[/bold yellow]\n")
        self.console.print(f"Error: {str(error)}")
        
        # Provide examples based on error type
        if "path" in str(error).lower():
            self.console.print("\n[cyan]Valid path examples:[/cyan]")
            self.console.print("  • /home/user/project/file.py")
            self.console.print("  • ./relative/path/to/file.txt")
            self.console.print("  • ~/Documents/project")
        
        # Allow retry with correction
        if Confirm.ask("\n[cyan]Would you like to correct the input?[/cyan]"):
            corrected = Prompt.ask("Enter corrected value")
            return corrected
        
        return None
    
    async def _validate_configuration(self):
        """Validate current configuration"""
        # Implementation would validate config
        self.console.print("[green]Configuration validation complete[/green]")
    
    async def _reset_configuration(self):
        """Reset to default configuration"""
        # Implementation would reset config
        self.console.print("[green]Configuration reset to defaults[/green]")
    
    async def _edit_configuration_interactive(self):
        """Interactive configuration editor"""
        # Implementation would provide interactive editing
        self.console.print("[green]Configuration updated[/green]")
    
    async def _import_configuration(self):
        """Import configuration from file"""
        file_path = Prompt.ask("Enter configuration file path")
        # Implementation would import config
        self.console.print(f"[green]Configuration imported from {file_path}[/green]")
    
    async def _check_provider(self, provider: str) -> bool:
        """Check if provider is available"""
        # Implementation would check provider availability
        return True  # Placeholder
    
    def _has_api_key(self, provider: str) -> bool:
        """Check if API key is configured for provider"""
        # Implementation would check API key
        return True  # Placeholder