"""
Integration tests for LLM providers using mock servers
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import patch

from app.llm_providers.ollama_provider import OllamaProvider
from app.llm_providers.provider_manager import ProviderManager
from app.llm_providers.base_provider import CompletionRequest, CompletionResponse
from tests.integration.test_mock_server import MockServerFactory, MockServer
from tests.mocks.mock_provider import MockScenario


class TestOllamaProviderIntegration:
    """Integration tests for OllamaProvider with mock server"""
    
    def setup_method(self):
        """Setup mock server for each test"""
        self.mock_server = MockServerFactory.create_ollama_server()
        self.server_url = self.mock_server.start()
        
        # Create provider pointing to mock server
        config = {'base_url': self.server_url}
        self.provider = OllamaProvider(config)
    
    def teardown_method(self):
        """Cleanup mock server"""
        self.mock_server.stop()
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful provider initialization"""
        self.mock_server.set_scenario("ollama_healthy")
        
        result = await self.provider.initialize()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test provider initialization failure"""
        # Stop server to simulate connection failure
        self.mock_server.stop()
        
        result = await self.provider.initialize()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_models_success(self):
        """Test successful model listing"""
        self.mock_server.set_scenario("ollama_healthy")
        
        models = await self.provider.list_models()
        assert len(models) > 0
        assert all(model.provider == 'ollama' for model in models)
        assert all('chat' in model.capabilities for model in models)
    
    @pytest.mark.asyncio
    async def test_list_models_failure(self):
        """Test model listing failure"""
        # Add failing scenario
        self.mock_server.add_scenario("list_fail", MockScenario(
            name="list_fail",
            should_fail=True,
            failure_type="model_list"
        ))
        self.mock_server.set_scenario("list_fail")
        
        models = await self.provider.list_models()
        assert len(models) == 0  # Should return empty list on failure
    
    @pytest.mark.asyncio
    async def test_complete_success(self):
        """Test successful completion"""
        self.mock_server.set_scenario("ollama_healthy")
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello, world!"}],
            model="mock-model:latest"
        )
        
        response = await self.provider.complete(request)
        assert isinstance(response, CompletionResponse)
        assert response.provider == 'ollama'
        assert response.model == request.model
        assert "Hello, world!" in response.content or "mock response" in response.content.lower()
        assert response.usage['total_tokens'] > 0
        assert response.cost == 0.0  # Local models are free
    
    @pytest.mark.asyncio
    async def test_complete_with_system_prompt(self):
        """Test completion with system prompt"""
        self.mock_server.set_scenario("ollama_healthy")
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Tell me a joke"}],
            model="mock-model:latest",
            system_prompt="You are a comedian"
        )
        
        response = await self.provider.complete(request)
        assert response.content is not None
        assert len(response.content) > 0
    
    @pytest.mark.asyncio
    async def test_stream_complete_success(self):
        """Test successful streaming completion"""
        self.mock_server.set_scenario("ollama_healthy")
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Stream test"}],
            model="mock-model:latest",
            stream=True
        )
        
        chunks = []
        async for chunk in self.provider.stream_complete(request):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        full_response = ''.join(chunks)
        assert len(full_response) > 0
    
    @pytest.mark.asyncio
    async def test_complete_timeout_handling(self):
        """Test completion with slow response"""
        self.mock_server.set_scenario("ollama_slow")
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Slow request"}],
            model="mock-model:latest"
        )
        
        # Should complete but take some time
        start_time = asyncio.get_event_loop().time()
        response = await self.provider.complete(request)
        end_time = asyncio.get_event_loop().time()
        
        assert response.content is not None
        assert end_time - start_time >= 2.0  # Should take at least 2 seconds
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when provider is healthy"""
        self.mock_server.set_scenario("ollama_healthy")
        
        health = await self.provider.health_check()
        assert health['healthy'] is True
        assert health['provider'] == 'ollama'
        assert 'models_available' in health
        assert isinstance(health['models'], list)
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check when provider is unhealthy"""
        # Stop server
        self.mock_server.stop()
        
        health = await self.provider.health_check()
        assert health['healthy'] is False
        assert health['provider'] == 'ollama'
        assert 'error' in health
    
    @pytest.mark.asyncio
    async def test_pull_model_success(self):
        """Test successful model pulling"""
        self.mock_server.set_scenario("ollama_healthy")
        
        result = await self.provider.pull_model("test-model:latest")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_pull_model_failure(self):
        """Test model pulling failure"""
        self.mock_server.add_scenario("pull_fail", MockScenario(
            name="pull_fail",
            should_fail=True,
            failure_type="model_pull"
        ))
        self.mock_server.set_scenario("pull_fail")
        
        result = await self.provider.pull_model("nonexistent-model")
        assert result is False


class TestProviderManagerIntegration:
    """Integration tests for ProviderManager with multiple mock servers"""
    
    def setup_method(self):
        """Setup multiple mock servers"""
        self.ollama_server = MockServerFactory.create_ollama_server()
        self.openai_server = MockServerFactory.create_openai_server()
        
        self.ollama_url = self.ollama_server.start()
        self.openai_url = self.openai_server.start()
        
        # Configure manager with mock server URLs
        config = {
            'ollama': {'base_url': self.ollama_url}
        }
        self.manager = ProviderManager(config)
    
    def teardown_method(self):
        """Cleanup mock servers"""
        self.ollama_server.stop()
        self.openai_server.stop()
    
    @pytest.mark.asyncio
    async def test_initialize_providers_integration(self):
        """Test provider initialization with real HTTP calls"""
        self.ollama_server.set_scenario("ollama_healthy")
        
        await self.manager.initialize_providers()
        
        assert 'ollama' in self.manager.providers
        
        # Test that provider is actually functional
        ollama_provider = self.manager.get_provider('ollama')
        health = await ollama_provider.health_check()
        assert health['healthy'] is True
    
    @pytest.mark.asyncio
    async def test_complete_with_fallback_integration(self):
        """Test fallback chain with real HTTP servers"""
        self.ollama_server.set_scenario("ollama_healthy")
        
        await self.manager.initialize_providers()
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Integration test"}],
            model="mock-model:latest"
        )
        
        response = await self.manager.complete_with_fallback(request)
        assert response.content is not None
        assert "Integration test" in response.content or "mock" in response.content.lower()
    
    @pytest.mark.asyncio
    async def test_fallback_on_server_failure(self):
        """Test fallback when primary server fails"""
        # Setup two Ollama servers - one will fail
        backup_server = MockServerFactory.create_ollama_server()
        backup_url = backup_server.start()
        
        try:
            # Configure manager with both servers
            config = {
                'primary': {'base_url': self.ollama_url},
                'backup': {'base_url': backup_url}
            }
            
            manager = ProviderManager({})
            
            # Create providers manually for testing
            from app.llm_providers.ollama_provider import OllamaProvider
            primary_provider = OllamaProvider(config['primary'])
            backup_provider = OllamaProvider(config['backup'])
            
            manager.providers = {
                'primary': primary_provider,
                'backup': backup_provider
            }
            manager.fallback_order = ['primary', 'backup']
            
            # Set scenarios
            self.ollama_server.set_scenario("ollama_error")  # Primary fails
            backup_server.set_scenario("ollama_healthy")     # Backup works
            
            request = CompletionRequest(
                messages=[{"role": "user", "content": "Fallback test"}],
                model="mock-model:latest"
            )
            
            response = await manager.complete_with_fallback(request)
            assert response.content is not None
            
        finally:
            backup_server.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self):
        """Test concurrent requests to real mock server"""
        self.ollama_server.set_scenario("ollama_healthy")
        await self.manager.initialize_providers()
        
        # Create multiple concurrent requests
        requests = [
            CompletionRequest(
                messages=[{"role": "user", "content": f"Concurrent request {i}"}],
                model="mock-model:latest"
            )
            for i in range(5)
        ]
        
        # Execute concurrently
        responses = await asyncio.gather(*[
            self.manager.complete_with_fallback(req)
            for req in requests
        ])
        
        # All should succeed
        assert len(responses) == 5
        for response in responses:
            assert response.content is not None
    
    @pytest.mark.asyncio
    async def test_get_all_models_integration(self):
        """Test getting models from real mock server"""
        self.ollama_server.set_scenario("ollama_healthy")
        await self.manager.initialize_providers()
        
        models = await self.manager.get_all_models()
        assert 'ollama' in models
        assert len(models['ollama']) > 0
        assert all(isinstance(model_name, str) for model_name in models['ollama'])
    
    @pytest.mark.asyncio
    async def test_health_check_all_integration(self):
        """Test health check across all providers"""
        self.ollama_server.set_scenario("ollama_healthy")
        await self.manager.initialize_providers()
        
        health_results = await self.manager.health_check_all()
        assert 'ollama' in health_results
        assert health_results['ollama']['healthy'] is True


class TestProviderErrorRecovery:
    """Test error recovery and resilience"""
    
    def setup_method(self):
        """Setup for error recovery tests"""
        self.mock_server = MockServerFactory.create_ollama_server()
        self.server_url = self.mock_server.start()
        
        config = {'base_url': self.server_url}
        self.provider = OllamaProvider(config)
    
    def teardown_method(self):
        """Cleanup"""
        self.mock_server.stop()
    
    @pytest.mark.asyncio
    async def test_network_error_recovery(self):
        """Test recovery from network errors"""
        # First request fails
        self.mock_server.add_scenario("network_fail", MockScenario(
            name="network_fail",
            should_fail=True,
            failure_type="network"
        ))
        self.mock_server.set_scenario("network_fail")
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Test"}],
            model="mock-model:latest"
        )
        
        # First request should fail
        with pytest.raises(Exception):
            await self.provider.complete(request)
        
        # Switch to healthy scenario
        self.mock_server.set_scenario("ollama_healthy")
        
        # Second request should succeed
        response = await self.provider.complete(request)
        assert response.content is not None
    
    @pytest.mark.asyncio
    async def test_partial_stream_failure(self):
        """Test handling partial streaming failures"""
        # Create scenario that fails mid-stream
        self.mock_server.add_scenario("partial_stream", MockScenario(
            name="partial_stream",
            response_content="Partial response",
            streaming_chunks=["Start", "Middle"]  # Will be interrupted
        ))
        self.mock_server.set_scenario("partial_stream")
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Stream test"}],
            model="mock-model:latest",
            stream=True
        )
        
        chunks = []
        try:
            async for chunk in self.provider.stream_complete(request):
                chunks.append(chunk)
                # Simulate server stopping mid-stream
                if len(chunks) == 2:
                    self.mock_server.stop()
        except:
            pass  # Expected to fail
        
        # Should have received partial data
        assert len(chunks) >= 1
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling"""
        # Create very slow scenario
        self.mock_server.add_scenario("very_slow", MockScenario(
            name="very_slow",
            response_content="Delayed response",
            response_delay=5.0  # 5 second delay
        ))
        self.mock_server.set_scenario("very_slow")
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Timeout test"}],
            model="mock-model:latest"
        )
        
        # Test with custom timeout
        try:
            timeout = aiohttp.ClientTimeout(total=1.0)  # 1 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # This would normally be done inside the provider
                # Here we're testing the timeout behavior
                with pytest.raises(asyncio.TimeoutError):
                    await asyncio.wait_for(
                        self.provider.complete(request),
                        timeout=1.0
                    )
        except asyncio.TimeoutError:
            pass  # Expected behavior


class TestMultiProviderScenarios:
    """Test complex multi-provider scenarios"""
    
    def setup_method(self):
        """Setup multiple providers and servers"""
        self.ollama_server = MockServerFactory.create_ollama_server()
        self.openai_server = MockServerFactory.create_openai_server()
        self.multi_server = MockServerFactory.create_multi_model_server()
        
        self.ollama_url = self.ollama_server.start()
        self.openai_url = self.openai_server.start()
        self.multi_url = self.multi_server.start()
    
    def teardown_method(self):
        """Cleanup all servers"""
        self.ollama_server.stop()
        self.openai_server.stop()
        self.multi_server.stop()
    
    @pytest.mark.asyncio
    async def test_load_balancing_simulation(self):
        """Simulate load balancing across providers"""
        # Create manager with multiple providers
        from app.llm_providers.ollama_provider import OllamaProvider
        
        manager = ProviderManager({})
        
        # Create providers pointing to different servers
        ollama_provider = OllamaProvider({'base_url': self.ollama_url})
        openai_provider = OllamaProvider({'base_url': self.openai_url})  # Using Ollama provider for simplicity
        
        manager.providers = {
            'ollama': ollama_provider,
            'openai': openai_provider
        }
        
        # Set different scenarios
        self.ollama_server.set_scenario("ollama_healthy")
        self.openai_server.set_scenario("openai_gpt4")
        
        # Test round-robin style requests
        requests = [
            CompletionRequest(
                messages=[{"role": "user", "content": f"Request {i}"}],
                model="mock-model:latest"
            )
            for i in range(4)
        ]
        
        # Alternate preferred providers
        responses = []
        for i, request in enumerate(requests):
            preferred = 'ollama' if i % 2 == 0 else 'openai'
            response = await manager.complete_with_fallback(
                request,
                preferred_provider=preferred
            )
            responses.append(response)
        
        assert len(responses) == 4
        for response in responses:
            assert response.content is not None
    
    @pytest.mark.asyncio
    async def test_cost_optimization_strategy(self):
        """Test cost-aware provider selection"""
        # Setup providers with different cost profiles
        self.multi_server.set_scenario("text_model")  # Cheap
        
        # Simulate choosing based on cost
        cheap_request = CompletionRequest(
            messages=[{"role": "user", "content": "Simple query"}],
            model="cheap-model:latest"
        )
        
        expensive_request = CompletionRequest(
            messages=[{"role": "user", "content": "Complex analysis needed"}],
            model="expensive-model:latest"
        )
        
        from app.llm_providers.ollama_provider import OllamaProvider
        provider = OllamaProvider({'base_url': self.multi_url})
        
        # Test both requests
        cheap_response = await provider.complete(cheap_request)
        expensive_response = await provider.complete(expensive_request)
        
        assert cheap_response.content is not None
        assert expensive_response.content is not None
        assert cheap_response.cost == 0.0  # Ollama is always free
        assert expensive_response.cost == 0.0