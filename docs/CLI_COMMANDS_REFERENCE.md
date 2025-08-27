# LocalAgent CLI Commands Reference

## Table of Contents
- [Command Structure](#command-structure)
- [Global Options](#global-options)
- [Core Commands](#core-commands)
- [Configuration Commands](#configuration-commands)
- [Provider Management](#provider-management)
- [Workflow Execution](#workflow-execution)
- [Interactive Chat](#interactive-chat)
- [Plugin Management](#plugin-management)
- [System Health & Diagnostics](#system-health--diagnostics)
- [Development & Debug Commands](#development--debug-commands)
- [Extended Commands (Plugins)](#extended-commands-plugins)
- [Command Examples](#command-examples)
- [Exit Codes](#exit-codes)

---

## Command Structure

LocalAgent follows a hierarchical command structure with consistent patterns and intuitive organization.

### Basic Command Syntax
```bash
localagent [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

### Command Categories
```bash
Core Operations:
  init                    # System initialization and setup
  config                  # Configuration management
  providers               # Provider management and health checks
  workflow                # 12-phase workflow execution
  chat                    # Interactive chat sessions
  
System Management:
  health                  # System diagnostics and monitoring
  plugins                 # Plugin management and discovery
  logs                    # Log management and analysis
  performance             # Performance monitoring and optimization
  
Development Tools:
  debug                   # Debugging and diagnostic tools
  test                    # Testing framework integration
  profile                 # Performance profiling
  
Extended (Plugin-based):
  security-scan           # Security vulnerability scanning
  export-tools            # Data export and archiving
  dev-tools               # Developer utilities
```

---

## Global Options

These options are available for all commands and control overall behavior.

### Universal Global Options
```bash
--config PATH           # Custom configuration file path
                       # Default: ~/.localagent/config.yaml
                       # Environment: LOCALAGENT_CONFIG_FILE

--log-level LEVEL       # Set logging level
                       # Choices: DEBUG, INFO, WARNING, ERROR, CRITICAL
                       # Default: INFO
                       # Environment: LOCALAGENT_LOG_LEVEL

--no-plugins           # Disable plugin loading
                       # Useful for troubleshooting plugin issues

--debug                # Enable debug mode with verbose output
                       # Environment: LOCALAGENT_DEBUG=true

--working-dir PATH     # Set working directory for operations
                       # Default: current directory
                       # Environment: LOCALAGENT_WORKING_DIR

--provider PROVIDER    # Override default provider for this command
                       # Choices: ollama, openai, gemini, perplexity
                       # Environment: LOCALAGENT_DEFAULT_PROVIDER

--format FORMAT        # Output format for command results
                       # Choices: rich, json, yaml, table
                       # Default: rich (colored terminal output)

--quiet, -q            # Suppress non-essential output
                       # Only show errors and final results

--verbose, -v          # Verbose output with additional details
                       # Opposite of --quiet

--help, -h             # Show command help and exit

--version              # Show version information and exit
```

### Global Option Examples
```bash
# Use custom configuration
localagent --config ~/project/.localagent.yaml workflow "Fix bug"

# Debug mode with verbose logging
localagent --debug --log-level DEBUG providers --health

# JSON output for scripting
localagent --format json --quiet providers --list

# Override default provider
localagent --provider openai chat --session debugging

# Set working directory
localagent --working-dir /path/to/project workflow "Code review"
```

---

## Core Commands

### `init` - Initialize LocalAgent Configuration

Initialize LocalAgent with interactive or automated configuration setup.

#### Syntax
```bash
localagent init [OPTIONS]
```

#### Options
```bash
-f, --force            # Force reinitialize (overwrite existing config)
--template PATH        # Use configuration template file
--minimal              # Create minimal configuration (basic providers only)
--interactive / --no-interactive
                      # Interactive mode (default) vs batch mode
--providers LIST      # Comma-separated list of providers to configure
--skip-api-keys       # Skip API key configuration (use later)
--config-dir PATH     # Custom configuration directory
```

#### Examples
```bash
# Interactive setup (default)
localagent init

# Force reinitialize with existing config
localagent init --force

# Minimal configuration for development
localagent init --minimal --no-interactive

# Setup specific providers only
localagent init --providers ollama,openai --interactive

# Use company configuration template
localagent init --template company-config-template.yaml

# Setup in custom directory
localagent init --config-dir /opt/localagent/config
```

#### Interactive Flow
```
LocalAgent Configuration Setup

✓ Configuration directory: /home/user/.localagent
✓ Creating default configuration structure

Provider Configuration:
? Configure Ollama provider? (Y/n) y
  Ollama URL [http://localhost:11434]: 
  Default model [llama3.1]: 

? Configure OpenAI provider? (Y/n) y
  OpenAI API Key (will be stored securely): ***
  Default model [gpt-4]: 
  Organization ID (optional): 

? Configure Google Gemini provider? (Y/n) n
? Configure Perplexity provider? (Y/n) n

System Configuration:
  Default provider [ollama]: 
  Max parallel agents [10]: 
  Enable audit logging? (Y/n) y

Plugin Configuration:
? Enable built-in plugins? (Y/n) y
  [✓] workflow-automation
  [✓] security-scanner
  [ ] export-tools
  [ ] dev-tools

✓ Configuration saved successfully!
✓ API keys stored in system keyring
✓ Ready to use LocalAgent

Run 'localagent health' to verify setup.
```

---

### `config` - Configuration Management

Manage LocalAgent configuration including viewing, validating, and modifying settings.

#### Syntax
```bash
localagent config [SUBCOMMAND] [OPTIONS]
```

#### Subcommands
```bash
show                   # Display current configuration
validate               # Validate configuration integrity
export                 # Export configuration to file
import                 # Import configuration from file
reset                  # Reset to default configuration
migrate-credentials    # Migrate API keys to secure storage
set                    # Set configuration value
get                    # Get configuration value
```

#### `config show` Options
```bash
--section SECTION      # Show specific configuration section
                      # Choices: providers, system, plugins, caching, logging
--format FORMAT       # Output format (rich, json, yaml)
--verbose             # Show detailed information including sources
--secrets             # Show masked secrets (for debugging)
```

#### `config validate` Options
```bash
--fix                 # Attempt to fix common configuration issues
--comprehensive       # Perform deep validation including provider connectivity
--check-credentials   # Validate API key accessibility
--output PATH         # Save validation report to file
```

#### `config export/import` Options
```bash
--output PATH         # Output file path (export)
--input PATH          # Input file path (import)
--encrypted           # Use encryption for sensitive data
--backup              # Create backup before import
--merge               # Merge with existing config instead of replacing
```

#### Examples
```bash
# Show current configuration
localagent config show

# Show only provider configuration
localagent config show --section providers

# Show configuration with source information
localagent config show --verbose

# Validate configuration
localagent config validate

# Validate and fix issues
localagent config validate --fix --comprehensive

# Export configuration
localagent config export --output config-backup.yaml --encrypted

# Import configuration with backup
localagent config import --input company-config.yaml --backup

# Set configuration value
localagent config set system.max_parallel_agents 15

# Get configuration value
localagent config get providers.ollama.base_url

# Migrate API keys to keyring
localagent config migrate-credentials

# Reset to defaults (with confirmation)
localagent config reset --confirm
```

---

## Provider Management

### `providers` - LLM Provider Management

Manage and monitor LLM providers including health checks, model listing, and connectivity testing.

#### Syntax
```bash
localagent providers [OPTIONS]
```

#### Options
```bash
-l, --list             # List all configured providers
--health               # Check provider health and connectivity
--models               # List available models for providers
-p, --provider NAME    # Target specific provider
--info                 # Show detailed provider information
--test                 # Test provider with sample request
--verbose             # Show detailed output
--format FORMAT       # Output format (rich, json, yaml, table)
--timeout SECONDS     # Connection timeout for health checks
```

#### Examples
```bash
# List all providers
localagent providers --list

# Check health of all providers
localagent providers --health

# Check specific provider health
localagent providers --provider ollama --health

# List models for all providers
localagent providers --models

# List models for specific provider
localagent providers --provider openai --models

# Detailed provider information
localagent providers --provider gemini --info --verbose

# Test provider connectivity
localagent providers --provider perplexity --test

# JSON output for automation
localagent providers --health --format json

# Comprehensive provider report
localagent providers --list --health --models --verbose
```

#### Output Examples
```bash
# Provider list output
┏━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Provider   ┃ Status     ┃ Models        ┃ Default Model       ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ ollama     │ ✅ Healthy │ 5 available   │ llama3.1           │
│ openai     │ ✅ Healthy │ 12 available  │ gpt-4              │
│ gemini     │ ✅ Healthy │ 3 available   │ gemini-1.5-pro     │
│ perplexity │ ❌ Offline │ 0 available   │ N/A                │
└────────────┴────────────┴───────────────┴─────────────────────┘

# Health check output with details
Provider Health Status:

Ollama (http://localhost:11434):
  ✅ Connection: OK (47ms)
  ✅ Authentication: Not required
  ✅ Models: 5 available
     • llama3.1 (7B) - Default
     • codellama (13B)
     • mistral (7B)
  📊 Performance: Avg response 1.2s
  💾 Memory: 2.1GB used

OpenAI (api.openai.com):
  ✅ Connection: OK (123ms)  
  ✅ Authentication: Valid API key
  ✅ Models: 12 available
     • gpt-4 - Default
     • gpt-4-turbo
     • gpt-3.5-turbo
  📊 Performance: Avg response 3.4s
  💰 Cost: $0.03 per 1K tokens (gpt-4)
  ⚠️  Rate limit: 60 req/min

Perplexity (api.perplexity.ai):
  ❌ Connection: Timeout after 30s
  ❌ Authentication: Cannot verify
  ❌ Models: Unable to fetch
  🔍 Troubleshoot: Check API key and network connectivity
```

---

## Workflow Execution

### `workflow` - Execute 12-Phase UnifiedWorkflow

Execute comprehensive 12-phase workflows with parallel agent orchestration.

#### Syntax
```bash
localagent workflow PROMPT [OPTIONS]
```

#### Arguments
```bash
PROMPT                 # Workflow description/prompt (required)
                      # Examples:
                      #   "Fix authentication system"
                      #   "Add dark mode support"
                      #   "Optimize database queries"
```

#### Options
```bash
-p, --provider PROVIDER # LLM provider to use
                       # Choices: ollama, openai, gemini, perplexity
                       # Default: from configuration

--phases PHASES        # Specific phases to run (comma-separated)
                      # Format: "1,2,3" or "1-5,8-9"
                      # Default: all phases (0-9)

--parallel / --sequential
                      # Enable/disable parallel execution
                      # Default: parallel (from config)

--max-agents INTEGER  # Maximum parallel agents
                      # Default: 10 (from config)
                      # Range: 1-50

--format FORMAT       # Output format
                      # Choices: rich, json, yaml, report
                      # Default: rich

--save PATH           # Save detailed report to file
                      # Auto-detects format from extension

--context TEXT        # Additional context as JSON string
                      # Example: '{"urgency":"high","env":"prod"}'

--context-file PATH   # Load context from file
                      # Supports JSON and YAML formats

--dry-run             # Plan workflow without execution
                      # Shows execution plan and resource estimates

--resume WORKFLOW_ID  # Resume previous workflow from checkpoint
                      # Continues from last successful phase

--timeout SECONDS     # Overall workflow timeout
                      # Default: 3600 (1 hour)

--evidence            # Enable comprehensive evidence collection
                      # Default: true (from config)

--auto-commit         # Auto-commit results to git (if in repo)
                      # Requires git repository

--watch               # Monitor workflow in real-time
                      # Opens live progress dashboard
```

#### Examples
```bash
# Basic workflow execution
localagent workflow "Fix login authentication bug"

# Use specific provider
localagent workflow "Code security audit" --provider openai

# Run specific phases only
localagent workflow "Quick code review" --phases "1,2,6,7"

# High-performance parallel execution
localagent workflow "Large refactoring project" \
  --provider gemini \
  --parallel \
  --max-agents 20 \
  --timeout 7200

# Workflow with context
localagent workflow "Deploy to production" \
  --context '{"environment":"prod","deployment_type":"blue-green","notify_team":true}'

# Load context from file
localagent workflow "Database migration" \
  --context-file ./migration-context.yaml

# Save detailed report
localagent workflow "Performance optimization" \
  --save performance-report-$(date +%Y%m%d).json \
  --format json

# Dry run to see execution plan
localagent workflow "Complex feature implementation" \
  --dry-run \
  --provider openai

# Resume previous workflow
localagent workflow resume --workflow-id abc123-def456

# Auto-commit results
localagent workflow "Bug fixes" \
  --auto-commit \
  --context '{"branch":"bugfix/auth-issues"}'

# Monitor with live dashboard
localagent workflow "System health check" \
  --watch \
  --parallel
```

#### Workflow Phase Reference
```bash
Phase 0: Interactive Prompt Engineering & Environment Setup
  - User prompt confirmation and refinement
  - Environment validation and setup
  - Todo context integration
  - Background system preparation

Phase 1: Parallel Research & Discovery
  - Documentation research (online best practices)
  - Codebase analysis (structure, dependencies, patterns)
  - Runtime analysis (logs, metrics, performance)
  - Security assessment (vulnerabilities, compliance)

Phase 2: Strategic Planning & Stream Design  
  - Research synthesis and analysis
  - Execution stream design
  - Resource allocation planning
  - Integration strategy development

Phase 3: Context Package Creation & Distribution
  - Agent-specific context packages (max 4000 tokens)
  - Task distribution and specialization
  - Communication protocol establishment
  - Dependency resolution

Phase 4: Parallel Stream Execution
  - Multi-stream parallel agent execution
  - Real-time progress coordination
  - Cross-stream communication
  - Quality assurance and validation

Phase 5: Integration & Merge
  - Stream result consolidation
  - Conflict resolution
  - Integration testing
  - Rollback preparation

Phase 6: Comprehensive Testing & Validation
  - Unit and integration testing
  - Security validation
  - Performance benchmarking
  - User acceptance criteria

Phase 7: Audit, Learning & Improvement
  - Process effectiveness analysis
  - Performance optimization
  - Knowledge base updates
  - Best practice documentation

Phase 8: Cleanup & Documentation
  - File organization (15-file root limit)
  - Documentation updates
  - Dependency consolidation
  - System cleanup

Phase 9: Development Deployment
  - Build process execution
  - Development environment deployment
  - Monitoring setup
  - Success validation
```

#### Workflow Output Examples
```bash
# Rich terminal output (default)
╭─────────────────────────────────────────────────────────╮
│                  LocalAgent Workflow                    │
│               Fix authentication system                 │
╰─────────────────────────────────────────────────────────╯

Phase 0: Interactive Prompt Engineering ✓
└─ Prompt confirmed and refined (2.3s)

Phase 1: Parallel Research & Discovery ⚡
├─ Documentation Research ████████████ 100% (15.2s)
├─ Codebase Analysis     ████████████ 100% (18.7s)  
├─ Runtime Analysis      ████████████ 100% (12.4s)
└─ Security Assessment   ████████████ 100% (21.1s)

Phase 2: Strategic Planning ✓
└─ Execution strategy designed (8.9s)

Phase 4: Parallel Stream Execution ⚡
├─ Backend Security     ████████████ 100% ✓
├─ Frontend Integration ████████████ 100% ✓  
├─ Database Updates     ████████████ 100% ✓
└─ Testing Suite        ████████████ 100% ✓

[... phases continue ...]

Workflow Summary:
✅ Phases completed: 9/9 (100%)
⏱️  Total duration: 4m 23s
👥 Agents deployed: 12
📊 Success rate: 100%
📋 Evidence collected: 47 items
🔒 Security validated: ✅
```

---

## Interactive Chat

### `chat` - Interactive Chat Sessions

Start interactive chat sessions with LLM providers for conversational AI assistance.

#### Syntax
```bash
localagent chat [OPTIONS]
```

#### Options
```bash
-p, --provider PROVIDER # LLM provider to use
                       # Choices: ollama, openai, gemini, perplexity
                       # Default: from configuration

-m, --model MODEL      # Specific model to use
                      # Provider-specific model names
                      # Default: provider default

--session NAME        # Named session for history persistence
                      # Sessions saved to ~/.localagent/sessions/
                      # Default: "default"

--context TEXT        # Initial context as JSON string
                      # Sets conversation context

--context-file PATH   # Load initial context from file
                      # Supports JSON and YAML

--list-sessions       # List available saved sessions and exit

--restore-session NAME # Restore previous session
                      # Loads conversation history

--max-history INTEGER # Maximum conversation history to maintain
                      # Default: 50 messages

--temperature FLOAT   # Model temperature (creativity)
                      # Range: 0.0-2.0, Default: 0.7

--max-tokens INTEGER  # Maximum tokens per response
                      # Default: 2000

--streaming / --no-streaming
                      # Enable/disable response streaming
                      # Default: streaming

--save-on-exit        # Save session when exiting
                      # Default: true

--export-format FORMAT # Format for session export
                      # Choices: json, markdown, text
                      # Used with /export command
```

#### Examples
```bash
# Basic interactive chat
localagent chat

# Use specific provider and model
localagent chat --provider openai --model gpt-4

# Named session with context
localagent chat \
  --session project-review \
  --context '{"project":"web-api","language":"python"}' \
  --provider gemini

# Load context from file
localagent chat \
  --context-file ./project-context.json \
  --session debugging

# Restore previous session
localagent chat --session project-review --restore-session

# List available sessions
localagent chat --list-sessions

# High creativity mode
localagent chat \
  --temperature 1.2 \
  --max-tokens 3000 \
  --provider openai

# Focused analysis mode
localagent chat \
  --temperature 0.2 \
  --max-tokens 1000 \
  --provider ollama \
  --session code-analysis
```

#### Interactive Chat Commands

While in chat mode, use these slash commands:

#### Session Management
```bash
/help                  # Show available commands and usage
/clear                 # Clear conversation history (keep session)
/save [NAME]          # Save current session with optional name
/load NAME            # Load saved session
/sessions             # List all saved sessions  
/new SESSION_NAME     # Start new named session
/export [FORMAT]      # Export session (json, markdown, text)
/exit                 # Exit chat mode
```

#### Provider/Model Management  
```bash
/providers            # List available providers and status
/provider PROVIDER    # Switch to different provider
/models               # List models for current provider
/model MODEL          # Switch to specific model
/settings             # Show current session settings
/temperature VALUE    # Set model temperature (0.0-2.0)
/max-tokens VALUE     # Set maximum response tokens
```

#### Context Management
```bash
/context              # Show current context and token usage
/context-reset        # Reset conversation context
/context-add TEXT     # Add text to conversation context
/context-file PATH    # Load context from file  
/context-save PATH    # Save current context to file
/history              # Show conversation history
/history-clear        # Clear conversation history
/tokens               # Show token usage statistics
```

#### File Operations
```bash
/files                # List files in current directory
/cd PATH              # Change working directory  
/pwd                  # Show current working directory
/read FILE            # Read file and add to conversation
/edit FILE            # Edit file with AI assistance
/write FILE CONTENT   # Write content to file
/diff FILE1 FILE2     # Compare two files
/search PATTERN       # Search files in current directory
```

#### Advanced Features
```bash
/workflow PROMPT      # Execute workflow from chat
/analyze TOPIC        # Perform structured analysis
/summarize [LENGTH]   # Summarize conversation (short/medium/long)  
/translate LANG       # Translate last response to language
/explain [LEVEL]      # Explain concept (basic/intermediate/advanced)
/debug                # Enable debug mode for troubleshooting
/performance          # Show performance metrics
/stream on|off        # Enable/disable response streaming
```

#### Chat Session Examples
```bash
# Starting chat session
$ localagent chat --session development --provider ollama

LocalAgent Chat Session: development
Provider: ollama (llama3.1)  
Type /help for commands or start chatting!

You: Can you help me understand this authentication error?

Assistant (llama3.1): I'd be happy to help you debug authentication errors! 
To provide the most accurate assistance, could you share:

1. The specific error message you're seeing
2. Which authentication method you're using (JWT, OAuth, etc.)
3. Where the error occurs (login, API call, etc.)

You can use `/read error.log` to share log files, or `/read auth.py` 
to show the authentication code.

You: /read auth.log

[Reading auth.log...]

# File shows JWT token validation errors
# Analysis of authentication patterns...

You: /summarize
Assistant: Based on our conversation about JWT authentication errors:

**Summary**: You're experiencing JWT token validation failures. The logs show expired tokens and signature mismatches. Key issues identified:
1. Token expiration handling needs improvement
2. Secret key rotation may be causing signature validation issues
3. Clock synchronization between services might be off

**Recommendations**:
- Implement proper token refresh logic
- Verify JWT secret consistency across services
- Check system clock synchronization

You: /save debugging-session-2024
Session saved successfully!

You: /exit
Chat session ended. Session auto-saved as 'development'.
```

---

## Plugin Management

### `plugins` - Plugin System Management

Discover, manage, and configure LocalAgent plugins for extended functionality.

#### Syntax
```bash
localagent plugins [OPTIONS]
```

#### Options
```bash
-l, --list             # List discovered plugins
--enabled              # Show only enabled plugins
--available            # Show only available (not loaded) plugins
--loaded               # Show only currently loaded plugins

--enable PLUGIN        # Enable specific plugin
--disable PLUGIN       # Disable specific plugin
--reload PLUGIN        # Reload plugin (useful for development)

--info PLUGIN          # Show detailed plugin information
--config PLUGIN        # Show plugin configuration schema
--test PLUGIN          # Test plugin functionality

--discover             # Force plugin discovery refresh
--install PATH         # Install plugin from path/URL
--uninstall PLUGIN     # Uninstall plugin

--verbose              # Show detailed output
--format FORMAT        # Output format (rich, json, yaml, table)
```

#### Examples
```bash
# List all plugins
localagent plugins --list

# Show only enabled plugins
localagent plugins --list --enabled

# Enable plugin
localagent plugins --enable security-scanner

# Disable plugin
localagent plugins --disable export-tools

# Show plugin information
localagent plugins --info workflow-automation --verbose

# Test plugin functionality
localagent plugins --test security-scanner

# Show plugin configuration schema
localagent plugins --config dev-tools

# Reload plugin during development
localagent plugins --reload custom-plugin

# Install plugin from directory
localagent plugins --install ./my-custom-plugin

# Force discovery refresh
localagent plugins --discover

# JSON output for automation
localagent plugins --list --format json
```

#### Plugin Management Examples
```bash
# Plugin list output
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Plugin               ┃ Version ┃ Status  ┃ Description                         ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ workflow-automation  │ 1.2.0   │ ✅ Loaded │ Advanced workflow automation tools  │
│ security-scanner     │ 2.1.3   │ ✅ Loaded │ Security vulnerability scanning     │
│ export-tools        │ 1.0.5   │ ⭕ Enabled│ Export workflows and configurations │
│ dev-tools           │ 1.4.2   │ ❌ Disabled│ Developer debugging utilities       │
│ custom-analysis     │ 0.9.1   │ 🔄 Loading│ Custom project analysis tools      │
└──────────────────────┴─────────┴─────────┴─────────────────────────────────────┘

# Plugin information output
Plugin Information: security-scanner

Basic Info:
  Name: security-scanner
  Version: 2.1.3
  Type: Command Plugin
  Author: LocalAgent Team
  License: MIT
  
Description:
  Comprehensive security vulnerability scanning for codebases.
  Supports OWASP Top 10, dependency scanning, and compliance reporting.

Commands Added:
  • security-scan     - Scan codebase for vulnerabilities
  • vulnerability-check - Check specific vulnerability types
  • compliance-report - Generate compliance reports

Configuration Schema:
  scan_depth: [shallow, medium, deep] (default: medium)
  exclude_patterns: array of strings
  severity_threshold: [low, medium, high, critical] (default: medium)
  include_dependencies: boolean (default: true)
  
Dependencies:
  • Python packages: bandit, safety, semgrep
  • External tools: npm audit, yarn audit
  
Status: ✅ Loaded and operational
Last loaded: 2024-01-15 14:23:45
```

---

## System Health & Diagnostics

### `health` - System Health Monitoring

Monitor LocalAgent system health, performance, and component status.

#### Syntax  
```bash
localagent health [OPTIONS]
```

#### Options
```bash
--comprehensive        # Perform comprehensive health check
                      # Includes all components, connectivity, performance

--quick               # Quick health check (essential components only)
                      # Default mode for regular monitoring

--components LIST     # Check specific components (comma-separated)
                      # Choices: providers, plugins, config, cache, logs, performance

--resources           # Show system resource usage
                      # CPU, memory, disk, network

--performance         # Show performance metrics
                      # Response times, throughput, error rates

--connectivity        # Test connectivity to external services
                      # Provider APIs, update servers, etc.

--fix                 # Attempt to fix detected issues automatically
                      # Safe repairs only (no destructive changes)

--report              # Generate detailed health report
                      # Saves comprehensive system status

--output PATH         # Save health report to file
                      # Auto-detects format from extension

--format FORMAT       # Output format (rich, json, yaml)
                      # Default: rich

--watch               # Continuous monitoring mode
                      # Updates every 5 seconds

--threshold LEVEL     # Alert threshold level
                      # Choices: low, medium, high
```

#### Examples
```bash
# Quick health check
localagent health

# Comprehensive system health check  
localagent health --comprehensive

# Check specific components
localagent health --components providers,plugins,performance

# Show resource usage
localagent health --resources

# Test connectivity
localagent health --connectivity

# Generate detailed report
localagent health --comprehensive --report --output health-report.json

# Continuous monitoring
localagent health --watch --resources

# Fix issues automatically
localagent health --comprehensive --fix

# Performance-focused check
localagent health --performance --verbose
```

#### Health Check Output Examples
```bash
# Quick health check
LocalAgent System Health Check

✅ Core System: Operational
  ├─ Configuration: Valid
  ├─ Plugins: 4/5 loaded successfully  
  └─ Logging: Active

✅ Providers: 3/4 healthy
  ├─ ✅ ollama: Healthy (47ms response)
  ├─ ✅ openai: Healthy (123ms response)  
  ├─ ✅ gemini: Healthy (89ms response)
  └─ ⚠️  perplexity: Connection timeout

⚠️  Performance: Moderate load
  ├─ CPU: 45% usage
  ├─ Memory: 78% usage (3.2GB/4GB)
  └─ Active workflows: 2

Overall Status: Healthy with minor issues
Recommendations: 
  • Check perplexity API connectivity
  • Consider memory cleanup (78% usage)

# Comprehensive health report
╭─────────────────────────────────────────────────────────╮
│             LocalAgent Comprehensive Health Report      │
╰─────────────────────────────────────────────────────────╯

System Information:
  Version: 1.2.0
  Python: 3.11.5  
  OS: Ubuntu 22.04 LTS
  Uptime: 2 days, 14 hours

Configuration Health: ✅ Excellent
  ├─ Config file: ~/.localagent/config.yaml ✅
  ├─ Validation: All checks passed ✅
  ├─ API keys: 3/4 accessible via keyring ✅
  └─ Permissions: Appropriate access levels ✅

Provider Health: ⚠️ Mostly Healthy (3/4)
  ┏━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ Provider   ┃ Status  ┃ Response    ┃ Last Check              ┃
  ┡━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
  │ ollama     │ ✅ Healthy│ 47ms       │ 2024-01-15 14:30:12    │
  │ openai     │ ✅ Healthy│ 123ms      │ 2024-01-15 14:30:15    │
  │ gemini     │ ✅ Healthy│ 89ms       │ 2024-01-15 14:30:18    │
  │ perplexity │ ❌ Error  │ Timeout    │ 2024-01-15 14:30:21    │
  └────────────┴─────────┴─────────────┴────────────────────────┘

Plugin System: ✅ Healthy (4/5 loaded)
  ├─ ✅ workflow-automation (1.2.0): Loaded successfully
  ├─ ✅ security-scanner (2.1.3): Loaded successfully  
  ├─ ✅ export-tools (1.0.5): Loaded successfully
  ├─ ✅ dev-tools (1.4.2): Loaded successfully
  └─ ❌ custom-analysis (0.9.1): Load failed - dependency missing

System Resources: ⚠️ Moderate Usage
  ├─ CPU Usage: 45% (4 cores)
  ├─ Memory: 78% (3.2GB/4GB used)
  ├─ Disk: 65% (125GB/192GB used)  
  └─ Network: Normal activity

Performance Metrics:
  ├─ Average workflow time: 4m 23s
  ├─ Provider response time: 86ms avg
  ├─ Cache hit rate: 73%
  ├─ Active workflows: 2
  └─ Error rate: 0.3% (last 24h)

Security Status: ✅ Secure
  ├─ API keys: Securely stored in keyring
  ├─ File permissions: Correct (644/755)
  ├─ Audit logging: Active
  └─ Update status: Current (last check: 3h ago)

Recommendations:
  🔧 Fix perplexity provider connectivity (check API key)
  🧹 Consider memory cleanup (78% usage - threshold 80%)
  🔌 Resolve custom-analysis plugin dependency
  📊 Memory usage trending upward - monitor closely
  
Overall Health: ⚠️ Good with minor issues
Risk Level: Low
```

---

## Development & Debug Commands

### `debug` - Debugging and Diagnostic Tools

Advanced debugging tools for troubleshooting LocalAgent issues and development.

#### Syntax
```bash
localagent debug [SUBCOMMAND] [OPTIONS]
```

#### Subcommands
```bash
workflow                # Debug workflow execution
providers               # Debug provider connectivity  
plugins                 # Debug plugin issues
config                  # Debug configuration problems
memory                  # Memory usage analysis
logs                    # Log analysis and filtering
performance             # Performance profiling
network                 # Network connectivity debugging
```

#### `debug workflow` Options
```bash
--workflow-id ID       # Debug specific workflow
--phase PHASE          # Debug specific phase
--agent AGENT          # Debug specific agent
--trace                # Enable execution tracing
--breakpoint PHASE     # Set breakpoint at phase
--interactive          # Interactive debugging session
```

#### `debug providers` Options
```bash
--provider PROVIDER    # Debug specific provider
--test-request         # Send test request
--check-auth          # Verify authentication
--network-trace       # Network request tracing
--timeout SECONDS     # Connection timeout for testing
```

#### Examples
```bash
# Debug workflow execution
localagent debug workflow --workflow-id abc123 --trace

# Interactive workflow debugging
localagent debug workflow --interactive --breakpoint 4

# Debug provider connectivity
localagent debug providers --provider openai --network-trace

# Memory usage analysis
localagent debug memory --detailed --save memory-report.json

# Log analysis  
localagent debug logs --level error --since 24h --pattern "auth|token"

# Plugin debugging
localagent debug plugins --plugin security-scanner --verbose

# Performance profiling
localagent debug performance --workflow "test task" --duration 300

# Network connectivity troubleshooting
localagent debug network --all-providers --trace
```

---

## Extended Commands (Plugins)

These commands are provided by plugins and may not be available depending on your plugin configuration.

### `security-scan` - Security Vulnerability Scanning

Comprehensive security analysis of codebases and configurations.

#### Syntax
```bash
localagent security-scan [OPTIONS] [PATH]
```

#### Options
```bash
--depth LEVEL          # Scan depth: shallow, medium, deep
                      # Default: medium

--severity LEVEL       # Minimum severity to report
                      # Choices: low, medium, high, critical
                      # Default: medium

--exclude PATTERNS     # Exclude patterns (comma-separated)
                      # Example: "*.test.js,node_modules/*"

--include-deps         # Include dependency scanning
                      # Default: true

--format FORMAT       # Output format: rich, json, sarif
                      # Default: rich

--output PATH         # Save scan results to file

--fix                 # Attempt to fix issues automatically
                      # Safe fixes only

--compliance STANDARD # Check compliance (owasp, pci, sox)
                      # Can be used multiple times
```

#### Examples
```bash
# Basic security scan
localagent security-scan ./src

# Deep scan with high severity threshold  
localagent security-scan --depth deep --severity high

# Compliance-focused scan
localagent security-scan --compliance owasp --compliance pci --output compliance-report.json

# Scan with auto-fix
localagent security-scan --fix --exclude "*.test.js"
```

### `export-tools` - Data Export and Archiving

Export workflows, configurations, and session data in various formats.

#### Syntax
```bash
localagent export-tools [SUBCOMMAND] [OPTIONS]
```

#### Subcommands
```bash
workflow               # Export workflow results
config                 # Export configuration
sessions               # Export chat sessions
all                    # Export everything
```

#### Options
```bash
--format FORMAT        # Export format: json, yaml, html, pdf
--output PATH          # Output file or directory
--compressed           # Create compressed archive
--encrypted           # Encrypt exported data
--include ITEMS       # Items to include (comma-separated)
--exclude ITEMS       # Items to exclude (comma-separated)
--since TIMESPEC      # Export items since time (e.g., "7d", "2024-01-01")
```

#### Examples
```bash
# Export workflow results as HTML report
localagent export-tools workflow --workflow-id abc123 --format html --output report.html

# Export configuration with encryption
localagent export-tools config --encrypted --output secure-config.yaml

# Export all data compressed
localagent export-tools all --compressed --output localagent-backup-$(date +%Y%m%d).tar.gz

# Export recent sessions
localagent export-tools sessions --since 30d --format json --output recent-sessions.json
```

---

## Command Examples

### Common Use Cases

#### Development Workflow
```bash
# Initialize project
cd /path/to/project
localagent init --template development

# Check system health
localagent health --quick

# Start development session
localagent chat --session project-dev --provider ollama

# Run code analysis workflow
localagent workflow "Comprehensive code analysis and optimization" \
  --provider openai \
  --save analysis-report.json \
  --auto-commit

# Security scan before deployment
localagent security-scan --depth deep --severity high --compliance owasp
```

#### Debugging Session
```bash  
# Check provider connectivity
localagent providers --health --verbose

# Debug authentication issues
localagent debug workflow --workflow-id failed-workflow --trace

# Analyze logs for errors
localagent debug logs --level error --since 1h --pattern "auth|token"

# Memory usage investigation  
localagent debug memory --detailed

# Interactive debugging
localagent debug workflow --interactive
```

#### Production Deployment
```bash
# Validate configuration
localagent config validate --comprehensive --fix

# Pre-deployment health check
localagent health --comprehensive --connectivity

# Deploy with monitoring
localagent workflow "Production deployment validation" \
  --provider gemini \
  --context '{"env":"production","safety_checks":true}' \
  --evidence \
  --save deployment-report.json

# Post-deployment verification
localagent workflow "Post-deployment health verification" \
  --phases "1,6,7" \
  --watch
```

#### Team Collaboration
```bash
# Export team configuration
localagent config export --output team-config-template.yaml

# Share workflow template
localagent export-tools workflow --workflow-id successful-deployment \
  --format yaml --output deployment-workflow-template.yaml

# Import team settings
localagent config import --input team-config.yaml --merge

# Validate team plugin setup
localagent plugins --list --enabled --verbose
```

#### Performance Monitoring
```bash
# Continuous health monitoring
localagent health --watch --resources --threshold medium

# Performance profiling
localagent debug performance --workflow "performance test" \
  --duration 600 --output performance-profile.html

# Resource optimization
localagent workflow "System performance optimization" \
  --provider ollama \
  --phases "1,2,6,8" \
  --max-agents 5

# Cache optimization
localagent cache stats
localagent cache optimize
```

#### Batch Operations
```bash
# Multiple provider health checks
for provider in ollama openai gemini; do
  localagent providers --provider $provider --health --verbose
done

# Batch workflow execution
localagent workflow "Code quality check" --provider ollama &
localagent workflow "Security audit" --provider openai &
localagent workflow "Performance analysis" --provider gemini &
wait

# Automated reporting
localagent export-tools all --since 24h --compressed \
  --output daily-report-$(date +%Y%m%d).tar.gz
```

---

## Exit Codes

LocalAgent uses standard exit codes to indicate command execution status.

### Standard Exit Codes
```bash
0    # Success - command completed successfully
1    # General error - unspecified error occurred  
2    # Configuration error - invalid configuration
3    # Provider error - LLM provider connectivity/authentication issue
4    # Workflow error - workflow execution failed
5    # Plugin error - plugin loading or execution failed
6    # Permission error - insufficient permissions
7    # Resource error - insufficient system resources (memory, disk, etc.)
8    # Network error - network connectivity issues
9    # Authentication error - API key or credential issues
10   # Validation error - input validation failed
11   # Timeout error - operation timed out
12   # Cancelled error - operation cancelled by user
```

### Exit Code Usage Examples
```bash
# Check command success in scripts
if localagent providers --health --quiet; then
    echo "Providers healthy"
else
    case $? in
        3) echo "Provider connectivity issue" ;;
        9) echo "Authentication problem" ;;
        *) echo "Unknown error" ;;
    esac
fi

# Workflow execution with error handling
localagent workflow "Deploy to staging" --format json --quiet
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "Deployment successful"
elif [ $RESULT -eq 4 ]; then
    echo "Workflow failed - check logs"
    localagent debug logs --level error --since 10m
elif [ $RESULT -eq 7 ]; then
    echo "Insufficient resources - check system health"
    localagent health --resources
fi

exit $RESULT
```

### CI/CD Integration with Exit Codes
```bash
# GitHub Actions example
- name: Run LocalAgent Analysis
  run: |
    localagent workflow "CI security check" --format junit --output results.xml
    
  # Continue on specific errors but fail on others
  continue-on-error: ${{ false }}
  
- name: Handle Results  
  if: always()
  run: |
    if [ $? -eq 4 ]; then
      echo "Workflow failed but continuing with deployment"
      exit 0
    elif [ $? -eq 3 ]; then
      echo "Provider issue - failing build"
      exit 1
    fi
```

---

This comprehensive CLI Commands Reference provides detailed information about all LocalAgent commands, options, and usage patterns. Each command includes practical examples and covers both basic and advanced usage scenarios for effective LocalAgent utilization.