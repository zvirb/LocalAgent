# LocalAgent CLI Migration Guide
## From Click to Typer Architecture

This guide provides step-by-step instructions for migrating from the existing Click-based CLI to the new Typer-based architecture.

## Migration Overview

### What's Changing
- **CLI Framework**: Click → Typer with Rich integration
- **Configuration**: Manual setup → Environment variables + YAML + Keyring
- **Commands**: Basic implementation → Type-hint driven with validation
- **UI**: Limited Rich usage → Full Rich terminal experience
- **Extensibility**: Hardcoded features → Plugin architecture
- **File Operations**: Basic I/O → Atomic operations with safety

### What's Staying Compatible
- **Core Commands**: Same command names and basic functionality
- **Provider System**: Same multi-provider architecture
- **Workflow Engine**: Same 12-phase UnifiedWorkflow
- **Configuration Files**: Existing YAML configs will be migrated

## Pre-Migration Checklist

### 1. Backup Current Setup
```bash
# Backup current configuration
cp ~/.localagent/config.yaml ~/.localagent/config.yaml.backup

# Export current settings
localagent config --show > current_config_backup.txt

# Backup any custom scripts
cp -r ~/.localagent/plugins ~/.localagent/plugins.backup
```

### 2. Document Current Usage
- [ ] List currently used commands
- [ ] Document custom configurations
- [ ] Note any custom scripts or integrations
- [ ] Record API keys and provider settings

### 3. Environment Preparation
```bash
# Install new dependencies
pip install typer[all]>=0.16.0 rich>=13.6.0 inquirerpy>=0.3.4

# Verify Python version (3.9+ required)
python --version
```

## Step-by-Step Migration

### Phase 1: Install New CLI (Week 1)

#### 1.1 Install Updated LocalAgent
```bash
# Install from updated requirements
pip install -r requirements.txt

# Or install development version
pip install -e .
```

#### 1.2 Verify Installation
```bash
# Check new CLI is working
localagent --help

# Test basic functionality
localagent health
```

#### 1.3 Run Migration Tool
```bash
# Migrate existing configuration
localagent migrate-config ~/.localagent/config.yaml

# Validate migrated configuration
localagent config --validate
```

### Phase 2: Update Configuration (Week 1-2)

#### 2.1 Environment Variables Setup
```bash
# Create environment configuration
cat > ~/.localagent/env.conf << EOF
# Provider Configuration
LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
LOCALAGENT_OPENAI_API_KEY=sk-your-key-here
LOCALAGENT_GEMINI_API_KEY=your-gemini-key
LOCALAGENT_DEFAULT_PROVIDER=ollama

# System Configuration  
LOCALAGENT_LOG_LEVEL=INFO
LOCALAGENT_MAX_PARALLEL_AGENTS=10

# Plugin Configuration
LOCALAGENT_PLUGINS_AUTO_LOAD=true
EOF

# Source environment (add to ~/.bashrc)
source ~/.localagent/env.conf
```

#### 2.2 Secure Credential Storage
```bash
# Migrate API keys to keyring (interactive)
localagent migrate-credentials

# Or manually set secure credentials
keyring set localagent openai_api_key
keyring set localagent gemini_api_key
keyring set localagent perplexity_api_key
```

#### 2.3 Validate New Configuration
```bash
# Test all providers
localagent providers --health

# Validate complete configuration
localagent config --validate --verbose
```

### Phase 3: Command Migration (Week 2)

#### 3.1 Update Command Syntax

**Old Click Commands:**
```bash
# Old workflow command
localagent complete "Fix bug" --provider openai

# Old provider listing
localagent providers
```

**New Typer Commands:**
```bash
# New workflow command (enhanced)
localagent workflow "Fix bug" --provider openai --parallel --max-agents 10

# New provider management (enhanced)
localagent providers --list --health
```

#### 3.2 Interactive Mode Updates

**Old Interactive Mode:**
- Basic prompt interface
- Limited command options
- Manual provider switching

**New Interactive Mode:**
```bash
# Start enhanced interactive mode
localagent chat

# Features include:
# - Fuzzy search for providers/models
# - Rich terminal UI
# - Session management
# - Auto-completion
```

#### 3.3 Script Updates

**Update Existing Scripts:**
```python
# Old API usage
import click
from app.main import LocalAgentCLI

# New API usage  
import asyncio
from app.cli import create_app, ConfigurationManager
from app.orchestration.orchestration_integration import create_orchestrator

async def main():
    orchestrator = await create_orchestrator()
    result = await orchestrator.execute_12_phase_workflow("prompt")
```

### Phase 4: Plugin Migration (Week 2-3)

#### 4.1 Convert Custom Extensions

**Old Custom Scripts (if any):**
```python
# Old hook/script approach
def my_custom_workflow():
    pass
```

**New Plugin Format:**
```python
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
        return "My custom workflow"
    
    async def initialize(self, context) -> bool:
        return True
    
    def register_commands(self, app: typer.Typer) -> None:
        @app.command("my-workflow")
        def my_workflow(prompt: str):
            """Execute my custom workflow"""
            # Your logic here
            pass
```

#### 4.2 Enable Plugin System
```bash
# Discover available plugins
localagent plugins --list

# Enable desired plugins
localagent plugins --enable workflow-automation
localagent plugins --enable security-scanner

# Verify plugin loading
localagent plugins --list
```

### Phase 5: Testing & Validation (Week 3)

#### 5.1 Functionality Testing
```bash
# Test core workflows
localagent workflow "Test migration" --format json --save test_result.json

# Test provider switching
localagent providers --health
localagent chat --provider ollama

# Test plugin functionality
localagent my-workflow "Test plugin"
```

#### 5.2 Performance Testing
```bash
# Test parallel execution
time localagent workflow "Performance test" --parallel --max-agents 15

# Test interactive responsiveness  
localagent chat  # Test fuzzy search responsiveness
```

#### 5.3 Integration Testing
```bash
# Test with existing automation
./existing_automation_script.sh

# Test CI/CD integration (if applicable)
# Update .github/workflows or equivalent
```

### Phase 6: Production Deployment (Week 4)

#### 6.1 Environment-Specific Configuration
```bash
# Production environment variables
export LOCALAGENT_LOG_LEVEL=WARNING
export LOCALAGENT_MAX_PARALLEL_AGENTS=20
export LOCALAGENT_ENABLE_AUDIT_LOG=true

# Staging environment
export LOCALAGENT_LOG_LEVEL=INFO  
export LOCALAGENT_MAX_PARALLEL_AGENTS=10
```

#### 6.2 Monitoring Setup
```bash
# Enable system health monitoring
localagent config --set monitoring.enabled=true

# Setup log aggregation (if applicable)
export LOCALAGENT_LOG_FORMAT=json
```

#### 6.3 Documentation Updates
- [ ] Update team documentation
- [ ] Update automation scripts
- [ ] Update CI/CD configurations
- [ ] Train team members on new features

## Common Migration Issues & Solutions

### Issue 1: Command Not Found
**Problem:** `localagent: command not found`

**Solutions:**
```bash
# Ensure proper installation
pip install --upgrade localagent-cli

# Check PATH
echo $PATH
which localagent

# Reinstall if needed
pip uninstall localagent-cli
pip install localagent-cli
```

### Issue 2: Configuration Not Loading
**Problem:** Settings not being applied

**Solutions:**
```bash
# Check configuration sources
localagent config --show --verbose

# Validate configuration
localagent config --validate

# Reset to defaults and reconfigure
localagent init --force
```

### Issue 3: Provider Connection Issues
**Problem:** Providers showing as offline

**Solutions:**
```bash
# Check network connectivity
curl -s http://localhost:11434/api/tags  # For Ollama

# Verify credentials
localagent providers --provider openai --health

# Reset provider configuration  
localagent migrate-credentials
```

### Issue 4: Plugin Loading Failures
**Problem:** Plugins not loading or working

**Solutions:**
```bash
# Check plugin discovery
localagent plugins --list --verbose

# Verify plugin dependencies
pip install --upgrade setuptools importlib-metadata

# Reinstall plugins
localagent plugins --disable problematic-plugin
localagent plugins --enable problematic-plugin
```

### Issue 5: Performance Issues
**Problem:** Slower than expected execution

**Solutions:**
```bash
# Check system resources
localagent health --verbose

# Adjust parallel execution
export LOCALAGENT_MAX_PARALLEL_AGENTS=5

# Enable performance monitoring
export LOCALAGENT_LOG_LEVEL=DEBUG
```

## Rollback Plan

If issues arise during migration, follow these steps:

### Emergency Rollback
```bash
# Stop new CLI processes
pkill -f localagent

# Restore backup configuration
cp ~/.localagent/config.yaml.backup ~/.localagent/config.yaml

# Restore backup plugins
rm -rf ~/.localagent/plugins
cp -r ~/.localagent/plugins.backup ~/.localagent/plugins

# Downgrade packages
pip install localagent-cli==1.0.0  # Previous stable version
```

### Gradual Rollback
```bash
# Disable specific problematic features
export LOCALAGENT_PLUGINS_AUTO_LOAD=false

# Use compatibility mode
localagent --legacy-mode workflow "test"

# Disable parallel execution
export LOCALAGENT_MAX_PARALLEL_AGENTS=1
```

## Post-Migration Optimization

### 1. Performance Tuning
```bash
# Optimize for your workload
export LOCALAGENT_MAX_PARALLEL_AGENTS=20  # Adjust based on system
export LOCALAGENT_PROVIDER_TIMEOUT=300    # Adjust based on network

# Enable caching
export LOCALAGENT_ENABLE_CACHING=true
```

### 2. Security Hardening
```bash
# Enable audit logging
export LOCALAGENT_ENABLE_AUDIT_LOG=true

# Restrict plugin loading
export LOCALAGENT_ALLOW_DEV_PLUGINS=false

# Use secure configuration storage
localagent config --export-secure config_backup.yaml
```

### 3. Monitoring & Alerting
```bash
# Setup health check monitoring
echo "*/5 * * * * localagent health --quiet || echo 'LocalAgent health check failed'" | crontab -

# Log analysis setup (if using log aggregation)
localagent config --set logging.format=json
localagent config --set logging.level=INFO
```

## Training & Documentation

### Team Training Checklist
- [ ] New command syntax and options
- [ ] Plugin system usage
- [ ] Interactive mode features
- [ ] Configuration management
- [ ] Troubleshooting procedures

### Updated Documentation
- [ ] Command reference updates
- [ ] Configuration examples
- [ ] Plugin development guides
- [ ] Integration examples
- [ ] Troubleshooting guides

## Success Metrics

Track these metrics to validate successful migration:

### Performance Metrics
- Command execution time < 2 seconds for basic operations
- Workflow execution time improvement of 20%+ 
- Interactive mode response time < 100ms

### Reliability Metrics
- Configuration loading success rate > 99%
- Provider connection success rate > 95%
- Plugin loading success rate > 98%

### User Experience Metrics
- Reduced time to complete common tasks
- Improved error message clarity
- Enhanced discoverability of features

## Conclusion

The migration to the new Typer-based architecture provides:

### Migration Benefits Realized

✅ **Enhanced User Experience**: Rich terminal UI, interactive prompts, and modern CLI patterns
✅ **Improved Extensibility**: Plugin architecture enabling custom commands and providers
✅ **Better Configuration**: Hierarchical configuration with environment variables and secure credential storage
✅ **Increased Reliability**: Atomic file operations, comprehensive error recovery, and system health monitoring
✅ **Modern Development**: Full type hints, async patterns, and contemporary Python best practices
✅ **Performance Optimization**: Parallel execution, intelligent caching, and resource management
✅ **Security Enhancement**: Secure credential storage, audit logging, and permission management
✅ **Maintainability**: Cleaner architecture, comprehensive testing, and better documentation

---

Following this comprehensive migration guide ensures a smooth transition while maintaining all existing functionality and unlocking powerful new capabilities. The modern Typer-based architecture provides enhanced user experience, improved extensibility, and better maintainability for long-term success.