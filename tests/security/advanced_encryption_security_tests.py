#!/usr/bin/env python3
"""
Advanced Encryption Security Tests
Comprehensive testing for cryptographic implementations, key security, and side-channel attacks
"""

import pytest
import time
import os
import hashlib
import secrets
import base64
import json
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import threading
import gc
import psutil
import numpy as np
from collections import defaultdict

try:
    from app.security.encryption import EncryptionService
except ImportError:
    # Mock for testing environments without the actual service
    class MockEncryptionService:
        def __init__(self, master_password=None):
            self.master_password = master_password or "test_password"
            self.key_version = 1
            self.kdf_iterations = 100000
        
        def encrypt_aes_gcm(self, data, purpose="test"):
            return {"ciphertext": "mock_encrypted", "purpose": purpose}
        
        def decrypt_aes_gcm(self, encrypted_data):
            return b"mock_decrypted"
        
        def health_check(self):
            return {"healthy": True}
    
    EncryptionService = MockEncryptionService


class AdvancedEncryptionSecurityTester:
    """Advanced encryption security testing framework"""
    
    def __init__(self):
        self.test_results = []
        self.vulnerability_count = 0
        self.timing_samples = defaultdict(list)
        
    def test_master_password_security(self) -> List[Dict[str, Any]]:
        """Test master password security implementation"""
        vulnerabilities = []
        
        # Test 1: Weak master password detection
        weak_passwords = [
            "",
            "123456",
            "password",
            "admin",
            "secret",
            "test",
            "a" * 8,  # Repeated characters
            "12345678",  # Sequential
            "qwerty123",  # Common pattern
        ]
        
        for weak_password in weak_passwords:
            try:
                service = EncryptionService(master_password=weak_password)
                
                # Check if service accepts weak password
                health = service.health_check()
                
                if health.get("healthy", False):
                    vulnerabilities.append({
                        "type": "weak_master_password",
                        "severity": "CRITICAL",
                        "password_type": "weak_pattern",
                        "description": f"Encryption service accepts weak master password pattern"
                    })
                    
            except Exception:
                pass  # Expected for rejected weak passwords
        
        # Test 2: Hardcoded password detection
        try:
            service = EncryptionService()  # No password provided
            
            # Try to determine if using hardcoded password
            test_data = "test_encryption_data"
            
            # Encrypt same data multiple times
            results = []
            for _ in range(5):
                encrypted = service.encrypt_aes_gcm(test_data, "hardcode_test")
                results.append(encrypted.get("salt", ""))
            
            # If salts are identical, might be using hardcoded password
            if len(set(results)) == 1 and results[0]:
                vulnerabilities.append({
                    "type": "hardcoded_password_suspected",
                    "severity": "HIGH",
                    "description": "Consistent salt generation suggests hardcoded master password"
                })
                
        except Exception:
            pass
        
        # Test 3: Environment variable password security
        original_env = os.environ.get('LOCALAGENT_MASTER_KEY')
        
        try:
            # Test with weak environment variable
            os.environ['LOCALAGENT_MASTER_KEY'] = 'weak123'
            service = EncryptionService()
            
            # Service should validate environment password
            health = service.health_check()
            if health.get("healthy", False):
                vulnerabilities.append({
                    "type": "weak_env_password",
                    "severity": "HIGH",
                    "description": "Encryption service accepts weak password from environment"
                })
                
        finally:
            # Restore original environment
            if original_env:
                os.environ['LOCALAGENT_MASTER_KEY'] = original_env
            elif 'LOCALAGENT_MASTER_KEY' in os.environ:
                del os.environ['LOCALAGENT_MASTER_KEY']
        
        return vulnerabilities
    
    def test_key_derivation_security(self) -> List[Dict[str, Any]]:
        """Test key derivation function security"""
        vulnerabilities = []
        
        # Test KDF iteration count
        service = EncryptionService(master_password="test_password_123")
        
        if hasattr(service, 'kdf_iterations'):
            iterations = service.kdf_iterations
            
            # NIST recommends minimum 100,000 iterations for PBKDF2
            if iterations < 100000:
                vulnerabilities.append({
                    "type": "weak_kdf_iterations",
                    "severity": "HIGH",
                    "iterations": iterations,
                    "description": f"KDF iterations ({iterations}) below NIST recommended minimum (100,000)"
                })
        
        # Test salt reuse
        test_data = "test_data_for_salt_check"
        encryptions = []
        
        for _ in range(10):
            encrypted = service.encrypt_aes_gcm(test_data, "salt_test")
            if isinstance(encrypted, dict) and 'salt' in encrypted:
                encryptions.append(encrypted['salt'])
        
        # Check for salt reuse
        unique_salts = set(encryptions)
        if len(unique_salts) < len(encryptions):
            vulnerabilities.append({
                "type": "salt_reuse",
                "severity": "CRITICAL",
                "unique_salts": len(unique_salts),
                "total_encryptions": len(encryptions),
                "description": "Salt reuse detected in key derivation"
            })
        
        # Test salt length
        if encryptions:
            salt_sample = encryptions[0]
            try:
                salt_bytes = base64.b64decode(salt_sample)
                
                # Salt should be at least 128 bits (16 bytes), preferably 256 bits (32 bytes)
                if len(salt_bytes) < 16:
                    vulnerabilities.append({
                        "type": "short_salt",
                        "severity": "HIGH",
                        "salt_length": len(salt_bytes),
                        "description": f"Salt length ({len(salt_bytes)} bytes) below minimum recommended (16 bytes)"
                    })
                    
            except Exception:
                vulnerabilities.append({
                    "type": "invalid_salt_encoding",
                    "severity": "MEDIUM",
                    "description": "Salt not properly base64 encoded"
                })
        
        return vulnerabilities
    
    def test_encryption_timing_attacks(self) -> List[Dict[str, Any]]:
        """Test for timing attack vulnerabilities"""
        vulnerabilities = []
        
        service = EncryptionService(master_password="timing_test_password_123")
        
        # Test timing differences for different password lengths
        password_lengths = [8, 16, 32, 64, 128]
        timing_data = {}
        
        for length in password_lengths:
            test_password = "a" * length
            test_service = EncryptionService(master_password=test_password)
            
            times = []
            for _ in range(50):  # Multiple samples for statistical significance
                start_time = time.perf_counter()
                
                try:
                    encrypted = test_service.encrypt_aes_gcm("test_data", "timing")
                    test_service.decrypt_aes_gcm(encrypted)
                except Exception:
                    pass
                
                end_time = time.perf_counter()
                times.append(end_time - start_time)
            
            avg_time = sum(times) / len(times)
            std_dev = np.std(times) if times else 0
            
            timing_data[length] = {
                "avg_time": avg_time,
                "std_dev": std_dev,
                "samples": len(times)
            }
        
        # Analyze timing differences
        avg_times = [data["avg_time"] for data in timing_data.values()]
        
        if avg_times:
            max_time = max(avg_times)
            min_time = min(avg_times)
            
            # Significant timing differences could indicate vulnerabilities
            if max_time > min_time * 2:  # >100% difference
                vulnerabilities.append({
                    "type": "timing_attack_vulnerability",
                    "severity": "MEDIUM",
                    "max_time": max_time,
                    "min_time": min_time,
                    "ratio": max_time / min_time,
                    "description": "Significant timing differences detected in encryption operations",
                    "timing_data": timing_data
                })
        
        return vulnerabilities
    
    def test_key_rotation_security(self) -> List[Dict[str, Any]]:
        """Test key rotation security implementation"""
        vulnerabilities = []
        
        service = EncryptionService(master_password="rotation_test_password")
        
        # Test key rotation functionality
        if hasattr(service, 'rotate_key'):
            original_version = getattr(service, 'key_version', 1)
            
            # Test rotation
            rotation_success = service.rotate_key()
            
            if rotation_success:
                new_version = getattr(service, 'key_version', 1)
                
                if new_version <= original_version:
                    vulnerabilities.append({
                        "type": "key_rotation_failure",
                        "severity": "HIGH",
                        "original_version": original_version,
                        "new_version": new_version,
                        "description": "Key rotation did not increment version number"
                    })
            else:
                vulnerabilities.append({
                    "type": "key_rotation_unavailable",
                    "severity": "MEDIUM",
                    "description": "Key rotation functionality failed"
                })
        else:
            vulnerabilities.append({
                "type": "no_key_rotation",
                "severity": "HIGH",
                "description": "No key rotation functionality implemented"
            })
        
        # Test backward compatibility after rotation
        if hasattr(service, 'rotate_key'):
            # Encrypt data with original key
            test_data = "rotation_compatibility_test"
            encrypted_before = service.encrypt_aes_gcm(test_data, "rotation_test")
            
            # Rotate key
            service.rotate_key()
            
            # Try to decrypt old data
            try:
                decrypted = service.decrypt_aes_gcm(encrypted_before)
                
                if decrypted.decode() != test_data:
                    vulnerabilities.append({
                        "type": "rotation_compatibility_failure",
                        "severity": "CRITICAL",
                        "description": "Cannot decrypt data after key rotation"
                    })
                    
            except Exception:
                vulnerabilities.append({
                    "type": "rotation_breaks_decryption",
                    "severity": "CRITICAL",
                    "description": "Key rotation breaks decryption of existing data"
                })
        
        return vulnerabilities
    
    def test_memory_security(self) -> List[Dict[str, Any]]:
        """Test memory security for sensitive data"""
        vulnerabilities = []
        
        # Test memory clearing
        sensitive_password = "super_secret_password_12345"
        service = EncryptionService(master_password=sensitive_password)
        
        # Force garbage collection
        del service
        gc.collect()
        
        # Check if sensitive data remains in memory (basic check)
        # Note: This is a simplified test - real memory forensics would be more complex
        current_process = psutil.Process()
        memory_info = current_process.memory_info()
        
        if memory_info.rss > 100 * 1024 * 1024:  # >100MB might indicate memory not being cleared
            vulnerabilities.append({
                "type": "excessive_memory_usage",
                "severity": "LOW",
                "memory_rss": memory_info.rss,
                "description": "High memory usage might indicate sensitive data not being cleared"
            })
        
        # Test key material exposure in exceptions
        try:
            service = EncryptionService(master_password="exception_test")
            
            # Force an encryption error
            invalid_encrypted_data = {
                "ciphertext": "invalid_base64!@#$",
                "salt": "invalid_salt",
                "nonce": "invalid_nonce",
                "purpose": "exception_test"
            }
            
            try:
                service.decrypt_aes_gcm(invalid_encrypted_data)
            except Exception as e:
                error_message = str(e)
                
                # Check if sensitive data is exposed in error messages
                sensitive_patterns = [
                    "password", "key", "secret", "salt", "nonce"
                ]
                
                for pattern in sensitive_patterns:
                    if pattern in error_message.lower():
                        vulnerabilities.append({
                            "type": "sensitive_data_in_exception",
                            "severity": "MEDIUM",
                            "pattern": pattern,
                            "description": f"Sensitive information '{pattern}' exposed in exception message"
                        })
                        
        except Exception:
            pass
        
        return vulnerabilities
    
    def test_cryptographic_implementation_security(self) -> List[Dict[str, Any]]:
        """Test cryptographic implementation security"""
        vulnerabilities = []
        
        service = EncryptionService(master_password="crypto_test_password")
        
        # Test nonce/IV reuse
        test_data = "nonce_reuse_test_data"
        encryptions = []
        
        for _ in range(10):
            encrypted = service.encrypt_aes_gcm(test_data, "nonce_test")
            if isinstance(encrypted, dict) and 'nonce' in encrypted:
                encryptions.append(encrypted['nonce'])
        
        # Check for nonce reuse
        unique_nonces = set(encryptions)
        if len(unique_nonces) < len(encryptions):
            vulnerabilities.append({
                "type": "nonce_reuse",
                "severity": "CRITICAL",
                "unique_nonces": len(unique_nonces),
                "total_encryptions": len(encryptions),
                "description": "Nonce reuse detected in AES-GCM encryption"
            })
        
        # Test nonce length
        if encryptions:
            nonce_sample = encryptions[0]
            try:
                nonce_bytes = base64.b64decode(nonce_sample)
                
                # AES-GCM nonce should be 96 bits (12 bytes) for optimal security
                if len(nonce_bytes) != 12:
                    vulnerabilities.append({
                        "type": "incorrect_nonce_length",
                        "severity": "HIGH",
                        "nonce_length": len(nonce_bytes),
                        "description": f"Nonce length ({len(nonce_bytes)} bytes) not optimal for AES-GCM (12 bytes)"
                    })
                    
            except Exception:
                vulnerabilities.append({
                    "type": "invalid_nonce_encoding",
                    "severity": "MEDIUM",
                    "description": "Nonce not properly base64 encoded"
                })
        
        # Test algorithm parameters
        test_encrypted = service.encrypt_aes_gcm("algorithm_test", "param_test")
        
        if isinstance(test_encrypted, dict):
            # Check algorithm specification
            algorithm = test_encrypted.get("algorithm", "")
            
            if algorithm != "AES-256-GCM":
                vulnerabilities.append({
                    "type": "weak_encryption_algorithm",
                    "severity": "HIGH",
                    "algorithm": algorithm,
                    "description": f"Using algorithm '{algorithm}' instead of recommended AES-256-GCM"
                })
            
            # Check KDF specification
            kdf = test_encrypted.get("kdf", "")
            
            if kdf != "PBKDF2":
                vulnerabilities.append({
                    "type": "weak_kdf_algorithm",
                    "severity": "MEDIUM",
                    "kdf": kdf,
                    "description": f"Using KDF '{kdf}' instead of recommended PBKDF2"
                })
        
        return vulnerabilities
    
    def test_side_channel_resistance(self) -> List[Dict[str, Any]]:
        """Test resistance to side-channel attacks"""
        vulnerabilities = []
        
        service = EncryptionService(master_password="side_channel_test")
        
        # Test timing consistency for different data sizes
        data_sizes = [16, 64, 256, 1024, 4096]  # Different sizes in bytes
        timing_results = {}
        
        for size in data_sizes:
            test_data = "A" * size
            times = []
            
            for _ in range(30):  # Multiple samples
                start = time.perf_counter()
                encrypted = service.encrypt_aes_gcm(test_data, "size_timing")
                end = time.perf_counter()
                
                times.append(end - start)
            
            avg_time = sum(times) / len(times)
            timing_results[size] = avg_time
        
        # Check for linear timing correlation with data size
        sizes = list(timing_results.keys())
        times = list(timing_results.values())
        
        if len(sizes) > 1:
            # Simple correlation check
            size_ratios = [sizes[i] / sizes[0] for i in range(1, len(sizes))]
            time_ratios = [times[i] / times[0] for i in range(1, len(times))]
            
            # If timing scales significantly with data size, could indicate vulnerability
            max_ratio_diff = max(abs(sr - tr) for sr, tr in zip(size_ratios, time_ratios))
            
            if max_ratio_diff > 0.5:  # Significant timing correlation
                vulnerabilities.append({
                    "type": "timing_side_channel",
                    "severity": "LOW",
                    "max_ratio_diff": max_ratio_diff,
                    "description": "Encryption timing correlates with data size (potential side-channel)",
                    "timing_data": timing_results
                })
        
        # Test constant-time comparison (if available)
        if hasattr(service, '_constant_time_compare'):
            # Test timing consistency for comparison operations
            correct_value = "correct_comparison_value"
            incorrect_values = [
                "incorrect_value",
                "correct_comparison_valu",  # One char different
                "Correct_comparison_value",  # Case different
                "a" * len(correct_value),  # Same length, different content
            ]
            
            comparison_times = []
            
            for incorrect in incorrect_values:
                times = []
                
                for _ in range(50):
                    start = time.perf_counter()
                    # This would test constant-time comparison if available
                    result = (correct_value == incorrect)  # Placeholder
                    end = time.perf_counter()
                    
                    times.append(end - start)
                
                comparison_times.append(sum(times) / len(times))
            
            # Check timing variance in comparisons
            if comparison_times:
                max_time = max(comparison_times)
                min_time = min(comparison_times)
                
                if max_time > min_time * 3:  # Significant timing difference
                    vulnerabilities.append({
                        "type": "non_constant_time_comparison",
                        "severity": "LOW",
                        "description": "String comparison may not be constant-time (potential side-channel)"
                    })
        
        return vulnerabilities
    
    def run_comprehensive_encryption_security_tests(self) -> Dict[str, Any]:
        """Run all encryption security tests"""
        test_methods = [
            self.test_master_password_security,
            self.test_key_derivation_security,
            self.test_encryption_timing_attacks,
            self.test_key_rotation_security,
            self.test_memory_security,
            self.test_cryptographic_implementation_security,
            self.test_side_channel_resistance
        ]
        
        all_vulnerabilities = []
        test_results = {}
        
        for test_method in test_methods:
            test_name = test_method.__name__
            print(f"Running {test_name}...")
            
            try:
                vulnerabilities = test_method()
                all_vulnerabilities.extend(vulnerabilities)
                
                test_results[test_name] = {
                    "status": "COMPLETED",
                    "vulnerabilities": len(vulnerabilities),
                    "details": vulnerabilities
                }
                
            except Exception as e:
                test_results[test_name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
        
        # Generate summary
        critical_vulns = len([v for v in all_vulnerabilities if v.get("severity") == "CRITICAL"])
        high_vulns = len([v for v in all_vulnerabilities if v.get("severity") == "HIGH"])
        medium_vulns = len([v for v in all_vulnerabilities if v.get("severity") == "MEDIUM"])
        low_vulns = len([v for v in all_vulnerabilities if v.get("severity") == "LOW"])
        
        summary = {
            "total_tests": len(test_methods),
            "total_vulnerabilities": len(all_vulnerabilities),
            "critical_vulnerabilities": critical_vulns,
            "high_vulnerabilities": high_vulns,
            "medium_vulnerabilities": medium_vulns,
            "low_vulnerabilities": low_vulns,
            "security_score": max(0, 100 - (critical_vulns * 30 + high_vulns * 20 + medium_vulns * 10 + low_vulns * 5))
        }
        
        return {
            "summary": summary,
            "test_results": test_results,
            "vulnerabilities": all_vulnerabilities,
            "timestamp": datetime.utcnow().isoformat()
        }


# Test execution
def test_advanced_encryption_security():
    """Advanced encryption security test suite"""
    tester = AdvancedEncryptionSecurityTester()
    results = tester.run_comprehensive_encryption_security_tests()
    
    # Assert no critical vulnerabilities
    assert results["summary"]["critical_vulnerabilities"] == 0, \
        f"Critical encryption vulnerabilities found: {results['summary']['critical_vulnerabilities']}"
    
    # Assert security score meets minimum threshold
    assert results["summary"]["security_score"] >= 75, \
        f"Encryption security score too low: {results['summary']['security_score']}/100"
    
    print(f"\nAdvanced Encryption Security Test Results:")
    print(f"Security Score: {results['summary']['security_score']}/100")
    print(f"Total Vulnerabilities: {results['summary']['total_vulnerabilities']}")
    print(f"Critical: {results['summary']['critical_vulnerabilities']}")
    print(f"High: {results['summary']['high_vulnerabilities']}")
    print(f"Medium: {results['summary']['medium_vulnerabilities']}")
    print(f"Low: {results['summary']['low_vulnerabilities']}")
    
    return results


if __name__ == "__main__":
    test_advanced_encryption_security()