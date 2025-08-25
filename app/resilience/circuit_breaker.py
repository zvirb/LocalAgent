"""
Circuit Breaker Pattern for Provider Fault Tolerance
Implements automatic failure detection and recovery
"""

import asyncio
import time
from typing import Dict, Optional, Any, Callable, List
from dataclasses import dataclass
from enum import Enum
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing fast
    HALF_OPEN = "half_open" # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close from half-open
    timeout: float = 60.0              # Time before trying half-open
    reset_timeout: float = 300.0       # Time to reset failure count
    expected_exceptions: List[type] = None  # Exceptions that trigger circuit
    ignored_exceptions: List[type] = None   # Exceptions to ignore

@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    state_transitions: int = 0
    open_duration: float = 0.0

class CircuitBreaker:
    """
    Circuit breaker implementation with the following features:
    - Configurable failure thresholds and timeouts
    - Automatic state transitions (closed -> open -> half-open -> closed)
    - Exception filtering (expected vs unexpected failures)
    - Detailed statistics and monitoring
    - Fallback function support
    - Manual control (force open/close)
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._last_success_time = 0.0
        self._state_change_time = time.time()
        self._lock = asyncio.Lock()
        self._stats = CircuitBreakerStats()
        
        # Set default expected exceptions if none provided
        if self.config.expected_exceptions is None:
            self.config.expected_exceptions = [
                ConnectionError, TimeoutError, OSError,
                asyncio.TimeoutError, aiohttp.ClientError if 'aiohttp' in globals() else Exception
            ]
        
        if self.config.ignored_exceptions is None:
            self.config.ignored_exceptions = [ValueError, TypeError]
        
        logger.info(f"CircuitBreaker '{name}' initialized: {self.config.failure_threshold} failure threshold")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state"""
        return self._state
    
    async def _change_state(self, new_state: CircuitState):
        """Change circuit breaker state with logging"""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self._state_change_time = time.time()
            self._stats.state = new_state
            self._stats.state_transitions += 1
            
            logger.info(f"CircuitBreaker '{self.name}' state changed: {old_state.value} -> {new_state.value}")
            
            # Reset counters on state changes
            if new_state == CircuitState.CLOSED:
                self._failure_count = 0
                self._success_count = 0
            elif new_state == CircuitState.HALF_OPEN:
                self._success_count = 0
    
    async def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset from open to half-open"""
        if self._state != CircuitState.OPEN:
            return False
        
        time_since_last_failure = time.time() - self._last_failure_time
        return time_since_last_failure >= self.config.timeout
    
    async def _should_reset_failure_count(self) -> bool:
        """Check if failure count should be reset due to time passage"""
        if self._failure_count == 0:
            return False
        
        time_since_last_failure = time.time() - self._last_failure_time
        return time_since_last_failure >= self.config.reset_timeout
    
    def _is_expected_exception(self, exception: Exception) -> bool:
        """Check if exception should trigger circuit breaker"""
        # Ignore certain exceptions
        for ignored_type in self.config.ignored_exceptions:
            if isinstance(exception, ignored_type):
                return False
        
        # Check for expected exceptions
        for expected_type in self.config.expected_exceptions:
            if isinstance(exception, expected_type):
                return True
        
        return False
    
    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection
        """
        async with self._lock:
            self._stats.total_requests += 1
            
            # Check if we should attempt reset
            if await self._should_attempt_reset():
                await self._change_state(CircuitState.HALF_OPEN)
            
            # Reset failure count if enough time has passed
            if await self._should_reset_failure_count():
                self._failure_count = 0
                logger.info(f"CircuitBreaker '{self.name}' failure count reset due to timeout")
            
            # Fast fail if circuit is open
            if self._state == CircuitState.OPEN:
                self._stats.rejected_requests += 1
                self._stats.open_duration = time.time() - self._state_change_time
                raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is OPEN")
        
        # Execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Handle success
            await self._on_success()
            return result
            
        except Exception as e:
            # Handle failure
            await self._on_failure(e)
            raise
    
    async def _on_success(self):
        """Handle successful function execution"""
        async with self._lock:
            self._last_success_time = time.time()
            self._stats.successful_requests += 1
            self._stats.last_success_time = self._last_success_time
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._change_state(CircuitState.CLOSED)
            
            # Reset failure count on success in closed state
            elif self._state == CircuitState.CLOSED and self._failure_count > 0:
                self._failure_count = max(0, self._failure_count - 1)
    
    async def _on_failure(self, exception: Exception):
        """Handle failed function execution"""
        async with self._lock:
            self._stats.failed_requests += 1
            
            # Only count expected exceptions as failures
            if not self._is_expected_exception(exception):
                logger.debug(f"CircuitBreaker '{self.name}' ignoring exception: {type(exception).__name__}")
                return
            
            self._failure_count += 1
            self._last_failure_time = time.time()
            self._stats.failure_count = self._failure_count
            self._stats.last_failure_time = self._last_failure_time
            
            logger.warning(f"CircuitBreaker '{self.name}' failure #{self._failure_count}: {exception}")
            
            # Open circuit if threshold reached
            if self._state == CircuitState.CLOSED and self._failure_count >= self.config.failure_threshold:
                await self._change_state(CircuitState.OPEN)
            
            # Go back to open if half-open attempt fails
            elif self._state == CircuitState.HALF_OPEN:
                await self._change_state(CircuitState.OPEN)
    
    async def force_open(self):
        """Manually force circuit breaker to open state"""
        async with self._lock:
            await self._change_state(CircuitState.OPEN)
            logger.warning(f"CircuitBreaker '{self.name}' manually forced OPEN")
    
    async def force_close(self):
        """Manually force circuit breaker to closed state"""
        async with self._lock:
            await self._change_state(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            logger.info(f"CircuitBreaker '{self.name}' manually forced CLOSED")
    
    async def force_half_open(self):
        """Manually force circuit breaker to half-open state"""
        async with self._lock:
            await self._change_state(CircuitState.HALF_OPEN)
            self._success_count = 0
            logger.info(f"CircuitBreaker '{self.name}' manually forced HALF_OPEN")
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics"""
        stats = self._stats
        stats.state = self._state
        stats.failure_count = self._failure_count
        stats.success_count = self._success_count
        
        if self._state == CircuitState.OPEN:
            stats.open_duration = time.time() - self._state_change_time
        
        return stats


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers with shared configuration
    Features:
    - Per-provider circuit breaker instances
    - Bulk operations across all breakers
    - Centralized monitoring and statistics
    - Configuration templates
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._configs: Dict[str, CircuitBreakerConfig] = {}
        self._lock = asyncio.Lock()
        
        # Default configurations for known providers
        self._default_configs = {
            'openai': CircuitBreakerConfig(failure_threshold=3, timeout=30.0),
            'ollama': CircuitBreakerConfig(failure_threshold=5, timeout=10.0),  # Local, more lenient
            'gemini': CircuitBreakerConfig(failure_threshold=3, timeout=60.0),
            'perplexity': CircuitBreakerConfig(failure_threshold=2, timeout=120.0),  # Conservative
            'anthropic': CircuitBreakerConfig(failure_threshold=3, timeout=30.0),
            'default': CircuitBreakerConfig(failure_threshold=3, timeout=60.0)
        }
    
    async def get_breaker(self, provider_name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create circuit breaker for provider"""
        if provider_name not in self._breakers:
            async with self._lock:
                if provider_name not in self._breakers:
                    if config is None:
                        config = self._default_configs.get(provider_name, self._default_configs['default'])
                    
                    self._configs[provider_name] = config
                    self._breakers[provider_name] = CircuitBreaker(provider_name, config)
                    
                    logger.info(f"Created circuit breaker for {provider_name}")
        
        return self._breakers[provider_name]
    
    async def call_with_breaker(self, provider_name: str, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        breaker = await self.get_breaker(provider_name)
        return await breaker.call(func, *args, **kwargs)
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }
    
    def get_provider_stats(self, provider_name: str) -> Optional[CircuitBreakerStats]:
        """Get statistics for specific provider"""
        if provider_name in self._breakers:
            return self._breakers[provider_name].get_stats()
        return None
    
    async def force_open_all(self):
        """Force all circuit breakers to open state"""
        for breaker in self._breakers.values():
            await breaker.force_open()
    
    async def force_close_all(self):
        """Force all circuit breakers to closed state"""
        for breaker in self._breakers.values():
            await breaker.force_close()
    
    async def update_config(self, provider_name: str, config: CircuitBreakerConfig):
        """Update configuration for a provider"""
        async with self._lock:
            self._configs[provider_name] = config
            if provider_name in self._breakers:
                # Recreate breaker with new config
                old_stats = self._breakers[provider_name].get_stats()
                self._breakers[provider_name] = CircuitBreaker(provider_name, config)
                logger.info(f"Updated circuit breaker config for {provider_name}")


# Global circuit breaker manager
_global_manager: Optional[CircuitBreakerManager] = None

def get_global_manager() -> CircuitBreakerManager:
    """Get or create the global circuit breaker manager"""
    global _global_manager
    if _global_manager is None:
        _global_manager = CircuitBreakerManager()
    return _global_manager


# Decorator for automatic circuit breaker protection
def circuit_breaker(provider: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to automatically protect function with circuit breaker
    Usage: @circuit_breaker('openai', CircuitBreakerConfig(...))
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            manager = get_global_manager()
            breaker = await manager.get_breaker(provider, config)
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator