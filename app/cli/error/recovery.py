"""
Error Recovery Management System
Comprehensive error handling with recovery strategies
"""

import asyncio
import traceback
import logging
from typing import Dict, Any, List, Optional, Type, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.config import LocalAgentConfig


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryResult(Enum):
    """Recovery attempt results"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class ErrorContext:
    """Context information for error analysis"""
    error_type: str
    error_message: str
    traceback: str
    timestamp: datetime
    command: Optional[str] = None
    provider: Optional[str] = None
    phase: Optional[str] = None
    agent: Optional[str] = None
    user_input: Optional[str] = None
    system_state: Dict[str, Any] = field(default_factory=dict)
    previous_errors: List['ErrorContext'] = field(default_factory=list)


class RecoveryStrategy:
    """Base class for error recovery strategies"""
    
    def __init__(self, name: str, description: str, severity_threshold: ErrorSeverity = ErrorSeverity.MEDIUM):
        self.name = name
        self.description = description
        self.severity_threshold = severity_threshold
        self.success_count = 0
        self.failure_count = 0
    
    async def can_handle(self, error_context: ErrorContext) -> bool:
        """Check if this strategy can handle the error"""
        return True
    
    async def execute(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Execute the recovery strategy"""
        raise NotImplementedError
    
    def get_success_rate(self) -> float:
        """Get success rate of this strategy"""
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class ConfigurationRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for configuration-related errors"""
    
    def __init__(self):
        super().__init__(
            "Configuration Recovery",
            "Attempts to recover from configuration errors",
            ErrorSeverity.HIGH
        )
    
    async def can_handle(self, error_context: ErrorContext) -> bool:
        config_keywords = ['config', 'configuration', 'settings', 'invalid', 'missing']
        return any(keyword in error_context.error_message.lower() for keyword in config_keywords)
    
    async def execute(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Attempt to recover from configuration errors"""
        try:
            # Try to reload configuration
            from ..core.config import ConfigurationManager
            
            config_manager = ConfigurationManager()
            new_config = await config_manager.load_configuration()
            
            # Validate new configuration
            validation_result = await config_manager.validate_configuration()
            
            if validation_result['valid']:
                self.success_count += 1
                return RecoveryResult.SUCCESS
            else:
                self.failure_count += 1
                return RecoveryResult.PARTIAL
                
        except Exception:
            self.failure_count += 1
            return RecoveryResult.FAILED


class ProviderRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for provider connection errors"""
    
    def __init__(self):
        super().__init__(
            "Provider Recovery",
            "Attempts to recover from provider connection issues",
            ErrorSeverity.HIGH
        )
    
    async def can_handle(self, error_context: ErrorContext) -> bool:
        provider_keywords = ['provider', 'connection', 'timeout', 'api', 'network', 'unreachable']
        return any(keyword in error_context.error_message.lower() for keyword in provider_keywords)
    
    async def execute(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Attempt to recover from provider errors"""
        try:
            # If the error is from a specific provider, try fallback
            if error_context.provider:
                # Try to switch to a different provider
                enabled_providers = config.get_enabled_providers()
                
                if len(enabled_providers) > 1:
                    # Switch to next available provider
                    current_index = enabled_providers.index(error_context.provider)
                    next_provider = enabled_providers[(current_index + 1) % len(enabled_providers)]
                    
                    # This would need integration with actual provider system
                    self.success_count += 1
                    return RecoveryResult.PARTIAL
            
            # Generic retry with exponential backoff
            await asyncio.sleep(2)  # Wait before retry
            
            self.success_count += 1
            return RecoveryResult.RETRY
            
        except Exception:
            self.failure_count += 1
            return RecoveryResult.FAILED


class WorkflowRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for workflow execution errors"""
    
    def __init__(self):
        super().__init__(
            "Workflow Recovery",
            "Attempts to recover from workflow execution failures",
            ErrorSeverity.MEDIUM
        )
    
    async def can_handle(self, error_context: ErrorContext) -> bool:
        workflow_keywords = ['workflow', 'phase', 'agent', 'orchestration', 'execution']
        return any(keyword in error_context.error_message.lower() for keyword in workflow_keywords)
    
    async def execute(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Attempt to recover from workflow errors"""
        try:
            # If error is from a specific phase, try to restart that phase
            if error_context.phase:
                # Implement phase restart logic
                pass
            
            # If error is from a specific agent, try different decomposition
            if error_context.agent:
                # Implement agent recovery logic
                pass
            
            # Generic workflow restart with reduced parallelism
            self.success_count += 1
            return RecoveryResult.RETRY
            
        except Exception:
            self.failure_count += 1
            return RecoveryResult.FAILED


class MemoryRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for memory/resource errors"""
    
    def __init__(self):
        super().__init__(
            "Memory Recovery",
            "Attempts to recover from memory and resource issues",
            ErrorSeverity.HIGH
        )
    
    async def can_handle(self, error_context: ErrorContext) -> bool:
        memory_keywords = ['memory', 'resource', 'disk', 'space', 'allocation', 'timeout']
        return any(keyword in error_context.error_message.lower() for keyword in memory_keywords)
    
    async def execute(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Attempt to recover from memory errors"""
        try:
            # Reduce parallel agent count
            if hasattr(config.orchestration, 'max_parallel_agents'):
                # Temporarily reduce parallelism
                pass
            
            # Clear caches and temporary files
            # This would integrate with actual cleanup systems
            
            # Force garbage collection
            import gc
            gc.collect()
            
            self.success_count += 1
            return RecoveryResult.PARTIAL
            
        except Exception:
            self.failure_count += 1
            return RecoveryResult.FAILED


class ErrorHandler:
    """Individual error handler with pattern matching"""
    
    def __init__(self, name: str, error_patterns: List[str], 
                 handler_func: Callable[[ErrorContext, LocalAgentConfig], Any],
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        self.name = name
        self.error_patterns = error_patterns
        self.handler_func = handler_func
        self.severity = severity
        self.usage_count = 0
    
    def matches(self, error_context: ErrorContext) -> bool:
        """Check if this handler matches the error"""
        error_text = error_context.error_message.lower()
        return any(pattern.lower() in error_text for pattern in self.error_patterns)
    
    async def handle(self, error_context: ErrorContext, config: LocalAgentConfig) -> Any:
        """Handle the error"""
        self.usage_count += 1
        return await self.handler_func(error_context, config)


class ErrorRecoveryManager:
    """
    Centralized error recovery management system
    Provides intelligent error handling and recovery strategies
    """
    
    def __init__(self, config: LocalAgentConfig):
        self.config = config
        self.console = Console()
        
        # Recovery strategies
        self.recovery_strategies: List[RecoveryStrategy] = []
        self._initialize_recovery_strategies()
        
        # Error handlers
        self.error_handlers: List[ErrorHandler] = []
        self._initialize_error_handlers()
        
        # Error tracking
        self.error_history: List[ErrorContext] = []
        self.max_error_history = 100
        self.recovery_attempts: Dict[str, int] = {}
        self.max_recovery_attempts = 3
        
        # Logging
        self.logger = logging.getLogger('localagent.recovery')
    
    def _initialize_recovery_strategies(self):
        """Initialize default recovery strategies"""
        self.recovery_strategies = [
            ConfigurationRecoveryStrategy(),
            ProviderRecoveryStrategy(),
            WorkflowRecoveryStrategy(),
            MemoryRecoveryStrategy()
        ]
    
    def _initialize_error_handlers(self):
        """Initialize default error handlers"""
        # Configuration errors
        config_handler = ErrorHandler(
            "Configuration Errors",
            ["config", "configuration", "settings", "invalid"],
            self._handle_configuration_error,
            ErrorSeverity.HIGH
        )
        
        # Provider errors
        provider_handler = ErrorHandler(
            "Provider Errors", 
            ["provider", "connection", "api", "timeout", "network"],
            self._handle_provider_error,
            ErrorSeverity.HIGH
        )
        
        # Workflow errors
        workflow_handler = ErrorHandler(
            "Workflow Errors",
            ["workflow", "phase", "agent", "orchestration"],
            self._handle_workflow_error,
            ErrorSeverity.MEDIUM
        )
        
        # Memory errors
        memory_handler = ErrorHandler(
            "Memory Errors",
            ["memory", "resource", "allocation", "disk space"],
            self._handle_memory_error,
            ErrorSeverity.HIGH
        )
        
        self.error_handlers = [config_handler, provider_handler, workflow_handler, memory_handler]
    
    async def handle_error(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> RecoveryResult:
        """
        Handle an error with automatic recovery attempts
        """
        error_context = self._create_error_context(exception, context or {})
        
        # Log the error
        self._log_error(error_context)
        
        # Add to error history
        self._add_to_history(error_context)
        
        # Check for repeated errors (circuit breaker pattern)
        if self._is_repeated_error(error_context):
            self._display_repeated_error_warning(error_context)
            return RecoveryResult.FAILED
        
        # Try error handlers first
        handler_result = await self._try_error_handlers(error_context)
        if handler_result != RecoveryResult.FAILED:
            return handler_result
        
        # Try recovery strategies
        recovery_result = await self._try_recovery_strategies(error_context)
        
        # Display recovery results
        self._display_recovery_results(error_context, recovery_result)
        
        return recovery_result
    
    async def handle_workflow_error(self, exception: Exception, workflow_context: Dict[str, Any] = None) -> RecoveryResult:
        """Handle workflow-specific errors"""
        context = workflow_context or {}
        context['error_category'] = 'workflow'
        
        return await self.handle_error(exception, context)
    
    async def handle_provider_error(self, exception: Exception, provider: str, model: Optional[str] = None) -> RecoveryResult:
        """Handle provider-specific errors"""
        context = {
            'error_category': 'provider',
            'provider': provider,
            'model': model
        }
        
        return await self.handle_error(exception, context)
    
    def _create_error_context(self, exception: Exception, context: Dict[str, Any]) -> ErrorContext:
        """Create error context from exception and additional context"""
        return ErrorContext(
            error_type=type(exception).__name__,
            error_message=str(exception),
            traceback=traceback.format_exc(),
            timestamp=datetime.now(),
            command=context.get('command'),
            provider=context.get('provider'),
            phase=context.get('phase'),
            agent=context.get('agent'),
            user_input=context.get('user_input'),
            system_state=context.get('system_state', {}),
            previous_errors=self.error_history[-5:]  # Last 5 errors
        )
    
    def _log_error(self, error_context: ErrorContext):
        """Log error with appropriate level"""
        log_message = f"Error in {error_context.command or 'unknown command'}: {error_context.error_message}"
        
        if error_context.provider:
            log_message += f" (Provider: {error_context.provider})"
        
        self.logger.error(log_message, extra={
            'error_type': error_context.error_type,
            'timestamp': error_context.timestamp,
            'traceback': error_context.traceback
        })
    
    def _add_to_history(self, error_context: ErrorContext):
        """Add error to history with size limit"""
        self.error_history.append(error_context)
        
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
    
    def _is_repeated_error(self, error_context: ErrorContext) -> bool:
        """Check if this is a repeated error (circuit breaker)"""
        error_key = f"{error_context.error_type}:{error_context.command}:{error_context.provider}"
        
        # Count recent occurrences (within last 10 minutes)
        recent_threshold = datetime.now() - timedelta(minutes=10)
        recent_count = sum(
            1 for error in self.error_history[-10:]
            if (error.error_type == error_context.error_type and
                error.command == error_context.command and
                error.provider == error_context.provider and
                error.timestamp > recent_threshold)
        )
        
        return recent_count >= 3  # 3 identical errors in 10 minutes
    
    def _display_repeated_error_warning(self, error_context: ErrorContext):
        """Display warning for repeated errors"""
        warning_text = f"""
[bold red]🚨 Repeated Error Detected[/bold red]

[yellow]The same error has occurred multiple times recently:[/yellow]
{error_context.error_message}

[yellow]Recovery attempts have been suspended to prevent infinite loops.[/yellow]
[blue]Please check the system configuration and try again later.[/blue]
        """
        
        panel = Panel(warning_text, title="Error Recovery Suspended", border_style="red")
        self.console.print(panel)
    
    async def _try_error_handlers(self, error_context: ErrorContext) -> RecoveryResult:
        """Try specialized error handlers"""
        for handler in self.error_handlers:
            if handler.matches(error_context):
                try:
                    result = await handler.handle(error_context, self.config)
                    if result != RecoveryResult.FAILED:
                        return result
                except Exception as e:
                    self.logger.error(f"Error handler {handler.name} failed: {e}")
        
        return RecoveryResult.FAILED
    
    async def _try_recovery_strategies(self, error_context: ErrorContext) -> RecoveryResult:
        """Try recovery strategies in order of suitability"""
        # Sort strategies by their ability to handle this error
        suitable_strategies = []
        
        for strategy in self.recovery_strategies:
            if await strategy.can_handle(error_context):
                suitable_strategies.append(strategy)
        
        # Sort by success rate (highest first)
        suitable_strategies.sort(key=lambda s: s.get_success_rate(), reverse=True)
        
        # Try each strategy
        for strategy in suitable_strategies:
            try:
                result = await strategy.execute(error_context, self.config)
                
                if result in [RecoveryResult.SUCCESS, RecoveryResult.PARTIAL, RecoveryResult.RETRY]:
                    return result
                    
            except Exception as e:
                self.logger.error(f"Recovery strategy {strategy.name} failed: {e}")
        
        return RecoveryResult.FAILED
    
    def _display_recovery_results(self, error_context: ErrorContext, result: RecoveryResult):
        """Display recovery attempt results"""
        if result == RecoveryResult.SUCCESS:
            self.console.print("[green]✅ Error recovered successfully[/green]")
        elif result == RecoveryResult.PARTIAL:
            self.console.print("[yellow]⚠️  Partial recovery achieved[/yellow]")
        elif result == RecoveryResult.RETRY:
            self.console.print("[blue]🔄 Recovery suggests retry[/blue]")
        else:
            self.console.print("[red]❌ Recovery failed[/red]")
    
    # Default error handlers
    
    async def _handle_configuration_error(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Handle configuration-related errors"""
        try:
            from ..core.config import ConfigurationManager
            
            config_manager = ConfigurationManager()
            
            # Try to reload configuration
            new_config = await config_manager.load_configuration()
            
            # Validate configuration
            validation_result = await config_manager.validate_configuration()
            
            if validation_result['valid']:
                return RecoveryResult.SUCCESS
            else:
                return RecoveryResult.PARTIAL
                
        except Exception:
            return RecoveryResult.FAILED
    
    async def _handle_provider_error(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Handle provider-related errors"""
        try:
            # Try to switch to fallback provider
            enabled_providers = config.get_enabled_providers()
            
            if len(enabled_providers) > 1 and error_context.provider:
                # This would need integration with provider system
                return RecoveryResult.PARTIAL
            
            return RecoveryResult.RETRY
            
        except Exception:
            return RecoveryResult.FAILED
    
    async def _handle_workflow_error(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Handle workflow-related errors"""
        try:
            # Suggest workflow restart with modified parameters
            return RecoveryResult.RETRY
            
        except Exception:
            return RecoveryResult.FAILED
    
    async def _handle_memory_error(self, error_context: ErrorContext, config: LocalAgentConfig) -> RecoveryResult:
        """Handle memory-related errors"""
        try:
            # Force garbage collection
            import gc
            gc.collect()
            
            return RecoveryResult.PARTIAL
            
        except Exception:
            return RecoveryResult.FAILED
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error and recovery statistics"""
        if not self.error_history:
            return {"total_errors": 0}
        
        # Error type distribution
        error_types = {}
        for error in self.error_history:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
        
        # Provider error distribution
        provider_errors = {}
        for error in self.error_history:
            if error.provider:
                provider_errors[error.provider] = provider_errors.get(error.provider, 0) + 1
        
        # Recovery strategy performance
        strategy_stats = {}
        for strategy in self.recovery_strategies:
            strategy_stats[strategy.name] = {
                'success_count': strategy.success_count,
                'failure_count': strategy.failure_count,
                'success_rate': strategy.get_success_rate()
            }
        
        # Handler usage
        handler_stats = {}
        for handler in self.error_handlers:
            handler_stats[handler.name] = handler.usage_count
        
        return {
            'total_errors': len(self.error_history),
            'error_types': error_types,
            'provider_errors': provider_errors,
            'recovery_strategies': strategy_stats,
            'handler_usage': handler_stats,
            'recent_errors': len([e for e in self.error_history if e.timestamp > datetime.now() - timedelta(hours=1)])
        }
    
    def display_error_statistics(self):
        """Display error and recovery statistics"""
        stats = self.get_error_statistics()
        
        if stats['total_errors'] == 0:
            self.console.print("[green]No errors recorded[/green]")
            return
        
        # Main statistics table
        stats_table = Table(title="Error Recovery Statistics", show_header=True, header_style="bold magenta")
        stats_table.add_column("Metric", style="cyan", width=25)
        stats_table.add_column("Value", style="white", width=15)
        stats_table.add_column("Details", style="blue")
        
        stats_table.add_row("Total Errors", str(stats['total_errors']), "All recorded errors")
        stats_table.add_row("Recent Errors", str(stats['recent_errors']), "Errors in last hour")
        
        # Error types
        if stats['error_types']:
            top_error = max(stats['error_types'].items(), key=lambda x: x[1])
            stats_table.add_row("Most Common Error", top_error[0], f"{top_error[1]} occurrences")
        
        # Provider errors
        if stats['provider_errors']:
            problematic_provider = max(stats['provider_errors'].items(), key=lambda x: x[1])
            stats_table.add_row("Most Problematic Provider", problematic_provider[0], f"{problematic_provider[1]} errors")
        
        self.console.print(stats_table)
        
        # Recovery strategy performance
        if stats['recovery_strategies']:
            strategy_table = Table(title="Recovery Strategy Performance", show_header=True, header_style="bold blue")
            strategy_table.add_column("Strategy", style="cyan", width=20)
            strategy_table.add_column("Success Rate", style="green", width=12)
            strategy_table.add_column("Successes", style="white", width=10)
            strategy_table.add_column("Failures", style="red", width=10)
            
            for strategy_name, strategy_data in stats['recovery_strategies'].items():
                success_rate = f"{strategy_data['success_rate']:.1%}"
                successes = str(strategy_data['success_count'])
                failures = str(strategy_data['failure_count'])
                
                strategy_table.add_row(strategy_name, success_rate, successes, failures)
            
            self.console.print(strategy_table)
    
    async def cleanup(self):
        """Cleanup recovery manager resources"""
        # Clear old error history
        cutoff_time = datetime.now() - timedelta(days=7)
        self.error_history = [
            error for error in self.error_history 
            if error.timestamp > cutoff_time
        ]