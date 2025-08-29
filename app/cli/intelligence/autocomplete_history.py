"""
Autocomplete History Manager
============================

Secure storage and retrieval of command history for autocomplete suggestions.
Implements privacy controls, encryption, and intelligent history management.
"""

import json
import time
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from collections import deque, defaultdict
from datetime import datetime, timedelta
import re
import logging

# Security imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    import base64
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

@dataclass
class CommandHistoryEntry:
    """Single command history entry with metadata"""
    command: str
    timestamp: float
    success: bool = True
    execution_time: float = 0.0
    provider: Optional[str] = None
    working_directory: Optional[str] = None
    arguments: List[str] = field(default_factory=list)
    frequency_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandHistoryEntry':
        """Create from dictionary"""
        return cls(**data)

@dataclass 
class AutocompleteConfig:
    """Configuration for autocomplete behavior"""
    max_history_size: int = 10000
    max_suggestions: int = 10
    min_confidence: float = 0.1
    enable_fuzzy: bool = True
    fuzzy_threshold: float = 0.6
    enable_ml_predictions: bool = True
    enable_encryption: bool = True
    sensitive_pattern_filters: List[str] = field(default_factory=lambda: [
        r'api[_-]?key',
        r'password',
        r'token',
        r'secret',
        r'credential',
        r'auth'
    ])
    history_retention_days: int = 30
    deduplication_window: int = 100  # Don't suggest same command within N entries

class AutocompleteHistoryManager:
    """
    Manages command history for autocomplete with security and privacy features
    """
    
    def __init__(self, config_dir: Optional[Path] = None, config: Optional[AutocompleteConfig] = None):
        self.config_dir = config_dir or Path.home() / ".localagent"
        self.history_file = self.config_dir / "autocomplete_history.json"
        self.encrypted_history_file = self.config_dir / "autocomplete_history.enc"
        self.config = config or AutocompleteConfig()
        
        self.logger = logging.getLogger("AutocompleteHistory")
        
        # In-memory history cache
        self.history: deque = deque(maxlen=self.config.max_history_size)
        self.command_frequency: Dict[str, int] = defaultdict(int)
        self.command_success_rate: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))  # (success, total)
        
        # Security
        self.encryption_key: Optional[bytes] = None
        if ENCRYPTION_AVAILABLE and self.config.enable_encryption:
            self._initialize_encryption()
        
        # Session tracking
        self.session_id = hashlib.sha256(f"{os.getpid()}_{time.time()}".encode()).hexdigest()[:16]
        self.session_commands: List[str] = []
        
        # Load existing history
        self.load_history()
    
    def _initialize_encryption(self):
        """Initialize encryption key for secure storage"""
        key_file = self.config_dir / ".autocomplete_key"
        
        if key_file.exists() and os.stat(key_file).st_mode & 0o777 == 0o600:
            # Load existing key
            with open(key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new key
            self.encryption_key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with restricted permissions
            old_umask = os.umask(0o077)
            try:
                with open(key_file, 'wb') as f:
                    f.write(self.encryption_key)
            finally:
                os.umask(old_umask)
    
    def _sanitize_command(self, command: str) -> str:
        """Remove sensitive information from commands"""
        sanitized = command
        
        for pattern in self.config.sensitive_pattern_filters:
            # Replace sensitive values with placeholder
            sanitized = re.sub(
                rf'({pattern})[=:\s]+\S+',
                r'\1=<REDACTED>',
                sanitized,
                flags=re.IGNORECASE
            )
        
        return sanitized
    
    def add_command(self, 
                   command: str,
                   success: bool = True,
                   execution_time: float = 0.0,
                   provider: Optional[str] = None,
                   working_directory: Optional[str] = None,
                   arguments: Optional[List[str]] = None) -> None:
        """Add a command to history with metadata"""
        
        # Sanitize for storage
        sanitized_command = self._sanitize_command(command)
        
        # Create history entry
        entry = CommandHistoryEntry(
            command=sanitized_command,
            timestamp=time.time(),
            success=success,
            execution_time=execution_time,
            provider=provider,
            working_directory=working_directory or os.getcwd(),
            arguments=arguments or []
        )
        
        # Update history
        self.history.append(entry)
        self.session_commands.append(sanitized_command)
        
        # Update frequency tracking
        self.command_frequency[sanitized_command] += 1
        
        # Update success rate
        success_count, total_count = self.command_success_rate[sanitized_command]
        if success:
            success_count += 1
        total_count += 1
        self.command_success_rate[sanitized_command] = (success_count, total_count)
        
        # Calculate frequency score
        entry.frequency_score = self._calculate_frequency_score(sanitized_command)
        
        # Auto-save periodically
        if len(self.history) % 10 == 0:
            self.save_history()
    
    def _calculate_frequency_score(self, command: str) -> float:
        """Calculate frequency-based score for a command"""
        frequency = self.command_frequency.get(command, 0)
        success, total = self.command_success_rate.get(command, (0, 0))
        
        # Combine frequency and success rate
        freq_score = min(frequency / 100.0, 1.0)  # Normalize to 0-1
        success_score = success / total if total > 0 else 0.5
        
        # Time decay factor (recent commands score higher)
        recency_boost = 0.0
        for i, entry in enumerate(reversed(list(self.history)[-100:])):
            if entry.command == command:
                recency_boost = (100 - i) / 100.0
                break
        
        # Weighted combination
        return (freq_score * 0.3 + success_score * 0.3 + recency_boost * 0.4)
    
    def get_suggestions(self, 
                        partial: str,
                        context: Optional[Dict[str, Any]] = None,
                        max_suggestions: Optional[int] = None) -> List[Tuple[str, float]]:
        """Get autocomplete suggestions for partial command"""
        
        max_suggestions = max_suggestions or self.config.max_suggestions
        suggestions = []
        seen = set()
        
        # Check recent commands to avoid repetition
        recent_window = list(self.history)[-self.config.deduplication_window:]
        recent_commands = {e.command for e in recent_window}
        
        # 1. Exact prefix matches from history
        for entry in reversed(list(self.history)):
            if entry.command not in seen and entry.command not in recent_commands:
                if entry.command.startswith(partial):
                    confidence = entry.frequency_score * 1.0  # Full confidence for exact prefix
                    suggestions.append((entry.command, confidence))
                    seen.add(entry.command)
        
        # 2. Fuzzy matches if enabled
        if self.config.enable_fuzzy and len(suggestions) < max_suggestions:
            from difflib import SequenceMatcher
            
            for entry in reversed(list(self.history)):
                if entry.command not in seen and entry.command not in recent_commands:
                    similarity = SequenceMatcher(None, partial.lower(), entry.command.lower()).ratio()
                    
                    if similarity >= self.config.fuzzy_threshold:
                        confidence = entry.frequency_score * similarity
                        if confidence >= self.config.min_confidence:
                            suggestions.append((entry.command, confidence))
                            seen.add(entry.command)
        
        # 3. Context-aware suggestions
        if context:
            suggestions = self._apply_context_filtering(suggestions, context)
        
        # Sort by confidence and limit
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:max_suggestions]
    
    def _apply_context_filtering(self, 
                                 suggestions: List[Tuple[str, float]], 
                                 context: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Apply contextual filtering and boosting to suggestions"""
        
        filtered = []
        
        for command, confidence in suggestions:
            # Boost based on context
            boost = 1.0
            
            # Provider context
            if 'provider' in context:
                if context['provider'] in command:
                    boost *= 1.2
            
            # Working directory context
            if 'working_directory' in context:
                # Boost commands used in similar directories
                for entry in self.history:
                    if entry.command == command and entry.working_directory == context['working_directory']:
                        boost *= 1.1
                        break
            
            # Time of day patterns
            if 'time_of_day' in context:
                hour = context['time_of_day']
                # Check if command is frequently used at this time
                time_matches = sum(1 for e in self.history 
                                 if e.command == command 
                                 and datetime.fromtimestamp(e.timestamp).hour == hour)
                if time_matches > 2:
                    boost *= 1.1
            
            filtered.append((command, confidence * boost))
        
        return filtered
    
    def get_command_patterns(self, command: str) -> List[str]:
        """Get common patterns that follow a given command"""
        patterns = []
        
        # Find sequences in history
        history_list = list(self.history)
        for i in range(len(history_list) - 1):
            if history_list[i].command == command:
                next_command = history_list[i + 1].command
                patterns.append(next_command)
        
        # Return most common patterns
        from collections import Counter
        pattern_counts = Counter(patterns)
        return [cmd for cmd, _ in pattern_counts.most_common(5)]
    
    def save_history(self) -> None:
        """Save history to persistent storage"""
        try:
            # Prepare data for saving
            data = {
                'version': '1.0',
                'session_id': self.session_id,
                'timestamp': time.time(),
                'entries': [entry.to_dict() for entry in list(self.history)[-self.config.max_history_size:]],
                'command_frequency': dict(self.command_frequency),
                'command_success_rate': dict(self.command_success_rate)
            }
            
            if ENCRYPTION_AVAILABLE and self.config.enable_encryption and self.encryption_key:
                # Encrypt and save
                fernet = Fernet(self.encryption_key)
                encrypted_data = fernet.encrypt(json.dumps(data).encode())
                
                self.encrypted_history_file.parent.mkdir(parents=True, exist_ok=True)
                old_umask = os.umask(0o077)
                try:
                    with open(self.encrypted_history_file, 'wb') as f:
                        f.write(encrypted_data)
                finally:
                    os.umask(old_umask)
            else:
                # Save unencrypted with restricted permissions
                self.history_file.parent.mkdir(parents=True, exist_ok=True)
                old_umask = os.umask(0o077)
                try:
                    with open(self.history_file, 'w') as f:
                        json.dump(data, f, indent=2)
                finally:
                    os.umask(old_umask)
                    
        except Exception as e:
            self.logger.error(f"Failed to save autocomplete history: {e}")
    
    def load_history(self) -> None:
        """Load history from persistent storage"""
        try:
            data = None
            
            # Try loading encrypted history first
            if ENCRYPTION_AVAILABLE and self.encrypted_history_file.exists() and self.encryption_key:
                try:
                    fernet = Fernet(self.encryption_key)
                    with open(self.encrypted_history_file, 'rb') as f:
                        encrypted_data = f.read()
                    decrypted = fernet.decrypt(encrypted_data)
                    data = json.loads(decrypted)
                except Exception as e:
                    self.logger.warning(f"Failed to decrypt history: {e}")
            
            # Fall back to unencrypted file
            if data is None and self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
            
            if data:
                # Load entries
                cutoff_time = time.time() - (self.config.history_retention_days * 86400)
                
                for entry_dict in data.get('entries', []):
                    if entry_dict['timestamp'] > cutoff_time:
                        entry = CommandHistoryEntry.from_dict(entry_dict)
                        self.history.append(entry)
                
                # Load frequency data
                self.command_frequency = defaultdict(int, data.get('command_frequency', {}))
                self.command_success_rate = defaultdict(
                    lambda: (0, 0),
                    {k: tuple(v) for k, v in data.get('command_success_rate', {}).items()}
                )
                
                self.logger.info(f"Loaded {len(self.history)} history entries")
                
        except Exception as e:
            self.logger.warning(f"Failed to load history: {e}")
    
    def clear_history(self, older_than_days: Optional[int] = None) -> int:
        """Clear history entries, optionally older than specified days"""
        if older_than_days:
            cutoff_time = time.time() - (older_than_days * 86400)
            original_size = len(self.history)
            
            # Filter out old entries
            self.history = deque(
                (e for e in self.history if e.timestamp > cutoff_time),
                maxlen=self.config.max_history_size
            )
            
            # Rebuild frequency data
            self.command_frequency.clear()
            self.command_success_rate.clear()
            
            for entry in self.history:
                self.command_frequency[entry.command] += 1
                success, total = self.command_success_rate[entry.command]
                if entry.success:
                    success += 1
                total += 1
                self.command_success_rate[entry.command] = (success, total)
            
            removed = original_size - len(self.history)
            self.save_history()
            return removed
        else:
            # Clear all history
            count = len(self.history)
            self.history.clear()
            self.command_frequency.clear()
            self.command_success_rate.clear()
            self.session_commands.clear()
            self.save_history()
            return count
    
    def export_history(self, output_file: Path, format: str = 'json') -> None:
        """Export history to a file"""
        if format == 'json':
            data = {
                'entries': [entry.to_dict() for entry in self.history],
                'statistics': {
                    'total_commands': len(self.history),
                    'unique_commands': len(self.command_frequency),
                    'session_id': self.session_id,
                    'export_time': datetime.now().isoformat()
                }
            }
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        elif format == 'txt':
            with open(output_file, 'w') as f:
                f.write(f"# LocalAgent Command History Export\n")
                f.write(f"# Exported: {datetime.now().isoformat()}\n")
                f.write(f"# Total Commands: {len(self.history)}\n\n")
                
                for entry in self.history:
                    timestamp = datetime.fromtimestamp(entry.timestamp).isoformat()
                    f.write(f"[{timestamp}] {entry.command}\n")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics"""
        if not self.history:
            return {
                'total_commands': 0,
                'unique_commands': 0,
                'average_success_rate': 0.0,
                'most_used_commands': [],
                'session_commands': 0
            }
        
        # Calculate average success rate
        total_success = sum(s for s, _ in self.command_success_rate.values())
        total_attempts = sum(t for _, t in self.command_success_rate.values())
        avg_success = total_success / total_attempts if total_attempts > 0 else 0.0
        
        # Most used commands
        most_used = sorted(
            self.command_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_commands': len(self.history),
            'unique_commands': len(self.command_frequency),
            'average_success_rate': avg_success,
            'most_used_commands': most_used,
            'session_commands': len(self.session_commands),
            'history_size_bytes': self.encrypted_history_file.stat().st_size if self.encrypted_history_file.exists() else 0
        }