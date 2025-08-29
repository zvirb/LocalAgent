#!/usr/bin/env python3
"""
Continuous Performance Monitoring Framework for LocalAgent CLI
Provides ongoing performance monitoring, alerting, and optimization tracking
"""

import asyncio
import time
import json
import psutil
import gc
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import statistics
import logging

@dataclass
class PerformanceMetric:
    """Single performance metric data point"""
    timestamp: float
    value: float
    unit: str
    context: Dict[str, Any] = None

@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    comparison: str = "greater_than"  # greater_than, less_than
    enabled: bool = True

class PerformanceMonitor:
    """Continuous performance monitoring system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.metrics: Dict[str, List[PerformanceMetric]] = {}
        self.thresholds: List[PerformanceThreshold] = self._create_default_thresholds()
        self.alerts: List[Dict[str, Any]] = []
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default monitoring configuration"""
        return {
            'monitoring_interval': 5.0,  # seconds
            'metrics_retention': 3600,   # seconds (1 hour)
            'alert_cooldown': 300,       # seconds (5 minutes)
            'metrics_to_monitor': [
                'cpu_percent',
                'memory_percent',
                'memory_rss_mb',
                'disk_io_read_mb_s',
                'disk_io_write_mb_s',
                'gc_collections',
                'thread_count'
            ],
            'enable_gc_monitoring': True,
            'enable_thread_monitoring': True
        }
    
    def _create_default_thresholds(self) -> List[PerformanceThreshold]:
        """Create default performance thresholds"""
        return [
            PerformanceThreshold("cpu_percent", 70.0, 90.0),
            PerformanceThreshold("memory_percent", 80.0, 95.0),
            PerformanceThreshold("memory_rss_mb", 500.0, 1000.0),
            PerformanceThreshold("thread_count", 50, 100),
            PerformanceThreshold("gc_collections", 10, 50, "greater_than")
        ]
    
    async def start_monitoring(self):
        """Start continuous performance monitoring"""
        if self.monitoring_active:
            self.logger.warning("Performance monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        last_disk_io = psutil.disk_io_counters()
        last_timestamp = time.time()
        
        while self.monitoring_active:
            try:
                current_time = time.time()
                process = psutil.Process()
                
                # Collect system metrics
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                memory_percent = process.memory_percent()
                
                # Calculate disk I/O rates
                current_disk_io = psutil.disk_io_counters()
                time_delta = current_time - last_timestamp
                
                if time_delta > 0 and last_disk_io:
                    read_rate = ((current_disk_io.read_bytes - last_disk_io.read_bytes) / time_delta) / (1024 * 1024)  # MB/s
                    write_rate = ((current_disk_io.write_bytes - last_disk_io.write_bytes) / time_delta) / (1024 * 1024)  # MB/s
                else:
                    read_rate = write_rate = 0
                
                # Thread count
                thread_count = threading.active_count()
                
                # Garbage collection metrics
                gc_stats = gc.get_stats()
                total_collections = sum(stat.get('collections', 0) for stat in gc_stats)
                
                # Record metrics
                metrics_data = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_rss_mb': memory_info.rss / (1024 * 1024),
                    'memory_vms_mb': memory_info.vms / (1024 * 1024),
                    'disk_io_read_mb_s': read_rate,
                    'disk_io_write_mb_s': write_rate,
                    'thread_count': thread_count,
                    'gc_collections': total_collections
                }
                
                # Store metrics
                for metric_name, value in metrics_data.items():
                    if metric_name in self.config['metrics_to_monitor']:
                        self._record_metric(metric_name, value, self._get_metric_unit(metric_name))
                
                # Check thresholds
                await self._check_thresholds(metrics_data)
                
                # Cleanup old metrics
                self._cleanup_old_metrics()
                
                # Update for next iteration
                last_disk_io = current_disk_io
                last_timestamp = current_time
                
                await asyncio.sleep(self.config['monitoring_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1)
    
    def _record_metric(self, name: str, value: float, unit: str, context: Optional[Dict[str, Any]] = None):
        """Record a performance metric"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        metric = PerformanceMetric(
            timestamp=time.time(),
            value=value,
            unit=unit,
            context=context or {}
        )
        
        self.metrics[name].append(metric)
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """Get the unit for a metric"""
        unit_mapping = {
            'cpu_percent': '%',
            'memory_percent': '%',
            'memory_rss_mb': 'MB',
            'memory_vms_mb': 'MB',
            'disk_io_read_mb_s': 'MB/s',
            'disk_io_write_mb_s': 'MB/s',
            'thread_count': 'count',
            'gc_collections': 'count'
        }
        return unit_mapping.get(metric_name, 'unknown')
    
    async def _check_thresholds(self, metrics_data: Dict[str, float]):
        """Check if any metrics exceed thresholds"""
        current_time = time.time()
        
        for threshold in self.thresholds:
            if not threshold.enabled or threshold.metric_name not in metrics_data:
                continue
            
            value = metrics_data[threshold.metric_name]
            
            # Check if threshold is breached
            breached = False
            severity = None
            
            if threshold.comparison == "greater_than":
                if value >= threshold.critical_threshold:
                    breached, severity = True, "critical"
                elif value >= threshold.warning_threshold:
                    breached, severity = True, "warning"
            else:  # less_than
                if value <= threshold.critical_threshold:
                    breached, severity = True, "critical"
                elif value <= threshold.warning_threshold:
                    breached, severity = True, "warning"
            
            if breached:
                # Check cooldown
                recent_alerts = [a for a in self.alerts 
                               if a['metric'] == threshold.metric_name and 
                               current_time - a['timestamp'] < self.config['alert_cooldown']]
                
                if not recent_alerts:
                    alert = {
                        'timestamp': current_time,
                        'metric': threshold.metric_name,
                        'value': value,
                        'threshold': threshold.critical_threshold if severity == "critical" else threshold.warning_threshold,
                        'severity': severity,
                        'message': f"{threshold.metric_name} {severity}: {value:.2f} {self._get_metric_unit(threshold.metric_name)}"
                    }
                    
                    self.alerts.append(alert)
                    self.logger.warning(f"Performance alert: {alert['message']}")
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff_time = time.time() - self.config['metrics_retention']
        
        for metric_name in self.metrics:
            self.metrics[metric_name] = [
                m for m in self.metrics[metric_name] 
                if m.timestamp >= cutoff_time
            ]
    
    def get_metric_statistics(self, metric_name: str, time_window: int = 300) -> Dict[str, float]:
        """Get statistics for a metric over a time window"""
        if metric_name not in self.metrics:
            return {}
        
        cutoff_time = time.time() - time_window
        recent_metrics = [m for m in self.metrics[metric_name] if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        values = [m.value for m in recent_metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'latest': values[-1],
            'unit': recent_metrics[0].unit
        }
    
    def get_performance_report(self, time_window: int = 300) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'time_window_seconds': time_window,
            'metrics': {},
            'alerts': [a for a in self.alerts if time.time() - a['timestamp'] < time_window],
            'summary': {}
        }
        
        # Get statistics for each metric
        for metric_name in self.metrics:
            stats = self.get_metric_statistics(metric_name, time_window)
            if stats:
                report['metrics'][metric_name] = stats
        
        # Generate summary
        critical_alerts = [a for a in report['alerts'] if a['severity'] == 'critical']
        warning_alerts = [a for a in report['alerts'] if a['severity'] == 'warning']
        
        report['summary'] = {
            'monitoring_active': self.monitoring_active,
            'total_alerts': len(report['alerts']),
            'critical_alerts': len(critical_alerts),
            'warning_alerts': len(warning_alerts),
            'health_status': self._calculate_health_status(report['metrics'], critical_alerts)
        }
        
        return report
    
    def _calculate_health_status(self, metrics: Dict[str, Any], critical_alerts: List[Dict]) -> str:
        """Calculate overall system health status"""
        if critical_alerts:
            return "critical"
        
        # Check if any metrics are consistently high
        high_metrics = []
        for metric_name, stats in metrics.items():
            if metric_name.endswith('_percent'):
                if stats.get('mean', 0) > 80:
                    high_metrics.append(metric_name)
        
        if len(high_metrics) >= 2:
            return "warning"
        elif high_metrics:
            return "degraded"
        else:
            return "healthy"

class PerformanceOptimizer:
    """Automated performance optimizer"""
    
    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.optimizations_applied = []
        self.logger = logging.getLogger(__name__)
    
    async def analyze_and_optimize(self) -> List[Dict[str, Any]]:
        """Analyze performance data and apply optimizations"""
        report = self.monitor.get_performance_report()
        optimizations = []
        
        # Memory optimization
        memory_stats = report['metrics'].get('memory_percent', {})
        if memory_stats.get('mean', 0) > 70:
            optimization = await self._optimize_memory()
            if optimization:
                optimizations.append(optimization)
        
        # CPU optimization  
        cpu_stats = report['metrics'].get('cpu_percent', {})
        if cpu_stats.get('mean', 0) > 60:
            optimization = await self._optimize_cpu()
            if optimization:
                optimizations.append(optimization)
        
        # Garbage collection optimization
        gc_stats = report['metrics'].get('gc_collections', {})
        if gc_stats.get('latest', 0) > 20:
            optimization = await self._optimize_garbage_collection()
            if optimization:
                optimizations.append(optimization)
        
        return optimizations
    
    async def _optimize_memory(self) -> Optional[Dict[str, Any]]:
        """Apply memory optimizations"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Get memory info before/after
            process = psutil.Process()
            memory_after = process.memory_info()
            
            optimization = {
                'type': 'memory',
                'action': 'garbage_collection',
                'timestamp': time.time(),
                'objects_collected': collected,
                'memory_after_mb': memory_after.rss / (1024 * 1024),
                'success': collected > 0
            }
            
            self.optimizations_applied.append(optimization)
            self.logger.info(f"Memory optimization applied: collected {collected} objects")
            
            return optimization
            
        except Exception as e:
            self.logger.error(f"Memory optimization failed: {e}")
            return None
    
    async def _optimize_cpu(self) -> Optional[Dict[str, Any]]:
        """Apply CPU optimizations"""
        try:
            # This would implement CPU optimization strategies
            # For now, just log that CPU optimization was attempted
            optimization = {
                'type': 'cpu',
                'action': 'optimization_attempted',
                'timestamp': time.time(),
                'success': True,
                'note': 'CPU optimization placeholder - would implement task scheduling optimization'
            }
            
            self.optimizations_applied.append(optimization)
            self.logger.info("CPU optimization applied")
            
            return optimization
            
        except Exception as e:
            self.logger.error(f"CPU optimization failed: {e}")
            return None
    
    async def _optimize_garbage_collection(self) -> Optional[Dict[str, Any]]:
        """Optimize garbage collection settings"""
        try:
            # Tune garbage collection thresholds
            current_thresholds = gc.get_threshold()
            
            # Increase thresholds to reduce frequency
            new_thresholds = (
                int(current_thresholds[0] * 1.5),
                int(current_thresholds[1] * 1.5),
                int(current_thresholds[2] * 1.5)
            )
            
            gc.set_threshold(*new_thresholds)
            
            optimization = {
                'type': 'garbage_collection',
                'action': 'threshold_adjustment',
                'timestamp': time.time(),
                'old_thresholds': current_thresholds,
                'new_thresholds': new_thresholds,
                'success': True
            }
            
            self.optimizations_applied.append(optimization)
            self.logger.info(f"GC thresholds adjusted: {current_thresholds} -> {new_thresholds}")
            
            return optimization
            
        except Exception as e:
            self.logger.error(f"GC optimization failed: {e}")
            return None

async def main():
    """Demonstrate performance monitoring framework"""
    print("🔍 Starting Performance Monitoring Framework Demo")
    
    # Create monitor
    monitor = PerformanceMonitor()
    optimizer = PerformanceOptimizer(monitor)
    
    try:
        # Start monitoring
        await monitor.start_monitoring()
        print("✅ Performance monitoring started")
        
        # Let it run for a short time
        print("📊 Collecting performance data...")
        await asyncio.sleep(10)
        
        # Generate report
        report = monitor.get_performance_report()
        print(f"📈 Performance Report Generated:")
        print(f"   Health Status: {report['summary']['health_status']}")
        print(f"   Total Alerts: {report['summary']['total_alerts']}")
        print(f"   Metrics Collected: {len(report['metrics'])}")
        
        # Show some key metrics
        for metric_name, stats in list(report['metrics'].items())[:3]:
            print(f"   {metric_name}: {stats['latest']:.2f} {stats['unit']} (avg: {stats['mean']:.2f})")
        
        # Apply optimizations
        print("\n🔧 Running performance optimizations...")
        optimizations = await optimizer.analyze_and_optimize()
        
        if optimizations:
            print(f"✅ Applied {len(optimizations)} optimizations:")
            for opt in optimizations:
                print(f"   - {opt['type']}: {opt['action']}")
        else:
            print("ℹ️ No optimizations needed at this time")
        
        # Save detailed report
        report_file = Path(__file__).parent.parent / "docs" / "performance" / "monitoring_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"💾 Detailed report saved to: {report_file}")
        
    finally:
        await monitor.stop_monitoring()
        print("🛑 Performance monitoring stopped")

if __name__ == "__main__":
    asyncio.run(main())