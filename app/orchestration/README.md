# LocalAgent + UnifiedWorkflow Orchestration Integration

Complete integration system connecting LocalAgent's LLM provider architecture with UnifiedWorkflow's 12-phase agent orchestration system.

## Overview

This integration stream delivers a complete orchestration system that combines:

- **LocalAgent**: Multi-provider LLM system with fallback capabilities
- **UnifiedWorkflow**: 12-phase agent orchestration with evidence collection
- **MCP Integration**: Memory and Redis servers for context and coordination
- **CLI Interface**: Command-line access to all orchestration capabilities

## Components

### 1. Agent Provider Adapter (`agent_adapter.py`)
- Bridges LocalAgent providers with UnifiedWorkflow agents
- Handles agent request/response standardization
- Provides parallel execution capabilities
- Manages provider health and statistics

**Key Features**:
- Automatic agent registry loading from UnifiedWorkflow
- Provider fallback and health checking
- Parallel agent execution with semaphore limiting
- Evidence extraction and success assessment

### 2. Workflow Engine (`workflow_engine.py`)
- Implements complete 12-phase workflow execution
- Manages phase transitions and dependencies
- Handles evidence collection and validation
- Supports multi-stream parallel orchestration

**Key Features**:
- Sequential and parallel phase execution
- Multi-stream coordination (Phase 5 style)
- Context package integration
- Phase result tracking and evidence collection

### 3. MCP Integration (`mcp_integration.py`)
- Memory MCP for persistent context storage
- Redis MCP for real-time agent coordination
- Orchestration MCP combining both systems
- Context compression and token management

**Key Features**:
- Entity storage with retention policies
- Agent coordination through Redis
- Timeline tracking and event logging
- Health monitoring for all MCP servers

### 4. Context Manager (`context_manager.py`)
- Intelligent context package management
- Token counting and compression
- Cross-session context continuity
- Package type-specific compression strategies

**Key Features**:
- Automatic token compression to limits
- Type-aware compression strategies
- Package expiration and cleanup
- Workflow context summarization

### 5. Orchestration Integration (`orchestration_integration.py`)
- Main orchestrator class combining all components
- CLI command implementations
- Workflow execution and monitoring
- System health and status reporting

**Key Features**:
- Complete 12-phase workflow execution
- Single and parallel agent execution
- System health monitoring
- CLI command interface

### 6. CLI Interface (`cli_interface.py`)
- Command-line interface for all operations
- Interactive workflow execution
- Agent management and monitoring
- System administration commands

**Available Commands**:
- `workflow` - Execute 12-phase workflow
- `agent` - Execute single agent
- `parallel` - Execute agents in parallel
- `status` - Get workflow status
- `health` - System health check
- `agents` - List available agents
- `phases` - List workflow phases

## Installation

1. **Copy integration files to LocalAgent**:
```bash
# Copy to app/orchestration/
mkdir -p app/orchestration
cp /tmp/localagent-stream-integration/* app/orchestration/
```

2. **Install dependencies**:
```bash
pip install aioredis pyyaml
```

3. **Configure system**:
```yaml
# config/orchestration.yaml
orchestration:
  max_parallel_agents: 10
  enable_evidence_collection: true

providers:
  ollama:
    base_url: http://localhost:11434
    default_model: llama3.1:latest

mcp:
  redis:
    redis_url: redis://localhost:6379
```

## Usage

### CLI Usage

```bash
# Initialize system
python -m app.orchestration.cli_interface init --provider-config config/orchestration.yaml

# Execute 12-phase workflow
python -m app.orchestration.cli_interface workflow "Fix authentication system"

# Execute single agent
python -m app.orchestration.cli_interface agent codebase-research-analyst "Analyze authentication code"

# Check system health
python -m app.orchestration.cli_interface health

# List available agents
python -m app.orchestration.cli_interface agents
```

#### AGENTS.md Support

The CLI automatically searches for `AGENTS.md` files in the current directory and its parents. Any instructions found are combined and injected into the `agents_md` field of the context sent to agents and workflows.

### Programmatic Usage

```python
from app.orchestration import LocalAgentOrchestrator, create_orchestrator
from app.llm_providers import ProviderManager

# Create and initialize orchestrator
provider_manager = ProviderManager(config)
await provider_manager.initialize_providers()

orchestrator = await create_orchestrator('config/orchestration.yaml')
await orchestrator.initialize(provider_manager)

# Execute workflow
result = await orchestrator.execute_12_phase_workflow(
    user_prompt="Implement user authentication",
    context={'priority': 'high'}
)

# Check results
if result['success']:
    print(f"Workflow completed: {result['execution_summary']['completed_phases']} phases")
else:
    print(f"Workflow failed: {result.get('error')}")
```

### Configuration

Create `config/orchestration.yaml`:

```yaml
orchestration:
  max_parallel_agents: 10
  max_workflow_iterations: 3
  enable_evidence_collection: true
  enable_cross_session_continuity: true

context:
  strategic_context_tokens: 3000
  technical_context_tokens: 4000
  default_context_tokens: 4000

mcp:
  redis:
    redis_url: redis://localhost:6379
  memory: {}

providers:
  ollama:
    base_url: http://localhost:11434
    default_model: llama3.1:latest
    timeout: 120
```

## Integration with UnifiedWorkflow

The system automatically discovers and loads agents from:
- `UnifiedWorkflow/agents/*.md`
- Requires proper frontmatter format:

```yaml
---
name: agent-name
description: Specialized agent for handling [purpose] tasks.
---
```

## Evidence Collection

The system collects evidence throughout execution:

- **Agent Evidence**: File paths, commands executed, validation results
- **Phase Evidence**: Execution summaries, timing data, success metrics  
- **Workflow Evidence**: Complete execution reports, context packages
- **System Evidence**: Health checks, provider statistics, MCP status

Evidence is stored in:
- Memory MCP for persistent storage
- Redis MCP for real-time coordination
- Context packages for cross-phase continuity

## Parallel Execution

The system supports multiple levels of parallelization:

1. **Phase-Level**: Phases with `execution: parallel`
2. **Agent-Level**: Multiple agents within a phase
3. **Stream-Level**: Multi-stream orchestration (Phase 5)
4. **Provider-Level**: Multiple LLM providers with fallback

## Context Management

Context packages are automatically managed:

- **Token Limits**: Per-package-type token limits enforced
- **Compression**: Intelligent compression preserving essential info
- **Expiration**: Automatic cleanup of expired contexts
- **Cross-Session**: Context continuity across workflow executions

## MCP Server Integration

### Memory MCP
- Stores agent outputs, context packages, evidence
- Retention policies by entity type
- Cross-session continuity support
- Search and retrieval capabilities

### Redis MCP  
- Real-time agent coordination
- Shared scratch pad for streams
- Event timeline tracking
- Workflow state management

## Testing

Run integration tests:

```bash
python -m app.orchestration.integration_test
```

Tests validate:
- Agent adapter functionality
- MCP integration (Memory + Redis)
- Context manager compression
- Workflow engine execution
- Complete orchestration integration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LocalAgent CLI                           │
├─────────────────────────────────────────────────────────────┤
│                 Orchestration Integration                   │
├─────────────────────────────────────────────────────────────┤
│  Agent Adapter  │  Workflow Engine  │   Context Manager    │
├─────────────────────────────────────────────────────────────┤
│                    MCP Integration                          │
│  Memory MCP     │     Redis MCP     │  Orchestration MCP   │
├─────────────────────────────────────────────────────────────┤
│              LocalAgent Provider System                     │
│   Ollama        │    OpenAI        │     Gemini           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  UnifiedWorkflow                            │
│              12-Phase Agent System                          │
│   Phase 0-12    │   Agent Registry  │   Evidence System   │
└─────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

- **Agent Execution**: 2-5s per agent (depending on provider)
- **Context Compression**: Sub-second for 4000 token packages
- **Memory MCP**: In-memory, instant access
- **Redis MCP**: Network-dependent, typically <10ms
- **Parallel Agents**: Limited by `max_parallel_agents` setting

## Error Handling

The system provides robust error handling:

- **Provider Fallback**: Automatic failover between LLM providers
- **Graceful Degradation**: Continue with available components
- **Retry Logic**: Configurable retry for transient failures
- **Evidence Preservation**: Error states captured in evidence
- **Health Monitoring**: Continuous component health tracking

## Deployment

For production deployment:

1. **Redis Server**: Required for multi-agent coordination
2. **LLM Providers**: Configure multiple providers for reliability
3. **Resource Limits**: Set appropriate memory and CPU limits
4. **Monitoring**: Enable health checks and evidence collection
5. **Persistence**: Configure MCP retention policies

## Security Considerations

- **Token Management**: Secure storage of API keys
- **Context Isolation**: Agent contexts properly isolated
- **Evidence Sanitization**: Sensitive data filtering in evidence
- **Provider Security**: Secure communication with LLM providers
- **Redis Security**: Authentication and encryption for Redis

## Contributing

To extend the system:

1. **New Agent Types**: Add to UnifiedWorkflow/agents/
2. **Custom Compression**: Extend ContextCompressor strategies
3. **Provider Support**: Add to LocalAgent provider system
4. **MCP Servers**: Implement additional MCP integrations
5. **CLI Commands**: Add commands to cli_interface.py

## License

Same as parent LocalAgent and UnifiedWorkflow projects.

---

**Integration Stream Deliverables**: ✅ Complete
- Agent Provider Adapter Bridge: ✅ 
- 12-Phase Workflow Engine: ✅
- MCP Integration (Memory + Redis): ✅
- Context Package Management: ✅
- CLI Interface: ✅
- Integration Tests: ✅
- Documentation: ✅