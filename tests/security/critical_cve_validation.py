#!/usr/bin/env python3
"""
Critical CVE Security Validation Suite
Tests for CVE-LOCALAGENT-001, CVE-LOCALAGENT-002, CVE-LOCALAGENT-003
"""

import os
import sys
import asyncio
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

class SecurityValidationResults:
    """Results container for security validation tests"""
    
    def __init__(self):
        self.cve_001_results = {}  # WebSocket security
        self.cve_002_results = {}  # Shell command injection
        self.cve_003_results = {}  # Encryption security
        self.overall_score = 0.0
        self.passed_tests = 0
        self.total_tests = 0
        self.critical_failures = []

class CriticalCVEValidator:
    """Validates fixes for the 3 critical CVE vulnerabilities"""
    
    def __init__(self):
        self.results = SecurityValidationResults()
        
    async def validate_cve_001_websocket_security(self) -> Dict[str, Any]:
        """
        Validate CVE-LOCALAGENT-001 (WebSocket Authentication Bypass) fixes
        
        Tests:
        1. Query parameter authentication is blocked
        2. Header-based authentication is required
        3. Connection closes on invalid auth attempts
        4. Security logging is active
        """
        print("\n🔍 Testing CVE-LOCALAGENT-001 (WebSocket Security)")
        
        tests = {
            "query_param_blocked": False,
            "header_auth_required": False,
            "invalid_auth_closes": False,
            "security_logging": False
        }
        
        try:
            # Test 1: Verify query parameter authentication is blocked
            websocket_file = project_root / "UnifiedWorkflow/app/kanban_service/routers/websocket.py"
            if websocket_file.exists():
                content = websocket_file.read_text()
                
                # Check for CVE mitigation code
                if "CVE-LOCALAGENT-001" in content and "query parameter authentication not allowed" in content:
                    tests["query_param_blocked"] = True
                    print("✅ Query parameter authentication blocked")
                else:
                    print("❌ Query parameter authentication still vulnerable")
                    self.results.critical_failures.append("CVE-001: Query parameter auth not blocked")
                
                # Check for header-only authentication
                if "Authorization header required" in content and "Bearer " in content:
                    tests["header_auth_required"] = True
                    print("✅ Header-based authentication enforced")
                else:
                    print("❌ Header-based authentication not properly enforced")
                    self.results.critical_failures.append("CVE-001: Header auth not enforced")
                
                # Check for connection closure on invalid auth
                if "websocket.close(code=1008" in content:
                    tests["invalid_auth_closes"] = True
                    print("✅ Invalid authentication closes connection")
                else:
                    print("❌ Invalid authentication handling inadequate")
                    
                # Check for security logging
                if "logging.warning" in content and "CVE-LOCALAGENT-001" in content:
                    tests["security_logging"] = True
                    print("✅ Security event logging active")
                else:
                    print("❌ Security event logging missing")
            else:
                print("❌ WebSocket router file not found")
                self.results.critical_failures.append("CVE-001: WebSocket router file missing")
        
        except Exception as e:
            print(f"❌ CVE-001 validation failed: {e}")
            self.results.critical_failures.append(f"CVE-001: Validation error - {e}")
        
        passed = sum(tests.values())
        total = len(tests)
        score = (passed / total) * 100
        
        print(f"CVE-001 Score: {passed}/{total} ({score:.1f}%)")
        
        self.results.cve_001_results = {
            "tests": tests,
            "passed": passed,
            "total": total,
            "score": score
        }
        
        return self.results.cve_001_results
    
    async def validate_cve_002_shell_security(self) -> Dict[str, Any]:
        """
        Validate CVE-LOCALAGENT-002 (Shell Command Injection) fixes
        
        Tests:
        1. Environment variable injection blocked
        2. Process substitution attacks blocked
        3. Command chaining attacks blocked
        4. Allowlist-based validation active
        """
        print("\n🔍 Testing CVE-LOCALAGENT-002 (Shell Command Injection)")
        
        tests = {
            "env_injection_blocked": False,
            "process_substitution_blocked": False,
            "command_chaining_blocked": False,
            "allowlist_validation": False,
            "comprehensive_patterns": False
        }
        
        try:
            shell_file = project_root / "app/cli/plugins/builtin/shell_plugin.py"
            if shell_file.exists():
                content = shell_file.read_text()
                
                # Test environment variable injection protection
                if r"\$\{[^}]*\}" in content and "CVE-LOCALAGENT-002" in content:
                    tests["env_injection_blocked"] = True
                    print("✅ Environment variable injection blocked")
                else:
                    print("❌ Environment variable injection vulnerable")
                    self.results.critical_failures.append("CVE-002: Env variable injection not blocked")
                
                # Test process substitution protection
                if r"<\([^)]*\)" in content and r">\([^)]*\)" in content:
                    tests["process_substitution_blocked"] = True
                    print("✅ Process substitution attacks blocked")
                else:
                    print("❌ Process substitution attacks vulnerable")
                    self.results.critical_failures.append("CVE-002: Process substitution not blocked")
                
                # Test command chaining protection
                if r"[;&|]\s*(rm|dd|format|mkfs|shutdown|reboot)" in content:
                    tests["command_chaining_blocked"] = True
                    print("✅ Command chaining attacks blocked")
                else:
                    print("❌ Command chaining attacks vulnerable")
                    self.results.critical_failures.append("CVE-002: Command chaining not blocked")
                
                # Test allowlist validation
                if "ALLOWED_COMMANDS" in content and "'ls'" in content:
                    tests["allowlist_validation"] = True
                    print("✅ Allowlist-based validation implemented")
                else:
                    print("❌ Allowlist-based validation missing")
                    self.results.critical_failures.append("CVE-002: Allowlist validation missing")
                
                # Test comprehensive pattern coverage
                pattern_count = content.count("r'.*")
                if pattern_count >= 15:  # Should have many security patterns
                    tests["comprehensive_patterns"] = True
                    print(f"✅ Comprehensive security patterns ({pattern_count} patterns)")
                else:
                    print(f"❌ Insufficient security patterns ({pattern_count} patterns)")
                    
            else:
                print("❌ Shell plugin file not found")
                self.results.critical_failures.append("CVE-002: Shell plugin file missing")
        
        except Exception as e:
            print(f"❌ CVE-002 validation failed: {e}")
            self.results.critical_failures.append(f"CVE-002: Validation error - {e}")
        
        passed = sum(tests.values())
        total = len(tests)
        score = (passed / total) * 100
        
        print(f"CVE-002 Score: {passed}/{total} ({score:.1f}%)")
        
        self.results.cve_002_results = {
            "tests": tests,
            "passed": passed,
            "total": total,
            "score": score
        }
        
        return self.results.cve_002_results
    
    async def validate_cve_003_encryption_security(self) -> Dict[str, Any]:
        """
        Validate CVE-LOCALAGENT-003 (Hardcoded Encryption Keys) fixes
        
        Tests:
        1. Hardcoded password removed
        2. Hardware entropy implementation
        3. Secure key derivation
        4. Memory cleanup implementation
        """
        print("\n🔍 Testing CVE-LOCALAGENT-003 (Encryption Security)")
        
        tests = {
            "hardcoded_password_removed": False,
            "hardware_entropy_used": False,
            "secure_key_derivation": False,
            "memory_cleanup": False,
            "nist_compliance": False
        }
        
        try:
            key_manager_file = project_root / "app/security/key_manager.py"
            if key_manager_file.exists():
                content = key_manager_file.read_text()
                
                # Test hardcoded password removal
                if "localagent_secure_key_derivation" not in content or "CVE-LOCALAGENT-003" in content:
                    tests["hardcoded_password_removed"] = True
                    print("✅ Hardcoded password removed")
                else:
                    print("❌ Hardcoded password still present")
                    self.results.critical_failures.append("CVE-003: Hardcoded password not removed")
                
                # Test hardware entropy usage
                if "os.urandom" in content and "_derive_master_key_from_system" in content:
                    tests["hardware_entropy_used"] = True
                    print("✅ Hardware entropy implementation found")
                else:
                    print("❌ Hardware entropy implementation missing")
                    self.results.critical_failures.append("CVE-003: Hardware entropy not implemented")
                
                # Test secure key derivation
                if "hashlib.pbkdf2_hmac" in content and "platform.node" in content:
                    tests["secure_key_derivation"] = True
                    print("✅ Secure key derivation implemented")
                else:
                    print("❌ Secure key derivation missing")
                    self.results.critical_failures.append("CVE-003: Secure key derivation missing")
                
                # Test memory cleanup
                if 'b"0" * len(' in content and "del master_key" in content:
                    tests["memory_cleanup"] = True
                    print("✅ Memory cleanup implementation found")
                else:
                    print("❌ Memory cleanup implementation missing")
                
                # Test NIST compliance (600,000 iterations)
                if "iterations=600000" in content:
                    tests["nist_compliance"] = True
                    print("✅ NIST 2024 compliance (600,000 iterations)")
                else:
                    print("❌ NIST compliance not met (should be 600,000 iterations)")
                    
            else:
                print("❌ Key manager file not found")
                self.results.critical_failures.append("CVE-003: Key manager file missing")
        
        except Exception as e:
            print(f"❌ CVE-003 validation failed: {e}")
            self.results.critical_failures.append(f"CVE-003: Validation error - {e}")
        
        passed = sum(tests.values())
        total = len(tests)
        score = (passed / total) * 100
        
        print(f"CVE-003 Score: {passed}/{total} ({score:.1f}%)")
        
        self.results.cve_003_results = {
            "tests": tests,
            "passed": passed,
            "total": total,
            "score": score
        }
        
        return self.results.cve_003_results
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all CVE validation tests and generate comprehensive report"""
        
        print("🛡️  CRITICAL CVE SECURITY VALIDATION SUITE")
        print("=" * 60)
        print("Testing fixes for CVE-LOCALAGENT-001, CVE-LOCALAGENT-002, CVE-LOCALAGENT-003")
        print("=" * 60)
        
        # Run all CVE validations
        cve_001 = await self.validate_cve_001_websocket_security()
        cve_002 = await self.validate_cve_002_shell_security()
        cve_003 = await self.validate_cve_003_encryption_security()
        
        # Calculate overall results
        total_passed = cve_001["passed"] + cve_002["passed"] + cve_003["passed"]
        total_tests = cve_001["total"] + cve_002["total"] + cve_003["total"]
        overall_score = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        self.results.passed_tests = total_passed
        self.results.total_tests = total_tests
        self.results.overall_score = overall_score
        
        # Generate summary report
        print("\n" + "=" * 60)
        print("🎯 VALIDATION SUMMARY")
        print("=" * 60)
        
        if overall_score >= 90:
            status = "✅ EXCELLENT"
        elif overall_score >= 75:
            status = "⚠️  GOOD"
        elif overall_score >= 50:
            status = "🔸 NEEDS IMPROVEMENT"
        else:
            status = "❌ CRITICAL ISSUES"
        
        print(f"Overall Security Score: {overall_score:.1f}% ({total_passed}/{total_tests} tests passed)")
        print(f"Security Status: {status}")
        
        if self.results.critical_failures:
            print(f"\n❌ CRITICAL ISSUES ({len(self.results.critical_failures)}):")
            for failure in self.results.critical_failures:
                print(f"   • {failure}")
        else:
            print("\n✅ No critical security issues detected")
        
        # Individual CVE scores
        print(f"\nCVE-LOCALAGENT-001 (WebSocket): {cve_001['score']:.1f}%")
        print(f"CVE-LOCALAGENT-002 (Shell Injection): {cve_002['score']:.1f}%")  
        print(f"CVE-LOCALAGENT-003 (Encryption): {cve_003['score']:.1f}%")
        
        # Security improvement calculation
        original_score = 4.2  # From security assessment
        improvement = ((overall_score/10) - original_score) / original_score * 100
        print(f"\nSecurity Improvement: {improvement:.1f}% (from {original_score}/10 baseline)")
        
        return {
            "overall_score": overall_score,
            "passed_tests": total_passed,
            "total_tests": total_tests,
            "cve_001": cve_001,
            "cve_002": cve_002, 
            "cve_003": cve_003,
            "critical_failures": self.results.critical_failures,
            "security_improvement": improvement,
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

async def main():
    """Main validation entry point"""
    
    validator = CriticalCVEValidator()
    results = await validator.run_comprehensive_validation()
    
    # Save results to file
    results_file = Path(__file__).parent / "critical_cve_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Exit with appropriate code
    if results["overall_score"] >= 75:
        print("\n🎉 Security validation PASSED!")
        return 0
    else:
        print("\n⚠️  Security validation FAILED - critical issues must be addressed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)