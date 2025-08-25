"""
Unit tests for LocalAgent provider interfaces
Tests the core functionality of all LLM providers
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import aiohttp
import json
import time
from typing import Dict, Any

# Import the providers and base classes
from app.llm_providers.base_provider import BaseProvider, ModelInfo, CompletionRequest, CompletionResponse
from app.llm_providers.ollama_provider import OllamaProvider
from app.llm_providers.provider_manager import ProviderManager

# Test fixtures
@pytest.fixture
def sample_completion_request():
    return CompletionRequest(
        messages=[{"role": "user", "content": "Hello world"}],
        model="test-model",
        temperature=0.7,
        stream=False
    )

@pytest.fixture
def sample_model_info():
    return ModelInfo(
        name="test-model",
        provider="test-provider", 
        context_length=4096,
        capabilities=["chat", "completion"]
    )

@pytest.fixture
def sample_completion_response():
    return CompletionResponse(
        content="Hello! How can I help you?",
        model="test-model",
        provider="test-provider",
        usage={"prompt_tokens": 2, "completion_tokens": 6, "total_tokens": 8}
    )

class TestBaseProvider:
    """Test the base provider abstract class"""
    
    def test_base_provider_is_abstract(self):
        """Test that BaseProvider cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseProvider({})
    
    def test_provider_name_extraction(self):
        """Test that provider names are extracted correctly from class names"""
        class TestProvider(BaseProvider):
            async def initialize(self): return True
            async def list_models(self): return []
            async def complete(self, request): return None
            async def stream_complete(self, request): pass
            async def health_check(self): return {}
        
        provider = TestProvider({})
        assert provider.name == "Test"
    
    def test_default_token_counting(self):
        """Test default token counting implementation"""
        class MockProvider(BaseProvider):
            async def initialize(self): return True
            async def list_models(self): return []
            async def complete(self, request): return None
            async def stream_complete(self, request): pass
            async def health_check(self): return {}
        
        provider = MockProvider({})
        
        # Test token counting
        token_count = provider.count_tokens("hello world test", "model")
        assert isinstance(token_count, (int, float))
        assert token_count > 0
    
    def test_default_cost_estimation(self):
        """Test default cost estimation (should be 0 for local providers)"""
        class MockProvider(BaseProvider):
            async def initialize(self): return True
            async def list_models(self): return []
            async def complete(self, request): return None
            async def stream_complete(self, request): pass
            async def health_check(self): return {}
        
        provider = MockProvider({})
        
        # Test cost estimation
        cost = provider.estimate_cost(100, "model")
        assert cost == 0.0

class TestOllamaProvider:
    """Test the Ollama provider implementation"""
    
    @pytest.fixture
    def ollama_config(self):
        return {"base_url": "http://localhost:11434"}
    
    @pytest.fixture
    def ollama_provider(self, ollama_config):
        return OllamaProvider(ollama_config)
    
    def test_ollama_provider_initialization(self, ollama_provider):
        """Test Ollama provider initialization"""
        assert ollama_provider.base_url == "http://localhost:11434"
        assert ollama_provider.is_local is True
        assert ollama_provider.requires_api_key is False
        assert ollama_provider.name == "Ollama"
    
    @pytest.mark.asyncio
    async def test_ollama_server_connection_success(self, ollama_provider):
        """Test successful connection to Ollama server"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await ollama_provider.initialize()
            assert result is True
            
            # Verify the correct endpoint was called
            mock_get.assert_called_once()
            call_args = mock_get.call_args[0]
            assert call_args[0] == "http://localhost:11434/api/tags"
    
    @pytest.mark.asyncio
    async def test_ollama_server_connection_failure(self, ollama_provider):
        """Test failed connection to Ollama server"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock connection error
            mock_get.side_effect = aiohttp.ClientError("Connection failed")
            
            result = await ollama_provider.initialize()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_ollama_server_http_error(self, ollama_provider):
        """Test HTTP error from Ollama server"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock 404 response
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await ollama_provider.initialize()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_list_models_success(self, ollama_provider):
        """Test successful model listing"""
        mock_models_response = {
            "models": [
                {
                    "name": "llama2:7b",
                    "size": 3825819519,
                    "digest": "sha256:abc123"
                },
                {
                    "name": "codellama:13b", 
                    "size": 7365960935,
                    "digest": "sha256:def456"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_models_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            models = await ollama_provider.list_models()
            
            assert len(models) == 2
            assert models[0].name == "llama2:7b"
            assert models[0].provider == "ollama"
            assert models[1].name == "codellama:13b"
            assert models[1].provider == "ollama"
            
            # Verify capabilities are set
            for model in models:
                assert "chat" in model.capabilities
                assert "completion" in model.capabilities
    
    @pytest.mark.asyncio
    async def test_list_models_empty_response(self, ollama_provider):
        """Test empty models response"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"models": []}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            models = await ollama_provider.list_models()
            assert len(models) == 0
    
    @pytest.mark.asyncio
    async def test_list_models_error(self, ollama_provider):
        """Test error handling in model listing"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            models = await ollama_provider.list_models()
            assert len(models) == 0
    
    @pytest.mark.asyncio
    async def test_non_streaming_completion(self, ollama_provider, sample_completion_request):
        """Test non-streaming completion"""
        mock_response = {
            "response": "Hello! How can I help you today?",
            "model": "llama2:7b",
            "created_at": "2024-08-25T10:00:00Z",
            "done": True,
            "total_duration": 1500000000,
            "load_duration": 500000000,
            "prompt_eval_count": 5,
            "prompt_eval_duration": 800000000,
            "eval_count": 8,
            "eval_duration": 700000000
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            response = await ollama_provider.complete(sample_completion_request)
            
            assert isinstance(response, CompletionResponse)
            assert response.content == "Hello! How can I help you today?"
            assert response.model == "llama2:7b"
            assert response.provider == "ollama"
            assert response.usage["prompt_tokens"] == 5
            assert response.usage["completion_tokens"] == 8
            assert response.usage["total_tokens"] == 13
    
    @pytest.mark.asyncio
    async def test_streaming_completion(self, ollama_provider, sample_completion_request):
        """Test streaming completion"""
        sample_completion_request.stream = True
        
        # Mock streaming response chunks
        mock_chunks = [
            json.dumps({"response": "Hello", "done": False}),
            json.dumps({"response": " there", "done": False}),
            json.dumps({"response": "!", "done": False}),
            json.dumps({"response": "", "done": True, "eval_count": 3, "prompt_eval_count": 2})
        ]
        
        async def mock_stream_content():
            for chunk in mock_chunks:
                yield chunk.encode()
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.content.iter_chunked.return_value = mock_stream_content()
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            chunks = []
            async for chunk in ollama_provider.stream_complete(sample_completion_request):
                chunks.append(chunk)
            
            # Verify we got the expected chunks
            assert chunks == ["Hello", " there", "!"]
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, ollama_provider):
        """Test health check when server is healthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"models": [{"name": "llama2:7b"}]}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            health = await ollama_provider.health_check()
            
            assert health["healthy"] is True
            assert health["models_available"] == 1
            assert "latency_ms" in health
            assert health["latency_ms"] >= 0
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, ollama_provider):
        """Test health check when server is unhealthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            
            health = await ollama_provider.health_check()
            
            assert health["healthy"] is False
            assert health["models_available"] == 0
            assert "error" in health
            assert "Connection refused" in health["error"]
    
    @pytest.mark.asyncio
    async def test_completion_error_handling(self, ollama_provider, sample_completion_request):
        """Test error handling during completion"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientError("Request failed")
            
            with pytest.raises(Exception) as exc_info:
                await ollama_provider.complete(sample_completion_request)
            
            assert "Request failed" in str(exc_info.value)

class TestProviderManager:
    """Test the provider manager functionality"""
    
    @pytest.fixture
    def manager_config(self):
        return {
            "ollama": {"base_url": "http://localhost:11434"},
            "openai": {"api_key": "test-key"}
        }
    
    @pytest.fixture
    def provider_manager(self, manager_config):
        return ProviderManager(manager_config)
    
    def test_provider_manager_initialization(self, provider_manager):
        """Test provider manager initialization"""
        assert provider_manager.primary_provider == "ollama"
        assert len(provider_manager.providers) == 0  # Not initialized yet
        assert provider_manager.fallback_order == ["ollama", "openai", "gemini", "perplexity"]
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self, provider_manager):
        """Test provider initialization"""
        with patch('app.llm_providers.ollama_provider.OllamaProvider.initialize', return_value=True):
            await provider_manager.initialize_providers()
            
            assert "ollama" in provider_manager.providers
            assert isinstance(provider_manager.providers["ollama"], OllamaProvider)
    
    @pytest.mark.asyncio
    async def test_provider_initialization_with_failures(self, provider_manager):
        """Test provider initialization with some failures"""
        with patch('app.llm_providers.ollama_provider.OllamaProvider.initialize', return_value=False):
            await provider_manager.initialize_providers()
            
            # Provider should still be added even if initialization fails
            assert "ollama" in provider_manager.providers
    
    @pytest.mark.asyncio 
    async def test_fallback_completion_success(self, provider_manager, sample_completion_request, sample_completion_response):
        """Test successful completion with fallback"""
        # Mock providers
        mock_ollama = AsyncMock()
        mock_ollama.health_check.return_value = {"healthy": True}
        mock_ollama.complete.return_value = sample_completion_response
        
        provider_manager.providers = {"ollama": mock_ollama}
        
        response = await provider_manager.complete_with_fallback(sample_completion_request)
        
        assert response == sample_completion_response
        mock_ollama.health_check.assert_called_once()
        mock_ollama.complete.assert_called_once_with(sample_completion_request)
    
    @pytest.mark.asyncio
    async def test_fallback_completion_with_primary_failure(self, provider_manager, sample_completion_request, sample_completion_response):
        """Test fallback when primary provider fails"""
        # Mock primary provider (unhealthy)
        mock_ollama = AsyncMock()
        mock_ollama.health_check.return_value = {"healthy": False}
        
        # Mock secondary provider (healthy)
        mock_openai = AsyncMock()
        mock_openai.health_check.return_value = {"healthy": True}
        mock_openai.complete.return_value = sample_completion_response
        
        provider_manager.providers = {"ollama": mock_ollama, "openai": mock_openai}
        
        response = await provider_manager.complete_with_fallback(sample_completion_request)
        
        assert response == sample_completion_response
        mock_ollama.health_check.assert_called_once()
        mock_openai.health_check.assert_called_once()
        mock_openai.complete.assert_called_once_with(sample_completion_request)
    
    @pytest.mark.asyncio
    async def test_fallback_all_providers_fail(self, provider_manager, sample_completion_request):
        """Test behavior when all providers fail"""
        # Mock all providers as unhealthy
        mock_ollama = AsyncMock()
        mock_ollama.health_check.return_value = {"healthy": False}
        
        mock_openai = AsyncMock() 
        mock_openai.health_check.return_value = {"healthy": False}
        
        provider_manager.providers = {"ollama": mock_ollama, "openai": mock_openai}
        
        with pytest.raises(Exception, match="No providers available"):
            await provider_manager.complete_with_fallback(sample_completion_request)
    
    @pytest.mark.asyncio
    async def test_get_all_models(self, provider_manager):
        """Test getting models from all providers"""
        # Mock providers with different models
        mock_ollama = AsyncMock()
        mock_ollama.list_models.return_value = [
            ModelInfo("llama2:7b", "ollama", 4096, ["chat"])
        ]
        
        mock_openai = AsyncMock()
        mock_openai.list_models.return_value = [
            ModelInfo("gpt-3.5-turbo", "openai", 16385, ["chat"])
        ]
        
        provider_manager.providers = {"ollama": mock_ollama, "openai": mock_openai}
        
        all_models = await provider_manager.get_all_models()
        
        assert "ollama" in all_models
        assert "openai" in all_models
        assert all_models["ollama"] == ["llama2:7b"]
        assert all_models["openai"] == ["gpt-3.5-turbo"]
    
    @pytest.mark.asyncio
    async def test_health_check_all(self, provider_manager):
        """Test health check for all providers"""
        # Mock providers with different health statuses
        mock_ollama = AsyncMock()
        mock_ollama.health_check.return_value = {"healthy": True, "models_available": 2}
        
        mock_openai = AsyncMock()
        mock_openai.health_check.return_value = {"healthy": False, "error": "API key invalid"}
        
        provider_manager.providers = {"ollama": mock_ollama, "openai": mock_openai}
        
        health_results = await provider_manager.health_check_all()
        
        assert health_results["ollama"]["healthy"] is True
        assert health_results["ollama"]["models_available"] == 2
        assert health_results["openai"]["healthy"] is False
        assert "error" in health_results["openai"]
    
    def test_get_provider(self, provider_manager):
        """Test getting specific provider"""
        mock_ollama = Mock()
        provider_manager.providers = {"ollama": mock_ollama}
        
        # Test existing provider
        provider = provider_manager.get_provider("ollama")
        assert provider == mock_ollama
        
        # Test non-existent provider
        provider = provider_manager.get_provider("nonexistent")
        assert provider is None

class TestDataModels:
    """Test the data models (ModelInfo, CompletionRequest, CompletionResponse)"""
    
    def test_model_info_creation(self):
        """Test ModelInfo dataclass creation"""
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
    
    def test_model_info_defaults(self):
        """Test ModelInfo with default values"""
        model = ModelInfo(
            name="test-model",
            provider="test-provider", 
            context_length=4096,
            capabilities=["chat"]
        )
        
        assert model.cost_per_token is None
    
    def test_completion_request_creation(self):
        """Test CompletionRequest dataclass creation"""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model",
            temperature=0.8,
            max_tokens=100,
            stream=True
        )
        
        assert len(request.messages) == 1
        assert request.messages[0]["role"] == "user"
        assert request.model == "test-model"
        assert request.temperature == 0.8
        assert request.max_tokens == 100
        assert request.stream is True
    
    def test_completion_request_defaults(self):
        """Test CompletionRequest with default values"""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        assert request.temperature == 0.7
        assert request.max_tokens is None
        assert request.stream is False
        assert request.functions is None
        assert request.system_prompt is None
    
    def test_completion_response_creation(self):
        """Test CompletionResponse dataclass creation"""
        response = CompletionResponse(
            content="Hello there!",
            model="test-model",
            provider="test-provider",
            usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            cost=0.001,
            citations=[{"url": "test.com", "title": "Test"}]
        )
        
        assert response.content == "Hello there!"
        assert response.model == "test-model"
        assert response.provider == "test-provider"
        assert response.usage["total_tokens"] == 5
        assert response.cost == 0.001
        assert len(response.citations) == 1

@pytest.mark.integration
class TestProviderIntegration:
    """Integration tests that require actual network calls or mock servers"""
    
    @pytest.mark.asyncio
    async def test_provider_roundtrip(self):
        """Test a complete provider roundtrip with mocked responses"""
        # This would be moved to integration tests in practice
        config = {"base_url": "http://localhost:11434"}
        provider = OllamaProvider(config)
        
        # Mock all network calls
        with patch('aiohttp.ClientSession.get') as mock_get, \
             patch('aiohttp.ClientSession.post') as mock_post:
            
            # Mock initialization
            mock_init_resp = AsyncMock()
            mock_init_resp.status = 200
            mock_get.return_value.__aenter__.return_value = mock_init_resp
            
            # Mock completion
            mock_completion_resp = AsyncMock()
            mock_completion_resp.json.return_value = {
                "response": "Test response",
                "model": "test-model",
                "done": True,
                "eval_count": 10,
                "prompt_eval_count": 5
            }
            mock_post.return_value.__aenter__.return_value = mock_completion_resp
            
            # Test the flow
            assert await provider.initialize() is True
            
            request = CompletionRequest(
                messages=[{"role": "user", "content": "Test"}],
                model="test-model"
            )
            
            response = await provider.complete(request)
            assert response.content == "Test response"
            assert response.provider == "ollama"

if __name__ == "__main__":
    # Run tests with: python -m pytest tests/unit/test_provider_interfaces.py -v
    pytest.main([__file__, "-v"])