#!/usr/bin/env python3
"""
Simple demonstration of resilience features without external dependencies
Shows the core functionality of each resilience component
"""

import asyncio
import time
import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def demo_token_bucket():
    """Demonstrate token bucket rate limiting"""
    print("🪣 Token Bucket Rate Limiter Demo")
    print("-" * 40)
    
    try:
        from app.resilience.rate_limiter import TokenBucket, RateLimitConfig
        
        # Create a token bucket with 2 tokens/sec, max 3 tokens
        config = RateLimitConfig(tokens_per_second=2.0, max_tokens=3)
        bucket = TokenBucket(config)
        
        print(f"Created token bucket: {config.tokens_per_second} tokens/sec, max {config.max_tokens}")
        print()
        
        # Test immediate consumption (should succeed)
        for i in range(3):
            success = await bucket.consume(1)
            stats = bucket.get_stats()
            print(f"Request {i+1}: {'✅ Allowed' if success else '❌ Denied'} "
                  f"(tokens: {stats.current_tokens:.1f})")
        
        # This should be denied (bucket empty)
        success = await bucket.consume(1)
        stats = bucket.get_stats()
        print(f"Request 4: {'✅ Allowed' if success else '❌ Denied'} "
              f"(tokens: {stats.current_tokens:.1f})")
        
        print("\n⏳ Waiting 1 second for token refill...")
        await asyncio.sleep(1.0)
        
        # Should succeed after refill
        success = await bucket.consume(1)
        stats = bucket.get_stats()
        print(f"Request 5: {'✅ Allowed' if success else '❌ Denied'} "
              f"(tokens: {stats.current_tokens:.1f})")
        
        print(f"\nFinal stats: {stats.allowed_requests} allowed, {stats.denied_requests} denied")
        return True
        
    except Exception as e:
        print(f"❌ Token bucket demo failed: {e}")
        return False

async def demo_circuit_breaker():
    """Demonstrate circuit breaker pattern"""
    print("\n⚡ Circuit Breaker Demo")
    print("-" * 40)
    
    try:
        from app.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
        
        # Create circuit breaker with low failure threshold for demo
        config = CircuitBreakerConfig(failure_threshold=2, timeout=3.0)
        breaker = CircuitBreaker("demo", config)
        
        print(f"Created circuit breaker: {config.failure_threshold} failure threshold")
        print(f"Initial state: {breaker.state.value}")
        print()
        
        # Simulate successful operations
        async def successful_op():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await breaker.call(successful_op)
        print(f"Operation 1: {result} (state: {breaker.state.value})")
        
        # Simulate failing operations
        async def failing_op():
            raise ConnectionError("Simulated failure")
        
        failures = 0
        for i in range(4):
            try:
                await breaker.call(failing_op)
            except Exception:
                failures += 1
                stats = breaker.get_stats()
                print(f"Operation {i+2}: Failed #{failures} (state: {breaker.state.value}, "
                      f"failures: {stats.failure_count})")
        
        # Try operation when circuit is open (should fail fast)
        try:
            await breaker.call(successful_op)
            print("❌ Operation should have been rejected")
        except Exception as e:
            print(f"Operation 6: Rejected - {e}")
        
        print(f"\nFinal state: {breaker.state.value}")
        return True
        
    except Exception as e:
        print(f"❌ Circuit breaker demo failed: {e}")
        return False

async def demo_response_cache():
    """Demonstrate response caching"""
    print("\n💾 Response Cache Demo")
    print("-" * 40)
    
    try:
        from app.caching.response_cache import ResponseCache, CacheConfig, CacheStrategy
        
        # Create cache with small size for demo
        config = CacheConfig(max_size=3, default_ttl=5.0, strategy=CacheStrategy.AGGRESSIVE)
        cache = ResponseCache(config)
        
        print(f"Created cache: max {config.max_size} entries, {config.default_ttl}s TTL")
        print()
        
        # Test cache miss
        request1 = {"query": "hello", "temperature": 0.0}
        result = await cache.get(request1)
        print(f"Cache lookup 1: {'Hit' if result else 'Miss'}")
        
        # Add to cache
        response1 = {"content": "Hello there!", "tokens": 5}
        cached = await cache.put(request1, response1)
        print(f"Cache store 1: {'Success' if cached else 'Failed'}")
        
        # Test cache hit
        result = await cache.get(request1)
        print(f"Cache lookup 2: {'Hit' if result else 'Miss'}")
        if result:
            print(f"  Retrieved: {result}")
        
        # Add more items to test LRU
        request2 = {"query": "goodbye", "temperature": 0.1}
        response2 = {"content": "Goodbye!", "tokens": 3}
        await cache.put(request2, response2)
        
        request3 = {"query": "maybe", "temperature": 0.2}
        response3 = {"content": "Maybe...", "tokens": 2}
        await cache.put(request3, response3)
        
        # This should trigger LRU eviction
        request4 = {"query": "certainly", "temperature": 0.3}
        response4 = {"content": "Certainly!", "tokens": 4}
        await cache.put(request4, response4)
        
        # Check what's still in cache
        stats = cache.get_stats()
        print(f"\nCache stats: {stats.current_entries} entries, "
              f"{stats.cache_hits} hits, {stats.cache_misses} misses")
        print(f"Hit rate: {stats.hit_rate:.2%}")
        
        # Test TTL expiration
        request5 = {"query": "short", "temperature": 0.0}
        response5 = {"content": "Short!", "tokens": 1}
        await cache.put(request5, response5, ttl=0.5)  # Very short TTL
        
        result = await cache.get(request5)
        print(f"Short TTL lookup (immediate): {'Hit' if result else 'Miss'}")
        
        print("⏳ Waiting for TTL expiration...")
        await asyncio.sleep(1.0)
        
        result = await cache.get(request5)
        print(f"Short TTL lookup (after expiry): {'Hit' if result else 'Miss'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Response cache demo failed: {e}")
        return False

async def demo_token_counting():
    """Demonstrate token counting"""
    print("\n🔢 Token Counter Demo")
    print("-" * 40)
    
    try:
        from app.llm_providers.token_counter import TokenCounterManager
        
        manager = TokenCounterManager()
        
        test_texts = [
            "Hello world",
            "This is a longer sentence with more words and punctuation!",
            "The quick brown fox jumps over the lazy dog. This is a classic pangram used for testing."
        ]
        
        providers = ['openai', 'ollama', 'gemini']
        
        print("Token counts by provider:")
        print()
        
        for i, text in enumerate(test_texts, 1):
            print(f"Text {i}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            
            for provider in providers:
                tokens = manager.count_tokens(provider, text)
                print(f"  {provider:>8}: {tokens:>3} tokens")
            print()
        
        # Test message counting
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is a subset of AI that enables computers to learn and improve from data without being explicitly programmed for each task."}
        ]
        
        print("Message token counting:")
        for provider in providers:
            tokens = manager.count_message_tokens(provider, messages)
            print(f"  {provider:>8}: {tokens:>3} tokens")
        
        # Test cost estimation
        print("\nCost estimation (1000 tokens):")
        for provider in providers:
            cost = manager.estimate_cost(provider, 1000, "default")
            if cost > 0:
                print(f"  {provider:>8}: ${cost:.4f}")
            else:
                print(f"  {provider:>8}: Free (local)")
        
        return True
        
    except Exception as e:
        print(f"❌ Token counting demo failed: {e}")
        return False

async def demo_connection_pool():
    """Demonstrate connection pool (without actual HTTP calls)"""
    print("\n🌐 Connection Pool Demo")
    print("-" * 40)
    
    try:
        from app.resilience.connection_pool import ConnectionPool, PoolConfig
        
        # Create pool with demo config
        config = PoolConfig(max_connections=10, max_connections_per_host=3)
        pool = ConnectionPool(config)
        
        print(f"Created connection pool: max {config.max_connections} connections")
        print(f"Per-host limit: {config.max_connections_per_host}")
        
        # Start the pool
        await pool.start()
        
        # Demonstrate host key generation
        test_urls = [
            "http://localhost:11434/api/tags",
            "https://api.openai.com/v1/chat/completions",
            "http://localhost:11434/api/chat",
            "https://api.openai.com/v1/models"
        ]
        
        print("\nHost key mapping:")
        for url in test_urls:
            host_key = pool._get_host_key(url)
            print(f"  {url} -> {host_key}")
        
        # Show stats
        stats = pool.get_stats()
        print(f"\nPool stats: {stats.total_requests} requests, "
              f"{stats.active_connections} active connections")
        
        # Cleanup
        await pool.stop()
        
        return True
        
    except Exception as e:
        print(f"❌ Connection pool demo failed: {e}")
        return False

async def main():
    """Run all demos"""
    print("🚀 Provider Resilience Features Demo")
    print("=" * 50)
    
    demos = [
        ("Token Bucket Rate Limiter", demo_token_bucket),
        ("Circuit Breaker", demo_circuit_breaker),
        ("Response Cache", demo_response_cache),
        ("Token Counting", demo_token_counting),
        ("Connection Pool", demo_connection_pool)
    ]
    
    results = []
    start_time = time.time()
    
    for name, demo_func in demos:
        try:
            success = await demo_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ {name} demo failed: {e}")
            results.append((name, False))
    
    # Summary
    total_time = time.time() - start_time
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print("\n" + "=" * 50)
    print("📊 Demo Summary")
    print("=" * 50)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    print(f"Duration: {total_time:.2f}s")
    
    if passed == total:
        print("\n🎉 All demos completed successfully!")
        print("\n📖 Key Features Demonstrated:")
        print("  • Token bucket rate limiting with burst handling")
        print("  • Circuit breaker with state transitions")
        print("  • LRU cache with TTL expiration")
        print("  • Provider-specific token counting")
        print("  • Connection pool host management")
        print("\n🔗 For full integration, see enhanced_ollama_provider.py")
    else:
        print(f"\n⚠️  {total - passed} demos had issues")

if __name__ == "__main__":
    asyncio.run(main())