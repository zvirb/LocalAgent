"""
CLI Context Management
Shared context and state management across commands
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import time
from dataclasses import dataclass, field

from .config import LocalAgentConfig

@dataclass
class CLISession:
    """Information about the current CLI session"""
    session_id: str
    start_time: float
    user: str
    working_directory: Path
    environment: Dict[str, str] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class CommandContext:
    """Context for a single command execution"""
    command_name: str
    start_time: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    execution_id: str = ""
    parent_context: Optional['CommandContext'] = None

class CLIContext:
    """
    Shared context and state management for LocalAgent CLI
    Maintains session state, configuration, and execution context
    """
    
    def __init__(self, config: LocalAgentConfig, debug_mode: bool = False, log_level: str = "INFO"):
        self.config = config
        self.debug_mode = debug_mode
        self.log_level = log_level
        
        # Session management
        self.session = CLISession(
            session_id=self._generate_session_id(),
            start_time=time.time(),
            user=self._get_current_user(),
            working_directory=Path.cwd()
        )
        
        # Command execution context
        self.current_command: Optional[CommandContext] = None
        self.command_history: List[CommandContext] = []
        
        # Shared state
        self.shared_state: Dict[str, Any] = {}
        
        # Provider state
        self.provider_manager = None
        self.current_provider = config.default_provider
        
        # Plugin state
        self.plugin_manager = None
        
    def _generate_session_id(self) -> str:
        """Generate unique session identifier"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_current_user(self) -> str:
        """Get current system user"""
        import getpass
        try:
            return getpass.getuser()
        except Exception:
            return "unknown"
    
    def start_command(self, command_name: str, parameters: Dict[str, Any] = None) -> CommandContext:
        """Start tracking a new command execution"""
        import uuid
        
        context = CommandContext(
            command_name=command_name,
            start_time=time.time(),
            parameters=parameters or {},
            execution_id=str(uuid.uuid4())[:8],
            parent_context=self.current_command
        )
        
        self.current_command = context
        return context
    
    def end_command(self, context: CommandContext, success: bool = True, error: str = None) -> None:
        """End command execution tracking"""
        if context == self.current_command:
            self.current_command = context.parent_context
        
        # Add to session history
        command_record = {
            'command_name': context.command_name,
            'execution_id': context.execution_id,
            'start_time': context.start_time,
            'end_time': time.time(),
            'duration': time.time() - context.start_time,
            'parameters': context.parameters,
            'success': success,
            'error': error
        }
        
        self.session.history.append(command_record)
        self.command_history.append(context)
    
    def set_shared_value(self, key: str, value: Any) -> None:
        """Set a value in shared state"""
        self.shared_state[key] = value
    
    def get_shared_value(self, key: str, default: Any = None) -> Any:
        """Get a value from shared state"""
        return self.shared_state.get(key, default)
    
    def remove_shared_value(self, key: str) -> None:
        """Remove a value from shared state"""
        self.shared_state.pop(key, None)
    
    def clear_shared_state(self) -> None:
        """Clear all shared state"""
        self.shared_state.clear()
    
    def set_current_provider(self, provider_name: str) -> bool:
        """Set the current active provider"""
        if provider_name in self.config.providers:
            self.current_provider = provider_name
            return True
        return False
    
    def get_current_provider(self) -> str:
        """Get the current active provider"""
        return self.current_provider
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session"""
        return {
            'session_id': self.session.session_id,
            'start_time': self.session.start_time,
            'duration': time.time() - self.session.start_time,
            'user': self.session.user,
            'working_directory': str(self.session.working_directory),
            'commands_executed': len(self.session.history),
            'current_provider': self.current_provider,
            'debug_mode': self.debug_mode,
            'log_level': self.log_level
        }
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics for the session"""
        if not self.session.history:
            return {
                'total_commands': 0,
                'successful_commands': 0,
                'failed_commands': 0,
                'average_duration': 0,
                'total_duration': 0
            }
        
        successful = sum(1 for cmd in self.session.history if cmd['success'])
        failed = len(self.session.history) - successful
        total_duration = sum(cmd['duration'] for cmd in self.session.history)
        average_duration = total_duration / len(self.session.history)
        
        return {
            'total_commands': len(self.session.history),
            'successful_commands': successful,
            'failed_commands': failed,
            'success_rate': successful / len(self.session.history) * 100,
            'average_duration': average_duration,
            'total_duration': total_duration
        }
    
    def get_command_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get command execution history"""
        history = self.session.history.copy()
        if limit:
            history = history[-limit:]
        return history
    
    def get_recent_errors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent command errors"""
        errors = [cmd for cmd in self.session.history if not cmd['success'] and cmd['error']]
        return errors[-limit:] if errors else []
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return self.debug_mode
    
    def should_log(self, level: str) -> bool:
        """Check if a log level should be output"""
        log_levels = {
            'DEBUG': 10,
            'INFO': 20,
            'WARNING': 30,
            'ERROR': 40,
            'CRITICAL': 50
        }
        
        current_level = log_levels.get(self.log_level.upper(), 20)
        check_level = log_levels.get(level.upper(), 20)
        
        return check_level >= current_level
    
    def export_session_data(self) -> Dict[str, Any]:
        """Export complete session data"""
        return {
            'session': {
                'session_id': self.session.session_id,
                'start_time': self.session.start_time,
                'user': self.session.user,
                'working_directory': str(self.session.working_directory),
                'environment': self.session.environment
            },
            'history': self.session.history,
            'stats': self.get_execution_stats(),
            'config': {
                'default_provider': self.config.default_provider,
                'providers': list(self.config.providers.keys()),
                'debug_mode': self.debug_mode,
                'log_level': self.log_level
            },
            'shared_state': self.shared_state
        }
    
    async def persist_session(self, file_path: Optional[Path] = None) -> None:
        """Persist session data to file"""
        if not file_path:
            file_path = self.config.config_dir / f"session_{self.session.session_id}.json"
        
        from ..io.atomic import AtomicFileManager
        
        session_data = self.export_session_data()
        await AtomicFileManager.write_json(file_path, session_data)
    
    async def load_session(self, file_path: Path) -> bool:
        """Load session data from file"""
        try:
            import json
            import aiofiles
            
            async with aiofiles.open(file_path, 'r') as f:
                session_data = json.loads(await f.read())
            
            # Restore session data (selective restore to avoid conflicts)
            if 'shared_state' in session_data:
                self.shared_state.update(session_data['shared_state'])
            
            # Optionally restore command history
            if 'history' in session_data:
                self.session.history.extend(session_data['history'])
            
            return True
            
        except Exception:
            return False