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

__all__ = [
    'SystemInfoPlugin',
    'WorkflowDebugPlugin',
    'ConfigurationPlugin', 
    'BUILTIN_PLUGINS',
    'register_builtin_plugins'
]