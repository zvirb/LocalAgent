"""
Comprehensive CLI Integration Tests
Tests for the complete CLI system including plugins, providers, and orchestration
"""

import asyncio
import pytest
import tempfile
import json
import yaml
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

# Import CLI components
from app.cli.core.app import LocalAgentApp
from app.cli.core.config import ConfigurationManager, LocalAgentConfig
from app.cli.core.context import CLIContext
from app.cli.core.enhanced_command_registration import (
    EnhancedCommandRegistry, 
    EnhancedCommandBuilder,
    CommandPriority,
    CommandScope
)
from app.cli.plugins.framework import PluginManager, CLIPlugin
from app.cli.integration.enhanced_orchestration_bridge import EnhancedOrchestrationBridge
from app.cli.integration.enhanced_provider_integration import EnhancedProviderIntegration
from app.cli.ui.display import create_display_manager

class TestCLIPlugin(CLIPlugin):
    """Test plugin for integration testing"""
    
    @property
    def name(self) -> str:
        return "test-plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Test plugin for CLI integration testing"
    
    async def initialize(self, context) -> bool:
        return True
    
    def register_commands(self, app):
        @app.command("test")
        def test_command():
            return "Test command executed"

@pytest.fixture
async def temp_config_dir():
    """Create a temporary configuration directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".localagent"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield config_dir

@pytest.fixture
async def test_config(temp_config_dir):
    """Create test configuration"""
    config_data = {
        'config_dir': temp_config_dir,
        'log_level': 'DEBUG',
        'debug_mode': True,
        'providers': {
            'mock_provider': {
                'base_url': 'http://localhost:11434',
                'enabled': True
            }
        },
        'default_provider': 'mock_provider',
        'orchestration': {
            'max_parallel_agents': 5,
            'max_workflow_iterations': 2,
            'enable_evidence_collection': True
        },
        'plugins': {
            'enabled_plugins': ['test-plugin'],
            'auto_load_plugins': True,
            'plugin_directories': [str(temp_config_dir / 'plugins')],
            'allow_dev_plugins': True
        }
    }
    
    config_file = temp_config_dir / 'config.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)
    
    return LocalAgentConfig(**config_data)

@pytest.fixture
def mock_display_manager():
    """Create mock display manager"""
    return Mock()

@pytest.fixture
async def cli_context(test_config, mock_display_manager):
    """Create CLI context for testing"""
    return CLIContext(
        config=test_config,
        debug_mode=True,
        log_level='DEBUG'
    )

class TestEnhancedCommandRegistration:
    """Test the enhanced command registration system"""
    
    @pytest.mark.asyncio
    async def test_command_registry_creation(self):
        """Test creation of enhanced command registry"""
        registry = EnhancedCommandRegistry()
        
        assert registry is not None
        assert len(registry.commands) == 0
        assert len(registry.groups) == 0
        assert len(registry.aliases) == 0
    
    @pytest.mark.asyncio
    async def test_command_registration(self):
        """Test registering commands with enhanced metadata"""
        registry = EnhancedCommandRegistry()
        
        def test_cmd():
            return "test result"
        
        success = registry.register_command(
            name="test-cmd",
            function=test_cmd,
            group="test",
            help_text="Test command",
            priority=CommandPriority.USER,
            scope=CommandScope.GLOBAL,
            aliases=["tc"],
            tags={"test", "demo"}
        )
        
        assert success
        assert "test-cmd" in registry.commands
        assert "tc" in registry.aliases
        assert registry.aliases["tc"] == "test-cmd"
        assert "test" in registry.groups
    
    @pytest.mark.asyncio
    async def test_command_resolution(self):
        """Test command name and alias resolution"""
        registry = EnhancedCommandRegistry()
        
        def test_cmd():
            return "test result"
        
        registry.register_command(
            name="test-cmd",
            function=test_cmd,
            aliases=["tc", "test"]
        )
        
        # Test direct name resolution
        cmd = registry.resolve_command("test-cmd")
        assert cmd is not None
        assert cmd.name == "test-cmd"
        
        # Test alias resolution
        cmd_alias = registry.resolve_command("tc")
        assert cmd_alias is not None
        assert cmd_alias.name == "test-cmd"
        
        # Test non-existent command
        cmd_none = registry.resolve_command("non-existent")
        assert cmd_none is None
    
    @pytest.mark.asyncio
    async def test_command_execution_with_monitoring(self):
        """Test command execution with performance monitoring"""
        registry = EnhancedCommandRegistry()
        
        def test_cmd(message: str = "hello"):
            return f"Response: {message}"
        
        registry.register_command(
            name="monitored-cmd",
            function=test_cmd,
            priority=CommandPriority.USER
        )
        
        # Execute command
        result = await registry.execute_command("monitored-cmd", "test message")
        
        assert result == "Response: test message"
        
        # Check metrics
        cmd_metadata = registry.commands["monitored-cmd"]
        assert cmd_metadata.call_count == 1
        assert cmd_metadata.total_execution_time > 0
        assert cmd_metadata.last_called is not None
    
    @pytest.mark.asyncio
    async def test_command_builder_integration(self):
        """Test integration with Typer command builder"""
        registry = EnhancedCommandRegistry()
        builder = EnhancedCommandBuilder(registry)
        
        def hello_cmd(name: str = "World"):
            return f"Hello, {name}!"
        
        registry.register_command(
            name="hello",
            function=hello_cmd,
            group="greetings",
            help_text="Say hello"
        )
        
        # Build Typer app
        app = builder.build_main_app_with_groups()
        
        assert app is not None
        # Note: More detailed Typer integration testing would require
        # actually invoking the CLI, which is complex in unit tests

class TestPluginSystem:
    """Test the plugin system integration"""
    
    @pytest.mark.asyncio
    async def test_plugin_manager_initialization(self, cli_context):
        """Test plugin manager initialization"""
        plugin_manager = PluginManager(cli_context)
        
        assert plugin_manager is not None
        assert plugin_manager.context == cli_context
        assert len(plugin_manager.discovered_plugins) == 0
        
    @pytest.mark.asyncio
    async def test_plugin_discovery(self, cli_context):
        """Test plugin discovery process"""
        plugin_manager = PluginManager(cli_context)
        
        # Mock the built-in plugins discovery
        with patch('app.cli.plugins.builtin.builtin_plugins.get_builtin_plugins') as mock_builtin:
            mock_builtin.return_value = [TestCLIPlugin]
            
            await plugin_manager.discover_plugins()
            
            # Should have discovered built-in plugins
            assert len(plugin_manager.discovered_plugins) > 0
    
    @pytest.mark.asyncio
    async def test_plugin_loading(self, cli_context):
        """Test plugin loading process"""
        plugin_manager = PluginManager(cli_context)
        
        # Register test plugin manually
        from app.cli.plugins.framework import PluginInfo
        plugin_info = PluginInfo(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            plugin_class=TestCLIPlugin,
            enabled=True
        )
        plugin_manager.discovered_plugins["test-plugin"] = plugin_info
        
        # Load the plugin
        success = await plugin_manager.load_plugin("test-plugin")
        
        assert success
        assert "test-plugin" in plugin_manager.loaded_plugins
        assert plugin_info.loaded

class TestProviderIntegration:
    """Test provider integration system"""
    
    @pytest.mark.asyncio
    async def test_provider_integration_initialization(self, cli_context, mock_display_manager):
        """Test provider integration initialization"""
        integration = EnhancedProviderIntegration(cli_context, mock_display_manager)
        
        assert integration is not None
        assert integration.context == cli_context
        assert integration.display_manager == mock_display_manager
        assert not integration.monitoring_active
    
    @pytest.mark.asyncio
    async def test_provider_config_extraction(self, cli_context, mock_display_manager):
        """Test provider configuration extraction"""
        integration = EnhancedProviderIntegration(cli_context, mock_display_manager)
        
        config = integration._extract_provider_config()
        
        assert isinstance(config, dict)
        assert 'mock_provider' in config
        assert config['mock_provider']['enabled'] is True
    
    @pytest.mark.asyncio
    async def test_provider_health_monitoring(self, cli_context, mock_display_manager):
        """Test provider health monitoring"""
        integration = EnhancedProviderIntegration(cli_context, mock_display_manager)
        
        # Mock a provider for testing
        mock_provider = AsyncMock()
        mock_provider.health_check.return_value = {'healthy': True, 'response_time': 0.1}
        
        integration.provider_status['test_provider'] = Mock()
        integration.provider_status['test_provider'].provider = mock_provider
        integration.provider_status['test_provider'].health_status = {}
        integration.provider_status['test_provider'].performance_metrics = {
            'uptime_percentage': 100.0
        }
        integration.provider_status['test_provider'].recent_errors = []
        
        await integration._update_provider_status('test_provider')
        
        # Verify health check was called
        mock_provider.health_check.assert_called_once()

class TestOrchestrationBridge:
    """Test orchestration bridge integration"""
    
    @pytest.mark.asyncio
    async def test_orchestration_bridge_initialization(self, cli_context, mock_display_manager):
        """Test orchestration bridge initialization"""
        bridge = EnhancedOrchestrationBridge(cli_context, mock_display_manager)
        
        assert bridge is not None
        assert bridge.context == cli_context
        assert bridge.display_manager == mock_display_manager
        assert bridge.current_workflow is None
        assert not bridge.monitoring_active
    
    @pytest.mark.asyncio
    async def test_workflow_execution_tracking(self, cli_context, mock_display_manager):
        """Test workflow execution tracking"""
        bridge = EnhancedOrchestrationBridge(cli_context, mock_display_manager)
        
        # Mock the orchestrator
        mock_orchestrator = AsyncMock()
        bridge.orchestrator = mock_orchestrator
        
        # Start a workflow execution (without actually executing)
        workflow_id = "test-workflow-123"
        prompt = "Test workflow prompt"
        execution_context = {"test": True}
        
        # This would normally start a full workflow execution
        # For testing, we just verify the setup
        from app.cli.integration.enhanced_orchestration_bridge import WorkflowExecution
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            prompt=prompt,
            execution_context=execution_context
        )
        
        assert workflow.workflow_id == workflow_id
        assert workflow.prompt == prompt
        assert workflow.execution_context == execution_context
        assert len(workflow.phase_progress) == 10  # 10 phases (0-9)

class TestFullCLIIntegration:
    """Test full CLI system integration"""
    
    @pytest.mark.asyncio
    async def test_cli_app_initialization(self, temp_config_dir):
        """Test full CLI application initialization"""
        # Create a configuration file
        config_data = {
            'config_dir': str(temp_config_dir),
            'providers': {
                'test_provider': {
                    'enabled': True
                }
            },
            'plugins': {
                'enabled_plugins': [],
                'auto_load_plugins': False
            }
        }
        
        config_file = temp_config_dir / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Initialize CLI app
        app = LocalAgentApp()
        
        # Test that app was created
        assert app is not None
        assert app.app is not None
        assert not app.initialized
    
    @pytest.mark.asyncio
    async def test_configuration_management_flow(self, temp_config_dir):
        """Test complete configuration management flow"""
        config_manager = ConfigurationManager(str(temp_config_dir / 'config.yaml'))
        
        # Test loading non-existent config (should use defaults)
        config = await config_manager.load_configuration()
        
        assert config is not None
        assert config.config_dir is not None
        
        # Test saving configuration
        await config_manager.save_configuration(config)
        
        # Test loading saved configuration
        config2 = await config_manager.load_configuration()
        
        assert config2 is not None
        assert config2.config_dir == config.config_dir
    
    @pytest.mark.asyncio
    async def test_command_registration_and_execution_flow(self):
        """Test complete command registration and execution flow"""
        registry = EnhancedCommandRegistry()
        
        # Register multiple commands with different priorities
        def system_cmd():
            return "system command"
        
        def user_cmd():
            return "user command"
        
        def debug_cmd():
            return "debug command"
        
        registry.register_command(
            "system", system_cmd, priority=CommandPriority.SYSTEM
        )
        registry.register_command(
            "user", user_cmd, priority=CommandPriority.USER
        )
        registry.register_command(
            "debug", debug_cmd, priority=CommandPriority.USER, scope=CommandScope.DEBUG
        )
        
        # Test command manifest generation
        manifest = registry.generate_command_manifest()
        
        assert manifest['metadata']['total_commands'] == 3
        assert len(manifest['commands']) == 3
        
        # Test performance report
        perf_report = registry.get_performance_report()
        assert 'overview' in perf_report
        assert 'top_commands_by_usage' in perf_report
        
        # Execute commands and verify tracking
        result1 = await registry.execute_command("system")
        result2 = await registry.execute_command("user")
        
        assert result1 == "system command"
        assert result2 == "user command"
        
        # Verify metrics were updated
        system_cmd_meta = registry.commands["system"]
        assert system_cmd_meta.call_count == 1
        
    @pytest.mark.asyncio
    async def test_plugin_and_command_integration(self, cli_context):
        """Test integration between plugin system and command registration"""
        plugin_manager = PluginManager(cli_context)
        registry = EnhancedCommandRegistry()
        
        # Create and register test plugin
        plugin_info = PluginInfo(
            name="integration-test",
            version="1.0.0", 
            description="Integration test plugin",
            plugin_class=TestCLIPlugin,
            enabled=True
        )
        plugin_manager.discovered_plugins["integration-test"] = plugin_info
        
        # Load plugin
        success = await plugin_manager.load_plugin("integration-test")
        assert success
        
        # Get loaded plugin and register its commands
        loaded_plugin = plugin_manager.get_loaded_plugin("integration-test")
        assert loaded_plugin is not None
        
        # This would normally be handled by the main CLI app
        # but for testing we simulate the command registration
        def mock_register_commands(app):
            registry.register_command(
                name="plugin-test",
                function=lambda: "plugin command executed",
                plugin_source="integration-test"
            )
        
        mock_register_commands(None)
        
        # Verify command was registered
        assert "plugin-test" in registry.commands
        cmd_meta = registry.commands["plugin-test"]
        assert cmd_meta.plugin_source == "integration-test"
        
        # Execute plugin command
        result = await registry.execute_command("plugin-test")
        assert result == "plugin command executed"

class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms"""
    
    @pytest.mark.asyncio
    async def test_command_execution_error_handling(self):
        """Test error handling during command execution"""
        registry = EnhancedCommandRegistry()
        
        def failing_command():
            raise ValueError("Test error")
        
        registry.register_command("failing", failing_command)
        
        # Execute failing command
        with pytest.raises(ValueError):
            await registry.execute_command("failing")
        
        # Verify error metrics were updated
        assert registry.registry_stats['error_count'] == 1
    
    @pytest.mark.asyncio
    async def test_plugin_loading_error_recovery(self, cli_context):
        """Test recovery from plugin loading errors"""
        plugin_manager = PluginManager(cli_context)
        
        # Create a plugin that fails to initialize
        class FailingPlugin(CLIPlugin):
            @property
            def name(self):
                return "failing-plugin"
            
            @property
            def version(self):
                return "1.0.0"
            
            @property
            def description(self):
                return "Failing plugin"
            
            async def initialize(self, context):
                raise RuntimeError("Plugin initialization failed")
        
        plugin_info = PluginInfo(
            name="failing-plugin",
            version="1.0.0",
            description="Failing plugin",
            plugin_class=FailingPlugin,
            enabled=True
        )
        plugin_manager.discovered_plugins["failing-plugin"] = plugin_info
        
        # Try to load failing plugin
        success = await plugin_manager.load_plugin("failing-plugin")
        
        # Should fail gracefully
        assert not success
        assert "failing-plugin" not in plugin_manager.loaded_plugins

# Performance and stress tests
class TestPerformanceAndScaling:
    """Test performance and scaling characteristics"""
    
    @pytest.mark.asyncio
    async def test_command_registry_performance(self):
        """Test command registry performance with many commands"""
        registry = EnhancedCommandRegistry()
        
        # Register many commands
        for i in range(100):
            def make_cmd(index):
                return lambda: f"Command {index} executed"
            
            registry.register_command(
                name=f"cmd-{i}",
                function=make_cmd(i),
                group=f"group-{i // 10}",
                aliases=[f"c{i}", f"command{i}"]
            )
        
        assert len(registry.commands) == 100
        assert len(registry.aliases) == 200  # 2 aliases per command
        
        # Test resolution performance
        import time
        start_time = time.time()
        
        for i in range(100):
            cmd = registry.resolve_command(f"cmd-{i}")
            assert cmd is not None
        
        end_time = time.time()
        resolution_time = end_time - start_time
        
        # Should resolve 100 commands quickly (< 0.1 seconds)
        assert resolution_time < 0.1
    
    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self):
        """Test concurrent command execution"""
        registry = EnhancedCommandRegistry()
        
        async def async_cmd(delay: float = 0.01):
            await asyncio.sleep(delay)
            return f"Async command completed"
        
        registry.register_command("async-cmd", async_cmd)
        
        # Execute multiple commands concurrently
        tasks = [
            registry.execute_command("async-cmd", 0.01)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 10
        assert all(result == "Async command completed" for result in results)
        
        # Verify metrics
        cmd_meta = registry.commands["async-cmd"]
        assert cmd_meta.call_count == 10

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])