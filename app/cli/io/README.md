# Atomic File Operations Module

A comprehensive Python module for atomic file operations with advanced error handling, progress tracking, and data integrity features.

## Features

### 🔒 Atomic Operations
- **Write-then-rename pattern** ensures file integrity
- **Multi-file transactions** with automatic rollback on failure
- **Backup and recovery mechanisms** for critical data protection

### 🛡️ Data Integrity
- **SHA256 checksum verification** for file integrity
- **JSON/YAML schema validation** (with jsonschema)
- **Automatic backup creation** before modifications

### 📊 Progress & Monitoring
- **Rich progress bars** for long-running operations
- **Comprehensive audit trails** with detailed logging
- **Real-time operation monitoring** and reporting

### ⚡ Advanced Features
- **Error recovery mechanisms** with configurable retry logic
- **Large file handling** with chunked operations
- **Configuration file merging** with deep merge support
- **File rotation utilities** for log management

## Installation

```bash
# Install required dependencies
pip install aiofiles rich pyyaml jsonschema
```

## Quick Start

### Basic Atomic Write

```python
import asyncio
from atomic import AtomicWriter

async def main():
    data = {"config": "value", "version": "1.0"}
    
    async with AtomicWriter("config.json", backup=True) as writer:
        await writer.write_json(data)

asyncio.run(main())
```

### Multi-File Transaction

```python
from atomic import FileTransaction

async def deploy_configs():
    async with FileTransaction() as tx:
        tx.add_write("app.json", app_config, "json")
        tx.add_write("db.json", db_config, "json")
        tx.add_write("cache.yaml", cache_config, "yaml")
        
        await tx.commit()  # All or nothing
```

### High-Level Operations

```python
from atomic import AtomicFileOperations

ops = AtomicFileOperations("audit.log")

# Atomic JSON updates
await ops.atomic_json_update(
    "settings.json",
    lambda data: {**data, "updated": True}
)

# Config merging
merged = await ops.atomic_config_merge(
    ["base.json", "env.json", "user.json"],
    "final_config.json"
)
```

## API Reference

### AtomicWriter

The core class for atomic file operations.

```python
class AtomicWriter:
    def __init__(
        self, 
        target_path: Union[str, Path], 
        backup: bool = True,
        show_progress: bool = True, 
        verify_integrity: bool = True,
        schema: Optional[Dict[str, Any]] = None
    )
```

**Parameters:**
- `target_path`: Target file path
- `backup`: Create backup before writing
- `show_progress`: Show Rich progress display
- `verify_integrity`: Verify file integrity with checksums
- `schema`: JSON schema for validation

**Methods:**
- `write_text(content: str, encoding: str = 'utf-8')`: Write text content
- `write_json(data: Any, indent: int = 2)`: Write JSON data with optional schema validation
- `write_yaml(data: Any)`: Write YAML data
- `write_bytes(content: bytes)`: Write binary content

### FileTransaction

Transaction-like interface for multiple file operations.

```python
class FileTransaction:
    def __init__(self, show_progress: bool = True, transaction_id: Optional[str] = None)
```

**Methods:**
- `add_write(file_path, content, content_type, schema=None)`: Add write operation
- `add_copy(source_path, dest_path)`: Add copy operation
- `add_move(source_path, dest_path)`: Add move operation
- `add_delete(file_path)`: Add delete operation
- `commit()`: Execute all operations atomically

### AtomicFileOperations

High-level operations with audit trail.

```python
class AtomicFileOperations:
    def __init__(self, audit_file: Optional[Union[str, Path]] = None)
```

**Methods:**
- `atomic_json_update(file_path, update_function)`: Update JSON file atomically
- `atomic_config_merge(config_files, output_file, strategy='deep')`: Merge configs
- `cleanup_backups(directory, max_age_hours=24)`: Clean old backups
- `batch_operation(operation_name)`: Context manager for batch operations

### Utility Functions

```python
# Write configuration files
await write_config_atomically(path, data, schema=None)

# Safe file rotation (log rotation pattern)
await safe_file_rotation(file_path, max_files=5)

# Global audit trail
set_global_audit_trail(audit_file_path)
trail = get_global_audit_trail()
```

## Error Handling

The module provides comprehensive error handling with custom exception types:

- `AtomicWriteError`: Base exception for atomic operations
- `ValidationError`: Schema validation failures
- `IntegrityError`: File integrity check failures

### Recovery Mechanisms

```python
# Automatic recovery with RecoveryManager
recovery_manager = RecoveryManager()
recovery_manager.add_recovery_point("write", file_path, backup_path)

# Attempt recovery on failure
success = await recovery_manager.attempt_recovery(error)
```

## Schema Validation

JSON schema validation (requires `jsonschema` package):

```python
user_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"}
    },
    "required": ["name", "email"]
}

async with AtomicWriter("user.json", schema=user_schema) as writer:
    await writer.write_json(user_data)  # Validates against schema
```

## Progress Display

Rich progress integration for visual feedback:

```python
# Automatic progress for large operations
async with AtomicWriter("large_file.json", show_progress=True) as writer:
    await writer.write_json(large_data)  # Shows progress bar

# Transaction progress
async with FileTransaction(show_progress=True) as tx:
    # ... add operations
    await tx.commit()  # Shows transaction progress
```

## Audit Trail

Comprehensive logging and audit trail:

```python
# Enable audit trail
ops = AtomicFileOperations("operations.audit")

# Operations are automatically logged
await ops.atomic_json_update("config.json", update_func)

# View audit summary
ops.display_audit_summary()  # Rich table display
```

## File Integrity

SHA256 checksum verification ensures data integrity:

```python
# Automatic integrity checking
async with AtomicWriter("critical.json", verify_integrity=True) as writer:
    await writer.write_json(data)  # Verifies checksum after write
```

## Configuration Merging

Deep merge multiple configuration files:

```python
ops = AtomicFileOperations()

# Merge configs with deep merge strategy
result = await ops.atomic_config_merge(
    ["base.json", "env.json", "local.json"],
    "final.json",
    merge_strategy="deep"
)
```

## Best Practices

### 1. Always Use Context Managers

```python
# Good
async with AtomicWriter("file.json") as writer:
    await writer.write_json(data)

# Bad - no automatic cleanup
writer = AtomicWriter("file.json")
await writer.write_json(data)
```

### 2. Enable Backups for Critical Files

```python
async with AtomicWriter("critical.json", backup=True) as writer:
    await writer.write_json(critical_data)
```

### 3. Use Transactions for Related Operations

```python
# Ensure all configs are updated together
async with FileTransaction() as tx:
    tx.add_write("app.json", app_config, "json")
    tx.add_write("db.json", db_config, "json")
    await tx.commit()
```

### 4. Validate Important Data

```python
async with AtomicWriter("user.json", schema=user_schema) as writer:
    await writer.write_json(user_data)  # Validates first
```

### 5. Use Audit Trails for Compliance

```python
ops = AtomicFileOperations("audit.log")
# All operations automatically logged for compliance
```

## Performance Considerations

- **Large files**: Automatic chunked operations for files > 1MB
- **Concurrent operations**: Thread-safe atomic operations
- **Memory usage**: Streaming operations for large files
- **Disk space**: Automatic cleanup of old backups

## Examples

See `demo_atomic_operations.py` for comprehensive examples of all features.

## Testing

Run the comprehensive test suite:

```bash
cd tests/cli
python -m pytest test_atomic_operations.py -v
```

## Dependencies

- `aiofiles`: Async file operations
- `rich`: Progress display and formatting
- `pyyaml`: YAML file support
- `jsonschema`: JSON schema validation (optional)

## License

This module is part of the LocalAgent project and follows the same license terms.

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass

## Error Recovery Examples

### Transaction Rollback

```python
try:
    async with FileTransaction() as tx:
        tx.add_write("file1.json", data1, "json")
        tx.add_write("file2.json", data2, "json")
        tx.add_write("file3.json", invalid_data, "json")  # This fails
        await tx.commit()
except AtomicWriteError:
    # All operations automatically rolled back
    # file1.json and file2.json are not created
    pass
```

### Backup Recovery

```python
# Original file preserved on failure
try:
    async with AtomicWriter("important.json", backup=True) as writer:
        await writer.write_json(new_data)
        raise Exception("Simulated failure")
except:
    # Original file is preserved
    # Backup can be used for manual recovery
    pass
```

This atomic operations module provides enterprise-grade file handling with comprehensive safety mechanisms, making it ideal for critical data operations in production environments.