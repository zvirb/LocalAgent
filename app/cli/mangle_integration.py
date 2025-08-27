"""
Google Mangle Integration for LocalAgent CLI

Provides deductive reasoning and pattern analysis capabilities for agent orchestration.
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class MangleQuery:
    """Represents a Mangle query for agent analysis"""
    name: str
    rules: str
    facts: List[Dict[str, Any]]
    query: str


@dataclass
class MangleResult:
    """Results from Mangle query execution"""
    success: bool
    output: str
    facts: List[Dict[str, Any]]
    error: Optional[str] = None


class MangleIntegration:
    """Integrates Google Mangle for agent decision-making and analysis"""
    
    def __init__(self, mangle_path: str = None):
        """Initialize Mangle integration
        
        Args:
            mangle_path: Path to Mangle interpreter (mg command)
        """
        self.mangle_path = mangle_path or self._find_mangle_interpreter()
        self.rules_dir = Path(__file__).parent / "mangle_rules"
        self.rules_dir.mkdir(exist_ok=True)
        
    def _find_mangle_interpreter(self) -> str:
        """Find the Mangle interpreter (mg) in the system"""
        # Check if mg is in PATH
        result = subprocess.run(["which", "mg"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        
        # Check common locations
        possible_paths = [
            Path.home() / "go" / "bin" / "mg",
            Path.home() / ".local" / "bin" / "mg",
            Path("/usr/local/bin/mg"),
            Path(__file__).parent.parent.parent / "libs" / "mangle" / "interpreter" / "mg" / "mg"
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        logger.warning("Mangle interpreter (mg) not found. Install with: go install github.com/google/mangle/interpreter/mg@latest")
        return "mg"  # Fallback to system command
    
    def create_agent_analysis_rules(self) -> str:
        """Create Mangle rules for agent performance analysis"""
        return """
        # Agent performance analysis rules
        
        # Define agent execution facts
        AgentExecution(agent_name string, task_id string, duration_ms int, success bool, timestamp int).
        
        # Define agent dependencies
        AgentDependency(agent string, depends_on string).
        
        # Define task complexity
        TaskComplexity(task_id string, complexity string).
        
        # Derive performance metrics
        SlowExecution(agent, task) :- 
            AgentExecution(agent, task, duration, true, _),
            duration > 5000.
        
        # Find bottleneck agents
        BottleneckAgent(agent) :-
            AgentExecution(agent, _, duration, _, _),
            duration > 10000.
        
        # Detect failed dependencies
        FailedDependency(agent, dependency) :-
            AgentDependency(agent, dependency),
            AgentExecution(dependency, _, _, false, _).
        
        # Recommend parallelization opportunities
        ParallelCandidate(agent1, agent2) :-
            AgentExecution(agent1, task1, _, true, time1),
            AgentExecution(agent2, task2, _, true, time2),
            agent1 != agent2,
            !AgentDependency(agent1, agent2),
            !AgentDependency(agent2, agent1),
            abs(time1 - time2) < 1000.
        
        # Identify frequently failing agents
        UnreliableAgent(agent) :-
            let N = count({task | AgentExecution(agent, task, _, false, _)}),
            let T = count({task | AgentExecution(agent, task, _, _, _)}),
            N > 0,
            T > 0,
            N * 100 / T > 20.  # More than 20% failure rate
        """
    
    def create_workflow_optimization_rules(self) -> str:
        """Create rules for workflow optimization"""
        return """
        # Workflow optimization rules
        
        # Define workflow phases
        WorkflowPhase(phase_id string, phase_name string, order int).
        PhaseExecution(phase_id string, start_time int, end_time int, success bool).
        
        # Define resource usage
        ResourceUsage(phase_id string, cpu_percent float, memory_mb int, io_ops int).
        
        # Identify slow phases
        SlowPhase(phase) :-
            PhaseExecution(phase, start, end, true),
            let duration = end - start,
            duration > 30000.  # More than 30 seconds
        
        # Find resource-intensive phases
        ResourceIntensive(phase) :-
            ResourceUsage(phase, cpu, memory, _),
            cpu > 80.0 | memory > 2048.
        
        # Detect phase dependencies that could be parallelized
        ParallelizablePhases(phase1, phase2) :-
            WorkflowPhase(phase1, _, order1),
            WorkflowPhase(phase2, _, order2),
            order2 = order1 + 1,
            !ResourceIntensive(phase1),
            !ResourceIntensive(phase2).
        
        # Recommend phase optimizations
        OptimizationCandidate(phase, reason) :-
            SlowPhase(phase),
            let reason = "slow_execution".
        
        OptimizationCandidate(phase, reason) :-
            ResourceIntensive(phase),
            let reason = "high_resource_usage".
        """
    
    def analyze_agent_performance(self, execution_data: List[Dict[str, Any]]) -> MangleResult:
        """Analyze agent performance using Mangle
        
        Args:
            execution_data: List of agent execution records
            
        Returns:
            MangleResult with analysis results
        """
        try:
            # Create temporary file with rules and facts
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mg', delete=False) as f:
                # Write rules
                f.write(self.create_agent_analysis_rules())
                f.write("\n\n")
                
                # Write facts
                for record in execution_data:
                    f.write(f"AgentExecution({self._format_value(record.get('agent_name'))}, "
                           f"{self._format_value(record.get('task_id'))}, "
                           f"{record.get('duration_ms', 0)}, "
                           f"{'true' if record.get('success') else 'false'}, "
                           f"{record.get('timestamp', 0)}).\n")
                
                # Write queries
                f.write("\n# Queries\n")
                f.write("?SlowExecution(agent, task)\n")
                f.write("?BottleneckAgent(agent)\n")
                f.write("?UnreliableAgent(agent)\n")
                f.write("?ParallelCandidate(agent1, agent2)\n")
                
                temp_file = f.name
            
            # Execute Mangle
            result = subprocess.run(
                [self.mangle_path, temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse results
            output_facts = self._parse_mangle_output(result.stdout)
            
            return MangleResult(
                success=result.returncode == 0,
                output=result.stdout,
                facts=output_facts,
                error=result.stderr if result.returncode != 0 else None
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze with Mangle: {e}")
            return MangleResult(
                success=False,
                output="",
                facts=[],
                error=str(e)
            )
        finally:
            # Cleanup temporary file
            if 'temp_file' in locals():
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    def analyze_workflow_optimization(self, workflow_data: Dict[str, Any]) -> MangleResult:
        """Analyze workflow for optimization opportunities
        
        Args:
            workflow_data: Workflow execution data
            
        Returns:
            MangleResult with optimization recommendations
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mg', delete=False) as f:
                # Write rules
                f.write(self.create_workflow_optimization_rules())
                f.write("\n\n")
                
                # Write workflow phase facts
                for phase in workflow_data.get('phases', []):
                    f.write(f"WorkflowPhase({self._format_value(phase['id'])}, "
                           f"{self._format_value(phase['name'])}, "
                           f"{phase['order']}).\n")
                
                # Write execution facts
                for execution in workflow_data.get('executions', []):
                    f.write(f"PhaseExecution({self._format_value(execution['phase_id'])}, "
                           f"{execution['start_time']}, "
                           f"{execution['end_time']}, "
                           f"{'true' if execution['success'] else 'false'}).\n")
                
                # Write resource usage facts
                for resource in workflow_data.get('resources', []):
                    f.write(f"ResourceUsage({self._format_value(resource['phase_id'])}, "
                           f"{resource['cpu_percent']}, "
                           f"{resource['memory_mb']}, "
                           f"{resource['io_ops']}).\n")
                
                # Write queries
                f.write("\n# Queries\n")
                f.write("?SlowPhase(phase)\n")
                f.write("?ResourceIntensive(phase)\n")
                f.write("?ParallelizablePhases(phase1, phase2)\n")
                f.write("?OptimizationCandidate(phase, reason)\n")
                
                temp_file = f.name
            
            # Execute Mangle
            result = subprocess.run(
                [self.mangle_path, temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output_facts = self._parse_mangle_output(result.stdout)
            
            return MangleResult(
                success=result.returncode == 0,
                output=result.stdout,
                facts=output_facts,
                error=result.stderr if result.returncode != 0 else None
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze workflow: {e}")
            return MangleResult(
                success=False,
                output="",
                facts=[],
                error=str(e)
            )
        finally:
            if 'temp_file' in locals():
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    def custom_query(self, rules: str, facts: List[str], queries: List[str]) -> MangleResult:
        """Execute custom Mangle query
        
        Args:
            rules: Mangle rules as string
            facts: List of fact strings
            queries: List of query strings
            
        Returns:
            MangleResult with query results
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mg', delete=False) as f:
                # Write rules
                f.write(rules)
                f.write("\n\n")
                
                # Write facts
                for fact in facts:
                    f.write(f"{fact}\n")
                
                # Write queries
                f.write("\n# Queries\n")
                for query in queries:
                    f.write(f"?{query}\n")
                
                temp_file = f.name
            
            # Execute Mangle
            result = subprocess.run(
                [self.mangle_path, temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output_facts = self._parse_mangle_output(result.stdout)
            
            return MangleResult(
                success=result.returncode == 0,
                output=result.stdout,
                facts=output_facts,
                error=result.stderr if result.returncode != 0 else None
            )
            
        except Exception as e:
            logger.error(f"Failed to execute custom query: {e}")
            return MangleResult(
                success=False,
                output="",
                facts=[],
                error=str(e)
            )
        finally:
            if 'temp_file' in locals():
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    def _format_value(self, value: Any) -> str:
        """Format value for Mangle syntax"""
        if isinstance(value, str):
            # Escape quotes and wrap in quotes
            return f'"{value.replace('"', '\\"')}"'
        return str(value)
    
    def _parse_mangle_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse Mangle output into structured facts"""
        facts = []
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '(' in line and ')' in line:
                # Extract fact name and arguments
                fact_name = line[:line.index('(')]
                args_str = line[line.index('(') + 1:line.rindex(')')]
                
                # Parse arguments (simplified parsing)
                args = []
                for arg in args_str.split(','):
                    arg = arg.strip()
                    if arg.startswith('"') and arg.endswith('"'):
                        args.append(arg[1:-1])
                    elif arg in ['true', 'false']:
                        args.append(arg == 'true')
                    else:
                        try:
                            if '.' in arg:
                                args.append(float(arg))
                            else:
                                args.append(int(arg))
                        except ValueError:
                            args.append(arg)
                
                facts.append({
                    'predicate': fact_name,
                    'arguments': args
                })
        
        return facts


class MangleAgentAnalyzer:
    """Analyzes agent interactions using Mangle deductive reasoning"""
    
    def __init__(self, mangle_integration: MangleIntegration):
        self.mangle = mangle_integration
        self.analysis_history = []
    
    def analyze_agent_chain(self, agents: List[str], execution_times: Dict[str, float]) -> Dict[str, Any]:
        """Analyze a chain of agent executions
        
        Args:
            agents: List of agent names in execution order
            execution_times: Dict of agent name to execution time
            
        Returns:
            Analysis results including optimization suggestions
        """
        # Prepare execution data
        execution_data = []
        timestamp = 0
        
        for i, agent in enumerate(agents):
            duration = int(execution_times.get(agent, 1000) * 1000)  # Convert to ms
            execution_data.append({
                'agent_name': agent,
                'task_id': f"task_{i}",
                'duration_ms': duration,
                'success': True,
                'timestamp': timestamp
            })
            timestamp += duration
        
        # Run Mangle analysis
        result = self.mangle.analyze_agent_performance(execution_data)
        
        # Extract insights
        insights = {
            'slow_agents': [],
            'bottlenecks': [],
            'parallel_opportunities': [],
            'optimization_score': 0.0
        }
        
        if result.success:
            for fact in result.facts:
                if fact['predicate'] == 'SlowExecution':
                    insights['slow_agents'].append(fact['arguments'][0])
                elif fact['predicate'] == 'BottleneckAgent':
                    insights['bottlenecks'].append(fact['arguments'][0])
                elif fact['predicate'] == 'ParallelCandidate':
                    insights['parallel_opportunities'].append({
                        'agent1': fact['arguments'][0],
                        'agent2': fact['arguments'][1]
                    })
            
            # Calculate optimization score
            total_time = sum(execution_times.values())
            parallel_savings = len(insights['parallel_opportunities']) * 0.3  # Assume 30% savings
            insights['optimization_score'] = min(parallel_savings, 0.5)  # Max 50% improvement
            
        self.analysis_history.append({
            'timestamp': timestamp,
            'agents': agents,
            'insights': insights
        })
        
        return insights
    
    def suggest_agent_composition(self, task_type: str, available_agents: List[str]) -> List[str]:
        """Suggest optimal agent composition for a task
        
        Args:
            task_type: Type of task to perform
            available_agents: List of available agent names
            
        Returns:
            Ordered list of suggested agents
        """
        # Define rules for agent selection based on task type
        rules = """
        # Agent capability rules
        AgentCapability(agent string, capability string).
        TaskRequirement(task string, requirement string).
        
        # Agent selection rules
        SuitableAgent(task, agent) :-
            TaskRequirement(task, req),
            AgentCapability(agent, req).
        
        # Prefer specialized agents
        PreferredAgent(task, agent) :-
            SuitableAgent(task, agent),
            AgentCapability(agent, "specialized").
        
        # Agent ordering based on dependencies
        AgentOrder(agent1, agent2) :-
            AgentCapability(agent1, "analysis"),
            AgentCapability(agent2, "implementation").
        """
        
        # Define facts based on known agent capabilities
        facts = []
        
        # Map common agent types to capabilities
        capability_map = {
            'research': ['analysis', 'discovery'],
            'security': ['validation', 'scanning'],
            'test': ['testing', 'validation'],
            'orchestrator': ['coordination', 'planning'],
            'monitor': ['monitoring', 'metrics'],
            'deploy': ['deployment', 'infrastructure']
        }
        
        for agent in available_agents:
            agent_lower = agent.lower()
            for keyword, capabilities in capability_map.items():
                if keyword in agent_lower:
                    for cap in capabilities:
                        facts.append(f'AgentCapability("{agent}", "{cap}").')
        
        # Add task requirements
        task_requirements = {
            'debug': ['analysis', 'testing'],
            'implement': ['planning', 'implementation', 'testing'],
            'deploy': ['validation', 'deployment', 'monitoring'],
            'optimize': ['analysis', 'metrics', 'testing'],
            'security': ['scanning', 'validation']
        }
        
        for req in task_requirements.get(task_type.lower(), ['analysis']):
            facts.append(f'TaskRequirement("{task_type}", "{req}").')
        
        # Execute query
        queries = [f'SuitableAgent("{task_type}", agent)']
        result = self.mangle.custom_query(rules, facts, queries)
        
        # Extract suggested agents
        suggested = []
        if result.success:
            for fact in result.facts:
                if fact['predicate'] == 'SuitableAgent':
                    agent = fact['arguments'][1]
                    if agent not in suggested:
                        suggested.append(agent)
        
        return suggested[:5]  # Return top 5 suggestions