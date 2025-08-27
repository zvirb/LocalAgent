#!/usr/bin/env python3
"""
Performance Optimization Demo Script
Demonstrates the CLI visual rendering performance improvements
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

def main():
    """Main demo function"""
    print("🚀 LocalAgent CLI Performance Optimization Demo")
    print("=" * 55)
    
    # Test basic import
    try:
        from cli.ui import PERFORMANCE_OPTIMIZATION_AVAILABLE
        print(f"✅ Performance optimization available: {PERFORMANCE_OPTIMIZATION_AVAILABLE}")
    except ImportError:
        print("❌ Could not import UI module")
        return False
    
    if not PERFORMANCE_OPTIMIZATION_AVAILABLE:
        print("⚠️  Performance optimization not available - using standard UI")
        return demo_fallback()
    
    return demo_optimized()

def demo_optimized():
    """Demo with full optimization system"""
    print("\n🎯 Running with Full Performance Optimization")
    print("-" * 45)
    
    try:
        # Import optimization components
        from cli.ui.rendering_system import get_rendering_system, display_performance_dashboard
        from cli.ui import create_optimized_console
        
        print("✅ Optimization modules loaded successfully")
        
        # Initialize rendering system
        system = get_rendering_system()
        console = create_optimized_console()
        
        print("✅ Optimized console created")
        
        # Display system information
        metrics = system.get_system_metrics()
        
        print(f"\n📊 System Performance Metrics:")
        print(f"   • Health Score: {metrics.overall_health_score:.1%}")
        print(f"   • Performance Tier: {metrics.performance_tier}")
        print(f"   • Memory Usage: {metrics.memory.current_usage_mb:.1f}MB")
        print(f"   • Frame Rate: {metrics.performance.fps:.1f} FPS")
        
        # Demonstrate optimized rendering
        console.print("\n🎨 [bold green]Optimized CLI rendering active![/bold green]")
        console.print("   • Frame rate monitoring enabled")
        console.print("   • Memory optimization active")
        console.print("   • Terminal capabilities detected")
        console.print("   • Animation system ready")
        
        # Show terminal capabilities
        terminal_stats = metrics.terminal_stats
        console.print(f"\n🖥️  Terminal Information:")
        console.print(f"   • Type: {terminal_stats.get('terminal_type', 'unknown')}")
        console.print(f"   • Connection: {terminal_stats.get('connection_type', 'unknown')}")
        console.print(f"   • True Color: {terminal_stats.get('supports_true_color', False)}")
        console.print(f"   • Unicode: {terminal_stats.get('supports_unicode', False)}")
        
        console.print(f"\n✅ [bold blue]Demo completed successfully![/bold blue]")
        console.print("The CLI is now running with optimized performance.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in optimized demo: {e}")
        return False

def demo_fallback():
    """Demo with fallback (standard) UI"""
    print("\n⚠️  Running with Standard UI (Fallback Mode)")
    print("-" * 45)
    
    try:
        from cli.ui import DisplayManager
        
        display = DisplayManager(debug_mode=False)
        
        display.print("📋 Standard CLI interface active")
        display.print("   • Basic Rich formatting available")
        display.print("   • Standard progress displays")
        display.print("   • Legacy terminal compatibility")
        
        display.print("\n💡 To enable performance optimization:")
        display.print("   1. Install required dependencies (psutil, rich)")
        display.print("   2. Ensure Python 3.8+ is available")
        display.print("   3. Restart the CLI application")
        
        display.print("\n✅ Fallback demo completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in fallback demo: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🎉 Demo completed successfully!")
    else:
        print(f"\n💥 Demo encountered errors")
    
    sys.exit(0 if success else 1)