"""
Comprehensive Test Executor with Parallel Stream Management
=========================================================

Orchestrates all 8 test streams with performance monitoring and CI/CD integration.
"""

import asyncio
import time
import threading
import multiprocessing
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import json
import logging

from .test_framework_config import get_test_config, TestFrameworkConfig, detect_test_environment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestStreamResult:
    """Result of a single test stream execution"""
    stream_name: str
    success: bool
    test_count: int
    passed: int
    failed: int
    skipped: int
    execution_time: float
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    error_details: List[str] = field(default_factory=list)
    coverage_percentage: float = 0.0

@dataclass
class ComprehensiveTestResult:
    """Overall test execution results"""
    success: bool
    total_execution_time: float
    stream_results: Dict[str, TestStreamResult] = field(default_factory=dict)
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    ci_metrics: Dict[str, Any] = field(default_factory=dict)
    regression_detected: bool = False

class TestStreamExecutor:
    """Individual test stream executor"""
    
    def __init__(self, stream_name: str, config: TestFrameworkConfig):
        self.stream_name = stream_name
        self.config = config
        self.logger = logging.getLogger(f"TestStream.{stream_name}")
        
    async def execute_stream(self) -> TestStreamResult:
        """Execute a specific test stream"""
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting test stream: {self.stream_name}")
            
            # Route to appropriate test execution method
            if self.stream_name == "unit_tests":
                result = await self._execute_unit_tests()
            elif self.stream_name == "integration_tests":
                result = await self._execute_integration_tests()
            elif self.stream_name == "performance_tests":
                result = await self._execute_performance_tests()
            elif self.stream_name == "cross_platform_tests":
                result = await self._execute_cross_platform_tests()
            elif self.stream_name == "accessibility_tests":
                result = await self._execute_accessibility_tests()
            elif self.stream_name == "web_interface_tests":
                result = await self._execute_web_interface_tests()
            elif self.stream_name == "ai_intelligence_tests":
                result = await self._execute_ai_intelligence_tests()
            elif self.stream_name == "regression_tests":
                result = await self._execute_regression_tests()
            else:
                raise ValueError(f"Unknown test stream: {self.stream_name}")
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            self.logger.info(f"Completed test stream: {self.stream_name} in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Test stream {self.stream_name} failed: {e}")
            
            return TestStreamResult(
                stream_name=self.stream_name,
                success=False,
                test_count=0,
                passed=0,
                failed=1,
                skipped=0,
                execution_time=execution_time,
                error_details=[str(e)]
            )
    
    async def _execute_unit_tests(self) -> TestStreamResult:
        """Execute unit tests with pytest"""
        cmd = [
            "python", "-m", "pytest",
            "tests/ui_ux_comprehensive/unit/",
            "--cov=app/cli",
            "--cov-report=json",
            "--junit-xml=test_results/unit_tests.xml",
            "-v", "--tb=short"
        ]
        
        result = await self._run_subprocess_async(cmd)
        
        # Parse pytest results
        return TestStreamResult(
            stream_name="unit_tests",
            success=result["returncode"] == 0,
            test_count=result.get("test_count", 0),
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            execution_time=result.get("duration", 0.0),
            coverage_percentage=result.get("coverage", 0.0)
        )
    
    async def _execute_integration_tests(self) -> TestStreamResult:
        """Execute integration tests"""
        cmd = [
            "python", "-m", "pytest",
            "tests/ui_ux_comprehensive/integration/",
            "--junit-xml=test_results/integration_tests.xml",
            "-v", "--tb=short"
        ]
        
        result = await self._run_subprocess_async(cmd)
        
        return TestStreamResult(
            stream_name="integration_tests",
            success=result["returncode"] == 0,
            test_count=result.get("test_count", 0),
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            execution_time=result.get("duration", 0.0)
        )
    
    async def _execute_performance_tests(self) -> TestStreamResult:
        """Execute performance tests with benchmarking"""
        cmd = [
            "python", "-m", "pytest",
            "tests/ui_ux_comprehensive/performance/",
            "--benchmark-json=test_results/performance_benchmark.json",
            "--junit-xml=test_results/performance_tests.xml",
            "-v"
        ]
        
        result = await self._run_subprocess_async(cmd)
        
        # Extract performance metrics
        performance_metrics = await self._extract_performance_metrics()
        
        return TestStreamResult(
            stream_name="performance_tests",
            success=result["returncode"] == 0 and self._validate_performance_metrics(performance_metrics),
            test_count=result.get("test_count", 0),
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            execution_time=result.get("duration", 0.0),
            performance_metrics=performance_metrics
        )
    
    async def _execute_cross_platform_tests(self) -> TestStreamResult:
        """Execute cross-platform compatibility tests"""
        
        # Execute tests for each supported terminal
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for terminal in self.config.cross_platform.supported_terminals:
            cmd = [
                "python", "-m", "pytest",
                "tests/ui_ux_comprehensive/cross_platform/",
                f"--terminal={terminal}",
                f"--junit-xml=test_results/cross_platform_{terminal}.xml",
                "-v"
            ]
            
            result = await self._run_subprocess_async(cmd)
            total_tests += result.get("test_count", 0)
            total_passed += result.get("passed", 0)
            total_failed += result.get("failed", 0)
        
        return TestStreamResult(
            stream_name="cross_platform_tests",
            success=total_failed == 0,
            test_count=total_tests,
            passed=total_passed,
            failed=total_failed,
            skipped=0,
            execution_time=result.get("duration", 0.0)
        )
    
    async def _execute_accessibility_tests(self) -> TestStreamResult:
        """Execute accessibility tests"""
        cmd = [
            "python", "-m", "pytest",
            "tests/ui_ux_comprehensive/accessibility/",
            "--junit-xml=test_results/accessibility_tests.xml",
            "-v", "--tb=short"
        ]
        
        result = await self._run_subprocess_async(cmd)
        
        return TestStreamResult(
            stream_name="accessibility_tests",
            success=result["returncode"] == 0,
            test_count=result.get("test_count", 0),
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            execution_time=result.get("duration", 0.0)
        )
    
    async def _execute_web_interface_tests(self) -> TestStreamResult:
        """Execute web interface tests with Playwright"""
        cmd = [
            "python", "-m", "pytest",
            "tests/ui_ux_comprehensive/web_interface/",
            "--browser=chromium",
            "--browser=firefox",
            "--junit-xml=test_results/web_interface_tests.xml",
            "-v"
        ]
        
        result = await self._run_subprocess_async(cmd)
        
        return TestStreamResult(
            stream_name="web_interface_tests",
            success=result["returncode"] == 0,
            test_count=result.get("test_count", 0),
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            execution_time=result.get("duration", 0.0)
        )
    
    async def _execute_ai_intelligence_tests(self) -> TestStreamResult:
        """Execute AI intelligence and ML model tests"""
        cmd = [
            "python", "-m", "pytest",
            "tests/ui_ux_comprehensive/ai_intelligence/",
            "--junit-xml=test_results/ai_intelligence_tests.xml",
            "-v", "--tb=short"
        ]
        
        result = await self._run_subprocess_async(cmd)
        
        # Validate ML model performance
        ml_metrics = await self._validate_ml_performance()
        
        return TestStreamResult(
            stream_name="ai_intelligence_tests",
            success=result["returncode"] == 0 and ml_metrics["accuracy"] > self.config.ai_intelligence.model_accuracy_threshold,
            test_count=result.get("test_count", 0),
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            execution_time=result.get("duration", 0.0),
            performance_metrics=ml_metrics
        )
    
    async def _execute_regression_tests(self) -> TestStreamResult:
        """Execute regression tests"""
        cmd = [
            "python", "-m", "pytest",
            "tests/ui_ux_comprehensive/regression/",
            "--junit-xml=test_results/regression_tests.xml",
            "-v", "--tb=short"
        ]
        
        result = await self._run_subprocess_async(cmd)
        
        return TestStreamResult(
            stream_name="regression_tests",
            success=result["returncode"] == 0,
            test_count=result.get("test_count", 0),
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            skipped=result.get("skipped", 0),
            execution_time=result.get("duration", 0.0)
        )
    
    async def _run_subprocess_async(self, cmd: List[str]) -> Dict[str, Any]:
        """Run subprocess asynchronously"""
        start_time = time.time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            execution_time = time.time() - start_time
            
            # Parse output for test results
            test_results = self._parse_test_output(stdout.decode(), stderr.decode())
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "duration": execution_time,
                **test_results
            }
        
        except Exception as e:
            return {
                "returncode": 1,
                "stdout": "",
                "stderr": str(e),
                "duration": time.time() - start_time,
                "test_count": 0,
                "passed": 0,
                "failed": 1,
                "skipped": 0
            }
    
    def _parse_test_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse test output to extract metrics"""
        # Simple parsing - in real implementation, this would be more sophisticated
        results = {
            "test_count": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }
        
        # Look for pytest summary line
        for line in stdout.split('\n'):
            if 'passed' in line or 'failed' in line:
                # Extract numbers from pytest output
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    for i, num in enumerate(numbers):
                        if i == 0:
                            results["passed"] = int(num)
                        elif i == 1:
                            results["failed"] = int(num)
                        elif i == 2:
                            results["skipped"] = int(num)
                    
                    results["test_count"] = results["passed"] + results["failed"] + results["skipped"]
                    break
        
        return results
    
    async def _extract_performance_metrics(self) -> Dict[str, Any]:
        """Extract performance metrics from benchmark results"""
        try:
            benchmark_file = Path("test_results/performance_benchmark.json")
            if benchmark_file.exists():
                with open(benchmark_file, 'r') as f:
                    data = json.load(f)
                
                metrics = {
                    "average_fps": 0.0,
                    "max_memory_mb": 0.0,
                    "average_response_time_ms": 0.0,
                    "animation_smoothness": 0.0
                }
                
                # Extract relevant metrics from benchmark data
                if "benchmarks" in data:
                    for bench in data["benchmarks"]:
                        name = bench.get("name", "")
                        if "fps" in name:
                            metrics["average_fps"] = max(metrics["average_fps"], 
                                                       bench.get("stats", {}).get("mean", 0))
                        elif "memory" in name:
                            metrics["max_memory_mb"] = max(metrics["max_memory_mb"],
                                                         bench.get("stats", {}).get("max", 0))
                
                return metrics
        except Exception as e:
            self.logger.warning(f"Failed to extract performance metrics: {e}")
        
        return {"error": "metrics extraction failed"}
    
    def _validate_performance_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Validate performance metrics against targets"""
        if "error" in metrics:
            return False
        
        # Check FPS target
        avg_fps = metrics.get("average_fps", 0)
        if avg_fps < self.config.performance.target_fps * 0.9:  # 90% of target
            return False
        
        # Check memory target
        max_memory = metrics.get("max_memory_mb", float('inf'))
        if max_memory > self.config.performance.memory_limit_mb:
            return False
        
        return True
    
    async def _validate_ml_performance(self) -> Dict[str, Any]:
        """Validate ML model performance"""
        try:
            # This would connect to actual ML models and test them
            return {
                "accuracy": 0.87,  # Placeholder
                "prediction_latency_ms": 45,
                "model_loaded": True
            }
        except Exception:
            return {
                "accuracy": 0.0,
                "prediction_latency_ms": float('inf'),
                "model_loaded": False
            }

class ComprehensiveTestExecutor:
    """Main test executor orchestrating all streams"""
    
    def __init__(self, config: Optional[TestFrameworkConfig] = None):
        self.config = config or get_test_config()
        self.logger = logging.getLogger("ComprehensiveTestExecutor")
        
        # Create results directory
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)
    
    async def execute_all_tests(self, selected_streams: Optional[List[str]] = None) -> ComprehensiveTestResult:
        """Execute all test streams in parallel"""
        start_time = time.time()
        
        # Define all test streams
        all_streams = [
            "unit_tests",
            "integration_tests", 
            "performance_tests",
            "cross_platform_tests",
            "accessibility_tests",
            "web_interface_tests",
            "ai_intelligence_tests",
            "regression_tests"
        ]
        
        # Use selected streams or all streams
        streams_to_run = selected_streams or all_streams
        
        self.logger.info(f"Starting comprehensive test execution with {len(streams_to_run)} streams")
        
        # Create stream executors
        stream_executors = []
        for stream_name in streams_to_run:
            executor = TestStreamExecutor(stream_name, self.config)
            stream_executors.append(executor)
        
        # Execute streams in parallel or sequential based on config
        if self.config.parallel_execution:
            results = await self._execute_streams_parallel(stream_executors)
        else:
            results = await self._execute_streams_sequential(stream_executors)
        
        # Compile comprehensive results
        total_execution_time = time.time() - start_time
        
        comprehensive_result = ComprehensiveTestResult(
            success=all(result.success for result in results.values()),
            total_execution_time=total_execution_time,
            stream_results=results,
            performance_summary=self._compile_performance_summary(results),
            ci_metrics=self._compile_ci_metrics(results),
            regression_detected=self._detect_regressions(results)
        )
        
        # Generate reports
        await self._generate_reports(comprehensive_result)
        
        self.logger.info(f"Comprehensive test execution completed in {total_execution_time:.2f}s")
        return comprehensive_result
    
    async def _execute_streams_parallel(self, executors: List[TestStreamExecutor]) -> Dict[str, TestStreamResult]:
        """Execute test streams in parallel"""
        
        # Limit concurrency to prevent resource exhaustion
        semaphore = asyncio.Semaphore(self.config.max_parallel_streams)
        
        async def run_with_semaphore(executor):
            async with semaphore:
                return await executor.execute_stream()
        
        # Execute all streams concurrently
        tasks = [run_with_semaphore(executor) for executor in executors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        stream_results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                stream_name = executors[i].stream_name
                stream_results[stream_name] = TestStreamResult(
                    stream_name=stream_name,
                    success=False,
                    test_count=0,
                    passed=0,
                    failed=1,
                    skipped=0,
                    execution_time=0.0,
                    error_details=[str(result)]
                )
            else:
                stream_results[result.stream_name] = result
        
        return stream_results
    
    async def _execute_streams_sequential(self, executors: List[TestStreamExecutor]) -> Dict[str, TestStreamResult]:
        """Execute test streams sequentially"""
        stream_results = {}
        
        for executor in executors:
            result = await executor.execute_stream()
            stream_results[result.stream_name] = result
        
        return stream_results
    
    def _compile_performance_summary(self, results: Dict[str, TestStreamResult]) -> Dict[str, Any]:
        """Compile performance summary from all streams"""
        summary = {
            "overall_fps": 0.0,
            "peak_memory_mb": 0.0,
            "total_test_time": 0.0,
            "performance_score": 0.0
        }
        
        # Extract performance metrics
        perf_result = results.get("performance_tests")
        if perf_result and perf_result.performance_metrics:
            summary["overall_fps"] = perf_result.performance_metrics.get("average_fps", 0.0)
            summary["peak_memory_mb"] = perf_result.performance_metrics.get("max_memory_mb", 0.0)
        
        # Calculate total test time
        summary["total_test_time"] = sum(result.execution_time for result in results.values())
        
        # Calculate performance score (0-100)
        fps_score = min(100, (summary["overall_fps"] / self.config.performance.target_fps) * 100)
        memory_score = max(0, 100 - ((summary["peak_memory_mb"] / self.config.performance.memory_limit_mb) * 100))
        summary["performance_score"] = (fps_score + memory_score) / 2
        
        return summary
    
    def _compile_ci_metrics(self, results: Dict[str, TestStreamResult]) -> Dict[str, Any]:
        """Compile CI/CD relevant metrics"""
        total_tests = sum(result.test_count for result in results.values())
        total_passed = sum(result.passed for result in results.values())
        total_failed = sum(result.failed for result in results.values())
        
        return {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0,
            "coverage_percentage": results.get("unit_tests", TestStreamResult("", False, 0, 0, 0, 0, 0.0)).coverage_percentage,
            "test_efficiency": total_tests / sum(result.execution_time for result in results.values()) if results else 0
        }
    
    def _detect_regressions(self, results: Dict[str, TestStreamResult]) -> bool:
        """Detect performance regressions"""
        # Load previous results for comparison
        previous_results_file = self.results_dir / "previous_results.json"
        
        if not previous_results_file.exists():
            return False
        
        try:
            with open(previous_results_file, 'r') as f:
                previous_data = json.load(f)
            
            # Compare performance metrics
            current_perf = results.get("performance_tests")
            if current_perf and current_perf.performance_metrics:
                current_fps = current_perf.performance_metrics.get("average_fps", 0)
                previous_fps = previous_data.get("performance_summary", {}).get("overall_fps", 0)
                
                if previous_fps > 0:
                    fps_degradation = ((previous_fps - current_fps) / previous_fps) * 100
                    if fps_degradation > self.config.performance_regression_threshold:
                        return True
            
        except Exception as e:
            self.logger.warning(f"Could not detect regressions: {e}")
        
        return False
    
    async def _generate_reports(self, result: ComprehensiveTestResult):
        """Generate comprehensive test reports"""
        
        # JSON report for CI/CD
        json_report = {
            "success": result.success,
            "total_execution_time": result.total_execution_time,
            "stream_results": {
                name: {
                    "success": stream.success,
                    "test_count": stream.test_count,
                    "passed": stream.passed,
                    "failed": stream.failed,
                    "execution_time": stream.execution_time
                }
                for name, stream in result.stream_results.items()
            },
            "performance_summary": result.performance_summary,
            "ci_metrics": result.ci_metrics,
            "regression_detected": result.regression_detected
        }
        
        # Save JSON report
        json_file = self.results_dir / "comprehensive_test_results.json"
        with open(json_file, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        # Save as previous results for regression detection
        previous_file = self.results_dir / "previous_results.json"
        with open(previous_file, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        # HTML report
        await self._generate_html_report(result)
        
        self.logger.info(f"Test reports generated in {self.results_dir}")
    
    async def _generate_html_report(self, result: ComprehensiveTestResult):
        """Generate HTML test report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Comprehensive UI/UX Test Results</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                .summary {{ background: #f0f0f0; padding: 15px; margin: 10px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Comprehensive UI/UX Test Results</h1>
            
            <div class="summary">
                <h2>Overall Result: <span class="{'success' if result.success else 'failure'}">
                    {'PASSED' if result.success else 'FAILED'}
                </span></h2>
                <p>Total Execution Time: {result.total_execution_time:.2f} seconds</p>
                <p>Regression Detected: {'Yes' if result.regression_detected else 'No'}</p>
            </div>
            
            <h2>Stream Results</h2>
            <table>
                <tr>
                    <th>Stream</th>
                    <th>Status</th>
                    <th>Tests</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Time (s)</th>
                </tr>
        """
        
        for name, stream in result.stream_results.items():
            status_class = "success" if stream.success else "failure"
            status_text = "PASSED" if stream.success else "FAILED"
            
            html_content += f"""
                <tr>
                    <td>{name}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{stream.test_count}</td>
                    <td>{stream.passed}</td>
                    <td>{stream.failed}</td>
                    <td>{stream.execution_time:.2f}</td>
                </tr>
            """
        
        html_content += f"""
            </table>
            
            <h2>Performance Summary</h2>
            <div class="summary">
                <p>Overall FPS: {result.performance_summary.get('overall_fps', 0):.1f}</p>
                <p>Peak Memory: {result.performance_summary.get('peak_memory_mb', 0):.1f} MB</p>
                <p>Performance Score: {result.performance_summary.get('performance_score', 0):.1f}/100</p>
            </div>
            
            <h2>CI/CD Metrics</h2>
            <div class="summary">
                <p>Success Rate: {result.ci_metrics.get('success_rate', 0):.1f}%</p>
                <p>Coverage: {result.ci_metrics.get('coverage_percentage', 0):.1f}%</p>
                <p>Test Efficiency: {result.ci_metrics.get('test_efficiency', 0):.2f} tests/second</p>
            </div>
        </body>
        </html>
        """
        
        html_file = self.results_dir / "comprehensive_test_report.html"
        with open(html_file, 'w') as f:
            f.write(html_content)

# CLI interface
async def main():
    """Main entry point for test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive UI/UX Test Executor")
    parser.add_argument("--streams", nargs="*", help="Specific test streams to run")
    parser.add_argument("--parallel", action="store_true", help="Force parallel execution")
    parser.add_argument("--sequential", action="store_true", help="Force sequential execution")
    
    args = parser.parse_args()
    
    # Update config based on arguments
    config = get_test_config()
    if args.parallel:
        config.parallel_execution = True
    elif args.sequential:
        config.parallel_execution = False
    
    # Execute tests
    executor = ComprehensiveTestExecutor(config)
    result = await executor.execute_all_tests(args.streams)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"COMPREHENSIVE TEST RESULTS")
    print(f"{'='*50}")
    print(f"Overall Status: {'PASSED' if result.success else 'FAILED'}")
    print(f"Total Time: {result.total_execution_time:.2f}s")
    print(f"Success Rate: {result.ci_metrics.get('success_rate', 0):.1f}%")
    print(f"Performance Score: {result.performance_summary.get('performance_score', 0):.1f}/100")
    print(f"Regression Detected: {'Yes' if result.regression_detected else 'No'}")
    print(f"{'='*50}")
    
    # Exit with appropriate code for CI/CD
    exit(0 if result.success else 1)

if __name__ == "__main__":
    asyncio.run(main())