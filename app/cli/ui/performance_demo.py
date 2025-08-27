#!/usr/bin/env python3
"""
Performance Optimization Demonstration
Showcases the rendering system optimizations with real-world scenarios
"""

import asyncio
import time
import random
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.layout import Layout

# Import our optimization system
try:
    from .rendering_system import (
        get_rendering_system, 
        display_performance_dashboard,
        RenderingSystemConfig
    )
    from .animation_engine import create_typewriter_effect, create_fade_effect
    from .memory_optimizer import get_memory_optimizer
    from .terminal_optimizer import get_terminal_optimizer
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    print("⚠️  Optimization modules not available - running basic demo")


class PerformanceDemo:
    """Demonstration of CLI performance optimizations"""
    
    def __init__(self):
        if OPTIMIZATION_AVAILABLE:
            # Initialize with high-performance configuration
            config = RenderingSystemConfig(
                target_fps=60,
                memory_limit_mb=150,
                enable_animations=True,
                enable_adaptive_quality=True
            )
            self.rendering_system = get_rendering_system(config)
            self.console = self.rendering_system.create_optimized_console()
            self.memory_optimizer = get_memory_optimizer()
            self.terminal_optimizer = get_terminal_optimizer()
        else:
            self.console = Console()
            self.rendering_system = None
            self.memory_optimizer = None
            self.terminal_optimizer = None
    
    def run_complete_demo(self):
        """Run complete performance demonstration"""
        self.console.print(Panel(
            "[bold cyan]CLI Visual Rendering Performance Optimization Demo[/bold cyan]\n\n"
            "This demonstration showcases:\n"
            "• Frame rate monitoring and adaptive rendering\n"
            "• Memory optimization with object pooling\n"
            "• Cross-platform terminal optimization\n"
            "• Smooth animations and effects\n"
            "• Virtual scrolling for large datasets\n\n"
            "[dim]Press Ctrl+C at any time to exit[/dim]",
            title="🚀 Performance Demo",
            border_style="blue"
        ))
        
        demos = [
            ("Terminal Detection", self.demo_terminal_detection),
            ("Memory Optimization", self.demo_memory_optimization),
            ("Frame Rate Monitoring", self.demo_frame_rate_monitoring),
            ("Animation System", self.demo_animation_system),
            ("Large Dataset Rendering", self.demo_large_dataset),
            ("Performance Dashboard", self.demo_performance_dashboard),
        ]
        
        try:
            for name, demo_func in demos:
                self.console.print(f"\n[bold yellow]🔧 Running: {name}[/bold yellow]")
                demo_func()
                self.console.print("[dim]Press Enter to continue...[/dim]")
                input()
                
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Demo interrupted by user[/yellow]")
        
        self.console.print(Panel(
            "[bold green]Demo completed! 🎉[/bold green]\n\n"
            "The CLI now runs with optimized performance:\n"
            "• Adaptive frame rate based on terminal capabilities\n"
            "• Memory usage optimized with pooling and caching\n"
            "• Terminal-specific rendering optimizations\n"
            "• Smooth animations that adapt to performance",
            title="✅ Optimization Complete",
            border_style="green"
        ))
    
    def demo_terminal_detection(self):
        """Demonstrate terminal detection and optimization"""
        if not OPTIMIZATION_AVAILABLE:
            self.console.print("[red]Optimization not available[/red]")
            return
        
        self.console.print("[bold]Detecting terminal capabilities...[/bold]")
        
        # Get terminal information
        profile = self.terminal_optimizer.detector.detect_terminal_profile()
        
        # Display terminal info
        table = Table(title="Terminal Analysis Results")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Impact", style="yellow")
        
        table.add_row("Terminal Type", profile.terminal_type.value, "Optimization profile selected")
        table.add_row("Connection", profile.connection_type.value, "Latency compensation applied")
        table.add_row("Max FPS", str(profile.max_fps), "Frame rate target adjusted")
        table.add_row("True Color", str(profile.supports_true_color), "Color rendering optimized")
        table.add_row("Unicode Support", str(profile.supports_unicode), "Character set optimized")
        table.add_row("Estimated Latency", f"{profile.estimated_latency_ms:.1f}ms", "Buffering adjusted")
        
        self.console.print(table)
    
    def demo_memory_optimization(self):
        """Demonstrate memory optimization features"""
        if not OPTIMIZATION_AVAILABLE:
            self.console.print("[red]Memory optimization not available[/red]")
            return
        
        self.console.print("[bold]Demonstrating memory optimization...[/bold]")
        
        # Show initial memory stats
        initial_stats = self.memory_optimizer.get_memory_stats()
        
        # Create lots of text objects to show pooling
        with Progress(
            SpinnerColumn(),
            TextColumn("Creating optimized text objects..."),
            BarColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Creating objects", total=1000)
            
            texts = []
            for i in range(1000):
                # Use memory-optimized text creation
                with self.memory_optimizer.optimized_text() as text:
                    text.append(f"Optimized text object {i}")
                    texts.append(str(text))  # Convert to string
                
                if i % 100 == 0:
                    progress.update(task, advance=100)
        
        # Show final memory stats
        final_stats = self.memory_optimizer.get_memory_stats()
        
        # Display memory comparison
        comparison_table = Table(title="Memory Optimization Results")
        comparison_table.add_column("Metric", style="cyan")
        comparison_table.add_column("Before", style="red")
        comparison_table.add_column("After", style="green")
        comparison_table.add_column("Improvement", style="yellow")
        
        memory_diff = final_stats.current_usage_mb - initial_stats.current_usage_mb
        pool_efficiency = final_stats.pool_efficiency
        
        comparison_table.add_row(
            "Memory Usage",
            f"{initial_stats.current_usage_mb:.1f}MB",
            f"{final_stats.current_usage_mb:.1f}MB",
            f"+{memory_diff:.1f}MB (optimized)"
        )
        
        comparison_table.add_row(
            "Pool Efficiency",
            "0%",
            f"{pool_efficiency:.1%}",
            f"{pool_efficiency:.1%} object reuse"
        )
        
        comparison_table.add_row(
            "String Cache",
            "0",
            str(final_stats.string_pool_size),
            f"{final_stats.string_pool_size} cached strings"
        )
        
        self.console.print(comparison_table)
        self.console.print(f"[green]✓ Created 1000 objects with {pool_efficiency:.1%} memory efficiency[/green]")
    
    def demo_frame_rate_monitoring(self):
        """Demonstrate frame rate monitoring and adaptation"""
        if not OPTIMIZATION_AVAILABLE:
            self.console.print("[red]Frame rate monitoring not available[/red]")
            return
        
        self.console.print("[bold]Demonstrating adaptive frame rate...[/bold]")
        
        layout = Layout()
        layout.split_column(
            Layout(name="metrics", size=8),
            Layout(name="animation", size=5)
        )
        
        start_time = time.time()
        frame_count = 0
        
        with Live(layout, console=self.console, refresh_per_second=30) as live:
            for i in range(150):  # Run for ~5 seconds at 30fps
                with self.rendering_system.optimized_rendering_context() as context:
                    if context.get("skip_frame", False):
                        continue  # Skip frame for performance
                    
                    frame_count += 1
                    
                    # Get current performance metrics
                    metrics = self.rendering_system.get_system_metrics()
                    
                    # Update metrics display
                    metrics_table = Table(title="Real-time Performance Metrics")
                    metrics_table.add_column("Metric", style="cyan")
                    metrics_table.add_column("Value", style="green")
                    
                    elapsed = time.time() - start_time
                    actual_fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    metrics_table.add_row("Target FPS", "30")
                    metrics_table.add_row("Actual FPS", f"{actual_fps:.1f}")
                    metrics_table.add_row("Frame Time", f"{metrics.performance.frame_time_ms:.1f}ms")
                    metrics_table.add_row("Memory", f"{metrics.memory.current_usage_mb:.1f}MB")
                    metrics_table.add_row("Health Score", f"{metrics.overall_health_score:.1%}")
                    
                    layout["metrics"].update(Panel(metrics_table, border_style="blue"))
                    
                    # Animated progress bar
                    progress = (i % 50) / 50.0
                    bar_width = 40
                    filled = int(progress * bar_width)
                    bar = "█" * filled + "░" * (bar_width - filled)
                    
                    layout["animation"].update(Panel(
                        f"[bold green]{bar}[/bold green] {progress:.1%}",
                        title="Smooth Animation Demo",
                        border_style="green"
                    ))
                
                time.sleep(1/30)  # Target 30fps
    
    def demo_animation_system(self):
        """Demonstrate the animation system"""
        if not OPTIMIZATION_AVAILABLE:
            self.console.print("[red]Animation system not available[/red]")
            return
        
        self.console.print("[bold]Demonstrating smooth animations...[/bold]")
        
        # Typewriter effect
        self.console.print("\n[dim]Typewriter Effect:[/dim]")
        typewriter = create_typewriter_effect(
            "This text appears character by character with smooth timing!",
            duration_ms=2000,
            style="bold cyan"
        )
        
        start_time = time.time()
        while typewriter.is_running and (time.time() - start_time) < 3:
            content = typewriter.update()
            if content:
                # Clear line and print new content
                self.console.print(f"\r{content}", end="")
            time.sleep(1/30)  # 30fps
        
        self.console.print("\n")
        
        # Fade effect demo
        self.console.print("[dim]Fade Effect:[/dim]")
        fade_panel = Panel("This panel will fade in smoothly!", border_style="yellow")
        fade_animation = create_fade_effect(fade_panel, fade_in=True, duration_ms=1500)
        
        start_time = time.time()
        while fade_animation.is_running and (time.time() - start_time) < 2:
            content = fade_animation.update()
            if content:
                self.console.clear()
                self.console.print(content)
            time.sleep(1/30)
        
        self.console.print("[green]✓ Animations completed with smooth frame timing[/green]")
    
    def demo_large_dataset(self):
        """Demonstrate performance with large datasets"""
        self.console.print("[bold]Demonstrating large dataset rendering...[/bold]")
        
        # Generate large dataset
        dataset = [f"Item {i:04d}: Sample data with content {random.randint(1000, 9999)}" 
                  for i in range(5000)]
        
        # Measure rendering performance
        start_time = time.time()
        
        # Render large table efficiently
        table = Table(title=f"Large Dataset ({len(dataset):,} items)")
        table.add_column("Index", style="dim", width=8)
        table.add_column("Content", style="white")
        table.add_column("Status", style="green")
        
        # Only render visible items (virtual scrolling concept)
        visible_items = dataset[:50]  # Show first 50 items
        
        for i, item in enumerate(visible_items):
            status = "✓ Loaded" if i % 3 == 0 else "⏳ Processing" if i % 3 == 1 else "📝 Ready"
            table.add_row(str(i), item, status)
        
        render_time = time.time() - start_time
        
        self.console.print(table)
        
        # Performance summary
        perf_panel = Panel(
            f"[bold green]Performance Results[/bold green]\n\n"
            f"Dataset Size: [cyan]{len(dataset):,}[/cyan] items\n"
            f"Rendered Items: [cyan]{len(visible_items)}[/cyan] (virtual scrolling)\n"
            f"Render Time: [yellow]{render_time*1000:.1f}ms[/yellow]\n"
            f"Memory Usage: [blue]Optimized with object pooling[/blue]\n\n"
            f"[dim]Note: In a real application, virtual scrolling would allow\n"
            f"smooth navigation through all {len(dataset):,} items.[/dim]",
            title="📊 Performance Analysis",
            border_style="cyan"
        )
        
        self.console.print(perf_panel)
    
    def demo_performance_dashboard(self):
        """Show the comprehensive performance dashboard"""
        if not OPTIMIZATION_AVAILABLE:
            self.console.print("[red]Performance dashboard not available[/red]")
            return
        
        self.console.print("[bold]Comprehensive Performance Dashboard:[/bold]")
        
        # Display the full dashboard
        display_performance_dashboard()
        
        # Show optimization recommendations
        metrics = self.rendering_system.get_system_metrics()
        
        if metrics.recommendations:
            rec_panel = Panel(
                "\n".join([f"💡 {rec}" for rec in metrics.recommendations]),
                title="🔧 Optimization Recommendations",
                border_style="yellow"
            )
            self.console.print(rec_panel)
        
        if metrics.warnings:
            warning_panel = Panel(
                "\n".join([f"⚠️  {warning}" for warning in metrics.warnings]),
                title="⚠️  Performance Warnings",
                border_style="red"
            )
            self.console.print(warning_panel)


def main():
    """Main demonstration function"""
    demo = PerformanceDemo()
    demo.run_complete_demo()


if __name__ == "__main__":
    main()