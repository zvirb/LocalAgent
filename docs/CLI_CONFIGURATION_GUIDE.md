# LocalAgent CLI Configuration Guide

## Table of Contents
- [Overview](#overview)
- [Configuration Hierarchy](#configuration-hierarchy)
- [Configuration Sources](#configuration-sources)
- [Configuration Schema](#configuration-schema)
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Secure Credential Management](#secure-credential-management)
- [Provider Configuration](#provider-configuration)
- [Plugin Configuration](#plugin-configuration)
- [Environment-Specific Configuration](#environment-specific-configuration)
- [Configuration Management Commands](#configuration-management-commands)
- [Validation and Troubleshooting](#validation-and-troubleshooting)
- [Migration and Backup](#migration-and-backup)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [Reference](#reference)

---

## Overview

LocalAgent CLI uses a hierarchical configuration system that supports multiple sources, secure credential storage, and environment-specific settings. The system is designed for flexibility, security, and ease of management across different deployment scenarios.

### Configuration Philosophy
- **Security First**: Sensitive data stored securely using system keyring
- **Hierarchical**: Multiple configuration sources with clear precedence
- **Environment Aware**: Support for development, staging, and production environments
- **Validation**: Comprehensive configuration validation and error reporting
- **Hot Reload**: Runtime configuration updates without restart

### Key Features
- Environment variable support with `LOCALAGENT_*` prefix
- YAML configuration files with environment interpolation
- Secure keyring integration for API keys
- Plugin-specific configuration sections
- Configuration validation and migration tools
- Multi-environment support

---

## Configuration Hierarchy

LocalAgent loads configuration from multiple sources in the following order (highest to lowest priority):

```
Configuration Priority (High → Low)
├── 1. Command-line Arguments          # --provider openai, --config path
├── 2. Environment Variables           # LOCALAGENT_DEFAULT_PROVIDER=ollama
├── 3. User Configuration File         # ~/.localagent/config.yaml
├── 4. System Configuration File       # /etc/localagent/config.yaml
├── 5. Project Configuration File      # ./localagent.yaml
└── 6. Default Values                  # Built-in defaults
```

### Priority Rules
- Higher priority sources override lower priority sources
- Within configuration files, more specific settings override general settings
- Array values are merged, not replaced
- Plugin configurations are isolated and merged independently

### Configuration Resolution Example
```bash
# Example: Determining default provider
# 1. Command line: localagent --provider openai workflow "task"  → openai
# 2. Environment: LOCALAGENT_DEFAULT_PROVIDER=gemini              → gemini  
# 3. Config file: system.default_provider: ollama                → ollama
# 4. Default: ollama                                              → ollama
# Result: openai (command line wins)
```

---

## Configuration Sources

### 1. Command-Line Arguments
```bash
# Global configuration options
localagent --config /custom/config.yaml workflow "task"
localagent --log-level DEBUG providers --health
localagent --no-plugins chat

# Command-specific configuration
localagent workflow "task" --provider openai --parallel --max-agents 15
localagent chat --provider ollama --session work-session
```

### 2. Environment Variables
```bash
# Core system settings
export LOCALAGENT_DEFAULT_PROVIDER=ollama
export LOCALAGENT_MAX_PARALLEL_AGENTS=10
export LOCALAGENT_LOG_LEVEL=INFO
export LOCALAGENT_CONFIG_DIR=~/.localagent

# Provider settings
export LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
export LOCALAGENT_OPENAI_API_KEY=sk-your-key-here
export LOCALAGENT_GEMINI_API_KEY=your-gemini-key

# Plugin settings
export LOCALAGENT_PLUGINS_ENABLED=workflow-automation,security-scanner
export LOCALAGENT_PLUGINS_AUTO_LOAD=true

# Feature flags
export LOCALAGENT_ENABLE_CACHING=true
export LOCALAGENT_ENABLE_AUDIT_LOG=true
```

### 3. Configuration Files
```yaml
# ~/.localagent/config.yaml
system:
  default_provider: "ollama"
  max_parallel_agents: 10
  log_level: "INFO"
  config_dir: "~/.localagent"

providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
    timeout: 120
    
  openai:
    api_key: "${OPENAI_API_KEY}"  # Environment variable reference
    default_model: "gpt-4"
    timeout: 60
    rate_limit: 60
    
plugins:
  enabled_plugins:
    - "workflow-automation" 
    - "security-scanner"
  auto_load_plugins: true
  plugin_directories:
    - "~/.localagent/plugins"

workflow:
  max_iterations: 3
  evidence_collection: true
  auto_cleanup: true
```

---

## Configuration Schema

### Root Configuration Structure
```yaml
# Complete configuration schema
system:              # Core system settings
  default_provider: string
  max_parallel_agents: integer (1-50)
  log_level: enum [DEBUG, INFO, WARNING, ERROR]
  config_dir: path
  cache_enabled: boolean
  audit_log_enabled: boolean
  
providers:           # Provider configurations
  <provider_name>:
    <provider_config>
    
plugins:            # Plugin system configuration
  enabled_plugins: [string]
  auto_load_plugins: boolean
  plugin_directories: [path]
  allow_dev_plugins: boolean
  
workflow:           # Workflow engine settings
  max_iterations: integer
  evidence_collection: boolean
  auto_cleanup: boolean
  parallel_execution: boolean
  
caching:            # Caching configuration
  enabled: boolean
  strategy: enum [memory, redis, disk]
  ttl: integer (seconds)
  max_entries: integer
  
security:           # Security settings
  keyring_service: string
  tls_verify: boolean
  allowed_hosts: [string]
  audit_log_path: path
  
chat:              # Interactive chat settings
  default_provider: string
  max_history: integer
  auto_save: boolean
  session_timeout: integer
  
performance:       # Performance tuning
  connection_pool_size: integer
  timeout_default: integer
  rate_limit_default: integer
  memory_limit: integer (MB)
  
development:       # Development settings
  hot_reload: boolean
  debug_mode: boolean
  verbose_errors: boolean
```

### Configuration Validation
```python
# Configuration is validated using Pydantic models
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional
from pathlib import Path

class SystemConfig(BaseModel):
    default_provider: str = Field(default="ollama", regex=r'^[a-zA-Z][a-zA-Z0-9-_]*$')
    max_parallel_agents: int = Field(default=10, ge=1, le=50)
    log_level: str = Field(default="INFO", regex=r'^(DEBUG|INFO|WARNING|ERROR)$')
    config_dir: Path = Field(default_factory=lambda: Path.home() / ".localagent")
    cache_enabled: bool = Field(default=True)
    audit_log_enabled: bool = Field(default=False)
    
    @validator('config_dir')
    def config_dir_exists(cls, v):
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        return v

class ProviderConfig(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    timeout: int = Field(default=120, ge=1, le=600)
    rate_limit: Optional[int] = Field(default=None, ge=1)
    
class LocalAgentConfig(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    plugins: 'PluginConfig' = Field(default_factory=lambda: PluginConfig())
    workflow: 'WorkflowConfig' = Field(default_factory=lambda: WorkflowConfig())
    
    class Config:
        env_prefix = "LOCALAGENT_"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields for forward compatibility
```

---

## Environment Variables

### Variable Naming Convention
All LocalAgent environment variables use the `LOCALAGENT_` prefix followed by hierarchical keys:

```bash
# Pattern: LOCALAGENT_<SECTION>_<SUBSECTION>_<KEY>
LOCALAGENT_SYSTEM_DEFAULT_PROVIDER=ollama
LOCALAGENT_PROVIDERS_OLLAMA_BASE_URL=http://localhost:11434
LOCALAGENT_PLUGINS_AUTO_LOAD=true
```

### Core Environment Variables

#### System Configuration
```bash
# Core system settings
LOCALAGENT_DEFAULT_PROVIDER=ollama           # Default LLM provider
LOCALAGENT_MAX_PARALLEL_AGENTS=10            # Maximum parallel agents
LOCALAGENT_LOG_LEVEL=INFO                    # Logging level
LOCALAGENT_CONFIG_DIR=~/.localagent          # Configuration directory

# Feature toggles
LOCALAGENT_CACHE_ENABLED=true               # Enable response caching
LOCALAGENT_AUDIT_LOG_ENABLED=false          # Enable audit logging
LOCALAGENT_HOT_RELOAD=false                 # Enable hot reload (dev only)
```

#### Provider Configuration
```bash
# Ollama provider
LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
LOCALAGENT_OLLAMA_DEFAULT_MODEL=llama3.1
LOCALAGENT_OLLAMA_TIMEOUT=120

# OpenAI provider
LOCALAGENT_OPENAI_API_KEY=sk-your-key-here
LOCALAGENT_OPENAI_DEFAULT_MODEL=gpt-4
LOCALAGENT_OPENAI_BASE_URL=https://api.openai.com/v1
LOCALAGENT_OPENAI_TIMEOUT=60
LOCALAGENT_OPENAI_RATE_LIMIT=60

# Gemini provider
LOCALAGENT_GEMINI_API_KEY=your-gemini-key
LOCALAGENT_GEMINI_DEFAULT_MODEL=gemini-1.5-pro

# Perplexity provider  
LOCALAGENT_PERPLEXITY_API_KEY=pplx-your-key
LOCALAGENT_PERPLEXITY_DEFAULT_MODEL=llama-3.1-sonar-huge-128k-online
```

#### Plugin System
```bash
# Plugin configuration
LOCALAGENT_PLUGINS_ENABLED=workflow-automation,security-scanner
LOCALAGENT_PLUGINS_AUTO_LOAD=true
LOCALAGENT_PLUGINS_ALLOW_DEV=false
LOCALAGENT_PLUGINS_DIRECTORIES=~/.localagent/plugins,/opt/localagent/plugins
```

#### Performance and Security
```bash
# Performance settings
LOCALAGENT_CONNECTION_POOL_SIZE=10
LOCALAGENT_TIMEOUT_DEFAULT=120
LOCALAGENT_MEMORY_LIMIT=2048                # MB

# Security settings
LOCALAGENT_KEYRING_SERVICE=localagent
LOCALAGENT_TLS_VERIFY=true
LOCALAGENT_ALLOWED_HOSTS=api.openai.com,localhost
```

### Environment Variable Management

#### Setting Variables in Shell
```bash
# Temporary (current session only)
export LOCALAGENT_DEFAULT_PROVIDER=openai

# Persistent (add to ~/.bashrc or ~/.zshrc)
echo 'export LOCALAGENT_DEFAULT_PROVIDER=openai' >> ~/.bashrc
source ~/.bashrc

# Using .env file (supported by LocalAgent)
cat > ~/.localagent/.env << 'EOF'
LOCALAGENT_DEFAULT_PROVIDER=ollama
LOCALAGENT_MAX_PARALLEL_AGENTS=15
LOCALAGENT_LOG_LEVEL=DEBUG
EOF
```

#### Environment-Specific Variables
```bash
# Development environment
export LOCALAGENT_ENV=development
export LOCALAGENT_LOG_LEVEL=DEBUG
export LOCALAGENT_HOT_RELOAD=true
export LOCALAGENT_PLUGINS_ALLOW_DEV=true

# Production environment
export LOCALAGENT_ENV=production
export LOCALAGENT_LOG_LEVEL=WARNING
export LOCALAGENT_AUDIT_LOG_ENABLED=true
export LOCALAGENT_PLUGINS_ALLOW_DEV=false
```

---

## Configuration Files

### Main Configuration File
```yaml
# ~/.localagent/config.yaml
# Main configuration file with complete settings

# System-wide settings
system:
  default_provider: "ollama"
  max_parallel_agents: 10
  log_level: "INFO"
  config_dir: "~/.localagent"
  cache_enabled: true
  audit_log_enabled: false
  
  # Environment-specific overrides
  environments:
    development:
      log_level: "DEBUG"
      hot_reload: true
    production:
      log_level: "WARNING"
      audit_log_enabled: true

# Provider configurations
providers:
  ollama:
    base_url: "${LOCALAGENT_OLLAMA_BASE_URL:-http://localhost:11434}"
    default_model: "llama3.1"
    timeout: 120
    connection_pool_size: 5
    models:
      preferred: ["llama3.1", "codellama", "mistral"]
      fallback: ["llama3.1:7b"]
      
  openai:
    api_key: "${OPENAI_API_KEY}"  # From environment or keyring
    base_url: "https://api.openai.com/v1"
    default_model: "gpt-4"
    timeout: 60
    rate_limit: 60  # requests per minute
    models:
      cost_effective: ["gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
      high_quality: ["gpt-4", "gpt-4-turbo-preview"]
      
  gemini:
    api_key: "${GEMINI_API_KEY}"
    default_model: "gemini-1.5-pro"
    timeout: 90
    safety_settings:
      harassment: "BLOCK_MEDIUM_AND_ABOVE"
      hate_speech: "BLOCK_MEDIUM_AND_ABOVE"
      
  perplexity:
    api_key: "${PERPLEXITY_API_KEY}"
    default_model: "llama-3.1-sonar-huge-128k-online"
    timeout: 120
    search_domains: ["github.com", "stackoverflow.com", "docs.python.org"]

# Plugin system configuration
plugins:
  # Core plugin settings
  enabled_plugins:
    - "workflow-automation"
    - "security-scanner"
    - "export-tools"
  
  auto_load_plugins: true
  allow_dev_plugins: false
  plugin_directories:
    - "~/.localagent/plugins"
    - "/opt/localagent/plugins"
  
  # Plugin-specific configurations
  workflow-automation:
    enabled: true
    config:
      default_template: "standard"
      auto_save_templates: true
      
  security-scanner:
    enabled: true
    config:
      scan_depth: "deep"
      severity_threshold: "medium"
      exclude_patterns:
        - "*.test.*"
        - "node_modules/*"
        - ".git/*"

# Workflow engine configuration
workflow:
  max_iterations: 3
  evidence_collection: true
  auto_cleanup: true
  parallel_execution: true
  
  phase_settings:
    research_timeout: 300  # 5 minutes
    execution_timeout: 1800  # 30 minutes
    validation_timeout: 600  # 10 minutes
    
  agent_settings:
    max_context_tokens: 8000
    context_compression: true
    memory_optimization: true

# Caching configuration
caching:
  enabled: true
  strategy: "intelligent"  # memory, redis, disk, intelligent
  ttl: 3600  # 1 hour default
  max_entries: 1000
  
  # Strategy-specific settings
  memory:
    max_size_mb: 100
  redis:
    url: "redis://localhost:6379"
    db: 0
  disk:
    cache_dir: "~/.localagent/cache"
    max_size_mb: 500

# Security configuration
security:
  keyring_service: "localagent"
  tls_verify: true
  allowed_hosts:
    - "api.openai.com"
    - "localhost"
    - "127.0.0.1"
  audit_log_path: "~/.localagent/audit.log"
  
  # Encryption settings
  encryption:
    enabled: false  # For sensitive config files
    algorithm: "AES-256-GCM"

# Chat interface configuration
chat:
  default_provider: "ollama"
  default_model: null  # Use provider default
  max_history: 100  # messages
  auto_save: true
  session_timeout: 3600  # 1 hour
  
  ui:
    show_tokens: true
    show_timing: true
    enable_syntax_highlighting: true
    theme: "dark"  # dark, light, auto
    
  features:
    streaming: true
    auto_complete: true
    fuzzy_search: true

# Performance tuning
performance:
  connection_pool_size: 10
  timeout_default: 120
  rate_limit_default: 60
  memory_limit: 2048  # MB
  
  optimization:
    lazy_loading: true
    background_tasks: true
    connection_reuse: true

# Development settings
development:
  hot_reload: false
  debug_mode: false
  verbose_errors: false
  profiling: false
  
  test_mode:
    enabled: false
    mock_providers: false
    dry_run: false
```

### Environment-Specific Configuration Files
```yaml
# ~/.localagent/environments/development.yaml
system:
  log_level: "DEBUG"
  cache_enabled: false
  
development:
  hot_reload: true
  debug_mode: true
  verbose_errors: true
  
plugins:
  allow_dev_plugins: true
  enabled_plugins:
    - "workflow-automation"
    - "dev-tools"
    - "debug-helpers"

providers:
  ollama:
    base_url: "http://localhost:11434"
  openai:
    rate_limit: 10  # Lower rate limit for development

---
# ~/.localagent/environments/production.yaml
system:
  log_level: "WARNING"
  audit_log_enabled: true
  
security:
  tls_verify: true
  audit_log_path: "/var/log/localagent/audit.log"
  
plugins:
  allow_dev_plugins: false
  enabled_plugins:
    - "workflow-automation"
    - "security-scanner"
    - "monitoring-tools"

caching:
  enabled: true
  strategy: "redis"
  ttl: 7200  # 2 hours

performance:
  memory_limit: 4096  # More memory in production
```

### Project-Specific Configuration
```yaml
# ./localagent.yaml (project root)
# Project-specific settings override user/system settings

system:
  default_provider: "openai"  # This project uses OpenAI
  
workflow:
  evidence_collection: true
  auto_cleanup: false  # Keep evidence for this project
  
plugins:
  enabled_plugins:
    - "workflow-automation"
    - "project-specific-tools"
  
  project-specific-tools:
    config:
      project_type: "web-api"
      framework: "fastapi"
      testing_framework: "pytest"

# Project context for workflows
context:
  project_name: "My Web API"
  primary_language: "python"
  framework: "fastapi"
  database: "postgresql"
  deployment: "docker"
```

---

## Secure Credential Management

### Keyring Integration
LocalAgent integrates with the system keyring for secure credential storage:

```bash
# Store credentials securely
keyring set localagent openai_api_key
keyring set localagent gemini_api_key  
keyring set localagent perplexity_api_key

# LocalAgent automatically retrieves from keyring
localagent providers --health  # Uses stored credentials
```

### Credential Migration
```bash
# Migrate environment variables to keyring
localagent config migrate-credentials

# This will:
# 1. Read API keys from environment variables
# 2. Store them securely in system keyring
# 3. Update configuration to use keyring references
# 4. Optionally remove environment variables
```

### Keyring Configuration
```yaml
# ~/.localagent/config.yaml
security:
  keyring_service: "localagent"
  keyring_username: "${USER}"
  
  credential_mapping:
    "providers.openai.api_key": "openai_api_key"
    "providers.gemini.api_key": "gemini_api_key"
    "providers.perplexity.api_key": "perplexity_api_key"
```

### Manual Keyring Management
```python
# Python script for keyring management
import keyring

# Set credentials
keyring.set_password("localagent", "openai_api_key", "sk-your-key-here")

# Get credentials
api_key = keyring.get_password("localagent", "openai_api_key")

# List stored credentials
import keyring.backends.SecretService
backend = keyring.backends.SecretService.Keyring()
# Implementation varies by system
```

### Credential Security Best Practices
1. **Never commit API keys to version control**
2. **Use keyring for production environments**
3. **Rotate credentials regularly**
4. **Use environment-specific credentials**
5. **Monitor credential usage through audit logs**

---

## Provider Configuration

### Ollama Configuration
```yaml
providers:
  ollama:
    base_url: "http://localhost:11434"
    timeout: 120
    connection_pool_size: 5
    keep_alive: true
    
    # Model management
    default_model: "llama3.1"
    models:
      preferred: ["llama3.1:70b", "llama3.1", "codellama"]
      fallback: ["llama3.1:7b"]
      
    # Performance tuning
    context_length: 4096
    temperature: 0.7
    top_p: 0.9
    
    # Resource limits
    gpu_layers: -1  # Use all GPU layers
    num_thread: 8
    memory_map: true
```

### OpenAI Configuration
```yaml
providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
    organization: "${OPENAI_ORG_ID}"  # Optional
    timeout: 60
    
    # Model configuration
    default_model: "gpt-4"
    models:
      fast: ["gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
      quality: ["gpt-4", "gpt-4-turbo-preview"]
      vision: ["gpt-4-vision-preview"]
      
    # Rate limiting
    rate_limit: 60  # requests per minute
    max_tokens: 4096
    
    # Features
    function_calling: true
    json_mode: true
    streaming: true
    
    # Cost optimization
    cost_tracking: true
    budget_limit: 100  # USD per month
```

### Gemini Configuration
```yaml
providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    default_model: "gemini-1.5-pro"
    timeout: 90
    
    # Safety settings
    safety_settings:
      harassment: "BLOCK_MEDIUM_AND_ABOVE"
      hate_speech: "BLOCK_MEDIUM_AND_ABOVE"
      sexually_explicit: "BLOCK_MEDIUM_AND_ABOVE"
      dangerous_content: "BLOCK_MEDIUM_AND_ABOVE"
      
    # Model parameters
    temperature: 0.7
    top_p: 0.8
    top_k: 40
    max_output_tokens: 2048
    
    # Features
    code_execution: true
    multimodal: true
```

### Multi-Provider Configuration
```yaml
providers:
  # Primary provider for most tasks
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
    priority: 1
    
  # Fallback for complex tasks
  openai:
    api_key: "${OPENAI_API_KEY}"
    default_model: "gpt-4"
    priority: 2
    
  # Specialized for research
  perplexity:
    api_key: "${PERPLEXITY_API_KEY}"
    default_model: "llama-3.1-sonar-huge-128k-online"
    priority: 3
    use_cases: ["research", "web-search"]

# Provider selection strategy
system:
  provider_selection:
    strategy: "cost_optimized"  # performance, quality, cost_optimized
    fallback_enabled: true
    max_fallback_attempts: 2
    health_check_interval: 300  # 5 minutes
```

---

## Plugin Configuration

### Plugin System Settings
```yaml
plugins:
  # Core plugin system configuration
  enabled_plugins:
    - "workflow-automation"
    - "security-scanner" 
    - "export-tools"
    - "dev-tools"
    
  auto_load_plugins: true
  allow_dev_plugins: false
  hot_reload: false
  
  plugin_directories:
    - "~/.localagent/plugins"
    - "/opt/localagent/plugins"
    - "./plugins"  # Project-specific plugins
    
  # Plugin discovery settings
  discovery:
    scan_entry_points: true
    scan_directories: true
    cache_discovery: true
    discovery_timeout: 30
    
  # Plugin loading settings  
  loading:
    parallel_loading: true
    dependency_resolution: true
    max_load_attempts: 3
    load_timeout: 60
```

### Individual Plugin Configuration
```yaml
plugins:
  # Workflow Automation Plugin
  workflow-automation:
    enabled: true
    priority: 1
    config:
      default_template: "standard"
      auto_save_templates: true
      template_directory: "~/.localagent/templates"
      max_concurrent_workflows: 5
      
      templates:
        bug-fix:
          phases: [1, 2, 4, 6, 8, 9]
          parallel: true
          max_agents: 8
        feature-development:
          phases: [1, 2, 3, 4, 5, 6, 7, 8, 9]
          parallel: true
          max_agents: 12
          
  # Security Scanner Plugin
  security-scanner:
    enabled: true
    config:
      scan_depth: "deep"
      severity_threshold: "medium"
      exclude_patterns:
        - "*.test.*"
        - "node_modules/*"
        - ".git/*"
        - "venv/*"
        - "__pycache__/*"
        
      scanners:
        vulnerability_scanner: true
        dependency_scanner: true
        code_analysis: true
        secret_detection: true
        
      reporting:
        format: "json"
        include_false_positives: false
        output_directory: "~/.localagent/security-reports"
        
  # Export Tools Plugin
  export-tools:
    enabled: true
    config:
      default_format: "markdown"
      include_metadata: true
      compress_exports: true
      
      formats:
        markdown:
          template: "default"
          include_toc: true
        html:
          theme: "github"
          syntax_highlighting: true
        json:
          pretty_print: true
          include_schema: true
          
  # Development Tools Plugin
  dev-tools:
    enabled: false  # Only enable in development
    config:
      debug_mode: true
      verbose_logging: true
      performance_profiling: true
      
      tools:
        inspector: true
        debugger: true
        profiler: true
        validator: true
```

### Plugin Dependencies
```yaml
plugins:
  # Plugin with dependencies
  advanced-analytics:
    enabled: true
    dependencies:
      - "export-tools"
      - "data-visualization"
    config:
      analytics_engine: "pandas"
      visualization_backend: "plotly"
      
  # Plugin dependency resolution
  dependency_resolution:
    strategy: "strict"  # strict, lenient, ignore
    auto_install: false
    version_checking: true
```

---

## Environment-Specific Configuration

### Environment Detection
```yaml
# ~/.localagent/config.yaml
system:
  # Environment can be set via:
  # 1. LOCALAGENT_ENV environment variable
  # 2. --env command line argument  
  # 3. Auto-detection based on conditions
  environment: "${LOCALAGENT_ENV}"
  
  # Auto-detection rules
  environment_detection:
    rules:
      development:
        - "hostname contains 'dev'"
        - "user in ['developer', 'dev']"
        - "directory contains '.git'"
      production:
        - "hostname contains 'prod'"
        - "user in ['localagent', 'app']"
        - "file exists '/etc/localagent/production'"
      staging:
        - "hostname contains 'staging'"
        - "environment variable STAGING exists"
```

### Environment-Specific Overrides
```yaml
# Base configuration
system:
  default_provider: "ollama"
  log_level: "INFO"
  max_parallel_agents: 10

# Environment-specific overrides
environments:
  development:
    system:
      log_level: "DEBUG"
      max_parallel_agents: 5
    development:
      hot_reload: true
      debug_mode: true
    plugins:
      allow_dev_plugins: true
      enabled_plugins:
        - "workflow-automation"
        - "dev-tools"
        
  staging:
    system:
      log_level: "INFO" 
      max_parallel_agents: 8
    providers:
      openai:
        rate_limit: 30  # Lower rate limit
    caching:
      enabled: true
      ttl: 1800  # 30 minutes
      
  production:
    system:
      log_level: "WARNING"
      max_parallel_agents: 15
      audit_log_enabled: true
    providers:
      openai:
        rate_limit: 60
    caching:
      enabled: true
      strategy: "redis"
      ttl: 7200  # 2 hours
    security:
      tls_verify: true
      audit_log_path: "/var/log/localagent/audit.log"
```

### Environment Configuration Files
```bash
# Directory structure
~/.localagent/
├── config.yaml              # Base configuration
├── environments/
│   ├── development.yaml     # Development overrides
│   ├── staging.yaml         # Staging overrides
│   ├── production.yaml      # Production overrides
│   └── testing.yaml         # Testing overrides
├── templates/               # Configuration templates
│   ├── minimal.yaml
│   ├── full-featured.yaml
│   └── secure.yaml
└── backups/                 # Configuration backups
    ├── config-20241201.yaml
    └── config-20241201.yaml.backup
```

---

## Configuration Management Commands

### Basic Configuration Commands
```bash
# Show current configuration
localagent config --show

# Show configuration with sources
localagent config --show --verbose

# Show specific section
localagent config --show system
localagent config --show providers.openai

# Validate configuration
localagent config --validate

# Validate with detailed output
localagent config --validate --verbose
```

### Configuration Editing
```bash
# Set configuration value
localagent config set system.default_provider openai
localagent config set providers.ollama.base_url http://localhost:11434

# Get configuration value
localagent config get system.default_provider
localagent config get providers.openai.api_key

# Unset configuration value
localagent config unset providers.openai.rate_limit

# Edit configuration file
localagent config edit
localagent config edit --editor vim
```

### Configuration Import/Export
```bash
# Export current configuration
localagent config export --output config-backup.yaml

# Export with environment variables
localagent config export --include-env --output full-config.yaml

# Export secure (encrypted) configuration
localagent config export --secure --output config-secure.yaml

# Import configuration
localagent config import --input config-backup.yaml

# Import with merge strategy
localagent config import --input config.yaml --merge-strategy deep
```

### Configuration Templates
```bash
# List available templates
localagent config templates --list

# Create configuration from template
localagent config init --template minimal
localagent config init --template full-featured

# Save current config as template
localagent config save-template --name my-template

# Apply template to existing configuration  
localagent config apply-template --name production-template
```

### Environment Management
```bash
# Set environment
localagent config set-env development
localagent config set-env production

# Show environment-specific configuration
localagent config show --env production

# Validate environment configuration
localagent config validate --env staging

# Compare environments
localagent config compare --env development --env production
```

---

## Validation and Troubleshooting

### Configuration Validation
```bash
# Basic validation
localagent config --validate

# Comprehensive validation with details
localagent config --validate --verbose

# Validation output example:
✅ Configuration file syntax: Valid
✅ Schema validation: Passed
✅ Provider connectivity: 3/4 providers accessible
⚠️  Warning: OpenAI rate limit not set, using default
❌ Error: Gemini API key not found
✅ Plugin configuration: All enabled plugins validated
✅ Environment variables: All required variables set
```

### Common Configuration Issues

#### 1. Provider Connection Issues
```bash
# Problem: Providers showing as offline
localagent config diagnose providers

# Diagnosis output:
Provider Diagnosis:
├── Ollama
│   ✅ Configuration valid
│   ❌ Connection failed: Connection refused
│   💡 Suggestion: Start Ollama service with 'ollama serve'
├── OpenAI  
│   ✅ Configuration valid
│   ✅ Connection successful
│   ⚠️  Rate limit: 60/min (consider reducing for development)
└── Gemini
    ❌ API key missing
    💡 Suggestion: Set GEMINI_API_KEY or use 'keyring set localagent gemini_api_key'
```

#### 2. Plugin Loading Issues
```bash
# Problem: Plugins not loading
localagent config diagnose plugins

# Diagnosis output:
Plugin Diagnosis:
├── workflow-automation
│   ✅ Found via entry points
│   ✅ Dependencies satisfied
│   ✅ Configuration valid
│   ✅ Loaded successfully
├── security-scanner
│   ✅ Found via entry points  
│   ❌ Dependency missing: python-security-tools
│   💡 Suggestion: Install with 'pip install python-security-tools'
└── custom-plugin
    ❌ Not found in plugin directories
    💡 Suggestion: Check plugin_directories configuration
```

#### 3. Environment Variable Issues
```bash
# Problem: Environment variables not being loaded
localagent config diagnose environment

# Diagnosis output:
Environment Variables Diagnosis:
├── LOCALAGENT_DEFAULT_PROVIDER
│   ✅ Set: ollama
│   ✅ Valid value
├── LOCALAGENT_OPENAI_API_KEY
│   ❌ Not set
│   💡 Available in keyring: Yes
│   💡 Suggestion: Environment variable not needed when using keyring
└── LOCALAGENT_MAX_PARALLEL_AGENTS  
    ⚠️  Set: 100 (exceeds recommended maximum of 50)
    💡 Suggestion: Consider reducing to 10-20 for better performance
```

### Configuration Debugging
```bash
# Enable debug mode for configuration
export LOCALAGENT_CONFIG_DEBUG=true
localagent config --show

# Debug output shows:
Configuration Loading Debug:
1. Loading defaults... ✅
2. Loading system config (/etc/localagent/config.yaml)... ❌ Not found
3. Loading user config (~/.localagent/config.yaml)... ✅
4. Loading project config (./localagent.yaml)... ❌ Not found
5. Loading environment variables... ✅ (12 variables loaded)
6. Applying environment overrides (development)... ✅
7. Validating final configuration... ✅
```

### Troubleshooting Tools
```bash
# Configuration health check
localagent health --config

# Reset configuration to defaults
localagent config reset --confirm

# Fix common configuration issues
localagent config fix --auto

# Generate diagnostic report
localagent config diagnose --report --output diagnostic-report.txt
```

---

## Migration and Backup

### Configuration Migration
```bash
# Migrate from old version
localagent config migrate --from-version 1.0

# Migration process:
Migration from v1.0 to v2.0:
├── ✅ Backing up current configuration
├── ✅ Converting provider settings
├── ✅ Updating plugin configuration format
├── ✅ Migrating environment variables
├── ⚠️  Manual review required:
│   └── Custom plugin configurations need verification
└── ✅ Migration completed

# Verify migration
localagent config validate --verbose
```

### Credential Migration
```bash
# Migrate API keys to keyring
localagent config migrate-credentials

# Migration process:
Credential Migration:
├── 🔍 Scanning for API keys in environment variables
├── 🔐 Storing OpenAI API key in keyring... ✅
├── 🔐 Storing Gemini API key in keyring... ✅
├── ⚠️  Perplexity API key not found in environment
├── 📝 Updating configuration to use keyring references... ✅
└── 🧹 Cleaning up environment variables (optional)
    └── Remove OPENAI_API_KEY from ~/.bashrc? [y/N]
```

### Backup and Restore
```bash
# Create comprehensive backup
localagent config backup --output ~/.localagent/backups/config-$(date +%Y%m%d).tar.gz

# Backup includes:
Creating Backup:
├── 📄 Configuration files
├── 🔐 Keyring credentials (encrypted)
├── 🔌 Plugin configurations
├── 📊 Usage statistics
├── 🗂️  Template files
└── 📝 Environment snapshots

# Restore from backup
localagent config restore --input ~/.localagent/backups/config-20241201.tar.gz

# Restore options:
Restore Options:
├── 🔄 Full restore (replaces current configuration)
├── 🔀 Merge restore (combines with current configuration)
├── 🎯 Selective restore (choose components to restore)
└── 🔍 Preview restore (show changes without applying)
```

### Version Control Integration
```bash
# Create version control friendly configuration
localagent config export --version-control --output .localagent.template.yaml

# Template excludes sensitive data:
# - API keys (replaced with environment variable references)
# - User-specific paths (replaced with variables)
# - Temporary settings (excluded entirely)

# Team configuration setup
localagent config init --template .localagent.template.yaml --interactive
```

---

## Best Practices

### Security Best Practices
1. **Use Keyring for API Keys**: Never store API keys in configuration files
2. **Environment Variable Security**: Avoid putting sensitive data in shell history
3. **File Permissions**: Set appropriate permissions on configuration files (600)
4. **Audit Logging**: Enable audit logging in production environments
5. **Regular Credential Rotation**: Rotate API keys regularly

```bash
# Secure configuration file permissions
chmod 600 ~/.localagent/config.yaml
chmod 700 ~/.localagent/

# Enable audit logging
localagent config set security.audit_log_enabled true
localagent config set security.audit_log_path ~/.localagent/audit.log
```

### Organization Best Practices
1. **Environment Separation**: Use separate configurations for dev/staging/production
2. **Template Usage**: Create configuration templates for consistent setups
3. **Documentation**: Document custom configurations and plugin settings
4. **Version Control**: Track configuration templates (not actual configs) in git
5. **Regular Validation**: Regularly validate configurations

```bash
# Set up environment-specific configurations
mkdir -p ~/.localagent/environments
localagent config export --env development --output ~/.localagent/environments/dev.yaml
localagent config export --env production --output ~/.localagent/environments/prod.yaml
```

### Performance Best Practices
1. **Connection Pooling**: Configure appropriate connection pool sizes
2. **Caching Strategy**: Choose appropriate caching strategy for your use case
3. **Rate Limiting**: Set reasonable rate limits to avoid API throttling
4. **Resource Limits**: Configure memory and timeout limits appropriately
5. **Monitoring**: Monitor configuration performance and adjust as needed

```yaml
# Performance-optimized configuration
performance:
  connection_pool_size: 10
  timeout_default: 120
  rate_limit_default: 60
  memory_limit: 2048

caching:
  enabled: true
  strategy: "intelligent"
  ttl: 3600
```

### Maintenance Best Practices
1. **Regular Backups**: Automatically backup configurations
2. **Configuration Validation**: Validate configurations after changes
3. **Update Management**: Keep configurations up-to-date with new versions
4. **Cleanup**: Regularly clean up unused configurations and plugins
5. **Monitoring**: Monitor configuration health and usage

```bash
# Automated backup script
cat > ~/.localagent/scripts/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d)
localagent config backup --output ~/.localagent/backups/config-$DATE.tar.gz
find ~/.localagent/backups/ -name "*.tar.gz" -mtime +30 -delete
EOF

# Add to cron for daily backups
echo "0 2 * * * ~/.localagent/scripts/backup.sh" | crontab -
```

---

## Examples

### Complete Configuration Examples

#### Minimal Configuration
```yaml
# ~/.localagent/config.yaml - Minimal setup
system:
  default_provider: "ollama"
  
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"

plugins:
  enabled_plugins: []
  auto_load_plugins: false
```

#### Development Configuration
```yaml
# ~/.localagent/config.yaml - Development setup
system:
  default_provider: "ollama"
  log_level: "DEBUG"
  max_parallel_agents: 5
  
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
    timeout: 120
    
  openai:
    api_key: "${OPENAI_API_KEY}"
    default_model: "gpt-3.5-turbo"  # Cost effective for development
    rate_limit: 10

plugins:
  enabled_plugins:
    - "workflow-automation"
    - "dev-tools"
  auto_load_plugins: true
  allow_dev_plugins: true
  
development:
  hot_reload: true
  debug_mode: true
  verbose_errors: true

caching:
  enabled: false  # Disable caching for development
```

#### Production Configuration
```yaml
# ~/.localagent/config.yaml - Production setup
system:
  default_provider: "openai"
  log_level: "WARNING"
  max_parallel_agents: 20
  audit_log_enabled: true
  
providers:
  openai:
    api_key: "${OPENAI_API_KEY}"  # From keyring
    default_model: "gpt-4"
    rate_limit: 60
    timeout: 60
    
  gemini:
    api_key: "${GEMINI_API_KEY}"  # From keyring
    default_model: "gemini-1.5-pro"
    timeout: 90
    
  # Fallback to local if APIs unavailable
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
    priority: 3

plugins:
  enabled_plugins:
    - "workflow-automation"
    - "security-scanner"
    - "monitoring-tools"
  auto_load_plugins: true
  allow_dev_plugins: false

caching:
  enabled: true
  strategy: "redis"
  ttl: 7200
  redis:
    url: "redis://localhost:6379"
    db: 1

security:
  keyring_service: "localagent"
  tls_verify: true
  audit_log_path: "/var/log/localagent/audit.log"
  allowed_hosts:
    - "api.openai.com"
    - "generativelanguage.googleapis.com"
    - "localhost"

performance:
  connection_pool_size: 15
  memory_limit: 4096
  timeout_default: 120
```

#### Multi-Environment Configuration
```yaml
# ~/.localagent/config.yaml - Multi-environment setup
system:
  default_provider: "ollama"
  environment: "${LOCALAGENT_ENV:-development}"
  
providers:
  ollama:
    base_url: "${LOCALAGENT_OLLAMA_BASE_URL:-http://localhost:11434}"
    default_model: "llama3.1"
    
  openai:
    api_key: "${OPENAI_API_KEY}"
    default_model: "gpt-4"
    base_url: "https://api.openai.com/v1"

environments:
  development:
    system:
      log_level: "DEBUG"
      max_parallel_agents: 5
    plugins:
      allow_dev_plugins: true
      enabled_plugins:
        - "workflow-automation"
        - "dev-tools"
    caching:
      enabled: false
      
  staging:
    system:
      log_level: "INFO"
      max_parallel_agents: 10
    providers:
      openai:
        default_model: "gpt-3.5-turbo"  # Cost effective for staging
    caching:
      enabled: true
      strategy: "memory"
      ttl: 1800
      
  production:
    system:
      log_level: "WARNING"
      max_parallel_agents: 20
      audit_log_enabled: true
    caching:
      enabled: true
      strategy: "redis"
      ttl: 7200
    security:
      audit_log_path: "/var/log/localagent/audit.log"
```

### Environment Setup Examples

#### Shell Environment Setup
```bash
# ~/.bashrc or ~/.zshrc
# LocalAgent CLI Environment Configuration

# Core settings
export LOCALAGENT_ENV=development
export LOCALAGENT_DEFAULT_PROVIDER=ollama
export LOCALAGENT_LOG_LEVEL=DEBUG
export LOCALAGENT_CONFIG_DIR=~/.localagent

# Provider settings (development)
export LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
# OpenAI API key stored in keyring, not environment

# Plugin settings
export LOCALAGENT_PLUGINS_AUTO_LOAD=true
export LOCALAGENT_PLUGINS_ALLOW_DEV=true

# Feature flags
export LOCALAGENT_HOT_RELOAD=true
export LOCALAGENT_DEBUG_MODE=true
export LOCALAGENT_CACHE_ENABLED=false

# Development aliases
alias la="localagent"
alias law="localagent workflow"
alias lac="localagent chat"
alias lah="localagent health"
alias laconfig="localagent config"

# Function for quick environment switching
switch_env() {
    export LOCALAGENT_ENV=$1
    echo "Switched to $1 environment"
    localagent config show system.environment
}
```

#### Docker Environment Configuration
```bash
# Docker environment variables
# docker-compose.yml
version: '3.8'
services:
  localagent:
    image: localagent:latest
    environment:
      - LOCALAGENT_ENV=production
      - LOCALAGENT_DEFAULT_PROVIDER=openai
      - LOCALAGENT_LOG_LEVEL=INFO
      - LOCALAGENT_MAX_PARALLEL_AGENTS=15
      
      # API keys from Docker secrets
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key
      - GEMINI_API_KEY_FILE=/run/secrets/gemini_api_key
      
      # Redis for caching
      - LOCALAGENT_CACHE_STRATEGY=redis
      - LOCALAGENT_REDIS_URL=redis://redis:6379
      
      # Plugin settings
      - LOCALAGENT_PLUGINS_AUTO_LOAD=true
      - LOCALAGENT_PLUGINS_ALLOW_DEV=false
      
    secrets:
      - openai_api_key
      - gemini_api_key
    volumes:
      - ./config:/app/.localagent
    depends_on:
      - redis
      
  redis:
    image: redis:alpine
    
secrets:
  openai_api_key:
    file: ./secrets/openai_api_key.txt
  gemini_api_key:
    file: ./secrets/gemini_api_key.txt
```

---

## Reference

### Configuration File Locations

| File | Purpose | Priority |
|------|---------|----------|
| `/etc/localagent/config.yaml` | System-wide configuration | Low |
| `~/.localagent/config.yaml` | User configuration | Medium |
| `./localagent.yaml` | Project configuration | Medium |
| `~/.localagent/environments/{env}.yaml` | Environment overrides | High |

### Environment Variables Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOCALAGENT_ENV` | string | `development` | Environment name |
| `LOCALAGENT_DEFAULT_PROVIDER` | string | `ollama` | Default LLM provider |
| `LOCALAGENT_MAX_PARALLEL_AGENTS` | integer | `10` | Maximum parallel agents |
| `LOCALAGENT_LOG_LEVEL` | enum | `INFO` | Logging level |
| `LOCALAGENT_CONFIG_DIR` | path | `~/.localagent` | Configuration directory |
| `LOCALAGENT_CACHE_ENABLED` | boolean | `true` | Enable response caching |
| `LOCALAGENT_PLUGINS_AUTO_LOAD` | boolean | `true` | Auto-load plugins |
| `LOCALAGENT_HOT_RELOAD` | boolean | `false` | Enable hot reload |

### Command Reference

| Command | Description |
|---------|-------------|
| `localagent config --show` | Show current configuration |
| `localagent config --validate` | Validate configuration |
| `localagent config set <key> <value>` | Set configuration value |
| `localagent config get <key>` | Get configuration value |
| `localagent config export --output <file>` | Export configuration |
| `localagent config import --input <file>` | Import configuration |
| `localagent config migrate-credentials` | Migrate credentials to keyring |
| `localagent config diagnose` | Diagnose configuration issues |
| `localagent config backup` | Create configuration backup |
| `localagent config restore` | Restore from backup |

This comprehensive configuration guide covers all aspects of LocalAgent CLI configuration management, from basic setup to advanced multi-environment deployments. Use this guide to optimize your LocalAgent installation for your specific needs and environment.