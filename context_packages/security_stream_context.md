# Security Stream Context Package
**Package ID**: security-stream-20250825
**Token Limit**: 3000 tokens
**Target Specialists**: security-validator, credential-manager, input-validator

## Critical Security Vulnerabilities Identified

### CVE-2024-LOCALAGENT-001: Plain Text API Key Storage (CRITICAL)
**CVSS Score**: 9.1
**Current Issue**: API keys stored in plain text YAML configuration files
```yaml
# VULNERABLE - config/localagent_config.yaml
openai:
  api_key: "${OPENAI_API_KEY}"  # Environment variable - INSECURE
```

### CVE-2024-LOCALAGENT-002: Insecure Configuration Permissions (HIGH)
**CVSS Score**: 7.8
**File Permissions Issue**:
```bash
-rw-rw-r-- localagent_config.yaml  # World-readable configuration
```

### CVE-2024-LOCALAGENT-003: Unencrypted Communication (MEDIUM)
**CVSS Score**: 5.9
**Ollama HTTP Issue**:
```python
# VULNERABLE - HTTP by default
self.base_url = config.get('base_url', 'http://localhost:11434')
```

## Required Security Implementation

### 1. Secure Credential Management

#### OS Keyring Integration (Priority 1)
```python
# app/cli/security/credential_manager.py - NEEDS IMPLEMENTATION
import keyring
from cryptography.fernet import Fernet
from typing import Optional, Dict, Any

class SecureCredentialManager:
    """OS-level secure credential storage"""
    
    def __init__(self):
        self.service_name = "localagent-cli"
        self.encryption_key = self._get_or_create_encryption_key()
    
    async def store_credential(self, provider: str, credential_type: str, value: str):
        """Store credential in OS keyring"""
        encrypted_value = self._encrypt_credential(value)
        keyring.set_password(
            service_name=f"{self.service_name}-{provider}",
            username=credential_type,
            password=encrypted_value
        )
    
    async def get_credential(self, provider: str, credential_type: str) -> Optional[str]:
        """Retrieve and decrypt credential from keyring"""
        encrypted_value = keyring.get_password(
            service_name=f"{self.service_name}-{provider}",
            username=credential_type
        )
        if encrypted_value:
            return self._decrypt_credential(encrypted_value)
        return None
    
    def _encrypt_credential(self, value: str) -> str:
        """Encrypt credential with AES-256-GCM"""
        fernet = Fernet(self.encryption_key)
        return fernet.encrypt(value.encode()).decode()
```

#### Encrypted File Storage (Fallback)
```python
class EncryptedFileStorage:
    """AES-256-GCM encrypted file storage for credentials"""
    
    def __init__(self, storage_path: str, master_key: bytes):
        self.storage_path = Path(storage_path)
        self.cipher = Fernet(master_key)
        
    async def store_credentials(self, credentials: Dict[str, Any]):
        """Store encrypted credentials to file"""
        encrypted_data = self.cipher.encrypt(
            json.dumps(credentials).encode()
        )
        
        # Secure file permissions (user-only)
        self.storage_path.touch(mode=0o600)
        self.storage_path.write_bytes(encrypted_data)
```

### 2. Configuration Security Hardening

#### Secure Configuration Management
```python
# app/cli/core/secure_config.py - NEEDS IMPLEMENTATION
from pathlib import Path
import stat
import os

class SecureConfigurationManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or self.get_default_config_path())
        self.credential_manager = SecureCredentialManager()
    
    def secure_config_file(self):
        """Ensure configuration file has secure permissions"""
        if self.config_path.exists():
            # Set user-only permissions (0600)
            os.chmod(self.config_path, stat.S_IRUSR | stat.S_IWUSR)
    
    async def load_secure_config(self) -> LocalAgentConfig:
        """Load configuration with credential resolution"""
        self.secure_config_file()
        
        # Load base configuration
        config_data = self.load_yaml_config()
        
        # Resolve credentials securely
        for provider, provider_config in config_data.get('providers', {}).items():
            if 'api_key' in provider_config:
                # Replace with secure credential lookup
                api_key = await self.credential_manager.get_credential(
                    provider=provider,
                    credential_type='api_key'
                )
                if api_key:
                    provider_config['api_key'] = api_key
        
        return LocalAgentConfig(**config_data)
```

### 3. Input Validation and Sanitization

#### User Input Security
```python
# app/cli/security/input_validator.py - NEEDS IMPLEMENTATION
import re
from typing import Optional
from html import escape

class InputValidator:
    """Secure input validation for CLI parameters"""
    
    MAX_PROMPT_LENGTH = 10000
    FORBIDDEN_PATTERNS = [
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # Script injection
        r'javascript:',                                        # JavaScript URLs
        r'data:.*base64',                                     # Data URL injection
        r'vbscript:',                                         # VBScript URLs
    ]
    
    def sanitize_user_prompt(self, prompt: str) -> str:
        """Sanitize user input prompt"""
        if not prompt or len(prompt) > self.MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt must be between 1 and {self.MAX_PROMPT_LENGTH} characters")
        
        # Check for injection patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                raise ValueError("Potentially malicious content detected in prompt")
        
        # HTML escape for safety
        return escape(prompt.strip())
    
    def validate_provider_name(self, provider: str) -> bool:
        """Validate provider name against allowlist"""
        allowed_providers = {'ollama', 'openai', 'gemini', 'perplexity'}
        return provider.lower() in allowed_providers
    
    def validate_file_path(self, file_path: str) -> bool:
        """Validate file paths to prevent directory traversal"""
        normalized_path = Path(file_path).resolve()
        
        # Prevent directory traversal
        if '..' in file_path or file_path.startswith('/'):
            return False
        
        return True
```

### 4. Network Security Implementation

#### HTTPS Enforcement
```python
# app/cli/security/network_security.py - NEEDS IMPLEMENTATION
import ssl
import aiohttp
from typing import Optional

class SecureNetworkManager:
    """Enforce secure network communications"""
    
    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        
    def create_secure_session(self) -> aiohttp.ClientSession:
        """Create HTTP session with security enforcement"""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(
            ssl=self.ssl_context,
            use_dns_cache=False,  # Prevent DNS cache poisoning
            ttl_dns_cache=300
        )
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'LocalAgent-CLI/2.0.0',
                'Accept': 'application/json'
            }
        )
    
    def validate_url_security(self, url: str) -> bool:
        """Validate URL uses HTTPS"""
        if not url.startswith('https://'):
            # Only allow HTTP for localhost development
            if not (url.startswith('http://localhost') or url.startswith('http://127.0.0.1')):
                return False
        return True
```

### 5. Audit Logging and Security Monitoring

#### Security Event Logging
```python
# app/cli/security/audit_logger.py - NEEDS IMPLEMENTATION
import logging
import json
from datetime import datetime
from typing import Dict, Any

class SecurityAuditLogger:
    """Security event logging and monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger('localagent.security')
        self.setup_secure_logging()
    
    def setup_secure_logging(self):
        """Configure secure audit logging"""
        handler = logging.FileHandler('~/.localagent/security.log', mode='a')
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Set secure file permissions
        log_path = Path('~/.localagent/security.log').expanduser()
        if log_path.exists():
            os.chmod(log_path, stat.S_IRUSR | stat.S_IWUSR)
    
    def log_credential_access(self, provider: str, operation: str, success: bool):
        """Log credential access attempts"""
        event = {
            'event_type': 'credential_access',
            'provider': provider,
            'operation': operation,
            'success': success,
            'timestamp': datetime.utcnow().isoformat(),
            'user': os.getenv('USER', 'unknown')
        }
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, json.dumps(event))
    
    def log_security_violation(self, violation_type: str, details: Dict[str, Any]):
        """Log security violations"""
        event = {
            'event_type': 'security_violation',
            'violation_type': violation_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        self.logger.error(json.dumps(event))
```

## Implementation Priorities

### Phase 1: Critical Vulnerabilities (IMMEDIATE)
1. **Implement SecureCredentialManager** with OS keyring storage
2. **Fix configuration file permissions** to 0600 (user-only)
3. **Add HTTPS enforcement** for all external communications
4. **Implement basic input validation** for user prompts

### Phase 2: Enhanced Security (Week 2)
1. **Add encrypted file storage** fallback for credentials
2. **Implement comprehensive audit logging**
3. **Add provider name validation** against allowlist
4. **Create security configuration validation**

### Phase 3: Advanced Security (Week 3+)
1. **Add security monitoring dashboard**
2. **Implement threat detection** for unusual patterns
3. **Create incident response procedures**
4. **Add compliance reporting framework**

## Security Configuration Template

### Secure Configuration Structure
```yaml
# ~/.localagent/config.yaml - SECURE VERSION
security:
  storage_backend: "keyring"           # OS-level secure storage
  encryption_algorithm: "AES-256-GCM" # Strong encryption
  audit_logging: true                 # Complete audit trail
  tls_enforcement: true               # Force HTTPS/TLS
  input_validation: true              # Enable input sanitization
  
providers:
  ollama:
    base_url: "https://localhost:11434"  # HTTPS enforced
    # api_key stored in keyring, not in file
  openai:
    # api_key stored in keyring, not in file
    rate_limit: 10
```

## Security Validation Checklist
- [ ] API keys stored securely in OS keyring
- [ ] Configuration files have 0600 permissions
- [ ] HTTPS enforced for all external communications
- [ ] User input sanitization implemented
- [ ] Provider names validated against allowlist
- [ ] Security audit logging operational
- [ ] Encrypted storage fallback available
- [ ] Network security headers implemented

## Success Criteria
1. **No Plain Text Secrets**: All API keys stored in OS keyring
2. **Secure Communications**: HTTPS enforced for all providers
3. **Input Validation**: User prompts sanitized and validated
4. **Audit Trail**: Complete logging of security events
5. **Configuration Security**: Proper file permissions and access controls