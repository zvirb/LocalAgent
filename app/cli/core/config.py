"""
Configuration Management System
Environment-based configuration with validation and hot-reload capabilities
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import yaml
import json
import keyring
from rich.console import Console

console = Console()

class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider"""
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    timeout: int = Field(default=120, ge=1, le=600)
    rate_limit: Optional[int] = Field(default=None, ge=1)
    enabled: bool = Field(default=True)
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('base_url must start with http:// or https://')
        return v

class OrchestrationConfig(BaseModel):
    """Orchestration system configuration"""
    max_parallel_agents: int = Field(default=10, ge=1, le=50)
    max_workflow_iterations: int = Field(default=3, ge=1, le=10)
    enable_evidence_collection: bool = Field(default=True)
    enable_cross_session_continuity: bool = Field(default=True)
    default_timeout: int = Field(default=300, ge=30, le=3600)

class MCPConfig(BaseModel):
    """MCP (Memory/Context/Protocol) configuration"""
    redis_url: str = Field(default="redis://localhost:6379")
    memory_retention_days: int = Field(default=7, ge=1, le=365)
    enable_timeline: bool = Field(default=True)
    enable_context_compression: bool = Field(default=True)

class PluginConfig(BaseModel):
    """Plugin system configuration"""
    enabled_plugins: List[str] = Field(default_factory=list)
    auto_load_plugins: bool = Field(default=True)
    plugin_directories: List[str] = Field(default_factory=lambda: ["~/.localagent/plugins"])
    allow_dev_plugins: bool = Field(default=False)

class LocalAgentConfig(BaseModel):
    """Main LocalAgent configuration model"""
    
    # Core settings
    config_dir: Path = Field(default_factory=lambda: Path.home() / ".localagent")
    log_level: str = Field(default="INFO")
    debug_mode: bool = Field(default=False)
    
    # Provider configurations
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    default_provider: str = Field(default="ollama")
    
    # System configurations
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    
    # File paths
    config_file: Optional[Path] = None
    
    @model_validator(mode='before')
    @classmethod
    def validate_config(cls, values):
        """Validate the overall configuration"""
        # Ensure default provider exists in providers
        default_provider = values.get('default_provider')
        providers = values.get('providers', {})
        
        if default_provider and default_provider not in providers:
            # Add default provider config
            providers[default_provider] = ProviderConfig()
            values['providers'] = providers
        
        # Ensure config directory exists
        config_dir = values.get('config_dir')
        if config_dir:
            config_dir.mkdir(exist_ok=True, parents=True)
        
        return values
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    def is_configured(self) -> bool:
        """Check if the configuration is properly set up"""
        return bool(self.providers and self.default_provider in self.providers)
    
    def is_valid(self) -> bool:
        """Check if the configuration is valid"""
        try:
            self.__class__(**self.dict())
            return True
        except Exception:
            return False
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider"""
        return self.providers.get(provider_name)
    
    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled providers"""
        return [name for name, config in self.providers.items() if config.enabled]

class ConfigurationManager:
    """Manages LocalAgent configuration from multiple sources"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else None
        self.config: Optional[LocalAgentConfig] = None
        self.config_sources: List[str] = []
        self.keyring_service = "localagent"
    
    async def load_configuration(self) -> LocalAgentConfig:
        """Load configuration from multiple sources in priority order"""
        config_data = {}
        self.config_sources = []
        
        # 1. Load default configuration
        default_config = self._get_default_config()
        config_data.update(default_config)
        self.config_sources.append("defaults")
        
        # 2. Load from environment variables
        env_config = self._load_from_environment()
        if env_config:
            config_data.update(env_config)
            self.config_sources.append("environment")
        
        # 3. Load from configuration files
        file_config = await self._load_from_files()
        if file_config:
            config_data.update(file_config)
            self.config_sources.append("config_files")
        
        # 4. Load sensitive data from keyring
        keyring_config = await self._load_from_keyring()
        if keyring_config:
            self._merge_sensitive_config(config_data, keyring_config)
            self.config_sources.append("keyring")
        
        # 5. Set config file path
        if self.config_path:
            config_data['config_file'] = self.config_path
        
        # 6. Create and validate configuration
        try:
            self.config = LocalAgentConfig(**config_data)
            return self.config
        except Exception as e:
            console.print(f"[red]Configuration validation failed: {e}[/red]")
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            'config_dir': Path.home() / ".localagent",
            'log_level': "INFO",
            'debug_mode': False,
            'providers': {
                'ollama': {
                    'base_url': 'http://localhost:11434',
                    'enabled': True
                }
            },
            'default_provider': 'ollama',
            'orchestration': {
                'max_parallel_agents': 10,
                'max_workflow_iterations': 3,
                'enable_evidence_collection': True,
                'enable_cross_session_continuity': True
            },
            'mcp': {
                'redis_url': 'redis://localhost:6379',
                'memory_retention_days': 7,
                'enable_timeline': True,
                'enable_context_compression': True
            },
            'plugins': {
                'enabled_plugins': [],
                'auto_load_plugins': True,
                'plugin_directories': ["~/.localagent/plugins"],
                'allow_dev_plugins': False
            }
        }
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        prefix = "LOCALAGENT_"
        
        # Provider configurations
        providers = {}
        provider_names = ['ollama', 'openai', 'gemini', 'perplexity']
        
        for provider in provider_names:
            provider_config = {}
            
            # Check for provider-specific environment variables
            base_url_key = f"{prefix}{provider.upper()}_BASE_URL"
            api_key_key = f"{prefix}{provider.upper()}_API_KEY"
            model_key = f"{prefix}{provider.upper()}_DEFAULT_MODEL"
            enabled_key = f"{prefix}{provider.upper()}_ENABLED"
            
            if base_url_key in os.environ:
                provider_config['base_url'] = os.environ[base_url_key]
            if api_key_key in os.environ:
                provider_config['api_key'] = os.environ[api_key_key]
            if model_key in os.environ:
                provider_config['default_model'] = os.environ[model_key]
            if enabled_key in os.environ:
                provider_config['enabled'] = os.environ[enabled_key].lower() == 'true'
            
            if provider_config:
                providers[provider] = provider_config
        
        if providers:
            config['providers'] = providers
        
        # System configuration
        system_vars = {
            'config_dir': f"{prefix}CONFIG_DIR",
            'log_level': f"{prefix}LOG_LEVEL",
            'debug_mode': f"{prefix}DEBUG_MODE",
            'default_provider': f"{prefix}DEFAULT_PROVIDER"
        }
        
        for config_key, env_key in system_vars.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                if config_key == 'debug_mode':
                    config[config_key] = value.lower() == 'true'
                elif config_key == 'config_dir':
                    config[config_key] = Path(value).expanduser()
                else:
                    config[config_key] = value
        
        # Orchestration configuration
        orchestration_vars = {
            'max_parallel_agents': f"{prefix}MAX_PARALLEL_AGENTS",
            'max_workflow_iterations': f"{prefix}MAX_WORKFLOW_ITERATIONS",
            'enable_evidence_collection': f"{prefix}ENABLE_EVIDENCE_COLLECTION",
            'enable_cross_session_continuity': f"{prefix}ENABLE_CROSS_SESSION_CONTINUITY"
        }
        
        orchestration_config = {}
        for config_key, env_key in orchestration_vars.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                if config_key.startswith('enable_'):
                    orchestration_config[config_key] = value.lower() == 'true'
                elif config_key.startswith('max_'):
                    orchestration_config[config_key] = int(value)
        
        if orchestration_config:
            config['orchestration'] = orchestration_config
        
        # MCP configuration
        mcp_vars = {
            'redis_url': f"{prefix}MCP_REDIS_URL",
            'memory_retention_days': f"{prefix}MCP_MEMORY_RETENTION_DAYS"
        }
        
        mcp_config = {}
        for config_key, env_key in mcp_vars.items():
            if env_key in os.environ:
                value = os.environ[env_key]
                if config_key == 'memory_retention_days':
                    mcp_config[config_key] = int(value)
                else:
                    mcp_config[config_key] = value
        
        if mcp_config:
            config['mcp'] = mcp_config
        
        return config
    
    async def _load_from_files(self) -> Dict[str, Any]:
        """Load configuration from YAML/JSON files"""
        config = {}
        
        # Possible configuration file locations
        config_paths = []
        
        if self.config_path and self.config_path.exists():
            config_paths.append(self.config_path)
        
        # Default locations
        default_locations = [
            Path.home() / ".localagent" / "config.yaml",
            Path.home() / ".localagent" / "config.yml",
            Path.home() / ".localagent" / "config.json",
            Path.cwd() / "localagent.yaml",
            Path.cwd() / ".localagent.yaml"
        ]
        
        for path in default_locations:
            if path.exists():
                config_paths.append(path)
        
        # Load from the first available config file
        for config_path in config_paths:
            try:
                if config_path.suffix in ['.yaml', '.yml']:
                    with open(config_path, 'r') as f:
                        file_config = yaml.safe_load(f) or {}
                elif config_path.suffix == '.json':
                    with open(config_path, 'r') as f:
                        file_config = json.load(f) or {}
                else:
                    continue
                
                if file_config:
                    config.update(file_config)
                    self.config_path = config_path
                    break
                    
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to load config from {config_path}: {e}[/yellow]")
                continue
        
        return config
    
    async def _load_from_keyring(self) -> Dict[str, Any]:
        """Load sensitive configuration from system keyring"""
        config = {}
        
        try:
            # Load API keys from keyring
            provider_names = ['openai', 'gemini', 'perplexity']
            
            for provider in provider_names:
                try:
                    api_key = keyring.get_password(self.keyring_service, f"{provider}_api_key")
                    if api_key:
                        if 'providers' not in config:
                            config['providers'] = {}
                        if provider not in config['providers']:
                            config['providers'][provider] = {}
                        config['providers'][provider]['api_key'] = api_key
                except Exception:
                    # Keyring not available or key not found
                    pass
            
        except Exception:
            # Keyring not available
            pass
        
        return config
    
    def _merge_sensitive_config(self, main_config: Dict[str, Any], sensitive_config: Dict[str, Any]):
        """Merge sensitive configuration into main config"""
        if 'providers' in sensitive_config:
            if 'providers' not in main_config:
                main_config['providers'] = {}
            
            for provider, provider_config in sensitive_config['providers'].items():
                if provider not in main_config['providers']:
                    main_config['providers'][provider] = {}
                main_config['providers'][provider].update(provider_config)
    
    async def save_configuration(self, config: LocalAgentConfig, include_sensitive: bool = False) -> None:
        """Save configuration to file"""
        if not self.config_path:
            config_dir = config.config_dir
            self.config_path = config_dir / "config.yaml"
        
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare config for saving
        config_dict = config.dict(exclude_unset=True)
        
        # Remove sensitive data if not including
        if not include_sensitive:
            config_dict = self._remove_sensitive_data(config_dict)
        
        # Save to file using atomic write
        from ..io.atomic import AtomicWriter
        
        async with AtomicWriter(self.config_path) as writer:
            await writer.write_yaml(config_dict)
        
        # Save sensitive data to keyring
        await self._save_to_keyring(config)
    
    def _remove_sensitive_data(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from configuration before saving to file"""
        if 'providers' in config_dict:
            for provider_config in config_dict['providers'].values():
                if 'api_key' in provider_config:
                    provider_config.pop('api_key')
        
        return config_dict
    
    async def _save_to_keyring(self, config: LocalAgentConfig) -> None:
        """Save sensitive configuration to keyring"""
        try:
            for provider_name, provider_config in config.providers.items():
                if provider_config.api_key:
                    keyring.set_password(
                        self.keyring_service, 
                        f"{provider_name}_api_key", 
                        provider_config.api_key
                    )
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save to keyring: {e}[/yellow]")
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and return validation results"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'provider_status': {}
        }
        
        if not self.config:
            validation_results['valid'] = False
            validation_results['errors'].append("No configuration loaded")
            return validation_results
        
        # Validate provider configurations
        for provider_name, provider_config in self.config.providers.items():
            provider_result = await self._validate_provider_config(provider_name, provider_config)
            validation_results['provider_status'][provider_name] = provider_result
            
            if not provider_result['valid']:
                validation_results['errors'].extend(provider_result['errors'])
            
            if provider_result['warnings']:
                validation_results['warnings'].extend(provider_result['warnings'])
        
        # Check if default provider is valid
        default_provider = self.config.default_provider
        if default_provider not in self.config.providers:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Default provider '{default_provider}' not configured")
        elif not self.config.providers[default_provider].enabled:
            validation_results['warnings'].append(f"Default provider '{default_provider}' is disabled")
        
        # Overall validation status
        validation_results['valid'] = len(validation_results['errors']) == 0
        
        return validation_results
    
    async def _validate_provider_config(self, provider_name: str, config: ProviderConfig) -> Dict[str, Any]:
        """Validate a single provider configuration"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'requires_api_key': provider_name != 'ollama',
            'has_api_key': bool(config.api_key)
        }
        
        # Check required fields
        if result['requires_api_key'] and not config.api_key:
            result['valid'] = False
            result['errors'].append(f"API key required for {provider_name}")
        
        # Check URLs
        if config.base_url:
            if not (config.base_url.startswith('http://') or config.base_url.startswith('https://')):
                result['valid'] = False
                result['errors'].append(f"Invalid base_url for {provider_name}")
        
        # Provider-specific validation
        if provider_name == 'ollama' and not config.base_url:
            result['warnings'].append("No base_url specified for Ollama, using default")
        
        return result
    
    async def export_configuration(self, export_path: Path, format: str = "yaml") -> None:
        """Export current configuration to file"""
        if not self.config:
            raise ValueError("No configuration loaded")
        
        config_dict = self.config.dict()
        
        from ..io.atomic import AtomicWriter
        
        async with AtomicWriter(export_path) as writer:
            if format.lower() == "yaml":
                await writer.write_yaml(config_dict)
            elif format.lower() == "json":
                await writer.write_json(config_dict)
            else:
                raise ValueError(f"Unsupported export format: {format}")
    
    async def hot_reload_config(self) -> bool:
        """Hot reload configuration if files have changed"""
        try:
            new_config = await self.load_configuration()
            
            if new_config.dict() != (self.config.dict() if self.config else {}):
                self.config = new_config
                return True
            
            return False
            
        except Exception as e:
            console.print(f"[red]Hot reload failed: {e}[/red]")
            return False