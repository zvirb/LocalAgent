"""
Unified UI Configuration Management System
=========================================

Central configuration system for all LocalAgent UI/UX components including:
- Whimsical animations and UI system
- Performance optimization settings  
- CLIX web interface configuration
- AI intelligence adaptive features
- Enhanced layout and UX components

Ensures consistent configuration across all UI subsystems while maintaining
performance targets (60fps, <200MB memory) and backward compatibility.
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import logging

# Import performance monitoring for validation
try:
    from .performance_monitor import PerformanceMetrics, RenderingOptimizer
    PERFORMANCE_MONITORING_AVAILABLE = True
except ImportError:
    PERFORMANCE_MONITORING_AVAILABLE = False

# Import AI intelligence components
try:
    from ..intelligence import BehaviorTracker, PersonalizationEngine
    AI_INTELLIGENCE_AVAILABLE = True
except ImportError:
    AI_INTELLIGENCE_AVAILABLE = False

class UIFeatureLevel(Enum):
    """UI feature complexity levels"""
    MINIMAL = "minimal"      # Basic functionality, lowest resource usage
    STANDARD = "standard"    # Balanced features and performance
    ENHANCED = "enhanced"    # Full features with optimizations
    PREMIUM = "premium"      # All features, maximum capabilities

class AnimationQuality(Enum):
    """Animation quality settings"""
    DISABLED = "disabled"    # No animations
    LOW = "low"             # Simple animations, 15fps target
    MEDIUM = "medium"       # Smooth animations, 30fps target
    HIGH = "high"           # Full animations, 60fps target
    ADAPTIVE = "adaptive"   # Auto-adjust based on performance

class PerformanceProfile(Enum):
    """Performance optimization profiles"""
    POWER_SAVE = "power_save"     # Minimal CPU/memory usage
    BALANCED = "balanced"         # Standard performance
    PERFORMANCE = "performance"   # Prioritize responsiveness
    DEVELOPER = "developer"       # Full features, debug info

@dataclass
class WhimsyAnimationConfig:
    """Configuration for whimsical animation system"""
    enabled: bool = True
    quality: AnimationQuality = AnimationQuality.ADAPTIVE
    particle_effects: bool = True
    celebration_animations: bool = True
    interactive_elements: bool = True
    ascii_art_banners: bool = True
    notification_animations: bool = True
    
    # Performance settings
    max_particles: int = 50
    animation_fps: int = 60
    texture_quality: str = "high"  # "low", "medium", "high"
    
    # Fallback settings
    fallback_to_text: bool = True
    graceful_degradation: bool = True

@dataclass
class PerformanceOptimizationConfig:
    """Performance optimization system configuration"""
    enabled: bool = True
    profile: PerformanceProfile = PerformanceProfile.BALANCED
    
    # Frame rate settings
    target_fps: int = 60
    max_frame_time_ms: float = 16.67
    adaptive_fps: bool = True
    
    # Memory settings
    memory_limit_mb: int = 200
    memory_optimization: bool = True
    cache_size_limit: int = 1000
    
    # Rendering settings
    gpu_acceleration: bool = True
    text_rendering_cache: bool = True
    buffer_size: int = 3
    
    # Monitoring
    performance_monitoring: bool = True
    metrics_collection: bool = True
    auto_optimization: bool = True

@dataclass
class CLIXWebInterfaceConfig:
    """CLIX web terminal interface configuration"""
    enabled: bool = True
    port: int = 3000
    host: str = "localhost"
    
    # WebSocket settings
    websocket_port: int = 8080
    authentication_method: str = "header"  # header, token, none
    auto_reconnect: bool = True
    heartbeat_interval: int = 30
    
    # UI settings
    theme: str = "dark"  # dark, light, auto
    font_family: str = "JetBrains Mono"
    font_size: int = 14
    
    # Features
    file_drag_drop: bool = True
    collaboration: bool = True
    session_recording: bool = True
    mobile_support: bool = True
    
    # Performance
    webgl_acceleration: bool = True
    lazy_loading: bool = True
    pwa_enabled: bool = True

@dataclass
class AIIntelligenceConfig:
    """AI intelligence and adaptation configuration"""
    enabled: bool = True
    
    # Learning settings
    behavior_tracking: bool = True
    command_learning: bool = True
    adaptation_enabled: bool = True
    personalization_level: str = "medium"  # low, medium, high
    
    # ML model settings
    model_training: bool = True
    prediction_enabled: bool = True
    suggestion_quality: str = "high"  # low, medium, high
    
    # Privacy settings
    data_retention_days: int = 30
    anonymous_analytics: bool = True
    local_processing: bool = True
    
    # Performance
    max_inference_time_ms: float = 16.0  # Must be <16ms for 60fps
    batch_predictions: bool = True
    model_caching: bool = True

@dataclass
class EnhancedLayoutConfig:
    """Enhanced layout and UX components configuration"""
    enabled: bool = True
    
    # Layout settings
    responsive_design: bool = True
    adaptive_layouts: bool = True
    grid_system: str = "flexbox"  # flexbox, grid, hybrid
    
    # UX features
    interactive_prompts: bool = True
    guided_wizards: bool = True
    contextual_help: bool = True
    accessibility_features: bool = True
    
    # Theming
    theme_system: bool = True
    custom_themes: bool = True
    color_customization: bool = True
    
    # Advanced features
    multi_column_layout: bool = True
    resizable_panels: bool = True
    keyboard_shortcuts: bool = True

@dataclass
class BackwardCompatibilityConfig:
    """Backward compatibility settings"""
    legacy_support: bool = True
    fallback_ui: bool = True
    command_aliases: bool = True
    
    # Version compatibility
    min_terminal_version: str = "1.0.0"
    legacy_theme_support: bool = True
    old_config_migration: bool = True
    
    # Feature flags
    progressive_enhancement: bool = True
    graceful_degradation: bool = True

@dataclass
class UnifiedUIConfig:
    """Master configuration for all UI components"""
    
    # Feature level and profiles
    feature_level: UIFeatureLevel = UIFeatureLevel.STANDARD
    performance_profile: PerformanceProfile = PerformanceProfile.BALANCED
    
    # Component configurations
    whimsy_animations: WhimsyAnimationConfig = field(default_factory=WhimsyAnimationConfig)
    performance_optimization: PerformanceOptimizationConfig = field(default_factory=PerformanceOptimizationConfig)
    clix_web_interface: CLIXWebInterfaceConfig = field(default_factory=CLIXWebInterfaceConfig)
    ai_intelligence: AIIntelligenceConfig = field(default_factory=AIIntelligenceConfig)
    enhanced_layout: EnhancedLayoutConfig = field(default_factory=EnhancedLayoutConfig)
    backward_compatibility: BackwardCompatibilityConfig = field(default_factory=BackwardCompatibilityConfig)
    
    # Global settings
    debug_mode: bool = False
    telemetry_enabled: bool = False
    auto_update_config: bool = True
    config_validation: bool = True
    
    # Performance targets
    target_fps: int = 60
    max_memory_mb: int = 200
    startup_time_target_ms: int = 500
    
    # Metadata
    config_version: str = "1.0.0"
    last_updated: float = field(default_factory=time.time)


class UIConfigManager:
    """
    Unified UI Configuration Manager
    
    Manages all UI component configurations with:
    - Performance validation against targets
    - Automatic optimization based on system capabilities
    - Runtime configuration updates
    - Backward compatibility
    - Feature flag management
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".localagent" / "ui"
        self.config_file = self.config_dir / "unified_ui_config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("UIConfigManager")
        
        # Configuration state
        self.config: UnifiedUIConfig = UnifiedUIConfig()
        self.config_locked = False
        self.validation_enabled = True
        
        # Performance monitoring integration
        self.performance_optimizer: Optional[RenderingOptimizer] = None
        if PERFORMANCE_MONITORING_AVAILABLE:
            try:
                from .performance_monitor import get_rendering_optimizer
                self.performance_optimizer = get_rendering_optimizer()
            except Exception as e:
                self.logger.warning(f"Performance optimizer not available: {e}")
        
        # AI intelligence integration
        self.behavior_tracker: Optional[BehaviorTracker] = None
        self.personalization_engine: Optional[PersonalizationEngine] = None
        if AI_INTELLIGENCE_AVAILABLE:
            try:
                self.behavior_tracker = BehaviorTracker()
                self.personalization_engine = PersonalizationEngine(self.behavior_tracker)
            except Exception as e:
                self.logger.warning(f"AI intelligence not available: {e}")
        
        # Configuration change callbacks
        self.change_callbacks: List[Callable[[UnifiedUIConfig], None]] = []
        
        # Initialize
        asyncio.create_task(self._initialize_config_system())
    
    async def _initialize_config_system(self):
        """Initialize the configuration system"""
        try:
            # Load existing configuration
            await self.load_configuration()
            
            # Validate and optimize configuration
            await self.validate_configuration()
            await self._optimize_for_system_capabilities()
            
            # Apply configurations to subsystems
            await self._apply_configurations()
            
            self.logger.info("UI configuration system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize UI configuration system: {e}")
            # Use default configuration as fallback
            self.config = UnifiedUIConfig()
    
    async def load_configuration(self) -> UnifiedUIConfig:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Create configuration from data
                self.config = self._create_config_from_dict(config_data)
                
                # Migrate old configuration if needed
                if self.config.config_version != "1.0.0":
                    await self._migrate_configuration()
                
                self.logger.info("UI configuration loaded successfully")
            else:
                # Create default configuration
                self.config = UnifiedUIConfig()
                await self.save_configuration()
                self.logger.info("Created default UI configuration")
            
            return self.config
            
        except Exception as e:
            self.logger.error(f"Failed to load UI configuration: {e}")
            self.config = UnifiedUIConfig()
            return self.config
    
    async def save_configuration(self) -> bool:
        """Save current configuration to file"""
        try:
            # Update timestamp
            self.config.last_updated = time.time()
            
            # Convert to dictionary
            config_dict = asdict(self.config)
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            self.logger.debug("UI configuration saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save UI configuration: {e}")
            return False
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration against performance targets and constraints"""
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'performance_violations': [],
            'recommendations': []
        }
        
        try:
            # Performance target validation
            if self.config.target_fps > 60:
                validation_result['warnings'].append("Target FPS > 60 may not be achievable on all systems")
            
            if self.config.max_memory_mb > 500:
                validation_result['warnings'].append("Memory target > 500MB may cause system strain")
            
            # Feature compatibility validation
            if (self.config.whimsy_animations.enabled and 
                self.config.performance_profile == PerformanceProfile.POWER_SAVE):
                validation_result['warnings'].append("Animations enabled with power save profile may impact battery life")
            
            if (self.config.ai_intelligence.enabled and 
                not self.config.performance_optimization.enabled):
                validation_result['recommendations'].append("Enable performance optimization when using AI features")
            
            # System capability validation
            if self.performance_optimizer:
                metrics = self.performance_optimizer.get_current_metrics()
                
                if metrics.memory_usage_mb > self.config.max_memory_mb * 0.8:
                    validation_result['performance_violations'].append("Current memory usage approaching target limit")
                
                if metrics.fps < self.config.target_fps * 0.8:
                    validation_result['performance_violations'].append("Current FPS below target performance")
            
            # Web interface validation
            if self.config.clix_web_interface.enabled:
                if not (1024 <= self.config.clix_web_interface.port <= 65535):
                    validation_result['errors'].append("Web interface port must be between 1024-65535")
                    validation_result['valid'] = False
            
            # AI intelligence validation
            if self.config.ai_intelligence.enabled:
                if self.config.ai_intelligence.max_inference_time_ms > 16.0:
                    validation_result['performance_violations'].append("AI inference time exceeds 60fps requirement")
            
            self.logger.debug(f"Configuration validation completed: {validation_result}")
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")
            validation_result['valid'] = False
            self.logger.error(f"Configuration validation failed: {e}")
        
        return validation_result
    
    async def _optimize_for_system_capabilities(self):
        """Optimize configuration based on detected system capabilities"""
        try:
            if not self.performance_optimizer:
                return
            
            capabilities = self.performance_optimizer.capabilities
            current_metrics = self.performance_optimizer.get_current_metrics()
            
            # Memory-based optimizations
            if current_metrics.memory_usage_mb > 150:  # 75% of 200MB target
                self.config.whimsy_animations.max_particles = min(25, self.config.whimsy_animations.max_particles)
                self.config.performance_optimization.cache_size_limit = min(500, self.config.performance_optimization.cache_size_limit)
                self.logger.info("Applied memory optimization adjustments")
            
            # Performance-based optimizations
            if current_metrics.fps < 45:  # Below 75% of 60fps target
                self.config.whimsy_animations.quality = AnimationQuality.MEDIUM
                self.config.whimsy_animations.animation_fps = 30
                self.config.performance_optimization.target_fps = 30
                self.logger.info("Applied performance optimization adjustments")
            
            # Terminal capability optimizations
            if capabilities and capabilities.ssh_connection:
                self.config.whimsy_animations.quality = AnimationQuality.LOW
                self.config.performance_optimization.gpu_acceleration = False
                self.config.clix_web_interface.webgl_acceleration = False
                self.logger.info("Applied SSH connection optimizations")
            
            if capabilities and capabilities.memory_constraints:
                self.config.feature_level = UIFeatureLevel.STANDARD
                self.config.ai_intelligence.model_caching = False
                self.config.performance_optimization.memory_limit_mb = 100
                self.logger.info("Applied memory constraint optimizations")
            
        except Exception as e:
            self.logger.warning(f"System capability optimization failed: {e}")
    
    async def _apply_configurations(self):
        """Apply configurations to all UI subsystems"""
        try:
            # Apply whimsical animations configuration
            await self._apply_whimsy_config()
            
            # Apply performance optimization configuration
            await self._apply_performance_config()
            
            # Apply CLIX web interface configuration
            await self._apply_clix_config()
            
            # Apply AI intelligence configuration
            await self._apply_ai_intelligence_config()
            
            # Apply enhanced layout configuration
            await self._apply_enhanced_layout_config()
            
            # Notify all change callbacks
            for callback in self.change_callbacks:
                try:
                    callback(self.config)
                except Exception as e:
                    self.logger.warning(f"Configuration change callback failed: {e}")
            
            self.logger.debug("All UI configurations applied successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to apply UI configurations: {e}")
    
    async def _apply_whimsy_config(self):
        """Apply whimsical animations configuration"""
        try:
            # Import whimsy components if available
            from .whimsy_animations import WHIMSY_AVAILABLE
            
            if not WHIMSY_AVAILABLE or not self.config.whimsy_animations.enabled:
                self.logger.info("Whimsy animations disabled or not available")
                return
            
            # Configure whimsy system based on settings
            whimsy_config = self.config.whimsy_animations
            
            # Set animation quality and performance settings
            os.environ['WHIMSY_ANIMATION_QUALITY'] = whimsy_config.quality.value
            os.environ['WHIMSY_MAX_PARTICLES'] = str(whimsy_config.max_particles)
            os.environ['WHIMSY_TARGET_FPS'] = str(whimsy_config.animation_fps)
            
            self.logger.debug("Whimsy animations configuration applied")
            
        except ImportError:
            self.logger.info("Whimsy animations not available")
        except Exception as e:
            self.logger.warning(f"Failed to apply whimsy configuration: {e}")
    
    async def _apply_performance_config(self):
        """Apply performance optimization configuration"""
        try:
            if not self.performance_optimizer or not self.config.performance_optimization.enabled:
                return
            
            perf_config = self.config.performance_optimization
            
            # Update performance optimizer settings
            self.performance_optimizer.config.target_fps = perf_config.target_fps
            self.performance_optimizer.config.max_frame_time_ms = perf_config.max_frame_time_ms
            self.performance_optimizer.config.memory_limit_mb = perf_config.memory_limit_mb
            
            # Apply performance profile
            if perf_config.profile == PerformanceProfile.POWER_SAVE:
                self.performance_optimizer.performance_tier = "low"
            elif perf_config.profile == PerformanceProfile.PERFORMANCE:
                self.performance_optimizer.performance_tier = "high"
            else:
                self.performance_optimizer.performance_tier = "medium"
            
            self.logger.debug("Performance optimization configuration applied")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply performance configuration: {e}")
    
    async def _apply_clix_config(self):
        """Apply CLIX web interface configuration"""
        try:
            if not self.config.clix_web_interface.enabled:
                return
            
            # Set environment variables for CLIX configuration
            clix_config = self.config.clix_web_interface
            
            os.environ['CLIX_PORT'] = str(clix_config.port)
            os.environ['CLIX_HOST'] = clix_config.host
            os.environ['CLIX_WEBSOCKET_PORT'] = str(clix_config.websocket_port)
            os.environ['CLIX_THEME'] = clix_config.theme
            os.environ['CLIX_WEBGL_ENABLED'] = str(clix_config.webgl_acceleration).lower()
            
            self.logger.debug("CLIX web interface configuration applied")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply CLIX configuration: {e}")
    
    async def _apply_ai_intelligence_config(self):
        """Apply AI intelligence configuration"""
        try:
            if not self.config.ai_intelligence.enabled or not AI_INTELLIGENCE_AVAILABLE:
                return
            
            ai_config = self.config.ai_intelligence
            
            # Configure behavior tracking
            if self.behavior_tracker:
                self.behavior_tracker.enabled = ai_config.behavior_tracking
                
            # Configure personalization engine
            if self.personalization_engine:
                self.personalization_engine.personalization_level = ai_config.personalization_level
                self.personalization_engine.prediction_enabled = ai_config.prediction_enabled
            
            self.logger.debug("AI intelligence configuration applied")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply AI intelligence configuration: {e}")
    
    async def _apply_enhanced_layout_config(self):
        """Apply enhanced layout configuration"""
        try:
            layout_config = self.config.enhanced_layout
            
            # Set layout environment variables
            os.environ['UI_RESPONSIVE_DESIGN'] = str(layout_config.responsive_design).lower()
            os.environ['UI_GRID_SYSTEM'] = layout_config.grid_system
            os.environ['UI_THEME_SYSTEM'] = str(layout_config.theme_system).lower()
            
            self.logger.debug("Enhanced layout configuration applied")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply enhanced layout configuration: {e}")
    
    def _create_config_from_dict(self, config_data: Dict[str, Any]) -> UnifiedUIConfig:
        """Create UnifiedUIConfig from dictionary data"""
        try:
            # Extract component configurations
            whimsy_data = config_data.get('whimsy_animations', {})
            perf_data = config_data.get('performance_optimization', {})
            clix_data = config_data.get('clix_web_interface', {})
            ai_data = config_data.get('ai_intelligence', {})
            layout_data = config_data.get('enhanced_layout', {})
            compat_data = config_data.get('backward_compatibility', {})
            
            # Create component configurations
            whimsy_config = WhimsyAnimationConfig(**whimsy_data)
            perf_config = PerformanceOptimizationConfig(**perf_data)
            clix_config = CLIXWebInterfaceConfig(**clix_data)
            ai_config = AIIntelligenceConfig(**ai_data)
            layout_config = EnhancedLayoutConfig(**layout_data)
            compat_config = BackwardCompatibilityConfig(**compat_data)
            
            # Create main configuration
            config = UnifiedUIConfig(
                feature_level=UIFeatureLevel(config_data.get('feature_level', 'standard')),
                performance_profile=PerformanceProfile(config_data.get('performance_profile', 'balanced')),
                whimsy_animations=whimsy_config,
                performance_optimization=perf_config,
                clix_web_interface=clix_config,
                ai_intelligence=ai_config,
                enhanced_layout=layout_config,
                backward_compatibility=compat_config,
                debug_mode=config_data.get('debug_mode', False),
                telemetry_enabled=config_data.get('telemetry_enabled', False),
                target_fps=config_data.get('target_fps', 60),
                max_memory_mb=config_data.get('max_memory_mb', 200),
                config_version=config_data.get('config_version', '1.0.0')
            )
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to create configuration from dictionary: {e}")
            return UnifiedUIConfig()
    
    async def _migrate_configuration(self):
        """Migrate configuration from older versions"""
        self.logger.info(f"Migrating configuration from version {self.config.config_version} to 1.0.0")
        
        # Update version
        self.config.config_version = "1.0.0"
        
        # Save migrated configuration
        await self.save_configuration()
        
        self.logger.info("Configuration migration completed")
    
    def register_change_callback(self, callback: Callable[[UnifiedUIConfig], None]):
        """Register callback for configuration changes"""
        self.change_callbacks.append(callback)
    
    async def update_configuration(self, updates: Dict[str, Any]) -> bool:
        """Update configuration with new values"""
        try:
            if self.config_locked:
                self.logger.warning("Configuration is locked, updates ignored")
                return False
            
            # Apply updates to configuration
            for key, value in updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    self.logger.warning(f"Unknown configuration key: {key}")
            
            # Validate updated configuration
            validation_result = await self.validate_configuration()
            if not validation_result['valid']:
                self.logger.error(f"Configuration validation failed: {validation_result['errors']}")
                return False
            
            # Apply configurations
            await self._apply_configurations()
            
            # Save configuration
            await self.save_configuration()
            
            self.logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False
    
    def get_feature_status(self) -> Dict[str, Any]:
        """Get current status of all UI features"""
        return {
            'whimsy_animations': {
                'enabled': self.config.whimsy_animations.enabled,
                'quality': self.config.whimsy_animations.quality.value,
                'available': True  # Always available as it has fallbacks
            },
            'performance_optimization': {
                'enabled': self.config.performance_optimization.enabled,
                'profile': self.config.performance_optimization.profile.value,
                'available': PERFORMANCE_MONITORING_AVAILABLE
            },
            'clix_web_interface': {
                'enabled': self.config.clix_web_interface.enabled,
                'port': self.config.clix_web_interface.port,
                'available': True
            },
            'ai_intelligence': {
                'enabled': self.config.ai_intelligence.enabled,
                'personalization': self.config.ai_intelligence.personalization_level,
                'available': AI_INTELLIGENCE_AVAILABLE
            },
            'enhanced_layout': {
                'enabled': self.config.enhanced_layout.enabled,
                'responsive': self.config.enhanced_layout.responsive_design,
                'available': True
            }
        }
    
    def get_performance_status(self) -> Dict[str, Any]:
        """Get current performance status against targets"""
        status = {
            'targets': {
                'fps': self.config.target_fps,
                'memory_mb': self.config.max_memory_mb,
                'startup_ms': self.config.startup_time_target_ms
            },
            'current': {
                'fps': 0,
                'memory_mb': 0,
                'startup_ms': 0
            },
            'performance_grade': 'unknown'
        }
        
        if self.performance_optimizer:
            metrics = self.performance_optimizer.get_current_metrics()
            status['current'] = {
                'fps': metrics.fps,
                'memory_mb': metrics.memory_usage_mb,
                'startup_ms': 0  # Would need to track startup time
            }
            
            # Calculate performance grade
            fps_ratio = metrics.fps / self.config.target_fps
            memory_ratio = metrics.memory_usage_mb / self.config.max_memory_mb
            
            if fps_ratio >= 0.9 and memory_ratio <= 0.8:
                status['performance_grade'] = 'excellent'
            elif fps_ratio >= 0.7 and memory_ratio <= 1.0:
                status['performance_grade'] = 'good'
            elif fps_ratio >= 0.5 and memory_ratio <= 1.2:
                status['performance_grade'] = 'acceptable'
            else:
                status['performance_grade'] = 'poor'
        
        return status


# Global configuration manager instance
_global_config_manager: Optional[UIConfigManager] = None

def get_ui_config_manager() -> UIConfigManager:
    """Get global UI configuration manager instance"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = UIConfigManager()
    return _global_config_manager

async def initialize_ui_config_system(config_dir: Optional[Path] = None) -> UIConfigManager:
    """Initialize the UI configuration system"""
    global _global_config_manager
    _global_config_manager = UIConfigManager(config_dir)
    return _global_config_manager

def get_current_ui_config() -> UnifiedUIConfig:
    """Get current UI configuration"""
    return get_ui_config_manager().config