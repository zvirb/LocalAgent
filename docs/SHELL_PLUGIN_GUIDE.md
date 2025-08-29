# LocalAgent CLI Shell Plugin Guide

## Overview

The LocalAgent CLI now includes a **secure shell command plugin** that enables controlled execution of shell commands with comprehensive security features. This plugin provides a safe way to run system commands while maintaining security through validation, risk assessment, and policy enforcement.

## Features

### 🛡️ Security Features
- **Command Risk Assessment** - Categorizes commands by risk level
- **Command Validation** - Blocks dangerous patterns and commands
- **Security Policies** - Configurable safety controls
- **Command Whitelisting** - Pre-approved safe commands
- **Pattern Blocking** - Prevents dangerous command patterns
- **Sandbox Mode** - Extra-restrictive environment

### 🔧 Functionality
- **Interactive Shell** - Full shell session with history
- **Direct Commands** - Execute single commands quickly
- **Command History** - Persistent command tracking
- **Working Directory** - Support for directory changes
- **Output Control** - Size limits and timeout controls
- **Error Recovery** - Integration with CLI error handling

## Installation

The shell plugin is **automatically included** as a built-in plugin when you install LocalAgent CLI. No additional installation required.

## Usage

### Basic Command Execution

```bash
# Execute a single command
localagent shell "ls -la"

# Quick shell alias
localagent sh "pwd"

# With options
localagent shell "git status" --timeout 60 --cwd /path/to/project
```

### Interactive Shell Mode

```bash
# Start interactive shell
localagent shell --interactive

# Interactive with reduced safety
localagent shell -i --unsafe
```

In interactive mode:
```bash
LocalAgent Interactive Shell
/current/directory $ ls -la
/current/directory $ cd /tmp
/tmp $ pwd
/tmp $ exit
```

### Command History

```bash
# Show recent commands
localagent shell-history

# Show more commands
localagent shell-history --count 20

# Search history
localagent shell-history --search "git"
```

### Security Policy

```bash
# View current security settings
localagent shell-policy
```

## Security Model

### Risk Levels

#### ✅ **SAFE** Commands
Commands that are generally safe to execute:
- `ls`, `pwd`, `echo`, `date`, `whoami`
- `cat`, `head`, `tail`, `grep`, `find`
- `ps`, `top`, `df`, `du`, `free`
- `git`, `python`, `node`, `npm`, `pip`

#### ⚠️ **MODERATE** Commands
Commands that may modify system state (require confirmation):
- `cp`, `mv`, `mkdir`, `touch`, `chmod`
- `docker`, `docker-compose`
- `apt`, `apt-get`, `yum`, `brew`

#### 🚨 **DANGEROUS** Commands  
Commands that can cause damage (blocked by default):
- `rm`, `rmdir`, `dd`, `format`
- `kill`, `killall`
- `shutdown`, `reboot`, `halt`

#### 🚫 **FORBIDDEN** Commands
Command patterns that are always blocked:
- Redirects to devices (`> /dev/...`)
- Pipes to sudo (`| sudo ...`)
- Destructive chains (`; rm -rf ...`)
- System file access (`/etc/passwd`, `/etc/shadow`)
- Command substitution (`$(...)` or backticks)

### Security Policies

Default security policy:
```yaml
allow_shell: false          # Don't use shell interpretation
allow_pipes: false          # Block pipe operators  
allow_redirects: false      # Block I/O redirection
allow_sudo: false           # Block sudo commands
max_execution_time: 30      # 30 second timeout
max_output_size: 1MB        # 1MB output limit
require_confirmation: true  # Ask before risky commands
log_commands: true          # Log all executions
sandbox_mode: false         # Standard restrictions
```

## Configuration

### Environment Variables

```bash
export LOCALAGENT_SHELL_POLICY_ALLOW_PIPES=true
export LOCALAGENT_SHELL_POLICY_MAX_EXECUTION_TIME=60
export LOCALAGENT_SHELL_POLICY_SANDBOX_MODE=false
```

### Configuration File

Add to your LocalAgent config:
```yaml
shell_policy:
  allow_pipes: true
  allow_redirects: false
  max_execution_time: 60
  require_confirmation: false
  sandbox_mode: false
```

## Examples

### Safe Commands (No Confirmation Required)
```bash
localagent sh "ls -la"                    # List files
localagent sh "git status"                # Check git status  
localagent sh "docker ps"                 # List containers
localagent sh "find . -name '*.py'"       # Find Python files
localagent sh "grep -r 'TODO' src/"       # Search for TODOs
```

### Interactive Development Workflow
```bash
localagent shell -i

# Inside interactive shell:
/project $ git status
/project $ git add .
/project $ git commit -m "Update features"
/project $ docker-compose up -d
/project $ curl http://localhost:8000/health
/project $ exit
```

### Advanced Usage
```bash
# Run in specific directory
localagent shell "make build" --cwd /path/to/project

# Extended timeout for long operations  
localagent shell "npm install" --timeout 300

# Disable safety for trusted scripts
localagent shell "./trusted-script.sh" --unsafe
```

## Integration with LocalAgent Features

### Error Recovery
The shell plugin integrates with LocalAgent's error recovery system:
- Automatic retry for transient failures
- Contextual error messages and suggestions
- Integration with interactive error resolution

### Workflow Integration
Shell commands can be used within LocalAgent workflows:
```bash
# Execute shell command as part of workflow
localagent workflow create "Deploy application" \
  --step "shell:git pull origin main" \
  --step "shell:docker-compose build" \
  --step "shell:docker-compose up -d"
```

### Plugin System
The shell plugin demonstrates the plugin architecture:
- Clean separation of concerns
- Security-first design
- Rich user experience integration
- Comprehensive error handling

## Safety Best Practices

### ✅ Recommended Practices
1. **Keep Safety Mode On** - Use `--safe` mode by default
2. **Review Dangerous Commands** - Always confirm risky operations
3. **Use Specific Directories** - Specify `--cwd` for context
4. **Monitor Command History** - Regular review of executed commands
5. **Configure Timeouts** - Set appropriate limits for long operations

### ❌ Things to Avoid
1. **Don't Disable All Safety** - Avoid `--unsafe` unless necessary
2. **Don't Run Untrusted Scripts** - Validate script contents first
3. **Don't Chain Dangerous Commands** - Avoid `rm -rf` in command chains
4. **Don't Access System Files** - Leave `/etc/passwd` alone
5. **Don't Use Sudo Unnecessarily** - Run with appropriate permissions

## Troubleshooting

### Common Issues

**Command Blocked as Dangerous:**
```bash
❌ Command is forbidden by security policy
```
- Check if command contains dangerous patterns
- Use `localagent shell-policy` to review restrictions
- Consider if the command is actually necessary

**Permission Denied:**
```bash  
❌ Permission denied
```
- Check file/directory permissions
- Ensure you're in the correct directory
- Consider if elevated permissions are needed

**Command Timeout:**
```bash
❌ Command timed out after 30 seconds
```
- Increase timeout with `--timeout` option
- Consider if command is stuck or needs more time
- Break long operations into smaller steps

**Plugin Not Found:**
```bash
❌ Command 'shell' not found
```
- Ensure LocalAgent CLI is properly installed
- Check that built-in plugins are loaded
- Try `localagent plugins list` to verify

### Debugging

Enable verbose output:
```bash
# Show command execution details
localagent shell "command" --verbose

# Show security policy decisions  
LOCALAGENT_DEBUG=true localagent shell "command"
```

View plugin status:
```bash
localagent plugins status shell
localagent system health
```

## Security Considerations

### Threat Model
The shell plugin protects against:
- **Accidental Damage** - Prevents common destructive commands
- **Injection Attacks** - Blocks command injection patterns  
- **Privilege Escalation** - Controls sudo usage
- **System Access** - Prevents access to sensitive files
- **Resource Abuse** - Limits execution time and output size

### Limitations
The shell plugin does NOT:
- Provide complete sandbox isolation
- Prevent all possible system modifications
- Replace proper system permissions
- Guarantee 100% security for all commands

### Recommendations
- Run LocalAgent CLI with appropriate user permissions
- Use dedicated service accounts for production
- Monitor shell command usage in logs
- Regularly review and update security policies
- Consider containerized execution for high-risk environments

## Development

### Extending the Plugin

To add custom security policies:
```python
from app.cli.plugins.builtin.shell_plugin import CommandPolicy

# Create custom policy
custom_policy = CommandPolicy(
    allow_pipes=True,
    allow_sudo=True,  # For development environments
    max_execution_time=120,
    sandbox_mode=False
)
```

To add custom command validation:
```python
from app.cli.plugins.builtin.shell_plugin import CommandValidator

class CustomValidator(CommandValidator):
    def assess_risk(self, command: str):
        # Add custom validation logic
        return super().assess_risk(command)
```

### Testing

Run the plugin test suite:
```bash
python3 scripts/test_shell_simple.py
```

## Changelog

### v1.0.0
- ✅ Initial secure shell plugin implementation
- ✅ Command risk assessment and validation
- ✅ Interactive shell mode with history
- ✅ Comprehensive security policies
- ✅ Integration with LocalAgent error recovery
- ✅ Built-in plugin architecture integration

---

**🎉 The LocalAgent CLI now supports secure shell command execution!**

For more information, see:
- [Plugin Framework Guide](CLI_IMPLEMENTATION_COMPLETE.md)
- [Error Recovery Documentation](CLI_ORCHESTRATION_AUDIT_REPORT.md) 
- [Security Best Practices](../config/secure_config_template.json)