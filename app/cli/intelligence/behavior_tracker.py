"""
User Behavior Tracking and Analysis System
===========================================

Monitors user interactions, command patterns, and interface usage to provide
data for ML-powered adaptations. Privacy-focused with local storage only.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from pathlib import Path
from collections import defaultdict, deque
import hashlib
import logging

# Import MCP for persistent storage
try:
    from ..mcp_integration import get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

@dataclass
class UserInteraction:
    """Single user interaction event"""
    timestamp: float
    interaction_type: str  # 'command', 'selection', 'navigation', 'completion'
    command: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    response_time: float = 0.0  # Time to complete action
    success: bool = True
    error_message: Optional[str] = None
    ui_state: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserInteraction':
        return cls(**data)

@dataclass 
class UserSession:
    """User session with multiple interactions"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    interactions: List[UserInteraction] = field(default_factory=list)
    provider_usage: Dict[str, int] = field(default_factory=dict)
    command_frequency: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    completion_rate: float = 0.0
    average_response_time: float = 0.0
    workflow_patterns: List[str] = field(default_factory=list)
    
    def add_interaction(self, interaction: UserInteraction):
        """Add interaction and update session metrics"""
        self.interactions.append(interaction)
        
        # Update command frequency
        if interaction.command:
            self.command_frequency[interaction.command] = \
                self.command_frequency.get(interaction.command, 0) + 1
        
        # Update error count
        if not interaction.success:
            self.error_count += 1
        
        # Update provider usage
        provider = interaction.context.get('provider')
        if provider:
            self.provider_usage[provider] = \
                self.provider_usage.get(provider, 0) + 1
        
        # Update averages
        self._update_metrics()
    
    def _update_metrics(self):
        """Update session-level metrics"""
        if not self.interactions:
            return
        
        # Completion rate
        successful = sum(1 for i in self.interactions if i.success)
        self.completion_rate = successful / len(self.interactions)
        
        # Average response time
        response_times = [i.response_time for i in self.interactions if i.response_time > 0]
        if response_times:
            self.average_response_time = sum(response_times) / len(response_times)

class BehaviorTracker:
    """
    Core behavior tracking system that monitors user interactions
    and provides data for ML-powered adaptations
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".localagent"
        self.behavior_dir = self.config_dir / "behavior_data"
        self.behavior_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("BehaviorTracker")
        
        # Current session
        self.current_session: Optional[UserSession] = None
        self.session_start_time = time.time()
        
        # Interaction buffer (for real-time processing)
        self.interaction_buffer = deque(maxlen=1000)
        
        # Privacy settings
        self.anonymize_data = True
        self.max_storage_days = 30
        
        # Performance tracking
        self.processing_times = deque(maxlen=100)
        
    def start_session(self, session_context: Optional[Dict[str, Any]] = None) -> str:
        """Start a new user session"""
        session_id = self._generate_session_id()
        
        self.current_session = UserSession(
            session_id=session_id,
            start_time=time.time()
        )
        
        self.logger.info(f"Started behavior tracking session: {session_id}")
        
        # Log session start interaction
        self.track_interaction(
            interaction_type='session_start',
            context=session_context or {},
            session_id=session_id
        )
        
        return session_id
    
    def end_session(self) -> Optional[UserSession]:
        """End current session and save data"""
        if not self.current_session:
            return None
        
        self.current_session.end_time = time.time()
        
        # Log session end
        self.track_interaction(
            interaction_type='session_end',
            context={'duration': self.current_session.end_time - self.current_session.start_time}
        )
        
        # Save session data
        asyncio.create_task(self._save_session_data(self.current_session))
        
        session = self.current_session
        self.current_session = None
        
        self.logger.info(f"Ended session {session.session_id} with {len(session.interactions)} interactions")
        
        return session
    
    def track_interaction(
        self,
        interaction_type: str,
        command: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        response_time: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        ui_state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ):
        """Track a user interaction"""
        start_time = time.time()
        
        if not self.current_session and not session_id:
            # Auto-start session if needed
            self.start_session()
        
        interaction = UserInteraction(
            timestamp=time.time(),
            interaction_type=interaction_type,
            command=command,
            context=self._sanitize_context(context or {}),
            response_time=response_time,
            success=success,
            error_message=error_message,
            ui_state=ui_state or {},
            session_id=session_id or (self.current_session.session_id if self.current_session else None)
        )
        
        # Add to current session
        if self.current_session:
            self.current_session.add_interaction(interaction)
        
        # Add to buffer for real-time processing
        self.interaction_buffer.append(interaction)
        
        # Track processing performance
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        # Ensure we maintain 60+ FPS (< 16ms processing time)
        if processing_time > 0.016:  # 16ms = 1/60 second
            self.logger.warning(f"Behavior tracking took {processing_time*1000:.1f}ms (target: <16ms)")
    
    def track_command_execution(
        self,
        command: str,
        args: List[str],
        start_time: float,
        end_time: float,
        success: bool,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Track command execution with detailed metrics"""
        self.track_interaction(
            interaction_type='command_execution',
            command=command,
            context={
                'args': args,
                'execution_time': end_time - start_time,
                'command_length': len(command),
                'arg_count': len(args),
                **(context or {})
            },
            response_time=end_time - start_time,
            success=success,
            error_message=error
        )
    
    def track_ui_interaction(
        self,
        element_type: str,
        action: str,
        element_id: Optional[str] = None,
        response_time: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ):
        """Track UI element interactions"""
        self.track_interaction(
            interaction_type='ui_interaction',
            context={
                'element_type': element_type,
                'action': action,
                'element_id': element_id,
                **(context or {})
            },
            response_time=response_time
        )
    
    def track_provider_usage(
        self,
        provider_name: str,
        model_name: Optional[str] = None,
        request_type: str = 'completion',
        response_time: float = 0.0,
        success: bool = True,
        context: Optional[Dict[str, Any]] = None
    ):
        """Track LLM provider usage patterns"""
        self.track_interaction(
            interaction_type='provider_usage',
            context={
                'provider': provider_name,
                'model': model_name,
                'request_type': request_type,
                **(context or {})
            },
            response_time=response_time,
            success=success
        )
    
    def track_workflow_pattern(
        self,
        workflow_type: str,
        phase: Optional[str] = None,
        agent_type: Optional[str] = None,
        duration: float = 0.0,
        success: bool = True,
        context: Optional[Dict[str, Any]] = None
    ):
        """Track workflow execution patterns"""
        self.track_interaction(
            interaction_type='workflow_execution',
            context={
                'workflow_type': workflow_type,
                'phase': phase,
                'agent_type': agent_type,
                'duration': duration,
                **(context or {})
            },
            response_time=duration,
            success=success
        )
    
    async def get_recent_patterns(
        self,
        hours: int = 24,
        interaction_types: Optional[List[str]] = None
    ) -> List[UserInteraction]:
        """Get recent interaction patterns for analysis"""
        cutoff_time = time.time() - (hours * 3600)
        
        recent_interactions = []
        
        # From current session
        if self.current_session:
            for interaction in self.current_session.interactions:
                if interaction.timestamp >= cutoff_time:
                    if not interaction_types or interaction.interaction_type in interaction_types:
                        recent_interactions.append(interaction)
        
        # From buffer
        for interaction in self.interaction_buffer:
            if interaction.timestamp >= cutoff_time:
                if not interaction_types or interaction.interaction_type in interaction_types:
                    recent_interactions.append(interaction)
        
        # Sort by timestamp
        recent_interactions.sort(key=lambda x: x.timestamp)
        
        return recent_interactions
    
    async def get_command_frequency(self, hours: int = 168) -> Dict[str, int]:
        """Get command usage frequency over time period"""
        recent_interactions = await self.get_recent_patterns(hours, ['command_execution'])
        
        frequency = defaultdict(int)
        for interaction in recent_interactions:
            if interaction.command:
                frequency[interaction.command] += 1
        
        return dict(frequency)
    
    async def get_provider_preferences(self, hours: int = 168) -> Dict[str, Dict[str, Any]]:
        """Get provider usage preferences and performance"""
        provider_interactions = await self.get_recent_patterns(hours, ['provider_usage'])
        
        preferences = defaultdict(lambda: {
            'usage_count': 0,
            'success_rate': 0.0,
            'avg_response_time': 0.0,
            'models_used': set()
        })
        
        for interaction in provider_interactions:
            provider = interaction.context.get('provider')
            if not provider:
                continue
            
            prefs = preferences[provider]
            prefs['usage_count'] += 1
            
            if interaction.success:
                prefs['success_rate'] += 1
            
            if interaction.response_time > 0:
                prefs['avg_response_time'] += interaction.response_time
            
            model = interaction.context.get('model')
            if model:
                prefs['models_used'].add(model)
        
        # Calculate averages
        for provider, data in preferences.items():
            if data['usage_count'] > 0:
                data['success_rate'] /= data['usage_count']
                data['avg_response_time'] /= data['usage_count']
                data['models_used'] = list(data['models_used'])
        
        return dict(preferences)
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get behavior tracking performance metrics"""
        return {
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0,
            'max_processing_time': max(self.processing_times) if self.processing_times else 0,
            'buffer_size': len(self.interaction_buffer),
            'buffer_max_size': self.interaction_buffer.maxlen,
            'fps_compliant': all(t < 0.016 for t in self.processing_times),
            'current_session_interactions': len(self.current_session.interactions) if self.current_session else 0
        }
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = str(time.time())
        user_hash = hashlib.md5(str(Path.home()).encode()).hexdigest()[:8]
        return f"session_{user_hash}_{int(time.time())}"
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context data for privacy"""
        if not self.anonymize_data:
            return context
        
        # Remove sensitive information
        sensitive_keys = ['api_key', 'password', 'token', 'secret', 'auth']
        sanitized = {}
        
        for key, value in context.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str) and len(value) > 100:
                # Truncate very long strings
                sanitized[key] = value[:100] + '...'
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def _save_session_data(self, session: UserSession):
        """Save session data to storage"""
        try:
            # Save to local file
            session_file = self.behavior_dir / f"{session.session_id}.json"
            
            session_data = {
                'session_id': session.session_id,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'interactions': [i.to_dict() for i in session.interactions],
                'provider_usage': session.provider_usage,
                'command_frequency': session.command_frequency,
                'error_count': session.error_count,
                'completion_rate': session.completion_rate,
                'average_response_time': session.average_response_time,
                'workflow_patterns': session.workflow_patterns
            }
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            # Also save to MCP if available
            if MCP_AVAILABLE:
                try:
                    mcp_client = await get_mcp_client('memory')
                    if mcp_client:
                        await mcp_client.store_entity(
                            entity_type='user_session',
                            entity_id=session.session_id,
                            data=session_data,
                            metadata={'retention_days': self.max_storage_days}
                        )
                except Exception as e:
                    self.logger.warning(f"Failed to save session to MCP: {e}")
            
            self.logger.debug(f"Saved session data: {session.session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
    
    async def cleanup_old_data(self):
        """Clean up old behavior data"""
        cutoff_time = time.time() - (self.max_storage_days * 24 * 3600)
        
        # Clean local files
        for session_file in self.behavior_dir.glob("session_*.json"):
            try:
                stat = session_file.stat()
                if stat.st_mtime < cutoff_time:
                    session_file.unlink()
                    self.logger.debug(f"Removed old session file: {session_file}")
            except Exception as e:
                self.logger.warning(f"Failed to remove old session file {session_file}: {e}")


class UserBehaviorAnalyzer:
    """
    Analyzes user behavior patterns to provide insights for UI adaptations
    """
    
    def __init__(self, behavior_tracker: BehaviorTracker):
        self.behavior_tracker = behavior_tracker
        self.logger = logging.getLogger("UserBehaviorAnalyzer")
    
    async def analyze_command_patterns(self, hours: int = 168) -> Dict[str, Any]:
        """Analyze command usage patterns"""
        command_freq = await self.behavior_tracker.get_command_frequency(hours)
        recent_interactions = await self.behavior_tracker.get_recent_patterns(hours, ['command_execution'])
        
        # Calculate patterns
        total_commands = sum(command_freq.values())
        most_used = sorted(command_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Command sequences
        sequences = self._find_command_sequences(recent_interactions)
        
        # Time-based patterns
        time_patterns = self._analyze_time_patterns(recent_interactions)
        
        return {
            'total_commands': total_commands,
            'unique_commands': len(command_freq),
            'most_used_commands': most_used,
            'command_sequences': sequences,
            'time_patterns': time_patterns,
            'efficiency_score': self._calculate_efficiency_score(recent_interactions)
        }
    
    async def analyze_provider_patterns(self, hours: int = 168) -> Dict[str, Any]:
        """Analyze LLM provider usage patterns"""
        provider_prefs = await self.behavior_tracker.get_provider_preferences(hours)
        
        # Find preferred provider
        preferred_provider = max(provider_prefs.items(), key=lambda x: x[1]['usage_count'])[0] \
                            if provider_prefs else None
        
        # Performance rankings
        performance_ranking = sorted(
            provider_prefs.items(),
            key=lambda x: (x[1]['success_rate'], -x[1]['avg_response_time']),
            reverse=True
        )
        
        return {
            'preferred_provider': preferred_provider,
            'provider_preferences': provider_prefs,
            'performance_ranking': performance_ranking,
            'provider_diversity': len(provider_prefs),
            'recommendations': self._generate_provider_recommendations(provider_prefs)
        }
    
    async def analyze_ui_patterns(self, hours: int = 72) -> Dict[str, Any]:
        """Analyze UI interaction patterns"""
        ui_interactions = await self.behavior_tracker.get_recent_patterns(hours, ['ui_interaction'])
        
        # Element usage frequency
        element_frequency = defaultdict(int)
        action_frequency = defaultdict(int)
        response_times = defaultdict(list)
        
        for interaction in ui_interactions:
            element_type = interaction.context.get('element_type')
            action = interaction.context.get('action')
            
            if element_type:
                element_frequency[element_type] += 1
            if action:
                action_frequency[action] += 1
            
            if interaction.response_time > 0:
                response_times[f"{element_type}_{action}"].append(interaction.response_time)
        
        # Calculate averages
        avg_response_times = {
            key: sum(times) / len(times)
            for key, times in response_times.items()
        }
        
        return {
            'element_frequency': dict(element_frequency),
            'action_frequency': dict(action_frequency),
            'avg_response_times': avg_response_times,
            'ui_efficiency': self._calculate_ui_efficiency(ui_interactions),
            'adaptation_suggestions': self._generate_ui_adaptations(element_frequency, avg_response_times)
        }
    
    async def analyze_workflow_patterns(self, hours: int = 168) -> Dict[str, Any]:
        """Analyze workflow execution patterns"""
        workflow_interactions = await self.behavior_tracker.get_recent_patterns(hours, ['workflow_execution'])
        
        # Workflow type frequency
        workflow_frequency = defaultdict(int)
        phase_success_rates = defaultdict(list)
        agent_usage = defaultdict(int)
        
        for interaction in workflow_interactions:
            workflow_type = interaction.context.get('workflow_type')
            phase = interaction.context.get('phase')
            agent_type = interaction.context.get('agent_type')
            
            if workflow_type:
                workflow_frequency[workflow_type] += 1
            
            if phase:
                phase_success_rates[phase].append(1.0 if interaction.success else 0.0)
            
            if agent_type:
                agent_usage[agent_type] += 1
        
        # Calculate phase success rates
        phase_success = {
            phase: sum(successes) / len(successes)
            for phase, successes in phase_success_rates.items()
        }
        
        return {
            'workflow_frequency': dict(workflow_frequency),
            'phase_success_rates': phase_success,
            'agent_usage': dict(agent_usage),
            'workflow_recommendations': self._generate_workflow_recommendations(workflow_frequency, phase_success)
        }
    
    def _find_command_sequences(self, interactions: List[UserInteraction]) -> List[Tuple[List[str], int]]:
        """Find common command sequences"""
        sequences = defaultdict(int)
        
        # Look for sequences of 2-4 commands
        commands = [i.command for i in interactions if i.command]
        
        for length in [2, 3, 4]:
            for i in range(len(commands) - length + 1):
                sequence = tuple(commands[i:i+length])
                sequences[sequence] += 1
        
        # Return most common sequences
        return sorted([(list(seq), count) for seq, count in sequences.items()], 
                     key=lambda x: x[1], reverse=True)[:10]
    
    def _analyze_time_patterns(self, interactions: List[UserInteraction]) -> Dict[str, Any]:
        """Analyze time-based usage patterns"""
        hour_usage = defaultdict(int)
        day_usage = defaultdict(int)
        
        for interaction in interactions:
            dt = datetime.fromtimestamp(interaction.timestamp)
            hour_usage[dt.hour] += 1
            day_usage[dt.weekday()] += 1
        
        return {
            'peak_hours': sorted(hour_usage.items(), key=lambda x: x[1], reverse=True)[:5],
            'peak_days': sorted(day_usage.items(), key=lambda x: x[1], reverse=True)[:3],
            'hour_distribution': dict(hour_usage),
            'day_distribution': dict(day_usage)
        }
    
    def _calculate_efficiency_score(self, interactions: List[UserInteraction]) -> float:
        """Calculate user efficiency score (0-1)"""
        if not interactions:
            return 0.0
        
        success_rate = sum(1 for i in interactions if i.success) / len(interactions)
        
        # Factor in response times (faster = more efficient)
        response_times = [i.response_time for i in interactions if i.response_time > 0]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            time_efficiency = 1.0 / (1.0 + avg_response)  # Inverse relationship
        else:
            time_efficiency = 1.0
        
        return (success_rate * 0.7 + time_efficiency * 0.3)
    
    def _calculate_ui_efficiency(self, interactions: List[UserInteraction]) -> float:
        """Calculate UI interaction efficiency"""
        if not interactions:
            return 0.0
        
        # Measure click-to-completion ratios, navigation patterns, etc.
        total_interactions = len(interactions)
        successful_interactions = sum(1 for i in interactions if i.success)
        
        return successful_interactions / total_interactions if total_interactions > 0 else 0.0
    
    def _generate_provider_recommendations(self, provider_prefs: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate provider usage recommendations"""
        recommendations = []
        
        if not provider_prefs:
            recommendations.append("Consider configuring LLM providers for better productivity")
            return recommendations
        
        # Find best performing provider
        best_provider = max(provider_prefs.items(), 
                           key=lambda x: x[1]['success_rate'])[0]
        
        recommendations.append(f"Consider using {best_provider} more often (highest success rate)")
        
        # Check for slow providers
        for provider, data in provider_prefs.items():
            if data['avg_response_time'] > 5.0:  # 5 seconds
                recommendations.append(f"Consider optimizing {provider} configuration (slow response times)")
        
        return recommendations
    
    def _generate_ui_adaptations(self, element_freq: Dict[str, int], response_times: Dict[str, float]) -> List[str]:
        """Generate UI adaptation suggestions"""
        adaptations = []
        
        # Most used elements should be more accessible
        if element_freq:
            most_used = max(element_freq.items(), key=lambda x: x[1])[0]
            adaptations.append(f"Optimize accessibility for {most_used} elements")
        
        # Slow interactions should be improved
        slow_interactions = [(k, v) for k, v in response_times.items() if v > 1.0]
        if slow_interactions:
            slowest = max(slow_interactions, key=lambda x: x[1])[0]
            adaptations.append(f"Optimize performance for {slowest} interactions")
        
        return adaptations
    
    def _generate_workflow_recommendations(self, workflow_freq: Dict[str, int], 
                                         phase_success: Dict[str, float]) -> List[str]:
        """Generate workflow optimization recommendations"""
        recommendations = []
        
        # Find frequently used workflows
        if workflow_freq:
            most_used = max(workflow_freq.items(), key=lambda x: x[1])[0]
            recommendations.append(f"Consider creating shortcuts for {most_used} workflows")
        
        # Find problematic phases
        problem_phases = [(k, v) for k, v in phase_success.items() if v < 0.8]
        if problem_phases:
            worst_phase = min(problem_phases, key=lambda x: x[1])[0]
            recommendations.append(f"Focus on improving {worst_phase} phase reliability")
        
        return recommendations


# Global behavior tracker instance
_behavior_tracker: Optional[BehaviorTracker] = None

def get_behavior_tracker(config_dir: Optional[Path] = None) -> BehaviorTracker:
    """Get or create global behavior tracker instance"""
    global _behavior_tracker
    if _behavior_tracker is None:
        _behavior_tracker = BehaviorTracker(config_dir)
    return _behavior_tracker

def get_behavior_analyzer(behavior_tracker: Optional[BehaviorTracker] = None) -> UserBehaviorAnalyzer:
    """Get behavior analyzer instance"""
    tracker = behavior_tracker or get_behavior_tracker()
    return UserBehaviorAnalyzer(tracker)