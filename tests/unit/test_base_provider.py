"""
Unit tests for BaseProvider interface and data models
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from app.llm_providers.base_provider import (
    BaseProvider, 
    ModelInfo, 
    CompletionRequest, 
    CompletionResponse
)


class TestModelInfo:
    """Test ModelInfo data class"""
    
    def test_model_info_creation(self):
        """Test basic ModelInfo creation"""
        model = ModelInfo(
            name="test-model",
            provider="test-provider",
            context_length=4096,
            capabilities=["chat", "completion"],
            cost_per_token=0.001
        )
        
        assert model.name == "test-model"
        assert model.provider == "test-provider"
        assert model.context_length == 4096
        assert model.capabilities == ["chat", "completion"]
        assert model.cost_per_token == 0.001
    
    def test_model_info_optional_fields(self):
        """Test ModelInfo with optional fields"""
        model = ModelInfo(
            name="basic-model",
            provider="basic-provider", 
            context_length=2048,
            capabilities=["chat"]
        )
        
        assert model.cost_per_token is None


class TestCompletionRequest:
    """Test CompletionRequest data class"""
    
    def test_completion_request_basic(self):
        """Test basic CompletionRequest creation"""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        assert request.messages == [{"role": "user", "content": "Hello"}]
        assert request.model == "test-model"
        assert request.temperature == 0.7  # default
        assert request.max_tokens is None
        assert request.stream is False
        assert request.functions is None
        assert request.system_prompt is None
    
    def test_completion_request_full(self):
        """Test CompletionRequest with all parameters"""
        functions = [{"name": "test_func", "description": "Test function"}]
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model",
            temperature=0.9,
            max_tokens=1000,
            stream=True,
            functions=functions,
            system_prompt="You are a helpful assistant"
        )
        
        assert request.temperature == 0.9
        assert request.max_tokens == 1000
        assert request.stream is True
        assert request.functions == functions
        assert request.system_prompt == "You are a helpful assistant"


class TestCompletionResponse:
    """Test CompletionResponse data class"""
    
    def test_completion_response_basic(self):
        """Test basic CompletionResponse creation"""
        response = CompletionResponse(
            content="Hello, world!",
            model="test-model",
            provider="test-provider",
            usage={"total_tokens": 100}
        )
        
        assert response.content == "Hello, world!"
        assert response.model == "test-model"
        assert response.provider == "test-provider"
        assert response.usage == {"total_tokens": 100}
        assert response.cost is None
        assert response.citations is None
    
    def test_completion_response_full(self):
        """Test CompletionResponse with all fields"""
        citations = [{"url": "https://example.com", "title": "Test"}]
        response = CompletionResponse(
            content="Response with citations",
            model="test-model",
            provider="test-provider",
            usage={"total_tokens": 150, "prompt_tokens": 50, "completion_tokens": 100},
            cost=0.05,
            citations=citations
        )
        
        assert response.cost == 0.05
        assert response.citations == citations


class ConcreteProvider(BaseProvider):
    """Concrete implementation of BaseProvider for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.initialized = False
        self.models = [
            ModelInfo("test-model-1", "test", 4096, ["chat"]),
            ModelInfo("test-model-2", "test", 8192, ["chat", "completion"])
        ]
    
    async def initialize(self) -> bool:
        self.initialized = True
        return True
    
    async def list_models(self) -> List[ModelInfo]:
        return self.models
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            content="Test response",
            model=request.model,
            provider=self.name,
            usage={"total_tokens": 100}
        )
    
    async def stream_complete(self, request: CompletionRequest):
        chunks = ["Test ", "streaming ", "response"]
        for chunk in chunks:
            yield chunk
    
    async def health_check(self) -> Dict[str, Any]:
        return {
            "healthy": self.initialized,
            "provider": self.name,
            "models_available": len(self.models)
        }


class TestBaseProvider:
    """Test BaseProvider abstract class implementation"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            "api_key": "test-key",
            "base_url": "https://api.test.com"
        }
        self.provider = ConcreteProvider(self.config)
    
    def test_provider_initialization(self):
        """Test provider basic initialization"""
        assert self.provider.config == self.config
        assert self.provider.name == "Concrete"  # Class name minus 'Provider'
        assert self.provider.is_local is False
        assert self.provider.requires_api_key is True
    
    def test_provider_name_extraction(self):
        """Test automatic name extraction from class name"""
        assert self.provider.name == "Concrete"
    
    @pytest.mark.asyncio
    async def test_provider_initialize(self):
        """Test provider initialization"""
        result = await self.provider.initialize()
        assert result is True
        assert self.provider.initialized is True
    
    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test model listing"""
        models = await self.provider.list_models()
        assert len(models) == 2
        assert models[0].name == "test-model-1"
        assert models[1].name == "test-model-2"
    
    @pytest.mark.asyncio
    async def test_complete(self):
        """Test completion generation"""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model-1"
        )
        
        response = await self.provider.complete(request)
        assert response.content == "Test response"
        assert response.model == "test-model-1"
        assert response.provider == "Concrete"
    
    @pytest.mark.asyncio
    async def test_stream_complete(self):
        """Test streaming completion"""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model-1",
            stream=True
        )
        
        chunks = []
        async for chunk in self.provider.stream_complete(request):
            chunks.append(chunk)
        
        assert chunks == ["Test ", "streaming ", "response"]
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check"""
        # Before initialization
        health = await self.provider.health_check()
        assert health["healthy"] is False
        
        # After initialization
        await self.provider.initialize()
        health = await self.provider.health_check()
        assert health["healthy"] is True
        assert health["provider"] == "Concrete"
        assert health["models_available"] == 2
    
    @pytest.mark.asyncio
    async def test_count_tokens_default(self):
        """Test default token counting implementation"""
        text = "This is a test string with multiple words"
        tokens = await self.provider.count_tokens(text, "test-model")
        
        # Default implementation: len(text.split()) * 1.3
        expected = len(text.split()) * 1.3
        assert tokens == expected
    
    @pytest.mark.asyncio
    async def test_estimate_cost_default(self):
        """Test default cost estimation"""
        cost = await self.provider.estimate_cost(1000, "test-model")
        assert cost == 0.0  # Default implementation returns 0


class TestProviderConfiguration:
    """Test provider configuration handling"""
    
    def test_local_provider_config(self):
        """Test local provider configuration"""
        config = {
            "base_url": "http://localhost:11434",
            "is_local": True,
            "requires_api_key": False
        }
        
        class LocalProvider(ConcreteProvider):
            def __init__(self, config):
                super().__init__(config)
                self.is_local = config.get('is_local', False)
                self.requires_api_key = config.get('requires_api_key', True)
        
        provider = LocalProvider(config)
        assert provider.is_local is True
        assert provider.requires_api_key is False
    
    def test_remote_provider_config(self):
        """Test remote provider configuration"""
        config = {
            "api_key": "sk-test123",
            "base_url": "https://api.openai.com/v1",
            "is_local": False,
            "requires_api_key": True
        }
        
        class RemoteProvider(ConcreteProvider):
            def __init__(self, config):
                super().__init__(config)
                self.is_local = config.get('is_local', False)
                self.requires_api_key = config.get('requires_api_key', True)
        
        provider = RemoteProvider(config)
        assert provider.is_local is False
        assert provider.requires_api_key is True
    
    def test_missing_config_handling(self):
        """Test behavior with missing configuration"""
        empty_config = {}
        provider = ConcreteProvider(empty_config)
        
        # Should still work with defaults
        assert provider.config == {}
        assert provider.name == "Concrete"
        assert provider.is_local is False
        assert provider.requires_api_key is True


class TestProviderErrorHandling:
    """Test error handling in provider implementations"""
    
    def setup_method(self):
        """Setup for error testing"""
        self.config = {"api_key": "test-key"}
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test handling of initialization failures"""
        class FailingProvider(ConcreteProvider):
            async def initialize(self) -> bool:
                raise Exception("Initialization failed")
        
        provider = FailingProvider(self.config)
        
        with pytest.raises(Exception, match="Initialization failed"):
            await provider.initialize()
    
    @pytest.mark.asyncio
    async def test_completion_failure(self):
        """Test handling of completion failures"""
        class FailingProvider(ConcreteProvider):
            async def complete(self, request: CompletionRequest) -> CompletionResponse:
                raise Exception("Completion failed")
        
        provider = FailingProvider(self.config)
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        with pytest.raises(Exception, match="Completion failed"):
            await provider.complete(request)
    
    @pytest.mark.asyncio
    async def test_streaming_failure(self):
        """Test handling of streaming failures"""
        class FailingProvider(ConcreteProvider):
            async def stream_complete(self, request: CompletionRequest):
                yield "Partial"
                raise Exception("Streaming failed")
        
        provider = FailingProvider(self.config)
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model",
            stream=True
        )
        
        chunks = []
        with pytest.raises(Exception, match="Streaming failed"):
            async for chunk in provider.stream_complete(request):
                chunks.append(chunk)
        
        # Should have received partial data before failure
        assert chunks == ["Partial"]


class TestProviderIntegration:
    """Integration tests for provider functionality"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete provider workflow"""
        provider = ConcreteProvider({"test": "config"})
        
        # Initialize
        init_result = await provider.initialize()
        assert init_result is True
        
        # Check health
        health = await provider.health_check()
        assert health["healthy"] is True
        
        # List models
        models = await self.provider.list_models()
        assert len(models) > 0
        
        # Complete request
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Test message"}],
            model=models[0].name
        )
        
        response = await provider.complete(request)
        assert response.content is not None
        assert response.model == models[0].name
        assert response.provider == provider.name
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        provider = ConcreteProvider({})
        await provider.initialize()
        
        requests = [
            CompletionRequest(
                messages=[{"role": "user", "content": f"Message {i}"}],
                model="test-model-1"
            )
            for i in range(5)
        ]
        
        # Run concurrent completions
        responses = await asyncio.gather(*[
            provider.complete(req) for req in requests
        ])
        
        assert len(responses) == 5
        for i, response in enumerate(responses):
            assert response.content == "Test response"
            assert response.model == "test-model-1"