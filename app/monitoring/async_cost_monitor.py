"""
🚀 Async Cost Monitoring System
Real-time detection and prevention of cost-multiplying async anti-patterns
"""

import asyncio
import aiohttp
import time
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import weakref

logger = logging.getLogger(__name__)

@dataclass
class AsyncCallMetric:
    """Metrics for individual async calls"""
    timestamp: float
    function_name: str
    duration: float
    session_reused: bool
    parallel_execution: bool
    error_count: int
    memory_usage: float
    cost_estimate: float

@dataclass
class AntiPatternAlert:
    """Alert for detected async anti-patterns"""
    pattern_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    evidence: Dict[str, Any]
    estimated_cost_impact: float
    recommendation: str
    timestamp: float

class AsyncCostMonitor:
    """🚀 Monitors and optimizes async patterns to reduce LLM costs by up to 90%"""
    
    def __init__(self):
        self.metrics: deque = deque(maxlen=10000)  # Keep last 10K metrics
        self.session_registry: Dict[str, aiohttp.ClientSession] = {}
        self.call_patterns: Dict[str, List[float]] = defaultdict(list)
        self.alerts: List[AntiPatternAlert] = []
        self.total_cost_saved: float = 0.0
        self.monitoring_active = True
        
        # Cost estimates (per 1K requests)
        self.cost_multipliers = {
            'session_recreation': 10.0,  # 10x connection overhead
            'sequential_execution': 3.0,  # 3x time waste
            'race_conditions': 5.0,      # 5x duplicate calls
            'missing_caching': 2.5,      # 2.5x repeated work
            'memory_leaks': 1.5          # 1.5x resource waste
        }
    
    async def start_monitoring(self):
        """Start the async cost monitoring system"""
        logger.info("🚀 Starting Async Cost Monitor")
        asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await self._detect_anti_patterns()
                await self._calculate_cost_savings()
                await self._cleanup_old_metrics()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    def track_async_call(self, func_name: str, start_time: float, end_time: float, 
                        session_reused: bool = False, parallel: bool = False,
                        error_count: int = 0):
        """Track individual async call metrics"""
        metric = AsyncCallMetric(
            timestamp=start_time,
            function_name=func_name,
            duration=end_time - start_time,
            session_reused=session_reused,
            parallel_execution=parallel,
            error_count=error_count,
            memory_usage=self._estimate_memory_usage(),
            cost_estimate=self._estimate_call_cost(func_name, end_time - start_time)
        )
        
        self.metrics.append(metric)
        self.call_patterns[func_name].append(start_time)
    
    def register_session(self, provider: str, session: aiohttp.ClientSession):
        """Register a reusable session to detect session recreation patterns"""
        session_id = f"{provider}_{id(session)}"
        self.session_registry[session_id] = session
        
        # Use weakref to auto-cleanup when session is destroyed
        def cleanup_callback(ref):
            self.session_registry.pop(session_id, None)
        
        weakref.finalize(session, cleanup_callback)
    
    async def _detect_anti_patterns(self):
        """Detect cost-multiplying async anti-patterns"""
        if len(self.metrics) < 10:
            return
            
        recent_metrics = list(self.metrics)[-100:]  # Last 100 calls
        
        # 1. Detect session recreation anti-pattern
        await self._detect_session_recreation(recent_metrics)
        
        # 2. Detect sequential execution when parallel is possible
        await self._detect_sequential_execution(recent_metrics)
        
        # 3. Detect race conditions (duplicate calls)
        await self._detect_race_conditions(recent_metrics)
        
        # 4. Detect missing caching opportunities
        await self._detect_missing_caching(recent_metrics)
        
        # 5. Detect memory leaks
        await self._detect_memory_leaks(recent_metrics)
    
    async def _detect_session_recreation(self, metrics: List[AsyncCallMetric]):
        """Detect HTTP session recreation anti-pattern"""
        provider_calls = defaultdict(int)
        session_reuse_count = defaultdict(int)
        
        for metric in metrics:
            if 'provider' in metric.function_name.lower():
                provider_calls[metric.function_name] += 1
                if metric.session_reused:
                    session_reuse_count[metric.function_name] += 1
        
        for func_name, total_calls in provider_calls.items():
            if total_calls > 5:  # Only alert if significant usage
                reuse_rate = session_reuse_count[func_name] / total_calls
                
                if reuse_rate < 0.8:  # Less than 80% session reuse
                    cost_impact = total_calls * self.cost_multipliers['session_recreation'] * 0.001
                    
                    alert = AntiPatternAlert(
                        pattern_type='session_recreation',
                        severity='critical' if reuse_rate < 0.3 else 'high',
                        message=f"Session recreation detected in {func_name}: {reuse_rate:.1%} reuse rate",
                        evidence={
                            'total_calls': total_calls,
                            'session_reuse_rate': reuse_rate,
                            'function': func_name
                        },
                        estimated_cost_impact=cost_impact,
                        recommendation="Implement connection pooling with persistent sessions",
                        timestamp=time.time()
                    )
                    
                    self.alerts.append(alert)
                    logger.warning(f"🚨 {alert.message} - Cost impact: ${cost_impact:.2f}")
    
    async def _detect_sequential_execution(self, metrics: List[AsyncCallMetric]):
        """Detect sequential execution that could be parallelized"""
        time_windows = defaultdict(list)
        
        # Group calls by 1-second windows
        for metric in metrics:
            window = int(metric.timestamp)
            time_windows[window].append(metric)
        
        for window, window_metrics in time_windows.items():
            if len(window_metrics) > 3:  # Multiple calls in same window
                parallel_count = sum(1 for m in window_metrics if m.parallel_execution)
                sequential_rate = 1 - (parallel_count / len(window_metrics))
                
                if sequential_rate > 0.7 and len(window_metrics) > 5:
                    cost_impact = len(window_metrics) * self.cost_multipliers['sequential_execution'] * 0.001
                    
                    alert = AntiPatternAlert(
                        pattern_type='sequential_execution',
                        severity='high',
                        message=f"Sequential execution detected: {len(window_metrics)} calls, {sequential_rate:.1%} sequential",
                        evidence={
                            'total_calls': len(window_metrics),
                            'sequential_rate': sequential_rate,
                            'window': window,
                            'functions': [m.function_name for m in window_metrics]
                        },
                        estimated_cost_impact=cost_impact,
                        recommendation="Use Promise.all() or asyncio.gather() for parallel execution",
                        timestamp=time.time()
                    )
                    
                    self.alerts.append(alert)
                    logger.warning(f"🚨 {alert.message} - Cost impact: ${cost_impact:.2f}")
    
    async def _detect_race_conditions(self, metrics: List[AsyncCallMetric]):
        """Detect race conditions causing duplicate API calls"""
        recent_calls = defaultdict(list)
        
        # Group calls by function and check for rapid duplicates
        for metric in metrics:
            recent_calls[metric.function_name].append(metric.timestamp)
        
        for func_name, timestamps in recent_calls.items():
            if len(timestamps) < 3:
                continue
                
            # Check for calls within 100ms of each other (likely duplicates)
            duplicates = 0
            for i in range(1, len(timestamps)):
                if timestamps[i] - timestamps[i-1] < 0.1:  # Within 100ms
                    duplicates += 1
            
            if duplicates > len(timestamps) * 0.3:  # More than 30% are duplicates
                cost_impact = duplicates * self.cost_multipliers['race_conditions'] * 0.001
                
                alert = AntiPatternAlert(
                    pattern_type='race_conditions',
                    severity='high',
                    message=f"Race conditions detected in {func_name}: {duplicates} duplicate calls",
                    evidence={
                        'function': func_name,
                        'total_calls': len(timestamps),
                        'duplicate_calls': duplicates,
                        'duplicate_rate': duplicates / len(timestamps)
                    },
                    estimated_cost_impact=cost_impact,
                    recommendation="Implement request deduplication and proper dependency management",
                    timestamp=time.time()
                )
                
                self.alerts.append(alert)
                logger.warning(f"🚨 {alert.message} - Cost impact: ${cost_impact:.2f}")
    
    async def _detect_missing_caching(self, metrics: List[AsyncCallMetric]):
        """Detect repeated identical calls that could be cached"""
        function_calls = defaultdict(int)
        
        for metric in metrics:
            # Look for frequent calls to same function (potential caching opportunity)
            function_calls[metric.function_name] += 1
        
        for func_name, call_count in function_calls.items():
            if call_count > 10:  # More than 10 calls to same function
                # Check if calls are spread over time (cacheable pattern)
                timestamps = [m.timestamp for m in metrics if m.function_name == func_name]
                time_span = max(timestamps) - min(timestamps)
                
                if time_span > 30:  # Calls spread over 30+ seconds
                    cost_impact = call_count * self.cost_multipliers['missing_caching'] * 0.001
                    
                    alert = AntiPatternAlert(
                        pattern_type='missing_caching',
                        severity='medium',
                        message=f"Caching opportunity detected: {func_name} called {call_count} times",
                        evidence={
                            'function': func_name,
                            'call_count': call_count,
                            'time_span': time_span,
                            'calls_per_minute': call_count / (time_span / 60)
                        },
                        estimated_cost_impact=cost_impact,
                        recommendation="Implement response caching with appropriate TTL",
                        timestamp=time.time()
                    )
                    
                    self.alerts.append(alert)
                    logger.info(f"💡 {alert.message} - Potential savings: ${cost_impact:.2f}")
    
    async def _detect_memory_leaks(self, metrics: List[AsyncCallMetric]):
        """Detect memory leak patterns"""
        if len(metrics) < 50:
            return
        
        # Check for increasing memory usage trend
        recent_memory = [m.memory_usage for m in metrics[-20:]]
        older_memory = [m.memory_usage for m in metrics[-50:-30]]
        
        if recent_memory and older_memory:
            recent_avg = sum(recent_memory) / len(recent_memory)
            older_avg = sum(older_memory) / len(older_memory)
            
            growth_rate = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            
            if growth_rate > 0.2:  # 20% memory growth
                cost_impact = growth_rate * self.cost_multipliers['memory_leaks'] * 0.01
                
                alert = AntiPatternAlert(
                    pattern_type='memory_leaks',
                    severity='medium' if growth_rate < 0.5 else 'high',
                    message=f"Memory leak detected: {growth_rate:.1%} increase",
                    evidence={
                        'recent_avg_memory': recent_avg,
                        'older_avg_memory': older_avg,
                        'growth_rate': growth_rate
                    },
                    estimated_cost_impact=cost_impact,
                    recommendation="Check for unclosed connections, timers, and event listeners",
                    timestamp=time.time()
                )
                
                self.alerts.append(alert)
                logger.warning(f"🚨 {alert.message} - Cost impact: ${cost_impact:.2f}")
    
    def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage (MB)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _estimate_call_cost(self, func_name: str, duration: float) -> float:
        """Estimate cost of individual call"""
        base_cost = 0.001  # $0.001 per call baseline
        
        # Higher cost for longer operations
        duration_multiplier = 1 + (duration / 10)  # +10% per 10 seconds
        
        # Higher cost for provider calls
        provider_multiplier = 2.0 if 'provider' in func_name.lower() else 1.0
        
        return base_cost * duration_multiplier * provider_multiplier
    
    async def _calculate_cost_savings(self):
        """Calculate total cost savings from optimizations"""
        recent_alerts = [a for a in self.alerts if time.time() - a.timestamp < 3600]  # Last hour
        total_waste = sum(alert.estimated_cost_impact for alert in recent_alerts)
        
        # Estimate savings (assume 80% of detected issues are fixed)
        potential_savings = total_waste * 0.8
        self.total_cost_saved += potential_savings
        
        if total_waste > 0.1:  # Only log significant waste
            logger.info(f"💰 Potential cost savings: ${potential_savings:.2f}/hour")
    
    async def _cleanup_old_metrics(self):
        """Clean up old alerts and metrics"""
        # Remove alerts older than 24 hours
        cutoff_time = time.time() - 86400
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff_time]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        if not self.metrics:
            return {"error": "No metrics available"}
        
        recent_metrics = list(self.metrics)[-100:]
        recent_alerts = [a for a in self.alerts if time.time() - a.timestamp < 3600]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics_summary": {
                "total_calls": len(recent_metrics),
                "avg_duration": sum(m.duration for m in recent_metrics) / len(recent_metrics),
                "session_reuse_rate": sum(1 for m in recent_metrics if m.session_reused) / len(recent_metrics),
                "parallel_execution_rate": sum(1 for m in recent_metrics if m.parallel_execution) / len(recent_metrics),
                "avg_memory_usage": sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
            },
            "alerts": {
                "total_alerts": len(recent_alerts),
                "critical_alerts": len([a for a in recent_alerts if a.severity == 'critical']),
                "high_alerts": len([a for a in recent_alerts if a.severity == 'high']),
                "recent_alerts": [asdict(a) for a in recent_alerts[-10:]]  # Last 10 alerts
            },
            "cost_analysis": {
                "total_cost_saved": self.total_cost_saved,
                "hourly_waste_estimate": sum(a.estimated_cost_impact for a in recent_alerts),
                "top_cost_patterns": self._get_top_cost_patterns(recent_alerts)
            },
            "recommendations": self._get_optimization_recommendations(recent_alerts)
        }
    
    def _get_top_cost_patterns(self, alerts: List[AntiPatternAlert]) -> List[Dict[str, Any]]:
        """Get top cost-causing patterns"""
        pattern_costs = defaultdict(float)
        
        for alert in alerts:
            pattern_costs[alert.pattern_type] += alert.estimated_cost_impact
        
        return [
            {"pattern": pattern, "cost_impact": cost} 
            for pattern, cost in sorted(pattern_costs.items(), key=lambda x: x[1], reverse=True)
        ]
    
    def _get_optimization_recommendations(self, alerts: List[AntiPatternAlert]) -> List[str]:
        """Get prioritized optimization recommendations"""
        recommendations = set()
        
        for alert in alerts:
            if alert.severity in ['critical', 'high']:
                recommendations.add(alert.recommendation)
        
        return list(recommendations)[:5]  # Top 5 recommendations
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
        logger.info("🛑 Async Cost Monitor stopped")

# Global monitor instance
_global_monitor: Optional[AsyncCostMonitor] = None

def get_async_cost_monitor() -> AsyncCostMonitor:
    """Get the global async cost monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = AsyncCostMonitor()
    return _global_monitor

# Context manager for tracking async calls
class AsyncCallTracker:
    """Context manager to track async calls"""
    
    def __init__(self, func_name: str, session_reused: bool = False, parallel: bool = False):
        self.func_name = func_name
        self.session_reused = session_reused
        self.parallel = parallel
        self.start_time = None
        self.error_count = 0
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        if exc_type is not None:
            self.error_count = 1
        
        monitor = get_async_cost_monitor()
        monitor.track_async_call(
            self.func_name, 
            self.start_time, 
            end_time,
            self.session_reused,
            self.parallel,
            self.error_count
        )

# Decorator for tracking async functions
def track_async_cost(func_name: str = None, session_reused: bool = False, parallel: bool = False):
    """Decorator to track async function costs"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            name = func_name or func.__name__
            async with AsyncCallTracker(name, session_reused, parallel):
                return await func(*args, **kwargs)
        return wrapper
    return decorator