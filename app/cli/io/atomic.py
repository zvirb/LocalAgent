"""
Atomic File Operations
Safe file manipulation with write-then-rename patterns
"""

import asyncio
import os
import tempfile
import json
import yaml
import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Dict, Union, Optional, List, Callable, AsyncContextManager
from contextlib import asynccontextmanager
import aiofiles
from rich.console import Console
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)
console = Console()

# Global audit trail instance (optional)
_global_audit_trail: Optional['AuditTrail'] = None

def set_global_audit_trail(audit_file: Union[str, Path]):
    """Set global audit trail for all atomic operations"""
    global _global_audit_trail
    _global_audit_trail = AuditTrail(audit_file)

def get_global_audit_trail() -> Optional['AuditTrail']:
    """Get global audit trail instance"""
    return _global_audit_trail

class AtomicWriteError(Exception):
    """Error during atomic write operation"""
    def __init__(self, message: str, original_error: Optional[Exception] = None, 
                 operation_context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.original_error = original_error
        self.operation_context = operation_context or {}
        self.timestamp = time.time()

class ValidationError(AtomicWriteError):
    """Error during data validation"""
    pass

class IntegrityError(AtomicWriteError):
    """Error during integrity checking"""
    pass

class RecoveryManager:
    """Manages error recovery and rollback operations"""
    
    def __init__(self):
        self.recovery_stack: List[Dict[str, Any]] = []
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
    
    def add_recovery_point(self, operation: str, file_path: Path, 
                          backup_path: Optional[Path] = None,
                          metadata: Optional[Dict[str, Any]] = None):
        """Add a recovery point for potential rollback"""
        recovery_point = {
            'operation': operation,
            'file_path': file_path,
            'backup_path': backup_path,
            'metadata': metadata or {},
            'timestamp': time.time()
        }
        self.recovery_stack.append(recovery_point)
        logger.debug(f"Added recovery point: {operation} for {file_path}")
    
    async def attempt_recovery(self, error: Exception) -> bool:
        """Attempt to recover from an error using recovery stack"""
        if self.recovery_attempts >= self.max_recovery_attempts:
            logger.error(f"Max recovery attempts ({self.max_recovery_attempts}) exceeded")
            return False
        
        self.recovery_attempts += 1
        logger.info(f"Attempting recovery (attempt {self.recovery_attempts})")
        
        success = True
        for recovery_point in reversed(self.recovery_stack):
            try:
                await self._execute_recovery_point(recovery_point)
            except Exception as recovery_error:
                logger.error(f"Recovery failed for {recovery_point}: {recovery_error}")
                success = False
        
        return success
    
    async def _execute_recovery_point(self, recovery_point: Dict[str, Any]):
        """Execute a single recovery point"""
        operation = recovery_point['operation']
        file_path = recovery_point['file_path']
        backup_path = recovery_point['backup_path']
        
        if operation == 'write' and backup_path and backup_path.exists():
            # Restore from backup
            os.rename(backup_path, file_path)
        elif operation == 'delete' and backup_path and backup_path.exists():
            # Restore deleted file
            os.rename(backup_path, file_path)
        elif operation == 'create' and file_path.exists():
            # Remove created file
            file_path.unlink()
    
    def clear_recovery_stack(self):
        """Clear the recovery stack after successful operation"""
        self.recovery_stack.clear()
        self.recovery_attempts = 0

class AtomicWriter:
    """
    Atomic file writer using write-then-rename pattern
    Ensures file integrity during write operations with Rich progress display
    """
    
    def __init__(self, target_path: Union[str, Path], backup: bool = True,
                 show_progress: bool = True, verify_integrity: bool = True,
                 schema: Optional[Dict[str, Any]] = None):
        self.target_path = Path(target_path)
        self.backup = backup
        self.show_progress = show_progress
        self.verify_integrity = verify_integrity
        self.schema = schema
        self.temp_path: Optional[Path] = None
        self.backup_path: Optional[Path] = None
        self._file_handle = None
        self._progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None
        self._recovery_manager = RecoveryManager()
        self._original_checksum: Optional[str] = None
        self._operation_metadata = {
            'start_time': None,
            'end_time': None,
            'bytes_written': 0,
            'operation_id': f"atomic_write_{int(time.time() * 1000)}"
        }
        
    async def __aenter__(self):
        """Async context manager entry with Rich progress initialization"""
        self._operation_metadata['start_time'] = time.time()
        
        # Initialize progress display
        if self.show_progress:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(complete_style="green", finished_style="green"),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
                transient=True
            )
            self._progress.start()
            self._task_id = self._progress.add_task(
                f"Writing {self.target_path.name}",
                total=100
            )
        
        try:
            # Create target directory if needed
            self.target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Store original file checksum for integrity verification
            if self.verify_integrity and self.target_path.exists():
                self._original_checksum = await self._calculate_checksum(self.target_path)
            
            # Create temporary file in same directory as target
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.target_path.parent,
                prefix=f".{self.target_path.name}.tmp"
            )
            self.temp_path = Path(temp_path)
            
            # Close the file descriptor and reopen with aiofiles
            os.close(temp_fd)
            
            # Add recovery point
            self._recovery_manager.add_recovery_point(
                'temp_create', self.temp_path, metadata=self._operation_metadata
            )
            
            if self._progress and self._task_id:
                self._progress.update(self._task_id, completed=10)
            
            logger.info(f"Initialized atomic write for {self.target_path}")
            return self
            
        except Exception as e:
            if self._progress:
                self._progress.stop()
            raise AtomicWriteError(
                f"Failed to initialize atomic writer for {self.target_path}",
                original_error=e,
                operation_context=self._operation_metadata
            ) from e
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with enhanced error handling"""
        self._operation_metadata['end_time'] = time.time()
        
        try:
            if exc_type is None:
                # Success - commit the atomic write
                if self._progress and self._task_id:
                    self._progress.update(self._task_id, completed=90)
                
                await self._commit_write()
                
                if self._progress and self._task_id:
                    self._progress.update(self._task_id, completed=100,
                                        description=f"✓ Completed {self.target_path.name}")
                
                # Clear recovery stack on success
                self._recovery_manager.clear_recovery_stack()
                
                # Log successful operation
                duration = self._operation_metadata['end_time'] - self._operation_metadata['start_time']
                logger.info(f"Successfully wrote {self.target_path} in {duration:.2f}s")
                
            else:
                # Error occurred - attempt recovery
                if self._progress and self._task_id:
                    self._progress.update(self._task_id, 
                                        description=f"✗ Failed {self.target_path.name}")
                
                logger.error(f"Error during atomic write: {exc_val}")
                
                # Attempt recovery
                recovery_success = await self._recovery_manager.attempt_recovery(exc_val)
                if recovery_success:
                    logger.info("Recovery successful")
                else:
                    logger.error("Recovery failed")
                
                # Cleanup temporary file
                await self._cleanup_temp()
                
        finally:
            # Always cleanup progress and file handles
            if self._progress:
                if self._task_id:
                    await asyncio.sleep(0.1)  # Brief pause to show final status
                self._progress.stop()
            
            if self._file_handle:
                await self._file_handle.aclose()
                self._file_handle = None
    
    async def _commit_write(self):
        """Commit the atomic write operation with integrity verification"""
        if not self.temp_path or not self.temp_path.exists():
            raise AtomicWriteError(
                "No temporary file to commit",
                operation_context=self._operation_metadata
            )
        
        try:
            # Verify integrity of temporary file if requested
            if self.verify_integrity:
                temp_checksum = await self._calculate_checksum(self.temp_path)
                if not temp_checksum:
                    raise IntegrityError(
                        "Failed to calculate checksum for temporary file",
                        operation_context=self._operation_metadata
                    )
            
            # Create backup if requested and target exists
            if self.backup and self.target_path.exists():
                self.backup_path = self.target_path.with_suffix(
                    self.target_path.suffix + '.backup'
                )
                
                # Add recovery point for backup operation
                self._recovery_manager.add_recovery_point(
                    'write', self.target_path, self.backup_path,
                    metadata=self._operation_metadata
                )
                
                # Use rename for atomic backup
                os.rename(self.target_path, self.backup_path)
                logger.debug(f"Created backup at {self.backup_path}")
            
            # Atomic rename from temp to target
            os.rename(self.temp_path, self.target_path)
            self.temp_path = None  # Prevent cleanup
            
            # Verify final file integrity
            if self.verify_integrity:
                final_checksum = await self._calculate_checksum(self.target_path)
                if temp_checksum != final_checksum:
                    raise IntegrityError(
                        "File integrity check failed after commit",
                        operation_context={
                            **self._operation_metadata,
                            'temp_checksum': temp_checksum,
                            'final_checksum': final_checksum
                        }
                    )
            
            logger.debug(f"Successfully committed write to {self.target_path}")
            
        except Exception as e:
            # Enhanced error recovery
            logger.error(f"Commit failed: {e}")
            
            # Restore backup if we created one
            if self.backup_path and self.backup_path.exists():
                try:
                    if self.target_path.exists():
                        self.target_path.unlink()  # Remove potentially corrupted file
                    os.rename(self.backup_path, self.target_path)
                    logger.info(f"Restored backup from {self.backup_path}")
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {restore_error}")
            
            # Cleanup temp file
            await self._cleanup_temp()
            
            raise AtomicWriteError(
                f"Failed to commit atomic write: {e}",
                original_error=e,
                operation_context=self._operation_metadata
            ) from e
    
    async def _cleanup_temp(self):
        """Cleanup temporary file"""
        if self.temp_path and self.temp_path.exists():
            try:
                self.temp_path.unlink()
            except Exception:
                pass  # Best effort cleanup
    
    async def write_text(self, content: str, encoding: str = 'utf-8') -> None:
        """Write text content to file with progress tracking"""
        if not self.temp_path:
            raise AtomicWriteError(
                "AtomicWriter not properly initialized",
                operation_context=self._operation_metadata
            )
        
        try:
            if self._progress and self._task_id:
                self._progress.update(self._task_id, completed=30)
            
            async with aiofiles.open(self.temp_path, 'w', encoding=encoding) as f:
                # Write content in chunks for large files with progress updates
                content_bytes = content.encode(encoding)
                self._operation_metadata['bytes_written'] = len(content_bytes)
                
                if len(content_bytes) > 1024 * 1024:  # 1MB chunks for large files
                    chunk_size = 1024 * 1024
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        await f.write(chunk)
                        
                        if self._progress and self._task_id:
                            progress = 30 + (50 * (i + len(chunk)) // len(content))
                            self._progress.update(self._task_id, completed=progress)
                else:
                    await f.write(content)
                    if self._progress and self._task_id:
                        self._progress.update(self._task_id, completed=80)
                
                await f.flush()
                await asyncio.to_thread(os.fsync, f.fileno())
                
                logger.debug(f"Wrote {len(content_bytes)} bytes to {self.temp_path}")
                
        except Exception as e:
            raise AtomicWriteError(
                f"Failed to write text content: {e}",
                original_error=e,
                operation_context=self._operation_metadata
            ) from e
    
    async def write_bytes(self, content: bytes) -> None:
        """Write binary content to file"""
        if not self.temp_path:
            raise AtomicWriteError("AtomicWriter not properly initialized")
        
        async with aiofiles.open(self.temp_path, 'wb') as f:
            await f.write(content)
            await f.flush()
            await asyncio.to_thread(os.fsync, f.fileno())
    
    async def write_json(self, data: Any, indent: int = 2, ensure_ascii: bool = False) -> None:
        """Write JSON data to file with optional schema validation"""
        try:
            # Validate against schema if provided
            if self.schema and JSONSCHEMA_AVAILABLE:
                try:
                    jsonschema.validate(data, self.schema)
                    logger.debug("JSON data passed schema validation")
                except jsonschema.ValidationError as e:
                    raise ValidationError(
                        f"JSON data failed schema validation: {e}",
                        original_error=e,
                        operation_context={
                            **self._operation_metadata,
                            'schema': self.schema,
                            'validation_error': str(e)
                        }
                    ) from e
            elif self.schema and not JSONSCHEMA_AVAILABLE:
                logger.warning("Schema provided but jsonschema library not available")
            
            # Serialize JSON with error handling
            try:
                json_content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
            except (TypeError, ValueError) as e:
                raise ValidationError(
                    f"Failed to serialize data to JSON: {e}",
                    original_error=e,
                    operation_context=self._operation_metadata
                ) from e
            
            await self.write_text(json_content)
            
        except AtomicWriteError:
            raise  # Re-raise our custom errors
        except Exception as e:
            raise AtomicWriteError(
                f"Failed to write JSON data: {e}",
                original_error=e,
                operation_context=self._operation_metadata
            ) from e
    
    async def write_yaml(self, data: Any, default_flow_style: bool = False) -> None:
        """Write YAML data to file with validation"""
        try:
            # Serialize YAML with error handling
            try:
                yaml_content = yaml.dump(
                    data, 
                    default_flow_style=default_flow_style,
                    allow_unicode=True, 
                    indent=2,
                    sort_keys=False
                )
            except yaml.YAMLError as e:
                raise ValidationError(
                    f"Failed to serialize data to YAML: {e}",
                    original_error=e,
                    operation_context=self._operation_metadata
                ) from e
            
            await self.write_text(yaml_content)
            
        except AtomicWriteError:
            raise  # Re-raise our custom errors
        except Exception as e:
            raise AtomicWriteError(
                f"Failed to write YAML data: {e}",
                original_error=e,
                operation_context=self._operation_metadata
            ) from e
    
    async def _calculate_checksum(self, file_path: Path) -> Optional[str]:
        """Calculate SHA256 checksum of a file"""
        try:
            hash_sha256 = hashlib.sha256()
            async with aiofiles.open(file_path, 'rb') as f:
                while chunk := await f.read(8192):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate checksum for {file_path}: {e}")
            return None

class AtomicFileManager:
    """
    Higher-level atomic file operations manager
    Provides convenient methods for common file operations
    """
    
    @staticmethod
    async def write_json(file_path: Union[str, Path], data: Any, 
                        backup: bool = True, indent: int = 2) -> None:
        """Write JSON data atomically"""
        async with AtomicWriter(file_path, backup=backup) as writer:
            await writer.write_json(data, indent=indent)
    
    @staticmethod
    async def write_yaml(file_path: Union[str, Path], data: Any, 
                        backup: bool = True) -> None:
        """Write YAML data atomically"""
        async with AtomicWriter(file_path, backup=backup) as writer:
            await writer.write_yaml(data)
    
    @staticmethod
    async def write_text(file_path: Union[str, Path], content: str, 
                        backup: bool = True, encoding: str = 'utf-8') -> None:
        """Write text content atomically"""
        async with AtomicWriter(file_path, backup=backup) as writer:
            await writer.write_text(content, encoding=encoding)
    
    @staticmethod
    async def write_bytes(file_path: Union[str, Path], content: bytes, 
                         backup: bool = True) -> None:
        """Write binary content atomically"""
        async with AtomicWriter(file_path, backup=backup) as writer:
            await writer.write_bytes(content)
    
    @staticmethod
    async def update_json(file_path: Union[str, Path], 
                         update_func: callable, backup: bool = True) -> None:
        """Update JSON file atomically using update function"""
        # Read existing data
        path = Path(file_path)
        data = {}
        if path.exists():
            async with aiofiles.open(path, 'r') as f:
                content = await f.read()
                if content.strip():
                    data = json.loads(content)
        
        # Apply update function
        updated_data = update_func(data)
        
        # Write updated data atomically
        await AtomicFileManager.write_json(file_path, updated_data, backup=backup)
    
    @staticmethod
    async def update_yaml(file_path: Union[str, Path], 
                         update_func: callable, backup: bool = True) -> None:
        """Update YAML file atomically using update function"""
        # Read existing data
        path = Path(file_path)
        data = {}
        if path.exists():
            async with aiofiles.open(path, 'r') as f:
                content = await f.read()
                if content.strip():
                    data = yaml.safe_load(content) or {}
        
        # Apply update function
        updated_data = update_func(data)
        
        # Write updated data atomically
        await AtomicFileManager.write_yaml(file_path, updated_data, backup=backup)
    
    @staticmethod
    async def safe_copy(source_path: Union[str, Path], 
                       dest_path: Union[str, Path], backup: bool = True) -> None:
        """Copy file atomically"""
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # Read source file
        if source.stat().st_size > 100 * 1024 * 1024:  # 100MB
            # Large file - read in chunks
            async with AtomicWriter(dest_path, backup=backup) as writer:
                async with aiofiles.open(source, 'rb') as src:
                    chunk_size = 64 * 1024  # 64KB chunks
                    async with aiofiles.open(writer.temp_path, 'wb') as dst:
                        while True:
                            chunk = await src.read(chunk_size)
                            if not chunk:
                                break
                            await dst.write(chunk)
                        await dst.flush()
                        await asyncio.to_thread(os.fsync, dst.fileno())
        else:
            # Small file - read all at once
            async with aiofiles.open(source, 'rb') as f:
                content = await f.read()
            
            async with AtomicWriter(dest_path, backup=backup) as writer:
                await writer.write_bytes(content)
    
    @staticmethod
    async def safe_move(source_path: Union[str, Path], 
                       dest_path: Union[str, Path], backup: bool = True) -> None:
        """Move file atomically with fallback to copy+delete"""
        source = Path(source_path)
        dest = Path(dest_path)
        
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # Try simple rename first (works if same filesystem)
        try:
            # Create backup if requested and destination exists
            if backup and dest.exists():
                backup_path = dest.with_suffix(dest.suffix + '.backup')
                os.rename(dest, backup_path)
            
            # Atomic rename
            os.rename(source, dest)
            
        except OSError:
            # Cross-filesystem move - use copy then delete
            await AtomicFileManager.safe_copy(source, dest, backup=backup)
            source.unlink()  # Delete source after successful copy

class FileTransaction:
    """
    Transaction-like interface for multiple file operations with Rich progress display
    Allows rollback of multiple file changes with comprehensive error recovery
    """
    
    def __init__(self, show_progress: bool = True, 
                 transaction_id: Optional[str] = None):
        self.operations: List[Dict[str, Any]] = []
        self.completed_operations: List[Dict[str, Any]] = []
        self.show_progress = show_progress
        self.transaction_id = transaction_id or f"tx_{int(time.time() * 1000)}"
        self._progress: Optional[Progress] = None
        self._recovery_manager = RecoveryManager()
        self._transaction_metadata = {
            'transaction_id': self.transaction_id,
            'start_time': None,
            'end_time': None,
            'operations_count': 0,
            'files_affected': set()
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Error occurred - rollback all operations
            await self._rollback()
    
    def add_write(self, file_path: Union[str, Path], content: Any, 
                  content_type: str = 'json', schema: Optional[Dict[str, Any]] = None,
                  verify_integrity: bool = True):
        """Add a write operation to the transaction with validation options"""
        file_path = Path(file_path)
        self.operations.append({
            'type': 'write',
            'file_path': file_path,
            'content': content,
            'content_type': content_type,
            'schema': schema,
            'verify_integrity': verify_integrity,
            'operation_id': f"write_{len(self.operations)}"
        })
        self._transaction_metadata['files_affected'].add(str(file_path))
    
    def add_copy(self, source_path: Union[str, Path], dest_path: Union[str, Path]):
        """Add a copy operation to the transaction"""
        self.operations.append({
            'type': 'copy',
            'source_path': Path(source_path),
            'dest_path': Path(dest_path)
        })
    
    def add_move(self, source_path: Union[str, Path], dest_path: Union[str, Path]):
        """Add a move operation to the transaction"""
        self.operations.append({
            'type': 'move',
            'source_path': Path(source_path),
            'dest_path': Path(dest_path)
        })
    
    def add_delete(self, file_path: Union[str, Path]):
        """Add a delete operation to the transaction"""
        self.operations.append({
            'type': 'delete',
            'file_path': Path(file_path)
        })
    
    async def commit(self) -> bool:
        """Execute all operations in the transaction with Rich progress display"""
        self._transaction_metadata['start_time'] = time.time()
        self._transaction_metadata['operations_count'] = len(self.operations)
        
        if self.show_progress:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold green]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                console=console
            )
            self._progress.start()
            
            task_id = self._progress.add_task(
                f"Transaction {self.transaction_id[:8]}",
                total=len(self.operations)
            )
        
        try:
            logger.info(f"Starting transaction {self.transaction_id} with {len(self.operations)} operations")
            
            for i, operation in enumerate(self.operations):
                if self._progress:
                    self._progress.update(
                        task_id,
                        completed=i,
                        description=f"Executing {operation['type']} on {operation['file_path'].name}"
                    )
                
                await self._execute_operation(operation)
                self.completed_operations.append(operation)
                
                # Add recovery point for each completed operation
                self._recovery_manager.add_recovery_point(
                    operation['type'],
                    operation['file_path'],
                    metadata={'transaction_id': self.transaction_id, 'operation_index': i}
                )
            
            if self._progress:
                self._progress.update(
                    task_id,
                    completed=len(self.operations),
                    description=f"✓ Transaction {self.transaction_id[:8]} completed"
                )
            
            self._transaction_metadata['end_time'] = time.time()
            duration = self._transaction_metadata['end_time'] - self._transaction_metadata['start_time']
            logger.info(f"Transaction {self.transaction_id} completed successfully in {duration:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"Transaction {self.transaction_id} failed: {e}")
            
            if self._progress:
                self._progress.update(
                    task_id,
                    description=f"✗ Transaction {self.transaction_id[:8]} failed - rolling back"
                )
            
            # Attempt recovery first
            recovery_success = await self._recovery_manager.attempt_recovery(e)
            if not recovery_success:
                # Fallback to manual rollback
                await self._rollback()
            
            raise AtomicWriteError(
                f"Transaction {self.transaction_id} failed: {e}",
                original_error=e,
                operation_context=self._transaction_metadata
            ) from e
            
        finally:
            if self._progress:
                await asyncio.sleep(0.5)  # Brief pause to show final status
                self._progress.stop()
    
    async def _execute_operation(self, operation: Dict[str, Any]):
        """Execute a single operation with enhanced error handling"""
        op_type = operation['type']
        operation_id = operation.get('operation_id', f"{op_type}_{time.time()}")
        
        try:
            logger.debug(f"Executing operation {operation_id}: {op_type}")
            
            if op_type == 'write':
                content_type = operation['content_type']
                schema = operation.get('schema')
                verify_integrity = operation.get('verify_integrity', True)
                
                # Use AtomicWriter with enhanced features
                async with AtomicWriter(
                    operation['file_path'],
                    backup=True,
                    show_progress=False,  # Transaction handles progress
                    verify_integrity=verify_integrity,
                    schema=schema
                ) as writer:
                    if content_type == 'json':
                        await writer.write_json(operation['content'])
                    elif content_type == 'yaml':
                        await writer.write_yaml(operation['content'])
                    elif content_type == 'text':
                        await writer.write_text(operation['content'])
                    elif content_type == 'bytes':
                        await writer.write_bytes(operation['content'])
                    else:
                        raise AtomicWriteError(f"Unsupported content type: {content_type}")
                
            elif op_type == 'copy':
                await AtomicFileManager.safe_copy(
                    operation['source_path'], operation['dest_path']
                )
                
            elif op_type == 'move':
                await AtomicFileManager.safe_move(
                    operation['source_path'], operation['dest_path']
                )
                
            elif op_type == 'delete':
                file_path = operation['file_path']
                if file_path.exists():
                    # Create backup before deletion
                    backup_path = file_path.with_suffix(file_path.suffix + '.deleted_backup')
                    await AtomicFileManager.safe_copy(file_path, backup_path)
                    operation['backup_path'] = backup_path  # Store for potential rollback
                    
                    file_path.unlink()
                    logger.debug(f"Deleted {file_path} with backup at {backup_path}")
            
            else:
                raise AtomicWriteError(f"Unknown operation type: {op_type}")
                
            logger.debug(f"Successfully executed operation {operation_id}")
            
        except Exception as e:
            raise AtomicWriteError(
                f"Failed to execute {op_type} operation: {e}",
                original_error=e,
                operation_context={
                    'operation_id': operation_id,
                    'operation_type': op_type,
                    'file_path': str(operation.get('file_path', 'unknown')),
                    'transaction_id': self.transaction_id
                }
            ) from e
    
    async def _rollback(self):
        """Rollback completed operations"""
        # Reverse the order for rollback
        for operation in reversed(self.completed_operations):
            try:
                await self._rollback_operation(operation)
            except Exception as e:
                # Best effort rollback - log but continue
                print(f"Warning: Failed to rollback operation {operation}: {e}")
    
    async def _rollback_operation(self, operation: Dict[str, Any]):
        """Rollback a single operation"""
        op_type = operation['type']
        
        if op_type == 'write':
            # Restore backup if it exists
            file_path = operation['file_path']
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            if backup_path.exists():
                os.rename(backup_path, file_path)
            elif file_path.exists():
                file_path.unlink()
                
        elif op_type == 'copy':
            # Delete the copied file
            dest_path = operation['dest_path']
            if dest_path.exists():
                dest_path.unlink()
                
        elif op_type == 'move':
            # Move file back to original location
            await AtomicFileManager.safe_move(
                operation['dest_path'], operation['source_path'], backup=False
            )
            
        elif op_type == 'delete':
            # Restore deleted file from backup if available
            backup_path = operation.get('backup_path')
            if backup_path and Path(backup_path).exists():
                await AtomicFileManager.safe_move(
                    backup_path, operation['file_path'], backup=False
                )
                logger.info(f"Restored deleted file {operation['file_path']} from backup")

class AuditTrail:
    """Comprehensive audit trail for atomic file operations"""
    
    def __init__(self, audit_file: Optional[Union[str, Path]] = None):
        self.audit_file = Path(audit_file) if audit_file else None
        self.audit_entries: List[Dict[str, Any]] = []
        self.session_id = f"session_{int(time.time() * 1000)}"
    
    def log_operation(self, operation: str, file_path: Path, 
                     metadata: Optional[Dict[str, Any]] = None,
                     status: str = 'started', error: Optional[str] = None):
        """Log an atomic file operation"""
        entry = {
            'timestamp': time.time(),
            'session_id': self.session_id,
            'operation': operation,
            'file_path': str(file_path),
            'status': status,
            'metadata': metadata or {},
            'error': error
        }
        
        self.audit_entries.append(entry)
        logger.info(f"Audit: {operation} {file_path} - {status}")
        
        # Write to audit file if specified
        if self.audit_file:
            asyncio.create_task(self._write_audit_entry(entry))
    
    async def _write_audit_entry(self, entry: Dict[str, Any]):
        """Write audit entry to file"""
        try:
            audit_line = json.dumps(entry) + "\n"
            
            # Ensure audit directory exists
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to audit file (no need for atomic write here as we're appending)
            async with aiofiles.open(self.audit_file, 'a', encoding='utf-8') as f:
                await f.write(audit_line)
                await f.flush()
                
        except Exception as e:
            logger.error(f"Failed to write audit entry: {e}")
    
    def get_operations_summary(self) -> Dict[str, Any]:
        """Get summary of operations in this session"""
        total_operations = len(self.audit_entries)
        successful_operations = len([e for e in self.audit_entries if e['status'] == 'completed'])
        failed_operations = len([e for e in self.audit_entries if e['status'] == 'failed'])
        
        file_operations = {}
        for entry in self.audit_entries:
            file_path = entry['file_path']
            if file_path not in file_operations:
                file_operations[file_path] = []
            file_operations[file_path].append(entry)
        
        return {
            'session_id': self.session_id,
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'files_affected': len(file_operations),
            'file_operations': file_operations
        }
    
    def display_summary(self):
        """Display operations summary using Rich"""
        summary = self.get_operations_summary()
        
        table = Table(title=f"Atomic Operations Summary - Session {self.session_id[:8]}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Operations", str(summary['total_operations']))
        table.add_row("Successful", str(summary['successful_operations']))
        table.add_row("Failed", str(summary['failed_operations']))
        table.add_row("Files Affected", str(summary['files_affected']))
        
        console.print(table)
        
        # Display file operations if any
        if summary['file_operations']:
            file_table = Table(title="File Operations")
            file_table.add_column("File", style="green")
            file_table.add_column("Operations", style="yellow")
            file_table.add_column("Status", style="blue")
            
            for file_path, operations in summary['file_operations'].items():
                operation_types = ", ".join([op['operation'] for op in operations])
                statuses = ", ".join(set([op['status'] for op in operations]))
                file_table.add_row(Path(file_path).name, operation_types, statuses)
            
            console.print(file_table)

class AtomicFileOperations:
    """High-level atomic file operations with comprehensive features"""
    
    def __init__(self, audit_file: Optional[Union[str, Path]] = None):
        self.audit_trail = AuditTrail(audit_file)
    
    @asynccontextmanager
    async def batch_operation(self, operation_name: str = "batch_operation"):
        """Context manager for batch operations with audit trail"""
        batch_id = f"batch_{int(time.time() * 1000)}"
        self.audit_trail.log_operation(
            f"batch_start_{operation_name}", Path("."),
            metadata={'batch_id': batch_id}, status='started'
        )
        
        try:
            yield self
            self.audit_trail.log_operation(
                f"batch_complete_{operation_name}", Path("."),
                metadata={'batch_id': batch_id}, status='completed'
            )
        except Exception as e:
            self.audit_trail.log_operation(
                f"batch_failed_{operation_name}", Path("."),
                metadata={'batch_id': batch_id}, status='failed', error=str(e)
            )
            raise
    
    async def atomic_json_update(self, file_path: Union[str, Path], 
                               update_function: Callable[[Dict[str, Any]], Dict[str, Any]],
                               create_if_missing: bool = True,
                               schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Atomically update JSON file with function"""
        file_path = Path(file_path)
        
        self.audit_trail.log_operation('json_update', file_path, status='started')
        
        try:
            # Read existing data or create empty dict
            current_data = {}
            if file_path.exists():
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    if content.strip():
                        current_data = json.loads(content)
            elif not create_if_missing:
                raise FileNotFoundError(f"File {file_path} does not exist and create_if_missing=False")
            
            # Apply update function
            updated_data = update_function(current_data.copy())
            
            # Write updated data atomically
            async with AtomicWriter(file_path, schema=schema) as writer:
                await writer.write_json(updated_data)
            
            self.audit_trail.log_operation(
                'json_update', file_path, 
                metadata={'keys_modified': list(updated_data.keys())},
                status='completed'
            )
            
            return updated_data
            
        except Exception as e:
            self.audit_trail.log_operation(
                'json_update', file_path, status='failed', error=str(e)
            )
            raise
    
    async def atomic_config_merge(self, config_files: List[Union[str, Path]],
                                output_file: Union[str, Path],
                                merge_strategy: str = 'deep') -> Dict[str, Any]:
        """Merge multiple configuration files atomically"""
        output_path = Path(output_file)
        
        self.audit_trail.log_operation(
            'config_merge', output_path,
            metadata={'input_files': [str(f) for f in config_files], 'strategy': merge_strategy},
            status='started'
        )
        
        try:
            merged_config = {}
            
            for config_file in config_files:
                config_path = Path(config_file)
                if not config_path.exists():
                    logger.warning(f"Config file {config_path} does not exist, skipping")
                    continue
                
                # Determine file format and load
                if config_path.suffix.lower() in ['.json']:
                    async with aiofiles.open(config_path, 'r') as f:
                        config_data = json.loads(await f.read())
                elif config_path.suffix.lower() in ['.yml', '.yaml']:
                    async with aiofiles.open(config_path, 'r') as f:
                        config_data = yaml.safe_load(await f.read())
                else:
                    logger.warning(f"Unsupported config file format: {config_path}")
                    continue
                
                # Merge configuration
                if merge_strategy == 'deep':
                    merged_config = self._deep_merge(merged_config, config_data)
                else:  # shallow merge
                    merged_config.update(config_data)
            
            # Write merged configuration
            if output_path.suffix.lower() in ['.json']:
                async with AtomicWriter(output_path) as writer:
                    await writer.write_json(merged_config)
            else:
                async with AtomicWriter(output_path) as writer:
                    await writer.write_yaml(merged_config)
            
            self.audit_trail.log_operation(
                'config_merge', output_path,
                metadata={'merged_keys': list(merged_config.keys())},
                status='completed'
            )
            
            return merged_config
            
        except Exception as e:
            self.audit_trail.log_operation(
                'config_merge', output_path, status='failed', error=str(e)
            )
            raise
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def cleanup_backups(self, directory: Union[str, Path], 
                            max_age_hours: int = 24,
                            backup_pattern: str = "*.backup") -> int:
        """Clean up old backup files"""
        directory = Path(directory)
        
        self.audit_trail.log_operation(
            'cleanup_backups', directory,
            metadata={'max_age_hours': max_age_hours, 'pattern': backup_pattern},
            status='started'
        )
        
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            removed_count = 0
            
            for backup_file in directory.glob(backup_pattern):
                if backup_file.is_file():
                    file_age = current_time - backup_file.stat().st_mtime
                    if file_age > max_age_seconds:
                        backup_file.unlink()
                        removed_count += 1
                        logger.debug(f"Removed old backup: {backup_file}")
            
            self.audit_trail.log_operation(
                'cleanup_backups', directory,
                metadata={'removed_count': removed_count},
                status='completed'
            )
            
            return removed_count
            
        except Exception as e:
            self.audit_trail.log_operation(
                'cleanup_backups', directory, status='failed', error=str(e)
            )
            raise
    
    def get_audit_summary(self):
        """Get audit trail summary"""
        return self.audit_trail.get_operations_summary()
    
    def display_audit_summary(self):
        """Display audit trail summary"""
        self.audit_trail.display_summary()

# Convenience functions for common operations
async def write_config_atomically(config_path: Union[str, Path], 
                                 config_data: Dict[str, Any],
                                 backup: bool = True,
                                 schema: Optional[Dict[str, Any]] = None) -> None:
    """Convenience function to write configuration files atomically"""
    config_path = Path(config_path)
    
    if config_path.suffix.lower() in ['.json']:
        async with AtomicWriter(config_path, backup=backup, schema=schema) as writer:
            await writer.write_json(config_data)
    elif config_path.suffix.lower() in ['.yml', '.yaml']:
        async with AtomicWriter(config_path, backup=backup) as writer:
            await writer.write_yaml(config_data)
    else:
        raise ValueError(f"Unsupported config format: {config_path.suffix}")

async def safe_file_rotation(file_path: Union[str, Path], 
                           max_files: int = 5,
                           compression: bool = False) -> None:
    """Rotate files safely (log rotation pattern)"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        return
    
    # Rotate existing files
    for i in range(max_files - 1, 0, -1):
        old_file = file_path.with_suffix(f"{file_path.suffix}.{i}")
        new_file = file_path.with_suffix(f"{file_path.suffix}.{i + 1}")
        
        if old_file.exists():
            if i == max_files - 1:
                old_file.unlink()  # Remove oldest file
            else:
                await AtomicFileManager.safe_move(old_file, new_file, backup=False)
    
    # Move current file to .1
    rotated_file = file_path.with_suffix(f"{file_path.suffix}.1")
    await AtomicFileManager.safe_move(file_path, rotated_file, backup=False)

# Export main classes and functions
__all__ = [
    'AtomicWriter',
    'AtomicFileManager', 
    'FileTransaction',
    'AtomicFileOperations',
    'AuditTrail',
    'RecoveryManager',
    'AtomicWriteError',
    'ValidationError',
    'IntegrityError',
    'write_config_atomically',
    'safe_file_rotation'
]