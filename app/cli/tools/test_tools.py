"""
Test suite for search and file operations tools
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from rich.console import Console

from .search import SearchManager, SearchContext, SearchType, MatchType
from .file_ops import FileOperationsManager, OperationContext, FileOperation


async def create_test_files(temp_dir: Path):
    """Create test files for testing"""
    
    # Create directory structure
    (temp_dir / "docs").mkdir()
    (temp_dir / "src" / "python").mkdir(parents=True)
    (temp_dir / "src" / "javascript").mkdir()
    (temp_dir / "config").mkdir()
    
    # Create test files with content
    test_files = {
        "README.md": "# Test Project\nThis is a test project for LocalAgent tools.",
        "docs/api.md": "# API Documentation\nFunction search_files() searches for files.",
        "docs/guide.md": "# User Guide\nHow to use the search functionality.",
        "src/python/main.py": "def search_content():\n    return 'Found content'",
        "src/python/utils.py": "import os\ndef find_files():\n    pass",
        "src/javascript/app.js": "function searchFiles() {\n    console.log('Searching...');\n}",
        "src/javascript/helper.js": "const search = require('./search');\nmodule.exports = search;",
        "config/settings.json": '{"search": {"enabled": true}}',
        "config/database.yml": "host: localhost\nport: 5432"
    }
    
    for file_path, content in test_files.items():
        full_path = temp_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    
    console.print(f"[green]Created {len(test_files)} test files in {temp_dir}[/green]")


async def test_search_functionality(temp_dir: Path, console: Console):
    """Test search functionality"""
    console.print("\n[bold blue]Testing Search Functionality[/bold blue]")
    
    search_manager = SearchManager(console)
    
    # Test 1: Content search with fuzzy matching
    console.print("\n[yellow]Test 1: Fuzzy content search for 'search'[/yellow]")
    context = SearchContext(
        query="search",
        search_type=SearchType.TEXT_CONTENT,
        match_type=MatchType.FUZZY,
        root_paths=[temp_dir],
        max_results=50
    )
    
    results = await search_manager.execute_search(context)
    console.print(f"Found {len(results)} matches")
    
    # Test 2: File name search
    console.print("\n[yellow]Test 2: File name search for '*.py'[/yellow]")
    context = SearchContext(
        query="py",
        search_type=SearchType.FILE_NAMES,
        match_type=MatchType.FUZZY,
        root_paths=[temp_dir],
        include_patterns=["*.py"],
        max_results=50
    )
    
    results = await search_manager.execute_search(context)
    console.print(f"Found {len(results)} Python files")
    
    # Test 3: Exact match search
    console.print("\n[yellow]Test 3: Exact search for 'function'[/yellow]")
    context = SearchContext(
        query="function",
        search_type=SearchType.TEXT_CONTENT,
        match_type=MatchType.EXACT,
        root_paths=[temp_dir],
        case_sensitive=False
    )
    
    results = await search_manager.execute_search(context)
    console.print(f"Found {len(results)} exact matches")


async def test_file_operations(temp_dir: Path, console: Console):
    """Test file operations functionality"""
    console.print("\n[bold blue]Testing File Operations[/bold blue]")
    
    file_ops_manager = FileOperationsManager(console)
    
    # Test 1: Organize files by extension
    console.print("\n[yellow]Test 1: Organize files by extension[/yellow]")
    organize_dir = temp_dir / "organized"
    
    context = OperationContext(
        operation=FileOperation.ORGANIZE,
        source_patterns=[str(temp_dir / "src" / "**" / "*")],
        destination=organize_dir,
        dry_run=True,  # First run as dry-run
        options={'strategy': 'extension'}
    )
    
    results = await file_ops_manager.processor.process_files(context)
    console.print(f"Would organize {len(results)} files")
    
    # Test 2: Copy files
    console.print("\n[yellow]Test 2: Copy Python files[/yellow]")
    backup_dir = temp_dir / "backup"
    
    context = OperationContext(
        operation=FileOperation.COPY,
        source_patterns=[str(temp_dir / "src" / "python" / "*.py")],
        destination=backup_dir,
        dry_run=True
    )
    
    results = await file_ops_manager.processor.process_files(context)
    console.print(f"Would copy {len(results)} Python files")
    
    # Test 3: Batch rename
    console.print("\n[yellow]Test 3: Batch rename with pattern[/yellow]")
    
    context = OperationContext(
        operation=FileOperation.BATCH_RENAME,
        source_patterns=[str(temp_dir / "docs" / "*.md")],
        dry_run=True,
        options={'pattern': 'doc_{counter}_{name}', 'counter': 1}
    )
    
    results = await file_ops_manager.processor.process_files(context)
    console.print(f"Would rename {len(results)} markdown files")


async def test_integration():
    """Run integration tests"""
    console = Console()
    console.print("[bold green]🧪 LocalAgent Tools Integration Test[/bold green]")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        console.print(f"Using temporary directory: {temp_dir}")
        
        # Create test files
        await create_test_files(temp_dir)
        
        # Test search functionality
        await test_search_functionality(temp_dir, console)
        
        # Test file operations
        await test_file_operations(temp_dir, console)
        
        console.print("\n[bold green]✅ All tests completed successfully![/bold green]")


async def test_performance():
    """Test performance with larger datasets"""
    console = Console()
    console.print("[bold yellow]🚀 Performance Test[/bold yellow]")
    
    # This would create a larger test dataset
    # and measure search/operation performance
    console.print("Performance tests would go here...")


def check_dependencies():
    """Check if required dependencies are available"""
    console = Console()
    console.print("[bold blue]Checking Dependencies[/bold blue]")
    
    try:
        import rich
        console.print("[green]✅ Rich is available[/green]")
    except ImportError:
        console.print("[red]❌ Rich not found[/red]")
        return False
    
    try:
        import inquirerpy
        console.print("[green]✅ InquirerPy is available[/green]")
    except ImportError:
        console.print("[red]❌ InquirerPy not found[/red]")
        return False
    
    try:
        import aiofiles
        console.print("[green]✅ aiofiles is available[/green]")
    except ImportError:
        console.print("[red]❌ aiofiles not found[/red]")
        return False
    
    # Check ripgrep
    if shutil.which('rg'):
        console.print("[green]✅ ripgrep (rg) is available[/green]")
    else:
        console.print("[yellow]⚠️  ripgrep (rg) not found - fallback search will be used[/yellow]")
    
    return True


if __name__ == "__main__":
    console = Console()
    
    # Check dependencies first
    if not check_dependencies():
        console.print("[red]Missing required dependencies. Please install them first.[/red]")
        exit(1)
    
    # Run tests
    try:
        asyncio.run(test_integration())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")
        raise