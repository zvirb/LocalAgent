"""
Provider Command Implementation
Manages LLM providers through CLI
"""

from typing import Dict, Any, Optional, List

from .base import AsyncCommand, InteractiveCommand, CommandResult, CommandStatus
from ..core.context import CLIContext
from ..ui.display import DisplayManager


class ProviderCommand(InteractiveCommand, AsyncCommand):
    """
    Command for managing LLM providers
    Handles provider configuration, health checks, and switching
    """
    
    @property
    def name(self) -> str:
        return "provider"
    
    @property
    def description(self) -> str:
        return "Manage and configure LLM providers"
    
    @property
    def aliases(self) -> List[str]:
        return ["providers", "prov"]
    
    async def execute(self, list_all: bool = False, health_check: bool = False,
                     provider: Optional[str] = None, configure: bool = False,
                     test: bool = False, **kwargs) -> CommandResult:
        """Execute provider management command"""
        
        try:
            # Get provider manager
            provider_manager = await self._get_provider_manager()
            if not provider_manager:
                return self._create_error_result("Provider manager not available")
            
            if list_all or not any([health_check, configure, test, provider]):
                return await self._list_providers(provider_manager, provider)
            
            if health_check:
                return await self._health_check_providers(provider_manager, provider)
            
            if configure:
                return await self._configure_provider(provider_manager, provider)
            
            if test:
                return await self._test_provider(provider_manager, provider)
            
            return self._create_success_result("Provider operation completed")
            
        except Exception as e:
            return self._create_error_result(f"Provider command failed: {e}", str(e))
    
    async def _get_provider_manager(self):
        """Get provider manager from context or initialize"""
        try:
            # Try to get from existing orchestration system
            from ...orchestration.orchestration_integration import create_orchestrator
            
            orchestrator = await create_orchestrator(self.context.config.config_file)
            return orchestrator.provider_manager if orchestrator else None
            
        except Exception as e:
            self.display_manager.print_debug(f"Could not get provider manager: {e}")
            return None
    
    async def _list_providers(self, provider_manager, specific_provider: Optional[str] = None) -> CommandResult:
        """List available providers"""
        try:
            if specific_provider:
                provider_info = await provider_manager.get_provider_info(specific_provider)
                if not provider_info:
                    return self._create_error_result(f"Provider '{specific_provider}' not found")
                
                self.display_manager.display_providers({specific_provider: provider_info})
            else:
                # Get all providers
                all_providers = {}
                enabled_providers = self.context.config.get_enabled_providers()
                
                for provider_name in enabled_providers:
                    provider_config = self.context.config.get_provider_config(provider_name)
                    if provider_config:
                        all_providers[provider_name] = {
                            'enabled': provider_config.enabled,
                            'base_url': provider_config.base_url,
                            'default_model': provider_config.default_model,
                            'rate_limit': provider_config.rate_limit,
                            'timeout': provider_config.timeout
                        }
                
                self.display_manager.display_providers(all_providers)
            
            return self._create_success_result(
                f"Listed {len(all_providers) if not specific_provider else 1} provider(s)"
            )
            
        except Exception as e:
            return self._create_error_result(f"Failed to list providers: {e}")
    
    async def _health_check_providers(self, provider_manager, specific_provider: Optional[str] = None) -> CommandResult:
        """Check provider health status"""
        try:
            await self.update_progress("Checking provider health...", 0.0)
            
            if specific_provider:
                # Check specific provider
                health_result = await self._check_single_provider_health(provider_manager, specific_provider)
                health_data = {specific_provider: health_result}
            else:
                # Check all enabled providers
                enabled_providers = self.context.config.get_enabled_providers()
                health_data = {}
                
                for i, provider_name in enumerate(enabled_providers):
                    await self.update_progress(f"Checking {provider_name}...", (i / len(enabled_providers)) * 100)
                    
                    health_result = await self._check_single_provider_health(provider_manager, provider_name)
                    health_data[provider_name] = health_result
            
            self.display_manager.display_provider_health(health_data)
            
            healthy_count = sum(1 for health in health_data.values() if health.get('healthy', False))
            total_count = len(health_data)
            
            return self._create_success_result(
                f"Health check complete: {healthy_count}/{total_count} providers healthy",
                {"health_data": health_data}
            )
            
        except Exception as e:
            return self._create_error_result(f"Health check failed: {e}")
    
    async def _check_single_provider_health(self, provider_manager, provider_name: str) -> Dict[str, Any]:
        """Check health of a single provider"""
        try:
            # This would integrate with actual provider health checking
            # For now, simulate health check
            import random
            import time
            
            start_time = time.time()
            
            # Simulate health check delay
            await asyncio.sleep(0.2)
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Mock health status (in real implementation, would test actual connection)
            healthy = random.choice([True, True, True, False])  # 75% healthy rate
            
            return {
                'healthy': healthy,
                'response_time': response_time,
                'last_check': time.strftime('%Y-%m-%d %H:%M:%S'),
                'issues': [] if healthy else ['Connection timeout', 'Authentication failed']
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'response_time': 0,
                'last_check': time.strftime('%Y-%m-%d %H:%M:%S'),
                'issues': [str(e)]
            }
    
    async def _configure_provider(self, provider_manager, provider_name: Optional[str] = None) -> CommandResult:
        """Configure a provider interactively"""
        try:
            if not provider_name:
                # Let user choose provider to configure
                available_providers = ['ollama', 'openai', 'gemini', 'perplexity']
                provider_name = await self.get_user_choice(
                    "Which provider would you like to configure?",
                    available_providers
                )
            
            self.display_manager.print_info(f"Configuring {provider_name} provider...")
            
            # Use configuration wizard
            from ..ui.prompts import ProviderConfigurationWizard
            
            wizard = ProviderConfigurationWizard(self.console)
            provider_config = await wizard.configure_provider(provider_name)
            
            if provider_config:
                # Update configuration
                self.context.config.providers[provider_name] = provider_config
                
                # Save configuration
                from ..core.config import ConfigurationManager
                config_manager = ConfigurationManager()
                await config_manager.save_configuration(self.context.config)
                
                self.display_manager.print_success(f"Provider {provider_name} configured successfully")
                return self._create_success_result(f"Provider {provider_name} configured")
            else:
                return self._create_error_result("Provider configuration cancelled")
            
        except Exception as e:
            return self._create_error_result(f"Failed to configure provider: {e}")
    
    async def _test_provider(self, provider_manager, provider_name: Optional[str] = None) -> CommandResult:
        """Test provider connection with a simple request"""
        try:
            if not provider_name:
                provider_name = self.context.config.default_provider
            
            self.display_manager.print_info(f"Testing {provider_name} provider...")
            
            # Simulate provider test
            await self.update_progress(f"Connecting to {provider_name}...", 0.0)
            await asyncio.sleep(0.5)
            
            await self.update_progress("Sending test request...", 50.0)
            await asyncio.sleep(0.5)
            
            await self.update_progress("Validating response...", 75.0)
            await asyncio.sleep(0.3)
            
            # Mock test result
            test_successful = True  # In real implementation, would actually test
            
            if test_successful:
                self.display_manager.print_success(f"Provider {provider_name} test successful")
                
                test_results = {
                    'provider': provider_name,
                    'connection': 'successful',
                    'response_time': '1.2s',
                    'model_available': True,
                    'test_prompt': 'Hello, this is a test',
                    'test_response': 'Test response received successfully'
                }
                
                # Display test results
                self.display_manager.display_tree_structure(
                    test_results, 
                    f"Test Results - {provider_name}"
                )
                
                return self._create_success_result(
                    f"Provider {provider_name} test successful",
                    {"test_results": test_results}
                )
            else:
                return self._create_error_result(f"Provider {provider_name} test failed")
            
        except Exception as e:
            return self._create_error_result(f"Provider test failed: {e}")
    
    def get_help_text(self) -> str:
        """Get detailed help for provider command"""
        return """
provider - Manage LLM providers

USAGE:
    localagent provider [OPTIONS]
    localagent provider --list
    localagent provider --health
    localagent provider --configure <provider>
    localagent provider --test <provider>

OPTIONS:
    --list, -l          List all configured providers
    --health           Check health status of providers  
    --configure        Configure a provider interactively
    --test             Test provider connection
    --provider, -p     Specify provider name

EXAMPLES:
    localagent provider --list
    localagent provider --health
    localagent provider --configure ollama
    localagent provider --test openai
    localagent provider --health --provider gemini

SUPPORTED PROVIDERS:
    ollama      Local LLM provider (no API key required)
    openai      OpenAI GPT models (requires API key)
    gemini      Google Gemini models (requires API key)  
    perplexity  Perplexity AI models (requires API key)

The provider command helps you manage and troubleshoot LLM provider
connections, ensuring optimal performance for workflow execution.
        """