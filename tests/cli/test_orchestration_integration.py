"""
Comprehensive Test Suite for CLI Orchestration Integration
Tests cli-009 (orchestration), cli-001 (plugin framework), cli-005 (error handling)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json
from pathlib import Path

# Import components to test
from app.cli.plugins.framework import PluginManager, CLIPlugin, PluginInfo
from app.cli.plugins.hot_reload import PluginHotReloadManager
from app.cli.integration.orchestration_bridge import OrchestrationBridge, WorkflowPhaseTracker
from app.cli.error.cli_error_handler import CLIErrorHandler, InteractiveErrorResolver
from app.cli.monitoring.realtime_monitor import WorkflowMonitor, ProgressTracker
from app.cli.error.recovery import ErrorContext, ErrorSeverity, RecoveryResult


class TestPluginFramework:
    """Test suite for plugin framework completion (cli-001)"""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock CLI context"""
        context = Mock()
        context.config = Mock()
        context.config.plugins = Mock()
        context.config.plugins.plugin_directories = ['/tmp/test-plugins']
        context.config.plugins.enabled_plugins = []
        context.config.plugins.allow_dev_plugins = True
        return context
    
    @pytest.fixture
    async def plugin_manager(self, mock_context):
        """Create plugin manager instance"""
        manager = PluginManager(mock_context)
        return manager
    
    @pytest.mark.asyncio
    async def test_plugin_discovery(self, plugin_manager):
        """Test plugin discovery from entry points"""
        with patch('pkg_resources.iter_entry_points') as mock_iter:
            # Mock entry point
            mock_entry = Mock()
            mock_entry.name = 'test-plugin'
            mock_entry.load = Mock(return_value=Mock(spec=CLIPlugin))
            mock_iter.return_value = [mock_entry]
            
            await plugin_manager.discover_plugins()
            
            assert 'test-plugin' in plugin_manager.discovered_plugins
            assert len(plugin_manager.discovered_plugins) > 0
    
    @pytest.mark.asyncio
    async def test_hot_reload_manager(self, plugin_manager):
        """Test hot-reload functionality"""
        hot_reload = PluginHotReloadManager(plugin_manager)
        
        # Test file hash calculation
        test_file = Path('/tmp/test-plugin.py')
        test_file.write_text('# Test plugin content')
        
        hash1 = hot_reload.calculate_file_hash(test_file)
        assert hash1 is not None
        
        # Modify file
        test_file.write_text('# Modified content')
        hash2 = hot_reload.calculate_file_hash(test_file)
        
        assert hash1 != hash2
        
        # Cleanup
        test_file.unlink()
    
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self, plugin_manager, mock_context):
        """Test plugin initialization and cleanup"""
        # Create mock plugin
        mock_plugin = Mock(spec=CLIPlugin)
        mock_plugin.name = 'test-plugin'
        mock_plugin.version = '1.0.0'
        mock_plugin.description = 'Test plugin'
        mock_plugin.initialize = AsyncMock(return_value=True)
        mock_plugin.cleanup = AsyncMock()
        
        plugin_info = PluginInfo(
            name='test-plugin',
            version='1.0.0',
            description='Test plugin',
            plugin_class=Mock(return_value=mock_plugin),
            enabled=True
        )
        
        plugin_manager.discovered_plugins['test-plugin'] = plugin_info
        
        # Load plugin
        await plugin_manager.load_plugins()
        
        assert 'test-plugin' in plugin_manager.loaded_plugins
        mock_plugin.initialize.assert_called_once()
        
        # Cleanup
        await plugin_manager.cleanup_plugins()
        mock_plugin.cleanup.assert_called_once()
    
    def test_plugin_info_creation(self):
        """Test PluginInfo data structure"""
        plugin_info = PluginInfo(
            name='test',
            version='1.0',
            description='Test',
            plugin_class=Mock(spec=CLIPlugin),
            entry_point='localagent.plugins.test',
            enabled=True
        )
        
        assert plugin_info.name == 'test'
        assert plugin_info.version == '1.0'
        assert plugin_info.entry_point == 'localagent.plugins.test'
        assert plugin_info.enabled is True


class TestErrorHandling:
    """Test suite for CLI error handling integration (cli-005)"""
    
    @pytest.fixture
    def error_handler(self):
        """Create error handler instance"""
        recovery_manager = Mock()
        recovery_manager.config = Mock(debug=True)
        handler = CLIErrorHandler(recovery_manager)
        return handler
    
    @pytest.mark.asyncio
    async def test_cli_error_decorator(self, error_handler):
        """Test CLI error handler decorator"""
        @error_handler.cli_error_handler
        async def test_command():
            raise ValueError("Test error")
        
        with pytest.raises(SystemExit):
            await test_command()
        
        # Check error was added to history
        assert len(error_handler.error_history) == 1
        assert error_handler.error_history[0].error_type == 'ValueError'
    
    def test_error_severity_determination(self, error_handler):
        """Test error severity determination"""
        # Critical error
        critical_context = ErrorContext(
            error_type='SecurityError',
            error_message='Critical security breach detected',
            traceback='',
            timestamp=datetime.now()
        )
        severity = error_handler._determine_severity(critical_context)
        assert severity == ErrorSeverity.CRITICAL
        
        # High severity
        high_context = ErrorContext(
            error_type='ConfigError',
            error_message='Configuration failed to load',
            traceback='',
            timestamp=datetime.now()
        )
        severity = error_handler._determine_severity(high_context)
        assert severity == ErrorSeverity.HIGH
        
        # Medium severity
        medium_context = ErrorContext(
            error_type='TimeoutError',
            error_message='Request timeout exceeded',
            traceback='',
            timestamp=datetime.now()
        )
        severity = error_handler._determine_severity(medium_context)
        assert severity == ErrorSeverity.MEDIUM
    
    def test_recovery_suggestions_generation(self, error_handler):
        """Test recovery suggestions generation"""
        # Configuration error
        config_context = ErrorContext(
            error_type='ConfigError',
            error_message='Invalid configuration file format',
            traceback='',
            timestamp=datetime.now()
        )
        suggestions = error_handler.create_recovery_suggestions(config_context)
        assert len(suggestions) > 0
        assert any('config' in s.lower() for s in suggestions)
        
        # Network error
        network_context = ErrorContext(
            error_type='ConnectionError',
            error_message='Network connection timeout',
            traceback='',
            timestamp=datetime.now()
        )
        suggestions = error_handler.create_recovery_suggestions(network_context)
        assert any('connection' in s.lower() or 'network' in s.lower() for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_interactive_error_resolver(self):
        """Test interactive error resolution"""
        cli_context = Mock()
        resolver = InteractiveErrorResolver(cli_context)
        
        # Test provider error resolution
        with patch.object(resolver, '_check_provider', return_value=True):
            with patch.object(resolver, '_has_api_key', return_value=True):
                # Mock user input
                with patch('rich.prompt.Prompt.ask', return_value='ollama'):
                    provider = await resolver.resolve_provider_error(Exception("Provider failed"))
                    assert provider == 'ollama'


class TestOrchestrationIntegration:
    """Test suite for orchestration bridge (cli-009)"""
    
    @pytest.fixture
    def orchestration_bridge(self):
        """Create orchestration bridge instance"""
        cli_context = Mock()
        cli_context.config = Mock()
        cli_context.config.auth = Mock(jwt_token='test-token')
        bridge = OrchestrationBridge(cli_context)
        return bridge
    
    def test_phase_tracker(self):
        """Test workflow phase tracking"""
        tracker = WorkflowPhaseTracker()
        
        # Update phase
        tracker.update_phase(1, 'running', {'test': 'evidence'})
        assert tracker.current_phase == 1
        assert tracker.phase_statuses[1] == 'running'
        assert tracker.phase_evidence[1] == {'test': 'evidence'}
        
        # Update agent
        tracker.update_agent('test-agent', 'completed')
        assert tracker.agent_statuses['test-agent'] == 'completed'
        
        # Get summary
        summary = tracker.get_phase_summary()
        assert summary['current_phase'] == 1
        assert 'test-agent' in summary['agent_statuses']
    
    @pytest.mark.asyncio
    async def test_workflow_initialization(self, orchestration_bridge):
        """Test workflow initialization"""
        with patch.object(orchestration_bridge, 'redis_client') as mock_redis:
            mock_redis.hset = AsyncMock()
            
            workflow_id = await orchestration_bridge._initialize_workflow(
                "Test prompt",
                {"context": "test"}
            )
            
            assert workflow_id.startswith('cli-workflow-')
            mock_redis.hset.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_phase_execution(self, orchestration_bridge):
        """Test phase execution"""
        with patch.object(orchestration_bridge, 'redis_client') as mock_redis:
            mock_redis.publish = AsyncMock()
            
            # Test Phase 1 execution
            with patch.object(orchestration_bridge, '_execute_agent', 
                            return_value={'success': True, 'output': 'test'}):
                result = await orchestration_bridge._execute_phase_1_research(
                    'test-workflow',
                    {}
                )
                
                assert result['success'] is True
                assert 'agents_executed' in result['evidence']
    
    def test_phase_name_retrieval(self, orchestration_bridge):
        """Test phase name retrieval"""
        assert orchestration_bridge._get_phase_name(1) == "Parallel Research & Discovery"
        assert orchestration_bridge._get_phase_name(6) == "Comprehensive Testing"
        assert orchestration_bridge._get_phase_name(12) == "Monitoring & Loop Control"
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, orchestration_bridge):
        """Test WebSocket connection with JWT header"""
        with patch('websockets.connect') as mock_connect:
            mock_connect.return_value = AsyncMock()
            
            await orchestration_bridge._connect_websocket()
            
            # Verify JWT token in headers
            mock_connect.assert_called_once()
            call_args = mock_connect.call_args
            assert 'extra_headers' in call_args[1]
            assert 'Authorization' in call_args[1]['extra_headers']
            assert 'Bearer test-token' in call_args[1]['extra_headers']['Authorization']


class TestRealtimeMonitoring:
    """Test suite for real-time monitoring"""
    
    @pytest.fixture
    def workflow_monitor(self):
        """Create workflow monitor instance"""
        return WorkflowMonitor()
    
    @pytest.mark.asyncio
    async def test_monitor_initialization(self, workflow_monitor):
        """Test monitor initialization"""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis.return_value = AsyncMock()
            mock_redis.return_value.ping = AsyncMock()
            
            await workflow_monitor.initialize('test-workflow')
            
            assert workflow_monitor.workflow_id == 'test-workflow'
            assert workflow_monitor.start_time is not None
            mock_redis.assert_called_once()
    
    def test_dashboard_layout_creation(self, workflow_monitor):
        """Test dashboard layout generation"""
        layout = workflow_monitor.create_dashboard_layout()
        
        assert layout is not None
        # Layout should have header, main, and footer sections
        assert 'header' in str(layout)
    
    def test_phases_table_generation(self, workflow_monitor):
        """Test phases table generation"""
        workflow_monitor.current_phase = 3
        workflow_monitor.phases_status = {
            0: 'completed',
            1: 'completed',
            2: 'completed',
            3: 'running',
            4: 'pending'
        }
        
        table = workflow_monitor.generate_phases_table()
        assert table is not None
        assert table.title == "Workflow Phases"
    
    def test_agents_table_generation(self, workflow_monitor):
        """Test agents table generation"""
        workflow_monitor.agent_status = {
            'codebase-research-analyst': {
                'status': 'completed',
                'duration': '5.2s'
            },
            'security-validator': {
                'status': 'running',
                'duration': '-'
            }
        }
        
        table = workflow_monitor.generate_agents_table()
        assert table is not None
        assert table.title == "Agent Execution"
    
    @pytest.mark.asyncio
    async def test_event_handling(self, workflow_monitor):
        """Test event handling"""
        # Test phase start event
        await workflow_monitor._handle_event(
            'orchestration:phase:start',
            json.dumps({'phase': 5, 'workflow_id': 'test'})
        )
        assert workflow_monitor.phases_status[5] == 'running'
        assert workflow_monitor.current_phase == 5
        
        # Test phase complete event
        await workflow_monitor._handle_event(
            'orchestration:phase:complete',
            json.dumps({'phase': 5, 'success': True})
        )
        assert workflow_monitor.phases_status[5] == 'completed'
        
        # Test agent start event
        await workflow_monitor._handle_event(
            'orchestration:agent:start',
            json.dumps({'agent': 'test-agent'})
        )
        assert 'test-agent' in workflow_monitor.agent_status
        assert workflow_monitor.agent_status['test-agent']['status'] == 'running'
    
    def test_progress_tracker(self):
        """Test progress tracking"""
        tracker = ProgressTracker()
        
        # Add phase task
        phase_id = tracker.add_phase_task(1, "Research")
        assert 'phase_1' in tracker.tasks
        
        # Add agent task
        agent_id = tracker.add_agent_task('test-agent', "Processing")
        assert 'agent_test-agent' in tracker.tasks
        
        # Update progress
        tracker.update_task('phase_1', 50)
        tracker.complete_task('agent_test-agent')


class TestIntegrationScenarios:
    """End-to-end integration test scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_execution(self):
        """Test complete workflow execution"""
        # Create components
        cli_context = Mock()
        cli_context.config = Mock()
        cli_context.config.auth = Mock(jwt_token='test-token')
        cli_context.config.debug = False
        
        bridge = OrchestrationBridge(cli_context)
        
        # Mock Redis and WebSocket
        with patch.object(bridge, 'redis_client') as mock_redis:
            mock_redis.hset = AsyncMock()
            mock_redis.publish = AsyncMock()
            mock_redis.hgetall = AsyncMock(return_value={'status': 'completed'})
            
            with patch.object(bridge, '_connect_websocket'):
                with patch.object(bridge, '_phase_0_interactive', return_value='refined prompt'):
                    with patch.object(bridge, '_execute_phase', return_value={'success': True}):
                        
                        result = await bridge.execute_workflow(
                            "Test task",
                            {"context": "test"},
                            interactive=True
                        )
                        
                        assert result['status'] == 'completed'
                        assert 'workflow_id' in result
                        assert 'phases' in result
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self):
        """Test error recovery during workflow execution"""
        recovery_manager = Mock()
        recovery_manager.config = Mock(debug=False)
        recovery_manager.handle_error = AsyncMock(return_value=RecoveryResult.PARTIAL)
        
        error_handler = CLIErrorHandler(recovery_manager)
        
        # Create error context
        error_context = ErrorContext(
            error_type='TestError',
            error_message='Test error message',
            traceback='',
            timestamp=datetime.now()
        )
        
        # Test recovery flow
        with patch.object(error_handler, 'interactive_recovery', 
                         return_value=RecoveryResult.SUCCESS):
            result = await error_handler.handle_cli_error(error_context)
            assert result == RecoveryResult.SUCCESS
    
    @pytest.mark.asyncio
    async def test_plugin_hot_reload_scenario(self):
        """Test plugin hot-reload scenario"""
        mock_context = Mock()
        mock_context.config = Mock()
        mock_context.config.plugins = Mock()
        mock_context.config.plugins.plugin_directories = []
        mock_context.config.plugins.enabled_plugins = []
        
        plugin_manager = PluginManager(mock_context)
        hot_reload = PluginHotReloadManager(plugin_manager)
        
        # Mock plugin
        mock_plugin_info = PluginInfo(
            name='test-plugin',
            version='1.0',
            description='Test',
            plugin_class=Mock(spec=CLIPlugin),
            file_path=Path('/tmp/test-plugin.py')
        )
        
        plugin_manager.discovered_plugins['test-plugin'] = mock_plugin_info
        
        # Test reload
        with patch.object(plugin_manager, '_load_plugin', return_value=True):
            success = await hot_reload.reload_plugin('test-plugin')
            assert success is True
            assert len(hot_reload.reload_history) == 1


# Performance and Security Tests
class TestPerformanceAndSecurity:
    """Performance and security validation tests"""
    
    def test_websocket_security_headers(self):
        """Test WebSocket security header implementation (CVE-2024-WS002)"""
        cli_context = Mock()
        cli_context.config = Mock()
        cli_context.config.auth = Mock(jwt_token='secure-token-123')
        
        bridge = OrchestrationBridge(cli_context)
        
        with patch('websockets.connect') as mock_connect:
            asyncio.run(bridge._connect_websocket())
            
            # Verify no token in URL
            call_args = mock_connect.call_args
            assert 'token=' not in call_args[0][0]  # URL should not contain token
            
            # Verify token in headers
            assert 'Authorization' in call_args[1]['extra_headers']
            assert 'Bearer secure-token-123' in call_args[1]['extra_headers']['Authorization']
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self):
        """Test memory cleanup in monitoring components"""
        monitor = WorkflowMonitor()
        
        # Initialize with mock Redis
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_redis.return_value = AsyncMock()
            await monitor.initialize('test')
            
            # Cleanup
            await monitor.cleanup()
            
            # Verify cleanup was called
            assert monitor.monitoring_task is None or monitor.monitoring_task.cancelled()
    
    def test_error_history_memory_limit(self):
        """Test error history memory management"""
        recovery_manager = Mock()
        recovery_manager.config = Mock(debug=True)
        handler = CLIErrorHandler(recovery_manager)
        
        # Add many errors
        for i in range(20):
            error = ErrorContext(
                error_type='TestError',
                error_message=f'Error {i}',
                traceback='',
                timestamp=datetime.now()
            )
            handler.error_history.append(error)
        
        # Create new error with history
        new_error = ErrorContext(
            error_type='NewError',
            error_message='New error',
            traceback='',
            timestamp=datetime.now(),
            previous_errors=handler.error_history[-5:]  # Should only keep last 5
        )
        
        assert len(new_error.previous_errors) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])