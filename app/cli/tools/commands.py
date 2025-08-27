"""
CLI Commands Integration for Search and File Operations
Typer-based commands with Rich display and InquirerPy prompts
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Annotated

import typer
from rich.console import Console

from .search import SearchManager, SearchContext, SearchType, MatchType
from .file_ops import FileOperationsManager, OperationContext, FileOperation


console = Console()


def create_tools_commands() -> typer.Typer:
    """Create tools command group"""
    tools_app = typer.Typer(
        name="tools",
        help="Advanced search and file operations tools",
        no_args_is_help=True,
        rich_markup_mode="rich"
    )
    
    @tools_app.command()
    def search(
        query: Annotated[Optional[str], typer.Argument(help="Search query")] = None,
        content: Annotated[bool, typer.Option("--content", "-c", help="Search file contents")] = True,
        files: Annotated[bool, typer.Option("--files", "-f", help="Search file names")] = False,
        fuzzy: Annotated[bool, typer.Option("--fuzzy/--exact", help="Use fuzzy matching")] = True,
        regex: Annotated[bool, typer.Option("--regex", "-r", help="Use regex matching")] = False,
        case_sensitive: Annotated[bool, typer.Option("--case-sensitive", "-s", help="Case sensitive search")] = False,
        max_results: Annotated[int, typer.Option("--max", "-m", help="Maximum results")] = 100,
        paths: Annotated[Optional[str], typer.Option("--paths", "-p", help="Search paths (comma-separated)")] = None,
        include: Annotated[Optional[str], typer.Option("--include", "-i", help="Include patterns (comma-separated)")] = None,
        exclude: Annotated[Optional[str], typer.Option("--exclude", "-e", help="Exclude patterns (comma-separated)")] = None,
        context_lines: Annotated[int, typer.Option("--context", "-C", help="Context lines around matches")] = 2,
        interactive: Annotated[bool, typer.Option("--interactive", help="Interactive mode")] = False
    ):
        """Advanced search with fuzzy matching and ripgrep integration"""
        
        if interactive or not query:
            # Interactive mode
            manager = SearchManager(console)
            asyncio.run(manager.interactive_search())
            return
        
        # Direct search mode
        search_type = SearchType.MIXED if (content and files) else (
            SearchType.FILE_NAMES if files else SearchType.TEXT_CONTENT
        )
        
        match_type = MatchType.REGEX if regex else (
            MatchType.FUZZY if fuzzy else MatchType.EXACT
        )
        
        # Parse paths
        root_paths = []
        if paths:
            root_paths = [Path(p.strip()) for p in paths.split(',')]
        
        # Parse patterns
        include_patterns = []
        if include:
            include_patterns = [p.strip() for p in include.split(',')]
        
        exclude_patterns = []
        if exclude:
            exclude_patterns = [p.strip() for p in exclude.split(',')]
        
        # Create search context
        context = SearchContext(
            query=query,
            search_type=search_type,
            match_type=match_type,
            root_paths=root_paths,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_results=max_results,
            case_sensitive=case_sensitive,
            context_lines=context_lines
        )
        
        # Execute search
        manager = SearchManager(console)
        results = asyncio.run(manager.execute_search(context))
        
        if results:
            console.print(f"\n[green]Search completed: {len(results)} matches found[/green]")
        else:
            console.print("[yellow]No matches found[/yellow]")
    
    @tools_app.command()
    def file_ops(
        operation: Annotated[Optional[str], typer.Argument(help="Operation: copy, move, rename, delete, compress, organize")] = None,
        source: Annotated[Optional[str], typer.Option("--source", "-s", help="Source patterns (comma-separated)")] = None,
        destination: Annotated[Optional[str], typer.Option("--dest", "-d", help="Destination path")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without executing")] = False,
        overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite existing files")] = False,
        backup: Annotated[bool, typer.Option("--backup", help="Create backup before destructive operations")] = False,
        interactive: Annotated[bool, typer.Option("--interactive", help="Interactive mode")] = False
    ):
        """Batch file operations with rich progress display"""
        
        if interactive or not operation:
            # Interactive mode
            manager = FileOperationsManager(console)
            asyncio.run(manager.interactive_operations())
            return
        
        # Direct operation mode
        try:
            op_enum = FileOperation(operation.lower())
        except ValueError:
            console.print(f"[red]Invalid operation: {operation}[/red]")
            console.print("Valid operations: copy, move, rename, delete, compress, organize, batch_rename")
            raise typer.Exit(1)
        
        if not source:
            console.print("[red]Source patterns are required[/red]")
            raise typer.Exit(1)
        
        # Parse source patterns
        source_patterns = [p.strip() for p in source.split(',')]
        
        # Create operation context
        context = OperationContext(
            operation=op_enum,
            source_patterns=source_patterns,
            destination=Path(destination) if destination else None,
            dry_run=dry_run,
            overwrite=overwrite,
            backup=backup
        )
        
        # Execute operation
        manager = FileOperationsManager(console)
        results = asyncio.run(manager.processor.process_files(context))
        
        if results:
            successful = len([r for r in results if r.success])
            total = len(results)
            console.print(f"\n[green]Operation completed: {successful}/{total} files processed successfully[/green]")
    
    @tools_app.command()
    def organize(
        source: Annotated[str, typer.Argument(help="Source directory or pattern")],
        strategy: Annotated[str, typer.Option("--strategy", "-s", help="Organization strategy")] = "extension",
        destination: Annotated[str, typer.Option("--dest", "-d", help="Destination directory")] = "organized",
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview organization")] = False
    ):
        """Organize files by extension, date, size, or type"""
        
        valid_strategies = ["extension", "date", "size", "mime_type"]
        if strategy not in valid_strategies:
            console.print(f"[red]Invalid strategy: {strategy}[/red]")
            console.print(f"Valid strategies: {', '.join(valid_strategies)}")
            raise typer.Exit(1)
        
        context = OperationContext(
            operation=FileOperation.ORGANIZE,
            source_patterns=[source],
            destination=Path(destination),
            dry_run=dry_run,
            options={'strategy': strategy}
        )
        
        manager = FileOperationsManager(console)
        results = asyncio.run(manager.processor.process_files(context))
        
        if not dry_run and results:
            successful = len([r for r in results if r.success])
            console.print(f"\n[green]Organized {successful} files into '{destination}'[/green]")
    
    @tools_app.command()
    def compress(
        source: Annotated[str, typer.Argument(help="Source files pattern")],
        format: Annotated[str, typer.Option("--format", "-f", help="Compression format")] = "zip",
        output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output archive name")] = None
    ):
        """Compress files into archives"""
        
        valid_formats = ["zip", "tar", "tar.gz", "tar.bz2", "gz"]
        if format not in valid_formats:
            console.print(f"[red]Invalid format: {format}[/red]")
            console.print(f"Valid formats: {', '.join(valid_formats)}")
            raise typer.Exit(1)
        
        context = OperationContext(
            operation=FileOperation.COMPRESS,
            source_patterns=[source],
            options={'format': format, 'output': output}
        )
        
        manager = FileOperationsManager(console)
        results = asyncio.run(manager.processor.process_files(context))
        
        if results:
            successful = len([r for r in results if r.success])
            console.print(f"\n[green]Compressed {successful} files[/green]")
    
    @tools_app.command()
    def batch_rename(
        source: Annotated[str, typer.Argument(help="Source files pattern")],
        pattern: Annotated[str, typer.Option("--pattern", "-p", help="Rename pattern")] = "{name}_{counter}",
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview renames")] = False
    ):
        """Batch rename files using patterns"""
        
        console.print(f"[blue]Pattern placeholders:[/blue]")
        console.print("  {name} - Original filename without extension")
        console.print("  {ext} - File extension")
        console.print("  {counter} - Sequential counter")
        console.print("  {date} - Current date (YYYYMMDD)")
        console.print("  {time} - Current time (HHMMSS)")
        console.print()
        
        context = OperationContext(
            operation=FileOperation.BATCH_RENAME,
            source_patterns=[source],
            dry_run=dry_run,
            options={'pattern': pattern, 'counter': 1}
        )
        
        manager = FileOperationsManager(console)
        results = asyncio.run(manager.processor.process_files(context))
        
        if not dry_run and results:
            successful = len([r for r in results if r.success])
            console.print(f"\n[green]Renamed {successful} files[/green]")
    
    @tools_app.command()
    def find_duplicates(
        path: Annotated[str, typer.Argument(help="Path to search for duplicates")] = ".",
        by_hash: Annotated[bool, typer.Option("--hash", help="Compare by file hash")] = True,
        by_size: Annotated[bool, typer.Option("--size", help="Compare by file size")] = False,
        min_size: Annotated[int, typer.Option("--min-size", help="Minimum file size in bytes")] = 0,
        delete: Annotated[bool, typer.Option("--delete", help="Delete duplicates")] = False
    ):
        """Find and optionally remove duplicate files"""
        
        console.print(f"[blue]Searching for duplicates in: {path}[/blue]")
        
        # This would be implemented in a separate duplicate finder utility
        # For now, show placeholder
        console.print("[yellow]Duplicate finder implementation coming soon...[/yellow]")
    
    @tools_app.command()
    def history():
        """Show search and file operation history"""
        
        manager = FileOperationsManager(console)
        history = manager.get_operation_history()
        
        if not history:
            console.print("[yellow]No operation history found[/yellow]")
            return
        
        from rich.table import Table
        
        table = Table(title="Operation History", show_header=True, header_style="bold magenta")
        table.add_column("Time", style="cyan")
        table.add_column("Operation", style="green")
        table.add_column("Source", style="yellow")
        table.add_column("Destination", style="blue")
        table.add_column("Status", style="red")
        
        for result in history[-20:]:  # Show last 20 operations
            time_str = "Recent"  # Would use actual timestamp
            status = "✅" if result.success else "❌"
            dest_str = str(result.destination_path) if result.destination_path else "N/A"
            
            table.add_row(
                time_str,
                result.operation.value if result.operation else "N/A",
                str(result.source_path),
                dest_str,
                status
            )
        
        console.print(table)
    
    return tools_app


def register_tools_commands(main_app: typer.Typer):
    """Register tools commands with the main app"""
    tools_app = create_tools_commands()
    main_app.add_typer(tools_app)


if __name__ == "__main__":
    # Test the commands
    app = create_tools_commands()
    app()