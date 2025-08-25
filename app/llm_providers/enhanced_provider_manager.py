"""
Enhanced Provider Manager with Security and Resilience Integration
Integrates all stream outputs: Security, Resilience, Caching, Testing
"""

import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
import logging

from .base_provider import BaseProvider, CompletionRequest, CompletionResponse
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .perplexity_provider import PerplexityProvider

# Security integration
from ..security.key_manager import SecureKeyManager
from ..security.audit import AuditLogger

# Resilience integration
from ..resilience.connection_pool import ConnectionPoolManager
from ..resilience.rate_limiter import RateLimiter, RateLimitConfig
from ..resilience.circuit_breaker import CircuitBreaker

# Caching integration
from ..caching.response_cache import ResponseCache

logger = logging.getLogger(__name__)

class EnhancedProviderManager:
    """Production-ready provider manager with all enhancements"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".localagent" / "config.yaml"
        self.providers: Dict[str, BaseProvider] = {}
        
        # Security integration
        self.key_manager = SecureKeyManager()
        self.audit_logger = AuditLogger()
        
        # Resilience integration
        self.connection_manager = ConnectionPoolManager()
        self.rate_limiter = RateLimiter()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Caching integration
        self.response_cache = ResponseCache(max_size=1000, ttl=3600)
        
        # Provider configurations
        self.primary_provider = 'ollama'
        self.fallback_order = ['ollama', 'openai', 'gemini', 'perplexity']
        
    async def initialize(self) -> bool:
        """Initialize all providers with enhanced features"""
        try:
            # Load configuration
            config = await self._load_secure_config()
            
            # Initialize providers
            await self._initialize_providers(config)
            
            # Setup resilience patterns
            await self._setup_resilience()
            
            # Audit initialization
            await self.audit_logger.log_event(
                "provider_manager_init",
                {"providers_count": len(self.providers), "config_loaded": True}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize provider manager: {e}")
            await self.audit_logger.log_event(
                "provider_manager_init_failed", 
                {"error": str(e)}
            )
            return False
    
    async def _load_secure_config(self) -> Dict[str, Any]:
        """Load configuration using secure key manager"""
        if not self.config_path.exists():
            return self._get_default_config()
        
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        # Load API keys securely
        for provider_name in ['openai', 'gemini', 'perplexity']:
            if provider_name in config:
                api_key = await self._get_secure_api_key(provider_name)
                if api_key:
                    config[provider_name]['api_key'] = api_key
        
        return config
    
    async def _get_secure_api_key(self, provider: str) -> Optional[str]:
        """Get API key using secure storage"""
        try:
            key = self.key_manager.retrieve_key(provider)
            if key:
                await self.audit_logger.log_event(
                    "api_key_retrieved",
                    {"provider": provider, "success": True}
                )
            return key
        except Exception as e:
            await self.audit_logger.log_event(
                "api_key_retrieval_failed",
                {"provider": provider, "error": str(e)}
            )
            return None
    
    async def _initialize_providers(self, config: Dict[str, Any]):
        """Initialize all configured providers"""
        provider_classes = {
            'ollama': OllamaProvider,
            'openai': OpenAIProvider,
            'gemini': GeminiProvider,
            'perplexity': PerplexityProvider
        }
        
        for provider_name, provider_class in provider_classes.items():
            if provider_name in config or provider_name == 'ollama':
                provider_config = config.get(provider_name, {'base_url': 'http://localhost:11434'})
                provider = provider_class(provider_config)
                
                # Initialize provider
                if await provider.initialize():
                    self.providers[provider_name] = provider
                    logger.info(f"Initialized provider: {provider_name}")
                else:
                    logger.warning(f"Failed to initialize provider: {provider_name}")
    
    async def _setup_resilience(self):
        """Setup resilience patterns for all providers"""
        for provider_name, provider in self.providers.items():
            # Setup circuit breaker
            self.circuit_breakers[provider_name] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60.0,
                name=f"{provider_name}_circuit_breaker"
            )
            
            # Setup rate limiting
            if provider_name == 'openai':
                rate_config = RateLimitConfig(
                    requests_per_minute=3500,
                    tokens_per_minute=90000
                )
            elif provider_name == 'gemini':
                rate_config = RateLimitConfig(
                    requests_per_minute=60,
                    tokens_per_minute=32000
                )
            elif provider_name == 'perplexity':
                rate_config = RateLimitConfig(
                    requests_per_minute=20,
                    tokens_per_minute=4000
                )
            else:  # ollama
                rate_config = RateLimitConfig(
                    requests_per_minute=1000  # Local, higher limit
                )
            
            self.rate_limiter.configure_provider(provider_name, rate_config)
    
    async def complete_with_resilience(
        self,
        request: CompletionRequest,
        preferred_provider: Optional[str] = None
    ) -> CompletionResponse:
        """Complete request with full resilience patterns"""
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached_response = self.response_cache.get(cache_key)
        if cached_response:
            await self.audit_logger.log_event(
                "cache_hit",
                {"provider": "cache", "cache_key": cache_key}
            )
            return cached_response
        
        # Determine provider order
        provider_order = self._get_provider_order(preferred_provider)
        
        # Try each provider with resilience
        last_exception = None
        for provider_name in provider_order:
            if provider_name not in self.providers:
                continue
            
            try:
                # Apply rate limiting
                await self.rate_limiter.acquire(provider_name, 
                    tokens=len(str(request.messages)))
                
                # Execute with circuit breaker
                circuit_breaker = self.circuit_breakers[provider_name]
                response = await circuit_breaker.call(
                    self.providers[provider_name].complete,
                    request
                )
                
                # Cache successful response
                self.response_cache.put(cache_key, response)
                
                # Audit success
                await self.audit_logger.log_event(
                    "completion_success",
                    {
                        "provider": provider_name,
                        "tokens": response.usage.get('total_tokens', 0),
                        "cached": False
                    }
                )
                
                return response
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Provider {provider_name} failed: {e}")
                
                # Audit failure
                await self.audit_logger.log_event(
                    "completion_failed",
                    {"provider": provider_name, "error": str(e)}
                )
                
                continue
        
        # All providers failed
        if last_exception:
            raise Exception(f"All providers failed. Last error: {last_exception}")
        else:
            raise Exception("No providers available")
    
    def _generate_cache_key(self, request: CompletionRequest) -> str:
        """Generate cache key for request"""
        import hashlib
        content = f"{request.model}:{request.messages}:{request.temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_provider_order(self, preferred: Optional[str]) -> List[str]:
        """Get provider order with preferred first"""
        if preferred and preferred in self.providers:
            order = [preferred]
            order.extend([p for p in self.fallback_order if p != preferred])
            return order
        return self.fallback_order
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'ollama': {'base_url': 'http://localhost:11434'},
            'provider_settings': {
                'primary': 'ollama',
                'fallback_order': ['ollama', 'openai', 'gemini', 'perplexity']
            }
        }
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all providers"""
        health_results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                health = await provider.health_check()
                circuit_breaker = self.circuit_breakers.get(provider_name)
                
                health_results[provider_name] = {
                    **health,
                    "circuit_breaker": circuit_breaker.get_state() if circuit_breaker else None,
                    "cache_stats": self.response_cache.get_stats() if provider_name == "cache" else None
                }
            except Exception as e:
                health_results[provider_name] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return health_results
    
    async def get_provider_metrics(self) -> Dict[str, Any]:
        """Get comprehensive provider metrics"""
        return {
            "cache_stats": self.response_cache.get_stats(),
            "circuit_breakers": {
                name: cb.get_state() 
                for name, cb in self.circuit_breakers.items()
            },
            "provider_health": await self.health_check_all()
        }
    
    async def shutdown(self):
        """Graceful shutdown of all systems"""
        # Close connection pools
        await self.connection_manager.close_all()
        
        # Final audit log
        await self.audit_logger.log_event(
            "provider_manager_shutdown",
            {"graceful": True}
        )
        
        # Close audit logger
        await self.audit_logger.close()
        
        logger.info("Provider manager shutdown complete")