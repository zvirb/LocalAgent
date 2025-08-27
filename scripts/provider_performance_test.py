#!/usr/bin/env python3
"""
LLM Provider Performance Testing Suite
=====================================

Tests performance characteristics of different LLM providers including:
- Initialization latency
- Response time distribution  
- Throughput under load
- Memory usage patterns
- Error handling performance
- Provider comparison benchmarks
"""

import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Mock provider imports for testing
from tests.mocks.mock_provider import MockProviderFactory, MockScenario


@dataclass
class ProviderPerformanceResult:
    """Performance test result for a provider"""
    provider_name: str
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    throughput_rps: float
    error_rate: float
    memory_peak_mb: float
    custom_metrics: Dict[str, Any]


class ProviderPerformanceTester:
    """Comprehensive provider performance testing"""
    
    def __init__(self, output_dir: str = "provider_performance_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = []
    
    async def test_provider_initialization_performance(self) -> List[ProviderPerformanceResult]:
        """Test provider initialization performance across different provider types"""
        print("Testing provider initialization performance...")
        
        providers_to_test = [
            ("fast_provider", MockProviderFactory.create_fast_provider),
            ("slow_provider", MockProviderFactory.create_slow_provider),
            ("failing_provider", lambda: MockProviderFactory.create_failing_provider("timeout")),
        ]
        
        results = []
        
        for provider_name, provider_factory in providers_to_test:
            print(f"  Testing {provider_name} initialization...")
            
            response_times = []
            successful_inits = 0
            failed_inits = 0
            
            for i in range(20):  # Test 20 initializations
                try:
                    start_time = time.time()
                    provider = provider_factory()
                    init_result = await provider.initialize()
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    response_times.append(response_time)
                    
                    if init_result:
                        successful_inits += 1
                    else:
                        failed_inits += 1
                        
                except Exception as e:
                    failed_inits += 1
                    print(f"    Init {i} failed: {e}")
            
            # Calculate statistics
            if response_times:
                response_times.sort()
                n = len(response_times)
                
                result = ProviderPerformanceResult(
                    provider_name=provider_name,
                    test_name="initialization",
                    total_requests=20,
                    successful_requests=successful_inits,
                    failed_requests=failed_inits,
                    avg_response_time_ms=statistics.mean(response_times),
                    p50_response_time_ms=response_times[int(n * 0.5)] if n > 0 else 0,
                    p95_response_time_ms=response_times[int(n * 0.95)] if n > 0 else 0,
                    p99_response_time_ms=response_times[int(n * 0.99)] if n > 0 else 0,
                    min_response_time_ms=min(response_times),
                    max_response_time_ms=max(response_times),
                    throughput_rps=successful_inits / (sum(response_times) / 1000) if sum(response_times) > 0 else 0,
                    error_rate=failed_inits / 20,
                    memory_peak_mb=0,  # Not measured in this test
                    custom_metrics={
                        'init_success_rate': successful_inits / 20,
                        'avg_init_time_ms': statistics.mean(response_times)
                    }
                )
                
                results.append(result)
                print(f"    {provider_name}: {result.avg_response_time_ms:.2f}ms avg, {result.error_rate:.1%} error rate")
        
        return results
    
    async def test_completion_performance_comparison(self) -> List[ProviderPerformanceResult]:
        """Compare completion performance across different provider configurations"""
        print("Testing completion performance comparison...")
        
        # Different provider configurations to test
        provider_configs = [
            ("fast_provider", MockProviderFactory.create_fast_provider()),
            ("slow_provider", MockProviderFactory.create_slow_provider()),
        ]
        
        # Add custom configured providers
        custom_fast = MockProviderFactory.create_fast_provider()
        custom_fast.add_scenario("ultra_fast", MockScenario(
            name="ultra_fast",
            response_content="Ultra fast response",
            response_delay=0.001,  # 1ms delay
            streaming_chunks=["Fast", " response"]
        ))
        custom_fast.set_scenario("ultra_fast")
        provider_configs.append(("ultra_fast_provider", custom_fast))
        
        results = []
        
        for provider_name, provider in provider_configs:
            print(f"  Testing {provider_name} completion performance...")
            
            await provider.initialize()
            
            response_times = []
            successful_completions = 0
            failed_completions = 0
            total_response_length = 0
            
            # Test with different request patterns
            test_requests = [
                {"role": "user", "content": "Short test"},
                {"role": "user", "content": "Medium length test message for performance analysis"},
                {"role": "user", "content": "Long test message " * 20},  # Longer content
            ]
            
            for request_content in test_requests:
                for i in range(10):  # 10 requests per content type
                    try:
                        from app.llm_providers.base_provider import CompletionRequest
                        
                        request = CompletionRequest(
                            messages=[request_content],
                            model="test-model"
                        )
                        
                        start_time = time.time()
                        response = await provider.complete(request)
                        end_time = time.time()
                        
                        response_time = (end_time - start_time) * 1000
                        response_times.append(response_time)
                        successful_completions += 1
                        total_response_length += len(response.content) if response.content else 0
                        
                    except Exception as e:
                        failed_completions += 1
                        print(f"    Completion failed: {e}")
            
            # Calculate statistics
            if response_times:
                response_times.sort()
                n = len(response_times)
                total_requests = successful_completions + failed_completions
                
                result = ProviderPerformanceResult(
                    provider_name=provider_name,
                    test_name="completion_comparison",
                    total_requests=total_requests,
                    successful_requests=successful_completions,
                    failed_requests=failed_completions,
                    avg_response_time_ms=statistics.mean(response_times),
                    p50_response_time_ms=response_times[int(n * 0.5)] if n > 0 else 0,
                    p95_response_time_ms=response_times[int(n * 0.95)] if n > 0 else 0,
                    p99_response_time_ms=response_times[int(n * 0.99)] if n > 0 else 0,
                    min_response_time_ms=min(response_times),
                    max_response_time_ms=max(response_times),
                    throughput_rps=successful_completions / (sum(response_times) / 1000) if sum(response_times) > 0 else 0,
                    error_rate=failed_completions / total_requests if total_requests > 0 else 0,
                    memory_peak_mb=0,
                    custom_metrics={
                        'avg_response_length': total_response_length / successful_completions if successful_completions > 0 else 0,
                        'response_time_std': statistics.stdev(response_times) if len(response_times) > 1 else 0
                    }
                )
                
                results.append(result)
                print(f"    {provider_name}: {result.avg_response_time_ms:.2f}ms avg, {result.throughput_rps:.1f} rps")
        
        return results
    
    async def test_concurrent_load_performance(self) -> List[ProviderPerformanceResult]:
        """Test performance under concurrent load"""
        print("Testing concurrent load performance...")
        
        provider = MockProviderFactory.create_fast_provider()
        await provider.initialize()
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        results = []
        
        for concurrency in concurrency_levels:
            print(f"  Testing concurrency level: {concurrency}")
            
            async def make_concurrent_request():
                try:
                    from app.llm_providers.base_provider import CompletionRequest
                    
                    request = CompletionRequest(
                        messages=[{"role": "user", "content": f"Concurrent test {concurrency}"}],
                        model="test-model"
                    )
                    
                    start_time = time.time()
                    response = await provider.complete(request)
                    end_time = time.time()
                    
                    return {
                        'success': True,
                        'response_time': (end_time - start_time) * 1000,
                        'response_length': len(response.content) if response.content else 0
                    }
                    
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e),
                        'response_time': 0,
                        'response_length': 0
                    }
            
            # Run concurrent requests
            start_time = time.time()
            tasks = [make_concurrent_request() for _ in range(concurrency * 10)]  # 10 requests per concurrency level
            request_results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Analyze results
            successful_results = [r for r in request_results if r['success']]
            failed_results = [r for r in request_results if not r['success']]
            
            response_times = [r['response_time'] for r in successful_results]
            
            if response_times:
                response_times.sort()
                n = len(response_times)
                total_duration = end_time - start_time
                
                result = ProviderPerformanceResult(
                    provider_name="fast_provider",
                    test_name=f"concurrent_load_{concurrency}",
                    total_requests=len(request_results),
                    successful_requests=len(successful_results),
                    failed_requests=len(failed_results),
                    avg_response_time_ms=statistics.mean(response_times),
                    p50_response_time_ms=response_times[int(n * 0.5)] if n > 0 else 0,
                    p95_response_time_ms=response_times[int(n * 0.95)] if n > 0 else 0,
                    p99_response_time_ms=response_times[int(n * 0.99)] if n > 0 else 0,
                    min_response_time_ms=min(response_times),
                    max_response_time_ms=max(response_times),
                    throughput_rps=len(successful_results) / total_duration if total_duration > 0 else 0,
                    error_rate=len(failed_results) / len(request_results) if request_results else 0,
                    memory_peak_mb=0,
                    custom_metrics={
                        'concurrency_level': concurrency,
                        'total_duration_sec': total_duration,
                        'requests_per_concurrency': 10
                    }
                )
                
                results.append(result)
                print(f"    Concurrency {concurrency}: {result.throughput_rps:.1f} rps, {result.avg_response_time_ms:.2f}ms avg")
        
        return results
    
    async def test_streaming_performance(self) -> List[ProviderPerformanceResult]:
        """Test streaming completion performance"""
        print("Testing streaming performance...")
        
        provider = MockProviderFactory.create_fast_provider()
        
        # Configure for streaming
        provider.add_scenario("streaming_test", MockScenario(
            name="streaming_test", 
            response_content="Streaming performance test response",
            response_delay=0.05,
            streaming_chunks=["Stream", " performance", " test", " response", " data"]
        ))
        provider.set_scenario("streaming_test")
        
        await provider.initialize()
        
        response_times = []
        first_chunk_times = []
        chunk_counts = []
        successful_streams = 0
        failed_streams = 0
        
        for i in range(20):  # Test 20 streaming requests
            try:
                from app.llm_providers.base_provider import CompletionRequest
                
                request = CompletionRequest(
                    messages=[{"role": "user", "content": f"Stream test {i}"}],
                    model="test-model",
                    stream=True
                )
                
                start_time = time.time()
                first_chunk_time = None
                chunks = []
                
                async for chunk in provider.stream_complete(request):
                    if first_chunk_time is None:
                        first_chunk_time = time.time() - start_time
                    chunks.append(chunk)
                
                end_time = time.time()
                total_time = (end_time - start_time) * 1000
                
                response_times.append(total_time)
                first_chunk_times.append(first_chunk_time * 1000 if first_chunk_time else 0)
                chunk_counts.append(len(chunks))
                successful_streams += 1
                
            except Exception as e:
                failed_streams += 1
                print(f"    Streaming request {i} failed: {e}")
        
        if response_times:
            response_times.sort()
            n = len(response_times)
            
            result = ProviderPerformanceResult(
                provider_name="fast_provider",
                test_name="streaming_performance",
                total_requests=successful_streams + failed_streams,
                successful_requests=successful_streams,
                failed_requests=failed_streams,
                avg_response_time_ms=statistics.mean(response_times),
                p50_response_time_ms=response_times[int(n * 0.5)] if n > 0 else 0,
                p95_response_time_ms=response_times[int(n * 0.95)] if n > 0 else 0,
                p99_response_time_ms=response_times[int(n * 0.99)] if n > 0 else 0,
                min_response_time_ms=min(response_times),
                max_response_time_ms=max(response_times),
                throughput_rps=successful_streams / (sum(response_times) / 1000) if sum(response_times) > 0 else 0,
                error_rate=failed_streams / (successful_streams + failed_streams) if (successful_streams + failed_streams) > 0 else 0,
                memory_peak_mb=0,
                custom_metrics={
                    'avg_first_chunk_time_ms': statistics.mean(first_chunk_times) if first_chunk_times else 0,
                    'avg_chunk_count': statistics.mean(chunk_counts) if chunk_counts else 0,
                    'streaming_efficiency': statistics.mean(first_chunk_times) / statistics.mean(response_times) if first_chunk_times and response_times else 0
                }
            )
            
            print(f"  Streaming: {result.avg_response_time_ms:.2f}ms total, {result.custom_metrics['avg_first_chunk_time_ms']:.2f}ms first chunk")
            return [result]
        
        return []
    
    def save_results(self, all_results: List[ProviderPerformanceResult]):
        """Save performance test results"""
        
        # Convert results to JSON format
        json_results = []
        for result in all_results:
            json_results.append({
                'provider_name': result.provider_name,
                'test_name': result.test_name,
                'total_requests': result.total_requests,
                'successful_requests': result.successful_requests,
                'failed_requests': result.failed_requests,
                'avg_response_time_ms': result.avg_response_time_ms,
                'p95_response_time_ms': result.p95_response_time_ms,
                'p99_response_time_ms': result.p99_response_time_ms,
                'throughput_rps': result.throughput_rps,
                'error_rate': result.error_rate,
                'custom_metrics': result.custom_metrics
            })
        
        # Save to JSON file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_file = self.output_dir / f"provider_performance_results_{timestamp}.json"
        
        with open(json_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'total_tests': len(json_results),
                'results': json_results
            }, f, indent=2)
        
        print(f"Provider performance results saved to: {json_file}")
        
        # Generate summary report
        self.generate_summary_report(all_results, timestamp)
    
    def generate_summary_report(self, results: List[ProviderPerformanceResult], timestamp: str):
        """Generate a summary performance report"""
        
        # Group results by provider
        by_provider = {}
        for result in results:
            if result.provider_name not in by_provider:
                by_provider[result.provider_name] = []
            by_provider[result.provider_name].append(result)
        
        # Generate HTML report
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LLM Provider Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #34495e; color: white; padding: 20px; border-radius: 5px; }}
        .provider {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .provider h3 {{ margin-top: 0; color: #2c3e50; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
        .best {{ background-color: #d4edda; }}
        .worst {{ background-color: #f8d7da; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LLM Provider Performance Report</h1>
        <p>Generated on: {timestamp}</p>
        <p>Total tests: {len(results)}</p>
    </div>
"""
        
        for provider_name, provider_results in by_provider.items():
            html += f"""
    <div class="provider">
        <h3>{provider_name.replace('_', ' ').title()}</h3>
        <table>
            <tr>
                <th>Test</th>
                <th>Requests</th>
                <th>Success Rate</th>
                <th>Avg Response (ms)</th>
                <th>P95 Response (ms)</th>
                <th>Throughput (rps)</th>
                <th>Error Rate</th>
            </tr>"""
            
            for result in provider_results:
                html += f"""
            <tr>
                <td>{result.test_name}</td>
                <td>{result.total_requests}</td>
                <td>{(result.successful_requests/result.total_requests)*100:.1f}%</td>
                <td>{result.avg_response_time_ms:.2f}</td>
                <td>{result.p95_response_time_ms:.2f}</td>
                <td>{result.throughput_rps:.1f}</td>
                <td>{result.error_rate*100:.1f}%</td>
            </tr>"""
            
            html += """
        </table>
    </div>"""
        
        html += """
</body>
</html>"""
        
        html_file = self.output_dir / f"provider_performance_report_{timestamp}.html"
        with open(html_file, 'w') as f:
            f.write(html)
        
        print(f"HTML report saved to: {html_file}")


async def main():
    """Main provider performance testing execution"""
    print("=== LLM Provider Performance Testing ===")
    
    tester = ProviderPerformanceTester()
    all_results = []
    
    try:
        # Test provider initialization
        init_results = await tester.test_provider_initialization_performance()
        all_results.extend(init_results)
        
        # Test completion performance comparison
        completion_results = await tester.test_completion_performance_comparison()
        all_results.extend(completion_results)
        
        # Test concurrent load performance  
        concurrent_results = await tester.test_concurrent_load_performance()
        all_results.extend(concurrent_results)
        
        # Test streaming performance
        streaming_results = await tester.test_streaming_performance()
        all_results.extend(streaming_results)
        
        # Save all results
        tester.save_results(all_results)
        
        # Print summary
        print(f"\n=== Provider Performance Summary ===")
        print(f"Total tests completed: {len(all_results)}")
        
        # Find best and worst performers
        if completion_results:
            best_throughput = max(completion_results, key=lambda x: x.throughput_rps)
            best_response_time = min(completion_results, key=lambda x: x.avg_response_time_ms)
            
            print(f"Best throughput: {best_throughput.provider_name} ({best_throughput.throughput_rps:.1f} rps)")
            print(f"Best response time: {best_response_time.provider_name} ({best_response_time.avg_response_time_ms:.2f}ms)")
        
    except Exception as e:
        print(f"Provider performance testing failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())