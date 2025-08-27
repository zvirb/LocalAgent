"""
CLI Validation Tools
Validation utilities for configuration, providers, and commands
"""

import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table

from ..core.config import LocalAgentConfig, ProviderConfig


class ValidationResult:
    """Result of a validation operation"""
    
    def __init__(self, valid: bool, message: str = "", details: Optional[Dict[str, Any]] = None):
        self.valid = valid
        self.message = message
        self.details = details or {}
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        self.valid = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'valid': self.valid,
            'message': self.message,
            'details': self.details,
            'warnings': self.warnings,
            'errors': self.errors
        }


class ConfigValidator:
    """
    Comprehensive configuration validator
    Validates LocalAgent configuration files and settings
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    async def validate_config(self, config: LocalAgentConfig) -> ValidationResult:
        """Validate complete configuration"""
        result = ValidationResult(True, "Configuration validation complete")
        
        # Validate basic settings
        self._validate_basic_settings(config, result)
        
        # Validate providers
        await self._validate_providers(config, result)
        
        # Validate orchestration settings
        self._validate_orchestration_settings(config, result)
        
        # Validate MCP settings  
        self._validate_mcp_settings(config, result)
        
        # Validate plugin settings
        self._validate_plugin_settings(config, result)
        
        # Overall validation
        if result.errors:
            result.message = f"Configuration has {len(result.errors)} errors"
        elif result.warnings:
            result.message = f"Configuration valid with {len(result.warnings)} warnings"
        
        return result
    
    def _validate_basic_settings(self, config: LocalAgentConfig, result: ValidationResult):
        """Validate basic configuration settings"""
        # Config directory
        if not config.config_dir:
            result.add_error("Configuration directory not specified")
        elif not config.config_dir.exists():
            result.add_warning(f"Configuration directory does not exist: {config.config_dir}")
        
        # Log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if config.log_level.upper() not in valid_log_levels:
            result.add_error(f"Invalid log level: {config.log_level}")
        
        # Default provider
        if not config.default_provider:
            result.add_error("Default provider not specified")
        elif config.default_provider not in config.providers:
            result.add_error(f"Default provider '{config.default_provider}' not found in providers")
    
    async def _validate_providers(self, config: LocalAgentConfig, result: ValidationResult):
        """Validate provider configurations"""
        if not config.providers:
            result.add_error("No providers configured")
            return
        
        enabled_count = 0
        
        for provider_name, provider_config in config.providers.items():
            provider_result = await self._validate_single_provider(provider_name, provider_config)
            
            if provider_result.errors:
                for error in provider_result.errors:
                    result.add_error(f"Provider '{provider_name}': {error}")
            
            if provider_result.warnings:
                for warning in provider_result.warnings:
                    result.add_warning(f"Provider '{provider_name}': {warning}")
            
            if provider_config.enabled:
                enabled_count += 1
        
        if enabled_count == 0:
            result.add_error("No enabled providers found")
    
    async def _validate_single_provider(self, provider_name: str, config: ProviderConfig) -> ValidationResult:
        """Validate a single provider configuration"""
        result = ValidationResult(True)
        
        # Base URL validation
        if config.base_url:
            if not self._is_valid_url(config.base_url):
                result.add_error("Invalid base URL format")
        
        # API key validation (required for non-Ollama providers)
        if provider_name != 'ollama':
            if not config.api_key:
                result.add_error("API key required")
            elif len(config.api_key) < 10:
                result.add_warning("API key appears to be too short")
        
        # Timeout validation
        if config.timeout < 1 or config.timeout > 600:
            result.add_error("Timeout must be between 1 and 600 seconds")
        
        # Rate limit validation
        if config.rate_limit is not None:
            if config.rate_limit < 1 or config.rate_limit > 10000:
                result.add_error("Rate limit must be between 1 and 10000 requests per minute")
        
        return result
    
    def _validate_orchestration_settings(self, config: LocalAgentConfig, result: ValidationResult):
        """Validate orchestration configuration"""
        orchestration = config.orchestration
        
        # Max parallel agents
        if orchestration.max_parallel_agents < 1 or orchestration.max_parallel_agents > 100:
            result.add_error("Max parallel agents must be between 1 and 100")
        
        # Max workflow iterations
        if orchestration.max_workflow_iterations < 1 or orchestration.max_workflow_iterations > 20:
            result.add_error("Max workflow iterations must be between 1 and 20")
        
        # Default timeout
        if orchestration.default_timeout < 30 or orchestration.default_timeout > 7200:
            result.add_error("Default timeout must be between 30 and 7200 seconds")
    
    def _validate_mcp_settings(self, config: LocalAgentConfig, result: ValidationResult):
        """Validate MCP configuration"""
        mcp = config.mcp
        
        # Redis URL
        if not self._is_valid_redis_url(mcp.redis_url):
            result.add_error("Invalid Redis URL format")
        
        # Memory retention
        if mcp.memory_retention_days < 1 or mcp.memory_retention_days > 365:
            result.add_error("Memory retention days must be between 1 and 365")
    
    def _validate_plugin_settings(self, config: LocalAgentConfig, result: ValidationResult):
        """Validate plugin configuration"""
        plugins = config.plugins
        
        # Plugin directories
        for plugin_dir in plugins.plugin_directories:
            path = Path(plugin_dir).expanduser()
            if not path.exists():
                result.add_warning(f"Plugin directory does not exist: {plugin_dir}")
            elif not path.is_dir():
                result.add_error(f"Plugin directory path is not a directory: {plugin_dir}")
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except Exception:
            return False
    
    def _is_valid_redis_url(self, url: str) -> bool:
        """Validate Redis URL format"""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ['redis', 'rediss'] and parsed.netloc
        except Exception:
            return False


class ProviderValidator:
    """
    Provider-specific validation and health checking
    """
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    async def validate_provider_connection(self, provider_name: str, config: ProviderConfig) -> ValidationResult:
        """Test provider connection and functionality"""
        result = ValidationResult(True, f"Provider {provider_name} validation")
        
        try:
            # Basic configuration validation
            config_result = await self._validate_provider_config(provider_name, config)
            if not config_result.valid:
                result.errors.extend(config_result.errors)
                result.warnings.extend(config_result.warnings)
                return result
            
            # Connection test
            connection_result = await self._test_provider_connection(provider_name, config)
            if not connection_result.valid:
                result.errors.extend(connection_result.errors)
                result.warnings.extend(connection_result.warnings)
                return result
            
            # Functionality test
            functionality_result = await self._test_provider_functionality(provider_name, config)
            if not functionality_result.valid:
                result.errors.extend(functionality_result.errors)
                result.warnings.extend(functionality_result.warnings)
                return result
            
            result.details = {
                'connection_time': functionality_result.details.get('connection_time', 0),
                'response_time': functionality_result.details.get('response_time', 0),
                'models_available': functionality_result.details.get('models_available', [])
            }
            
        except Exception as e:
            result.add_error(f"Provider validation failed: {e}")
        
        return result
    
    async def _validate_provider_config(self, provider_name: str, config: ProviderConfig) -> ValidationResult:
        """Validate provider configuration"""
        result = ValidationResult(True)
        
        if provider_name == 'ollama':
            # Ollama-specific validation
            if not config.base_url:
                result.add_error("Base URL required for Ollama")
            elif not config.base_url.startswith(('http://', 'https://')):
                result.add_error("Ollama base URL must start with http:// or https://")
                
        elif provider_name in ['openai', 'gemini', 'perplexity']:
            # API-based provider validation
            if not config.api_key:
                result.add_error("API key required")
            elif len(config.api_key) < 20:
                result.add_warning("API key appears to be too short")
        
        return result
    
    async def _test_provider_connection(self, provider_name: str, config: ProviderConfig) -> ValidationResult:
        """Test basic connection to provider"""
        result = ValidationResult(True)
        
        try:
            # Simulate connection test
            # In real implementation, this would make actual HTTP requests
            import random
            await asyncio.sleep(0.1 + random.random() * 0.2)  # Simulate network delay
            
            # Mock connection success/failure
            connection_success = random.choice([True, True, True, False])  # 75% success rate
            
            if connection_success:
                result.details['connection_time'] = random.uniform(0.1, 0.5)
            else:
                result.add_error("Connection failed - timeout or network error")
                
        except Exception as e:
            result.add_error(f"Connection test failed: {e}")
        
        return result
    
    async def _test_provider_functionality(self, provider_name: str, config: ProviderConfig) -> ValidationResult:
        """Test provider functionality with a simple request"""
        result = ValidationResult(True)
        
        try:
            # Simulate functionality test
            import random
            await asyncio.sleep(0.2 + random.random() * 0.3)  # Simulate API call
            
            # Mock functionality test
            functionality_success = random.choice([True, True, False])  # 67% success rate
            
            if functionality_success:
                result.details.update({
                    'response_time': random.uniform(0.2, 1.0),
                    'models_available': self._get_mock_models(provider_name),
                    'test_response': 'Test message received successfully'
                })
            else:
                result.add_error("Functionality test failed - invalid response or API error")
                
        except Exception as e:
            result.add_error(f"Functionality test failed: {e}")
        
        return result
    
    def _get_mock_models(self, provider_name: str) -> List[str]:
        """Get mock model list for provider"""
        mock_models = {
            'ollama': ['llama3.2', 'codellama', 'mistral', 'phi3'],
            'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
            'gemini': ['gemini-pro', 'gemini-pro-vision'],
            'perplexity': ['llama-3-sonar-large-32k-online', 'llama-3-sonar-small-32k-online']
        }
        return mock_models.get(provider_name, ['default'])
    
    async def run_comprehensive_provider_validation(self, config: LocalAgentConfig) -> Dict[str, ValidationResult]:
        """Run comprehensive validation on all providers"""
        results = {}
        
        for provider_name, provider_config in config.providers.items():
            if provider_config.enabled:
                result = await self.validate_provider_connection(provider_name, provider_config)
                results[provider_name] = result
        
        return results
    
    def display_validation_results(self, results: Dict[str, ValidationResult]):
        """Display provider validation results"""
        table = Table(title="Provider Validation Results", show_header=True, header_style="bold magenta")
        table.add_column("Provider", style="cyan", width=15)
        table.add_column("Status", style="white", width=10)
        table.add_column("Connection", style="blue", width=12)
        table.add_column("Response Time", style="green", width=12)
        table.add_column("Issues", style="red")
        
        for provider_name, result in results.items():
            status = "✅ Valid" if result.valid else "❌ Invalid"
            connection_time = result.details.get('connection_time')
            connection = f"{connection_time:.2f}s" if connection_time else "Failed"
            response_time = result.details.get('response_time')
            response = f"{response_time:.2f}s" if response_time else "N/A"
            issues = ", ".join(result.errors[:2])  # Show first 2 errors
            
            table.add_row(provider_name, status, connection, response, issues)
        
        self.console.print(table)


class CommandValidator:
    """
    Validator for CLI commands and their parameters
    """
    
    def __init__(self):
        self.validation_rules = self._setup_validation_rules()
    
    def _setup_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Setup validation rules for commands"""
        return {
            'workflow': {
                'required_params': ['prompt'],
                'optional_params': ['provider', 'phases', 'parallel', 'max_agents', 'output_format', 'save_report'],
                'param_types': {
                    'prompt': str,
                    'provider': str,
                    'phases': str,
                    'parallel': bool,
                    'max_agents': int,
                    'output_format': str,
                    'save_report': str
                },
                'param_constraints': {
                    'max_agents': lambda x: 1 <= x <= 50,
                    'output_format': lambda x: x in ['rich', 'json', 'yaml'],
                    'phases': lambda x: all(p.strip().isdigit() for p in x.split(','))
                }
            },
            'provider': {
                'optional_params': ['list_all', 'health_check', 'provider', 'configure', 'test'],
                'param_types': {
                    'list_all': bool,
                    'health_check': bool,
                    'provider': str,
                    'configure': bool,
                    'test': bool
                }
            },
            'config': {
                'optional_params': ['show', 'validate', 'export', 'edit', 'reset'],
                'param_types': {
                    'show': bool,
                    'validate': bool,
                    'export': str,
                    'edit': bool,
                    'reset': bool
                }
            }
        }
    
    def validate_command_params(self, command: str, params: Dict[str, Any]) -> ValidationResult:
        """Validate command parameters"""
        result = ValidationResult(True, f"Command '{command}' parameters valid")
        
        if command not in self.validation_rules:
            result.add_error(f"Unknown command: {command}")
            return result
        
        rules = self.validation_rules[command]
        
        # Check required parameters
        if 'required_params' in rules:
            for param in rules['required_params']:
                if param not in params or params[param] is None:
                    result.add_error(f"Required parameter '{param}' missing")
        
        # Check parameter types and constraints
        for param_name, param_value in params.items():
            if param_value is None:
                continue
                
            # Type validation
            if param_name in rules.get('param_types', {}):
                expected_type = rules['param_types'][param_name]
                if not isinstance(param_value, expected_type):
                    result.add_error(f"Parameter '{param_name}' should be of type {expected_type.__name__}")
            
            # Constraint validation
            if param_name in rules.get('param_constraints', {}):
                constraint = rules['param_constraints'][param_name]
                try:
                    if not constraint(param_value):
                        result.add_error(f"Parameter '{param_name}' violates constraint")
                except Exception as e:
                    result.add_error(f"Parameter '{param_name}' constraint validation failed: {e}")
        
        return result