"""
Built-in plugins for LocalAgent CLI
"""

from .builtin_plugins import (
    SystemInfoPlugin,
    WorkflowDebugPlugin, 
    ConfigurationPlugin,
    BUILTIN_PLUGINS,
    register_builtin_plugins
)
from .shell_plugin import ShellCommandPlugin

__all__ = [
    'SystemInfoPlugin',
    'WorkflowDebugPlugin',
    'ConfigurationPlugin',
    'ShellCommandPlugin', 
    'BUILTIN_PLUGINS',
    'register_builtin_plugins'
]