"""
Visual Rendering Performance Monitor
Frame rate monitoring, adaptive rendering, and GPU acceleration detection
"""

import asyncio
import time
import threading
import psutil
from typing import Dict, Any, Optional, Callable, List, NamedTuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import sys
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.text import Text


class PerformanceMetrics(NamedTuple):
    """Performance metrics snapshot"""
    frame_time_ms: float
    fps: float
    memory_usage_mb: float
    cpu_usage_percent: float
    terminal_capabilities: Dict[str, bool]
    rendering_mode: str


@dataclass
class RenderingConfig:
    """Dynamic rendering configuration"""
    target_fps: int = 60
    max_frame_time_ms: float = 16.67  # ~60fps
    adaptive_rendering: bool = True
    gpu_acceleration: bool = False
    terminal_optimized: bool = True
    memory_limit_mb: int = 200
    performance_tier: str = "auto"  # "high", "medium", "low", "auto"
    
    # Advanced settings
    frame_buffer_size: int = 3
    render_queue_size: int = 100
    animation_quality: str = "high"  # "high", "medium", "low"
    text_rendering_mode: str = "optimized"  # "raw", "optimized", "cached"


@dataclass 
class TerminalCapabilities:
    """Terminal capability detection"""
    supports_256_colors: bool = False
    supports_true_color: bool = False
    supports_unicode: bool = False
    supports_mouse: bool = False
    width: int = 80
    height: int = 24
    terminal_type: str = "unknown"
    ssh_connection: bool = False
    
    # Performance characteristics
    estimated_latency_ms: float = 0.0
    render_speed_factor: float = 1.0
    memory_constraints: bool = False


class TerminalDetector:
    """Advanced terminal capability detection and optimization"""
    
    def __init__(self):
        self.capabilities: Optional[TerminalCapabilities] = None
        self._detection_cache: Dict[str, Any] = {}
        
    def detect_capabilities(self) -> TerminalCapabilities:
        """Comprehensive terminal capability detection"""
        if self.capabilities:
            return self.capabilities
            
        caps = TerminalCapabilities()
        
        # Basic terminal info
        caps.width, caps.height = self._get_terminal_size()
        caps.terminal_type = self._detect_terminal_type()
        caps.ssh_connection = self._is_ssh_connection()
        
        # Color support detection
        caps.supports_256_colors = self._test_256_colors()
        caps.supports_true_color = self._test_true_color()
        caps.supports_unicode = self._test_unicode()
        caps.supports_mouse = self._test_mouse_support()
        
        # Performance characteristics
        caps.estimated_latency_ms = self._measure_terminal_latency()
        caps.render_speed_factor = self._calculate_render_speed_factor(caps)
        caps.memory_constraints = self._detect_memory_constraints()
        
        self.capabilities = caps
        return caps
    
    def _get_terminal_size(self) -> tuple[int, int]:
        """Get terminal dimensions"""
        try:
            size = os.get_terminal_size()
            return size.columns, size.lines
        except:
            return 80, 24
    
    def _detect_terminal_type(self) -> str:
        """Detect specific terminal type for optimizations"""
        term = os.environ.get('TERM', '').lower()
        term_program = os.environ.get('TERM_PROGRAM', '').lower()
        
        if 'iterm' in term_program:
            return 'iterm2'
        elif 'windows terminal' in term_program:
            return 'windows_terminal'  
        elif 'gnome-terminal' in term_program:
            return 'gnome_terminal'
        elif 'alacritty' in term:
            return 'alacritty'
        elif 'kitty' in term:
            return 'kitty'
        elif 'tmux' in term:
            return 'tmux'
        elif 'screen' in term:
            return 'screen'
        else:
            return term or 'unknown'
    
    def _is_ssh_connection(self) -> bool:
        """Detect if running over SSH"""
        return bool(os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_CLIENT'))
    
    def _test_256_colors(self) -> bool:
        """Test 256-color support"""
        if 'COLORTERM' in os.environ:
            return True
        term = os.environ.get('TERM', '')
        return '256color' in term or 'color' in term
    
    def _test_true_color(self) -> bool:
        """Test true color (24-bit) support"""
        colorterm = os.environ.get('COLORTERM', '').lower()
        return colorterm in ('truecolor', '24bit')
    
    def _test_unicode(self) -> bool:
        """Test Unicode support"""
        try:
            # Test if we can encode/print Unicode
            test_chars = "▲▼◆◇★☆✓✗"
            test_chars.encode(sys.stdout.encoding or 'utf-8')
            return True
        except:
            return False
    
    def _test_mouse_support(self) -> bool:
        """Test mouse support capability"""
        # This is a basic heuristic - full mouse testing requires terminal interaction
        term = os.environ.get('TERM', '').lower()
        return 'xterm' in term or self.capabilities and self.capabilities.terminal_type in [
            'iterm2', 'windows_terminal', 'gnome_terminal', 'alacritty', 'kitty'
        ]
    
    def _measure_terminal_latency(self) -> float:
        """Measure terminal rendering latency"""
        if self._is_ssh_connection():
            return 50.0  # Assume higher latency for SSH
        
        # Basic latency estimation based on terminal type
        terminal_latencies = {
            'iterm2': 8.0,
            'windows_terminal': 12.0, 
            'gnome_terminal': 15.0,
            'alacritty': 5.0,
            'kitty': 6.0,
            'tmux': 20.0,
            'screen': 25.0
        }
        
        if self.capabilities:
            return terminal_latencies.get(self.capabilities.terminal_type, 16.0)
        return 16.0
    
    def _calculate_render_speed_factor(self, caps: TerminalCapabilities) -> float:
        """Calculate relative rendering speed factor"""
        factor = 1.0
        
        # SSH connection penalty
        if caps.ssh_connection:
            factor *= 0.6
        
        # Terminal type adjustments
        if caps.terminal_type in ['alacritty', 'kitty', 'iterm2']:
            factor *= 1.2  # Fast terminals
        elif caps.terminal_type in ['tmux', 'screen']:
            factor *= 0.8  # Terminal multiplexers
        
        # Size penalty for very large terminals
        if caps.width * caps.height > 200 * 50:
            factor *= 0.85
        
        return max(0.3, min(2.0, factor))
    
    def _detect_memory_constraints(self) -> bool:
        """Detect if running in memory-constrained environment"""
        try:
            memory = psutil.virtual_memory()
            # Consider constrained if less than 1GB available
            return memory.available < 1024 * 1024 * 1024
        except:
            return False


class FrameRateMonitor:
    """Real-time frame rate monitoring and adaptive control"""
    
    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.target_frame_time = 1.0 / target_fps
        
        self.frame_times: List[float] = []
        self.max_samples = 60  # Keep last 60 frames
        self.last_frame_time = time.time()
        
        self.current_fps = 0.0
        self.average_frame_time = 0.0
        self.frame_drops = 0
        self.adaptive_enabled = True
        
        self._lock = threading.Lock()
    
    def start_frame(self) -> float:
        """Mark the start of a frame, returns frame start time"""
        current_time = time.time()
        
        with self._lock:
            if self.last_frame_time > 0:
                frame_time = current_time - self.last_frame_time
                self.frame_times.append(frame_time)
                
                # Keep only recent samples
                if len(self.frame_times) > self.max_samples:
                    self.frame_times = self.frame_times[-self.max_samples:]
                
                # Update metrics
                self.average_frame_time = sum(self.frame_times) / len(self.frame_times)
                self.current_fps = 1.0 / self.average_frame_time if self.average_frame_time > 0 else 0
                
                # Track frame drops
                if frame_time > self.target_frame_time * 1.5:
                    self.frame_drops += 1
            
            self.last_frame_time = current_time
        
        return current_time
    
    def end_frame(self, frame_start_time: float) -> Dict[str, float]:
        """Mark end of frame and return performance metrics"""
        frame_render_time = time.time() - frame_start_time
        
        return {
            'frame_render_time_ms': frame_render_time * 1000,
            'frame_total_time_ms': self.average_frame_time * 1000,
            'current_fps': self.current_fps,
            'frame_drops': self.frame_drops,
            'target_fps': self.target_fps
        }
    
    def should_skip_frame(self) -> bool:
        """Determine if frame should be skipped for performance"""
        if not self.adaptive_enabled:
            return False
            
        # Skip if we're running significantly behind
        return self.current_fps < self.target_fps * 0.7
    
    def get_adaptive_delay(self) -> float:
        """Get adaptive delay to maintain target frame rate"""
        if not self.adaptive_enabled or not self.frame_times:
            return 0.0
            
        # If we're running too fast, add delay
        if self.current_fps > self.target_fps * 1.1:
            excess_speed = self.current_fps - self.target_fps
            delay_factor = excess_speed / self.target_fps
            return min(0.01, delay_factor * 0.005)  # Max 10ms delay
        
        return 0.0
    
    def reset_metrics(self):
        """Reset frame rate metrics"""
        with self._lock:
            self.frame_times.clear()
            self.frame_drops = 0
            self.last_frame_time = time.time()


class RenderingOptimizer:
    """Main rendering optimization controller"""
    
    def __init__(self):
        self.config = RenderingConfig()
        self.terminal_detector = TerminalDetector()
        self.frame_monitor = FrameRateMonitor(self.config.target_fps)
        
        self.capabilities: Optional[TerminalCapabilities] = None
        self.performance_tier = "auto"
        self.optimization_active = False
        
        # Performance tracking
        self.render_cache: Dict[str, Any] = {}
        self.object_pool: Dict[type, List[Any]] = {}
        self.memory_usage_history: List[float] = []
        
        self._initialize_optimization()
    
    def _initialize_optimization(self):
        """Initialize rendering optimization"""
        self.capabilities = self.terminal_detector.detect_capabilities()
        self.performance_tier = self._determine_performance_tier()
        self._apply_tier_optimizations()
    
    def _determine_performance_tier(self) -> str:
        """Determine optimal performance tier"""
        if not self.capabilities:
            return "medium"
        
        caps = self.capabilities
        
        # High performance tier criteria
        if (caps.supports_true_color and 
            not caps.ssh_connection and
            caps.render_speed_factor > 1.0 and
            not caps.memory_constraints):
            return "high"
        
        # Low performance tier criteria
        if (caps.ssh_connection and 
            caps.estimated_latency_ms > 30 or
            caps.memory_constraints or
            caps.render_speed_factor < 0.7):
            return "low"
        
        return "medium"
    
    def _apply_tier_optimizations(self):
        """Apply optimizations based on performance tier"""
        if self.performance_tier == "high":
            self.config.target_fps = 60
            self.config.animation_quality = "high"
            self.config.text_rendering_mode = "optimized"
            self.config.frame_buffer_size = 3
            
        elif self.performance_tier == "medium":
            self.config.target_fps = 30
            self.config.animation_quality = "medium"
            self.config.text_rendering_mode = "optimized"
            self.config.frame_buffer_size = 2
            
        else:  # low
            self.config.target_fps = 15
            self.config.animation_quality = "low"
            self.config.text_rendering_mode = "cached"
            self.config.frame_buffer_size = 1
        
        # Update frame rate monitor
        self.frame_monitor.target_fps = self.config.target_fps
        self.frame_monitor.target_frame_time = 1.0 / self.config.target_fps
    
    @contextmanager
    def optimized_render_context(self):
        """Context manager for optimized rendering"""
        frame_start = self.frame_monitor.start_frame()
        
        try:
            # Check if we should skip this frame
            if self.frame_monitor.should_skip_frame():
                yield {"skip_frame": True, "reason": "performance"}
                return
            
            yield {"skip_frame": False, "frame_start": frame_start}
            
        finally:
            metrics = self.frame_monitor.end_frame(frame_start)
            self._update_adaptive_settings(metrics)
            
            # Apply adaptive delay if needed
            delay = self.frame_monitor.get_adaptive_delay()
            if delay > 0:
                time.sleep(delay)
    
    def _update_adaptive_settings(self, metrics: Dict[str, float]):
        """Update adaptive settings based on performance metrics"""
        if not self.config.adaptive_rendering:
            return
        
        current_fps = metrics.get('current_fps', 0)
        frame_drops = metrics.get('frame_drops', 0)
        
        # Downgrade quality if performance is poor
        if current_fps < self.config.target_fps * 0.8 and frame_drops > 10:
            if self.config.animation_quality == "high":
                self.config.animation_quality = "medium"
            elif self.config.animation_quality == "medium":
                self.config.animation_quality = "low"
        
        # Upgrade quality if performance is good and stable
        elif (current_fps > self.config.target_fps * 1.1 and 
              frame_drops < 3 and 
              len(self.frame_monitor.frame_times) > 30):
            if self.config.animation_quality == "low":
                self.config.animation_quality = "medium"
            elif self.config.animation_quality == "medium":
                self.config.animation_quality = "high"
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        memory_mb = self._get_memory_usage()
        cpu_percent = self._get_cpu_usage()
        
        return PerformanceMetrics(
            frame_time_ms=self.frame_monitor.average_frame_time * 1000,
            fps=self.frame_monitor.current_fps,
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            terminal_capabilities=self._format_capabilities_dict(),
            rendering_mode=self.performance_tier
        )
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            # Track memory history
            self.memory_usage_history.append(memory_mb)
            if len(self.memory_usage_history) > 100:
                self.memory_usage_history = self.memory_usage_history[-100:]
            
            return memory_mb
        except:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.Process().cpu_percent()
        except:
            return 0.0
    
    def _format_capabilities_dict(self) -> Dict[str, bool]:
        """Format terminal capabilities as dict"""
        if not self.capabilities:
            return {}
        
        return {
            '256_colors': self.capabilities.supports_256_colors,
            'true_color': self.capabilities.supports_true_color,
            'unicode': self.capabilities.supports_unicode,
            'mouse': self.capabilities.supports_mouse,
            'ssh_connection': self.capabilities.ssh_connection,
            'memory_constrained': self.capabilities.memory_constraints
        }
    
    def create_optimized_console(self) -> Console:
        """Create an optimized Rich console"""
        console_kwargs = {}
        
        # Apply optimizations based on capabilities
        if self.capabilities:
            if not self.capabilities.supports_true_color:
                console_kwargs['color_system'] = '256' if self.capabilities.supports_256_colors else 'standard'
            
            if not self.capabilities.supports_unicode:
                console_kwargs['legacy_windows'] = True
            
            console_kwargs['width'] = min(self.capabilities.width, 120)  # Limit width for performance
            console_kwargs['height'] = self.capabilities.height
        
        # Performance-based settings
        if self.performance_tier == "low":
            console_kwargs['no_color'] = False  # Keep colors but reduce complexity
            console_kwargs['force_terminal'] = True
        
        return Console(**console_kwargs)
    
    def should_use_animation(self) -> bool:
        """Determine if animations should be used"""
        return (self.config.animation_quality != "low" and 
                self.frame_monitor.current_fps > 20)
    
    def get_animation_speed_factor(self) -> float:
        """Get animation speed adjustment factor"""
        if self.config.animation_quality == "high":
            return 1.0
        elif self.config.animation_quality == "medium":
            return 0.7
        else:
            return 0.5
    
    def display_performance_dashboard(self):
        """Display real-time performance dashboard"""
        console = self.create_optimized_console()
        metrics = self.get_current_metrics()
        
        # Create performance table
        table = Table(title="Rendering Performance Monitor")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")
        
        # FPS metrics
        fps_status = "🟢 Excellent" if metrics.fps > 45 else "🟡 Good" if metrics.fps > 25 else "🔴 Poor"
        table.add_row("Frame Rate", f"{metrics.fps:.1f} FPS", fps_status)
        
        # Frame time
        frame_time_status = "🟢 Smooth" if metrics.frame_time_ms < 20 else "🟡 Acceptable" if metrics.frame_time_ms < 35 else "🔴 Slow"
        table.add_row("Frame Time", f"{metrics.frame_time_ms:.1f}ms", frame_time_status)
        
        # Memory usage
        memory_status = "🟢 Low" if metrics.memory_usage_mb < 100 else "🟡 Moderate" if metrics.memory_usage_mb < 200 else "🔴 High"
        table.add_row("Memory Usage", f"{metrics.memory_usage_mb:.1f}MB", memory_status)
        
        # Performance tier
        table.add_row("Performance Tier", metrics.rendering_mode.title(), "ℹ️ Auto-detected")
        
        console.print(table)
        
        # Terminal capabilities
        caps_table = Table(title="Terminal Capabilities")
        caps_table.add_column("Feature", style="cyan")
        caps_table.add_column("Supported", style="white")
        
        for feature, supported in metrics.terminal_capabilities.items():
            icon = "✅" if supported else "❌"
            caps_table.add_row(feature.replace('_', ' ').title(), f"{icon} {supported}")
        
        console.print(caps_table)


# Global optimizer instance
_global_optimizer: Optional[RenderingOptimizer] = None

def get_rendering_optimizer() -> RenderingOptimizer:
    """Get global rendering optimizer instance"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = RenderingOptimizer()
    return _global_optimizer

def create_optimized_console() -> Console:
    """Create an optimized console instance"""
    return get_rendering_optimizer().create_optimized_console()

@contextmanager
def optimized_rendering():
    """Context manager for optimized rendering operations"""
    optimizer = get_rendering_optimizer()
    with optimizer.optimized_render_context() as context:
        yield context

async def async_optimized_rendering():
    """Async context manager for optimized rendering"""
    optimizer = get_rendering_optimizer()
    with optimizer.optimized_render_context() as context:
        if not context.get("skip_frame", False):
            yield context
        else:
            # Skip frame - yield minimal context
            yield {"skip_frame": True}