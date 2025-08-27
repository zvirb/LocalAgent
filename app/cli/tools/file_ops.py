"""
Batch File Operations with Rich Progress Display
Modern file manipulation utilities with interactive features
"""

import asyncio
import shutil
import zipfile
import tarfile
import gzip
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, AsyncGenerator, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import hashlib
from datetime import datetime
import mimetypes

import aiofiles
from rich.console import Console
from rich.progress import (
    Progress, 
    TaskID, 
    BarColumn, 
    TextColumn, 
    TimeRemainingColumn,
    TransferSpeedColumn,
    FileSizeColumn
)
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.prompt import Confirm, Prompt
# TODO: Re-enable inquirerpy when properly installed
# from inquirerpy import prompt
from rich.prompt import Prompt, Confirm
# from inquirerpy.base.control import Choice


class FileOperation(Enum):
    """Supported file operations"""
    COPY = "copy"
    MOVE = "move"
    RENAME = "rename"
    DELETE = "delete"
    COMPRESS = "compress"
    EXTRACT = "extract"
    ORGANIZE = "organize"
    DEDUPLICATE = "deduplicate"
    PERMISSION_CHANGE = "chmod"
    BATCH_RENAME = "batch_rename"


class CompressionFormat(Enum):
    """Supported compression formats"""
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar.gz"
    TAR_BZ2 = "tar.bz2"
    GZIP = "gz"


class OrganizeStrategy(Enum):
    """File organization strategies"""
    BY_EXTENSION = "extension"
    BY_DATE = "date"
    BY_SIZE = "size"
    BY_TYPE = "mime_type"
    CUSTOM = "custom"


@dataclass
class FileOperationResult:
    """Result of a file operation"""
    source_path: Path
    destination_path: Optional[Path] = None
    operation: FileOperation = None
    success: bool = False
    error: Optional[str] = None
    bytes_processed: int = 0
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationContext:
    """Context for batch file operations"""
    operation: FileOperation
    source_patterns: List[str] = field(default_factory=list)
    destination: Optional[Path] = None
    options: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    backup: bool = False
    overwrite: bool = False
    preserve_permissions: bool = True
    filter_func: Optional[Callable[[Path], bool]] = None


class FileProcessor:
    """Core file processing engine"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.operation_history: List[FileOperationResult] = []
    
    async def process_files(
        self, 
        context: OperationContext,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[FileOperationResult]:
        """Process files according to the operation context"""
        
        # Collect files to process
        files_to_process = await self._collect_files(context)
        
        if not files_to_process:
            self.console.print("[yellow]No files found matching the criteria[/yellow]")
            return []
        
        if context.dry_run:
            self.console.print(f"[blue]Dry run: Would process {len(files_to_process)} files[/blue]")
            self._display_file_list(files_to_process, "Files that would be processed:")
            return []
        
        # Confirm operation if not in dry run mode
        if not await self._confirm_operation(context, files_to_process):
            self.console.print("[yellow]Operation cancelled[/yellow]")
            return []
        
        # Execute operations with progress tracking
        return await self._execute_operations(context, files_to_process, progress_callback)
    
    async def _collect_files(self, context: OperationContext) -> List[Path]:
        """Collect files matching the source patterns"""
        all_files = []
        
        for pattern in context.source_patterns:
            pattern_path = Path(pattern)
            
            if pattern_path.is_file():
                all_files.append(pattern_path)
            elif pattern_path.is_dir():
                # Add all files in directory
                for file_path in pattern_path.rglob('*'):
                    if file_path.is_file():
                        all_files.append(file_path)
            else:
                # Treat as glob pattern
                base_path = Path('.')
                for match in base_path.glob(pattern):
                    if match.is_file():
                        all_files.append(match)
        
        # Apply custom filter if provided
        if context.filter_func:
            all_files = [f for f in all_files if context.filter_func(f)]
        
        # Remove duplicates and sort
        return sorted(list(set(all_files)))
    
    async def _confirm_operation(self, context: OperationContext, files: List[Path]) -> bool:
        """Confirm the operation with the user"""
        self.console.print(f"\n[bold]Operation: {context.operation.value.upper()}[/bold]")
        self.console.print(f"Files to process: {len(files)}")
        
        if len(files) <= 10:
            self._display_file_list(files, "Files:")
        else:
            self._display_file_list(files[:5], "First 5 files:")
            self.console.print(f"[dim]... and {len(files) - 5} more files[/dim]")
        
        return Confirm.ask("\nProceed with operation?", default=False)
    
    def _display_file_list(self, files: List[Path], title: str):
        """Display a list of files in a formatted table"""
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("File", style="cyan")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Modified", style="blue")
        
        for file_path in files:
            try:
                stat = file_path.stat()
                size = self._format_size(stat.st_size)
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                table.add_row(str(file_path), size, modified)
            except OSError:
                table.add_row(str(file_path), "N/A", "N/A")
        
        self.console.print(table)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    async def _execute_operations(
        self, 
        context: OperationContext, 
        files: List[Path],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[FileOperationResult]:
        """Execute the file operations with progress tracking"""
        
        results = []
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            FileSizeColumn(),
            TransferSpeedColumn(),
            console=self.console
        ) as progress:
            
            main_task = progress.add_task(
                f"Processing {context.operation.value}...",
                total=len(files)
            )
            
            for i, file_path in enumerate(files):
                try:
                    result = await self._execute_single_operation(context, file_path, progress)
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback(i + 1, len(files))
                    
                    progress.update(main_task, advance=1)
                    
                except Exception as e:
                    error_result = FileOperationResult(
                        source_path=file_path,
                        operation=context.operation,
                        success=False,
                        error=str(e)
                    )
                    results.append(error_result)
                    progress.update(main_task, advance=1)
        
        # Display summary
        self._display_operation_summary(results, context)
        
        # Add to history
        self.operation_history.extend(results)
        
        return results
    
    async def _execute_single_operation(
        self, 
        context: OperationContext, 
        file_path: Path,
        progress: Progress
    ) -> FileOperationResult:
        """Execute a single file operation"""
        
        start_time = datetime.now()
        
        try:
            if context.operation == FileOperation.COPY:
                return await self._copy_file(context, file_path)
            elif context.operation == FileOperation.MOVE:
                return await self._move_file(context, file_path)
            elif context.operation == FileOperation.RENAME:
                return await self._rename_file(context, file_path)
            elif context.operation == FileOperation.DELETE:
                return await self._delete_file(context, file_path)
            elif context.operation == FileOperation.COMPRESS:
                return await self._compress_file(context, file_path)
            elif context.operation == FileOperation.EXTRACT:
                return await self._extract_file(context, file_path)
            elif context.operation == FileOperation.ORGANIZE:
                return await self._organize_file(context, file_path)
            elif context.operation == FileOperation.BATCH_RENAME:
                return await self._batch_rename_file(context, file_path)
            else:
                raise ValueError(f"Unsupported operation: {context.operation}")
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return FileOperationResult(
                source_path=file_path,
                operation=context.operation,
                success=False,
                error=str(e),
                duration=duration
            )
    
    async def _copy_file(self, context: OperationContext, file_path: Path) -> FileOperationResult:
        """Copy a single file"""
        destination = self._get_destination_path(context, file_path)
        
        # Create destination directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle overwrite policy
        if destination.exists() and not context.overwrite:
            if not context.options.get('auto_rename', False):
                raise FileExistsError(f"Destination exists: {destination}")
            destination = self._get_unique_path(destination)
        
        # Perform copy with progress tracking
        start_time = datetime.now()
        bytes_processed = 0
        
        async with aiofiles.open(file_path, 'rb') as src:
            async with aiofiles.open(destination, 'wb') as dst:
                while chunk := await src.read(8192):  # 8KB chunks
                    await dst.write(chunk)
                    bytes_processed += len(chunk)
        
        # Preserve permissions if requested
        if context.preserve_permissions:
            shutil.copystat(file_path, destination)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return FileOperationResult(
            source_path=file_path,
            destination_path=destination,
            operation=FileOperation.COPY,
            success=True,
            bytes_processed=bytes_processed,
            duration=duration
        )
    
    async def _move_file(self, context: OperationContext, file_path: Path) -> FileOperationResult:
        """Move a single file"""
        destination = self._get_destination_path(context, file_path)
        
        # Create destination directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle overwrite policy
        if destination.exists() and not context.overwrite:
            if not context.options.get('auto_rename', False):
                raise FileExistsError(f"Destination exists: {destination}")
            destination = self._get_unique_path(destination)
        
        start_time = datetime.now()
        bytes_processed = file_path.stat().st_size
        
        # Perform move
        shutil.move(str(file_path), str(destination))
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return FileOperationResult(
            source_path=file_path,
            destination_path=destination,
            operation=FileOperation.MOVE,
            success=True,
            bytes_processed=bytes_processed,
            duration=duration
        )
    
    async def _rename_file(self, context: OperationContext, file_path: Path) -> FileOperationResult:
        """Rename a single file"""
        new_name = context.options.get('new_name')
        if not new_name:
            raise ValueError("new_name is required for rename operation")
        
        destination = file_path.parent / new_name
        
        start_time = datetime.now()
        file_path.rename(destination)
        duration = (datetime.now() - start_time).total_seconds()
        
        return FileOperationResult(
            source_path=file_path,
            destination_path=destination,
            operation=FileOperation.RENAME,
            success=True,
            duration=duration
        )
    
    async def _delete_file(self, context: OperationContext, file_path: Path) -> FileOperationResult:
        """Delete a single file"""
        start_time = datetime.now()
        bytes_processed = file_path.stat().st_size
        
        if context.backup:
            # Create backup before deletion
            backup_path = Path(f"{file_path}.backup.{int(start_time.timestamp())}")
            shutil.copy2(file_path, backup_path)
        
        file_path.unlink()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return FileOperationResult(
            source_path=file_path,
            operation=FileOperation.DELETE,
            success=True,
            bytes_processed=bytes_processed,
            duration=duration
        )
    
    async def _compress_file(self, context: OperationContext, file_path: Path) -> FileOperationResult:
        """Compress a single file"""
        compression_format = CompressionFormat(context.options.get('format', 'zip'))
        
        if compression_format == CompressionFormat.ZIP:
            destination = file_path.with_suffix('.zip')
            return await self._compress_zip(file_path, destination)
        elif compression_format in [CompressionFormat.TAR, CompressionFormat.TAR_GZ, CompressionFormat.TAR_BZ2]:
            return await self._compress_tar(file_path, compression_format)
        elif compression_format == CompressionFormat.GZIP:
            return await self._compress_gzip(file_path)
        else:
            raise ValueError(f"Unsupported compression format: {compression_format}")
    
    async def _compress_zip(self, file_path: Path, destination: Path) -> FileOperationResult:
        """Compress file to ZIP format"""
        start_time = datetime.now()
        bytes_processed = 0
        
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, file_path.name)
            bytes_processed = file_path.stat().st_size
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return FileOperationResult(
            source_path=file_path,
            destination_path=destination,
            operation=FileOperation.COMPRESS,
            success=True,
            bytes_processed=bytes_processed,
            duration=duration
        )
    
    async def _organize_file(self, context: OperationContext, file_path: Path) -> FileOperationResult:
        """Organize file according to strategy"""
        strategy = OrganizeStrategy(context.options.get('strategy', 'extension'))
        base_path = context.destination or Path('organized')
        
        if strategy == OrganizeStrategy.BY_EXTENSION:
            ext = file_path.suffix.lstrip('.') or 'no_extension'
            destination_dir = base_path / ext
        elif strategy == OrganizeStrategy.BY_DATE:
            stat = file_path.stat()
            date = datetime.fromtimestamp(stat.st_mtime)
            destination_dir = base_path / date.strftime("%Y/%m")
        elif strategy == OrganizeStrategy.BY_SIZE:
            size = file_path.stat().st_size
            if size < 1024 * 1024:  # < 1MB
                destination_dir = base_path / "small"
            elif size < 100 * 1024 * 1024:  # < 100MB
                destination_dir = base_path / "medium"
            else:
                destination_dir = base_path / "large"
        elif strategy == OrganizeStrategy.BY_TYPE:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                type_category = mime_type.split('/')[0]
                destination_dir = base_path / type_category
            else:
                destination_dir = base_path / "unknown"
        else:
            raise ValueError(f"Unsupported organize strategy: {strategy}")
        
        # Create a new context for the move operation
        move_context = OperationContext(
            operation=FileOperation.MOVE,
            destination=destination_dir,
            overwrite=context.overwrite,
            preserve_permissions=context.preserve_permissions
        )
        
        return await self._move_file(move_context, file_path)
    
    async def _batch_rename_file(self, context: OperationContext, file_path: Path) -> FileOperationResult:
        """Batch rename file according to pattern"""
        pattern = context.options.get('pattern', '{name}_{counter}')
        counter = context.options.get('counter', 1)
        
        # Replace placeholders
        name_parts = {
            'name': file_path.stem,
            'ext': file_path.suffix,
            'counter': str(counter).zfill(3),
            'date': datetime.now().strftime("%Y%m%d"),
            'time': datetime.now().strftime("%H%M%S")
        }
        
        new_name = pattern.format(**name_parts) + file_path.suffix
        destination = file_path.parent / new_name
        
        # Ensure unique name
        if destination.exists():
            destination = self._get_unique_path(destination)
        
        start_time = datetime.now()
        file_path.rename(destination)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Update counter for next file
        context.options['counter'] = counter + 1
        
        return FileOperationResult(
            source_path=file_path,
            destination_path=destination,
            operation=FileOperation.BATCH_RENAME,
            success=True,
            duration=duration
        )
    
    def _get_destination_path(self, context: OperationContext, file_path: Path) -> Path:
        """Get the destination path for a file operation"""
        if not context.destination:
            raise ValueError("Destination is required for this operation")
        
        if context.destination.is_dir():
            return context.destination / file_path.name
        else:
            return context.destination
    
    def _get_unique_path(self, path: Path) -> Path:
        """Get a unique path by appending counter if file exists"""
        if not path.exists():
            return path
        
        counter = 1
        base_name = path.stem
        suffix = path.suffix
        parent = path.parent
        
        while True:
            new_name = f"{base_name}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _display_operation_summary(self, results: List[FileOperationResult], context: OperationContext):
        """Display operation summary"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        total_bytes = sum(r.bytes_processed for r in successful)
        total_duration = sum(r.duration for r in results)
        
        panel_content = f"""
[green]✅ Successful: {len(successful)}[/green]
[red]❌ Failed: {len(failed)}[/red]
[blue]📊 Total size: {self._format_size(total_bytes)}[/blue]
[yellow]⏱️  Total time: {total_duration:.2f}s[/yellow]
"""
        
        if failed:
            panel_content += "\n[bold red]Errors:[/bold red]\n"
            for result in failed[:5]:  # Show first 5 errors
                panel_content += f"• {result.source_path}: {result.error}\n"
            if len(failed) > 5:
                panel_content += f"... and {len(failed) - 5} more errors\n"
        
        panel = Panel(panel_content.strip(), title=f"{context.operation.value.title()} Summary", border_style="blue")
        self.console.print("\n")
        self.console.print(panel)


class FileOperationsManager:
    """High-level file operations manager with interactive interface"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.processor = FileProcessor(console)
        self.presets: Dict[str, OperationContext] = {}
    
    async def interactive_operations(self) -> Optional[List[FileOperationResult]]:
        """Start interactive file operations session"""
        self.console.print("[bold blue]🗂️  LocalAgent File Operations[/bold blue]")
        self.console.print()
        
        # Get operation context through interactive prompts
        context = await self._get_operation_context()
        if not context:
            return None
        
        # Execute operations
        return await self.processor.process_files(context)
    
    async def _get_operation_context(self) -> Optional[OperationContext]:
        """Get operation context through interactive prompts"""
        questions = [
            {
                'type': 'list',
                'name': 'operation',
                'message': 'Select file operation:',
                'choices': [
                    Choice(FileOperation.COPY, name="Copy files"),
                    Choice(FileOperation.MOVE, name="Move files"),
                    Choice(FileOperation.RENAME, name="Rename files"),
                    Choice(FileOperation.DELETE, name="Delete files"),
                    Choice(FileOperation.COMPRESS, name="Compress files"),
                    Choice(FileOperation.ORGANIZE, name="Organize files"),
                    Choice(FileOperation.BATCH_RENAME, name="Batch rename files"),
                    Choice(FileOperation.DEDUPLICATE, name="Remove duplicates")
                ]
            },
            {
                'type': 'input',
                'name': 'source_patterns',
                'message': 'Source patterns (comma-separated, e.g., "*.txt,docs/*.md"):',
                'validate': lambda x: len(x.strip()) > 0 or "At least one pattern is required"
            },
            {
                'type': 'confirm',
                'name': 'dry_run',
                'message': 'Perform dry run first?',
                'default': True
            }
        ]
        
        answers = prompt(questions)
        if not answers:
            return None
        
        operation = answers['operation']
        source_patterns = [p.strip() for p in answers['source_patterns'].split(',')]
        
        # Get operation-specific options
        options = await self._get_operation_specific_options(operation)
        if options is None:
            return None
        
        return OperationContext(
            operation=operation,
            source_patterns=source_patterns,
            dry_run=answers['dry_run'],
            **options
        )
    
    async def _get_operation_specific_options(self, operation: FileOperation) -> Optional[Dict[str, Any]]:
        """Get operation-specific options"""
        options = {}
        
        if operation in [FileOperation.COPY, FileOperation.MOVE, FileOperation.ORGANIZE]:
            destination = Prompt.ask("Destination path")
            if not destination:
                return None
            options['destination'] = Path(destination)
            options['overwrite'] = Confirm.ask("Overwrite existing files?", default=False)
        
        elif operation == FileOperation.COMPRESS:
            format_choices = [
                Choice(CompressionFormat.ZIP, name="ZIP"),
                Choice(CompressionFormat.TAR_GZ, name="TAR.GZ"),
                Choice(CompressionFormat.TAR_BZ2, name="TAR.BZ2")
            ]
            
            format_answer = prompt([{
                'type': 'list',
                'name': 'format',
                'message': 'Compression format:',
                'choices': format_choices
            }])
            
            if not format_answer:
                return None
            
            options['options'] = {'format': format_answer['format'].value}
        
        elif operation == FileOperation.ORGANIZE:
            strategy_choices = [
                Choice(OrganizeStrategy.BY_EXTENSION, name="By file extension"),
                Choice(OrganizeStrategy.BY_DATE, name="By modification date"),
                Choice(OrganizeStrategy.BY_SIZE, name="By file size"),
                Choice(OrganizeStrategy.BY_TYPE, name="By MIME type")
            ]
            
            strategy_answer = prompt([{
                'type': 'list',
                'name': 'strategy',
                'message': 'Organization strategy:',
                'choices': strategy_choices
            }])
            
            if not strategy_answer:
                return None
            
            destination = Prompt.ask("Base organization directory", default="organized")
            options['destination'] = Path(destination)
            options['options'] = {'strategy': strategy_answer['strategy'].value}
        
        elif operation == FileOperation.BATCH_RENAME:
            pattern = Prompt.ask("Rename pattern (use {name}, {counter}, {date}, {time})", 
                               default="{name}_{counter}")
            options['options'] = {'pattern': pattern, 'counter': 1}
        
        elif operation == FileOperation.DELETE:
            options['backup'] = Confirm.ask("Create backup before deletion?", default=True)
        
        return options
    
    def save_preset(self, name: str, context: OperationContext):
        """Save operation context as preset"""
        self.presets[name] = context
        self.console.print(f"[green]Preset '{name}' saved[/green]")
    
    def load_preset(self, name: str) -> Optional[OperationContext]:
        """Load operation context from preset"""
        if name in self.presets:
            return self.presets[name]
        return None
    
    def list_presets(self):
        """List available presets"""
        if not self.presets:
            self.console.print("[yellow]No presets saved[/yellow]")
            return
        
        table = Table(title="Saved Presets", show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("Operation", style="green")
        table.add_column("Patterns", style="yellow")
        
        for name, context in self.presets.items():
            patterns = ", ".join(context.source_patterns)
            table.add_row(name, context.operation.value, patterns)
        
        self.console.print(table)
    
    def get_operation_history(self) -> List[FileOperationResult]:
        """Get file operation history"""
        return self.processor.operation_history.copy()


# Convenience function for CLI integration
async def file_operations_interactive(console: Optional[Console] = None) -> Optional[List[FileOperationResult]]:
    """Convenience function for interactive file operations"""
    manager = FileOperationsManager(console)
    return await manager.interactive_operations()


# CLI command integration example
def create_file_ops_commands(app):
    """Create file operations CLI commands"""
    
    @app.command()
    def file_ops(
        operation: str = None,
        source: str = None,
        destination: str = None,
        dry_run: bool = False
    ):
        """Batch file operations with rich interface"""
        if not operation:
            # Interactive mode
            return asyncio.run(file_operations_interactive())
        
        # Direct operation mode
        try:
            op_enum = FileOperation(operation.lower())
        except ValueError:
            console = Console()
            console.print(f"[red]Invalid operation: {operation}[/red]")
            return
        
        context = OperationContext(
            operation=op_enum,
            source_patterns=source.split(',') if source else [],
            destination=Path(destination) if destination else None,
            dry_run=dry_run
        )
        
        manager = FileOperationsManager()
        asyncio.run(manager.processor.process_files(context))


if __name__ == "__main__":
    # Test the file operations functionality
    async def test_file_ops():
        console = Console()
        manager = FileOperationsManager(console)
        await manager.interactive_operations()
    
    asyncio.run(test_file_ops())