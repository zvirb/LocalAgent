"""
CLIX Web Interface Browser Compatibility Tests
============================================

Tests the CLIX web-based terminal interface across different browsers,
WebSocket connections, and responsive design requirements.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import websockets
import requests
from dataclasses import dataclass

# Playwright for browser automation
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Selenium fallback
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Import test configuration
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from tests.ui_ux_comprehensive.test_framework_config import get_test_config

@dataclass
class BrowserTestResult:
    """Result of browser compatibility testing"""
    browser_name: str
    browser_version: str
    test_name: str
    passed: bool
    load_time_ms: float
    websocket_connected: bool
    responsive_design_ok: bool
    javascript_errors: List[str]
    console_warnings: List[str]
    performance_score: float

@dataclass
class WebSocketTestResult:
    """WebSocket connection test result"""
    connected: bool
    connection_time_ms: float
    message_round_trip_ms: float
    max_concurrent_connections: int
    reconnection_successful: bool
    error_messages: List[str]

class CLIXWebInterfaceTester:
    """Main tester for CLIX web interface"""
    
    def __init__(self):
        self.config = get_test_config()
        self.base_url = "http://localhost:3000"  # Default CLIX URL
        self.websocket_url = "ws://localhost:3000/ws/terminal"
        
        # Browser configurations
        self.browsers = self.config.web_interface.supported_browsers
        self.browser_matrix = self.config.web_interface.browser_compatibility_matrix
        
        # Test results
        self.test_results = {}
    
    async def run_all_browser_tests(self) -> Dict[str, List[BrowserTestResult]]:
        """Run tests across all supported browsers"""
        if not PLAYWRIGHT_AVAILABLE:
            pytest.skip("Playwright not available for browser testing")
        
        results = {}
        
        async with async_playwright() as p:
            for browser_name in self.browsers:
                browser_results = []
                
                # Test each browser version
                versions = self.browser_matrix.get(browser_name, ["latest"])
                
                for version in versions:
                    try:
                        browser = await self._launch_browser(p, browser_name, version)
                        context = await browser.new_context()
                        page = await context.new_page()
                        
                        # Run test suite for this browser
                        test_result = await self._run_browser_test_suite(browser_name, version, page)
                        browser_results.append(test_result)
                        
                        await browser.close()
                        
                    except Exception as e:
                        # Record failed browser test
                        browser_results.append(BrowserTestResult(
                            browser_name=browser_name,
                            browser_version=version,
                            test_name="browser_launch",
                            passed=False,
                            load_time_ms=0,
                            websocket_connected=False,
                            responsive_design_ok=False,
                            javascript_errors=[str(e)],
                            console_warnings=[],
                            performance_score=0.0
                        ))
                
                results[browser_name] = browser_results
        
        self.test_results = results
        return results
    
    async def _launch_browser(self, playwright_instance, browser_name: str, version: str = "latest"):
        """Launch specific browser"""
        browser_configs = {
            'chromium': playwright_instance.chromium.launch,
            'chrome': playwright_instance.chromium.launch,
            'firefox': playwright_instance.firefox.launch,
            'safari': playwright_instance.webkit.launch,
            'webkit': playwright_instance.webkit.launch,
            'edge': playwright_instance.chromium.launch
        }
        
        launch_func = browser_configs.get(browser_name, playwright_instance.chromium.launch)
        
        return await launch_func(
            headless=True,  # Run headless for CI/CD
            args=['--no-sandbox', '--disable-dev-shm-usage'] if browser_name in ['chrome', 'chromium'] else None
        )
    
    async def _run_browser_test_suite(self, browser_name: str, version: str, page: Page) -> BrowserTestResult:
        """Run complete test suite for a browser"""
        
        javascript_errors = []
        console_warnings = []
        
        # Listen for console messages
        page.on("console", lambda msg: console_warnings.append(f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda error: javascript_errors.append(str(error)))
        
        # Measure load time
        start_time = time.time()
        
        try:
            # Navigate to CLIX interface
            await page.goto(self.base_url, timeout=10000)
            
            load_time_ms = (time.time() - start_time) * 1000
            
            # Test WebSocket connection
            websocket_connected = await self._test_websocket_connection(page)
            
            # Test responsive design
            responsive_ok = await self._test_responsive_design(page)
            
            # Calculate performance score
            performance_score = await self._calculate_performance_score(page)
            
            return BrowserTestResult(
                browser_name=browser_name,
                browser_version=version,
                test_name="full_suite",
                passed=len(javascript_errors) == 0 and websocket_connected,
                load_time_ms=load_time_ms,
                websocket_connected=websocket_connected,
                responsive_design_ok=responsive_ok,
                javascript_errors=javascript_errors,
                console_warnings=console_warnings,
                performance_score=performance_score
            )
            
        except Exception as e:
            return BrowserTestResult(
                browser_name=browser_name,
                browser_version=version,
                test_name="full_suite",
                passed=False,
                load_time_ms=(time.time() - start_time) * 1000,
                websocket_connected=False,
                responsive_design_ok=False,
                javascript_errors=[str(e)],
                console_warnings=console_warnings,
                performance_score=0.0
            )
    
    async def _test_websocket_connection(self, page: Page) -> bool:
        """Test WebSocket connection functionality"""
        try:
            # Execute JavaScript to test WebSocket connection
            websocket_result = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        const ws = new WebSocket('ws://localhost:3000/ws/terminal');
                        
                        ws.onopen = () => {
                            ws.close();
                            resolve(true);
                        };
                        
                        ws.onerror = () => {
                            resolve(false);
                        };
                        
                        // Timeout after 5 seconds
                        setTimeout(() => resolve(false), 5000);
                    });
                }
            """)
            
            return websocket_result
            
        except Exception as e:
            return False
    
    async def _test_responsive_design(self, page: Page) -> bool:
        """Test responsive design across different viewport sizes"""
        
        # Test different viewport sizes
        viewports = [
            {"width": 320, "height": 568},   # Mobile
            {"width": 768, "height": 1024},  # Tablet
            {"width": 1024, "height": 768},  # Tablet landscape
            {"width": 1920, "height": 1080}  # Desktop
        ]
        
        responsive_issues = []
        
        for viewport in viewports:
            try:
                await page.set_viewport_size(viewport)
                await page.wait_for_timeout(500)  # Allow layout to adjust
                
                # Check if terminal is usable at this size
                terminal_visible = await page.is_visible('.terminal-container', timeout=1000)
                terminal_usable = await page.evaluate("""
                    () => {
                        const terminal = document.querySelector('.terminal-container');
                        if (!terminal) return false;
                        
                        const rect = terminal.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    }
                """)
                
                if not (terminal_visible and terminal_usable):
                    responsive_issues.append(f"Terminal not usable at {viewport['width']}x{viewport['height']}")
                
            except Exception as e:
                responsive_issues.append(f"Viewport test failed for {viewport}: {str(e)}")
        
        return len(responsive_issues) == 0
    
    async def _calculate_performance_score(self, page: Page) -> float:
        """Calculate overall performance score"""
        try:
            # Get performance metrics
            performance_metrics = await page.evaluate("""
                () => {
                    const performance = window.performance;
                    const navigation = performance.getEntriesByType('navigation')[0];
                    
                    return {
                        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
                        totalLoadTime: navigation.loadEventEnd - navigation.fetchStart,
                        transferSize: navigation.transferSize || 0
                    };
                }
            """)
            
            # Calculate score based on metrics (0-100)
            load_time_score = max(0, 100 - (performance_metrics['totalLoadTime'] / 50))  # 5s = 0 points
            size_score = max(0, 100 - (performance_metrics['transferSize'] / 10000))  # 1MB = 0 points
            
            return (load_time_score + size_score) / 2
            
        except Exception:
            return 0.0

class WebSocketTester:
    """Dedicated WebSocket testing"""
    
    def __init__(self, websocket_url: str = "ws://localhost:3000/ws/terminal"):
        self.websocket_url = websocket_url
        self.config = get_test_config()
    
    async def test_websocket_connection(self) -> WebSocketTestResult:
        """Test WebSocket connection establishment"""
        
        try:
            start_time = time.time()
            
            async with websockets.connect(self.websocket_url) as websocket:
                connection_time_ms = (time.time() - start_time) * 1000
                
                # Test message round trip
                test_message = json.dumps({"type": "ping", "data": "test"})
                
                round_trip_start = time.time()
                await websocket.send(test_message)
                response = await websocket.recv()
                round_trip_time = (time.time() - round_trip_start) * 1000
                
                return WebSocketTestResult(
                    connected=True,
                    connection_time_ms=connection_time_ms,
                    message_round_trip_ms=round_trip_time,
                    max_concurrent_connections=0,  # Will be tested separately
                    reconnection_successful=True,
                    error_messages=[]
                )
                
        except Exception as e:
            return WebSocketTestResult(
                connected=False,
                connection_time_ms=0,
                message_round_trip_ms=0,
                max_concurrent_connections=0,
                reconnection_successful=False,
                error_messages=[str(e)]
            )
    
    async def test_websocket_reconnection(self) -> bool:
        """Test WebSocket reconnection capability"""
        
        try:
            # Establish initial connection
            websocket = await websockets.connect(self.websocket_url)
            
            # Simulate connection loss
            await websocket.close()
            
            # Attempt reconnection
            await asyncio.sleep(1)
            websocket = await websockets.connect(self.websocket_url)
            
            # Test that reconnection works
            await websocket.send(json.dumps({"type": "test", "data": "reconnection"}))
            response = await websocket.recv()
            
            await websocket.close()
            return True
            
        except Exception:
            return False
    
    async def test_concurrent_connections(self, max_connections: int = 50) -> int:
        """Test maximum concurrent WebSocket connections"""
        
        connections = []
        successful_connections = 0
        
        try:
            for i in range(max_connections):
                try:
                    websocket = await websockets.connect(self.websocket_url)
                    connections.append(websocket)
                    successful_connections += 1
                    
                    # Small delay between connections
                    await asyncio.sleep(0.01)
                    
                except Exception:
                    break
            
            # Close all connections
            for websocket in connections:
                await websocket.close()
            
            return successful_connections
            
        except Exception:
            # Cleanup on error
            for websocket in connections:
                try:
                    await websocket.close()
                except:
                    pass
            
            return successful_connections

# Test fixtures
@pytest.fixture
def clix_tester():
    """CLIX web interface tester fixture"""
    return CLIXWebInterfaceTester()

@pytest.fixture
def websocket_tester():
    """WebSocket tester fixture"""
    return WebSocketTester()

# Browser compatibility tests
class TestBrowserCompatibility:
    """Test browser compatibility"""
    
    @pytest.mark.web_interface
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_chromium_compatibility(self, clix_tester):
        """Test Chromium/Chrome compatibility"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            result = await clix_tester._run_browser_test_suite("chromium", "latest", page)
            
            await browser.close()
            
            assert result.passed, f"Chromium test failed: {result.javascript_errors}"
            assert result.websocket_connected, "WebSocket connection failed in Chromium"
            assert result.responsive_design_ok, "Responsive design issues in Chromium"
            assert result.load_time_ms < 5000, f"Load time too slow: {result.load_time_ms}ms"
    
    @pytest.mark.web_interface
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_firefox_compatibility(self, clix_tester):
        """Test Firefox compatibility"""
        
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            result = await clix_tester._run_browser_test_suite("firefox", "latest", page)
            
            await browser.close()
            
            assert result.passed, f"Firefox test failed: {result.javascript_errors}"
            assert result.websocket_connected, "WebSocket connection failed in Firefox"
            assert result.responsive_design_ok, "Responsive design issues in Firefox"
    
    @pytest.mark.web_interface
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_webkit_safari_compatibility(self, clix_tester):
        """Test WebKit/Safari compatibility"""
        
        async with async_playwright() as p:
            browser = await p.webkit.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            result = await clix_tester._run_browser_test_suite("webkit", "latest", page)
            
            await browser.close()
            
            assert result.passed, f"WebKit test failed: {result.javascript_errors}"
            assert result.websocket_connected, "WebSocket connection failed in WebKit"
    
    @pytest.mark.web_interface
    async def test_all_supported_browsers(self, clix_tester):
        """Test all supported browsers in matrix"""
        
        results = await clix_tester.run_all_browser_tests()
        
        failed_browsers = []
        for browser_name, browser_results in results.items():
            for result in browser_results:
                if not result.passed:
                    failed_browsers.append(f"{browser_name} {result.browser_version}")
        
        assert len(failed_browsers) == 0, f"Failed browsers: {failed_browsers}"

class TestWebSocketFunctionality:
    """Test WebSocket functionality"""
    
    @pytest.mark.web_interface
    async def test_websocket_basic_connection(self, websocket_tester):
        """Test basic WebSocket connection"""
        
        result = await websocket_tester.test_websocket_connection()
        
        assert result.connected, f"WebSocket connection failed: {result.error_messages}"
        assert result.connection_time_ms < 5000, f"Connection too slow: {result.connection_time_ms}ms"
        assert result.message_round_trip_ms < 100, f"Message round trip too slow: {result.message_round_trip_ms}ms"
    
    @pytest.mark.web_interface
    async def test_websocket_reconnection(self, websocket_tester):
        """Test WebSocket reconnection"""
        
        reconnection_successful = await websocket_tester.test_websocket_reconnection()
        assert reconnection_successful, "WebSocket reconnection failed"
    
    @pytest.mark.web_interface
    async def test_websocket_concurrent_connections(self, websocket_tester):
        """Test concurrent WebSocket connections"""
        
        max_connections = await websocket_tester.test_concurrent_connections(20)
        
        # Should support at least 10 concurrent connections
        assert max_connections >= 10, f"Only {max_connections} concurrent connections supported"
    
    @pytest.mark.web_interface
    async def test_websocket_message_types(self):
        """Test different WebSocket message types"""
        
        message_types = [
            {"type": "terminal_input", "data": "ls -la"},
            {"type": "terminal_resize", "data": {"cols": 80, "rows": 24}},
            {"type": "ping", "data": "keepalive"},
            {"type": "auth", "data": {"token": "test_token"}}
        ]
        
        try:
            async with websockets.connect("ws://localhost:3000/ws/terminal") as websocket:
                for message in message_types:
                    await websocket.send(json.dumps(message))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response_data = json.loads(response)
                        
                        # Should receive some form of acknowledgment
                        assert "type" in response_data, f"Invalid response for {message['type']}"
                        
                    except asyncio.TimeoutError:
                        # Some message types might not have responses, which is OK
                        pass
                        
        except Exception as e:
            pytest.fail(f"WebSocket message testing failed: {e}")

class TestResponsiveDesign:
    """Test responsive design"""
    
    @pytest.mark.web_interface
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_mobile_viewport(self):
        """Test mobile viewport compatibility"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set mobile viewport
            await page.set_viewport_size({"width": 375, "height": 667})  # iPhone 6/7/8
            await page.goto("http://localhost:3000")
            
            # Check terminal usability on mobile
            terminal_visible = await page.is_visible('.terminal-container', timeout=5000)
            assert terminal_visible, "Terminal not visible on mobile viewport"
            
            # Check if virtual keyboard support works
            input_field = page.locator('input[type="text"], textarea').first
            if await input_field.count() > 0:
                await input_field.click()
                await input_field.type("test command")
                
                value = await input_field.input_value()
                assert "test command" in value, "Input not working on mobile"
            
            await browser.close()
    
    @pytest.mark.web_interface
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_tablet_viewport(self):
        """Test tablet viewport compatibility"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set tablet viewport
            await page.set_viewport_size({"width": 768, "height": 1024})  # iPad
            await page.goto("http://localhost:3000")
            
            # Check layout on tablet
            terminal_visible = await page.is_visible('.terminal-container', timeout=5000)
            assert terminal_visible, "Terminal not visible on tablet viewport"
            
            # Check if touch interactions work
            if await page.locator('button').count() > 0:
                button = page.locator('button').first
                await button.tap()  # Use tap instead of click for touch
            
            await browser.close()
    
    @pytest.mark.web_interface
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_desktop_viewport(self):
        """Test desktop viewport compatibility"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set desktop viewport
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.goto("http://localhost:3000")
            
            # Check full desktop functionality
            terminal_visible = await page.is_visible('.terminal-container', timeout=5000)
            assert terminal_visible, "Terminal not visible on desktop"
            
            # Test keyboard shortcuts
            await page.keyboard.press('Control+c')  # Should be handled gracefully
            await page.keyboard.press('F1')  # Help shortcut
            
            await browser.close()

class TestPerformanceMetrics:
    """Test web interface performance"""
    
    @pytest.mark.web_interface
    @pytest.mark.performance
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_page_load_performance(self):
        """Test page load performance"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            start_time = time.time()
            await page.goto("http://localhost:3000")
            
            # Wait for terminal to be ready
            await page.wait_for_selector('.terminal-container', timeout=10000)
            
            load_time = (time.time() - start_time) * 1000
            
            # Should load within 5 seconds
            assert load_time < 5000, f"Page load too slow: {load_time}ms"
            
            # Get performance metrics
            performance_metrics = await page.evaluate("""
                () => {
                    const navigation = performance.getEntriesByType('navigation')[0];
                    return {
                        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
                        firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0
                    };
                }
            """)
            
            # DOM should be ready quickly
            assert performance_metrics['domContentLoaded'] < 2000, "DOM content loaded too slowly"
            
            await browser.close()
    
    @pytest.mark.web_interface
    @pytest.mark.performance
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_javascript_performance(self):
        """Test JavaScript execution performance"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            await page.goto("http://localhost:3000")
            await page.wait_for_selector('.terminal-container')
            
            # Test JavaScript performance
            js_performance = await page.evaluate("""
                () => {
                    const start = performance.now();
                    
                    // Simulate terminal operations
                    for (let i = 0; i < 1000; i++) {
                        const div = document.createElement('div');
                        div.textContent = `Line ${i}`;
                        document.body.appendChild(div);
                        document.body.removeChild(div);
                    }
                    
                    return performance.now() - start;
                }
            """)
            
            # JavaScript operations should be fast
            assert js_performance < 100, f"JavaScript too slow: {js_performance}ms"
            
            await browser.close()

class TestSecurityFeatures:
    """Test web interface security"""
    
    @pytest.mark.web_interface
    @pytest.mark.security
    async def test_websocket_authentication(self):
        """Test WebSocket authentication"""
        
        try:
            # Test connection without authentication
            async with websockets.connect("ws://localhost:3000/ws/terminal") as websocket:
                # Send command without auth
                await websocket.send(json.dumps({
                    "type": "command",
                    "data": "ls -la"
                }))
                
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Should require authentication
                assert response_data.get("error") or response_data.get("auth_required"), \
                    "WebSocket allows unauthorized access"
                    
        except Exception as e:
            # Connection rejection is also acceptable
            assert "authentication" in str(e).lower() or "unauthorized" in str(e).lower()
    
    @pytest.mark.web_interface
    @pytest.mark.security
    @pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
    async def test_content_security_policy(self):
        """Test Content Security Policy headers"""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            response = await page.goto("http://localhost:3000")
            
            # Check for security headers
            headers = response.headers
            
            # Should have CSP header
            csp_header = headers.get('content-security-policy') or headers.get('x-content-security-policy')
            assert csp_header is not None, "Missing Content Security Policy header"
            
            # Should have other security headers
            assert 'x-frame-options' in headers, "Missing X-Frame-Options header"
            
            await browser.close()

# Integration tests
@pytest.mark.web_interface
@pytest.mark.integration
class TestIntegratedWebInterface:
    """Integrated web interface testing"""
    
    async def test_complete_terminal_session(self):
        """Test complete terminal session workflow"""
        
        if not PLAYWRIGHT_AVAILABLE:
            pytest.skip("Playwright not available")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to CLIX
            await page.goto("http://localhost:3000")
            await page.wait_for_selector('.terminal-container', timeout=10000)
            
            # Test terminal interaction
            terminal_input = page.locator('input.terminal-input, textarea.terminal-input').first
            if await terminal_input.count() > 0:
                await terminal_input.click()
                await terminal_input.type("help")
                await page.keyboard.press('Enter')
                
                # Wait for response
                await page.wait_for_timeout(1000)
                
                # Should see help output
                terminal_content = await page.text_content('.terminal-output, .terminal-content')
                assert "help" in terminal_content.lower() or "command" in terminal_content.lower()
            
            await browser.close()
    
    async def test_websocket_terminal_integration(self):
        """Test WebSocket integration with terminal"""
        
        try:
            async with websockets.connect("ws://localhost:3000/ws/terminal") as websocket:
                # Send terminal command
                command_message = json.dumps({
                    "type": "terminal_input",
                    "data": "echo 'Hello WebSocket'"
                })
                
                await websocket.send(command_message)
                
                # Should receive terminal output
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                assert response_data.get("type") in ["terminal_output", "output"], \
                    f"Unexpected response type: {response_data.get('type')}"
                    
        except Exception as e:
            pytest.fail(f"WebSocket terminal integration failed: {e}")

# Configure web interface test markers
def pytest_configure(config):
    """Configure web interface test markers"""
    config.addinivalue_line(
        "markers",
        "web_interface: marks tests as web interface tests"
    )
    config.addinivalue_line(
        "markers", 
        "security: marks tests as security tests"
    )