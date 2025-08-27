# Interactive UI Stream Context Package
**Package ID**: interactive-ui-stream-20250825
**Token Limit**: 3000 tokens
**Target Specialists**: ui-architect, interactive-designer, terminal-formatter

## Current UI Architecture

### Existing CLI Interface (app/orchestration/cli_interface.py)
```python
class LocalAgentCLI:
    def create_parser(self) -> argparse.ArgumentParser:
        # Uses basic argparse - NOT modern CLI approach
        parser = argparse.ArgumentParser(
            description='LocalAgent + UnifiedWorkflow Orchestration CLI'
        )
```

**Issues Identified**:
- Uses outdated argparse instead of modern Typer framework
- No Rich integration for enhanced output
- No interactive prompts or user experience enhancements
- Basic text output without formatting or progress indicators

### Target Modern CLI Architecture

#### Typer-Based Application Structure
```python
# app/cli/core/app.py - NEW STRUCTURE NEEDED
import typer
from rich.console import Console
from typing import Optional

app = typer.Typer(
    name="localagent",
    help="LocalAgent CLI with rich interactive interface",
    rich_markup_mode="rich"
)
console = Console()
```

## Interactive Components Required

### 1. InquirerPy Integration (inquirerpy>=0.3.4)

#### Configuration Wizard
```python
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

def interactive_setup():
    provider = inquirer.select(
        message="Select your primary LLM provider:",
        choices=[
            Choice("ollama", "Ollama (Local)"),
            Choice("openai", "OpenAI GPT"),
            Choice("gemini", "Google Gemini"),
            Choice("perplexity", "Perplexity AI")
        ],
        default="ollama"
    ).execute()
```

#### Workflow Confirmation System
```python
def confirm_workflow_plan(plan_summary: str):
    console.print(f"[bold blue]Proposed Workflow Plan:[/bold blue]")
    console.print(plan_summary)
    
    confirm = inquirer.confirm(
        message="Proceed with this workflow?",
        default=True
    ).execute()
    
    return confirm
```

### 2. Rich Terminal UI (rich>=13.6.0)

#### Progress Tracking
```python
from rich.progress import Progress, SpinnerColumn, TextColumn

def show_workflow_progress():
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Executing Phase 1: Research & Discovery", total=None)
        # Update task as phases complete
```

#### Status Display
```python
from rich.table import Table
from rich.panel import Panel

def display_agent_status(agents_status):
    table = Table(title="Agent Execution Status")
    table.add_column("Agent Type", style="cyan")
    table.add_column("Status", style="green") 
    table.add_column("Progress", style="blue")
    
    for agent, status in agents_status.items():
        table.add_row(agent, status['status'], f"{status['progress']}%")
    
    console.print(Panel(table, title="🤖 Agent Dashboard"))
```

#### Error Display with Rich Formatting
```python
from rich.traceback import install
from rich import print as rprint

install()  # Rich traceback formatting

def handle_error(error):
    rprint(f"[bold red]❌ Error:[/bold red] {error}")
    rprint("[yellow]💡 Suggestion:[/yellow] Check provider configuration")
```

### 3. Interactive Command Design

#### Command Structure with Rich Help
```python
@app.command(rich_help_panel="Core Commands")
def workflow(
    prompt: str = typer.Argument(..., help="Task description for the workflow"),
    provider: str = typer.Option("ollama", help="LLM provider to use"),
    parallel: bool = typer.Option(True, help="Enable parallel agent execution"),
    interactive: bool = typer.Option(True, help="Use interactive confirmations")
):
    """Execute a 12-phase UnifiedWorkflow with [bold blue]interactive guidance[/bold blue]."""
```

#### Interactive Provider Setup
```python
@app.command(name="setup", rich_help_panel="Configuration")
def interactive_setup():
    """Interactive setup wizard with [green]guided configuration[/green]."""
    
    console.print("[bold green]🚀 LocalAgent Interactive Setup[/bold green]")
    
    # Provider selection with descriptions
    providers = inquirer.checkbox(
        message="Select LLM providers to configure:",
        choices=[
            Choice("ollama", "Ollama (Local, free, private)"),
            Choice("openai", "OpenAI GPT (Cloud, paid, high-quality)"),
            Choice("gemini", "Google Gemini (Cloud, free tier available)")
        ]
    ).execute()
    
    # Configuration for each selected provider
    config = {}
    for provider in providers:
        if provider == "ollama":
            config["ollama"] = configure_ollama_interactive()
        elif provider == "openai":
            config["openai"] = configure_openai_interactive()
```

## Color Schemes and Themes

### Rich Color Configuration
```python
from rich.theme import Theme

# LocalAgent custom theme
localagent_theme = Theme({
    "primary": "bold blue",
    "secondary": "cyan", 
    "success": "bold green",
    "warning": "yellow",
    "error": "bold red",
    "info": "bright_blue",
    "agent": "magenta",
    "workflow": "bold cyan",
    "phase": "blue",
    "evidence": "green"
})

console = Console(theme=localagent_theme)
```

### Status Indicators
- 🚀 Workflow start
- ⚡ Phase execution  
- 🤖 Agent activity
- ✅ Success states
- ❌ Error states
- 💡 Tips/suggestions
- 📊 Progress/metrics
- 🔍 Evidence collection

## User Experience Patterns

### 1. Guided Workflow Execution
- **Phase 0**: Interactive prompt refinement with confirmation
- **Progress Tracking**: Real-time phase and agent status
- **Evidence Review**: Interactive evidence collection display
- **Error Recovery**: Guided error resolution prompts

### 2. Configuration Management
```python
def interactive_config_management():
    action = inquirer.select(
        message="Configuration action:",
        choices=[
            Choice("view", "View current configuration"),
            Choice("edit", "Edit configuration interactively"),
            Choice("validate", "Validate configuration"),
            Choice("backup", "Backup configuration")
        ]
    ).execute()
```

### 3. Real-time Monitoring
```python
from rich.live import Live
from rich.table import Table

def live_agent_monitor():
    with Live(generate_agent_table(), refresh_per_second=2) as live:
        while workflow_active:
            live.update(generate_agent_table())
            time.sleep(0.5)
```

## Implementation Strategy

### Phase 1: Core UI Framework
1. **Replace argparse** with Typer in cli_interface.py
2. **Integrate Rich Console** for all output
3. **Add basic progress indicators** for workflow phases
4. **Implement color theme** system

### Phase 2: Interactive Components  
1. **Add InquirerPy prompts** for configuration
2. **Create workflow confirmation** system
3. **Implement interactive setup** wizard
4. **Add real-time status displays**

### Phase 3: Advanced UI Features
1. **Live monitoring dashboards** with Rich Live
2. **Interactive error recovery** prompts
3. **Evidence collection UI** with selection
4. **Configuration management** interface

## Styling Guidelines

### Command Output Format
```
🚀 LocalAgent Workflow Execution

┏━━ Workflow: Fix authentication system ━━┓
┃ Provider: ollama (llama3.1:latest)      ┃
┃ Parallel: ✅ Enabled (max 15 agents)    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Phase 0: Interactive Prompt Engineering [in progress] ⚡
├── Prompt Analysis: Complete ✅
├── Context Loading: Complete ✅  
└── User Confirmation: Waiting... ⏳
```

## Success Criteria
1. **Modern CLI Experience**: Typer-based interface with Rich formatting
2. **Interactive Setup**: Guided configuration wizard
3. **Real-time Feedback**: Progress indicators and status displays
4. **Error Handling**: User-friendly error messages with recovery guidance
5. **Consistent Theme**: Coherent color scheme and iconography