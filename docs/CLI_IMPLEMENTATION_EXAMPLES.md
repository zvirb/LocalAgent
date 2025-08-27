# LocalAgent CLI Implementation Examples

This document provides concrete examples of how to use the new LocalAgent CLI toolkit architecture.

## Basic Usage Examples

### 1. Initialize LocalAgent

```bash
# Interactive setup
localagent init

# Force reinitialize
localagent init --force

# Configuration with environment variables
export LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
export LOCALAGENT_OPENAI_API_KEY=sk-your-key-here
localagent config --validate
```

### 2. Provider Management

```bash
# List all providers
localagent providers --list

# Check provider health
localagent providers --health

# Focus on specific provider
localagent providers --provider ollama --health
```

### 3. Workflow Execution

```bash
# Basic workflow
localagent workflow "Fix authentication bug"

# Advanced workflow with options
localagent workflow "Implement user dashboard" \
  --provider openai \
  --parallel \
  --max-agents 15 \
  --format json \
  --save report.json

# Specific phases only
localagent workflow "Security audit" --phases "1,6,7"
```

### 4. Interactive Chat

```bash
# Start interactive session
localagent chat

# With specific provider and model
localagent chat --provider ollama --model llama3.1:latest

# Named session for history
localagent chat --session "debug-session"
```

### 5. Plugin Management

```bash
# List available plugins
localagent plugins --list

# Enable plugin
localagent plugins --enable workflow-automation

# Get plugin info
localagent plugins --info security-scanner
```

## Configuration Examples

### Environment Variables

```bash
# Provider Configuration
export LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
export LOCALAGENT_OPENAI_API_KEY=sk-...
export LOCALAGENT_GEMINI_API_KEY=AI...
export LOCALAGENT_PERPLEXITY_API_KEY=pplx-...

# System Configuration
export LOCALAGENT_DEFAULT_PROVIDER=ollama
export LOCALAGENT_MAX_PARALLEL_AGENTS=20
export LOCALAGENT_LOG_LEVEL=DEBUG

# Plugin Configuration
export LOCALAGENT_PLUGINS_ENABLED=workflow,export,monitoring
export LOCALAGENT_PLUGINS_AUTO_LOAD=true
```

### YAML Configuration File

```yaml
# ~/.localagent/config.yaml
providers:
  ollama:
    base_url: http://localhost:11434
    default_model: llama3.1:latest
    enabled: true
  
  openai:
    default_model: gpt-4
    enabled: true
    rate_limit: 10

orchestration:
  max_parallel_agents: 15
  max_workflow_iterations: 5
  enable_evidence_collection: true

plugins:
  enabled_plugins:
    - workflow-automation
    - security-scanner
    - performance-monitor
  auto_load_plugins: true
  allow_dev_plugins: false
```

## Plugin Development Examples

### 1. Simple Command Plugin

```python
# ~/.localagent/plugins/my_plugin.py
from app.cli.plugins.framework import CommandPlugin
import typer

class MyWorkflowPlugin(CommandPlugin):
    @property
    def name(self) -> str:
        return "my-workflow"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property 
    def description(self) -> str:
        return "Custom workflow automation"
    
    async def initialize(self, context) -> bool:
        return True
    
    def register_commands(self, app: typer.Typer) -> None:
        @app.command("custom-workflow")
        def custom_workflow(
            project: str,
            target: str = "development"
        ):
            """Execute custom workflow for project"""
            # Your custom workflow logic here
            pass
```

### 2. Provider Plugin

```python
from app.cli.plugins.framework import ProviderPlugin
from app.llm_providers.base_provider import BaseProvider

class CustomLLMProvider(BaseProvider):
    async def initialize(self) -> bool:
        # Initialize your custom provider
        return True
    
    async def list_models(self):
        # Return available models
        pass
    
    # Implement other required methods...

class CustomProviderPlugin(ProviderPlugin):
    @property
    def name(self) -> str:
        return "custom-llm"
    
    def get_provider_class(self):
        return CustomLLMProvider
```

### 3. Entry Points Registration

```toml
# setup.py or pyproject.toml
[project.entry-points."localagent.plugins.commands"]
my_workflow = "my_plugin:MyWorkflowPlugin"

[project.entry-points."localagent.plugins.providers"]  
custom_llm = "my_plugin:CustomProviderPlugin"
```

## Advanced Usage Patterns

### 1. Batch Operations with Configuration File

```yaml
# batch_config.yaml
agents:
  - agent_type: codebase-research-analyst
    description: "Analyze Python files"
    prompt: "Search Python files for security vulnerabilities"
  
  - agent_type: security-validator
    description: "Security validation"
    prompt: "Validate authentication mechanisms"

context:
  project_type: "web_application"
  security_focus: true
```

```bash
localagent parallel batch_config.yaml
```

### 2. Atomic File Operations in Scripts

```python
from app.cli.io.atomic import AtomicFileManager, FileTransaction

# Simple atomic write
await AtomicFileManager.write_json("config.json", config_data)

# Multiple operations in transaction
async with FileTransaction() as tx:
    tx.add_write("config.json", new_config, "json")
    tx.add_copy("backup.json", "config.backup.json")  
    tx.add_delete("old_config.json")
    await tx.commit()
```

### 3. Custom Error Handling

```python
from app.cli.error.exceptions import LocalAgentError, WorkflowError

class MyCustomPlugin(CommandPlugin):
    async def my_command(self):
        try:
            # Plugin logic here
            pass
        except Exception as e:
            raise WorkflowError(
                "Custom workflow failed", 
                phase="custom",
                recovery_suggestion="Check plugin configuration"
            ) from e
```

## Integration Examples

### 1. With CI/CD Pipelines

```yaml
# .github/workflows/localagent.yml
name: LocalAgent Workflow
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup LocalAgent
        run: |
          pip install localagent-cli
          localagent init --force
          
      - name: Run Analysis
        run: |
          localagent workflow "Analyze code changes" \
            --format json \
            --save analysis.json
            
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: analysis-results
          path: analysis.json
```

### 2. With Docker

```dockerfile
FROM python:3.11-slim

# Install LocalAgent
RUN pip install localagent-cli

# Configuration
ENV LOCALAGENT_OLLAMA_BASE_URL=http://ollama:11434
ENV LOCALAGENT_LOG_LEVEL=INFO

# Entry point
ENTRYPOINT ["localagent"]
CMD ["--help"]
```

### 3. Programmatic Usage

```python
import asyncio
from app.cli import create_app, ConfigurationManager

async def main():
    # Load configuration
    config_manager = ConfigurationManager()
    config = await config_manager.load_configuration()
    
    # Create CLI app programmatically
    app = create_app()
    
    # Execute workflow programmatically
    from app.orchestration.orchestration_integration import create_orchestrator
    
    orchestrator = await create_orchestrator()
    result = await orchestrator.execute_12_phase_workflow(
        "Implement user authentication"
    )
    
    print(f"Workflow result: {result['success']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Optimization

### 1. Configuration Caching

```python
# Hot-reload configuration without restart
await config_manager.hot_reload_config()

# Persistent session data
await context.persist_session()
```

### 2. Parallel Execution

```bash
# Maximum parallelization
localagent workflow "Large refactoring task" \
  --parallel \
  --max-agents 25

# Controlled parallelization
localagent workflow "Careful security audit" \
  --max-agents 5
```

### 3. Resource Management

```python
# Plugin cleanup
await plugin_manager.cleanup_all_plugins()

# Context cleanup
context.clear_shared_state()
```

## Troubleshooting Examples

### 1. Diagnostic Commands

```bash
# System health check
localagent health

# Configuration validation
localagent config --validate

# Provider connectivity
localagent providers --health
```

### 2. Debug Mode

```bash
# Enable debug output
localagent --debug workflow "Debug this issue"

# Verbose logging
LOCALAGENT_LOG_LEVEL=DEBUG localagent workflow "Detailed analysis"
```

### 3. Session Recovery

```bash
# View session history
localagent config --show | grep session

# Export session data
localagent config --export session_backup.yaml
```

## Testing Examples

### 1. Unit Tests

```python
import pytest
from app.cli.core.app import LocalAgentApp

@pytest.mark.asyncio
async def test_workflow_execution():
    app = LocalAgentApp()
    await app._initialize_app(None, "INFO", False, True)
    
    # Test workflow execution
    result = await app._cmd_workflow(
        "test prompt", None, None, True, 5, "json", None
    )
    
    assert result is not None
```

### 2. Plugin Tests

```python
def test_plugin_loading():
    plugin_manager = PluginManager(mock_context)
    await plugin_manager.discover_plugins()
    
    assert "my-plugin" in plugin_manager.discovered_plugins
    
    success = await plugin_manager.load_plugin("my-plugin")
    assert success
```

### 3. Integration Tests

```python
@pytest.mark.asyncio
async def test_full_workflow():
    # Test complete workflow execution
    cli = LocalAgentApp()
    result = await cli._cmd_workflow("integration test", None, None, False, 3, "json", None)
    
    assert result["success"] is True
    assert "workflow_id" in result
```

These examples demonstrate the comprehensive capabilities of the new LocalAgent CLI architecture and provide practical guidance for users, developers, and integrators.