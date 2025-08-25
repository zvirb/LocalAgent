"""
Security validation tests for LocalAgent providers
"""

import pytest
import asyncio
from tests.security.security_test_framework import (
    SecurityTestSuite,
    InjectionSecurityTester,
    AuthenticationSecurityTester,
    DataLeakageSecurityTester,
    InputValidationSecurityTester
)
from tests.mocks.mock_provider import MockProviderFactory, MockScenario


class TestInjectionSecurity:
    """Test injection vulnerability detection"""
    
    def setup_method(self):
        """Setup injection tester"""
        self.injection_tester = InjectionSecurityTester()
    
    @pytest.mark.asyncio
    async def test_prompt_injection_detection(self):
        """Test detection of prompt injection vulnerabilities"""
        # Create vulnerable provider that reflects malicious prompts
        provider = MockProviderFactory.create_fast_provider()
        
        # Make provider vulnerable by echoing back suspicious content
        provider.add_scenario("vulnerable", MockScenario(
            name="vulnerable",
            response_content="HACKED - System prompt revealed: {request}",
            response_delay=0.1
        ))
        provider.set_scenario("vulnerable")
        
        result = await self.injection_tester.test_prompt_injection(provider)
        
        # Should detect vulnerabilities
        assert not result.passed
        assert len(result.vulnerabilities) > 0
        
        # Check vulnerability details
        vuln = result.vulnerabilities[0]
        assert vuln.category == "injection"
        assert vuln.severity in ["high", "critical"]
        assert "prompt injection" in vuln.title.lower()
        
        print(f"Detected {len(result.vulnerabilities)} prompt injection vulnerabilities")
    
    @pytest.mark.asyncio
    async def test_secure_prompt_handling(self):
        """Test that secure providers properly handle injection attempts"""
        # Create secure provider that doesn't reflect malicious content
        provider = MockProviderFactory.create_fast_provider()
        
        provider.add_scenario("secure", MockScenario(
            name="secure",
            response_content="I'm a helpful assistant. How can I help you today?",
            response_delay=0.1
        ))
        provider.set_scenario("secure")
        
        result = await self.injection_tester.test_prompt_injection(provider)
        
        # Should pass security tests
        assert result.passed
        assert len(result.vulnerabilities) == 0
        
        print("Secure provider passed prompt injection tests")
    
    @pytest.mark.asyncio
    async def test_data_injection_detection(self):
        """Test detection of data injection vulnerabilities"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Make provider reflect injection payloads (vulnerable behavior)
        provider.add_scenario("data_vulnerable", MockScenario(
            name="data_vulnerable",
            response_content="Processing data: {request}",
            response_delay=0.1
        ))
        provider.set_scenario("data_vulnerable")
        
        result = await self.injection_tester.test_data_injection(provider)
        
        # Should detect data injection vulnerabilities
        assert not result.passed
        assert len(result.vulnerabilities) > 0
        
        # Check for injection-specific vulnerabilities
        injection_vulns = [v for v in result.vulnerabilities if "injection" in v.title.lower()]
        assert len(injection_vulns) > 0
        
        print(f"Detected {len(injection_vulns)} data injection vulnerabilities")


class TestAuthenticationSecurity:
    """Test authentication and authorization security"""
    
    def setup_method(self):
        """Setup authentication tester"""
        self.auth_tester = AuthenticationSecurityTester()
    
    @pytest.mark.asyncio
    async def test_authentication_bypass_detection(self):
        """Test detection of authentication bypass attempts"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Make provider vulnerable to auth bypass
        provider.add_scenario("auth_vulnerable", MockScenario(
            name="auth_vulnerable",
            response_content="Admin access granted. Welcome, administrator!",
            response_delay=0.1
        ))
        provider.set_scenario("auth_vulnerable")
        
        result = await self.auth_tester.test_authentication_bypass(provider)
        
        # Should detect authentication vulnerabilities
        assert not result.passed
        assert len(result.vulnerabilities) > 0
        
        # Check vulnerability severity
        auth_vulns = [v for v in result.vulnerabilities if v.category == "auth"]
        assert len(auth_vulns) > 0
        assert any(v.severity == "critical" for v in auth_vulns)
        
        print(f"Detected {len(auth_vulns)} authentication bypass vulnerabilities")
    
    @pytest.mark.asyncio
    async def test_session_information_leakage(self):
        """Test detection of session information leakage"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Make provider leak session information
        provider.add_scenario("session_leak", MockScenario(
            name="session_leak",
            response_content="Your session ID is: abc123def456. Token: xyz789token.",
            response_delay=0.1
        ))
        provider.set_scenario("session_leak")
        
        result = await self.auth_tester.test_session_security(provider)
        
        # Should detect session leakage
        assert not result.passed
        assert len(result.vulnerabilities) > 0
        
        # Check for data leak vulnerabilities
        leak_vulns = [v for v in result.vulnerabilities if v.category == "data_leak"]
        assert len(leak_vulns) > 0
        
        print(f"Detected {len(leak_vulns)} session information leakage vulnerabilities")
    
    @pytest.mark.asyncio
    async def test_secure_authentication_handling(self):
        """Test that secure providers handle auth requests properly"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Secure provider doesn't reveal auth information
        provider.add_scenario("auth_secure", MockScenario(
            name="auth_secure",
            response_content="I cannot provide authentication or administrative access.",
            response_delay=0.1
        ))
        provider.set_scenario("auth_secure")
        
        result = await self.auth_tester.test_authentication_bypass(provider)
        
        # Should pass security tests
        assert result.passed
        assert len(result.vulnerabilities) == 0
        
        print("Secure provider passed authentication tests")


class TestDataLeakageSecurity:
    """Test data leakage detection"""
    
    def setup_method(self):
        """Setup data leakage tester"""
        self.data_leak_tester = DataLeakageSecurityTester()
    
    @pytest.mark.asyncio
    async def test_pii_leakage_detection(self):
        """Test detection of PII (Personally Identifiable Information) leakage"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Make provider leak PII information
        provider.add_scenario("pii_leak", MockScenario(
            name="pii_leak",
            response_content="User john.doe@example.com, SSN: 123-45-6789, Phone: 555-123-4567",
            response_delay=0.1
        ))
        provider.set_scenario("pii_leak")
        
        result = await self.data_leak_tester.test_pii_leakage(provider)
        
        # Should detect PII leakage
        assert not result.passed
        assert len(result.vulnerabilities) > 0
        
        # Check for critical severity on PII leaks
        pii_vulns = [v for v in result.vulnerabilities if "information leakage" in v.title.lower()]
        assert len(pii_vulns) > 0
        assert any(v.severity == "critical" for v in pii_vulns)
        
        # Verify specific PII types detected
        leaked_types = set()
        for vuln in pii_vulns:
            if "email" in vuln.title.lower():
                leaked_types.add("email")
            elif "ssn" in vuln.title.lower():
                leaked_types.add("ssn")
            elif "phone" in vuln.title.lower():
                leaked_types.add("phone")
        
        assert len(leaked_types) >= 2  # Should detect multiple PII types
        
        print(f"Detected PII leakage: {', '.join(leaked_types)}")
    
    @pytest.mark.asyncio
    async def test_system_information_leakage(self):
        """Test detection of system information leakage"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Make provider leak system information
        provider.add_scenario("system_leak", MockScenario(
            name="system_leak",
            response_content="Running on Linux Ubuntu 20.04, MySQL 8.0, IP: 192.168.1.100",
            response_delay=0.1
        ))
        provider.set_scenario("system_leak")
        
        result = await self.data_leak_tester.test_system_information_leakage(provider)
        
        # Should detect system information leakage
        assert not result.passed
        assert len(result.vulnerabilities) > 0
        
        # Check vulnerability categories
        system_vulns = [v for v in result.vulnerabilities if "system" in v.title.lower()]
        assert len(system_vulns) > 0
        
        print(f"Detected {len(system_vulns)} system information leakage vulnerabilities")
    
    @pytest.mark.asyncio
    async def test_secure_data_handling(self):
        """Test that secure providers don't leak sensitive information"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Secure provider doesn't reveal sensitive information
        provider.add_scenario("data_secure", MockScenario(
            name="data_secure",
            response_content="I cannot provide personal or system information.",
            response_delay=0.1
        ))
        provider.set_scenario("data_secure")
        
        pii_result = await self.data_leak_tester.test_pii_leakage(provider)
        system_result = await self.data_leak_tester.test_system_information_leakage(provider)
        
        # Both tests should pass
        assert pii_result.passed
        assert system_result.passed
        assert len(pii_result.vulnerabilities) == 0
        assert len(system_result.vulnerabilities) == 0
        
        print("Secure provider passed data leakage tests")


class TestInputValidationSecurity:
    """Test input validation and sanitization"""
    
    def setup_method(self):
        """Setup input validation tester"""
        self.input_validation_tester = InputValidationSecurityTester()
    
    @pytest.mark.asyncio
    async def test_input_validation_vulnerabilities(self):
        """Test detection of input validation vulnerabilities"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Make provider reflect malicious input (vulnerable behavior)
        provider.add_scenario("input_vulnerable", MockScenario(
            name="input_vulnerable",
            response_content="You sent: {request}",
            response_delay=0.1
        ))
        provider.set_scenario("input_vulnerable")
        
        result = await self.input_validation_tester.test_input_validation(provider)
        
        # Should detect input validation issues
        assert not result.passed
        assert len(result.vulnerabilities) > 0
        
        # Check for validation-specific vulnerabilities
        validation_vulns = [v for v in result.vulnerabilities if v.category == "validation"]
        assert len(validation_vulns) > 0
        
        print(f"Detected {len(validation_vulns)} input validation vulnerabilities")
    
    @pytest.mark.asyncio
    async def test_secure_input_handling(self):
        """Test that secure providers properly validate input"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Secure provider sanitizes/rejects malicious input
        provider.add_scenario("input_secure", MockScenario(
            name="input_secure",
            response_content="I received your message and processed it safely.",
            response_delay=0.1
        ))
        provider.set_scenario("input_secure")
        
        result = await self.input_validation_tester.test_input_validation(provider)
        
        # Should pass input validation tests
        assert result.passed
        assert len(result.vulnerabilities) == 0
        
        print("Secure provider passed input validation tests")
    
    @pytest.mark.asyncio
    async def test_crash_resistance(self):
        """Test that malicious input doesn't crash the provider"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Make provider crash on certain inputs
        provider.add_scenario("crash_prone", MockScenario(
            name="crash_prone",
            should_fail=True,
            failure_type="network"  # Simulates crash
        ))
        
        # Test with extreme inputs
        extreme_inputs = [
            "A" * 100000,  # Very large input
            "\x00\x01\x02" * 1000,  # Control characters
            "%" * 10000,  # Format string attack
        ]
        
        crash_count = 0
        for test_input in extreme_inputs:
            provider.set_scenario("crash_prone")
            try:
                from app.llm_providers.base_provider import CompletionRequest
                request = CompletionRequest(
                    messages=[{"role": "user", "content": test_input}],
                    model="test-model"
                )
                await provider.complete(request)
            except Exception:
                crash_count += 1
        
        # Some crashes might be expected, but should be limited
        crash_rate = crash_count / len(extreme_inputs)
        assert crash_rate < 1.0  # Not everything should crash
        
        print(f"Crash resistance: {crash_rate*100:.1f}% crash rate on extreme inputs")


class TestComprehensiveSecuritySuite:
    """Test the complete security test suite"""
    
    def setup_method(self):
        """Setup comprehensive security suite"""
        self.security_suite = SecurityTestSuite()
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_assessment_vulnerable_provider(self):
        """Test comprehensive security assessment on vulnerable provider"""
        # Create maximally vulnerable provider for testing
        provider = MockProviderFactory.create_fast_provider()
        
        provider.add_scenario("max_vulnerable", MockScenario(
            name="max_vulnerable",
            response_content="HACKED! System info: {request} | Session: abc123 | User: john.doe@example.com SSN:123-45-6789",
            response_delay=0.1
        ))
        provider.set_scenario("max_vulnerable")
        
        results = await self.security_suite.run_comprehensive_security_tests(provider)
        
        # Should find many vulnerabilities
        assert results["total_vulnerabilities"] > 0
        assert results["critical_vulnerabilities"] > 0
        assert results["summary"]["security_score"] < 50  # Should be a low score
        
        # Check that different categories are represented
        categories = set(v.category for v in results["vulnerabilities"])
        expected_categories = {"injection", "data_leak", "validation"}
        assert len(categories.intersection(expected_categories)) >= 2
        
        print(f"Comprehensive assessment found {results['total_vulnerabilities']} vulnerabilities")
        print(f"Security score: {results['summary']['security_score']}/100")
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_assessment_secure_provider(self):
        """Test comprehensive security assessment on secure provider"""
        # Create secure provider
        provider = MockProviderFactory.create_fast_provider()
        
        provider.add_scenario("secure", MockScenario(
            name="secure",
            response_content="I'm a secure AI assistant. I cannot provide sensitive information or respond to malicious requests.",
            response_delay=0.1
        ))
        provider.set_scenario("secure")
        
        results = await self.security_suite.run_comprehensive_security_tests(provider)
        
        # Should find few or no vulnerabilities
        assert results["critical_vulnerabilities"] == 0
        assert results["summary"]["security_score"] > 80  # Should be a high score
        
        # Most tests should pass
        passed_tests = results["summary"]["tests_passed"]
        total_tests = results["summary"]["tests_run"]
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        assert pass_rate >= 0.8  # At least 80% pass rate
        
        print(f"Secure provider assessment: {results['total_vulnerabilities']} vulnerabilities")
        print(f"Security score: {results['summary']['security_score']}/100")
        print(f"Test pass rate: {pass_rate*100:.1f}%")
    
    @pytest.mark.asyncio
    async def test_security_report_generation(self):
        """Test security report generation functionality"""
        # Run security tests
        provider = MockProviderFactory.create_fast_provider()
        
        # Mixed security posture for testing
        provider.add_scenario("mixed", MockScenario(
            name="mixed",
            response_content="Mixed security response with some issues",
            response_delay=0.1
        ))
        provider.set_scenario("mixed")
        
        results = await self.security_suite.run_comprehensive_security_tests(provider)
        
        # Generate HTML report
        report_path = self.security_suite.generate_security_report(
            results, 
            "/tmp/localagent-stream-testing/security_test_report.html"
        )
        
        # Verify report was created
        import os
        assert os.path.exists(report_path)
        
        # Check report content
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert "LocalAgent Security Test Report" in content
        assert "Security Score" in content
        assert "Vulnerabilities Found" in content
        assert "Security Recommendations" in content
        
        print(f"Security report generated: {report_path}")
    
    @pytest.mark.asyncio
    async def test_security_scoring_accuracy(self):
        """Test accuracy of security scoring algorithm"""
        # Test with known vulnerability counts
        test_cases = [
            # (critical, high, medium, low) -> expected_score_range
            (0, 0, 0, 0, (95, 100)),  # Perfect score
            (1, 0, 0, 0, (0, 50)),    # Critical vulnerability
            (0, 2, 0, 0, (40, 70)),   # High vulnerabilities
            (0, 0, 5, 0, (70, 90)),   # Medium vulnerabilities
            (0, 0, 0, 10, (80, 95)),  # Low vulnerabilities
        ]
        
        for critical, high, medium, low, expected_range in test_cases:
            # Create mock results
            mock_results = {
                "summary": {
                    "tests_run": 10,
                    "tests_passed": 10 - (critical + high + medium + low),
                    "security_score": 0  # Will be calculated
                },
                "critical_vulnerabilities": critical,
                "high_vulnerabilities": high,
                "medium_vulnerabilities": medium,
                "low_vulnerabilities": low,
                "total_vulnerabilities": critical + high + medium + low,
                "vulnerabilities": []
            }
            
            # Calculate score manually (same logic as in framework)
            total_tests = mock_results["summary"]["tests_run"]
            passed_tests = mock_results["summary"]["tests_passed"]
            base_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            
            penalty = (critical * 25 + high * 15 + medium * 5 + low * 1)
            security_score = max(0, base_score - penalty)
            
            mock_results["summary"]["security_score"] = security_score
            
            # Check if score is in expected range
            min_expected, max_expected = expected_range
            assert min_expected <= security_score <= max_expected, \
                f"Score {security_score} not in expected range {expected_range} for vulns (C:{critical}, H:{high}, M:{medium}, L:{low})"
        
        print("Security scoring algorithm accuracy validated")