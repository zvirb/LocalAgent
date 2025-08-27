# Agent Orchestration Analysis Rules for LocalAgent CLI
# Uses Google Mangle deductive database for reasoning about agent interactions

# ============================================================================
# CORE AGENT FACTS
# ============================================================================

# Agent definitions with capabilities
Agent(name string, type string, capability string).
AgentVersion(name string, version string).

# Agent execution records
AgentExecution(
    execution_id string,
    agent_name string,
    phase int,
    start_time int,
    end_time int,
    success bool,
    error_msg string
).

# Agent dependencies and interactions
AgentDependency(agent string, depends_on string, dependency_type string).
AgentCommunication(from_agent string, to_agent string, message_type string, timestamp int).

# Resource consumption
ResourceUsage(
    agent string,
    execution_id string,
    cpu_percent float,
    memory_mb int,
    network_kb int
).

# ============================================================================
# WORKFLOW FACTS
# ============================================================================

# Workflow phases from UnifiedWorkflow
WorkflowPhase(phase_id int, phase_name string, parallel bool).
PhaseAgent(phase_id int, agent_name string).

# Phase transitions
PhaseTransition(from_phase int, to_phase int, condition string).

# ============================================================================
# PERFORMANCE ANALYSIS RULES
# ============================================================================

# Calculate execution duration
ExecutionDuration(execution_id, duration) :-
    AgentExecution(execution_id, _, _, start, end, _, _),
    let duration = end - start.

# Identify slow agents (>5 seconds)
SlowAgent(agent, avg_duration) :-
    let executions = count({id | AgentExecution(id, agent, _, _, _, _, _)}),
    let total_duration = sum({duration | 
        AgentExecution(id, agent, _, start, end, _, _),
        let duration = end - start
    }),
    executions > 0,
    let avg_duration = total_duration / executions,
    avg_duration > 5000.

# Find bottleneck agents blocking parallel execution
BottleneckAgent(agent, phase) :-
    WorkflowPhase(phase, _, true),  # Parallel phase
    PhaseAgent(phase, agent),
    AgentExecution(_, agent, phase, start, end, _, _),
    let duration = end - start,
    # Check if this agent takes longer than others in same phase
    duration > max({other_duration | 
        PhaseAgent(phase, other_agent),
        other_agent != agent,
        AgentExecution(_, other_agent, phase, other_start, other_end, _, _),
        let other_duration = other_end - other_start
    }).

# Detect cascading failures
CascadingFailure(root_agent, dependent_agent) :-
    AgentExecution(_, root_agent, _, _, _, false, _),
    AgentDependency(dependent_agent, root_agent, _),
    AgentExecution(_, dependent_agent, _, _, _, false, _).

# ============================================================================
# OPTIMIZATION RULES
# ============================================================================

# Identify parallelization opportunities
ParallelizationOpportunity(agent1, agent2) :-
    AgentExecution(_, agent1, phase1, _, _, true, _),
    AgentExecution(_, agent2, phase2, _, _, true, _),
    phase2 = phase1 + 1,  # Sequential phases
    !AgentDependency(agent2, agent1, _),
    !AgentDependency(agent1, agent2, _),
    !AgentCommunication(agent1, agent2, _, _),
    !AgentCommunication(agent2, agent1, _, _).

# Recommend agent consolidation (agents with minimal interaction)
ConsolidationCandidate(agent1, agent2) :-
    Agent(agent1, type1, _),
    Agent(agent2, type2, _),
    type1 = type2,  # Same type of agent
    let comm_count = count({msg | 
        AgentCommunication(agent1, agent2, msg, _) |
        AgentCommunication(agent2, agent1, msg, _)
    }),
    comm_count < 3.  # Minimal communication

# Identify redundant agent executions
RedundantExecution(agent, phase) :-
    let exec_count = count({id | AgentExecution(id, agent, phase, _, _, true, _)}),
    exec_count > 1,  # Multiple successful executions
    # No state change between executions
    !exists({comm | 
        AgentExecution(id1, agent, phase, _, end1, true, _),
        AgentExecution(id2, agent, phase, start2, _, true, _),
        start2 > end1,
        AgentCommunication(_, agent, comm, ts),
        ts > end1,
        ts < start2
    }).

# ============================================================================
# RESOURCE OPTIMIZATION RULES
# ============================================================================

# High resource consumption agents
ResourceIntensiveAgent(agent, avg_cpu, avg_memory) :-
    let exec_count = count({id | ResourceUsage(agent, id, _, _, _)}),
    let total_cpu = sum({cpu | ResourceUsage(agent, _, cpu, _, _)}),
    let total_memory = sum({mem | ResourceUsage(agent, _, _, mem, _)}),
    exec_count > 0,
    let avg_cpu = total_cpu / exec_count,
    let avg_memory = total_memory / exec_count,
    avg_cpu > 70.0 | avg_memory > 1024.

# Resource contention detection
ResourceContention(agent1, agent2, resource_type) :-
    AgentExecution(id1, agent1, _, start1, end1, _, _),
    AgentExecution(id2, agent2, _, start2, end2, _, _),
    agent1 != agent2,
    # Overlapping execution times
    start1 < end2,
    start2 < end1,
    # High resource usage
    ResourceUsage(agent1, id1, cpu1, mem1, _),
    ResourceUsage(agent2, id2, cpu2, mem2, _),
    (cpu1 + cpu2 > 150.0 & let resource_type = "cpu") |
    (mem1 + mem2 > 3072 & let resource_type = "memory").

# ============================================================================
# RELIABILITY ANALYSIS
# ============================================================================

# Calculate agent reliability score
AgentReliability(agent, success_rate) :-
    let total = count({id | AgentExecution(id, agent, _, _, _, _, _)}),
    let successes = count({id | AgentExecution(id, agent, _, _, _, true, _)}),
    total > 0,
    let success_rate = successes * 100 / total.

# Identify unreliable agents
UnreliableAgent(agent) :-
    AgentReliability(agent, rate),
    rate < 80.  # Less than 80% success rate

# Detect error patterns
ErrorPattern(agent, error_type, frequency) :-
    let frequency = count({id | 
        AgentExecution(id, agent, _, _, _, false, error),
        contains(error, error_type)
    }),
    frequency > 2.

# ============================================================================
# WORKFLOW OPTIMIZATION RECOMMENDATIONS
# ============================================================================

# Suggest phase reordering for better parallelization
PhaseReorderSuggestion(phase1, phase2) :-
    PhaseTransition(phase1, phase2, _),
    !WorkflowPhase(phase1, _, true),  # phase1 not parallel
    WorkflowPhase(phase2, _, true),    # phase2 is parallel
    # Check if agents in phase1 could run in parallel
    let agents = count({agent | PhaseAgent(phase1, agent)}),
    agents > 1,
    # No strong dependencies between agents
    !exists({a1, a2 | 
        PhaseAgent(phase1, a1),
        PhaseAgent(phase1, a2),
        a1 != a2,
        AgentDependency(a1, a2, "strong")
    }).

# Identify critical path through workflow
CriticalPath(phase, total_duration) :-
    WorkflowPhase(phase, _, _),
    let total_duration = sum({duration |
        PhaseAgent(phase, agent),
        AgentExecution(_, agent, phase, start, end, _, _),
        let duration = end - start
    }).

# ============================================================================
# QUERIES FOR ANALYSIS
# ============================================================================

# Performance queries
?SlowAgent(agent, duration)
?BottleneckAgent(agent, phase)
?ResourceIntensiveAgent(agent, cpu, memory)

# Optimization queries
?ParallelizationOpportunity(agent1, agent2)
?ConsolidationCandidate(agent1, agent2)
?RedundantExecution(agent, phase)

# Reliability queries
?UnreliableAgent(agent)
?CascadingFailure(root, dependent)
?ErrorPattern(agent, error, freq)

# Workflow optimization
?PhaseReorderSuggestion(phase1, phase2)
?CriticalPath(phase, duration)
?ResourceContention(agent1, agent2, resource)