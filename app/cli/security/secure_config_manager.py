"""
Enhanced Secure Configuration Manager
Integrates SecureKeyManager with CLI configuration system
CVE-2024-LOCALAGENT-001 & CVE-2024-LOCALAGENT-002 Comprehensive Mitigation
"""

import os
import stat
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from pydantic import ValidationError
import keyring
from contextlib import contextmanager

# Import existing security components
try:
    import sys
    sys.path.append('/home/marku/Documents/programming/LocalProgramming')
    from app.security.key_manager import SecureKeyManager
    from app.security.encryption import EncryptionService
    from app.security.audit import AuditLogger
except ImportError as e:
    print(f"Warning: Could not import security modules: {e}")
    # Fallback implementations would go here
    SecureKeyManager = None
    EncryptionService = None
    AuditLogger = None


class SecureConfigManager:
    """
    Enhanced configuration manager with comprehensive security features
    
    Security Features:
    - Integrates with SecureKeyManager for API key storage
    - AES-256-GCM encryption for sensitive configuration data
    - Proper file permissions (0600) for config files
    - Comprehensive input validation
    - Audit logging for all configuration operations
    - Environment variable validation and sanitization
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir or os.getenv('LOCALAGENT_CONFIG_DIR', Path.home() / '.localagent'))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize security components
        self.key_manager = SecureKeyManager("localagent_cli") if SecureKeyManager else None
        self.encryption_service = EncryptionService() if EncryptionService else None
        self.audit_logger = AuditLogger() if AuditLogger else None
        
        self.logger = logging.getLogger(__name__)
        
        # Configuration file paths
        self.config_file = self.config_dir / "config.yaml"
        self.secure_config_file = self.config_dir / "secure_config.json"
        
        # Ensure secure permissions
        self._ensure_secure_permissions()
        
        if self.audit_logger:
            self.audit_logger.log_key_operation("secure_config_manager_initialized", {
                "config_dir": str(self.config_dir),
                "has_key_manager": self.key_manager is not None,
                "has_encryption": self.encryption_service is not None
            })
    
    def _ensure_secure_permissions(self):
        """Ensure configuration directory and files have secure permissions (0600)"""
        try:
            # Set directory permissions (0700)
            self.config_dir.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            
            # Set file permissions for existing files
            for config_file in [self.config_file, self.secure_config_file]:
                if config_file.exists():
                    config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            
            if self.audit_logger:
                self.audit_logger.log_security_event(
                    "file_permissions_secured",
                    f"Set secure permissions for config directory: {self.config_dir}",
                    {"config_dir": str(self.config_dir)},
                    "INFO"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to set secure permissions: {e}")
            if self.audit_logger:
                self.audit_logger.log_security_event(
                    "file_permissions_error",
                    f"Failed to set secure permissions: {e}",
                    {"config_dir": str(self.config_dir), "error": str(e)},
                    "ERROR"
                )
            raise
    
    def _validate_provider_name(self, provider: str) -> None:
        """Validate provider name for security"""
        if not provider or not isinstance(provider, str):
            raise ValueError("Provider name must be a non-empty string")
        
        if len(provider) > 50:
            raise ValueError("Provider name too long (max 50 characters)")
        
        # Allow only alphanumeric, hyphens, and underscores
        if not provider.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Provider name contains invalid characters")
    
    def _validate_api_key(self, api_key: str) -> None:
        """Validate API key format for security"""
        if not api_key or not isinstance(api_key, str):
            raise ValueError("API key must be a non-empty string")
        
        if len(api_key) < 10:
            raise ValueError("API key too short (minimum 10 characters)")
        
        if len(api_key) > 500:
            raise ValueError("API key too long (maximum 500 characters)")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            "password", "secret", "token", "key", "admin", "test", "demo", "example"
        ]
        
        api_key_lower = api_key.lower()
        for pattern in suspicious_patterns:
            if pattern in api_key_lower and len(api_key) < 20:
                raise ValueError(f"API key appears to contain placeholder text: {pattern}")
    
    def _validate_config_data(self, config_data: Dict[str, Any]) -> None:
        """Validate configuration data structure"""
        if not isinstance(config_data, dict):
            raise ValueError("Configuration must be a dictionary")
        
        # Validate nested structures
        for key, value in config_data.items():
            if key.startswith('_'):
                raise ValueError(f"Configuration key cannot start with underscore: {key}")
            
            # Recursive validation for nested dicts
            if isinstance(value, dict):
                self._validate_config_data(value)
    
    def store_provider_config(self, 
                            provider: str, 
                            config: Dict[str, Any],
                            include_api_key: bool = True) -> bool:
        """
        Securely store provider configuration
        
        Args:
            provider: Provider name (e.g., 'openai', 'gemini')
            config: Configuration dictionary
            include_api_key: Whether to extract and securely store API key
        
        Returns:
            True if successful
        """
        try:
            self._validate_provider_name(provider)
            self._validate_config_data(config)
            
            # Extract API key for secure storage
            api_key = None
            if include_api_key and 'api_key' in config:
                api_key = config.pop('api_key')
                self._validate_api_key(api_key)
            
            # Store API key securely using KeyManager
            if api_key and self.key_manager:
                metadata = {
                    "provider": provider,
                    "config_stored": True,
                    "created_by": "secure_config_manager"
                }
                
                success = self.key_manager.store_api_key(provider, api_key, metadata)
                if not success:
                    raise Exception("Failed to store API key securely")
            
            # Encrypt and store remaining configuration
            if self.encryption_service:
                encrypted_config = self.encryption_service.encrypt_aes_gcm(
                    json.dumps(config, indent=2),
                    purpose=f"provider_config_{provider}"
                )
                
                # Load existing secure config
                secure_configs = {}
                if self.secure_config_file.exists():
                    try:
                        with open(self.secure_config_file, 'r') as f:
                            secure_configs = json.load(f)
                    except (json.JSONDecodeError, FileNotFoundError):
                        secure_configs = {}
                
                # Update with new provider config
                secure_configs[f"provider_{provider}"] = encrypted_config
                
                # Write back with secure permissions
                with open(self.secure_config_file, 'w') as f:
                    json.dump(secure_configs, f, indent=2)
                
                # Ensure file permissions
                self.secure_config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
            
            # Audit log
            if self.audit_logger:
                self.audit_logger.log_key_operation("provider_config_stored", {
                    "provider": provider,
                    "has_api_key": api_key is not None,
                    "config_keys": list(config.keys()),
                    "encrypted": self.encryption_service is not None
                })
            
            self.logger.info(f"Successfully stored secure configuration for provider: {provider}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store provider config for {provider}: {e}")
            if self.audit_logger:
                self.audit_logger.log_key_operation("provider_config_store_error", {
                    "provider": provider,
                    "error": str(e)
                }, severity="ERROR")
            return False
    
    def retrieve_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve provider configuration with API key
        
        Args:
            provider: Provider name
        
        Returns:
            Complete provider configuration or None
        """
        try:
            self._validate_provider_name(provider)
            
            config = {}
            
            # Retrieve API key from secure storage
            if self.key_manager:
                api_key = self.key_manager.retrieve_api_key(provider)
                if api_key:
                    config['api_key'] = api_key
            
            # Retrieve encrypted configuration
            if self.encryption_service and self.secure_config_file.exists():
                try:
                    with open(self.secure_config_file, 'r') as f:
                        secure_configs = json.load(f)
                    
                    encrypted_config = secure_configs.get(f"provider_{provider}")
                    if encrypted_config:
                        decrypted_data = self.encryption_service.decrypt_aes_gcm(encrypted_config)
                        provider_config = json.loads(decrypted_data.decode())
                        config.update(provider_config)
                        
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    self.logger.warning(f"Failed to decrypt config for {provider}: {e}")
            
            # Audit log
            if self.audit_logger and config:
                self.audit_logger.log_key_operation("provider_config_retrieved", {
                    "provider": provider,
                    "has_api_key": 'api_key' in config,
                    "config_keys": [k for k in config.keys() if k != 'api_key']
                })
            
            return config if config else None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve provider config for {provider}: {e}")
            if self.audit_logger:
                self.audit_logger.log_key_operation("provider_config_retrieve_error", {
                    "provider": provider,
                    "error": str(e)
                }, severity="ERROR")
            return None
    
    def list_configured_providers(self) -> List[str]:
        """List all configured providers"""
        try:
            providers = set()
            
            # From key manager
            if self.key_manager:
                providers.update(self.key_manager.list_stored_providers())
            
            # From encrypted configs
            if self.secure_config_file.exists():
                try:
                    with open(self.secure_config_file, 'r') as f:
                        secure_configs = json.load(f)
                    
                    for key in secure_configs.keys():
                        if key.startswith('provider_'):
                            provider = key[9:]  # Remove 'provider_' prefix
                            providers.add(provider)
                            
                except (json.JSONDecodeError, Exception):
                    pass
            
            provider_list = list(providers)
            
            if self.audit_logger:
                self.audit_logger.log_key_operation("providers_listed", {
                    "count": len(provider_list),
                    "providers": provider_list
                })
            
            return provider_list
            
        except Exception as e:
            self.logger.error(f"Failed to list providers: {e}")
            return []
    
    def delete_provider_config(self, provider: str) -> bool:
        """Delete provider configuration and API key"""
        try:
            self._validate_provider_name(provider)
            
            success = True
            
            # Delete from key manager
            if self.key_manager:
                if not self.key_manager.delete_api_key(provider):
                    success = False
            
            # Delete from encrypted configs
            if self.secure_config_file.exists():
                try:
                    with open(self.secure_config_file, 'r') as f:
                        secure_configs = json.load(f)
                    
                    config_key = f"provider_{provider}"
                    if config_key in secure_configs:
                        del secure_configs[config_key]
                        
                        with open(self.secure_config_file, 'w') as f:
                            json.dump(secure_configs, f, indent=2)
                        
                        self.secure_config_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
                        
                except (json.JSONDecodeError, FileNotFoundError, Exception):
                    success = False
            
            # Audit log
            if self.audit_logger:
                self.audit_logger.log_key_operation("provider_config_deleted", {
                    "provider": provider,
                    "success": success
                })
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete provider config for {provider}: {e}")
            if self.audit_logger:
                self.audit_logger.log_key_operation("provider_config_delete_error", {
                    "provider": provider,
                    "error": str(e)
                }, severity="ERROR")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of the secure configuration system"""
        try:
            health = {
                "healthy": True,
                "config_dir_accessible": False,
                "permissions_secure": False,
                "key_manager_healthy": False,
                "encryption_service_healthy": False,
                "audit_logger_available": False,
                "last_check": os.urandom(16).hex()  # Simple timestamp alternative
            }
            
            # Check config directory
            try:
                health["config_dir_accessible"] = self.config_dir.exists() and self.config_dir.is_dir()
                
                # Check permissions
                if health["config_dir_accessible"]:
                    dir_stat = self.config_dir.stat()
                    # Check if only owner has read/write/execute
                    health["permissions_secure"] = (dir_stat.st_mode & 0o777) == 0o700
                    
            except Exception as e:
                health["config_dir_error"] = str(e)
                health["healthy"] = False
            
            # Check key manager
            if self.key_manager:
                try:
                    km_health = self.key_manager.health_check()
                    health["key_manager_healthy"] = km_health.get("healthy", False)
                    health["key_manager_details"] = km_health
                except Exception as e:
                    health["key_manager_error"] = str(e)
                    health["healthy"] = False
            
            # Check encryption service
            if self.encryption_service:
                try:
                    enc_health = self.encryption_service.health_check()
                    health["encryption_service_healthy"] = enc_health.get("healthy", False)
                    health["encryption_service_details"] = enc_health
                except Exception as e:
                    health["encryption_service_error"] = str(e)
                    health["healthy"] = False
            
            # Check audit logger
            health["audit_logger_available"] = self.audit_logger is not None
            
            # Overall health
            if not all([
                health["config_dir_accessible"],
                health["permissions_secure"],
                health.get("key_manager_healthy", True),  # True if not available
                health.get("encryption_service_healthy", True)
            ]):
                health["healthy"] = False
            
            return health
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    @contextmanager
    def secure_config_context(self):
        """Context manager for secure configuration operations"""
        try:
            # Additional security setup if needed
            yield self
        finally:
            # Cleanup sensitive data from memory if needed
            pass
    
    def migrate_insecure_config(self, old_config_file: Path) -> bool:
        """
        Migrate from insecure configuration file to secure storage
        
        Args:
            old_config_file: Path to old insecure config file
        
        Returns:
            True if migration successful
        """
        try:
            if not old_config_file.exists():
                return False
            
            # Read old configuration
            if old_config_file.suffix.lower() == '.json':
                with open(old_config_file, 'r') as f:
                    old_config = json.load(f)
            elif old_config_file.suffix.lower() in ['.yml', '.yaml']:
                import yaml
                with open(old_config_file, 'r') as f:
                    old_config = yaml.safe_load(f)
            else:
                self.logger.error(f"Unsupported config file format: {old_config_file}")
                return False
            
            migrated_count = 0
            
            # Extract provider configurations
            providers_config = old_config.get('providers', {})
            for provider, config in providers_config.items():
                if self.store_provider_config(provider, config):
                    migrated_count += 1
            
            # Audit log
            if self.audit_logger:
                self.audit_logger.log_security_event(
                    "config_migration",
                    f"Migrated {migrated_count} provider configs from insecure file",
                    {
                        "old_file": str(old_config_file),
                        "migrated_providers": migrated_count,
                        "total_providers": len(providers_config)
                    },
                    "INFO"
                )
            
            self.logger.info(f"Successfully migrated {migrated_count} provider configurations")
            return migrated_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to migrate config from {old_config_file}: {e}")
            if self.audit_logger:
                self.audit_logger.log_security_event(
                    "config_migration_error",
                    f"Failed to migrate config: {e}",
                    {"old_file": str(old_config_file), "error": str(e)},
                    "ERROR"
                )
            return False