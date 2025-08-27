"""
Unit Tests for Animation Engine - 60fps Performance Validation
============================================================

Tests the animation_engine.py module for performance targets and functionality.
"""

import pytest
import time
import asyncio
from typing import List, Any
from unittest.mock import Mock, patch

# Import the modules to test
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.cli.ui.animation_engine import (
    AnimationConfig, Animation, TypewriterAnimation, FadeAnimation,
    ProgressSmoothAnimation, VirtualScrollView, VirtualScrollConfig,
    AnimationManager, EasingFunctions, EasingFunction, FrameRateMonitor
)

@pytest.fixture
def animation_config():
    """Standard animation configuration for testing"""
    return AnimationConfig(
        duration_ms=1000,
        fps=60,
        easing=EasingFunction.EASE_IN_OUT,
        auto_reverse=False,
        loop=False
    )

@pytest.fixture
def frame_rate_monitor():
    """Frame rate monitor for testing"""
    return FrameRateMonitor(target_fps=60)

class TestAnimationConfig:
    """Test animation configuration"""
    
    def test_default_config(self):
        """Test default animation configuration"""
        config = AnimationConfig()
        assert config.duration_ms == 1000
        assert config.fps == 30
        assert config.quality == "high"
        assert config.adaptive == True
    
    def test_60fps_config(self):
        """Test 60fps configuration meets performance targets"""
        config = AnimationConfig(fps=60, duration_ms=1000)
        frame_time = 1.0 / config.fps
        
        # Should meet 60fps target (16.67ms per frame)
        assert frame_time <= 0.01667  # 16.67ms
        assert config.fps >= 60

class TestEasingFunctions:
    """Test easing function implementations"""
    
    def test_linear_easing(self):
        """Test linear easing function"""
        assert EasingFunctions.linear(0.0) == 0.0
        assert EasingFunctions.linear(0.5) == 0.5
        assert EasingFunctions.linear(1.0) == 1.0
    
    def test_ease_in_out(self):
        """Test ease in/out function"""
        result_start = EasingFunctions.ease_in_out(0.0)
        result_mid = EasingFunctions.ease_in_out(0.5)
        result_end = EasingFunctions.ease_in_out(1.0)
        
        assert result_start == 0.0
        assert result_end == 1.0
        assert 0.0 < result_mid < 1.0
    
    def test_bounce_easing(self):
        """Test bounce easing function"""
        result = EasingFunctions.bounce(1.0)
        assert result == 1.0
        
        # Test intermediate values
        mid_result = EasingFunctions.bounce(0.5)
        assert 0.0 <= mid_result <= 1.0
    
    def test_get_function_by_enum(self):
        """Test retrieving easing function by enum"""
        linear_func = EasingFunctions.get_function(EasingFunction.LINEAR)
        assert linear_func(0.5) == 0.5
        
        ease_func = EasingFunctions.get_function(EasingFunction.EASE_IN_OUT)
        assert callable(ease_func)

class TestAnimation:
    """Test base Animation class"""
    
    def test_animation_creation(self, animation_config):
        """Test animation creation and initialization"""
        def test_callback(progress: float):
            return f"Progress: {progress:.2f}"
        
        animation = Animation(animation_config, test_callback)
        assert animation.config == animation_config
        assert animation.target_update_callback == test_callback
        assert animation.is_running == False
        assert animation.current_progress == 0.0
    
    def test_animation_start_stop(self, animation_config):
        """Test animation start and stop functionality"""
        def test_callback(progress: float):
            return f"Progress: {progress:.2f}"
        
        animation = Animation(animation_config, test_callback)
        
        # Start animation
        animation.start()
        assert animation.is_running == True
        assert animation.start_time is not None
        
        # Stop animation
        animation.stop()
        assert animation.is_running == False
    
    def test_animation_frame_rate_limiting(self, animation_config):
        """Test frame rate limiting functionality"""
        frame_times = []
        
        def test_callback(progress: float):
            frame_times.append(time.time())
            return f"Progress: {progress:.2f}"
        
        # Set to 30 FPS for testing
        animation_config.fps = 30
        animation_config.adaptive = True
        animation = Animation(animation_config, test_callback)
        animation.start()
        
        # Update animation multiple times rapidly
        update_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 0.1 and update_count < 10:  # 100ms test
            result = animation.update()
            if result is not None:
                update_count += 1
            time.sleep(0.001)  # 1ms sleep
        
        # Should respect frame rate limits
        expected_frame_time = 1.0 / 30  # ~33.33ms
        assert animation.frame_time <= expected_frame_time * 1.1  # Allow 10% tolerance
    
    @pytest.mark.benchmark
    def test_animation_update_performance(self, animation_config, benchmark):
        """Benchmark animation update performance"""
        def test_callback(progress: float):
            return f"Progress: {progress:.2f}"
        
        animation = Animation(animation_config, test_callback)
        animation.start()
        
        # Benchmark animation update
        result = benchmark(animation.update)
        
        # Should complete within performance target (< 1ms for 60fps headroom)
        assert benchmark.stats['mean'] < 0.001  # 1ms

class TestTypewriterAnimation:
    """Test typewriter animation implementation"""
    
    def test_typewriter_creation(self):
        """Test typewriter animation creation"""
        config = AnimationConfig(duration_ms=2000, fps=20)
        text = "Hello, World!"
        
        animation = TypewriterAnimation(text, config)
        assert animation.text == text
        assert animation.config == config
    
    def test_typewriter_progress(self):
        """Test typewriter animation progress"""
        config = AnimationConfig(duration_ms=100, fps=60)  # Fast for testing
        text = "Test"
        
        animation = TypewriterAnimation(text, config)
        animation.start()
        
        # Let animation run for a bit
        time.sleep(0.05)  # 50ms
        result = animation.update()
        
        # Should have some content visible
        if result:
            content_str = str(result)
            assert len(content_str) > 0
            # Should show partial text
            assert len(content_str) <= len(text) + 1  # +1 for possible cursor
    
    @pytest.mark.performance
    def test_typewriter_60fps_capability(self):
        """Test typewriter animation can maintain 60fps"""
        config = AnimationConfig(duration_ms=1000, fps=60)
        text = "Performance test text for 60fps validation"
        
        animation = TypewriterAnimation(text, config)
        animation.start()
        
        frame_times = []
        frame_count = 0
        max_frames = 60  # Test 1 second worth
        
        start_time = time.time()
        
        while frame_count < max_frames and (time.time() - start_time) < 1.1:
            frame_start = time.time()
            result = animation.update()
            frame_end = time.time()
            
            if result is not None:
                frame_times.append(frame_end - frame_start)
                frame_count += 1
            
            time.sleep(0.001)  # Minimal sleep to allow other operations
        
        # Verify performance
        if frame_times:
            avg_frame_time = sum(frame_times) / len(frame_times)
            assert avg_frame_time < 0.01667  # 16.67ms for 60fps
            assert len(frame_times) >= 30  # Should achieve reasonable frame count

class TestVirtualScrollView:
    """Test virtual scrolling implementation"""
    
    def test_virtual_scroll_creation(self):
        """Test virtual scroll view creation"""
        items = list(range(100))
        config = VirtualScrollConfig(viewport_height=10)
        
        def render_item(item, index):
            return f"Item {item} at {index}"
        
        scroll_view = VirtualScrollView(items, config, render_item)
        assert len(scroll_view.items) == 100
        assert scroll_view.config.viewport_height == 10
        assert scroll_view.viewport_start == 0
        assert scroll_view.viewport_end == 10
    
    def test_virtual_scroll_performance_with_large_dataset(self):
        """Test virtual scrolling performance with large datasets"""
        # Create large dataset
        items = list(range(10000))
        config = VirtualScrollConfig(
            viewport_height=20,
            buffer_size=40,
            lazy_render=True
        )
        
        def render_item(item, index):
            return f"Item {item}"
        
        scroll_view = VirtualScrollView(items, config, render_item)
        
        # Test scrolling performance
        start_time = time.time()
        
        # Scroll through various positions
        for position in [0, 100, 500, 1000, 5000, 9900]:
            scroll_view.scroll_to(position, animate=False)
            visible_items = scroll_view.get_visible_items()
            
            # Should always return viewport_height items (or remaining items)
            expected_count = min(config.viewport_height, len(items) - position)
            assert len(visible_items) <= expected_count
        
        total_time = time.time() - start_time
        # Should complete all scroll operations quickly
        assert total_time < 0.1  # 100ms for all scroll operations
    
    @pytest.mark.memory
    def test_virtual_scroll_memory_efficiency(self):
        """Test virtual scrolling memory efficiency"""
        # Large dataset
        items = list(range(50000))
        config = VirtualScrollConfig(
            viewport_height=25,
            buffer_size=50,
            lazy_render=True
        )
        
        def render_item(item, index):
            return f"Item {item} - Content for item {item}"
        
        scroll_view = VirtualScrollView(items, config, render_item)
        
        # Scroll through dataset to populate cache
        for i in range(0, 1000, 100):
            scroll_view.scroll_to(i, animate=False)
            scroll_view.get_visible_items()
        
        # Cache should be limited
        cache_size = len(scroll_view.render_cache)
        assert cache_size <= config.buffer_size * 2  # Should respect cache limits
        
        # Memory usage should be reasonable
        import sys
        cache_memory = sum(sys.getsizeof(item) for item in scroll_view.render_cache.values())
        # Should use less than 1MB for cache
        assert cache_memory < 1024 * 1024

class TestAnimationManager:
    """Test animation manager functionality"""
    
    def test_animation_manager_creation(self):
        """Test animation manager creation"""
        manager = AnimationManager(max_concurrent_animations=5)
        assert manager.max_concurrent == 5
        assert len(manager.active_animations) == 0
        assert len(manager.animation_queue) == 0
    
    def test_animation_manager_concurrency(self, animation_config):
        """Test animation manager concurrent animation handling"""
        manager = AnimationManager(max_concurrent_animations=2)
        
        # Create test animations
        animations = []
        for i in range(5):
            def callback(progress: float, i=i):
                return f"Animation {i}: {progress:.2f}"
            
            animation = Animation(animation_config, callback)
            animations.append(animation)
            manager.add_animation(animation)
        
        # Should have 2 active and 3 queued
        assert len(manager.active_animations) <= 2
        assert len(manager.animation_queue) >= 3
    
    @pytest.mark.performance
    def test_animation_manager_update_performance(self, animation_config):
        """Test animation manager update performance with multiple animations"""
        manager = AnimationManager(max_concurrent_animations=10)
        
        # Add multiple animations
        for i in range(8):
            def callback(progress: float, i=i):
                return f"Animation {i}: {progress:.2f}"
            
            animation = Animation(animation_config, callback)
            manager.add_animation(animation)
        
        # Benchmark update performance
        start_time = time.time()
        update_count = 0
        
        while (time.time() - start_time) < 0.1:  # 100ms test
            rendered_content = manager.update_all()
            update_count += 1
        
        total_time = time.time() - start_time
        
        # Should maintain good update rate
        updates_per_second = update_count / total_time
        assert updates_per_second >= 100  # At least 100 updates/second
        
        # Should not take too long per update
        avg_update_time = total_time / update_count
        assert avg_update_time < 0.005  # Less than 5ms per update

class TestFrameRateMonitor:
    """Test frame rate monitoring functionality"""
    
    def test_frame_rate_monitor_creation(self):
        """Test frame rate monitor creation"""
        monitor = FrameRateMonitor(target_fps=60)
        assert monitor.target_fps == 60
        assert monitor.current_fps == 0.0
        assert monitor.frame_drops == 0
    
    def test_frame_rate_monitoring(self, frame_rate_monitor):
        """Test frame rate monitoring accuracy"""
        monitor = frame_rate_monitor
        
        # Simulate 30 FPS for testing
        target_frame_time = 1.0 / 30.0  # ~33.33ms
        
        for _ in range(10):
            frame_start = monitor.start_frame()
            time.sleep(target_frame_time)  # Simulate frame processing
            metrics = monitor.end_frame(frame_start)
        
        # Should measure approximately 30 FPS
        assert 25 <= monitor.current_fps <= 35  # Allow some variance
    
    def test_frame_drop_detection(self, frame_rate_monitor):
        """Test frame drop detection"""
        monitor = frame_rate_monitor
        
        # Simulate normal frame
        frame_start = monitor.start_frame()
        time.sleep(0.01)  # 10ms
        monitor.end_frame(frame_start)
        
        # Simulate slow frame (should be detected as drop)
        frame_start = monitor.start_frame()
        time.sleep(0.05)  # 50ms - much slower than 16.67ms target
        monitor.end_frame(frame_start)
        
        # Should detect frame drop
        assert monitor.frame_drops > 0
    
    def test_adaptive_frame_skipping(self, frame_rate_monitor):
        """Test adaptive frame skipping"""
        monitor = frame_rate_monitor
        monitor.adaptive_enabled = True
        
        # Simulate running slowly
        for _ in range(10):
            frame_start = monitor.start_frame()
            time.sleep(0.05)  # 50ms - very slow
            monitor.end_frame(frame_start)
        
        # Should recommend skipping frames when running slowly
        should_skip = monitor.should_skip_frame()
        assert should_skip == True

# Performance test markers
pytest_plugins = ['pytest_benchmark']

@pytest.mark.performance
class TestOverallPerformance:
    """Overall performance validation tests"""
    
    def test_60fps_target_capability(self):
        """Test overall system capability to maintain 60fps"""
        config = AnimationConfig(fps=60, duration_ms=1000)
        
        # Create multiple animation types
        typewriter = TypewriterAnimation("Performance test", config)
        
        def fade_callback(progress: float):
            return f"Fade: {progress:.2f}"
        
        fade = FadeAnimation(fade_callback, True, config)
        
        # Animation manager
        manager = AnimationManager(max_concurrent_animations=5)
        manager.add_animation(typewriter)
        manager.add_animation(fade)
        
        # Run for 60 frames (1 second at 60fps)
        frame_times = []
        target_frame_time = 1.0 / 60.0  # 16.67ms
        
        start_time = time.time()
        for _ in range(60):
            frame_start = time.time()
            
            # Update all animations
            rendered_content = manager.update_all()
            
            frame_end = time.time()
            frame_times.append(frame_end - frame_start)
            
            # Sleep to maintain frame rate
            elapsed = frame_end - frame_start
            if elapsed < target_frame_time:
                time.sleep(target_frame_time - elapsed)
        
        total_time = time.time() - start_time
        
        # Verify performance
        avg_frame_time = sum(frame_times) / len(frame_times)
        max_frame_time = max(frame_times)
        
        # Should average well under 60fps target
        assert avg_frame_time < 0.01667  # 16.67ms
        
        # No frame should take longer than 20ms (allows some variance)
        assert max_frame_time < 0.020
        
        # Total time should be close to 1 second (allowing overhead)
        assert 0.9 <= total_time <= 1.2
    
    @pytest.mark.memory
    def test_memory_usage_target(self):
        """Test memory usage stays within 200MB target"""
        import tracemalloc
        
        tracemalloc.start()
        
        # Create memory-intensive scenario
        config = AnimationConfig(fps=60)
        manager = AnimationManager(max_concurrent_animations=10)
        
        # Large virtual scroll with many animations
        large_dataset = list(range(10000))
        scroll_config = VirtualScrollConfig(viewport_height=50, buffer_size=100)
        
        def render_item(item, index):
            return f"Large item content {item} with index {index} and more text"
        
        scroll_view = VirtualScrollView(large_dataset, scroll_config, render_item)
        
        # Add many animations
        for i in range(8):
            def callback(progress: float, i=i):
                return f"Memory test animation {i}: {progress:.3f} with content"
            
            animation = Animation(config, callback)
            manager.add_animation(animation)
        
        # Run scenario
        for _ in range(100):
            manager.update_all()
            scroll_view.get_visible_items()
            scroll_view.scroll_to(_ * 10, animate=False)
        
        # Check memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Convert to MB
        current_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)
        
        # Should stay well under 200MB target (allowing for test overhead)
        assert current_mb < 50  # Should be much lower for just animations
        assert peak_mb < 50