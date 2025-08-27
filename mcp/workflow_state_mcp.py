#!/usr/bin/env python3
"""
Workflow State MCP (Model Context Protocol) Server
Independent implementation for LocalAgent project
Provides workflow execution state management, phase tracking, and evidence collection
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import uuid

@dataclass
class PhaseResult:
    """Result from a workflow phase execution"""
    phase_id: str
    phase_name: str
    status: str  # pending, in_progress, completed, failed, skipped
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        if data['started_at']:
            data['started_at'] = data['started_at'].isoformat()
        if data['completed_at']:
            data['completed_at'] = data['completed_at'].isoformat()
        return data

@dataclass
class WorkflowExecution:
    """Complete workflow execution state"""
    execution_id: str
    workflow_name: str
    status: str  # pending, running, completed, failed, cancelled
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    current_phase: Optional[str]
    phase_results: List[PhaseResult] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    iteration_count: int = 0
    max_iterations: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['created_at'] = data['created_at'].isoformat()
        if data['started_at']:
            data['started_at'] = data['started_at'].isoformat()
        if data['completed_at']:
            data['completed_at'] = data['completed_at'].isoformat()
        data['phase_results'] = [p.to_dict() if isinstance(p, PhaseResult) else p 
                                 for p in data['phase_results']]
        return data

class PhaseStatus(str, Enum):
    """Workflow phase status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowStatus(str, Enum):
    """Overall workflow status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowStateMCP:
    """
    Workflow State MCP Server
    Manages workflow execution state and phase progression
    """
    
    # Standard 12-phase workflow definition
    STANDARD_PHASES = [
        "0A_prompt_engineering",
        "0B_environment_setup",
        "1_research_discovery",
        "2_strategic_planning",
        "3_context_creation",
        "4_parallel_execution",
        "5_integration_merge",
        "6_testing_validation",
        "7_audit_learning",
        "8_cleanup_documentation",
        "9_production_deployment"
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.active_execution: Optional[str] = None
        self.phase_templates: Dict[str, Dict[str, Any]] = self._load_phase_templates()
        self.logger = logging.getLogger(__name__)
        self.state_file = Path(self.config.get('state_file', '.workflow_state.json'))
        
    def _load_phase_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load phase templates with success criteria"""
        return {
            "0A_prompt_engineering": {
                "name": "Interactive Prompt Engineering",
                "description": "Refine and clarify user requirements",
                "success_criteria": ["user_approval", "refined_prompt"],
                "required_evidence": ["user_confirmation"]
            },
            "0B_environment_setup": {
                "name": "Environment Setup & Validation",
                "description": "Validate environment and MCP servers",
                "success_criteria": ["environment_validated", "mcps_available"],
                "required_evidence": ["validation_results"]
            },
            "1_research_discovery": {
                "name": "Parallel Research & Discovery",
                "description": "Gather information from multiple sources",
                "success_criteria": ["research_complete", "data_collected"],
                "required_evidence": ["research_results", "analysis_output"]
            },
            "2_strategic_planning": {
                "name": "Strategic Planning & Stream Design",
                "description": "Design execution strategy and streams",
                "success_criteria": ["plan_created", "streams_defined"],
                "required_evidence": ["execution_plan", "stream_definitions"]
            },
            "3_context_creation": {
                "name": "Context Package Creation",
                "description": "Create context packages for agents",
                "success_criteria": ["packages_created", "token_limits_met"],
                "required_evidence": ["context_packages"]
            },
            "4_parallel_execution": {
                "name": "Parallel Stream Execution",
                "description": "Execute parallel agent streams",
                "success_criteria": ["all_streams_complete", "tests_pass"],
                "required_evidence": ["stream_results", "test_results"]
            },
            "5_integration_merge": {
                "name": "Integration & Merge",
                "description": "Integrate results from parallel streams",
                "success_criteria": ["merge_successful", "no_conflicts"],
                "required_evidence": ["merge_report"]
            },
            "6_testing_validation": {
                "name": "Comprehensive Testing",
                "description": "Run comprehensive test suite",
                "success_criteria": ["all_tests_pass", "security_validated"],
                "required_evidence": ["test_results", "security_report"]
            },
            "7_audit_learning": {
                "name": "Audit & Learning",
                "description": "Audit execution and extract learnings",
                "success_criteria": ["audit_complete", "improvements_identified"],
                "required_evidence": ["audit_report", "learnings"]
            },
            "8_cleanup_documentation": {
                "name": "Cleanup & Documentation",
                "description": "Clean workspace and update documentation",
                "success_criteria": ["workspace_clean", "docs_updated"],
                "required_evidence": ["cleanup_report", "documentation"]
            },
            "9_production_deployment": {
                "name": "Production Deployment",
                "description": "Deploy to production environment",
                "success_criteria": ["deployment_successful", "monitoring_active"],
                "required_evidence": ["deployment_log", "health_check"]
            }
        }
    
    async def initialize(self):
        """Initialize the Workflow State MCP server"""
        self.logger.info("Initializing Workflow State MCP Server")
        
        # Load saved state
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    # Restore executions
                    for exec_data in state.get('executions', []):
                        exec_id = exec_data['execution_id']
                        self.executions[exec_id] = self._execution_from_dict(exec_data)
                    self.active_execution = state.get('active_execution')
                    self.logger.info(f"Loaded {len(self.executions)} workflow executions")
            except Exception as e:
                self.logger.warning(f"Could not load state: {e}")
        
        return True
    
    def _execution_from_dict(self, data: Dict[str, Any]) -> WorkflowExecution:
        """Create WorkflowExecution from dictionary"""
        # Convert ISO strings to datetime
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        
        # Convert phase results
        phase_results = []
        for pr_data in data.get('phase_results', []):
            if 'started_at' in pr_data and pr_data['started_at']:
                pr_data['started_at'] = datetime.fromisoformat(pr_data['started_at'])
            if 'completed_at' in pr_data and pr_data['completed_at']:
                pr_data['completed_at'] = datetime.fromisoformat(pr_data['completed_at'])
            phase_results.append(PhaseResult(**pr_data))
        
        data['phase_results'] = phase_results
        return WorkflowExecution(**data)
    
    async def create_execution(
        self,
        workflow_name: str,
        context: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> WorkflowExecution:
        """Create a new workflow execution"""
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_name=workflow_name,
            status=WorkflowStatus.PENDING.value,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            current_phase=None,
            context=context or {},
            metadata=metadata or {}
        )
        
        self.executions[execution_id] = execution
        self.active_execution = execution_id
        
        self.logger.info(f"Created workflow execution {execution_id}: {workflow_name}")
        return execution
    
    async def start_phase(
        self,
        execution_id: str,
        phase_id: str,
        phase_name: Optional[str] = None
    ) -> PhaseResult:
        """Start a workflow phase"""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution = self.executions[execution_id]
        
        # Update execution status if needed
        if execution.status == WorkflowStatus.PENDING.value:
            execution.status = WorkflowStatus.RUNNING.value
            execution.started_at = datetime.now()
        
        # Create phase result
        phase_result = PhaseResult(
            phase_id=phase_id,
            phase_name=phase_name or self.phase_templates.get(phase_id, {}).get('name', phase_id),
            status=PhaseStatus.IN_PROGRESS.value,
            started_at=datetime.now(),
            completed_at=None
        )
        
        execution.phase_results.append(phase_result)
        execution.current_phase = phase_id
        
        self.logger.info(f"Started phase {phase_id} for execution {execution_id}")
        return phase_result
    
    async def complete_phase(
        self,
        execution_id: str,
        phase_id: str,
        status: str = PhaseStatus.COMPLETED.value,
        evidence: List[Dict[str, Any]] = None,
        outputs: Dict[str, Any] = None,
        errors: List[str] = None,
        metrics: Dict[str, Any] = None
    ) -> bool:
        """Complete a workflow phase"""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        
        # Find the phase result
        phase_result = None
        for pr in execution.phase_results:
            if pr.phase_id == phase_id and pr.status == PhaseStatus.IN_PROGRESS.value:
                phase_result = pr
                break
        
        if not phase_result:
            self.logger.warning(f"Phase {phase_id} not found or not in progress")
            return False
        
        # Update phase result
        phase_result.status = status
        phase_result.completed_at = datetime.now()
        phase_result.evidence = evidence or []
        phase_result.outputs = outputs or {}
        phase_result.errors = errors or []
        phase_result.metrics = metrics or {}
        
        # Calculate execution time
        if phase_result.started_at:
            duration = (phase_result.completed_at - phase_result.started_at).total_seconds()
            phase_result.metrics['execution_time_seconds'] = duration
        
        self.logger.info(f"Completed phase {phase_id} with status {status}")
        
        # Check if workflow is complete
        await self._check_workflow_completion(execution_id)
        
        return True
    
    async def _check_workflow_completion(self, execution_id: str):
        """Check if workflow is complete"""
        execution = self.executions[execution_id]
        
        # Check if all phases are complete
        incomplete_phases = [
            pr for pr in execution.phase_results 
            if pr.status in [PhaseStatus.IN_PROGRESS.value, PhaseStatus.PENDING.value]
        ]
        
        if not incomplete_phases:
            # Check if any phase failed
            failed_phases = [
                pr for pr in execution.phase_results 
                if pr.status == PhaseStatus.FAILED.value
            ]
            
            if failed_phases:
                execution.status = WorkflowStatus.FAILED.value
            else:
                execution.status = WorkflowStatus.COMPLETED.value
            
            execution.completed_at = datetime.now()
            execution.current_phase = None
            
            self.logger.info(f"Workflow {execution_id} completed with status {execution.status}")
    
    async def add_evidence(
        self,
        execution_id: str,
        phase_id: str,
        evidence_type: str,
        evidence_data: Any,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Add evidence to a phase"""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        
        # Find the phase
        for phase_result in execution.phase_results:
            if phase_result.phase_id == phase_id:
                evidence = {
                    'type': evidence_type,
                    'data': evidence_data,
                    'timestamp': datetime.now().isoformat(),
                    'metadata': metadata or {}
                }
                phase_result.evidence.append(evidence)
                self.logger.debug(f"Added {evidence_type} evidence to phase {phase_id}")
                return True
        
        return False
    
    async def iterate_workflow(
        self,
        execution_id: str,
        reason: str,
        context_updates: Dict[str, Any] = None
    ) -> bool:
        """Iterate workflow with updated context"""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        
        # Check iteration limit
        if execution.iteration_count >= execution.max_iterations:
            self.logger.warning(f"Workflow {execution_id} reached max iterations")
            execution.status = WorkflowStatus.FAILED.value
            execution.completed_at = datetime.now()
            return False
        
        # Increment iteration count
        execution.iteration_count += 1
        
        # Update context
        if context_updates:
            execution.context.update(context_updates)
        
        # Add iteration metadata
        execution.metadata[f'iteration_{execution.iteration_count}'] = {
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'context_updates': list(context_updates.keys()) if context_updates else []
        }
        
        # Reset current phase
        execution.current_phase = None
        
        self.logger.info(f"Iterating workflow {execution_id}, iteration {execution.iteration_count}")
        return True
    
    async def get_execution_progress(self, execution_id: str) -> Dict[str, Any]:
        """Get execution progress information"""
        if execution_id not in self.executions:
            return {}
        
        execution = self.executions[execution_id]
        
        total_phases = len(self.STANDARD_PHASES)
        completed_phases = sum(
            1 for pr in execution.phase_results 
            if pr.status in [PhaseStatus.COMPLETED.value, PhaseStatus.SKIPPED.value]
        )
        
        failed_phases = sum(
            1 for pr in execution.phase_results 
            if pr.status == PhaseStatus.FAILED.value
        )
        
        progress_percentage = (completed_phases / total_phases * 100) if total_phases > 0 else 0
        
        # Calculate total execution time
        total_time = 0
        for pr in execution.phase_results:
            if 'execution_time_seconds' in pr.metrics:
                total_time += pr.metrics['execution_time_seconds']
        
        return {
            'execution_id': execution_id,
            'workflow_name': execution.workflow_name,
            'status': execution.status,
            'current_phase': execution.current_phase,
            'iteration': execution.iteration_count,
            'progress_percentage': round(progress_percentage, 2),
            'phases_completed': completed_phases,
            'phases_failed': failed_phases,
            'total_phases': total_phases,
            'total_execution_time_seconds': round(total_time, 2),
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'phase_summary': [
                {
                    'phase_id': pr.phase_id,
                    'status': pr.status,
                    'errors': len(pr.errors),
                    'evidence_count': len(pr.evidence)
                }
                for pr in execution.phase_results
            ]
        }
    
    async def get_phase_evidence(
        self,
        execution_id: str,
        phase_id: str
    ) -> List[Dict[str, Any]]:
        """Get evidence for a specific phase"""
        if execution_id not in self.executions:
            return []
        
        execution = self.executions[execution_id]
        
        for phase_result in execution.phase_results:
            if phase_result.phase_id == phase_id:
                return phase_result.evidence
        
        return []
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a workflow execution"""
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        
        if execution.status in [WorkflowStatus.COMPLETED.value, WorkflowStatus.FAILED.value]:
            return False
        
        execution.status = WorkflowStatus.CANCELLED.value
        execution.completed_at = datetime.now()
        
        # Mark current phase as cancelled
        if execution.current_phase:
            for pr in execution.phase_results:
                if pr.phase_id == execution.current_phase and pr.status == PhaseStatus.IN_PROGRESS.value:
                    pr.status = PhaseStatus.SKIPPED.value
                    pr.completed_at = datetime.now()
                    break
        
        self.logger.info(f"Cancelled workflow execution {execution_id}")
        return True
    
    async def get_execution_summary(self, execution_id: str) -> str:
        """Get a markdown summary of the execution"""
        if execution_id not in self.executions:
            return "Execution not found"
        
        execution = self.executions[execution_id]
        
        lines = [f"# Workflow Execution: {execution.workflow_name}\n"]
        lines.append(f"**ID:** {execution_id}")
        lines.append(f"**Status:** {execution.status}")
        lines.append(f"**Iterations:** {execution.iteration_count}")
        
        if execution.started_at:
            lines.append(f"**Started:** {execution.started_at.strftime('%Y-%m-%d %H:%M')}")
        if execution.completed_at:
            lines.append(f"**Completed:** {execution.completed_at.strftime('%Y-%m-%d %H:%M')}")
        
        lines.append("\n## Phase Results\n")
        
        for phase_result in execution.phase_results:
            status_emoji = {
                PhaseStatus.COMPLETED.value: "✅",
                PhaseStatus.FAILED.value: "❌",
                PhaseStatus.IN_PROGRESS.value: "🔄",
                PhaseStatus.SKIPPED.value: "⏭️",
                PhaseStatus.PENDING.value: "⏸️"
            }.get(phase_result.status, "❓")
            
            lines.append(f"### {status_emoji} {phase_result.phase_name}")
            lines.append(f"- **Status:** {phase_result.status}")
            
            if phase_result.metrics.get('execution_time_seconds'):
                lines.append(f"- **Duration:** {phase_result.metrics['execution_time_seconds']:.2f}s")
            
            if phase_result.evidence:
                lines.append(f"- **Evidence:** {len(phase_result.evidence)} items")
            
            if phase_result.errors:
                lines.append(f"- **Errors:** {len(phase_result.errors)}")
                for error in phase_result.errors[:3]:  # Show first 3 errors
                    lines.append(f"  - {error}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    async def save_state(self):
        """Save current state to disk"""
        try:
            # Convert executions to serializable format
            executions_data = []
            for execution in self.executions.values():
                executions_data.append(execution.to_dict())
            
            state = {
                'executions': executions_data,
                'active_execution': self.active_execution,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.logger.info(f"Saved workflow state to {self.state_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False

# Convenience function for standalone usage
async def create_workflow_state_server(config: Dict[str, Any] = None):
    """Create and initialize a Workflow State MCP server"""
    server = WorkflowStateMCP(config)
    await server.initialize()
    return server

if __name__ == "__main__":
    # Test the Workflow State MCP
    async def test():
        workflow_state = await create_workflow_state_server()
        
        # Create an execution
        execution = await workflow_state.create_execution(
            "Test Authentication Implementation",
            context={"project": "LocalAgent"}
        )
        
        # Start and complete phases
        phase1 = await workflow_state.start_phase(execution.execution_id, "0A_prompt_engineering")
        await workflow_state.complete_phase(
            execution.execution_id,
            "0A_prompt_engineering",
            evidence=[{"type": "user_approval", "data": "User approved refined prompt"}]
        )
        
        phase2 = await workflow_state.start_phase(execution.execution_id, "1_research_discovery")
        await workflow_state.add_evidence(
            execution.execution_id,
            "1_research_discovery",
            "research_output",
            {"findings": ["JWT implementation needed", "OAuth2 support required"]}
        )
        await workflow_state.complete_phase(execution.execution_id, "1_research_discovery")
        
        # Get progress
        progress = await workflow_state.get_execution_progress(execution.execution_id)
        print("Progress:", json.dumps(progress, indent=2))
        
        # Get summary
        summary = await workflow_state.get_execution_summary(execution.execution_id)
        print("\nSummary:\n", summary)
        
        # Save state
        await workflow_state.save_state()
    
    asyncio.run(test())