"""
Complete LocalAgent + UnifiedWorkflow Orchestration Integration
Main orchestration module that combines all components for 12-phase workflow execution
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import yaml

from .agent_adapter import AgentProviderAdapter, AgentRequest, AgentResponse
from .workflow_engine import WorkflowEngine, WorkflowExecution, PhaseStatus
from .mcp_integration import OrchestrationMCP
from .context_manager import ContextManager

class LocalAgentOrchestrator:
    """
    Complete LocalAgent orchestration system with UnifiedWorkflow integration
    Provides CLI interface for 12-phase workflow execution with local/remote flexibility
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = self._load_orchestrator_config()
        
        # Core components
        self.agent_adapter = AgentProviderAdapter(config_path)
        self.workflow_engine = WorkflowEngine()
        self.context_manager = ContextManager(self.config.get('context', {}))
        self.mcp_integration = OrchestrationMCP(self.config.get('mcp', {}))
        
        # Provider manager (will be injected)
        self.provider_manager = None
        
        # State tracking
        self.initialized = False
        self.current_workflow: Optional[WorkflowExecution] = None
        
        # Logging setup
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def _load_orchestrator_config(self) -> Dict[str, Any]:
        """Load orchestrator configuration"""
        default_config = {
            'orchestration': {
                'max_parallel_agents': 10,
                'max_workflow_iterations': 3,
                'enable_evidence_collection': True,
                'enable_cross_session_continuity': True
            },
            'context': {
                'strategic_context_tokens': 3000,
                'technical_context_tokens': 4000,
                'default_context_tokens': 4000
            },
            'mcp': {
                'redis': {
                    'redis_url': 'redis://localhost:6379'
                },
                'memory': {}
            },
            'workflow': {
                'config_path': None  # Will use default UnifiedWorkflow config
            }
        }
        
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                self._deep_merge_config(default_config, user_config)
        
        return default_config
    
    def _deep_merge_config(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Deep merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge_config(base[key], value)
            else:
                base[key] = value
    
    async def initialize(self, provider_manager) -> bool:
        """Initialize all orchestration components"""
        try:
            self.provider_manager = provider_manager
            
            # Initialize components in sequence
            self.logger.info("Initializing LocalAgent Orchestrator...")
            
            # 1. Initialize agent adapter
            await self.agent_adapter.initialize(provider_manager)
            
            # 2. Initialize MCP integration
            mcp_success = await self.mcp_integration.initialize()
            if not mcp_success:
                self.logger.warning("MCP integration failed - continuing with limited functionality")
            
            # 3. Initialize context manager with MCP
            self.context_manager.mcp_integration = self.mcp_integration
            
            # 4. Initialize workflow engine
            await self.workflow_engine.initialize(
                self.agent_adapter, 
                self.context_manager,
                self.mcp_integration
            )
            
            self.initialized = True
            self.logger.info("LocalAgent Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    async def execute_12_phase_workflow(
        self, 
        user_prompt: str,
        context: Dict[str, Any] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute complete 12-phase UnifiedWorkflow"""
        
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        
        context = context or {}
        workflow_id = workflow_id or f"localagent_workflow_{int(time.time())}"
        
        self.logger.info(f"Starting 12-phase workflow: {workflow_id}")
        self.logger.info(f"User prompt: {user_prompt}")
        
        try:
            # Log workflow start
            await self._log_workflow_event(workflow_id, 'workflow_started', {
                'user_prompt': user_prompt,
                'context': context,
                'timestamp': time.time()
            })
            
            # Execute workflow through engine
            execution = await self.workflow_engine.execute_workflow(
                initial_prompt=user_prompt,
                context=context,
                workflow_id=workflow_id
            )
            
            self.current_workflow = execution
            
            # Generate execution report
            report = await self._generate_workflow_report(execution)
            
            # Log workflow completion
            await self._log_workflow_event(workflow_id, 'workflow_completed', {
                'status': execution.status.value,
                'phases_completed': len(execution.phase_results),
                'total_execution_time': execution.end_time - execution.start_time if execution.end_time else 0,
                'evidence_collected': len(execution.global_evidence)
            })
            
            return report
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            await self._log_workflow_event(workflow_id, 'workflow_failed', {
                'error': str(e),
                'timestamp': time.time()
            })
            
            return {
                'success': False,
                'workflow_id': workflow_id,
                'error': str(e),
                'status': 'failed'
            }
    
    async def execute_single_agent(
        self, 
        agent_type: str, 
        prompt: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute a single agent directly (for testing/debugging)"""
        
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized")
        
        context = context or {}
        
        agent_request = AgentRequest(
            agent_type='direct_execution',
            subagent_type=agent_type,
            description=f"Direct execution of {agent_type}",
            prompt=prompt,
            context=context
        )
        
        response = await self.agent_adapter.execute_agent(agent_request)
        
        return {
            'success': response.success,
            'agent_type': agent_type,
            'content': response.content,
            'evidence': response.evidence,
            'execution_time': response.execution_time,
            'token_usage': response.token_usage,
            'provider_used': response.provider_used,
            'error': response.error
        }
    
    async def execute_parallel_agents(
        self, 
        agent_configs: List[Dict[str, str]], 
        shared_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute multiple agents in parallel"""
        
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized")
        
        shared_context = shared_context or {}
        
        # Create agent requests
        requests = []
        for config in agent_configs:
            agent_request = AgentRequest(
                agent_type='parallel_execution',
                subagent_type=config['agent_type'],
                description=config.get('description', f"Parallel execution of {config['agent_type']}"),
                prompt=config['prompt'],
                context=shared_context
            )
            requests.append(agent_request)
        
        # Execute in parallel
        responses = await self.agent_adapter.execute_parallel_agents(requests)
        
        # Compile results
        results = []
        for i, response in enumerate(responses):
            results.append({
                'agent_type': agent_configs[i]['agent_type'],
                'success': response.success,
                'content': response.content,
                'evidence': response.evidence,
                'execution_time': response.execution_time,
                'error': response.error
            })
        
        return {
            'success': all(r['success'] for r in results),
            'total_agents': len(results),
            'successful_agents': sum(1 for r in results if r['success']),
            'results': results
        }
    
    async def get_available_agents(self) -> List[Dict[str, str]]:
        """Get list of available agents"""
        if not self.initialized:
            return []
        
        return self.agent_adapter.get_available_agents()
    
    async def get_workflow_status(self) -> Optional[Dict[str, Any]]:
        """Get current workflow status"""
        if not self.workflow_engine:
            return None
        
        return self.workflow_engine.get_workflow_status()
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health check"""
        health_data = {
            'orchestrator_initialized': self.initialized,
            'timestamp': time.time()
        }
        
        if self.initialized:
            # Agent adapter health
            adapter_health = await self.agent_adapter.health_check()
            health_data['agent_adapter'] = adapter_health
            
            # MCP health
            mcp_health = await self.mcp_integration.health_check()
            health_data['mcp_integration'] = mcp_health
            
            # Context manager stats
            context_stats = self.context_manager.get_storage_stats()
            health_data['context_manager'] = {
                'healthy': True,
                'stats': context_stats
            }
            
            # Provider manager health (if available)
            if self.provider_manager:
                provider_health = await self.provider_manager.health_check_all()
                health_data['providers'] = provider_health
            
            # Overall health assessment
            health_data['overall_healthy'] = (
                adapter_health['adapter_healthy'] and
                mcp_health['overall_healthy'] and
                (not self.provider_manager or any(p.get('healthy', False) for p in health_data.get('providers', {}).values()))
            )
        else:
            health_data['overall_healthy'] = False
        
        return health_data
    
    async def _generate_workflow_report(self, execution: WorkflowExecution) -> Dict[str, Any]:
        """Generate comprehensive workflow execution report"""
        
        # Phase summaries
        phase_summaries = []
        for phase_result in execution.phase_results:
            phase_summaries.append({
                'phase_id': phase_result.phase_id,
                'phase_name': phase_result.metadata.get('phase_name', 'Unknown'),
                'status': phase_result.status.value,
                'agents_executed': phase_result.agents_executed,
                'successful_agents': sum(1 for r in phase_result.agent_responses if r.success),
                'execution_time': phase_result.end_time - phase_result.start_time,
                'evidence_count': len(phase_result.evidence),
                'error': phase_result.error
            })
        
        # Agent performance
        agent_stats = {}
        for phase_result in execution.phase_results:
            for i, agent_name in enumerate(phase_result.agents_executed):
                if i < len(phase_result.agent_responses):
                    response = phase_result.agent_responses[i]
                    if agent_name not in agent_stats:
                        agent_stats[agent_name] = {
                            'executions': 0,
                            'successes': 0,
                            'total_time': 0,
                            'total_tokens': 0
                        }
                    
                    agent_stats[agent_name]['executions'] += 1
                    if response.success:
                        agent_stats[agent_name]['successes'] += 1
                    agent_stats[agent_name]['total_time'] += response.execution_time
                    agent_stats[agent_name]['total_tokens'] += response.token_usage.get('total_tokens', 0)
        
        # Evidence summary
        evidence_summary = {
            'total_evidence_items': len(execution.global_evidence),
            'phase_evidence': sum(len(p.evidence) for p in execution.phase_results),
            'agent_evidence': sum(len(r.evidence) for p in execution.phase_results for r in p.agent_responses)
        }
        
        # Context summary
        context_summary = await self.context_manager.get_workflow_context_summary(execution.workflow_id)
        
        return {
            'success': execution.status.value == 'completed',
            'workflow_id': execution.workflow_id,
            'status': execution.status.value,
            'execution_summary': {
                'total_phases': len(execution.phase_results),
                'completed_phases': len([p for p in execution.phase_results if p.status == PhaseStatus.COMPLETED]),
                'failed_phases': len([p for p in execution.phase_results if p.status == PhaseStatus.FAILED]),
                'total_execution_time': execution.end_time - execution.start_time if execution.end_time else 0,
                'iteration_count': execution.iteration_count
            },
            'phase_summaries': phase_summaries,
            'agent_performance': agent_stats,
            'evidence_summary': evidence_summary,
            'context_summary': context_summary,
            'metadata': execution.metadata
        }
    
    async def _log_workflow_event(self, workflow_id: str, event_type: str, data: Dict[str, Any]):
        """Log workflow event to MCP timeline"""
        if self.mcp_integration:
            await self.mcp_integration.log_workflow_event(workflow_id, event_type, data)
    
    # CLI Command Methods
    
    async def cmd_workflow(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """CLI command: Execute 12-phase workflow"""
        return await self.execute_12_phase_workflow(prompt, kwargs)
    
    async def cmd_agent(self, agent_type: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """CLI command: Execute single agent"""
        return await self.execute_single_agent(agent_type, prompt, kwargs)
    
    async def cmd_parallel(self, config_file: str) -> Dict[str, Any]:
        """CLI command: Execute parallel agents from config"""
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            agent_configs = config.get('agents', [])
            shared_context = config.get('context', {})
            
            return await self.execute_parallel_agents(agent_configs, shared_context)
            
        except Exception as e:
            return {'success': False, 'error': f"Failed to load config: {e}"}
    
    async def cmd_status(self) -> Dict[str, Any]:
        """CLI command: Get workflow status"""
        status = await self.get_workflow_status()
        return status or {'status': 'no_active_workflow'}
    
    async def cmd_health(self) -> Dict[str, Any]:
        """CLI command: System health check"""
        return await self.get_system_health()
    
    async def cmd_agents(self) -> Dict[str, Any]:
        """CLI command: List available agents"""
        agents = await self.get_available_agents()
        return {'agents': agents, 'total_agents': len(agents)}
    
    async def cmd_phases(self) -> Dict[str, Any]:
        """CLI command: List workflow phases"""
        if self.workflow_engine:
            phases = self.workflow_engine.get_available_phases()
            return {'phases': phases, 'total_phases': len(phases)}
        return {'phases': [], 'total_phases': 0}

# Factory function for easy integration
async def create_orchestrator(config_path: Optional[str] = None) -> LocalAgentOrchestrator:
    """Create and initialize a LocalAgent orchestrator"""
    orchestrator = LocalAgentOrchestrator(config_path)
    return orchestrator