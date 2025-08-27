"""
Cross-Platform Terminal Performance Optimization
Terminal-specific optimizations, SSH adaptation, and legacy support
"""

import os
import sys
import time
import subprocess
import platform
from typing import Dict, Any, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import asyncio
from pathlib import Path

from rich.console import Console, RenderableType
from rich.text import Text
from rich.panel import Panel
from rich.table import Table


class TerminalType(Enum):
    """Supported terminal types with optimization profiles"""
    WINDOWS_TERMINAL = "windows_terminal"
    POWERSHELL = "powershell"
    CMD = "cmd"
    ITERM2 = "iterm2"
    GNOME_TERMINAL = "gnome_terminal"
    KDE_KONSOLE = "kde_konsole"
    ALACRITTY = "alacritty"
    KITTY = "kitty"
    TMUX = "tmux"
    SCREEN = "screen"
    XTERM = "xterm"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    """Connection types affecting performance"""
    LOCAL = "local"
    SSH = "ssh"
    MOSH = "mosh"
    SERIAL = "serial"
    WSL = "wsl"


@dataclass
class TerminalProfile:
    """Terminal-specific performance profile"""
    terminal_type: TerminalType
    connection_type: ConnectionType
    
    # Performance characteristics
    max_fps: int = 30
    supports_true_color: bool = False
    supports_unicode: bool = True
    supports_mouse: bool = False
    supports_bracketed_paste: bool = False
    
    # Optimization settings
    buffer_size: int = 8192
    chunk_size: int = 1024
    render_delay_ms: float = 0.0
    
    # Feature flags
    use_alternate_screen: bool = True
    use_raw_mode: bool = True
    enable_scrollback: bool = True
    
    # Latency characteristics
    estimated_latency_ms: float = 10.0
    render_overhead_ms: float = 5.0


class TerminalDetector:
    """Advanced terminal detection and capability analysis"""
    
    def __init__(self):
        self.detection_cache: Dict[str, Any] = {}
        self.profile: Optional[TerminalProfile] = None
        
    def detect_terminal_profile(self) -> TerminalProfile:
        """Comprehensive terminal detection and profiling"""
        if self.profile:
            return self.profile
        
        # Detect terminal type
        terminal_type = self._detect_terminal_type()
        connection_type = self._detect_connection_type()
        
        # Create base profile
        profile = TerminalProfile(
            terminal_type=terminal_type,
            connection_type=connection_type
        )
        
        # Apply terminal-specific optimizations
        self._apply_terminal_optimizations(profile)
        self._apply_connection_optimizations(profile)
        
        # Test actual capabilities
        self._test_terminal_capabilities(profile)
        
        # Measure performance characteristics
        self._measure_performance_metrics(profile)
        
        self.profile = profile
        return profile
    
    def _detect_terminal_type(self) -> TerminalType:
        """Detect specific terminal type"""
        # Environment variable detection
        term_program = os.environ.get('TERM_PROGRAM', '').lower()
        term = os.environ.get('TERM', '').lower()
        
        # Windows Terminal detection
        if 'windows terminal' in term_program or os.environ.get('WT_SESSION'):
            return TerminalType.WINDOWS_TERMINAL
        
        # PowerShell detection
        if os.environ.get('PSHOME') or 'powershell' in term_program:
            return TerminalType.POWERSHELL
        
        # CMD detection (Windows)
        if platform.system() == 'Windows' and not term_program:
            return TerminalType.CMD
        
        # iTerm2 detection
        if 'iterm' in term_program or term == 'iterm2':
            return TerminalType.ITERM2
        
        # GNOME Terminal
        if 'gnome-terminal' in term_program or 'gnome-terminal' in term:
            return TerminalType.GNOME_TERMINAL
        
        # KDE Konsole
        if 'konsole' in term_program or 'konsole' in term:
            return TerminalType.KDE_KONSOLE
        
        # Alacritty
        if 'alacritty' in term_program or 'alacritty' in term:
            return TerminalType.ALACRITTY
        
        # Kitty
        if 'kitty' in term_program or 'xterm-kitty' in term:
            return TerminalType.KITTY
        
        # Terminal multiplexers
        if 'tmux' in term:
            return TerminalType.TMUX
        if 'screen' in term:
            return TerminalType.SCREEN
        
        # Generic xterm
        if 'xterm' in term:
            return TerminalType.XTERM
        
        return TerminalType.UNKNOWN
    
    def _detect_connection_type(self) -> ConnectionType:
        """Detect connection type"""
        # SSH detection
        if (os.environ.get('SSH_CONNECTION') or 
            os.environ.get('SSH_CLIENT') or 
            os.environ.get('SSH_TTY')):
            return ConnectionType.SSH
        
        # Mosh detection
        if os.environ.get('MOSH_CONNECTION'):
            return ConnectionType.MOSH
        
        # WSL detection
        if os.path.exists('/proc/version'):
            try:
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower():
                        return ConnectionType.WSL
            except:
                pass
        
        return ConnectionType.LOCAL
    
    def _apply_terminal_optimizations(self, profile: TerminalProfile):
        """Apply terminal-specific optimizations"""
        optimizations = {
            TerminalType.WINDOWS_TERMINAL: {
                'max_fps': 60,
                'supports_true_color': True,
                'supports_unicode': True,
                'supports_mouse': True,
                'buffer_size': 16384,
                'estimated_latency_ms': 8.0
            },
            TerminalType.ITERM2: {
                'max_fps': 60,
                'supports_true_color': True,
                'supports_unicode': True,
                'supports_mouse': True,
                'supports_bracketed_paste': True,
                'buffer_size': 32768,
                'estimated_latency_ms': 6.0
            },
            TerminalType.ALACRITTY: {
                'max_fps': 60,
                'supports_true_color': True,
                'supports_unicode': True,
                'supports_mouse': True,
                'buffer_size': 32768,
                'estimated_latency_ms': 4.0  # Very fast
            },
            TerminalType.KITTY: {
                'max_fps': 60,
                'supports_true_color': True,
                'supports_unicode': True,
                'supports_mouse': True,
                'buffer_size': 32768,
                'estimated_latency_ms': 5.0
            },
            TerminalType.GNOME_TERMINAL: {
                'max_fps': 30,
                'supports_true_color': True,
                'supports_unicode': True,
                'supports_mouse': True,
                'buffer_size': 16384,
                'estimated_latency_ms': 12.0
            },
            TerminalType.TMUX: {
                'max_fps': 30,
                'supports_true_color': True,
                'supports_unicode': True,
                'buffer_size': 8192,
                'estimated_latency_ms': 15.0,
                'render_delay_ms': 5.0  # tmux adds overhead
            },
            TerminalType.CMD: {
                'max_fps': 15,
                'supports_true_color': False,
                'supports_unicode': False,
                'supports_mouse': False,
                'buffer_size': 4096,
                'estimated_latency_ms': 25.0
            }
        }
        
        if profile.terminal_type in optimizations:
            opts = optimizations[profile.terminal_type]
            for key, value in opts.items():
                setattr(profile, key, value)
    
    def _apply_connection_optimizations(self, profile: TerminalProfile):
        """Apply connection-type optimizations"""
        if profile.connection_type == ConnectionType.SSH:
            # SSH connections need aggressive optimization
            profile.max_fps = min(15, profile.max_fps)
            profile.buffer_size = min(4096, profile.buffer_size)
            profile.chunk_size = min(512, profile.chunk_size)
            profile.estimated_latency_ms += 30.0
            profile.render_delay_ms += 10.0
            
        elif profile.connection_type == ConnectionType.MOSH:
            # Mosh handles latency better but still needs optimization
            profile.max_fps = min(30, profile.max_fps)
            profile.estimated_latency_ms += 10.0
            
        elif profile.connection_type == ConnectionType.WSL:
            # WSL has some overhead
            profile.estimated_latency_ms += 5.0
    
    def _test_terminal_capabilities(self, profile: TerminalProfile):
        """Test actual terminal capabilities"""
        # Test true color support
        if profile.supports_true_color:
            profile.supports_true_color = self._test_true_color_support()
        
        # Test Unicode support
        if profile.supports_unicode:
            profile.supports_unicode = self._test_unicode_support()
        
        # Test mouse support
        if profile.supports_mouse:
            profile.supports_mouse = self._test_mouse_support()
    
    def _test_true_color_support(self) -> bool:
        """Test if terminal supports true color"""
        colorterm = os.environ.get('COLORTERM', '').lower()
        if colorterm in ('truecolor', '24bit'):
            return True
        
        # Test by checking color capability
        term = os.environ.get('TERM', '')
        if 'truecolor' in term or '24bit' in term:
            return True
        
        return False
    
    def _test_unicode_support(self) -> bool:
        """Test Unicode support"""
        try:
            # Test if we can encode/decode Unicode
            test_string = "▲▼◆◇★☆✓✗"
            encoding = sys.stdout.encoding or 'utf-8'
            test_string.encode(encoding)
            return True
        except (UnicodeEncodeError, LookupError):
            return False
    
    def _test_mouse_support(self) -> bool:
        """Test mouse support (heuristic)"""
        # This is difficult to test without user interaction
        # Use heuristics based on terminal type
        return self.profile.terminal_type in [
            TerminalType.WINDOWS_TERMINAL,
            TerminalType.ITERM2,
            TerminalType.GNOME_TERMINAL,
            TerminalType.ALACRITTY,
            TerminalType.KITTY
        ]
    
    def _measure_performance_metrics(self, profile: TerminalProfile):
        """Measure actual terminal performance"""
        try:
            # Simple render timing test
            console = Console(file=sys.stdout, force_terminal=True)
            
            start_time = time.time()
            for _ in range(10):
                console.print(".", end="", style="dim")
            console.print()  # Flush
            
            render_time = (time.time() - start_time) / 10
            profile.render_overhead_ms = render_time * 1000
            
        except Exception:
            # If measurement fails, use defaults
            pass


class TerminalOptimizer:
    """Main terminal optimization controller"""
    
    def __init__(self):
        self.detector = TerminalDetector()
        self.profile: Optional[TerminalProfile] = None
        self.optimization_active = False
        
        # Performance tracking
        self.render_times: List[float] = []
        self.output_buffer = []
        self.buffer_lock = threading.Lock()
        
        # Adaptive settings
        self.current_fps = 30
        self.adaptive_enabled = True
        
    def initialize(self):
        """Initialize terminal optimization"""
        self.profile = self.detector.detect_terminal_profile()
        self.current_fps = self.profile.max_fps
        self.optimization_active = True
        
        # Apply initial optimizations
        self._apply_console_optimizations()
    
    def _apply_console_optimizations(self):
        """Apply optimizations to console output"""
        if not self.profile:
            return
        
        # Set environment variables for optimal rendering
        if self.profile.supports_true_color:
            os.environ['COLORTERM'] = 'truecolor'
        
        # Configure terminal settings if possible
        if platform.system() != 'Windows':
            try:
                # Enable raw mode for better responsiveness
                import tty
                if self.profile.use_raw_mode and sys.stdin.isatty():
                    # Note: This would need more careful implementation in production
                    pass
            except ImportError:
                pass
    
    def create_optimized_console(self) -> Console:
        """Create console optimized for detected terminal"""
        if not self.profile:
            self.initialize()
        
        kwargs = {
            'force_terminal': True,
            'width': None,  # Auto-detect
            'height': None  # Auto-detect
        }
        
        # Color system optimization
        if not self.profile.supports_true_color:
            if self.profile.terminal_type in [TerminalType.CMD, TerminalType.POWERSHELL]:
                kwargs['color_system'] = 'windows'
            else:
                kwargs['color_system'] = '256'  # 256-color fallback
        else:
            kwargs['color_system'] = 'truecolor'
        
        # Legacy terminal support
        if self.profile.terminal_type == TerminalType.CMD:
            kwargs['legacy_windows'] = True
            kwargs['no_color'] = False
        
        # Unicode support
        if not self.profile.supports_unicode:
            kwargs['ascii_only'] = True
        
        return Console(**kwargs)
    
    def optimize_output(self, content: RenderableType) -> RenderableType:
        """Optimize content for current terminal"""
        if not self.profile:
            return content
        
        # Content simplification for slow terminals
        if self.profile.connection_type == ConnectionType.SSH:
            return self._simplify_content_for_ssh(content)
        
        # Legacy terminal adaptations
        if self.profile.terminal_type in [TerminalType.CMD, TerminalType.UNKNOWN]:
            return self._adapt_for_legacy_terminal(content)
        
        return content
    
    def _simplify_content_for_ssh(self, content: RenderableType) -> RenderableType:
        """Simplify content for SSH connections"""
        if isinstance(content, Panel):
            # Simplify panel borders for SSH
            return Panel(
                content.renderable,
                title=content.title,
                border_style="ascii",  # Use ASCII borders
                padding=(0, 1)  # Reduce padding
            )
        
        elif isinstance(content, Table):
            # Simplify table appearance
            content.show_lines = False  # Remove internal lines
            content.border_style = "ascii"
        
        return content
    
    def _adapt_for_legacy_terminal(self, content: RenderableType) -> RenderableType:
        """Adapt content for legacy terminals"""
        if isinstance(content, Text):
            # Remove complex styling for legacy terminals
            simplified = Text(str(content))
            # Keep only basic styling
            for span in content._spans:
                if span.style and hasattr(span.style, 'color'):
                    if span.style.color and span.style.color.name in ['red', 'green', 'yellow', 'blue']:
                        simplified.stylize(span.style.color.name, span.start, span.end)
            return simplified
        
        return content
    
    def buffered_output(self, content: RenderableType, console: Console):
        """Optimize output through buffering"""
        if not self.profile:
            console.print(content)
            return
        
        with self.buffer_lock:
            self.output_buffer.append(content)
            
            # Flush buffer based on terminal characteristics
            should_flush = (
                len(self.output_buffer) >= self.profile.buffer_size or
                time.time() % (1.0 / self.current_fps) < 0.01  # Time-based flush
            )
            
            if should_flush:
                self._flush_buffer(console)
    
    def _flush_buffer(self, console: Console):
        """Flush output buffer to terminal"""
        if not self.output_buffer:
            return
        
        start_time = time.time()
        
        # Output buffered content
        for content in self.output_buffer:
            optimized_content = self.optimize_output(content)
            console.print(optimized_content)
        
        # Clear buffer
        self.output_buffer.clear()
        
        # Track performance
        render_time = time.time() - start_time
        self.render_times.append(render_time)
        
        # Adaptive optimization
        if self.adaptive_enabled and len(self.render_times) > 10:
            self._adjust_performance_settings()
    
    def _adjust_performance_settings(self):
        """Adjust settings based on performance"""
        if not self.render_times:
            return
        
        # Calculate average render time
        recent_times = self.render_times[-10:]
        avg_render_time = sum(recent_times) / len(recent_times)
        
        # Adjust FPS based on performance
        target_frame_time = 1.0 / self.current_fps
        
        if avg_render_time > target_frame_time * 1.5:
            # Reduce FPS if we're falling behind
            self.current_fps = max(10, int(self.current_fps * 0.8))
        elif avg_render_time < target_frame_time * 0.5:
            # Increase FPS if we have headroom
            self.current_fps = min(self.profile.max_fps, int(self.current_fps * 1.1))
        
        # Keep only recent render times
        if len(self.render_times) > 100:
            self.render_times = self.render_times[-50:]
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get terminal optimization statistics"""
        if not self.profile:
            return {}
        
        avg_render_time = 0.0
        if self.render_times:
            avg_render_time = sum(self.render_times) / len(self.render_times)
        
        return {
            'terminal_type': self.profile.terminal_type.value,
            'connection_type': self.profile.connection_type.value,
            'current_fps': self.current_fps,
            'max_fps': self.profile.max_fps,
            'avg_render_time_ms': avg_render_time * 1000,
            'estimated_latency_ms': self.profile.estimated_latency_ms,
            'supports_true_color': self.profile.supports_true_color,
            'supports_unicode': self.profile.supports_unicode,
            'optimization_active': self.optimization_active,
            'buffer_size': len(self.output_buffer),
            'adaptive_enabled': self.adaptive_enabled
        }
    
    def display_terminal_info(self):
        """Display detailed terminal information"""
        console = self.create_optimized_console()
        stats = self.get_optimization_stats()
        
        # Terminal detection table
        detection_table = Table(title="Terminal Detection Results")
        detection_table.add_column("Property", style="cyan")
        detection_table.add_column("Value", style="white")
        detection_table.add_column("Status", style="green")
        
        detection_table.add_row("Terminal Type", stats['terminal_type'], "🔍 Detected")
        detection_table.add_row("Connection Type", stats['connection_type'], "🔍 Detected")
        detection_table.add_row("True Color Support", str(stats['supports_true_color']), "✅" if stats['supports_true_color'] else "❌")
        detection_table.add_row("Unicode Support", str(stats['supports_unicode']), "✅" if stats['supports_unicode'] else "❌")
        
        console.print(detection_table)
        
        # Performance table
        perf_table = Table(title="Performance Optimization")
        perf_table.add_column("Metric", style="cyan")
        perf_table.add_column("Current", style="yellow")
        perf_table.add_column("Maximum", style="green")
        perf_table.add_column("Status", style="white")
        
        fps_status = "🟢 Optimal" if stats['current_fps'] >= stats['max_fps'] * 0.8 else "🟡 Reduced"
        perf_table.add_row("Frame Rate", f"{stats['current_fps']} FPS", f"{stats['max_fps']} FPS", fps_status)
        
        latency_status = "🟢 Low" if stats['estimated_latency_ms'] < 20 else "🟡 Moderate" if stats['estimated_latency_ms'] < 50 else "🔴 High"
        perf_table.add_row("Estimated Latency", f"{stats['estimated_latency_ms']:.1f}ms", "N/A", latency_status)
        
        render_time_status = "🟢 Fast" if stats['avg_render_time_ms'] < 10 else "🟡 Acceptable" if stats['avg_render_time_ms'] < 25 else "🔴 Slow"
        perf_table.add_row("Average Render Time", f"{stats['avg_render_time_ms']:.1f}ms", "16.7ms", render_time_status)
        
        console.print(perf_table)
        
        # Optimization recommendations
        recommendations = self._get_optimization_recommendations()
        if recommendations:
            rec_panel = Panel(
                "\n".join([f"• {rec}" for rec in recommendations]),
                title="Optimization Recommendations",
                border_style="yellow"
            )
            console.print(rec_panel)
    
    def _get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations for current setup"""
        recommendations = []
        
        if not self.profile:
            return recommendations
        
        # SSH-specific recommendations
        if self.profile.connection_type == ConnectionType.SSH:
            recommendations.append("Consider using mosh for better SSH performance")
            recommendations.append("Enable SSH connection compression (-C flag)")
            recommendations.append("Use SSH multiplexing for multiple connections")
        
        # Terminal-specific recommendations
        if self.profile.terminal_type == TerminalType.CMD:
            recommendations.append("Consider upgrading to Windows Terminal for better performance")
            recommendations.append("Enable UTF-8 support in Windows console")
        
        # Performance recommendations
        if self.current_fps < self.profile.max_fps * 0.7:
            recommendations.append("Consider reducing animation complexity for better performance")
            recommendations.append("Enable adaptive rendering to maintain smooth performance")
        
        # Color support recommendations
        if not self.profile.supports_true_color:
            recommendations.append("Enable true color support in terminal settings if available")
        
        return recommendations


# Global terminal optimizer
_global_terminal_optimizer: Optional[TerminalOptimizer] = None

def get_terminal_optimizer() -> TerminalOptimizer:
    """Get global terminal optimizer instance"""
    global _global_terminal_optimizer
    if _global_terminal_optimizer is None:
        _global_terminal_optimizer = TerminalOptimizer()
        _global_terminal_optimizer.initialize()
    return _global_terminal_optimizer

def create_optimized_console() -> Console:
    """Create optimized console for current terminal"""
    return get_terminal_optimizer().create_optimized_console()

def optimize_for_terminal(content: RenderableType) -> RenderableType:
    """Optimize content for current terminal"""
    return get_terminal_optimizer().optimize_output(content)

async def buffered_print(content: RenderableType, console: Console = None):
    """Print with terminal-optimized buffering"""
    if console is None:
        console = create_optimized_console()
    
    optimizer = get_terminal_optimizer()
    optimizer.buffered_output(content, console)