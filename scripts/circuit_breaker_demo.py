#!/usr/bin/env python3
"""
Circuit Breaker Load Test Demo
Demonstrates circuit breaker behavior under simulated load and failures
"""

import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

async def simulate_circuit_breaker_load():
    """Demonstrate circuit breaker under load with failures"""
    print("⚡ Circuit Breaker Load Test")
    print("=" * 50)
    
    try:
        from app.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
        
        # Create circuit breaker with aggressive settings for demo
        config = CircuitBreakerConfig(
            failure_threshold=3,      # Open after 3 failures
            success_threshold=2,      # Close after 2 successes
            timeout=2.0,             # Try half-open after 2 seconds
            reset_timeout=10.0
        )
        
        breaker = CircuitBreaker("load_test", config)
        print(f"Circuit Breaker Config:")
        print(f"  Failure Threshold: {config.failure_threshold}")
        print(f"  Success Threshold: {config.success_threshold}")
        print(f"  Timeout: {config.timeout}s")
        print()
        
        # Simulate varying service reliability
        service_failure_rate = 0.0  # Start with healthy service
        request_count = 0
        
        async def simulated_service():
            """Simulate a service with configurable failure rate"""
            nonlocal request_count
            request_count += 1
            
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Simulate failures based on current failure rate
            import random
            if random.random() < service_failure_rate:
                raise ConnectionError(f"Service unavailable (failure rate: {service_failure_rate:.0%})")
            
            return f"Success #{request_count}"
        
        # Phase 1: Healthy service
        print("Phase 1: Healthy Service (0% failure rate)")
        print("-" * 30)
        
        for i in range(5):
            try:
                result = await breaker.call(simulated_service)
                stats = breaker.get_stats()
                print(f"Request {i+1}: ✅ {result} (State: {breaker.state.value}, Failures: {stats.failure_count})")
            except Exception as e:
                stats = breaker.get_stats()
                print(f"Request {i+1}: ❌ {e} (State: {breaker.state.value}, Failures: {stats.failure_count})")
        
        print()
        
        # Phase 2: Introduce failures
        print("Phase 2: Degraded Service (70% failure rate)")
        print("-" * 30)
        service_failure_rate = 0.7
        
        for i in range(10):
            try:
                result = await breaker.call(simulated_service)
                stats = breaker.get_stats()
                print(f"Request {i+6}: ✅ {result} (State: {breaker.state.value}, Failures: {stats.failure_count})")
            except Exception as e:
                stats = breaker.get_stats()
                print(f"Request {i+6}: ❌ {str(e)[:40]} (State: {breaker.state.value}, Failures: {stats.failure_count})")
                
                # Break early if circuit opens
                if breaker.state == CircuitState.OPEN:
                    print(f"🚨 Circuit breaker OPENED after {stats.failure_count} failures!")
                    break
        
        print()
        
        # Phase 3: Circuit is open - requests should fail fast
        print("Phase 3: Circuit Open - Fast Failures")
        print("-" * 30)
        
        for i in range(3):
            try:
                result = await breaker.call(simulated_service)
                print(f"Request {i+16}: ✅ {result}")
            except Exception as e:
                print(f"Request {i+16}: ❌ {str(e)[:50]}")
        
        print()
        
        # Phase 4: Wait for half-open transition
        print(f"Phase 4: Waiting {config.timeout}s for half-open transition...")
        print("-" * 30)
        await asyncio.sleep(config.timeout + 0.5)
        
        # Service becomes healthy again
        service_failure_rate = 0.0
        print("Service recovered (0% failure rate)")
        
        # Should transition to half-open and then closed
        for i in range(5):
            try:
                result = await breaker.call(simulated_service)
                stats = breaker.get_stats()
                print(f"Request {i+19}: ✅ {result} (State: {breaker.state.value}, Success: {stats.success_count})")
                
                # Note when circuit closes
                if breaker.state == CircuitState.CLOSED and i > 0:
                    print(f"🎉 Circuit breaker CLOSED after {stats.success_count} successes!")
                    
            except Exception as e:
                stats = breaker.get_stats()
                print(f"Request {i+19}: ❌ {e} (State: {breaker.state.value})")
        
        # Final statistics
        final_stats = breaker.get_stats()
        print(f"\nFinal Statistics:")
        print(f"  State: {final_stats.state.value}")
        print(f"  Total Requests: {final_stats.total_requests}")
        print(f"  Successful: {final_stats.successful_requests}")
        print(f"  Failed: {final_stats.failed_requests}")
        print(f"  Rejected: {final_stats.rejected_requests}")
        print(f"  State Transitions: {final_stats.state_transitions}")
        print(f"  Success Rate: {final_stats.successful_requests / max(1, final_stats.total_requests):.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ Circuit breaker demo failed: {e}")
        return False

async def simulate_concurrent_load():
    """Demonstrate circuit breaker under concurrent load"""
    print("\n🚀 Concurrent Load Test")
    print("=" * 50)
    
    try:
        from app.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        
        config = CircuitBreakerConfig(failure_threshold=5, timeout=3.0)
        breaker = CircuitBreaker("concurrent_test", config)
        
        # Shared state for simulating service
        shared_state = {"failure_rate": 0.3, "request_count": 0}
        
        async def concurrent_service(worker_id: int):
            """Service simulation for concurrent testing"""
            shared_state["request_count"] += 1
            request_num = shared_state["request_count"]
            
            await asyncio.sleep(0.05)  # Small delay
            
            import random
            if random.random() < shared_state["failure_rate"]:
                raise ConnectionError(f"Worker {worker_id} request {request_num} failed")
            
            return f"Worker {worker_id} success {request_num}"
        
        # Launch concurrent workers
        async def worker(worker_id: int, num_requests: int):
            results = {"success": 0, "failed": 0, "rejected": 0}
            
            for i in range(num_requests):
                try:
                    result = await breaker.call(lambda: concurrent_service(worker_id))
                    results["success"] += 1
                except Exception as e:
                    if "circuit breaker" in str(e).lower():
                        results["rejected"] += 1
                    else:
                        results["failed"] += 1
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            return worker_id, results
        
        print("Starting 5 concurrent workers with 10 requests each...")
        print("Service failure rate: 30%")
        print()
        
        # Run concurrent workers
        tasks = [worker(i, 10) for i in range(5)]
        worker_results = await asyncio.gather(*tasks)
        
        # Collect results
        total_results = {"success": 0, "failed": 0, "rejected": 0}
        
        print("Worker Results:")
        for worker_id, results in worker_results:
            total_results["success"] += results["success"]
            total_results["failed"] += results["failed"] 
            total_results["rejected"] += results["rejected"]
            
            print(f"  Worker {worker_id}: {results['success']} success, "
                  f"{results['failed']} failed, {results['rejected']} rejected")
        
        # Circuit breaker stats
        cb_stats = breaker.get_stats()
        
        print(f"\nConcurrent Test Results:")
        print(f"  Total Requests: {sum(total_results.values())}")
        print(f"  Successful: {total_results['success']}")
        print(f"  Failed: {total_results['failed']}")
        print(f"  Rejected by Circuit: {total_results['rejected']}")
        print(f"  Circuit State: {cb_stats.state.value}")
        print(f"  Circuit Transitions: {cb_stats.state_transitions}")
        
        return True
        
    except Exception as e:
        print(f"❌ Concurrent load test failed: {e}")
        return False

async def main():
    """Run circuit breaker demonstrations"""
    start_time = time.time()
    
    # Run sequential load test
    success1 = await simulate_circuit_breaker_load()
    
    # Run concurrent load test  
    success2 = await simulate_concurrent_load()
    
    # Summary
    total_time = time.time() - start_time
    
    print(f"\n{'='*50}")
    print("Circuit Breaker Demo Summary")
    print(f"{'='*50}")
    
    tests = [
        ("Sequential Load Test", success1),
        ("Concurrent Load Test", success2)
    ]
    
    for name, success in tests:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    passed = sum(1 for _, success in tests if success)
    print(f"\nPassed: {passed}/{len(tests)}")
    print(f"Duration: {total_time:.2f}s")
    
    if passed == len(tests):
        print("\n🎉 Circuit breaker demos completed successfully!")
        print("\n📊 Demonstrated Behaviors:")
        print("  • State transitions: Closed → Open → Half-Open → Closed")
        print("  • Failure threshold detection and fast-fail mode")
        print("  • Automatic recovery testing after timeout")
        print("  • Concurrent request handling with shared state")
        print("  • Comprehensive statistics tracking")

if __name__ == "__main__":
    asyncio.run(main())