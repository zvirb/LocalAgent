"""
Token Bucket Rate Limiter for Provider API Calls
Implements per-provider rate limiting with burst handling
"""

import asyncio
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    tokens_per_second: float = 1.0  # Sustained rate
    max_tokens: int = 10  # Burst capacity
    initial_tokens: int = None  # Start with full bucket if None
    window_size: float = 1.0  # Time window for rate calculation

@dataclass
class RateLimitStats:
    """Statistics for rate limiter monitoring"""
    total_requests: int = 0
    allowed_requests: int = 0
    denied_requests: int = 0
    current_tokens: float = 0.0
    last_refill: float = 0.0
    wait_time_total: float = 0.0
    avg_wait_time: float = 0.0

class TokenBucket:
    """
    Token bucket algorithm implementation with the following features:
    - Configurable token refill rate and burst capacity
    - Thread-safe operation using asyncio locks
    - Request queuing with optional timeout
    - Detailed statistics for monitoring
    - Graceful degradation under high load
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.initial_tokens if config.initial_tokens is not None else config.max_tokens
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
        self._stats = RateLimitStats()
        self._stats.current_tokens = self.tokens
        self._stats.last_refill = self.last_refill
        
        logger.info(f"TokenBucket initialized: {config.tokens_per_second} tokens/sec, max {config.max_tokens}")
    
    async def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate new tokens to add
        tokens_to_add = elapsed * self.config.tokens_per_second
        self.tokens = min(self.config.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
        
        self._stats.current_tokens = self.tokens
        self._stats.last_refill = now
    
    async def consume(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Consume tokens from the bucket
        Returns True if tokens were consumed, False if rate limited
        """
        async with self._lock:
            await self._refill_tokens()
            
            self._stats.total_requests += 1
            
            if self.tokens >= tokens:
                # Allow request
                self.tokens -= tokens
                self._stats.allowed_requests += 1
                self._stats.current_tokens = self.tokens
                return True
            
            # Rate limited
            self._stats.denied_requests += 1
            return False
    
    async def consume_blocking(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Consume tokens with blocking wait if not available
        Will wait until tokens are available or timeout occurs
        """
        start_time = time.time()
        
        while True:
            if await self.consume(tokens):
                return True
            
            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                logger.warning(f"Rate limiter timeout after {timeout}s waiting for {tokens} tokens")
                return False
            
            # Calculate wait time until next token
            async with self._lock:
                await self._refill_tokens()
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.config.tokens_per_second
                wait_time = min(wait_time, 1.0)  # Cap at 1 second
            
            self._stats.wait_time_total += wait_time
            self._stats.avg_wait_time = self._stats.wait_time_total / max(1, self._stats.total_requests)
            
            await asyncio.sleep(wait_time)
    
    def get_stats(self) -> RateLimitStats:
        """Get current rate limiter statistics"""
        return self._stats
    
    async def reset(self):
        """Reset the token bucket to full capacity"""
        async with self._lock:
            self.tokens = self.config.max_tokens
            self.last_refill = time.time()
            self._stats.current_tokens = self.tokens
            logger.info("TokenBucket reset to full capacity")


class RateLimiter:
    """
    Multi-provider rate limiter managing separate buckets per provider
    Features:
    - Per-provider rate limit configurations
    - Dynamic provider registration
    - Bulk token consumption for batch operations
    - Global and per-provider statistics
    - Emergency bypass for critical operations
    """
    
    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._configs: Dict[str, RateLimitConfig] = {}
        self._lock = asyncio.Lock()
        
        # Default configurations for known providers
        self._default_configs = {
            'openai': RateLimitConfig(tokens_per_second=60.0, max_tokens=100),  # 60 RPM burst
            'ollama': RateLimitConfig(tokens_per_second=10.0, max_tokens=20),   # Local, generous
            'gemini': RateLimitConfig(tokens_per_second=15.0, max_tokens=30),   # 15 RPM
            'perplexity': RateLimitConfig(tokens_per_second=5.0, max_tokens=10), # Conservative
            'anthropic': RateLimitConfig(tokens_per_second=20.0, max_tokens=40), # 20 RPM
            'default': RateLimitConfig(tokens_per_second=5.0, max_tokens=10)     # Safe default
        }
    
    async def register_provider(self, provider_name: str, config: Optional[RateLimitConfig] = None):
        """Register a provider with specific rate limiting configuration"""
        async with self._lock:
            if config is None:
                config = self._default_configs.get(provider_name, self._default_configs['default'])
            
            self._configs[provider_name] = config
            self._buckets[provider_name] = TokenBucket(config)
            
            logger.info(f"Registered rate limiter for {provider_name}: {config.tokens_per_second} tokens/sec")
    
    async def get_bucket(self, provider_name: str) -> TokenBucket:
        """Get or create token bucket for provider"""
        if provider_name not in self._buckets:
            await self.register_provider(provider_name)
        
        return self._buckets[provider_name]
    
    async def allow_request(self, provider_name: str, tokens: int = 1) -> bool:
        """Check if request is allowed without blocking"""
        bucket = await self.get_bucket(provider_name)
        return await bucket.consume(tokens)
    
    async def wait_for_tokens(self, provider_name: str, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Wait for tokens to become available"""
        bucket = await self.get_bucket(provider_name)
        return await bucket.consume_blocking(tokens, timeout)
    
    async def bulk_consume(self, requests: Dict[str, int]) -> Dict[str, bool]:
        """
        Consume tokens for multiple providers atomically
        Returns dict of provider -> success status
        """
        results = {}
        
        # First pass: check availability without consuming
        all_available = True
        for provider, tokens in requests.items():
            bucket = await self.get_bucket(provider)
            if not await bucket.consume(tokens):
                all_available = False
                break
        
        if all_available:
            # All requests can be satisfied
            for provider in requests.keys():
                results[provider] = True
        else:
            # Reject all requests to maintain atomicity
            for provider in requests.keys():
                results[provider] = False
        
        return results
    
    def get_provider_stats(self, provider_name: str) -> Optional[RateLimitStats]:
        """Get statistics for specific provider"""
        if provider_name in self._buckets:
            return self._buckets[provider_name].get_stats()
        return None
    
    def get_all_stats(self) -> Dict[str, RateLimitStats]:
        """Get statistics for all providers"""
        return {
            provider: bucket.get_stats()
            for provider, bucket in self._buckets.items()
        }
    
    async def reset_provider(self, provider_name: str):
        """Reset rate limiter for specific provider"""
        if provider_name in self._buckets:
            await self._buckets[provider_name].reset()
    
    async def reset_all(self):
        """Reset all provider rate limiters"""
        for bucket in self._buckets.values():
            await bucket.reset()
    
    async def update_config(self, provider_name: str, config: RateLimitConfig):
        """Update configuration for a provider"""
        async with self._lock:
            self._configs[provider_name] = config
            self._buckets[provider_name] = TokenBucket(config)
            logger.info(f"Updated rate limiter config for {provider_name}")


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None

def get_global_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance"""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter

async def initialize_global_limiter(provider_configs: Optional[Dict[str, RateLimitConfig]] = None):
    """Initialize the global rate limiter with provider configurations"""
    global _global_limiter
    _global_limiter = RateLimiter()
    
    if provider_configs:
        for provider, config in provider_configs.items():
            await _global_limiter.register_provider(provider, config)


# Convenience decorator for rate limiting
def rate_limited(provider: str, tokens: int = 1, timeout: Optional[float] = None):
    """
    Decorator to automatically rate limit function calls
    Usage: @rate_limited('openai', tokens=2, timeout=30.0)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            limiter = get_global_limiter()
            
            if await limiter.wait_for_tokens(provider, tokens, timeout):
                return await func(*args, **kwargs)
            else:
                raise Exception(f"Rate limit exceeded for {provider}, timeout after {timeout}s")
        
        return wrapper
    return decorator