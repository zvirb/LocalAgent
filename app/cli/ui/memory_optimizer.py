"""
Memory Management and Buffer Optimization
Object pooling, efficient string operations, and memory leak prevention
"""

import gc
import sys
import time
import weakref
from typing import Dict, Any, List, Optional, TypeVar, Generic, Callable, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager
import threading
import psutil
from pathlib import Path

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn


T = TypeVar('T')


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    current_usage_mb: float
    peak_usage_mb: float
    pool_efficiency: float
    cache_hit_ratio: float
    gc_collections: int
    string_pool_size: int
    object_pool_sizes: Dict[str, int]
    memory_leaks_detected: int


class ObjectPool(Generic[T]):
    """High-performance object pool with automatic cleanup"""
    
    def __init__(self, factory: Callable[[], T], max_size: int = 100, 
                 cleanup_callback: Optional[Callable[[T], None]] = None):
        self.factory = factory
        self.max_size = max_size
        self.cleanup_callback = cleanup_callback
        
        self._pool: deque[T] = deque()
        self._in_use: Set[int] = set()
        self._lock = threading.Lock()
        self._created_count = 0
        self._reused_count = 0
        
    def acquire(self) -> T:
        """Acquire an object from the pool"""
        with self._lock:
            if self._pool:
                obj = self._pool.popleft()
                self._in_use.add(id(obj))
                self._reused_count += 1
                return obj
            else:
                obj = self.factory()
                self._in_use.add(id(obj))
                self._created_count += 1
                return obj
    
    def release(self, obj: T) -> None:
        """Release an object back to the pool"""
        obj_id = id(obj)
        
        with self._lock:
            if obj_id not in self._in_use:
                return  # Object not from this pool or already released
                
            self._in_use.remove(obj_id)
            
            # Clean up object if callback provided
            if self.cleanup_callback:
                self.cleanup_callback(obj)
            
            # Add back to pool if under size limit
            if len(self._pool) < self.max_size:
                self._pool.append(obj)
    
    @contextmanager
    def acquire_context(self):
        """Context manager for automatic acquire/release"""
        obj = self.acquire()
        try:
            yield obj
        finally:
            self.release(obj)
    
    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics"""
        with self._lock:
            return {
                'pool_size': len(self._pool),
                'in_use': len(self._in_use),
                'created': self._created_count,
                'reused': self._reused_count,
                'efficiency': self._reused_count / max(1, self._created_count + self._reused_count)
            }
    
    def clear(self) -> None:
        """Clear the entire pool"""
        with self._lock:
            self._pool.clear()
            self._in_use.clear()


class StringPool:
    """Optimized string pooling and escape sequence caching"""
    
    def __init__(self, max_cache_size: int = 10000):
        self.max_cache_size = max_cache_size
        
        # String interning caches
        self._string_cache: Dict[str, str] = {}
        self._escape_cache: Dict[str, str] = {}
        self._format_cache: Dict[tuple, str] = {}
        
        # Usage tracking for LRU eviction
        self._access_times: Dict[str, float] = {}
        self._lock = threading.Lock()
        
        # Pre-populate with common strings
        self._populate_common_strings()
    
    def _populate_common_strings(self):
        """Pre-populate cache with commonly used strings"""
        common_strings = [
            # Rich markup
            "[bold]", "[/bold]", "[italic]", "[/italic]",
            "[underline]", "[/underline]", "[dim]", "[/dim]",
            
            # Colors
            "[red]", "[green]", "[blue]", "[yellow]", "[cyan]", "[magenta]",
            "[/red]", "[/green]", "[/blue]", "[/yellow]", "[/cyan]", "[/magenta]",
            
            # Status indicators
            "✓", "✗", "⚠", "ℹ", "🔄", "⚡", "🎉", "💥",
            
            # Common words
            "Success", "Error", "Warning", "Info", "Loading", "Complete", "Failed",
            "Agent", "Phase", "Task", "Config", "Provider", "Status",
        ]
        
        for s in common_strings:
            self._string_cache[s] = s
    
    def intern_string(self, s: str) -> str:
        """Intern a string to save memory"""
        if not isinstance(s, str) or len(s) > 1000:  # Skip very long strings
            return s
        
        with self._lock:
            if s in self._string_cache:
                self._access_times[s] = time.time()
                return self._string_cache[s]
            
            # Check if we need to evict old entries
            if len(self._string_cache) >= self.max_cache_size:
                self._evict_lru_entries()
            
            # Intern the string
            interned = sys.intern(s)
            self._string_cache[s] = interned
            self._access_times[s] = time.time()
            return interned
    
    def cache_escape_sequence(self, content: str, style: str) -> str:
        """Cache styled content with escape sequences"""
        cache_key = f"{content}:{style}"
        
        with self._lock:
            if cache_key in self._escape_cache:
                self._access_times[cache_key] = time.time()
                return self._escape_cache[cache_key]
            
            # Generate escape sequence
            if style:
                styled = f"[{style}]{content}[/{style}]"
            else:
                styled = content
            
            # Cache it
            if len(self._escape_cache) >= self.max_cache_size:
                self._evict_lru_entries()
            
            self._escape_cache[cache_key] = styled
            self._access_times[cache_key] = time.time()
            return styled
    
    def format_cached(self, template: str, *args, **kwargs) -> str:
        """Cache formatted strings"""
        cache_key = (template, args, tuple(sorted(kwargs.items())))
        
        with self._lock:
            if cache_key in self._format_cache:
                return self._format_cache[cache_key]
            
            # Format string
            try:
                formatted = template.format(*args, **kwargs)
            except (KeyError, ValueError, IndexError):
                return template  # Return template if formatting fails
            
            # Cache it
            if len(self._format_cache) >= self.max_cache_size:
                self._evict_format_entries()
            
            self._format_cache[cache_key] = formatted
            return formatted
    
    def _evict_lru_entries(self):
        """Evict least recently used string entries"""
        if not self._access_times:
            return
            
        # Find oldest 25% of entries
        sorted_entries = sorted(self._access_times.items(), key=lambda x: x[1])
        evict_count = len(sorted_entries) // 4
        
        for key, _ in sorted_entries[:evict_count]:
            self._string_cache.pop(key, None)
            self._escape_cache.pop(key, None)
            del self._access_times[key]
    
    def _evict_format_entries(self):
        """Evict old format cache entries"""
        if len(self._format_cache) > self.max_cache_size * 0.8:
            # Remove 25% of entries
            items = list(self._format_cache.items())
            keep_count = int(len(items) * 0.75)
            self._format_cache = dict(items[-keep_count:])
    
    def get_stats(self) -> Dict[str, int]:
        """Get string pool statistics"""
        with self._lock:
            return {
                'string_cache_size': len(self._string_cache),
                'escape_cache_size': len(self._escape_cache),
                'format_cache_size': len(self._format_cache),
                'total_cached': len(self._string_cache) + len(self._escape_cache) + len(self._format_cache)
            }
    
    def clear_cache(self):
        """Clear all caches"""
        with self._lock:
            self._string_cache.clear()
            self._escape_cache.clear()
            self._format_cache.clear()
            self._access_times.clear()
            self._populate_common_strings()


class MemoryLeakDetector:
    """Detect and track potential memory leaks"""
    
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.snapshots: List[Dict[str, Any]] = []
        self.max_snapshots = 10
        
        # Weak references to track objects
        self.tracked_objects: Dict[type, List[weakref.ref]] = defaultdict(list)
        self.leak_warnings: List[str] = []
        
        self.monitoring = False
        self._lock = threading.Lock()
    
    def start_monitoring(self):
        """Start memory leak monitoring"""
        self.monitoring = True
        import threading
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop memory leak monitoring"""
        self.monitoring = False
    
    def track_object(self, obj: Any):
        """Track an object for leak detection"""
        obj_type = type(obj)
        
        with self._lock:
            # Clean up dead references
            self.tracked_objects[obj_type] = [
                ref for ref in self.tracked_objects[obj_type] 
                if ref() is not None
            ]
            
            # Add new weak reference
            self.tracked_objects[obj_type].append(weakref.ref(obj))
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            self._take_snapshot()
            self._analyze_trends()
            time.sleep(self.check_interval)
    
    def _take_snapshot(self):
        """Take a memory usage snapshot"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            snapshot = {
                'timestamp': time.time(),
                'rss_mb': memory_info.rss / (1024 * 1024),
                'vms_mb': memory_info.vms / (1024 * 1024),
                'objects_tracked': {
                    obj_type.__name__: len(refs)
                    for obj_type, refs in self.tracked_objects.items()
                },
                'gc_stats': {
                    'collected': gc.get_count(),
                    'thresholds': gc.get_threshold()
                }
            }
            
            with self._lock:
                self.snapshots.append(snapshot)
                if len(self.snapshots) > self.max_snapshots:
                    self.snapshots = self.snapshots[-self.max_snapshots:]
                    
        except Exception:
            pass  # Ignore monitoring errors
    
    def _analyze_trends(self):
        """Analyze memory usage trends"""
        if len(self.snapshots) < 3:
            return
        
        # Check for consistent memory growth
        recent_snapshots = self.snapshots[-3:]
        memory_trend = [s['rss_mb'] for s in recent_snapshots]
        
        # Simple trend detection
        if all(memory_trend[i] < memory_trend[i + 1] for i in range(len(memory_trend) - 1)):
            growth_rate = (memory_trend[-1] - memory_trend[0]) / len(memory_trend)
            if growth_rate > 10:  # More than 10MB growth per snapshot
                warning = f"Potential memory leak detected: {growth_rate:.1f}MB growth rate"
                if warning not in self.leak_warnings:
                    self.leak_warnings.append(warning)
    
    def get_leak_report(self) -> Dict[str, Any]:
        """Get memory leak analysis report"""
        with self._lock:
            return {
                'monitoring_active': self.monitoring,
                'snapshots_taken': len(self.snapshots),
                'leak_warnings': self.leak_warnings.copy(),
                'tracked_objects': {
                    obj_type.__name__: len(refs)
                    for obj_type, refs in self.tracked_objects.items()
                },
                'current_memory_mb': self.snapshots[-1]['rss_mb'] if self.snapshots else 0
            }


class BufferManager:
    """Efficient buffer management for text and UI elements"""
    
    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        
        # Circular buffers for different content types
        self.text_buffer: deque[str] = deque(maxlen=max_buffer_size)
        self.panel_buffer: deque[Panel] = deque(maxlen=max_buffer_size // 2)
        self.table_buffer: deque[Table] = deque(maxlen=max_buffer_size // 4)
        
        # Message history with efficient access patterns
        self.message_history: deque[Dict[str, Any]] = deque(maxlen=max_buffer_size)
        self.recent_messages_index: Dict[str, int] = {}
        
        self._lock = threading.Lock()
    
    def add_text(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Add text to buffer with optional metadata"""
        with self._lock:
            self.text_buffer.append(text)
            
            if metadata:
                message_entry = {
                    'type': 'text',
                    'content': text,
                    'timestamp': time.time(),
                    'metadata': metadata
                }
                self.message_history.append(message_entry)
    
    def add_panel(self, panel: Panel, cache_key: Optional[str] = None):
        """Add panel to buffer with optional caching"""
        with self._lock:
            self.panel_buffer.append(panel)
            
            if cache_key:
                self.recent_messages_index[cache_key] = len(self.message_history)
            
            message_entry = {
                'type': 'panel',
                'content': panel,
                'timestamp': time.time(),
                'cache_key': cache_key
            }
            self.message_history.append(message_entry)
    
    def get_recent_messages(self, limit: int = 10, message_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent messages with optional type filtering"""
        with self._lock:
            messages = list(self.message_history)
            
            if message_type:
                messages = [m for m in messages if m['type'] == message_type]
            
            return messages[-limit:] if limit else messages
    
    def get_message_by_cache_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get message by cache key"""
        index = self.recent_messages_index.get(cache_key)
        if index is not None and index < len(self.message_history):
            return self.message_history[index]
        return None
    
    def clear_old_messages(self, max_age_seconds: int = 3600):
        """Clear messages older than specified age"""
        current_time = time.time()
        cutoff_time = current_time - max_age_seconds
        
        with self._lock:
            # Filter message history
            filtered_messages = deque(maxlen=self.max_buffer_size)
            for msg in self.message_history:
                if msg['timestamp'] > cutoff_time:
                    filtered_messages.append(msg)
            
            self.message_history = filtered_messages
            
            # Rebuild index
            self.recent_messages_index.clear()
            for i, msg in enumerate(self.message_history):
                cache_key = msg.get('cache_key')
                if cache_key:
                    self.recent_messages_index[cache_key] = i
    
    def get_buffer_stats(self) -> Dict[str, int]:
        """Get buffer usage statistics"""
        with self._lock:
            return {
                'text_buffer_size': len(self.text_buffer),
                'panel_buffer_size': len(self.panel_buffer),
                'table_buffer_size': len(self.table_buffer),
                'message_history_size': len(self.message_history),
                'cached_messages': len(self.recent_messages_index)
            }
    
    def optimize_memory(self):
        """Optimize memory usage by clearing old buffers"""
        self.clear_old_messages()
        
        # Force garbage collection
        gc.collect()


class MemoryOptimizer:
    """Main memory optimization coordinator"""
    
    def __init__(self):
        # Core components
        self.string_pool = StringPool()
        self.leak_detector = MemoryLeakDetector()
        self.buffer_manager = BufferManager()
        
        # Object pools for common Rich components
        self.text_pool = ObjectPool(
            lambda: Text(), 
            max_size=50,
            cleanup_callback=lambda t: setattr(t, '_text', [])
        )
        
        self.console_pool = ObjectPool(
            lambda: Console(), 
            max_size=5,
            cleanup_callback=lambda c: None  # Consoles don't need cleanup
        )
        
        # Performance tracking
        self.optimization_stats = {
            'string_cache_hits': 0,
            'object_pool_reuses': 0,
            'memory_optimizations': 0,
            'leak_warnings': 0
        }
        
        self.start_time = time.time()
        self._monitoring_active = False
    
    def start_monitoring(self):
        """Start comprehensive memory monitoring"""
        if not self._monitoring_active:
            self.leak_detector.start_monitoring()
            self._monitoring_active = True
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        if self._monitoring_active:
            self.leak_detector.stop_monitoring()
            self._monitoring_active = False
    
    @contextmanager
    def optimized_text(self):
        """Context manager for optimized Text objects"""
        with self.text_pool.acquire_context() as text:
            yield text
    
    @contextmanager
    def optimized_console(self):
        """Context manager for optimized Console objects"""
        with self.console_pool.acquire_context() as console:
            yield console
    
    def intern_string(self, s: str) -> str:
        """Intern string with caching"""
        self.optimization_stats['string_cache_hits'] += 1
        return self.string_pool.intern_string(s)
    
    def cache_styled_text(self, content: str, style: str = "") -> str:
        """Cache styled text content"""
        return self.string_pool.cache_escape_sequence(content, style)
    
    def format_cached(self, template: str, *args, **kwargs) -> str:
        """Use cached string formatting"""
        return self.string_pool.format_cached(template, *args, **kwargs)
    
    def track_object(self, obj: Any):
        """Track object for memory leak detection"""
        self.leak_detector.track_object(obj)
    
    def add_message_to_buffer(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Add message to efficient buffer"""
        self.buffer_manager.add_text(message, metadata)
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from buffer"""
        return self.buffer_manager.get_recent_messages(limit)
    
    def optimize_memory_usage(self):
        """Perform comprehensive memory optimization"""
        self.optimization_stats['memory_optimizations'] += 1
        
        # Clear caches
        self.string_pool.clear_cache()
        self.buffer_manager.optimize_memory()
        
        # Clear object pools
        self.text_pool.clear()
        
        # Force garbage collection
        gc.collect()
    
    def get_memory_stats(self) -> MemoryStats:
        """Get comprehensive memory statistics"""
        try:
            process = psutil.Process()
            current_memory = process.memory_info().rss / (1024 * 1024)
        except:
            current_memory = 0.0
        
        # Calculate pool efficiency
        text_stats = self.text_pool.get_stats()
        pool_efficiency = text_stats.get('efficiency', 0.0)
        
        # String pool stats
        string_stats = self.string_pool.get_stats()
        
        # Memory leak analysis
        leak_report = self.leak_detector.get_leak_report()
        
        return MemoryStats(
            current_usage_mb=current_memory,
            peak_usage_mb=getattr(self, '_peak_memory', current_memory),
            pool_efficiency=pool_efficiency,
            cache_hit_ratio=self.optimization_stats['string_cache_hits'] / max(1, time.time() - self.start_time),
            gc_collections=sum(gc.get_count()),
            string_pool_size=string_stats['total_cached'],
            object_pool_sizes={
                'text_pool': text_stats['pool_size'],
                'console_pool': self.console_pool.get_stats()['pool_size']
            },
            memory_leaks_detected=len(leak_report['leak_warnings'])
        )
    
    def display_memory_dashboard(self):
        """Display memory optimization dashboard"""
        console = Console()
        stats = self.get_memory_stats()
        
        # Memory usage table
        memory_table = Table(title="Memory Optimization Dashboard")
        memory_table.add_column("Metric", style="cyan")
        memory_table.add_column("Value", style="green")
        memory_table.add_column("Status", style="yellow")
        
        # Memory usage
        memory_status = "🟢 Excellent" if stats.current_usage_mb < 100 else "🟡 Good" if stats.current_usage_mb < 200 else "🔴 High"
        memory_table.add_row("Memory Usage", f"{stats.current_usage_mb:.1f}MB", memory_status)
        
        # Pool efficiency
        efficiency_status = "🟢 Excellent" if stats.pool_efficiency > 0.8 else "🟡 Good" if stats.pool_efficiency > 0.5 else "🔴 Poor"
        memory_table.add_row("Pool Efficiency", f"{stats.pool_efficiency:.1%}", efficiency_status)
        
        # String cache
        memory_table.add_row("String Cache Size", f"{stats.string_pool_size:,}", "ℹ️ Active")
        
        # Memory leaks
        leak_status = "🟢 Clean" if stats.memory_leaks_detected == 0 else f"🔴 {stats.memory_leaks_detected} warnings"
        memory_table.add_row("Memory Leaks", str(stats.memory_leaks_detected), leak_status)
        
        console.print(memory_table)
        
        # Object pools table
        pools_table = Table(title="Object Pool Status")
        pools_table.add_column("Pool", style="cyan")
        pools_table.add_column("Size", style="white")
        pools_table.add_column("Efficiency", style="green")
        
        for pool_name, size in stats.object_pool_sizes.items():
            pools_table.add_row(pool_name.replace('_', ' ').title(), str(size), f"{stats.pool_efficiency:.1%}")
        
        console.print(pools_table)


# Global memory optimizer instance
_global_memory_optimizer: Optional[MemoryOptimizer] = None

def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer instance"""
    global _global_memory_optimizer
    if _global_memory_optimizer is None:
        _global_memory_optimizer = MemoryOptimizer()
    return _global_memory_optimizer

def intern_string(s: str) -> str:
    """Convenient function to intern strings"""
    return get_memory_optimizer().intern_string(s)

def cache_styled_text(content: str, style: str = "") -> str:
    """Convenient function to cache styled text"""
    return get_memory_optimizer().cache_styled_text(content, style)

@contextmanager
def optimized_text():
    """Context manager for optimized Text objects"""
    with get_memory_optimizer().optimized_text() as text:
        yield text

@contextmanager
def optimized_console():
    """Context manager for optimized Console objects"""
    with get_memory_optimizer().optimized_console() as console:
        yield console

def optimize_memory():
    """Perform memory optimization"""
    get_memory_optimizer().optimize_memory_usage()