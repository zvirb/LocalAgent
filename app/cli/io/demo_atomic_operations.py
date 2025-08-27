#!/usr/bin/env python3
"""
Demonstration script for atomic file operations

This script shows how to use the advanced atomic file operations module
with examples of all major features.

Requirements:
    pip install aiofiles rich pyyaml jsonschema
"""

import asyncio
import json
import yaml
import tempfile
from pathlib import Path
import logging

# Configure logging to see audit trail
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

try:
    from atomic import (
        AtomicWriter,
        AtomicFileManager,
        FileTransaction,
        AtomicFileOperations,
        AuditTrail,
        write_config_atomically,
        safe_file_rotation
    )
    print("✓ Successfully imported atomic operations module")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Please install required packages: pip install aiofiles rich pyyaml jsonschema")
    exit(1)

async def demo_basic_atomic_writer():
    """Demonstrate basic AtomicWriter functionality"""
    print("\n=== AtomicWriter Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Example 1: Simple JSON write with progress and backup
        config_file = temp_dir / "app_config.json"
        config_data = {
            "app": {
                "name": "Demo App",
                "version": "1.0.0",
                "debug": True
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "demo_db"
            }
        }
        
        print(f"Writing configuration to {config_file}")
        async with AtomicWriter(config_file, backup=True, verify_integrity=True) as writer:
            await writer.write_json(config_data, indent=2)
        
        print(f"✓ Configuration written successfully")
        print(f"✓ File size: {config_file.stat().st_size} bytes")
        
        # Example 2: Update existing file with backup
        print(f"\nUpdating configuration...")
        async with AtomicWriter(config_file, backup=True) as writer:
            config_data["app"]["version"] = "1.1.0"
            config_data["app"]["debug"] = False
            config_data["features"] = ["feature1", "feature2"]
            await writer.write_json(config_data, indent=2)
        
        # Check backup was created
        backup_file = config_file.with_suffix(config_file.suffix + ".backup")
        if backup_file.exists():
            print(f"✓ Backup created at {backup_file}")
        
        # Example 3: YAML write
        yaml_file = temp_dir / "settings.yaml"
        yaml_data = {
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "ssl": True
            },
            "logging": {
                "level": "INFO",
                "file": "app.log"
            }
        }
        
        print(f"\nWriting YAML configuration to {yaml_file}")
        async with AtomicWriter(yaml_file) as writer:
            await writer.write_yaml(yaml_data)
        
        print(f"✓ YAML configuration written successfully")

async def demo_file_transaction():
    """Demonstrate FileTransaction for multi-file operations"""
    print("\n=== FileTransaction Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Create multiple related configuration files in a transaction
        base_config = {"environment": "production", "version": "2.0"}
        database_config = {"host": "db.example.com", "port": 5432}
        cache_config = {"redis_host": "cache.example.com", "ttl": 3600}
        
        print("Creating multiple configuration files in a transaction...")
        
        try:
            async with FileTransaction(show_progress=True) as tx:
                tx.add_write(temp_dir / "base.json", base_config, "json")
                tx.add_write(temp_dir / "database.json", database_config, "json")
                tx.add_write(temp_dir / "cache.json", cache_config, "json")
                
                # Also create a summary file
                summary = {
                    "created_files": ["base.json", "database.json", "cache.json"],
                    "creation_time": "2024-01-01T00:00:00Z"
                }
                tx.add_write(temp_dir / "summary.json", summary, "json")
                
                await tx.commit()
            
            print("✓ Transaction completed successfully")
            
            # Verify all files were created
            created_files = list(temp_dir.glob("*.json"))
            print(f"✓ Created {len(created_files)} files: {[f.name for f in created_files]}")
            
        except Exception as e:
            print(f"✗ Transaction failed: {e}")

async def demo_atomic_file_operations():
    """Demonstrate high-level AtomicFileOperations"""
    print("\n=== AtomicFileOperations Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        audit_file = temp_dir / "audit.log"
        
        # Create operations instance with audit trail
        ops = AtomicFileOperations(audit_file)
        
        # Example 1: Atomic JSON update
        print("Performing atomic JSON updates...")
        
        config_file = temp_dir / "dynamic_config.json"
        
        # Update 1: Create initial config
        result = await ops.atomic_json_update(
            config_file,
            lambda data: {**data, "initialized": True, "counter": 1}
        )
        print(f"✓ Initial config created: {result}")
        
        # Update 2: Increment counter
        result = await ops.atomic_json_update(
            config_file,
            lambda data: {**data, "counter": data.get("counter", 0) + 1, "last_update": "now"}
        )
        print(f"✓ Config updated: {result}")
        
        # Example 2: Config merging
        print("\nMerging multiple configuration files...")
        
        # Create source configs
        config1_data = {"app": {"name": "demo", "debug": True}, "feature_a": True}
        config2_data = {"app": {"version": "1.0", "debug": False}, "feature_b": True}
        
        config1 = temp_dir / "config1.json"
        config2 = temp_dir / "config2.json"
        merged_config = temp_dir / "merged_config.json"
        
        await write_config_atomically(config1, config1_data)
        await write_config_atomically(config2, config2_data)
        
        merged_result = await ops.atomic_config_merge(
            [config1, config2],
            merged_config,
            merge_strategy="deep"
        )
        
        print(f"✓ Configs merged successfully")
        print(f"  Merged result: {json.dumps(merged_result, indent=2)}")
        
        # Example 3: Batch operations
        print("\nPerforming batch operations...")
        
        async with ops.batch_operation("demo_batch"):
            # Create several files in batch
            for i in range(3):
                batch_file = temp_dir / f"batch_file_{i}.json"
                await write_config_atomically(batch_file, {"batch_id": i, "created": True})
        
        # Show audit summary
        print("\nAudit Trail Summary:")
        ops.display_audit_summary()
        
        # Check audit file
        if audit_file.exists():
            print(f"\n✓ Audit log created with {len(audit_file.read_text().splitlines())} entries")

async def demo_schema_validation():
    """Demonstrate schema validation (if jsonschema is available)"""
    print("\n=== Schema Validation Demo ===")
    
    try:
        import jsonschema
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            
            # Define a schema for user data
            user_schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "email": {"type": "string", "format": "email"},
                    "age": {"type": "number", "minimum": 0, "maximum": 120},
                    "active": {"type": "boolean"}
                },
                "required": ["name", "email"]
            }
            
            user_file = temp_dir / "user.json"
            
            # Example 1: Valid data
            print("Writing valid user data...")
            valid_user = {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
                "active": True
            }
            
            async with AtomicWriter(user_file, schema=user_schema, show_progress=False) as writer:
                await writer.write_json(valid_user)
            
            print("✓ Valid data written successfully")
            
            # Example 2: Invalid data (should fail)
            print("\nTrying to write invalid user data...")
            invalid_user = {
                "name": "Jane Doe",
                # Missing required email field
                "age": 25
            }
            
            try:
                async with AtomicWriter(user_file, schema=user_schema, show_progress=False) as writer:
                    await writer.write_json(invalid_user)
                print("✗ This should not have succeeded!")
            except Exception as e:
                print(f"✓ Validation correctly rejected invalid data: {type(e).__name__}")
                
    except ImportError:
        print("Schema validation demo skipped (jsonschema not available)")

async def demo_error_handling():
    """Demonstrate error handling and recovery"""
    print("\n=== Error Handling Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        # Create a critical file
        critical_file = temp_dir / "critical.json"
        original_data = {"critical": True, "version": 1, "important_data": "must_preserve"}
        
        await write_config_atomically(critical_file, original_data)
        print(f"✓ Created critical file: {critical_file}")
        
        # Simulate a failed update that should preserve the original
        print("\nSimulating failed update with backup preservation...")
        
        try:
            async with AtomicWriter(critical_file, backup=True, show_progress=False) as writer:
                # Write some new data
                new_data = {"critical": True, "version": 2, "important_data": "updated"}
                await writer.write_json(new_data)
                
                # Simulate an error after writing but before committing
                # In real usage, this could be a power failure, disk full, etc.
                raise Exception("Simulated failure during write process")
                
        except Exception as e:
            print(f"✓ Write failed as expected: {e}")
        
        # Check that original file is preserved
        if critical_file.exists():
            current_data = json.loads(critical_file.read_text())
            if current_data == original_data:
                print("✓ Original data preserved after failed write")
            else:
                print("✗ Original data was corrupted!")
        
        # Check if backup exists
        backup_file = critical_file.with_suffix(critical_file.suffix + ".backup")
        if backup_file.exists():
            print(f"✓ Backup file exists: {backup_file}")

async def demo_file_rotation():
    """Demonstrate file rotation functionality"""
    print("\n=== File Rotation Demo ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        
        log_file = temp_dir / "app.log"
        
        # Create initial log file
        log_file.write_text("Initial log content\n")
        print(f"✓ Created log file: {log_file}")
        
        # Simulate log rotation
        print("Performing log rotation...")
        await safe_file_rotation(log_file, max_files=3)
        
        # Check rotation result
        rotated_file = temp_dir / "app.log.1"
        if rotated_file.exists():
            print(f"✓ Log rotated to: {rotated_file}")
            print(f"  Content: {rotated_file.read_text().strip()}")
        
        if not log_file.exists():
            print("✓ Original log file removed (ready for new logs)")

async def main():
    """Run all demonstrations"""
    print("🚀 Atomic File Operations Demo")
    print("=" * 50)
    
    try:
        await demo_basic_atomic_writer()
        await demo_file_transaction()
        await demo_atomic_file_operations()
        await demo_schema_validation()
        await demo_error_handling()
        await demo_file_rotation()
        
        print("\n" + "=" * 50)
        print("✅ All demonstrations completed successfully!")
        print("\nThe atomic operations module provides:")
        print("  • Safe write-then-rename atomic operations")
        print("  • Multi-file transactions with rollback")
        print("  • Progress display with Rich integration")
        print("  • File integrity checking with checksums")
        print("  • Schema validation for JSON/YAML")
        print("  • Comprehensive audit trails")
        print("  • Advanced error handling and recovery")
        print("  • Backup and rollback mechanisms")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())