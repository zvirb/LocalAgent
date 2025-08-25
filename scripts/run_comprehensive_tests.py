#!/usr/bin/env python3
"""
Comprehensive test runner for LocalAgent
Orchestrates all test suites with proper reporting
"""

import asyncio
import subprocess
import sys
import json
import time
from pathlib import Path
from typing import Dict, List
import argparse
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveTestRunner:
    """Orchestrates all LocalAgent test suites"""
    
    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.results = {}
        self.start_time = time.time()
        self.project_root = Path(__file__).parent.parent
    
    def load_config(self, config_path: str) -> Dict:
        """Load test configuration"""
        default_config = {
            "test_suites": {
                "unit": {"enabled": True, "timeout": 300, "critical": True},
                "integration": {"enabled": True, "timeout": 600, "critical": True},
                "e2e": {"enabled": True, "timeout": 900, "critical": True},
                "performance": {"enabled": False, "timeout": 1800, "critical": False},
                "security": {"enabled": True, "timeout": 300, "critical": True},
                "contract": {"enabled": True, "timeout": 300, "critical": False},
                "chaos": {"enabled": False, "timeout": 1200, "critical": False},
                "load": {"enabled": False, "timeout": 1800, "critical": False},
                "regression": {"enabled": True, "timeout": 600, "critical": False}
            },
            "providers": {
                "ollama": {"required": True, "url": "http://localhost:11434"},
                "openai": {"required": False, "api_key_env": "OPENAI_API_KEY"},
                "gemini": {"required": False, "api_key_env": "GEMINI_API_KEY"},
                "perplexity": {"required": False, "api_key_env": "PERPLEXITY_API_KEY"}
            },
            "reporting": {
                "formats": ["html", "json", "junit"],
                "output_dir": "test-results"
            },
            "parallel_execution": True,
            "fail_fast": False
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
                # Deep merge configs
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in default_config:
                        if isinstance(default_config[key], dict):
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
                    else:
                        default_config[key] = value
        
        return default_config
    
    async def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        logger.info("🔍 Checking prerequisites...")
        
        # Check Python dependencies
        required_packages = ['pytest', 'aiohttp', 'click', 'rich', 'pytest-asyncio']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"❌ Missing Python packages: {', '.join(missing_packages)}")
            logger.info(f"Install with: pip install {' '.join(missing_packages)}")
            return False
        
        logger.info("✅ Python dependencies available")
        
        # Check LocalAgent CLI
        try:
            result = subprocess.run(
                [sys.executable, str(self.project_root / 'scripts' / 'localagent'), '--help'],
                capture_output=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.error("❌ LocalAgent CLI not working properly")
                return False
            logger.info("✅ LocalAgent CLI available")
        except Exception as e:
            logger.error(f"❌ LocalAgent CLI check failed: {e}")
            return False
        
        # Check provider availability
        for provider, config in self.config["providers"].items():
            if config.get("required", False):
                if provider == "ollama":
                    # Check Ollama server
                    try:
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(config["url"] + "/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                                if resp.status == 200:
                                    logger.info(f"✅ {provider} server available")
                                else:
                                    logger.error(f"❌ {provider} server not responding (status: {resp.status})")
                                    return False
                    except Exception as e:
                        logger.error(f"❌ Cannot reach {provider}: {e}")
                        return False
                        
                elif "api_key_env" in config:
                    if os.getenv(config["api_key_env"]):
                        logger.info(f"✅ {provider} API key available")
                    else:
                        logger.warning(f"⚠️  {provider} API key not set (will use mock server)")
        
        # Check test directories
        test_dir = self.project_root / "tests"
        if not test_dir.exists():
            logger.error(f"❌ Tests directory not found: {test_dir}")
            return False
        
        logger.info("✅ Prerequisites check passed")
        return True
    
    def run_test_suite(self, suite_name: str) -> Dict:
        """Run a specific test suite"""
        suite_config = self.config["test_suites"][suite_name]
        
        if not suite_config["enabled"]:
            return {"skipped": True, "reason": "disabled in config"}
        
        logger.info(f"🧪 Running {suite_name} tests...")
        
        # Determine pytest command
        test_dir = self.project_root / "tests" / suite_name
        if not test_dir.exists():
            return {"skipped": True, "reason": f"test directory {test_dir} not found"}
        
        # Prepare output directory
        results_dir = self.project_root / self.config["reporting"]["output_dir"]
        results_dir.mkdir(exist_ok=True)
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_dir),
            "-v",
            "--tb=short",
            f"--timeout={suite_config['timeout']}",
            f"--junitxml={results_dir}/{suite_name}-results.xml",
            "--json-report",
            f"--json-report-file={results_dir}/{suite_name}-report.json"
        ]
        
        # Add suite-specific flags
        if suite_name == "performance":
            cmd.extend([f"--benchmark-json={results_dir}/benchmark-results.json"])
        elif suite_name == "unit":
            cmd.extend(["--cov=app", f"--cov-report=html:{results_dir}/coverage-html"])
        elif suite_name == "security":
            cmd.extend(["--tb=long"])  # More detailed output for security issues
        
        # Add markers
        if suite_name in ["chaos", "load", "performance"]:
            cmd.extend(["-m", suite_name])
        
        start_time = time.time()
        
        try:
            # Set environment variables
            env = os.environ.copy()
            env.update({
                'PYTHONPATH': str(self.project_root),
                'TEST_MODE': 'true',
                'TEST_SUITE': suite_name
            })
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=suite_config["timeout"],
                cwd=self.project_root,
                env=env
            )
            
            end_time = time.time()
            
            # Parse pytest JSON report if available
            json_report_file = results_dir / f"{suite_name}-report.json"
            test_details = None
            if json_report_file.exists():
                try:
                    with open(json_report_file) as f:
                        test_details = json.load(f)
                except:
                    pass
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "duration": end_time - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd),
                "test_details": test_details
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "duration": suite_config["timeout"],
                "error": f"Test suite timed out after {suite_config['timeout']}s"
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "duration": 0,
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict:
        """Run all enabled test suites"""
        if not await self.check_prerequisites():
            return {"error": "Prerequisites not met"}
        
        # Prepare output directory
        results_dir = self.project_root / self.config["reporting"]["output_dir"]
        results_dir.mkdir(exist_ok=True)
        
        # Define execution order (critical tests first)
        suite_order = [
            "unit",           # Fast feedback
            "integration",    # Core functionality
            "contract",       # API contracts
            "security",       # Security validation
            "e2e",           # End-to-end workflows
            "regression",    # Regression detection
            "performance",   # Performance benchmarks
            "load",          # Load testing
            "chaos"          # Chaos engineering
        ]
        
        if self.config.get("parallel_execution") and not self.config.get("fail_fast"):
            # Run non-critical tests in parallel
            critical_suites = [s for s in suite_order if self.config["test_suites"].get(s, {}).get("critical")]
            non_critical_suites = [s for s in suite_order if not self.config["test_suites"].get(s, {}).get("critical")]
            
            # Run critical tests first (sequential)
            for suite_name in critical_suites:
                if suite_name in self.config["test_suites"]:
                    self.results[suite_name] = self.run_test_suite(suite_name)
                    self._print_suite_result(suite_name, self.results[suite_name])
                    
                    # Stop on critical failures if fail_fast enabled
                    if (self.config.get("fail_fast") and 
                        not self.results[suite_name].get("success") and 
                        not self.results[suite_name].get("skipped")):
                        logger.error(f"🛑 Stopping due to {suite_name} test failure (fail_fast enabled)")
                        break
            
            # Run non-critical tests in parallel
            if non_critical_suites and all(
                r.get("success") or r.get("skipped") 
                for r in self.results.values()
            ):
                logger.info(f"🚀 Running non-critical tests in parallel: {', '.join(non_critical_suites)}")
                
                tasks = []
                for suite_name in non_critical_suites:
                    if suite_name in self.config["test_suites"]:
                        task = asyncio.create_task(
                            asyncio.to_thread(self.run_test_suite, suite_name)
                        )
                        tasks.append((suite_name, task))
                
                # Wait for all parallel tasks
                for suite_name, task in tasks:
                    try:
                        self.results[suite_name] = await task
                        self._print_suite_result(suite_name, self.results[suite_name])
                    except Exception as e:
                        self.results[suite_name] = {
                            "success": False,
                            "error": f"Task execution failed: {str(e)}"
                        }
                        self._print_suite_result(suite_name, self.results[suite_name])
        else:
            # Sequential execution
            for suite_name in suite_order:
                if suite_name in self.config["test_suites"]:
                    self.results[suite_name] = self.run_test_suite(suite_name)
                    self._print_suite_result(suite_name, self.results[suite_name])
                    
                    # Stop on critical failures
                    if (suite_name in ["unit", "integration"] and 
                        not self.results[suite_name].get("success") and 
                        not self.results[suite_name].get("skipped")):
                        logger.error(f"🛑 Stopping due to {suite_name} test failure")
                        break
        
        return self.results
    
    def _print_suite_result(self, suite_name: str, result: Dict):
        """Print immediate feedback for a test suite result"""
        if result.get("skipped"):
            logger.info(f"⏭️  {suite_name}: skipped ({result['reason']})")
        elif result.get("success"):
            duration = result.get("duration", 0)
            logger.info(f"✅ {suite_name}: passed in {duration:.1f}s")
        else:
            duration = result.get("duration", 0)
            logger.error(f"❌ {suite_name}: failed in {duration:.1f}s")
            if result.get("error"):
                logger.error(f"   Error: {result['error']}")
            # Print first few lines of stderr for context
            if result.get("stderr"):
                stderr_lines = result["stderr"].split('\n')[:5]
                for line in stderr_lines:
                    if line.strip():
                        logger.error(f"   {line}")
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        
        # Count results
        passed = sum(1 for r in self.results.values() if r.get("success"))
        failed = sum(1 for r in self.results.values() if not r.get("success") and not r.get("skipped"))
        skipped = sum(1 for r in self.results.values() if r.get("skipped"))
        total = len(self.results)
        
        # Calculate detailed test statistics
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for result in self.results.values():
            if result.get("test_details") and "summary" in result["test_details"]:
                summary = result["test_details"]["summary"]
                total_tests += summary.get("total", 0)
                passed_tests += summary.get("passed", 0)
                failed_tests += summary.get("failed", 0)
        
        report = {
            "summary": {
                "total_suites": total,
                "passed_suites": passed,
                "failed_suites": failed,
                "skipped_suites": skipped,
                "suite_success_rate": passed / (total - skipped) if total > skipped else 0,
                "total_duration": total_duration,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "test_success_rate": passed_tests / total_tests if total_tests > 0 else 0
            },
            "results": self.results,
            "timestamp": time.time(),
            "config": self.config,
            "environment": {
                "python_version": sys.version,
                "platform": sys.platform,
                "cwd": str(self.project_root)
            }
        }
        
        # Save reports
        results_dir = self.project_root / self.config["reporting"]["output_dir"]
        
        # JSON report
        with open(results_dir / "comprehensive-report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # HTML report
        if "html" in self.config["reporting"]["formats"]:
            self.generate_html_report(report)
        
        return report
    
    def generate_html_report(self, report: Dict):
        """Generate HTML test report"""
        html_template = """<!DOCTYPE html>
<html>
<head>
    <title>LocalAgent Comprehensive Test Report</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; }}
        .summary-card h3 {{ margin: 0 0 10px 0; color: #495057; }}
        .summary-card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
        .success {{ color: #28a745 !important; border-color: #28a745 !important; }}
        .failure {{ color: #dc3545 !important; border-color: #dc3545 !important; }}
        .skipped {{ color: #ffc107 !important; border-color: #ffc107 !important; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; border: 1px solid #dee2e6; text-align: left; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        .status-badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; text-transform: uppercase; }}
        .status-passed {{ background: #d4edda; color: #155724; }}
        .status-failed {{ background: #f8d7da; color: #721c24; }}
        .status-skipped {{ background: #fff3cd; color: #856404; }}
        .details {{ margin: 20px; }}
        .suite-details {{ background: #f8f9fa; margin: 10px 0; padding: 20px; border-radius: 8px; }}
        .suite-details h3 {{ margin: 0 0 15px 0; color: #495057; }}
        .progress-bar {{ background: #e9ecef; border-radius: 4px; height: 20px; overflow: hidden; }}
        .progress-fill {{ height: 100%; transition: width 0.3s ease; }}
        .progress-success {{ background: #28a745; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 14px; }}
        .expandable {{ cursor: pointer; }}
        .expandable:hover {{ background: #f1f3f4; }}
        .hidden {{ display: none; }}
        .timestamp {{ color: #6c757d; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 LocalAgent Comprehensive Test Report</h1>
            <p class="timestamp">Generated on {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card {suite_success_class}">
                <h3>Test Suites</h3>
                <div class="value">{passed_suites}/{total_suites}</div>
                <div>Success Rate: {suite_success_rate:.1%}</div>
            </div>
            
            <div class="summary-card {test_success_class}">
                <h3>Individual Tests</h3>
                <div class="value">{passed_tests}/{total_tests}</div>
                <div>Success Rate: {test_success_rate:.1%}</div>
            </div>
            
            <div class="summary-card">
                <h3>Duration</h3>
                <div class="value">{total_duration:.1f}s</div>
                <div>Total execution time</div>
            </div>
            
            <div class="summary-card {skipped_class}">
                <h3>Skipped</h3>
                <div class="value">{skipped_suites}</div>
                <div>Suites not executed</div>
            </div>
        </div>
        
        <div class="details">
            <h2>📊 Test Suite Results</h2>
            <table>
                <tr>
                    <th>Test Suite</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Tests</th>
                    <th>Actions</th>
                </tr>
                {suite_rows}
            </table>
            
            <h2>📋 Detailed Results</h2>
            {detailed_results}
        </div>
    </div>
    
    <script>
        function toggleDetails(id) {{
            const element = document.getElementById(id);
            element.classList.toggle('hidden');
        }}
    </script>
</body>
</html>"""
        
        # Determine CSS classes for summary cards
        suite_success_rate = report["summary"]["suite_success_rate"]
        test_success_rate = report["summary"]["test_success_rate"]
        
        suite_success_class = "success" if suite_success_rate > 0.8 else "failure" if suite_success_rate < 0.5 else ""
        test_success_class = "success" if test_success_rate > 0.8 else "failure" if test_success_rate < 0.5 else ""
        skipped_class = "skipped" if report["summary"]["skipped_suites"] > 0 else ""
        
        # Generate suite rows
        suite_rows = []
        for suite_name, result in report["results"].items():
            if result.get("skipped"):
                status_badge = '<span class="status-badge status-skipped">SKIPPED</span>'
                duration = "-"
                tests = "-"
            elif result.get("success"):
                status_badge = '<span class="status-badge status-passed">PASSED</span>'
                duration = f"{result.get('duration', 0):.1f}s"
                test_details = result.get("test_details", {}).get("summary", {})
                tests = f"{test_details.get('passed', 0)}/{test_details.get('total', 0)}"
            else:
                status_badge = '<span class="status-badge status-failed">FAILED</span>'
                duration = f"{result.get('duration', 0):.1f}s"
                test_details = result.get("test_details", {}).get("summary", {})
                tests = f"{test_details.get('passed', 0)}/{test_details.get('total', 0)}"
            
            suite_rows.append(f"""
                <tr class="expandable" onclick="toggleDetails('{suite_name}_details')">
                    <td><strong>{suite_name.title()}</strong></td>
                    <td>{status_badge}</td>
                    <td>{duration}</td>
                    <td>{tests}</td>
                    <td><button onclick="event.stopPropagation(); toggleDetails('{suite_name}_details')">Toggle Details</button></td>
                </tr>
            """)
        
        # Generate detailed results
        detailed_results = []
        for suite_name, result in report["results"].items():
            status = "PASSED" if result.get("success") else "FAILED" if not result.get("skipped") else "SKIPPED"
            status_class = "success" if result.get("success") else "failure" if not result.get("skipped") else "skipped"
            
            # Test details
            test_info = ""
            if result.get("test_details") and "summary" in result["test_details"]:
                summary = result["test_details"]["summary"]
                test_info = f"""
                    <p><strong>Tests:</strong> {summary.get('total', 0)} total, 
                    {summary.get('passed', 0)} passed, 
                    {summary.get('failed', 0)} failed</p>
                """
            
            # Progress bar for test success
            progress_width = 0
            if result.get("test_details") and "summary" in result["test_details"]:
                summary = result["test_details"]["summary"]
                total = summary.get("total", 1)
                passed = summary.get("passed", 0)
                progress_width = (passed / total * 100) if total > 0 else 0
            
            # Error output (truncated)
            error_output = ""
            if result.get("stderr"):
                stderr_lines = result["stderr"].split('\n')[:20]  # First 20 lines
                error_output = f"""
                    <h4>Error Output:</h4>
                    <pre>{chr(10).join(stderr_lines)}</pre>
                """
            
            detailed_results.append(f"""
                <div class="suite-details" id="{suite_name}_details">
                    <h3 class="{status_class}">{suite_name.title()} Test Suite</h3>
                    <p><strong>Status:</strong> {status}</p>
                    <p><strong>Duration:</strong> {result.get('duration', 0):.1f}s</p>
                    {test_info}
                    <div class="progress-bar">
                        <div class="progress-fill progress-success" style="width: {progress_width}%"></div>
                    </div>
                    {f"<p><strong>Skip Reason:</strong> {result['reason']}</p>" if result.get('reason') else ""}
                    {f"<p><strong>Error:</strong> {result['error']}</p>" if result.get('error') else ""}
                    {error_output}
                </div>
            """)
        
        # Format timestamp
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report["timestamp"]))
        
        html_content = html_template.format(
            timestamp=timestamp_str,
            total_suites=report["summary"]["total_suites"],
            passed_suites=report["summary"]["passed_suites"],
            failed_suites=report["summary"]["failed_suites"],
            skipped_suites=report["summary"]["skipped_suites"],
            suite_success_rate=report["summary"]["suite_success_rate"],
            total_tests=report["summary"]["total_tests"],
            passed_tests=report["summary"]["passed_tests"],
            failed_tests=report["summary"]["failed_tests"],
            test_success_rate=report["summary"]["test_success_rate"],
            total_duration=report["summary"]["total_duration"],
            suite_success_class=suite_success_class,
            test_success_class=test_success_class,
            skipped_class=skipped_class,
            suite_rows="".join(suite_rows),
            detailed_results="".join(detailed_results)
        )
        
        results_dir = self.project_root / self.config["reporting"]["output_dir"]
        with open(results_dir / "comprehensive-report.html", "w") as f:
            f.write(html_content)

async def main():
    parser = argparse.ArgumentParser(description="LocalAgent Comprehensive Test Runner")
    parser.add_argument("--config", help="Test configuration file")
    parser.add_argument("--suites", nargs="+", help="Specific test suites to run")
    parser.add_argument("--skip-prerequisites", action="store_true", help="Skip prerequisite checks")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--parallel", action="store_true", help="Run non-critical tests in parallel")
    parser.add_argument("--output-dir", help="Output directory for test results")
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner(args.config)
    
    # Override config with command line args
    if args.fail_fast:
        runner.config["fail_fast"] = True
    if args.parallel:
        runner.config["parallel_execution"] = True
    if args.output_dir:
        runner.config["reporting"]["output_dir"] = args.output_dir
    
    if args.suites:
        # Run specific suites only
        logger.info(f"🎯 Running specific test suites: {', '.join(args.suites)}")
        for suite in args.suites:
            if suite in runner.config["test_suites"]:
                runner.results[suite] = runner.run_test_suite(suite)
                runner._print_suite_result(suite, runner.results[suite])
    else:
        # Run all tests
        logger.info("🚀 Starting comprehensive test execution")
        await runner.run_all_tests()
    
    # Generate report
    report = runner.generate_report()
    
    # Print final summary
    logger.info("\n" + "="*60)
    logger.info("📊 Final Test Summary")
    logger.info("="*60)
    logger.info(f"   Total Suites: {report['summary']['total_suites']}")
    logger.info(f"   ✅ Passed: {report['summary']['passed_suites']}")
    logger.info(f"   ❌ Failed: {report['summary']['failed_suites']}")
    logger.info(f"   ⏭️  Skipped: {report['summary']['skipped_suites']}")
    logger.info(f"   📈 Suite Success Rate: {report['summary']['suite_success_rate']:.1%}")
    
    if report['summary']['total_tests'] > 0:
        logger.info(f"   🧪 Individual Tests: {report['summary']['passed_tests']}/{report['summary']['total_tests']}")
        logger.info(f"   📈 Test Success Rate: {report['summary']['test_success_rate']:.1%}")
    
    logger.info(f"   ⏱️  Total Duration: {report['summary']['total_duration']:.1f}s")
    logger.info("="*60)
    
    # Report file locations
    results_dir = Path(runner.config["reporting"]["output_dir"])
    logger.info(f"📄 Reports generated:")
    logger.info(f"   📋 HTML Report: {results_dir}/comprehensive-report.html")
    logger.info(f"   📝 JSON Report: {results_dir}/comprehensive-report.json")
    
    # Exit with appropriate code
    if report['summary']['failed_suites'] > 0:
        logger.error("❌ Some test suites failed")
        sys.exit(1)
    else:
        logger.info("✅ All test suites passed")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())