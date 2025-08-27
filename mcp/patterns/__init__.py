"""
MCP Patterns Module - Orchestration patterns for LocalAgent
"""

from mcp.patterns.pattern_registry import (
    PatternCategory,
    PatternDefinition,
    BasePattern,
    MCPPatternRegistry,
    pattern_registry
)

from mcp.patterns.intelligent_selector import (
    PatternSelectionContext,
    PatternRecommendation,
    IntelligentPatternSelector,
    intelligent_selector,
    select_and_execute_pattern
)

__all__ = [
    'PatternCategory',
    'PatternDefinition',
    'BasePattern',
    'MCPPatternRegistry',
    'pattern_registry',
    'PatternSelectionContext',
    'PatternRecommendation',
    'IntelligentPatternSelector',
    'intelligent_selector',
    'select_and_execute_pattern'
]