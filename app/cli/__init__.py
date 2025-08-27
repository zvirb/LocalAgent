"""
LocalAgent CLI Toolkit
Modern CLI framework with Typer, Rich, and plugin architecture
"""

from .core.app import create_app
from .core.config import ConfigurationManager, LocalAgentConfig
from .core.context import CLIContext
from .plugins.framework import PluginManager
from .mangle_integration import MangleIntegration, MangleAgentAnalyzer

__version__ = "2.0.0"
__all__ = [
    "create_app",
    "ConfigurationManager", 
    "LocalAgentConfig",
    "CLIContext",
    "PluginManager",
    "MangleIntegration",
    "MangleAgentAnalyzer"
]