"""
Enhanced Ollama Provider for LocalAgent
Production-ready provider with full resilience patterns:
- Connection pooling for efficient HTTP session management
- Rate limiting to prevent API abuse
- Circuit breaker for fault tolerance
- Response caching for performance optimization
- Accurate token counting for cost estimation
- Comprehensive health monitoring
"""

import aiohttp
import asyncio
from typing import Dict, Any, AsyncIterator, List, Optional
from .base_provider import BaseProvider, ModelInfo, CompletionRequest, CompletionResponse
from .token_counter import get_global_token_manager
from ..resilience import (
    get_global_pool, get_global_limiter, get_global_manager,
    RateLimitConfig, CircuitBreakerConfig
)
from ..caching import get_global_cache_manager
import json
import time
import logging

logger = logging.getLogger(__name__)

class EnhancedOllamaProvider(BaseProvider):
    """Production-ready provider for local Ollama models with full resilience"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.is_local = True
        self.requires_api_key = False
        
        # Initialize resilience components
        self.connection_pool = get_global_pool()
        self.rate_limiter = get_global_limiter()
        self.circuit_manager = get_global_manager()
        self.cache_manager = get_global_cache_manager()
        self.token_manager = get_global_token_manager()
        
        # Performance metrics
        self._request_count = 0
        self._total_response_time = 0.0
        self._error_count = 0
        self._initialization_time = None
        
        logger.info(f"EnhancedOllamaProvider initialized with resilience features: {self.base_url}")
    
    async def initialize(self) -> bool:
        """Verify Ollama server is running and initialize resilience components"""
        start_time = time.time()
        
        try:
            # Initialize rate limiter for Ollama with generous limits (local server)
            await self.rate_limiter.register_provider(
                'ollama', 
                RateLimitConfig(
                    tokens_per_second=10.0,  # 10 requests per second
                    max_tokens=20,           # Burst capacity
                    window_size=1.0
                )
            )
            
            # Initialize circuit breaker with local-friendly settings
            breaker_config = CircuitBreakerConfig(
                failure_threshold=5,    # More lenient for local
                timeout=10.0,          # Quick recovery
                reset_timeout=60.0
            )
            
            # Test connection with circuit breaker protection
            async def test_connection():
                response = await self.connection_pool.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10.0)
                )
                return response.status == 200
            
            breaker = await self.circuit_manager.get_breaker('ollama', breaker_config)
            is_healthy = await breaker.call(test_connection)
            
            self._initialization_time = time.time() - start_time
            
            if is_healthy:
                logger.info(f"Ollama initialized successfully in {self._initialization_time:.2f}s")
            else:
                logger.error(f"Ollama initialization failed after {self._initialization_time:.2f}s")
            
            return is_healthy
            
        except Exception as e:
            self._initialization_time = time.time() - start_time
            logger.error(f"Ollama initialization failed: {e}")
            return False
    
    def _detect_context_length(self, model_name: str) -> int:
        """Detect context length based on model name patterns"""
        model_lower = model_name.lower()
        
        # Known context lengths for popular models
        context_patterns = {
            'llama-2': 4096,
            'llama2': 4096,
            'llama-3': 8192,
            'llama3': 8192,
            'mistral-7b': 8192,
            'mistral': 4096,
            'codellama-34b': 16384,
            'codellama': 4096,
            'vicuna': 2048,
            'alpaca': 2048,
            'orca': 4096,
            'wizard': 4096,
            'openchat': 8192,
            'neural-chat': 4096,
            'starling': 8192,
        }
        
        for pattern, length in context_patterns.items():
            if pattern in model_lower:
                return length
        
        # Size-based heuristics
        if any(size in model_lower for size in ['70b', '65b']):
            return 4096
        elif any(size in model_lower for size in ['34b', '30b']):
            return 8192 if 'code' in model_lower else 4096
        elif any(size in model_lower for size in ['13b', '15b']):
            return 4096
        elif '7b' in model_lower:
            return 8192 if any(model in model_lower for model in ['mistral', 'openchat']) else 4096
        
        return 4096  # Conservative default
    
    async def list_models(self) -> List[ModelInfo]:
        """List installed Ollama models with caching and resilience"""
        # Create cache key for model listing
        cache_key = {
            'provider': 'ollama',
            'endpoint': 'list_models',
            'base_url': self.base_url
        }
        
        # Try cache first (models don't change frequently)
        cached_models = await self.cache_manager.get_cached_response('ollama', cache_key)
        if cached_models is not None:
            logger.debug("Returning cached model list")
            return cached_models
        
        models = []
        try:
            # Rate limit the request
            if not await self.rate_limiter.wait_for_tokens('ollama', 1, timeout=10.0):
                raise Exception("Rate limit exceeded for model listing")
            
            # Use circuit breaker protection
            async def fetch_models():
                response = await self.connection_pool.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=30.0)
                )
                
                if response.status != 200:
                    raise Exception(f"Ollama API error: {response.status}")
                
                data = await response.json()
                model_list = []
                
                for model in data.get('models', []):
                    # Enhanced model info with better context length detection
                    context_length = self._detect_context_length(model['name'])
                    
                    # Determine capabilities based on model type
                    capabilities = ['chat', 'completion']
                    if 'code' in model['name'].lower():
                        capabilities.append('code_generation')
                    if any(vision in model['name'].lower() for vision in ['vision', 'llava']):
                        capabilities.append('vision')
                    
                    model_list.append(ModelInfo(
                        name=model['name'],
                        provider='ollama',
                        context_length=context_length,
                        capabilities=capabilities,
                        cost_per_token=0.0  # Local models are free
                    ))
                
                return model_list
            
            breaker = await self.circuit_manager.get_breaker('ollama')
            models = await breaker.call(fetch_models)
            
            # Cache the results for 10 minutes (models don't change often)
            await self.cache_manager.cache_response('ollama', cache_key, models, ttl=600)
            
            logger.info(f"Listed {len(models)} Ollama models")
            
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            self._error_count += 1
        
        return models
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion using Ollama with full resilience"""
        start_time = time.time()
        self._request_count += 1
        
        # Create cache key for potential caching
        cache_key = {
            'provider': 'ollama',
            'model': request.model,
            'messages': request.messages,
            'temperature': request.temperature,
            'system_prompt': request.system_prompt,
            'max_tokens': request.max_tokens
        }
        
        # Try cache for deterministic requests (low temperature)
        if request.temperature <= 0.3:
            cached_response = await self.cache_manager.get_cached_response('ollama', cache_key)
            if cached_response is not None:
                logger.debug("Returning cached response for deterministic request")
                return cached_response
        
        try:
            # Calculate input tokens for rate limiting
            input_tokens = self.token_manager.count_message_tokens('ollama', request.messages, request.model)
            if request.system_prompt:
                input_tokens += self.token_manager.count_tokens('ollama', request.system_prompt, request.model)
            
            # Scale rate limiting by request size (larger requests cost more)
            rate_limit_tokens = max(1, input_tokens // 1000)
            
            if not await self.rate_limiter.wait_for_tokens('ollama', rate_limit_tokens, timeout=60.0):
                raise Exception("Rate limit exceeded for completion request")
            
            # Build request payload
            payload = {
                'model': request.model,
                'messages': request.messages,
                'temperature': request.temperature,
                'stream': False
            }
            
            # Add optional parameters
            if request.system_prompt:
                payload['system'] = request.system_prompt
            
            if request.max_tokens:
                payload['options'] = {'num_predict': request.max_tokens}
            
            # Execute with circuit breaker protection
            async def make_request():
                response = await self.connection_pool.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120.0)
                )
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama API error {response.status}: {error_text}")
                
                return await response.json()
            
            breaker = await self.circuit_manager.get_breaker('ollama')
            data = await breaker.call(make_request)
            
            # Extract response content
            if 'message' not in data or 'content' not in data['message']:
                raise Exception("Invalid response format from Ollama")
            
            content = data['message']['content']
            
            # Calculate accurate token counts
            output_tokens = self.token_manager.count_tokens('ollama', content, request.model)
            total_tokens = input_tokens + output_tokens
            
            response = CompletionResponse(
                content=content,
                model=request.model,
                provider='ollama',
                usage={
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': total_tokens
                },
                cost=0.0  # Local models are free
            )
            
            # Cache deterministic responses (30 minute TTL)
            if request.temperature <= 0.3:
                await self.cache_manager.cache_response('ollama', cache_key, response, ttl=1800)
            
            # Update performance metrics
            response_time = time.time() - start_time
            self._total_response_time += response_time
            
            logger.debug(f"Ollama completion: {total_tokens} tokens, {response_time:.2f}s")
            return response
            
        except Exception as e:
            self._error_count += 1
            response_time = time.time() - start_time
            logger.error(f"Ollama completion failed after {response_time:.2f}s: {e}")
            raise
    
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion from Ollama with resilience patterns"""
        start_time = time.time()
        self._request_count += 1
        
        try:
            # Rate limiting for streaming
            input_tokens = self.token_manager.count_message_tokens('ollama', request.messages, request.model)
            if request.system_prompt:
                input_tokens += self.token_manager.count_tokens('ollama', request.system_prompt, request.model)
            
            rate_limit_tokens = max(1, input_tokens // 1000)
            
            if not await self.rate_limiter.wait_for_tokens('ollama', rate_limit_tokens, timeout=60.0):
                raise Exception("Rate limit exceeded for streaming request")
            
            payload = {
                'model': request.model,
                'messages': request.messages,
                'temperature': request.temperature,
                'stream': True
            }
            
            if request.system_prompt:
                payload['system'] = request.system_prompt
            if request.max_tokens:
                payload['options'] = {'num_predict': request.max_tokens}
            
            # Execute with circuit breaker protection
            async def stream_request():
                response = await self.connection_pool.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300.0)  # 5 minute timeout for streaming
                )
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama streaming error {response.status}: {error_text}")
                
                return response
            
            breaker = await self.circuit_manager.get_breaker('ollama')
            response = await breaker.call(stream_request)
            
            # Stream response with robust error handling
            chunks_yielded = 0
            async for line in response.content:
                if line:
                    try:
                        # Handle both bytes and string input
                        if isinstance(line, bytes):
                            line_str = line.decode('utf-8').strip()
                        else:
                            line_str = line.strip()
                        
                        if not line_str:
                            continue
                        
                        data = json.loads(line_str)
                        
                        # Handle chunk data
                        if 'message' in data and 'content' in data['message']:
                            chunk = data['message']['content']
                            if chunk:  # Only yield non-empty chunks
                                chunks_yielded += 1
                                yield chunk
                        
                        # Check if streaming is complete
                        if data.get('done', False):
                            break
                            
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        logger.debug(f"Skipping malformed streaming chunk: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing streaming chunk: {e}")
                        break
            
            # Update performance metrics
            response_time = time.time() - start_time
            self._total_response_time += response_time
            
            logger.debug(f"Ollama streaming complete: {chunks_yielded} chunks, {response_time:.2f}s")
            
        except Exception as e:
            self._error_count += 1
            response_time = time.time() - start_time
            logger.error(f"Ollama streaming failed after {response_time:.2f}s: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check with resilience metrics"""
        try:
            # Basic connectivity test
            start_time = time.time()
            
            async def test_health():
                response = await self.connection_pool.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10.0)
                )
                return response.status == 200
            
            breaker = await self.circuit_manager.get_breaker('ollama')
            is_healthy = await breaker.call(test_health)
            
            health_check_time = time.time() - start_time
            
            # Get models if healthy (don't fail health check if this fails)
            models = []
            model_count = 0
            if is_healthy:
                try:
                    models = await self.list_models()
                    model_count = len(models)
                except Exception as e:
                    logger.warning(f"Could not list models during health check: {e}")
            
            # Gather resilience statistics
            circuit_stats = self.circuit_manager.get_provider_stats('ollama')
            rate_limit_stats = self.rate_limiter.get_provider_stats('ollama')
            cache_stats = self.cache_manager.get_all_stats().get('ollama')
            pool_stats = self.connection_pool.get_stats()
            
            # Calculate performance metrics
            avg_response_time = (
                self._total_response_time / max(1, self._request_count)
            )
            error_rate = self._error_count / max(1, self._request_count)
            
            return {
                'healthy': is_healthy,
                'provider': 'ollama',
                'base_url': self.base_url,
                'timestamp': time.time(),
                
                # Model information
                'models': {
                    'available': model_count,
                    'names': [m.name for m in models[:10]] if models else []  # Limit for readability
                },
                
                # Performance metrics
                'performance': {
                    'total_requests': self._request_count,
                    'error_count': self._error_count,
                    'error_rate': round(error_rate, 4),
                    'avg_response_time_ms': round(avg_response_time * 1000, 2),
                    'health_check_time_ms': round(health_check_time * 1000, 2),
                    'initialization_time_ms': round((self._initialization_time or 0) * 1000, 2)
                },
                
                # Circuit breaker status
                'circuit_breaker': {
                    'state': circuit_stats.state.value if circuit_stats else 'unknown',
                    'failure_count': circuit_stats.failure_count if circuit_stats else 0,
                    'success_count': circuit_stats.success_count if circuit_stats else 0,
                    'total_requests': circuit_stats.total_requests if circuit_stats else 0,
                    'success_rate': round(
                        circuit_stats.successful_requests / max(1, circuit_stats.total_requests)
                        if circuit_stats else 1.0, 4
                    )
                },
                
                # Rate limiter status
                'rate_limiter': {
                    'current_tokens': round(rate_limit_stats.current_tokens, 2) if rate_limit_stats else 0,
                    'total_requests': rate_limit_stats.total_requests if rate_limit_stats else 0,
                    'allowed_requests': rate_limit_stats.allowed_requests if rate_limit_stats else 0,
                    'denied_requests': rate_limit_stats.denied_requests if rate_limit_stats else 0,
                    'avg_wait_time_ms': round((rate_limit_stats.avg_wait_time or 0) * 1000, 2) if rate_limit_stats else 0
                },
                
                # Cache performance
                'cache': {
                    'hit_rate': round(cache_stats.hit_rate, 4) if cache_stats else 0.0,
                    'current_entries': cache_stats.current_entries if cache_stats else 0,
                    'total_requests': cache_stats.total_requests if cache_stats else 0,
                    'memory_mb': round(cache_stats.memory_usage_mb, 2) if cache_stats else 0.0
                },
                
                # Connection pool status
                'connection_pool': {
                    'active_connections': pool_stats.active_connections,
                    'total_requests': pool_stats.total_requests,
                    'failed_requests': pool_stats.failed_requests,
                    'cache_hit_rate': round(
                        pool_stats.cache_hits / max(1, pool_stats.cache_hits + pool_stats.cache_misses), 4
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'healthy': False,
                'provider': 'ollama',
                'base_url': self.base_url,
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def pull_model(self, model_name: str, timeout: float = 3600) -> bool:
        """Pull a model from Ollama registry with resilience"""
        try:
            # Rate limit model pulling (expensive operation)
            if not await self.rate_limiter.wait_for_tokens('ollama', 5, timeout=60.0):
                raise Exception("Rate limit exceeded for model pulling")
            
            payload = {'name': model_name, 'stream': False}
            
            async def pull_request():
                response = await self.connection_pool.post(
                    f"{self.base_url}/api/pull",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                )
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Model pull failed {response.status}: {error_text}")
                
                return response.status == 200
            
            breaker = await self.circuit_manager.get_breaker('ollama')
            success = await breaker.call(pull_request)
            
            if success:
                # Invalidate model cache after successful pull
                cache_key = {
                    'provider': 'ollama',
                    'endpoint': 'list_models',
                    'base_url': self.base_url
                }
                await self.cache_manager.get_cache('ollama').invalidate(cache_key)
                logger.info(f"Successfully pulled model: {model_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def count_tokens(self, text: str, model: str) -> int:
        """Accurate token counting for Ollama models"""
        return self.token_manager.count_tokens('ollama', text, model)
    
    async def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost for token usage (always 0 for local models)"""
        return 0.0  # Local models are free