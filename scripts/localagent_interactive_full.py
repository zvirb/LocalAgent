#!/usr/bin/env python3
"""
LocalAgent Full Interactive CLI - Chat with orchestration, agents, and tools
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
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.orchestration.workflow_engine import WorkflowEngine, WorkflowStatus
from app.orchestration.agent_adapter import AgentProviderAdapter, AgentRequest
from app.orchestration.context_manager import ContextManager
from app.orchestration.orchestration_integration import LocalAgentOrchestrator
from app.cli.core.config import ConfigurationManager
from app.cli.core.context import CLIContext
from app.cli.tools.search import SearchManager
from app.cli.tools.file_ops import FileOperationsManager
from app.llm_providers.ollama_provider import OllamaProvider

console = Console()

class InteractiveCLIOrchestrator:
    """Full-featured interactive CLI with workflow and tools"""
    
    def __init__(self):
        self.console = console
        self.workflow_engine = None
        self.agent_adapter = None
        self.context_manager = None
        self.config_manager = None
        self.search_manager = None
        self.file_ops_manager = None
        self.ollama_url = None
        self.current_model = None
        self.workflow_active = False
        
    async def initialize(self):
        """Initialize all components"""
        # Find Ollama
        self.ollama_url = self.get_ollama_url()
        if not self.ollama_url:
            self.console.print("[red]❌ Could not connect to Ollama[/red]")
            return False
            
        # Initialize configuration
        self.config_manager = ConfigurationManager()
        self.config = await self.config_manager.load_configuration()
        
        # Initialize workflow components
        self.workflow_engine = WorkflowEngine()
        self.agent_adapter = AgentProviderAdapter()
        self.context_manager = ContextManager(self.config.model_dump())
        
        # Initialize tools
        self.search_manager = SearchManager(self.console)
        self.file_ops_manager = FileOperationsManager(self.console)
        
        # Load workflow configuration
        workflow_config_path = Path("workflows/12-phase-workflow.yaml")
        if workflow_config_path.exists():
            await self.workflow_engine.load_workflow(str(workflow_config_path))
            
        self.console.print("[green]✓ All systems initialized[/green]")
        return True
        
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
        
    async def process_with_workflow(self, prompt: str):
        """Process prompt through workflow engine"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Executing workflow...", total=12)
            
            # Execute workflow
            execution = await self.workflow_engine.execute_workflow(
                task_description=prompt,
                provider_config={
                    "type": "ollama",
                    "base_url": self.ollama_url,
                    "model": self.current_model
                }
            )
            
            progress.update(task, completed=12)
            
        return execution
        
    async def process_with_tools(self, prompt: str):
        """Process prompt to detect and execute tool commands"""
        prompt_lower = prompt.lower()
        
        # Search commands
        if any(cmd in prompt_lower for cmd in ['search', 'find', 'grep', 'locate']):
            self.console.print("[cyan]Detected search request...[/cyan]")
            await self.search_manager.interactive_search()
            return "Search completed"
            
        # File operations
        if any(cmd in prompt_lower for cmd in ['create', 'edit', 'delete', 'move', 'copy']):
            self.console.print("[cyan]Detected file operation request...[/cyan]")
            await self.file_ops_manager.interactive_operations()
            return "File operation completed"
            
        return None
        
    async def chat_with_model(self, prompt: str):
        """Send a chat request to Ollama with tool detection"""
        # Check for tool commands first
        tool_result = await self.process_with_tools(prompt)
        if tool_result:
            return tool_result
            
        # Check for workflow activation
        if "workflow" in prompt.lower() or "orchestrate" in prompt.lower():
            self.console.print("[yellow]Activating workflow engine...[/yellow]")
            execution = await self.process_with_workflow(prompt)
            return f"Workflow completed: {execution.status}"
            
        # Standard chat
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
        
        commands = [
            ("search [query]", "Search files and content"),
            ("find [pattern]", "Find files by pattern"),
            ("create [file]", "Create new file"),
            ("edit [file]", "Edit existing file"),
            ("workflow [task]", "Execute 12-phase workflow"),
            ("orchestrate [task]", "Run orchestrated task"),
            ("model", "Switch AI model"),
            ("tools", "Show available tools"),
            ("config", "Show configuration"),
            ("clear", "Clear screen"),
            ("help", "Show this help"),
            ("exit/quit/bye", "Exit the CLI")
        ]
        
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
            
        self.console.print(help_table)
        
    async def run(self):
        """Main interactive loop"""
        # Welcome message
        self.console.print(Panel.fit(
            "[bold cyan]🤖 LocalAgent Full Interactive CLI[/bold cyan]\n"
            "[dim]Chat with orchestration, agents, and tools[/dim]",
            border_style="cyan"
        ))
        
        # Initialize
        if not await self.initialize():
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
                    
                if user_input.lower() == 'tools':
                    self.console.print("[cyan]Available tools:[/cyan]")
                    self.console.print("  • Search Manager - Advanced file and content search")
                    self.console.print("  • File Operations - Create, edit, delete files")
                    self.console.print("  • Workflow Engine - 12-phase orchestration")
                    self.console.print("  • Agent System - Multi-agent coordination")
                    continue
                    
                if user_input.lower() == 'config':
                    self.console.print(Panel(
                        json.dumps(self.config.model_dump(), indent=2),
                        title="Current Configuration",
                        border_style="green"
                    ))
                    continue
                    
                if user_input.lower() == 'model':
                    self.console.print("[cyan]Available models:[/cyan]")
                    for i, m in enumerate(models, 1):
                        self.console.print(f"  {i}. {m}")
                    choice = Prompt.ask("Select a model", default="1")
                    self.current_model = models[int(choice)-1] if choice.isdigit() else models[0]
                    self.console.print(f"[green]Switched to: {self.current_model}[/green]\n")
                    continue
                    
                # Show thinking indicator
                with self.console.status("[dim]Processing...[/dim]", spinner="dots"):
                    response = await self.chat_with_model(user_input)
                    
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
def interactive_chat_full(model=None):
    """Start a full-featured interactive chat session with orchestration and tools"""
    orchestrator = InteractiveCLIOrchestrator()
    if model:
        orchestrator.current_model = model
    asyncio.run(orchestrator.run())

def main():
    """Main entry point for console script"""
    interactive_chat_full()

if __name__ == '__main__':
    interactive_chat_full()