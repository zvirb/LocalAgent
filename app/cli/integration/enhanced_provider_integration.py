"""
Enhanced Provider Integration for CLI
Seamless integration between CLI commands and LLM provider management system
"""

import asyncio
from typing import Dict, Any, Optional, List, Union, Type
from pathlib import Path
import json
import yaml
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.text import Text

from ..core.context import CLIContext
from ..ui.display import DisplayManager
from ...llm_providers.provider_manager import ProviderManager
from ...llm_providers.base_provider import BaseProvider, CompletionRequest, CompletionResponse
from ...llm_providers.ollama_provider import OllamaProvider

console = Console()

class ProviderStatus:
    """Enhanced provider status tracking"""
    
    def __init__(self, name: str, provider: BaseProvider):
        self.name = name
        self.provider = provider
        self.last_health_check: Optional[datetime] = None
        self.health_status: Dict[str, Any] = {}
        self.performance_metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'total_response_time': 0.0,
            'last_request_time': None,
            'uptime_percentage': 100.0
        }
        self.recent_errors: List[Dict[str, Any]] = []
        self.model_cache: List[str] = []
        self.cache_expiry: Optional[datetime] = None
    average_response_time: float
    tokens_processed: int
    uptime_percentage: float
    last_24h_requests: int

@dataclass 
class ModelInfo:
    """Information about a provider's model"""
    name: str
    provider: str
    context_length: int
    cost_per_token: Optional[float]
    capabilities: List[str]
    status: str
    last_used: Optional[float] = None

class CLIProviderManager:
    """Enhanced provider manager with CLI-specific features"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers: Dict[str, Any] = {}
        self.health_status: Dict[str, ProviderHealth] = {}
        self.metrics: Dict[str, ProviderMetrics] = {}
        self.models: Dict[str, List[ModelInfo]] = {}
        
        # CLI-specific settings
        self.monitor_interval = config.get('monitoring', {}).get('interval', 30)
        self.health_check_timeout = config.get('health_check_timeout', 10)
        self.auto_failover = config.get('auto_failover', True)
        self.preferred_providers = config.get('preferred_providers', ['ollama'])
        
        # Monitoring
        self.monitoring_active = False
        self.health_monitor_task: Optional[asyncio.Task] = None
    
    async def initialize(self, provider_manager_instance) -> bool:
        """Initialize with existing provider manager"""
        try:
            self.provider_manager = provider_manager_instance
            
            # Discover providers
            await self._discover_providers()
            
            # Initialize health monitoring
            await self._initialize_health_monitoring()
            
            # Start background monitoring
            if self.config.get('auto_monitoring', True):
                await self.start_monitoring()
            
            logger.info("CLI Provider Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize CLI Provider Manager: {e}")
            return False
    
    async def _discover_providers(self):
        """Discover available providers"""
        if not hasattr(self.provider_manager, 'providers'):
            return
        
        for provider_name, provider_instance in self.provider_manager.providers.items():
            # Get provider information
            provider_info = {
                'name': provider_name,
                'instance': provider_instance,
                'config': getattr(provider_instance, 'config', {}),
                'models': await self._get_provider_models(provider_instance)
            }
            
            self.providers[provider_name] = provider_info
            
            # Initialize health status
            self.health_status[provider_name] = ProviderHealth(
                name=provider_name,
                status=ProviderStatus.AVAILABLE,
                response_time=None,
                error_count=0,
                success_rate=100.0,
                last_check=time.time(),
                model_count=len(provider_info['models'])
            )
            
            # Initialize metrics
            self.metrics[provider_name] = ProviderMetrics(
                name=provider_name,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_response_time=0.0,
                tokens_processed=0,
                uptime_percentage=100.0,
                last_24h_requests=0
            )
    
    async def _get_provider_models(self, provider_instance) -> List[ModelInfo]:
        """Get models available for a provider"""
        models = []
        
        try:
            if hasattr(provider_instance, 'get_available_models'):
                model_names = await provider_instance.get_available_models()
                
                for model_name in model_names:
                    model_info = ModelInfo(
                        name=model_name,
                        provider=provider_instance.__class__.__name__.lower(),
                        context_length=getattr(provider_instance, 'context_length', 4096),
                        cost_per_token=None,  # Would be provider-specific
                        capabilities=['text'],  # Would be model-specific
                        status='available'
                    )
                    models.append(model_info)
                    
        except Exception as e:
            logger.warning(f"Failed to get models for provider: {e}")
            
        return models
    
    async def _initialize_health_monitoring(self):
        """Initialize health monitoring system"""
        for provider_name in self.providers.keys():
            # Perform initial health check
            await self._health_check_provider(provider_name)
    
    async def start_monitoring(self):
        """Start background health monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.health_monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Provider monitoring started")
    
    async def stop_monitoring(self):
        """Stop background health monitoring"""
        self.monitoring_active = False
        
        if self.health_monitor_task and not self.health_monitor_task.done():
            self.health_monitor_task.cancel()
            try:
                await self.health_monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Provider monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Check all providers
                for provider_name in self.providers.keys():
                    await self._health_check_provider(provider_name)
                
                # Wait for next check
                await asyncio.sleep(self.monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _health_check_provider(self, provider_name: str) -> bool:
        """Perform health check on a specific provider"""
        if provider_name not in self.providers:
            return False
        
        health = self.health_status[provider_name]
        provider_instance = self.providers[provider_name]['instance']
        
        start_time = time.time()
        
        try:
            health.status = ProviderStatus.TESTING
            
            # Perform health check
            if hasattr(provider_instance, 'health_check'):
                health_result = await asyncio.wait_for(
                    provider_instance.health_check(),
                    timeout=self.health_check_timeout
                )
                
                if health_result.get('healthy', False):
                    health.status = ProviderStatus.AVAILABLE
                    health.response_time = time.time() - start_time
                    health.error_message = None
                    
                    # Update metrics
                    metrics = self.metrics[provider_name]
                    metrics.successful_requests += 1
                    metrics.total_requests += 1
                    
                else:
                    health.status = ProviderStatus.ERROR
                    health.error_count += 1
                    health.error_message = health_result.get('error', 'Health check failed')
                    
                    # Update metrics
                    metrics = self.metrics[provider_name]
                    metrics.failed_requests += 1
                    metrics.total_requests += 1
            else:
                # Basic connectivity test
                if hasattr(provider_instance, 'generate') or hasattr(provider_instance, 'complete'):
                    health.status = ProviderStatus.AVAILABLE
                else:
                    health.status = ProviderStatus.ERROR
                    health.error_message = "Provider does not support required methods"
            
            health.last_check = time.time()
            
            # Update success rate
            total_checks = health.error_count + getattr(health, 'success_count', 0)
            if total_checks > 0:
                health.success_rate = (getattr(health, 'success_count', 0) / total_checks) * 100
            
            return health.status == ProviderStatus.AVAILABLE
            
        except asyncio.TimeoutError:
            health.status = ProviderStatus.UNAVAILABLE
            health.error_count += 1
            health.error_message = "Health check timeout"
            health.last_check = time.time()
            return False
            
        except Exception as e:
            health.status = ProviderStatus.ERROR
            health.error_count += 1
            health.error_message = str(e)
            health.last_check = time.time()
            return False
    
    async def get_provider_status(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of providers"""
        if provider_name:
            if provider_name not in self.health_status:
                return {"error": f"Provider {provider_name} not found"}
            
            health = self.health_status[provider_name]
            return {
                "provider": provider_name,
                "status": health.status.value,
                "healthy": health.status == ProviderStatus.AVAILABLE,
                "response_time": health.response_time,
                "error_count": health.error_count,
                "success_rate": health.success_rate,
                "last_check": health.last_check,
                "error_message": health.error_message,
                "models": len(self.providers.get(provider_name, {}).get('models', []))
            }
        else:
            # Return status for all providers
            status_data = {}
            for name, health in self.health_status.items():
                status_data[name] = {
                    "status": health.status.value,
                    "healthy": health.status == ProviderStatus.AVAILABLE,
                    "response_time": health.response_time,
                    "error_count": health.error_count,
                    "success_rate": health.success_rate,
                    "models": health.model_count
                }
            
            return status_data
    
    async def get_provider_metrics(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for providers"""
        if provider_name:
            if provider_name not in self.metrics:
                return {"error": f"Provider {provider_name} not found"}
            
            return asdict(self.metrics[provider_name])
        else:
            return {name: asdict(metrics) for name, metrics in self.metrics.items()}
    
    async def get_available_models(self, provider_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get available models"""
        if provider_name:
            if provider_name not in self.providers:
                return {"error": f"Provider {provider_name} not found"}
            
            models = self.providers[provider_name]['models']
            return {provider_name: [asdict(model) for model in models]}
        else:
            all_models = {}
            for name, provider_info in self.providers.items():
                models = provider_info['models']
                all_models[name] = [asdict(model) for model in models]
            
            return all_models
    
    async def test_provider(self, provider_name: str, test_prompt: str = "Hello, world!") -> Dict[str, Any]:
        """Test a provider with a simple prompt"""
        if provider_name not in self.providers:
            return {"success": False, "error": f"Provider {provider_name} not found"}
        
        provider_instance = self.providers[provider_name]['instance']
        start_time = time.time()
        
        try:
            # Test the provider
            if hasattr(provider_instance, 'generate'):
                response = await provider_instance.generate(test_prompt)
            elif hasattr(provider_instance, 'complete'):
                response = await provider_instance.complete(test_prompt)
            else:
                return {"success": False, "error": "Provider does not support testing"}
            
            response_time = time.time() - start_time
            
            # Update metrics
            metrics = self.metrics[provider_name]
            metrics.successful_requests += 1
            metrics.total_requests += 1
            
            # Update average response time
            if metrics.average_response_time == 0:
                metrics.average_response_time = response_time
            else:
                metrics.average_response_time = (
                    metrics.average_response_time + response_time
                ) / 2
            
            return {
                "success": True,
                "response": response.get('content', '') if isinstance(response, dict) else str(response),
                "response_time": response_time,
                "provider": provider_name
            }
            
        except Exception as e:
            # Update metrics
            metrics = self.metrics[provider_name]
            metrics.failed_requests += 1
            metrics.total_requests += 1
            
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "provider": provider_name
            }
    
    async def configure_provider(self, provider_name: str, config: Dict[str, Any]) -> bool:
        """Configure a provider"""
        if provider_name not in self.providers:
            logger.error(f"Provider {provider_name} not found")
            return False
        
        try:
            provider_instance = self.providers[provider_name]['instance']
            
            # Update configuration
            if hasattr(provider_instance, 'update_config'):
                await provider_instance.update_config(config)
            else:
                # Update config directly if no method available
                for key, value in config.items():
                    if hasattr(provider_instance, key):
                        setattr(provider_instance, key, value)
            
            # Update our stored config
            self.providers[provider_name]['config'].update(config)
            
            # Re-check health after configuration
            await self._health_check_provider(provider_name)
            
            logger.info(f"Provider {provider_name} configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure provider {provider_name}: {e}")
            return False
    
    def display_provider_status(self):
        """Display provider status in rich format"""
        table = Table(title="Provider Status")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Response Time", style="blue")
        table.add_column("Success Rate", style="yellow")
        table.add_column("Models", style="white")
        table.add_column("Errors", style="red")
        
        for name, health in self.health_status.items():
            status_display = self._get_status_display(health.status)
            response_time = f"{health.response_time:.2f}s" if health.response_time else "N/A"
            success_rate = f"{health.success_rate:.1f}%"
            
            table.add_row(
                name,
                status_display,
                response_time,
                success_rate,
                str(health.model_count),
                str(health.error_count)
            )
        
        console.print(table)
    
    def _get_status_display(self, status: ProviderStatus) -> str:
        """Get colored status display"""
        status_map = {
            ProviderStatus.AVAILABLE: "[green]✅ Available[/green]",
            ProviderStatus.UNAVAILABLE: "[red]❌ Unavailable[/red]",
            ProviderStatus.CONFIGURING: "[yellow]⚙️ Configuring[/yellow]",
            ProviderStatus.ERROR: "[red]💥 Error[/red]",
            ProviderStatus.TESTING: "[blue]🔍 Testing[/blue]"
        }
        return status_map.get(status, str(status.value))
    
    async def get_best_provider(self, criteria: Dict[str, Any] = None) -> Optional[str]:
        """Get the best available provider based on criteria"""
        criteria = criteria or {}
        
        available_providers = [
            name for name, health in self.health_status.items()
            if health.status == ProviderStatus.AVAILABLE
        ]
        
        if not available_providers:
            return None
        
        # Simple scoring based on success rate and response time
        best_provider = None
        best_score = -1
        
        for provider_name in available_providers:
            health = self.health_status[provider_name]
            metrics = self.metrics[provider_name]
            
            # Calculate score (higher is better)
            score = (
                health.success_rate * 0.6 +  # 60% weight on success rate
                (1 / (health.response_time or 1)) * 100 * 0.3 +  # 30% on speed
                (metrics.uptime_percentage * 0.1)  # 10% on uptime
            )
            
            # Prefer providers in preferred list
            if provider_name in self.preferred_providers:
                score *= 1.2
            
            if score > best_score:
                best_score = score
                best_provider = provider_name
        
        return best_provider
    
    async def cleanup(self):
        """Cleanup provider manager resources"""
        await self.stop_monitoring()
        
        # Clear data structures
        self.providers.clear()
        self.health_status.clear()
        self.metrics.clear()
        self.models.clear()
        
        logger.info("Provider manager cleanup completed")

# Factory function for CLI integration
async def create_cli_provider_manager(config: Dict[str, Any], provider_manager_instance) -> CLIProviderManager:
    """Create and initialize CLI provider manager"""
    cli_manager = CLIProviderManager(config)
    
    if await cli_manager.initialize(provider_manager_instance):
        return cli_manager
    else:
        raise RuntimeError("Failed to initialize CLI provider manager")