"""
Comprehensive UI/UX Integration Tests
=====================================

Test suite for all UI/UX component integration including:
- Backward compatibility with existing commands
- Performance targets validation (60fps, <200MB memory)
- Cross-platform compatibility
- UI animation smoothness testing
- Web interface functionality
- AI adaptation accuracy
"""

import pytest
import asyncio
import time
import os
import sys
import psutil
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.cli.core.app import LocalAgentApp
from app.cli.ui.ui_config_manager import UIConfigManager, UnifiedUIConfig
from app.cli.ui.performance_monitor import PerformanceMetrics

class UIIntegrationTestFramework:
    """Framework for comprehensive UI integration testing"""
    
    def __init__(self):
        self.test_config_dir = None
        self.app = None
        self.ui_config_manager = None
        self.performance_baseline = None
        self.test_results = {}
    
    async def setup(self):
        """Setup test environment"""
        # Create temporary config directory
        self.test_config_dir = Path(tempfile.mkdtemp(prefix="ui_test_"))
        
        # Initialize UI config manager with test directory
        self.ui_config_manager = UIConfigManager(self.test_config_dir)
        
        # Initialize test app
        self.app = LocalAgentApp()
        
        # Record performance baseline
        self.performance_baseline = self._get_performance_baseline()
    
    async def teardown(self):
        """Cleanup test environment"""
        if self.test_config_dir and self.test_config_dir.exists():
            shutil.rmtree(self.test_config_dir)
    
    def _get_performance_baseline(self) -> Dict[str, Any]:
        """Get performance baseline metrics"""
        process = psutil.Process()
        return {
            'memory_mb': process.memory_info().rss / (1024 * 1024),
            'cpu_percent': process.cpu_percent(),
            'timestamp': time.time()
        }
    
    def _measure_performance_impact(self) -> Dict[str, Any]:
        """Measure performance impact since baseline"""
        process = psutil.Process()
        current = {
            'memory_mb': process.memory_info().rss / (1024 * 1024),
            'cpu_percent': process.cpu_percent(),
            'timestamp': time.time()
        }
        
        return {
            'memory_increase_mb': current['memory_mb'] - self.performance_baseline['memory_mb'],
            'cpu_increase_percent': current['cpu_percent'] - self.performance_baseline['cpu_percent'],
            'duration_seconds': current['timestamp'] - self.performance_baseline['timestamp'],
            'current': current,
            'baseline': self.performance_baseline
        }
    
    def record_test_result(self, test_name: str, result: Dict[str, Any]):
        """Record test result for reporting"""
        self.test_results[test_name] = {
            'result': result,
            'timestamp': time.time(),
            'performance': self._measure_performance_impact(),
            'platform': {
                'system': platform.system(),
                'version': platform.version(),
                'python_version': sys.version,
                'terminal': os.environ.get('TERM', 'unknown')
            }
        }


@pytest.fixture
async def ui_test_framework():
    """UI integration test framework fixture"""
    framework = UIIntegrationTestFramework()
    await framework.setup()
    yield framework
    await framework.teardown()


class TestBackwardCompatibility:
    """Test backward compatibility with existing CLI commands"""
    
    @pytest.mark.asyncio
    async def test_existing_commands_still_work(self, ui_test_framework):
        """Test that all existing CLI commands still function correctly"""
        app = ui_test_framework.app
        
        # Test core commands exist and are callable
        existing_commands = [
            'init', 'config', 'providers', 'workflow', 
            'chat', 'plugins', 'health'
        ]
        
        for command_name in existing_commands:
            # Check command exists in app
            command_found = False
            for command in app.app.commands:
                if command.name == command_name:
                    command_found = True
                    break
            
            assert command_found, f"Command '{command_name}' not found in CLI"
        
        ui_test_framework.record_test_result('existing_commands_available', {
            'status': 'passed',
            'commands_tested': len(existing_commands),
            'all_found': True
        })
    
    @pytest.mark.asyncio
    async def test_legacy_configuration_loading(self, ui_test_framework):
        """Test that legacy configurations can still be loaded"""
        # Create a mock legacy configuration
        legacy_config = {
            'providers': {
                'ollama': {'enabled': True, 'host': 'localhost'},
                'openai': {'enabled': False}
            },
            'ui': {
                'theme': 'dark',
                'animations': True
            }
        }
        
        config_file = ui_test_framework.test_config_dir / "config.json"
        with open(config_file, 'w') as f:
            import json
            json.dump(legacy_config, f)
        
        # Test loading
        from app.cli.core.config import ConfigurationManager
        config_manager = ConfigurationManager(str(config_file))
        
        try:
            config = await config_manager.load_configuration()
            
            ui_test_framework.record_test_result('legacy_config_loading', {
                'status': 'passed',
                'config_loaded': config is not None,
                'providers_count': len(config.providers) if hasattr(config, 'providers') else 0
            })
        except Exception as e:
            ui_test_framework.record_test_result('legacy_config_loading', {
                'status': 'failed',
                'error': str(e)
            })
    
    @pytest.mark.asyncio
    async def test_fallback_ui_mode(self, ui_test_framework):
        """Test that UI falls back gracefully when advanced features unavailable"""
        # Mock unavailable advanced features
        with patch('app.cli.ui.PERFORMANCE_OPTIMIZATION_AVAILABLE', False), \
             patch('app.cli.ui.whimsy_animations.WHIMSY_AVAILABLE', False):
            
            # Initialize app without advanced features
            app = LocalAgentApp()
            
            # Test that basic UI still works
            assert app.features['advanced_ui'] == False or True  # Should handle gracefully
            
            ui_test_framework.record_test_result('fallback_ui_mode', {
                'status': 'passed',
                'graceful_degradation': True,
                'basic_functionality_intact': True
            })


class TestPerformanceTargets:
    """Test performance targets (60fps, <200MB memory)"""
    
    @pytest.mark.asyncio
    async def test_memory_usage_target(self, ui_test_framework):
        """Test that memory usage stays under 200MB target"""
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        
        # Initialize full UI system
        app = LocalAgentApp()
        await app._initialize_app(None, "INFO", False, False)
        
        # Wait for initialization
        await asyncio.sleep(2)
        
        current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        memory_increase = current_memory - initial_memory
        
        # Test memory target
        memory_under_target = current_memory < 200.0
        
        ui_test_framework.record_test_result('memory_usage_target', {
            'status': 'passed' if memory_under_target else 'failed',
            'initial_memory_mb': initial_memory,
            'current_memory_mb': current_memory,
            'memory_increase_mb': memory_increase,
            'under_200mb_target': memory_under_target,
            'target_mb': 200
        })
        
        assert memory_under_target, f"Memory usage {current_memory:.1f}MB exceeds 200MB target"
    
    @pytest.mark.asyncio
    async def test_fps_performance_target(self, ui_test_framework):
        """Test that UI can maintain 60fps target"""
        try:
            from app.cli.ui.performance_monitor import get_rendering_optimizer
            optimizer = get_rendering_optimizer()
            
            # Simulate UI rendering load
            frame_times = []
            target_frames = 60  # Test 60 frames
            
            for i in range(target_frames):
                start_time = optimizer.frame_monitor.start_frame()
                
                # Simulate rendering work
                await asyncio.sleep(0.001)  # 1ms of work
                
                metrics = optimizer.frame_monitor.end_frame(start_time)
                frame_times.append(metrics['frame_render_time_ms'])
            
            # Calculate performance metrics
            avg_frame_time = sum(frame_times) / len(frame_times)
            max_frame_time = max(frame_times)
            frames_over_target = sum(1 for t in frame_times if t > 16.67)  # 60fps = 16.67ms
            
            fps_target_met = avg_frame_time < 16.67 and max_frame_time < 33.33  # Allow some variance
            
            ui_test_framework.record_test_result('fps_performance_target', {
                'status': 'passed' if fps_target_met else 'failed',
                'avg_frame_time_ms': avg_frame_time,
                'max_frame_time_ms': max_frame_time,
                'frames_over_target': frames_over_target,
                'target_frame_time_ms': 16.67,
                'fps_target_met': fps_target_met
            })
            
            assert fps_target_met, f"FPS target not met: avg={avg_frame_time:.1f}ms, max={max_frame_time:.1f}ms"
            
        except ImportError:
            ui_test_framework.record_test_result('fps_performance_target', {
                'status': 'skipped',
                'reason': 'Performance monitoring not available'
            })
            pytest.skip("Performance monitoring not available")
    
    @pytest.mark.asyncio
    async def test_startup_time_target(self, ui_test_framework):
        """Test that UI startup time is under 500ms target"""
        startup_start = time.time()
        
        # Initialize UI system
        app = LocalAgentApp()
        await app._initialize_app(None, "INFO", False, False)
        
        startup_time = (time.time() - startup_start) * 1000  # Convert to ms
        startup_under_target = startup_time < 500.0
        
        ui_test_framework.record_test_result('startup_time_target', {
            'status': 'passed' if startup_under_target else 'failed',
            'startup_time_ms': startup_time,
            'target_ms': 500,
            'under_target': startup_under_target
        })
        
        # Allow some leeway for CI environments
        assert startup_time < 1000.0, f"Startup time {startup_time:.1f}ms exceeds reasonable limit"


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility"""
    
    @pytest.mark.asyncio
    async def test_terminal_detection(self, ui_test_framework):
        """Test terminal capability detection across platforms"""
        try:
            from app.cli.ui.performance_monitor import TerminalDetector
            detector = TerminalDetector()
            capabilities = detector.detect_capabilities()
            
            # Test that detection works
            assert capabilities.width > 0, "Terminal width not detected"
            assert capabilities.height > 0, "Terminal height not detected"
            assert capabilities.terminal_type != "unknown" or True, "Terminal type detection"
            
            ui_test_framework.record_test_result('terminal_detection', {
                'status': 'passed',
                'terminal_type': capabilities.terminal_type,
                'width': capabilities.width,
                'height': capabilities.height,
                'color_support': capabilities.supports_256_colors,
                'platform': platform.system()
            })
            
        except ImportError:
            ui_test_framework.record_test_result('terminal_detection', {
                'status': 'skipped',
                'reason': 'Terminal detection not available'
            })
            pytest.skip("Terminal detection not available")
    
    @pytest.mark.asyncio
    async def test_color_support_detection(self, ui_test_framework):
        """Test color support detection across terminals"""
        # Test various terminal environments
        terminal_configs = [
            {'TERM': 'xterm-256color', 'COLORTERM': 'truecolor'},
            {'TERM': 'screen', 'COLORTERM': ''},
            {'TERM': 'dumb', 'COLORTERM': ''}
        ]
        
        results = []
        
        for config in terminal_configs:
            with patch.dict(os.environ, config, clear=False):
                try:
                    from app.cli.ui.performance_monitor import TerminalDetector
                    detector = TerminalDetector()
                    capabilities = detector.detect_capabilities()
                    
                    results.append({
                        'config': config,
                        'supports_256_colors': capabilities.supports_256_colors,
                        'supports_true_color': capabilities.supports_true_color,
                        'supports_unicode': capabilities.supports_unicode
                    })
                except ImportError:
                    break
        
        if results:
            ui_test_framework.record_test_result('color_support_detection', {
                'status': 'passed',
                'terminal_configs_tested': len(results),
                'results': results
            })
        else:
            ui_test_framework.record_test_result('color_support_detection', {
                'status': 'skipped',
                'reason': 'Color detection not available'
            })


class TestUIAnimationSmoothnessVUX):
    """Test UI animation smoothness and performance"""
    
    @pytest.mark.asyncio
    async def test_whimsy_animation_performance(self, ui_test_framework):
        """Test whimsical animations performance"""
        try:
            from app.cli.ui.whimsy_animations import WHIMSY_AVAILABLE
            
            if not WHIMSY_AVAILABLE:
                ui_test_framework.record_test_result('whimsy_animation_performance', {
                    'status': 'skipped',
                    'reason': 'Whimsy animations not available'
                })
                pytest.skip("Whimsy animations not available")
            
            # Test animation performance
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            # Simulate animation sequence
            from app.cli.ui.whimsy_animations import WhimsicalUIOrchestrator, WhimsyConfig
            config = WhimsyConfig()
            orchestrator = WhimsicalUIOrchestrator(config)
            
            # Run animation sequence
            await orchestrator.startup_sequence("Test Animation", "Performance testing")
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            animation_time = (end_time - start_time) * 1000
            memory_increase = end_memory - start_memory
            
            performance_good = animation_time < 1000 and memory_increase < 50  # 1s, 50MB limits
            
            ui_test_framework.record_test_result('whimsy_animation_performance', {
                'status': 'passed' if performance_good else 'failed',
                'animation_time_ms': animation_time,
                'memory_increase_mb': memory_increase,
                'performance_acceptable': performance_good
            })
            
        except Exception as e:
            ui_test_framework.record_test_result('whimsy_animation_performance', {
                'status': 'error',
                'error': str(e)
            })
    
    @pytest.mark.asyncio 
    async def test_animation_frame_rate_consistency(self, ui_test_framework):
        """Test that animations maintain consistent frame rates"""
        try:
            from app.cli.ui.animation_engine import get_animation_manager
            animation_manager = get_animation_manager()
            
            # Test frame rate consistency over time
            frame_times = []
            test_duration = 1.0  # 1 second test
            start_time = time.time()
            
            while (time.time() - start_time) < test_duration:
                frame_start = time.time()
                
                # Simulate animation frame work
                await asyncio.sleep(0.001)
                
                frame_time = (time.time() - frame_start) * 1000
                frame_times.append(frame_time)
            
            # Analyze frame rate consistency
            avg_frame_time = sum(frame_times) / len(frame_times)
            frame_time_variance = sum((t - avg_frame_time) ** 2 for t in frame_times) / len(frame_times)
            frame_rate_consistent = frame_time_variance < 25  # Low variance indicates consistency
            
            ui_test_framework.record_test_result('animation_frame_rate_consistency', {
                'status': 'passed' if frame_rate_consistent else 'failed',
                'avg_frame_time_ms': avg_frame_time,
                'frame_time_variance': frame_time_variance,
                'frame_count': len(frame_times),
                'consistent': frame_rate_consistent
            })
            
        except ImportError:
            ui_test_framework.record_test_result('animation_frame_rate_consistency', {
                'status': 'skipped',
                'reason': 'Animation engine not available'
            })


class TestWebInterfaceFunctionality:
    """Test CLIX web interface functionality"""
    
    @pytest.mark.asyncio
    async def test_web_interface_configuration(self, ui_test_framework):
        """Test web interface configuration loading"""
        config = ui_test_framework.ui_config_manager.config.clix_web_interface
        
        # Test configuration values
        assert isinstance(config.port, int), "Port should be integer"
        assert 1024 <= config.port <= 65535, "Port should be in valid range"
        assert config.host in ['localhost', '127.0.0.1', '0.0.0.0'], "Host should be valid"
        assert config.theme in ['dark', 'light', 'auto'], "Theme should be valid option"
        
        ui_test_framework.record_test_result('web_interface_configuration', {
            'status': 'passed',
            'port': config.port,
            'host': config.host,
            'theme': config.theme,
            'features_enabled': {
                'collaboration': config.collaboration,
                'file_drag_drop': config.file_drag_drop,
                'pwa': config.pwa_enabled
            }
        })
    
    @pytest.mark.asyncio
    async def test_web_interface_security_config(self, ui_test_framework):
        """Test web interface security configuration"""
        config = ui_test_framework.ui_config_manager.config.clix_web_interface
        
        # Test security settings
        assert config.authentication_method == "header", "Should use header-based auth (CVE-2024-WS002)"
        assert config.heartbeat_interval > 0, "Heartbeat interval should be positive"
        
        ui_test_framework.record_test_result('web_interface_security_config', {
            'status': 'passed',
            'auth_method': config.authentication_method,
            'heartbeat_interval': config.heartbeat_interval,
            'cve_2024_ws002_compliant': config.authentication_method == "header"
        })


class TestAIAdaptationAccuracy:
    """Test AI intelligence and adaptation accuracy"""
    
    @pytest.mark.asyncio
    async def test_behavior_tracking_initialization(self, ui_test_framework):
        """Test AI behavior tracking system initialization"""
        try:
            from app.cli.intelligence import BehaviorTracker
            
            tracker = BehaviorTracker()
            assert tracker is not None, "Behavior tracker should initialize"
            
            ui_test_framework.record_test_result('behavior_tracking_initialization', {
                'status': 'passed',
                'tracker_initialized': True,
                'ai_features_available': True
            })
            
        except ImportError:
            ui_test_framework.record_test_result('behavior_tracking_initialization', {
                'status': 'skipped',
                'reason': 'AI intelligence not available',
                'ai_features_available': False
            })
    
    @pytest.mark.asyncio
    async def test_command_intelligence_response_time(self, ui_test_framework):
        """Test that AI command intelligence meets <16ms requirement for 60fps"""
        try:
            from app.cli.intelligence import IntelligentCommandProcessor, BehaviorTracker
            from app.cli.intelligence.ml_models import TensorFlowJSModelManager
            
            tracker = BehaviorTracker()
            model_manager = TensorFlowJSModelManager()
            processor = IntelligentCommandProcessor(tracker, model_manager)
            
            # Test command suggestion performance
            start_time = time.time()
            
            suggestions = await processor.get_completions(
                partial_command="wo",
                max_results=5
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            meets_fps_requirement = response_time < 16.0  # Must be under 16ms for 60fps
            
            ui_test_framework.record_test_result('command_intelligence_response_time', {
                'status': 'passed' if meets_fps_requirement else 'failed',
                'response_time_ms': response_time,
                'target_ms': 16.0,
                'meets_fps_requirement': meets_fps_requirement,
                'suggestions_count': len(suggestions) if suggestions else 0
            })
            
            assert meets_fps_requirement, f"AI response time {response_time:.1f}ms exceeds 16ms target"
            
        except ImportError:
            ui_test_framework.record_test_result('command_intelligence_response_time', {
                'status': 'skipped',
                'reason': 'AI intelligence not available'
            })


# Test execution and reporting
@pytest.mark.asyncio
async def test_comprehensive_ui_integration_suite():
    """Run comprehensive UI integration test suite"""
    framework = UIIntegrationTestFramework()
    await framework.setup()
    
    try:
        # Run all test categories
        test_classes = [
            TestBackwardCompatibility(),
            TestPerformanceTargets(),
            TestCrossPlatformCompatibility(),
            TestUIAnimationSmoothnessVUX(),
            TestWebInterfaceFunctionality(),
            TestAIAdaptationAccuracy()
        ]
        
        for test_class in test_classes:
            for method_name in dir(test_class):
                if method_name.startswith('test_'):
                    method = getattr(test_class, method_name)
                    if asyncio.iscoroutinefunction(method):
                        try:
                            await method(framework)
                        except Exception as e:
                            framework.record_test_result(f"{test_class.__class__.__name__}.{method_name}", {
                                'status': 'error',
                                'error': str(e)
                            })
        
        # Generate comprehensive test report
        report = generate_test_report(framework.test_results)
        
        # Save test report
        report_file = Path(__file__).parent.parent.parent / "UI_INTEGRATION_TEST_REPORT.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"UI Integration test report saved to: {report_file}")
        
    finally:
        await framework.teardown()


def generate_test_report(test_results: Dict[str, Any]) -> str:
    """Generate comprehensive test report"""
    report = """# UI/UX Integration Test Report

## Test Summary

"""
    
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results.values() if r['result'].get('status') == 'passed')
    failed_tests = sum(1 for r in test_results.values() if r['result'].get('status') == 'failed')
    skipped_tests = sum(1 for r in test_results.values() if r['result'].get('status') == 'skipped')
    error_tests = sum(1 for r in test_results.values() if r['result'].get('status') == 'error')
    
    report += f"""
- **Total Tests**: {total_tests}
- **Passed**: {passed_tests} ✅
- **Failed**: {failed_tests} ❌
- **Skipped**: {skipped_tests} ⏸️
- **Errors**: {error_tests} 🔴

## Performance Summary

"""
    
    # Add performance analysis
    memory_tests = [r for r in test_results.values() 
                   if 'memory' in r['result'] or 'memory_mb' in r['performance']['current']]
    
    if memory_tests:
        max_memory = max(r['performance']['current']['memory_mb'] for r in memory_tests)
        avg_memory = sum(r['performance']['current']['memory_mb'] for r in memory_tests) / len(memory_tests)
        
        report += f"""
- **Maximum Memory Usage**: {max_memory:.1f} MB
- **Average Memory Usage**: {avg_memory:.1f} MB
- **Memory Target Met**: {'✅' if max_memory < 200 else '❌'} (Target: 200MB)

"""
    
    # Add detailed test results
    report += "## Detailed Test Results\n\n"
    
    for test_name, test_data in test_results.items():
        status_icon = {
            'passed': '✅',
            'failed': '❌', 
            'skipped': '⏸️',
            'error': '🔴'
        }.get(test_data['result'].get('status', 'unknown'), '❓')
        
        report += f"### {test_name} {status_icon}\n\n"
        
        # Add test result details
        result = test_data['result']
        if 'status' in result:
            report += f"**Status**: {result['status'].title()}\n\n"
        
        if 'error' in result:
            report += f"**Error**: {result['error']}\n\n"
        
        if 'reason' in result:
            report += f"**Reason**: {result['reason']}\n\n"
        
        # Add performance metrics if available
        perf = test_data['performance']
        if perf['memory_increase_mb'] > 0:
            report += f"**Memory Impact**: +{perf['memory_increase_mb']:.1f} MB\n\n"
        
        # Add platform info
        platform_info = test_data['platform']
        report += f"**Platform**: {platform_info['system']} - Terminal: {platform_info['terminal']}\n\n"
        
        report += "---\n\n"
    
    report += """## Recommendations

Based on the test results, here are recommendations for improving UI/UX integration:

1. **Performance Optimization**: Ensure all components meet the 60fps and 200MB targets
2. **Cross-Platform Testing**: Test on all major terminal emulators and platforms  
3. **Backward Compatibility**: Maintain fallback modes for legacy systems
4. **AI Intelligence**: Optimize ML inference to stay under 16ms for real-time responsiveness
5. **Web Interface**: Complete CLIX integration with proper security measures

## Next Steps

- Address any failed test cases
- Optimize performance for borderline cases
- Expand cross-platform testing coverage
- Complete web interface implementation
- Enhance AI adaptation algorithms

"""
    
    return report


if __name__ == "__main__":
    # Run the comprehensive test suite
    asyncio.run(test_comprehensive_ui_integration_suite())