"""
Claude CLI-style Theming and Color Schemes
Implements the visual identity of Claude Code patterns
"""

from typing import Dict, Any, List
from rich.console import Console
from rich.theme import Theme
from rich.style import Style
from inquirerpy.prompts.common import InquirerPyStyle
from inquirerpy import inquirer

# Claude CLI Color Palette
CLAUDE_COLORS = {
    # Primary brand colors
    'claude_orange': '#FF6B35',
    'claude_blue': '#2B5CE6', 
    'claude_purple': '#8B5CF6',
    'claude_teal': '#0891B2',
    
    # Interface colors
    'primary': '#2B5CE6',
    'secondary': '#8B5CF6',
    'success': '#10B981',
    'warning': '#F59E0B',
    'error': '#EF4444',
    'info': '#3B82F6',
    
    # Neutral colors
    'text_primary': '#1F2937',
    'text_secondary': '#6B7280',
    'text_muted': '#9CA3AF',
    'background': '#F9FAFB',
    'surface': '#FFFFFF',
    'border': '#E5E7EB',
    
    # Dark mode colors
    'dark_bg': '#111827',
    'dark_surface': '#1F2937',
    'dark_text': '#F9FAFB',
    'dark_border': '#374151',
    
    # Accent colors for different contexts
    'provider_ollama': '#0891B2',
    'provider_openai': '#10B981',
    'provider_gemini': '#8B5CF6',
    'provider_claude': '#FF6B35',
    'provider_perplexity': '#F59E0B',
}

# Rich Theme Configuration
CLAUDE_RICH_THEME = Theme({
    # Base styles
    'primary': f"bold {CLAUDE_COLORS['primary']}",
    'secondary': f"bold {CLAUDE_COLORS['secondary']}",
    'success': f"bold {CLAUDE_COLORS['success']}",
    'warning': f"bold {CLAUDE_COLORS['warning']}",
    'error': f"bold {CLAUDE_COLORS['error']}",
    'info': f"bold {CLAUDE_COLORS['info']}",
    
    # Text styles
    'text.primary': CLAUDE_COLORS['text_primary'],
    'text.secondary': CLAUDE_COLORS['text_secondary'],
    'text.muted': CLAUDE_COLORS['text_muted'],
    
    # Interactive elements
    'prompt.question': f"bold {CLAUDE_COLORS['primary']}",
    'prompt.answer': f"bold {CLAUDE_COLORS['success']}",
    'prompt.default': CLAUDE_COLORS['text_muted'],
    'prompt.error': f"bold {CLAUDE_COLORS['error']}",
    'prompt.validation': CLAUDE_COLORS['text_secondary'],
    
    # Status indicators
    'status.success': f"bold {CLAUDE_COLORS['success']} on default",
    'status.error': f"bold {CLAUDE_COLORS['error']} on default",
    'status.warning': f"bold {CLAUDE_COLORS['warning']} on default",
    'status.info': f"bold {CLAUDE_COLORS['info']} on default",
    'status.processing': f"bold {CLAUDE_COLORS['secondary']} on default",
    
    # UI Components
    'panel.border': CLAUDE_COLORS['border'],
    'panel.title': f"bold {CLAUDE_COLORS['primary']}",
    'table.header': f"bold {CLAUDE_COLORS['primary']}",
    'table.row.even': CLAUDE_COLORS['surface'],
    'table.row.odd': CLAUDE_COLORS['background'],
    
    # Progress bars
    'progress.bar': CLAUDE_COLORS['primary'],
    'progress.complete': CLAUDE_COLORS['success'],
    'progress.remaining': CLAUDE_COLORS['border'],
    'progress.spinner': CLAUDE_COLORS['secondary'],
    
    # Providers
    'provider.ollama': CLAUDE_COLORS['provider_ollama'],
    'provider.openai': CLAUDE_COLORS['provider_openai'],
    'provider.gemini': CLAUDE_COLORS['provider_gemini'],
    'provider.claude': CLAUDE_COLORS['provider_claude'],
    'provider.perplexity': CLAUDE_COLORS['provider_perplexity'],
    
    # Workflow phases
    'phase.active': f"bold {CLAUDE_COLORS['primary']}",
    'phase.completed': f"bold {CLAUDE_COLORS['success']}",
    'phase.failed': f"bold {CLAUDE_COLORS['error']}",
    'phase.pending': CLAUDE_COLORS['text_muted'],
    
    # Agent types
    'agent.orchestration': CLAUDE_COLORS['claude_purple'],
    'agent.research': CLAUDE_COLORS['claude_blue'],
    'agent.development': CLAUDE_COLORS['claude_teal'],
    'agent.testing': CLAUDE_COLORS['success'],
    'agent.security': CLAUDE_COLORS['error'],
    'agent.infrastructure': CLAUDE_COLORS['warning'],
})

# InquirerPy Style Configuration
CLAUDE_INQUIRER_STYLE = InquirerPyStyle([
    # Question styles
    ("question", f"bold fg:{CLAUDE_COLORS['primary']}"),
    ("instruction", f"fg:{CLAUDE_COLORS['text_secondary']}"),
    ("answer", f"bold fg:{CLAUDE_COLORS['success']}"),
    ("input", f"fg:{CLAUDE_COLORS['text_primary']}"),
    ("default", f"italic fg:{CLAUDE_COLORS['text_muted']}"),
    
    # Selection styles
    ("pointer", f"bold fg:{CLAUDE_COLORS['primary']}"),
    ("highlighted", f"bold bg:{CLAUDE_COLORS['primary']} fg:white"),
    ("selected", f"fg:{CLAUDE_COLORS['success']}"),
    ("skipped", f"fg:{CLAUDE_COLORS['text_muted']} italic"),
    
    # Validation styles
    ("validation-toolbar", f"bg:{CLAUDE_COLORS['error']} fg:white bold"),
    ("invalid", f"fg:{CLAUDE_COLORS['error']}"),
    ("valid", f"fg:{CLAUDE_COLORS['success']}"),
    
    # Fuzzy search styles
    ("fuzzy", f"fg:{CLAUDE_COLORS['text_secondary']}"),
    ("fuzzy-pattern", f"bold fg:{CLAUDE_COLORS['primary']}"),
    ("fuzzy-match", f"bold fg:{CLAUDE_COLORS['claude_orange']}"),
    
    # Progress and loading
    ("spinner", f"fg:{CLAUDE_COLORS['secondary']}"),
    ("long-instruction", f"fg:{CLAUDE_COLORS['text_secondary']}"),
    
    # Checkbox and multi-select
    ("checkbox", f"fg:{CLAUDE_COLORS['primary']}"),
    ("checkbox-selected", f"bold fg:{CLAUDE_COLORS['success']}"),
    ("checkbox-checked", f"bold fg:{CLAUDE_COLORS['success']}"),
    
    # Scrollbar and borders
    ("scrollbar", f"fg:{CLAUDE_COLORS['border']}"),
    ("frame.border", f"fg:{CLAUDE_COLORS['border']}"),
    ("frame.label", f"bold fg:{CLAUDE_COLORS['primary']}"),
])

# Provider-specific color mappings
PROVIDER_COLORS = {
    'ollama': CLAUDE_COLORS['provider_ollama'],
    'openai': CLAUDE_COLORS['provider_openai'],
    'gemini': CLAUDE_COLORS['provider_gemini'], 
    'claude': CLAUDE_COLORS['provider_claude'],
    'perplexity': CLAUDE_COLORS['provider_perplexity'],
    'anthropic': CLAUDE_COLORS['provider_claude'],  # Alias for Claude
}

# Workflow phase color mappings
PHASE_COLORS = {
    'phase_0': CLAUDE_COLORS['claude_orange'],
    'phase_1': CLAUDE_COLORS['claude_blue'],
    'phase_2': CLAUDE_COLORS['claude_purple'],
    'phase_3': CLAUDE_COLORS['claude_teal'],
    'phase_4': CLAUDE_COLORS['primary'],
    'phase_5': CLAUDE_COLORS['secondary'],
    'phase_6': CLAUDE_COLORS['success'],
    'phase_7': CLAUDE_COLORS['info'],
    'phase_8': CLAUDE_COLORS['warning'],
    'phase_9': CLAUDE_COLORS['provider_perplexity'],
}

# Status icons with colors
STATUS_ICONS = {
    'success': ('✓', CLAUDE_COLORS['success']),
    'error': ('✗', CLAUDE_COLORS['error']),
    'warning': ('⚠', CLAUDE_COLORS['warning']),
    'info': ('ℹ', CLAUDE_COLORS['info']),
    'processing': ('⚡', CLAUDE_COLORS['secondary']),
    'waiting': ('⏳', CLAUDE_COLORS['text_muted']),
    'running': ('🔄', CLAUDE_COLORS['primary']),
    'completed': ('🎉', CLAUDE_COLORS['success']),
    'failed': ('💥', CLAUDE_COLORS['error']),
    'partial': ('⚡', CLAUDE_COLORS['warning']),
}

# Progress indicators
PROGRESS_STYLES = {
    'default': {
        'complete_style': CLAUDE_COLORS['success'],
        'incomplete_style': CLAUDE_COLORS['border'],
        'bar_width': 40,
        'pulse': True,
    },
    'workflow': {
        'complete_style': CLAUDE_COLORS['primary'],
        'incomplete_style': CLAUDE_COLORS['text_muted'],
        'bar_width': 50,
        'pulse': True,
    },
    'provider_test': {
        'complete_style': CLAUDE_COLORS['provider_ollama'],
        'incomplete_style': CLAUDE_COLORS['border'],
        'bar_width': 30,
        'pulse': False,
    }
}


class ClaudeThemeManager:
    """
    Manages Claude CLI theming and styling
    """
    
    def __init__(self, dark_mode: bool = False):
        self.dark_mode = dark_mode
        self.console = Console(theme=CLAUDE_RICH_THEME)
        self.inquirer_style = CLAUDE_INQUIRER_STYLE
    
    def get_console(self) -> Console:
        """Get themed Rich console instance"""
        return self.console
    
    def get_inquirer_style(self) -> InquirerPyStyle:
        """Get InquirerPy style configuration"""
        return self.inquirer_style
    
    def get_provider_color(self, provider_name: str) -> str:
        """Get color for specific provider"""
        return PROVIDER_COLORS.get(provider_name.lower(), CLAUDE_COLORS['text_primary'])
    
    def get_phase_color(self, phase_number: int) -> str:
        """Get color for workflow phase"""
        phase_key = f'phase_{phase_number}'
        return PHASE_COLORS.get(phase_key, CLAUDE_COLORS['text_primary'])
    
    def get_status_icon(self, status: str) -> tuple:
        """Get icon and color for status"""
        return STATUS_ICONS.get(status, ('•', CLAUDE_COLORS['text_primary']))
    
    def format_provider_name(self, provider_name: str, enabled: bool = True) -> str:
        """Format provider name with appropriate styling"""
        color = self.get_provider_color(provider_name)
        status = "✓" if enabled else "✗"
        return f"[{color}]{status} {provider_name.title()}[/{color}]"
    
    def format_phase_name(self, phase_number: int, phase_name: str, status: str = 'pending') -> str:
        """Format workflow phase with appropriate styling"""
        color = self.get_phase_color(phase_number)
        icon, icon_color = self.get_status_icon(status)
        return f"[{icon_color}]{icon}[/{icon_color}] [{color}]Phase {phase_number}: {phase_name}[/{color}]"
    
    def format_agent_name(self, agent_type: str, agent_name: str) -> str:
        """Format agent name with type-specific styling"""
        color = CLAUDE_RICH_THEME.styles.get(f'agent.{agent_type}', CLAUDE_COLORS['text_primary'])
        return f"[{color}]{agent_name}[/{color}]"
    
    def create_status_text(self, status: str, message: str) -> str:
        """Create formatted status message"""
        icon, color = self.get_status_icon(status)
        return f"[{color}]{icon} {message}[/{color}]"
    
    def create_progress_style(self, style_name: str = 'default') -> Dict[str, Any]:
        """Create progress bar style configuration"""
        return PROGRESS_STYLES.get(style_name, PROGRESS_STYLES['default'])
    
    def get_color_palette(self) -> Dict[str, str]:
        """Get the complete color palette"""
        return CLAUDE_COLORS.copy()
    
    def apply_dark_mode(self):
        """Apply dark mode theme modifications"""
        self.dark_mode = True
        # Update colors for dark mode
        dark_theme_overrides = {
            'text.primary': CLAUDE_COLORS['dark_text'],
            'text.secondary': CLAUDE_COLORS['text_muted'],
            'panel.border': CLAUDE_COLORS['dark_border'],
            'table.row.even': CLAUDE_COLORS['dark_surface'],
            'table.row.odd': CLAUDE_COLORS['dark_bg'],
        }
        
        # Update Rich theme
        updated_styles = {**CLAUDE_RICH_THEME.styles, **dark_theme_overrides}
        self.console = Console(theme=Theme(updated_styles))
    
    def apply_light_mode(self):
        """Apply light mode theme (default)"""
        self.dark_mode = False
        self.console = Console(theme=CLAUDE_RICH_THEME)


# Global theme manager instance
_theme_manager: ClaudeThemeManager = None

def get_theme_manager(dark_mode: bool = False) -> ClaudeThemeManager:
    """Get or create global theme manager instance"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ClaudeThemeManager(dark_mode)
    return _theme_manager

def get_console() -> Console:
    """Get themed console instance"""
    return get_theme_manager().get_console()

def get_inquirer_style() -> InquirerPyStyle:
    """Get InquirerPy style configuration"""
    return get_theme_manager().get_inquirer_style()

def format_provider(provider_name: str, enabled: bool = True) -> str:
    """Format provider name with theming"""
    return get_theme_manager().format_provider_name(provider_name, enabled)

def format_phase(phase_number: int, phase_name: str, status: str = 'pending') -> str:
    """Format workflow phase with theming"""
    return get_theme_manager().format_phase_name(phase_number, phase_name, status)

def format_status(status: str, message: str) -> str:
    """Format status message with theming"""
    return get_theme_manager().create_status_text(status, message)


# Example theme showcase for testing
def showcase_theme():
    """Display a showcase of the Claude CLI theme"""
    console = get_console()
    
    console.print("\n[bold]🎨 Claude CLI Theme Showcase[/bold]\n")
    
    # Colors showcase
    console.print("[primary]Primary Color[/primary]")
    console.print("[secondary]Secondary Color[/secondary]")
    console.print("[success]Success Color[/success]")
    console.print("[warning]Warning Color[/warning]")
    console.print("[error]Error Color[/error]")
    console.print("[info]Info Color[/info]")
    
    # Provider colors
    console.print("\n[bold]Provider Colors:[/bold]")
    for provider in ['ollama', 'openai', 'gemini', 'claude', 'perplexity']:
        console.print(format_provider(provider, True))
    
    # Status indicators
    console.print("\n[bold]Status Indicators:[/bold]")
    for status in ['success', 'error', 'warning', 'info', 'processing', 'waiting']:
        console.print(format_status(status, f"This is a {status} message"))
    
    # Phase indicators
    console.print("\n[bold]Workflow Phases:[/bold]")
    for i, (phase_name, status) in enumerate([
        ("Interactive Prompt Engineering", "completed"),
        ("Parallel Research & Discovery", "running"),
        ("Strategic Planning & Stream Design", "pending"),
        ("Context Package Creation", "pending"),
    ]):
        console.print(format_phase(i, phase_name, status))


if __name__ == "__main__":
    showcase_theme()