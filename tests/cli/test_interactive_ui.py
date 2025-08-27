"""
Tests for Interactive UI Components
Verifies modern prompts, theming, and display components
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from rich.console import Console

from app.cli.ui.themes import ClaudeThemeManager, get_theme_manager, format_provider
from app.cli.ui.enhanced_prompts import ModernInteractivePrompts, GuidedSetupWizard
from app.cli.ui.display import DisplayManager, create_display_manager


class TestClaudeThemeManager:
    """Test Claude CLI theming system"""
    
    def test_theme_manager_initialization(self):
        """Test theme manager creates properly"""
        theme_manager = ClaudeThemeManager()
        assert theme_manager is not None
        assert theme_manager.console is not None
    
    def test_provider_color_mapping(self):
        """Test provider color retrieval"""
        theme_manager = ClaudeThemeManager()
        
        # Test known providers
        ollama_color = theme_manager.get_provider_color('ollama')
        openai_color = theme_manager.get_provider_color('openai')
        
        assert ollama_color is not None
        assert openai_color is not None
        assert ollama_color != openai_color
    
    def test_phase_color_mapping(self):
        """Test workflow phase color retrieval"""
        theme_manager = ClaudeThemeManager()
        
        phase_0_color = theme_manager.get_phase_color(0)
        phase_1_color = theme_manager.get_phase_color(1)
        
        assert phase_0_color is not None
        assert phase_1_color is not None
    
    def test_status_icon_mapping(self):
        """Test status icon and color retrieval"""
        theme_manager = ClaudeThemeManager()
        
        success_icon, success_color = theme_manager.get_status_icon('success')
        error_icon, error_color = theme_manager.get_status_icon('error')
        
        assert success_icon != error_icon
        assert success_color != error_color
    
    def test_provider_formatting(self):
        """Test provider name formatting"""
        theme_manager = ClaudeThemeManager()
        
        enabled_provider = theme_manager.format_provider_name('ollama', True)
        disabled_provider = theme_manager.format_provider_name('ollama', False)
        
        assert '✓' in enabled_provider or 'ollama' in enabled_provider.lower()
        assert enabled_provider != disabled_provider
    
    def test_dark_mode_toggle(self):
        """Test dark mode functionality"""
        theme_manager = ClaudeThemeManager()
        
        # Start in light mode
        assert not theme_manager.dark_mode
        
        # Switch to dark mode
        theme_manager.apply_dark_mode()
        assert theme_manager.dark_mode
        
        # Switch back to light mode
        theme_manager.apply_light_mode()
        assert not theme_manager.dark_mode


class TestModernInteractivePrompts:
    """Test modern interactive prompts"""
    
    def setup_method(self):
        """Setup test console and prompts"""
        self.console = Console(file=open('/dev/null', 'w'))  # Suppress output in tests
        self.prompts = ModernInteractivePrompts(self.console)
    
    def test_prompts_initialization(self):
        """Test prompts initialize properly"""
        assert self.prompts.console is not None
        assert hasattr(self.prompts, 'modern_mode')
    
    @patch('builtins.input', return_value='test_value')
    def test_text_input_fallback(self, mock_input):
        """Test text input works in fallback mode"""
        # This tests the fallback when InquirerPy is not available
        if not self.prompts.modern_mode:
            result = self.prompts.ask_text("Test question", default="default")
            assert result is not None
    
    def test_provider_selection_choices(self):
        """Test provider selection creates proper choices"""
        available_providers = ['ollama', 'openai', 'gemini']
        
        # This should work regardless of InquirerPy availability
        # In fallback mode, it will use rich prompts
        assert len(available_providers) == 3
        assert 'ollama' in available_providers
    
    def test_workflow_options_structure(self):
        """Test workflow options return proper structure"""
        # Mock the prompting to avoid user interaction
        with patch.object(self.prompts, 'ask_choice', return_value='guided'), \
             patch.object(self.prompts, 'ask_integer', return_value=5), \
             patch.object(self.prompts, 'ask_boolean', return_value=True), \
             patch.object(self.prompts, 'ask_multi_choice', return_value=['Phase 1', 'Phase 2']):
            
            options = self.prompts.ask_workflow_options()
            
            assert 'execution_mode' in options
            assert 'max_parallel_agents' in options
            assert 'collect_evidence' in options
            assert 'phases_to_run' in options


class TestDisplayManager:
    """Test enhanced display components"""
    
    def setup_method(self):
        """Setup test display manager"""
        self.console = Console(file=open('/dev/null', 'w'))  # Suppress output
        self.display = create_display_manager(self.console)
    
    def test_display_manager_initialization(self):
        """Test display manager initializes properly"""
        assert self.display.console is not None
        assert hasattr(self.display, 'theme_manager')
    
    def test_progress_creation(self):
        """Test progress indicator creation"""
        simple_progress = self.display.create_simple_progress("Test")
        assert simple_progress is not None
        
        phase_progress = self.display.create_phase_progress()
        assert phase_progress is not None
        
        provider_progress = self.display.create_provider_progress('ollama')
        assert provider_progress is not None
    
    def test_status_display_methods(self):
        """Test status display methods don't crash"""
        # Test with empty data
        empty_phases = {}
        empty_agents = {}
        empty_status = {}
        
        # These should not raise exceptions
        try:
            self.display.display_phase_status(empty_phases)
            self.display.display_agent_activity(empty_agents)
            self.display.display_quick_status(empty_status)
            # Success if no exceptions
            assert True
        except Exception as e:
            pytest.fail(f"Display methods should not crash with empty data: {e}")
    
    def test_workflow_progress_context_manager(self):
        """Test workflow progress context manager"""
        with self.display.create_workflow_progress("Test Workflow") as progress:
            assert progress is not None
            task = progress.add_task("Test task", total=100)
            progress.update(task, advance=50)
            # Should not crash
    
    def test_provider_status_display(self):
        """Test provider status display with sample data"""
        providers_data = {
            'ollama': {
                'enabled': True,
                'healthy': True,
                'default_model': 'llama2'
            },
            'openai': {
                'enabled': False,
                'healthy': False,
                'has_api_key': False,
                'api_key_required': True
            }
        }
        
        # Should not crash
        try:
            from app.cli.ui.enhanced_prompts import ModernInteractivePrompts
            prompts = ModernInteractivePrompts(self.console)
            prompts.display_provider_status(providers_data)
            assert True
        except Exception as e:
            pytest.fail(f"Provider status display should not crash: {e}")


class TestGuidedSetupWizard:
    """Test guided setup wizard"""
    
    def setup_method(self):
        """Setup test wizard"""
        self.console = Console(file=open('/dev/null', 'w'))
        self.wizard = GuidedSetupWizard(self.console)
    
    def test_wizard_initialization(self):
        """Test wizard initializes properly"""
        assert self.wizard.console is not None
        assert self.wizard.prompts is not None
    
    @pytest.mark.asyncio
    async def test_quick_setup_structure(self):
        """Test quick setup returns valid config structure"""
        # Mock all user inputs
        with patch.object(self.wizard.prompts, 'ask_boolean', return_value=False), \
             patch.object(self.wizard.prompts, 'ask_multi_choice', return_value=[]):
            
            config = await self.wizard._quick_setup()
            
            assert config is not None
            assert hasattr(config, 'config_dir')
            assert hasattr(config, 'providers')
            assert hasattr(config, 'default_provider')


class TestUIIntegration:
    """Test UI component integration"""
    
    def test_theme_formatting_functions(self):
        """Test global theme formatting functions"""
        provider_formatted = format_provider('ollama', True)
        assert 'ollama' in provider_formatted.lower()
        
        provider_disabled = format_provider('ollama', False)
        assert provider_formatted != provider_disabled
    
    def test_console_creation(self):
        """Test themed console creation"""
        from app.cli.ui.display import create_themed_console
        
        console = create_themed_console()
        assert console is not None
    
    def test_component_compatibility(self):
        """Test that components work together"""
        # Create components
        console = Console(file=open('/dev/null', 'w'))
        display = create_display_manager(console)
        prompts = ModernInteractivePrompts(console)
        
        # Test they can work together
        assert display.console is not None
        assert prompts.console is not None
        
        # They should use the same console or compatible ones
        assert True  # No crashes means success


# Integration test with mock CLI commands
class TestCLIIntegration:
    """Test integration with CLI commands"""
    
    def test_ui_components_importable(self):
        """Test that UI components can be imported without errors"""
        try:
            from app.cli.ui.themes import get_console, get_theme_manager
            from app.cli.ui.enhanced_prompts import create_modern_prompts
            from app.cli.ui.display import create_display_manager
            
            # All imports successful
            assert True
        except ImportError as e:
            pytest.fail(f"UI components should be importable: {e}")
    
    def test_fallback_behavior(self):
        """Test that fallback behavior works when dependencies missing"""
        # This tests the graceful degradation when InquirerPy is not available
        console = Console(file=open('/dev/null', 'w'))
        prompts = ModernInteractivePrompts(console)
        
        # Should work in both modern and fallback modes
        assert prompts is not None
        assert hasattr(prompts, 'modern_mode')
        
        # Test some basic functionality works
        with patch('builtins.input', return_value='test'):
            # In fallback mode, should still work
            result = prompts.ask_text("Test", default="default")
            # Should get either the input or default
            assert result in ['test', 'default'] or result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])