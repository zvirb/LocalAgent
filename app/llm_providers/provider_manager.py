"""
Provider Manager for LocalAgent
Manages multiple LLM providers and handles routing/fallback
"""

from typing import Dict, Any, Optional, List
from .base_provider import BaseProvider, CompletionRequest, CompletionResponse
from .ollama_provider import OllamaProvider
import asyncio

class ProviderManager:
    """Manages multiple LLM providers with routing and fallback"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers: Dict[str, BaseProvider] = {}
        self.primary_provider = 'ollama'  # Default to local
        self.fallback_order = ['ollama', 'openai', 'gemini', 'perplexity']
        
    async def initialize_providers(self):
        """Initialize all configured providers"""
        # Initialize Ollama (always available)
        ollama_config = self.config.get('ollama', {'base_url': 'http://localhost:11434'})
        self.providers['ollama'] = OllamaProvider(ollama_config)
        
        # Initialize OpenAI if configured
        if 'openai' in self.config and self.config['openai'].get('api_key'):
            from .openai_provider import OpenAIProvider
            self.providers['openai'] = OpenAIProvider(self.config['openai'])
        
        # Initialize Gemini if configured
        if 'gemini' in self.config and self.config['gemini'].get('api_key'):
            from .gemini_provider import GeminiProvider
            self.providers['gemini'] = GeminiProvider(self.config['gemini'])
        
        # Initialize Perplexity if configured
        if 'perplexity' in self.config and self.config['perplexity'].get('api_key'):
            from .perplexity_provider import PerplexityProvider
            self.providers['perplexity'] = PerplexityProvider(self.config['perplexity'])
        
        # Initialize all providers
        init_tasks = []
        for provider in self.providers.values():
            init_tasks.append(provider.initialize())
        
        results = await asyncio.gather(*init_tasks, return_exceptions=True)
        
        # Check initialization results
        for provider_name, result in zip(self.providers.keys(), results):
            if isinstance(result, Exception):
                print(f"Failed to initialize {provider_name}: {result}")
            elif not result:
                print(f"Provider {provider_name} is not available")
    
    async def complete_with_fallback(
        self, 
        request: CompletionRequest,
        preferred_provider: Optional[str] = None
    ) -> CompletionResponse:
        """Complete with automatic fallback on failure"""
        
        # Determine provider order
        if preferred_provider and preferred_provider in self.providers:
            provider_order = [preferred_provider] + [
                p for p in self.fallback_order if p != preferred_provider
            ]
        else:
            provider_order = self.fallback_order
        
        # Try each provider in order
        last_error = None
        for provider_name in provider_order:
            if provider_name not in self.providers:
                continue
                
            provider = self.providers[provider_name]
            try:
                # Check if provider is healthy
                health = await provider.health_check()
                if not health['healthy']:
                    continue
                
                # Attempt completion
                return await provider.complete(request)
                
            except Exception as e:
                last_error = e
                print(f"Provider {provider_name} failed: {e}")
                continue
        
        # All providers failed
        if last_error:
            raise Exception(f"All providers failed. Last error: {last_error}")
        else:
            raise Exception("No providers available")
    
    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get a specific provider by name"""
        return self.providers.get(name)
    
    async def get_all_models(self) -> Dict[str, List[str]]:
        """Get all available models from all providers"""
        all_models = {}
        
        for provider_name, provider in self.providers.items():
            try:
                models = await provider.list_models()
                all_models[provider_name] = [m.name for m in models]
            except Exception as e:
                print(f"Error getting models from {provider_name}: {e}")
                all_models[provider_name] = []
        
        return all_models
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all providers"""
        health_results = {}
        
        for provider_name, provider in self.providers.items():
            health_results[provider_name] = await provider.health_check()
        
        return health_results