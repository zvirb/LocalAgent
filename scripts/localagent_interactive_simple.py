#!/usr/bin/env python3
"""
LocalAgent Simplified Interactive CLI - Minimal dependencies version
"""

import click
import requests
import json
import sys
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table

console = Console()

class SimplifiedCLI:
    """Simplified interactive CLI with basic features"""
    
    def __init__(self):
        self.console = console
        self.ollama_url = None
        self.current_model = None
        
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
        """Show available commands"""
        help_table = Table(title="Available Commands", show_header=True)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")
        
        commands = [
            ("help", "Show this help"),
            ("model", "Switch AI model"),
            ("models", "List available models"),
            ("clear", "Clear screen"),
            ("exit/quit/bye", "Exit the CLI")
        ]
        
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
            
        self.console.print(help_table)
        
    def run(self):
        """Main interactive loop"""
        # Welcome message
        self.console.print(Panel.fit(
            "[bold cyan]🤖 LocalAgent Interactive CLI[/bold cyan]\n"
            "[dim]Simplified chat interface with Ollama[/dim]",
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
                    
                if user_input.lower() == 'models':
                    models = self.get_available_models()
                    self.console.print("[cyan]Available models:[/cyan]")
                    for m in models:
                        marker = "→" if m == self.current_model else " "
                        self.console.print(f"  {marker} {m}")
                    continue
                    
                if user_input.lower() == 'model':
                    models = self.get_available_models()
                    self.console.print("[cyan]Available models:[/cyan]")
                    for i, m in enumerate(models, 1):
                        self.console.print(f"  {i}. {m}")
                    choice = Prompt.ask("Select a model", default="1")
                    self.current_model = models[int(choice)-1] if choice.isdigit() else models[0]
                    self.console.print(f"[green]Switched to: {self.current_model}[/green]\n")
                    continue
                    
                # Show thinking indicator
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
def interactive_simple(model=None):
    """Start a simplified interactive chat session"""
    cli = SimplifiedCLI()
    if model:
        cli.current_model = model
    cli.run()

def main():
    """Main entry point for console script"""
    interactive_simple()

if __name__ == '__main__':
    interactive_simple()