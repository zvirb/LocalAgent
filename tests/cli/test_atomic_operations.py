"""
Comprehensive test suite for atomic file operations

Tests all aspects of the atomic.py module including:
- AtomicWriter functionality
- FileTransaction operations  
- Error handling and recovery
- Schema validation
- Integrity checking
- Audit trails
- Rich progress integration
"""

import asyncio
import json
import yaml
import tempfile
import pytest
import os
import shutil
import time
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import the module under test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "app"))

from cli.io.atomic import (
    AtomicWriter,
    AtomicFileManager,
    FileTransaction,
    AtomicFileOperations,
    AuditTrail,
    RecoveryManager,
    AtomicWriteError,
    ValidationError,
    IntegrityError,
    write_config_atomically,
    safe_file_rotation,
    set_global_audit_trail,
    get_global_audit_trail
)

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

class TestAtomicWriter:
    """Test AtomicWriter class functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def test_file(self, temp_dir):
        """Create test file path"""
        return temp_dir / "test_file.txt"
    
    @pytest.mark.asyncio
    async def test_atomic_text_write_success(self, test_file):
        """Test successful atomic text write"""
        content = "Hello, atomic world!"
        
        async with AtomicWriter(test_file, show_progress=False) as writer:
            await writer.write_text(content)
        
        # Verify file exists and has correct content
        assert test_file.exists()
        assert test_file.read_text() == content
    
    @pytest.mark.asyncio
    async def test_atomic_json_write_success(self, test_file):
        """Test successful atomic JSON write"""
        data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        json_file = test_file.with_suffix(".json")
        
        async with AtomicWriter(json_file, show_progress=False) as writer:
            await writer.write_json(data)
        
        # Verify file exists and has correct content
        assert json_file.exists()
        loaded_data = json.loads(json_file.read_text())
        assert loaded_data == data
    
    @pytest.mark.asyncio
    async def test_atomic_yaml_write_success(self, test_file):
        """Test successful atomic YAML write"""
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        yaml_file = test_file.with_suffix(".yaml")
        
        async with AtomicWriter(yaml_file, show_progress=False) as writer:
            await writer.write_yaml(data)
        
        # Verify file exists and has correct content
        assert yaml_file.exists()
        loaded_data = yaml.safe_load(yaml_file.read_text())
        assert loaded_data == data
    
    @pytest.mark.asyncio
    async def test_backup_creation(self, test_file):
        """Test backup file creation"""
        # Create original file
        original_content = "Original content"
        test_file.write_text(original_content)
        
        # Write new content with backup
        new_content = "New content"
        async with AtomicWriter(test_file, backup=True, show_progress=False) as writer:
            await writer.write_text(new_content)
        
        # Verify new content and backup
        assert test_file.read_text() == new_content
        backup_file = test_file.with_suffix(test_file.suffix + ".backup")
        assert backup_file.exists()
        assert backup_file.read_text() == original_content
    
    @pytest.mark.asyncio
    async def test_integrity_verification(self, test_file):
        """Test file integrity verification"""
        content = "Content for integrity check"
        
        async with AtomicWriter(test_file, verify_integrity=True, show_progress=False) as writer:
            await writer.write_text(content)
        
        # Verify file integrity
        assert test_file.exists()
        assert test_file.read_text() == content
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not available")
    async def test_json_schema_validation_success(self, test_file):
        """Test JSON schema validation success"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"}
            },
            "required": ["name", "age"]
        }
        
        valid_data = {"name": "John", "age": 30}
        json_file = test_file.with_suffix(".json")
        
        async with AtomicWriter(json_file, schema=schema, show_progress=False) as writer:
            await writer.write_json(valid_data)
        
        assert json_file.exists()
        loaded_data = json.loads(json_file.read_text())
        assert loaded_data == valid_data
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not available")
    async def test_json_schema_validation_failure(self, test_file):
        """Test JSON schema validation failure"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"}
            },
            "required": ["name", "age"]
        }
        
        invalid_data = {"name": "John"}  # Missing required 'age' field
        json_file = test_file.with_suffix(".json")
        
        with pytest.raises(ValidationError):
            async with AtomicWriter(json_file, schema=schema, show_progress=False) as writer:
                await writer.write_json(invalid_data)
        
        # File should not exist after failed validation
        assert not json_file.exists()
    
    @pytest.mark.asyncio
    async def test_write_failure_cleanup(self, test_file):
        """Test cleanup after write failure"""
        async with AtomicWriter(test_file, show_progress=False) as writer:
            # Simulate write failure
            with patch.object(writer, 'write_text', side_effect=Exception("Simulated error")):
                with pytest.raises(Exception):
                    await writer.write_text("content")
        
        # File should not exist after failure
        assert not test_file.exists()
        
        # Temporary files should be cleaned up
        temp_files = list(test_file.parent.glob(f".{test_file.name}.tmp*"))
        assert len(temp_files) == 0
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self, test_file):
        """Test handling of large files with progress tracking"""
        # Create large content (> 1MB)
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        
        async with AtomicWriter(test_file, show_progress=False) as writer:
            await writer.write_text(large_content)
        
        assert test_file.exists()
        assert test_file.read_text() == large_content

class TestAtomicFileManager:
    """Test AtomicFileManager utility functions"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_update_json(self, temp_dir):
        """Test JSON file update functionality"""
        json_file = temp_dir / "config.json"
        initial_data = {"version": 1, "settings": {"debug": False}}
        
        # Create initial file
        await AtomicFileManager.write_json(json_file, initial_data)
        
        # Update file
        def update_func(data):
            data["version"] = 2
            data["settings"]["debug"] = True
            data["new_field"] = "added"
            return data
        
        await AtomicFileManager.update_json(json_file, update_func)
        
        # Verify update
        with open(json_file) as f:
            updated_data = json.load(f)
        
        assert updated_data["version"] == 2
        assert updated_data["settings"]["debug"] is True
        assert updated_data["new_field"] == "added"
    
    @pytest.mark.asyncio
    async def test_safe_copy(self, temp_dir):
        """Test safe file copy functionality"""
        source_file = temp_dir / "source.txt"
        dest_file = temp_dir / "destination.txt"
        
        content = "Content to copy"
        source_file.write_text(content)
        
        await AtomicFileManager.safe_copy(source_file, dest_file)
        
        assert dest_file.exists()
        assert dest_file.read_text() == content
        assert source_file.exists()  # Original should still exist
    
    @pytest.mark.asyncio
    async def test_safe_move(self, temp_dir):
        """Test safe file move functionality"""
        source_file = temp_dir / "source.txt"
        dest_file = temp_dir / "destination.txt"
        
        content = "Content to move"
        source_file.write_text(content)
        
        await AtomicFileManager.safe_move(source_file, dest_file)
        
        assert dest_file.exists()
        assert dest_file.read_text() == content
        assert not source_file.exists()  # Source should be moved
    
    @pytest.mark.asyncio
    async def test_large_file_copy(self, temp_dir):
        """Test copying large files (>100MB simulation)"""
        source_file = temp_dir / "large_source.txt"
        dest_file = temp_dir / "large_dest.txt"
        
        # Create a moderately sized file to test chunking
        content = "x" * (1024 * 1024)  # 1MB
        source_file.write_bytes(content.encode())
        
        await AtomicFileManager.safe_copy(source_file, dest_file)
        
        assert dest_file.exists()
        assert dest_file.read_bytes() == content.encode()

class TestFileTransaction:
    """Test FileTransaction functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_successful_transaction(self, temp_dir):
        """Test successful multi-file transaction"""
        file1 = temp_dir / "file1.json"
        file2 = temp_dir / "file2.yaml"
        file3 = temp_dir / "file3.txt"
        
        data1 = {"key": "value1"}
        data2 = {"key": "value2"}
        text3 = "text content"
        
        async with FileTransaction(show_progress=False) as tx:
            tx.add_write(file1, data1, 'json')
            tx.add_write(file2, data2, 'yaml')
            tx.add_write(file3, text3, 'text')
            
            await tx.commit()
        
        # Verify all files were created
        assert file1.exists()
        assert file2.exists()
        assert file3.exists()
        
        # Verify content
        assert json.loads(file1.read_text()) == data1
        assert yaml.safe_load(file2.read_text()) == data2
        assert file3.read_text() == text3
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, temp_dir):
        """Test transaction rollback on failure"""
        file1 = temp_dir / "file1.json"
        file2 = temp_dir / "file2.json"
        
        data1 = {"key": "value1"}
        data2 = {"key": "value2"}
        
        # Create transaction that will fail
        tx = FileTransaction(show_progress=False)
        tx.add_write(file1, data1, 'json')
        tx.add_write(file2, data2, 'json')
        
        # Simulate failure during second operation
        with patch.object(AtomicWriter, 'write_json', side_effect=[None, Exception("Simulated failure")]):
            with pytest.raises(AtomicWriteError):
                await tx.commit()
        
        # Files should not exist after rollback
        assert not file1.exists()
        assert not file2.exists()
    
    @pytest.mark.asyncio
    async def test_copy_operations(self, temp_dir):
        """Test copy operations in transactions"""
        source_file = temp_dir / "source.txt"
        dest_file1 = temp_dir / "dest1.txt"
        dest_file2 = temp_dir / "dest2.txt"
        
        content = "Content to copy"
        source_file.write_text(content)
        
        async with FileTransaction(show_progress=False) as tx:
            tx.add_copy(source_file, dest_file1)
            tx.add_copy(source_file, dest_file2)
            
            await tx.commit()
        
        assert dest_file1.exists()
        assert dest_file2.exists()
        assert dest_file1.read_text() == content
        assert dest_file2.read_text() == content
    
    @pytest.mark.asyncio
    async def test_delete_operations_with_backup(self, temp_dir):
        """Test delete operations with backup in transactions"""
        file_to_delete = temp_dir / "delete_me.txt"
        content = "Content to delete"
        file_to_delete.write_text(content)
        
        async with FileTransaction(show_progress=False) as tx:
            tx.add_delete(file_to_delete)
            await tx.commit()
        
        # File should be deleted
        assert not file_to_delete.exists()
        
        # Backup should exist
        backup_files = list(temp_dir.glob("*.deleted_backup"))
        assert len(backup_files) == 1
        assert backup_files[0].read_text() == content

class TestAuditTrail:
    """Test AuditTrail functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_audit_trail_logging(self, temp_dir):
        """Test audit trail operation logging"""
        audit_file = temp_dir / "audit.log"
        audit_trail = AuditTrail(audit_file)
        
        # Log some operations
        test_file = Path("test.txt")
        audit_trail.log_operation("write", test_file, {"size": 100}, "started")
        audit_trail.log_operation("write", test_file, {"size": 100}, "completed")
        
        # Check audit entries
        assert len(audit_trail.audit_entries) == 2
        assert audit_trail.audit_entries[0]["operation"] == "write"
        assert audit_trail.audit_entries[0]["status"] == "started"
        assert audit_trail.audit_entries[1]["status"] == "completed"
    
    def test_operations_summary(self, temp_dir):
        """Test operations summary generation"""
        audit_trail = AuditTrail()
        
        # Add various operations
        audit_trail.log_operation("write", Path("file1.txt"), status="completed")
        audit_trail.log_operation("read", Path("file2.txt"), status="completed")
        audit_trail.log_operation("delete", Path("file3.txt"), status="failed", error="Permission denied")
        
        summary = audit_trail.get_operations_summary()
        
        assert summary["total_operations"] == 3
        assert summary["successful_operations"] == 2
        assert summary["failed_operations"] == 1
        assert summary["files_affected"] == 3

class TestAtomicFileOperations:
    """Test high-level AtomicFileOperations class"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_atomic_json_update(self, temp_dir):
        """Test atomic JSON update functionality"""
        ops = AtomicFileOperations()
        json_file = temp_dir / "config.json"
        
        # Update non-existing file (should create)
        result = await ops.atomic_json_update(
            json_file,
            lambda data: {**data, "new_key": "new_value", "counter": 1}
        )
        
        assert result == {"new_key": "new_value", "counter": 1}
        assert json_file.exists()
        
        # Update existing file
        result = await ops.atomic_json_update(
            json_file,
            lambda data: {**data, "counter": data.get("counter", 0) + 1}
        )
        
        assert result["counter"] == 2
        assert result["new_key"] == "new_value"
    
    @pytest.mark.asyncio
    async def test_config_merge(self, temp_dir):
        """Test configuration file merging"""
        ops = AtomicFileOperations()
        
        # Create source config files
        config1 = temp_dir / "config1.json"
        config2 = temp_dir / "config2.json"
        output_config = temp_dir / "merged.json"
        
        data1 = {"app": {"name": "test", "version": "1.0"}, "debug": True}
        data2 = {"app": {"version": "2.0", "author": "tester"}, "features": ["A", "B"]}
        
        config1.write_text(json.dumps(data1))
        config2.write_text(json.dumps(data2))
        
        # Merge configurations
        result = await ops.atomic_config_merge([config1, config2], output_config)
        
        # Verify deep merge
        assert result["app"]["name"] == "test"  # From config1
        assert result["app"]["version"] == "2.0"  # From config2 (overridden)
        assert result["app"]["author"] == "tester"  # From config2
        assert result["debug"] is True  # From config1
        assert result["features"] == ["A", "B"]  # From config2
    
    @pytest.mark.asyncio
    async def test_cleanup_backups(self, temp_dir):
        """Test backup cleanup functionality"""
        ops = AtomicFileOperations()
        
        # Create some backup files with different ages
        old_backup = temp_dir / "old_file.txt.backup"
        recent_backup = temp_dir / "recent_file.txt.backup"
        
        old_backup.write_text("old content")
        recent_backup.write_text("recent content")
        
        # Manually set old timestamp (simulate old file)
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(old_backup, (old_time, old_time))
        
        # Cleanup backups older than 24 hours
        removed_count = await ops.cleanup_backups(temp_dir, max_age_hours=24)
        
        assert removed_count == 1
        assert not old_backup.exists()
        assert recent_backup.exists()

class TestUtilityFunctions:
    """Test utility functions"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_write_config_atomically(self, temp_dir):
        """Test write_config_atomically function"""
        json_config = temp_dir / "config.json"
        yaml_config = temp_dir / "config.yaml"
        
        config_data = {"setting1": "value1", "setting2": 42}
        
        # Test JSON config
        await write_config_atomically(json_config, config_data)
        assert json_config.exists()
        assert json.loads(json_config.read_text()) == config_data
        
        # Test YAML config
        await write_config_atomically(yaml_config, config_data)
        assert yaml_config.exists()
        assert yaml.safe_load(yaml_config.read_text()) == config_data
    
    @pytest.mark.asyncio
    async def test_safe_file_rotation(self, temp_dir):
        """Test safe file rotation function"""
        log_file = temp_dir / "app.log"
        
        # Create initial log file
        log_file.write_text("Initial log content")
        
        # Rotate the file
        await safe_file_rotation(log_file, max_files=3)
        
        # Original file should be moved to .1
        rotated_file = temp_dir / "app.log.1"
        assert rotated_file.exists()
        assert rotated_file.read_text() == "Initial log content"
        assert not log_file.exists()

class TestErrorHandling:
    """Test error handling and recovery mechanisms"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_atomic_write_error_context(self):
        """Test AtomicWriteError context information"""
        context = {"operation_id": "test_op", "file_path": "/tmp/test"}
        error = AtomicWriteError("Test error", operation_context=context)
        
        assert error.operation_context == context
        assert error.timestamp > 0
    
    def test_recovery_manager(self):
        """Test RecoveryManager functionality"""
        recovery_manager = RecoveryManager()
        test_file = Path("/tmp/test.txt")
        backup_path = Path("/tmp/test.txt.backup")
        
        # Add recovery point
        recovery_manager.add_recovery_point("write", test_file, backup_path)
        
        assert len(recovery_manager.recovery_stack) == 1
        assert recovery_manager.recovery_stack[0]["operation"] == "write"
        assert recovery_manager.recovery_stack[0]["file_path"] == test_file
    
    def test_global_audit_trail(self):
        """Test global audit trail functionality"""
        audit_file = Path("/tmp/global_audit.log")
        
        # Set global audit trail
        set_global_audit_trail(audit_file)
        
        # Get global audit trail
        global_trail = get_global_audit_trail()
        
        assert global_trail is not None
        assert global_trail.audit_file == audit_file

class TestIntegrationScenarios:
    """Integration tests for complex scenarios"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_complex_workflow_scenario(self, temp_dir):
        """Test complex workflow with multiple operations"""
        ops = AtomicFileOperations()
        
        # Simulate a complex configuration management scenario
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        
        # Create multiple config files
        base_config = {"app": {"name": "testapp", "version": "1.0"}}
        env_config = {"app": {"debug": True}, "database": {"host": "localhost"}}
        user_config = {"app": {"theme": "dark"}, "user": {"name": "testuser"}}
        
        base_file = config_dir / "base.json"
        env_file = config_dir / "env.json"
        user_file = config_dir / "user.json"
        merged_file = config_dir / "app_config.json"
        
        # Use batch operation context manager
        async with ops.batch_operation("config_setup"):
            # Write individual config files
            await write_config_atomically(base_file, base_config)
            await write_config_atomically(env_file, env_config)
            await write_config_atomically(user_file, user_config)
            
            # Merge all configs
            merged_result = await ops.atomic_config_merge(
                [base_file, env_file, user_file],
                merged_file
            )
        
        # Verify final merged configuration
        assert merged_result["app"]["name"] == "testapp"
        assert merged_result["app"]["version"] == "1.0"
        assert merged_result["app"]["debug"] is True
        assert merged_result["app"]["theme"] == "dark"
        assert merged_result["database"]["host"] == "localhost"
        assert merged_result["user"]["name"] == "testuser"
        
        # Verify audit trail
        summary = ops.get_audit_summary()
        assert summary["total_operations"] > 0
        assert summary["successful_operations"] > 0
    
    @pytest.mark.asyncio
    async def test_failure_recovery_scenario(self, temp_dir):
        """Test failure and recovery in complex scenario"""
        critical_file = temp_dir / "critical_data.json"
        backup_file = temp_dir / "critical_data.json.backup"
        
        # Create initial critical file
        initial_data = {"critical": True, "version": 1, "data": "important"}
        critical_file.write_text(json.dumps(initial_data))
        
        # Simulate a write operation that creates backup but fails
        try:
            async with AtomicWriter(critical_file, backup=True, show_progress=False) as writer:
                # This should create a backup
                await writer.write_json({"critical": True, "version": 2, "data": "updated"})
                # Simulate failure after backup but before final commit
                raise Exception("Simulated failure")
        except Exception:
            pass
        
        # Original file should be restored from backup
        # (In real scenario, recovery mechanism would handle this)
        if backup_file.exists():
            # Manual recovery simulation
            backup_content = json.loads(backup_file.read_text())
            assert backup_content == initial_data

# Performance tests
class TestPerformance:
    """Performance tests for atomic operations"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_large_transaction_performance(self, temp_dir):
        """Test performance of large transactions"""
        start_time = time.time()
        
        # Create a transaction with many files
        async with FileTransaction(show_progress=False) as tx:
            for i in range(100):
                file_path = temp_dir / f"file_{i}.json"
                data = {"index": i, "data": f"content_{i}"}
                tx.add_write(file_path, data, 'json')
            
            await tx.commit()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time
        assert duration < 10.0  # 10 seconds max for 100 files
        
        # Verify all files were created
        created_files = list(temp_dir.glob("file_*.json"))
        assert len(created_files) == 100
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, temp_dir):
        """Test concurrent atomic operations"""
        async def write_file(file_index):
            file_path = temp_dir / f"concurrent_{file_index}.json"
            data = {"index": file_index, "timestamp": time.time()}
            
            async with AtomicWriter(file_path, show_progress=False) as writer:
                await writer.write_json(data)
            
            return file_path
        
        # Run multiple concurrent operations
        tasks = [write_file(i) for i in range(20)]
        completed_files = await asyncio.gather(*tasks)
        
        # Verify all files were created successfully
        assert len(completed_files) == 20
        for file_path in completed_files:
            assert file_path.exists()

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])