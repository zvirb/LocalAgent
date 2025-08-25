"""
Unit tests for ProviderManager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.llm_providers.provider_manager import ProviderManager
from app.llm_providers.base_provider import CompletionRequest, CompletionResponse, ModelInfo
from tests.mocks.mock_provider import MockProvider, MockProviderFactory, MockScenario


class TestProviderManager:
    """Test ProviderManager functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.config = {
            'ollama': {'base_url': 'http://localhost:11434'},
            'openai': {'api_key': 'sk-test123'},
            'gemini': {'api_key': 'test-gemini-key'},
            'perplexity': {'api_key': 'test-perplexity-key'}
        }
        self.manager = ProviderManager(self.config)
    
    def test_manager_initialization(self):
        """Test ProviderManager basic initialization"""
        assert self.manager.config == self.config
        assert self.manager.primary_provider == 'ollama'
        assert self.manager.fallback_order == ['ollama', 'openai', 'gemini', 'perplexity']
        assert len(self.manager.providers) == 0  # Not initialized yet
    
    @pytest.mark.asyncio
    async def test_initialize_providers_success(self):
        """Test successful provider initialization"""
        with patch('app.llm_providers.provider_manager.OllamaProvider') as MockOllama, \
             patch('app.llm_providers.openai_provider.OpenAIProvider') as MockOpenAI:
            
            # Create mock provider instances
            mock_ollama = AsyncMock()
            mock_ollama.initialize.return_value = True
            MockOllama.return_value = mock_ollama
            
            mock_openai = AsyncMock()
            mock_openai.initialize.return_value = True
            MockOpenAI.return_value = mock_openai
            
            await self.manager.initialize_providers()
            
            # Verify providers were created and initialized
            assert 'ollama' in self.manager.providers
            assert 'openai' in self.manager.providers
            mock_ollama.initialize.assert_called_once()
            mock_openai.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_providers_partial_failure(self):
        """Test provider initialization with some failures"""
        with patch('app.llm_providers.provider_manager.OllamaProvider') as MockOllama:
            mock_ollama = AsyncMock()
            mock_ollama.initialize.side_effect = Exception("Connection failed")
            MockOllama.return_value = mock_ollama
            
            # Should not raise exception, just log failures
            await self.manager.initialize_providers()
            
            assert 'ollama' in self.manager.providers
            mock_ollama.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_providers_missing_config(self):
        """Test initialization with missing provider configs"""
        # Manager with only Ollama config
        minimal_config = {'ollama': {'base_url': 'http://localhost:11434'}}
        manager = ProviderManager(minimal_config)
        
        with patch('app.llm_providers.provider_manager.OllamaProvider') as MockOllama:
            mock_ollama = AsyncMock()
            mock_ollama.initialize.return_value = True
            MockOllama.return_value = mock_ollama
            
            await manager.initialize_providers()
            
            # Only Ollama should be initialized
            assert len(manager.providers) == 1
            assert 'ollama' in manager.providers
            assert 'openai' not in manager.providers


class TestProviderManagerWithMocks:
    """Test ProviderManager using MockProvider"""
    
    def setup_method(self):
        """Setup with mock providers"""
        self.manager = ProviderManager({})
        
        # Create mock providers
        self.mock_ollama = MockProviderFactory.create_fast_provider()
        self.mock_openai = MockProviderFactory.create_slow_provider()
        self.mock_gemini = MockProviderFactory.create_cost_aware_provider()
        
        # Manually assign to manager
        self.manager.providers = {
            'ollama': self.mock_ollama,
            'openai': self.mock_openai,
            'gemini': self.mock_gemini
        }
    
    @pytest.mark.asyncio
    async def test_complete_with_fallback_success(self):
        """Test successful completion with preferred provider"""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        response = await self.manager.complete_with_fallback(
            request, 
            preferred_provider='ollama'
        )
        
        assert response.provider == 'mock'
        assert response.content == "Quick mock response"
        assert self.mock_ollama.call_count == 1
    
    @pytest.mark.asyncio
    async def test_complete_with_fallback_chain(self):
        """Test fallback chain when primary provider fails"""
        # Make ollama fail
        self.mock_ollama.set_scenario("failing")
        self.mock_ollama.add_scenario("failing", MockScenario(
            name="failing",
            should_fail=True,
            failure_type="network"
        ))
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        response = await self.manager.complete_with_fallback(
            request,
            preferred_provider='ollama'
        )
        
        # Should have fallen back to openai
        assert response.provider == 'mock'
        assert self.mock_ollama.call_count == 1
        assert self.mock_openai.call_count == 1
    
    @pytest.mark.asyncio
    async def test_complete_with_fallback_all_fail(self):
        """Test behavior when all providers fail"""
        # Make all providers fail
        for provider in self.manager.providers.values():
            provider.add_scenario("failing", MockScenario(
                name="failing",
                should_fail=True,
                failure_type="network"
            ))
            provider.set_scenario("failing")
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        with pytest.raises(Exception, match="All providers failed"):
            await self.manager.complete_with_fallback(request)
    
    @pytest.mark.asyncio
    async def test_complete_with_fallback_unhealthy_providers(self):
        """Test fallback when providers are unhealthy"""
        # Make ollama unhealthy
        self.mock_ollama.set_health_status(False)
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        response = await self.manager.complete_with_fallback(request)
        
        # Should skip ollama and use openai
        assert self.mock_ollama.call_count == 0
        assert self.mock_openai.call_count == 1
    
    def test_get_provider(self):
        """Test getting specific provider"""
        provider = self.manager.get_provider('ollama')
        assert provider is self.mock_ollama
        
        provider = self.manager.get_provider('nonexistent')
        assert provider is None
    
    @pytest.mark.asyncio
    async def test_get_all_models(self):
        """Test getting models from all providers"""
        models = await self.manager.get_all_models()
        
        assert 'ollama' in models
        assert 'openai' in models
        assert 'gemini' in models
        
        # Each provider should return model names
        for provider_models in models.values():
            assert isinstance(provider_models, list)
    
    @pytest.mark.asyncio
    async def test_get_all_models_with_failures(self):
        """Test getting models when some providers fail"""
        # Make ollama fail model listing
        self.mock_ollama.add_scenario("model_fail", MockScenario(
            name="model_fail",
            should_fail=True,
            failure_type="model_list"
        ))
        self.mock_ollama.set_scenario("model_fail")
        
        models = await self.manager.get_all_models()
        
        assert models['ollama'] == []  # Empty due to failure
        assert len(models['openai']) > 0  # Should still work
    
    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all providers"""
        health_results = await self.manager.health_check_all()
        
        assert 'ollama' in health_results
        assert 'openai' in health_results
        assert 'gemini' in health_results
        
        for provider_health in health_results.values():
            assert 'healthy' in provider_health
            assert 'provider' in provider_health


class TestProviderManagerFallbackLogic:
    """Test advanced fallback logic"""
    
    def setup_method(self):
        """Setup for fallback testing"""
        self.manager = ProviderManager({})
        self.manager.fallback_order = ['primary', 'secondary', 'tertiary']
    
    @pytest.mark.asyncio
    async def test_fallback_order_preferred_provider(self):
        """Test fallback order with preferred provider"""
        # Create providers with different response patterns
        primary = MockProviderFactory.create_fast_provider()
        secondary = MockProviderFactory.create_slow_provider() 
        tertiary = MockProviderFactory.create_cost_aware_provider()
        
        # Set up identifiable responses
        primary.add_scenario("id", MockScenario(name="id", response_content="PRIMARY"))
        secondary.add_scenario("id", MockScenario(name="id", response_content="SECONDARY"))
        tertiary.add_scenario("id", MockScenario(name="id", response_content="TERTIARY"))
        
        primary.set_scenario("id")
        secondary.set_scenario("id")
        tertiary.set_scenario("id")
        
        self.manager.providers = {
            'primary': primary,
            'secondary': secondary,
            'tertiary': tertiary
        }
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        # Test preferred provider first
        response = await self.manager.complete_with_fallback(
            request,
            preferred_provider='secondary'
        )
        assert response.content == "SECONDARY"
        
        # Test default order (should use primary)
        primary.reset_call_history()
        secondary.reset_call_history()
        tertiary.reset_call_history()
        
        response = await self.manager.complete_with_fallback(request)
        assert response.content == "PRIMARY"
        assert primary.call_count == 1
        assert secondary.call_count == 0
    
    @pytest.mark.asyncio
    async def test_fallback_with_mixed_health_states(self):
        """Test fallback with mixed provider health states"""
        primary = MockProviderFactory.create_failing_provider("network")
        secondary = MockProviderFactory.create_fast_provider()
        secondary.set_health_status(False)  # Unhealthy
        tertiary = MockProviderFactory.create_cost_aware_provider()
        
        tertiary.add_scenario("working", MockScenario(
            name="working",
            response_content="TERTIARY_SUCCESS"
        ))
        tertiary.set_scenario("working")
        
        self.manager.providers = {
            'primary': primary,
            'secondary': secondary, 
            'tertiary': tertiary
        }
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        response = await self.manager.complete_with_fallback(request)
        assert response.content == "TERTIARY_SUCCESS"
        assert tertiary.call_count == 1
    
    @pytest.mark.asyncio
    async def test_provider_error_handling(self):
        """Test various provider error scenarios"""
        # Network error provider
        network_fail = MockProviderFactory.create_failing_provider("network")
        
        # Auth error provider  
        auth_fail = MockProviderFactory.create_failing_provider("auth")
        
        # Working provider
        working = MockProviderFactory.create_fast_provider()
        working.add_scenario("success", MockScenario(
            name="success",
            response_content="SUCCESS_AFTER_FAILURES"
        ))
        working.set_scenario("success")
        
        self.manager.providers = {
            'network_fail': network_fail,
            'auth_fail': auth_fail,
            'working': working
        }
        self.manager.fallback_order = ['network_fail', 'auth_fail', 'working']
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model"
        )
        
        response = await self.manager.complete_with_fallback(request)
        assert response.content == "SUCCESS_AFTER_FAILURES"
        assert working.call_count == 1


class TestProviderManagerPerformance:
    """Test ProviderManager performance characteristics"""
    
    def setup_method(self):
        """Setup for performance testing"""
        self.manager = ProviderManager({})
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling multiple concurrent requests"""
        fast_provider = MockProviderFactory.create_fast_provider()
        self.manager.providers = {'fast': fast_provider}
        self.manager.fallback_order = ['fast']
        
        requests = [
            CompletionRequest(
                messages=[{"role": "user", "content": f"Request {i}"}],
                model="test-model"
            )
            for i in range(10)
        ]
        
        start_time = asyncio.get_event_loop().time()
        responses = await asyncio.gather(*[
            self.manager.complete_with_fallback(req) 
            for req in requests
        ])
        end_time = asyncio.get_event_loop().time()
        
        # All requests should complete
        assert len(responses) == 10
        assert fast_provider.call_count == 10
        
        # Should complete in reasonable time (concurrent, not sequential)
        total_time = end_time - start_time
        assert total_time < 1.0  # Should be much faster than 10 * delay
    
    @pytest.mark.asyncio
    async def test_provider_selection_performance(self):
        """Test performance of provider selection logic"""
        # Create many providers
        providers = {}
        for i in range(20):
            provider = MockProviderFactory.create_fast_provider()
            provider.add_scenario("perf", MockScenario(
                name="perf",
                response_content=f"Provider_{i}",
                response_delay=0.001  # Very fast
            ))
            provider.set_scenario("perf")
            providers[f'provider_{i}'] = provider
        
        self.manager.providers = providers
        self.manager.fallback_order = list(providers.keys())
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Performance test"}],
            model="test-model"
        )
        
        # Time provider selection and execution
        start_time = asyncio.get_event_loop().time()
        response = await self.manager.complete_with_fallback(request)
        end_time = asyncio.get_event_loop().time()
        
        assert response.content == "Provider_0"  # First provider should be used
        assert end_time - start_time < 0.1  # Should be very fast
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_many_providers(self):
        """Test memory behavior with many providers"""
        import tracemalloc
        
        tracemalloc.start()
        
        # Create many providers
        for i in range(50):
            provider = MockProviderFactory.create_fast_provider()
            self.manager.providers[f'provider_{i}'] = provider
        
        # Perform operations
        health_results = await self.manager.health_check_all()
        models = await self.manager.get_all_models()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Verify operations completed successfully
        assert len(health_results) == 50
        assert len(models) == 50
        
        # Memory usage should be reasonable (less than 50MB)
        assert peak < 50 * 1024 * 1024