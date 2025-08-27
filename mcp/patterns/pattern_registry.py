#!/usr/bin/env python3
"""
MCP Pattern Registry - Central registry for all MCP orchestration patterns
Designed for Docker container deployment with intelligent pattern selection
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import uuid

# Pattern Categories
class PatternCategory(str, Enum):
    """Categories of MCP patterns"""
    SEQUENTIAL = "sequential"      # Linear task execution
    PARALLEL = "parallel"          # Concurrent task execution
    HIERARCHICAL = "hierarchical"  # Tree-based delegation
    MESH = "mesh"                  # Fully connected communication
    PIPELINE = "pipeline"          # Stream processing
    EVENT_DRIVEN = "event_driven"  # Reactive patterns
    CONSENSUS = "consensus"        # Multi-agent agreement
    SCATTER_GATHER = "scatter_gather"  # Distribute and collect

@dataclass
class PatternDefinition:
    """Definition of an MCP orchestration pattern"""
    pattern_id: str
    name: str
    category: PatternCategory
    description: str
    use_cases: List[str]
    required_mcps: List[str]  # Which MCPs are needed
    docker_requirements: Dict[str, Any]  # Container specs
    performance_profile: Dict[str, Any]
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BasePattern(ABC):
    """Abstract base class for MCP patterns"""
    
    def __init__(self, pattern_def: PatternDefinition):
        self.pattern_def = pattern_def
        self.logger = logging.getLogger(f"Pattern.{pattern_def.pattern_id}")
        self.active_mcps: Dict[str, Any] = {}
        
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the pattern with given context"""
        pass
    
    @abstractmethod
    async def validate_prerequisites(self) -> bool:
        """Check if pattern can be executed"""
        pass
    
    async def setup_docker_network(self):
        """Setup Docker networking for pattern execution"""
        # This would interface with docker-compose or docker SDK
        pass

# ============= HRM MCP Patterns =============

class HRMStrategicPlanningPattern(BasePattern):
    """Strategic planning using HRM's hierarchical reasoning"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute strategic planning pattern"""
        # Implement 4-level hierarchical reasoning
        from mcp.hrm_mcp import create_hrm_server
        
        hrm = await create_hrm_server()
        
        # Strategic level reasoning
        strategic_result = await hrm.reason(
            context.get('query', ''),
            context,
            level=0
        )
        
        # Cascade through tactical, operational, implementation
        results = {'strategic': strategic_result}
        
        for child in strategic_result.children:
            results[f'tactical_{child.node_id}'] = child
            
        return results
    
    async def validate_prerequisites(self) -> bool:
        return True

class HRMConsensusPattern(BasePattern):
    """Multi-agent consensus using HRM reasoning"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Multiple HRM instances reach consensus"""
        from mcp.hrm_mcp import create_hrm_server
        
        # Create multiple HRM instances for consensus
        hrm_instances = []
        for i in range(3):  # 3 instances for voting
            hrm = await create_hrm_server({'state_file': f'.hrm_consensus_{i}.json'})
            hrm_instances.append(hrm)
        
        # Each instance reasons independently
        results = []
        for hrm in hrm_instances:
            result = await hrm.reason(context.get('query', ''), context)
            results.append(result)
        
        # Aggregate results and find consensus
        consensus = self._find_consensus(results)
        
        return {'consensus': consensus, 'individual_results': results}
    
    def _find_consensus(self, results):
        """Find consensus among multiple reasoning results"""
        # Implement consensus logic (majority vote, weighted average, etc.)
        decisions = [r.decision for r in results]
        confidences = [r.confidence for r in results]
        
        # Simple majority vote for now
        from collections import Counter
        most_common = Counter(decisions).most_common(1)[0][0]
        avg_confidence = sum(confidences) / len(confidences)
        
        return {
            'decision': most_common,
            'confidence': avg_confidence,
            'agreement_level': Counter(decisions).most_common(1)[0][1] / len(decisions)
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class HRMCascadePattern(BasePattern):
    """Cascading reasoning from strategic to implementation"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute cascading pattern through all reasoning levels"""
        from mcp.hrm_mcp import create_hrm_server
        
        hrm = await create_hrm_server()
        
        # Execute reasoning at each level with context from previous
        results = {}
        current_context = context.copy()
        
        for level in range(4):  # 0: strategic, 1: tactical, 2: operational, 3: implementation
            level_name = ['strategic', 'tactical', 'operational', 'implementation'][level]
            
            result = await hrm.reason(
                current_context.get('query', ''),
                current_context,
                level=level
            )
            
            results[level_name] = result
            
            # Update context with results from this level
            current_context['previous_decision'] = result.decision
            current_context['previous_confidence'] = result.confidence
            
        return results
    
    async def validate_prerequisites(self) -> bool:
        return True

class HRMAdaptivePattern(BasePattern):
    """Adaptive reasoning that adjusts based on feedback"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute adaptive reasoning with feedback loops"""
        from mcp.hrm_mcp import create_hrm_server
        
        hrm = await create_hrm_server()
        
        max_iterations = context.get('max_iterations', 3)
        confidence_threshold = context.get('confidence_threshold', 0.8)
        
        results = []
        current_context = context.copy()
        
        for iteration in range(max_iterations):
            result = await hrm.reason(
                current_context.get('query', ''),
                current_context
            )
            
            results.append(result)
            
            # Check if confidence threshold met
            if result.confidence >= confidence_threshold:
                break
            
            # Adapt context based on result
            current_context['iteration'] = iteration + 1
            current_context['previous_confidence'] = result.confidence
            current_context['refinement_needed'] = True
            
        return {
            'final_result': results[-1],
            'iterations': len(results),
            'adaptation_history': results
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

# ============= Task MCP Patterns =============

class TaskPipelinePattern(BasePattern):
    """Pipeline pattern for sequential task execution"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks in a pipeline"""
        from mcp.task_mcp import create_task_server
        
        task_mcp = await create_task_server()
        
        pipeline_tasks = context.get('pipeline_tasks', [])
        results = []
        
        previous_output = None
        for task_config in pipeline_tasks:
            # Create task with dependency on previous
            task = await task_mcp.create_task(
                title=task_config['title'],
                description=task_config.get('description', ''),
                metadata={'pipeline_stage': len(results), 'previous_output': previous_output}
            )
            
            # Execute task (simulation - would integrate with actual execution)
            await task_mcp.update_task(task.task_id, status="in_progress")
            
            # Process task
            output = await self._process_pipeline_task(task, previous_output)
            
            await task_mcp.update_task(task.task_id, status="completed")
            
            results.append({'task': task, 'output': output})
            previous_output = output
        
        return {'pipeline_results': results}
    
    async def _process_pipeline_task(self, task, previous_output):
        """Process a single pipeline task"""
        # Implement actual task processing
        return {'processed': True, 'task_id': task.task_id}
    
    async def validate_prerequisites(self) -> bool:
        return True

class TaskScatterGatherPattern(BasePattern):
    """Scatter work across multiple tasks, gather results"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Scatter tasks and gather results"""
        from mcp.task_mcp import create_task_server
        
        task_mcp = await create_task_server()
        
        # Scatter phase - create parallel tasks
        scatter_tasks = []
        work_items = context.get('work_items', [])
        
        for item in work_items:
            task = await task_mcp.create_task(
                title=f"Process: {item.get('name', 'item')}",
                description=item.get('description', ''),
                priority=item.get('priority', 'medium'),
                metadata={'scatter_gather': True, 'item': item}
            )
            scatter_tasks.append(task)
        
        # Execute all tasks in parallel (simulation)
        results = await asyncio.gather(*[
            self._execute_scattered_task(task_mcp, task)
            for task in scatter_tasks
        ])
        
        # Gather phase - aggregate results
        gathered = self._gather_results(results)
        
        return {
            'scattered_tasks': len(scatter_tasks),
            'gathered_results': gathered,
            'individual_results': results
        }
    
    async def _execute_scattered_task(self, task_mcp, task):
        """Execute a scattered task"""
        await task_mcp.update_task(task.task_id, status="in_progress")
        # Simulate work
        await asyncio.sleep(0.1)
        await task_mcp.update_task(task.task_id, status="completed")
        return {'task_id': task.task_id, 'result': 'processed'}
    
    def _gather_results(self, results):
        """Aggregate scattered results"""
        return {
            'total_processed': len(results),
            'successful': sum(1 for r in results if r.get('result') == 'processed')
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class TaskPriorityQueuePattern(BasePattern):
    """Priority-based task execution pattern"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks based on priority"""
        from mcp.task_mcp import create_task_server
        
        task_mcp = await create_task_server()
        
        # Get all pending tasks sorted by priority
        tasks = await task_mcp.list_tasks(status="todo", include_completed=False)
        
        # Group by priority
        priority_groups = {
            'urgent': [],
            'high': [],
            'medium': [],
            'low': []
        }
        
        for task in tasks:
            priority_groups[task.priority].append(task)
        
        # Execute in priority order
        execution_order = []
        for priority in ['urgent', 'high', 'medium', 'low']:
            for task in priority_groups[priority]:
                execution_order.append(task)
                await task_mcp.update_task(task.task_id, status="in_progress")
                # Simulate execution
                await asyncio.sleep(0.05)
                await task_mcp.update_task(task.task_id, status="completed")
        
        return {
            'executed_tasks': len(execution_order),
            'priority_distribution': {k: len(v) for k, v in priority_groups.items()},
            'execution_order': [t.task_id for t in execution_order]
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class TaskDependencyGraphPattern(BasePattern):
    """Execute tasks based on dependency graph"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tasks respecting dependencies"""
        from mcp.task_mcp import create_task_server
        
        task_mcp = await create_task_server()
        
        # Build dependency graph
        all_tasks = await task_mcp.list_tasks(include_completed=True)
        
        # Topological sort for execution order
        execution_layers = self._topological_sort(all_tasks)
        
        results = []
        for layer in execution_layers:
            # Execute tasks in this layer in parallel
            layer_results = await asyncio.gather(*[
                self._execute_task_with_deps(task_mcp, task)
                for task in layer
            ])
            results.append(layer_results)
        
        return {
            'execution_layers': len(execution_layers),
            'total_tasks': sum(len(layer) for layer in execution_layers),
            'results': results
        }
    
    def _topological_sort(self, tasks):
        """Sort tasks based on dependencies"""
        # Simple implementation - group by dependency count
        layers = []
        
        # Tasks with no dependencies
        no_deps = [t for t in tasks if not t.dependencies]
        if no_deps:
            layers.append(no_deps)
        
        # Tasks with dependencies
        with_deps = [t for t in tasks if t.dependencies]
        if with_deps:
            layers.append(with_deps)
        
        return layers
    
    async def _execute_task_with_deps(self, task_mcp, task):
        """Execute task checking dependencies"""
        # Check if dependencies are complete
        for dep_id in task.dependencies:
            dep_task = await task_mcp.get_task(dep_id)
            if dep_task and dep_task.status != "completed":
                return {'task_id': task.task_id, 'blocked': True}
        
        await task_mcp.update_task(task.task_id, status="completed")
        return {'task_id': task.task_id, 'executed': True}
    
    async def validate_prerequisites(self) -> bool:
        return True

# ============= Coordination MCP Patterns =============

class CoordHubSpokePattern(BasePattern):
    """Hub-and-spoke coordination pattern"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hub-and-spoke coordination"""
        from mcp.coordination_mcp import create_coordination_server
        
        coord = await create_coordination_server()
        
        # Register hub agent
        hub = await coord.register_agent("hub", "coordinator", capabilities=["routing", "aggregation"])
        
        # Register spoke agents
        spokes = []
        num_spokes = context.get('num_spokes', 4)
        
        for i in range(num_spokes):
            spoke = await coord.register_agent(
                f"spoke_{i}",
                "worker",
                capabilities=["processing"]
            )
            spokes.append(spoke)
        
        # Hub sends tasks to spokes
        for i, spoke in enumerate(spokes):
            await coord.send_message(
                "hub",
                spoke.agent_id,
                "task_request",
                {"task": f"Process segment {i}"}
            )
        
        # Collect responses
        responses = []
        for spoke in spokes:
            messages = await coord.get_messages(spoke.agent_id)
            responses.extend(messages)
        
        return {
            'hub': hub.agent_id,
            'spokes': [s.agent_id for s in spokes],
            'messages_sent': num_spokes,
            'pattern': 'hub-spoke'
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class CoordMeshNetworkPattern(BasePattern):
    """Fully connected mesh network pattern"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mesh network coordination"""
        from mcp.coordination_mcp import create_coordination_server
        
        coord = await create_coordination_server()
        
        # Register mesh agents
        num_agents = context.get('num_agents', 4)
        agents = []
        
        for i in range(num_agents):
            agent = await coord.register_agent(
                f"mesh_{i}",
                "peer",
                capabilities=["communicate", "process"]
            )
            agents.append(agent)
        
        # Each agent communicates with every other agent
        message_count = 0
        for sender in agents:
            for receiver in agents:
                if sender.agent_id != receiver.agent_id:
                    await coord.send_message(
                        sender.agent_id,
                        receiver.agent_id,
                        "sync_request",
                        {"from": sender.agent_id, "to": receiver.agent_id}
                    )
                    message_count += 1
        
        return {
            'agents': [a.agent_id for a in agents],
            'total_connections': message_count,
            'pattern': 'mesh',
            'connectivity': 'full'
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class CoordEventBusPattern(BasePattern):
    """Event-driven coordination using pub/sub"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute event bus pattern"""
        from mcp.coordination_mcp import create_coordination_server
        
        coord = await create_coordination_server()
        
        # Define topics
        topics = context.get('topics', ['task', 'status', 'result'])
        
        # Register publisher agents
        publishers = []
        for i in range(2):
            pub = await coord.register_agent(f"publisher_{i}", "publisher")
            publishers.append(pub)
            # Subscribe to result topic
            await coord.subscribe_topic(pub.agent_id, "result")
        
        # Register subscriber agents
        subscribers = []
        for i in range(3):
            sub = await coord.register_agent(f"subscriber_{i}", "subscriber")
            subscribers.append(sub)
            # Subscribe to all topics
            for topic in topics:
                await coord.subscribe_topic(sub.agent_id, topic)
        
        # Publishers broadcast to topics
        broadcasts = 0
        for pub in publishers:
            for topic in topics[:2]:  # Publishers send to task and status topics
                reach = await coord.publish_to_topic(
                    topic,
                    pub.agent_id,
                    {"event": f"{topic}_event", "publisher": pub.agent_id}
                )
                broadcasts += reach
        
        return {
            'publishers': [p.agent_id for p in publishers],
            'subscribers': [s.agent_id for s in subscribers],
            'topics': topics,
            'total_broadcasts': broadcasts,
            'pattern': 'event-bus'
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class CoordConsensusPattern(BasePattern):
    """Multi-agent consensus coordination"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute consensus pattern"""
        from mcp.coordination_mcp import create_coordination_server
        
        coord = await create_coordination_server()
        
        # Register consensus agents
        num_agents = context.get('num_agents', 5)
        agents = []
        
        for i in range(num_agents):
            agent = await coord.register_agent(
                f"consensus_{i}",
                "voter",
                capabilities=["vote", "propose"]
            )
            agents.append(agent)
        
        # Proposal phase
        proposal = context.get('proposal', 'Execute task X')
        proposer = agents[0]
        
        for agent in agents[1:]:
            await coord.send_message(
                proposer.agent_id,
                agent.agent_id,
                "proposal",
                {"proposal": proposal, "request_vote": True}
            )
        
        # Voting phase
        votes = {'yes': 0, 'no': 0}
        for agent in agents[1:]:
            # Simulate vote (would be actual agent decision)
            vote = 'yes' if hash(agent.agent_id) % 2 == 0 else 'no'
            votes[vote] += 1
            
            await coord.send_message(
                agent.agent_id,
                proposer.agent_id,
                "vote",
                {"vote": vote, "agent": agent.agent_id}
            )
        
        # Consensus decision
        consensus_reached = votes['yes'] > num_agents / 2
        
        return {
            'agents': [a.agent_id for a in agents],
            'proposer': proposer.agent_id,
            'votes': votes,
            'consensus_reached': consensus_reached,
            'pattern': 'consensus'
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

# ============= Workflow State MCP Patterns =============

class WorkflowLinearPattern(BasePattern):
    """Linear workflow execution pattern"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute linear workflow"""
        from mcp.workflow_state_mcp import create_workflow_state_server
        
        workflow = await create_workflow_state_server()
        
        # Create execution
        execution = await workflow.create_execution(
            context.get('workflow_name', 'Linear Workflow'),
            context
        )
        
        # Execute phases sequentially
        phases = workflow.STANDARD_PHASES[:5]  # First 5 phases for demo
        
        for phase_id in phases:
            phase = await workflow.start_phase(execution.execution_id, phase_id)
            
            # Simulate phase execution
            await asyncio.sleep(0.1)
            
            await workflow.complete_phase(
                execution.execution_id,
                phase_id,
                evidence=[{"type": "completion", "data": f"{phase_id} completed"}]
            )
        
        progress = await workflow.get_execution_progress(execution.execution_id)
        
        return {
            'execution_id': execution.execution_id,
            'phases_executed': len(phases),
            'progress': progress,
            'pattern': 'linear'
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class WorkflowParallelPhasesPattern(BasePattern):
    """Parallel phase execution pattern"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow phases in parallel"""
        from mcp.workflow_state_mcp import create_workflow_state_server
        
        workflow = await create_workflow_state_server()
        
        execution = await workflow.create_execution(
            context.get('workflow_name', 'Parallel Workflow'),
            context
        )
        
        # Define parallel phase groups
        parallel_groups = [
            ["1_research_discovery", "2_strategic_planning"],
            ["3_context_creation", "4_parallel_execution"],
            ["5_integration_merge"]
        ]
        
        results = []
        for group in parallel_groups:
            # Start all phases in group
            group_phases = []
            for phase_id in group:
                phase = await workflow.start_phase(execution.execution_id, phase_id)
                group_phases.append((phase_id, phase))
            
            # Execute in parallel
            await asyncio.gather(*[
                self._execute_phase(workflow, execution.execution_id, phase_id)
                for phase_id, _ in group_phases
            ])
            
            results.append(group_phases)
        
        progress = await workflow.get_execution_progress(execution.execution_id)
        
        return {
            'execution_id': execution.execution_id,
            'parallel_groups': len(parallel_groups),
            'total_phases': sum(len(g) for g in parallel_groups),
            'progress': progress,
            'pattern': 'parallel-phases'
        }
    
    async def _execute_phase(self, workflow, execution_id, phase_id):
        """Execute a single phase"""
        await asyncio.sleep(0.1)  # Simulate work
        await workflow.complete_phase(
            execution_id,
            phase_id,
            evidence=[{"type": "parallel", "data": f"{phase_id} parallel execution"}]
        )
    
    async def validate_prerequisites(self) -> bool:
        return True

class WorkflowIterativePattern(BasePattern):
    """Iterative workflow with retry logic"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute iterative workflow pattern"""
        from mcp.workflow_state_mcp import create_workflow_state_server
        
        workflow = await create_workflow_state_server()
        
        execution = await workflow.create_execution(
            context.get('workflow_name', 'Iterative Workflow'),
            context
        )
        
        max_iterations = context.get('max_iterations', 3)
        success_threshold = context.get('success_threshold', 0.8)
        
        iteration_results = []
        
        for iteration in range(max_iterations):
            # Execute key phases
            phases = ["1_research_discovery", "4_parallel_execution", "6_testing_validation"]
            
            iteration_success = True
            for phase_id in phases:
                phase = await workflow.start_phase(execution.execution_id, phase_id)
                
                # Simulate phase execution with possible failure
                success = (hash(f"{phase_id}{iteration}") % 10) > 2  # 80% success rate
                
                if success:
                    await workflow.complete_phase(
                        execution.execution_id,
                        phase_id,
                        evidence=[{"type": "success", "iteration": iteration}]
                    )
                else:
                    await workflow.complete_phase(
                        execution.execution_id,
                        phase_id,
                        status="failed",
                        errors=[f"Failed in iteration {iteration}"]
                    )
                    iteration_success = False
                    break
            
            iteration_results.append({
                'iteration': iteration,
                'success': iteration_success
            })
            
            if iteration_success:
                break
            
            # Iterate workflow if failed
            if iteration < max_iterations - 1:
                await workflow.iterate_workflow(
                    execution.execution_id,
                    f"Iteration {iteration + 1} due to failure",
                    {'retry_attempt': iteration + 1}
                )
        
        return {
            'execution_id': execution.execution_id,
            'iterations': len(iteration_results),
            'iteration_results': iteration_results,
            'pattern': 'iterative'
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

class WorkflowCheckpointPattern(BasePattern):
    """Workflow with checkpoint and recovery"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow with checkpoints"""
        from mcp.workflow_state_mcp import create_workflow_state_server
        
        workflow = await create_workflow_state_server()
        
        execution = await workflow.create_execution(
            context.get('workflow_name', 'Checkpoint Workflow'),
            context
        )
        
        # Define checkpoint phases
        checkpoint_phases = [
            "0B_environment_setup",
            "2_strategic_planning",
            "5_integration_merge",
            "8_cleanup_documentation"
        ]
        
        checkpoints = []
        
        for phase_id in checkpoint_phases:
            phase = await workflow.start_phase(execution.execution_id, phase_id)
            
            # Create checkpoint before phase
            checkpoint = {
                'phase': phase_id,
                'timestamp': asyncio.get_event_loop().time(),
                'state': await workflow.get_execution_progress(execution.execution_id)
            }
            checkpoints.append(checkpoint)
            
            # Execute phase
            await asyncio.sleep(0.1)
            
            # Simulate possible failure
            if hash(phase_id) % 4 == 0:  # 25% failure rate
                # Restore from last checkpoint
                await workflow.complete_phase(
                    execution.execution_id,
                    phase_id,
                    status="failed",
                    errors=["Checkpoint recovery needed"]
                )
                
                # Recovery logic would go here
                checkpoint['recovered'] = True
            else:
                await workflow.complete_phase(
                    execution.execution_id,
                    phase_id,
                    evidence=[{"type": "checkpoint", "data": "Phase checkpointed"}]
                )
        
        await workflow.save_state()
        
        return {
            'execution_id': execution.execution_id,
            'checkpoints_created': len(checkpoints),
            'checkpoints': checkpoints,
            'pattern': 'checkpoint'
        }
    
    async def validate_prerequisites(self) -> bool:
        return True

# ============= Pattern Registry =============

class MCPPatternRegistry:
    """Central registry for all MCP patterns"""
    
    def __init__(self):
        self.patterns: Dict[str, PatternDefinition] = {}
        self.pattern_classes: Dict[str, Type[BasePattern]] = {}
        self.logger = logging.getLogger("PatternRegistry")
        self._register_patterns()
    
    def _register_patterns(self):
        """Register all available patterns"""
        
        # HRM Patterns
        self.register_pattern(
            PatternDefinition(
                pattern_id="hrm_strategic",
                name="HRM Strategic Planning",
                category=PatternCategory.HIERARCHICAL,
                description="Strategic planning using 4-level hierarchical reasoning",
                use_cases=["Complex decision making", "Project planning", "Architecture design"],
                required_mcps=["hrm"],
                docker_requirements={"memory": "512MB", "cpu": "0.5"},
                performance_profile={"latency": "medium", "throughput": "medium"}
            ),
            HRMStrategicPlanningPattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="hrm_consensus",
                name="HRM Consensus",
                category=PatternCategory.CONSENSUS,
                description="Multi-instance HRM consensus for critical decisions",
                use_cases=["Critical decisions", "Risk assessment", "Validation"],
                required_mcps=["hrm"],
                docker_requirements={"memory": "1GB", "cpu": "1.0"},
                performance_profile={"latency": "high", "throughput": "low"}
            ),
            HRMConsensusPattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="hrm_cascade",
                name="HRM Cascade",
                category=PatternCategory.PIPELINE,
                description="Cascading reasoning from strategic to implementation",
                use_cases=["Full stack planning", "End-to-end solutions"],
                required_mcps=["hrm"],
                docker_requirements={"memory": "512MB", "cpu": "0.5"},
                performance_profile={"latency": "high", "throughput": "low"}
            ),
            HRMCascadePattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="hrm_adaptive",
                name="HRM Adaptive",
                category=PatternCategory.EVENT_DRIVEN,
                description="Adaptive reasoning with feedback loops",
                use_cases=["Learning systems", "Optimization", "Refinement"],
                required_mcps=["hrm"],
                docker_requirements={"memory": "512MB", "cpu": "0.5"},
                performance_profile={"latency": "variable", "throughput": "medium"}
            ),
            HRMAdaptivePattern
        )
        
        # Task Patterns
        self.register_pattern(
            PatternDefinition(
                pattern_id="task_pipeline",
                name="Task Pipeline",
                category=PatternCategory.PIPELINE,
                description="Sequential task execution with data flow",
                use_cases=["ETL processes", "Build pipelines", "Data processing"],
                required_mcps=["task"],
                docker_requirements={"memory": "256MB", "cpu": "0.25"},
                performance_profile={"latency": "low", "throughput": "high"}
            ),
            TaskPipelinePattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="task_scatter_gather",
                name="Task Scatter-Gather",
                category=PatternCategory.SCATTER_GATHER,
                description="Distribute work and collect results",
                use_cases=["Parallel processing", "Map-reduce", "Batch operations"],
                required_mcps=["task"],
                docker_requirements={"memory": "512MB", "cpu": "1.0"},
                performance_profile={"latency": "low", "throughput": "very high"}
            ),
            TaskScatterGatherPattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="task_priority_queue",
                name="Task Priority Queue",
                category=PatternCategory.SEQUENTIAL,
                description="Priority-based task execution",
                use_cases=["Job scheduling", "Resource allocation", "Queue management"],
                required_mcps=["task"],
                docker_requirements={"memory": "256MB", "cpu": "0.25"},
                performance_profile={"latency": "low", "throughput": "high"}
            ),
            TaskPriorityQueuePattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="task_dependency_graph",
                name="Task Dependency Graph",
                category=PatternCategory.HIERARCHICAL,
                description="Execute tasks based on dependency DAG",
                use_cases=["Build systems", "Workflow orchestration", "Project management"],
                required_mcps=["task"],
                docker_requirements={"memory": "512MB", "cpu": "0.5"},
                performance_profile={"latency": "medium", "throughput": "medium"}
            ),
            TaskDependencyGraphPattern
        )
        
        # Coordination Patterns
        self.register_pattern(
            PatternDefinition(
                pattern_id="coord_hub_spoke",
                name="Coordination Hub-Spoke",
                category=PatternCategory.HIERARCHICAL,
                description="Centralized coordination through hub",
                use_cases=["Service orchestration", "API gateway", "Load balancing"],
                required_mcps=["coordination"],
                docker_requirements={"memory": "256MB", "cpu": "0.5"},
                performance_profile={"latency": "low", "throughput": "high"}
            ),
            CoordHubSpokePattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="coord_mesh",
                name="Coordination Mesh",
                category=PatternCategory.MESH,
                description="Fully connected agent mesh",
                use_cases=["P2P systems", "Distributed consensus", "Resilient systems"],
                required_mcps=["coordination"],
                docker_requirements={"memory": "1GB", "cpu": "1.0"},
                performance_profile={"latency": "medium", "throughput": "medium"}
            ),
            CoordMeshNetworkPattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="coord_event_bus",
                name="Coordination Event Bus",
                category=PatternCategory.EVENT_DRIVEN,
                description="Event-driven pub/sub coordination",
                use_cases=["Event streaming", "Microservices", "Real-time systems"],
                required_mcps=["coordination"],
                docker_requirements={"memory": "512MB", "cpu": "0.5"},
                performance_profile={"latency": "very low", "throughput": "very high"}
            ),
            CoordEventBusPattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="coord_consensus",
                name="Coordination Consensus",
                category=PatternCategory.CONSENSUS,
                description="Multi-agent consensus protocol",
                use_cases=["Distributed decisions", "Blockchain", "Voting systems"],
                required_mcps=["coordination"],
                docker_requirements={"memory": "512MB", "cpu": "0.75"},
                performance_profile={"latency": "high", "throughput": "low"}
            ),
            CoordConsensusPattern
        )
        
        # Workflow Patterns
        self.register_pattern(
            PatternDefinition(
                pattern_id="workflow_linear",
                name="Workflow Linear",
                category=PatternCategory.SEQUENTIAL,
                description="Sequential phase execution",
                use_cases=["Simple workflows", "Step-by-step processes", "Tutorials"],
                required_mcps=["workflow_state"],
                docker_requirements={"memory": "256MB", "cpu": "0.25"},
                performance_profile={"latency": "low", "throughput": "high"}
            ),
            WorkflowLinearPattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="workflow_parallel_phases",
                name="Workflow Parallel Phases",
                category=PatternCategory.PARALLEL,
                description="Parallel phase execution",
                use_cases=["Complex workflows", "CI/CD pipelines", "Parallel testing"],
                required_mcps=["workflow_state"],
                docker_requirements={"memory": "512MB", "cpu": "1.0"},
                performance_profile={"latency": "low", "throughput": "very high"}
            ),
            WorkflowParallelPhasesPattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="workflow_iterative",
                name="Workflow Iterative",
                category=PatternCategory.EVENT_DRIVEN,
                description="Iterative workflow with retry",
                use_cases=["Resilient workflows", "Self-healing", "Optimization loops"],
                required_mcps=["workflow_state"],
                docker_requirements={"memory": "512MB", "cpu": "0.5"},
                performance_profile={"latency": "variable", "throughput": "medium"}
            ),
            WorkflowIterativePattern
        )
        
        self.register_pattern(
            PatternDefinition(
                pattern_id="workflow_checkpoint",
                name="Workflow Checkpoint",
                category=PatternCategory.SEQUENTIAL,
                description="Workflow with checkpoints and recovery",
                use_cases=["Long-running workflows", "Fault tolerance", "State recovery"],
                required_mcps=["workflow_state"],
                docker_requirements={"memory": "512MB", "cpu": "0.5"},
                performance_profile={"latency": "medium", "throughput": "medium"}
            ),
            WorkflowCheckpointPattern
        )
    
    def register_pattern(self, definition: PatternDefinition, pattern_class: Type[BasePattern]):
        """Register a new pattern"""
        self.patterns[definition.pattern_id] = definition
        self.pattern_classes[definition.pattern_id] = pattern_class
        self.logger.info(f"Registered pattern: {definition.pattern_id}")
    
    def get_pattern(self, pattern_id: str) -> Optional[BasePattern]:
        """Get a pattern instance by ID"""
        if pattern_id not in self.patterns:
            return None
        
        definition = self.patterns[pattern_id]
        pattern_class = self.pattern_classes[pattern_id]
        return pattern_class(definition)
    
    def list_patterns(self, category: Optional[PatternCategory] = None) -> List[PatternDefinition]:
        """List all patterns, optionally filtered by category"""
        patterns = list(self.patterns.values())
        
        if category:
            patterns = [p for p in patterns if p.category == category]
        
        return patterns
    
    def find_patterns_for_use_case(self, use_case: str) -> List[PatternDefinition]:
        """Find patterns matching a use case"""
        matching = []
        
        for pattern in self.patterns.values():
            for uc in pattern.use_cases:
                if use_case.lower() in uc.lower():
                    matching.append(pattern)
                    break
        
        return matching

# Singleton instance
pattern_registry = MCPPatternRegistry()

# Register GitHub patterns if available
try:
    from mcp.patterns.github_patterns import register_github_patterns
    num_github = register_github_patterns(pattern_registry)
    logging.getLogger("PatternRegistry").info(f"Registered {num_github} GitHub patterns")
except ImportError:
    pass

if __name__ == "__main__":
    # Test pattern registry
    registry = MCPPatternRegistry()
    
    print(f"Registered {len(registry.patterns)} patterns")
    print("\nPatterns by category:")
    
    for category in PatternCategory:
        patterns = registry.list_patterns(category)
        print(f"  {category.value}: {len(patterns)} patterns")
        for p in patterns:
            print(f"    - {p.name} ({p.pattern_id})")