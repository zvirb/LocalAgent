#!/usr/bin/env python3
"""
Comprehensive Performance Testing Suite for LocalAgent
======================================================

This script runs comprehensive performance tests including:
- Memory leak detection
- Load testing scenarios  
- Response time measurements
- Throughput analysis
- Resource optimization validation
- LLM provider performance benchmarking
"""

import asyncio
import concurrent.futures
import gc
import json
import os
import psutil
import statistics
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.performance.benchmark_framework import (
    BenchmarkRunner, 
    ProviderBenchmarkSuite,
    BenchmarkReportGenerator,
    PerformanceMonitor
)
from tests.mocks.mock_provider import MockProviderFactory


@dataclass
class LoadTestResult:
    """Result of a load testing scenario"""
    test_name: str
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    memory_peak_mb: float
    memory_growth_mb: float
    cpu_peak_percent: float
    cpu_avg_percent: float
    error_rate: float
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


class ComprehensivePerformanceTester:
    """Comprehensive performance testing suite"""
    
    def __init__(self, output_dir: str = "performance_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = []
        self.system_info = self._get_system_info()
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for context"""
        return {
            'cpu_count': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total_gb': psutil.virtual_memory().total / 1024**3,
            'disk_space_gb': psutil.disk_usage('.').total / 1024**3,
            'python_version': sys.version,
            'timestamp': datetime.now().isoformat()
        }
    
    async def run_memory_leak_tests(self):
        """Run comprehensive memory leak detection tests"""
        print("Running memory leak detection tests...")
        
        results = []
        
        # Test 1: Provider creation/destruction cycles
        memory_result = await self._test_provider_lifecycle_memory()
        results.append(memory_result)
        
        # Test 2: Concurrent request memory behavior
        concurrent_memory_result = await self._test_concurrent_memory_usage()
        results.append(concurrent_memory_result)
        
        # Test 3: Long-running process memory stability
        longrun_result = await self._test_longrunning_memory_stability()
        results.append(longrun_result)
        
        return results
    
    async def _test_provider_lifecycle_memory(self) -> LoadTestResult:
        """Test memory usage during provider creation/destruction"""
        tracemalloc.start()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        successful_cycles = 0
        failed_cycles = 0
        
        try:
            for i in range(50):  # Create/destroy 50 provider instances
                try:
                    provider = MockProviderFactory.create_fast_provider()
                    await provider.initialize()
                    # Simulate some work
                    await asyncio.sleep(0.01)  
                    # Provider should be garbage collected when going out of scope
                    del provider
                    successful_cycles += 1
                    
                    if i % 10 == 0:  # Force GC every 10 cycles
                        gc.collect()
                        
                except Exception as e:
                    failed_cycles += 1
                    print(f"Provider cycle {i} failed: {e}")
        
        except Exception as e:
            print(f"Provider lifecycle test failed: {e}")
        
        # Final measurements
        duration = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return LoadTestResult(
            test_name="provider_lifecycle_memory",
            duration=duration,
            total_requests=successful_cycles + failed_cycles,
            successful_requests=successful_cycles,
            failed_requests=failed_cycles,
            requests_per_second=successful_cycles / duration if duration > 0 else 0,
            avg_response_time=duration / successful_cycles if successful_cycles > 0 else 0,
            p95_response_time=0,  # Not applicable for this test
            p99_response_time=0,  # Not applicable for this test
            memory_peak_mb=peak / 1024 / 1024,
            memory_growth_mb=final_memory - initial_memory,
            cpu_peak_percent=0,  # Not measured in this simple test
            cpu_avg_percent=0,   # Not measured in this simple test
            error_rate=failed_cycles / (successful_cycles + failed_cycles) if (successful_cycles + failed_cycles) > 0 else 0
        )
    
    async def _test_concurrent_memory_usage(self) -> LoadTestResult:
        """Test memory usage under concurrent load"""
        tracemalloc.start()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        provider = MockProviderFactory.create_fast_provider()
        await provider.initialize()
        
        start_time = time.time()
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        async def make_request():
            nonlocal successful_requests, failed_requests
            try:
                req_start = time.time()
                from app.llm_providers.base_provider import CompletionRequest
                request = CompletionRequest(
                    messages=[{"role": "user", "content": "Concurrent test"}],
                    model="test-model"
                )
                response = await provider.complete(request)
                req_end = time.time()
                response_times.append(req_end - req_start)
                successful_requests += 1
            except Exception as e:
                failed_requests += 1
                print(f"Concurrent request failed: {e}")
        
        # Run 100 concurrent requests in batches of 10
        for batch in range(10):
            tasks = [make_request() for _ in range(10)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Small delay between batches to avoid overwhelming
            await asyncio.sleep(0.1)
        
        duration = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate response time percentiles
        response_times.sort()
        n = len(response_times)
        p95_idx = int(n * 0.95) if n > 0 else 0
        p99_idx = int(n * 0.99) if n > 0 else 0
        
        return LoadTestResult(
            test_name="concurrent_memory_usage",
            duration=duration,
            total_requests=successful_requests + failed_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=successful_requests / duration if duration > 0 else 0,
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            p95_response_time=response_times[p95_idx] if response_times else 0,
            p99_response_time=response_times[p99_idx] if response_times else 0,
            memory_peak_mb=peak / 1024 / 1024,
            memory_growth_mb=final_memory - initial_memory,
            cpu_peak_percent=0,
            cpu_avg_percent=0,
            error_rate=failed_requests / (successful_requests + failed_requests) if (successful_requests + failed_requests) > 0 else 0
        )
    
    async def _test_longrunning_memory_stability(self) -> LoadTestResult:
        """Test memory stability over longer periods"""
        tracemalloc.start()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        provider = MockProviderFactory.create_fast_provider()
        await provider.initialize()
        
        start_time = time.time()
        successful_requests = 0
        failed_requests = 0
        memory_measurements = []
        
        # Run for 30 seconds with requests every 0.1 seconds
        end_time = start_time + 30  
        
        while time.time() < end_time:
            try:
                from app.llm_providers.base_provider import CompletionRequest
                request = CompletionRequest(
                    messages=[{"role": "user", "content": "Long running test"}],
                    model="test-model"
                )
                await provider.complete(request)
                successful_requests += 1
                
                # Take memory measurement
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_measurements.append(current_memory)
                
                # Force GC periodically
                if successful_requests % 50 == 0:
                    gc.collect()
                
            except Exception as e:
                failed_requests += 1
                
            await asyncio.sleep(0.1)
        
        duration = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Analyze memory trend
        memory_trend = "stable"
        if len(memory_measurements) > 10:
            early_avg = statistics.mean(memory_measurements[:10])
            late_avg = statistics.mean(memory_measurements[-10:])
            if late_avg > early_avg * 1.1:
                memory_trend = "increasing"
            elif late_avg < early_avg * 0.9:
                memory_trend = "decreasing"
        
        return LoadTestResult(
            test_name="longrunning_memory_stability",
            duration=duration,
            total_requests=successful_requests + failed_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=successful_requests / duration if duration > 0 else 0,
            avg_response_time=0.1,  # Approximate based on sleep
            p95_response_time=0.15,  # Estimated
            p99_response_time=0.2,   # Estimated
            memory_peak_mb=peak / 1024 / 1024,
            memory_growth_mb=final_memory - initial_memory,
            cpu_peak_percent=0,
            cpu_avg_percent=0,
            error_rate=failed_requests / (successful_requests + failed_requests) if (successful_requests + failed_requests) > 0 else 0,
            custom_metrics={
                'memory_trend': memory_trend,
                'memory_measurements_count': len(memory_measurements),
                'memory_variance': statistics.variance(memory_measurements) if len(memory_measurements) > 1 else 0
            }
        )
    
    async def run_load_testing_scenarios(self):
        """Run various load testing scenarios"""
        print("Running load testing scenarios...")
        
        scenarios = [
            ("light_load", 50, 1),      # 50 requests, 1 concurrent
            ("moderate_load", 100, 5),   # 100 requests, 5 concurrent  
            ("heavy_load", 200, 10),     # 200 requests, 10 concurrent
            ("stress_load", 500, 20),    # 500 requests, 20 concurrent
        ]
        
        results = []
        benchmark_suite = ProviderBenchmarkSuite()
        
        for scenario_name, total_requests, concurrency in scenarios:
            print(f"Running {scenario_name}: {total_requests} requests with {concurrency} concurrency")
            
            provider = MockProviderFactory.create_fast_provider()
            
            try:
                result = await benchmark_suite.benchmark_completion_latency(
                    provider,
                    iterations=total_requests,
                    concurrency=concurrency
                )
                
                load_result = LoadTestResult(
                    test_name=scenario_name,
                    duration=result.total_duration,
                    total_requests=result.total_operations,
                    successful_requests=result.successful_operations,
                    failed_requests=result.failed_operations,
                    requests_per_second=result.throughput_ops_sec,
                    avg_response_time=result.avg_duration,
                    p95_response_time=result.p95_duration,
                    p99_response_time=result.p99_duration,
                    memory_peak_mb=result.memory_peak / 1024 / 1024,
                    memory_growth_mb=0,  # Not tracked in benchmark framework
                    cpu_peak_percent=0,  # Not tracked in benchmark framework  
                    cpu_avg_percent=result.cpu_avg,
                    error_rate=result.error_rate
                )
                
                results.append(load_result)
                
            except Exception as e:
                print(f"Load test {scenario_name} failed: {e}")
        
        return results
    
    def generate_performance_report(self, memory_results: List[LoadTestResult], load_results: List[LoadTestResult]):
        """Generate comprehensive performance report"""
        
        report = {
            'system_info': self.system_info,
            'test_summary': {
                'total_tests': len(memory_results) + len(load_results),
                'memory_tests': len(memory_results),
                'load_tests': len(load_results),
                'timestamp': datetime.now().isoformat()
            },
            'memory_test_results': [
                {
                    'test_name': r.test_name,
                    'duration': r.duration,
                    'memory_growth_mb': r.memory_growth_mb,
                    'memory_peak_mb': r.memory_peak_mb,
                    'successful_requests': r.successful_requests,
                    'error_rate': r.error_rate,
                    'custom_metrics': r.custom_metrics
                }
                for r in memory_results
            ],
            'load_test_results': [
                {
                    'test_name': r.test_name,
                    'requests_per_second': r.requests_per_second,
                    'avg_response_time_ms': r.avg_response_time * 1000,
                    'p95_response_time_ms': r.p95_response_time * 1000,
                    'p99_response_time_ms': r.p99_response_time * 1000,
                    'error_rate': r.error_rate,
                    'total_requests': r.total_requests
                }
                for r in load_results
            ],
            'performance_analysis': self._analyze_performance_results(memory_results, load_results),
            'recommendations': self._generate_recommendations(memory_results, load_results)
        }
        
        # Save to JSON
        report_file = self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Generate HTML report  
        html_report = self._generate_html_report(report)
        html_file = self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, 'w') as f:
            f.write(html_report)
        
        print(f"Performance report saved to: {report_file}")
        print(f"HTML report saved to: {html_file}")
        
        return report
    
    def _analyze_performance_results(self, memory_results: List[LoadTestResult], load_results: List[LoadTestResult]) -> Dict[str, Any]:
        """Analyze performance test results"""
        
        analysis = {}
        
        # Memory analysis
        if memory_results:
            memory_growths = [r.memory_growth_mb for r in memory_results]
            memory_peaks = [r.memory_peak_mb for r in memory_results]
            
            analysis['memory_analysis'] = {
                'max_memory_growth_mb': max(memory_growths),
                'avg_memory_growth_mb': statistics.mean(memory_growths),
                'max_memory_peak_mb': max(memory_peaks),
                'memory_leak_risk': 'high' if max(memory_growths) > 50 else 'low'
            }
        
        # Load test analysis
        if load_results:
            throughputs = [r.requests_per_second for r in load_results if r.requests_per_second > 0]
            response_times = [r.avg_response_time for r in load_results]
            error_rates = [r.error_rate for r in load_results]
            
            analysis['load_analysis'] = {
                'max_throughput_ops_sec': max(throughputs) if throughputs else 0,
                'avg_throughput_ops_sec': statistics.mean(throughputs) if throughputs else 0,
                'min_response_time_ms': min(response_times) * 1000 if response_times else 0,
                'max_response_time_ms': max(response_times) * 1000 if response_times else 0,
                'max_error_rate': max(error_rates) if error_rates else 0,
                'performance_grade': self._calculate_performance_grade(throughputs, response_times, error_rates)
            }
        
        return analysis
    
    def _calculate_performance_grade(self, throughputs: List[float], response_times: List[float], error_rates: List[float]) -> str:
        """Calculate overall performance grade"""
        if not throughputs or not response_times:
            return "insufficient_data"
        
        max_throughput = max(throughputs)
        avg_response_time = statistics.mean(response_times)
        max_error_rate = max(error_rates) if error_rates else 0
        
        score = 0
        
        # Throughput scoring
        if max_throughput >= 100:
            score += 3
        elif max_throughput >= 50:
            score += 2
        elif max_throughput >= 10:
            score += 1
        
        # Response time scoring  
        if avg_response_time <= 0.01:  # 10ms
            score += 3
        elif avg_response_time <= 0.05:  # 50ms
            score += 2
        elif avg_response_time <= 0.1:   # 100ms
            score += 1
        
        # Error rate scoring
        if max_error_rate == 0:
            score += 2
        elif max_error_rate <= 0.01:  # 1%
            score += 1
        
        if score >= 7:
            return "excellent"
        elif score >= 5:
            return "good"
        elif score >= 3:
            return "fair"
        else:
            return "poor"
    
    def _generate_recommendations(self, memory_results: List[LoadTestResult], load_results: List[LoadTestResult]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Memory recommendations
        if memory_results:
            max_growth = max(r.memory_growth_mb for r in memory_results)
            if max_growth > 50:
                recommendations.append("HIGH: Memory growth exceeds 50MB - investigate potential memory leaks")
            elif max_growth > 20:
                recommendations.append("MEDIUM: Memory growth is moderate - consider more frequent garbage collection")
        
        # Load test recommendations  
        if load_results:
            max_throughput = max(r.requests_per_second for r in load_results if r.requests_per_second > 0)
            max_error_rate = max(r.error_rate for r in load_results)
            
            if max_throughput < 10:
                recommendations.append("HIGH: Low throughput detected - optimize request processing pipeline")
            elif max_throughput < 50:
                recommendations.append("MEDIUM: Moderate throughput - consider async optimization")
            
            if max_error_rate > 0.05:  # 5%
                recommendations.append("HIGH: High error rate under load - improve error handling and resilience")
            elif max_error_rate > 0.01:  # 1%
                recommendations.append("MEDIUM: Some errors under load - review error scenarios")
        
        if not recommendations:
            recommendations.append("GOOD: No critical performance issues detected")
        
        return recommendations
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML performance report"""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LocalAgent Comprehensive Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .section {{ background: white; margin: 20px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #ecf0f1; border-radius: 5px; min-width: 150px; text-align: center; }}
        .metric-value {{ font-size: 1.4em; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ font-size: 0.9em; color: #7f8c8d; margin-top: 5px; }}
        .grade-excellent {{ background-color: #2ecc71; color: white; }}
        .grade-good {{ background-color: #3498db; color: white; }}
        .grade-fair {{ background-color: #f39c12; color: white; }}
        .grade-poor {{ background-color: #e74c3c; color: white; }}
        .recommendations {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; }}
        .recommendation {{ margin: 5px 0; padding: 5px; }}
        .high {{ border-left: 3px solid #dc3545; }}
        .medium {{ border-left: 3px solid #ffc107; }}
        .good {{ border-left: 3px solid #28a745; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LocalAgent Comprehensive Performance Report</h1>
        <p>Generated on: {report['test_summary']['timestamp']}</p>
        <p>System: {report['system_info']['cpu_count']} cores, {report['system_info']['memory_total_gb']:.1f} GB RAM</p>
    </div>
"""
        
        # Performance Analysis Section
        if 'performance_analysis' in report:
            analysis = report['performance_analysis']
            html += """
    <div class="section">
        <h2>Performance Analysis</h2>"""
            
            if 'load_analysis' in analysis:
                load_analysis = analysis['load_analysis']
                grade_class = f"grade-{load_analysis.get('performance_grade', 'fair')}"
                
                html += f"""
        <div class="metric {grade_class}">
            <div class="metric-value">{load_analysis.get('performance_grade', 'unknown').title()}</div>
            <div class="metric-label">Overall Grade</div>
        </div>
        <div class="metric">
            <div class="metric-value">{load_analysis.get('max_throughput_ops_sec', 0):.1f}</div>
            <div class="metric-label">Peak Throughput (ops/sec)</div>
        </div>
        <div class="metric">
            <div class="metric-value">{load_analysis.get('min_response_time_ms', 0):.1f}ms</div>
            <div class="metric-label">Best Response Time</div>
        </div>"""
            
            if 'memory_analysis' in analysis:
                memory_analysis = analysis['memory_analysis']
                html += f"""
        <div class="metric">
            <div class="metric-value">{memory_analysis.get('max_memory_peak_mb', 0):.1f}MB</div>
            <div class="metric-label">Peak Memory Usage</div>
        </div>
        <div class="metric">
            <div class="metric-value">{memory_analysis.get('memory_leak_risk', 'unknown').title()}</div>
            <div class="metric-label">Memory Leak Risk</div>
        </div>"""
            
            html += """
    </div>"""
        
        # Recommendations Section
        if 'recommendations' in report:
            html += """
    <div class="section">
        <h2>Performance Recommendations</h2>
        <div class="recommendations">"""
            
            for rec in report['recommendations']:
                if rec.startswith('HIGH'):
                    css_class = 'high'
                elif rec.startswith('MEDIUM'):
                    css_class = 'medium'
                else:
                    css_class = 'good'
                
                html += f'<div class="recommendation {css_class}">{rec}</div>'
            
            html += """
        </div>
    </div>"""
        
        # Load Test Results Table
        if 'load_test_results' in report:
            html += """
    <div class="section">
        <h2>Load Test Results</h2>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Requests/sec</th>
                <th>Avg Response (ms)</th>
                <th>P95 Response (ms)</th>
                <th>Error Rate</th>
                <th>Total Requests</th>
            </tr>"""
            
            for result in report['load_test_results']:
                html += f"""
            <tr>
                <td>{result['test_name']}</td>
                <td>{result['requests_per_second']:.2f}</td>
                <td>{result['avg_response_time_ms']:.2f}</td>
                <td>{result['p95_response_time_ms']:.2f}</td>
                <td>{result['error_rate']:.2%}</td>
                <td>{result['total_requests']}</td>
            </tr>"""
            
            html += """
        </table>
    </div>"""
        
        # Memory Test Results Table
        if 'memory_test_results' in report:
            html += """
    <div class="section">
        <h2>Memory Test Results</h2>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Duration (s)</th>
                <th>Memory Growth (MB)</th>
                <th>Memory Peak (MB)</th>
                <th>Successful Requests</th>
                <th>Error Rate</th>
            </tr>"""
            
            for result in report['memory_test_results']:
                html += f"""
            <tr>
                <td>{result['test_name']}</td>
                <td>{result['duration']:.2f}</td>
                <td>{result['memory_growth_mb']:.2f}</td>
                <td>{result['memory_peak_mb']:.2f}</td>
                <td>{result['successful_requests']}</td>
                <td>{result['error_rate']:.2%}</td>
            </tr>"""
            
            html += """
        </table>
    </div>"""
        
        html += """
</body>
</html>"""
        
        return html


async def main():
    """Main performance testing execution"""
    print("=== LocalAgent Comprehensive Performance Testing ===")
    print()
    
    tester = ComprehensivePerformanceTester()
    
    try:
        # Run memory leak tests
        memory_results = await tester.run_memory_leak_tests()
        print(f"Completed {len(memory_results)} memory tests")
        
        # Run load testing scenarios
        load_results = await tester.run_load_testing_scenarios()
        print(f"Completed {len(load_results)} load tests")
        
        # Generate comprehensive report
        report = tester.generate_performance_report(memory_results, load_results)
        
        # Print summary
        print("\n=== Performance Test Summary ===")
        print(f"Total tests completed: {len(memory_results) + len(load_results)}")
        
        if 'performance_analysis' in report and 'load_analysis' in report['performance_analysis']:
            load_analysis = report['performance_analysis']['load_analysis']
            print(f"Performance Grade: {load_analysis.get('performance_grade', 'unknown').title()}")
            print(f"Peak Throughput: {load_analysis.get('max_throughput_ops_sec', 0):.1f} ops/sec")
        
        if 'recommendations' in report:
            print(f"Recommendations: {len(report['recommendations'])}")
            for rec in report['recommendations'][:3]:  # Show first 3
                print(f"  - {rec}")
        
        print(f"\nDetailed reports saved to: {tester.output_dir}")
        
    except Exception as e:
        print(f"Performance testing failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())