#!/usr/bin/env python3
"""
Pattern-aware CLI for MCP orchestration
Integrates intelligent pattern selection with the enhanced CLI
"""

import click
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.markdown import Markdown
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.patterns import (
    pattern_registry,
    intelligent_selector,
    PatternSelectionContext,
    PatternCategory,
    select_and_execute_pattern
)

console = Console()

class PatternCLI:
    """CLI interface for MCP patterns"""
    
    def __init__(self):
        self.console = console
        self.available_mcps = self._detect_available_mcps()
    
    def _detect_available_mcps(self) -> List[str]:
        """Detect which MCPs are available"""
        available = []
        
        # Check for each MCP
        mcp_checks = {
            'hrm': 'mcp.hrm_mcp',
            'task': 'mcp.task_mcp',
            'coordination': 'mcp.coordination_mcp',
            'workflow_state': 'mcp.workflow_state_mcp',
            'memory': 'app.orchestration.mcp_integration',
            'redis': 'app.orchestration.mcp_integration'
        }
        
        for mcp_name, module_path in mcp_checks.items():
            try:
                __import__(module_path)
                available.append(mcp_name)
            except ImportError:
                pass
        
        return available
    
    def list_patterns(self, category: Optional[str] = None):
        """List available patterns"""
        if category:
            try:
                cat_enum = PatternCategory(category)
                patterns = pattern_registry.list_patterns(cat_enum)
            except ValueError:
                self.console.print(f"[red]Invalid category: {category}[/red]")
                return
        else:
            patterns = pattern_registry.list_patterns()
        
        # Create table
        table = Table(title="Available MCP Patterns", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Category", style="yellow")
        table.add_column("MCPs Required", style="green")
        table.add_column("Performance", style="blue")
        
        for pattern in patterns:
            perf = pattern.performance_profile
            perf_str = f"L:{perf.get('latency', '?')} T:{perf.get('throughput', '?')}"
            
            table.add_row(
                pattern.pattern_id,
                pattern.name,
                pattern.category.value,
                ', '.join(pattern.required_mcps),
                perf_str
            )
        
        self.console.print(table)
    
    def show_pattern_details(self, pattern_id: str):
        """Show detailed information about a pattern"""
        if pattern_id not in pattern_registry.patterns:
            self.console.print(f"[red]Pattern '{pattern_id}' not found[/red]")
            return
        
        pattern = pattern_registry.patterns[pattern_id]
        
        # Create tree view
        tree = Tree(f"[bold cyan]{pattern.name}[/bold cyan]")
        
        # Basic info
        info = tree.add("[green]Information[/green]")
        info.add(f"ID: {pattern.pattern_id}")
        info.add(f"Category: {pattern.category.value}")
        info.add(f"Description: {pattern.description}")
        
        # Use cases
        use_cases = tree.add("[yellow]Use Cases[/yellow]")
        for uc in pattern.use_cases:
            use_cases.add(f"• {uc}")
        
        # Requirements
        reqs = tree.add("[blue]Requirements[/blue]")
        reqs.add(f"MCPs: {', '.join(pattern.required_mcps)}")
        reqs.add(f"Memory: {pattern.docker_requirements.get('memory', 'N/A')}")
        reqs.add(f"CPU: {pattern.docker_requirements.get('cpu', 'N/A')}")
        
        # Performance
        perf = tree.add("[magenta]Performance Profile[/magenta]")
        for key, value in pattern.performance_profile.items():
            perf.add(f"{key}: {value}")
        
        self.console.print(tree)
    
    async def recommend_pattern(self, task: str):
        """Get pattern recommendations for a task"""
        self.console.print(f"\n[cyan]Analyzing task:[/cyan] {task}\n")
        
        with self.console.status("[dim]Selecting optimal pattern...[/dim]"):
            context = PatternSelectionContext(
                query=task,
                available_mcps=self.available_mcps
            )
            
            recommendation = await intelligent_selector.select_pattern(context)
        
        # Display recommendation
        panel_content = f"""
[bold]Recommended Pattern:[/bold] {recommendation.pattern_name}
[bold]Pattern ID:[/bold] {recommendation.pattern_id}
[bold]Confidence:[/bold] {recommendation.confidence:.2%}

[bold]Reasoning:[/bold]
"""
        for reason in recommendation.reasoning:
            panel_content += f"• {reason}\n"
        
        if recommendation.alternative_patterns:
            panel_content += "\n[bold]Alternative Patterns:[/bold]\n"
            for alt_id, alt_conf in recommendation.alternative_patterns:
                alt_name = pattern_registry.patterns[alt_id].name if alt_id in pattern_registry.patterns else alt_id
                panel_content += f"• {alt_name} (confidence: {alt_conf:.2%})\n"
        
        self.console.print(Panel(
            panel_content,
            title="Pattern Recommendation",
            border_style="green"
        ))
        
        # Show execution plan
        if recommendation.execution_plan:
            plan_tree = Tree("[bold]Execution Plan[/bold]")
            
            steps = plan_tree.add("Steps")
            for i, step in enumerate(recommendation.execution_plan.get('steps', []), 1):
                steps.add(f"{i}. {step}")
            
            if 'docker_config' in recommendation.execution_plan:
                docker = plan_tree.add("Docker Configuration")
                for key, value in recommendation.execution_plan['docker_config'].items():
                    docker.add(f"{key}: {value}")
            
            self.console.print(plan_tree)
        
        return recommendation
    
    async def execute_pattern(self, pattern_id: str, context: Dict[str, Any]):
        """Execute a specific pattern"""
        if pattern_id not in pattern_registry.patterns:
            self.console.print(f"[red]Pattern '{pattern_id}' not found[/red]")
            return
        
        pattern_def = pattern_registry.patterns[pattern_id]
        
        # Check prerequisites
        missing_mcps = [mcp for mcp in pattern_def.required_mcps if mcp not in self.available_mcps]
        if missing_mcps:
            self.console.print(f"[red]Missing required MCPs: {', '.join(missing_mcps)}[/red]")
            return
        
        self.console.print(f"\n[cyan]Executing pattern:[/cyan] {pattern_def.name}\n")
        
        try:
            with self.console.status(f"[dim]Executing {pattern_id}...[/dim]"):
                pattern = pattern_registry.get_pattern(pattern_id)
                
                if not await pattern.validate_prerequisites():
                    self.console.print("[red]Pattern prerequisites not met[/red]")
                    return
                
                result = await pattern.execute(context)
            
            # Display results
            self.console.print(Panel(
                json.dumps(result, indent=2),
                title=f"Execution Result - {pattern_def.name}",
                border_style="green"
            ))
            
            # Record learning
            await intelligent_selector.learn_from_execution(
                pattern_id,
                {'success': True, 'execution_time': 1.0}
            )
            
        except Exception as e:
            self.console.print(f"[red]Execution failed: {e}[/red]")
            
            # Record failure
            await intelligent_selector.learn_from_execution(
                pattern_id,
                {'success': False, 'error': str(e)}
            )
    
    def show_categories(self):
        """Show all pattern categories"""
        table = Table(title="Pattern Categories", show_header=True)
        table.add_column("Category", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Pattern Count", style="green")
        
        category_descriptions = {
            PatternCategory.SEQUENTIAL: "Linear task execution",
            PatternCategory.PARALLEL: "Concurrent task execution",
            PatternCategory.HIERARCHICAL: "Tree-based delegation",
            PatternCategory.MESH: "Fully connected communication",
            PatternCategory.PIPELINE: "Stream processing",
            PatternCategory.EVENT_DRIVEN: "Reactive patterns",
            PatternCategory.CONSENSUS: "Multi-agent agreement",
            PatternCategory.SCATTER_GATHER: "Distribute and collect"
        }
        
        for category in PatternCategory:
            patterns = pattern_registry.list_patterns(category)
            table.add_row(
                category.value,
                category_descriptions.get(category, ""),
                str(len(patterns))
            )
        
        self.console.print(table)
    
    def show_mcp_status(self):
        """Show MCP availability status"""
        table = Table(title="MCP Service Status", show_header=True)
        table.add_column("MCP", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Patterns Using", style="yellow")
        
        all_mcps = ['hrm', 'task', 'coordination', 'workflow_state', 'memory', 'redis']
        
        for mcp in all_mcps:
            available = mcp in self.available_mcps
            status = "[green]✓ Available[/green]" if available else "[red]✗ Not Available[/red]"
            
            # Count patterns using this MCP
            patterns_using = sum(
                1 for p in pattern_registry.patterns.values()
                if mcp in p.required_mcps
            )
            
            table.add_row(mcp, status, str(patterns_using))
        
        self.console.print(table)

@click.group()
def cli():
    """MCP Pattern Orchestration CLI"""
    pass

@cli.command()
@click.option('--category', '-c', help='Filter by category')
def list_patterns(category):
    """List available MCP patterns"""
    pattern_cli = PatternCLI()
    pattern_cli.list_patterns(category)

@cli.command()
@click.argument('pattern_id')
def show_pattern(pattern_id):
    """Show details of a specific pattern"""
    pattern_cli = PatternCLI()
    pattern_cli.show_pattern_details(pattern_id)

@cli.command()
@click.argument('task')
def recommend(task):
    """Get pattern recommendation for a task"""
    pattern_cli = PatternCLI()
    asyncio.run(pattern_cli.recommend_pattern(task))

@cli.command()
@click.argument('pattern_id')
@click.option('--context', '-c', default='{}', help='Context JSON')
def execute(pattern_id, context):
    """Execute a specific pattern"""
    pattern_cli = PatternCLI()
    try:
        context_dict = json.loads(context)
    except json.JSONDecodeError:
        console.print("[red]Invalid context JSON[/red]")
        return
    
    asyncio.run(pattern_cli.execute_pattern(pattern_id, context_dict))

@cli.command()
def categories():
    """Show all pattern categories"""
    pattern_cli = PatternCLI()
    pattern_cli.show_categories()

@cli.command()
def status():
    """Show MCP service status"""
    pattern_cli = PatternCLI()
    pattern_cli.show_mcp_status()

@cli.command()
@click.argument('task')
def auto(task):
    """Automatically select and execute best pattern for task"""
    async def auto_execute():
        pattern_cli = PatternCLI()
        
        # Get recommendation
        recommendation = await pattern_cli.recommend_pattern(task)
        
        # Ask for confirmation
        console.print("\n[yellow]Do you want to execute this pattern? (y/n)[/yellow]")
        if input().lower() == 'y':
            await pattern_cli.execute_pattern(
                recommendation.pattern_id,
                {'query': task}
            )
    
    asyncio.run(auto_execute())

if __name__ == '__main__':
    cli()