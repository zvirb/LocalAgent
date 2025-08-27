"""
60fps Performance Validation Tests
=================================

Comprehensive performance testing to validate 60fps animation targets
and memory usage under 200MB across all UI components.
"""

import pytest
import time
import threading
import psutil
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

# Performance monitoring
import tracemalloc
from memory_profiler import memory_usage
import gc

# Import modules to test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.cli.ui.animation_engine import (
    AnimationManager, AnimationConfig, TypewriterAnimation, 
    VirtualScrollView, VirtualScrollConfig, AdvancedProgressBar
)
from app.cli.ui.rendering_system import RenderingSystem, RenderingSystemConfig
from app.cli.ui.performance_monitor import get_rendering_optimizer
from app.cli.ui.memory_optimizer import get_memory_optimizer

@dataclass
class PerformanceMetrics:
    """Performance measurement results"""
    fps_achieved: float
    avg_frame_time_ms: float
    max_frame_time_ms: float
    memory_peak_mb: float
    memory_avg_mb: float
    cpu_usage_percent: float
    frame_drops: int
    total_frames: int
    test_duration_s: float

class PerformanceProfiler:
    """Real-time performance profiler for UI components"""
    
    def __init__(self, target_fps: int = 60, memory_limit_mb: int = 200):
        self.target_fps = target_fps
        self.memory_limit_mb = memory_limit_mb
        self.target_frame_time_ms = 1000.0 / target_fps  # Convert to ms
        
        # Tracking
        self.frame_times = []
        self.memory_samples = []
        self.cpu_samples = []
        self.frame_drops = 0
        self.start_time = None
        
        # Process monitoring
        self.process = psutil.Process()
        
    def start_profiling(self):
        """Start performance profiling"""
        self.start_time = time.time()
        self.frame_times.clear()
        self.memory_samples.clear()
        self.cpu_samples.clear()
        self.frame_drops = 0
        
        # Start memory tracing
        tracemalloc.start()
        gc.collect()  # Clean start
    
    def record_frame(self, frame_duration_ms: float):
        """Record frame timing"""
        self.frame_times.append(frame_duration_ms)
        
        if frame_duration_ms > self.target_frame_time_ms * 1.5:
            self.frame_drops += 1
        
        # Sample memory and CPU periodically
        if len(self.frame_times) % 10 == 0:  # Every 10th frame
            try:
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                self.memory_samples.append(memory_mb)
                
                cpu_percent = self.process.cpu_percent()
                self.cpu_samples.append(cpu_percent)
            except:
                pass  # Ignore sampling errors
    
    def stop_profiling(self) -> PerformanceMetrics:
        """Stop profiling and return metrics"""
        end_time = time.time()
        test_duration = end_time - (self.start_time or end_time)
        
        # Calculate FPS and frame metrics
        total_frames = len(self.frame_times)
        fps_achieved = total_frames / test_duration if test_duration > 0 else 0
        
        avg_frame_time_ms = sum(self.frame_times) / max(1, total_frames)
        max_frame_time_ms = max(self.frame_times) if self.frame_times else 0
        
        # Memory metrics
        memory_peak_mb = max(self.memory_samples) if self.memory_samples else 0
        memory_avg_mb = sum(self.memory_samples) / max(1, len(self.memory_samples))
        
        # CPU metrics
        cpu_avg = sum(self.cpu_samples) / max(1, len(self.cpu_samples))
        
        # Get tracemalloc memory
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return PerformanceMetrics(
            fps_achieved=fps_achieved,
            avg_frame_time_ms=avg_frame_time_ms,
            max_frame_time_ms=max_frame_time_ms,
            memory_peak_mb=max(memory_peak_mb, peak / (1024 * 1024)),
            memory_avg_mb=memory_avg_mb,
            cpu_usage_percent=cpu_avg,
            frame_drops=self.frame_drops,
            total_frames=total_frames,
            test_duration_s=test_duration
        )

@pytest.fixture
def performance_profiler():
    """Performance profiler fixture"""
    return PerformanceProfiler(target_fps=60, memory_limit_mb=200)

@pytest.fixture
def rendering_system():
    """Rendering system with performance configuration"""
    config = RenderingSystemConfig(
        target_fps=60,
        memory_limit_mb=200,
        enable_animations=True,
        enable_adaptive_quality=True
    )
    return RenderingSystem(config)

class TestAnimationPerformance:
    """Test animation system performance at 60fps"""
    
    @pytest.mark.performance
    def test_single_animation_60fps(self, performance_profiler):
        """Test single animation maintains 60fps"""
        config = AnimationConfig(fps=60, duration_ms=2000)
        text = "Performance testing animation with longer content to simulate realistic usage"
        
        animation = TypewriterAnimation(text, config)
        animation.start()
        
        performance_profiler.start_profiling()
        
        # Run animation for 2 seconds at 60fps
        frame_count = 0
        target_frames = 120  # 2 seconds * 60fps
        
        while frame_count < target_frames and animation.is_running:
            frame_start = time.time()
            
            result = animation.update()
            
            frame_end = time.time()
            frame_duration_ms = (frame_end - frame_start) * 1000
            
            performance_profiler.record_frame(frame_duration_ms)
            frame_count += 1
            
            # Maintain frame rate
            target_frame_time = 1.0 / 60
            elapsed = frame_end - frame_start
            if elapsed < target_frame_time:
                time.sleep(target_frame_time - elapsed)
        
        metrics = performance_profiler.stop_profiling()
        
        # Validate 60fps target
        assert metrics.fps_achieved >= 55  # Allow 5fps tolerance
        assert metrics.avg_frame_time_ms <= 18.0  # Target: 16.67ms, allow 1.33ms tolerance
        assert metrics.max_frame_time_ms <= 25.0  # No frame should exceed 25ms
        assert metrics.frame_drops <= 5  # Max 5 frame drops in 120 frames
    
    @pytest.mark.performance
    def test_multiple_animations_60fps(self, performance_profiler):
        """Test multiple concurrent animations maintain 60fps"""
        manager = AnimationManager(max_concurrent_animations=8)
        config = AnimationConfig(fps=60, duration_ms=3000)
        
        # Create multiple different animations
        animations = []
        
        # Typewriter animations
        for i in range(3):
            text = f"Concurrent animation {i} with varying content lengths and complexity"
            animation = TypewriterAnimation(text, config)
            animations.append(animation)
            manager.add_animation(animation)
        
        # Fade animations
        from rich.text import Text
        for i in range(3):
            content = Text(f"Fade animation content {i}")
            from app.cli.ui.animation_engine import FadeAnimation
            animation = FadeAnimation(content, fade_in=True, config=config)
            animations.append(animation)
            manager.add_animation(animation)
        
        performance_profiler.start_profiling()
        
        # Run for 2 seconds
        frame_count = 0
        target_frames = 120
        
        while frame_count < target_frames:
            frame_start = time.time()
            
            rendered_content = manager.update_all()
            
            frame_end = time.time()
            frame_duration_ms = (frame_end - frame_start) * 1000
            
            performance_profiler.record_frame(frame_duration_ms)
            frame_count += 1
            
            # Frame rate maintenance
            target_frame_time = 1.0 / 60
            elapsed = frame_end - frame_start
            if elapsed < target_frame_time:
                time.sleep(target_frame_time - elapsed)
        
        metrics = performance_profiler.stop_profiling()
        
        # Validate multi-animation performance
        assert metrics.fps_achieved >= 50  # Allow more tolerance for multiple animations
        assert metrics.avg_frame_time_ms <= 20.0  # Slightly relaxed for multiple animations
        assert metrics.max_frame_time_ms <= 30.0
        assert metrics.frame_drops <= 10  # More tolerance for complex scenario
    
    @pytest.mark.performance
    def test_virtual_scroll_60fps(self, performance_profiler):
        """Test virtual scrolling maintains 60fps with large datasets"""
        # Large dataset
        items = [f"Virtual scroll item {i} with content and data" for i in range(5000)]
        
        config = VirtualScrollConfig(
            viewport_height=25,
            buffer_size=50,
            smooth_scroll=True,
            lazy_render=True
        )
        
        def render_item(item, index):
            return f"[{index:04d}] {item}"
        
        scroll_view = VirtualScrollView(items, config, render_item)
        
        performance_profiler.start_profiling()
        
        # Simulate scrolling through dataset
        frame_count = 0
        target_frames = 180  # 3 seconds
        scroll_positions = [i * 20 for i in range(100)]  # Various positions
        
        while frame_count < target_frames:
            frame_start = time.time()
            
            # Scroll to different positions
            position = scroll_positions[frame_count % len(scroll_positions)]
            scroll_view.scroll_to(position, animate=True)
            
            # Render viewport
            rendered = scroll_view.render_viewport()
            
            frame_end = time.time()
            frame_duration_ms = (frame_end - frame_start) * 1000
            
            performance_profiler.record_frame(frame_duration_ms)
            frame_count += 1
            
            # Frame rate maintenance
            time.sleep(max(0, (1.0 / 60) - (frame_end - frame_start)))
        
        metrics = performance_profiler.stop_profiling()
        
        # Virtual scrolling should be very efficient
        assert metrics.fps_achieved >= 55
        assert metrics.avg_frame_time_ms <= 16.0  # Should be very fast
        assert metrics.max_frame_time_ms <= 25.0
        assert metrics.frame_drops <= 5

class TestMemoryPerformance:
    """Test memory usage stays within 200MB target"""
    
    @pytest.mark.memory
    def test_animation_memory_usage(self, performance_profiler):
        """Test animation system memory usage"""
        manager = AnimationManager(max_concurrent_animations=10)
        config = AnimationConfig(fps=60, duration_ms=5000)
        
        # Create memory-intensive scenario
        animations = []
        for i in range(10):
            # Large text content
            text = f"Memory test animation {i}: " + "Lorem ipsum dolor sit amet. " * 100
            animation = TypewriterAnimation(text, config)
            animations.append(animation)
            manager.add_animation(animation)
        
        performance_profiler.start_profiling()
        
        # Run for extended period to test memory leaks
        frame_count = 0
        target_frames = 300  # 5 seconds
        
        while frame_count < target_frames:
            frame_start = time.time()
            
            rendered_content = manager.update_all()
            
            # Force some garbage collection pressure
            if frame_count % 60 == 0:
                gc.collect()
            
            frame_end = time.time()
            frame_duration_ms = (frame_end - frame_start) * 1000
            
            performance_profiler.record_frame(frame_duration_ms)
            frame_count += 1
            
            time.sleep(max(0, (1.0 / 60) - (frame_end - frame_start)))
        
        metrics = performance_profiler.stop_profiling()
        
        # Memory should stay well under 200MB target
        assert metrics.memory_peak_mb < 100  # Should be much lower for animations only
        assert metrics.memory_avg_mb < 50
    
    @pytest.mark.memory
    def test_virtual_scroll_memory_efficiency(self, performance_profiler):
        """Test virtual scrolling memory efficiency with massive datasets"""
        # Huge dataset to test memory management
        items = [f"Large dataset item {i} with substantial content: " + "x" * 200 
                for i in range(50000)]
        
        config = VirtualScrollConfig(
            viewport_height=30,
            buffer_size=60,
            lazy_render=True
        )
        
        def render_item(item, index):
            return f"[{index:05d}] {item[:50]}..."  # Truncate for display
        
        scroll_view = VirtualScrollView(items, config, render_item)
        
        performance_profiler.start_profiling()
        
        # Scroll through large portions of dataset
        frame_count = 0
        target_frames = 200
        
        while frame_count < target_frames:
            frame_start = time.time()
            
            # Jump to random positions to test cache management
            position = (frame_count * 250) % (len(items) - 100)
            scroll_view.scroll_to(position, animate=False)
            
            rendered = scroll_view.get_visible_items()
            
            frame_end = time.time()
            frame_duration_ms = (frame_end - frame_start) * 1000
            
            performance_profiler.record_frame(frame_duration_ms)
            frame_count += 1
            
            time.sleep(max(0, (1.0 / 60) - (frame_end - frame_start)))
        
        metrics = performance_profiler.stop_profiling()
        
        # Memory should be well managed despite large dataset
        assert metrics.memory_peak_mb < 150  # Well under 200MB target
        assert metrics.fps_achieved >= 55  # Should maintain performance
    
    @pytest.mark.memory
    def test_memory_leak_detection(self, performance_profiler):
        """Test for memory leaks over extended periods"""
        manager = AnimationManager(max_concurrent_animations=5)
        config = AnimationConfig(fps=60, duration_ms=1000)  # Short duration
        
        performance_profiler.start_profiling()
        
        # Repeatedly create and destroy animations
        frame_count = 0
        target_frames = 600  # 10 seconds
        animation_cycle = 0
        
        memory_samples_over_time = []
        
        while frame_count < target_frames:
            frame_start = time.time()
            
            # Create new animation every 60 frames (1 second)
            if frame_count % 60 == 0:
                text = f"Leak test animation {animation_cycle}"
                animation = TypewriterAnimation(text, config)
                manager.add_animation(animation)
                animation_cycle += 1
            
            rendered_content = manager.update_all()
            
            # Sample memory every 30 frames
            if frame_count % 30 == 0:
                try:
                    memory_info = psutil.Process().memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                    memory_samples_over_time.append(memory_mb)
                except:
                    pass
            
            frame_end = time.time()
            frame_duration_ms = (frame_end - frame_start) * 1000
            
            performance_profiler.record_frame(frame_duration_ms)
            frame_count += 1
            
            time.sleep(max(0, (1.0 / 60) - (frame_end - frame_start)))
        
        metrics = performance_profiler.stop_profiling()
        
        # Check for memory leak patterns
        if len(memory_samples_over_time) >= 4:
            # Compare first quarter vs last quarter
            first_quarter = memory_samples_over_time[:len(memory_samples_over_time)//4]
            last_quarter = memory_samples_over_time[-len(memory_samples_over_time)//4:]
            
            avg_first = sum(first_quarter) / len(first_quarter)
            avg_last = sum(last_quarter) / len(last_quarter)
            
            # Memory should not grow significantly over time
            growth_percentage = ((avg_last - avg_first) / avg_first) * 100
            assert growth_percentage < 25  # Less than 25% growth over test period
        
        # Overall memory should stay under target
        assert metrics.memory_peak_mb < 200

class TestIntegratedPerformance:
    """Test integrated system performance"""
    
    @pytest.mark.performance
    @pytest.mark.integration
    def test_full_rendering_system_performance(self, performance_profiler, rendering_system):
        """Test complete rendering system performance"""
        
        # Initialize rendering system
        rendering_system.initialize()
        console = rendering_system.create_optimized_console()
        
        performance_profiler.start_profiling()
        
        frame_count = 0
        target_frames = 240  # 4 seconds at 60fps
        
        while frame_count < target_frames:
            frame_start = time.time()
            
            # Use rendering system's optimized context
            with rendering_system.optimized_rendering_context() as context:
                if not context.get("skip_frame", False):
                    # Create complex content
                    from rich.table import Table
                    from rich.panel import Panel
                    from rich.text import Text
                    
                    table = Table(title=f"Frame {frame_count}")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")
                    
                    table.add_row("Frame", str(frame_count))
                    table.add_row("FPS Target", "60.0")
                    table.add_row("Memory Target", "< 200MB")
                    
                    panel = Panel(table, title="Performance Monitor")
                    
                    # Render content
                    rendering_system.render_content(panel, console)
            
            frame_end = time.time()
            frame_duration_ms = (frame_end - frame_start) * 1000
            
            performance_profiler.record_frame(frame_duration_ms)
            frame_count += 1
            
            # Frame rate control
            time.sleep(max(0, (1.0 / 60) - (frame_end - frame_start)))
        
        metrics = performance_profiler.stop_profiling()
        
        # Full system should meet all targets
        assert metrics.fps_achieved >= 50  # Integrated system tolerance
        assert metrics.avg_frame_time_ms <= 22.0  # Slightly relaxed for full system
        assert metrics.memory_peak_mb < 200  # Must meet memory target
        assert metrics.frame_drops <= 15  # Allow some drops for complex rendering
    
    @pytest.mark.stress
    def test_stress_test_performance(self, performance_profiler):
        """Stress test with maximum load"""
        
        # Maximum concurrent animations
        manager = AnimationManager(max_concurrent_animations=15)
        config = AnimationConfig(fps=60, duration_ms=3000)
        
        # Multiple virtual scroll views
        scroll_views = []
        for i in range(3):
            items = [f"Stress test item {j} in view {i}" for j in range(1000)]
            scroll_config = VirtualScrollConfig(viewport_height=20, buffer_size=40)
            
            def render_item(item, index, view_id=i):
                return f"View{view_id}[{index}]: {item}"
            
            scroll_view = VirtualScrollView(items, scroll_config, render_item)
            scroll_views.append(scroll_view)
        
        # Many animations
        for i in range(12):
            text = f"Stress test animation {i}: " + "Content " * 50
            animation = TypewriterAnimation(text, config)
            manager.add_animation(animation)
        
        performance_profiler.start_profiling()
        
        frame_count = 0
        target_frames = 300  # 5 seconds
        
        while frame_count < target_frames:
            frame_start = time.time()
            
            # Update all animations
            rendered_animations = manager.update_all()
            
            # Update all scroll views
            for i, scroll_view in enumerate(scroll_views):
                position = (frame_count + i * 50) % 900
                scroll_view.scroll_to(position, animate=True)
                scroll_view.render_viewport()
            
            frame_end = time.time()
            frame_duration_ms = (frame_end - frame_start) * 1000
            
            performance_profiler.record_frame(frame_duration_ms)
            frame_count += 1
            
            # Minimal sleep to allow system breathing room
            time.sleep(max(0, (1.0 / 60) - (frame_end - frame_start)))
        
        metrics = performance_profiler.stop_profiling()
        
        # Even under stress, should maintain reasonable performance
        assert metrics.fps_achieved >= 40  # Relaxed for stress test
        assert metrics.memory_peak_mb < 200  # Must not exceed memory target
        assert metrics.avg_frame_time_ms <= 30.0  # Allow higher frame times under stress
    
    @pytest.mark.benchmark
    def test_performance_benchmarks(self, benchmark):
        """Benchmark individual component performance"""
        
        config = AnimationConfig(fps=60)
        manager = AnimationManager(max_concurrent_animations=5)
        
        # Add test animations
        for i in range(5):
            text = f"Benchmark animation {i}"
            animation = TypewriterAnimation(text, config)
            manager.add_animation(animation)
        
        # Benchmark animation update
        def update_animations():
            return manager.update_all()
        
        result = benchmark(update_animations)
        
        # Should complete well within 60fps frame budget
        assert benchmark.stats['mean'] < 0.01  # 10ms for 5 animations
        assert benchmark.stats['max'] < 0.016  # Never exceed single frame budget

@pytest.mark.performance
class TestPerformanceRegression:
    """Test for performance regressions"""
    
    def test_load_previous_benchmarks(self):
        """Load previous performance benchmarks for comparison"""
        benchmark_file = Path("test_results/performance_benchmarks.json")
        
        if benchmark_file.exists():
            with open(benchmark_file, 'r') as f:
                previous_benchmarks = json.load(f)
            
            # Previous benchmarks exist, we can compare
            assert "animation_fps" in previous_benchmarks
            assert "memory_usage_mb" in previous_benchmarks
        else:
            # No previous benchmarks, this will create baseline
            pytest.skip("No previous benchmarks found, creating baseline")
    
    def test_save_current_benchmarks(self, performance_profiler):
        """Save current benchmarks for future regression testing"""
        
        # Quick performance test
        config = AnimationConfig(fps=60, duration_ms=1000)
        animation = TypewriterAnimation("Benchmark test", config)
        animation.start()
        
        performance_profiler.start_profiling()
        
        for _ in range(60):  # 1 second
            frame_start = time.time()
            animation.update()
            frame_end = time.time()
            
            performance_profiler.record_frame((frame_end - frame_start) * 1000)
            time.sleep(max(0, (1.0 / 60) - (frame_end - frame_start)))
        
        metrics = performance_profiler.stop_profiling()
        
        # Save benchmark data
        benchmark_data = {
            "animation_fps": metrics.fps_achieved,
            "memory_usage_mb": metrics.memory_peak_mb,
            "avg_frame_time_ms": metrics.avg_frame_time_ms,
            "timestamp": time.time(),
            "test_version": "1.0"
        }
        
        # Ensure results directory exists
        results_dir = Path("test_results")
        results_dir.mkdir(exist_ok=True)
        
        benchmark_file = results_dir / "performance_benchmarks.json"
        with open(benchmark_file, 'w') as f:
            json.dump(benchmark_data, f, indent=2)

# Custom pytest markers for performance tests
pytest_plugins = ['pytest_benchmark']

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", 
        "performance: marks tests as performance tests (deselect with '-m \"not performance\"')"
    )
    config.addinivalue_line(
        "markers",
        "memory: marks tests as memory usage tests"
    )
    config.addinivalue_line(
        "markers",
        "stress: marks tests as stress/load tests"
    )