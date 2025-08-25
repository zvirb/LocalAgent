"""
HTTP Connection Pool for Provider Resilience
Manages reusable HTTP sessions with connection pooling
"""

import aiohttp
import asyncio
from typing import Dict, Optional, Any
from urllib.parse import urlparse
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PoolConfig:
    """Configuration for connection pool"""
    max_connections: int = 100
    max_connections_per_host: int = 20
    connection_timeout: float = 30.0
    read_timeout: float = 60.0
    keepalive_timeout: float = 300.0
    ttl_dns_cache: int = 300
    enable_cleanup_closed: bool = True
    cleanup_interval: float = 60.0

@dataclass
class PoolStats:
    """Statistics for connection pool monitoring"""
    active_connections: int = 0
    idle_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_cleanup: float = 0.0

class ConnectionPool:
    """
    Production-ready HTTP connection pool with the following features:
    - Per-host connection limits
    - Connection reuse and keepalive
    - Automatic connection cleanup
    - DNS caching with TTL
    - Request/response statistics
    - Graceful shutdown handling
    """
    
    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig()
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._stats = PoolStats()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Create connector with optimized settings
        self._connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.max_connections_per_host,
            ttl_dns_cache=self.config.ttl_dns_cache,
            enable_cleanup_closed=self.config.enable_cleanup_closed,
            keepalive_timeout=self.config.keepalive_timeout
        )
        
        logger.info(f"ConnectionPool initialized with {self.config.max_connections} max connections")
        
    async def start(self):
        """Start the connection pool and cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("ConnectionPool cleanup task started")
    
    async def stop(self):
        """Gracefully shutdown the connection pool"""
        logger.info("Shutting down ConnectionPool...")
        self._shutdown_event.set()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        for session in self._sessions.values():
            if not session.closed:
                await session.close()
        
        # Close main connector
        await self._connector.close()
        self._sessions.clear()
        self._session_locks.clear()
        
        logger.info("ConnectionPool shutdown complete")
    
    def _get_host_key(self, url: str) -> str:
        """Extract host key for session management"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    async def get_session(self, url: str) -> aiohttp.ClientSession:
        """
        Get or create a session for the given URL's host
        Sessions are reused per host for connection pooling
        """
        host_key = self._get_host_key(url)
        
        # Get or create lock for this host
        if host_key not in self._session_locks:
            self._session_locks[host_key] = asyncio.Lock()
        
        lock = self._session_locks[host_key]
        
        async with lock:
            # Check if we have an existing session
            if host_key in self._sessions:
                session = self._sessions[host_key]
                if not session.closed:
                    self._stats.cache_hits += 1
                    return session
                else:
                    # Clean up closed session
                    del self._sessions[host_key]
            
            # Create new session
            timeout = aiohttp.ClientTimeout(
                total=self.config.connection_timeout,
                sock_read=self.config.read_timeout
            )
            
            session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'LocalAgent-ConnectionPool/1.0'
                }
            )
            
            self._sessions[host_key] = session
            self._stats.cache_misses += 1
            
            logger.debug(f"Created new session for {host_key}")
            return session
    
    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """
        Make an HTTP request using the connection pool
        Automatically handles session management and statistics
        """
        session = await self.get_session(url)
        
        try:
            self._stats.total_requests += 1
            response = await session.request(method, url, **kwargs)
            return response
        except Exception as e:
            self._stats.failed_requests += 1
            logger.error(f"Request failed for {method} {url}: {e}")
            raise
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Convenience method for GET requests"""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Convenience method for POST requests"""
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Convenience method for PUT requests"""
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Convenience method for DELETE requests"""
        return await self.request('DELETE', url, **kwargs)
    
    def get_stats(self) -> PoolStats:
        """Get current connection pool statistics"""
        # Update live connection counts
        self._stats.active_connections = len([s for s in self._sessions.values() if not s.closed])
        self._stats.idle_connections = self._connector._conns.total_size if hasattr(self._connector, '_conns') else 0
        return self._stats
    
    async def _cleanup_loop(self):
        """Background task for periodic cleanup of stale connections"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_stale_sessions()
                self._stats.last_cleanup = time.time()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_stale_sessions(self):
        """Remove closed or stale sessions"""
        stale_keys = []
        
        for host_key, session in self._sessions.items():
            if session.closed:
                stale_keys.append(host_key)
        
        for key in stale_keys:
            del self._sessions[key]
            if key in self._session_locks:
                del self._session_locks[key]
        
        if stale_keys:
            logger.debug(f"Cleaned up {len(stale_keys)} stale sessions")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()


# Global connection pool instance
_global_pool: Optional[ConnectionPool] = None

def get_global_pool() -> ConnectionPool:
    """Get or create the global connection pool instance"""
    global _global_pool
    if _global_pool is None:
        _global_pool = ConnectionPool()
    return _global_pool

async def initialize_global_pool(config: Optional[PoolConfig] = None):
    """Initialize the global connection pool"""
    global _global_pool
    if _global_pool is not None:
        await _global_pool.stop()
    
    _global_pool = ConnectionPool(config)
    await _global_pool.start()

async def shutdown_global_pool():
    """Shutdown the global connection pool"""
    global _global_pool
    if _global_pool is not None:
        await _global_pool.stop()
        _global_pool = None