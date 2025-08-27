# LocalAgent CLI Troubleshooting Guide

## Table of Contents
- [Common Installation Issues](#common-installation-issues)
- [Configuration Problems](#configuration-problems)
- [Provider Connection Issues](#provider-connection-issues)
- [Workflow Execution Problems](#workflow-execution-problems)
- [Plugin-Related Issues](#plugin-related-issues)
- [Performance Issues](#performance-issues)
- [Security and Authentication Issues](#security-and-authentication-issues)
- [Platform-Specific Issues](#platform-specific-issues)
- [Diagnostic Commands](#diagnostic-commands)
- [Log Analysis](#log-analysis)
- [Recovery Procedures](#recovery-procedures)
- [Advanced Troubleshooting](#advanced-troubleshooting)

---

## Common Installation Issues

### Issue: `localagent: command not found`

**Symptoms:**
```bash
$ localagent --help
bash: localagent: command not found
```

**Diagnosis:**
```bash
# Check if LocalAgent is installed
pip list | grep localagent

# Check Python PATH
which python
echo $PATH

# Check installation location
pip show localagent-cli
```

**Solutions:**

**Solution 1: Installation Path Issues**
```bash
# Check where pip installs binaries
python -m site --user-base

# Add user bin directory to PATH (Linux/Mac)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# For system-wide installation
pip install --upgrade localagent-cli

# For user installation
pip install --user --upgrade localagent-cli
```

**Solution 2: Virtual Environment Issues**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install in virtual environment
pip install localagent-cli

# Verify installation
which localagent
localagent --version
```

**Solution 3: Python Version Compatibility**
```bash
# Check Python version (requires 3.9+)
python --version

# If using older Python, upgrade or use specific version
python3.9 -m pip install localagent-cli
python3.10 -m pip install localagent-cli
```

### Issue: Import Errors During Installation

**Symptoms:**
```bash
ModuleNotFoundError: No module named 'typer'
ModuleNotFoundError: No module named 'rich'
```

**Solutions:**
```bash
# Install missing dependencies
pip install typer rich pydantic aiohttp

# Force reinstall with dependencies
pip install --force-reinstall --no-deps localagent-cli
pip install localagent-cli

# Install with all dependencies
pip install -r requirements.txt
```

### Issue: Permission Errors

**Symptoms:**
```bash
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Solutions:**
```bash
# Use user installation (recommended)
pip install --user localagent-cli

# Use virtual environment (best practice)
python -m venv localagent-env
source localagent-env/bin/activate
pip install localagent-cli

# Fix permissions (Linux/Mac only if needed)
sudo chown -R $USER:$USER ~/.local/
```

---

## Configuration Problems

### Issue: Configuration File Not Found

**Symptoms:**
```bash
$ localagent config show
Error: Configuration file not found at ~/.localagent/config.yaml
```

**Diagnosis:**
```bash
# Check configuration directory
ls -la ~/.localagent/

# Check current configuration
localagent config show --verbose
```

**Solutions:**
```bash
# Initialize configuration
localagent init

# Create configuration manually
mkdir -p ~/.localagent
cat > ~/.localagent/config.yaml << 'EOF'
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
    
system:
  default_provider: "ollama"
  max_parallel_agents: 10
  log_level: "INFO"
EOF

# Validate configuration
localagent config validate
```

### Issue: Configuration Validation Errors

**Symptoms:**
```bash
$ localagent config validate
❌ Configuration validation failed:
  - providers.openai.api_key: field required
  - system.max_parallel_agents: ensure this value is greater than 0
```

**Solutions:**
```bash
# Fix configuration issues automatically
localagent config validate --fix

# Show detailed validation errors
localagent config validate --verbose

# Reset to default configuration
localagent config reset --confirm

# Check configuration schema
localagent config --help
```

### Issue: Environment Variables Not Loading

**Symptoms:**
```bash
# Environment variable not recognized
export LOCALAGENT_DEFAULT_PROVIDER=openai
localagent config show  # Still shows ollama as default
```

**Solutions:**
```bash
# Check environment variable format
env | grep LOCALAGENT

# Correct format (uppercase, underscores)
export LOCALAGENT_DEFAULT_PROVIDER=openai
export LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
export LOCALAGENT_LOG_LEVEL=DEBUG

# Restart shell or reload environment
source ~/.bashrc

# Verify environment loading
localagent config show --verbose
```

---

## Provider Connection Issues

### Issue: Ollama Connection Failed

**Symptoms:**
```bash
$ localagent providers --health
❌ ollama: Connection timeout
Provider Health: 0/1 healthy
```

**Diagnosis:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check Ollama process
ps aux | grep ollama
systemctl status ollama  # Linux with systemd

# Check Ollama logs
journalctl -u ollama -f  # Linux
~/Library/Logs/Ollama/server.log  # Mac
```

**Solutions:**

**Solution 1: Start Ollama Service**
```bash
# Linux with systemd
sudo systemctl start ollama
sudo systemctl enable ollama

# Mac
brew services start ollama

# Manual start
ollama serve &
```

**Solution 2: Check Ollama Configuration**
```bash
# Check Ollama port and binding
netstat -tlnp | grep 11434
ss -tlnp | grep 11434

# If Ollama is on different port/host
localagent config set providers.ollama.base_url "http://localhost:11435"

# Test connection manually
curl http://localhost:11434/api/version
```

**Solution 3: Network Issues**
```bash
# Check firewall (Linux)
sudo iptables -L | grep 11434
sudo ufw status

# Check if bound to localhost only
sudo netstat -tlnp | grep 11434

# Configure Ollama to bind to all interfaces
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

### Issue: OpenAI API Authentication Failed

**Symptoms:**
```bash
$ localagent providers --provider openai --health
❌ openai: Authentication failed (401)
Invalid API key provided
```

**Solutions:**
```bash
# Check API key format
echo $LOCALAGENT_OPENAI_API_KEY | head -c 20
# Should start with "sk-"

# Set API key correctly
export LOCALAGENT_OPENAI_API_KEY="sk-your-actual-api-key-here"

# Use keyring for security (recommended)
keyring set localagent openai_api_key
# Then enter your API key when prompted

# Verify API key works
curl -H "Authorization: Bearer $LOCALAGENT_OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Test with LocalAgent
localagent providers --provider openai --test
```

### Issue: Rate Limiting / Quota Exceeded

**Symptoms:**
```bash
$ localagent workflow "test task" --provider openai
❌ Workflow failed: Rate limit exceeded
API quota exceeded for current billing period
```

**Solutions:**
```bash
# Check API usage (OpenAI)
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/usage

# Switch to alternative provider
localagent workflow "test task" --provider ollama

# Configure rate limiting
localagent config set providers.openai.rate_limit_per_minute 20

# Use multiple providers with fallback
localagent config set system.provider_fallback true
localagent config set system.fallback_order "ollama,gemini,openai"
```

---

## Workflow Execution Problems

### Issue: Workflow Hangs or Times Out

**Symptoms:**
```bash
$ localagent workflow "analyze code"
Phase 1: Parallel Research & Discovery...
[Hangs for several minutes]
❌ Workflow timeout after 3600 seconds
```

**Diagnosis:**
```bash
# Check active workflows
localagent health --resources

# Monitor system resources
top -p $(pgrep -f localagent)
ps aux | grep localagent

# Check logs for stuck processes
localagent logs --level debug --since 10m
```

**Solutions:**

**Solution 1: Resource Issues**
```bash
# Check memory usage
localagent health --resources

# Reduce parallel agents
localagent workflow "analyze code" --max-agents 3

# Increase timeout
localagent workflow "analyze code" --timeout 7200

# Run sequential execution
localagent workflow "analyze code" --sequential
```

**Solution 2: Provider Issues**
```bash
# Test provider connectivity
localagent providers --health --verbose

# Use different provider
localagent workflow "analyze code" --provider ollama

# Enable provider fallback
localagent workflow "analyze code" --provider openai,ollama
```

**Solution 3: Debug Workflow Execution**
```bash
# Enable debug mode
localagent --debug workflow "analyze code"

# Run specific phases only
localagent workflow "analyze code" --phases "1,2"

# Interactive debugging
localagent debug workflow --interactive
```

### Issue: Workflow Phase Failures

**Symptoms:**
```bash
Phase 4: Parallel Stream Execution ❌
├─ Backend Security     ❌ Failed: Connection timeout
├─ Frontend Integration ✅ Complete
└─ Database Updates     ❌ Failed: Permission denied
```

**Solutions:**
```bash
# Check specific agent logs
localagent debug workflow --agent backend-gateway-expert

# Retry failed phases
localagent workflow resume --workflow-id abc123 --from-phase 4

# Run phases individually
localagent workflow "fix auth" --phases 4 --sequential

# Check permissions
localagent debug config --check-permissions
```

### Issue: Out of Memory During Workflow

**Symptoms:**
```bash
MemoryError: Unable to allocate array
Process killed (OOM killer)
```

**Solutions:**
```bash
# Monitor memory usage
localagent health --watch --resources

# Reduce parallel execution
export LOCALAGENT_MAX_PARALLEL_AGENTS=3
localagent workflow "large task" --max-agents 3

# Enable memory optimization
export LOCALAGENT_MEMORY_OPTIMIZATION=true

# Use swap if available (Linux)
sudo swapon --show
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## Plugin-Related Issues

### Issue: Plugin Not Loading

**Symptoms:**
```bash
$ localagent plugins --list
❌ security-scanner: Load failed - ImportError
✅ workflow-automation: Loaded successfully
```

**Diagnosis:**
```bash
# Check plugin details
localagent plugins --info security-scanner

# Test plugin individually
localagent plugins --test security-scanner

# Check plugin dependencies
localagent debug plugins --plugin security-scanner --verbose
```

**Solutions:**
```bash
# Install missing dependencies
pip install bandit safety semgrep

# Reload plugin
localagent plugins --reload security-scanner

# Enable development mode for debugging
export LOCALAGENT_PLUGINS_ALLOW_DEV=true
localagent plugins --discover

# Check plugin configuration
localagent plugins --config security-scanner
```

### Issue: Plugin Command Not Available

**Symptoms:**
```bash
$ localagent security-scan ./src
Error: No such command "security-scan"
```

**Solutions:**
```bash
# Check if plugin is enabled
localagent plugins --list --enabled

# Enable plugin
localagent plugins --enable security-scanner

# Force plugin discovery
localagent plugins --discover

# Check plugin commands
localagent plugins --info security-scanner --verbose

# Restart LocalAgent to refresh commands
# (Exit and restart your shell session)
```

### Issue: Plugin Configuration Errors

**Symptoms:**
```bash
$ localagent plugins --enable my-plugin
❌ Plugin configuration validation failed:
  - scan_depth: 'invalid' is not one of ['shallow', 'medium', 'deep']
```

**Solutions:**
```bash
# Check plugin configuration schema
localagent plugins --config my-plugin

# Fix configuration
cat > ~/.localagent/plugins/my-plugin-config.yaml << 'EOF'
scan_depth: medium
exclude_patterns:
  - "*.test.js"
  - "node_modules/*"
severity_threshold: high
EOF

# Validate configuration
localagent config validate --plugin my-plugin

# Reset plugin configuration
localagent plugins --disable my-plugin
localagent plugins --enable my-plugin
```

---

## Performance Issues

### Issue: Slow Command Execution

**Symptoms:**
```bash
$ time localagent providers --health
# Takes 30+ seconds to complete
```

**Diagnosis:**
```bash
# Profile command execution
localagent debug performance --command "providers --health"

# Check network connectivity
ping api.openai.com
ping localhost

# Monitor system resources
localagent health --resources --watch
```

**Solutions:**
```bash
# Increase connection timeouts
localagent config set providers.openai.timeout 60

# Reduce concurrent connections
localagent config set providers.openai.connection_pool_size 5

# Enable caching
localagent config set caching.enabled true
localagent config set caching.ttl 1800

# Use faster provider for health checks
localagent config set system.default_provider ollama
```

### Issue: High Memory Usage

**Symptoms:**
```bash
$ localagent health --resources
Memory: 95% (7.8GB/8GB used)
⚠️ High memory usage detected
```

**Solutions:**
```bash
# Enable memory monitoring
export LOCALAGENT_MEMORY_MONITORING=true

# Set memory limits
export LOCALAGENT_MAX_MEMORY=4096  # MB

# Clean up memory
localagent cache clear
localagent debug memory --cleanup

# Restart with fresh memory
# (Exit LocalAgent and restart)

# Reduce parallel agents
export LOCALAGENT_MAX_PARALLEL_AGENTS=3

# Check for memory leaks
localagent debug memory --detailed --save memory-report.json
```

### Issue: Disk Space Issues

**Symptoms:**
```bash
OSError: [Errno 28] No space left on device
```

**Solutions:**
```bash
# Check disk usage
df -h ~/.localagent/

# Clean up logs
localagent logs --cleanup --older-than 7d

# Clear cache
localagent cache clear

# Remove old workflows
find ~/.localagent/workflows/ -name "*.json" -mtime +30 -delete

# Clean up temporary files
localagent debug cleanup --temp-files
```

---

## Security and Authentication Issues

### Issue: API Key Storage Problems

**Symptoms:**
```bash
$ localagent providers --health
❌ Cannot access API keys from keyring
❌ Environment variables not found
```

**Diagnosis:**
```bash
# Check keyring availability
python -c "import keyring; print(keyring.get_keyring())"

# Check environment variables
env | grep LOCALAGENT | grep API_KEY

# Test keyring access
keyring get localagent openai_api_key
```

**Solutions:**
```bash
# Install keyring backend (Linux)
sudo apt-get install python3-keyring
pip install keyrings.alt

# Set up keyring (Mac)
# Keyring is built-in, no additional setup needed

# Store keys in keyring
keyring set localagent openai_api_key
keyring set localagent gemini_api_key

# Migrate from environment variables
localagent config migrate-credentials

# Verify keyring access
localagent config validate --check-credentials
```

### Issue: Permission Denied Errors

**Symptoms:**
```bash
PermissionError: [Errno 13] Permission denied: '/home/user/.localagent/config.yaml'
```

**Solutions:**
```bash
# Fix file permissions
chmod 644 ~/.localagent/config.yaml
chmod 755 ~/.localagent/

# Fix ownership (Linux)
sudo chown -R $USER:$USER ~/.localagent/

# Check directory permissions
ls -la ~/.localagent/

# Reset configuration directory
rm -rf ~/.localagent/
localagent init
```

### Issue: TLS/SSL Certificate Problems

**Symptoms:**
```bash
SSL: CERTIFICATE_VERIFY_FAILED
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
```

**Solutions:**
```bash
# Update certificates (Linux)
sudo apt-get update && sudo apt-get install ca-certificates

# Update certificates (Mac)
brew upgrade ca-certificates

# Set certificate file location
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Disable SSL verification (NOT recommended for production)
export PYTHONHTTPSVERIFY=0

# Configure LocalAgent SSL settings
localagent config set system.ssl_verify true
localagent config set system.ca_bundle_path "/etc/ssl/certs/ca-certificates.crt"
```

---

## Platform-Specific Issues

### Linux Issues

**Issue: Systemd Service Problems**
```bash
# Check service status
sudo systemctl status localagent-daemon
sudo journalctl -u localagent-daemon -f

# Restart service
sudo systemctl restart localagent-daemon

# Enable auto-start
sudo systemctl enable localagent-daemon
```

**Issue: SELinux Restrictions**
```bash
# Check SELinux status
sestatus

# Check AVC denials
sudo ausearch -m AVC -ts recent | grep localagent

# Create SELinux policy (if needed)
sudo audit2allow -a -M localagent_policy
sudo semodule -i localagent_policy.pp
```

### macOS Issues

**Issue: Gatekeeper Blocking Execution**
```bash
# Allow unsigned binaries
sudo spctl --master-disable

# Or sign LocalAgent (if you have developer account)
codesign -s "Developer ID" /usr/local/bin/localagent
```

**Issue: Homebrew Installation**
```bash
# Install via Homebrew
brew tap localagent/tap
brew install localagent

# Update Homebrew
brew update && brew upgrade localagent
```

### Windows Issues

**Issue: PowerShell Execution Policy**
```powershell
# Check execution policy
Get-ExecutionPolicy

# Allow script execution
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run LocalAgent
localagent.exe --help
```

**Issue: Windows Defender Blocking**
```powershell
# Add exclusion for LocalAgent
Add-MpPreference -ExclusionPath "C:\Users\$env:USERNAME\.localagent"
Add-MpPreference -ExclusionProcess "localagent.exe"
```

---

## Diagnostic Commands

### System Health Diagnostics

```bash
# Comprehensive health check
localagent health --comprehensive --output health-report.json

# Quick system status
localagent health --quick

# Component-specific checks
localagent health --components providers,plugins,config

# Resource monitoring
localagent health --resources --watch

# Performance metrics
localagent health --performance --verbose
```

### Debug Commands

```bash
# Debug workflow execution
localagent debug workflow --workflow-id abc123 --trace

# Debug provider connectivity
localagent debug providers --provider openai --network-trace

# Debug plugin issues
localagent debug plugins --plugin security-scanner --verbose

# Debug configuration
localagent debug config --validate --fix

# Memory analysis
localagent debug memory --detailed --save memory-analysis.json

# Network diagnostics
localagent debug network --all-providers --timeout 30
```

### Log Analysis Commands

```bash
# View recent logs
localagent logs --tail 100

# Filter by level
localagent logs --level error --since 1h

# Search logs
localagent logs --search "authentication failed" --since 24h

# Export logs
localagent logs --export logs-$(date +%Y%m%d).json --since 7d

# Real-time log monitoring
localagent logs --follow --filter "workflow|error"
```

---

## Log Analysis

### Understanding Log Formats

#### Structured JSON Logs
```json
{
  "timestamp": "2024-01-15T14:30:12.345Z",
  "level": "ERROR",
  "component": "workflow_engine",
  "message": "Phase 4 execution failed",
  "workflow_id": "wf_abc123",
  "phase": 4,
  "agent": "backend-gateway-expert",
  "error": {
    "type": "ConnectionTimeoutError",
    "message": "Connection to provider timed out",
    "traceback": "..."
  },
  "context": {
    "provider": "openai",
    "retry_count": 3,
    "execution_time": 45.2
  }
}
```

#### Common Log Patterns

**Authentication Failures:**
```bash
grep "authentication failed\|401\|403\|invalid.*key" ~/.localagent/logs/localagent.log
```

**Connection Issues:**
```bash
grep "connection.*failed\|timeout\|unreachable" ~/.localagent/logs/localagent.log
```

**Memory Issues:**
```bash
grep "memory\|OOM\|allocation.*failed" ~/.localagent/logs/localagent.log
```

**Plugin Issues:**
```bash
grep "plugin.*failed\|import.*error" ~/.localagent/logs/localagent.log
```

### Log Analysis Scripts

```bash
# Create log analysis script
cat > analyze_logs.sh << 'EOF'
#!/bin/bash

LOG_FILE="$HOME/.localagent/logs/localagent.log"
SINCE=${1:-"24h"}

echo "=== LocalAgent Log Analysis ==="
echo "Analyzing logs from last $SINCE"
echo

# Error summary
echo "=== Error Summary ==="
journalctl --since="$SINCE" -u localagent 2>/dev/null || \
    grep -E "ERROR|CRITICAL" "$LOG_FILE" | tail -20

echo
echo "=== Connection Issues ==="
grep -E "connection.*failed|timeout|unreachable" "$LOG_FILE" | tail -10

echo
echo "=== Authentication Issues ==="
grep -E "auth.*failed|401|403|invalid.*key" "$LOG_FILE" | tail -10

echo
echo "=== Plugin Issues ==="
grep -E "plugin.*failed|import.*error" "$LOG_FILE" | tail -10

echo
echo "=== Memory Issues ==="
grep -E "memory|OOM|allocation.*failed" "$LOG_FILE" | tail -5

echo
echo "=== Most Common Errors ==="
grep ERROR "$LOG_FILE" | cut -d'"' -f8 | sort | uniq -c | sort -nr | head -10

EOF

chmod +x analyze_logs.sh
./analyze_logs.sh 1h
```

---

## Recovery Procedures

### Configuration Recovery

```bash
# Backup current configuration
cp ~/.localagent/config.yaml ~/.localagent/config.yaml.backup

# Reset to defaults
localagent config reset --confirm

# Restore from backup
localagent config import ~/.localagent/config.yaml.backup

# Gradual recovery - start minimal
localagent init --minimal

# Test basic functionality
localagent health --quick

# Gradually add providers
localagent config set providers.ollama.base_url "http://localhost:11434"
localagent providers --provider ollama --health
```

### Plugin Recovery

```bash
# Disable all plugins
localagent plugins --disable-all

# Test core functionality
localagent health

# Enable plugins one by one
for plugin in workflow-automation security-scanner export-tools; do
    echo "Testing plugin: $plugin"
    localagent plugins --enable "$plugin"
    if ! localagent plugins --test "$plugin"; then
        echo "Plugin $plugin failed, disabling"
        localagent plugins --disable "$plugin"
    fi
done
```

### Workflow Recovery

```bash
# List failed workflows
localagent workflow history --status failed

# Get workflow details
localagent workflow show abc123

# Resume from checkpoint
localagent workflow resume --workflow-id abc123 --from-phase 4

# Restart with modified parameters
localagent workflow "same task" --max-agents 3 --sequential
```

### Database Recovery

```bash
# Check LocalAgent data integrity
localagent debug database --check-integrity

# Repair corrupted data
localagent debug database --repair

# Reset workflow database
localagent debug database --reset-workflows --confirm

# Backup and restore
localagent export-tools all --output backup-$(date +%Y%m%d).tar.gz
localagent debug database --restore backup-20240115.tar.gz
```

---

## Advanced Troubleshooting

### Network Debugging

```bash
# Trace network requests
export LOCALAGENT_DEBUG_NETWORK=true
localagent providers --health 2>&1 | grep -E "REQUEST|RESPONSE"

# Check proxy settings
echo "HTTP_PROXY: $HTTP_PROXY"
echo "HTTPS_PROXY: $HTTPS_PROXY"
echo "NO_PROXY: $NO_PROXY"

# Test connectivity with curl
curl -v -H "Authorization: Bearer $OPENAI_API_KEY" \
     --connect-timeout 10 \
     https://api.openai.com/v1/models

# DNS resolution testing
nslookup api.openai.com
dig api.openai.com
```

### Process Debugging

```bash
# Monitor LocalAgent processes
ps aux | grep localagent
pstree -p $(pgrep localagent)

# Trace system calls (Linux)
strace -p $(pgrep localagent) -f -e trace=network 2>&1 | head -50

# Memory debugging with valgrind (if available)
valgrind --tool=memcheck --leak-check=full localagent health

# CPU profiling
perf record -g localagent workflow "test task"
perf report
```

### Python Environment Debugging

```bash
# Check Python environment
python -c "
import sys
print('Python version:', sys.version)
print('Python executable:', sys.executable)
print('Python path:', sys.path)
"

# Check LocalAgent installation
python -c "
import pkg_resources
try:
    dist = pkg_resources.get_distribution('localagent-cli')
    print('LocalAgent version:', dist.version)
    print('Installation path:', dist.location)
except:
    print('LocalAgent not found in Python environment')
"

# Check dependencies
python -c "
import importlib
modules = ['typer', 'rich', 'pydantic', 'aiohttp', 'asyncio']
for module in modules:
    try:
        mod = importlib.import_module(module)
        print(f'{module}: OK ({getattr(mod, \"__version__\", \"unknown\")})')
    except ImportError as e:
        print(f'{module}: MISSING ({e})')
"
```

### Container Debugging (if using Docker)

```bash
# Check container status
docker ps -a | grep localagent

# Container logs
docker logs localagent-container -f

# Execute into container
docker exec -it localagent-container bash

# Check container resources
docker stats localagent-container

# Inspect container configuration
docker inspect localagent-container
```

### Creating Support Bundle

```bash
# Create comprehensive diagnostic bundle
cat > create_support_bundle.sh << 'EOF'
#!/bin/bash

BUNDLE_DIR="localagent-support-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BUNDLE_DIR"

echo "Creating LocalAgent support bundle..."

# System information
uname -a > "$BUNDLE_DIR/system_info.txt"
python --version >> "$BUNDLE_DIR/system_info.txt"
pip list > "$BUNDLE_DIR/python_packages.txt"

# LocalAgent configuration
localagent config show --format json > "$BUNDLE_DIR/config.json" 2>/dev/null
localagent health --comprehensive --format json > "$BUNDLE_DIR/health_check.json" 2>/dev/null
localagent providers --health --format json > "$BUNDLE_DIR/providers.json" 2>/dev/null
localagent plugins --list --format json > "$BUNDLE_DIR/plugins.json" 2>/dev/null

# Logs
cp ~/.localagent/logs/localagent.log "$BUNDLE_DIR/" 2>/dev/null
localagent logs --level error --since 24h > "$BUNDLE_DIR/recent_errors.log" 2>/dev/null

# Process information
ps aux | grep localagent > "$BUNDLE_DIR/processes.txt"
lsof -p $(pgrep localagent) > "$BUNDLE_DIR/open_files.txt" 2>/dev/null

# Network information
netstat -tulnp > "$BUNDLE_DIR/network_ports.txt"
ss -tulnp > "$BUNDLE_DIR/network_sockets.txt" 2>/dev/null

# Create archive
tar -czf "${BUNDLE_DIR}.tar.gz" "$BUNDLE_DIR"
rm -rf "$BUNDLE_DIR"

echo "Support bundle created: ${BUNDLE_DIR}.tar.gz"
EOF

chmod +x create_support_bundle.sh
./create_support_bundle.sh
```

---

## Getting Additional Help

### Before Asking for Help

1. **Gather Information:**
   ```bash
   # Run diagnostics
   localagent health --comprehensive --output diagnostics.json
   
   # Create support bundle
   ./create_support_bundle.sh
   
   # Check documentation
   localagent --help
   localagent COMMAND --help
   ```

2. **Try Basic Solutions:**
   - Restart LocalAgent
   - Check configuration with `localagent config validate`
   - Test with minimal setup
   - Check logs for error messages

3. **Search Known Issues:**
   - Check the troubleshooting guide (this document)
   - Search GitHub issues
   - Check community forums

### Reporting Issues

When reporting issues, include:

1. **System Information:**
   - Operating system and version
   - Python version
   - LocalAgent version

2. **Error Description:**
   - What you were trying to do
   - What happened instead
   - Complete error messages

3. **Reproduction Steps:**
   - Minimal steps to reproduce the issue
   - Configuration used
   - Commands executed

4. **Diagnostic Information:**
   - Output from `localagent health --comprehensive`
   - Relevant log entries
   - Support bundle (if requested)

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Comprehensive guides and API reference  
- **Community Forum**: Get help from other users
- **Discord/Slack**: Real-time support and discussions

This troubleshooting guide should help resolve most common LocalAgent CLI issues. For persistent problems not covered here, please create a support bundle and report the issue through the appropriate channels.