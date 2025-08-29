#!/usr/bin/env python3
"""
LocalAgent Interactive CLI - Chat with Ollama models interactively
"""

import click
import requests
import json
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
import sys

console = Console()

def get_ollama_url():
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
                return url
        except:
            continue
    return None

def get_available_models():
    """Get list of available models from Ollama"""
    base_url = get_ollama_url()
    if not base_url:
        return []
    
    try:
        response = requests.get(f"{base_url}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [m['name'] for m in models]
    except:
        pass
    return []

def chat_with_model(model, prompt):
    """Send a chat request to Ollama"""
    base_url = get_ollama_url()
    if not base_url:
        return "Error: Could not connect to Ollama"
    
    try:
        response = requests.post(f"{base_url}/api/generate", 
            json={
                "model": model,
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

@click.command()
@click.option('--model', '-m', help='Model to use (default: auto-detect)')
def interactive_chat(model=None):
    """Start an interactive chat session with Ollama"""
    
    # Welcome message
    console.print(Panel.fit(
        "[bold cyan]🤖 LocalAgent Interactive CLI[/bold cyan]\n"
        "[dim]Chat with local LLM models powered by Ollama[/dim]",
        border_style="cyan"
    ))
    
    # Get available models
    models = get_available_models()
    
    if not models:
        console.print("[red]❌ No models installed. Please run:[/red]")
        console.print("[yellow]docker exec localagent-ollama ollama pull tinyllama:latest[/yellow]")
        sys.exit(1)
    
    # Select model
    if not model:
        if len(models) == 1:
            model = models[0]
            console.print(f"[green]Using model: {model}[/green]\n")
        else:
            console.print("[cyan]Available models:[/cyan]")
            for i, m in enumerate(models, 1):
                console.print(f"  {i}. {m}")
            
            choice = Prompt.ask(
                "Select a model",
                choices=[str(i) for i in range(1, len(models)+1)],
                default="1"
            )
            model = models[int(choice)-1]
            console.print(f"[green]Selected: {model}[/green]\n")
    
    # Instructions
    console.print("[dim]Type 'exit', 'quit', or 'bye' to end the session[/dim]")
    console.print("[dim]Type 'clear' to clear the screen[/dim]")
    console.print("[dim]Type 'model' to switch models[/dim]\n")
    
    # Chat loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("[bold blue]You[/bold blue]")
            
            # Handle special commands
            if user_input.lower() in ['exit', 'quit', 'bye']:
                console.print("\n[cyan]👋 Goodbye![/cyan]")
                break
            
            if user_input.lower() == 'clear':
                console.clear()
                continue
            
            if user_input.lower() == 'model':
                console.print("[cyan]Available models:[/cyan]")
                for i, m in enumerate(models, 1):
                    console.print(f"  {i}. {m}")
                choice = Prompt.ask("Select a model", default="1")
                model = models[int(choice)-1] if choice.isdigit() else models[0]
                console.print(f"[green]Switched to: {model}[/green]\n")
                continue
            
            # Show thinking indicator
            with console.status("[dim]Thinking...[/dim]", spinner="dots"):
                response = chat_with_model(model, user_input)
            
            # Display response
            console.print("\n[bold green]Assistant:[/bold green]")
            console.print(Panel(
                Markdown(response),
                border_style="green",
                padding=(1, 2)
            ))
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n\n[cyan]👋 Interrupted. Goodbye![/cyan]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")

def main():
    """Main entry point for console script"""
    interactive_chat()

if __name__ == '__main__':
    interactive_chat()