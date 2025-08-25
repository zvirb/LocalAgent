"""
MockProvider Framework for LocalAgent Testing
Provides configurable mock LLM providers for comprehensive testing
"""

import asyncio
import json
from typing import Dict, Any, AsyncIterator, List, Optional, Callable
from dataclasses import dataclass, field
from unittest.mock import AsyncMock
from app.llm_providers.base_provider import BaseProvider, ModelInfo, CompletionRequest, CompletionResponse

@dataclass
class MockScenario:
    """Defines a test scenario for mock provider behavior"""
    name: str
    response_content: str = "Mock response"
    response_delay: float = 0.1
    should_fail: bool = False
    failure_type: str = "network"  # network, auth, rate_limit, model_error
    usage_tokens: int = 100
    cost: float = 0.01
    streaming_chunks: List[str] = field(default_factory=list)
    custom_response: Optional[Dict[str, Any]] = None

class MockProvider(BaseProvider):
    """Highly configurable mock provider for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = 'mock'
        self.is_local = config.get('is_local', True)
        self.requires_api_key = config.get('requires_api_key', False)
        
        # Test configuration
        self.scenarios: Dict[str, MockScenario] = {}
        self.current_scenario = "default"
        self.call_count = 0
        self.call_history: List[CompletionRequest] = []
        self.health_status = True
        self.available_models = [
            ModelInfo("mock-model-small", "mock", 2048, ["chat", "completion"]),
            ModelInfo("mock-model-large", "mock", 8192, ["chat", "completion", "function_calling"]),
            ModelInfo("mock-vision-model", "mock", 4096, ["chat", "completion", "vision"])
        ]
        
        # Add default scenario
        self.add_scenario("default", MockScenario(
            name="default",
            response_content="This is a mock response for testing purposes.",
            streaming_chunks=["This is ", "a mock ", "response ", "for testing ", "purposes."]
        ))
    
    def add_scenario(self, name: str, scenario: MockScenario):
        """Add a test scenario"""
        self.scenarios[name] = scenario
    
    def set_scenario(self, name: str):
        """Switch to a specific test scenario"""
        if name in self.scenarios:
            self.current_scenario = name
        else:
            raise ValueError(f"Scenario '{name}' not found")
    
    def get_current_scenario(self) -> MockScenario:
        """Get the current active scenario"""
        return self.scenarios[self.current_scenario]
    
    def reset_call_history(self):
        """Reset call history for fresh test runs"""
        self.call_count = 0
        self.call_history = []
    
    def set_health_status(self, healthy: bool):
        """Set provider health status for testing"""
        self.health_status = healthy
    
    async def initialize(self) -> bool:
        """Mock initialization - configurable success/failure"""
        scenario = self.get_current_scenario()
        if scenario.response_delay > 0:
            await asyncio.sleep(scenario.response_delay)
        
        if scenario.should_fail and scenario.failure_type == "init":
            return False
        return True
    
    async def list_models(self) -> List[ModelInfo]:
        """Return mock model list"""
        scenario = self.get_current_scenario()
        if scenario.should_fail and scenario.failure_type == "model_list":
            raise Exception("Failed to list models")
        return self.available_models
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate mock completion"""
        self.call_count += 1
        self.call_history.append(request)
        
        scenario = self.get_current_scenario()
        
        # Simulate delay
        if scenario.response_delay > 0:
            await asyncio.sleep(scenario.response_delay)
        
        # Handle failure scenarios
        if scenario.should_fail:
            if scenario.failure_type == "network":
                raise aiohttp.ClientError("Network connection failed")
            elif scenario.failure_type == "auth":
                raise Exception("Authentication failed")
            elif scenario.failure_type == "rate_limit":
                raise Exception("Rate limit exceeded")
            elif scenario.failure_type == "model_error":
                raise Exception("Model inference error")
        
        # Return custom response if provided
        if scenario.custom_response:
            return CompletionResponse(**scenario.custom_response)
        
        # Generate standard mock response
        response_content = scenario.response_content
        if "{request}" in response_content:
            response_content = response_content.format(
                request=request.messages[-1].get('content', '') if request.messages else ''
            )
        
        return CompletionResponse(
            content=response_content,
            model=request.model,
            provider=self.name,
            usage={'total_tokens': scenario.usage_tokens},
            cost=scenario.cost
        )
    
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Generate mock streaming completion"""
        self.call_count += 1
        self.call_history.append(request)
        
        scenario = self.get_current_scenario()
        
        if scenario.should_fail:
            raise Exception(f"Streaming failed: {scenario.failure_type}")
        
        # Stream mock chunks
        chunks = scenario.streaming_chunks if scenario.streaming_chunks else [scenario.response_content]
        
        for chunk in chunks:
            if scenario.response_delay > 0:
                await asyncio.sleep(scenario.response_delay / len(chunks))
            yield chunk
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check"""
        scenario = self.get_current_scenario()
        
        if not self.health_status or (scenario.should_fail and scenario.failure_type == "health"):
            return {
                'healthy': False,
                'provider': self.name,
                'error': 'Mock provider unhealthy'
            }
        
        return {
            'healthy': True,
            'provider': self.name,
            'models_available': len(self.available_models),
            'call_count': self.call_count,
            'current_scenario': self.current_scenario
        }

class MockProviderFactory:
    """Factory for creating configured mock providers"""
    
    @staticmethod
    def create_fast_provider() -> MockProvider:
        """Create a fast-responding mock provider"""
        config = {'is_local': True, 'requires_api_key': False}
        provider = MockProvider(config)
        provider.add_scenario("fast", MockScenario(
            name="fast",
            response_content="Quick mock response",
            response_delay=0.01,
            usage_tokens=50,
            streaming_chunks=["Quick ", "mock ", "response"]
        ))
        provider.set_scenario("fast")
        return provider
    
    @staticmethod
    def create_slow_provider() -> MockProvider:
        """Create a slow-responding mock provider"""
        config = {'is_local': False, 'requires_api_key': True}
        provider = MockProvider(config)
        provider.add_scenario("slow", MockScenario(
            name="slow",
            response_content="Slow mock response after delay",
            response_delay=1.0,
            usage_tokens=200,
            streaming_chunks=["Slow ", "mock ", "response ", "after ", "delay"]
        ))
        provider.set_scenario("slow")
        return provider
    
    @staticmethod
    def create_failing_provider(failure_type: str = "network") -> MockProvider:
        """Create a provider that fails with specified failure type"""
        config = {'is_local': False, 'requires_api_key': True}
        provider = MockProvider(config)
        provider.add_scenario("failing", MockScenario(
            name="failing",
            should_fail=True,
            failure_type=failure_type
        ))
        provider.set_scenario("failing")
        return provider
    
    @staticmethod
    def create_cost_aware_provider() -> MockProvider:
        """Create a provider with detailed cost tracking"""
        config = {'is_local': False, 'requires_api_key': True}
        provider = MockProvider(config)
        provider.add_scenario("expensive", MockScenario(
            name="expensive",
            response_content="High-cost response with detailed usage",
            usage_tokens=1000,
            cost=0.05
        ))
        provider.add_scenario("cheap", MockScenario(
            name="cheap", 
            response_content="Low-cost response",
            usage_tokens=100,
            cost=0.001
        ))
        return provider

class MockProviderManager:
    """Mock version of ProviderManager for testing"""
    
    def __init__(self, providers: Dict[str, MockProvider]):
        self.providers = providers
        self.primary_provider = list(providers.keys())[0] if providers else None
        self.fallback_order = list(providers.keys())
        self.call_history: List[Dict[str, Any]] = []
    
    async def initialize_providers(self):
        """Initialize all mock providers"""
        for provider in self.providers.values():
            await provider.initialize()
    
    async def complete_with_fallback(
        self, 
        request: CompletionRequest,
        preferred_provider: Optional[str] = None
    ) -> CompletionResponse:
        """Mock completion with fallback logic"""
        self.call_history.append({
            'request': request,
            'preferred_provider': preferred_provider,
            'timestamp': asyncio.get_event_loop().time()
        })
        
        # Determine provider order
        if preferred_provider and preferred_provider in self.providers:
            provider_order = [preferred_provider] + [
                p for p in self.fallback_order if p != preferred_provider
            ]
        else:
            provider_order = self.fallback_order
        
        # Try each provider
        last_error = None
        for provider_name in provider_order:
            if provider_name not in self.providers:
                continue
                
            provider = self.providers[provider_name]
            try:
                health = await provider.health_check()
                if not health['healthy']:
                    continue
                return await provider.complete(request)
            except Exception as e:
                last_error = e
                continue
        
        if last_error:
            raise Exception(f"All providers failed. Last error: {last_error}")
        else:
            raise Exception("No providers available")
    
    def get_provider(self, name: str) -> Optional[MockProvider]:
        """Get mock provider by name"""
        return self.providers.get(name)
    
    def reset_all_history(self):
        """Reset call history for all providers"""
        self.call_history = []
        for provider in self.providers.values():
            provider.reset_call_history()

# Pre-configured test scenarios for common testing patterns
TEST_SCENARIOS = {
    'multi_provider_success': {
        'ollama': MockProviderFactory.create_fast_provider(),
        'openai': MockProviderFactory.create_slow_provider(),
        'gemini': MockProviderFactory.create_cost_aware_provider()
    },
    'fallback_chain': {
        'primary': MockProviderFactory.create_failing_provider('network'),
        'secondary': MockProviderFactory.create_failing_provider('auth'),
        'tertiary': MockProviderFactory.create_fast_provider()
    },
    'performance_comparison': {
        'fast_local': MockProviderFactory.create_fast_provider(),
        'slow_remote': MockProviderFactory.create_slow_provider()
    }
}