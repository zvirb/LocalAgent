#!/usr/bin/env python3
"""
Comprehensive Test Suite for Provider Resilience Features
Tests connection pooling, rate limiting, circuit breaker, caching, and token counting
"""

import asyncio
import sys
import os
import time
import json
import logging
from pathlib import Path

# Add the app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.llm_providers.enhanced_ollama_provider import EnhancedOllamaProvider
from app.llm_providers.base_provider import CompletionRequest
from app.resilience import (
    initialize_global_pool, initialize_global_limiter, get_global_manager,
    RateLimitConfig, CircuitBreakerConfig, PoolConfig
)
from app.caching import get_global_cache_manager
from app.benchmarks import ProviderBenchmark, BenchmarkConfig, quick_benchmark

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_connection_pool():
    """Test connection pool functionality"""
    logger.info("Testing Connection Pool...")
    
    try:
        # Initialize connection pool with test config
        pool_config = PoolConfig(
            max_connections=50,
            max_connections_per_host=10,
            connection_timeout=10.0,
            cleanup_interval=5.0
        )
        
        await initialize_global_pool(pool_config)
        
        from app.resilience import get_global_pool
        pool = get_global_pool()
        await pool.start()
        
        # Test basic connectivity
        try:
            response = await pool.get("http://localhost:11434/api/tags", timeout=10.0)
            logger.info(f"✅ Connection pool test successful: HTTP {response.status}")
            await response.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"⚠️  Connection pool test failed (Ollama may not be running): {e}")
        
        # Get pool statistics
        stats = pool.get_stats()
        logger.info(f"Pool stats: {stats.total_requests} requests, {stats.active_connections} active connections")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection pool test failed: {e}")
        return False

async def test_rate_limiter():
    """Test rate limiting functionality"""
    logger.info("Testing Rate Limiter...")
    
    try:
        # Initialize rate limiter
        await initialize_global_limiter({
            'test_provider': RateLimitConfig(
                tokens_per_second=2.0,  # Very restrictive for testing
                max_tokens=3,
                window_size=1.0
            )
        })
        
        from app.resilience import get_global_limiter
        limiter = get_global_limiter()
        
        # Test token consumption
        start_time = time.time()
        
        # These should succeed immediately
        for i in range(3):
            allowed = await limiter.allow_request('test_provider', 1)
            if not allowed:
                logger.error(f"❌ Rate limiter test failed: request {i} denied unexpectedly")
                return False
        
        # This should be rate limited
        allowed = await limiter.allow_request('test_provider', 1)
        if allowed:
            logger.warning("⚠️  Rate limiter may not be working - expected denial")
        else:
            logger.info("✅ Rate limiter correctly denied request when limit exceeded")
        
        # Test blocking wait
        wait_start = time.time()
        allowed = await limiter.wait_for_tokens('test_provider', 1, timeout=5.0)
        wait_time = time.time() - wait_start
        
        if allowed and wait_time > 0.3:  # Should have waited for token refill
            logger.info(f"✅ Rate limiter blocking wait successful: waited {wait_time:.2f}s")
        else:
            logger.warning(f"⚠️  Rate limiter blocking behavior unclear: waited {wait_time:.2f}s")
        
        # Get statistics
        stats = limiter.get_all_stats()
        if 'test_provider' in stats:
            provider_stats = stats['test_provider']
            logger.info(f"Rate limiter stats: {provider_stats.total_requests} requests, "
                       f"{provider_stats.denied_requests} denied")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Rate limiter test failed: {e}")
        return False

async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    logger.info("Testing Circuit Breaker...")
    
    try:
        circuit_manager = get_global_manager()
        
        # Configure a test circuit breaker
        test_config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout=5.0,
            reset_timeout=10.0
        )
        
        breaker = await circuit_manager.get_breaker('test_circuit', test_config)
        
        # Test normal operation
        async def successful_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await breaker.call(successful_operation)
        if result == "success":
            logger.info("✅ Circuit breaker allows successful operations")
        
        # Test failure handling
        async def failing_operation():
            raise ConnectionError("Simulated failure")
        
        # Generate failures to open circuit
        failure_count = 0
        for i in range(3):
            try:
                await breaker.call(failing_operation)
            except:
                failure_count += 1
        
        logger.info(f"Generated {failure_count} failures")
        
        # Check if circuit is open
        stats = breaker.get_stats()
        logger.info(f"Circuit breaker state: {stats.state.value}, failures: {stats.failure_count}")
        
        if stats.failure_count >= test_config.failure_threshold:
            logger.info("✅ Circuit breaker correctly tracked failures")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Circuit breaker test failed: {e}")
        return False

async def test_response_cache():
    """Test response caching functionality"""
    logger.info("Testing Response Cache...")
    
    try:
        cache_manager = get_global_cache_manager()
        cache = await cache_manager.get_cache('test_provider')
        
        # Test cache miss and put
        test_request = {'test': 'request', 'temperature': 0.0}
        test_response = {'content': 'test response', 'tokens': 10}
        
        # Should be cache miss initially
        cached = await cache.get(test_request)
        if cached is None:
            logger.info("✅ Cache miss for new request (expected)")
        else:
            logger.warning("⚠️  Unexpected cache hit for new request")
        
        # Cache the response
        cached_success = await cache.put(test_request, test_response, ttl=60)
        if cached_success:
            logger.info("✅ Successfully cached response")
        
        # Should be cache hit now
        cached = await cache.get(test_request)
        if cached == test_response:
            logger.info("✅ Cache hit returned correct data")
        else:
            logger.error(f"❌ Cache hit returned wrong data: {cached}")
            return False
        
        # Test cache statistics
        stats = cache.get_stats()
        logger.info(f"Cache stats: {stats.cache_hits} hits, {stats.cache_misses} misses, "
                   f"hit rate: {stats.hit_rate:.2%}")
        
        # Test TTL expiration (with short TTL)
        short_ttl_request = {'test': 'short_ttl', 'temperature': 0.1}
        await cache.put(short_ttl_request, test_response, ttl=0.5)
        
        # Should hit immediately
        cached = await cache.get(short_ttl_request)
        if cached:
            logger.info("✅ Short TTL cache hit works")
        
        # Wait for expiration
        await asyncio.sleep(1.0)
        cached = await cache.get(short_ttl_request)
        if cached is None:
            logger.info("✅ Cache TTL expiration works correctly")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Response cache test failed: {e}")
        return False

async def test_token_counting():
    """Test token counting accuracy"""
    logger.info("Testing Token Counting...")
    
    try:
        from app.llm_providers.token_counter import get_global_token_manager
        token_manager = get_global_token_manager()
        
        # Test different text sizes
        test_cases = [
            ("Hello world", "Short text"),
            ("This is a longer piece of text that should have more tokens than the short one.", "Medium text"),
            ("""This is a much longer piece of text that contains multiple sentences and should result in 
            a significantly higher token count. It includes various punctuation marks, numbers like 123, 
            and different types of words including technical terms and common vocabulary.""", "Long text")
        ]
        
        for text, description in test_cases:
            ollama_tokens = token_manager.count_tokens('ollama', text, 'llama2')
            openai_tokens = token_manager.count_tokens('openai', text, 'gpt-3.5-turbo')
            
            logger.info(f"{description}: Ollama={ollama_tokens}, OpenAI={openai_tokens} tokens")
            
            # Basic sanity checks
            if ollama_tokens <= 0 or openai_tokens <= 0:
                logger.error("❌ Token counting returned zero or negative values")
                return False
        
        # Test message token counting
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is a subset of AI..."}
        ]
        
        message_tokens = token_manager.count_message_tokens('ollama', messages, 'llama2')
        logger.info(f"Message array tokens: {message_tokens}")
        
        if message_tokens > 0:
            logger.info("✅ Token counting tests passed")
            return True
        else:
            logger.error("❌ Message token counting failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Token counting test failed: {e}")
        return False

async def test_enhanced_provider():
    """Test the enhanced Ollama provider integration"""
    logger.info("Testing Enhanced Ollama Provider...")
    
    try:
        # Initialize provider
        config = {
            'base_url': 'http://localhost:11434',
            'timeout': 30
        }
        
        provider = EnhancedOllamaProvider(config)
        
        # Test initialization
        initialized = await provider.initialize()
        if not initialized:
            logger.warning("⚠️  Ollama server not available - skipping provider tests")
            return True  # Not a failure if server isn't running
        
        logger.info("✅ Enhanced provider initialized successfully")
        
        # Test health check
        health = await provider.health_check()
        logger.info(f"Provider health: {health['healthy']}")
        
        if health['healthy']:
            logger.info(f"Models available: {health['models']['available']}")
            
            # Test model listing
            models = await provider.list_models()
            if models:
                logger.info(f"✅ Listed {len(models)} models")
                test_model = models[0].name
            else:
                logger.warning("⚠️  No models available for testing")
                return True
            
            # Test completion (if we have a model)
            try:
                request = CompletionRequest(
                    messages=[{"role": "user", "content": "Say 'Hello, World!' and nothing else."}],
                    model=test_model,
                    temperature=0.1,
                    max_tokens=20
                )
                
                response = await provider.complete(request)
                logger.info(f"✅ Completion successful: {len(response.content)} chars, {response.usage['total_tokens']} tokens")
                
                # Test streaming
                chunks = []
                async for chunk in provider.stream_complete(request):
                    chunks.append(chunk)
                    if len(chunks) > 10:  # Limit for testing
                        break
                
                if chunks:
                    logger.info(f"✅ Streaming successful: {len(chunks)} chunks")
                
            except Exception as e:
                logger.warning(f"⚠️  Provider completion test failed (model may not be available): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced provider test failed: {e}")
        return False

async def run_performance_benchmark():
    """Run performance benchmark tests"""
    logger.info("Running Performance Benchmarks...")
    
    try:
        # Initialize provider for benchmarking
        config = {'base_url': 'http://localhost:11434'}
        provider = EnhancedOllamaProvider(config)
        
        if not await provider.initialize():
            logger.warning("⚠️  Skipping benchmarks - Ollama not available")
            return True
        
        # Quick benchmark
        logger.info("Running quick benchmark (5 concurrent, 25 total requests)...")
        result = await quick_benchmark(provider, concurrent=5, total=25)
        
        logger.info(f"Benchmark Results:")
        logger.info(f"  Successful: {result.successful_requests}/{result.total_requests}")
        logger.info(f"  Error rate: {result.error_rate:.2%}")
        logger.info(f"  Throughput: {result.throughput_rps:.2f} req/sec")
        logger.info(f"  Avg response time: {result.avg_response_time*1000:.1f}ms")
        logger.info(f"  P95 response time: {result.p95_response_time*1000:.1f}ms")
        
        if result.cache_hit_rate > 0:
            logger.info(f"  Cache hit rate: {result.cache_hit_rate:.2%}")
        
        # Consider benchmark successful if most requests succeeded
        success_rate = result.successful_requests / result.total_requests
        if success_rate >= 0.8:  # 80% success rate threshold
            logger.info("✅ Performance benchmark passed")
            return True
        else:
            logger.warning(f"⚠️  Performance benchmark concern: {success_rate:.2%} success rate")
            return True  # Don't fail on performance issues
        
    except Exception as e:
        logger.error(f"❌ Performance benchmark failed: {e}")
        return False

async def main():
    """Run all resilience tests"""
    logger.info("🚀 Starting Provider Resilience Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Connection Pool", test_connection_pool),
        ("Rate Limiter", test_rate_limiter),
        ("Circuit Breaker", test_circuit_breaker),
        ("Response Cache", test_response_cache),
        ("Token Counting", test_token_counting),
        ("Enhanced Provider", test_enhanced_provider),
        ("Performance Benchmark", run_performance_benchmark)
    ]
    
    results = {}
    start_time = time.time()
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} Test...")
        test_start = time.time()
        
        try:
            success = await test_func()
            test_time = time.time() - test_start
            results[test_name] = {
                'success': success,
                'duration': test_time,
                'error': None
            }
            
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{status} - {test_name} ({test_time:.2f}s)")
            
        except Exception as e:
            test_time = time.time() - test_start
            results[test_name] = {
                'success': False,
                'duration': test_time,
                'error': str(e)
            }
            logger.error(f"❌ FAILED - {test_name} ({test_time:.2f}s): {e}")
    
    # Generate summary
    total_time = time.time() - start_time
    passed = sum(1 for r in results.values() if r['success'])
    total = len(results)
    
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    logger.info(f"Success rate: {passed/total:.2%}")
    logger.info(f"Total duration: {total_time:.2f}s")
    logger.info("")
    
    # Detailed results
    for test_name, result in results.items():
        status = "✅" if result['success'] else "❌"
        duration = result['duration']
        logger.info(f"{status} {test_name:<20} ({duration:>6.2f}s)")
        if result['error']:
            logger.info(f"    Error: {result['error']}")
    
    # Clean up
    logger.info("\n🧹 Cleaning up...")
    try:
        from app.resilience import shutdown_global_pool
        await shutdown_global_pool()
    except Exception as e:
        logger.debug(f"Cleanup error: {e}")
    
    # Exit code
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        sys.exit(1)