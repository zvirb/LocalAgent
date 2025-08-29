"""
12-Phase Workflow Engine for LocalAgent Integration
Implements the complete orchestration system with local agent execution
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
from enum import Enum

from .agent_adapter import AgentProviderAdapter, AgentRequest, AgentResponse

class PhaseStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowStatus(Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class PhaseResult:
    """Result of a single workflow phase execution"""
    phase_id: str
    status: PhaseStatus
    start_time: float
    end_time: float
    agents_executed: List[str]
    agent_responses: List[AgentResponse]
    evidence: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    error: Optional[str] = None

@dataclass
class WorkflowExecution:
    """Complete workflow execution tracking"""
    workflow_id: str
    status: WorkflowStatus
    start_time: float
    end_time: Optional[float]
    current_phase: str
    phase_results: List[PhaseResult]
    iteration_count: int
    context_packages: Dict[str, Any]
    global_evidence: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class WorkflowEngine:
    """
    Complete 12-phase workflow engine with agent orchestration
    Manages the full lifecycle from Phase 0 to Phase 12 with evidence collection
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_workflow_config(config_path)
        self.agent_adapter = None
        self.current_execution: Optional[WorkflowExecution] = None
        self.phase_definitions = {}
        self.logger = logging.getLogger(__name__)
        
        # Evidence collection
        self.evidence_collector = EvidenceCollector()
        
        # Context management
        self.context_manager = None  # Will be set during initialization
        
        # MCP integration (placeholder for now)
        self.mcp_integration = None
        
    def _load_workflow_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load workflow configuration"""
        default_config_path = "workflows/12-phase-workflow.yaml"
        if not Path(default_config_path).exists():
            default_config_path = "/mnt/7ac3bfed-9d8e-4829-b134-b5e98ff7c013/programming/LocalProgramming/workflows/12-phase-workflow.yaml"
            
        config_path = config_path or default_config_path
        
        if Path(config_path).exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Return minimal default configuration
            return {
                'workflow': {
                    'phases': {
                        'phase_0': {
                            'name': 'Todo Context Integration',
                            'agents': ['orchestration-todo-manager']
                        }
                    }
                },
                'context_limits': {
                    'context_packages': 4000
                }
            }
    
    async def initialize(self, agent_adapter: AgentProviderAdapter, context_manager=None, mcp_integration=None):
        """Initialize the workflow engine"""
        self.agent_adapter = agent_adapter
        self.context_manager = context_manager
        self.mcp_integration = mcp_integration
        
        # Load phase definitions
        workflow_config = self.config.get('workflow', {})
        self.phase_definitions = workflow_config.get('phases', {})
        
        self.logger.info("Workflow Engine initialized with {} phases".format(len(self.phase_definitions)))
        
    async def execute_workflow(
        self, 
        initial_prompt: str, 
        context: Dict[str, Any] = None,
        workflow_id: Optional[str] = None
    ) -> WorkflowExecution:
        """Execute the complete 12-phase workflow"""
        
        if not self.agent_adapter:
            raise RuntimeError("Agent adapter not initialized")
            
        workflow_id = workflow_id or f"workflow_{int(time.time())}"
        context = context or {}
        
        # Create workflow execution
        self.current_execution = WorkflowExecution(
            workflow_id=workflow_id,
            status=WorkflowStatus.INITIALIZING,
            start_time=time.time(),
            end_time=None,
            current_phase="phase_0",
            phase_results=[],
            iteration_count=0,
            context_packages={},
            global_evidence=[],
            metadata={
                'initial_prompt': initial_prompt,
                'context': context
            }
        )
        
        try:
            self.current_execution.status = WorkflowStatus.RUNNING
            
            # Execute all phases in sequence
            for phase_id in sorted(self.phase_definitions.keys()):
                if phase_id.startswith('phase_'):
                    await self._execute_phase(phase_id, initial_prompt, context)
                    
                    # Check for early termination conditions
                    last_result = self.current_execution.phase_results[-1]
                    if last_result.status == PhaseStatus.FAILED:
                        # Check if this is a critical failure
                        if self._is_critical_failure(phase_id, last_result):
                            break
            
            # Mark workflow as completed
            self.current_execution.status = WorkflowStatus.COMPLETED
            self.current_execution.end_time = time.time()
            
        except Exception as e:
            self.current_execution.status = WorkflowStatus.FAILED
            self.current_execution.end_time = time.time()
            self.logger.error(f"Workflow execution failed: {e}")
            
        return self.current_execution
    
    async def _execute_phase(self, phase_id: str, initial_prompt: str, context: Dict[str, Any]):
        """Execute a single workflow phase"""
        phase_def = self.phase_definitions[phase_id]
        self.current_execution.current_phase = phase_id
        
        phase_result = PhaseResult(
            phase_id=phase_id,
            status=PhaseStatus.RUNNING,
            start_time=time.time(),
            end_time=0.0,
            agents_executed=[],
            agent_responses=[],
            evidence=[],
            metadata={
                'phase_name': phase_def.get('name', 'Unknown Phase'),
                'phase_description': phase_def.get('description', '')
            }
        )
        
        try:
            self.logger.info(f"Executing {phase_id}: {phase_def.get('name', 'Unknown Phase')}")
            
            # Get agents for this phase
            agents = phase_def.get('agents', [])
            execution_mode = phase_def.get('execution', 'sequential')
            
            if execution_mode == 'parallel':
                # Execute agents in parallel
                await self._execute_agents_parallel(agents, phase_id, initial_prompt, context, phase_result)
            elif execution_mode == 'multi-stream':
                # Execute multi-stream orchestration
                await self._execute_multi_stream(phase_def, initial_prompt, context, phase_result)
            else:
                # Execute agents sequentially
                await self._execute_agents_sequential(agents, phase_id, initial_prompt, context, phase_result)
            
            # Collect phase evidence
            phase_result.evidence = self.evidence_collector.collect_phase_evidence(phase_id, phase_result)
            
            # Update context packages if context manager available
            if self.context_manager:
                await self._update_context_packages(phase_id, phase_result)
            
            phase_result.status = PhaseStatus.COMPLETED
            
        except Exception as e:
            phase_result.status = PhaseStatus.FAILED
            phase_result.error = str(e)
            self.logger.error(f"Phase {phase_id} failed: {e}")
            
        finally:
            phase_result.end_time = time.time()
            self.current_execution.phase_results.append(phase_result)
    
    async def _execute_agents_sequential(self, agents: List[str], phase_id: str, prompt: str, context: Dict[str, Any], phase_result: PhaseResult):
        """Execute agents sequentially"""
        for agent_type in agents:
            agent_request = AgentRequest(
                agent_type=phase_id,
                subagent_type=agent_type,
                description=f"Execute {agent_type} for {phase_id}",
                prompt=self._build_phase_prompt(phase_id, agent_type, prompt),
                context=context,
                max_tokens=self.config.get('context_limits', {}).get('context_packages', 4000)
            )
            
            response = await self.agent_adapter.execute_agent(agent_request)
            phase_result.agents_executed.append(agent_type)
            phase_result.agent_responses.append(response)
    
    async def _execute_agents_parallel(self, agents: List[str], phase_id: str, prompt: str, context: Dict[str, Any], phase_result: PhaseResult):
        """Execute agents in parallel"""
        requests = []
        for agent_type in agents:
            agent_request = AgentRequest(
                agent_type=phase_id,
                subagent_type=agent_type,
                description=f"Execute {agent_type} for {phase_id}",
                prompt=self._build_phase_prompt(phase_id, agent_type, prompt),
                context=context,
                max_tokens=self.config.get('context_limits', {}).get('context_packages', 4000)
            )
            requests.append(agent_request)
        
        responses = await self.agent_adapter.execute_parallel_agents(requests)
        
        phase_result.agents_executed.extend(agents)
        phase_result.agent_responses.extend(responses)
    
    async def _execute_multi_stream(self, phase_def: Dict[str, Any], prompt: str, context: Dict[str, Any], phase_result: PhaseResult):
        """Execute multi-stream orchestration (Phase 5 style)"""
        streams = phase_def.get('streams', {})
        mandatory_agents = phase_def.get('mandatory_agents', [])
        
        # Execute all streams in parallel
        stream_tasks = []
        all_requests = []
        
        for stream_name, stream_def in streams.items():
            stream_agents = stream_def.get('agents', [])
            for agent_type in stream_agents:
                agent_request = AgentRequest(
                    agent_type=f"stream_{stream_name}",
                    subagent_type=agent_type,
                    description=f"Execute {agent_type} in {stream_name} stream",
                    prompt=self._build_stream_prompt(stream_name, agent_type, prompt),
                    context={**context, 'stream': stream_name},
                    max_tokens=self.config.get('context_limits', {}).get('context_packages', 4000)
                )
                all_requests.append(agent_request)
        
        # Add mandatory agents
        for agent_type in mandatory_agents:
            agent_request = AgentRequest(
                agent_type="mandatory",
                subagent_type=agent_type,
                description=f"Execute mandatory agent {agent_type}",
                prompt=self._build_phase_prompt("mandatory", agent_type, prompt),
                context=context,
                max_tokens=self.config.get('context_limits', {}).get('context_packages', 4000)
            )
            all_requests.append(agent_request)
        
        # Execute all in parallel
        responses = await self.agent_adapter.execute_parallel_agents(all_requests)
        
        phase_result.agents_executed.extend([req.subagent_type for req in all_requests])
        phase_result.agent_responses.extend(responses)
    
    def _build_phase_prompt(self, phase_id: str, agent_type: str, original_prompt: str) -> str:
        """Build phase-specific prompt for agent"""
        phase_def = self.phase_definitions.get(phase_id, {})
        phase_name = phase_def.get('name', 'Unknown Phase')
        phase_description = phase_def.get('description', '')
        
        return f"""
**Workflow Phase**: {phase_id} - {phase_name}
**Phase Description**: {phase_description}
**Agent Role**: {agent_type}

**Original User Request**: {original_prompt}

**Phase-Specific Context**: 
- This is part of a 12-phase workflow execution
- Focus on your agent's specific responsibilities
- Coordinate with the overall workflow objectives
- Provide evidence-based results

**Requirements**: {json.dumps(phase_def.get('requirements', []), indent=2)}

Execute your specialized agent work according to your agent definition.
"""
    
    def _build_stream_prompt(self, stream_name: str, agent_type: str, original_prompt: str) -> str:
        """Build stream-specific prompt for multi-stream execution"""
        return f"""
**Stream**: {stream_name}
**Agent**: {agent_type}
**Original Request**: {original_prompt}

**Stream Context**:
- You are working in the {stream_name} stream
- Coordinate with other streams through shared context
- Focus on {stream_name}-specific concerns
- Ensure compatibility with parallel stream outputs

Execute your specialized work for the {stream_name} stream.
"""
    
    def _is_critical_failure(self, phase_id: str, phase_result: PhaseResult) -> bool:
        """Determine if a phase failure is critical enough to stop workflow"""
        # Phase 0 and Phase 1 failures are always critical
        if phase_id in ['phase_0', 'phase_1']:
            return True
            
        # Check if all agents failed
        failed_agents = sum(1 for response in phase_result.agent_responses if not response.success)
        total_agents = len(phase_result.agent_responses)
        
        if total_agents > 0 and failed_agents == total_agents:
            return True
            
        return False
    
    async def _update_context_packages(self, phase_id: str, phase_result: PhaseResult):
        """Update context packages with phase results"""
        if self.context_manager:
            context_data = {
                'phase_id': phase_id,
                'agents_executed': phase_result.agents_executed,
                'success_count': sum(1 for r in phase_result.agent_responses if r.success),
                'evidence': phase_result.evidence,
                'execution_time': phase_result.end_time - phase_result.start_time
            }
            
            await self.context_manager.store_context_package(
                f"{self.current_execution.workflow_id}_{phase_id}",
                context_data,
                max_tokens=self.config.get('context_limits', {}).get('context_packages', 4000)
            )
    
    def get_workflow_status(self) -> Optional[Dict[str, Any]]:
        """Get current workflow status"""
        if not self.current_execution:
            return None
            
        return {
            'workflow_id': self.current_execution.workflow_id,
            'status': self.current_execution.status.value,
            'current_phase': self.current_execution.current_phase,
            'completed_phases': len([r for r in self.current_execution.phase_results if r.status == PhaseStatus.COMPLETED]),
            'total_phases': len(self.phase_definitions),
            'iteration_count': self.current_execution.iteration_count,
            'execution_time': time.time() - self.current_execution.start_time if self.current_execution.status == WorkflowStatus.RUNNING else None
        }
    
    async def pause_workflow(self):
        """Pause current workflow execution"""
        if self.current_execution and self.current_execution.status == WorkflowStatus.RUNNING:
            self.current_execution.status = WorkflowStatus.PAUSED
            
    async def resume_workflow(self):
        """Resume paused workflow execution"""
        if self.current_execution and self.current_execution.status == WorkflowStatus.PAUSED:
            self.current_execution.status = WorkflowStatus.RUNNING
    
    def get_available_phases(self) -> List[Dict[str, str]]:
        """Get list of available workflow phases"""
        return [
            {
                'phase_id': phase_id,
                'name': phase_def.get('name', 'Unknown Phase'),
                'description': phase_def.get('description', ''),
                'agents': phase_def.get('agents', [])
            }
            for phase_id, phase_def in self.phase_definitions.items()
        ]

class EvidenceCollector:
    """Collects and manages evidence throughout workflow execution"""
    
    def collect_phase_evidence(self, phase_id: str, phase_result: PhaseResult) -> List[Dict[str, Any]]:
        """Collect evidence from phase execution"""
        evidence = []
        
        # Collect evidence from agent responses
        for i, response in enumerate(phase_result.agent_responses):
            agent_name = phase_result.agents_executed[i] if i < len(phase_result.agents_executed) else f"agent_{i}"
            
            evidence.append({
                'type': 'agent_execution',
                'agent': agent_name,
                'success': response.success,
                'execution_time': response.execution_time,
                'token_usage': response.token_usage,
                'provider_used': response.provider_used,
                'evidence_items': response.evidence
            })
            
            # Extract concrete evidence from responses
            if response.evidence:
                evidence.extend([
                    {
                        'type': 'agent_evidence',
                        'agent': agent_name,
                        'source': 'response',
                        **item
                    }
                    for item in response.evidence
                ])
        
        # Add phase-level evidence
        evidence.append({
            'type': 'phase_summary',
            'phase_id': phase_id,
            'total_agents': len(phase_result.agents_executed),
            'successful_agents': sum(1 for r in phase_result.agent_responses if r.success),
            'total_execution_time': phase_result.end_time - phase_result.start_time,
            'status': phase_result.status.value
        })
        
        return evidence