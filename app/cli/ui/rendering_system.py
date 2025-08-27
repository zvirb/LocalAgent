"""
Unified Rendering System
Integration of all optimization streams for buttery-smooth CLI experience
"""

import asyncio
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Union, ContextManager
from dataclasses import dataclass, field
from contextlib import contextmanager, asynccontextmanager
import logging

from rich.console import Console, RenderableType
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress

# Import our optimization modules
from .performance_monitor import get_rendering_optimizer, PerformanceMetrics
from .memory_optimizer import get_memory_optimizer, MemoryStats
from .animation_engine import get_animation_manager, AnimationManager
from .terminal_optimizer import get_terminal_optimizer, TerminalOptimizer


logger = logging.getLogger(__name__)


@dataclass
class RenderingSystemConfig:
    """Configuration for the unified rendering system"""
    target_fps: int = 60
    memory_limit_mb: int = 200
    enable_animations: bool = True
    enable_adaptive_quality: bool = True
    enable_buffering: bool = True
    enable_caching: bool = True
    
    # Performance thresholds
    max_frame_time_ms: float = 16.67  # 60fps target
    memory_warning_threshold_mb: float = 150.0
    
    # Quality settings
    quality_mode: str = "auto"  # "low", "medium", "high", "auto"
    animation_quality: str = "high"
    text_rendering_quality: str = "high"


@dataclass
class SystemMetrics:
    """Comprehensive system performance metrics"""
    performance: PerformanceMetrics
    memory: MemoryStats
    animation_stats: Dict[str, Any]
    terminal_stats: Dict[str, Any]
    
    # Overall health indicators
    overall_health_score: float = 0.0
    performance_tier: str = "medium"
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class RenderingSystem:
    """
    Unified rendering system combining all optimization streams
    Provides the main interface for high-performance CLI rendering
    """
    
    def __init__(self, config: Optional[RenderingSystemConfig] = None):
        self.config = config or RenderingSystemConfig()
        
        # Initialize optimization subsystems
        self.perf_optimizer = get_rendering_optimizer()
        self.memory_optimizer = get_memory_optimizer()
        self.animation_manager = get_animation_manager()
        self.terminal_optimizer = get_terminal_optimizer()
        
        # System state
        self.initialized = False
        self.monitoring_active = False
        self.current_quality_mode = self.config.quality_mode
        
        # Performance tracking
        self.render_history: List[Dict[str, Any]] = []
        self.system_health_score = 0.0
        
        # Threading
        self._monitoring_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        logger.info("RenderingSystem initialized")
    
    def initialize(self):
        """Initialize the complete rendering system"""
        if self.initialized:
            return
        
        logger.info("Initializing rendering system components...")
        
        # Initialize subsystems
        self.terminal_optimizer.initialize()
        self.memory_optimizer.start_monitoring()
        
        # Apply initial configuration
        self._apply_configuration()
        
        # Start performance monitoring
        self.start_monitoring()
        
        self.initialized = True
        logger.info("Rendering system fully initialized")
    
    def _apply_configuration(self):
        """Apply configuration to all subsystems"""
        # Performance optimizer configuration
        perf_config = self.perf_optimizer.config
        perf_config.target_fps = self.config.target_fps
        perf_config.adaptive_rendering = self.config.enable_adaptive_quality
        perf_config.memory_limit_mb = self.config.memory_limit_mb
        
        # Animation manager configuration
        self.animation_manager.max_concurrent = 10 if self.config.enable_animations else 1
        
        # Set quality mode
        self._set_quality_mode(self.config.quality_mode)
    
    def _set_quality_mode(self, quality_mode: str):
        """Set system-wide quality mode"""
        self.current_quality_mode = quality_mode
        
        if quality_mode == "auto":
            # Auto mode will be handled by adaptive optimization
            return
        
        # Apply static quality settings
        quality_settings = {
            "low": {
                "target_fps": 15,
                "animation_quality": "low",
                "text_rendering_quality": "low",
                "enable_animations": False
            },
            "medium": {
                "target_fps": 30,
                "animation_quality": "medium", 
                "text_rendering_quality": "medium",
                "enable_animations": True
            },
            "high": {
                "target_fps": 60,
                "animation_quality": "high",
                "text_rendering_quality": "high",
                "enable_animations": True
            }
        }
        
        if quality_mode in quality_settings:
            settings = quality_settings[quality_mode]
            self.config.target_fps = settings["target_fps"]
            self.config.animation_quality = settings["animation_quality"]
            self.config.text_rendering_quality = settings["text_rendering_quality"]
            self.config.enable_animations = settings["enable_animations"]
    
    def create_optimized_console(self) -> Console:
        """Create a fully optimized console instance"""
        if not self.initialized:
            self.initialize()
        
        # Get optimized console from terminal optimizer
        console = self.terminal_optimizer.create_optimized_console()
        
        # Apply memory optimization tracking
        self.memory_optimizer.track_object(console)
        
        return console
    
    @contextmanager
    def optimized_rendering_context(self):
        """Context manager for optimized rendering operations"""
        if not self.initialized:
            self.initialize()
        
        # Start frame timing
        frame_start = time.time()
        
        try:
            # Use performance monitor's rendering context
            with self.perf_optimizer.optimized_render_context() as perf_context:
                if perf_context.get("skip_frame", False):
                    yield {"skip_frame": True, "reason": "performance"}
                else:
                    yield {
                        "skip_frame": False,
                        "frame_start": frame_start,
                        "console": self.create_optimized_console(),
                        "memory_optimizer": self.memory_optimizer,
                        "animation_manager": self.animation_manager
                    }
        finally:
            # Record render performance
            render_time = time.time() - frame_start
            self._record_render_performance(render_time)
    
    def render_content(self, content: RenderableType, console: Optional[Console] = None) -> None:
        """Render content with full optimization pipeline"""
        if console is None:
            console = self.create_optimized_console()
        
        with self.optimized_rendering_context() as context:
            if context["skip_frame"]:
                return  # Skip this frame for performance
            
            # Optimize content for terminal
            optimized_content = self.terminal_optimizer.optimize_output(content)
            
            # Use buffered output for performance
            self.terminal_optimizer.buffered_output(optimized_content, console)
    
    async def render_content_async(self, content: RenderableType, console: Optional[Console] = None):
        """Async version of render_content"""
        if console is None:
            console = self.create_optimized_console()
        
        # Run rendering in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.render_content, content, console)
    
    @asynccontextmanager
    async def live_rendering_context(self, refresh_per_second: int = None):
        """Async context manager for live rendering with optimization"""
        if refresh_per_second is None:
            refresh_per_second = min(self.config.target_fps, 30)  # Cap for live rendering
        
        console = self.create_optimized_console()
        
        with Live(console=console, refresh_per_second=refresh_per_second, transient=False) as live:
            # Enhance live with our optimizations
            live.console = console
            
            # Track live object for memory management
            self.memory_optimizer.track_object(live)
            
            yield live
    
    def create_optimized_progress(self, *args, **kwargs) -> Progress:
        """Create an optimized Progress instance"""
        console = self.create_optimized_console()
        
        # Apply performance optimizations to progress
        kwargs['console'] = console
        kwargs['refresh_per_second'] = min(self.config.target_fps, 30)
        
        progress = Progress(*args, **kwargs)
        
        # Track for memory management
        self.memory_optimizer.track_object(progress)
        
        return progress
    
    def optimize_text_content(self, text: str, style: str = "") -> Text:
        """Optimize text content with caching and styling"""
        # Use memory optimizer's string caching
        optimized_text = self.memory_optimizer.cache_styled_text(text, style)
        
        # Create Rich Text object
        if style:
            return Text(optimized_text, style=style)
        else:
            return Text(optimized_text)
    
    def create_performance_dashboard(self) -> RenderableType:
        """Create comprehensive performance dashboard"""
        metrics = self.get_system_metrics()
        
        # Main dashboard layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=5)
        )
        
        # Header
        health_color = "green" if metrics.overall_health_score > 0.8 else "yellow" if metrics.overall_health_score > 0.5 else "red"
        header_panel = Panel(
            f"[bold]Rendering System Dashboard[/bold] - Health Score: [{health_color}]{metrics.overall_health_score:.1%}[/{health_color}]",
            style="blue"
        )
        layout["header"].update(header_panel)
        
        # Main content - split into sections
        layout["main"].split_row(
            Layout(name="performance"),
            Layout(name="memory"),
            Layout(name="system")
        )
        
        # Performance metrics
        perf_table = Table(title="Performance", show_header=True, header_style="bold cyan")
        perf_table.add_column("Metric", style="white")
        perf_table.add_column("Value", style="green")
        perf_table.add_column("Status", style="yellow")
        
        fps_status = "🟢 Excellent" if metrics.performance.fps > 45 else "🟡 Good" if metrics.performance.fps > 25 else "🔴 Poor"
        perf_table.add_row("FPS", f"{metrics.performance.fps:.1f}", fps_status)
        
        frame_time_status = "🟢 Smooth" if metrics.performance.frame_time_ms < 20 else "🟡 OK" if metrics.performance.frame_time_ms < 35 else "🔴 Slow"
        perf_table.add_row("Frame Time", f"{metrics.performance.frame_time_ms:.1f}ms", frame_time_status)
        
        perf_table.add_row("Render Mode", metrics.performance.rendering_mode.title(), "ℹ️ Active")
        
        layout["performance"].update(Panel(perf_table, border_style="green"))
        
        # Memory metrics
        memory_table = Table(title="Memory", show_header=True, header_style="bold cyan")
        memory_table.add_column("Metric", style="white")
        memory_table.add_column("Value", style="green")
        memory_table.add_column("Status", style="yellow")
        
        memory_status = "🟢 Low" if metrics.memory.current_usage_mb < 100 else "🟡 Medium" if metrics.memory.current_usage_mb < 200 else "🔴 High"
        memory_table.add_row("Usage", f"{metrics.memory.current_usage_mb:.1f}MB", memory_status)
        
        efficiency_status = "🟢 Excellent" if metrics.memory.pool_efficiency > 0.8 else "🟡 Good" if metrics.memory.pool_efficiency > 0.5 else "🔴 Poor"
        memory_table.add_row("Pool Efficiency", f"{metrics.memory.pool_efficiency:.1%}", efficiency_status)
        
        memory_table.add_row("String Cache", f"{metrics.memory.string_pool_size:,}", "ℹ️ Active")
        
        layout["memory"].update(Panel(memory_table, border_style="blue"))
        
        # System info
        system_table = Table(title="System", show_header=True, header_style="bold cyan")
        system_table.add_column("Component", style="white")
        system_table.add_column("Status", style="green")
        
        system_table.add_row("Terminal Type", metrics.terminal_stats.get('terminal_type', 'Unknown'))
        system_table.add_row("Connection", metrics.terminal_stats.get('connection_type', 'Unknown'))
        system_table.add_row("Animations", f"{metrics.animation_stats.get('active_animations', 0)} active")
        system_table.add_row("Quality Mode", self.current_quality_mode.title())
        
        layout["system"].update(Panel(system_table, border_style="yellow"))
        
        # Footer with warnings and recommendations
        footer_content = []
        
        if metrics.warnings:
            footer_content.append("[bold red]Warnings:[/bold red]")
            for warning in metrics.warnings[:3]:  # Show max 3 warnings
                footer_content.append(f"⚠️  {warning}")
        
        if metrics.recommendations:
            footer_content.append("[bold green]Recommendations:[/bold green]")
            for rec in metrics.recommendations[:2]:  # Show max 2 recommendations
                footer_content.append(f"💡 {rec}")
        
        if not footer_content:
            footer_content = ["[dim]System running optimally[/dim]"]
        
        footer_panel = Panel("\n".join(footer_content), title="System Status", border_style="white")
        layout["footer"].update(footer_panel)
        
        return layout
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get comprehensive system metrics"""
        # Gather metrics from all subsystems
        performance_metrics = self.perf_optimizer.get_current_metrics()
        memory_stats = self.memory_optimizer.get_memory_stats()
        animation_stats = self.animation_manager.get_stats()
        terminal_stats = self.terminal_optimizer.get_optimization_stats()
        
        # Calculate overall health score
        health_score = self._calculate_health_score(
            performance_metrics, memory_stats, animation_stats, terminal_stats
        )
        
        # Generate warnings and recommendations
        warnings = self._generate_warnings(performance_metrics, memory_stats)
        recommendations = self._generate_recommendations(performance_metrics, memory_stats, terminal_stats)
        
        return SystemMetrics(
            performance=performance_metrics,
            memory=memory_stats,
            animation_stats=animation_stats,
            terminal_stats=terminal_stats,
            overall_health_score=health_score,
            performance_tier=performance_metrics.rendering_mode,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _calculate_health_score(self, perf: PerformanceMetrics, memory: MemoryStats, 
                               anim: Dict[str, Any], terminal: Dict[str, Any]) -> float:
        """Calculate overall system health score (0.0 to 1.0)"""
        scores = []
        
        # Performance score (30% weight)
        fps_score = min(1.0, perf.fps / self.config.target_fps)
        frame_time_score = max(0.0, 1.0 - (perf.frame_time_ms / self.config.max_frame_time_ms))
        perf_score = (fps_score + frame_time_score) / 2
        scores.append(perf_score * 0.3)
        
        # Memory score (25% weight)
        memory_score = max(0.0, 1.0 - (memory.current_usage_mb / self.config.memory_limit_mb))
        pool_score = memory.pool_efficiency
        mem_score = (memory_score + pool_score) / 2
        scores.append(mem_score * 0.25)
        
        # Animation score (20% weight)
        anim_perf_score = 1.0 if anim['performance_mode'] == 'high' else 0.7 if anim['performance_mode'] == 'medium' else 0.4
        scores.append(anim_perf_score * 0.2)
        
        # Terminal optimization score (25% weight)
        terminal_score = min(1.0, terminal.get('current_fps', 0) / terminal.get('max_fps', 1))
        scores.append(terminal_score * 0.25)
        
        return sum(scores)
    
    def _generate_warnings(self, perf: PerformanceMetrics, memory: MemoryStats) -> List[str]:
        """Generate performance warnings"""
        warnings = []
        
        if perf.fps < self.config.target_fps * 0.7:
            warnings.append(f"Low frame rate detected: {perf.fps:.1f} FPS")
        
        if memory.current_usage_mb > self.config.memory_warning_threshold_mb:
            warnings.append(f"High memory usage: {memory.current_usage_mb:.1f}MB")
        
        if memory.memory_leaks_detected > 0:
            warnings.append(f"Potential memory leaks detected: {memory.memory_leaks_detected}")
        
        if perf.frame_time_ms > self.config.max_frame_time_ms * 1.5:
            warnings.append(f"Slow frame rendering: {perf.frame_time_ms:.1f}ms")
        
        return warnings
    
    def _generate_recommendations(self, perf: PerformanceMetrics, memory: MemoryStats, 
                                terminal: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Performance recommendations
        if perf.fps < self.config.target_fps * 0.8:
            recommendations.append("Consider reducing animation complexity or enabling adaptive quality")
        
        # Memory recommendations
        if memory.pool_efficiency < 0.5:
            recommendations.append("Object pool efficiency is low - consider optimizing object reuse")
        
        if memory.current_usage_mb > self.config.memory_limit_mb * 0.8:
            recommendations.append("Consider enabling aggressive memory optimization")
        
        # Terminal recommendations
        if terminal.get('connection_type') == 'ssh':
            recommendations.append("SSH connection detected - consider enabling low-latency mode")
        
        if not terminal.get('supports_true_color', True):
            recommendations.append("Enable true color support in terminal for better visual quality")
        
        return recommendations
    
    def _record_render_performance(self, render_time: float):
        """Record render performance for analysis"""
        self.render_history.append({
            'timestamp': time.time(),
            'render_time': render_time,
            'fps': self.perf_optimizer.frame_monitor.current_fps,
            'memory_mb': self.memory_optimizer.get_memory_stats().current_usage_mb
        })
        
        # Keep only recent history
        if len(self.render_history) > 1000:
            self.render_history = self.render_history[-500:]
    
    def start_monitoring(self):
        """Start system monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        
        logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self._shutdown_event.set()
        
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        
        # Stop subsystem monitoring
        self.memory_optimizer.stop_monitoring()
        
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active and not self._shutdown_event.wait(1.0):
            try:
                # Update system health score
                metrics = self.get_system_metrics()
                self.system_health_score = metrics.overall_health_score
                
                # Adaptive quality adjustment
                if self.config.enable_adaptive_quality and self.current_quality_mode == "auto":
                    self._adaptive_quality_adjustment(metrics)
                
                # Memory optimization
                if metrics.memory.current_usage_mb > self.config.memory_warning_threshold_mb:
                    self.memory_optimizer.optimize_memory_usage()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def _adaptive_quality_adjustment(self, metrics: SystemMetrics):
        """Automatically adjust quality based on performance"""
        # Determine target quality based on health score
        if metrics.overall_health_score > 0.8:
            target_quality = "high"
        elif metrics.overall_health_score > 0.5:
            target_quality = "medium"
        else:
            target_quality = "low"
        
        # Apply quality change if needed
        if target_quality != self.current_quality_mode:
            logger.info(f"Adaptive quality change: {self.current_quality_mode} -> {target_quality}")
            self._set_quality_mode(target_quality)
    
    def shutdown(self):
        """Shutdown the rendering system"""
        logger.info("Shutting down rendering system")
        
        self.stop_monitoring()
        self.animation_manager.clear_all()
        
        logger.info("Rendering system shutdown complete")


# Global rendering system instance
_global_rendering_system: Optional[RenderingSystem] = None

def get_rendering_system(config: Optional[RenderingSystemConfig] = None) -> RenderingSystem:
    """Get global rendering system instance"""
    global _global_rendering_system
    if _global_rendering_system is None:
        _global_rendering_system = RenderingSystem(config)
        _global_rendering_system.initialize()
    return _global_rendering_system

def create_optimized_console() -> Console:
    """Create optimized console using the rendering system"""
    return get_rendering_system().create_optimized_console()

@contextmanager
def optimized_rendering():
    """Context manager for optimized rendering"""
    with get_rendering_system().optimized_rendering_context() as context:
        yield context

async def render_with_optimization(content: RenderableType, console: Optional[Console] = None):
    """Async function to render content with full optimization"""
    system = get_rendering_system()
    await system.render_content_async(content, console)

def display_performance_dashboard():
    """Display the comprehensive performance dashboard"""
    system = get_rendering_system()
    dashboard = system.create_performance_dashboard()
    console = system.create_optimized_console()
    console.print(dashboard)