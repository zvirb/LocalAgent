# CLI Integration Stream Context Package
**Package ID**: cli-integration-stream-20250825
**Token Limit**: 4000 tokens
**Target Specialists**: integration-orchestrator, plugin-architect, command-designer

## Current Integration State

### Existing CLI Integration (app/orchestration/cli_interface.py)
```python
class LocalAgentCLI:
    def __init__(self):
        self.orchestrator: Optional[LocalAgentOrchestrator] = None
    
    async def initialize_orchestrator(self, config_path: Optional[str] = None) -> bool:
        from app.llm_providers.provider_manager import ProviderManager
        provider_manager = ProviderManager(provider_config)
        self.orchestrator = LocalAgentOrchestrator(config_path)
```

**Current Limitations**:
- No plugin framework integration
- Monolithic CLI structure without modular commands
- Missing orchestration-CLI bridge layer
- No dynamic command registration
- Limited configuration management integration

## Target CLI Architecture

### Plugin Framework Integration
```python
# app/cli/plugins/framework.py - NEEDS IMPLEMENTATION
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import importlib.metadata

class CLIPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property 
    @abstractmethod
    def version(self) -> str: pass
    
    @abstractmethod
    async def initialize(self, context: CLIContext) -> bool: pass
    
    @abstractmethod
    def register_commands(self, app: typer.Typer) -> None: pass

class PluginManager:
    def __init__(self, context: CLIContext):
        self.plugins: Dict[str, CLIPlugin] = {}
        self.context = context
    
    async def discover_plugins(self):
        """Discover plugins via entry points"""
        for entry_point in importlib.metadata.entry_points(group='localagent.plugins.commands'):
            plugin_class = entry_point.load()
            plugin = plugin_class()
            self.plugins[plugin.name] = plugin
```

### Command Structure Integration
```python
# app/cli/commands/ - MODULAR COMMAND STRUCTURE
├── workflow.py      # Workflow execution commands
├── provider.py      # Provider management commands  
├── config.py        # Configuration commands
├── plugin.py        # Plugin management commands
└── orchestration.py # Direct orchestration integration
```

## Orchestration Integration Architecture

### Bridge Layer (app/cli/core/orchestration_bridge.py)
```python
class OrchestrationBridge:
    """Bridge between CLI and UnifiedWorkflow orchestration"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self.orchestrator: Optional[LocalAgentOrchestrator] = None
        self.provider_manager: Optional[ProviderManager] = None
    
    async def initialize(self) -> bool:
        """Initialize orchestration components"""
        config = await self.config_manager.load_configuration()
        
        # Initialize provider manager
        self.provider_manager = ProviderManager(config.providers)
        await self.provider_manager.initialize_providers()
        
        # Initialize orchestrator
        self.orchestrator = LocalAgentOrchestrator(config.orchestration)
        return await self.orchestrator.initialize(self.provider_manager)
    
    async def execute_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        """Execute 12-phase workflow via CLI"""
        return await self.orchestrator.execute_12_phase_workflow(
            user_prompt=request.prompt,
            context=request.context,
            workflow_id=request.workflow_id
        )
```

### Command Registration System
```python
# app/cli/core/app.py - MAIN APPLICATION STRUCTURE
import typer
from .config import ConfigurationManager
from .context import CLIContext
from .orchestration_bridge import OrchestrationBridge
from ..plugins.framework import PluginManager

def create_app() -> typer.Typer:
    """Create main CLI application with plugin support"""
    
    # Create main app
    app = typer.Typer(
        name="localagent",
        help="LocalAgent CLI with UnifiedWorkflow orchestration"
    )
    
    # Initialize core components
    config_manager = ConfigurationManager()
    cli_context = CLIContext(config_manager)
    orchestration_bridge = OrchestrationBridge(config_manager)
    plugin_manager = PluginManager(cli_context)
    
    # Register core commands
    register_core_commands(app, cli_context, orchestration_bridge)
    
    # Discover and register plugin commands  
    asyncio.run(plugin_manager.discover_and_register_plugins(app))
    
    return app
```

## Command Structure Design

### Core Command Categories
```python
# Workflow Commands
@app.command(rich_help_panel="Workflow Execution")
def workflow(
    prompt: str,
    provider: Optional[str] = None,
    parallel: bool = True,
    max_agents: int = 15,
    phases: Optional[str] = None
):
    """Execute 12-phase UnifiedWorkflow orchestration"""

@app.command(rich_help_panel="Workflow Execution") 
def agent(
    agent_type: str,
    prompt: str,
    context: Optional[str] = None
):
    """Execute single agent with orchestration context"""

# Provider Management Commands
@app.command(rich_help_panel="Provider Management")
def providers(
    list_providers: bool = False,
    health_check: bool = False,
    provider: Optional[str] = None
):
    """Manage LLM providers and check health"""

# Configuration Commands
@app.command(rich_help_panel="Configuration")
def config(
    show: bool = False,
    validate: bool = False,
    init: bool = False,
    edit: bool = False
):
    """Manage LocalAgent configuration"""
```

### Plugin Command Integration
```python
# Example Plugin Commands
class WorkflowAutomationPlugin(CLIPlugin):
    def register_commands(self, app: typer.Typer) -> None:
        
        @app.command("auto-workflow", rich_help_panel="Automation")
        def automated_workflow(
            config_file: str,
            schedule: Optional[str] = None
        ):
            """Execute automated workflow from configuration"""
            
        @app.command("workflow-template", rich_help_panel="Automation")  
        def create_workflow_template(
            template_name: str,
            base_prompt: str
        ):
            """Create reusable workflow template"""
```

## Configuration Integration

### CLI-Orchestration Configuration Bridge
```python
# app/cli/core/config.py - ENHANCED CONFIGURATION
from pydantic import BaseModel
from typing import Dict, Any, Optional
import yaml

class LocalAgentConfig(BaseModel):
    """Complete LocalAgent configuration model"""
    
    # Provider configuration
    providers: Dict[str, Any] = {}
    
    # Orchestration configuration
    orchestration: Dict[str, Any] = {
        "max_parallel_agents": 15,
        "max_workflow_iterations": 5,
        "enable_evidence_collection": True
    }
    
    # CLI-specific configuration
    cli: Dict[str, Any] = {
        "theme": "default",
        "interactive_prompts": True,
        "rich_formatting": True,
        "progress_indicators": True
    }
    
    # Plugin configuration
    plugins: Dict[str, Any] = {
        "enabled_plugins": [],
        "auto_load_plugins": True,
        "plugin_directories": ["~/.localagent/plugins"]
    }

class ConfigurationManager:
    async def load_configuration(self) -> LocalAgentConfig:
        """Load configuration from multiple sources"""
        config_data = {}
        
        # Load from YAML file
        config_file = self.get_config_file_path()
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
        
        # Override with environment variables
        config_data = self.apply_env_overrides(config_data)
        
        return LocalAgentConfig(**config_data)
```

### Environment Variable Integration
```python
# Environment variable mapping
ENV_VAR_MAPPINGS = {
    "LOCALAGENT_OLLAMA_BASE_URL": "providers.ollama.base_url",
    "LOCALAGENT_OPENAI_API_KEY": "providers.openai.api_key", 
    "LOCALAGENT_GEMINI_API_KEY": "providers.gemini.api_key",
    "LOCALAGENT_DEFAULT_PROVIDER": "orchestration.default_provider",
    "LOCALAGENT_MAX_PARALLEL_AGENTS": "orchestration.max_parallel_agents",
    "LOCALAGENT_PLUGINS_ENABLED": "plugins.enabled_plugins"
}
```

## Orchestration Command Patterns

### Workflow Execution Integration
```python
async def execute_workflow_command(
    prompt: str,
    cli_context: CLIContext,
    orchestration_bridge: OrchestrationBridge
) -> int:
    """Execute workflow with full CLI integration"""
    
    # Phase 0: Interactive prompt refinement (CLI-specific)
    if cli_context.config.cli.get("interactive_prompts", True):
        refined_prompt = await interactive_prompt_refinement(prompt)
    else:
        refined_prompt = prompt
    
    # Create workflow request
    request = WorkflowRequest(
        prompt=refined_prompt,
        context=cli_context.get_workflow_context(),
        workflow_id=generate_workflow_id()
    )
    
    # Execute with progress tracking
    with create_progress_tracker() as progress:
        result = await orchestration_bridge.execute_workflow(request)
        update_progress_from_result(progress, result)
    
    # Display results with CLI formatting
    display_workflow_results(result, cli_context)
    
    return 0 if result.success else 1
```

### Agent Execution Integration
```python
async def execute_agent_command(
    agent_type: str,
    prompt: str,
    orchestration_bridge: OrchestrationBridge
) -> int:
    """Execute single agent with orchestration context"""
    
    # Validate agent type against available agents
    available_agents = await orchestration_bridge.list_available_agents()
    if agent_type not in available_agents:
        console.print(f"[red]❌ Unknown agent type: {agent_type}[/red]")
        return 1
    
    # Execute agent with context
    result = await orchestration_bridge.execute_single_agent(
        agent_type=agent_type,
        prompt=prompt,
        context=create_agent_context()
    )
    
    # Display agent results
    display_agent_results(result)
    
    return 0 if result.success else 1
```

## Plugin System Architecture

### Plugin Discovery and Loading
```python
class PluginManager:
    async def discover_plugins(self) -> Dict[str, CLIPlugin]:
        """Discover plugins from entry points and directories"""
        discovered = {}
        
        # Entry point plugins (installed packages)
        for entry_point in importlib.metadata.entry_points(group='localagent.plugins.commands'):
            plugin_class = entry_point.load()
            plugin = plugin_class()
            discovered[plugin.name] = plugin
        
        # Directory plugins (local development)
        for plugin_dir in self.context.config.plugins.plugin_directories:
            discovered.update(await self.load_directory_plugins(plugin_dir))
        
        return discovered
    
    async def load_plugin(self, plugin_name: str) -> bool:
        """Load and initialize specific plugin"""
        if plugin_name not in self.discovered_plugins:
            return False
        
        plugin = self.discovered_plugins[plugin_name]
        
        # Initialize plugin
        if not await plugin.initialize(self.context):
            return False
        
        # Store loaded plugin
        self.loaded_plugins[plugin_name] = plugin
        return True
```

### Plugin Command Registration
```python
async def register_plugin_commands(self, app: typer.Typer):
    """Register commands from all loaded plugins"""
    
    for plugin in self.loaded_plugins.values():
        try:
            plugin.register_commands(app)
            console.print(f"[green]✅ Registered commands from {plugin.name}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Failed to register {plugin.name} commands: {e}[/red]")
```

## Implementation Priorities

### Phase 1: Core CLI-Orchestration Bridge
1. **Create OrchestrationBridge** class for provider/orchestrator integration
2. **Implement ConfigurationManager** with environment variable support
3. **Build CLIContext** for shared state management
4. **Convert argparse to Typer** in main CLI interface

### Phase 2: Plugin Framework Foundation
1. **Implement PluginManager** with entry point discovery
2. **Create CLIPlugin** base class and registration system
3. **Build command registration** system for plugins
4. **Add plugin lifecycle management**

### Phase 3: Advanced Integration Features
1. **Interactive workflow execution** with CLI prompts
2. **Real-time orchestration monitoring** via CLI
3. **Plugin development tools** and validation
4. **Configuration management** commands

## Success Criteria
1. **Seamless Integration**: CLI directly integrates with UnifiedWorkflow orchestration
2. **Plugin System**: Dynamic plugin discovery and command registration
3. **Configuration Bridge**: Unified configuration for CLI and orchestration
4. **Modern Architecture**: Typer-based modular command structure
5. **Developer Experience**: Easy plugin development and command extension