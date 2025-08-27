# CLI Integration Architecture - Implementation Guide

## Overview

This guide documents the complete CLI integration architecture for the LocalAgent system, including plugin framework enhancements, orchestration bridge improvements, and dynamic command registration.

## Components Implemented

### 1. Enhanced Plugin Discovery System (`enhanced_plugin_discovery.py`)

**Key Features:**
- Entry point discovery across multiple plugin groups
- Dynamic plugin loading and registration
- Plugin metadata extraction and caching
- Manifest generation for discovered plugins

**Integration Points:**
- Extends existing `app/cli/plugins/framework.py`
- Works with setuptools entry points
- Integrates with CLI configuration system

**Usage:**
```python
from enhanced_plugin_discovery import EntryPointDiscoveryEngine, DynamicPluginLoader

# Discover all plugins
engine = EntryPointDiscoveryEngine()
entries = await engine.discover_all_entry_points()

# Load specific plugins
loader = DynamicPluginLoader()
for entry in entries:
    await loader.load_plugin_from_entry(entry)
```

### 2. Built-in Plugins (`builtin_plugins.py`)

**Implemented Plugins:**
- **SystemInfoPlugin**: System information and health diagnostics
- **WorkflowDebugPlugin**: Workflow debugging and introspection tools  
- **ConfigurationPlugin**: Advanced configuration management

**Features:**
- Rich console output with tables and panels
- Comprehensive system health checks
- Configuration export and template generation
- Workflow phase debugging

**Integration:**
```python
from builtin_plugins import register_builtin_plugins

# Register all built-in plugins
registered_count = await register_builtin_plugins(plugin_manager)
```

### 3. Enhanced Orchestration Bridge (`enhanced_orchestration_bridge.py`)

**Key Enhancements:**
- Real-time workflow monitoring with Rich displays
- 12-phase workflow integration
- Agent status tracking
- Phase-by-phase execution control
- Workflow cancellation and reporting

**Features:**
- Live progress display during workflow execution
- Comprehensive phase definitions for all 12 phases
- Agent callback system for custom monitoring
- Export capabilities for workflow reports

**Integration:**
```python
from enhanced_orchestration_bridge import create_enhanced_orchestrator_bridge

bridge = await create_enhanced_orchestrator_bridge(context, display_manager)
result = await bridge.execute_12_phase_workflow(prompt, execution_context)
```

### 4. Dynamic Command Registration (`dynamic_command_registration.py`)

**Core Features:**
- Runtime command discovery and registration
- Command grouping and organization
- Parameter extraction from function signatures
- Command manifest generation
- Decorator-based command definition

**Command Types:**
- Standard commands
- Workflow commands (with phase integration)
- Agent commands (with agent type integration)
- Provider commands (with provider integration)

**Usage:**
```python
from dynamic_command_registration import command, workflow_command, agent_command

@workflow_command(name="status", phase="all")
def workflow_status():
    console.print("Workflow status: Active")

@agent_command(name="list", agent_type="all")
def list_agents():
    console.print("Available agents: 5")
```

### 5. Enhanced Provider Integration (`enhanced_provider_integration.py`)

**Advanced Features:**
- Real-time provider health monitoring
- Performance metrics collection
- Automatic failover capabilities
- Model discovery and management
- Provider testing and configuration

**Monitoring Capabilities:**
- Background health checks
- Response time tracking
- Success rate calculation
- Error count monitoring
- Rich status displays

**Integration:**
```python
from enhanced_provider_integration import create_cli_provider_manager

cli_manager = await create_cli_provider_manager(config, provider_manager_instance)
await cli_manager.start_monitoring()
```

## Integration Steps

### Step 1: Update Plugin Framework

1. **Extend existing plugin framework:**
   ```bash
   # Copy enhanced discovery to main project
   cp /tmp/integration-stream/enhanced_plugin_discovery.py app/cli/plugins/
   ```

2. **Update `framework.py` to use enhanced discovery:**
   ```python
   from .enhanced_plugin_discovery import EntryPointDiscoveryEngine
   
   # In PluginManager.__init__
   self.discovery_engine = EntryPointDiscoveryEngine()
   ```

### Step 2: Install Built-in Plugins

1. **Create builtin plugin directory:**
   ```bash
   mkdir -p app/cli/plugins/builtin/
   cp /tmp/integration-stream/builtin_plugins.py app/cli/plugins/builtin/
   ```

2. **Register built-ins in main app:**
   ```python
   from .plugins.builtin.builtin_plugins import register_builtin_plugins
   
   # In LocalAgentApp._initialize_app
   await register_builtin_plugins(self.plugin_manager)
   ```

### Step 3: Enhance Orchestration Bridge

1. **Replace existing orchestration integration:**
   ```bash
   cp /tmp/integration-stream/enhanced_orchestration_bridge.py app/cli/integration/
   ```

2. **Update main app to use enhanced bridge:**
   ```python
   from .integration.enhanced_orchestration_bridge import create_enhanced_orchestrator_bridge
   
   # In workflow command
   bridge = await create_enhanced_orchestrator_bridge(self.context, self.display_manager)
   ```

### Step 4: Implement Dynamic Commands

1. **Add dynamic command system:**
   ```bash
   cp /tmp/integration-stream/dynamic_command_registration.py app/cli/core/
   ```

2. **Update main app initialization:**
   ```python
   from .core.dynamic_command_registration import DynamicCommandRegistry, AutoCommandDiscovery
   
   # In LocalAgentApp.__init__
   self.command_registry = DynamicCommandRegistry()
   self.command_discovery = AutoCommandDiscovery(self.command_registry)
   ```

### Step 5: Enhance Provider Integration

1. **Add enhanced provider manager:**
   ```bash
   cp /tmp/integration-stream/enhanced_provider_integration.py app/cli/integration/
   ```

2. **Integrate with main provider system:**
   ```python
   from .integration.enhanced_provider_integration import create_cli_provider_manager
   
   # In provider commands
   self.cli_provider_manager = await create_cli_provider_manager(config, provider_manager)
   ```

## Configuration Updates

### Plugin Configuration

Add to `config.yaml`:
```yaml
plugins:
  enabled: true
  auto_load: true
  plugin_directories:
    - "~/.localagent/plugins"
  entry_point_groups:
    - "localagent.plugins.commands"
    - "localagent.plugins.providers" 
    - "localagent.plugins.ui"
    - "localagent.plugins.workflow"
  enabled_plugins:
    - "system-info"
    - "workflow-debug" 
    - "config-manager"
```

### Provider Configuration

Add monitoring settings:
```yaml
providers:
  monitoring:
    interval: 30
    auto_failover: true
    health_check_timeout: 10
  preferred_providers:
    - "ollama"
    - "openai"
```

### Orchestration Configuration

Add workflow monitoring:
```yaml
orchestration:
  monitoring:
    realtime_display: true
    progress_refresh_rate: 4
    save_reports: true
  phases:
    max_parallel_agents: 10
    enable_phase_callbacks: true
```

## Entry Points Setup

For plugin discovery to work with setuptools, add to `setup.py`:

```python
setup(
    name="localagent",
    entry_points={
        'console_scripts': [
            'localagent=app.cli.core.app:main',
        ],
        'localagent.plugins.commands': [
            'system-info=app.cli.plugins.builtin.builtin_plugins:SystemInfoPlugin',
            'workflow-debug=app.cli.plugins.builtin.builtin_plugins:WorkflowDebugPlugin',
            'config-manager=app.cli.plugins.builtin.builtin_plugins:ConfigurationPlugin',
        ],
        'localagent.plugins.workflow': [
            # Workflow plugins would be registered here
        ],
        'localagent.plugins.providers': [
            # Provider plugins would be registered here  
        ],
    },
)
```

## Usage Examples

### Using Enhanced CLI Commands

```bash
# System information
localagent system info
localagent system health

# Workflow debugging  
localagent debug phases
localagent debug agents

# Configuration management
localagent config show
localagent config validate
localagent config export --output my-config.yaml

# Provider management with enhanced features
localagent providers --list
localagent providers --health
localagent providers test ollama

# Workflow execution with monitoring
localagent workflow "Fix the authentication bug" --provider ollama --parallel
```

### Plugin Development

```python
from app.cli.plugins.framework import CommandPlugin
from app.cli.core.dynamic_command_registration import command

class MyCustomPlugin(CommandPlugin):
    name = "my-plugin"
    version = "1.0.0"
    description = "Custom plugin example"
    
    async def initialize(self, context):
        self.context = context
        return True
    
    def register_commands(self, app):
        @command(name="hello", group="custom")
        def hello():
            console.print("Hello from custom plugin!")
        
        app.command()(hello)
```

## Testing the Integration

### Unit Tests

```python
import pytest
from app.cli.plugins.enhanced_plugin_discovery import EntryPointDiscoveryEngine

@pytest.mark.asyncio
async def test_plugin_discovery():
    engine = EntryPointDiscoveryEngine()
    entries = await engine.discover_all_entry_points()
    assert len(entries) > 0

@pytest.mark.asyncio  
async def test_orchestration_bridge():
    # Test orchestration bridge functionality
    pass
```

### Integration Tests

```bash
# Test plugin system
localagent plugins --list

# Test orchestration
localagent workflow "test workflow" --phases 1,2

# Test provider integration
localagent providers --health

# Test dynamic commands
localagent system info
localagent debug phases
```

## Troubleshooting

### Common Issues

1. **Plugin Discovery Fails**
   - Check setuptools entry points configuration
   - Verify plugin directories exist and are readable
   - Check plugin class inheritance from base classes

2. **Orchestration Bridge Errors**
   - Ensure provider manager is properly initialized
   - Check MCP server availability
   - Verify configuration file paths

3. **Provider Monitoring Issues**
   - Check network connectivity to provider services
   - Verify API keys and authentication
   - Check provider configuration syntax

### Debug Mode

Enable debug mode for detailed logging:
```bash
localagent --debug workflow "test prompt"
```

## Performance Considerations

### Plugin Loading
- Entry point discovery is cached for performance
- Plugin loading is done lazily where possible
- Failed plugins don't block other plugins

### Orchestration Monitoring
- Real-time display refresh rate is configurable
- Monitoring can be disabled for headless operation
- Background monitoring uses minimal resources

### Provider Health Checks
- Health check timeout is configurable
- Failed providers are automatically marked unavailable
- Monitoring interval can be adjusted based on needs

## Future Enhancements

### Planned Features
1. **Plugin Marketplace**: Download and install plugins from repository
2. **Advanced Workflow Editor**: Visual workflow design interface
3. **Provider Load Balancing**: Intelligent request distribution
4. **Custom Agent Plugins**: User-defined agent implementations
5. **Workflow Templates**: Pre-built workflow configurations

### Extension Points
- Custom plugin types beyond the current four
- Provider-specific monitoring extensions
- Workflow phase plugins
- Custom UI components

This integration provides a comprehensive enhancement to the LocalAgent CLI system while maintaining compatibility with existing functionality.