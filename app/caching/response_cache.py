"""
Response Cache with LRU Eviction for Provider Responses
Implements intelligent caching with TTL and content-aware strategies
"""

import asyncio
import time
import hashlib
import json
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict
from collections import OrderedDict
import logging
import pickle
import zlib
from enum import Enum

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """Cache strategies for different types of requests"""
    AGGRESSIVE = "aggressive"    # Cache everything, long TTL
    CONSERVATIVE = "conservative"  # Cache only safe requests, short TTL
    SELECTIVE = "selective"      # Smart caching based on content
    DISABLED = "disabled"        # No caching

@dataclass
class CacheConfig:
    """Configuration for response caching"""
    max_size: int = 1000              # Maximum number of cached entries
    default_ttl: float = 300.0        # Default TTL in seconds (5 minutes)
    max_ttl: float = 3600.0          # Maximum TTL (1 hour)
    min_ttl: float = 30.0            # Minimum TTL (30 seconds)
    strategy: CacheStrategy = CacheStrategy.SELECTIVE
    compress_threshold: int = 1024    # Compress responses larger than this
    compression_level: int = 6        # zlib compression level
    exclude_patterns: List[str] = None  # Patterns to exclude from caching
    max_response_size: int = 1024 * 1024  # Max response size to cache (1MB)

@dataclass
class CacheEntry:
    """Cached response entry"""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    ttl: float
    hits: int = 0
    size: int = 0
    compressed: bool = False
    metadata: Dict[str, Any] = None

@dataclass
class CacheStats:
    """Statistics for cache monitoring"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    expired_entries: int = 0
    total_size: int = 0
    current_entries: int = 0
    hit_rate: float = 0.0
    avg_response_time: float = 0.0
    memory_usage_mb: float = 0.0

class ResponseCache:
    """
    LRU Response Cache with the following features:
    - Configurable TTL per entry or global default
    - LRU eviction policy with size limits
    - Optional compression for large responses
    - Content-aware caching strategies
    - Thread-safe operation
    - Detailed statistics and monitoring
    - Intelligent cache key generation
    - Partial response caching for streaming
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = CacheStats()
        
        # Set default exclude patterns
        if self.config.exclude_patterns is None:
            self.config.exclude_patterns = [
                '*password*', '*secret*', '*key*', '*token*',
                '*auth*', '*login*', '*session*'
            ]
        
        logger.info(f"ResponseCache initialized: max_size={self.config.max_size}, ttl={self.config.default_ttl}s")
    
    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """Generate deterministic cache key from request data"""
        # Sort keys for consistency
        normalized = json.dumps(request_data, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _should_cache(self, request_data: Dict[str, Any], response_data: Any) -> bool:
        """Determine if request/response should be cached"""
        if self.config.strategy == CacheStrategy.DISABLED:
            return False
        
        # Check exclude patterns
        request_str = json.dumps(request_data, default=str).lower()
        for pattern in self.config.exclude_patterns:
            if pattern.replace('*', '') in request_str:
                logger.debug(f"Excluding from cache due to pattern: {pattern}")
                return False
        
        # Check response size
        try:
            response_size = len(pickle.dumps(response_data))
            if response_size > self.config.max_response_size:
                logger.debug(f"Response too large to cache: {response_size} bytes")
                return False
        except Exception:
            return False
        
        # Strategy-based decisions
        if self.config.strategy == CacheStrategy.AGGRESSIVE:
            return True
        elif self.config.strategy == CacheStrategy.CONSERVATIVE:
            # Only cache GET-like operations
            return request_data.get('method', '').upper() in ['GET', 'HEAD', 'OPTIONS']
        elif self.config.strategy == CacheStrategy.SELECTIVE:
            # Smart caching based on content type and patterns
            return self._is_cacheable_content(request_data, response_data)
        
        return False
    
    def _is_cacheable_content(self, request_data: Dict[str, Any], response_data: Any) -> bool:
        """Intelligent content-based caching decisions"""
        # Cache model listings and static information
        if 'models' in json.dumps(request_data, default=str).lower():
            return True
        
        # Cache completions with low temperature (more deterministic)
        temperature = request_data.get('temperature', 1.0)
        if temperature <= 0.3:
            return True
        
        # Cache short responses (likely informational)
        try:
            if hasattr(response_data, '__len__') and len(str(response_data)) < 500:
                return True
        except Exception:
            pass
        
        return False
    
    def _calculate_ttl(self, request_data: Dict[str, Any], response_data: Any) -> float:
        """Calculate appropriate TTL based on content"""
        base_ttl = self.config.default_ttl
        
        # Model listings can be cached longer
        if 'models' in json.dumps(request_data, default=str).lower():
            return min(self.config.max_ttl, base_ttl * 4)
        
        # Low temperature requests are more stable
        temperature = request_data.get('temperature', 1.0)
        if temperature <= 0.1:
            return min(self.config.max_ttl, base_ttl * 2)
        elif temperature <= 0.5:
            return min(self.config.max_ttl, base_ttl * 1.5)
        
        # Short responses can be cached longer
        try:
            response_len = len(str(response_data))
            if response_len < 100:
                return min(self.config.max_ttl, base_ttl * 2)
        except Exception:
            pass
        
        return max(self.config.min_ttl, base_ttl)
    
    def _compress_data(self, data: Any) -> Tuple[bytes, bool]:
        """Compress data if beneficial"""
        try:
            serialized = pickle.dumps(data)
            
            if len(serialized) < self.config.compress_threshold:
                return serialized, False
            
            compressed = zlib.compress(serialized, self.config.compression_level)
            
            # Only use compression if it provides significant benefit
            if len(compressed) < len(serialized) * 0.8:
                return compressed, True
            else:
                return serialized, False
        except Exception as e:
            logger.error(f"Error compressing data: {e}")
            return pickle.dumps(data), False
    
    def _decompress_data(self, data: bytes, compressed: bool) -> Any:
        """Decompress data if needed"""
        try:
            if compressed:
                decompressed = zlib.decompress(data)
                return pickle.loads(decompressed)
            else:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Error decompressing data: {e}")
            raise
    
    async def _evict_expired(self):
        """Remove expired entries"""
        now = time.time()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if now - entry.created_at > entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self._stats.expired_entries += 1
        
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired cache entries")
    
    async def _evict_lru(self):
        """Evict least recently used entries to make space"""
        while len(self._cache) >= self.config.max_size:
            # Remove oldest entry (first in OrderedDict)
            key, entry = self._cache.popitem(last=False)
            self._stats.evictions += 1
            logger.debug(f"Evicted LRU cache entry: {key}")
    
    async def get(self, request_data: Dict[str, Any]) -> Optional[Any]:
        """Get cached response if available and valid"""
        cache_key = self._generate_cache_key(request_data)
        
        async with self._lock:
            self._stats.total_requests += 1
            
            # Clean expired entries periodically
            if self._stats.total_requests % 100 == 0:
                await self._evict_expired()
            
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                
                # Check TTL
                if time.time() - entry.created_at <= entry.ttl:
                    # Move to end (mark as recently used)
                    self._cache.move_to_end(cache_key)
                    entry.accessed_at = time.time()
                    entry.hits += 1
                    
                    self._stats.cache_hits += 1
                    self._stats.hit_rate = self._stats.cache_hits / self._stats.total_requests
                    
                    # Decompress and return data
                    try:
                        return self._decompress_data(entry.value, entry.compressed)
                    except Exception as e:
                        logger.error(f"Error retrieving cached data: {e}")
                        del self._cache[cache_key]
                else:
                    # Expired entry
                    del self._cache[cache_key]
                    self._stats.expired_entries += 1
            
            self._stats.cache_misses += 1
            self._stats.hit_rate = self._stats.cache_hits / self._stats.total_requests
            return None
    
    async def put(self, request_data: Dict[str, Any], response_data: Any, ttl: Optional[float] = None) -> bool:
        """Cache response if appropriate"""
        if not self._should_cache(request_data, response_data):
            return False
        
        cache_key = self._generate_cache_key(request_data)
        
        async with self._lock:
            # Calculate TTL
            entry_ttl = ttl if ttl is not None else self._calculate_ttl(request_data, response_data)
            entry_ttl = max(self.config.min_ttl, min(self.config.max_ttl, entry_ttl))
            
            # Compress data
            try:
                compressed_data, is_compressed = self._compress_data(response_data)
                data_size = len(compressed_data)
            except Exception as e:
                logger.error(f"Error caching data: {e}")
                return False
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                value=compressed_data,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=entry_ttl,
                size=data_size,
                compressed=is_compressed,
                metadata={'request_summary': str(request_data)[:100]}
            )
            
            # Evict LRU if needed
            await self._evict_lru()
            
            # Store entry
            self._cache[cache_key] = entry
            self._update_stats()
            
            logger.debug(f"Cached response: key={cache_key[:8]}, size={data_size}, ttl={entry_ttl}s")
            return True
    
    def _update_stats(self):
        """Update cache statistics"""
        self._stats.current_entries = len(self._cache)
        self._stats.total_size = sum(entry.size for entry in self._cache.values())
        self._stats.memory_usage_mb = self._stats.total_size / (1024 * 1024)
    
    async def invalidate(self, request_data: Dict[str, Any]) -> bool:
        """Invalidate specific cache entry"""
        cache_key = self._generate_cache_key(request_data)
        
        async with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                self._update_stats()
                logger.debug(f"Invalidated cache entry: {cache_key[:8]}")
                return True
            return False
    
    async def clear(self):
        """Clear all cache entries"""
        async with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self._update_stats()
            logger.info(f"Cleared {cleared_count} cache entries")
    
    async def cleanup(self):
        """Manual cleanup of expired entries"""
        async with self._lock:
            await self._evict_expired()
            self._update_stats()
    
    def get_stats(self) -> CacheStats:
        """Get current cache statistics"""
        self._update_stats()
        return self._stats
    
    def get_entry_info(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get information about specific cache entry"""
        cache_key = self._generate_cache_key(request_data)
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            return {
                'key': cache_key,
                'age': time.time() - entry.created_at,
                'ttl': entry.ttl,
                'hits': entry.hits,
                'size': entry.size,
                'compressed': entry.compressed,
                'expires_in': entry.ttl - (time.time() - entry.created_at)
            }
        return None


class CacheManager:
    """
    Manager for multiple response caches with provider-specific configurations
    """
    
    def __init__(self):
        self._caches: Dict[str, ResponseCache] = {}
        self._configs: Dict[str, CacheConfig] = {}
        self._lock = asyncio.Lock()
        
        # Default configurations for known providers
        self._default_configs = {
            'openai': CacheConfig(max_size=500, default_ttl=300, strategy=CacheStrategy.SELECTIVE),
            'ollama': CacheConfig(max_size=200, default_ttl=600, strategy=CacheStrategy.AGGRESSIVE),  # Local caching
            'gemini': CacheConfig(max_size=300, default_ttl=180, strategy=CacheStrategy.CONSERVATIVE),
            'perplexity': CacheConfig(max_size=100, default_ttl=120, strategy=CacheStrategy.CONSERVATIVE),
            'anthropic': CacheConfig(max_size=400, default_ttl=300, strategy=CacheStrategy.SELECTIVE),
            'default': CacheConfig(max_size=200, default_ttl=300, strategy=CacheStrategy.CONSERVATIVE)
        }
    
    async def get_cache(self, provider_name: str, config: Optional[CacheConfig] = None) -> ResponseCache:
        """Get or create cache for provider"""
        if provider_name not in self._caches:
            async with self._lock:
                if provider_name not in self._caches:
                    if config is None:
                        config = self._default_configs.get(provider_name, self._default_configs['default'])
                    
                    self._configs[provider_name] = config
                    self._caches[provider_name] = ResponseCache(config)
                    
                    logger.info(f"Created response cache for {provider_name}")
        
        return self._caches[provider_name]
    
    async def get_cached_response(self, provider_name: str, request_data: Dict[str, Any]) -> Optional[Any]:
        """Get cached response from provider cache"""
        cache = await self.get_cache(provider_name)
        return await cache.get(request_data)
    
    async def cache_response(self, provider_name: str, request_data: Dict[str, Any], 
                           response_data: Any, ttl: Optional[float] = None) -> bool:
        """Cache response in provider cache"""
        cache = await self.get_cache(provider_name)
        return await cache.put(request_data, response_data, ttl)
    
    def get_all_stats(self) -> Dict[str, CacheStats]:
        """Get statistics for all provider caches"""
        return {
            name: cache.get_stats()
            for name, cache in self._caches.items()
        }
    
    async def clear_all_caches(self):
        """Clear all provider caches"""
        for cache in self._caches.values():
            await cache.clear()
    
    async def cleanup_all_caches(self):
        """Cleanup expired entries in all caches"""
        for cache in self._caches.values():
            await cache.cleanup()


# Global cache manager
_global_cache_manager: Optional[CacheManager] = None

def get_global_cache_manager() -> CacheManager:
    """Get or create the global cache manager"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


# Decorator for automatic response caching
def cached_response(provider: str, ttl: Optional[float] = None):
    """
    Decorator to automatically cache function responses
    Usage: @cached_response('openai', ttl=300)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Create request data from function arguments
            request_data = {
                'function': func.__name__,
                'args': str(args),
                'kwargs': kwargs
            }
            
            manager = get_global_cache_manager()
            
            # Try to get cached response
            cached = await manager.get_cached_response(provider, request_data)
            if cached is not None:
                return cached
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await manager.cache_response(provider, request_data, result, ttl)
            
            return result
        
        return wrapper
    return decorator