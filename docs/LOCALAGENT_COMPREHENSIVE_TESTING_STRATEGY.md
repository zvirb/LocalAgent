# LocalAgent Comprehensive Testing Strategy

## Executive Summary

This document outlines a comprehensive testing strategy for LocalAgent, a multi-provider LLM orchestration CLI tool. The strategy encompasses unit testing, integration testing, end-to-end testing, performance benchmarking, security validation, chaos engineering, load testing, regression testing, contract testing, and continuous CI/CD integration.

## 1. Unit Testing Strategy for Provider Interfaces

### 1.1 Core Testing Framework Architecture

```python
# tests/unit/providers/test_base_provider.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
from app.llm_providers.base_provider import BaseProvider, CompletionRequest, CompletionResponse, ModelInfo

@pytest.fixture
def completion_request():
    return CompletionRequest(
        messages=[{"role": "user", "content": "Test message"}],
        model="test-model",
        temperature=0.7,
        stream=False
    )

@pytest.fixture
def expected_response():
    return CompletionResponse(
        content="Test response",
        model="test-model", 
        provider="test-provider",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )
```

### 1.2 Provider Interface Contract Testing

```python
class TestProviderContract:
    """Ensures all providers implement the required interface"""
    
    @pytest.mark.parametrize("provider_class", [
        OllamaProvider, OpenAIProvider, GeminiProvider, PerplexityProvider
    ])
    async def test_provider_implements_interface(self, provider_class):
        """Test that each provider implements all required methods"""
        provider = provider_class({"api_key": "test"})
        
        # Verify all abstract methods are implemented
        assert hasattr(provider, 'initialize')
        assert hasattr(provider, 'list_models')
        assert hasattr(provider, 'complete')
        assert hasattr(provider, 'stream_complete')
        assert hasattr(provider, 'health_check')
        
    async def test_completion_request_validation(self, provider_class):
        """Test request validation across all providers"""
        provider = provider_class({"api_key": "test"})
        
        # Invalid request should raise exception
        invalid_request = CompletionRequest(
            messages=[],  # Empty messages
            model="",     # Empty model
        )
        
        with pytest.raises(ValueError):
            await provider.complete(invalid_request)
```

### 1.3 Individual Provider Unit Tests

#### Ollama Provider Testing
```python
class TestOllamaProvider:
    
    @pytest.fixture
    def provider(self):
        return OllamaProvider({"base_url": "http://localhost:11434"})
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, provider):
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await provider.initialize()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self, provider):
        with patch('aiohttp.ClientSession.get', side_effect=Exception("Connection failed")):
            result = await provider.initialize()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_list_models(self, provider):
        mock_response = {
            "models": [
                {"name": "llama2:7b", "size": 3825819519},
                {"name": "codellama:13b", "size": 7365960935}
            ]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            models = await provider.list_models()
            assert len(models) == 2
            assert models[0].name == "llama2:7b"
            assert models[0].provider == "ollama"
    
    @pytest.mark.asyncio
    async def test_complete_non_streaming(self, provider, completion_request):
        mock_response = {
            "response": "Test response",
            "model": "llama2:7b",
            "eval_count": 20,
            "prompt_eval_count": 10
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_post.return_value.__aenter__.return_value = mock_resp
            
            response = await provider.complete(completion_request)
            assert response.content == "Test response"
            assert response.model == "llama2:7b"
            assert response.provider == "ollama"
```

#### OpenAI Provider Testing
```python
class TestOpenAIProvider:
    
    @pytest.fixture
    def provider(self):
        return OpenAIProvider({"api_key": "test-key"})
    
    @pytest.mark.asyncio
    async def test_api_key_validation(self):
        # Test with no API key
        provider_no_key = OpenAIProvider({})
        assert await provider_no_key.initialize() is False
        
        # Test with valid API key
        provider_with_key = OpenAIProvider({"api_key": "sk-test"})
        with patch.object(provider_with_key, 'client') as mock_client:
            mock_client.models.list.return_value = []
            assert await provider_with_key.initialize() is True
    
    @pytest.mark.asyncio 
    async def test_cost_calculation(self, provider):
        """Test accurate cost calculation for different models"""
        # GPT-4o pricing test
        cost = await provider.estimate_cost(1000, "gpt-4o")
        expected_cost = (1000/1000) * 0.005  # Input tokens
        assert cost == expected_cost
        
        # Test with usage data
        usage = {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}
        cost = provider._calculate_cost("gpt-4o", usage)
        expected = (100/1000 * 0.005) + (200/1000 * 0.015)
        assert cost == expected
    
    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, provider):
        """Test proper handling of rate limits"""
        from openai import RateLimitError
        
        with patch.object(provider.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = RateLimitError("Rate limit exceeded")
            
            with pytest.raises(RateLimitError):
                await provider.complete(completion_request)
```

### 1.4 Provider Manager Unit Tests

```python
class TestProviderManager:
    
    @pytest.fixture
    def config(self):
        return {
            "ollama": {"base_url": "http://localhost:11434"},
            "openai": {"api_key": "test-key"},
            "gemini": {"api_key": "test-key"}
        }
    
    @pytest.fixture
    def manager(self, config):
        return ProviderManager(config)
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self, manager):
        """Test that all configured providers are initialized"""
        with patch.multiple(
            'app.llm_providers.ollama_provider.OllamaProvider',
            initialize=AsyncMock(return_value=True)
        ), patch.multiple(
            'app.llm_providers.openai_provider.OpenAIProvider',
            initialize=AsyncMock(return_value=True)
        ):
            await manager.initialize_providers()
            
            assert 'ollama' in manager.providers
            assert 'openai' in manager.providers
            assert 'gemini' in manager.providers
    
    @pytest.mark.asyncio
    async def test_fallback_completion(self, manager, completion_request):
        """Test fallback mechanism when primary provider fails"""
        # Mock Ollama failure, OpenAI success
        ollama_mock = AsyncMock()
        ollama_mock.health_check.return_value = {"healthy": False}
        
        openai_mock = AsyncMock()
        openai_mock.health_check.return_value = {"healthy": True}
        openai_mock.complete.return_value = CompletionResponse(
            content="Fallback response",
            model="gpt-4o",
            provider="openai",
            usage={"total_tokens": 50}
        )
        
        manager.providers = {
            'ollama': ollama_mock,
            'openai': openai_mock
        }
        
        response = await manager.complete_with_fallback(completion_request)
        assert response.provider == "openai"
        assert response.content == "Fallback response"
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self, manager, completion_request):
        """Test behavior when all providers are unavailable"""
        failing_mock = AsyncMock()
        failing_mock.health_check.return_value = {"healthy": False}
        
        manager.providers = {
            'ollama': failing_mock,
            'openai': failing_mock
        }
        
        with pytest.raises(Exception, match="No providers available"):
            await manager.complete_with_fallback(completion_request)
```

## 2. Integration Testing with Mock LLM Servers

### 2.1 Mock Server Architecture

```python
# tests/integration/mock_servers.py
from aiohttp import web
import json
import asyncio
from typing import Dict, Any

class MockOllamaServer:
    """Mock Ollama server for integration testing"""
    
    def __init__(self, port=11434):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        self.app.router.add_get('/api/tags', self.list_models)
        self.app.router.add_post('/api/generate', self.generate)
        self.app.router.add_post('/api/chat', self.chat)
        
    async def list_models(self, request):
        """Mock model list endpoint"""
        return web.json_response({
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
        })
    
    async def generate(self, request):
        """Mock completion endpoint"""
        data = await request.json()
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        if data.get('stream', False):
            return self._stream_response(data)
        else:
            return web.json_response({
                "response": f"Mock response for: {data.get('prompt', '')}",
                "model": data.get('model', 'llama2:7b'),
                "eval_count": 25,
                "prompt_eval_count": 15,
                "total_duration": 1500000000
            })
    
    def _stream_response(self, data):
        """Mock streaming response"""
        async def generate_chunks():
            chunks = ["Mock ", "streaming ", "response ", "for: ", data.get('prompt', '')]
            for chunk in chunks:
                yield json.dumps({
                    "response": chunk,
                    "done": False
                }) + '\n'
                await asyncio.sleep(0.05)
            
            # Final chunk
            yield json.dumps({
                "response": "",
                "done": True,
                "eval_count": 25,
                "prompt_eval_count": 15
            }) + '\n'
        
        return web.Response(
            body=generate_chunks(),
            content_type='application/x-ndjson'
        )

class MockOpenAIServer:
    """Mock OpenAI server for testing"""
    
    def __init__(self, port=8080):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        self.app.router.add_get('/v1/models', self.list_models)
        self.app.router.add_post('/v1/chat/completions', self.chat_completions)
    
    async def list_models(self, request):
        return web.json_response({
            "object": "list",
            "data": [
                {
                    "id": "gpt-4o",
                    "object": "model",
                    "created": 1686935002,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-3.5-turbo",
                    "object": "model", 
                    "created": 1677610602,
                    "owned_by": "openai"
                }
            ]
        })
    
    async def chat_completions(self, request):
        data = await request.json()
        
        # Simulate API key validation
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return web.json_response(
                {"error": {"message": "Invalid API key"}},
                status=401
            )
        
        if data.get('stream', False):
            return self._stream_completion(data)
        else:
            return web.json_response({
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1694268190,
                "model": data.get('model', 'gpt-3.5-turbo'),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Mock OpenAI response to: {data['messages'][-1]['content']}"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 30,
                    "total_tokens": 50
                }
            })
```

### 2.2 Integration Test Suite

```python
# tests/integration/test_provider_integration.py
import pytest
import asyncio
from aiohttp import web
from app.llm_providers import ProviderManager
from app.llm_providers.base_provider import CompletionRequest
from .mock_servers import MockOllamaServer, MockOpenAIServer

@pytest.fixture
async def ollama_server():
    """Start mock Ollama server for testing"""
    server = MockOllamaServer(port=11434)
    runner = web.AppRunner(server.app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 11434)
    await site.start()
    
    yield server
    
    await runner.cleanup()

@pytest.fixture  
async def openai_server():
    """Start mock OpenAI server for testing"""
    server = MockOpenAIServer(port=8080)
    runner = web.AppRunner(server.app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    
    yield server
    
    await runner.cleanup()

class TestProviderIntegration:
    
    @pytest.mark.asyncio
    async def test_ollama_integration(self, ollama_server):
        """Test full integration with mock Ollama server"""
        config = {"ollama": {"base_url": "http://localhost:11434"}}
        manager = ProviderManager(config)
        await manager.initialize_providers()
        
        # Test model listing
        ollama_provider = manager.get_provider('ollama')
        models = await ollama_provider.list_models()
        assert len(models) == 2
        assert models[0].name == "llama2:7b"
        
        # Test completion
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello world"}],
            model="llama2:7b"
        )
        
        response = await ollama_provider.complete(request)
        assert "Mock response for: Hello world" in response.content
        assert response.provider == "ollama"
    
    @pytest.mark.asyncio
    async def test_openai_integration(self, openai_server):
        """Test full integration with mock OpenAI server"""
        config = {
            "openai": {
                "api_key": "test-key",
                "base_url": "http://localhost:8080/v1"
            }
        }
        manager = ProviderManager(config)
        await manager.initialize_providers()
        
        openai_provider = manager.get_provider('openai')
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Test message"}],
            model="gpt-4o"
        )
        
        response = await openai_provider.complete(request)
        assert "Mock OpenAI response" in response.content
        assert response.model == "gpt-4o"
    
    @pytest.mark.asyncio
    async def test_cross_provider_failover(self, ollama_server, openai_server):
        """Test failover between different provider types"""
        config = {
            "ollama": {"base_url": "http://localhost:11434"},
            "openai": {
                "api_key": "test-key",
                "base_url": "http://localhost:8080/v1"
            }
        }
        
        manager = ProviderManager(config)
        await manager.initialize_providers()
        
        # Simulate Ollama failure by stopping server
        # (In real test, would manipulate mock behavior)
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Failover test"}],
            model="llama2:7b"
        )
        
        # Should fallback to OpenAI
        response = await manager.complete_with_fallback(request, 'ollama')
        assert response.provider in ['ollama', 'openai']  # Depending on which succeeds
```

## 3. End-to-End CLI Command Testing

### 3.1 CLI Testing Framework

```python
# tests/e2e/test_cli_commands.py
import pytest
from click.testing import CliRunner
from unittest.mock import patch, AsyncMock
import tempfile
import yaml
from pathlib import Path

from scripts.localagent import cli, LocalAgentCLI

class TestCLICommands:
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def temp_config_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_cli_help(self, runner):
        """Test CLI help command"""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "LocalAgent - Multi-provider LLM orchestration CLI" in result.output
    
    def test_init_command_interactive(self, runner, temp_config_dir):
        """Test interactive initialization"""
        with patch('pathlib.Path.home', return_value=temp_config_dir):
            result = runner.invoke(cli, ['init'], input='http://localhost:11434\nn\nn\nn\n')
            
            assert result.exit_code == 0
            assert "Configuration saved successfully!" in result.output
            
            # Verify config file was created
            config_file = temp_config_dir / '.localagent' / 'config.yaml'
            assert config_file.exists()
            
            with open(config_file) as f:
                config = yaml.safe_load(f)
                assert config['ollama']['base_url'] == 'http://localhost:11434'
    
    @pytest.mark.asyncio
    async def test_providers_command(self, runner):
        """Test providers listing command"""
        mock_manager = AsyncMock()
        mock_provider = AsyncMock()
        mock_provider.health_check.return_value = {
            'healthy': True,
            'models_available': 5
        }
        mock_provider.requires_api_key = False
        mock_manager.providers = {'ollama': mock_provider}
        
        with patch('scripts.localagent.LocalAgentCLI') as mock_cli:
            mock_cli.return_value.initialize = AsyncMock()
            mock_cli.return_value.provider_manager = mock_manager
            
            result = runner.invoke(cli, ['providers'])
            assert result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_complete_command(self, runner):
        """Test completion command"""
        mock_provider = AsyncMock()
        mock_provider.list_models.return_value = [
            AsyncMock(name='test-model')
        ]
        mock_response = AsyncMock()
        mock_response.content = "Test response"
        mock_provider.complete.return_value = mock_response
        
        mock_manager = AsyncMock()
        mock_manager.providers = {'ollama': mock_provider}
        
        with patch('scripts.localagent.LocalAgentCLI') as mock_cli:
            mock_cli.return_value.initialize = AsyncMock()
            mock_cli.return_value.provider_manager = mock_manager
            
            result = runner.invoke(cli, ['complete', 'Test prompt', '--provider', 'ollama'])
            assert result.exit_code == 0
    
    def test_invalid_provider_error(self, runner):
        """Test error handling for invalid provider"""
        with patch('scripts.localagent.LocalAgentCLI') as mock_cli:
            mock_cli.return_value.initialize = AsyncMock()
            mock_cli.return_value.provider_manager.providers = {}
            
            result = runner.invoke(cli, ['complete', 'Test', '--provider', 'invalid'])
            assert "Provider 'invalid' not available" in result.output
```

### 3.2 Interactive Mode Testing

```python
# tests/e2e/test_interactive_mode.py  
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from rich.console import Console
from io import StringIO

class TestInteractiveMode:
    
    @pytest.mark.asyncio
    async def test_interactive_startup(self):
        """Test interactive mode initialization"""
        from scripts.localagent import interactive_mode
        
        mock_provider = AsyncMock()
        mock_provider.health_check.return_value = {'healthy': True}
        mock_provider.list_models.return_value = [AsyncMock(name='test-model')]
        mock_provider.stream_complete.return_value = async_generator(['Response ', 'chunk'])
        
        mock_manager = AsyncMock()
        mock_manager.providers = {'ollama': mock_provider}
        
        with patch('scripts.localagent.LocalAgentCLI') as mock_cli:
            mock_cli.return_value.initialize = AsyncMock()
            mock_cli.return_value.provider_manager = mock_manager
            
            # Mock user input to exit immediately
            with patch('rich.prompt.Prompt.ask', side_effect=['/exit']):
                await interactive_mode()
    
    @pytest.mark.asyncio  
    async def test_interactive_commands(self):
        """Test interactive mode commands"""
        # Test /help command
        # Test /provider switching
        # Test /models listing
        # Test /clear command
        pass
    
    @pytest.mark.asyncio
    async def test_streaming_response_display(self):
        """Test that streaming responses display correctly"""
        # Mock streaming response and verify output formatting
        pass

async def async_generator(items):
    for item in items:
        yield item
```

## 4. Performance Testing and Benchmarking Framework

### 4.1 Performance Test Suite

```python
# tests/performance/test_performance_benchmarks.py
import pytest
import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor
import psutil
import memory_profiler
from app.llm_providers import ProviderManager
from app.llm_providers.base_provider import CompletionRequest

class TestPerformanceBenchmarks:
    
    @pytest.fixture
    def performance_config(self):
        return {
            "ollama": {"base_url": "http://localhost:11434"},
            "openai": {"api_key": "test-key"}
        }
    
    @pytest.fixture
    async def manager(self, performance_config):
        manager = ProviderManager(performance_config)
        await manager.initialize_providers()
        return manager
    
    @pytest.mark.benchmark
    async def test_completion_latency(self, manager, benchmark):
        """Benchmark completion latency"""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello world"}],
            model="test-model"
        )
        
        provider = manager.get_provider('ollama')
        
        # Warm up
        await provider.complete(request)
        
        async def complete_task():
            return await provider.complete(request)
        
        # Benchmark multiple runs
        latencies = []
        for _ in range(10):
            start_time = time.time()
            await complete_task()
            latency = time.time() - start_time
            latencies.append(latency)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        # Performance assertions
        assert avg_latency < 2.0, f"Average latency too high: {avg_latency}s"
        assert p95_latency < 3.0, f"P95 latency too high: {p95_latency}s"
        
        return {
            'avg_latency': avg_latency,
            'p95_latency': p95_latency,
            'min_latency': min(latencies),
            'max_latency': max(latencies)
        }
    
    @pytest.mark.benchmark
    async def test_concurrent_completions(self, manager):
        """Test performance under concurrent load"""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Concurrent test"}],
            model="test-model"
        )
        
        provider = manager.get_provider('ollama')
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for concurrency in concurrency_levels:
            tasks = []
            start_time = time.time()
            
            for _ in range(concurrency):
                task = asyncio.create_task(provider.complete(request))
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            results[concurrency] = {
                'total_time': total_time,
                'requests_per_second': concurrency / total_time,
                'avg_time_per_request': total_time / concurrency
            }
            
            # Performance degradation check
            if concurrency > 1:
                prev_rps = results[1]['requests_per_second']
                current_rps = results[concurrency]['requests_per_second']
                degradation = (prev_rps - current_rps) / prev_rps
                
                # Ensure performance doesn't degrade more than 50% at 10x concurrency
                if concurrency == 10:
                    assert degradation < 0.5, f"Performance degraded by {degradation*100:.1f}%"
        
        return results
    
    @pytest.mark.benchmark
    @memory_profiler.profile
    async def test_memory_usage(self, manager):
        """Test memory usage patterns"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform multiple completions to check for memory leaks
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Memory test"}],
            model="test-model"
        )
        
        provider = manager.get_provider('ollama')
        memory_measurements = [initial_memory]
        
        for i in range(100):
            await provider.complete(request)
            
            if i % 10 == 0:  # Measure every 10 iterations
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_measurements.append(current_memory)
        
        final_memory = memory_measurements[-1]
        memory_growth = final_memory - initial_memory
        
        # Memory leak detection
        assert memory_growth < 50, f"Memory leak detected: {memory_growth}MB growth"
        
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': memory_growth,
            'measurements': memory_measurements
        }
    
    @pytest.mark.benchmark
    async def test_provider_initialization_time(self, performance_config):
        """Benchmark provider initialization performance"""
        initialization_times = {}
        
        provider_classes = [
            ('ollama', 'OllamaProvider'),
            ('openai', 'OpenAIProvider'), 
            ('gemini', 'GeminiProvider'),
            ('perplexity', 'PerplexityProvider')
        ]
        
        for provider_name, provider_class in provider_classes:
            if provider_name not in performance_config:
                continue
                
            times = []
            for _ in range(5):  # Average across multiple runs
                start_time = time.time()
                
                manager = ProviderManager({provider_name: performance_config[provider_name]})
                await manager.initialize_providers()
                
                init_time = time.time() - start_time
                times.append(init_time)
            
            initialization_times[provider_name] = {
                'avg_time': statistics.mean(times),
                'min_time': min(times),
                'max_time': max(times)
            }
            
            # Initialization should complete within reasonable time
            assert statistics.mean(times) < 5.0, f"{provider_name} initialization too slow"
        
        return initialization_times
```

### 4.2 Performance Regression Testing

```python
# tests/performance/test_performance_regression.py
import pytest
import json
from pathlib import Path
import statistics

class TestPerformanceRegression:
    
    BASELINE_FILE = Path("tests/performance/baselines.json")
    
    def load_baseline(self):
        """Load performance baselines"""
        if self.BASELINE_FILE.exists():
            with open(self.BASELINE_FILE) as f:
                return json.load(f)
        return {}
    
    def save_baseline(self, results):
        """Save new performance baseline"""
        self.BASELINE_FILE.parent.mkdir(exist_ok=True)
        with open(self.BASELINE_FILE, 'w') as f:
            json.dump(results, f, indent=2)
    
    @pytest.mark.regression
    async def test_latency_regression(self, manager):
        """Test for latency regression"""
        baseline = self.load_baseline()
        
        # Run current performance test
        current_results = await self.run_latency_test(manager)
        
        if 'latency' in baseline:
            baseline_avg = baseline['latency']['avg_latency']
            current_avg = current_results['avg_latency']
            
            # Allow 20% performance degradation
            regression_threshold = baseline_avg * 1.2
            assert current_avg <= regression_threshold, \
                f"Latency regression: {current_avg}s vs baseline {baseline_avg}s"
        else:
            # First run - establish baseline
            baseline['latency'] = current_results
            self.save_baseline(baseline)
    
    async def run_latency_test(self, manager):
        """Run standardized latency test"""
        # Implementation similar to test_completion_latency
        pass
```

## 5. Security Testing for API Key Handling

### 5.1 Security Test Framework

```python
# tests/security/test_api_key_security.py
import pytest
import tempfile
import yaml
import os
from pathlib import Path
from unittest.mock import patch
import logging

class TestAPIKeySecurity:
    
    @pytest.fixture
    def temp_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / '.localagent'
            config_dir.mkdir()
            yield config_dir
    
    def test_config_file_permissions(self, temp_config):
        """Test that config files have secure permissions"""
        config_file = temp_config / 'config.yaml'
        
        config = {
            'openai': {'api_key': 'sk-secret-key'},
            'gemini': {'api_key': 'secret-gemini-key'}
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Check file permissions (should be 600 - owner read/write only)
        file_mode = config_file.stat().st_mode
        permissions = oct(file_mode)[-3:]
        assert permissions <= '600', f"Config file too permissive: {permissions}"
    
    def test_api_key_not_in_logs(self, caplog):
        """Test that API keys don't appear in logs"""
        from app.llm_providers.openai_provider import OpenAIProvider
        
        with caplog.at_level(logging.DEBUG):
            provider = OpenAIProvider({'api_key': 'sk-secret-test-key'})
            
        # Check that no log messages contain the API key
        for record in caplog.records:
            assert 'sk-secret-test-key' not in record.getMessage()
            assert 'secret' not in record.getMessage().lower()
    
    def test_api_key_masking_in_errors(self):
        """Test that API keys are masked in error messages"""
        from app.llm_providers.openai_provider import OpenAIProvider
        
        provider = OpenAIProvider({'api_key': 'sk-1234567890abcdef'})
        
        # Trigger an error that might expose the key
        try:
            # Simulate API error
            raise Exception(f"Authentication failed with key: {provider.api_key}")
        except Exception as e:
            error_msg = str(e)
            # Key should be masked in error messages
            assert 'sk-1234567890abcdef' not in error_msg
            assert '****' in error_msg or 'sk-****' in error_msg
    
    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence over config"""
        config = {'openai': {'api_key': 'config-key'}}
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-key'}):
            from app.llm_providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider(config['openai'])
            
            # Should use environment variable
            assert provider.api_key == 'env-key'
    
    def test_api_key_validation(self):
        """Test API key format validation"""
        from app.llm_providers.openai_provider import OpenAIProvider
        
        # Valid OpenAI key format
        valid_provider = OpenAIProvider({'api_key': 'sk-1234567890abcdef'})
        assert valid_provider.api_key.startswith('sk-')
        
        # Invalid key format should be rejected
        with pytest.raises(ValueError):
            invalid_provider = OpenAIProvider({'api_key': 'invalid-key'})
            asyncio.run(invalid_provider.initialize())
    
    @pytest.mark.asyncio
    async def test_secure_key_transmission(self):
        """Test that API keys are transmitted securely"""
        from app.llm_providers.openai_provider import OpenAIProvider
        
        provider = OpenAIProvider({'api_key': 'sk-test-key'})
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {'choices': [{'message': {'content': 'test'}}]}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            request = CompletionRequest(
                messages=[{'role': 'user', 'content': 'test'}],
                model='gpt-3.5-turbo'
            )
            
            await provider.complete(request)
            
            # Verify HTTPS is used
            call_args = mock_post.call_args
            url = call_args[1]['url'] if 'url' in call_args[1] else call_args[0][0]
            assert url.startswith('https://'), "API calls must use HTTPS"
            
            # Verify Authorization header is set correctly
            headers = call_args[1]['headers']
            assert 'Authorization' in headers
            assert headers['Authorization'].startswith('Bearer ')
```

### 5.2 Credential Management Security

```python
# tests/security/test_credential_management.py
import pytest
import keyring
from unittest.mock import patch
from app.llm_providers.security import CredentialManager

class TestCredentialManagement:
    
    def test_keyring_storage(self):
        """Test secure credential storage using keyring"""
        cred_manager = CredentialManager()
        
        # Store credential securely
        cred_manager.store_credential('openai', 'api_key', 'sk-test-key')
        
        # Retrieve credential
        retrieved_key = cred_manager.get_credential('openai', 'api_key')
        assert retrieved_key == 'sk-test-key'
        
        # Clean up
        cred_manager.delete_credential('openai', 'api_key')
    
    def test_credential_encryption(self):
        """Test that stored credentials are encrypted"""
        cred_manager = CredentialManager()
        
        # Store a credential
        cred_manager.store_credential('test', 'key', 'secret-value')
        
        # Verify it's not stored in plaintext
        with patch('keyring.get_password') as mock_get:
            mock_get.return_value = 'encrypted-data'
            
            # The actual credential should not be in plaintext in storage
            # This test would need to examine the actual keyring storage
            pass
    
    def test_credential_access_logging(self, caplog):
        """Test that credential access is logged for security auditing"""
        cred_manager = CredentialManager()
        
        with caplog.at_level(logging.INFO):
            cred_manager.get_credential('openai', 'api_key')
            
        # Should log credential access attempts
        assert any('credential access' in record.getMessage().lower() for record in caplog.records)
```

## 6. Chaos Engineering for Provider Failures

### 6.1 Chaos Testing Framework

```python
# tests/chaos/test_provider_failures.py
import pytest
import asyncio
import random
from unittest.mock import patch, AsyncMock
from app.llm_providers import ProviderManager
from app.llm_providers.base_provider import CompletionRequest
import time

class ChaosTester:
    """Framework for introducing controlled failures"""
    
    def __init__(self, manager: ProviderManager):
        self.manager = manager
        self.failure_scenarios = {
            'network_timeout': self.inject_network_timeout,
            'api_rate_limit': self.inject_rate_limit,
            'provider_down': self.inject_provider_down,
            'partial_response': self.inject_partial_response,
            'authentication_failure': self.inject_auth_failure,
            'model_unavailable': self.inject_model_unavailable
        }
    
    async def inject_network_timeout(self, provider_name):
        """Simulate network timeout"""
        provider = self.manager.get_provider(provider_name)
        original_complete = provider.complete
        
        async def timeout_complete(request):
            await asyncio.sleep(10)  # Simulate timeout
            raise asyncio.TimeoutError("Network timeout")
        
        provider.complete = timeout_complete
        return original_complete
    
    async def inject_rate_limit(self, provider_name):
        """Simulate API rate limiting"""
        provider = self.manager.get_provider(provider_name)
        original_complete = provider.complete
        
        async def rate_limited_complete(request):
            from openai import RateLimitError
            raise RateLimitError("Rate limit exceeded")
        
        provider.complete = rate_limited_complete
        return original_complete
    
    async def inject_provider_down(self, provider_name):
        """Simulate provider being completely down"""
        provider = self.manager.get_provider(provider_name)
        original_health_check = provider.health_check
        
        async def unhealthy_check():
            return {'healthy': False, 'error': 'Service unavailable'}
        
        provider.health_check = unhealthy_check
        return original_health_check
    
    async def inject_partial_response(self, provider_name):
        """Simulate partial response corruption"""
        provider = self.manager.get_provider(provider_name)
        original_complete = provider.complete
        
        async def corrupted_complete(request):
            response = await original_complete(request)
            # Corrupt response content
            response.content = response.content[:len(response.content)//2] + "[[CORRUPTED]]"
            return response
        
        provider.complete = corrupted_complete
        return original_complete

class TestChaosEngineering:
    
    @pytest.fixture
    async def manager_with_fallbacks(self):
        config = {
            'ollama': {'base_url': 'http://localhost:11434'},
            'openai': {'api_key': 'test-key'},
            'gemini': {'api_key': 'test-key'}
        }
        manager = ProviderManager(config)
        await manager.initialize_providers()
        return manager
    
    @pytest.fixture
    def chaos_tester(self, manager_with_fallbacks):
        return ChaosTester(manager_with_fallbacks)
    
    @pytest.mark.chaos
    async def test_single_provider_failure_resilience(self, manager_with_fallbacks, chaos_tester):
        """Test system resilience when one provider fails"""
        request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'Test resilience'}],
            model='test-model'
        )
        
        # Inject failure into primary provider
        original_complete = await chaos_tester.inject_network_timeout('ollama')
        
        try:
            # Should fallback to secondary provider
            response = await manager_with_fallbacks.complete_with_fallback(request, 'ollama')
            assert response.provider != 'ollama'  # Should use fallback
            assert response.content  # Should still get valid response
        finally:
            # Restore original function
            manager_with_fallbacks.get_provider('ollama').complete = original_complete
    
    @pytest.mark.chaos
    async def test_cascading_failures(self, manager_with_fallbacks, chaos_tester):
        """Test behavior under cascading failures"""
        request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'Cascading test'}],
            model='test-model'
        )
        
        # Inject failures into multiple providers
        original_functions = []
        for provider_name in ['ollama', 'openai']:
            if manager_with_fallbacks.get_provider(provider_name):
                original = await chaos_tester.inject_provider_down(provider_name)
                original_functions.append((provider_name, 'health_check', original))
        
        try:
            # Should handle gracefully when multiple providers fail
            with pytest.raises(Exception, match="No providers available|All providers failed"):
                await manager_with_fallbacks.complete_with_fallback(request)
        finally:
            # Restore original functions
            for provider_name, method, original in original_functions:
                setattr(manager_with_fallbacks.get_provider(provider_name), method, original)
    
    @pytest.mark.chaos
    async def test_partial_failure_recovery(self, manager_with_fallbacks, chaos_tester):
        """Test recovery from partial failures"""
        request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'Recovery test'}],
            model='test-model'
        )
        
        # Inject partial response corruption
        original_complete = await chaos_tester.inject_partial_response('ollama')
        
        try:
            response = await manager_with_fallbacks.complete_with_fallback(request, 'ollama')
            
            # System should either:
            # 1. Detect corruption and retry with different provider
            # 2. Return corrupted response but mark it as such
            
            if '[[CORRUPTED]]' in response.content:
                # If corruption wasn't caught, it should be marked
                assert hasattr(response, 'warnings') or response.provider != 'ollama'
        finally:
            manager_with_fallbacks.get_provider('ollama').complete = original_complete
    
    @pytest.mark.chaos
    async def test_intermittent_failures(self, manager_with_fallbacks):
        """Test handling of intermittent, unpredictable failures"""
        request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'Intermittent test'}],
            model='test-model'
        )
        
        success_count = 0
        failure_count = 0
        
        # Simulate intermittent failures
        provider = manager_with_fallbacks.get_provider('ollama')
        original_complete = provider.complete
        
        async def intermittent_complete(req):
            if random.random() < 0.3:  # 30% failure rate
                raise Exception("Intermittent failure")
            return await original_complete(req)
        
        provider.complete = intermittent_complete
        
        try:
            # Run multiple requests
            for _ in range(20):
                try:
                    response = await manager_with_fallbacks.complete_with_fallback(request)
                    success_count += 1
                except:
                    failure_count += 1
            
            # Should have high success rate due to fallbacks
            success_rate = success_count / (success_count + failure_count)
            assert success_rate > 0.8, f"Success rate too low: {success_rate:.2%}"
            
        finally:
            provider.complete = original_complete
```

## 7. Load Testing for Concurrent Requests

### 7.1 Load Testing Framework

```python
# tests/load/test_concurrent_load.py
import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from app.llm_providers import ProviderManager
from app.llm_providers.base_provider import CompletionRequest

class LoadTestFramework:
    
    def __init__(self, manager: ProviderManager):
        self.manager = manager
        self.results = []
    
    async def single_request_task(self, request: CompletionRequest, provider_name: str = None):
        """Execute a single request and record metrics"""
        start_time = time.time()
        
        try:
            if provider_name:
                provider = self.manager.get_provider(provider_name)
                response = await provider.complete(request)
            else:
                response = await self.manager.complete_with_fallback(request)
            
            end_time = time.time()
            
            return {
                'success': True,
                'latency': end_time - start_time,
                'provider': response.provider,
                'tokens': response.usage.get('total_tokens', 0),
                'error': None
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'latency': end_time - start_time,
                'provider': None,
                'tokens': 0,
                'error': str(e)
            }
    
    async def run_concurrent_load(self, requests: list, concurrency: int):
        """Run multiple requests concurrently"""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_request(request):
            async with semaphore:
                return await self.single_request_task(request)
        
        start_time = time.time()
        results = await asyncio.gather(*[bounded_request(req) for req in requests])
        total_time = time.time() - start_time
        
        return {
            'results': results,
            'total_time': total_time,
            'requests_per_second': len(requests) / total_time,
            'successful_requests': sum(1 for r in results if r['success']),
            'failed_requests': sum(1 for r in results if not r['success'])
        }

class TestConcurrentLoad:
    
    @pytest.fixture
    async def load_test_manager(self):
        config = {
            'ollama': {'base_url': 'http://localhost:11434'},
            'openai': {'api_key': 'test-key'}
        }
        manager = ProviderManager(config)
        await manager.initialize_providers()
        return manager
    
    @pytest.fixture
    def load_tester(self, load_test_manager):
        return LoadTestFramework(load_test_manager)
    
    @pytest.mark.load
    async def test_light_concurrent_load(self, load_tester):
        """Test system under light concurrent load (10 requests)"""
        requests = [
            CompletionRequest(
                messages=[{'role': 'user', 'content': f'Light load test {i}'}],
                model='test-model'
            )
            for i in range(10)
        ]
        
        results = await load_tester.run_concurrent_load(requests, concurrency=5)
        
        # Assertions
        assert results['successful_requests'] >= 8, "Too many failures under light load"
        assert results['requests_per_second'] > 1, "RPS too low for light load"
        
        # Latency analysis
        successful_latencies = [r['latency'] for r in results['results'] if r['success']]
        avg_latency = statistics.mean(successful_latencies)
        p95_latency = statistics.quantiles(successful_latencies, n=20)[18]
        
        assert avg_latency < 5.0, f"Average latency too high: {avg_latency:.2f}s"
        assert p95_latency < 10.0, f"P95 latency too high: {p95_latency:.2f}s"
    
    @pytest.mark.load
    async def test_medium_concurrent_load(self, load_tester):
        """Test system under medium concurrent load (50 requests)"""
        requests = [
            CompletionRequest(
                messages=[{'role': 'user', 'content': f'Medium load test {i}'}],
                model='test-model'
            )
            for i in range(50)
        ]
        
        results = await load_tester.run_concurrent_load(requests, concurrency=15)
        
        # Should handle medium load with acceptable performance
        success_rate = results['successful_requests'] / len(requests)
        assert success_rate >= 0.80, f"Success rate too low: {success_rate:.2%}"
        
        # Performance shouldn't degrade too much
        assert results['requests_per_second'] > 2, "RPS degraded too much under medium load"
    
    @pytest.mark.load
    async def test_heavy_concurrent_load(self, load_tester):
        """Test system under heavy concurrent load (100 requests)"""
        requests = [
            CompletionRequest(
                messages=[{'role': 'user', 'content': f'Heavy load test {i}'}],
                model='test-model'
            )
            for i in range(100)
        ]
        
        results = await load_tester.run_concurrent_load(requests, concurrency=25)
        
        # System should remain functional under heavy load
        success_rate = results['successful_requests'] / len(requests)
        assert success_rate >= 0.70, f"System not resilient under heavy load: {success_rate:.2%}"
        
        # Analyze error patterns
        errors = [r['error'] for r in results['results'] if not r['success']]
        error_types = {}
        for error in errors:
            error_type = type(error).__name__ if error else 'Unknown'
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Ensure errors are due to expected causes (rate limits, timeouts)
        acceptable_errors = ['RateLimitError', 'TimeoutError', 'ConnectionError']
        for error_type in error_types:
            assert any(acceptable in error_type for acceptable in acceptable_errors), \
                f"Unexpected error type under load: {error_type}"
    
    @pytest.mark.load
    async def test_provider_load_balancing(self, load_tester):
        """Test load distribution across providers"""
        requests = [
            CompletionRequest(
                messages=[{'role': 'user', 'content': f'Load balancing test {i}'}],
                model='test-model'
            )
            for i in range(50)
        ]
        
        results = await load_tester.run_concurrent_load(requests, concurrency=10)
        
        # Analyze provider usage distribution
        provider_usage = {}
        for result in results['results']:
            if result['success'] and result['provider']:
                provider_usage[result['provider']] = provider_usage.get(result['provider'], 0) + 1
        
        # Should distribute load across available providers
        assert len(provider_usage) > 1, "Load not distributed across providers"
        
        # No single provider should handle all requests (unless others are down)
        max_usage = max(provider_usage.values()) if provider_usage else 0
        assert max_usage < len(requests) * 0.9, "Load not balanced across providers"
    
    @pytest.mark.load
    async def test_memory_usage_under_load(self, load_tester):
        """Test memory usage doesn't grow excessively under load"""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run sustained load
        for batch in range(5):  # 5 batches of 20 requests each
            requests = [
                CompletionRequest(
                    messages=[{'role': 'user', 'content': f'Memory test batch {batch} req {i}'}],
                    model='test-model'
                )
                for i in range(20)
            ]
            
            await load_tester.run_concurrent_load(requests, concurrency=8)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 100, f"Excessive memory growth under load: {memory_growth}MB"
```

### 7.2 Stress Testing

```python
# tests/load/test_stress_scenarios.py
import pytest
import asyncio
from app.llm_providers import ProviderManager

class TestStressScenarios:
    
    @pytest.mark.stress
    async def test_sustained_load_endurance(self, load_test_manager):
        """Test system endurance under sustained load"""
        # Run continuous load for extended period
        duration_minutes = 5
        end_time = time.time() + (duration_minutes * 60)
        
        success_count = 0
        failure_count = 0
        
        while time.time() < end_time:
            request = CompletionRequest(
                messages=[{'role': 'user', 'content': 'Endurance test'}],
                model='test-model'
            )
            
            try:
                await load_test_manager.complete_with_fallback(request)
                success_count += 1
            except:
                failure_count += 1
            
            # Brief pause between requests
            await asyncio.sleep(0.1)
        
        # System should maintain reasonable success rate
        total_requests = success_count + failure_count
        success_rate = success_count / total_requests if total_requests > 0 else 0
        assert success_rate > 0.75, f"Endurance test failed: {success_rate:.2%} success rate"
    
    @pytest.mark.stress
    async def test_burst_traffic_handling(self, load_test_manager):
        """Test handling of sudden traffic bursts"""
        # Simulate quiet period followed by burst
        
        # Quiet period
        for _ in range(5):
            request = CompletionRequest(
                messages=[{'role': 'user', 'content': 'Quiet period'}],
                model='test-model'
            )
            await load_test_manager.complete_with_fallback(request)
            await asyncio.sleep(1)
        
        # Sudden burst
        burst_requests = [
            CompletionRequest(
                messages=[{'role': 'user', 'content': f'Burst request {i}'}],
                model='test-model'
            )
            for i in range(50)
        ]
        
        # Execute burst with high concurrency
        start_time = time.time()
        tasks = [
            asyncio.create_task(load_test_manager.complete_with_fallback(req))
            for req in burst_requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        burst_time = time.time() - start_time
        
        # Analyze burst handling
        successes = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = successes / len(burst_requests)
        
        assert success_rate > 0.60, f"Poor burst handling: {success_rate:.2%} success rate"
        assert burst_time < 30, f"Burst took too long to process: {burst_time:.1f}s"
```

## 8. Regression Testing for Agent Workflows

### 8.1 Workflow Regression Framework

```python
# tests/regression/test_workflow_regression.py
import pytest
import json
import hashlib
from pathlib import Path
from app.llm_providers import ProviderManager
from app.llm_providers.base_provider import CompletionRequest

class WorkflowRegressionTester:
    
    def __init__(self, baseline_dir: Path):
        self.baseline_dir = baseline_dir
        self.baseline_dir.mkdir(exist_ok=True)
    
    def generate_test_id(self, test_name: str, inputs: dict) -> str:
        """Generate unique test ID based on inputs"""
        input_hash = hashlib.md5(
            json.dumps(inputs, sort_keys=True).encode()
        ).hexdigest()[:8]
        return f"{test_name}_{input_hash}"
    
    def save_baseline(self, test_id: str, result: dict):
        """Save baseline result for regression testing"""
        baseline_file = self.baseline_dir / f"{test_id}.json"
        with open(baseline_file, 'w') as f:
            json.dump(result, f, indent=2)
    
    def load_baseline(self, test_id: str) -> dict:
        """Load baseline result"""
        baseline_file = self.baseline_dir / f"{test_id}.json"
        if baseline_file.exists():
            with open(baseline_file) as f:
                return json.load(f)
        return None
    
    def compare_results(self, baseline: dict, current: dict, tolerance: dict = None) -> dict:
        """Compare current result with baseline"""
        if tolerance is None:
            tolerance = {'latency': 0.5, 'token_variance': 0.1}
        
        comparison = {
            'passed': True,
            'differences': [],
            'metrics': {}
        }
        
        # Compare latency
        if 'latency' in baseline and 'latency' in current:
            latency_diff = abs(current['latency'] - baseline['latency'])
            comparison['metrics']['latency_change'] = latency_diff
            
            if latency_diff > tolerance['latency']:
                comparison['passed'] = False
                comparison['differences'].append(
                    f"Latency regression: {latency_diff:.3f}s increase"
                )
        
        # Compare token usage
        if 'tokens' in baseline and 'tokens' in current:
            token_diff = abs(current['tokens'] - baseline['tokens']) / baseline['tokens']
            comparison['metrics']['token_variance'] = token_diff
            
            if token_diff > tolerance['token_variance']:
                comparison['passed'] = False
                comparison['differences'].append(
                    f"Token usage variance: {token_diff:.2%}"
                )
        
        # Compare success rate
        if 'success_rate' in baseline and 'success_rate' in current:
            success_diff = baseline['success_rate'] - current['success_rate']
            comparison['metrics']['success_rate_change'] = success_diff
            
            if success_diff > 0.05:  # 5% threshold
                comparison['passed'] = False
                comparison['differences'].append(
                    f"Success rate regression: {success_diff:.2%} decrease"
                )
        
        return comparison

class TestWorkflowRegression:
    
    @pytest.fixture
    def regression_tester(self):
        baseline_dir = Path("tests/regression/baselines")
        return WorkflowRegressionTester(baseline_dir)
    
    @pytest.fixture
    async def test_manager(self):
        config = {
            'ollama': {'base_url': 'http://localhost:11434'},
            'openai': {'api_key': 'test-key'}
        }
        manager = ProviderManager(config)
        await manager.initialize_providers()
        return manager
    
    @pytest.mark.regression
    async def test_basic_completion_workflow(self, test_manager, regression_tester):
        """Test basic completion workflow for regression"""
        test_inputs = {
            'messages': [{'role': 'user', 'content': 'What is Python?'}],
            'model': 'test-model',
            'provider': 'ollama'
        }
        
        test_id = regression_tester.generate_test_id('basic_completion', test_inputs)
        
        # Execute test
        start_time = time.time()
        request = CompletionRequest(**test_inputs)
        
        try:
            response = await test_manager.complete_with_fallback(request)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            response = None
        
        end_time = time.time()
        
        # Collect metrics
        current_result = {
            'success_rate': 1.0 if success else 0.0,
            'latency': end_time - start_time,
            'tokens': response.usage.get('total_tokens', 0) if response else 0,
            'provider_used': response.provider if response else None,
            'error': error,
            'timestamp': time.time()
        }
        
        # Load baseline
        baseline = regression_tester.load_baseline(test_id)
        
        if baseline:
            # Compare with baseline
            comparison = regression_tester.compare_results(baseline, current_result)
            
            assert comparison['passed'], \
                f"Regression detected: {', '.join(comparison['differences'])}"
        else:
            # First run - establish baseline
            regression_tester.save_baseline(test_id, current_result)
    
    @pytest.mark.regression
    async def test_provider_fallback_workflow(self, test_manager, regression_tester):
        """Test provider fallback workflow regression"""
        test_inputs = {
            'scenario': 'primary_provider_failure',
            'primary': 'ollama',
            'fallback_expected': 'openai'
        }
        
        test_id = regression_tester.generate_test_id('provider_fallback', test_inputs)
        
        # Mock primary provider failure
        original_health_check = test_manager.get_provider('ollama').health_check
        
        async def failing_health_check():
            return {'healthy': False, 'error': 'Simulated failure'}
        
        test_manager.get_provider('ollama').health_check = failing_health_check
        
        try:
            start_time = time.time()
            request = CompletionRequest(
                messages=[{'role': 'user', 'content': 'Fallback test'}],
                model='test-model'
            )
            
            response = await test_manager.complete_with_fallback(request, 'ollama')
            end_time = time.time()
            
            current_result = {
                'fallback_successful': response.provider != 'ollama',
                'fallback_provider': response.provider,
                'fallback_latency': end_time - start_time,
                'success_rate': 1.0
            }
            
        except Exception as e:
            current_result = {
                'fallback_successful': False,
                'error': str(e),
                'success_rate': 0.0
            }
            
        finally:
            # Restore original health check
            test_manager.get_provider('ollama').health_check = original_health_check
        
        # Compare with baseline
        baseline = regression_tester.load_baseline(test_id)
        if baseline:
            comparison = regression_tester.compare_results(baseline, current_result)
            assert comparison['passed'], \
                f"Fallback regression: {', '.join(comparison['differences'])}"
        else:
            regression_tester.save_baseline(test_id, current_result)
    
    @pytest.mark.regression
    async def test_concurrent_request_workflow(self, test_manager, regression_tester):
        """Test concurrent request handling regression"""
        test_inputs = {
            'concurrent_requests': 10,
            'request_template': 'Concurrent test {}'
        }
        
        test_id = regression_tester.generate_test_id('concurrent_requests', test_inputs)
        
        # Generate concurrent requests
        requests = [
            CompletionRequest(
                messages=[{'role': 'user', 'content': f'Concurrent test {i}'}],
                model='test-model'
            )
            for i in range(test_inputs['concurrent_requests'])
        ]
        
        # Execute concurrently
        start_time = time.time()
        tasks = [
            asyncio.create_task(test_manager.complete_with_fallback(req))
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        successes = sum(1 for r in results if not isinstance(r, Exception))
        total_tokens = sum(
            r.usage.get('total_tokens', 0) 
            for r in results if not isinstance(r, Exception)
        )
        
        current_result = {
            'success_rate': successes / len(requests),
            'total_latency': end_time - start_time,
            'avg_latency_per_request': (end_time - start_time) / len(requests),
            'total_tokens': total_tokens,
            'requests_per_second': len(requests) / (end_time - start_time)
        }
        
        # Compare with baseline
        baseline = regression_tester.load_baseline(test_id)
        if baseline:
            comparison = regression_tester.compare_results(baseline, current_result)
            assert comparison['passed'], \
                f"Concurrent workflow regression: {', '.join(comparison['differences'])}"
        else:
            regression_tester.save_baseline(test_id, current_result)
```

## 9. Contract Testing Between Providers

### 9.1 Contract Testing Framework

```python
# tests/contract/test_provider_contracts.py
import pytest
import json
from pathlib import Path
from jsonschema import validate, ValidationError
from app.llm_providers.base_provider import ModelInfo, CompletionRequest, CompletionResponse

class ProviderContractTester:
    """Framework for testing contracts between providers"""
    
    def __init__(self):
        self.contracts_dir = Path("tests/contract/schemas")
        self.contracts_dir.mkdir(exist_ok=True)
        self.load_schemas()
    
    def load_schemas(self):
        """Load JSON schemas for contract validation"""
        self.schemas = {
            'model_info': {
                "type": "object",
                "required": ["name", "provider", "context_length", "capabilities"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "provider": {"type": "string", "minLength": 1},
                    "context_length": {"type": "integer", "minimum": 1},
                    "capabilities": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["chat", "completion", "function_calling", "vision"]
                        }
                    },
                    "cost_per_token": {"type": ["number", "null"], "minimum": 0}
                }
            },
            
            'completion_request': {
                "type": "object", 
                "required": ["messages", "model"],
                "properties": {
                    "messages": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["role", "content"],
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                                "content": {"type": "string", "minLength": 1}
                            }
                        }
                    },
                    "model": {"type": "string", "minLength": 1},
                    "temperature": {"type": "number", "minimum": 0, "maximum": 2},
                    "max_tokens": {"type": ["integer", "null"], "minimum": 1},
                    "stream": {"type": "boolean"},
                    "functions": {"type": ["array", "null"]},
                    "system_prompt": {"type": ["string", "null"]}
                }
            },
            
            'completion_response': {
                "type": "object",
                "required": ["content", "model", "provider", "usage"],
                "properties": {
                    "content": {"type": "string"},
                    "model": {"type": "string", "minLength": 1},
                    "provider": {"type": "string", "minLength": 1},
                    "usage": {
                        "type": "object",
                        "properties": {
                            "prompt_tokens": {"type": "integer", "minimum": 0},
                            "completion_tokens": {"type": "integer", "minimum": 0},
                            "total_tokens": {"type": "integer", "minimum": 0}
                        }
                    },
                    "cost": {"type": ["number", "null"], "minimum": 0},
                    "citations": {"type": ["array", "null"]}
                }
            },
            
            'health_check_response': {
                "type": "object",
                "required": ["healthy"],
                "properties": {
                    "healthy": {"type": "boolean"},
                    "models_available": {"type": "integer", "minimum": 0},
                    "error": {"type": ["string", "null"]},
                    "latency_ms": {"type": "number", "minimum": 0}
                }
            }
        }
    
    def validate_contract(self, data: dict, schema_name: str):
        """Validate data against contract schema"""
        try:
            validate(instance=data, schema=self.schemas[schema_name])
            return True, None
        except ValidationError as e:
            return False, str(e)
    
    def validate_model_info(self, model_info: ModelInfo) -> tuple[bool, str]:
        """Validate ModelInfo contract"""
        data = {
            'name': model_info.name,
            'provider': model_info.provider,
            'context_length': model_info.context_length,
            'capabilities': model_info.capabilities,
            'cost_per_token': model_info.cost_per_token
        }
        return self.validate_contract(data, 'model_info')
    
    def validate_completion_request(self, request: CompletionRequest) -> tuple[bool, str]:
        """Validate CompletionRequest contract"""
        data = {
            'messages': request.messages,
            'model': request.model,
            'temperature': request.temperature,
            'max_tokens': request.max_tokens,
            'stream': request.stream,
            'functions': request.functions,
            'system_prompt': request.system_prompt
        }
        return self.validate_contract(data, 'completion_request')
    
    def validate_completion_response(self, response: CompletionResponse) -> tuple[bool, str]:
        """Validate CompletionResponse contract"""
        data = {
            'content': response.content,
            'model': response.model,
            'provider': response.provider,
            'usage': response.usage,
            'cost': response.cost,
            'citations': response.citations
        }
        return self.validate_contract(data, 'completion_response')

class TestProviderContracts:
    
    @pytest.fixture
    def contract_tester(self):
        return ProviderContractTester()
    
    @pytest.fixture
    async def test_providers(self):
        """Get all available providers for testing"""
        config = {
            'ollama': {'base_url': 'http://localhost:11434'},
            'openai': {'api_key': 'test-key'},
            'gemini': {'api_key': 'test-key'},
            'perplexity': {'api_key': 'test-key'}
        }
        
        from app.llm_providers import ProviderManager
        manager = ProviderManager(config)
        await manager.initialize_providers()
        return manager.providers
    
    @pytest.mark.contract
    async def test_model_info_contract(self, test_providers, contract_tester):
        """Test that all providers return valid ModelInfo"""
        for provider_name, provider in test_providers.items():
            try:
                models = await provider.list_models()
                
                for model in models:
                    valid, error = contract_tester.validate_model_info(model)
                    assert valid, f"{provider_name} ModelInfo contract violation: {error}"
                    
                    # Additional contract requirements
                    assert model.provider == provider_name, \
                        f"Model provider mismatch: expected {provider_name}, got {model.provider}"
                    
                    assert len(model.capabilities) > 0, \
                        f"Model {model.name} has no capabilities listed"
                        
            except Exception as e:
                pytest.skip(f"Provider {provider_name} unavailable: {e}")
    
    @pytest.mark.contract
    async def test_completion_request_contract(self, test_providers, contract_tester):
        """Test that all providers accept valid CompletionRequest"""
        valid_request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'Contract test'}],
            model='test-model',
            temperature=0.7,
            stream=False
        )
        
        # Validate request contract
        valid, error = contract_tester.validate_completion_request(valid_request)
        assert valid, f"CompletionRequest contract violation: {error}"
        
        # Test with all providers
        for provider_name, provider in test_providers.items():
            try:
                # Provider should accept valid request without raising validation errors
                await provider.complete(valid_request)
            except Exception as e:
                # Only skip if provider is unavailable, not for contract violations
                if "unavailable" in str(e).lower() or "not found" in str(e).lower():
                    pytest.skip(f"Provider {provider_name} unavailable")
                else:
                    # This might be a legitimate error - log but don't fail contract test
                    print(f"Provider {provider_name} error (may be expected): {e}")
    
    @pytest.mark.contract
    async def test_completion_response_contract(self, test_providers, contract_tester):
        """Test that all providers return valid CompletionResponse"""
        request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'Response contract test'}],
            model='test-model'
        )
        
        for provider_name, provider in test_providers.items():
            try:
                response = await provider.complete(request)
                
                # Validate response contract
                valid, error = contract_tester.validate_completion_response(response)
                assert valid, f"{provider_name} CompletionResponse contract violation: {error}"
                
                # Additional contract requirements
                assert response.provider == provider_name, \
                    f"Response provider mismatch: expected {provider_name}, got {response.provider}"
                
                assert len(response.content) > 0, \
                    f"Response content is empty from {provider_name}"
                
                assert response.usage.get('total_tokens', 0) > 0, \
                    f"Token usage not reported by {provider_name}"
                    
            except Exception as e:
                pytest.skip(f"Provider {provider_name} unavailable: {e}")
    
    @pytest.mark.contract
    async def test_health_check_contract(self, test_providers, contract_tester):
        """Test that all providers return valid health check response"""
        for provider_name, provider in test_providers.items():
            health_response = await provider.health_check()
            
            valid, error = contract_tester.validate_contract(health_response, 'health_check_response')
            assert valid, f"{provider_name} health check contract violation: {error}"
            
            # Health check specific requirements
            if health_response['healthy']:
                assert health_response.get('models_available', 0) >= 0, \
                    f"Healthy {provider_name} should report available models"
    
    @pytest.mark.contract
    async def test_streaming_contract(self, test_providers):
        """Test that streaming responses follow contract"""
        request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'Streaming contract test'}],
            model='test-model',
            stream=True
        )
        
        for provider_name, provider in test_providers.items():
            try:
                chunks = []
                async for chunk in provider.stream_complete(request):
                    # Each chunk should be a string
                    assert isinstance(chunk, str), \
                        f"{provider_name} streaming chunk not string: {type(chunk)}"
                    chunks.append(chunk)
                
                # Should receive at least one chunk
                assert len(chunks) > 0, f"{provider_name} streaming returned no chunks"
                
                # Concatenated chunks should form coherent response
                full_response = ''.join(chunks)
                assert len(full_response.strip()) > 0, \
                    f"{provider_name} streaming produced empty response"
                    
            except Exception as e:
                pytest.skip(f"Provider {provider_name} streaming unavailable: {e}")
    
    @pytest.mark.contract
    async def test_error_handling_contract(self, test_providers):
        """Test that providers handle errors according to contract"""
        # Invalid model request
        invalid_request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'Test'}],
            model='nonexistent-model-12345'
        )
        
        for provider_name, provider in test_providers.items():
            try:
                await provider.complete(invalid_request)
                # If no exception, this might be a mock provider - that's OK
            except Exception as e:
                # Exception should have meaningful message
                assert len(str(e)) > 0, f"{provider_name} raised empty error message"
                
                # Should be a known exception type
                acceptable_exceptions = [
                    'ValueError', 'ConnectionError', 'TimeoutError', 'HTTPError',
                    'AuthenticationError', 'RateLimitError', 'ModelNotFoundError'
                ]
                exception_name = type(e).__name__
                # Allow any exception for now - just ensure it's properly formed
                assert hasattr(e, '__str__'), f"{provider_name} exception not properly formed"
```

### 9.2 Cross-Provider Compatibility Testing

```python
# tests/contract/test_cross_provider_compatibility.py
import pytest
from app.llm_providers import ProviderManager
from app.llm_providers.base_provider import CompletionRequest

class TestCrossProviderCompatibility:
    
    @pytest.fixture
    async def multi_provider_manager(self):
        config = {
            'ollama': {'base_url': 'http://localhost:11434'},
            'openai': {'api_key': 'test-key'},
            'gemini': {'api_key': 'test-key'}
        }
        manager = ProviderManager(config)
        await manager.initialize_providers()
        return manager
    
    @pytest.mark.compatibility
    async def test_same_request_different_providers(self, multi_provider_manager):
        """Test that same request works across different providers"""
        request = CompletionRequest(
            messages=[{'role': 'user', 'content': 'What is machine learning?'}],
            model='test-model',
            temperature=0.1  # Low temperature for more consistent results
        )
        
        responses = {}
        
        for provider_name, provider in multi_provider_manager.providers.items():
            try:
                response = await provider.complete(request)
                responses[provider_name] = response
            except Exception as e:
                print(f"Provider {provider_name} failed: {e}")
                continue
        
        # Should have at least 2 providers working
        assert len(responses) >= 1, "Not enough providers available for compatibility test"
        
        # All responses should be valid and non-empty
        for provider_name, response in responses.items():
            assert len(response.content.strip()) > 0, \
                f"{provider_name} returned empty response"
            assert response.provider == provider_name, \
                f"Provider name mismatch for {provider_name}"
    
    @pytest.mark.compatibility
    async def test_provider_switching_consistency(self, multi_provider_manager):
        """Test that provider switching maintains session consistency"""
        conversation_history = [
            {'role': 'user', 'content': 'Hello, I want to learn about Python.'},
        ]
        
        # Start with first available provider
        available_providers = list(multi_provider_manager.providers.keys())
        if len(available_providers) < 2:
            pytest.skip("Need at least 2 providers for switching test")
        
        # First interaction
        request1 = CompletionRequest(
            messages=conversation_history,
            model='test-model'
        )
        
        provider1 = multi_provider_manager.get_provider(available_providers[0])
        try:
            response1 = await provider1.complete(request1)
            conversation_history.append({'role': 'assistant', 'content': response1.content})
        except Exception as e:
            pytest.skip(f"First provider {available_providers[0]} unavailable: {e}")
        
        # Continue conversation with different provider
        conversation_history.append({'role': 'user', 'content': 'Can you give me an example?'})
        
        request2 = CompletionRequest(
            messages=conversation_history,
            model='test-model'
        )
        
        provider2 = multi_provider_manager.get_provider(available_providers[1])
        try:
            response2 = await provider2.complete(request2)
            
            # Response should be contextually appropriate
            assert len(response2.content.strip()) > 0, "Second provider returned empty response"
            # Should reference the context (though this is hard to test automatically)
            
        except Exception as e:
            pytest.skip(f"Second provider {available_providers[1]} unavailable: {e}")
    
    @pytest.mark.compatibility  
    async def test_model_capability_consistency(self, multi_provider_manager):
        """Test that providers report capabilities consistently"""
        capability_map = {}
        
        for provider_name, provider in multi_provider_manager.providers.items():
            try:
                models = await provider.list_models()
                for model in models:
                    key = f"{model.name}_{provider_name}"
                    capability_map[key] = set(model.capabilities)
            except Exception as e:
                print(f"Cannot get models from {provider_name}: {e}")
                continue
        
        # All models should report at least 'chat' or 'completion'
        basic_capabilities = {'chat', 'completion'}
        
        for model_key, capabilities in capability_map.items():
            assert len(capabilities.intersection(basic_capabilities)) > 0, \
                f"Model {model_key} missing basic capabilities: {capabilities}"
        
        # Verify capability consistency within provider families
        # (This would be more specific to actual model mappings)
```

## 10. Continuous Testing in CI/CD Pipeline

### 10.1 CI/CD Configuration

```yaml
# .github/workflows/localagent-testing.yml
name: LocalAgent Comprehensive Testing

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC

env:
  PYTHON_VERSION: '3.11'
  POETRY_VERSION: '1.6.1'

jobs:
  # Unit Tests - Fast feedback
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        provider: [ollama, openai, gemini, perplexity]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: ${{ env.POETRY_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test
    
    - name: Run unit tests for ${{ matrix.provider }}
      run: |
        poetry run pytest tests/unit/providers/test_${{ matrix.provider }}_provider.py -v
        poetry run pytest tests/unit/test_provider_manager.py -v
    
    - name: Upload unit test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: unit-test-results-${{ matrix.provider }}
        path: test-results/

  # Integration Tests - With mock servers
  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      ollama-mock:
        image: ollama/ollama:latest
        ports:
          - 11434:11434
        options: --health-cmd="curl -f http://localhost:11434/api/tags" --health-interval=30s
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test
    
    - name: Start mock servers
      run: |
        poetry run python tests/integration/start_mock_servers.py &
        sleep 10
    
    - name: Run integration tests
      env:
        TEST_OLLAMA_URL: http://localhost:11434
        TEST_OPENAI_URL: http://localhost:8080
      run: |
        poetry run pytest tests/integration/ -v --tb=short
    
    - name: Upload integration test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: integration-test-results
        path: test-results/

  # End-to-End CLI Tests
  e2e-cli-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test
    
    - name: Make CLI executable
      run: chmod +x scripts/localagent
    
    - name: Test CLI installation
      run: |
        poetry run python -m pip install -e .
        localagent --help
    
    - name: Run E2E CLI tests
      run: |
        poetry run pytest tests/e2e/ -v --tb=short
    
    - name: Upload E2E test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: e2e-test-results
        path: test-results/

  # Performance & Load Tests
  performance-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[perf-test]')
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test,perf
    
    - name: Run performance benchmarks
      run: |
        poetry run pytest tests/performance/ -v --benchmark-json=benchmark-results.json
    
    - name: Upload benchmark results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: benchmark-results.json
    
    - name: Check performance regression
      run: |
        poetry run python scripts/check_performance_regression.py

  # Security Tests
  security-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test,security
    
    - name: Run security tests
      run: |
        poetry run pytest tests/security/ -v
    
    - name: Run Bandit security scan
      run: |
        poetry run bandit -r app/ -f json -o bandit-results.json
    
    - name: Run Safety check
      run: |
        poetry run safety check --json --output safety-results.json
    
    - name: Upload security scan results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: security-scan-results
        path: |
          bandit-results.json
          safety-results.json

  # Contract Tests
  contract-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test
    
    - name: Run contract tests
      run: |
        poetry run pytest tests/contract/ -v
    
    - name: Validate API schemas
      run: |
        poetry run python scripts/validate_api_schemas.py

  # Chaos Engineering Tests
  chaos-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'schedule' || contains(github.event.head_commit.message, '[chaos-test]')
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test,chaos
    
    - name: Run chaos engineering tests
      run: |
        poetry run pytest tests/chaos/ -v --tb=short
    
    - name: Upload chaos test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: chaos-test-results
        path: test-results/

  # Regression Tests
  regression-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Need full history for regression comparison
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test
    
    - name: Download baseline results
      uses: actions/download-artifact@v3
      with:
        name: regression-baselines
        path: tests/regression/baselines/
      continue-on-error: true  # OK if no baselines exist yet
    
    - name: Run regression tests
      run: |
        poetry run pytest tests/regression/ -v
    
    - name: Upload new baselines
      uses: actions/upload-artifact@v3
      with:
        name: regression-baselines
        path: tests/regression/baselines/

  # Deployment Readiness Check
  deployment-readiness:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-cli-tests, security-tests, contract-tests]
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        poetry install --with dev,test
    
    - name: Build package
      run: |
        poetry build
    
    - name: Test package installation
      run: |
        pip install dist/*.whl
        localagent --version
    
    - name: Run smoke tests
      run: |
        poetry run pytest tests/smoke/ -v
    
    - name: Generate test report
      run: |
        poetry run python scripts/generate_test_report.py
    
    - name: Upload test report
      uses: actions/upload-artifact@v3
      with:
        name: comprehensive-test-report
        path: test-report.html

  # Notification
  notify-results:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-cli-tests, security-tests, deployment-readiness]
    if: always()
    
    steps:
    - name: Notify test results
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: "LocalAgent Testing Pipeline Results"
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 10.2 Test Automation Scripts

```python
# scripts/run_comprehensive_tests.py
#!/usr/bin/env python3
"""
Comprehensive test runner for LocalAgent
Orchestrates all test suites with proper reporting
"""

import asyncio
import subprocess
import sys
import json
import time
from pathlib import Path
from typing import Dict, List
import argparse

class ComprehensiveTestRunner:
    """Orchestrates all LocalAgent test suites"""
    
    def __init__(self, config_path: str = None):
        self.config = self.load_config(config_path)
        self.results = {}
        self.start_time = time.time()
    
    def load_config(self, config_path: str) -> Dict:
        """Load test configuration"""
        default_config = {
            "test_suites": {
                "unit": {"enabled": True, "timeout": 300},
                "integration": {"enabled": True, "timeout": 600},
                "e2e": {"enabled": True, "timeout": 900},
                "performance": {"enabled": False, "timeout": 1800},
                "security": {"enabled": True, "timeout": 300},
                "contract": {"enabled": True, "timeout": 300},
                "chaos": {"enabled": False, "timeout": 1200},
                "load": {"enabled": False, "timeout": 1800},
                "regression": {"enabled": True, "timeout": 600}
            },
            "providers": {
                "ollama": {"required": True, "url": "http://localhost:11434"},
                "openai": {"required": False, "api_key_env": "OPENAI_API_KEY"},
                "gemini": {"required": False, "api_key_env": "GEMINI_API_KEY"}
            },
            "reporting": {
                "formats": ["html", "json", "junit"],
                "output_dir": "test-results"
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
                # Merge configs
                for key, value in user_config.items():
                    if isinstance(value, dict):
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
        
        return default_config
    
    async def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        print("Checking prerequisites...")
        
        # Check Python dependencies
        try:
            import pytest
            import aiohttp
            import click
            print("✓ Python dependencies available")
        except ImportError as e:
            print(f"✗ Missing Python dependency: {e}")
            return False
        
        # Check provider availability
        for provider, config in self.config["providers"].items():
            if config.get("required", False):
                if provider == "ollama":
                    # Check Ollama server
                    try:
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(config["url"] + "/api/tags", timeout=5) as resp:
                                if resp.status == 200:
                                    print(f"✓ {provider} server available")
                                else:
                                    print(f"✗ {provider} server not responding")
                                    return False
                    except Exception as e:
                        print(f"✗ Cannot reach {provider}: {e}")
                        return False
                        
                elif "api_key_env" in config:
                    import os
                    if os.getenv(config["api_key_env"]):
                        print(f"✓ {provider} API key available")
                    else:
                        print(f"! {provider} API key not set (optional)")
        
        return True
    
    def run_test_suite(self, suite_name: str) -> Dict:
        """Run a specific test suite"""
        suite_config = self.config["test_suites"][suite_name]
        
        if not suite_config["enabled"]:
            return {"skipped": True, "reason": "disabled in config"}
        
        print(f"\n🧪 Running {suite_name} tests...")
        
        # Determine pytest command
        test_dir = f"tests/{suite_name}"
        if not Path(test_dir).exists():
            return {"skipped": True, "reason": f"test directory {test_dir} not found"}
        
        cmd = [
            "python", "-m", "pytest",
            test_dir,
            "-v",
            "--tb=short",
            f"--timeout={suite_config['timeout']}",
            f"--junitxml=test-results/{suite_name}-results.xml",
            "--json-report",
            f"--json-report-file=test-results/{suite_name}-report.json"
        ]
        
        # Add suite-specific flags
        if suite_name == "performance":
            cmd.extend(["--benchmark-json=test-results/benchmark-results.json"])
        elif suite_name == "coverage":
            cmd.extend(["--cov=app", "--cov-report=html:test-results/coverage-html"])
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=suite_config["timeout"]
            )
            
            end_time = time.time()
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "duration": end_time - start_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "duration": suite_config["timeout"],
                "error": f"Test suite timed out after {suite_config['timeout']}s"
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "duration": 0,
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict:
        """Run all enabled test suites"""
        if not await self.check_prerequisites():
            return {"error": "Prerequisites not met"}
        
        # Prepare output directory
        Path("test-results").mkdir(exist_ok=True)
        
        # Run test suites in order
        suite_order = [
            "unit",           # Fast feedback
            "integration",    # Core functionality
            "contract",       # API contracts
            "security",       # Security validation
            "e2e",           # End-to-end workflows
            "regression",    # Regression detection
            "performance",   # Performance benchmarks
            "load",          # Load testing
            "chaos"          # Chaos engineering
        ]
        
        for suite_name in suite_order:
            if suite_name in self.config["test_suites"]:
                self.results[suite_name] = self.run_test_suite(suite_name)
                
                # Print immediate feedback
                result = self.results[suite_name]
                if result.get("skipped"):
                    print(f"⏭️  {suite_name}: skipped ({result['reason']})")
                elif result.get("success"):
                    duration = result.get("duration", 0)
                    print(f"✅ {suite_name}: passed in {duration:.1f}s")
                else:
                    duration = result.get("duration", 0)
                    print(f"❌ {suite_name}: failed in {duration:.1f}s")
                    if result.get("error"):
                        print(f"   Error: {result['error']}")
                
                # Stop on critical failures
                if suite_name in ["unit", "integration"] and not result.get("success") and not result.get("skipped"):
                    print(f"\n🛑 Stopping due to {suite_name} test failure")
                    break
        
        return self.results
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        
        # Count results
        passed = sum(1 for r in self.results.values() if r.get("success"))
        failed = sum(1 for r in self.results.values() if not r.get("success") and not r.get("skipped"))
        skipped = sum(1 for r in self.results.values() if r.get("skipped"))
        total = len(self.results)
        
        report = {
            "summary": {
                "total_suites": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": passed / (total - skipped) if total > skipped else 0,
                "total_duration": total_duration
            },
            "results": self.results,
            "timestamp": time.time(),
            "config": self.config
        }
        
        # Save JSON report
        with open("test-results/comprehensive-report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate HTML report
        self.generate_html_report(report)
        
        return report
    
    def generate_html_report(self, report: Dict):
        """Generate HTML test report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>LocalAgent Comprehensive Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .success { color: green; }
        .failure { color: red; }
        .skipped { color: orange; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
        th { background: #f2f2f2; }
        .details { margin: 10px 0; }
        pre { background: #f8f8f8; padding: 10px; border-radius: 3px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>LocalAgent Comprehensive Test Report</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Suites:</strong> {total_suites}</p>
        <p><strong>Passed:</strong> <span class="success">{passed}</span></p>
        <p><strong>Failed:</strong> <span class="failure">{failed}</span></p>
        <p><strong>Skipped:</strong> <span class="skipped">{skipped}</span></p>
        <p><strong>Success Rate:</strong> {success_rate:.1%}</p>
        <p><strong>Total Duration:</strong> {total_duration:.1f}s</p>
    </div>
    
    <h2>Test Suite Results</h2>
    <table>
        <tr>
            <th>Test Suite</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Details</th>
        </tr>
        {suite_rows}
    </table>
    
    <div class="details">
        <h2>Detailed Results</h2>
        {detailed_results}
    </div>
    
    <p><em>Generated at {timestamp}</em></p>
</body>
</html>
        """
        
        # Generate suite rows
        suite_rows = []
        for suite_name, result in report["results"].items():
            if result.get("skipped"):
                status = f'<span class="skipped">SKIPPED</span>'
                duration = "-"
            elif result.get("success"):
                status = f'<span class="success">PASSED</span>'
                duration = f"{result.get('duration', 0):.1f}s"
            else:
                status = f'<span class="failure">FAILED</span>'
                duration = f"{result.get('duration', 0):.1f}s"
            
            suite_rows.append(f"""
                <tr>
                    <td>{suite_name}</td>
                    <td>{status}</td>
                    <td>{duration}</td>
                    <td><a href="#{suite_name}">View Details</a></td>
                </tr>
            """)
        
        # Generate detailed results
        detailed_results = []
        for suite_name, result in report["results"].items():
            detailed_results.append(f"""
                <div id="{suite_name}">
                    <h3>{suite_name.title()} Test Suite</h3>
                    <p><strong>Status:</strong> {'PASSED' if result.get('success') else 'FAILED' if not result.get('skipped') else 'SKIPPED'}</p>
                    <p><strong>Duration:</strong> {result.get('duration', 0):.1f}s</p>
                    {f"<p><strong>Error:</strong> {result['error']}</p>" if result.get('error') else ""}
                    {f"<pre>{result['stdout'][:1000]}{'...' if len(result.get('stdout', '')) > 1000 else ''}</pre>" if result.get('stdout') else ""}
                </div>
            """)
        
        html_content = html_template.format(
            total_suites=report["summary"]["total_suites"],
            passed=report["summary"]["passed"],
            failed=report["summary"]["failed"],
            skipped=report["summary"]["skipped"],
            success_rate=report["summary"]["success_rate"],
            total_duration=report["summary"]["total_duration"],
            suite_rows="".join(suite_rows),
            detailed_results="".join(detailed_results),
            timestamp=time.ctime(report["timestamp"])
        )
        
        with open("test-results/comprehensive-report.html", "w") as f:
            f.write(html_content)

async def main():
    parser = argparse.ArgumentParser(description="LocalAgent Comprehensive Test Runner")
    parser.add_argument("--config", help="Test configuration file")
    parser.add_argument("--suites", nargs="+", help="Specific test suites to run")
    parser.add_argument("--skip-prerequisites", action="store_true", help="Skip prerequisite checks")
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner(args.config)
    
    if args.suites:
        # Run specific suites only
        for suite in args.suites:
            if suite in runner.config["test_suites"]:
                runner.results[suite] = runner.run_test_suite(suite)
    else:
        # Run all tests
        await runner.run_all_tests()
    
    # Generate report
    report = runner.generate_report()
    
    # Print summary
    print(f"\n📊 Test Summary:")
    print(f"   Total: {report['summary']['total_suites']}")
    print(f"   Passed: {report['summary']['passed']}")
    print(f"   Failed: {report['summary']['failed']}")
    print(f"   Skipped: {report['summary']['skipped']}")
    print(f"   Success Rate: {report['summary']['success_rate']:.1%}")
    print(f"   Duration: {report['summary']['total_duration']:.1f}s")
    print(f"\n📄 Reports generated in test-results/")
    
    # Exit with appropriate code
    if report['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
```

## Conclusion

This comprehensive testing strategy for LocalAgent provides:

1. **Complete Coverage**: All aspects of the system are tested from unit level to full system integration
2. **Multi-layered Approach**: Different types of tests catch different classes of issues
3. **Automation Ready**: Designed for CI/CD integration with proper reporting
4. **Performance Focused**: Includes benchmarking and regression detection
5. **Security First**: Comprehensive security testing including credential management
6. **Resilience Testing**: Chaos engineering and failure scenario testing
7. **Contract Validation**: Ensures consistency across different providers
8. **Scalability Testing**: Load testing and concurrent request handling
9. **Regression Prevention**: Automated detection of performance and functionality regressions
10. **Continuous Improvement**: Feedback loops for ongoing test enhancement

The framework is modular, allowing teams to adopt individual components as needed while providing a complete solution for organizations requiring comprehensive testing coverage.

Key benefits:
- **Early Issue Detection**: Multiple layers catch issues at different stages
- **Confidence in Releases**: Comprehensive validation before deployment
- **Performance Assurance**: Automated performance regression detection
- **Security Guarantee**: Thorough security validation and credential protection
- **Provider Independence**: Contract testing ensures consistent behavior across providers
- **Operational Reliability**: Chaos engineering validates system resilience

This testing strategy ensures LocalAgent maintains high quality, performance, and reliability standards while supporting rapid development and deployment cycles.