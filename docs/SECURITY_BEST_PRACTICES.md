# LocalAgent CLI Security Best Practices

## Overview

This document outlines security best practices for developing, deploying, and maintaining the LocalAgent CLI tools. These practices are derived from comprehensive security validation and industry standards.

## Input Validation and Sanitization

### 1. Use the Input Validation Framework

Always use the comprehensive input validation framework located in `app/cli/security/input_validation_framework.py`:

```python
from app.cli.security.input_validation_framework import InputValidator, ValidationLevel

# Create validator with appropriate strictness
validator = InputValidator(ValidationLevel.STRICT)

# Validate user input
result = validator.validate(user_input, ['sql_safe', 'xss_safe'], 'user_field')
if not result['valid']:
    raise ValidationError(f"Invalid input: {', '.join(result['errors'])}")

# Use sanitized value
clean_value = result['sanitized_value']
```

### 2. Built-in Validation Rules

The framework includes comprehensive validation rules:

- **`sql_safe`**: Protects against SQL injection
- **`xss_safe`**: Protects against Cross-Site Scripting
- **`file_path`**: Prevents path traversal attacks
- **`command`**: Prevents command injection
- **`api_key`**: Validates API key format and security
- **`provider_name`**: Validates provider names
- **`email`**: Validates email format
- **`url`**: Validates and sanitizes URLs

### 3. Custom Validation Rules

Create custom validation rules for specific use cases:

```python
from app.cli.security.input_validation_framework import ValidationRule

# Custom rule for project names
project_name_rule = ValidationRule(
    name='project_name',
    validator=lambda x: isinstance(x, str) and len(x) <= 50 and x.isalnum(),
    message='Project name must be alphanumeric and max 50 characters',
    sanitizer=lambda x: x.strip().lower()
)

validator.add_custom_rule(project_name_rule)
```

## Secure File Operations

### 1. Always Use Atomic Operations

Use the atomic file operations framework for all file manipulations:

```python
from app.cli.io.atomic import AtomicWriter

# Atomic file writing with integrity checking
async with AtomicWriter(
    target_path='/path/to/config.json',
    backup=True,
    verify_integrity=True
) as writer:
    await writer.write_json(config_data)
```

### 2. Proper File Permissions

Ensure sensitive files have restrictive permissions:

```python
import stat
from pathlib import Path

# Set secure permissions (owner read/write only)
config_file = Path('/path/to/sensitive/config')
config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600

# For directories (owner read/write/execute)
config_dir = Path('/path/to/sensitive/directory')
config_dir.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)  # 0700
```

### 3. Safe Temporary Files

Always use secure temporary file creation:

```python
import tempfile
import os

# Create secure temporary file
with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
    temp_path = tf.name
    # File automatically has secure permissions (0600)
    tf.write(sensitive_data)

try:
    # Process temporary file
    process_file(temp_path)
finally:
    # Always clean up
    os.unlink(temp_path)
```

## Credential and Secret Management

### 1. Use SecureKeyManager

Always use the secure key manager for API keys and secrets:

```python
from app.security.key_manager import SecureKeyManager

# Initialize key manager
key_manager = SecureKeyManager('localagent_cli')

# Store API key securely
success = key_manager.store_api_key(
    provider='openai',
    api_key=api_key,
    metadata={
        'created_by': 'cli_setup',
        'environment': 'production'
    }
)

# Retrieve API key
api_key = key_manager.retrieve_api_key('openai')
```

### 2. Never Hardcode Secrets

❌ **NEVER do this:**
```python
API_KEY = "sk-1234567890abcdef"  # Hardcoded secret
DATABASE_PASSWORD = "mypassword123"  # Hardcoded password
```

✅ **Instead do this:**
```python
import os
from app.security.key_manager import SecureKeyManager

# Use environment variables for development
api_key = os.getenv('OPENAI_API_KEY')

# Use secure key manager for production
key_manager = SecureKeyManager()
api_key = key_manager.retrieve_api_key('openai')
```

### 3. Secure Configuration Storage

Use the secure configuration manager:

```python
from app.cli.security.secure_config_manager import SecureConfigManager

# Initialize secure config manager
config_manager = SecureConfigManager()

# Store provider configuration securely
config_manager.store_provider_config(
    provider='openai',
    config={
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4',
        'timeout': 60
    },
    include_api_key=True  # API key stored separately in keyring
)
```

## Path Security and Traversal Prevention

### 1. Validate All File Paths

Always validate file paths to prevent traversal attacks:

```python
from pathlib import Path
from app.cli.security.input_validation_framework import InputValidator

validator = InputValidator()

# Validate file path
result = validator.validate(user_path, ['file_path'], 'config_file')
if not result['valid']:
    raise SecurityError("Invalid file path")

safe_path = Path(result['sanitized_value'])
```

### 2. Restrict File Access

Limit file operations to safe directories:

```python
from pathlib import Path

def safe_file_access(file_path: str, allowed_base: Path) -> Path:
    """Ensure file access is within allowed directory."""
    path = Path(file_path).resolve()
    allowed_base = allowed_base.resolve()
    
    # Check if path is within allowed base
    try:
        path.relative_to(allowed_base)
        return path
    except ValueError:
        raise SecurityError(f"Access denied: {file_path} outside allowed directory")

# Usage
config_dir = Path.home() / '.localagent'
safe_file = safe_file_access(user_provided_path, config_dir)
```

## Environment Variable Security

### 1. Sanitize Environment Variables

Always validate environment variables:

```python
import os
from app.cli.security.input_validation_framework import InputValidator

def get_safe_env_var(name: str, validator_rules: list = None) -> str:
    """Get environment variable with validation."""
    value = os.getenv(name)
    if not value:
        return None
    
    if validator_rules:
        validator = InputValidator()
        result = validator.validate(value, validator_rules, name)
        if not result['valid']:
            raise ValueError(f"Invalid environment variable {name}")
        return result['sanitized_value']
    
    return value

# Usage
api_key = get_safe_env_var('OPENAI_API_KEY', ['api_key'])
log_level = get_safe_env_var('LOG_LEVEL', ['sql_safe'])  # Prevent injection
```

### 2. Filter Sensitive Variables

Avoid exposing sensitive environment variables in logs:

```python
import os

SENSITIVE_ENV_PATTERNS = [
    'password', 'secret', 'key', 'token', 'auth'
]

def is_sensitive_env_var(var_name: str) -> bool:
    """Check if environment variable contains sensitive data."""
    var_lower = var_name.lower()
    return any(pattern in var_lower for pattern in SENSITIVE_ENV_PATTERNS)

def safe_env_dump():
    """Dump environment variables safely."""
    safe_vars = {}
    for key, value in os.environ.items():
        if is_sensitive_env_var(key):
            safe_vars[key] = '[REDACTED]'
        else:
            safe_vars[key] = value
    return safe_vars
```

## Audit Logging and Monitoring

### 1. Enable Comprehensive Audit Logging

Use the built-in audit logging system:

```python
from app.security.audit import AuditLogger

# Initialize audit logger
audit_logger = AuditLogger()

# Log security events
audit_logger.log_security_event(
    event_type='api_key_access',
    description='API key retrieved for provider',
    details={'provider': 'openai', 'user': 'admin'},
    severity='INFO'
)

# Log key operations
audit_logger.log_key_operation(
    operation='config_updated',
    details={'config_type': 'provider', 'provider': 'openai'}
)
```

### 2. Monitor Security Statistics

Track validation statistics for security monitoring:

```python
from app.cli.security.input_validation_framework import InputValidator

validator = InputValidator()

# Get security statistics
stats = validator.get_statistics()
print(f"Security violations: {stats['security_violations_detected']}")
print(f"Validation success rate: {stats['success_rate']:.2f}%")

# Reset statistics periodically
validator.reset_statistics()
```

## Error Handling and Information Disclosure

### 1. Secure Error Handling

Avoid exposing sensitive information in errors:

```python
import logging

logger = logging.getLogger(__name__)

def secure_error_handler(e: Exception, user_message: str = "Operation failed"):
    """Handle errors securely without information disclosure."""
    # Log detailed error for debugging (not shown to user)
    logger.error(f"Internal error: {str(e)}", exc_info=True)
    
    # Return generic error to user
    raise SecurityError(user_message)

# Usage
try:
    process_sensitive_data(user_input)
except ValidationError as e:
    secure_error_handler(e, "Invalid input provided")
except FileNotFoundError as e:
    secure_error_handler(e, "File operation failed")
```

### 2. Sanitize Log Messages

Ensure logs don't contain sensitive data:

```python
import re
import logging

class SecureFormatter(logging.Formatter):
    """Custom formatter that redacts sensitive information."""
    
    REDACT_PATTERNS = [
        (re.compile(r'password["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', re.I), 'password=***'),
        (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', re.I), 'api_key=***'),
        (re.compile(r'token["\']?\s*[:=]\s*["\']?([^"\'\\s]+)', re.I), 'token=***'),
    ]
    
    def format(self, record):
        message = super().format(record)
        for pattern, replacement in self.REDACT_PATTERNS:
            message = pattern.sub(replacement, message)
        return message
```

## Testing Security Controls

### 1. Input Validation Tests

Always test validation rules:

```python
import pytest
from app.cli.security.input_validation_framework import InputValidator

def test_sql_injection_protection():
    """Test SQL injection protection."""
    validator = InputValidator()
    
    # Test malicious inputs
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM passwords",
        "admin'--",
    ]
    
    for malicious_input in malicious_inputs:
        result = validator.validate(malicious_input, ['sql_safe'])
        assert not result['valid'], f"Should block: {malicious_input}"

def test_path_traversal_protection():
    """Test path traversal protection."""
    validator = InputValidator()
    
    dangerous_paths = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "~/../.ssh/id_rsa"
    ]
    
    for path in dangerous_paths:
        result = validator.validate(path, ['file_path'])
        assert not result['valid'], f"Should block: {path}"
```

### 2. File Security Tests

Test file operation security:

```python
import tempfile
import stat
from pathlib import Path

def test_file_permissions():
    """Test that sensitive files have correct permissions."""
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        temp_file = Path(tf.name)
        
        # Check permissions
        permissions = oct(temp_file.stat().st_mode)[-3:]
        assert permissions <= '600', f"File permissions too permissive: {permissions}"
        
        temp_file.unlink()
```

## Deployment Security

### 1. Production Environment Setup

Secure configuration for production:

```bash
# Set restrictive umask
umask 077

# Create secure directories
mkdir -p ~/.localagent/{config,logs,cache}
chmod 700 ~/.localagent
chmod 700 ~/.localagent/config
chmod 755 ~/.localagent/logs  # Logs can be readable for monitoring
chmod 700 ~/.localagent/cache

# Set secure environment variables
export LOCALAGENT_LOG_LEVEL=INFO
export LOCALAGENT_AUDIT_ENABLED=true
```

### 2. System Hardening

Additional system security measures:

- Enable firewall with minimal required ports
- Use fail2ban for intrusion detection
- Regular security updates
- Monitor file integrity
- Implement log rotation and monitoring

## Security Checklist

### Development Checklist

- [ ] All user inputs validated using InputValidator
- [ ] No hardcoded secrets or credentials
- [ ] Atomic file operations used for sensitive data
- [ ] Proper file permissions set (0600 for files, 0700 for directories)
- [ ] Comprehensive error handling without information disclosure
- [ ] Audit logging enabled for security events
- [ ] Path traversal protection implemented
- [ ] Environment variable validation

### Deployment Checklist

- [ ] Secure key manager initialized
- [ ] Configuration files encrypted
- [ ] Audit logging enabled and configured
- [ ] Log rotation configured
- [ ] System monitoring in place
- [ ] Regular security updates scheduled
- [ ] Backup and recovery procedures tested

### Testing Checklist

- [ ] Input validation tests written and passing
- [ ] Path traversal tests implemented
- [ ] File permission tests validated
- [ ] Security statistics monitoring functional
- [ ] Error handling tests verify no information disclosure
- [ ] Penetration testing completed

## Incident Response

### 1. Security Event Response

If a security issue is detected:

1. **Immediate Actions**:
   - Stop the affected service
   - Preserve logs and audit trails
   - Assess the scope of the incident

2. **Investigation**:
   - Review audit logs
   - Check validation statistics
   - Analyze error patterns

3. **Remediation**:
   - Apply security patches
   - Update validation rules
   - Enhance monitoring

### 2. Vulnerability Management

Regular security maintenance:

- Monthly security updates
- Quarterly penetration testing
- Annual security audits
- Continuous monitoring of validation statistics

## Support and Resources

### Internal Resources
- Security validation framework: `app/cli/security/`
- Audit logging system: `app/security/audit.py`
- Secure key manager: `app/security/key_manager.py`

### External Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE Top 25](https://cwe.mitre.org/top25/)

---

**Document Version**: 1.0  
**Last Updated**: August 26, 2025  
**Review Schedule**: Quarterly  
**Owner**: Security Team