"""
Orchestration Bridge
Bridge between CLI and orchestration system
"""

import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from rich.console import Console

from ..core.context import CLIContext
from ..ui.display import DisplayManager
from ...orchestration.orchestration_integration import LocalAgentOrchestrator


class OrchestrationBridge:
    """
    Bridge class for integrating CLI with orchestration system
    Provides a clean interface between CLI commands and workflow engine
    """
    
    def __init__(self, context: CLIContext, display_manager: DisplayManager):
        self.context = context
        self.display_manager = display_manager
        self.console = Console()
        self.orchestrator: Optional[LocalAgentOrchestrator] = None
    
    async def initialize_orchestrator(self, provider_override: Optional[str] = None) -> bool:
        """Initialize the orchestrator with current configuration"""
        try:
            # Create orchestrator with CLI configuration
            config_file = self.context.config.config_file
            self.orchestrator = LocalAgentOrchestrator(str(config_file) if config_file else None)
            
            # Initialize with provider manager from context if available
            if hasattr(self.context, 'provider_manager') and self.context.provider_manager:
                await self.orchestrator.initialize(self.context.provider_manager)
            else:
                # Initialize without provider manager (will create its own)
                await self.orchestrator.initialize(None)
            
            # Set provider override if specified
            if provider_override:
                self.orchestrator.current_provider = provider_override
            
            return True
            
        except Exception as e:
            self.display_manager.print_error(f"Failed to initialize orchestrator: {e}")
            return False
    
    async def execute_workflow(self, prompt: str, execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute 12-phase workflow through orchestrator"""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        
        try:
            # Execute workflow with context
            result = await self.orchestrator.execute_12_phase_workflow(
                prompt, 
                execution_context
            )
            
            return result
            
        except Exception as e:
            self.display_manager.print_error(f"Workflow execution failed: {e}")
            raise
    
    async def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow execution status"""
        if not self.orchestrator:
            return {"status": "not_initialized"}
        
        if self.orchestrator.current_workflow:
            return {
                "status": "running",
                "workflow_id": self.orchestrator.current_workflow.workflow_id,
                "current_phase": self.orchestrator.current_workflow.current_phase,
                "progress": self.orchestrator.current_workflow.get_progress()
            }
        
        return {"status": "idle"}
    
    async def cancel_workflow(self) -> bool:
        """Cancel current workflow execution"""
        if not self.orchestrator or not self.orchestrator.current_workflow:
            return False
        
        try:
            await self.orchestrator.current_workflow.cancel()
            return True
        except Exception as e:
            self.display_manager.print_error(f"Failed to cancel workflow: {e}")
            return False
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents in current workflow"""
        if not self.orchestrator or not self.orchestrator.current_workflow:
            return {"agents": []}
        
        try:
            agents_info = {}
            # This would integrate with actual agent tracking
            # For now, return mock data
            agents_info = {
                "total_agents": 5,
                "active_agents": 2,
                "completed_agents": 3,
                "agents": [
                    {
                        "name": "backend-gateway-expert",
                        "status": "completed",
                        "progress": 100
                    },
                    {
                        "name": "security-validator", 
                        "status": "running",
                        "progress": 75
                    }
                ]
            }
            
            return agents_info
            
        except Exception as e:
            self.display_manager.print_error(f"Failed to get agent status: {e}")
            return {"agents": []}
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get orchestration system health"""
        health_data = {
            "orchestrator_initialized": self.orchestrator is not None,
            "workflow_engine_healthy": False,
            "mcp_connected": False,
            "context_manager_healthy": False,
            "agent_adapter_healthy": False
        }
        
        if self.orchestrator:
            try:
                # Check individual components
                health_data["workflow_engine_healthy"] = hasattr(self.orchestrator, 'workflow_engine')
                health_data["mcp_connected"] = hasattr(self.orchestrator, 'mcp_integration')
                health_data["context_manager_healthy"] = hasattr(self.orchestrator, 'context_manager')
                health_data["agent_adapter_healthy"] = hasattr(self.orchestrator, 'agent_adapter')
                
            except Exception as e:
                self.display_manager.print_debug(f"Health check error: {e}")
        
        return health_data
    
    def is_ready(self) -> bool:
        """Check if orchestration bridge is ready for use"""
        return self.orchestrator is not None and self.orchestrator.initialized
    
    async def cleanup(self):
        """Cleanup orchestration resources"""
        if self.orchestrator:
            try:
                # Cancel any running workflow
                if self.orchestrator.current_workflow:
                    await self.orchestrator.current_workflow.cancel()
                
                # Cleanup orchestrator resources
                await self.orchestrator.cleanup()
                
            except Exception as e:
                self.display_manager.print_debug(f"Cleanup error: {e}")
            
            finally:
                self.orchestrator = None


async def create_orchestrator_for_cli(context: CLIContext, display_manager: DisplayManager) -> OrchestrationBridge:
    """Factory function to create and initialize orchestration bridge"""
    bridge = OrchestrationBridge(context, display_manager)
    
    if await bridge.initialize_orchestrator():
        return bridge
    else:
        raise RuntimeError("Failed to initialize orchestration bridge")