# LocalAgent CLI Toolkit - Complete Usage Guide

## Table of Contents
- [Overview](#overview)
- [Installation & Setup](#installation--setup)
- [Core Commands](#core-commands)
- [Configuration Management](#configuration-management)
- [Provider Management](#provider-management)
- [Workflow Execution](#workflow-execution)
- [Interactive Chat Mode](#interactive-chat-mode)
- [Plugin System](#plugin-system)
- [File Operations](#file-operations)
- [Advanced Features](#advanced-features)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Examples & Use Cases](#examples--use-cases)
- [API Reference](#api-reference)

---

## Overview

The LocalAgent CLI Toolkit is a modern, extensible command-line interface for multi-provider LLM orchestration. Built with Typer, Rich, and a comprehensive plugin architecture, it provides a professional CLI experience comparable to Claude Code while supporting local and cloud-based LLM providers.

### Key Features
- **Multi-Provider Support**: Ollama, OpenAI, Gemini, Perplexity
- **12-Phase UnifiedWorkflow**: Complete orchestration system
- **Plugin Architecture**: Extensible command system
- **Rich Terminal UI**: Modern, interactive interface
- **Atomic Operations**: Safe file handling
- **Interactive Prompts**: Fuzzy search and auto-completion
- **Configuration Management**: Environment-based configuration
- **Error Recovery**: Intelligent error handling and recovery

### Architecture Components
```
localagent/
├── Core Framework (Typer + Rich)
├── Provider System (Multi-LLM)
├── Plugin Architecture (Extensible)
├── Workflow Engine (12-Phase)
├── Configuration System (Environment + YAML)
├── Error Handling (Recovery + Diagnostics)
└── UI Components (Interactive + Rich)
```

---

## Installation & Setup

### System Requirements
- Python 3.9+
- Terminal with UTF-8 support
- Optional: Local Ollama installation

### Installation Methods

#### Method 1: From Source (Recommended for Development)
```bash
# Clone repository
git clone <repository-url>
cd LocalProgramming

# Install with development dependencies
pip install -e .

# Or install specific requirement sets
pip install -r requirements-core.txt
pip install -r requirements-dev.txt
```

#### Method 2: Using Setup Script
```bash
# Run automated setup
./scripts/setup-dev.sh

# Verify installation
localagent --help
```

#### Method 3: Docker Container
```bash
# Using Docker Compose
docker-compose up -d

# Access CLI in container
docker exec -it localagent_app localagent --help
```

### Initial Configuration

#### Quick Setup (Interactive)
```bash
# Initialize LocalAgent with interactive wizard
localagent init

# The wizard will guide you through:
# 1. Provider configuration (Ollama, OpenAI, etc.)
# 2. API key setup (secure storage)
# 3. Default preferences
# 4. Plugin configuration
```

#### Manual Configuration
```bash
# Create configuration directory
mkdir -p ~/.localagent

# Create basic configuration file
cat > ~/.localagent/config.yaml << 'EOF'
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
  openai:
    api_key: "${OPENAI_API_KEY}"
    default_model: "gpt-4"
    
system:
  default_provider: "ollama"
  max_parallel_agents: 10
  log_level: "INFO"
  
plugins:
  enabled_plugins:
    - "workflow-automation"
    - "security-scanner"
  auto_load_plugins: true
EOF
```

#### Environment Variables Setup
```bash
# Add to ~/.bashrc or ~/.zshrc
cat >> ~/.bashrc << 'EOF'
# LocalAgent Configuration
export LOCALAGENT_OLLAMA_BASE_URL="http://localhost:11434"
export LOCALAGENT_DEFAULT_PROVIDER="ollama"
export LOCALAGENT_MAX_PARALLEL_AGENTS=15
export LOCALAGENT_LOG_LEVEL="INFO"
export LOCALAGENT_PLUGINS_AUTO_LOAD=true

# API Keys (use keyring for production)
export LOCALAGENT_OPENAI_API_KEY="your-api-key"
export LOCALAGENT_GEMINI_API_KEY="your-api-key"
export LOCALAGENT_PERPLEXITY_API_KEY="your-api-key"
EOF

# Reload environment
source ~/.bashrc
```

### Verification
```bash
# Check installation
localagent --version
localagent health

# Verify providers
localagent providers --health

# Test basic functionality
localagent chat --provider ollama
```

---

## Core Commands

### Command Structure
LocalAgent follows modern CLI patterns with intuitive command organization:

```bash
# Basic structure
localagent [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]

# Global options (available for all commands)
--config PATH        # Custom configuration file
--log-level LEVEL    # Set log level (DEBUG, INFO, WARNING, ERROR)
--no-plugins        # Disable plugin loading
--debug             # Enable debug mode
--help, -h          # Show help
```

### Primary Commands Overview

| Command | Purpose | Examples |
|---------|---------|----------|
| `init` | Initialize configuration | `localagent init --force` |
| `config` | Manage configuration | `localagent config --show --validate` |
| `providers` | Manage LLM providers | `localagent providers --health` |
| `workflow` | Execute 12-phase workflows | `localagent workflow "Fix bug"` |
| `chat` | Interactive chat session | `localagent chat --provider openai` |
| `plugins` | Manage plugins | `localagent plugins --list --enable custom` |
| `health` | System diagnostics | `localagent health` |

---

## Configuration Management

### Configuration Hierarchy
LocalAgent loads configuration from multiple sources in priority order:

1. **Command-line arguments** (highest priority)
2. **Environment variables** (`LOCALAGENT_*`)
3. **Configuration files** (`~/.localagent/config.yaml`)
4. **Default values** (lowest priority)

### Configuration Commands

#### View Current Configuration
```bash
# Show all configuration
localagent config --show

# Show with source information
localagent config --show --verbose

# Show specific section
localagent config --show providers
```

#### Validate Configuration
```bash
# Validate all configuration
localagent config --validate

# Validate with detailed output
localagent config --validate --verbose

# Fix common configuration issues
localagent config --validate --fix
```

#### Export/Import Configuration
```bash
# Export current configuration
localagent config --export config-backup.yaml

# Export with encrypted secrets
localagent config --export-secure config-backup.yaml

# Import configuration
localagent config --import config-backup.yaml
```

### Configuration Sections

#### Provider Configuration
```yaml
providers:
  ollama:
    base_url: "http://localhost:11434"
    timeout: 120
    default_model: "llama3.1"
    max_retries: 3
    
  openai:
    api_key: "${OPENAI_API_KEY}"  # Environment variable
    base_url: "https://api.openai.com/v1"
    default_model: "gpt-4"
    timeout: 60
    
  gemini:
    api_key: "${GEMINI_API_KEY}"
    default_model: "gemini-1.5-pro"
    
  perplexity:
    api_key: "${PERPLEXITY_API_KEY}"
    default_model: "llama-3.1-sonar-huge-128k-online"
```

#### System Configuration
```yaml
system:
  default_provider: "ollama"
  max_parallel_agents: 10
  log_level: "INFO"
  config_dir: "~/.localagent"
  cache_enabled: true
  cache_ttl: 3600  # seconds
  
  # Workflow settings
  workflow:
    max_iterations: 3
    evidence_collection: true
    auto_cleanup: true
    
  # Security settings
  security:
    enable_audit_log: true
    restrict_file_access: false
    allow_command_execution: true
```

#### Plugin Configuration
```yaml
plugins:
  enabled_plugins:
    - "workflow-automation"
    - "security-scanner"
    - "export-tools"
  auto_load_plugins: true
  plugin_directories:
    - "~/.localagent/plugins"
    - "/opt/localagent/plugins"
  allow_dev_plugins: false  # Set to true for development
```

### Environment Variable Reference

#### Provider Settings
```bash
# Ollama
LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
LOCALAGENT_OLLAMA_DEFAULT_MODEL=llama3.1
LOCALAGENT_OLLAMA_TIMEOUT=120

# OpenAI
LOCALAGENT_OPENAI_API_KEY=sk-your-api-key
LOCALAGENT_OPENAI_DEFAULT_MODEL=gpt-4
LOCALAGENT_OPENAI_BASE_URL=https://api.openai.com/v1

# Gemini
LOCALAGENT_GEMINI_API_KEY=your-api-key
LOCALAGENT_GEMINI_DEFAULT_MODEL=gemini-1.5-pro

# Perplexity
LOCALAGENT_PERPLEXITY_API_KEY=pplx-your-api-key
LOCALAGENT_PERPLEXITY_DEFAULT_MODEL=llama-3.1-sonar-huge-128k-online
```

#### System Settings
```bash
# Core system settings
LOCALAGENT_DEFAULT_PROVIDER=ollama
LOCALAGENT_MAX_PARALLEL_AGENTS=10
LOCALAGENT_LOG_LEVEL=INFO
LOCALAGENT_CONFIG_DIR=~/.localagent

# Plugin settings
LOCALAGENT_PLUGINS_ENABLED=workflow-automation,security-scanner
LOCALAGENT_PLUGINS_AUTO_LOAD=true
LOCALAGENT_PLUGINS_ALLOW_DEV=false

# Security settings
LOCALAGENT_ENABLE_AUDIT_LOG=true
LOCALAGENT_KEYRING_SERVICE=localagent
```

### Secure Credential Management

#### Using System Keyring
```bash
# Store API keys securely
keyring set localagent openai_api_key
keyring set localagent gemini_api_key
keyring set localagent perplexity_api_key

# LocalAgent will automatically use keyring if available
localagent providers --health
```

#### Migration to Secure Storage
```bash
# Migrate existing API keys to keyring
localagent config migrate-credentials

# Verify secure storage
localagent config --validate --check-credentials
```

---

## Provider Management

### Provider Overview
LocalAgent supports multiple LLM providers with unified interface:

- **Ollama**: Local LLM serving (llama3.1, codellama, etc.)
- **OpenAI**: GPT-4, GPT-3.5-turbo, and other OpenAI models
- **Google Gemini**: Gemini 1.5 Pro, Gemini 1.5 Flash
- **Perplexity**: Sonar models with web search capabilities

### Provider Commands

#### List All Providers
```bash
# Basic provider list
localagent providers --list

# Detailed provider information
localagent providers --list --verbose

# Show specific provider
localagent providers --provider ollama --info
```

#### Health Check
```bash
# Check all providers
localagent providers --health

# Check specific provider
localagent providers --provider openai --health

# Detailed health check with metrics
localagent providers --health --verbose
```

#### Provider Models
```bash
# List models for all providers
localagent providers --models

# List models for specific provider
localagent providers --provider ollama --models

# Show model details
localagent providers --provider openai --model gpt-4 --info
```

### Provider Configuration Examples

#### Ollama Setup
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended models
ollama pull llama3.1
ollama pull codellama
ollama pull mistral

# Configure LocalAgent
export LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
export LOCALAGENT_OLLAMA_DEFAULT_MODEL=llama3.1

# Test connection
localagent providers --provider ollama --health
```

#### OpenAI Setup
```bash
# Set API key (use keyring in production)
export LOCALAGENT_OPENAI_API_KEY=sk-your-api-key-here

# Configure default model
export LOCALAGENT_OPENAI_DEFAULT_MODEL=gpt-4

# Test connection
localagent providers --provider openai --health

# List available models
localagent providers --provider openai --models
```

#### Multi-Provider Configuration
```yaml
# ~/.localagent/config.yaml
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
    priority: 1  # Primary for cost-effective tasks
    
  openai:
    api_key: "${OPENAI_API_KEY}"
    default_model: "gpt-4"
    priority: 2  # Secondary for complex tasks
    
  gemini:
    api_key: "${GEMINI_API_KEY}"
    default_model: "gemini-1.5-pro"
    priority: 3  # Tertiary for specific use cases

# Automatic fallback configuration
system:
  provider_fallback: true
  fallback_order: ["ollama", "openai", "gemini"]
  max_fallback_attempts: 2
```

### Provider-Specific Features

#### Ollama Features
- **Local execution**: No API costs
- **Model management**: Pull, list, delete models
- **Custom models**: Support for fine-tuned models
- **Embeddings**: Text embeddings support

```bash
# Ollama model management
ollama list                    # List installed models
ollama pull llama3.1:70b      # Pull specific model variant
ollama rm model_name           # Remove model

# Use specific model variant
localagent chat --provider ollama --model llama3.1:70b
```

#### OpenAI Features
- **Latest models**: GPT-4, GPT-3.5-turbo variants
- **Function calling**: Tool use capabilities
- **Vision**: Image analysis with GPT-4V
- **Structured outputs**: JSON mode support

```bash
# Use GPT-4 with vision
localagent chat --provider openai --model gpt-4-vision-preview

# Enable JSON mode
localagent workflow "Generate JSON schema" --provider openai --format json
```

#### Gemini Features
- **Large context**: Up to 1M tokens
- **Multimodal**: Text, image, audio support
- **Code execution**: Built-in code interpreter
- **Safety features**: Advanced content filtering

```bash
# Use Gemini Pro with large context
localagent workflow "Analyze large codebase" --provider gemini --model gemini-1.5-pro
```

#### Perplexity Features
- **Web search**: Real-time web search integration
- **Online models**: Access to latest information
- **Citations**: Source attribution
- **Specialized models**: Different model sizes

```bash
# Use Perplexity for research
localagent chat --provider perplexity --model llama-3.1-sonar-huge-128k-online
```

---

## Workflow Execution

### 12-Phase UnifiedWorkflow
The core feature of LocalAgent is the comprehensive 12-phase workflow system:

#### Phase Overview
1. **Phase 0**: Interactive Prompt Engineering & Environment Setup
2. **Phase 1**: Parallel Research & Discovery
3. **Phase 2**: Strategic Planning & Stream Design
4. **Phase 3**: Context Package Creation & Distribution
5. **Phase 4**: Parallel Stream Execution
6. **Phase 5**: Integration & Merge
7. **Phase 6**: Comprehensive Testing & Validation
8. **Phase 7**: Audit, Learning & Improvement
9. **Phase 8**: Cleanup & Documentation
10. **Phase 9**: Development Deployment

### Workflow Commands

#### Basic Workflow Execution
```bash
# Execute complete workflow
localagent workflow "Fix authentication system"

# Use specific provider
localagent workflow "Optimize database queries" --provider openai

# Run specific phases
localagent workflow "Code review" --phases 1,2,6,7

# Sequential execution (disable parallelization)
localagent workflow "Critical fix" --sequential
```

#### Advanced Workflow Options
```bash
# Customize parallel execution
localagent workflow "Large refactor" \
  --provider openai \
  --parallel \
  --max-agents 15 \
  --format rich \
  --save workflow-report.json

# Resume workflow from specific phase
localagent workflow resume --workflow-id abc123 --from-phase 4

# Dry run (plan only, no execution)
localagent workflow "Test plan" --dry-run
```

#### Workflow with Context
```bash
# Provide additional context
localagent workflow "Fix bug in user registration" \
  --context '{"repository": "user-service", "branch": "develop", "urgency": "high"}'

# Use context file
echo '{"project_type": "web_api", "framework": "fastapi"}' > context.json
localagent workflow "Add new endpoint" --context-file context.json
```

### Workflow Output Formats

#### Rich Terminal Output (Default)
```bash
localagent workflow "Task description" --format rich

# Features:
# - Real-time progress bars
# - Colored status indicators
# - Interactive tables
# - Live updates
# - Syntax highlighting
```

#### JSON Output
```bash
localagent workflow "Task description" --format json --save result.json

# Output includes:
# - Execution summary
# - Phase results
# - Agent performance metrics
# - Evidence collection
# - Error logs
```

#### Structured Report
```bash
localagent workflow "Task description" --format report --save report.md

# Generates:
# - Executive summary
# - Phase breakdown
# - Implementation details
# - Recommendations
# - Evidence attachments
```

### Workflow Monitoring

#### Real-time Status
```bash
# Check workflow status
localagent workflow status

# Monitor specific workflow
localagent workflow status --workflow-id abc123

# Watch mode (continuous updates)
localagent workflow status --watch
```

#### Workflow History
```bash
# List recent workflows
localagent workflow history

# Show workflow details
localagent workflow show abc123

# Export workflow data
localagent workflow export abc123 --format json
```

### Custom Workflow Configuration

#### Workflow Templates
```yaml
# ~/.localagent/workflows/bug-fix.yaml
name: "Bug Fix Workflow"
description: "Comprehensive bug investigation and fix"
phases:
  - phase: 1
    agents: ["codebase-research-analyst", "security-validator"]
    parallel: true
  - phase: 2
    agents: ["project-orchestrator"]
    depends_on: [1]
  - phase: 4
    agents: ["backend-gateway-expert", "test-automation-engineer"]
    parallel: true
    max_agents: 5
  - phase: 6
    agents: ["ui-regression-debugger"]
    required: true
```

```bash
# Use custom workflow template
localagent workflow "Fix login issue" --template bug-fix
```

#### Agent Configuration
```yaml
# ~/.localagent/agents/custom-agents.yaml
agents:
  custom-security-analyst:
    base_class: "security-validator"
    provider_preference: "openai"
    model: "gpt-4"
    context_limit: 8000
    specialized_prompts:
      - "Focus on authentication vulnerabilities"
      - "Check for OWASP Top 10 issues"
```

---

## Interactive Chat Mode

### Starting Chat Sessions

#### Basic Chat
```bash
# Start interactive chat with default provider
localagent chat

# Use specific provider and model
localagent chat --provider openai --model gpt-4

# Named session for history
localagent chat --session project-review
```

#### Chat with Context
```bash
# Start chat with project context
localagent chat --context '{"project": "web-api", "language": "python"}'

# Load context from file
localagent chat --context-file project.json
```

### Chat Commands
While in interactive mode, use these slash commands:

#### Session Management
```
/help                 # Show available commands
/clear                # Clear conversation history
/save session-name    # Save current session
/load session-name    # Load saved session
/sessions             # List saved sessions
/exit                 # Exit chat mode
```

#### Provider/Model Management
```
/providers            # List available providers
/provider openai      # Switch to OpenAI
/models               # List models for current provider
/model gpt-4          # Switch to specific model
/settings             # Show current settings
```

#### Context Management
```
/context              # Show current context usage
/context-reset        # Reset conversation context
/context-file path    # Load context from file
/context-save file    # Save current context
```

#### File Operations
```
/files                # List files in current directory
/cd /path/to/dir      # Change working directory
/pwd                  # Show current directory
/read filename        # Read and discuss file
/edit filename        # Edit file with AI assistance
```

#### Advanced Features
```
/workflow prompt      # Execute workflow from chat
/summarize           # Summarize conversation
/export format       # Export conversation (md, json, txt)
/temperature 0.7     # Adjust model temperature
/max-tokens 2000     # Set max response tokens
```

### Chat Session Features

#### Multi-turn Conversations
```
You: Explain Python decorators
Assistant: [Detailed explanation of decorators...]

You: Can you show an example with logging?
Assistant: [Builds on previous context with logging example...]

You: How would this work with async functions?
Assistant: [Continues thread with async decorators...]
```

#### Code Analysis and Editing
```
You: /read app.py
Assistant: I've read app.py. This appears to be a Flask application with...

You: Can you refactor the authentication function?
Assistant: I'll help refactor the authentication. Here's an improved version...

You: /edit app.py
# LocalAgent opens file for editing with AI assistance
```

#### Session Persistence
```bash
# Sessions are automatically saved
# ~/.localagent/sessions/
#   ├── default.json
#   ├── project-review.json
#   └── debugging-session.json

# Resume previous session
localagent chat --session project-review

# List all sessions
localagent chat --list-sessions
```

### Chat Configuration

#### Chat-specific Settings
```yaml
# ~/.localagent/config.yaml
chat:
  default_provider: "ollama"
  default_model: "llama3.1"
  max_history: 50  # messages
  auto_save: true
  session_timeout: 3600  # seconds
  
  # UI preferences
  show_tokens: true
  show_timing: true
  enable_syntax_highlighting: true
  
  # Behavior
  streaming: true
  temperature: 0.7
  max_tokens: 2000
```

#### Keyboard Shortcuts
- `Ctrl+C`: Exit chat mode
- `Ctrl+L`: Clear screen (preserve history)
- `Ctrl+R`: Search chat history
- `Escape`: Cancel current input
- `Tab`: Auto-complete commands/files
- `↑/↓`: Navigate command history
- `Shift+Enter`: Multi-line input

---

## Plugin System

### Plugin Architecture Overview
LocalAgent features a comprehensive plugin system that allows extending functionality through:

- **Command Plugins**: Add new CLI commands
- **Provider Plugins**: Add new LLM providers
- **UI Plugins**: Extend user interface components
- **Workflow Plugins**: Add workflow phases or agents

### Plugin Management Commands

#### List Available Plugins
```bash
# List all discovered plugins
localagent plugins --list

# List enabled plugins only
localagent plugins --list --enabled

# List plugins with detailed information
localagent plugins --list --verbose
```

#### Enable/Disable Plugins
```bash
# Enable a plugin
localagent plugins --enable workflow-automation

# Disable a plugin
localagent plugins --disable security-scanner

# Enable multiple plugins
localagent plugins --enable plugin1,plugin2,plugin3
```

#### Plugin Information
```bash
# Show detailed plugin information
localagent plugins --info workflow-automation

# Show plugin configuration schema
localagent plugins --info workflow-automation --config-schema

# Test plugin functionality
localagent plugins --test workflow-automation
```

### Built-in Plugins

#### Workflow Automation Plugin
```bash
# Enable workflow automation
localagent plugins --enable workflow-automation

# New commands available:
localagent workflow-template create bug-fix
localagent workflow-schedule "Daily health check" --cron "0 9 * * *"
localagent workflow-batch process --input tasks.yaml
```

#### Security Scanner Plugin
```bash
# Enable security scanner
localagent plugins --enable security-scanner

# New commands available:
localagent security-scan --target ./src
localagent vulnerability-check --severity high
localagent compliance-report --standard owasp
```

#### Export Tools Plugin
```bash
# Enable export tools
localagent plugins --enable export-tools

# New commands available:
localagent export-workflow result.html --format html
localagent export-config backup.tar.gz --encrypted
localagent export-sessions archive.json
```

#### Developer Tools Plugin
```bash
# Enable developer tools
localagent plugins --enable dev-tools

# New commands available:
localagent debug-workflow --workflow-id abc123
localagent profile-performance --command "workflow test"
localagent analyze-logs --level error
```

### Creating Custom Plugins

#### Plugin Development Setup
```bash
# Create plugin directory
mkdir -p ~/.localagent/plugins/my-plugin
cd ~/.localagent/plugins/my-plugin

# Create plugin structure
touch __init__.py
touch plugin.py
touch setup.py
```

#### Basic Command Plugin Example
```python
# ~/.localagent/plugins/my-plugin/plugin.py
from app.cli.plugins.framework import CommandPlugin
import typer
from rich.console import Console

console = Console()

class MyCustomPlugin(CommandPlugin):
    @property
    def name(self) -> str:
        return "my-custom-plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "My custom LocalAgent plugin"
    
    async def initialize(self, context) -> bool:
        """Initialize plugin with CLI context"""
        self.context = context
        console.print(f"[green]Initialized {self.name} v{self.version}[/green]")
        return True
    
    def register_commands(self, app: typer.Typer) -> None:
        """Register plugin commands"""
        
        @app.command("my-command")
        def my_command(
            target: str = typer.Argument(help="Target for the command"),
            option: bool = typer.Option(False, "--option", "-o", help="Enable option")
        ):
            """My custom command"""
            console.print(f"Executing my-command on {target}")
            if option:
                console.print("Option enabled")
            
            # Access plugin context
            console.print(f"Using provider: {self.context.config.default_provider}")
        
        @app.command("my-analysis")
        def my_analysis(file_path: str):
            """Analyze a file"""
            with open(file_path, 'r') as f:
                content = f.read()
            
            console.print(f"Analyzing {file_path}:")
            console.print(f"- Lines: {len(content.splitlines())}")
            console.print(f"- Characters: {len(content)}")
```

#### Entry Point Configuration
```python
# setup.py
from setuptools import setup

setup(
    name="my-localagent-plugin",
    version="1.0.0",
    packages=["my-plugin"],
    entry_points={
        "localagent.plugins.commands": [
            "my-custom-plugin = my-plugin.plugin:MyCustomPlugin"
        ]
    }
)
```

#### Install and Enable Plugin
```bash
# Install plugin
cd ~/.localagent/plugins/my-plugin
pip install -e .

# Enable in LocalAgent
localagent plugins --enable my-custom-plugin

# Verify installation
localagent plugins --list | grep my-custom-plugin

# Test plugin commands
localagent my-command "test-target" --option
localagent my-analysis "some-file.py"
```

### Advanced Plugin Development

#### Provider Plugin Example
```python
from app.cli.plugins.framework import ProviderPlugin
from app.llm_providers.base_provider import BaseProvider

class CustomLLMProvider(BaseProvider):
    """Custom LLM provider implementation"""
    
    async def initialize(self, config: dict) -> bool:
        # Initialize custom provider
        return True
    
    async def complete(self, request):
        # Implement completion logic
        pass
    
    async def stream_complete(self, request):
        # Implement streaming completion
        pass

class CustomProviderPlugin(ProviderPlugin):
    @property
    def name(self) -> str:
        return "custom-llm-provider"
    
    def get_provider_class(self):
        return CustomLLMProvider
    
    def get_provider_config_schema(self):
        return {
            "type": "object",
            "properties": {
                "api_endpoint": {"type": "string"},
                "api_key": {"type": "string"}
            }
        }
```

#### UI Plugin Example
```python
from app.cli.plugins.framework import UIPlugin
from rich.table import Table

class CustomUIPlugin(UIPlugin):
    @property
    def name(self) -> str:
        return "custom-ui-components"
    
    def get_ui_components(self):
        return {
            "custom_table": self.create_custom_table,
            "status_display": self.create_status_display
        }
    
    def create_custom_table(self, data):
        """Create a custom table component"""
        table = Table(title="Custom Data View")
        # Table implementation
        return table
    
    def create_status_display(self, status_data):
        """Create custom status display"""
        # Status display implementation
        pass
```

### Plugin Configuration

#### Plugin-specific Settings
```yaml
# ~/.localagent/config.yaml
plugins:
  my-custom-plugin:
    enabled: true
    config:
      option1: "value1"
      option2: true
      nested:
        setting: "nested_value"
  
  security-scanner:
    enabled: true
    config:
      scan_depth: "deep"
      exclude_patterns:
        - "*.test.js"
        - "node_modules/*"
      severity_threshold: "medium"
```

#### Dynamic Plugin Loading
```bash
# Enable hot-reload for development
export LOCALAGENT_PLUGINS_HOT_RELOAD=true

# Plugin will reload automatically when files change
localagent chat  # Plugin changes will be applied without restart
```

### Plugin Best Practices

1. **Error Handling**: Always implement proper error handling
2. **Resource Cleanup**: Implement cleanup methods
3. **Configuration**: Provide clear configuration schemas
4. **Documentation**: Include comprehensive help text
5. **Testing**: Write tests for plugin functionality
6. **Performance**: Consider performance impact
7. **Security**: Validate input and handle permissions

---

## File Operations

### Atomic File Operations
LocalAgent implements atomic file operations to ensure data integrity:

#### Safe File Writing
```python
# Internal implementation uses atomic writes
# - Write to temporary file
# - Validate content
# - Atomic rename to target
# - Automatic backup creation
```

#### File Operation Commands
```bash
# Read file with AI analysis
localagent file read project.py --analyze

# Edit file with AI assistance
localagent file edit config.yaml --backup

# Compare files
localagent file compare old_version.py new_version.py

# Batch file operations
localagent file batch-process *.py --operation "add-docstrings"
```

### Configuration File Management

#### Configuration Backup and Restore
```bash
# Create configuration backup
localagent config backup --output config-backup-$(date +%Y%m%d).tar.gz

# Restore from backup
localagent config restore config-backup-20241201.tar.gz

# Validate configuration integrity
localagent config verify --checksum
```

#### Configuration Versioning
```bash
# Enable configuration versioning
localagent config version --enable

# List configuration versions
localagent config version --list

# Rollback to previous version
localagent config version --rollback 2
```

### Working Directory Management

#### Directory Context
```bash
# Set working directory for session
localagent --working-dir /path/to/project workflow "Task"

# Change directory within interactive mode
localagent chat
> /cd /path/to/project
> /pwd
/path/to/project
```

#### Project Detection
```bash
# Auto-detect project type and configuration
localagent project detect

# Initialize project-specific configuration
localagent project init --type web-api

# Show project context
localagent project info
```

---

## Advanced Features

### Parallel Execution

#### Agent Parallelization
```bash
# Control parallel execution
localagent workflow "Complex task" \
  --parallel \
  --max-agents 15 \
  --agent-timeout 300

# Disable parallelization for debugging
localagent workflow "Debug task" --sequential
```

#### Resource Management
```bash
# Monitor resource usage
localagent health --resources

# Set resource limits
export LOCALAGENT_MAX_MEMORY=4096  # MB
export LOCALAGENT_MAX_CPU_PERCENT=80
```

### Caching and Performance

#### Response Caching
```yaml
# ~/.localagent/config.yaml
caching:
  enabled: true
  ttl: 3600  # 1 hour
  max_size: 1000  # entries
  storage: "redis"  # or "memory", "disk"
  
  # Cache key configuration
  include_provider: true
  include_model: true
  include_context_hash: true
```

```bash
# Cache management commands
localagent cache clear
localagent cache stats
localagent cache prune --older-than 24h
```

#### Performance Monitoring
```bash
# Enable performance tracking
export LOCALAGENT_PERFORMANCE_TRACKING=true

# View performance metrics
localagent performance report
localagent performance profile --command "workflow test"
```

### Workflow Scheduling

#### Scheduled Workflows
```bash
# Schedule recurring workflow
localagent schedule create \
  --name "daily-security-scan" \
  --workflow "security-scan" \
  --cron "0 9 * * *" \
  --provider "ollama"

# List scheduled workflows
localagent schedule list

# Disable/enable schedule
localagent schedule disable daily-security-scan
localagent schedule enable daily-security-scan
```

#### Workflow Chaining
```yaml
# ~/.localagent/workflows/chain-example.yaml
workflow_chain:
  name: "CI/CD Pipeline"
  steps:
    - workflow: "code-analysis"
      provider: "ollama"
      on_success: "continue"
      on_failure: "abort"
      
    - workflow: "security-scan"
      provider: "openai"
      depends_on: "code-analysis"
      
    - workflow: "deploy-staging"
      provider: "gemini"
      depends_on: "security-scan"
      condition: "security_score > 0.8"
```

### Integration Features

#### Git Integration
```bash
# Workflow with Git context
localagent workflow "Review changes" --git-diff

# Auto-commit workflow results
localagent workflow "Fix issues" --auto-commit

# Branch-aware workflows
localagent workflow "Feature implementation" --branch feature/new-api
```

#### CI/CD Integration
```bash
# Exit codes for CI/CD
localagent workflow "CI checks" --exit-on-failure

# Generate CI-friendly output
localagent workflow "Tests" --format junit --output results.xml

# Integration with popular CI systems
localagent ci github-actions --workflow security-scan
localagent ci jenkins --job code-review
```

#### API Integration
```bash
# REST API mode
localagent server start --port 8080

# API endpoints:
# POST /api/v1/workflow
# GET /api/v1/workflow/{id}/status
# GET /api/v1/providers
# GET /api/v1/health

# WebSocket for real-time updates
localagent server start --websocket
```

---

## Performance Tuning

### Resource Optimization

#### Memory Management
```bash
# Configure memory limits
export LOCALAGENT_MAX_MEMORY=4096  # MB
export LOCALAGENT_MEMORY_WARNING_THRESHOLD=80  # percent

# Enable memory monitoring
export LOCALAGENT_MEMORY_MONITORING=true

# Memory optimization settings
export LOCALAGENT_CONTEXT_COMPRESSION=true
export LOCALAGENT_HISTORY_CLEANUP_INTERVAL=300  # seconds
```

#### CPU Optimization
```bash
# Configure CPU usage
export LOCALAGENT_MAX_CPU_PERCENT=80
export LOCALAGENT_THREAD_POOL_SIZE=10

# I/O optimization
export LOCALAGENT_ASYNC_IO=true
export LOCALAGENT_IO_BUFFER_SIZE=65536
```

### Performance Monitoring

#### Built-in Metrics
```bash
# Performance dashboard
localagent performance dashboard

# Detailed metrics
localagent performance metrics --format json

# Performance alerts
localagent performance alerts --threshold 95
```

#### Profiling
```bash
# Profile specific command
localagent performance profile workflow "test task"

# Enable continuous profiling
export LOCALAGENT_PROFILING=true
localagent workflow "monitored task"

# Generate performance report
localagent performance report --output perf-report.html
```

### Optimization Strategies

#### Provider Selection
```yaml
# ~/.localagent/config.yaml
performance:
  provider_selection:
    strategy: "performance"  # or "cost", "quality"
    fallback_enabled: true
    timeout_threshold: 30  # seconds
    
  # Provider-specific optimization
  providers:
    ollama:
      connection_pool_size: 10
      keep_alive: true
      
    openai:
      rate_limit: 60  # requests per minute
      batch_requests: true
```

#### Caching Strategy
```yaml
caching:
  enabled: true
  strategy: "intelligent"  # or "aggressive", "conservative"
  levels:
    - "provider_responses"
    - "workflow_phases"
    - "file_analysis"
  
  intelligent_caching:
    similarity_threshold: 0.8
    context_aware: true
    auto_invalidate: true
```

### Benchmarking

#### Performance Baselines
```bash
# Establish performance baseline
localagent benchmark create --name "standard-workflow" --iterations 10

# Compare current performance
localagent benchmark compare --baseline standard-workflow

# Benchmark specific operations
localagent benchmark provider --provider all --model-size large
```

#### Load Testing
```bash
# Simulate concurrent workflows
localagent load-test \
  --concurrent-workflows 5 \
  --duration 300 \
  --ramp-up 60

# Test provider limits
localagent load-test provider --provider openai --requests-per-minute 100
```

---

## Best Practices

### Configuration Best Practices

1. **Use Environment Variables for Secrets**
   ```bash
   # Good
   export LOCALAGENT_OPENAI_API_KEY="your-key"
   
   # Better - use keyring
   keyring set localagent openai_api_key
   ```

2. **Organize Configuration Files**
   ```
   ~/.localagent/
   ├── config.yaml              # Main configuration
   ├── environments/
   │   ├── development.yaml     # Dev-specific settings
   │   ├── staging.yaml         # Staging settings
   │   └── production.yaml      # Production settings
   ├── workflows/               # Custom workflows
   ├── plugins/                 # Custom plugins
   └── sessions/               # Chat sessions
   ```

3. **Version Control Configuration**
   ```bash
   # .gitignore
   .localagent/config.yaml      # Contains secrets
   .localagent/sessions/        # Personal sessions
   
   # Include in version control
   .localagent/workflows/       # Team workflows
   .localagent/plugins/         # Team plugins
   .localagent/config.template.yaml  # Configuration template
   ```

### Security Best Practices

1. **API Key Management**
   ```bash
   # Use system keyring for production
   keyring set localagent openai_api_key
   keyring set localagent gemini_api_key
   
   # Audit API key usage
   localagent audit api-keys --report monthly
   ```

2. **Network Security**
   ```yaml
   # ~/.localagent/config.yaml
   security:
     tls_verify: true
     allowed_hosts:
       - "api.openai.com"
       - "localhost"
     proxy_settings:
       http_proxy: "http://proxy.company.com:8080"
   ```

3. **Audit Logging**
   ```bash
   # Enable comprehensive audit logging
   export LOCALAGENT_AUDIT_LOG=true
   export LOCALAGENT_AUDIT_LEVEL=detailed
   
   # Review audit logs
   localagent audit review --since 7d
   ```

### Performance Best Practices

1. **Resource Management**
   ```bash
   # Monitor resource usage
   localagent health --resources --watch
   
   # Set appropriate limits
   export LOCALAGENT_MAX_PARALLEL_AGENTS=8  # Based on CPU cores
   export LOCALAGENT_MAX_MEMORY=2048        # Based on available RAM
   ```

2. **Provider Selection**
   ```yaml
   # Use cost-effective providers for simple tasks
   workflow_defaults:
     simple_tasks:
       provider: "ollama"
       model: "llama3.1"
     complex_tasks:
       provider: "openai"
       model: "gpt-4"
   ```

3. **Caching Strategy**
   ```bash
   # Enable intelligent caching
   export LOCALAGENT_CACHING_ENABLED=true
   export LOCALAGENT_CACHE_STRATEGY=intelligent
   
   # Regular cache maintenance
   localagent cache prune --schedule weekly
   ```

### Development Best Practices

1. **Plugin Development**
   - Follow plugin interface contracts
   - Implement proper error handling
   - Include comprehensive tests
   - Provide clear documentation
   - Use semantic versioning

2. **Workflow Design**
   - Break complex workflows into phases
   - Use parallel execution where possible
   - Include validation steps
   - Document workflow purposes
   - Test with various inputs

3. **Error Handling**
   ```python
   # Plugin error handling example
   try:
       result = await self.execute_task()
       return result
   except Exception as e:
       self.logger.error(f"Task failed: {e}")
       await self.cleanup()
       raise
   ```

### Team Collaboration

1. **Shared Configuration**
   ```bash
   # Create team configuration template
   localagent config template --team --output .localagent-template.yaml
   
   # Team members initialize from template
   localagent init --template .localagent-template.yaml
   ```

2. **Workflow Sharing**
   ```bash
   # Export workflow for sharing
   localagent workflow export successful-workflow --format yaml
   
   # Import shared workflow
   localagent workflow import team-workflow.yaml
   ```

3. **Plugin Management**
   ```bash
   # Create team plugin bundle
   localagent plugins bundle --name team-plugins --output team-bundle.tar.gz
   
   # Install team plugin bundle
   localagent plugins install team-bundle.tar.gz
   ```

---

## Troubleshooting

### Common Issues

#### Installation Problems

**Issue**: `localagent: command not found`
```bash
# Solution 1: Check installation
which python
which pip
pip list | grep localagent

# Solution 2: Reinstall
pip uninstall localagent-cli
pip install -e .

# Solution 3: Check PATH
echo $PATH
export PATH="$HOME/.local/bin:$PATH"
```

**Issue**: Import errors
```bash
# Check dependencies
pip install -r requirements-core.txt

# Virtual environment issues
deactivate
python -m venv venv
source venv/bin/activate
pip install -e .
```

#### Configuration Issues

**Issue**: Configuration not loading
```bash
# Debug configuration loading
localagent config --show --verbose

# Check configuration file syntax
python -c "import yaml; yaml.safe_load(open('~/.localagent/config.yaml'))"

# Reset to defaults
localagent config reset --confirm
```

**Issue**: API key not found
```bash
# Check environment variables
env | grep LOCALAGENT

# Test keyring access
keyring get localagent openai_api_key

# Manual key setup
localagent config set providers.openai.api_key "your-key"
```

#### Provider Connection Issues

**Issue**: Ollama connection failed
```bash
# Check Ollama status
sudo systemctl status ollama
curl http://localhost:11434/api/tags

# Start Ollama if needed
sudo systemctl start ollama

# Test LocalAgent connection
localagent providers --provider ollama --health
```

**Issue**: OpenAI API errors
```bash
# Verify API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Check rate limits
localagent providers --provider openai --status

# Test with different model
localagent chat --provider openai --model gpt-3.5-turbo
```

#### Workflow Execution Issues

**Issue**: Workflow hangs or fails
```bash
# Enable debug mode
localagent --debug workflow "test task"

# Check system resources
localagent health --resources

# Run sequential mode for debugging
localagent workflow "test task" --sequential
```

**Issue**: Plugin loading errors
```bash
# List plugin status
localagent plugins --list --verbose

# Test plugin individually
localagent plugins --test plugin-name

# Disable problematic plugins
localagent plugins --disable plugin-name
```

### Diagnostic Commands

#### System Health Check
```bash
# Comprehensive health check
localagent health --comprehensive

# Check specific components
localagent health --check providers,plugins,config

# Generate diagnostic report
localagent health --report --output diagnostic-report.json
```

#### Performance Diagnostics
```bash
# Check performance metrics
localagent performance check

# Monitor resource usage
localagent performance monitor --duration 60

# Identify bottlenecks
localagent performance bottleneck-analysis
```

#### Log Analysis
```bash
# View recent logs
localagent logs --tail 100

# Filter by level
localagent logs --level error --since 1h

# Search logs
localagent logs --search "connection failed"
```

### Recovery Procedures

#### Configuration Recovery
```bash
# Backup current configuration
cp ~/.localagent/config.yaml ~/.localagent/config.yaml.backup

# Reset to known good state
localagent config restore --from-backup

# Gradual recovery
localagent init --minimal  # Basic configuration only
```

#### Plugin Recovery
```bash
# Disable all plugins
localagent plugins --disable-all

# Enable plugins one by one
localagent plugins --enable plugin-name
localagent health --check plugins
```

#### Data Recovery
```bash
# Recover workflow data
localagent workflow recover --workflow-id abc123

# Restore chat sessions
localagent chat --restore-session session-name

# Export data before major changes
localagent export --all --output backup-$(date +%Y%m%d).tar.gz
```

---

## Examples & Use Cases

### Development Workflows

#### Code Review Automation
```bash
# Comprehensive code review
localagent workflow "Review pull request changes" \
  --provider openai \
  --context '{"pr_id": "123", "target_branch": "main"}' \
  --format report

# Security-focused review
localagent workflow "Security code review" \
  --phases 1,2,6,7 \
  --parallel \
  --save security-review-report.json
```

#### Bug Investigation
```bash
# Multi-phase bug analysis
localagent workflow "Investigate authentication bug" \
  --context '{"severity": "high", "affected_users": "all", "environment": "production"}' \
  --max-agents 8

# Quick bug triage
localagent chat --provider ollama
> Analyze the login error logs from the past hour
> /read /var/log/auth.log
> Suggest immediate mitigation steps
```

#### Feature Development
```bash
# Feature planning and implementation
localagent workflow "Implement user dashboard API" \
  --provider gemini \
  --context '{"requirements": "./requirements.md", "api_spec": "./api-spec.yaml"}'

# Progressive development
localagent workflow "Phase 1: Database design" --phases 1,2,3
localagent workflow "Phase 2: API implementation" --phases 4,5,6
localagent workflow "Phase 3: Testing and deployment" --phases 7,8,9
```

### DevOps and Operations

#### Infrastructure Analysis
```bash
# System health analysis
localagent workflow "Analyze server performance issues" \
  --provider openai \
  --context '{"metrics_file": "./server-metrics.json", "timeframe": "24h"}'

# Security audit
localagent workflow "Complete security audit" \
  --parallel \
  --max-agents 12 \
  --save security-audit-$(date +%Y%m%d).json
```

#### Deployment Automation
```bash
# Deployment validation
localagent workflow "Pre-deployment validation" \
  --phases 1,2,6 \
  --provider ollama

# Post-deployment monitoring
localagent schedule create \
  --name "post-deploy-monitor" \
  --workflow "Monitor deployment health" \
  --interval 300  # 5 minutes
```

### Data Analysis and Research

#### Research Assistant
```bash
# Literature review
localagent workflow "Research latest ML techniques for NLP" \
  --provider perplexity \
  --context '{"domain": "machine_learning", "focus": "NLP", "time_range": "2024"}'

# Comparative analysis
localagent chat --provider gemini
> Compare the performance characteristics of different vector databases
> Focus on scalability, query performance, and memory usage
> Generate a comparison table
```

#### Data Processing
```bash
# Large dataset analysis
localagent workflow "Analyze customer feedback data" \
  --provider openai \
  --context '{"data_file": "feedback_2024.csv", "analysis_type": "sentiment"}' \
  --parallel

# Report generation
localagent workflow "Generate monthly analytics report" \
  --format html \
  --save monthly-report-$(date +%Y%m).html
```

### Education and Learning

#### Code Learning Assistant
```bash
# Explain complex code
localagent chat --provider ollama --session learning
> /read complex_algorithm.py
> Explain this algorithm step by step
> What are the time and space complexities?
> Suggest optimizations

# Interactive learning
> Can you create a simpler version for learning?
> Add detailed comments explaining each step
> /edit simple_algorithm.py
```

#### Documentation Generation
```bash
# Auto-generate documentation
localagent workflow "Generate API documentation" \
  --provider gemini \
  --context '{"source_dir": "./src/api", "output_format": "markdown"}'

# Update existing docs
localagent workflow "Update project README" \
  --context '{"recent_changes": true, "include_examples": true}'
```

### Custom Automation

#### Daily Routines
```bash
# Morning briefing
localagent schedule create \
  --name "morning-briefing" \
  --workflow "Generate daily development summary" \
  --cron "0 8 * * 1-5"  # Weekdays at 8 AM

# End-of-day cleanup
localagent schedule create \
  --name "eod-cleanup" \
  --workflow "Organize and backup work" \
  --cron "0 18 * * *"   # Daily at 6 PM
```

#### Batch Processing
```yaml
# batch-tasks.yaml
tasks:
  - workflow: "Code quality check"
    target: "./src/frontend"
    provider: "ollama"
    
  - workflow: "Security scan"
    target: "./src/backend"
    provider: "openai"
    
  - workflow: "Documentation update"
    target: "./docs"
    provider: "gemini"
```

```bash
# Execute batch tasks
localagent workflow batch --config batch-tasks.yaml --parallel
```

### Integration Examples

#### Git Integration
```bash
# Pre-commit workflow
git add .
localagent workflow "Pre-commit validation" --git-staged

# Post-merge analysis
localagent workflow "Analyze merge impact" \
  --git-diff origin/main..HEAD \
  --auto-commit-report
```

#### CI/CD Integration
```bash
# GitHub Actions integration
# .github/workflows/localagent.yml
name: LocalAgent Analysis
on: [push, pull_request]
jobs:
  analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run LocalAgent Analysis
        run: |
          localagent workflow "CI/CD quality check" \
            --format junit \
            --output test-results.xml
```

#### API Integration
```bash
# Start API server
localagent server start --port 8080 --background

# Use API endpoints
curl -X POST http://localhost:8080/api/v1/workflow \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analyze code quality", "provider": "ollama"}'
```

---

## API Reference

### Command Line Interface

#### Global Options
```
Usage: localagent [OPTIONS] COMMAND [ARGS]...

Options:
  --config PATH               Configuration file path
  --log-level [DEBUG|INFO|WARNING|ERROR]
                             Set logging level
  --no-plugins               Disable plugin loading
  --debug                    Enable debug mode
  --version                  Show version and exit
  --help                     Show this message and exit
```

#### Core Commands

##### `init` - Initialize Configuration
```
Usage: localagent init [OPTIONS]

Options:
  -f, --force                Force reinitialize
  --template PATH            Use configuration template
  --minimal                  Minimal configuration setup
  --interactive / --no-interactive
                             Interactive or batch mode
```

##### `config` - Configuration Management
```
Usage: localagent config [OPTIONS]

Options:
  --show                     Show current configuration
  --validate                 Validate configuration
  --export PATH              Export configuration to file
  --import PATH              Import configuration from file
  --reset                    Reset to default configuration
  --migrate-credentials      Migrate API keys to keyring
```

##### `providers` - Provider Management
```
Usage: localagent providers [OPTIONS]

Options:
  -l, --list                 List all providers
  --health                   Check provider health
  --models                   List available models
  -p, --provider TEXT        Specific provider name
  --info                     Show detailed provider info
  --verbose                  Verbose output
```

##### `workflow` - Workflow Execution
```
Usage: localagent workflow [OPTIONS] PROMPT

Arguments:
  PROMPT                     Workflow prompt [required]

Options:
  -p, --provider TEXT        LLM provider to use
  --phases TEXT              Specific phases to run (e.g., '1,2,3')
  --parallel / --sequential  Run agents in parallel/sequential
  --max-agents INTEGER       Maximum parallel agents [default: 10]
  --format [rich|json|yaml]  Output format [default: rich]
  --save PATH                Save report to file
  --context TEXT             JSON context data
  --context-file PATH        Context file path
  --dry-run                  Plan only, no execution
```

##### `chat` - Interactive Chat
```
Usage: localagent chat [OPTIONS]

Options:
  -p, --provider TEXT        LLM provider to use
  -m, --model TEXT           Specific model
  --session TEXT             Session name for history
  --context TEXT             Initial context
  --context-file PATH        Context file path
  --list-sessions            List available sessions
```

##### `plugins` - Plugin Management
```
Usage: localagent plugins [OPTIONS]

Options:
  -l, --list                 List available plugins
  --enable TEXT              Enable plugin
  --disable TEXT             Disable plugin
  --info TEXT                Show plugin info
  --test TEXT                Test plugin functionality
  --enabled                  Show only enabled plugins
  --verbose                  Verbose output
```

##### `health` - System Health Check
```
Usage: localagent health [OPTIONS]

Options:
  --comprehensive            Comprehensive health check
  --check TEXT               Check specific components
  --resources                Show resource usage
  --report                   Generate diagnostic report
  --output PATH              Report output file
```

### Configuration Schema

#### Root Configuration
```yaml
# ~/.localagent/config.yaml
providers:              # Provider configurations
  <provider_name>:
    <provider_config>

system:                 # System settings
  default_provider: string
  max_parallel_agents: integer
  log_level: string
  
plugins:               # Plugin configuration
  enabled_plugins: [string]
  auto_load_plugins: boolean
  
caching:               # Caching settings
  enabled: boolean
  ttl: integer
  
workflow:              # Workflow settings
  max_iterations: integer
  evidence_collection: boolean
```

#### Provider Configuration Schema
```yaml
providers:
  ollama:
    base_url: string
    timeout: integer
    default_model: string
    max_retries: integer
    
  openai:
    api_key: string
    base_url: string
    default_model: string
    timeout: integer
    organization: string
    
  gemini:
    api_key: string
    default_model: string
    safety_settings: object
    
  perplexity:
    api_key: string
    default_model: string
    search_domain_filter: [string]
```

### Environment Variables

#### Provider Variables
```bash
# Ollama
LOCALAGENT_OLLAMA_BASE_URL
LOCALAGENT_OLLAMA_DEFAULT_MODEL
LOCALAGENT_OLLAMA_TIMEOUT

# OpenAI
LOCALAGENT_OPENAI_API_KEY
LOCALAGENT_OPENAI_DEFAULT_MODEL
LOCALAGENT_OPENAI_BASE_URL
LOCALAGENT_OPENAI_ORGANIZATION

# Gemini
LOCALAGENT_GEMINI_API_KEY
LOCALAGENT_GEMINI_DEFAULT_MODEL

# Perplexity
LOCALAGENT_PERPLEXITY_API_KEY
LOCALAGENT_PERPLEXITY_DEFAULT_MODEL
```

#### System Variables
```bash
# Core System
LOCALAGENT_DEFAULT_PROVIDER
LOCALAGENT_MAX_PARALLEL_AGENTS
LOCALAGENT_LOG_LEVEL
LOCALAGENT_CONFIG_DIR

# Plugin System
LOCALAGENT_PLUGINS_ENABLED
LOCALAGENT_PLUGINS_AUTO_LOAD
LOCALAGENT_PLUGINS_ALLOW_DEV

# Performance
LOCALAGENT_MAX_MEMORY
LOCALAGENT_MAX_CPU_PERCENT
LOCALAGENT_CACHING_ENABLED

# Security
LOCALAGENT_ENABLE_AUDIT_LOG
LOCALAGENT_KEYRING_SERVICE
```

### Exit Codes

| Code | Description |
|------|-------------|
| 0    | Success |
| 1    | General error |
| 2    | Configuration error |
| 3    | Provider connection error |
| 4    | Workflow execution error |
| 5    | Plugin error |
| 6    | Permission error |
| 7    | Resource exhaustion |
| 8    | Network error |
| 9    | Authentication error |
| 10   | Validation error |

---

This comprehensive guide covers all aspects of the LocalAgent CLI Toolkit. For additional support, consult the troubleshooting section or reach out to the development team.