# LocalAgent MCP Servers Documentation

## Overview
LocalAgent now includes 7 independent MCP (Model Context Protocol) servers that provide advanced capabilities for AI orchestration, task management, and workflow execution. These servers are separate from the UnifiedWorkflow submodule and tailored specifically for the LocalAgent project.

## Available MCP Servers

### 1. HRM MCP (Hierarchical Reasoning Model)
**Location:** `/mcp/hrm_mcp.py`
**Purpose:** Provides hierarchical reasoning and decision-making capabilities

**Features:**
- 4-level reasoning hierarchy (Strategic → Tactical → Operational → Implementation)
- Confidence scoring for decisions
- Evidence-based reasoning
- Decision tree structure with automatic decomposition
- Persistent state across sessions

**CLI Commands:**
- `reason [query]` - Perform full hierarchical reasoning
- `strategic [query]` - Strategic level reasoning
- `tactical [query]` - Tactical level reasoning

### 2. Task MCP (Task Management)
**Location:** `/mcp/task_mcp.py`
**Purpose:** Comprehensive task tracking and management

**Features:**
- Task creation with priorities and dependencies
- Status tracking (todo, in_progress, blocked, completed, cancelled)
- Workload analysis and insights
- Timeline management with due dates
- Subtask support
- Markdown export capability

**CLI Commands:**
- `task create [title]` - Create a new task
- `task list` - List all active tasks
- `task complete [id]` - Mark task as completed

### 3. Coordination MCP (Agent Coordination)
**Location:** `/mcp/coordination_mcp.py`
**Purpose:** Multi-agent coordination and messaging

**Features:**
- Agent registration and heartbeat monitoring
- Message passing between agents
- Broadcast messaging
- Workflow stream management
- Shared scratch pad for data exchange
- Resource locking mechanism
- Topic-based pub/sub system

**CLI Commands:**
- `coord status` - Show coordination statistics

### 4. Workflow State MCP (Workflow Execution Tracking)
**Location:** `/mcp/workflow_state_mcp.py`
**Purpose:** Track and manage 12-phase workflow execution

**Features:**
- Complete workflow execution state management
- Phase tracking with evidence collection
- Progress monitoring
- Iteration support with context updates
- Success criteria validation
- Execution timeline and metrics

**CLI Commands:**
- `workflow status` - Show current workflow progress

### 5. Memory MCP (Persistent Storage)
**Location:** `/app/orchestration/mcp_integration.py`
**Purpose:** Persistent context and evidence storage

**Features:**
- Entity storage with retention policies
- Cross-session continuity
- Content search capabilities
- Automatic expiration handling

**CLI Commands:**
- `remember [key] [value]` - Store data
- `recall [key]` - Retrieve data

### 6. Redis MCP (Real-time Coordination)
**Location:** `/app/orchestration/mcp_integration.py`
**Purpose:** Real-time coordination between services

**Features:**
- Key-value storage
- Pub/sub messaging
- Real-time synchronization
- Distributed locking

### 7. Orchestration MCP
**Location:** `/app/orchestration/mcp_integration.py`
**Purpose:** Overall orchestration coordination

**Features:**
- Integration with Memory and Redis MCPs
- Workflow coordination
- Cross-MCP communication

## Integration with Enhanced CLI

All MCP servers are integrated into the enhanced CLI (`scripts/localagent_interactive_enhanced.py`).

### Initialization
```bash
# Run the enhanced CLI
clix

# Initialize all MCP features
init
```

### Using MCP Features

1. **Hierarchical Reasoning:**
```
reason Fix the authentication bug in the login system
strategic How should we approach the refactoring?
tactical What's the best way to implement caching?
```

2. **Task Management:**
```
task create Implement JWT authentication
task list
task complete task_abc123
```

3. **Coordination Monitoring:**
```
coord status
```

4. **Workflow Tracking:**
```
workflow status
```

5. **Memory Persistence:**
```
remember api_key sk-1234567890
recall api_key
```

## MCP Server States

All MCP servers maintain persistent state across sessions:
- HRM: `.hrm_state.json`
- Tasks: `.task_state.json`
- Coordination: `.coordination_state.json`
- Workflow: `.workflow_state.json`

## Architecture Benefits

### Independence from UnifiedWorkflow
- All MCPs are implemented independently in the root project
- No dependency on the UnifiedWorkflow submodule
- Tailored specifically for LocalAgent's needs

### Modular Design
- Each MCP server can be used independently
- Clean interfaces for integration
- Extensible for future capabilities

### Persistent State
- All servers maintain state across sessions
- Automatic state recovery on restart
- Evidence and history tracking

## Testing

Run the comprehensive test suite:
```bash
python test_all_mcps.py
```

This tests all MCP servers and verifies:
- Server initialization
- Core functionality
- State persistence
- Inter-MCP communication

## Future Enhancements

Potential additional MCPs to implement:
- **Calendar MCP** - Schedule management
- **Email MCP** - Communication automation
- **Security MCP** - Security validation and monitoring
- **Analytics MCP** - Performance and usage analytics
- **Documentation MCP** - Automated documentation generation

## Usage Examples

### Complete Workflow Example
```python
# Initialize all MCPs
from mcp.hrm_mcp import create_hrm_server
from mcp.task_mcp import create_task_server
from mcp.coordination_mcp import create_coordination_server
from mcp.workflow_state_mcp import create_workflow_state_server

# Create servers
hrm = await create_hrm_server()
tasks = await create_task_server()
coord = await create_coordination_server()
workflow = await create_workflow_state_server()

# Use HRM for reasoning
decision = await hrm.reason("Implement authentication system")

# Create tasks based on reasoning
task1 = await tasks.create_task("Design auth architecture", priority="high")
task2 = await tasks.create_task("Implement JWT tokens", priority="high")

# Register agents for coordination
await coord.register_agent("designer", "architecture")
await coord.register_agent("developer", "implementation")

# Track workflow execution
execution = await workflow.create_execution("Authentication Implementation")
await workflow.start_phase(execution.execution_id, "0A_prompt_engineering")
```

## Conclusion

The LocalAgent MCP server ecosystem provides a comprehensive foundation for AI-driven task management, reasoning, and workflow orchestration. These servers work together to enable sophisticated multi-agent collaboration while maintaining independence and modularity.