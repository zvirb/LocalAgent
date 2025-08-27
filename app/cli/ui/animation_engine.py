"""
Animation and Effects Pipeline
Smooth progress animations, virtual scrolling, and efficient text rendering
"""

import asyncio
import time
import math
from typing import Dict, Any, List, Optional, Callable, Iterator, AsyncIterator, Union
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import threading
from collections import deque

from rich.console import Console, RenderableType
from rich.text import Text
from rich.panel import Panel
from rich.progress import Progress, ProgressColumn, Task
from rich.live import Live
from rich.layout import Layout
from rich.table import Table
from rich.align import Align
from rich.columns import Columns
from rich.spinner import Spinner


class AnimationType(Enum):
    """Animation types with performance characteristics"""
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    SLIDE_IN = "slide_in"
    SLIDE_OUT = "slide_out"
    BOUNCE = "bounce"
    PULSE = "pulse"
    TYPEWRITER = "typewriter"
    PROGRESS_SMOOTH = "progress_smooth"
    SPINNER_CUSTOM = "spinner_custom"


class EasingFunction(Enum):
    """Easing functions for smooth animations"""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"


@dataclass
class AnimationConfig:
    """Animation configuration with performance optimization"""
    duration_ms: int = 1000
    fps: int = 30
    easing: EasingFunction = EasingFunction.EASE_IN_OUT
    auto_reverse: bool = False
    loop: bool = False
    delay_ms: int = 0
    
    # Performance settings
    quality: str = "high"  # "low", "medium", "high"
    adaptive: bool = True
    skip_frames: bool = False
    max_concurrent: int = 5


@dataclass
class VirtualScrollConfig:
    """Virtual scrolling configuration"""
    viewport_height: int = 10
    buffer_size: int = 20
    item_height: int = 1
    smooth_scroll: bool = True
    scroll_sensitivity: float = 1.0
    lazy_render: bool = True


class EasingFunctions:
    """Collection of easing functions for animations"""
    
    @staticmethod
    def linear(t: float) -> float:
        return t
    
    @staticmethod
    def ease_in(t: float) -> float:
        return t * t
    
    @staticmethod
    def ease_out(t: float) -> float:
        return 1 - (1 - t) ** 2
    
    @staticmethod
    def ease_in_out(t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        else:
            return 1 - 2 * (1 - t) ** 2
    
    @staticmethod
    def bounce(t: float) -> float:
        if t < 1/2.75:
            return 7.5625 * t * t
        elif t < 2/2.75:
            t -= 1.5/2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5/2.75:
            t -= 2.25/2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625/2.75
            return 7.5625 * t * t + 0.984375
    
    @staticmethod
    def elastic(t: float) -> float:
        if t == 0 or t == 1:
            return t
        p = 0.3
        s = p / 4
        return -(2 ** (10 * (t - 1))) * math.sin((t - 1 - s) * (2 * math.pi) / p)
    
    @classmethod
    def get_function(cls, easing: EasingFunction) -> Callable[[float], float]:
        """Get easing function by enum"""
        mapping = {
            EasingFunction.LINEAR: cls.linear,
            EasingFunction.EASE_IN: cls.ease_in,
            EasingFunction.EASE_OUT: cls.ease_out,
            EasingFunction.EASE_IN_OUT: cls.ease_in_out,
            EasingFunction.BOUNCE: cls.bounce,
            EasingFunction.ELASTIC: cls.elastic,
        }
        return mapping.get(easing, cls.linear)


class Animation:
    """Base animation class with frame rate optimization"""
    
    def __init__(self, config: AnimationConfig, target_update_callback: Callable[[float], RenderableType]):
        self.config = config
        self.target_update_callback = target_update_callback
        self.easing_func = EasingFunctions.get_function(config.easing)
        
        # Animation state
        self.start_time: Optional[float] = None
        self.current_progress = 0.0
        self.is_running = False
        self.is_paused = False
        self.reverse = False
        
        # Performance optimization
        self.frame_time = 1.0 / config.fps
        self.last_render_time = 0.0
        self.frame_skip_count = 0
        
    def start(self):
        """Start the animation"""
        self.start_time = time.time() + (self.config.delay_ms / 1000.0)
        self.is_running = True
        self.is_paused = False
    
    def pause(self):
        """Pause the animation"""
        self.is_paused = True
    
    def resume(self):
        """Resume the animation"""
        self.is_paused = False
    
    def stop(self):
        """Stop the animation"""
        self.is_running = False
        self.is_paused = False
    
    def update(self) -> Optional[RenderableType]:
        """Update animation and return renderable content"""
        if not self.is_running or self.is_paused or not self.start_time:
            return None
        
        current_time = time.time()
        
        # Frame rate limiting
        if self.config.adaptive and (current_time - self.last_render_time) < self.frame_time:
            if self.config.skip_frames:
                self.frame_skip_count += 1
                return None  # Skip this frame
        
        self.last_render_time = current_time
        
        # Calculate progress
        elapsed = current_time - self.start_time
        raw_progress = elapsed / (self.config.duration_ms / 1000.0)
        
        # Handle looping
        if raw_progress >= 1.0:
            if self.config.loop:
                self.start_time = current_time  # Restart
                raw_progress = 0.0
            elif self.config.auto_reverse and not self.reverse:
                self.reverse = True
                self.start_time = current_time
                raw_progress = 0.0
            else:
                self.is_running = False
                raw_progress = 1.0
        
        # Apply easing
        if self.reverse:
            eased_progress = 1.0 - self.easing_func(raw_progress)
        else:
            eased_progress = self.easing_func(raw_progress)
        
        self.current_progress = max(0.0, min(1.0, eased_progress))
        
        # Generate renderable content
        return self.target_update_callback(self.current_progress)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get animation performance statistics"""
        return {
            'is_running': self.is_running,
            'current_progress': self.current_progress,
            'frame_skip_count': self.frame_skip_count,
            'target_fps': self.config.fps,
            'actual_frame_time': self.last_render_time,
        }


class TypewriterAnimation(Animation):
    """Typewriter effect animation with character-by-character reveal"""
    
    def __init__(self, text: str, config: AnimationConfig, style: str = ""):
        self.text = text
        self.style = style
        self.cursor_visible = True
        self.cursor_blink_time = 0.0
        
        def update_callback(progress: float) -> RenderableType:
            chars_to_show = int(len(self.text) * progress)
            visible_text = self.text[:chars_to_show]
            
            # Add blinking cursor
            if progress < 1.0:
                cursor_blink = int(time.time() * 2) % 2 == 0  # Blink every 0.5s
                if cursor_blink:
                    visible_text += "▋"  # Block cursor
            
            if self.style:
                return Text(visible_text, style=self.style)
            return Text(visible_text)
        
        super().__init__(config, update_callback)


class FadeAnimation(Animation):
    """Fade in/out animation with opacity simulation"""
    
    def __init__(self, content: RenderableType, fade_in: bool = True, config: AnimationConfig = None):
        self.content = content
        self.fade_in = fade_in
        
        def update_callback(progress: float) -> RenderableType:
            # Simulate opacity with dimming
            opacity = progress if fade_in else (1.0 - progress)
            
            if opacity < 0.3:
                style = "dim"
            elif opacity < 0.6:
                style = "dim"
            else:
                style = ""
            
            if hasattr(content, 'style'):
                # Rich Text object
                styled_content = Text.from_markup(str(content))
                if style:
                    styled_content.stylize(style)
                return styled_content
            else:
                # Other renderable
                if style and opacity < 0.6:
                    return Panel(content, style=style)
                return content
        
        super().__init__(config or AnimationConfig(), update_callback)


class ProgressSmoothAnimation(Animation):
    """Smooth progress bar animation with momentum"""
    
    def __init__(self, progress: Progress, task_id: int, target_value: float, config: AnimationConfig = None):
        self.progress_bar = progress
        self.task_id = task_id
        self.target_value = target_value
        self.start_value = progress.tasks[task_id].completed
        
        def update_callback(progress: float) -> RenderableType:
            current_value = self.start_value + (self.target_value - self.start_value) * progress
            self.progress_bar.update(self.task_id, completed=current_value)
            return None  # Progress bar handles its own rendering
        
        super().__init__(config or AnimationConfig(duration_ms=500), update_callback)


class VirtualScrollView:
    """High-performance virtual scrolling for large datasets"""
    
    def __init__(self, items: List[Any], config: VirtualScrollConfig, 
                 render_item_callback: Callable[[Any, int], RenderableType]):
        self.items = items
        self.config = config
        self.render_item_callback = render_item_callback
        
        # Scrolling state
        self.scroll_position = 0
        self.viewport_start = 0
        self.viewport_end = min(config.viewport_height, len(items))
        
        # Rendering cache for performance
        self.render_cache: Dict[int, RenderableType] = {}
        self.cache_size_limit = config.buffer_size * 2
        
        # Scroll animation
        self.smooth_scroll_target = 0
        self.scroll_animation: Optional[Animation] = None
    
    def scroll_to(self, index: int, animate: bool = None):
        """Scroll to specific item index"""
        if animate is None:
            animate = self.config.smooth_scroll
        
        target_position = max(0, min(index, len(self.items) - self.config.viewport_height))
        
        if animate and abs(target_position - self.scroll_position) > 1:
            # Animate scroll
            self._animate_scroll_to(target_position)
        else:
            # Instant scroll
            self.scroll_position = target_position
            self._update_viewport()
    
    def scroll_by(self, delta: int, animate: bool = None):
        """Scroll by relative amount"""
        new_position = self.scroll_position + delta
        self.scroll_to(new_position, animate)
    
    def _animate_scroll_to(self, target_position: int):
        """Animate scrolling to target position"""
        start_position = self.scroll_position
        
        def scroll_update(progress: float) -> RenderableType:
            current_position = start_position + (target_position - start_position) * progress
            self.scroll_position = int(current_position)
            self._update_viewport()
            return None
        
        config = AnimationConfig(
            duration_ms=300,
            fps=60,
            easing=EasingFunction.EASE_OUT
        )
        
        self.scroll_animation = Animation(config, scroll_update)
        self.scroll_animation.start()
    
    def _update_viewport(self):
        """Update viewport boundaries"""
        self.viewport_start = max(0, self.scroll_position)
        self.viewport_end = min(
            self.viewport_start + self.config.viewport_height,
            len(self.items)
        )
    
    def get_visible_items(self) -> List[RenderableType]:
        """Get currently visible items as renderables"""
        visible_items = []
        
        # Include buffer items for smooth scrolling
        buffer_start = max(0, self.viewport_start - self.config.buffer_size // 2)
        buffer_end = min(len(self.items), self.viewport_end + self.config.buffer_size // 2)
        
        for i in range(self.viewport_start, self.viewport_end):
            if i >= len(self.items):
                break
            
            # Check cache first
            if i in self.render_cache and not self._item_needs_refresh(i):
                rendered = self.render_cache[i]
            else:
                # Render item
                rendered = self.render_item_callback(self.items[i], i)
                
                # Cache the rendered item
                if self.config.lazy_render:
                    self.render_cache[i] = rendered
                    
                    # Manage cache size
                    if len(self.render_cache) > self.cache_size_limit:
                        self._evict_cache_entries()
            
            visible_items.append(rendered)
        
        return visible_items
    
    def _item_needs_refresh(self, index: int) -> bool:
        """Check if cached item needs refresh"""
        # Simple heuristic - could be enhanced with change detection
        return False
    
    def _evict_cache_entries(self):
        """Evict old cache entries to maintain memory usage"""
        # Remove items far from current viewport
        viewport_center = (self.viewport_start + self.viewport_end) // 2
        
        items_to_remove = []
        for index in self.render_cache:
            distance = abs(index - viewport_center)
            if distance > self.config.buffer_size:
                items_to_remove.append(index)
        
        for index in items_to_remove:
            del self.render_cache[index]
    
    def update_items(self, new_items: List[Any]):
        """Update the item list and refresh cache"""
        self.items = new_items
        self.render_cache.clear()  # Clear cache on data change
        self._update_viewport()
    
    def render_viewport(self) -> RenderableType:
        """Render the current viewport"""
        # Update scroll animation if active
        if self.scroll_animation and self.scroll_animation.is_running:
            self.scroll_animation.update()
        
        visible_items = self.get_visible_items()
        
        if not visible_items:
            return Text("No items to display")
        
        # Combine visible items into a single renderable
        return Columns(visible_items, equal=False, expand=False)
    
    def get_scroll_info(self) -> Dict[str, Any]:
        """Get scrolling information"""
        return {
            'total_items': len(self.items),
            'viewport_size': self.config.viewport_height,
            'scroll_position': self.scroll_position,
            'viewport_start': self.viewport_start,
            'viewport_end': self.viewport_end,
            'cache_size': len(self.render_cache),
            'scroll_percentage': self.scroll_position / max(1, len(self.items) - self.config.viewport_height)
        }


class AnimationManager:
    """Manages multiple animations with performance optimization"""
    
    def __init__(self, max_concurrent_animations: int = 10):
        self.max_concurrent = max_concurrent_animations
        self.active_animations: List[Animation] = []
        self.animation_queue: deque[Animation] = deque()
        
        # Performance tracking
        self.total_frame_time = 0.0
        self.frame_count = 0
        self.performance_mode = "high"  # "low", "medium", "high"
        
        self._lock = threading.Lock()
    
    def add_animation(self, animation: Animation, priority: bool = False):
        """Add animation to manager"""
        with self._lock:
            if len(self.active_animations) < self.max_concurrent:
                self.active_animations.append(animation)
                animation.start()
            else:
                if priority:
                    self.animation_queue.appendleft(animation)
                else:
                    self.animation_queue.append(animation)
    
    def remove_animation(self, animation: Animation):
        """Remove animation from manager"""
        with self._lock:
            if animation in self.active_animations:
                self.active_animations.remove(animation)
                animation.stop()
                
                # Start next queued animation
                if self.animation_queue:
                    next_animation = self.animation_queue.popleft()
                    self.active_animations.append(next_animation)
                    next_animation.start()
    
    def update_all(self) -> List[RenderableType]:
        """Update all active animations"""
        frame_start = time.time()
        rendered_content = []
        
        with self._lock:
            # Update active animations
            finished_animations = []
            
            for animation in self.active_animations:
                content = animation.update()
                if content is not None:
                    rendered_content.append(content)
                
                if not animation.is_running:
                    finished_animations.append(animation)
            
            # Remove finished animations
            for animation in finished_animations:
                self.remove_animation(animation)
        
        # Track performance
        frame_time = time.time() - frame_start
        self.total_frame_time += frame_time
        self.frame_count += 1
        
        # Adaptive performance adjustment
        if self.frame_count % 60 == 0:  # Check every 60 frames
            avg_frame_time = self.total_frame_time / self.frame_count
            self._adjust_performance_mode(avg_frame_time)
        
        return rendered_content
    
    def _adjust_performance_mode(self, avg_frame_time: float):
        """Adjust performance mode based on frame times"""
        if avg_frame_time > 0.020:  # >20ms per frame
            self.performance_mode = "low"
            # Reduce FPS for all animations
            for animation in self.active_animations:
                animation.config.fps = min(15, animation.config.fps)
        elif avg_frame_time > 0.010:  # >10ms per frame
            self.performance_mode = "medium"
            for animation in self.active_animations:
                animation.config.fps = min(30, animation.config.fps)
        else:
            self.performance_mode = "high"
            # Allow full FPS
        
        # Reset counters
        self.total_frame_time = 0.0
        self.frame_count = 0
    
    def pause_all(self):
        """Pause all animations"""
        with self._lock:
            for animation in self.active_animations:
                animation.pause()
    
    def resume_all(self):
        """Resume all animations"""
        with self._lock:
            for animation in self.active_animations:
                animation.resume()
    
    def clear_all(self):
        """Clear all animations"""
        with self._lock:
            for animation in self.active_animations:
                animation.stop()
            self.active_animations.clear()
            self.animation_queue.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get animation manager statistics"""
        with self._lock:
            return {
                'active_animations': len(self.active_animations),
                'queued_animations': len(self.animation_queue),
                'performance_mode': self.performance_mode,
                'average_frame_time_ms': (self.total_frame_time / max(1, self.frame_count)) * 1000,
                'max_concurrent': self.max_concurrent
            }


class AdvancedProgressBar:
    """Advanced progress bar with smooth animations and effects"""
    
    def __init__(self, console: Console, total: float = 100.0):
        self.console = console
        self.total = total
        self.current = 0.0
        self.animation_manager = AnimationManager(max_concurrent_animations=3)
        
        # Visual effects
        self.pulse_effect = False
        self.rainbow_mode = False
        self.show_eta = True
        self.show_rate = True
        
        self.start_time = time.time()
    
    def update(self, value: float, animate: bool = True):
        """Update progress with optional animation"""
        if animate and abs(value - self.current) > 1.0:
            # Animate progress change
            config = AnimationConfig(
                duration_ms=300,
                fps=30,
                easing=EasingFunction.EASE_OUT
            )
            
            animation = ProgressSmoothAnimation(self, 0, value, config)
            self.animation_manager.add_animation(animation)
        else:
            self.current = value
    
    def set_pulse_effect(self, enabled: bool):
        """Enable/disable pulse effect"""
        self.pulse_effect = enabled
    
    def render(self) -> RenderableType:
        """Render the progress bar"""
        # Update animations
        self.animation_manager.update_all()
        
        # Calculate progress percentage
        progress_percent = (self.current / self.total) * 100 if self.total > 0 else 0
        
        # Generate progress bar visualization
        bar_width = 40
        filled_width = int((progress_percent / 100) * bar_width)
        
        # Create progress bar string with effects
        if self.rainbow_mode:
            # Rainbow effect (simplified)
            bar_parts = []
            for i in range(filled_width):
                color_index = i % 7
                colors = ["red", "yellow", "green", "cyan", "blue", "magenta", "white"]
                bar_parts.append(f"[{colors[color_index]}]█[/{colors[color_index]}]")
            bar_str = "".join(bar_parts) + "░" * (bar_width - filled_width)
        else:
            # Standard progress bar
            bar_str = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Add pulse effect
        if self.pulse_effect and filled_width > 0:
            pulse_intensity = (math.sin(time.time() * 4) + 1) / 2  # 0 to 1
            if pulse_intensity > 0.5:
                bar_str = f"[bold green]{bar_str}[/bold green]"
        
        # Calculate ETA and rate
        elapsed = time.time() - self.start_time
        if self.current > 0 and elapsed > 0:
            rate = self.current / elapsed
            eta_seconds = (self.total - self.current) / rate if rate > 0 else 0
            
            # Format display strings
            rate_str = f"{rate:.1f}/sec" if self.show_rate else ""
            eta_str = f"ETA: {eta_seconds:.0f}s" if self.show_eta and eta_seconds > 0 else ""
        else:
            rate_str = ""
            eta_str = ""
        
        # Combine all elements
        progress_text = f"[{bar_str}] {progress_percent:.1f}% {rate_str} {eta_str}"
        
        return Text(progress_text)


# Global animation manager
_global_animation_manager: Optional[AnimationManager] = None

def get_animation_manager() -> AnimationManager:
    """Get global animation manager"""
    global _global_animation_manager
    if _global_animation_manager is None:
        _global_animation_manager = AnimationManager()
    return _global_animation_manager

# Convenience functions
def create_typewriter_effect(text: str, duration_ms: int = 2000, style: str = "") -> TypewriterAnimation:
    """Create typewriter animation effect"""
    config = AnimationConfig(duration_ms=duration_ms, fps=20)
    return TypewriterAnimation(text, config, style)

def create_fade_effect(content: RenderableType, fade_in: bool = True, 
                      duration_ms: int = 1000) -> FadeAnimation:
    """Create fade in/out effect"""
    config = AnimationConfig(duration_ms=duration_ms, fps=30)
    return FadeAnimation(content, fade_in, config)

def create_virtual_scroll_view(items: List[Any], viewport_height: int = 10,
                              render_callback: Callable[[Any, int], RenderableType] = None) -> VirtualScrollView:
    """Create virtual scrolling view"""
    if render_callback is None:
        render_callback = lambda item, index: Text(str(item))
    
    config = VirtualScrollConfig(viewport_height=viewport_height)
    return VirtualScrollView(items, config, render_callback)

@asynccontextmanager
async def animated_progress(console: Console, total: float = 100.0):
    """Async context manager for animated progress"""
    progress_bar = AdvancedProgressBar(console, total)
    try:
        yield progress_bar
    finally:
        progress_bar.animation_manager.clear_all()