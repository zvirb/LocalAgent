"""
Base Command Classes
Foundation classes for CLI command implementation
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from rich.console import Console

from ..core.context import CLIContext
from ..ui.display import DisplayManager


class CommandStatus(Enum):
    """Command execution status"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandResult:
    """Result of command execution"""
    status: CommandStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class BaseCommand(ABC):
    """
    Abstract base class for CLI commands
    Provides common functionality and structure
    """
    
    def __init__(self, context: CLIContext, display_manager: DisplayManager):
        self.context = context
        self.display_manager = display_manager
        self.console = Console()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description"""
        pass
    
    @property
    def aliases(self) -> List[str]:
        """Command aliases (optional)"""
        return []
    
    @abstractmethod
    async def execute(self, **kwargs) -> CommandResult:
        """Execute the command with given parameters"""
        pass
    
    async def validate_parameters(self, **kwargs) -> bool:
        """Validate command parameters before execution"""
        return True
    
    def get_help_text(self) -> str:
        """Get detailed help text for the command"""
        return f"{self.name}: {self.description}"
    
    async def pre_execute(self, **kwargs) -> bool:
        """Pre-execution hook (return False to cancel execution)"""
        return True
    
    async def post_execute(self, result: CommandResult, **kwargs) -> None:
        """Post-execution hook"""
        pass
    
    def _create_success_result(self, message: str, data: Optional[Dict[str, Any]] = None) -> CommandResult:
        """Helper to create success result"""
        return CommandResult(
            status=CommandStatus.SUCCESS,
            message=message,
            data=data
        )
    
    def _create_error_result(self, message: str, error: Optional[str] = None) -> CommandResult:
        """Helper to create error result"""
        return CommandResult(
            status=CommandStatus.FAILED,
            message=message,
            error=error
        )
    
    def _create_partial_result(self, message: str, data: Optional[Dict[str, Any]] = None) -> CommandResult:
        """Helper to create partial success result"""
        return CommandResult(
            status=CommandStatus.PARTIAL,
            message=message,
            data=data
        )


class AsyncCommand(BaseCommand):
    """
    Base class for asynchronous commands
    Provides progress tracking and cancellation support
    """
    
    def __init__(self, context: CLIContext, display_manager: DisplayManager):
        super().__init__(context, display_manager)
        self.cancelled = False
        self.progress_callback: Optional[callable] = None
    
    async def execute_with_progress(self, progress_callback: Optional[callable] = None, **kwargs) -> CommandResult:
        """Execute command with progress tracking"""
        self.progress_callback = progress_callback
        
        try:
            return await self.execute(**kwargs)
        finally:
            self.progress_callback = None
    
    def cancel(self):
        """Cancel command execution"""
        self.cancelled = True
    
    def is_cancelled(self) -> bool:
        """Check if command was cancelled"""
        return self.cancelled
    
    async def update_progress(self, message: str, progress: Optional[float] = None):
        """Update progress if callback is available"""
        if self.progress_callback:
            await self.progress_callback(message, progress)
    
    async def check_cancellation(self):
        """Check for cancellation and raise if cancelled"""
        if self.cancelled:
            raise asyncio.CancelledError("Command cancelled by user")


class InteractiveCommand(BaseCommand):
    """
    Base class for interactive commands
    Provides user interaction capabilities
    """
    
    def __init__(self, context: CLIContext, display_manager: DisplayManager):
        super().__init__(context, display_manager)
        from ..ui.prompts import InteractivePrompts
        self.prompts = InteractivePrompts(self.console)
    
    async def confirm_action(self, message: str, default: bool = False) -> bool:
        """Ask user for confirmation"""
        return self.prompts.ask_boolean(message, default)
    
    async def get_user_choice(self, question: str, choices: List[str], default: Optional[str] = None) -> str:
        """Get user choice from list of options"""
        return self.prompts.ask_choice(question, choices, default)
    
    async def get_user_input(self, question: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """Get text input from user"""
        return self.prompts.ask_text(question, default, required)