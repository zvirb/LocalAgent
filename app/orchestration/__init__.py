"""
LocalAgent Orchestration Integration Package
Complete 12-phase workflow execution system with agent orchestration
"""

from .agent_adapter import AgentProviderAdapter, AgentRequest, AgentResponse
from .workflow_engine import WorkflowEngine, WorkflowExecution, PhaseStatus
from .mcp_integration import OrchestrationMCP, MemoryMCP, RedisMCP, ComputerControlMCP
from .context_manager import ContextManager, ContextPackage, TokenCounter
from .orchestration_integration import LocalAgentOrchestrator, create_orchestrator
from .cli_interface import LocalAgentCLI, main as cli_main

__version__ = "1.0.0"
__author__ = "LocalAgent Integration Team"
__description__ = "Complete orchestration system for LocalAgent"

__all__ = [
    # Core components
    "LocalAgentOrchestrator",
    "AgentProviderAdapter", 
    "WorkflowEngine",
    "ContextManager",
    "OrchestrationMCP",
    
    # Data structures
    "AgentRequest",
    "AgentResponse", 
    "WorkflowExecution",
    "ContextPackage",
    "PhaseStatus",
    
    # MCP components
    "MemoryMCP",
    "RedisMCP",
    "ComputerControlMCP",
    
    # Utilities
    "TokenCounter",
    "LocalAgentCLI",
    
    # Factory functions
    "create_orchestrator",
    "cli_main"
]

# Package metadata
INTEGRATION_INFO = {
    "name": "LocalAgent Orchestration Integration",
    "version": __version__,
    "components": [
        "Agent Provider Adapter Bridge",
        "12-Phase Workflow Engine", 
        "MCP Integration (Memory + Redis)",
        "Context Package Management",
        "CLI Interface"
    ],
    "capabilities": [
        "12-phase workflow execution",
        "Parallel agent orchestration",
        "Context package compression",
        "Evidence collection",
        "Cross-session continuity",
        "Real-time agent coordination",
        "Token management",
        "Provider fallback support"
    ],
    "requirements": [
        "LocalAgent agent definitions",
        "LocalAgent provider system",
        "Optional: Redis for coordination",
        "Optional: Custom MCP servers"
    ]
}