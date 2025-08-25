"""
Provider Performance Benchmarking Suite
Tests resilience patterns under various load conditions
"""

import asyncio
import time
import statistics
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
import json
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Results from a benchmark run"""
    test_name: str
    provider: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    throughput_rps: float
    error_rate: float
    cache_hit_rate: float = 0.0
    rate_limit_hits: int = 0
    circuit_breaker_opens: int = 0

@dataclass
class BenchmarkConfig:
    """Configuration for benchmark tests"""
    concurrent_requests: int = 10
    total_requests: int = 100
    request_delay: float = 0.1
    timeout: float = 30.0
    test_data_size: str = "small"  # small, medium, large
    enable_caching: bool = True
    enable_rate_limiting: bool = True

class ProviderBenchmark:
    """
    Comprehensive benchmarking suite for provider resilience testing
    """
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
    
    async def benchmark_provider(self, provider, config: BenchmarkConfig) -> BenchmarkResult:
        """Run comprehensive benchmark on a provider"""
        start_time = time.time()
        response_times = []
        successful = 0
        failed = 0
        rate_limited = 0
        
        # Test data based on size configuration
        test_messages = self._generate_test_messages(config.test_data_size)
        
        # Run concurrent requests
        semaphore = asyncio.Semaphore(config.concurrent_requests)
        
        async def single_request(request_id: int):
            nonlocal successful, failed, rate_limited
            
            async with semaphore:
                request_start = time.time()
                
                try:
                    # Rotate through test messages
                    messages = test_messages[request_id % len(test_messages)]
                    
                    from ..llm_providers.base_provider import CompletionRequest
                    request = CompletionRequest(
                        messages=messages,
                        model="llama2:7b",  # Default test model
                        temperature=0.7,
                        max_tokens=100
                    )
                    
                    response = await provider.complete(request)
                    
                    request_time = time.time() - request_start
                    response_times.append(request_time)
                    successful += 1
                    
                    logger.debug(f"Request {request_id} completed in {request_time:.3f}s")
                    
                except Exception as e:
                    failed += 1
                    if "rate limit" in str(e).lower():
                        rate_limited += 1
                    
                    logger.debug(f"Request {request_id} failed: {e}")
                
                # Delay between requests if configured
                if config.request_delay > 0:
                    await asyncio.sleep(config.request_delay)
        
        # Execute all requests
        tasks = [single_request(i) for i in range(config.total_requests)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 10 else max_response_time
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0.0
        
        throughput_rps = successful / total_time if total_time > 0 else 0.0
        error_rate = failed / config.total_requests
        
        # Get provider-specific metrics
        cache_hit_rate = 0.0
        circuit_breaker_opens = 0
        
        try:
            if hasattr(provider, 'cache_manager'):
                cache_stats = provider.cache_manager.get_all_stats().get('ollama')
                if cache_stats:
                    cache_hit_rate = cache_stats.hit_rate
            
            if hasattr(provider, 'circuit_manager'):
                circuit_stats = provider.circuit_manager.get_provider_stats('ollama')
                if circuit_stats:
                    circuit_breaker_opens = circuit_stats.state_transitions
        except Exception as e:
            logger.debug(f"Error getting provider metrics: {e}")
        
        result = BenchmarkResult(
            test_name=f"load_test_{config.concurrent_requests}c_{config.total_requests}r",
            provider=provider.__class__.__name__,
            total_requests=config.total_requests,
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            throughput_rps=throughput_rps,
            error_rate=error_rate,
            cache_hit_rate=cache_hit_rate,
            rate_limit_hits=rate_limited,
            circuit_breaker_opens=circuit_breaker_opens
        )
        
        self.results.append(result)
        return result
    
    def _generate_test_messages(self, size: str) -> List[List[Dict[str, str]]]:
        """Generate test message arrays of different sizes"""
        
        small_messages = [
            [{"role": "user", "content": "Hello, how are you?"}],
            [{"role": "user", "content": "What is 2+2?"}],
            [{"role": "user", "content": "Tell me a joke."}],
            [{"role": "user", "content": "What's the weather like?"}],
            [{"role": "user", "content": "How do I cook pasta?"}]
        ]
        
        medium_messages = [
            [{"role": "user", "content": "Explain the concept of machine learning in simple terms. What are the main types of machine learning algorithms and how do they differ from each other?"}],
            [{"role": "user", "content": "Write a short story about a robot that discovers emotions. Make it engaging and thought-provoking."}],
            [{"role": "user", "content": "Analyze the pros and cons of renewable energy sources like solar and wind power compared to traditional fossil fuels."}],
            [{"role": "user", "content": "Describe the process of photosynthesis and explain why it's important for life on Earth."}],
            [{"role": "user", "content": "What are the key principles of good software engineering? How do they help create maintainable code?"}]
        ]
        
        large_messages = [
            [{
                "role": "user", 
                "content": """Provide a comprehensive analysis of the impact of artificial intelligence on modern society. 
                Consider the following aspects:
                1. Economic implications - job displacement vs. job creation
                2. Ethical considerations - privacy, bias, and fairness
                3. Technological advancement - current capabilities and future potential
                4. Social changes - how AI is changing human interaction and communication
                5. Regulatory challenges - the need for governance and oversight
                
                For each aspect, provide specific examples and discuss both positive and negative impacts. 
                Also, suggest potential solutions or mitigation strategies for the challenges you identify.
                Your analysis should be detailed, balanced, and well-reasoned."""
            }],
            [{
                "role": "user",
                "content": """You are a senior software architect tasked with designing a distributed microservices system 
                for an e-commerce platform. The system needs to handle:
                - 1 million active users
                - 10,000 transactions per minute during peak hours
                - Product catalog with 1 million items
                - Real-time inventory management
                - Payment processing with multiple providers
                - Order fulfillment and shipping integration
                - Customer support and recommendation engine
                
                Design a complete system architecture including:
                1. Service breakdown and responsibilities
                2. Data storage strategy (databases, caching)
                3. Communication patterns between services
                4. Scalability and reliability considerations
                5. Security measures and compliance requirements
                6. Monitoring and observability strategy
                7. Deployment and CI/CD pipeline
                
                Provide detailed justification for your architectural decisions and discuss potential trade-offs."""
            }]
        ]
        
        if size == "small":
            return small_messages
        elif size == "medium":
            return medium_messages
        elif size == "large":
            return large_messages
        else:
            return small_messages  # Default fallback
    
    async def run_stress_test(self, provider, duration_seconds: int = 60) -> BenchmarkResult:
        """Run a stress test for a specified duration"""
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        successful = 0
        failed = 0
        response_times = []
        request_count = 0
        
        # Simple test message
        test_message = [{"role": "user", "content": "Count from 1 to 5."}]
        
        while time.time() < end_time:
            request_start = time.time()
            request_count += 1
            
            try:
                from ..llm_providers.base_provider import CompletionRequest
                request = CompletionRequest(
                    messages=test_message,
                    model="llama2:7b",
                    temperature=0.1,  # Low temperature for consistency
                    max_tokens=50
                )
                
                response = await provider.complete(request)
                
                response_time = time.time() - request_start
                response_times.append(response_time)
                successful += 1
                
            except Exception as e:
                failed += 1
                logger.debug(f"Stress test request {request_count} failed: {e}")
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.05)
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 10 else max_response_time
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0.0
        
        result = BenchmarkResult(
            test_name=f"stress_test_{duration_seconds}s",
            provider=provider.__class__.__name__,
            total_requests=request_count,
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            throughput_rps=successful / total_time,
            error_rate=failed / request_count if request_count > 0 else 0.0
        )
        
        self.results.append(result)
        return result
    
    async def test_circuit_breaker(self, provider) -> Dict[str, Any]:
        """Test circuit breaker behavior under failure conditions"""
        # This would require a way to simulate failures
        # For now, we'll just check the circuit breaker stats
        
        try:
            if hasattr(provider, 'circuit_manager'):
                stats = provider.circuit_manager.get_provider_stats('ollama')
                return {
                    'circuit_breaker_available': True,
                    'current_state': stats.state.value if stats else 'unknown',
                    'failure_count': stats.failure_count if stats else 0,
                    'success_count': stats.success_count if stats else 0
                }
            else:
                return {'circuit_breaker_available': False}
        except Exception as e:
            return {'circuit_breaker_available': False, 'error': str(e)}
    
    async def test_cache_effectiveness(self, provider) -> Dict[str, Any]:
        """Test cache hit rates with repeated requests"""
        cache_stats_before = None
        cache_stats_after = None
        
        try:
            # Get initial cache stats
            if hasattr(provider, 'cache_manager'):
                cache_stats_before = provider.cache_manager.get_all_stats().get('ollama')
            
            # Make repeated identical requests (should hit cache)
            test_message = [{"role": "user", "content": "What is 1+1?"}]
            
            from ..llm_providers.base_provider import CompletionRequest
            request = CompletionRequest(
                messages=test_message,
                model="llama2:7b",
                temperature=0.0,  # Deterministic for caching
                max_tokens=10
            )
            
            # Make the same request multiple times
            for i in range(5):
                try:
                    await provider.complete(request)
                except Exception:
                    pass  # Ignore errors for cache testing
            
            # Get final cache stats
            if hasattr(provider, 'cache_manager'):
                cache_stats_after = provider.cache_manager.get_all_stats().get('ollama')
            
            return {
                'cache_available': cache_stats_after is not None,
                'cache_hits_before': cache_stats_before.cache_hits if cache_stats_before else 0,
                'cache_hits_after': cache_stats_after.cache_hits if cache_stats_after else 0,
                'cache_hit_rate': cache_stats_after.hit_rate if cache_stats_after else 0.0,
                'cache_entries': cache_stats_after.current_entries if cache_stats_after else 0
            }
            
        except Exception as e:
            return {'cache_available': False, 'error': str(e)}
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive performance report"""
        if not self.results:
            return "No benchmark results available."
        
        report = []
        report.append("=" * 80)
        report.append("PROVIDER PERFORMANCE BENCHMARK REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary statistics
        total_requests = sum(r.total_requests for r in self.results)
        total_successful = sum(r.successful_requests for r in self.results)
        avg_throughput = statistics.mean([r.throughput_rps for r in self.results if r.throughput_rps > 0])
        avg_response_time = statistics.mean([r.avg_response_time for r in self.results if r.avg_response_time > 0])
        
        report.append("SUMMARY:")
        report.append(f"Total requests across all tests: {total_requests}")
        report.append(f"Total successful requests: {total_successful}")
        report.append(f"Overall success rate: {total_successful/total_requests*100:.2f}%")
        report.append(f"Average throughput: {avg_throughput:.2f} requests/second")
        report.append(f"Average response time: {avg_response_time*1000:.2f} ms")
        report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS:")
        report.append("-" * 80)
        
        for result in self.results:
            report.append(f"Test: {result.test_name}")
            report.append(f"Provider: {result.provider}")
            report.append(f"Requests: {result.successful_requests}/{result.total_requests} successful")
            report.append(f"Error rate: {result.error_rate*100:.2f}%")
            report.append(f"Throughput: {result.throughput_rps:.2f} req/sec")
            report.append(f"Response times: avg={result.avg_response_time*1000:.1f}ms, "
                         f"min={result.min_response_time*1000:.1f}ms, "
                         f"max={result.max_response_time*1000:.1f}ms, "
                         f"p95={result.p95_response_time*1000:.1f}ms")
            
            if result.cache_hit_rate > 0:
                report.append(f"Cache hit rate: {result.cache_hit_rate*100:.2f}%")
            
            if result.rate_limit_hits > 0:
                report.append(f"Rate limit hits: {result.rate_limit_hits}")
            
            if result.circuit_breaker_opens > 0:
                report.append(f"Circuit breaker opens: {result.circuit_breaker_opens}")
            
            report.append("-" * 40)
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
        
        return report_text


# Convenience function for quick benchmarking
async def quick_benchmark(provider, concurrent=5, total=50) -> BenchmarkResult:
    """Run a quick benchmark with default settings"""
    benchmark = ProviderBenchmark()
    config = BenchmarkConfig(
        concurrent_requests=concurrent,
        total_requests=total,
        request_delay=0.1,
        test_data_size="small"
    )
    
    return await benchmark.benchmark_provider(provider, config)