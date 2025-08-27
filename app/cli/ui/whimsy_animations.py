"""
Whimsy Animation Integration for LocalAgent CLI
Lightweight integration module for whimsical UI components
"""

# Re-export all whimsy components from our development directory
import sys
from pathlib import Path

# Add our development path for import
whimsy_path = Path("/tmp/ui-animations-whimsy")
if whimsy_path.exists() and str(whimsy_path) not in sys.path:
    sys.path.insert(0, str(whimsy_path))

try:
    # Import all whimsical components
    from whimsy_ui_integration import (
        WhimsicalUIOrchestrator,
        WhimsyConfig
    )
    
    from advanced_progress import (
        AdvancedProgressSystem,
        AnimationSpeed
    )
    
    from particle_effects import (
        ParticleEffectPresets,
        AnimatedCelebration
    )
    
    from floating_notifications import (
        AdvancedNotificationSystem,
        NotificationType
    )
    
    from interactive_visual_elements import (
        ASCIIArtGenerator,
        BannerStyle
    )
    
    # Mark as available
    WHIMSY_AVAILABLE = True
    
except ImportError as e:
    # Graceful fallback if whimsy components not available
    WHIMSY_AVAILABLE = False
    
    # Create mock classes for graceful fallback
    class WhimsicalUIOrchestrator:
        def __init__(self, *args, **kwargs):
            pass
        async def startup_sequence(self, *args, **kwargs):
            pass
        async def handle_success(self, *args, **kwargs):
            pass
        async def handle_error(self, *args, **kwargs):
            pass
        async def show_progress_magic(self, *args, **kwargs):
            return lambda *a, **k: None
    
    class WhimsyConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class AnimationSpeed:
        SLOW = 0.2
        NORMAL = 0.1
        FAST = 0.05
        BLAZING = 0.02
    
    class AdvancedProgressSystem:
        def __init__(self, *args, **kwargs):
            pass
        def create_enhanced_workflow_progress(self):
            class MockContext:
                def __enter__(self):
                    return None
                def __exit__(self, *args):
                    pass
            return MockContext()
    
    # Other mock classes
    class ParticleEffectPresets:
        @staticmethod
        def success_celebration(*args, **kwargs):
            pass
    
    class AnimatedCelebration:
        def __init__(self, *args, **kwargs):
            pass
        async def play_success_sequence(self, *args, **kwargs):
            pass
    
    class AdvancedNotificationSystem:
        def __init__(self, *args, **kwargs):
            pass
        async def show_notification(self, *args, **kwargs):
            pass
    
    class NotificationType:
        SUCCESS = "success"
        ERROR = "error"
        INFO = "info"
        MAGIC = "magic"
    
    class ASCIIArtGenerator:
        @staticmethod
        def create_text_banner(*args, **kwargs):
            return ["Banner not available"]
    
    class BannerStyle:
        FUTURISTIC = "futuristic"

# Export all classes
__all__ = [
    'WhimsicalUIOrchestrator',
    'WhimsyConfig', 
    'AnimationSpeed',
    'AdvancedProgressSystem',
    'ParticleEffectPresets',
    'AnimatedCelebration',
    'AdvancedNotificationSystem',
    'NotificationType',
    'ASCIIArtGenerator',
    'BannerStyle',
    'WHIMSY_AVAILABLE'
]