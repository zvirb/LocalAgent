#!/usr/bin/env python3
"""
Security Validation Script - Tests all security fixes
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append('/home/marku/Documents/programming/LocalProgramming')

def test_secure_key_manager():
    """Test SecureKeyManager functionality"""
    try:
        from app.security.key_manager import SecureKeyManager
        
        print("Testing SecureKeyManager...")
        key_manager = SecureKeyManager("test_service")
        
        # Test health check
        health = key_manager.health_check()
        print(f"  Health check: {'✓' if health.get('healthy') else '✗'}")
        
        # Test key storage and retrieval
        test_key = "test_api_key_12345"
        stored = key_manager.store_api_key("test_provider", test_key)
        print(f"  Key storage: {'✓' if stored else '✗'}")
        
        retrieved = key_manager.retrieve_api_key("test_provider")
        print(f"  Key retrieval: {'✓' if retrieved == test_key else '✗'}")
        
        # Cleanup
        key_manager.delete_api_key("test_provider")
        
        return True
        
    except Exception as e:
        print(f"  SecureKeyManager test failed: {e}")
        return False

def test_encryption_service():
    """Test EncryptionService functionality"""
    try:
        from app.security.encryption import EncryptionService
        
        print("Testing EncryptionService...")
        enc_service = EncryptionService("test_password")
        
        # Test health check
        health = enc_service.health_check()
        print(f"  Health check: {'✓' if health.get('healthy') else '✗'}")
        
        # Test AES-GCM encryption
        test_data = "sensitive_test_data_12345"
        encrypted = enc_service.encrypt_aes_gcm(test_data, "test_purpose")
        print(f"  AES-GCM encryption: {'✓' if encrypted else '✗'}")
        
        decrypted = enc_service.decrypt_aes_gcm(encrypted).decode()
        print(f"  AES-GCM decryption: {'✓' if decrypted == test_data else '✗'}")
        
        return True
        
    except Exception as e:
        print(f"  EncryptionService test failed: {e}")
        return False

def test_input_validation():
    """Test input validation framework"""
    try:
        # Load validation framework from security stream
        sys.path.append('/tmp/security-stream')
        from input_validation_framework import InputValidator, ValidationLevel
        
        print("Testing Input Validation...")
        validator = InputValidator(ValidationLevel.NORMAL)
        
        # Test API key validation
        result = validator.validate("sk-test123456789012345678901234567890123456789", ["api_key"], "test_api_key")
        print(f"  API key validation: {'✓' if result['valid'] else '✗'}")
        
        # Test XSS prevention
        result = validator.validate("<script>alert('xss')</script>", ["xss_safe"], "user_input")
        print(f"  XSS prevention: {'✓' if not result['valid'] else '✗'}")
        
        # Test SQL injection prevention
        result = validator.validate("'; DROP TABLE users; --", ["sql_safe"], "user_input")
        print(f"  SQL injection prevention: {'✓' if not result['valid'] else '✗'}")
        
        return True
        
    except Exception as e:
        print(f"  Input validation test failed: {e}")
        return False

def test_config_permissions():
    """Test configuration file permissions"""
    try:
        print("Testing Configuration File Permissions...")
        
        # Check permissions of sensitive files
        sensitive_files = [
            "/home/marku/Documents/programming/LocalProgramming/UnifiedWorkflow/k8s/kanban-service/secrets.yaml"
        ]
        
        permissions_secure = True
        for file_path in sensitive_files:
            if Path(file_path).exists():
                perms = Path(file_path).stat().st_mode & 0o777
                expected = 0o600  # Owner read/write only
                
                if perms != expected:
                    permissions_secure = False
                    print(f"  {file_path}: {'✗'} (permissions: {oct(perms)}, expected: {oct(expected)})")
                else:
                    print(f"  {file_path}: {'✓'} (permissions: {oct(perms)})")
        
        return permissions_secure
        
    except Exception as e:
        print(f"  Configuration permissions test failed: {e}")
        return False

def main():
    """Run all security validation tests"""
    print("=== SECURITY VALIDATION TESTS ===\n")
    
    tests = [
        ("SecureKeyManager", test_secure_key_manager),
        ("EncryptionService", test_encryption_service),
        ("Input Validation", test_input_validation),
        ("Config Permissions", test_config_permissions),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} - PASSED\n")
            else:
                print(f"✗ {test_name} - FAILED\n")
        except Exception as e:
            print(f"✗ {test_name} - ERROR: {e}\n")
    
    print(f"=== RESULTS ===")
    print(f"Tests passed: {passed}/{total}")
    print(f"Overall status: {'✓ ALL TESTS PASSED' if passed == total else '⚠ SOME TESTS FAILED'}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
