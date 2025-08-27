"""
CLI Integration Validation Tests
Final validation tests to ensure all CLI components work together seamlessly
"""

import asyncio
import pytest
import tempfile
import sys
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

# Import all CLI components for validation
from app.cli.core.app import LocalAgentApp, create_app
from app.cli.core.config import ConfigurationManager, LocalAgentConfig
from app.cli.core.context import CLIContext
from app.cli.core.enhanced_command_registration import (
    EnhancedCommandRegistry, 
    EnhancedCommandBuilder,
    create_enhanced_registry,
    enhanced_command,
    workflow_command,
    agent_command,
    provider_command,
    CommandPriority,
    CommandScope
)
from app.cli.plugins.framework import PluginManager
from app.cli.plugins.builtin.builtin_plugins import (
    SystemInfoPlugin,
    WorkflowDebugPlugin,
    ConfigurationPlugin,
    get_builtin_plugins
)
from app.cli.integration.enhanced_orchestration_bridge import (
    EnhancedOrchestrationBridge,
    WorkflowPhase,
    WorkflowStatus,
    create_enhanced_orchestrator_for_cli
)
from app.cli.integration.enhanced_provider_integration import (
    EnhancedProviderIntegration,
    ProviderDisplayManager,
    create_provider_integration
)
from app.cli.ui.display import create_display_manager

class TestSystemIntegration:
    """Test system-wide integration of all CLI components"""
    
    @pytest.fixture
    async def temp_config(self):
        """Create temporary configuration for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".localagent"
            config_dir.mkdir(parents=True)
            
            config_data = {
                'config_dir': config_dir,
                'log_level': 'INFO',
                'debug_mode': False,
                'providers': {
                    'ollama': {
                        'base_url': 'http://localhost:11434',
                        'enabled': True
                    }
                },
                'default_provider': 'ollama',
                'orchestration': {
                    'max_parallel_agents': 10,
                    'max_workflow_iterations': 3,
                    'enable_evidence_collection': True
                },
                'plugins': {
                    'enabled_plugins': ['system-info', 'config-manager'],
                    'auto_load_plugins': True,
                    'plugin_directories': [str(config_dir / 'plugins')],
                    'allow_dev_plugins': True
                }
            }
            
            yield LocalAgentConfig(**config_data)
    
    @pytest.mark.asyncio
    async def test_complete_cli_initialization(self, temp_config):
        """Test complete CLI application initialization"""
        # Create CLI context
        context = CLIContext(
            config=temp_config,
            debug_mode=True,
            log_level='DEBUG'
        )
        
        # Create display manager
        console = Mock()
        display_manager = create_display_manager(console, debug=True)
        
        # Test component initialization
        assert context is not None
        assert context.config == temp_config
        assert display_manager is not None
    
    @pytest.mark.asyncio
    async def test_plugin_system_integration(self, temp_config):
        """Test complete plugin system integration"""
        context = CLIContext(config=temp_config, debug_mode=True)
        plugin_manager = PluginManager(context)
        
        # Test plugin discovery
        await plugin_manager.discover_plugins()
        
        # Should discover built-in plugins
        builtin_plugins = get_builtin_plugins()
        assert len(builtin_plugins) > 0
        
        # Test built-in plugin types
        plugin_types = [plugin.__name__ for plugin in builtin_plugins]
        assert 'SystemInfoPlugin' in plugin_types
        assert 'ConfigurationPlugin' in plugin_types
        assert 'WorkflowDebugPlugin' in plugin_types
    
    @pytest.mark.asyncio
    async def test_command_registry_full_integration(self):
        """Test complete command registry integration"""
        registry = create_enhanced_registry()
        builder = EnhancedCommandBuilder(registry)
        
        # Test enhanced command decorators
        @enhanced_command(
            name="test-enhanced",
            group="testing",
            priority=CommandPriority.USER,
            scope=CommandScope.GLOBAL,
            aliases=["te", "test"],
            tags={"test", "validation"}
        )
        async def test_enhanced_command():
            return "Enhanced command executed"
        
        @workflow_command(name="test-workflow", phase="0")
        async def test_workflow_command():
            return "Workflow command executed"
        
        @agent_command(name="test-agent", agent_type="test")
        async def test_agent_command():
            return "Agent command executed"
        
        @provider_command(name="test-provider", provider="test")
        async def test_provider_command():
            return "Provider command executed"
        
        # Register commands
        registry.register_command("test-enhanced", test_enhanced_command, 
                                 group="testing", aliases=["te", "test"])
        registry.register_command("test-workflow", test_workflow_command, 
                                 group="workflow", command_type="workflow")
        registry.register_command("test-agent", test_agent_command, 
                                 group="agents", command_type="agent")
        registry.register_command("test-provider", test_provider_command, 
                                 group="providers", command_type="provider")
        
        # Test command execution
        result1 = await registry.execute_command("test-enhanced")
        result2 = await registry.execute_command("te")  # Test alias
        result3 = await registry.execute_command("test-workflow")
        
        assert result1 == "Enhanced command executed"
        assert result2 == "Enhanced command executed"  # Alias should work
        assert result3 == "Workflow command executed"
        
        # Test manifest generation
        manifest = registry.generate_command_manifest()
        assert manifest['metadata']['total_commands'] >= 4
        assert 'testing' in manifest['groups']
        assert 'workflow' in manifest['groups']
        
        # Test Typer app building
        app = builder.build_main_app_with_groups()
        assert app is not None
    
    @pytest.mark.asyncio
    async def test_orchestration_bridge_integration(self, temp_config):
        """Test orchestration bridge integration"""
        context = CLIContext(config=temp_config, debug_mode=True)
        console = Mock()
        display_manager = create_display_manager(console, debug=True)
        
        # Create orchestration bridge
        bridge = EnhancedOrchestrationBridge(context, display_manager)
        
        # Test initialization (would normally initialize real orchestrator)
        with patch('app.orchestration.orchestration_integration.LocalAgentOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.initialized = True
            mock_orchestrator_class.return_value = mock_orchestrator
            
            success = await bridge.initialize_orchestrator()
            assert success
            assert bridge.orchestrator is not None
        
        # Test workflow status
        status = await bridge.get_workflow_status()
        assert 'status' in status
        
        # Test system health
        health = await bridge.get_system_health()
        assert 'orchestrator_initialized' in health
    
    @pytest.mark.asyncio
    async def test_provider_integration_flow(self, temp_config):
        """Test provider integration complete flow"""
        context = CLIContext(config=temp_config, debug_mode=True)
        console = Mock()
        display_manager = create_display_manager(console, debug=True)
        
        # Create provider integration
        integration = EnhancedProviderIntegration(context, display_manager)
        
        # Test configuration extraction
        provider_config = integration._extract_provider_config()
        assert isinstance(provider_config, dict)
        assert 'ollama' in provider_config
        
        # Test provider display manager
        provider_display = ProviderDisplayManager(console)
        assert provider_display is not None
        
        # Test mock provider info display
        mock_provider_info = {
            'total_providers': 1,
            'active_providers': 1,
            'providers': {
                'ollama': {
                    'name': 'ollama',
                    'healthy': True,
                    'models': ['llama2', 'codellama'],
                    'performance': {
                        'avg_response_time': 1.5,
                        'uptime_percentage': 98.5
                    },
                    'configuration': {
                        'provider_type': 'Ollama Local',
                        'local': True
                    }
                }
            }
        }
        
        # This would normally display the table, but we just test it doesn't crash
        provider_display.display_provider_list(mock_provider_info)
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_simulation(self, temp_config):
        """Test end-to-end workflow simulation"""
        # Create all major components
        context = CLIContext(config=temp_config, debug_mode=True)
        console = Mock()
        display_manager = create_display_manager(console, debug=True)
        
        # Initialize components
        registry = create_enhanced_registry()
        plugin_manager = PluginManager(context)
        
        # Simulate plugin discovery and loading
        await plugin_manager.discover_plugins()
        
        # Register some test commands
        @enhanced_command(name="simulate-workflow")
        async def simulate_workflow():
            return {
                'status': 'completed',
                'phases': 10,
                'agents': 5,
                'evidence': ['test1', 'test2']
            }
        
        registry.register_command("simulate-workflow", simulate_workflow,
                                 group="simulation", command_type="workflow")
        
        # Execute workflow simulation
        result = await registry.execute_command("simulate-workflow")
        assert result['status'] == 'completed'
        assert result['phases'] == 10
        
        # Test performance metrics
        cmd_meta = registry.commands["simulate-workflow"]
        assert cmd_meta.call_count == 1
        assert cmd_meta.total_execution_time > 0
        
        # Generate performance report
        perf_report = registry.get_performance_report()
        assert perf_report['overview']['total_calls'] >= 1
        assert len(perf_report['top_commands_by_usage']) >= 1

class TestErrorHandlingAndRobustness:
    """Test error handling and system robustness"""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation when components fail"""
        registry = EnhancedCommandRegistry()
        
        # Test command that fails
        def failing_command():
            raise RuntimeError("Simulated failure")
        
        registry.register_command("failing", failing_command)
        
        # Should handle error gracefully
        with pytest.raises(RuntimeError):
            await registry.execute_command("failing")
        
        # Registry should still be functional
        assert len(registry.commands) == 1
        assert registry.registry_stats['error_count'] == 1
    
    @pytest.mark.asyncio
    async def test_invalid_configurations(self):
        """Test handling of invalid configurations"""
        # Test with minimal config
        minimal_config = LocalAgentConfig(
            config_dir=Path("/tmp"),
            providers={},
            default_provider="nonexistent"
        )
        
        context = CLIContext(config=minimal_config)
        
        # Should not crash with invalid config
        assert context.config is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent operations don't interfere"""
        registry = EnhancedCommandRegistry()
        
        async def async_command(delay: float = 0.01):
            await asyncio.sleep(delay)
            return f"Completed with delay {delay}"
        
        registry.register_command("async-cmd", async_command)
        
        # Run multiple commands concurrently
        tasks = []
        for i in range(5):
            task = registry.execute_command("async-cmd", delay=0.01 * i)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should complete
        assert len(results) == 5
        
        # Metrics should be correct
        cmd_meta = registry.commands["async-cmd"]
        assert cmd_meta.call_count == 5

class TestPerformanceValidation:
    """Test performance characteristics of the CLI system"""
    
    @pytest.mark.asyncio
    async def test_command_registration_performance(self):
        """Test performance of command registration"""
        registry = EnhancedCommandRegistry()
        
        import time
        
        # Register many commands
        start_time = time.time()
        
        for i in range(1000):
            def make_cmd(index):
                return lambda: f"Command {index}"
            
            registry.register_command(
                name=f"perf-cmd-{i}",
                function=make_cmd(i),
                group=f"perf-group-{i // 100}"
            )
        
        registration_time = time.time() - start_time
        
        # Should register 1000 commands quickly (< 1 second)
        assert registration_time < 1.0
        assert len(registry.commands) == 1000
        
        # Test command resolution performance
        start_time = time.time()
        
        for i in range(100):
            cmd = registry.resolve_command(f"perf-cmd-{i}")
            assert cmd is not None
        
        resolution_time = time.time() - start_time
        
        # Should resolve quickly
        assert resolution_time < 0.1
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage characteristics"""
        import gc
        
        registry = EnhancedCommandRegistry()
        
        # Create and register many commands
        for i in range(100):
            def make_cmd(index):
                return lambda: f"Memory test {index}"
            
            registry.register_command(f"mem-cmd-{i}", make_cmd(i))
        
        # Force garbage collection
        gc.collect()
        
        # Test cleanup
        registry.cleanup()
        
        # Should cleanup properly
        assert len(registry._command_cache) == 0
        assert len(registry._resolution_cache) == 0

class TestDocumentationAndExamples:
    """Test that documentation examples work correctly"""
    
    @pytest.mark.asyncio
    async def test_readme_examples(self):
        """Test examples that would be in README"""
        registry = EnhancedCommandRegistry()
        
        # Example 1: Simple command registration
        def hello_world():
            return "Hello, World!"
        
        registry.register_command("hello", hello_world, help_text="Say hello")
        result = await registry.execute_command("hello")
        assert result == "Hello, World!"
        
        # Example 2: Command with parameters
        def greet_user(name: str = "Anonymous"):
            return f"Hello, {name}!"
        
        registry.register_command("greet", greet_user, help_text="Greet a user")
        result = await registry.execute_command("greet", "Alice")
        assert result == "Hello, Alice!"
        
        # Example 3: Using decorators
        @enhanced_command(name="decorated", aliases=["dec"])
        def decorated_command():
            return "Decorated command result"
        
        registry.register_command("decorated", decorated_command, aliases=["dec"])
        result1 = await registry.execute_command("decorated")
        result2 = await registry.execute_command("dec")
        
        assert result1 == "Decorated command result"
        assert result2 == "Decorated command result"

if __name__ == "__main__":
    # Run all validation tests
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=5"])