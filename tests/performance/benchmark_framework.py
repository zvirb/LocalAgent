"""
Performance Benchmarking Framework for LocalAgent
Comprehensive performance testing and analysis toolkit
"""

import asyncio
import time
import statistics
import json
import psutil
import tracemalloc
from typing import Dict, List, Any, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager
import concurrent.futures
from pathlib import Path

from app.llm_providers.base_provider import CompletionRequest, CompletionResponse
from tests.mocks.mock_provider import MockProvider, MockProviderFactory, MockScenario


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation"""
    operation: str
    duration: float
    memory_peak: int
    memory_current: int
    cpu_percent: float
    timestamp: datetime
    success: bool
    error: Optional[str] = None
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run"""
    name: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_duration: float
    avg_duration: float
    min_duration: float
    max_duration: float
    p50_duration: float
    p95_duration: float
    p99_duration: float
    throughput_ops_sec: float
    memory_peak: int
    memory_avg: int
    cpu_avg: float
    error_rate: float
    individual_metrics: List[PerformanceMetrics]
    summary: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Monitor system performance during operations"""
    
    def __init__(self, sample_interval: float = 0.1):
        self.sample_interval = sample_interval
        self.monitoring = False
        self.metrics: List[Dict[str, Any]] = []
        self._monitor_task = None
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.metrics = []
        tracemalloc.start()
        
        self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return summary"""
        if not self.monitoring:
            return {}
        
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Get final memory stats
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Calculate summary statistics
        if self.metrics:
            cpu_values = [m['cpu_percent'] for m in self.metrics]
            memory_values = [m['memory_mb'] for m in self.metrics]
            
            summary = {
                'duration': self.metrics[-1]['timestamp'] - self.metrics[0]['timestamp'],
                'samples': len(self.metrics),
                'cpu_avg': statistics.mean(cpu_values),
                'cpu_max': max(cpu_values),
                'memory_avg_mb': statistics.mean(memory_values),
                'memory_max_mb': max(memory_values),
                'memory_peak_tracemalloc': peak,
                'memory_current_tracemalloc': current
            }
        else:
            summary = {
                'duration': 0,
                'samples': 0,
                'memory_peak_tracemalloc': peak,
                'memory_current_tracemalloc': current
            }
        
        return summary
    
    async def _monitor_loop(self):
        """Internal monitoring loop"""
        process = psutil.Process()
        start_time = time.time()
        
        while self.monitoring:
            try:
                current_time = time.time() - start_time
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                self.metrics.append({
                    'timestamp': current_time,
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb
                })
                
                await asyncio.sleep(self.sample_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Monitoring error: {e}")
                break


class BenchmarkRunner:
    """Main benchmark execution engine"""
    
    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.monitor = PerformanceMonitor()
    
    async def run_benchmark(
        self,
        name: str,
        operation_func: Callable,
        iterations: int = 100,
        concurrency: int = 1,
        warmup_iterations: int = 10,
        **operation_kwargs
    ) -> BenchmarkResult:
        """Run a comprehensive benchmark"""
        
        print(f"Running benchmark: {name}")
        print(f"Iterations: {iterations}, Concurrency: {concurrency}, Warmup: {warmup_iterations}")
        
        # Warmup phase
        if warmup_iterations > 0:
            print("Warming up...")
            await self._run_warmup(operation_func, warmup_iterations, **operation_kwargs)
        
        # Main benchmark
        await self.monitor.start_monitoring()
        start_time = time.time()
        
        individual_metrics = []
        
        if concurrency == 1:
            # Sequential execution
            for i in range(iterations):
                metric = await self._run_single_operation(
                    f"{name}_seq_{i}",
                    operation_func,
                    **operation_kwargs
                )
                individual_metrics.append(metric)
        else:
            # Concurrent execution
            semaphore = asyncio.Semaphore(concurrency)
            tasks = []
            
            for i in range(iterations):
                task = self._run_single_operation_with_semaphore(
                    f"{name}_conc_{i}",
                    operation_func,
                    semaphore,
                    **operation_kwargs
                )
                tasks.append(task)
            
            individual_metrics = await asyncio.gather(*tasks)
        
        total_duration = time.time() - start_time
        monitor_summary = await self.monitor.stop_monitoring()
        
        # Calculate statistics
        result = self._calculate_benchmark_result(
            name, individual_metrics, total_duration, monitor_summary
        )
        
        # Save results
        await self._save_results(result)
        
        print(f"Benchmark completed: {result.throughput_ops_sec:.2f} ops/sec")
        return result
    
    async def _run_warmup(self, operation_func: Callable, iterations: int, **kwargs):
        """Run warmup iterations"""
        for _ in range(iterations):
            try:
                await operation_func(**kwargs)
            except Exception:
                pass  # Ignore warmup errors
    
    async def _run_single_operation(
        self, 
        operation_name: str,
        operation_func: Callable,
        **kwargs
    ) -> PerformanceMetrics:
        """Run a single operation and collect metrics"""
        
        # Get baseline metrics
        process = psutil.Process()
        cpu_before = process.cpu_percent()
        
        # Start memory tracking for this operation
        tracemalloc.start()
        
        start_time = time.time()
        success = True
        error = None
        custom_metrics = {}
        
        try:
            result = await operation_func(**kwargs)
            
            # Extract custom metrics if result is a dict
            if isinstance(result, dict) and 'metrics' in result:
                custom_metrics = result['metrics']
                
        except Exception as e:
            success = False
            error = str(e)
        
        duration = time.time() - start_time
        
        # Get final metrics
        memory_current, memory_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        cpu_after = process.cpu_percent()
        
        return PerformanceMetrics(
            operation=operation_name,
            duration=duration,
            memory_peak=memory_peak,
            memory_current=memory_current,
            cpu_percent=(cpu_before + cpu_after) / 2,
            timestamp=datetime.now(),
            success=success,
            error=error,
            custom_metrics=custom_metrics
        )
    
    async def _run_single_operation_with_semaphore(
        self,
        operation_name: str,
        operation_func: Callable,
        semaphore: asyncio.Semaphore,
        **kwargs
    ) -> PerformanceMetrics:
        """Run single operation with concurrency control"""
        async with semaphore:
            return await self._run_single_operation(operation_name, operation_func, **kwargs)
    
    def _calculate_benchmark_result(
        self,
        name: str,
        metrics: List[PerformanceMetrics],
        total_duration: float,
        monitor_summary: Dict[str, Any]
    ) -> BenchmarkResult:
        """Calculate comprehensive benchmark statistics"""
        
        successful_metrics = [m for m in metrics if m.success]
        failed_metrics = [m for m in metrics if not m.success]
        
        if successful_metrics:
            durations = [m.duration for m in successful_metrics]
            durations.sort()
            
            n = len(durations)
            p50_idx = int(n * 0.5)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            
            avg_duration = statistics.mean(durations)
            throughput = len(successful_metrics) / total_duration if total_duration > 0 else 0
            
            memory_peaks = [m.memory_peak for m in successful_metrics]
            cpu_values = [m.cpu_percent for m in successful_metrics]
            
        else:
            durations = [0]
            avg_duration = 0
            throughput = 0
            memory_peaks = [0]
            cpu_values = [0]
            p50_idx = p95_idx = p99_idx = 0
        
        return BenchmarkResult(
            name=name,
            total_operations=len(metrics),
            successful_operations=len(successful_metrics),
            failed_operations=len(failed_metrics),
            total_duration=total_duration,
            avg_duration=avg_duration,
            min_duration=min(durations) if durations else 0,
            max_duration=max(durations) if durations else 0,
            p50_duration=durations[p50_idx] if durations else 0,
            p95_duration=durations[p95_idx] if durations else 0,
            p99_duration=durations[p99_idx] if durations else 0,
            throughput_ops_sec=throughput,
            memory_peak=max(memory_peaks) if memory_peaks else 0,
            memory_avg=int(statistics.mean(memory_peaks)) if memory_peaks else 0,
            cpu_avg=statistics.mean(cpu_values) if cpu_values else 0,
            error_rate=len(failed_metrics) / len(metrics) if metrics else 0,
            individual_metrics=metrics,
            summary=monitor_summary
        )
    
    async def _save_results(self, result: BenchmarkResult):
        """Save benchmark results to disk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.name}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Convert to serializable format
        result_dict = {
            'name': result.name,
            'timestamp': timestamp,
            'summary': {
                'total_operations': result.total_operations,
                'successful_operations': result.successful_operations,
                'failed_operations': result.failed_operations,
                'total_duration': result.total_duration,
                'avg_duration': result.avg_duration,
                'min_duration': result.min_duration,
                'max_duration': result.max_duration,
                'p50_duration': result.p50_duration,
                'p95_duration': result.p95_duration,
                'p99_duration': result.p99_duration,
                'throughput_ops_sec': result.throughput_ops_sec,
                'memory_peak': result.memory_peak,
                'memory_avg': result.memory_avg,
                'cpu_avg': result.cpu_avg,
                'error_rate': result.error_rate
            },
            'monitor_summary': result.summary,
            'individual_metrics': [
                {
                    'operation': m.operation,
                    'duration': m.duration,
                    'memory_peak': m.memory_peak,
                    'memory_current': m.memory_current,
                    'cpu_percent': m.cpu_percent,
                    'timestamp': m.timestamp.isoformat(),
                    'success': m.success,
                    'error': m.error,
                    'custom_metrics': m.custom_metrics
                }
                for m in result.individual_metrics
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(result_dict, f, indent=2)
        
        print(f"Results saved to: {filepath}")


class ProviderBenchmarkSuite:
    """Benchmark suite specifically for LLM providers"""
    
    def __init__(self):
        self.runner = BenchmarkRunner("provider_benchmarks")
    
    async def benchmark_provider_initialization(
        self, 
        provider_factory: Callable,
        iterations: int = 50
    ) -> BenchmarkResult:
        """Benchmark provider initialization performance"""
        
        async def init_operation():
            provider = provider_factory()
            success = await provider.initialize()
            return {'metrics': {'success': success}}
        
        return await self.runner.run_benchmark(
            "provider_initialization",
            init_operation,
            iterations=iterations,
            warmup_iterations=5
        )
    
    async def benchmark_completion_latency(
        self,
        provider: MockProvider,
        iterations: int = 100,
        concurrency: int = 1
    ) -> BenchmarkResult:
        """Benchmark completion latency"""
        
        async def completion_operation():
            request = CompletionRequest(
                messages=[{"role": "user", "content": "Benchmark test message"}],
                model="test-model"
            )
            response = await provider.complete(request)
            return {
                'metrics': {
                    'response_length': len(response.content),
                    'usage_tokens': response.usage.get('total_tokens', 0)
                }
            }
        
        return await self.runner.run_benchmark(
            "completion_latency",
            completion_operation,
            iterations=iterations,
            concurrency=concurrency,
            warmup_iterations=10
        )
    
    async def benchmark_streaming_performance(
        self,
        provider: MockProvider,
        iterations: int = 50
    ) -> BenchmarkResult:
        """Benchmark streaming completion performance"""
        
        async def streaming_operation():
            request = CompletionRequest(
                messages=[{"role": "user", "content": "Stream benchmark test"}],
                model="test-model",
                stream=True
            )
            
            chunks = []
            chunk_count = 0
            first_chunk_time = None
            
            start_time = time.time()
            async for chunk in provider.stream_complete(request):
                if first_chunk_time is None:
                    first_chunk_time = time.time() - start_time
                chunks.append(chunk)
                chunk_count += 1
            
            total_time = time.time() - start_time
            total_length = sum(len(chunk) for chunk in chunks)
            
            return {
                'metrics': {
                    'chunk_count': chunk_count,
                    'total_length': total_length,
                    'first_chunk_latency': first_chunk_time or 0,
                    'avg_chunk_size': total_length / chunk_count if chunk_count > 0 else 0
                }
            }
        
        return await self.runner.run_benchmark(
            "streaming_performance",
            streaming_operation,
            iterations=iterations,
            warmup_iterations=5
        )
    
    async def benchmark_concurrent_requests(
        self,
        provider: MockProvider,
        requests_per_batch: int = 10,
        batches: int = 10,
        max_concurrency: int = 5
    ) -> BenchmarkResult:
        """Benchmark concurrent request handling"""
        
        async def concurrent_batch_operation():
            requests = [
                CompletionRequest(
                    messages=[{"role": "user", "content": f"Concurrent request {i}"}],
                    model="test-model"
                )
                for i in range(requests_per_batch)
            ]
            
            # Limit concurrency
            semaphore = asyncio.Semaphore(max_concurrency)
            
            async def single_request(req):
                async with semaphore:
                    return await provider.complete(req)
            
            start_time = time.time()
            responses = await asyncio.gather(*[
                single_request(req) for req in requests
            ])
            batch_duration = time.time() - start_time
            
            successful_responses = [r for r in responses if r]
            
            return {
                'metrics': {
                    'batch_size': requests_per_batch,
                    'successful_requests': len(successful_responses),
                    'batch_duration': batch_duration,
                    'requests_per_second': len(successful_responses) / batch_duration if batch_duration > 0 else 0
                }
            }
        
        return await self.runner.run_benchmark(
            "concurrent_requests",
            concurrent_batch_operation,
            iterations=batches,
            warmup_iterations=2
        )
    
    async def benchmark_memory_efficiency(
        self,
        provider: MockProvider,
        iterations: int = 100,
        message_sizes: List[int] = None
    ) -> BenchmarkResult:
        """Benchmark memory efficiency with different message sizes"""
        
        if message_sizes is None:
            message_sizes = [100, 1000, 5000]  # Character counts
        
        async def memory_operation():
            # Test with different message sizes
            results = []
            
            for size in message_sizes:
                message = "x" * size  # Create message of specific size
                request = CompletionRequest(
                    messages=[{"role": "user", "content": message}],
                    model="test-model"
                )
                
                tracemalloc.start()
                response = await provider.complete(request)
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                results.append({
                    'message_size': size,
                    'memory_peak': peak,
                    'memory_current': current,
                    'response_length': len(response.content)
                })
            
            return {
                'metrics': {
                    'size_tests': results,
                    'total_peak_memory': sum(r['memory_peak'] for r in results),
                    'avg_memory_per_char': sum(r['memory_peak'] / r['message_size'] for r in results) / len(results)
                }
            }
        
        return await self.runner.run_benchmark(
            "memory_efficiency",
            memory_operation,
            iterations=iterations,
            warmup_iterations=5
        )


class BenchmarkReportGenerator:
    """Generate comprehensive benchmark reports"""
    
    def __init__(self, results_dir: str = "benchmark_results"):
        self.results_dir = Path(results_dir)
    
    def generate_html_report(self, results: List[BenchmarkResult]) -> str:
        """Generate HTML benchmark report"""
        
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>LocalAgent Performance Benchmark Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .benchmark { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .metric { background: #f8f9fa; padding: 10px; border-radius: 3px; }
        .metric-value { font-size: 1.2em; font-weight: bold; color: #2c3e50; }
        .error { color: #e74c3c; }
        .success { color: #27ae60; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>LocalAgent Performance Benchmark Report</h1>
        <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </div>
"""
        
        for result in results:
            html += f"""
    <div class="benchmark">
        <h2>{result.name}</h2>
        <div class="metrics">
            <div class="metric">
                <div>Operations</div>
                <div class="metric-value">{result.successful_operations}/{result.total_operations}</div>
            </div>
            <div class="metric">
                <div>Throughput</div>
                <div class="metric-value">{result.throughput_ops_sec:.2f} ops/sec</div>
            </div>
            <div class="metric">
                <div>Avg Duration</div>
                <div class="metric-value">{result.avg_duration*1000:.2f} ms</div>
            </div>
            <div class="metric">
                <div>P95 Duration</div>
                <div class="metric-value">{result.p95_duration*1000:.2f} ms</div>
            </div>
            <div class="metric">
                <div>Memory Peak</div>
                <div class="metric-value">{result.memory_peak/1024/1024:.2f} MB</div>
            </div>
            <div class="metric">
                <div>Error Rate</div>
                <div class="metric-value {'error' if result.error_rate > 0 else 'success'}">{result.error_rate*100:.2f}%</div>
            </div>
        </div>
        
        <h3>Duration Distribution</h3>
        <table>
            <tr><th>Metric</th><th>Value (ms)</th></tr>
            <tr><td>Minimum</td><td>{result.min_duration*1000:.2f}</td></tr>
            <tr><td>P50 (Median)</td><td>{result.p50_duration*1000:.2f}</td></tr>
            <tr><td>P95</td><td>{result.p95_duration*1000:.2f}</td></tr>
            <tr><td>P99</td><td>{result.p99_duration*1000:.2f}</td></tr>
            <tr><td>Maximum</td><td>{result.max_duration*1000:.2f}</td></tr>
        </table>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        report_path = self.results_dir / "benchmark_report.html"
        with open(report_path, 'w') as f:
            f.write(html)
        
        return str(report_path)
    
    def load_results(self, pattern: str = "*.json") -> List[BenchmarkResult]:
        """Load benchmark results from JSON files"""
        results = []
        
        for filepath in self.results_dir.glob(pattern):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Convert back to BenchmarkResult
                individual_metrics = []
                for m_data in data.get('individual_metrics', []):
                    metric = PerformanceMetrics(
                        operation=m_data['operation'],
                        duration=m_data['duration'],
                        memory_peak=m_data['memory_peak'],
                        memory_current=m_data['memory_current'],
                        cpu_percent=m_data['cpu_percent'],
                        timestamp=datetime.fromisoformat(m_data['timestamp']),
                        success=m_data['success'],
                        error=m_data.get('error'),
                        custom_metrics=m_data.get('custom_metrics', {})
                    )
                    individual_metrics.append(metric)
                
                summary_data = data['summary']
                result = BenchmarkResult(
                    name=data['name'],
                    total_operations=summary_data['total_operations'],
                    successful_operations=summary_data['successful_operations'],
                    failed_operations=summary_data['failed_operations'],
                    total_duration=summary_data['total_duration'],
                    avg_duration=summary_data['avg_duration'],
                    min_duration=summary_data['min_duration'],
                    max_duration=summary_data['max_duration'],
                    p50_duration=summary_data['p50_duration'],
                    p95_duration=summary_data['p95_duration'],
                    p99_duration=summary_data['p99_duration'],
                    throughput_ops_sec=summary_data['throughput_ops_sec'],
                    memory_peak=summary_data['memory_peak'],
                    memory_avg=summary_data['memory_avg'],
                    cpu_avg=summary_data['cpu_avg'],
                    error_rate=summary_data['error_rate'],
                    individual_metrics=individual_metrics,
                    summary=data.get('monitor_summary', {})
                )
                
                results.append(result)
                
            except Exception as e:
                print(f"Error loading {filepath}: {e}")
        
        return results