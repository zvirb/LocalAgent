"""
Performance benchmark tests for LocalAgent providers
"""

import pytest
import asyncio
import time
from tests.performance.benchmark_framework import (
    BenchmarkRunner, 
    ProviderBenchmarkSuite, 
    BenchmarkReportGenerator
)
from tests.mocks.mock_provider import MockProviderFactory, MockScenario
from app.llm_providers.base_provider import CompletionRequest


class TestProviderPerformanceBenchmarks:
    """Performance benchmark tests for providers"""
    
    def setup_method(self):
        """Setup benchmark suite"""
        self.benchmark_suite = ProviderBenchmarkSuite()
    
    @pytest.mark.asyncio
    async def test_initialization_performance(self):
        """Benchmark provider initialization performance"""
        
        def fast_provider_factory():
            provider = MockProviderFactory.create_fast_provider()
            # Make initialization nearly instant
            provider.add_scenario("instant_init", MockScenario(
                name="instant_init",
                response_delay=0.001
            ))
            provider.set_scenario("instant_init")
            return provider
        
        result = await self.benchmark_suite.benchmark_provider_initialization(
            fast_provider_factory,
            iterations=50
        )
        
        # Assertions
        assert result.successful_operations == 50
        assert result.error_rate == 0.0
        assert result.avg_duration < 0.1  # Should be very fast
        assert result.throughput_ops_sec > 10  # Should handle many inits per second
        
        print(f"Initialization benchmark: {result.throughput_ops_sec:.2f} ops/sec")
    
    @pytest.mark.asyncio
    async def test_completion_latency_benchmark(self):
        """Benchmark completion latency"""
        provider = MockProviderFactory.create_fast_provider()
        
        result = await self.benchmark_suite.benchmark_completion_latency(
            provider,
            iterations=100,
            concurrency=1
        )
        
        # Assertions
        assert result.successful_operations == 100
        assert result.error_rate == 0.0
        assert result.p95_duration < 1.0  # 95% of requests under 1 second
        assert result.throughput_ops_sec > 5  # At least 5 ops/sec
        
        # Check custom metrics
        avg_response_length = sum(
            m.custom_metrics.get('response_length', 0) 
            for m in result.individual_metrics 
            if m.success
        ) / result.successful_operations
        
        assert avg_response_length > 0
        
        print(f"Completion latency: {result.avg_duration*1000:.2f}ms avg, {result.p95_duration*1000:.2f}ms p95")
    
    @pytest.mark.asyncio
    async def test_streaming_performance_benchmark(self):
        """Benchmark streaming completion performance"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Configure for streaming
        provider.add_scenario("streaming", MockScenario(
            name="streaming",
            response_content="Streaming test response",
            response_delay=0.05,
            streaming_chunks=["Stream ", "test ", "response ", "data"]
        ))
        provider.set_scenario("streaming")
        
        result = await self.benchmark_suite.benchmark_streaming_performance(
            provider,
            iterations=50
        )
        
        # Assertions
        assert result.successful_operations == 50
        assert result.error_rate == 0.0
        
        # Check streaming-specific metrics
        avg_chunks = sum(
            m.custom_metrics.get('chunk_count', 0)
            for m in result.individual_metrics
            if m.success
        ) / result.successful_operations
        
        avg_first_chunk_latency = sum(
            m.custom_metrics.get('first_chunk_latency', 0)
            for m in result.individual_metrics
            if m.success
        ) / result.successful_operations
        
        assert avg_chunks >= 3  # Should have multiple chunks
        assert avg_first_chunk_latency < result.avg_duration  # First chunk should be faster than total
        
        print(f"Streaming: {avg_chunks:.1f} chunks avg, {avg_first_chunk_latency*1000:.2f}ms first chunk")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_benchmark(self):
        """Benchmark concurrent request handling"""
        provider = MockProviderFactory.create_fast_provider()
        
        result = await self.benchmark_suite.benchmark_concurrent_requests(
            provider,
            requests_per_batch=10,
            batches=10,
            max_concurrency=5
        )
        
        # Assertions
        assert result.successful_operations == 10  # 10 batches
        assert result.error_rate == 0.0
        
        # Check concurrent metrics
        total_requests_processed = sum(
            m.custom_metrics.get('successful_requests', 0)
            for m in result.individual_metrics
            if m.success
        )
        
        avg_requests_per_second = sum(
            m.custom_metrics.get('requests_per_second', 0)
            for m in result.individual_metrics
            if m.success
        ) / result.successful_operations
        
        assert total_requests_processed == 100  # 10 batches * 10 requests
        assert avg_requests_per_second > 10  # Should handle good throughput
        
        print(f"Concurrent: {avg_requests_per_second:.2f} requests/sec avg per batch")
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_benchmark(self):
        """Benchmark memory efficiency"""
        provider = MockProviderFactory.create_fast_provider()
        
        result = await self.benchmark_suite.benchmark_memory_efficiency(
            provider,
            iterations=50,
            message_sizes=[100, 1000, 5000]
        )
        
        # Assertions
        assert result.successful_operations == 50
        assert result.error_rate == 0.0
        
        # Check memory metrics
        avg_memory_per_char = sum(
            m.custom_metrics.get('avg_memory_per_char', 0)
            for m in result.individual_metrics
            if m.success
        ) / result.successful_operations
        
        assert avg_memory_per_char > 0
        assert result.memory_peak > 0
        
        print(f"Memory efficiency: {avg_memory_per_char:.2f} bytes per character avg")
    
    @pytest.mark.asyncio
    async def test_error_rate_under_load(self):
        """Test error rate under high load"""
        provider = MockProviderFactory.create_failing_provider("network")
        
        # Make it fail 20% of the time
        provider.add_scenario("partial_fail", MockScenario(
            name="partial_fail",
            response_content="Success response",
            should_fail=False  # We'll manually control failures
        ))
        
        # Custom operation that fails sometimes
        async def flaky_operation():
            import random
            if random.random() < 0.2:  # 20% failure rate
                raise Exception("Simulated failure")
            
            request = CompletionRequest(
                messages=[{"role": "user", "content": "Test"}],
                model="test-model"
            )
            return await provider.complete(request)
        
        runner = BenchmarkRunner()
        result = await runner.run_benchmark(
            "error_rate_test",
            flaky_operation,
            iterations=100,
            concurrency=5
        )
        
        # Should have some failures
        assert result.error_rate > 0.1  # At least 10% errors
        assert result.error_rate < 0.4  # But not too many
        assert result.successful_operations > 60  # Most should still succeed
        
        print(f"Error rate under load: {result.error_rate*100:.1f}%")


class TestPerformanceComparisons:
    """Compare performance across different configurations"""
    
    @pytest.mark.asyncio
    async def test_fast_vs_slow_provider_comparison(self):
        """Compare performance between fast and slow providers"""
        fast_provider = MockProviderFactory.create_fast_provider()
        slow_provider = MockProviderFactory.create_slow_provider()
        
        benchmark_suite = ProviderBenchmarkSuite()
        
        # Benchmark both providers
        fast_result = await benchmark_suite.benchmark_completion_latency(
            fast_provider,
            iterations=50,
            concurrency=1
        )
        
        slow_result = await benchmark_suite.benchmark_completion_latency(
            slow_provider,
            iterations=50,
            concurrency=1
        )
        
        # Fast should be significantly faster
        assert fast_result.avg_duration < slow_result.avg_duration
        assert fast_result.throughput_ops_sec > slow_result.throughput_ops_sec
        
        performance_ratio = slow_result.avg_duration / fast_result.avg_duration
        assert performance_ratio > 5  # Slow should be at least 5x slower
        
        print(f"Performance comparison:")
        print(f"  Fast: {fast_result.avg_duration*1000:.2f}ms avg")
        print(f"  Slow: {slow_result.avg_duration*1000:.2f}ms avg")
        print(f"  Ratio: {performance_ratio:.1f}x")
    
    @pytest.mark.asyncio
    async def test_sequential_vs_concurrent_performance(self):
        """Compare sequential vs concurrent request performance"""
        provider = MockProviderFactory.create_fast_provider()
        benchmark_suite = ProviderBenchmarkSuite()
        
        # Sequential benchmark
        sequential_result = await benchmark_suite.benchmark_completion_latency(
            provider,
            iterations=50,
            concurrency=1
        )
        
        # Concurrent benchmark  
        concurrent_result = await benchmark_suite.benchmark_completion_latency(
            provider,
            iterations=50,
            concurrency=10
        )
        
        # Concurrent should have higher throughput
        assert concurrent_result.throughput_ops_sec > sequential_result.throughput_ops_sec
        
        throughput_improvement = concurrent_result.throughput_ops_sec / sequential_result.throughput_ops_sec
        assert throughput_improvement > 2  # At least 2x improvement
        
        print(f"Sequential vs Concurrent:")
        print(f"  Sequential: {sequential_result.throughput_ops_sec:.2f} ops/sec")
        print(f"  Concurrent: {concurrent_result.throughput_ops_sec:.2f} ops/sec")
        print(f"  Improvement: {throughput_improvement:.1f}x")


class TestBenchmarkReporting:
    """Test benchmark reporting functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_comprehensive_report(self):
        """Test generating comprehensive benchmark report"""
        # Run multiple benchmarks
        provider = MockProviderFactory.create_fast_provider()
        benchmark_suite = ProviderBenchmarkSuite()
        
        results = []
        
        # Run different benchmark types
        results.append(await benchmark_suite.benchmark_completion_latency(
            provider, iterations=30
        ))
        
        results.append(await benchmark_suite.benchmark_streaming_performance(
            provider, iterations=20
        ))
        
        results.append(await benchmark_suite.benchmark_memory_efficiency(
            provider, iterations=25
        ))
        
        # Generate HTML report
        report_generator = BenchmarkReportGenerator()
        report_path = report_generator.generate_html_report(results)
        
        # Verify report was created
        import os
        assert os.path.exists(report_path)
        assert report_path.endswith('.html')
        
        # Check report contains expected content
        with open(report_path, 'r') as f:
            content = f.read()
        
        assert 'LocalAgent Performance Benchmark Report' in content
        assert 'completion_latency' in content
        assert 'streaming_performance' in content
        assert 'memory_efficiency' in content
        assert 'ops/sec' in content  # Throughput metrics
        
        print(f"Report generated: {report_path}")
    
    @pytest.mark.asyncio
    async def test_benchmark_result_persistence(self):
        """Test that benchmark results are properly saved and loaded"""
        provider = MockProviderFactory.create_fast_provider()
        benchmark_suite = ProviderBenchmarkSuite()
        
        # Run benchmark
        result = await benchmark_suite.benchmark_completion_latency(
            provider, iterations=20
        )
        
        # Load results back
        report_generator = BenchmarkReportGenerator()
        loaded_results = report_generator.load_results("completion_latency_*.json")
        
        # Should have at least one result
        assert len(loaded_results) >= 1
        
        # Find our result
        our_result = None
        for loaded_result in loaded_results:
            if loaded_result.name == "completion_latency":
                our_result = loaded_result
                break
        
        assert our_result is not None
        assert our_result.total_operations == result.total_operations
        assert our_result.successful_operations == result.successful_operations
        assert abs(our_result.avg_duration - result.avg_duration) < 0.001
        
        print(f"Successfully loaded {len(loaded_results)} benchmark results")


class TestStressTestScenarios:
    """Stress test scenarios for performance validation"""
    
    @pytest.mark.asyncio
    async def test_high_concurrency_stress(self):
        """Test performance under high concurrency"""
        provider = MockProviderFactory.create_fast_provider()
        benchmark_suite = ProviderBenchmarkSuite()
        
        result = await benchmark_suite.benchmark_concurrent_requests(
            provider,
            requests_per_batch=50,
            batches=5,
            max_concurrency=20
        )
        
        # Should handle high concurrency reasonably well
        assert result.error_rate < 0.1  # Less than 10% errors
        assert result.successful_operations == 5  # All batches should complete
        
        avg_batch_throughput = sum(
            m.custom_metrics.get('requests_per_second', 0)
            for m in result.individual_metrics
            if m.success
        ) / result.successful_operations
        
        assert avg_batch_throughput > 20  # Should handle good throughput
        
        print(f"High concurrency stress: {avg_batch_throughput:.2f} requests/sec avg")
    
    @pytest.mark.asyncio
    async def test_memory_stress_large_messages(self):
        """Test memory performance with large messages"""
        provider = MockProviderFactory.create_fast_provider()
        benchmark_suite = ProviderBenchmarkSuite()
        
        # Test with progressively larger messages
        large_message_sizes = [1000, 10000, 50000, 100000]
        
        result = await benchmark_suite.benchmark_memory_efficiency(
            provider,
            iterations=20,
            message_sizes=large_message_sizes
        )
        
        # Should handle large messages without excessive memory usage
        assert result.successful_operations == 20
        assert result.error_rate == 0.0
        
        # Memory usage should scale reasonably with message size
        memory_mb = result.memory_peak / 1024 / 1024
        assert memory_mb < 100  # Should not exceed 100MB for test messages
        
        print(f"Large message stress: {memory_mb:.2f} MB peak memory")
    
    @pytest.mark.asyncio
    async def test_sustained_load_benchmark(self):
        """Test performance under sustained load"""
        provider = MockProviderFactory.create_fast_provider()
        
        # Configure for sustained testing
        provider.add_scenario("sustained", MockScenario(
            name="sustained",
            response_content="Sustained load response",
            response_delay=0.1  # Moderate delay
        ))
        provider.set_scenario("sustained")
        
        runner = BenchmarkRunner()
        
        async def sustained_operation():
            request = CompletionRequest(
                messages=[{"role": "user", "content": "Sustained load test"}],
                model="test-model"
            )
            response = await provider.complete(request)
            return {'metrics': {'response_length': len(response.content)}}
        
        # Run for sustained period
        result = await runner.run_benchmark(
            "sustained_load",
            sustained_operation,
            iterations=200,
            concurrency=5,
            warmup_iterations=20
        )
        
        # Should maintain consistent performance
        assert result.error_rate < 0.05  # Less than 5% errors
        assert result.successful_operations >= 190  # Most should succeed
        
        # Performance should not degrade significantly
        # (In a real scenario, we'd check for performance regression over time)
        assert result.p95_duration < result.avg_duration * 2  # P95 not too far from average
        
        print(f"Sustained load: {result.throughput_ops_sec:.2f} ops/sec over {result.total_duration:.1f}s")