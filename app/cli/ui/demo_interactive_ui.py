#!/usr/bin/env python3
"""
Interactive UI Components Demo
Showcases the modern LocalAgent CLI interface with Claude theming
"""

import asyncio
import time
from typing import Dict, Any
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from .themes import showcase_theme, get_console
from .enhanced_prompts import create_modern_prompts, create_guided_wizard
from .display import create_display_manager, create_themed_console


async def demo_modern_prompts():
    """Demo modern interactive prompts"""
    console = get_console()
    prompts = create_modern_prompts(console)
    
    console.print("\n[bold blue]🎯 Modern Interactive Prompts Demo[/bold blue]\n")
    
    # Text input
    console.rule("Text Input")
    name = prompts.ask_text("What's your name?", default="LocalAgent User")
    console.print(f"Hello, [bold cyan]{name}[/bold cyan]!")
    
    # Choice selection
    console.rule("Choice Selection")
    favorite_color = prompts.ask_choice(
        "What's your favorite color?",
        ["red", "green", "blue", "purple", "orange"],
        default="blue"
    )
    console.print(f"Great choice! [bold {favorite_color}]{favorite_color.title()}[/bold {favorite_color}] is awesome!")
    
    # Multiple choice
    console.rule("Multiple Choice")
    hobbies = prompts.ask_multi_choice(
        "What are your hobbies?",
        ["coding", "reading", "gaming", "music", "sports", "cooking", "travel"],
        default=["coding"]
    )
    console.print(f"Your hobbies: {', '.join(hobbies)}")
    
    # Provider selection demo
    console.rule("Provider Selection")
    available_providers = ["ollama", "openai", "gemini", "claude", "perplexity"]
    selected_provider = prompts.ask_provider_selection(available_providers, "ollama")
    console.print(f"Selected provider: [bold cyan]{selected_provider}[/bold cyan]")
    
    # Model selection demo
    console.rule("Model Selection")
    models = {
        'ollama': ['llama2', 'codellama', 'mistral', 'phi', 'neural-chat'],
        'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
        'gemini': ['gemini-pro', 'gemini-pro-vision'],
        'claude': ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
        'perplexity': ['llama-3-sonar-large-32k-online']
    }
    
    available_models = models.get(selected_provider, ['default-model'])
    selected_model = prompts.ask_model_selection(selected_provider, available_models)
    console.print(f"Selected model: [bold green]{selected_model}[/bold green]")
    
    # Workflow options
    console.rule("Workflow Configuration")
    workflow_config = prompts.ask_workflow_options()
    prompts.display_workflow_preview(workflow_config)
    
    console.print("\n[bold green]✅ Modern Prompts Demo Complete![/bold green]")


def demo_enhanced_display():
    """Demo enhanced display components"""
    console = get_console()
    display = create_display_manager(console)
    
    console.print("\n[bold blue]🎨 Enhanced Display Components Demo[/bold blue]\n")
    
    # Provider status display
    console.rule("Provider Status Display")
    providers_data = {
        'ollama': {
            'enabled': True,
            'healthy': True,
            'default_model': 'llama2',
            'base_url': 'http://localhost:11434'
        },
        'openai': {
            'enabled': True,
            'healthy': True,
            'default_model': 'gpt-4',
            'has_api_key': True,
            'api_key_required': True,
            'rate_limit': 60
        },
        'gemini': {
            'enabled': False,
            'healthy': False,
            'default_model': 'gemini-pro',
            'has_api_key': False,
            'api_key_required': True
        }
    }
    
    from .enhanced_prompts import ModernInteractivePrompts
    prompts = ModernInteractivePrompts(console)
    prompts.display_provider_status(providers_data)
    
    # Phase status display
    console.rule("Workflow Phases Display")
    phases_data = {
        'Phase 0': {
            'status': 'completed',
            'duration': 5.2,
            'agents': ['orchestrator'],
            'progress': 100
        },
        'Phase 1': {
            'status': 'running',
            'duration': 15.7,
            'agents': ['research-analyst', 'dependency-analyzer'],
            'progress': 75
        },
        'Phase 2': {
            'status': 'pending',
            'duration': 0,
            'agents': [],
            'progress': 0
        }
    }
    
    display.display_phase_status(phases_data)
    
    # Agent activity display
    console.rule("Agent Activity Display")
    agents_data = {
        'codebase-research-analyst': {
            'status': 'running',
            'type': 'research',
            'current_task': 'Analyzing Python files for dependencies',
            'progress': 65
        },
        'security-validator': {
            'status': 'waiting',
            'type': 'security',
            'current_task': 'Waiting for research completion',
            'progress': 0
        },
        'test-automation-engineer': {
            'status': 'completed',
            'type': 'testing',
            'current_task': 'Unit tests validation complete',
            'progress': 100
        }
    }
    
    display.display_agent_activity(agents_data)
    
    # Quick status overview
    console.rule("Quick Status Overview")
    status_data = {
        'system_healthy': True,
        'active_workflows': 2,
        'healthy_providers': 2,
        'total_providers': 3
    }
    
    display.display_quick_status(status_data)
    
    console.print("\n[bold green]✅ Enhanced Display Demo Complete![/bold green]")


async def demo_progress_indicators():
    """Demo enhanced progress indicators"""
    console = get_console()
    display = create_display_manager(console)
    
    console.print("\n[bold blue]⚡ Progress Indicators Demo[/bold blue]\n")
    
    # Simple progress spinner
    console.rule("Simple Progress Spinner")
    with display.create_simple_progress("Processing request...") as progress:
        task = progress.add_task("", total=None)
        for i in range(30):
            await asyncio.sleep(0.1)
    
    console.print("[bold green]✓[/bold green] Simple progress complete!")
    
    # Workflow progress
    console.rule("Workflow Progress")
    with display.create_workflow_progress("12-Phase Workflow") as progress:
        phases = [
            "Interactive Prompt Engineering",
            "Parallel Research & Discovery",
            "Strategic Planning",
            "Context Package Creation",
            "Parallel Stream Execution"
        ]
        
        tasks = {}
        for phase in phases:
            tasks[phase] = progress.add_task(f"Phase: {phase}", total=100)
        
        # Simulate phase execution
        for phase in phases:
            for i in range(101):
                progress.update(tasks[phase], advance=1)
                await asyncio.sleep(0.02)
    
    console.print("[bold green]✓[/bold green] Workflow progress complete!")
    
    # Provider-specific progress
    console.rule("Provider-Specific Progress")
    providers = ["ollama", "openai", "gemini"]
    
    for provider in providers:
        with display.create_provider_progress(provider) as progress:
            task = progress.add_task("Testing connection...", total=100)
            for i in range(101):
                progress.update(task, advance=1)
                await asyncio.sleep(0.01)
        
        console.print(f"[bold green]✓[/bold green] {provider.title()} connection test complete!")
    
    console.print("\n[bold green]✅ Progress Indicators Demo Complete![/bold green]")


async def demo_guided_wizard():
    """Demo guided setup wizard"""
    console = get_console()
    
    console.print("\n[bold blue]🧙‍♂️ Guided Setup Wizard Demo[/bold blue]\n")
    
    wizard = create_guided_wizard(console)
    
    # Show wizard info without actually running full setup
    welcome_panel = Panel(
        "[bold]Guided Setup Wizard[/bold]\n\n"
        "This wizard would guide you through:\n"
        "• Basic configuration setup\n"
        "• Provider selection and configuration\n"
        "• Workflow preferences\n"
        "• Plugin management\n"
        "• Advanced settings\n\n"
        "[dim]Demo mode - not actually configuring[/dim]",
        title="Setup Wizard Features",
        border_style="blue"
    )
    
    console.print(welcome_panel)
    
    # Quick demo of some wizard features
    prompts = create_modern_prompts(console)
    
    demo_mode = prompts.ask_boolean("Run a quick wizard demo?", default=True)
    
    if demo_mode:
        console.rule("Demo: Setup Mode Selection")
        setup_mode = prompts.ask_choice(
            "Choose setup mode",
            ["quick", "detailed"],
            default="quick"
        )
        console.print(f"Selected mode: [bold cyan]{setup_mode}[/bold cyan]")
        
        if setup_mode == "quick":
            console.print("\n[bold green]Quick setup would configure:[/bold green]")
            console.print("  ✓ Default Ollama provider")
            console.print("  ✓ Standard logging (INFO level)")
            console.print("  ✓ Basic orchestration settings")
            console.print("  ✓ Default plugin configuration")
    
    console.print("\n[bold green]✅ Guided Wizard Demo Complete![/bold green]")


async def main():
    """Main demo function"""
    console = get_console()
    
    # Welcome screen
    welcome = Panel(
        "[bold]LocalAgent Interactive UI Showcase[/bold]\n\n"
        "This demo showcases the modern CLI interface with:\n"
        "• Claude CLI-style theming and colors\n"
        "• Modern interactive prompts with fuzzy search\n"
        "• Enhanced progress indicators\n"
        "• Beautiful table displays and status indicators\n"
        "• Guided setup wizards\n\n"
        "[dim]Press Ctrl+C to exit at any time[/dim]",
        title="🚀 LocalAgent UI Demo",
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print(welcome)
    
    # Theme showcase
    console.print("\n[bold blue]🎨 Theme Showcase[/bold blue]")
    showcase_theme()
    
    try:
        # Demo components
        await demo_modern_prompts()
        demo_enhanced_display()
        await demo_progress_indicators()
        await demo_guided_wizard()
        
        # Closing message
        closing = Panel(
            "[bold green]Demo Complete![/bold green]\n\n"
            "You've seen the key features of LocalAgent's modern CLI interface.\n"
            "The system provides a beautiful, intuitive experience while maintaining\n"
            "powerful functionality for workflow orchestration and agent management.\n\n"
            "Ready to start using LocalAgent with these enhanced UI components!",
            title="✅ Success",
            border_style="green"
        )
        
        console.print(closing)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user. Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[red]Demo error: {e}[/red]")


if __name__ == "__main__":
    asyncio.run(main())