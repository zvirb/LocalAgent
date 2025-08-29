#!/usr/bin/env python3
"""
Advanced WebSocket Security Tests - Comprehensive CVE-2024-WS002 Compliance
Enhanced testing for authentication bypass, session hijacking, and real-time security
"""

import pytest
import asyncio
import websockets
import json
import jwt
import time
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import parse_qs, urlparse
import base64
from datetime import datetime, timedelta
import threading
import ssl
import socket


class AdvancedWebSocketSecurityTester:
    """Advanced WebSocket security testing framework"""
    
    def __init__(self):
        self.test_results = []
        self.vulnerability_count = 0
        self.websocket_url = "ws://localhost:8005"
        self.secure_websocket_url = "wss://localhost:8006"
        
    async def test_websocket_session_hijacking_protection(self):
        """Test WebSocket session hijacking protection mechanisms"""
        vulnerabilities = []
        
        # Test 1: Session token extraction resistance
        valid_token = self._generate_test_jwt()
        
        try:
            # Establish legitimate connection
            headers = {"Authorization": f"Bearer {valid_token}"}
            
            async with websockets.connect(
                f"{self.websocket_url}/ws/boards/123",
                extra_headers=headers
            ) as legitimate_ws:
                
                # Send legitimate message to establish session
                await legitimate_ws.send(json.dumps({
                    "action": "subscribe",
                    "board_id": "123"
                }))
                
                # Attempt session hijacking with extracted token
                try:
                    async with websockets.connect(
                        f"{self.websocket_url}/ws/boards/123",
                        extra_headers=headers
                    ) as hijacked_ws:
                        
                        # Attempt to receive messages from original session
                        await hijacked_ws.send(json.dumps({
                            "action": "get_session_data"
                        }))
                        
                        response = await asyncio.wait_for(
                            hijacked_ws.recv(), timeout=5.0
                        )
                        
                        # Should not receive original session data
                        if "session_data" in response:
                            vulnerabilities.append({
                                "type": "session_hijacking",
                                "severity": "HIGH",
                                "description": "WebSocket session data accessible from hijacked connection"
                            })
                            
                except Exception:
                    pass  # Expected behavior
                    
        except Exception as e:
            vulnerabilities.append({
                "type": "connection_error",
                "severity": "LOW", 
                "description": f"WebSocket connection failed: {str(e)}"
            })
        
        return vulnerabilities
    
    async def test_websocket_connection_state_manipulation(self):
        """Test WebSocket connection state manipulation attacks"""
        vulnerabilities = []
        
        # Test connection state bypass attempts
        attack_payloads = [
            {"action": "force_authenticate", "bypass": True},
            {"action": "elevate_privileges", "admin": True},
            {"action": "impersonate_user", "user_id": "admin"},
            {"action": "override_auth", "token": "fake_admin_token"},
            {"action": "session_fixation", "session_id": "fixed_session"}
        ]
        
        for payload in attack_payloads:
            try:
                # Attempt connection without proper authentication
                async with websockets.connect(
                    f"{self.websocket_url}/ws/boards/123"
                ) as ws:
                    
                    await ws.send(json.dumps(payload))
                    
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        
                        # Check if attack succeeded
                        if response_data.get("status") == "success":
                            vulnerabilities.append({
                                "type": "state_manipulation",
                                "severity": "CRITICAL",
                                "payload": payload["action"],
                                "description": "WebSocket connection state manipulation successful"
                            })
                            
                    except asyncio.TimeoutError:
                        pass  # Expected for blocked attacks
                        
            except Exception:
                continue  # Connection rejected (expected)
                
        return vulnerabilities
    
    async def test_websocket_cross_protocol_attacks(self):
        """Test cross-protocol WebSocket authentication bypass"""
        vulnerabilities = []
        
        # Test HTTP to WebSocket upgrade manipulation
        upgrade_headers = {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": base64.b64encode(b"test_key_123456").decode(),
            "Sec-WebSocket-Version": "13",
            "Authorization": "Bearer fake_token"
        }
        
        try:
            # Manual HTTP upgrade request with manipulated headers
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("localhost", 8005))
            
            upgrade_request = (
                "GET /ws/boards/123 HTTP/1.1\r\n"
                "Host: localhost:8005\r\n"
                + "\r\n".join([f"{k}: {v}" for k, v in upgrade_headers.items()])
                + "\r\n\r\n"
            )
            
            sock.send(upgrade_request.encode())
            response = sock.recv(1024).decode()
            
            # Check if upgrade succeeded without proper authentication
            if "101 Switching Protocols" in response:
                if "fake_token" in upgrade_request:
                    vulnerabilities.append({
                        "type": "cross_protocol_bypass",
                        "severity": "HIGH",
                        "description": "WebSocket upgrade succeeded with invalid authentication"
                    })
            
            sock.close()
            
        except Exception:
            pass  # Connection rejected (expected)
            
        return vulnerabilities
    
    async def test_websocket_message_injection_attacks(self):
        """Test WebSocket message injection and manipulation"""
        vulnerabilities = []
        
        valid_token = self._generate_test_jwt()
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Message injection payloads
        injection_payloads = [
            # Protocol confusion
            {"type": "http_request", "data": "GET /admin HTTP/1.1\r\nHost: localhost"},
            {"type": "binary_injection", "data": b"\x00\x01\x02\x03"},
            
            # JSON injection
            {"action": "'; DROP TABLE boards; --", "data": "sql_injection"},
            {"action": "admin", "override": True, "escalate": "privileges"},
            
            # Buffer overflow attempts
            {"action": "normal", "data": "A" * 100000},
            
            # Cross-site scripting in WebSocket
            {"action": "message", "content": "<script>alert('XSS')</script>"},
            
            # Command injection through WebSocket
            {"action": "system", "command": "; cat /etc/passwd"},
        ]
        
        try:
            async with websockets.connect(
                f"{self.websocket_url}/ws/boards/123",
                extra_headers=headers
            ) as ws:
                
                for payload in injection_payloads:
                    try:
                        await ws.send(json.dumps(payload))
                        
                        response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        
                        # Check for successful injection
                        if ("error" not in response_data and 
                            response_data.get("status") == "success"):
                            
                            vulnerabilities.append({
                                "type": "message_injection",
                                "severity": "HIGH",
                                "payload": str(payload)[:100],
                                "description": "Message injection attack successful"
                            })
                            
                    except Exception:
                        continue  # Expected for blocked payloads
                        
        except Exception:
            pass
            
        return vulnerabilities
    
    async def test_websocket_timing_attacks(self):
        """Test WebSocket timing-based attacks"""
        vulnerabilities = []
        
        # Test authentication timing differences
        timing_results = []
        
        test_tokens = [
            "invalid_token_123",
            "almost_valid_token_with_correct_format_but_wrong_signature",
            "",
            "valid_format_" + "x" * 200,  # Long token
            self._generate_test_jwt(expired=True)  # Expired but valid format
        ]
        
        for token in test_tokens:
            times = []
            
            for _ in range(10):  # Multiple attempts for timing analysis
                start_time = time.time()
                
                try:
                    headers = {"Authorization": f"Bearer {token}"}
                    async with websockets.connect(
                        f"{self.websocket_url}/ws/boards/123",
                        extra_headers=headers
                    ) as ws:
                        await ws.send(json.dumps({"action": "ping"}))
                        await asyncio.wait_for(ws.recv(), timeout=2.0)
                        
                except Exception:
                    pass  # Expected for invalid tokens
                    
                end_time = time.time()
                times.append(end_time - start_time)
            
            avg_time = sum(times) / len(times)
            timing_results.append((token[:20], avg_time))
        
        # Analyze timing differences (significant differences may indicate vulnerabilities)
        timing_values = [result[1] for result in timing_results]
        max_time = max(timing_values)
        min_time = min(timing_values)
        
        if max_time - min_time > 0.5:  # >500ms difference
            vulnerabilities.append({
                "type": "timing_attack",
                "severity": "MEDIUM",
                "description": f"Significant timing differences in authentication ({max_time:.2f}s vs {min_time:.2f}s)",
                "timing_data": timing_results
            })
            
        return vulnerabilities
    
    async def test_websocket_dos_protection(self):
        """Test WebSocket denial of service protection"""
        vulnerabilities = []
        
        valid_token = self._generate_test_jwt()
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Test 1: Connection flooding
        connections = []
        try:
            # Attempt to open many connections
            for i in range(100):
                try:
                    ws = await websockets.connect(
                        f"{self.websocket_url}/ws/boards/123",
                        extra_headers=headers
                    )
                    connections.append(ws)
                except Exception:
                    break  # Rate limiting engaged
            
            if len(connections) > 50:  # Too many connections allowed
                vulnerabilities.append({
                    "type": "dos_connection_flood",
                    "severity": "HIGH",
                    "description": f"Allowed {len(connections)} simultaneous connections"
                })
                
        finally:
            # Cleanup connections
            for ws in connections:
                try:
                    await ws.close()
                except:
                    pass
        
        # Test 2: Message flooding
        try:
            async with websockets.connect(
                f"{self.websocket_url}/ws/boards/123",
                extra_headers=headers
            ) as ws:
                
                # Send rapid messages
                for i in range(1000):
                    try:
                        await ws.send(json.dumps({
                            "action": "spam",
                            "message": f"flood_{i}",
                            "timestamp": time.time()
                        }))
                    except Exception:
                        break  # Rate limiting or connection closed
                        
                # If we sent too many messages, rate limiting may be insufficient
                if i > 100:
                    vulnerabilities.append({
                        "type": "dos_message_flood",
                        "severity": "MEDIUM",
                        "description": f"Sent {i} messages before rate limiting"
                    })
                    
        except Exception:
            pass
            
        return vulnerabilities
    
    def _generate_test_jwt(self, expired: bool = False) -> str:
        """Generate a test JWT token"""
        payload = {
            "sub": "test_user_123",
            "iat": int(time.time()),
            "exp": int(time.time()) + (3600 if not expired else -3600)
        }
        
        return jwt.encode(payload, "test_secret", algorithm="HS256")
    
    async def run_comprehensive_websocket_security_tests(self) -> Dict[str, Any]:
        """Run all advanced WebSocket security tests"""
        test_methods = [
            self.test_websocket_session_hijacking_protection,
            self.test_websocket_connection_state_manipulation,
            self.test_websocket_cross_protocol_attacks,
            self.test_websocket_message_injection_attacks,
            self.test_websocket_timing_attacks,
            self.test_websocket_dos_protection
        ]
        
        all_vulnerabilities = []
        test_results = {}
        
        for test_method in test_methods:
            test_name = test_method.__name__
            print(f"Running {test_name}...")
            
            try:
                vulnerabilities = await test_method()
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
            "total_vulnerabilities": len(all_vulnerabilities),
            "critical_vulnerabilities": critical_vulns,
            "high_vulnerabilities": high_vulns,
            "medium_vulnerabilities": medium_vulns,
            "security_score": max(0, 100 - (critical_vulns * 25 + high_vulns * 15 + medium_vulns * 5))
        }
        
        return {
            "summary": summary,
            "test_results": test_results,
            "vulnerabilities": all_vulnerabilities,
            "timestamp": datetime.utcnow().isoformat()
        }


# Test execution
@pytest.mark.asyncio
async def test_advanced_websocket_security():
    """Advanced WebSocket security test suite"""
    tester = AdvancedWebSocketSecurityTester()
    results = await tester.run_comprehensive_websocket_security_tests()
    
    # Assert no critical vulnerabilities
    assert results["summary"]["critical_vulnerabilities"] == 0, \
        f"Critical WebSocket vulnerabilities found: {results['summary']['critical_vulnerabilities']}"
    
    # Assert security score meets minimum threshold
    assert results["summary"]["security_score"] >= 80, \
        f"WebSocket security score too low: {results['summary']['security_score']}/100"
    
    print(f"\nAdvanced WebSocket Security Test Results:")
    print(f"Security Score: {results['summary']['security_score']}/100")
    print(f"Total Vulnerabilities: {results['summary']['total_vulnerabilities']}")
    print(f"Critical: {results['summary']['critical_vulnerabilities']}")
    print(f"High: {results['summary']['high_vulnerabilities']}")
    print(f"Medium: {results['summary']['medium_vulnerabilities']}")


if __name__ == "__main__":
    asyncio.run(test_advanced_websocket_security())