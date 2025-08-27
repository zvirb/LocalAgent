"""
Agent tools commands for LocalAgent CLI
Provides access to tools and MCP services for agents
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, List, Any
import typer
from rich import print
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.tree import Tree

from ..mcp_integration import MCPIntegration, AgentToolAccess
from ..core.context import CLIContext

app = typer.Typer(help="Agent tools and MCP services management")
console = Console()


@app.command()
def list_tools(
    ctx: typer.Context,
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Show tools available to specific agent")
):
    """List available tools for agents"""
    cli_ctx: CLIContext = ctx.obj
    
    # Initialize MCP integration
    mcp = MCPIntegration()
    
    if agent:
        # Show tools available to specific agent
        agent_access = AgentToolAccess(mcp)
        available_tools = agent_access.get_available_tools_for_agent(agent)
        
        console.print(Panel(f"[bold cyan]Tools Available to Agent: {agent}[/bold cyan]"))
        
        table = Table(title=f"Tools for {agent}")
        table.add_column("Tool Name", style="cyan")
        table.add_column("Category", style="yellow")
        table.add_column("Description", style="green")
        
        for tool_name in available_tools:
            tool = mcp.get_tool(tool_name)
            if tool:
                table.add_row(tool.name, tool.category, tool.description)
        
        console.print(table)
    else:
        # Show all tools or filtered by category
        tools = mcp.tools.values()
        
        if category:
            tools = [t for t in tools if t.category == category]
            title = f"Tools in Category: {category}"
        else:
            title = "All Available Tools"
        
        console.print(Panel(f"[bold cyan]{title}[/bold cyan]"))
        
        # Group tools by category
        categories = {}
        for tool in tools:
            if tool.category not in categories:
                categories[tool.category] = []
            categories[tool.category].append(tool)
        
        # Display as tree
        tree = Tree("[bold]Tools by Category[/bold]")
        
        for cat, cat_tools in sorted(categories.items()):
            branch = tree.add(f"[yellow]{cat}[/yellow] ({len(cat_tools)} tools)")
            for tool in cat_tools:
                branch.add(f"[cyan]{tool.name}[/cyan]: {tool.description}")
        
        console.print(tree)


@app.command()
def tool_info(
    ctx: typer.Context,
    tool_name: str = typer.Argument(..., help="Name of the tool to inspect")
):
    """Show detailed information about a specific tool"""
    cli_ctx: CLIContext = ctx.obj
    
    mcp = MCPIntegration()
    tool = mcp.get_tool(tool_name)
    
    if not tool:
        console.print(f"[red]Tool not found: {tool_name}[/red]")
        raise typer.Exit(1)
    
    console.print(Panel(f"[bold cyan]Tool Information: {tool_name}[/bold cyan]"))
    
    # Basic info
    console.print(f"[yellow]Name:[/yellow] {tool.name}")
    console.print(f"[yellow]Category:[/yellow] {tool.category}")
    console.print(f"[yellow]Description:[/yellow] {tool.description}")
    console.print(f"[yellow]Requires Auth:[/yellow] {tool.requires_auth}")
    
    # Parameters
    console.print("\n[yellow]Parameters:[/yellow]")
    
    if tool.parameters:
        param_table = Table()
        param_table.add_column("Parameter", style="cyan")
        param_table.add_column("Type", style="green")
        param_table.add_column("Default", style="yellow")
        param_table.add_column("Description")
        
        for param_name, param_info in tool.parameters.items():
            param_type = param_info.get('type', 'any')
            default = param_info.get('default', 'required')
            description = param_info.get('description', '')
            
            param_table.add_row(
                param_name,
                param_type,
                str(default) if default != 'required' else '[red]required[/red]',
                description
            )
        
        console.print(param_table)
    else:
        console.print("  No parameters required")


@app.command()
def invoke(
    ctx: typer.Context,
    tool_name: str = typer.Argument(..., help="Tool to invoke"),
    params: Optional[str] = typer.Option(None, "--params", "-p", help="Tool parameters as JSON"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Invoke as specific agent"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save output to file")
):
    """Invoke a tool directly (for testing)"""
    cli_ctx: CLIContext = ctx.obj
    
    mcp = MCPIntegration()
    
    # Parse parameters
    tool_params = {}
    if params:
        try:
            tool_params = json.loads(params)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON parameters: {e}[/red]")
            raise typer.Exit(1)
    
    # Execute tool
    try:
        with console.status(f"[bold green]Invoking tool: {tool_name}..."):
            if agent:
                # Invoke with agent permissions
                agent_access = AgentToolAccess(mcp)
                result = asyncio.run(
                    agent_access.invoke_tool_as_agent(agent, tool_name, **tool_params)
                )
                console.print(f"[green]Tool invoked as agent: {agent}[/green]")
            else:
                # Direct invocation
                result = asyncio.run(mcp.invoke_tool(tool_name, **tool_params))
        
        # Display result
        console.print(Panel("[bold cyan]Tool Execution Result[/bold cyan]"))
        
        if isinstance(result, dict):
            for key, value in result.items():
                console.print(f"[yellow]{key}:[/yellow] {value}")
        else:
            console.print(result)
        
        # Save if requested
        if output:
            with open(output, 'w') as f:
                json.dump(result if isinstance(result, (dict, list)) else str(result), f, indent=2)
            console.print(f"[green]Output saved to {output}[/green]")
            
    except PermissionError as e:
        console.print(f"[red]Permission denied: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Tool execution failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def permissions(
    ctx: typer.Context,
    agent: str = typer.Argument(..., help="Agent name to check permissions"),
    check_tool: Optional[str] = typer.Option(None, "--tool", "-t", help="Check specific tool permission")
):
    """Check agent permissions for tools"""
    cli_ctx: CLIContext = ctx.obj
    
    mcp = MCPIntegration()
    agent_access = AgentToolAccess(mcp)
    
    if check_tool:
        # Check specific tool permission
        can_use = agent_access.can_use_tool(agent, check_tool)
        
        if can_use:
            console.print(f"[green]✓ Agent '{agent}' CAN use tool '{check_tool}'[/green]")
        else:
            console.print(f"[red]✗ Agent '{agent}' CANNOT use tool '{check_tool}'[/red]")
    else:
        # Show all permissions for agent
        console.print(Panel(f"[bold cyan]Permissions for Agent: {agent}[/bold cyan]"))
        
        available_tools = agent_access.get_available_tools_for_agent(agent)
        all_tools = mcp.list_available_tools()
        denied_tools = [t for t in all_tools if t not in available_tools]
        
        # Create permission table
        table = Table(title="Tool Access Permissions")
        table.add_column("Status", style="bold", width=8)
        table.add_column("Tool Name", style="cyan")
        table.add_column("Category", style="yellow")
        
        # Add allowed tools
        for tool_name in sorted(available_tools):
            tool = mcp.get_tool(tool_name)
            if tool:
                table.add_row("[green]ALLOWED[/green]", tool.name, tool.category)
        
        # Add denied tools
        for tool_name in sorted(denied_tools):
            tool = mcp.get_tool(tool_name)
            if tool:
                table.add_row("[red]DENIED[/red]", tool.name, tool.category)
        
        console.print(table)
        
        # Summary
        console.print(f"\n[green]Allowed:[/green] {len(available_tools)} tools")
        console.print(f"[red]Denied:[/red] {len(denied_tools)} tools")


@app.command()
def mcp_status(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed status")
):
    """Check MCP services status"""
    cli_ctx: CLIContext = ctx.obj
    
    mcp = MCPIntegration()
    
    console.print(Panel("[bold cyan]MCP Services Status[/bold cyan]"))
    
    # Check each service
    services = [
        ('coordination', 'Coordination MCP', 'Agent coordination and orchestration'),
        ('hrm', 'HRM MCP', 'Human-readable memory storage'),
        ('task', 'Task MCP', 'Task management and tracking'),
        ('workflow_state', 'Workflow State MCP', 'Workflow state management')
    ]
    
    table = Table(title="MCP Services")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Description")
    
    for service_key, service_name, description in services:
        if service_key in mcp.services:
            status = "[green]✓ Active[/green]"
        else:
            status = "[red]✗ Inactive[/red]"
        
        table.add_row(service_name, status, description)
    
    console.print(table)
    
    if verbose:
        # Show tool counts by category
        console.print("\n[yellow]Tool Statistics:[/yellow]")
        
        categories = {}
        for tool in mcp.tools.values():
            if tool.category not in categories:
                categories[tool.category] = 0
            categories[tool.category] += 1
        
        for category, count in sorted(categories.items()):
            console.print(f"  • {category}: {count} tools")
        
        console.print(f"\n[green]Total tools available: {len(mcp.tools)}[/green]")


@app.command()
def test_file_ops(
    ctx: typer.Context,
    test_dir: Path = typer.Option(Path("/tmp/localagent_test"), help="Directory for testing")
):
    """Test file operations tools"""
    cli_ctx: CLIContext = ctx.obj
    
    console.print(Panel("[bold cyan]Testing File Operations[/bold cyan]"))
    
    mcp = MCPIntegration()
    
    async def run_tests():
        results = []
        
        # Test 1: Create directory
        console.print("\n[yellow]Test 1:[/yellow] Creating directory...")
        try:
            await mcp.invoke_tool('create_directory', path=str(test_dir))
            results.append(("Create Directory", "[green]✓ Passed[/green]"))
            console.print("  [green]✓ Directory created[/green]")
        except Exception as e:
            results.append(("Create Directory", f"[red]✗ Failed: {e}[/red]"))
            console.print(f"  [red]✗ Failed: {e}[/red]")
        
        # Test 2: Write file
        console.print("\n[yellow]Test 2:[/yellow] Writing file...")
        test_file = test_dir / "test.txt"
        try:
            await mcp.invoke_tool('write_file', 
                                 path=str(test_file), 
                                 content="Test content from LocalAgent CLI")
            results.append(("Write File", "[green]✓ Passed[/green]"))
            console.print("  [green]✓ File written[/green]")
        except Exception as e:
            results.append(("Write File", f"[red]✗ Failed: {e}[/red]"))
            console.print(f"  [red]✗ Failed: {e}[/red]")
        
        # Test 3: Read file
        console.print("\n[yellow]Test 3:[/yellow] Reading file...")
        try:
            content = await mcp.invoke_tool('read_file', path=str(test_file))
            if "Test content" in content:
                results.append(("Read File", "[green]✓ Passed[/green]"))
                console.print(f"  [green]✓ File read: {content}[/green]")
            else:
                results.append(("Read File", "[red]✗ Content mismatch[/red]"))
        except Exception as e:
            results.append(("Read File", f"[red]✗ Failed: {e}[/red]"))
            console.print(f"  [red]✗ Failed: {e}[/red]")
        
        # Test 4: List directory
        console.print("\n[yellow]Test 4:[/yellow] Listing directory...")
        try:
            files = await mcp.invoke_tool('list_directory', path=str(test_dir))
            if 'test.txt' in files:
                results.append(("List Directory", "[green]✓ Passed[/green]"))
                console.print(f"  [green]✓ Files found: {files}[/green]")
            else:
                results.append(("List Directory", "[red]✗ File not listed[/red]"))
        except Exception as e:
            results.append(("List Directory", f"[red]✗ Failed: {e}[/red]"))
            console.print(f"  [red]✗ Failed: {e}[/red]")
        
        # Test 5: Copy file
        console.print("\n[yellow]Test 5:[/yellow] Copying file...")
        copy_file = test_dir / "copy.txt"
        try:
            await mcp.invoke_tool('copy_path', 
                                 source=str(test_file), 
                                 destination=str(copy_file))
            results.append(("Copy File", "[green]✓ Passed[/green]"))
            console.print("  [green]✓ File copied[/green]")
        except Exception as e:
            results.append(("Copy File", f"[red]✗ Failed: {e}[/red]"))
            console.print(f"  [red]✗ Failed: {e}[/red]")
        
        # Test 6: Delete file
        console.print("\n[yellow]Test 6:[/yellow] Deleting files...")
        try:
            await mcp.invoke_tool('delete_path', path=str(test_file))
            await mcp.invoke_tool('delete_path', path=str(copy_file))
            results.append(("Delete Files", "[green]✓ Passed[/green]"))
            console.print("  [green]✓ Files deleted[/green]")
        except Exception as e:
            results.append(("Delete Files", f"[red]✗ Failed: {e}[/red]"))
            console.print(f"  [red]✗ Failed: {e}[/red]")
        
        # Test 7: Delete directory
        console.print("\n[yellow]Test 7:[/yellow] Deleting directory...")
        try:
            await mcp.invoke_tool('delete_path', path=str(test_dir), recursive=True)
            results.append(("Delete Directory", "[green]✓ Passed[/green]"))
            console.print("  [green]✓ Directory deleted[/green]")
        except Exception as e:
            results.append(("Delete Directory", f"[red]✗ Failed: {e}[/red]"))
            console.print(f"  [red]✗ Failed: {e}[/red]")
        
        return results
    
    # Run tests
    with console.status("[bold green]Running file operation tests..."):
        results = asyncio.run(run_tests())
    
    # Display results summary
    console.print("\n" + "=" * 50)
    console.print(Panel("[bold cyan]Test Results Summary[/bold cyan]"))
    
    table = Table()
    table.add_column("Test", style="cyan")
    table.add_column("Result", style="bold")
    
    for test_name, result in results:
        table.add_row(test_name, result)
    
    console.print(table)
    
    # Overall status
    passed = sum(1 for _, r in results if "Passed" in r)
    total = len(results)
    
    if passed == total:
        console.print(f"\n[bold green]All tests passed! ({passed}/{total})[/bold green]")
    else:
        console.print(f"\n[bold yellow]Tests completed: {passed}/{total} passed[/bold yellow]")


if __name__ == "__main__":
    app()