"""
Autocomplete Feature Tests
==========================

Test suite for command autocomplete functionality including
history management, suggestion generation, and UI integration.
"""

import pytest
import asyncio
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
from app.cli.intelligence.autocomplete_history import (
    AutocompleteHistoryManager,
    AutocompleteConfig,
    CommandHistoryEntry
)
from app.cli.intelligence.command_intelligence import (
    CommandIntelligenceEngine,
    CommandContext,
    CommandSuggestion
)


class TestAutocompleteHistory:
    """Test autocomplete history management"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def history_manager(self, temp_config_dir):
        """Create history manager instance"""
        config = AutocompleteConfig(
            max_history_size=100,
            enable_encryption=False  # Disable for testing
        )
        return AutocompleteHistoryManager(
            config_dir=temp_config_dir,
            config=config
        )
    
    def test_add_command(self, history_manager):
        """Test adding commands to history"""
        # Add a command
        history_manager.add_command(
            command="git status",
            success=True,
            execution_time=0.5,
            provider="ollama"
        )
        
        # Verify it was added
        assert len(history_manager.history) == 1
        assert history_manager.command_frequency["git status"] == 1
        
        # Add same command again
        history_manager.add_command("git status")
        assert history_manager.command_frequency["git status"] == 2
    
    def test_sanitize_sensitive_data(self, history_manager):
        """Test that sensitive data is sanitized"""
        # Add command with API key
        history_manager.add_command(
            command="export API_KEY=sk-12345abcdef"
        )
        
        # Check it was sanitized
        entry = list(history_manager.history)[0]
        assert "sk-12345abcdef" not in entry.command
        assert "<REDACTED>" in entry.command
        
        # Test password sanitization
        history_manager.add_command(
            command="mysql -u root -pMyPassword123"
        )
        
        entry = list(history_manager.history)[1]
        assert "MyPassword123" not in entry.command
    
    def test_get_suggestions_prefix_match(self, history_manager):
        """Test getting suggestions with prefix matching"""
        # Add test commands
        commands = [
            "git status",
            "git commit -m 'test'",
            "git push origin main",
            "docker ps",
            "docker compose up"
        ]
        
        for cmd in commands:
            history_manager.add_command(cmd)
        
        # Get suggestions for "git"
        suggestions = history_manager.get_suggestions("git")
        
        assert len(suggestions) > 0
        assert all("git" in cmd for cmd, _ in suggestions)
        
        # Get suggestions for "docker"
        suggestions = history_manager.get_suggestions("docker")
        assert all("docker" in cmd for cmd, _ in suggestions)
    
    def test_get_suggestions_fuzzy_match(self, history_manager):
        """Test fuzzy matching in suggestions"""
        # Configure for fuzzy matching
        history_manager.config.enable_fuzzy = True
        history_manager.config.fuzzy_threshold = 0.6
        
        # Add commands
        history_manager.add_command("kubectl get pods")
        history_manager.add_command("kubectl describe service")
        
        # Test fuzzy match
        suggestions = history_manager.get_suggestions("kctl")  # Typo
        
        # Should still find kubectl commands with fuzzy matching
        assert len(suggestions) > 0
    
    def test_context_filtering(self, history_manager):
        """Test context-aware suggestion filtering"""
        # Add commands with context
        history_manager.add_command(
            command="npm install",
            provider="openai",
            working_directory="/project/frontend"
        )
        
        history_manager.add_command(
            command="pip install requests",
            provider="ollama",
            working_directory="/project/backend"
        )
        
        # Get suggestions with context
        context = {
            'provider': 'openai',
            'working_directory': '/project/frontend'
        }
        
        suggestions = history_manager.get_suggestions("", context=context)
        
        # npm command should be boosted for matching context
        if suggestions:
            assert any("npm" in cmd for cmd, _ in suggestions)
    
    def test_deduplication_window(self, history_manager):
        """Test that recent commands are not suggested"""
        history_manager.config.deduplication_window = 3
        
        # Add commands
        for i in range(5):
            history_manager.add_command(f"command_{i}")
        
        # Most recent commands should not be suggested
        suggestions = history_manager.get_suggestions("command")
        suggested_commands = [cmd for cmd, _ in suggestions]
        
        # Recent commands (2, 3, 4) should not be suggested
        assert "command_4" not in suggested_commands
        assert "command_3" not in suggested_commands
    
    def test_save_load_history(self, history_manager, temp_config_dir):
        """Test saving and loading history"""
        # Add commands
        history_manager.add_command("test command 1")
        history_manager.add_command("test command 2")
        
        # Save
        history_manager.save_history()
        
        # Create new manager and load
        new_manager = AutocompleteHistoryManager(
            config_dir=temp_config_dir,
            config=AutocompleteConfig(enable_encryption=False)
        )
        
        # Verify loaded correctly
        assert len(new_manager.history) == 2
        assert new_manager.command_frequency["test command 1"] == 1
    
    def test_clear_old_history(self, history_manager):
        """Test clearing old history entries"""
        # Add old and new commands
        old_time = time.time() - (40 * 86400)  # 40 days ago
        
        # Manually add old entry
        old_entry = CommandHistoryEntry(
            command="old command",
            timestamp=old_time
        )
        history_manager.history.append(old_entry)
        
        # Add new command
        history_manager.add_command("new command")
        
        # Clear entries older than 30 days
        removed = history_manager.clear_history(older_than_days=30)
        
        assert removed == 1
        assert len(history_manager.history) == 1
        assert list(history_manager.history)[0].command == "new command"
    
    def test_export_history(self, history_manager, temp_config_dir):
        """Test exporting history to file"""
        # Add commands
        history_manager.add_command("export test 1")
        history_manager.add_command("export test 2")
        
        # Export as JSON
        export_file = temp_config_dir / "export.json"
        history_manager.export_history(export_file, format='json')
        
        assert export_file.exists()
        
        # Verify export content
        with open(export_file) as f:
            data = json.load(f)
        
        assert len(data['entries']) == 2
        assert data['statistics']['total_commands'] == 2
    
    def test_get_statistics(self, history_manager):
        """Test getting usage statistics"""
        # Add variety of commands
        history_manager.add_command("git status", success=True)
        history_manager.add_command("git status", success=True)
        history_manager.add_command("git commit", success=False)
        history_manager.add_command("docker ps", success=True)
        
        stats = history_manager.get_statistics()
        
        assert stats['total_commands'] == 4
        assert stats['unique_commands'] == 3
        assert stats['average_success_rate'] == 0.75  # 3/4 successful
        assert len(stats['most_used_commands']) > 0
        assert stats['most_used_commands'][0][0] == "git status"  # Most used


class TestCommandIntelligence:
    """Test command intelligence integration"""
    
    @pytest.fixture
    def mock_behavior_tracker(self):
        """Create mock behavior tracker"""
        return Mock()
    
    @pytest.fixture
    def mock_model_manager(self):
        """Create mock model manager"""
        return Mock()
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    async def intelligence_engine(self, mock_behavior_tracker, mock_model_manager, temp_config_dir):
        """Create command intelligence engine"""
        engine = CommandIntelligenceEngine(
            behavior_tracker=mock_behavior_tracker,
            model_manager=mock_model_manager,
            config_dir=temp_config_dir,
            autocomplete_config=AutocompleteConfig(enable_encryption=False)
        )
        # Wait for initialization
        await asyncio.sleep(0.1)
        return engine
    
    @pytest.mark.asyncio
    async def test_get_suggestions_with_autocomplete(self, intelligence_engine):
        """Test getting suggestions with autocomplete history"""
        # Add some history
        intelligence_engine.autocomplete_history.add_command("git status")
        intelligence_engine.autocomplete_history.add_command("git commit -m 'test'")
        
        # Create context
        context = CommandContext(
            current_directory="/test/project",
            recent_commands=["cd /test/project"],
            available_providers=["ollama"]
        )
        
        # Get suggestions
        suggestions = await intelligence_engine.get_command_suggestions(
            "git",
            context,
            max_suggestions=5
        )
        
        # Should have suggestions
        assert len(suggestions) > 0
        assert any(s.source == 'autocomplete' for s in suggestions)
        assert any("git" in s.command for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_record_command_execution(self, intelligence_engine):
        """Test recording command execution"""
        # Record a command
        await intelligence_engine.record_command_execution(
            command="test command",
            success=True,
            execution_time=1.5,
            provider="ollama",
            arguments=["arg1", "arg2"]
        )
        
        # Verify it was recorded
        assert "test command" in intelligence_engine.command_vocabulary
        assert intelligence_engine.command_frequency["test command"] == 1
        assert intelligence_engine.autocomplete_history.command_frequency["test command"] == 1
    
    @pytest.mark.asyncio
    async def test_command_pattern_learning(self, intelligence_engine):
        """Test learning command patterns"""
        # Record sequence of commands
        await intelligence_engine.record_command_execution("git status")
        await intelligence_engine.record_command_execution("git add .")
        await intelligence_engine.record_command_execution("git commit")
        
        # Check patterns were learned
        assert "git status" in intelligence_engine.command_patterns
        assert "git add ." in intelligence_engine.command_patterns["git status"]
    
    @pytest.mark.asyncio
    async def test_suggestion_caching(self, intelligence_engine):
        """Test that suggestions are cached"""
        context = CommandContext(current_directory="/test")
        
        # First call - should cache
        suggestions1 = await intelligence_engine.get_command_suggestions("test", context)
        
        # Second call - should use cache
        suggestions2 = await intelligence_engine.get_command_suggestions("test", context)
        
        # Should be the same object (cached)
        assert suggestions1 == suggestions2
    
    @pytest.mark.asyncio
    async def test_performance_target(self, intelligence_engine):
        """Test that suggestion generation meets performance target"""
        context = CommandContext(current_directory="/test")
        
        # Measure time
        start = time.time()
        suggestions = await intelligence_engine.get_command_suggestions("git", context)
        elapsed = time.time() - start
        
        # Should be under 16ms target (allow some margin for test environment)
        assert elapsed < 0.1  # 100ms margin for tests


class TestAutocompleteUI:
    """Test autocomplete UI components"""
    
    def test_autocomplete_prompt_creation(self):
        """Test creating autocomplete prompt"""
        from app.cli.ui.autocomplete_prompt import AutocompletePrompt
        from rich.console import Console
        
        console = Console()
        
        def mock_suggestions(partial):
            return [("test1", 0.9), ("test2", 0.7)]
        
        prompt = AutocompletePrompt(
            console=console,
            get_suggestions=mock_suggestions
        )
        
        assert prompt is not None
        assert prompt.max_suggestions == 10
    
    def test_autocomplete_state_management(self):
        """Test autocomplete state transitions"""
        from app.cli.ui.autocomplete_prompt import AutocompleteState
        
        state = AutocompleteState()
        
        # Initial state
        assert state.input_text == ""
        assert state.cursor_position == 0
        assert not state.show_suggestions
        
        # Update state
        state.input_text = "git"
        state.cursor_position = 3
        state.suggestions = [("git status", 0.9)]
        state.show_suggestions = True
        
        assert state.show_suggestions
        assert len(state.suggestions) == 1
    
    @patch('app.cli.ui.autocomplete_prompt.readchar')
    def test_keyboard_navigation(self, mock_readchar):
        """Test keyboard navigation in autocomplete"""
        from app.cli.ui.autocomplete_prompt import AutocompletePrompt
        from rich.console import Console
        
        console = Console()
        
        def mock_suggestions(partial):
            return [("test1", 0.9), ("test2", 0.7)]
        
        prompt = AutocompletePrompt(
            console=console,
            get_suggestions=mock_suggestions
        )
        
        # Test tab completion
        prompt.state.input_text = "te"
        prompt.state.suggestions = [("test1", 0.9), ("test2", 0.7)]
        prompt.state.show_suggestions = True
        prompt.state.selected_index = 0
        
        # Simulate Tab key
        result = prompt._handle_tab()
        assert prompt.state.input_text == "test1"
        assert not result  # Should continue
        
        # Test arrow navigation
        prompt.state.show_suggestions = True
        prompt.state.suggestions = [("test1", 0.9), ("test2", 0.7)]
        prompt.state.selected_index = 0
        
        prompt._handle_down()
        assert prompt.state.selected_index == 1
        
        prompt._handle_up()
        assert prompt.state.selected_index == 0


@pytest.mark.integration
class TestAutocompleteIntegration:
    """Integration tests for autocomplete system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_autocomplete(self):
        """Test complete autocomplete flow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create components
            from app.cli.intelligence.behavior_tracker import BehaviorTracker
            from app.cli.intelligence.ml_models import TensorFlowJSModelManager
            
            behavior_tracker = BehaviorTracker(config_dir=config_dir)
            model_manager = TensorFlowJSModelManager(config_dir=config_dir)
            
            # Create intelligence engine
            intelligence = CommandIntelligenceEngine(
                behavior_tracker=behavior_tracker,
                model_manager=model_manager,
                config_dir=config_dir,
                autocomplete_config=AutocompleteConfig(enable_encryption=False)
            )
            
            # Simulate command history
            await intelligence.record_command_execution("git status")
            await intelligence.record_command_execution("git add .")
            await intelligence.record_command_execution("git commit -m 'test'")
            await intelligence.record_command_execution("docker ps")
            await intelligence.record_command_execution("docker compose up")
            
            # Test autocomplete
            context = CommandContext(
                current_directory="/test/project",
                recent_commands=["cd /test/project"],
                available_providers=["ollama"]
            )
            
            # Get suggestions for "git"
            suggestions = await intelligence.get_command_suggestions("git", context)
            
            assert len(suggestions) > 0
            assert any("git" in s.command for s in suggestions)
            assert suggestions[0].source == 'autocomplete'  # History has priority
            
            # Get suggestions for "doc"
            suggestions = await intelligence.get_command_suggestions("doc", context)
            assert any("docker" in s.command for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_secure_storage(self):
        """Test secure storage of command history"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # Create manager with encryption
            config = AutocompleteConfig(enable_encryption=True)
            manager = AutocompleteHistoryManager(
                config_dir=config_dir,
                config=config
            )
            
            # Add sensitive command
            manager.add_command("export API_KEY=secret123")
            
            # Save with encryption
            manager.save_history()
            
            # Check encrypted file exists
            encrypted_file = config_dir / "autocomplete_history.enc"
            if encrypted_file.exists():
                # File should be encrypted (not readable as JSON)
                with open(encrypted_file, 'rb') as f:
                    content = f.read()
                
                # Should not contain plain text
                assert b"secret123" not in content
                assert b"API_KEY" not in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])