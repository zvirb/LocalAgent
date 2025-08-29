#!/usr/bin/env python3
"""
Penetration Testing Automation Framework
Automated security testing pipeline with OWASP ZAP integration and continuous testing
"""

import pytest
import asyncio
import subprocess
import json
import time
import requests
import threading
import socket
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PenetrationTestingFramework:
    """Automated penetration testing framework"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.results = []
        self.test_session_id = f"pentest_{int(time.time())}"
        self.report_dir = Path(f"/tmp/pentest_reports/{self.test_session_id}")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # OWASP ZAP configuration
        self.zap_config = {
            "proxy_port": 8080,
            "api_port": 8081,
            "enabled": self.config.get("enable_zap", True)
        }
        
    def _default_config(self) -> Dict[str, Any]:
        """Default penetration testing configuration"""
        return {
            "target_urls": [
                "http://localhost:8000",
                "http://localhost:8005",
                "ws://localhost:8005"
            ],
            "test_categories": [
                "injection",
                "authentication", 
                "authorization",
                "sensitive_data",
                "xml_external_entities",
                "broken_access_control",
                "security_misconfiguration",
                "xss",
                "insecure_deserialization",
                "vulnerable_components",
                "insufficient_logging"
            ],
            "intensity_level": "medium",  # low, medium, high
            "max_test_duration": 1800,  # 30 minutes
            "enable_active_scans": True,
            "enable_passive_scans": True,
            "enable_zap": True,
            "parallel_tests": True
        }
    
    async def initialize_zap_proxy(self) -> bool:
        """Initialize OWASP ZAP proxy for automated scanning"""
        if not self.zap_config["enabled"]:
            logger.info("OWASP ZAP disabled in configuration")
            return False
            
        try:
            # Check if ZAP is already running
            response = requests.get(
                f"http://localhost:{self.zap_config['api_port']}/JSON/core/view/version/",
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("OWASP ZAP already running")
                return True
                
        except requests.RequestException:
            pass
        
        try:
            # Start ZAP in daemon mode
            zap_command = [
                "zap.sh",
                "-daemon",
                "-port", str(self.zap_config["api_port"]),
                "-config", f"proxy.port={self.zap_config['proxy_port']}",
                "-config", "api.disablekey=true"
            ]
            
            logger.info("Starting OWASP ZAP proxy...")
            self.zap_process = subprocess.Popen(
                zap_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for ZAP to start
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get(
                        f"http://localhost:{self.zap_config['api_port']}/JSON/core/view/version/",
                        timeout=2
                    )
                    
                    if response.status_code == 200:
                        logger.info("OWASP ZAP started successfully")
                        return True
                        
                except requests.RequestException:
                    await asyncio.sleep(1)
            
            logger.error("Failed to start OWASP ZAP")
            return False
            
        except Exception as e:
            logger.error(f"Error starting OWASP ZAP: {e}")
            return False
    
    async def run_owasp_zap_scan(self, target_url: str) -> Dict[str, Any]:
        """Run OWASP ZAP automated security scan"""
        if not self.zap_config["enabled"]:
            return {"status": "disabled", "vulnerabilities": []}
        
        vulnerabilities = []
        scan_id = None
        
        try:
            # Start passive scan
            logger.info(f"Starting ZAP passive scan for {target_url}")
            
            # Access the target through ZAP proxy to trigger passive scan
            proxies = {"http": f"http://localhost:{self.zap_config['proxy_port']}"}
            
            try:
                requests.get(target_url, proxies=proxies, timeout=10, verify=False)
            except Exception:
                pass  # Expected if target is not accessible
            
            # Start active scan if enabled
            if self.config.get("enable_active_scans", True):
                logger.info(f"Starting ZAP active scan for {target_url}")
                
                response = requests.get(
                    f"http://localhost:{self.zap_config['api_port']}/JSON/ascan/action/scan/",
                    params={"url": target_url},
                    timeout=10
                )
                
                if response.status_code == 200:
                    scan_data = response.json()
                    scan_id = scan_data.get("scan")
                    
                    # Wait for scan completion
                    await self._wait_for_zap_scan_completion(scan_id)
            
            # Get scan results
            response = requests.get(
                f"http://localhost:{self.zap_config['api_port']}/JSON/core/view/alerts/",
                params={"baseurl": target_url},
                timeout=10
            )
            
            if response.status_code == 200:
                alerts = response.json().get("alerts", [])
                
                for alert in alerts:
                    vulnerability = {
                        "type": "zap_detection",
                        "severity": self._map_zap_severity(alert.get("risk", "Low")),
                        "name": alert.get("name", "Unknown"),
                        "description": alert.get("description", ""),
                        "url": alert.get("url", ""),
                        "param": alert.get("param", ""),
                        "evidence": alert.get("evidence", ""),
                        "solution": alert.get("solution", ""),
                        "reference": alert.get("reference", ""),
                        "cwe_id": alert.get("cweid", ""),
                        "wasc_id": alert.get("wascid", "")
                    }
                    vulnerabilities.append(vulnerability)
            
            return {
                "status": "completed",
                "scan_id": scan_id,
                "vulnerabilities": vulnerabilities,
                "target_url": target_url
            }
            
        except Exception as e:
            logger.error(f"ZAP scan error for {target_url}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "vulnerabilities": vulnerabilities
            }
    
    async def _wait_for_zap_scan_completion(self, scan_id: str, max_wait: int = 600) -> bool:
        """Wait for ZAP active scan to complete"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"http://localhost:{self.zap_config['api_port']}/JSON/ascan/view/status/",
                    params={"scanId": scan_id},
                    timeout=5
                )
                
                if response.status_code == 200:
                    status_data = response.json()
                    progress = int(status_data.get("status", 0))
                    
                    if progress >= 100:
                        logger.info(f"ZAP scan {scan_id} completed")
                        return True
                    
                    logger.info(f"ZAP scan {scan_id} progress: {progress}%")
                    
            except Exception as e:
                logger.warning(f"Error checking ZAP scan status: {e}")
            
            await asyncio.sleep(5)
        
        logger.warning(f"ZAP scan {scan_id} timed out")
        return False
    
    def _map_zap_severity(self, zap_severity: str) -> str:
        """Map ZAP severity levels to standard levels"""
        severity_map = {
            "High": "CRITICAL",
            "Medium": "HIGH", 
            "Low": "MEDIUM",
            "Informational": "LOW"
        }
        return severity_map.get(zap_severity, "LOW")
    
    async def run_custom_security_tests(self) -> List[Dict[str, Any]]:
        """Run custom security tests beyond ZAP scanning"""
        vulnerabilities = []
        
        # Test 1: SSL/TLS configuration
        ssl_vulns = await self._test_ssl_tls_configuration()
        vulnerabilities.extend(ssl_vulns)
        
        # Test 2: HTTP security headers
        header_vulns = await self._test_security_headers()
        vulnerabilities.extend(header_vulns)
        
        # Test 3: Authentication bypass attempts
        auth_vulns = await self._test_authentication_bypass()
        vulnerabilities.extend(auth_vulns)
        
        # Test 4: Information disclosure
        info_vulns = await self._test_information_disclosure()
        vulnerabilities.extend(info_vulns)
        
        # Test 5: Rate limiting and DoS protection
        dos_vulns = await self._test_dos_protection()
        vulnerabilities.extend(dos_vulns)
        
        return vulnerabilities
    
    async def _test_ssl_tls_configuration(self) -> List[Dict[str, Any]]:
        """Test SSL/TLS configuration security"""
        vulnerabilities = []
        
        for target_url in self.config["target_urls"]:
            if not target_url.startswith("https://"):
                continue
                
            try:
                # Parse URL to get host and port
                from urllib.parse import urlparse
                parsed = urlparse(target_url)
                host = parsed.hostname
                port = parsed.port or 443
                
                # Test SSL/TLS with different protocol versions
                ssl_tests = [
                    ("TLSv1.3", True),   # Should be supported
                    ("TLSv1.2", True),   # Should be supported  
                    ("TLSv1.1", False),  # Should be disabled
                    ("TLSv1", False),    # Should be disabled
                    ("SSLv3", False),    # Should be disabled
                    ("SSLv2", False),    # Should be disabled
                ]
                
                for protocol, should_support in ssl_tests:
                    try:
                        import ssl
                        context = ssl.create_default_context()
                        
                        # Configure for specific protocol testing
                        if protocol == "TLSv1.3":
                            context.minimum_version = ssl.TLSVersion.TLSv1_3
                        elif protocol == "TLSv1.2":
                            context.minimum_version = ssl.TLSVersion.TLSv1_2
                            context.maximum_version = ssl.TLSVersion.TLSv1_2
                        elif protocol == "TLSv1.1":
                            context.minimum_version = ssl.TLSVersion.TLSv1_1
                            context.maximum_version = ssl.TLSVersion.TLSv1_1
                        
                        sock = socket.create_connection((host, port), timeout=5)
                        ssl_sock = context.wrap_socket(sock, server_hostname=host)
                        
                        # Connection successful
                        actual_protocol = ssl_sock.version()
                        ssl_sock.close()
                        
                        if not should_support:
                            vulnerabilities.append({
                                "type": "weak_ssl_protocol",
                                "severity": "HIGH" if protocol in ["SSLv2", "SSLv3"] else "MEDIUM",
                                "protocol": actual_protocol,
                                "target": target_url,
                                "description": f"Insecure protocol {actual_protocol} supported"
                            })
                            
                    except Exception:
                        # Connection failed (expected for disabled protocols)
                        if should_support:
                            vulnerabilities.append({
                                "type": "missing_secure_protocol",
                                "severity": "MEDIUM",
                                "protocol": protocol,
                                "target": target_url,
                                "description": f"Secure protocol {protocol} not supported"
                            })
                
            except Exception as e:
                logger.warning(f"SSL/TLS test failed for {target_url}: {e}")
        
        return vulnerabilities
    
    async def _test_security_headers(self) -> List[Dict[str, Any]]:
        """Test HTTP security headers"""
        vulnerabilities = []
        
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=",
            "Content-Security-Policy": "default-src",
            "Referrer-Policy": ["strict-origin-when-cross-origin", "strict-origin"]
        }
        
        for target_url in self.config["target_urls"]:
            if target_url.startswith("ws://") or target_url.startswith("wss://"):
                continue  # Skip WebSocket URLs for HTTP header tests
            
            try:
                response = requests.get(target_url, timeout=10, verify=False)
                headers = response.headers
                
                for header_name, expected_values in required_headers.items():
                    if header_name not in headers:
                        vulnerabilities.append({
                            "type": "missing_security_header",
                            "severity": "MEDIUM",
                            "header": header_name,
                            "target": target_url,
                            "description": f"Missing security header: {header_name}"
                        })
                    else:
                        header_value = headers[header_name]
                        
                        # Check if header value is acceptable
                        if isinstance(expected_values, list):
                            if not any(exp in header_value for exp in expected_values):
                                vulnerabilities.append({
                                    "type": "weak_security_header",
                                    "severity": "LOW",
                                    "header": header_name,
                                    "value": header_value,
                                    "target": target_url,
                                    "description": f"Weak security header value: {header_name}: {header_value}"
                                })
                        elif expected_values not in header_value:
                            vulnerabilities.append({
                                "type": "weak_security_header",
                                "severity": "LOW",
                                "header": header_name,
                                "value": header_value,
                                "target": target_url,
                                "description": f"Weak security header value: {header_name}: {header_value}"
                            })
                
            except Exception as e:
                logger.warning(f"Security headers test failed for {target_url}: {e}")
        
        return vulnerabilities
    
    async def _test_authentication_bypass(self) -> List[Dict[str, Any]]:
        """Test authentication bypass vulnerabilities"""
        vulnerabilities = []
        
        # Common authentication bypass payloads
        bypass_payloads = [
            # SQL injection in auth
            {"username": "admin'--", "password": "anything"},
            {"username": "admin' OR '1'='1'--", "password": "anything"},
            
            # NoSQL injection
            {"username": {"$ne": "null"}, "password": {"$ne": "null"}},
            
            # LDAP injection
            {"username": "admin)(&(password=*))", "password": "anything"},
            
            # HTTP parameter pollution
            {"username": ["admin", "guest"], "password": "password"},
            
            # Header injection
            {"username": "admin", "password": "password", "headers": {"X-Forwarded-For": "127.0.0.1"}},
        ]
        
        for target_url in self.config["target_urls"]:
            if target_url.startswith("ws://") or target_url.startswith("wss://"):
                continue
                
            # Test common authentication endpoints
            auth_endpoints = [
                "/auth/login", "/login", "/api/auth/login", "/api/login",
                "/authenticate", "/signin", "/api/signin"
            ]
            
            for endpoint in auth_endpoints:
                test_url = f"{target_url.rstrip('/')}{endpoint}"
                
                for payload in bypass_payloads:
                    try:
                        headers = payload.pop("headers", {})
                        
                        response = requests.post(
                            test_url,
                            json=payload,
                            headers=headers,
                            timeout=5,
                            verify=False
                        )
                        
                        # Check for successful bypass indicators
                        if response.status_code == 200:
                            response_text = response.text.lower()
                            success_indicators = [
                                "success", "authenticated", "token", "welcome",
                                "dashboard", "profile", "admin"
                            ]
                            
                            if any(indicator in response_text for indicator in success_indicators):
                                vulnerabilities.append({
                                    "type": "authentication_bypass",
                                    "severity": "CRITICAL",
                                    "endpoint": test_url,
                                    "payload": str(payload),
                                    "response_code": response.status_code,
                                    "description": "Potential authentication bypass detected"
                                })
                        
                    except Exception:
                        continue  # Expected for many endpoints
        
        return vulnerabilities
    
    async def _test_information_disclosure(self) -> List[Dict[str, Any]]:
        """Test information disclosure vulnerabilities"""
        vulnerabilities = []
        
        # Common information disclosure paths
        disclosure_paths = [
            "/.env", "/config.json", "/config.yml", "/config.yaml",
            "/backup.sql", "/database.sql", "/db.sql",
            "/admin", "/admin.php", "/administrator",
            "/.git/config", "/.git/HEAD", "/.svn/entries",
            "/robots.txt", "/sitemap.xml", "/crossdomain.xml",
            "/web.config", "/.htaccess", "/.htpasswd",
            "/server-status", "/server-info", "/info.php",
            "/test", "/test.php", "/debug", "/debug.php",
            "/phpmyadmin", "/adminer", "/wp-admin",
            "/api/users", "/api/admin", "/api/config",
            "/logs/", "/log/", "/error_log", "/access_log"
        ]
        
        for target_url in self.config["target_urls"]:
            if target_url.startswith("ws://") or target_url.startswith("wss://"):
                continue
                
            for path in disclosure_paths:
                test_url = f"{target_url.rstrip('/')}{path}"
                
                try:
                    response = requests.get(test_url, timeout=5, verify=False)
                    
                    # Check for successful disclosure
                    if response.status_code == 200:
                        content = response.text.lower()
                        
                        # Look for sensitive information patterns
                        sensitive_patterns = [
                            "password", "secret", "api_key", "database",
                            "mysql", "postgresql", "mongodb", "redis",
                            "aws_access_key", "private_key", "certificate",
                            "config", "environment", "debug", "error"
                        ]
                        
                        found_patterns = [p for p in sensitive_patterns if p in content]
                        
                        if found_patterns:
                            vulnerabilities.append({
                                "type": "information_disclosure",
                                "severity": "HIGH",
                                "url": test_url,
                                "patterns": found_patterns,
                                "response_code": response.status_code,
                                "description": f"Information disclosure at {path}"
                            })
                    
                except Exception:
                    continue
        
        return vulnerabilities
    
    async def _test_dos_protection(self) -> List[Dict[str, Any]]:
        """Test denial of service protection"""
        vulnerabilities = []
        
        for target_url in self.config["target_urls"]:
            if target_url.startswith("ws://") or target_url.startswith("wss://"):
                continue
                
            # Test rate limiting
            try:
                response_codes = []
                start_time = time.time()
                
                # Send rapid requests
                for i in range(100):
                    try:
                        response = requests.get(target_url, timeout=2, verify=False)
                        response_codes.append(response.status_code)
                        
                        # Check if rate limited
                        if response.status_code == 429:  # Too Many Requests
                            break
                            
                    except Exception:
                        break
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Analyze results
                successful_requests = len([code for code in response_codes if code == 200])
                
                if successful_requests > 50 and duration < 10:  # Too many successful requests too quickly
                    vulnerabilities.append({
                        "type": "insufficient_rate_limiting",
                        "severity": "MEDIUM",
                        "url": target_url,
                        "successful_requests": successful_requests,
                        "duration": duration,
                        "description": f"Insufficient rate limiting: {successful_requests} requests in {duration:.2f}s"
                    })
                
            except Exception as e:
                logger.warning(f"DoS protection test failed for {target_url}: {e}")
        
        return vulnerabilities
    
    async def run_comprehensive_penetration_test(self) -> Dict[str, Any]:
        """Run comprehensive automated penetration test"""
        start_time = time.time()
        
        logger.info(f"Starting comprehensive penetration test session: {self.test_session_id}")
        
        # Initialize ZAP if enabled
        zap_initialized = await self.initialize_zap_proxy()
        
        all_vulnerabilities = []
        test_results = {}
        
        try:
            # Run ZAP scans for each target
            if zap_initialized:
                for target_url in self.config["target_urls"]:
                    if target_url.startswith("ws://") or target_url.startswith("wss://"):
                        continue  # ZAP doesn't scan WebSocket URLs directly
                    
                    logger.info(f"Running ZAP scan for {target_url}")
                    zap_result = await self.run_owasp_zap_scan(target_url)
                    
                    all_vulnerabilities.extend(zap_result.get("vulnerabilities", []))
                    test_results[f"zap_scan_{target_url}"] = zap_result
            
            # Run custom security tests
            logger.info("Running custom security tests")
            custom_vulnerabilities = await self.run_custom_security_tests()
            all_vulnerabilities.extend(custom_vulnerabilities)
            
            test_results["custom_security_tests"] = {
                "status": "completed",
                "vulnerabilities": len(custom_vulnerabilities),
                "details": custom_vulnerabilities
            }
            
        except Exception as e:
            logger.error(f"Penetration test error: {e}")
            test_results["error"] = str(e)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate summary
        critical_vulns = len([v for v in all_vulnerabilities if v.get("severity") == "CRITICAL"])
        high_vulns = len([v for v in all_vulnerabilities if v.get("severity") == "HIGH"])
        medium_vulns = len([v for v in all_vulnerabilities if v.get("severity") == "MEDIUM"])
        low_vulns = len([v for v in all_vulnerabilities if v.get("severity") == "LOW"])
        
        summary = {
            "session_id": self.test_session_id,
            "duration": duration,
            "targets_tested": len(self.config["target_urls"]),
            "zap_enabled": zap_initialized,
            "total_vulnerabilities": len(all_vulnerabilities),
            "critical_vulnerabilities": critical_vulns,
            "high_vulnerabilities": high_vulns,
            "medium_vulnerabilities": medium_vulns,
            "low_vulnerabilities": low_vulns,
            "risk_score": critical_vulns * 10 + high_vulns * 7 + medium_vulns * 4 + low_vulns * 1,
            "security_grade": self._calculate_security_grade(critical_vulns, high_vulns, medium_vulns, low_vulns)
        }
        
        # Generate reports
        report_path = await self._generate_penetration_test_report(summary, test_results, all_vulnerabilities)
        
        result = {
            "summary": summary,
            "test_results": test_results,
            "vulnerabilities": all_vulnerabilities,
            "report_path": str(report_path),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Penetration test completed in {duration:.2f}s")
        logger.info(f"Found {len(all_vulnerabilities)} vulnerabilities (C:{critical_vulns}, H:{high_vulns}, M:{medium_vulns}, L:{low_vulns})")
        logger.info(f"Security Grade: {summary['security_grade']}")
        logger.info(f"Report saved to: {report_path}")
        
        return result
    
    def _calculate_security_grade(self, critical: int, high: int, medium: int, low: int) -> str:
        """Calculate security grade based on vulnerability counts"""
        if critical > 0:
            return "F"
        elif high > 5:
            return "D"
        elif high > 2:
            return "C"
        elif high > 0 or medium > 10:
            return "B"
        elif medium > 5:
            return "A-"
        elif medium > 0 or low > 10:
            return "A"
        else:
            return "A+"
    
    async def _generate_penetration_test_report(
        self, 
        summary: Dict[str, Any], 
        test_results: Dict[str, Any], 
        vulnerabilities: List[Dict[str, Any]]
    ) -> Path:
        """Generate comprehensive penetration test report"""
        
        report_path = self.report_dir / "penetration_test_report.html"
        
        # Generate HTML report
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Penetration Test Report - {self.test_session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ background: #ecf0f1; padding: 20px; margin: 20px 0; border-radius: 5px; }}
        .vulnerability {{ margin: 10px 0; padding: 15px; border-left: 4px solid; }}
        .critical {{ border-left-color: #e74c3c; background: #fdf2f2; }}
        .high {{ border-left-color: #e67e22; background: #fef9e7; }}
        .medium {{ border-left-color: #f39c12; background: #fefbf3; }}
        .low {{ border-left-color: #3498db; background: #f4f9ff; }}
        .grade {{ font-size: 3em; font-weight: bold; margin: 20px 0; text-align: center; }}
        .grade.A {{ color: #27ae60; }}
        .grade.B {{ color: #f39c12; }}
        .grade.C {{ color: #e67e22; }}
        .grade.D {{ color: #e74c3c; }}
        .grade.F {{ color: #c0392b; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .owasp {{ background: #3498db; color: white; padding: 5px 10px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Penetration Test Report</h1>
        <p>Session ID: {self.test_session_id}</p>
        <p>Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
    </div>
    
    <div class="grade {summary['security_grade'][0]}">
        Security Grade: {summary['security_grade']}
    </div>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Test Duration</td><td>{summary['duration']:.2f} seconds</td></tr>
            <tr><td>Targets Tested</td><td>{summary['targets_tested']}</td></tr>
            <tr><td>OWASP ZAP Enabled</td><td>{'Yes' if summary['zap_enabled'] else 'No'}</td></tr>
            <tr><td>Total Vulnerabilities</td><td>{summary['total_vulnerabilities']}</td></tr>
            <tr><td>Critical</td><td>{summary['critical_vulnerabilities']}</td></tr>
            <tr><td>High</td><td>{summary['high_vulnerabilities']}</td></tr>
            <tr><td>Medium</td><td>{summary['medium_vulnerabilities']}</td></tr>
            <tr><td>Low</td><td>{summary['low_vulnerabilities']}</td></tr>
            <tr><td>Risk Score</td><td>{summary['risk_score']}</td></tr>
        </table>
    </div>
    
    <div class="vulnerabilities">
        <h2>Vulnerabilities Found ({len(vulnerabilities)})</h2>
"""
        
        # Add vulnerabilities to report
        for vuln in vulnerabilities:
            severity_class = vuln.get("severity", "LOW").lower()
            html_content += f"""
        <div class="vulnerability {severity_class}">
            <h3>{vuln.get('name', vuln.get('type', 'Unknown'))}</h3>
            <p><strong>Severity:</strong> {vuln.get('severity', 'Unknown')}</p>
            <p><strong>Description:</strong> {vuln.get('description', 'No description available')}</p>
            {f'<p><strong>URL:</strong> {vuln.get("url", vuln.get("target", ""))}</p>' if vuln.get("url") or vuln.get("target") else ''}
            {f'<p><strong>Solution:</strong> {vuln.get("solution", "")}</p>' if vuln.get("solution") else ''}
            {f'<p><strong>CWE ID:</strong> <span class="owasp">CWE-{vuln.get("cwe_id", "")}</span></p>' if vuln.get("cwe_id") else ''}
        </div>
"""
        
        html_content += """
    </div>
    
    <div class="footer">
        <h2>Recommendations</h2>
        <ul>
            <li>Address all Critical and High severity vulnerabilities immediately</li>
            <li>Implement a regular penetration testing schedule</li>
            <li>Follow OWASP security guidelines and best practices</li>
            <li>Ensure all security patches are applied promptly</li>
            <li>Implement comprehensive security monitoring</li>
        </ul>
    </div>
</body>
</html>
"""
        
        # Write HTML report
        with open(report_path, "w") as f:
            f.write(html_content)
        
        # Generate JSON report for automation
        json_report_path = self.report_dir / "penetration_test_report.json"
        json_report = {
            "summary": summary,
            "test_results": test_results,
            "vulnerabilities": vulnerabilities,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with open(json_report_path, "w") as f:
            json.dump(json_report, f, indent=2)
        
        return report_path


# Test execution
@pytest.mark.asyncio
async def test_automated_penetration_testing():
    """Automated penetration testing suite"""
    
    config = {
        "target_urls": [
            "http://localhost:8000",
            "http://localhost:8005"
        ],
        "intensity_level": "medium",
        "enable_zap": False,  # Disable ZAP for CI/CD environments
        "enable_active_scans": True,
        "max_test_duration": 300  # 5 minutes for testing
    }
    
    framework = PenetrationTestingFramework(config)
    results = await framework.run_comprehensive_penetration_test()
    
    # Assertions for security standards
    assert results["summary"]["critical_vulnerabilities"] == 0, \
        f"Critical vulnerabilities found: {results['summary']['critical_vulnerabilities']}"
    
    assert results["summary"]["security_grade"] not in ["D", "F"], \
        f"Security grade too low: {results['summary']['security_grade']}"
    
    print(f"\nPenetration Test Results:")
    print(f"Security Grade: {results['summary']['security_grade']}")
    print(f"Risk Score: {results['summary']['risk_score']}")
    print(f"Total Vulnerabilities: {results['summary']['total_vulnerabilities']}")
    print(f"Report: {results['report_path']}")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_automated_penetration_testing())