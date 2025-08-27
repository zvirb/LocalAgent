"""
LocalAgent CLI UI Components
Modern interactive interface with Claude CLI-style theming
"""

# Core UI components
from .display import DisplayManager, create_display_manager, create_themed_console
from .enhanced_prompts import ModernInteractivePrompts, GuidedSetupWizard, create_modern_prompts, create_guided_wizard
from .prompts import ConfigurationWizard, InteractivePrompts  # Legacy compatibility
from .chat import InteractiveChatSession

# Performance optimization system
try:
    from .rendering_system import (
        get_rendering_system, create_optimized_console, optimized_rendering,
        render_with_optimization, display_performance_dashboard,
        RenderingSystemConfig, SystemMetrics
    )
    
    from .performance_monitor import (
        get_rendering_optimizer, PerformanceMetrics, TerminalCapabilities
    )
    
    from .memory_optimizer import (
        get_memory_optimizer, intern_string, cache_styled_text,
        optimized_text, optimized_console, optimize_memory, MemoryStats
    )
    
    from .animation_engine import (
        get_animation_manager, create_typewriter_effect, create_fade_effect,
        create_virtual_scroll_view, animated_progress
    )
    
    from .terminal_optimizer import (
        get_terminal_optimizer, optimize_for_terminal, buffered_print
    )
    
    PERFORMANCE_OPTIMIZATION_AVAILABLE = True
    
except ImportError:
    PERFORMANCE_OPTIMIZATION_AVAILABLE = False

# Theme system
try:
    from .themes import (
        ClaudeThemeManager, get_theme_manager, get_console, get_inquirer_style,
        format_provider, format_status, format_phase, CLAUDE_COLORS, STATUS_ICONS
    )
    THEMES_AVAILABLE = True
except ImportError:
    # Fallback definitions
    def get_console():
        from rich.console import Console
        return Console()
    
    def get_theme_manager():
        return None
    
    def format_provider(name, enabled=True):
        return f"{'✓' if enabled else '✗'} {name}"
    
    def format_status(status, message):
        return f"• {message}"
    
    def format_phase(phase_num, name, status='pending'):
        return f"Phase {phase_num}: {name}"
    
    CLAUDE_COLORS = {}
    STATUS_ICONS = {}
    THEMES_AVAILABLE = False

# Version and feature flags
__version__ = "1.0.0"
__features__ = {
    'modern_prompts': True,
    'fuzzy_search': True,  # Will be False if InquirerPy not available
    'claude_theming': THEMES_AVAILABLE,
    'enhanced_progress': True,
    'guided_wizard': True,
    'live_dashboard': True,
    'performance_optimization': PERFORMANCE_OPTIMIZATION_AVAILABLE,
    'frame_rate_monitoring': PERFORMANCE_OPTIMIZATION_AVAILABLE,
    'memory_optimization': PERFORMANCE_OPTIMIZATION_AVAILABLE,
    'terminal_optimization': PERFORMANCE_OPTIMIZATION_AVAILABLE,
    'animation_system': PERFORMANCE_OPTIMIZATION_AVAILABLE,
}

# Update features based on actual availability
try:
    import inquirerpy
    __features__['fuzzy_search'] = True
except ImportError:
    __features__['fuzzy_search'] = False

# Main UI interface factory
def create_ui_interface(console=None, debug_mode=False):
    """
    Create a complete UI interface with all components
    
    Args:
        console: Optional Rich Console instance
        debug_mode: Enable debug mode for additional logging
    
    Returns:
        dict: Complete UI interface with all components
    """
    # Use themed console if available, otherwise create basic console
    if console is None:
        console = get_console()
    
    # Create components
    display_manager = create_display_manager(console, debug_mode)
    interactive_prompts = create_modern_prompts(console)
    guided_wizard = create_guided_wizard(console)
    theme_manager = get_theme_manager() if THEMES_AVAILABLE else None
    
    return {
        'console': console,
        'display': display_manager,
        'prompts': interactive_prompts,
        'wizard': guided_wizard,
        'theme_manager': theme_manager,
        'features': __features__.copy(),
        'version': __version__
    }


def get_ui_capabilities():
    """
    Get current UI capabilities and feature availability
    
    Returns:
        dict: Available features and their status
    """
    return {
        'features': __features__.copy(),
        'version': __version__,
        'theme_system': THEMES_AVAILABLE,
        'modern_prompts': True,
        'enhanced_display': True,
        'fallback_mode': not THEMES_AVAILABLE or not __features__['fuzzy_search']
    }


def print_ui_status(console=None):
    """
    Print current UI system status and available features
    """
    if console is None:
        console = get_console()
    
    from rich.panel import Panel
    from rich.table import Table
    
    # Feature status table
    status_table = Table(title="LocalAgent UI Features", show_header=True, header_style="bold blue")
    status_table.add_column("Feature", style="cyan", width=20)
    status_table.add_column("Status", style="white", width=12)
    status_table.add_column("Description", style="dim")
    
    features_info = {
        'modern_prompts': 'Modern interactive prompts with Rich integration',
        'fuzzy_search': 'Fuzzy search capabilities with InquirerPy',
        'claude_theming': 'Claude CLI-style color schemes and theming',
        'enhanced_progress': 'Advanced progress indicators and displays',
        'guided_wizard': 'Step-by-step configuration wizards',
        'live_dashboard': 'Real-time dashboard and monitoring'
    }
    
    for feature, description in features_info.items():
        status = "✓ Available" if __features__.get(feature, False) else "✗ Unavailable"
        status_table.add_row(feature.replace('_', ' ').title(), status, description)
    
    info_panel = Panel(
        status_table,
        title=f"🎨 LocalAgent UI System v{__version__}",
        border_style="blue"
    )
    
    console.print(info_panel)
    
    # Show mode information
    mode = "Full" if THEMES_AVAILABLE and __features__['fuzzy_search'] else "Fallback"
    mode_color = "green" if mode == "Full" else "yellow"
    
    console.print(f"\n[bold {mode_color}]Current Mode: {mode}[/bold {mode_color}]")
    
    if mode == "Fallback":
        console.print("[dim]• Some advanced features may use simplified interfaces")
        console.print("• Install inquirerpy for full modern prompt capabilities")
        console.print("• All core functionality remains available[/dim]")


# Convenience exports for common use cases
__all__ = [
    # Legacy compatibility
    'DisplayManager', 'InteractivePrompts', 'ConfigurationWizard', 'InteractiveChatSession',
    
    # Modern components
    'ModernInteractivePrompts', 'GuidedSetupWizard',
    
    # Factory functions  
    'create_display_manager', 'create_modern_prompts', 'create_guided_wizard',
    'create_themed_console', 'create_ui_interface',
    
    # Theme system
    'get_theme_manager', 'get_console', 
    'format_provider', 'format_status', 'format_phase',
    
    # Utility functions
    'get_ui_capabilities', 'print_ui_status',
    
    # Constants
    'CLAUDE_COLORS', 'STATUS_ICONS', 'THEMES_AVAILABLE',
    '__version__', '__features__', 'PERFORMANCE_OPTIMIZATION_AVAILABLE'
]

# Add performance optimization exports if available
if PERFORMANCE_OPTIMIZATION_AVAILABLE:
    __all__.extend([
        # Rendering System
        'get_rendering_system', 'create_optimized_console', 'optimized_rendering',
        'render_with_optimization', 'display_performance_dashboard',
        'RenderingSystemConfig', 'SystemMetrics',
        
        # Performance Monitoring
        'get_rendering_optimizer', 'PerformanceMetrics', 'TerminalCapabilities',
        
        # Memory Optimization
        'get_memory_optimizer', 'intern_string', 'cache_styled_text',
        'optimized_text', 'optimized_console', 'optimize_memory', 'MemoryStats',
        
        # Animation System
        'get_animation_manager', 'create_typewriter_effect', 'create_fade_effect', 
        'create_virtual_scroll_view', 'animated_progress',
        
        # Terminal Optimization
        'get_terminal_optimizer', 'optimize_for_terminal', 'buffered_print',
    ])