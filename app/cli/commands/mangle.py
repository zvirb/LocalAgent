"""
Mangle analysis commands for agent orchestration
"""

import json
from pathlib import Path
from typing import Optional, List
import typer
from rich import print
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

from ..mangle_integration import MangleIntegration, MangleAgentAnalyzer
from ..core.context import CLIContext

app = typer.Typer(help="Google Mangle deductive analysis for agent orchestration")
console = Console()


@app.command()
def analyze_performance(
    ctx: typer.Context,
    execution_log: Path = typer.Argument(..., help="Path to agent execution log JSON file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to file")
):
    """Analyze agent performance using Mangle deductive reasoning"""
    cli_ctx: CLIContext = ctx.obj
    
    # Load execution log
    try:
        with open(execution_log) as f:
            execution_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading execution log: {e}[/red]")
        raise typer.Exit(1)
    
    # Initialize Mangle integration
    mangle = MangleIntegration()
    
    # Analyze performance
    with console.status("[bold green]Analyzing agent performance with Mangle..."):
        result = mangle.analyze_agent_performance(execution_data)
    
    if not result.success:
        console.print(f"[red]Analysis failed: {result.error}[/red]")
        raise typer.Exit(1)
    
    # Display results
    console.print(Panel("[bold cyan]Agent Performance Analysis Results[/bold cyan]"))
    
    # Create results table
    table = Table(title="Performance Issues Detected")
    table.add_column("Issue Type", style="cyan")
    table.add_column("Agent/Details", style="yellow")
    table.add_column("Recommendation", style="green")
    
    # Process facts
    slow_agents = []
    bottlenecks = []
    unreliable = []
    parallel_ops = []
    
    for fact in result.facts:
        if fact['predicate'] == 'SlowExecution':
            slow_agents.append(fact['arguments'])
        elif fact['predicate'] == 'BottleneckAgent':
            bottlenecks.append(fact['arguments'][0])
        elif fact['predicate'] == 'UnreliableAgent':
            unreliable.append(fact['arguments'][0])
        elif fact['predicate'] == 'ParallelCandidate':
            parallel_ops.append(fact['arguments'])
    
    # Add to table
    for agent, task in slow_agents:
        table.add_row("Slow Execution", f"{agent} (task: {task})", "Consider optimization or caching")
    
    for agent in bottlenecks:
        table.add_row("Bottleneck", agent, "High priority for optimization")
    
    for agent in unreliable:
        table.add_row("Unreliable", agent, "Add retry logic or fix issues")
    
    for agent1, agent2 in parallel_ops:
        table.add_row("Parallelization", f"{agent1} + {agent2}", "Can run concurrently")
    
    console.print(table)
    
    # Save results if requested
    if output:
        results = {
            "slow_agents": slow_agents,
            "bottlenecks": bottlenecks,
            "unreliable_agents": unreliable,
            "parallelization_opportunities": parallel_ops,
            "raw_output": result.output
        }
        
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        
        console.print(f"[green]Results saved to {output}[/green]")


@app.command()
def optimize_workflow(
    ctx: typer.Context,
    workflow_data: Path = typer.Argument(..., help="Path to workflow execution data JSON"),
    suggest_parallelization: bool = typer.Option(True, help="Suggest parallelization opportunities"),
    identify_bottlenecks: bool = typer.Option(True, help="Identify bottleneck phases")
):
    """Analyze and optimize workflow using Mangle reasoning"""
    cli_ctx: CLIContext = ctx.obj
    
    # Load workflow data
    try:
        with open(workflow_data) as f:
            data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading workflow data: {e}[/red]")
        raise typer.Exit(1)
    
    # Initialize Mangle
    mangle = MangleIntegration()
    
    # Analyze workflow
    with console.status("[bold green]Analyzing workflow optimization opportunities..."):
        result = mangle.analyze_workflow_optimization(data)
    
    if not result.success:
        console.print(f"[red]Analysis failed: {result.error}[/red]")
        raise typer.Exit(1)
    
    # Display optimization suggestions
    console.print(Panel("[bold cyan]Workflow Optimization Analysis[/bold cyan]"))
    
    # Process results
    slow_phases = []
    resource_intensive = []
    parallelizable = []
    optimizations = []
    
    for fact in result.facts:
        if fact['predicate'] == 'SlowPhase':
            slow_phases.append(fact['arguments'][0])
        elif fact['predicate'] == 'ResourceIntensive':
            resource_intensive.append(fact['arguments'][0])
        elif fact['predicate'] == 'ParallelizablePhases':
            parallelizable.append(fact['arguments'])
        elif fact['predicate'] == 'OptimizationCandidate':
            optimizations.append(fact['arguments'])
    
    # Display slow phases
    if slow_phases:
        console.print("\n[yellow]Slow Phases Detected:[/yellow]")
        for phase in slow_phases:
            console.print(f"  • Phase: {phase} (>30 seconds)")
    
    # Display resource-intensive phases
    if resource_intensive:
        console.print("\n[orange1]Resource-Intensive Phases:[/orange1]")
        for phase in resource_intensive:
            console.print(f"  • Phase: {phase} (High CPU/Memory)")
    
    # Display parallelization opportunities
    if suggest_parallelization and parallelizable:
        console.print("\n[green]Parallelization Opportunities:[/green]")
        for phase1, phase2 in parallelizable:
            console.print(f"  • {phase1} and {phase2} can run in parallel")
    
    # Display optimization candidates
    if optimizations:
        console.print("\n[cyan]Optimization Recommendations:[/cyan]")
        for phase, reason in optimizations:
            console.print(f"  • {phase}: {reason.replace('_', ' ').title()}")


@app.command()
def suggest_agents(
    ctx: typer.Context,
    task_type: str = typer.Argument(..., help="Type of task (debug, implement, deploy, optimize, security)"),
    list_available: bool = typer.Option(False, "--list", "-l", help="List available agents")
):
    """Suggest optimal agent composition for a task using Mangle reasoning"""
    cli_ctx: CLIContext = ctx.obj
    
    # Define available agents (would normally come from configuration)
    available_agents = [
        "codebase-research-analyst",
        "security-validator",
        "test-automation-engineer",
        "deployment-orchestrator",
        "monitoring-analyst",
        "performance-profiler",
        "documentation-specialist",
        "project-orchestrator",
        "dependency-analyzer"
    ]
    
    if list_available:
        console.print("[cyan]Available Agents:[/cyan]")
        for agent in available_agents:
            console.print(f"  • {agent}")
        return
    
    # Initialize Mangle analyzer
    mangle = MangleIntegration()
    analyzer = MangleAgentAnalyzer(mangle)
    
    # Get suggestions
    with console.status(f"[bold green]Analyzing best agents for '{task_type}' task..."):
        suggested = analyzer.suggest_agent_composition(task_type, available_agents)
    
    # Display suggestions
    console.print(Panel(f"[bold cyan]Suggested Agent Composition for '{task_type}'[/bold cyan]"))
    
    if suggested:
        table = Table(title="Recommended Agent Pipeline")
        table.add_column("Order", style="cyan", justify="center")
        table.add_column("Agent", style="yellow")
        table.add_column("Purpose", style="green")
        
        # Define agent purposes
        purposes = {
            "codebase-research-analyst": "Analyze existing code structure",
            "security-validator": "Validate security requirements",
            "test-automation-engineer": "Create and run tests",
            "deployment-orchestrator": "Handle deployment process",
            "monitoring-analyst": "Set up monitoring",
            "performance-profiler": "Analyze performance",
            "documentation-specialist": "Update documentation",
            "project-orchestrator": "Coordinate overall workflow",
            "dependency-analyzer": "Check dependencies"
        }
        
        for i, agent in enumerate(suggested, 1):
            purpose = purposes.get(agent, "Specialized task execution")
            table.add_row(str(i), agent, purpose)
        
        console.print(table)
        
        # Show execution order
        console.print("\n[green]Suggested Execution Order:[/green]")
        console.print(" → ".join(suggested))
    else:
        console.print(f"[yellow]No specific agent suggestions for task type '{task_type}'[/yellow]")
        console.print("Consider using the general-purpose orchestrator.")


@app.command()
def custom_query(
    ctx: typer.Context,
    rules_file: Path = typer.Argument(..., help="Path to Mangle rules file (.mg)"),
    facts_file: Optional[Path] = typer.Option(None, "--facts", "-f", help="Path to facts file"),
    query: str = typer.Option(..., "--query", "-q", help="Query to execute"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to file")
):
    """Execute custom Mangle query for agent analysis"""
    cli_ctx: CLIContext = ctx.obj
    
    # Load rules
    try:
        with open(rules_file) as f:
            rules = f.read()
    except Exception as e:
        console.print(f"[red]Error loading rules: {e}[/red]")
        raise typer.Exit(1)
    
    # Load facts if provided
    facts = []
    if facts_file:
        try:
            with open(facts_file) as f:
                # Support both .mg format and JSON
                if facts_file.suffix == '.json':
                    fact_data = json.load(f)
                    # Convert JSON to Mangle facts
                    for item in fact_data:
                        if isinstance(item, dict):
                            predicate = item.get('predicate', 'Fact')
                            args = item.get('arguments', [])
                            fact_str = f"{predicate}({', '.join(map(str, args))})."
                            facts.append(fact_str)
                else:
                    facts = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception as e:
            console.print(f"[red]Error loading facts: {e}[/red]")
            raise typer.Exit(1)
    
    # Initialize Mangle
    mangle = MangleIntegration()
    
    # Execute query
    with console.status(f"[bold green]Executing Mangle query: {query}"):
        result = mangle.custom_query(rules, facts, [query])
    
    if not result.success:
        console.print(f"[red]Query failed: {result.error}[/red]")
        raise typer.Exit(1)
    
    # Display results
    console.print(Panel(f"[bold cyan]Query Results: {query}[/bold cyan]"))
    
    if result.facts:
        table = Table()
        table.add_column("Predicate", style="cyan")
        table.add_column("Arguments", style="yellow")
        
        for fact in result.facts:
            args_str = ", ".join(map(str, fact['arguments']))
            table.add_row(fact['predicate'], args_str)
        
        console.print(table)
    else:
        console.print("[yellow]No results found[/yellow]")
    
    # Save if requested
    if output:
        with open(output, 'w') as f:
            json.dump({
                "query": query,
                "results": result.facts,
                "raw_output": result.output
            }, f, indent=2)
        
        console.print(f"[green]Results saved to {output}[/green]")


if __name__ == "__main__":
    app()