"""
Comprehensive UI/UX Test Framework Configuration
==============================================

Configuration for all test categories with performance targets and CI/CD integration.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field
import json

@dataclass
class PerformanceTargets:
    """Performance testing targets based on research"""
    target_fps: int = 60
    max_frame_time_ms: float = 16.67  # 60fps = 16.67ms per frame
    memory_limit_mb: int = 200
    startup_time_ms: int = 1000
    response_time_ms: int = 100
    animation_smoothness_threshold: float = 0.95
    
@dataclass
class CrossPlatformTargets:
    """Cross-platform compatibility targets"""
    supported_terminals: List[str] = field(default_factory=lambda: [
        'windows_terminal', 'iterm2', 'gnome_terminal', 'alacritty', 'kitty', 'tmux', 'screen'
    ])
    min_terminal_width: int = 80
    min_terminal_height: int = 24
    ssh_latency_tolerance_ms: int = 200
    unicode_support_required: bool = True

@dataclass
class AccessibilityTargets:
    """Accessibility testing targets"""
    screen_readers: List[str] = field(default_factory=lambda: ['nvda', 'jaws', 'voiceover', 'orca'])
    keyboard_navigation_coverage: float = 100.0  # 100% keyboard navigable
    contrast_ratio_min: float = 4.5  # WCAG AA standard
    text_scaling_support: List[int] = field(default_factory=lambda: [100, 125, 150, 200])

@dataclass
class WebInterfaceTargets:
    """CLIX web interface testing targets"""
    supported_browsers: List[str] = field(default_factory=lambda: [
        'chrome', 'firefox', 'safari', 'edge'
    ])
    websocket_connection_timeout_ms: int = 5000
    websocket_reconnection_attempts: int = 3
    browser_compatibility_matrix: Dict[str, List[str]] = field(default_factory=lambda: {
        'chrome': ['latest', 'latest-1', 'latest-2'],
        'firefox': ['latest', 'latest-1', 'latest-2'],
        'safari': ['latest', 'latest-1'],
        'edge': ['latest', 'latest-1']
    })

@dataclass
class AIIntelligenceTargets:
    """AI intelligence testing targets"""
    model_accuracy_threshold: float = 0.85
    prediction_latency_ms: int = 50
    adaptation_effectiveness_score: float = 0.75
    ml_model_formats: List[str] = field(default_factory=lambda: ['tensorflowjs', 'onnx'])
    behavior_learning_accuracy: float = 0.80

@dataclass
class TestFrameworkConfig:
    """Comprehensive test framework configuration"""
    
    # Test categories and their configurations
    performance: PerformanceTargets = field(default_factory=PerformanceTargets)
    cross_platform: CrossPlatformTargets = field(default_factory=CrossPlatformTargets)
    accessibility: AccessibilityTargets = field(default_factory=AccessibilityTargets)
    web_interface: WebInterfaceTargets = field(default_factory=WebInterfaceTargets)
    ai_intelligence: AIIntelligenceTargets = field(default_factory=AIIntelligenceTargets)
    
    # Framework settings
    parallel_execution: bool = True
    max_parallel_streams: int = 8
    test_timeout_seconds: int = 300
    retry_attempts: int = 3
    
    # CI/CD Integration
    ci_integration_enabled: bool = True
    test_results_format: List[str] = field(default_factory=lambda: ['junit', 'json', 'html'])
    coverage_threshold: float = 85.0
    performance_regression_threshold: float = 10.0  # 10% performance degradation
    
    # Output and reporting
    results_directory: Path = field(default_factory=lambda: Path("test_results"))
    screenshots_on_failure: bool = True
    video_recording: bool = False
    detailed_logs: bool = True
    
    # Environment-specific settings
    test_environments: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'local': {
            'docker_compose': False,
            'real_terminals': True,
            'gpu_acceleration': True
        },
        'ci': {
            'docker_compose': True,
            'headless_mode': True,
            'gpu_acceleration': False,
            'virtual_display': True
        },
        'staging': {
            'docker_compose': True,
            'real_browsers': True,
            'performance_monitoring': True
        }
    })

class TestFrameworkConfigManager:
    """Manages test framework configuration loading and validation"""
    
    def __init__(self, config_file: Path = None):
        self.config_file = config_file or Path("tests/ui_ux_comprehensive/config.json")
        self.config = self._load_or_create_config()
    
    def _load_or_create_config(self) -> TestFrameworkConfig:
        """Load existing config or create default"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                return self._dict_to_config(config_data)
            else:
                config = TestFrameworkConfig()
                self.save_config(config)
                return config
        except Exception as e:
            print(f"Warning: Failed to load config, using defaults: {e}")
            return TestFrameworkConfig()
    
    def _dict_to_config(self, data: Dict[str, Any]) -> TestFrameworkConfig:
        """Convert dictionary to TestFrameworkConfig"""
        # This is simplified - in a real implementation, you'd want proper deserialization
        config = TestFrameworkConfig()
        
        # Update performance targets
        if 'performance' in data:
            perf_data = data['performance']
            config.performance.target_fps = perf_data.get('target_fps', 60)
            config.performance.memory_limit_mb = perf_data.get('memory_limit_mb', 200)
            config.performance.max_frame_time_ms = perf_data.get('max_frame_time_ms', 16.67)
        
        # Update other sections similarly...
        config.parallel_execution = data.get('parallel_execution', True)
        config.max_parallel_streams = data.get('max_parallel_streams', 8)
        config.ci_integration_enabled = data.get('ci_integration_enabled', True)
        
        return config
    
    def save_config(self, config: TestFrameworkConfig):
        """Save configuration to file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = {
                'performance': {
                    'target_fps': config.performance.target_fps,
                    'max_frame_time_ms': config.performance.max_frame_time_ms,
                    'memory_limit_mb': config.performance.memory_limit_mb,
                    'startup_time_ms': config.performance.startup_time_ms,
                    'response_time_ms': config.performance.response_time_ms,
                    'animation_smoothness_threshold': config.performance.animation_smoothness_threshold
                },
                'cross_platform': {
                    'supported_terminals': config.cross_platform.supported_terminals,
                    'min_terminal_width': config.cross_platform.min_terminal_width,
                    'min_terminal_height': config.cross_platform.min_terminal_height,
                    'ssh_latency_tolerance_ms': config.cross_platform.ssh_latency_tolerance_ms,
                    'unicode_support_required': config.cross_platform.unicode_support_required
                },
                'accessibility': {
                    'screen_readers': config.accessibility.screen_readers,
                    'keyboard_navigation_coverage': config.accessibility.keyboard_navigation_coverage,
                    'contrast_ratio_min': config.accessibility.contrast_ratio_min,
                    'text_scaling_support': config.accessibility.text_scaling_support
                },
                'web_interface': {
                    'supported_browsers': config.web_interface.supported_browsers,
                    'websocket_connection_timeout_ms': config.web_interface.websocket_connection_timeout_ms,
                    'websocket_reconnection_attempts': config.web_interface.websocket_reconnection_attempts,
                    'browser_compatibility_matrix': config.web_interface.browser_compatibility_matrix
                },
                'ai_intelligence': {
                    'model_accuracy_threshold': config.ai_intelligence.model_accuracy_threshold,
                    'prediction_latency_ms': config.ai_intelligence.prediction_latency_ms,
                    'adaptation_effectiveness_score': config.ai_intelligence.adaptation_effectiveness_score,
                    'ml_model_formats': config.ai_intelligence.ml_model_formats,
                    'behavior_learning_accuracy': config.ai_intelligence.behavior_learning_accuracy
                },
                'parallel_execution': config.parallel_execution,
                'max_parallel_streams': config.max_parallel_streams,
                'test_timeout_seconds': config.test_timeout_seconds,
                'retry_attempts': config.retry_attempts,
                'ci_integration_enabled': config.ci_integration_enabled,
                'test_results_format': config.test_results_format,
                'coverage_threshold': config.coverage_threshold,
                'performance_regression_threshold': config.performance_regression_threshold,
                'results_directory': str(config.results_directory),
                'screenshots_on_failure': config.screenshots_on_failure,
                'video_recording': config.video_recording,
                'detailed_logs': config.detailed_logs,
                'test_environments': config.test_environments
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Failed to save config: {e}")
    
    def get_config(self) -> TestFrameworkConfig:
        """Get current configuration"""
        return self.config
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values"""
        # Apply updates to config
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        self.save_config(self.config)
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any issues"""
        issues = []
        
        # Validate performance targets
        if self.config.performance.target_fps <= 0:
            issues.append("target_fps must be positive")
        
        if self.config.performance.memory_limit_mb <= 0:
            issues.append("memory_limit_mb must be positive")
        
        # Validate environment requirements
        for env_name, env_config in self.config.test_environments.items():
            if not isinstance(env_config, dict):
                issues.append(f"test_environment '{env_name}' must be a dictionary")
        
        # Validate accessibility requirements
        if self.config.accessibility.contrast_ratio_min < 3.0:
            issues.append("contrast_ratio_min should be at least 3.0 for accessibility")
        
        return issues

# Global configuration instance
_config_manager = None

def get_test_config() -> TestFrameworkConfig:
    """Get global test configuration"""
    global _config_manager
    if _config_manager is None:
        _config_manager = TestFrameworkConfigManager()
    return _config_manager.get_config()

def update_test_config(updates: Dict[str, Any]):
    """Update global test configuration"""
    global _config_manager
    if _config_manager is None:
        _config_manager = TestFrameworkConfigManager()
    _config_manager.update_config(updates)

def validate_test_config() -> List[str]:
    """Validate global test configuration"""
    global _config_manager
    if _config_manager is None:
        _config_manager = TestFrameworkConfigManager()
    return _config_manager.validate_config()

# Environment detection utilities
def detect_test_environment() -> str:
    """Detect current test environment"""
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS') or os.environ.get('JENKINS_URL'):
        return 'ci'
    elif os.environ.get('STAGING') or os.environ.get('TESTING_ENV') == 'staging':
        return 'staging'
    else:
        return 'local'

def get_environment_config() -> Dict[str, Any]:
    """Get configuration for current environment"""
    env = detect_test_environment()
    config = get_test_config()
    return config.test_environments.get(env, config.test_environments['local'])

# Test discovery utilities
def get_test_categories() -> List[str]:
    """Get all available test categories"""
    return [
        'unit_tests',
        'integration_tests', 
        'performance_tests',
        'cross_platform_tests',
        'accessibility_tests',
        'web_interface_tests',
        'ai_intelligence_tests',
        'regression_tests'
    ]

def get_test_category_config(category: str) -> Dict[str, Any]:
    """Get configuration for specific test category"""
    config = get_test_config()
    
    category_configs = {
        'performance_tests': {
            'targets': config.performance,
            'parallel_execution': True,
            'timeout': 60
        },
        'cross_platform_tests': {
            'targets': config.cross_platform,
            'parallel_execution': True,
            'timeout': 120
        },
        'accessibility_tests': {
            'targets': config.accessibility,
            'parallel_execution': False,  # Sequential for better reliability
            'timeout': 180
        },
        'web_interface_tests': {
            'targets': config.web_interface,
            'parallel_execution': True,
            'timeout': 240
        },
        'ai_intelligence_tests': {
            'targets': config.ai_intelligence,
            'parallel_execution': True,
            'timeout': 300
        }
    }
    
    return category_configs.get(category, {'timeout': config.test_timeout_seconds})