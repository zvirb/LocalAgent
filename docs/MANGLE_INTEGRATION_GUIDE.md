# Google Mangle Integration Guide for LocalAgent CLI

## Overview

Google Mangle has been integrated into the LocalAgent CLI to provide deductive reasoning and pattern analysis capabilities for agent orchestration. Mangle is a deductive database programming language that extends Datalog, enabling sophisticated analysis of agent performance, workflow optimization, and orchestration patterns.

## Features

### 1. Agent Performance Analysis
- Identify slow-executing agents
- Detect bottleneck agents in workflows
- Find unreliable agents with high failure rates
- Discover parallelization opportunities
- Analyze resource consumption patterns

### 2. Workflow Optimization
- Detect slow phases in the 12-phase workflow
- Identify resource-intensive operations
- Suggest phase parallelization
- Recommend workflow restructuring
- Analyze critical paths

### 3. Deductive Reasoning for Agent Selection
- Automatically suggest optimal agent compositions
- Match agents to task requirements
- Identify agent dependencies
- Detect redundant agent executions

## Installation

### Prerequisites

1. **Install Go** (required for Mangle interpreter):
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install golang-go

   # macOS
   brew install go

   # Or download from https://go.dev/dl/
   ```

2. **Install Mangle Interpreter**:
   ```bash
   go install github.com/google/mangle/interpreter/mg@latest
   
   # Verify installation
   mg --version
   ```

3. **Alternative: Build from Submodule**:
   ```bash
   cd libs/mangle/interpreter/mg
   go build -o mg .
   
   # Add to PATH or copy to /usr/local/bin
   sudo cp mg /usr/local/bin/
   ```

## CLI Usage

### 1. Analyze Agent Performance

```bash
# Analyze agent execution logs
localagent mangle analyze-performance execution_log.json

# Save results to file
localagent mangle analyze-performance execution_log.json --output results.json
```

### 2. Optimize Workflow

```bash
# Analyze workflow for optimization opportunities
localagent mangle optimize-workflow workflow_data.json

# Options
localagent mangle optimize-workflow workflow_data.json \
  --suggest-parallelization \
  --identify-bottlenecks
```

### 3. Suggest Agent Composition

```bash
# Get agent suggestions for a task type
localagent mangle suggest-agents debug
localagent mangle suggest-agents implement
localagent mangle suggest-agents deploy

# List available agents
localagent mangle suggest-agents debug --list
```

### 4. Custom Mangle Queries

```bash
# Execute custom Mangle rules
localagent mangle custom-query rules.mg \
  --facts facts.json \
  --query "SlowAgent(agent, duration)" \
  --output results.json
```

## Python API Usage

```python
from app.cli.mangle_integration import MangleIntegration, MangleAgentAnalyzer

# Initialize Mangle integration
mangle = MangleIntegration()

# Analyze agent performance
execution_data = [
    {
        'agent_name': 'research-analyst',
        'task_id': 'task_1',
        'duration_ms': 5500,
        'success': True,
        'timestamp': 1000
    },
    # ... more execution records
]

result = mangle.analyze_agent_performance(execution_data)

if result.success:
    for fact in result.facts:
        print(f"{fact['predicate']}: {fact['arguments']}")

# Use agent analyzer for higher-level insights
analyzer = MangleAgentAnalyzer(mangle)

agents = ['research', 'planning', 'implementation', 'testing']
execution_times = {
    'research': 2.5,
    'planning': 1.8,
    'implementation': 5.2,
    'testing': 3.1
}

insights = analyzer.analyze_agent_chain(agents, execution_times)
print(f"Optimization potential: {insights['optimization_score']:.1%}")
```

## Mangle Rules Structure

### Agent Performance Rules (`agent_orchestration.mg`)

```datalog
# Define agent execution facts
AgentExecution(agent_name string, task_id string, duration_ms int, success bool, timestamp int).

# Identify slow agents
SlowExecution(agent, task) :- 
    AgentExecution(agent, task, duration, true),
    duration > 5000.

# Find bottlenecks
BottleneckAgent(agent) :-
    AgentExecution(agent, _, duration, _),
    duration > 10000.

# Detect parallelization opportunities
ParallelCandidate(agent1, agent2) :-
    AgentExecution(agent1, task1, _, true, time1),
    AgentExecution(agent2, task2, _, true, time2),
    agent1 != agent2,
    !AgentDependency(agent1, agent2),
    !AgentDependency(agent2, agent1).
```

### Custom Rule Development

1. Create a `.mg` file with your rules
2. Define facts (data structures)
3. Write deductive rules using Datalog syntax
4. Add queries to extract insights
5. Execute using the CLI or Python API

## Integration with UnifiedWorkflow

The Mangle integration enhances the 12-phase UnifiedWorkflow by:

### Phase 1: Research & Discovery
- Analyze historical agent performance
- Identify optimal agent combinations
- Predict execution times

### Phase 2: Strategic Planning
- Use deductive reasoning for workflow design
- Identify parallelization opportunities
- Optimize resource allocation

### Phase 4: Parallel Execution
- Real-time bottleneck detection
- Dynamic agent reallocation
- Performance monitoring

### Phase 7: Audit & Learning
- Comprehensive performance analysis
- Pattern recognition in failures
- Workflow optimization recommendations

## Example: Workflow Optimization

```python
# Prepare workflow data
workflow_data = {
    'phases': [
        {'id': 'phase_0', 'name': 'Prompt Engineering', 'order': 0},
        {'id': 'phase_1', 'name': 'Research', 'order': 1},
        # ... more phases
    ],
    'executions': [
        {'phase_id': 'phase_0', 'start_time': 0, 'end_time': 5000, 'success': True},
        # ... more executions
    ],
    'resources': [
        {'phase_id': 'phase_1', 'cpu_percent': 85.5, 'memory_mb': 2500, 'io_ops': 1000},
        # ... more resource data
    ]
}

# Analyze with Mangle
result = mangle.analyze_workflow_optimization(workflow_data)

# Extract insights
for fact in result.facts:
    if fact['predicate'] == 'OptimizationCandidate':
        phase, reason = fact['arguments']
        print(f"Optimize {phase}: {reason}")
```

## Testing

Run the test suite to verify Mangle integration:

```bash
# Simple test without full CLI dependencies
python test_mangle_simple.py

# Full integration test (requires CLI setup)
python test_mangle_integration.py
```

## Troubleshooting

### Mangle interpreter not found
- Ensure Go is installed: `go version`
- Install Mangle: `go install github.com/google/mangle/interpreter/mg@latest`
- Check PATH: `echo $PATH` should include `~/go/bin`

### Query timeout
- Simplify rules to reduce complexity
- Limit the number of facts being processed
- Increase timeout in Python code

### No results from queries
- Check fact syntax matches rule expectations
- Verify predicate names are consistent
- Use simpler queries for debugging

## Advanced Usage

### Creating Complex Analysis Rules

```datalog
# Multi-level dependency analysis
TransitiveDependency(a, c) :-
    AgentDependency(a, b),
    AgentDependency(b, c).

# Cascade failure prediction
CascadeRisk(agent, risk_level) :-
    let dependents = count({d | TransitiveDependency(d, agent)}),
    AgentReliability(agent, reliability),
    reliability < 80,
    let risk_level = dependents * (100 - reliability) / 100.
```

### Integration with LLM Providers

The Mangle analysis can be used to optimize LLM provider selection:

```python
# Analyze provider performance
provider_data = [
    {'agent_name': 'ollama', 'task_id': 'inference_1', 'duration_ms': 2000, ...},
    {'agent_name': 'perplexity', 'task_id': 'search_1', 'duration_ms': 1500, ...},
]

result = mangle.analyze_agent_performance(provider_data)
# Use insights to route requests to optimal providers
```

## Contributing

To contribute Mangle rules or integration improvements:

1. Add rules to `app/cli/mangle_rules/`
2. Update integration in `app/cli/mangle_integration.py`
3. Add tests to verify functionality
4. Submit PR with examples and documentation

## References

- [Google Mangle GitHub](https://github.com/google/mangle)
- [Mangle Documentation](https://github.com/google/mangle/blob/main/docs/README.md)
- [Datalog Tutorial](https://docs.racket-lang.org/datalog/)
- [UnifiedWorkflow Integration](../UnifiedWorkflow/docs/GOOGLE_MANGLE_IMPLEMENTATION.md)