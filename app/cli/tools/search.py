"""
Advanced Search Utilities with Fuzzy Matching
Modern search interface with ripgrep integration and fzf-like features
"""

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.panel import Panel
from rich.tree import Tree
# TODO: Re-enable inquirerpy when properly installed
# from inquirerpy import prompt
# from inquirerpy.base.control import Choice
# from inquirerpy.shortcuts import checkbox, select, text, confirm

from rich.prompt import Prompt, Confirm


class SearchType(Enum):
    """Search operation types"""
    TEXT_CONTENT = "content"
    FILE_NAMES = "files"
    DIRECTORY_NAMES = "dirs"
    MIXED = "mixed"


class MatchType(Enum):
    """Matching algorithm types"""
    EXACT = "exact"
    FUZZY = "fuzzy"
    REGEX = "regex"
    GLOB = "glob"


@dataclass
class SearchResult:
    """Search result with rich metadata"""
    path: Path
    match_type: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    matched_text: Optional[str] = None
    confidence_score: float = 1.0
    file_size: Optional[int] = None
    file_modified: Optional[float] = None
    file_type: Optional[str] = None


@dataclass
class SearchContext:
    """Search execution context and parameters"""
    query: str
    search_type: SearchType = SearchType.TEXT_CONTENT
    match_type: MatchType = MatchType.FUZZY
    root_paths: List[Path] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    file_types: List[str] = field(default_factory=list)
    max_results: int = 100
    case_sensitive: bool = False
    context_lines: int = 2
    min_confidence: float = 0.3


class RipgrepIntegrator:
    """High-performance ripgrep integration"""
    
    def __init__(self):
        self.rg_available = shutil.which('rg') is not None
        if not self.rg_available:
            raise RuntimeError("ripgrep (rg) not found. Please install ripgrep for optimal search performance.")
    
    async def search_content(self, context: SearchContext) -> List[SearchResult]:
        """Search file contents using ripgrep"""
        cmd = self._build_ripgrep_command(context)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0 and process.returncode != 1:  # 1 is "no matches"
                raise RuntimeError(f"ripgrep error: {stderr.decode()}")
            
            return self._parse_ripgrep_output(stdout.decode(), context)
            
        except Exception as e:
            raise RuntimeError(f"Failed to execute ripgrep search: {e}")
    
    def _build_ripgrep_command(self, context: SearchContext) -> List[str]:
        """Build optimized ripgrep command"""
        cmd = ['rg', '--json']
        
        # Basic search parameters
        if not context.case_sensitive:
            cmd.append('--ignore-case')
        
        if context.context_lines > 0:
            cmd.extend(['--context', str(context.context_lines)])
        
        # Pattern type handling
        if context.match_type == MatchType.REGEX:
            cmd.extend(['--regexp', context.query])
        elif context.match_type == MatchType.EXACT:
            cmd.extend(['--fixed-strings', context.query])
        else:
            # For fuzzy matching, we'll use regex approximation
            fuzzy_pattern = self._create_fuzzy_regex(context.query)
            cmd.extend(['--regexp', fuzzy_pattern])
        
        # File type filters
        for file_type in context.file_types:
            cmd.extend(['--type', file_type])
        
        # Include/exclude patterns
        for pattern in context.include_patterns:
            cmd.extend(['--glob', pattern])
        
        for pattern in context.exclude_patterns:
            cmd.extend(['--glob', f'!{pattern}'])
        
        # Paths to search
        for path in context.root_paths:
            cmd.append(str(path))
        
        if not context.root_paths:
            cmd.append('.')
        
        return cmd
    
    def _create_fuzzy_regex(self, query: str) -> str:
        """Create fuzzy matching regex pattern"""
        # Simple fuzzy matching: allow any character between query characters
        if len(query) <= 1:
            return re.escape(query)
        
        fuzzy_chars = []
        for char in query:
            if char.isalnum():
                fuzzy_chars.append(f'{re.escape(char)}.*?')
            else:
                fuzzy_chars.append(re.escape(char))
        
        return ''.join(fuzzy_chars).rstrip('.*?')
    
    def _parse_ripgrep_output(self, output: str, context: SearchContext) -> List[SearchResult]:
        """Parse ripgrep JSON output into SearchResult objects"""
        results = []
        
        for line in output.strip().split('\n'):
            if not line:
                continue
            
            try:
                data = json.loads(line)
                if data.get('type') != 'match':
                    continue
                
                match_data = data['data']
                path = Path(match_data['path']['text'])
                
                result = SearchResult(
                    path=path,
                    match_type="ripgrep",
                    line_number=match_data['line_number'],
                    matched_text=match_data['lines']['text'].strip(),
                    confidence_score=self._calculate_confidence(
                        context.query, 
                        match_data['lines']['text'],
                        context.match_type
                    )
                )
                
                # Add file metadata
                if path.exists():
                    stat = path.stat()
                    result.file_size = stat.st_size
                    result.file_modified = stat.st_mtime
                    result.file_type = path.suffix.lower()
                
                # Filter by confidence if using fuzzy matching
                if context.match_type == MatchType.FUZZY and result.confidence_score < context.min_confidence:
                    continue
                
                results.append(result)
                
                if len(results) >= context.max_results:
                    break
                    
            except json.JSONDecodeError:
                continue
        
        return sorted(results, key=lambda x: x.confidence_score, reverse=True)
    
    def _calculate_confidence(self, query: str, text: str, match_type: MatchType) -> float:
        """Calculate match confidence score"""
        if match_type == MatchType.EXACT:
            return 1.0 if query.lower() in text.lower() else 0.0
        
        # Fuzzy matching confidence based on character overlap and proximity
        query_lower = query.lower()
        text_lower = text.lower()
        
        if query_lower == text_lower:
            return 1.0
        
        # Calculate character overlap
        query_chars = set(query_lower)
        text_chars = set(text_lower)
        overlap = len(query_chars & text_chars) / len(query_chars) if query_chars else 0
        
        # Calculate sequence similarity (simplified Levenshtein-like)
        if query_lower in text_lower:
            position_score = 1.0 - (text_lower.index(query_lower) / len(text_lower))
        else:
            position_score = 0.5
        
        return (overlap * 0.7 + position_score * 0.3)


class FuzzyFileMatcher:
    """Fuzzy file name matching with advanced algorithms"""
    
    def __init__(self):
        self.cache: Dict[str, List[Path]] = {}
    
    async def find_files(self, context: SearchContext) -> List[SearchResult]:
        """Find files using fuzzy name matching"""
        all_files = []
        
        # Collect files from all root paths
        for root_path in context.root_paths or [Path('.')]:
            if root_path.is_file():
                all_files.append(root_path)
            else:
                async for file_path in self._scan_directory(root_path, context):
                    all_files.append(file_path)
        
        # Apply fuzzy matching
        results = []
        for file_path in all_files:
            confidence = self._calculate_file_name_confidence(context.query, file_path.name)
            
            if confidence >= context.min_confidence:
                result = SearchResult(
                    path=file_path,
                    match_type="fuzzy_file",
                    confidence_score=confidence,
                    file_type=file_path.suffix.lower()
                )
                
                # Add file metadata
                if file_path.exists():
                    stat = file_path.stat()
                    result.file_size = stat.st_size
                    result.file_modified = stat.st_mtime
                
                results.append(result)
        
        # Sort by confidence and limit results
        results.sort(key=lambda x: x.confidence_score, reverse=True)
        return results[:context.max_results]
    
    async def _scan_directory(self, root_path: Path, context: SearchContext) -> AsyncGenerator[Path, None]:
        """Asynchronously scan directory with filters"""
        try:
            for item in root_path.rglob('*'):
                if not item.is_file():
                    continue
                
                # Apply include/exclude patterns
                if context.exclude_patterns and any(item.match(pattern) for pattern in context.exclude_patterns):
                    continue
                
                if context.include_patterns and not any(item.match(pattern) for pattern in context.include_patterns):
                    continue
                
                # Apply file type filters
                if context.file_types and item.suffix.lower().lstrip('.') not in context.file_types:
                    continue
                
                yield item
                
        except PermissionError:
            pass  # Skip inaccessible directories
    
    def _calculate_file_name_confidence(self, query: str, filename: str) -> float:
        """Calculate fuzzy matching confidence for file names"""
        if not query or not filename:
            return 0.0
        
        query_lower = query.lower()
        filename_lower = filename.lower()
        
        # Exact match
        if query_lower == filename_lower:
            return 1.0
        
        # Substring match
        if query_lower in filename_lower:
            position = filename_lower.index(query_lower)
            length_ratio = len(query_lower) / len(filename_lower)
            position_score = 1.0 - (position / len(filename_lower))
            return length_ratio * 0.6 + position_score * 0.4
        
        # Character sequence matching
        return self._sequence_similarity(query_lower, filename_lower)
    
    def _sequence_similarity(self, query: str, target: str) -> float:
        """Calculate sequence similarity using dynamic programming"""
        if not query or not target:
            return 0.0
        
        # Simple implementation of longest common subsequence ratio
        query_chars = list(query)
        target_chars = list(target)
        
        # Count matching characters in order
        matches = 0
        target_idx = 0
        
        for query_char in query_chars:
            while target_idx < len(target_chars):
                if target_chars[target_idx] == query_char:
                    matches += 1
                    target_idx += 1
                    break
                target_idx += 1
        
        return matches / len(query_chars) if query_chars else 0.0


class SearchManager:
    """Main search manager with interactive interface"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.ripgrep = RipgrepIntegrator() if shutil.which('rg') else None
        self.fuzzy_matcher = FuzzyFileMatcher()
        self.search_history: List[SearchContext] = []
    
    async def interactive_search(self) -> Optional[List[SearchResult]]:
        """Start interactive search session"""
        self.console.print("[bold blue]🔍 LocalAgent Advanced Search[/bold blue]")
        self.console.print()
        
        # Get search parameters through interactive prompts
        context = await self._get_search_context()
        if not context:
            return None
        
        # Execute search
        return await self.execute_search(context)
    
    async def _get_search_context(self) -> Optional[SearchContext]:
        """Get search context through interactive prompts"""
        questions = [
            {
                'type': 'input',
                'name': 'query',
                'message': 'Enter search query:',
                'validate': lambda x: len(x.strip()) > 0 or "Query cannot be empty"
            },
            {
                'type': 'list',
                'name': 'search_type',
                'message': 'Select search type:',
                'choices': [
                    Choice(SearchType.TEXT_CONTENT, name="Search in file contents"),
                    Choice(SearchType.FILE_NAMES, name="Search file names"),
                    Choice(SearchType.DIRECTORY_NAMES, name="Search directory names"),
                    Choice(SearchType.MIXED, name="Search both content and names")
                ]
            },
            {
                'type': 'list',
                'name': 'match_type',
                'message': 'Select matching algorithm:',
                'choices': [
                    Choice(MatchType.FUZZY, name="Fuzzy matching (recommended)"),
                    Choice(MatchType.EXACT, name="Exact match"),
                    Choice(MatchType.REGEX, name="Regular expression"),
                    Choice(MatchType.GLOB, name="Glob pattern")
                ]
            },
            {
                'type': 'input',
                'name': 'root_paths',
                'message': 'Search paths (comma-separated, empty for current dir):',
                'default': ''
            },
            {
                'type': 'input',
                'name': 'include_patterns',
                'message': 'Include patterns (comma-separated, e.g., "*.py,*.js"):',
                'default': ''
            },
            {
                'type': 'input',
                'name': 'exclude_patterns', 
                'message': 'Exclude patterns (comma-separated, e.g., "node_modules,*.log"):',
                'default': '__pycache__,*.pyc,node_modules,*.log,.git'
            },
            {
                'type': 'input',
                'name': 'max_results',
                'message': 'Maximum results:',
                'default': '100',
                'validate': lambda x: x.isdigit() or "Must be a number"
            }
        ]
        
        answers = prompt(questions)
        
        if not answers:
            return None
        
        # Parse answers into SearchContext
        root_paths = []
        if answers['root_paths'].strip():
            root_paths = [Path(p.strip()) for p in answers['root_paths'].split(',')]
        
        include_patterns = []
        if answers['include_patterns'].strip():
            include_patterns = [p.strip() for p in answers['include_patterns'].split(',')]
        
        exclude_patterns = []
        if answers['exclude_patterns'].strip():
            exclude_patterns = [p.strip() for p in answers['exclude_patterns'].split(',')]
        
        return SearchContext(
            query=answers['query'].strip(),
            search_type=answers['search_type'],
            match_type=answers['match_type'],
            root_paths=root_paths,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_results=int(answers['max_results'])
        )
    
    async def execute_search(self, context: SearchContext) -> List[SearchResult]:
        """Execute search with progress display"""
        self.search_history.append(context)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("Searching...", total=None)
            
            try:
                if context.search_type == SearchType.TEXT_CONTENT:
                    if self.ripgrep:
                        progress.update(task, description="Searching content with ripgrep...")
                        results = await self.ripgrep.search_content(context)
                    else:
                        progress.update(task, description="Searching content (fallback)...")
                        results = await self._fallback_content_search(context)
                
                elif context.search_type == SearchType.FILE_NAMES:
                    progress.update(task, description="Searching file names...")
                    results = await self.fuzzy_matcher.find_files(context)
                
                elif context.search_type == SearchType.MIXED:
                    progress.update(task, description="Searching content and file names...")
                    content_results = []
                    if self.ripgrep:
                        content_results = await self.ripgrep.search_content(context)
                    else:
                        content_results = await self._fallback_content_search(context)
                    
                    file_results = await self.fuzzy_matcher.find_files(context)
                    results = content_results + file_results
                    results.sort(key=lambda x: x.confidence_score, reverse=True)
                    results = results[:context.max_results]
                
                else:
                    results = []
                
                progress.update(task, description=f"Found {len(results)} matches", completed=True)
                
            except Exception as e:
                progress.update(task, description=f"Search failed: {e}", completed=True)
                raise
        
        # Display results
        self._display_results(results, context)
        
        return results
    
    async def _fallback_content_search(self, context: SearchContext) -> List[SearchResult]:
        """Fallback content search when ripgrep is not available"""
        results = []
        
        for root_path in context.root_paths or [Path('.')]:
            async for file_path in self.fuzzy_matcher._scan_directory(root_path, context):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        if context.match_type == MatchType.EXACT:
                            if context.query.lower() in line.lower():
                                confidence = 1.0
                            else:
                                continue
                        else:
                            confidence = self._calculate_line_confidence(context.query, line)
                            if confidence < context.min_confidence:
                                continue
                        
                        result = SearchResult(
                            path=file_path,
                            match_type="fallback",
                            line_number=line_num,
                            matched_text=line.strip(),
                            confidence_score=confidence,
                            file_type=file_path.suffix.lower()
                        )
                        
                        results.append(result)
                        
                        if len(results) >= context.max_results:
                            return results
                
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        return sorted(results, key=lambda x: x.confidence_score, reverse=True)
    
    def _calculate_line_confidence(self, query: str, line: str) -> float:
        """Calculate confidence for fallback search"""
        if not query or not line:
            return 0.0
        
        query_lower = query.lower()
        line_lower = line.lower()
        
        if query_lower in line_lower:
            return 1.0
        
        # Simple fuzzy matching
        query_chars = set(query_lower)
        line_chars = set(line_lower)
        
        if not query_chars:
            return 0.0
        
        overlap = len(query_chars & line_chars) / len(query_chars)
        return overlap
    
    def _display_results(self, results: List[SearchResult], context: SearchContext):
        """Display search results with rich formatting"""
        if not results:
            self.console.print("[yellow]No matches found.[/yellow]")
            return
        
        self.console.print(f"\n[bold green]Found {len(results)} matches for '{context.query}'[/bold green]")
        
        # Group results by file for better display
        file_groups: Dict[Path, List[SearchResult]] = {}
        for result in results:
            if result.path not in file_groups:
                file_groups[result.path] = []
            file_groups[result.path].append(result)
        
        for file_path, file_results in file_groups.items():
            # File header
            self.console.print(f"\n[bold cyan]{file_path}[/bold cyan]")
            
            # Results table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Line", style="dim", width=6)
            table.add_column("Match", style="yellow")
            table.add_column("Confidence", style="green", width=10)
            
            for result in file_results[:5]:  # Show top 5 matches per file
                line_str = str(result.line_number) if result.line_number else "N/A"
                confidence_str = f"{result.confidence_score:.2f}"
                match_text = (result.matched_text or "")[:80]  # Truncate long lines
                
                table.add_row(line_str, match_text, confidence_str)
            
            self.console.print(table)
            
            if len(file_results) > 5:
                self.console.print(f"[dim]... and {len(file_results) - 5} more matches[/dim]")
    
    def get_search_history(self) -> List[SearchContext]:
        """Get search history"""
        return self.search_history.copy()
    
    async def repeat_last_search(self) -> Optional[List[SearchResult]]:
        """Repeat the last search"""
        if not self.search_history:
            self.console.print("[yellow]No previous searches to repeat.[/yellow]")
            return None
        
        last_context = self.search_history[-1]
        self.console.print(f"[blue]Repeating search for: '{last_context.query}'[/blue]")
        
        return await self.execute_search(last_context)


# Convenience function for CLI integration
async def search_interactive(console: Optional[Console] = None) -> Optional[List[SearchResult]]:
    """Convenience function for interactive search"""
    manager = SearchManager(console)
    return await manager.interactive_search()


# CLI command integration example
def create_search_commands(app):
    """Create search-related CLI commands"""
    
    @app.command()
    def search(
        query: str = None,
        content: bool = True,
        files: bool = False,
        fuzzy: bool = True,
        max_results: int = 100,
        include: str = None,
        exclude: str = None
    ):
        """Advanced search with fuzzy matching"""
        if not query:
            # Interactive mode
            return asyncio.run(search_interactive())
        
        # Direct search mode
        context = SearchContext(
            query=query,
            search_type=SearchType.TEXT_CONTENT if content else SearchType.FILE_NAMES,
            match_type=MatchType.FUZZY if fuzzy else MatchType.EXACT,
            max_results=max_results,
            include_patterns=include.split(',') if include else [],
            exclude_patterns=exclude.split(',') if exclude else []
        )
        
        manager = SearchManager()
        asyncio.run(manager.execute_search(context))


if __name__ == "__main__":
    # Test the search functionality
    async def test_search():
        console = Console()
        manager = SearchManager(console)
        await manager.interactive_search()
    
    asyncio.run(test_search())