#!/usr/bin/env python3
"""
LocalAgent Full Interactive CLI - Fixed version with proper initialization
"""

import click
import requests
import json
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console()

class FixedInteractiveCLI:
    """Fixed interactive CLI with proper async initialization"""
    
    def __init__(self):
        self.console = console
        self.ollama_url = None
        self.current_model = None
        self.config = None
        self.workflow_engine = None
        self.context_manager = None
        self.search_manager = None
        self.file_ops_manager = None
        self.initialized = False
        
    def get_ollama_url(self):
        """Try to find a working Ollama instance"""
        urls = [
            "http://alienware.local:11434",
            "http://localhost:11434", 
            "http://ollama:11434"
        ]
        
        for url in urls:
            try:
                response = requests.get(f"{url}/api/tags", timeout=2)
                if response.status_code == 200:
                    self.console.print(f"[green]✓ Connected to Ollama at {url}[/green]")
                    return url
            except:
                continue
        return None
        
    def get_available_models(self):
        """Get list of available models from Ollama"""
        if not self.ollama_url:
            return []
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m['name'] for m in models]
        except:
            pass
        return []
        
    async def lazy_initialize(self):
        """Lazy initialization of heavy components"""
        try:
            # Only import what we need when we need it
            from app.cli.core.config import ConfigurationManager
            
            # Initialize configuration
            self.console.print("[dim]Loading configuration...[/dim]")
            config_manager = ConfigurationManager()
            self.config = await config_manager.load_configuration()
            
            # Try to initialize workflow components (optional)
            try:
                from app.orchestration.workflow_engine import WorkflowEngine
                from app.orchestration.context_manager import ContextManager
                
                self.workflow_engine = WorkflowEngine()
                # Convert config to dict for ContextManager
                config_dict = self.config.model_dump() if hasattr(self.config, 'model_dump') else self.config.dict()
                self.context_manager = ContextManager(config_dict)
                self.console.print("[green]✓ Workflow engine initialized[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Workflow engine not available: {e}[/yellow]")
                
            # Try to initialize tools (optional)
            try:
                from app.cli.tools.search import SearchManager
                from app.cli.tools.file_ops import FileOperationsManager
                
                self.search_manager = SearchManager(self.console)
                self.file_ops_manager = FileOperationsManager(self.console)
                self.console.print("[green]✓ Tools initialized[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Tools not available: {e}[/yellow]")
                
            self.initialized = True
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error during initialization: {e}[/red]")
            return False
            
    async def process_with_workflow(self, prompt: str):
        """Process prompt through workflow engine if available"""
        if not self.workflow_engine:
            return "Workflow engine not available. Use basic chat instead."
            
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Executing workflow...", total=1)
                
                # Simple workflow execution stub
                await asyncio.sleep(1)  # Simulate work
                progress.update(task, completed=1)
                
            return "Workflow execution completed (stub implementation)"
        except Exception as e:
            return f"Workflow error: {str(e)}"
            
    async def process_with_tools(self, prompt: str):
        """Process prompt to detect and execute tool commands"""
        prompt_lower = prompt.lower()
        
        # Search commands
        if any(cmd in prompt_lower for cmd in ['search', 'find', 'grep', 'locate']):
            if self.search_manager:
                self.console.print("[cyan]Starting search interface...[/cyan]")
                try:
                    await self.search_manager.interactive_search()
                    return "Search completed"
                except Exception as e:
                    return f"Search error: {str(e)}"
            else:
                return "Search tools not available"
                
        # File operations
        if any(cmd in prompt_lower for cmd in ['create file', 'edit file', 'delete file']):
            if self.file_ops_manager:
                self.console.print("[cyan]Starting file operations...[/cyan]")
                try:
                    await self.file_ops_manager.interactive_operations()
                    return "File operation completed"
                except Exception as e:
                    return f"File operation error: {str(e)}"
            else:
                return "File tools not available"
                
        return None
        
    def chat_with_model(self, prompt: str):
        """Send a chat request to Ollama"""
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", 
                json={
                    "model": self.current_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get('response', 'No response')
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    def show_help(self):
        """Show available commands and features"""
        help_table = Table(title="Available Commands & Features", show_header=True)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")
        help_table.add_column("Status", style="green")
        
        commands = [
            ("search [query]", "Search files and content", "✓" if self.search_manager else "✗"),
            ("find [pattern]", "Find files by pattern", "✓" if self.search_manager else "✗"),
            ("create file", "Create new file", "✓" if self.file_ops_manager else "✗"),
            ("edit file", "Edit existing file", "✓" if self.file_ops_manager else "✗"),
            ("workflow [task]", "Execute workflow", "✓" if self.workflow_engine else "✗"),
            ("init", "Initialize advanced features", "✓" if self.initialized else "✗"),
            ("model", "Switch AI model", "✓"),
            ("config", "Show configuration", "✓" if self.config else "✗"),
            ("clear", "Clear screen", "✓"),
            ("help", "Show this help", "✓"),
            ("exit/quit/bye", "Exit the CLI", "✓")
        ]
        
        for cmd, desc, status in commands:
            help_table.add_row(cmd, desc, status)
            
        self.console.print(help_table)
        
    async def run(self):
        """Main interactive loop"""
        # Welcome message
        self.console.print(Panel.fit(
            "[bold cyan]🤖 LocalAgent Interactive CLI (Fixed)[/bold cyan]\n"
            "[dim]Chat with optional orchestration and tools[/dim]",
            border_style="cyan"
        ))
        
        # Find Ollama
        self.ollama_url = self.get_ollama_url()
        if not self.ollama_url:
            self.console.print("[red]❌ Could not connect to Ollama[/red]")
            self.console.print("[yellow]Make sure Ollama is running:[/yellow]")
            self.console.print("[yellow]docker-compose up -d[/yellow]")
            sys.exit(1)
            
        # Get available models
        models = self.get_available_models()
        
        if not models:
            self.console.print("[red]❌ No models installed. Please run:[/red]")
            self.console.print("[yellow]docker exec localagent-ollama ollama pull tinyllama:latest[/yellow]")
            sys.exit(1)
            
        # Select model
        if len(models) == 1:
            self.current_model = models[0]
            self.console.print(f"[green]Using model: {self.current_model}[/green]\n")
        else:
            self.console.print("[cyan]Available models:[/cyan]")
            for i, m in enumerate(models, 1):
                self.console.print(f"  {i}. {m}")
                
            choice = Prompt.ask(
                "Select a model",
                choices=[str(i) for i in range(1, len(models)+1)],
                default="1"
            )
            self.current_model = models[int(choice)-1]
            self.console.print(f"[green]Selected: {self.current_model}[/green]\n")
            
        # Instructions
        self.console.print("[dim]Type 'help' to see available commands[/dim]")
        self.console.print("[dim]Type 'init' to initialize advanced features[/dim]")
        self.console.print("[dim]Type 'exit', 'quit', or 'bye' to end the session[/dim]\n")
        
        # Chat loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("[bold blue]You[/bold blue]")
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    self.console.print("\n[cyan]👋 Goodbye![/cyan]")
                    break
                    
                if user_input.lower() == 'clear':
                    self.console.clear()
                    continue
                    
                if user_input.lower() == 'help':
                    self.show_help()
                    continue
                    
                if user_input.lower() == 'init':
                    self.console.print("[cyan]Initializing advanced features...[/cyan]")
                    success = await self.lazy_initialize()
                    if success:
                        self.console.print("[green]✓ Advanced features ready![/green]")
                    else:
                        self.console.print("[yellow]Some features may not be available[/yellow]")
                    continue
                    
                if user_input.lower() == 'config':
                    if self.config:
                        self.console.print(Panel(
                            json.dumps(self.config.model_dump() if hasattr(self.config, 'model_dump') else {}, indent=2),
                            title="Current Configuration",
                            border_style="green"
                        ))
                    else:
                        self.console.print("[yellow]Configuration not loaded. Type 'init' first.[/yellow]")
                    continue
                    
                if user_input.lower() == 'model':
                    self.console.print("[cyan]Available models:[/cyan]")
                    for i, m in enumerate(models, 1):
                        self.console.print(f"  {i}. {m}")
                    choice = Prompt.ask("Select a model", default="1")
                    self.current_model = models[int(choice)-1] if choice.isdigit() else models[0]
                    self.console.print(f"[green]Switched to: {self.current_model}[/green]\n")
                    continue
                    
                # Check for tool commands if initialized
                if self.initialized:
                    tool_result = await self.process_with_tools(user_input)
                    if tool_result:
                        self.console.print(f"\n[green]{tool_result}[/green]\n")
                        continue
                        
                    # Check for workflow activation
                    if "workflow" in user_input.lower():
                        result = await self.process_with_workflow(user_input)
                        self.console.print(f"\n[green]{result}[/green]\n")
                        continue
                        
                # Standard chat
                with self.console.status("[dim]Thinking...[/dim]", spinner="dots"):
                    response = self.chat_with_model(user_input)
                    
                # Display response
                self.console.print("\n[bold green]Assistant:[/bold green]")
                self.console.print(Panel(
                    Markdown(response) if isinstance(response, str) else str(response),
                    border_style="green",
                    padding=(1, 2)
                ))
                self.console.print()
                
            except KeyboardInterrupt:
                self.console.print("\n\n[cyan]👋 Interrupted. Goodbye![/cyan]")
                break
            except Exception as e:
                self.console.print(f"\n[red]Error: {e}[/red]\n")

@click.command()
@click.option('--model', '-m', help='Model to use (default: auto-detect)')
def interactive_fixed(model=None):
    """Start a fixed interactive chat session with optional features"""
    cli = FixedInteractiveCLI()
    if model:
        cli.current_model = model
    asyncio.run(cli.run())

def main():
    """Main entry point for console script"""
    interactive_fixed()

if __name__ == '__main__':
    interactive_fixed()