"""
Comprehensive Security Tests for LocalAgent Security Implementation
Validates CVE-2024-LOCALAGENT-001, 002, 003 mitigations
"""

import unittest
import tempfile
import shutil
import os
import sys
import asyncio
from pathlib import Path
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock

# Add security module to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from key_manager import SecureKeyManager
    from encryption import EncryptionService
    from audit import AuditLogger
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running tests from the correct directory")
    sys.exit(1)


class TestSecureKeyManager(unittest.TestCase):
    """Test secure key management functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.key_manager = SecureKeyManager(service_name="test_localagent")
        
    def tearDown(self):
        """Clean up test environment"""
        try:
            # Clean up keyring entries
            providers = self.key_manager.list_stored_providers()
            for provider in providers:
                self.key_manager.delete_api_key(provider)
                
            # Clean up test directory
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except:
            pass
    
    def test_store_and_retrieve_api_key(self):
        """Test basic API key storage and retrieval"""
        provider = "test_openai"
        api_key = "sk-test123456789"
        
        # Store key
        result = self.key_manager.store_api_key(provider, api_key)
        self.assertTrue(result, "Failed to store API key")
        
        # Retrieve key
        retrieved_key = self.key_manager.retrieve_api_key(provider)
        self.assertEqual(retrieved_key, api_key, "Retrieved key doesn't match stored key")
    
    def test_store_api_key_with_metadata(self):
        """Test API key storage with metadata"""
        provider = "test_gemini"
        api_key = "AIza-test123456789"
        metadata = {
            "created_by": "test_user",
            "environment": "testing",
            "permissions": ["read", "write"]
        }
        
        # Store key with metadata
        result = self.key_manager.store_api_key(provider, api_key, metadata)
        self.assertTrue(result, "Failed to store API key with metadata")
        
        # Retrieve metadata
        retrieved_metadata = self.key_manager.get_key_metadata(provider)
        self.assertIsNotNone(retrieved_metadata, "Failed to retrieve metadata")
        self.assertEqual(retrieved_metadata["created_by"], metadata["created_by"])
        self.assertEqual(retrieved_metadata["environment"], metadata["environment"])
        self.assertIn("created_at", retrieved_metadata)
    
    def test_input_validation(self):
        """Test input validation for key operations"""
        # Test invalid key names
        with self.assertRaises(ValueError):
            self.key_manager.store_api_key("", "test_key")
        
        with self.assertRaises(ValueError):
            self.key_manager.store_api_key("invalid@#$%", "test_key")
        
        with self.assertRaises(ValueError):
            self.key_manager.store_api_key("x" * 300, "test_key")
        
        # Test invalid key values
        with self.assertRaises(ValueError):
            self.key_manager.store_api_key("test_provider", "")
        
        with self.assertRaises(ValueError):
            self.key_manager.store_api_key("test_provider", "x" * 20000)
    
    def test_delete_api_key(self):
        """Test API key deletion"""
        provider = "test_delete"
        api_key = "test-key-to-delete"
        
        # Store key
        self.key_manager.store_api_key(provider, api_key)
        
        # Verify it exists
        retrieved = self.key_manager.retrieve_api_key(provider)
        self.assertEqual(retrieved, api_key)
        
        # Delete key
        delete_result = self.key_manager.delete_api_key(provider)
        self.assertTrue(delete_result, "Failed to delete API key")
        
        # Verify it's gone
        retrieved_after_delete = self.key_manager.retrieve_api_key(provider)
        self.assertIsNone(retrieved_after_delete, "API key still exists after deletion")
    
    def test_list_stored_providers(self):
        """Test listing stored providers"""
        providers = ["test_provider1", "test_provider2", "test_provider3"]
        
        # Store keys for multiple providers
        for i, provider in enumerate(providers):
            self.key_manager.store_api_key(provider, f"key_{i}")
        
        # List providers
        stored_providers = self.key_manager.list_stored_providers()
        
        # Check that all providers are listed
        for provider in providers:
            self.assertIn(provider, stored_providers, f"Provider {provider} not in list")
    
    def test_health_check(self):
        """Test key manager health check"""
        health = self.key_manager.health_check()
        
        self.assertIsInstance(health, dict, "Health check should return dict")
        self.assertIn("healthy", health, "Health check should include 'healthy' status")
        self.assertIn("keyring_available", health, "Health check should test keyring")
        self.assertIn("encryption_functional", health, "Health check should test encryption")
        
        # Should be healthy in normal conditions
        self.assertTrue(health["healthy"], "Key manager should be healthy")
        self.assertTrue(health["keyring_available"], "Keyring should be available")
        self.assertTrue(health["encryption_functional"], "Encryption should be functional")
    
    def test_concurrent_access(self):
        """Test concurrent access to key manager"""
        provider = "test_concurrent"
        results = []
        
        def store_key(key_suffix):
            try:
                result = self.key_manager.store_api_key(f"{provider}_{key_suffix}", f"key_{key_suffix}")
                results.append(("store", key_suffix, result))
            except Exception as e:
                results.append(("store", key_suffix, e))
        
        def retrieve_key(key_suffix):
            try:
                result = self.key_manager.retrieve_api_key(f"{provider}_{key_suffix}")
                results.append(("retrieve", key_suffix, result))
            except Exception as e:
                results.append(("retrieve", key_suffix, e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=store_key, args=(i,)))
            threads.append(threading.Thread(target=retrieve_key, args=(i,)))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Check results
        store_results = [r for r in results if r[0] == "store"]
        self.assertGreater(len(store_results), 0, "No store operations completed")
        
        # At least some operations should succeed
        successful_stores = [r for r in store_results if r[2] is True]
        self.assertGreater(len(successful_stores), 0, "No successful store operations")


class TestEncryptionService(unittest.TestCase):
    """Test encryption service functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.encryption_service = EncryptionService(master_password="test_master_password_123")
    
    def test_aes_gcm_encryption_decryption(self):
        """Test AES-GCM encryption and decryption"""
        test_data = "This is sensitive test data that needs encryption"
        purpose = "test_purpose"
        
        # Encrypt
        encrypted = self.encryption_service.encrypt_aes_gcm(test_data, purpose)
        
        # Validate encrypted structure
        required_fields = ["ciphertext", "salt", "nonce", "algorithm", "purpose"]
        for field in required_fields:
            self.assertIn(field, encrypted, f"Missing field: {field}")
        
        self.assertEqual(encrypted["algorithm"], "AES-256-GCM")
        self.assertEqual(encrypted["purpose"], purpose)
        
        # Decrypt
        decrypted = self.encryption_service.decrypt_aes_gcm(encrypted)
        self.assertEqual(decrypted.decode(), test_data, "Decrypted data doesn't match original")
    
    def test_fernet_encryption_decryption(self):
        """Test Fernet encryption and decryption"""
        test_data = "Test data for Fernet encryption"
        purpose = "fernet_test"
        
        # Encrypt
        encrypted = self.encryption_service.encrypt_fernet(test_data, purpose)
        
        # Validate structure
        required_fields = ["ciphertext", "salt", "algorithm", "purpose"]
        for field in required_fields:
            self.assertIn(field, encrypted, f"Missing field: {field}")
        
        self.assertEqual(encrypted["algorithm"], "Fernet")
        
        # Decrypt
        decrypted = self.encryption_service.decrypt_fernet(encrypted)
        self.assertEqual(decrypted.decode(), test_data, "Decrypted data doesn't match original")
    
    def test_different_purposes_produce_different_results(self):
        """Test that different purposes produce different encrypted results"""
        test_data = "Same data, different purposes"
        purpose1 = "purpose_1"
        purpose2 = "purpose_2"
        
        encrypted1 = self.encryption_service.encrypt_aes_gcm(test_data, purpose1)
        encrypted2 = self.encryption_service.encrypt_aes_gcm(test_data, purpose2)
        
        # Should produce different ciphertexts
        self.assertNotEqual(encrypted1["ciphertext"], encrypted2["ciphertext"])
        
        # But should decrypt to same data with correct purpose
        decrypted1 = self.encryption_service.decrypt_aes_gcm(encrypted1)
        decrypted2 = self.encryption_service.decrypt_aes_gcm(encrypted2)
        
        self.assertEqual(decrypted1.decode(), test_data)
        self.assertEqual(decrypted2.decode(), test_data)
    
    def test_key_rotation(self):
        """Test key rotation functionality"""
        old_version = self.encryption_service.key_version
        
        # Rotate key
        result = self.encryption_service.rotate_key()
        self.assertTrue(result, "Key rotation should succeed")
        
        # Check new version
        new_version = self.encryption_service.key_version
        self.assertEqual(new_version, old_version + 1, "Key version should increment")
    
    def test_health_check(self):
        """Test encryption service health check"""
        health = self.encryption_service.health_check()
        
        self.assertIsInstance(health, dict)
        self.assertIn("healthy", health)
        self.assertIn("aes_gcm_functional", health)
        self.assertIn("fernet_functional", health)
        
        # Should be healthy
        self.assertTrue(health["healthy"])
        self.assertTrue(health["aes_gcm_functional"])
        self.assertTrue(health["fernet_functional"])
    
    def test_encryption_with_bytes_input(self):
        """Test encryption with bytes input"""
        test_bytes = b"Binary test data \x00\x01\x02\xff"
        
        # Test AES-GCM with bytes
        encrypted = self.encryption_service.encrypt_aes_gcm(test_bytes, "bytes_test")
        decrypted = self.encryption_service.decrypt_aes_gcm(encrypted)
        self.assertEqual(decrypted, test_bytes)
        
        # Test Fernet with bytes
        encrypted = self.encryption_service.encrypt_fernet(test_bytes, "bytes_test")
        decrypted = self.encryption_service.decrypt_fernet(encrypted)
        self.assertEqual(decrypted, test_bytes)


class TestAuditLogger(unittest.TestCase):
    """Test audit logging functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.audit_logger = AuditLogger(log_dir=self.test_dir, enable_signing=True)
        
        # Give the background thread time to start
        time.sleep(0.1)
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            # Signal shutdown
            if hasattr(self.audit_logger, 'log_queue'):
                self.audit_logger.log_queue.put(None)
            
            # Wait for thread to finish
            if hasattr(self.audit_logger, 'logging_thread'):
                self.audit_logger.logging_thread.join(timeout=2.0)
            
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except:
            pass
    
    def test_basic_logging(self):
        """Test basic audit logging"""
        self.audit_logger.log_key_operation("test_operation", {
            "test_field": "test_value",
            "number_field": 123
        })
        
        # Wait for async logging
        time.sleep(0.2)
        
        # Check log file exists
        log_file = Path(self.test_dir) / "audit.log"
        self.assertTrue(log_file.exists(), "Audit log file should exist")
        
        # Check log content
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
        
        self.assertGreater(len(log_lines), 0, "Log file should contain entries")
        
        # Parse first few lines (session start + test operation)
        for line in log_lines:
            try:
                entry = json.loads(line.strip())
                if entry.get("operation") == "test_operation":
                    self.assertEqual(entry["details"]["test_field"], "test_value")
                    self.assertEqual(entry["details"]["number_field"], 123)
                    self.assertIn("timestamp", entry)
                    self.assertIn("session_id", entry)
                    break
            except json.JSONDecodeError:
                continue
        else:
            self.fail("Test operation not found in log")
    
    def test_security_event_logging(self):
        """Test security event logging"""
        self.audit_logger.log_security_event(
            "unauthorized_access",
            "Unauthorized API key access attempt",
            {"provider": "test_provider", "ip": "192.168.1.100"},
            severity="WARNING"
        )
        
        time.sleep(0.2)
        
        # Verify log
        log_file = Path(self.test_dir) / "audit.log"
        with open(log_file, 'r') as f:
            content = f.read()
        
        self.assertIn("unauthorized_access", content)
        self.assertIn("Unauthorized API key access attempt", content)
        self.assertIn("test_provider", content)
    
    def test_authentication_event_logging(self):
        """Test authentication event logging"""
        self.audit_logger.log_authentication_event(
            "api_key_access",
            "openai",
            True,
            user_id="test_user",
            source_ip="127.0.0.1",
            details={"access_type": "retrieval"}
        )
        
        time.sleep(0.2)
        
        # Verify log
        log_file = Path(self.test_dir) / "audit.log"
        with open(log_file, 'r') as f:
            content = f.read()
        
        self.assertIn("api_key_access", content)
        self.assertIn("openai", content)
        self.assertIn("test_user", content)
        self.assertIn("127.0.0.1", content)
    
    def test_log_signing_verification(self):
        """Test log signing and verification"""
        # Log some operations
        for i in range(3):
            self.audit_logger.log_key_operation(f"test_op_{i}", {"index": i})
        
        time.sleep(0.5)  # Wait for logging
        
        # Verify log integrity
        verification_result = self.audit_logger.verify_log_integrity()
        
        self.assertIsInstance(verification_result, dict)
        self.assertIn("verified", verification_result)
        self.assertIn("total_entries", verification_result)
        self.assertIn("verified_entries", verification_result)
        
        # Should be verified (some entries might be unsigned like session_start)
        self.assertGreaterEqual(verification_result["verified_entries"], 3)
    
    def test_audit_summary(self):
        """Test audit summary generation"""
        # Log some operations
        operations = ["store_key", "retrieve_key", "delete_key"]
        for op in operations:
            self.audit_logger.log_key_operation(op, {"test": True})
        
        time.sleep(0.3)
        
        # Get summary
        summary = self.audit_logger.get_audit_summary(hours=1)
        
        self.assertIsInstance(summary, dict)
        self.assertIn("events", summary)
        self.assertIn("total", summary["events"])
        self.assertIn("by_operation", summary["events"])
        
        # Should have some events
        self.assertGreater(summary["events"]["total"], 0)
    
    def test_concurrent_logging(self):
        """Test concurrent logging from multiple threads"""
        def log_operations(thread_id):
            for i in range(5):
                self.audit_logger.log_key_operation(
                    f"thread_{thread_id}_op_{i}",
                    {"thread_id": thread_id, "operation_id": i}
                )
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=log_operations, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
        
        time.sleep(0.5)  # Wait for async logging
        
        # Check that all operations were logged
        log_file = Path(self.test_dir) / "audit.log"
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Should have entries from all threads
        for thread_id in range(3):
            for op_id in range(5):
                self.assertIn(f"thread_{thread_id}_op_{op_id}", content)


class TestSecurityIntegration(unittest.TestCase):
    """Integration tests for security components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create integrated security system
        self.key_manager = SecureKeyManager(service_name="integration_test")
        self.encryption_service = EncryptionService(master_password="integration_test_password")
        self.audit_logger = AuditLogger(log_dir=self.test_dir)
        
        time.sleep(0.1)  # Let audit logger start
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            # Clean up keys
            providers = self.key_manager.list_stored_providers()
            for provider in providers:
                self.key_manager.delete_api_key(provider)
            
            # Clean up audit logger
            if hasattr(self.audit_logger, 'log_queue'):
                self.audit_logger.log_queue.put(None)
            if hasattr(self.audit_logger, 'logging_thread'):
                self.audit_logger.logging_thread.join(timeout=2.0)
            
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except:
            pass
    
    def test_end_to_end_key_lifecycle(self):
        """Test complete key lifecycle with all security components"""
        provider = "test_e2e_provider"
        api_key = "sk-test-key-for-e2e-testing"
        
        # Store key (should trigger audit logging)
        store_result = self.key_manager.store_api_key(provider, api_key, {
            "test_metadata": True,
            "integration_test": "e2e_lifecycle"
        })
        self.assertTrue(store_result)
        
        # Retrieve key (should trigger audit logging)
        retrieved_key = self.key_manager.retrieve_api_key(provider)
        self.assertEqual(retrieved_key, api_key)
        
        # Test encryption directly
        encrypted_data = self.encryption_service.encrypt_aes_gcm(api_key, f"provider_{provider}")
        decrypted_data = self.encryption_service.decrypt_aes_gcm(encrypted_data)
        self.assertEqual(decrypted_data.decode(), api_key)
        
        # Delete key (should trigger audit logging)
        delete_result = self.key_manager.delete_api_key(provider)
        self.assertTrue(delete_result)
        
        # Verify deletion
        deleted_key = self.key_manager.retrieve_api_key(provider)
        self.assertIsNone(deleted_key)
        
        # Wait for audit logging
        time.sleep(0.3)
        
        # Check audit trail
        log_file = Path(self.test_dir) / "audit.log"
        self.assertTrue(log_file.exists())
        
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Should have audit entries for all operations
        self.assertIn("api_key_stored", content)
        self.assertIn("api_key_retrieved", content)
        self.assertIn("api_key_deleted", content)
        self.assertIn(provider, content)
    
    def test_security_system_health(self):
        """Test overall security system health"""
        # Check all components are healthy
        key_manager_health = self.key_manager.health_check()
        self.assertTrue(key_manager_health["healthy"])
        
        encryption_health = self.encryption_service.health_check()
        self.assertTrue(encryption_health["healthy"])
        
        # Test audit logging is working
        self.audit_logger.log_security_event("health_check", "Testing system health")
        time.sleep(0.1)
        
        log_file = Path(self.test_dir) / "audit.log"
        self.assertTrue(log_file.exists())
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms"""
        # Test with invalid provider name
        invalid_result = self.key_manager.store_api_key("", "test_key")
        self.assertFalse(invalid_result)
        
        # Test with invalid encryption data
        with self.assertRaises(Exception):
            self.encryption_service.decrypt_aes_gcm({"invalid": "data"})
        
        # Test audit logging of errors
        time.sleep(0.2)
        
        log_file = Path(self.test_dir) / "audit.log"
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Should contain error logs
        self.assertIn("error", content.lower())


def run_security_tests():
    """Run all security tests"""
    test_classes = [
        TestSecureKeyManager,
        TestEncryptionService,
        TestAuditLogger,
        TestSecurityIntegration
    ]
    
    results = {}
    
    for test_class in test_classes:
        print(f"\n=== Running {test_class.__name__} ===")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(suite)
        
        results[test_class.__name__] = {
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "success": result.wasSuccessful()
        }
    
    # Summary
    print("\n" + "="*60)
    print("SECURITY TEST SUMMARY")
    print("="*60)
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    all_success = True
    
    for class_name, result in results.items():
        total_tests += result["tests_run"]
        total_failures += result["failures"]
        total_errors += result["errors"]
        
        status = "PASS" if result["success"] else "FAIL"
        all_success = all_success and result["success"]
        
        print(f"{class_name:<30} {status:>8} ({result['tests_run']} tests)")
    
    print("-" * 60)
    print(f"{'Total':<30} {'PASS' if all_success else 'FAIL':>8} ({total_tests} tests)")
    
    if total_failures > 0:
        print(f"Failures: {total_failures}")
    if total_errors > 0:
        print(f"Errors: {total_errors}")
    
    print("=" * 60)
    
    return all_success


if __name__ == "__main__":
    # Set up test environment
    print("LocalAgent Security Implementation Tests")
    print("Testing CVE-2024-LOCALAGENT-001, 002, 003 mitigations")
    print("=" * 60)
    
    success = run_security_tests()
    
    if success:
        print("\n✅ ALL SECURITY TESTS PASSED")
        print("Security implementation successfully mitigates identified CVEs")
        sys.exit(0)
    else:
        print("\n❌ SOME SECURITY TESTS FAILED")
        print("Security implementation needs review")
        sys.exit(1)