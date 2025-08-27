"""
Intelligent Command Processing System
====================================

Provides ML-enhanced command completion, suggestion, and prediction features.
Uses behavior patterns and TensorFlow.js models to improve CLI productivity.
"""

import asyncio
import time
import logging
import difflib
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from pathlib import Path
import json
import re

# Import behavior tracking and ML models
from .behavior_tracker import BehaviorTracker, UserInteraction
from .ml_models import TensorFlowJSModelManager, AdaptiveUIModel, TrainingData

# Import MCP integration for intelligent pattern selection
try:
    from ...mcp.patterns.intelligent_selector import intelligent_selector
    MCP_INTELLIGENT_SELECTOR_AVAILABLE = True
except ImportError:
    MCP_INTELLIGENT_SELECTOR_AVAILABLE = False

@dataclass
class CommandSuggestion:
    """A command completion suggestion"""
    command: str
    confidence: float
    source: str  # 'ml_model', 'frequency', 'similarity', 'context'
    description: Optional[str] = None
    usage_count: int = 0
    success_rate: float = 0.0
    estimated_time: float = 0.0  # Estimated execution time
    
    def __lt__(self, other):
        return self.confidence > other.confidence  # Sort by confidence descending

@dataclass
class CommandContext:
    """Context information for command suggestions"""
    current_directory: str
    recent_commands: List[str] = field(default_factory=list)
    available_providers: List[str] = field(default_factory=list)
    active_session: Optional[str] = None
    workflow_phase: Optional[str] = None
    user_skill_level: str = 'intermediate'
    time_of_day: int = 12
    environment_vars: Dict[str, str] = field(default_factory=dict)

@dataclass
class CommandPrediction:
    """Predicted next command based on context"""
    predicted_command: str
    probability: float
    reasoning: List[str]
    suggested_args: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0

class CommandIntelligenceEngine:
    """
    Core engine for intelligent command processing
    """
    
    def __init__(self, 
                 behavior_tracker: BehaviorTracker,
                 model_manager: TensorFlowJSModelManager,
                 config_dir: Optional[Path] = None):
        
        self.behavior_tracker = behavior_tracker
        self.model_manager = model_manager
        self.config_dir = config_dir or Path.home() / ".localagent"
        
        self.logger = logging.getLogger("CommandIntelligenceEngine")
        
        # Command knowledge base
        self.command_vocabulary: Set[str] = set()
        self.command_frequency: Dict[str, int] = defaultdict(int)
        self.command_patterns: Dict[str, List[str]] = defaultdict(list)  # command -> frequent next commands
        self.command_success_rates: Dict[str, float] = defaultdict(float)
        self.command_descriptions: Dict[str, str] = {}
        
        # ML models
        self.command_completion_model: Optional[AdaptiveUIModel] = None
        
        # Performance tracking
        self.suggestion_times = deque(maxlen=1000)
        self.cache = {}  # Simple caching for frequently requested suggestions
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize system
        asyncio.create_task(self._initialize_command_intelligence())
    
    async def _initialize_command_intelligence(self):
        """Initialize the command intelligence system"""
        try:
            # Load command knowledge base
            await self._load_command_knowledge()
            
            # Initialize ML model
            await self._initialize_completion_model()
            
            # Build vocabulary from recent interactions
            await self._build_vocabulary_from_history()
            
            self.logger.info("Command intelligence engine initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize command intelligence: {e}")
    
    async def _initialize_completion_model(self):
        """Initialize ML model for command completion"""
        try:
            # Try to load existing model
            self.command_completion_model = await self.model_manager.load_model("command_completer")
            
            # Create new model if none exists
            if not self.command_completion_model:
                from .ml_models import create_command_completion_model
                self.command_completion_model = await create_command_completion_model(
                    self.model_manager,
                    sequence_length=10,
                    vocab_size=1000
                )
                
                # Train with initial data if available
                await self._train_completion_model()
            
        except Exception as e:
            self.logger.warning(f"Command completion model not available: {e}")
    
    async def get_command_suggestions(self, 
                                   partial_command: str,
                                   context: CommandContext,
                                   max_suggestions: int = 10) -> List[CommandSuggestion]:
        """Get intelligent command completion suggestions"""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{partial_command}:{hash(str(context))}"
            if cache_key in self.cache:
                cached_result, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    return cached_result
            
            suggestions = []
            
            # 1. ML-based suggestions (if model available)
            if self.command_completion_model and len(partial_command) > 0:
                ml_suggestions = await self._get_ml_suggestions(partial_command, context)
                suggestions.extend(ml_suggestions)
            
            # 2. Frequency-based suggestions
            frequency_suggestions = await self._get_frequency_suggestions(partial_command)
            suggestions.extend(frequency_suggestions)
            
            # 3. Similarity-based suggestions
            similarity_suggestions = await self._get_similarity_suggestions(partial_command)
            suggestions.extend(similarity_suggestions)
            
            # 4. Context-aware suggestions
            context_suggestions = await self._get_context_suggestions(partial_command, context)
            suggestions.extend(context_suggestions)
            
            # 5. Pattern-based suggestions (command sequences)
            pattern_suggestions = await self._get_pattern_suggestions(partial_command, context)
            suggestions.extend(pattern_suggestions)
            
            # Deduplicate and rank suggestions
            unique_suggestions = self._deduplicate_suggestions(suggestions)
            ranked_suggestions = self._rank_suggestions(unique_suggestions, context)
            
            # Limit to max_suggestions
            final_suggestions = ranked_suggestions[:max_suggestions]
            
            # Cache results
            self.cache[cache_key] = (final_suggestions, time.time())
            
            # Track performance
            suggestion_time = (time.time() - start_time) * 1000
            self.suggestion_times.append(suggestion_time)
            
            if suggestion_time > 16.0:  # Must be under 16ms for 60+ FPS
                self.logger.warning(f"Command suggestions took {suggestion_time:.1f}ms (target: <16ms)")
            
            return final_suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to generate command suggestions: {e}")
            return []
    
    async def _get_ml_suggestions(self, partial_command: str, context: CommandContext) -> List[CommandSuggestion]:
        """Get ML-based command suggestions"""
        try:
            # Create feature vector from partial command and context
            features = self._encode_command_context(partial_command, context)
            
            # Get predictions from ML model
            predictions = await self.model_manager.predict(
                "command_completer", features, timeout_ms=5
            )
            
            if not predictions:
                return []
            
            suggestions = []
            
            # Convert predictions to command suggestions
            # This is a simplified approach - in practice, you'd use a vocabulary mapping
            for i, prob in enumerate(predictions):
                if prob > 0.3 and i < len(self.command_vocabulary):  # Confidence threshold
                    command = list(self.command_vocabulary)[i] if self.command_vocabulary else f"cmd_{i}"
                    
                    suggestions.append(CommandSuggestion(
                        command=command,
                        confidence=float(prob),
                        source='ml_model',
                        description=self.command_descriptions.get(command, 'ML-predicted command')
                    ))
            
            return suggestions
            
        except Exception as e:
            self.logger.warning(f"ML suggestions failed: {e}")
            return []
    
    async def _get_frequency_suggestions(self, partial_command: str) -> List[CommandSuggestion]:
        """Get frequency-based suggestions from command usage history"""
        suggestions = []
        
        # Get commands that start with the partial input
        matching_commands = [
            cmd for cmd in self.command_frequency.keys()
            if cmd.lower().startswith(partial_command.lower())
        ]
        
        # Sort by frequency
        matching_commands.sort(key=lambda x: self.command_frequency[x], reverse=True)
        
        total_usage = sum(self.command_frequency.values()) or 1
        
        for command in matching_commands[:20]:  # Top 20 by frequency
            usage_count = self.command_frequency[command]
            confidence = min(0.9, usage_count / (total_usage * 0.1))  # Normalize confidence
            
            suggestions.append(CommandSuggestion(
                command=command,
                confidence=confidence,
                source='frequency',
                usage_count=usage_count,
                success_rate=self.command_success_rates.get(command, 0.8),
                description=self.command_descriptions.get(command)
            ))
        
        return suggestions
    
    async def _get_similarity_suggestions(self, partial_command: str) -> List[CommandSuggestion]:
        """Get suggestions based on string similarity"""
        suggestions = []
        
        if len(partial_command) < 2:  # Too short for meaningful similarity
            return suggestions
        
        # Find similar commands using difflib
        similar_commands = difflib.get_close_matches(
            partial_command.lower(),
            [cmd.lower() for cmd in self.command_vocabulary],
            n=10,
            cutoff=0.6
        )
        
        for similar_cmd in similar_commands:
            # Find the original case command
            original_command = None
            for cmd in self.command_vocabulary:
                if cmd.lower() == similar_cmd:
                    original_command = cmd
                    break
            
            if original_command:
                similarity_ratio = difflib.SequenceMatcher(
                    None, partial_command.lower(), similar_cmd
                ).ratio()
                
                suggestions.append(CommandSuggestion(
                    command=original_command,
                    confidence=similarity_ratio * 0.7,  # Lower confidence for similarity
                    source='similarity',
                    description=f"Similar to '{partial_command}'"
                ))
        
        return suggestions
    
    async def _get_context_suggestions(self, partial_command: str, context: CommandContext) -> List[CommandSuggestion]:
        """Get context-aware command suggestions"""
        suggestions = []
        
        # Recent command patterns
        if context.recent_commands:
            last_command = context.recent_commands[-1] if context.recent_commands else ""
            
            # Look for commands that frequently follow the last command
            if last_command in self.command_patterns:
                next_commands = self.command_patterns[last_command]
                
                for next_cmd in next_commands[:5]:  # Top 5 following commands
                    if next_cmd.lower().startswith(partial_command.lower()) or not partial_command:
                        confidence = 0.6  # Context-based confidence
                        
                        suggestions.append(CommandSuggestion(
                            command=next_cmd,
                            confidence=confidence,
                            source='context',
                            description=f"Often follows '{last_command}'"
                        ))
        
        # Workflow phase suggestions
        if context.workflow_phase:
            phase_commands = self._get_phase_appropriate_commands(context.workflow_phase, partial_command)
            suggestions.extend(phase_commands)
        
        # Provider-specific suggestions
        if context.available_providers and partial_command.startswith('provider '):
            provider_suggestions = self._get_provider_suggestions(partial_command, context.available_providers)
            suggestions.extend(provider_suggestions)
        
        return suggestions
    
    async def _get_pattern_suggestions(self, partial_command: str, context: CommandContext) -> List[CommandSuggestion]:
        """Get suggestions based on command sequence patterns"""
        suggestions = []
        
        # Use intelligent pattern selector if available
        if MCP_INTELLIGENT_SELECTOR_AVAILABLE and not partial_command:
            try:
                # Suggest patterns based on recent context
                recent_context = " ".join(context.recent_commands[-3:])
                pattern_recommendations = await intelligent_selector.recommend_patterns_for_task(recent_context)
                
                for rec in pattern_recommendations[:3]:
                    suggestions.append(CommandSuggestion(
                        command=f"pattern {rec.pattern_id}",
                        confidence=rec.confidence,
                        source='pattern',
                        description=f"Execute {rec.pattern_name} pattern"
                    ))
                    
            except Exception as e:
                self.logger.warning(f"Pattern suggestions failed: {e}")
        
        return suggestions
    
    def _get_phase_appropriate_commands(self, phase: str, partial_command: str) -> List[CommandSuggestion]:
        """Get commands appropriate for the current workflow phase"""
        suggestions = []
        
        # Define phase-specific commands
        phase_commands = {
            'research': ['search', 'analyze', 'inspect', 'list', 'status'],
            'planning': ['plan', 'design', 'configure', 'setup', 'init'],
            'execution': ['run', 'execute', 'start', 'deploy', 'build'],
            'testing': ['test', 'validate', 'verify', 'check', 'audit'],
            'cleanup': ['clean', 'remove', 'reset', 'archive', 'finish']
        }
        
        relevant_commands = []
        for phase_key, commands in phase_commands.items():
            if phase_key in phase.lower():
                relevant_commands.extend(commands)
        
        # Filter by partial command
        if partial_command:
            relevant_commands = [
                cmd for cmd in relevant_commands
                if cmd.lower().startswith(partial_command.lower())
            ]
        
        for command in relevant_commands:
            suggestions.append(CommandSuggestion(
                command=command,
                confidence=0.5,
                source='context',
                description=f"Relevant for {phase} phase"
            ))
        
        return suggestions
    
    def _get_provider_suggestions(self, partial_command: str, available_providers: List[str]) -> List[CommandSuggestion]:
        """Get provider-specific command suggestions"""
        suggestions = []
        
        # Extract provider name from partial command
        parts = partial_command.split()
        if len(parts) >= 2:
            provider_name = parts[1]
        else:
            provider_name = ""
        
        # Suggest available providers
        if not provider_name:
            for provider in available_providers:
                suggestions.append(CommandSuggestion(
                    command=f"provider {provider}",
                    confidence=0.7,
                    source='context',
                    description=f"Use {provider} provider"
                ))
        else:
            # Provider-specific commands
            provider_commands = {
                'ollama': ['models', 'pull', 'run', 'show'],
                'openai': ['models', 'usage', 'limits'],
                'gemini': ['models', 'config'],
                'claude': ['models', 'limits']
            }
            
            for provider in available_providers:
                if provider.startswith(provider_name.lower()):
                    commands = provider_commands.get(provider, [])
                    for cmd in commands:
                        suggestions.append(CommandSuggestion(
                            command=f"provider {provider} {cmd}",
                            confidence=0.6,
                            source='context',
                            description=f"{provider} {cmd} command"
                        ))
        
        return suggestions
    
    def _encode_command_context(self, partial_command: str, context: CommandContext) -> List[float]:
        """Encode command and context into feature vector for ML model"""
        features = []
        
        # Command features (10 features)
        features.extend([
            len(partial_command) / 50.0,  # Normalized command length
            1.0 if partial_command else 0.0,  # Has partial input
            len(partial_command.split()) / 10.0,  # Word count
            1.0 if any(char.isdigit() for char in partial_command) else 0.0,  # Contains numbers
            1.0 if any(char in '/-.' for char in partial_command) else 0.0,  # Contains path/option chars
        ])
        
        # Add character frequency features (simplified)
        vowels = sum(1 for char in partial_command.lower() if char in 'aeiou')
        features.append(vowels / max(1, len(partial_command)))
        
        # Add more command features to reach 10
        features.extend([0.0, 0.0, 0.0, 0.0])
        
        # Context features (10 features)  
        features.extend([
            len(context.recent_commands) / 10.0,  # Recent commands count
            len(context.available_providers) / 10.0,  # Provider count
            context.time_of_day / 24.0,  # Time of day
            1.0 if context.active_session else 0.0,  # Has active session
            1.0 if context.workflow_phase else 0.0,  # In workflow phase
        ])
        
        # Skill level encoding
        skill_levels = {'beginner': 0.0, 'intermediate': 0.5, 'expert': 1.0}
        features.append(skill_levels.get(context.user_skill_level, 0.5))
        
        # Add more context features to reach 10
        features.extend([0.0, 0.0, 0.0, 0.0])
        
        # Ensure exactly the expected number of features for the model
        while len(features) < 20:  # Adjust based on model input size
            features.append(0.0)
        
        return features[:20]
    
    def _deduplicate_suggestions(self, suggestions: List[CommandSuggestion]) -> List[CommandSuggestion]:
        """Remove duplicate suggestions, keeping the highest confidence"""
        unique_suggestions = {}
        
        for suggestion in suggestions:
            command = suggestion.command
            if command not in unique_suggestions or suggestion.confidence > unique_suggestions[command].confidence:
                unique_suggestions[command] = suggestion
        
        return list(unique_suggestions.values())
    
    def _rank_suggestions(self, suggestions: List[CommandSuggestion], context: CommandContext) -> List[CommandSuggestion]:
        """Rank suggestions by relevance and confidence"""
        
        for suggestion in suggestions:
            # Boost confidence based on various factors
            
            # Boost frequently used commands
            if suggestion.usage_count > 5:
                suggestion.confidence *= 1.1
            
            # Boost commands with high success rates
            if suggestion.success_rate > 0.8:
                suggestion.confidence *= 1.05
            
            # Boost ML suggestions
            if suggestion.source == 'ml_model':
                suggestion.confidence *= 1.2
            
            # Boost context-relevant suggestions
            if suggestion.source == 'context':
                suggestion.confidence *= 1.15
            
            # Apply skill level adjustments
            if context.user_skill_level == 'beginner' and suggestion.source == 'similarity':
                suggestion.confidence *= 0.8  # Reduce similarity suggestions for beginners
            elif context.user_skill_level == 'expert' and suggestion.source == 'pattern':
                suggestion.confidence *= 1.3  # Boost pattern suggestions for experts
            
            # Ensure confidence stays within bounds
            suggestion.confidence = min(1.0, suggestion.confidence)
        
        # Sort by confidence
        suggestions.sort(reverse=True)
        
        return suggestions
    
    async def predict_next_command(self, context: CommandContext) -> Optional[CommandPrediction]:
        """Predict the most likely next command based on context"""
        try:
            if not context.recent_commands:
                return None
            
            last_command = context.recent_commands[-1]
            
            # Look for common patterns
            if last_command in self.command_patterns:
                next_commands = self.command_patterns[last_command]
                if next_commands:
                    most_likely = next_commands[0]  # Most frequent next command
                    
                    # Calculate probability based on frequency
                    total_following = len(self.command_patterns[last_command])
                    frequency = self.command_patterns[last_command].count(most_likely)
                    probability = frequency / total_following
                    
                    return CommandPrediction(
                        predicted_command=most_likely,
                        probability=probability,
                        reasoning=[
                            f"Frequently follows '{last_command}'",
                            f"Occurs {frequency}/{total_following} times after this command"
                        ]
                    )
            
            # ML-based prediction if available
            if self.command_completion_model:
                features = self._encode_command_context("", context)
                predictions = await self.model_manager.predict(
                    "command_completer", features, timeout_ms=5
                )
                
                if predictions:
                    max_prob_index = predictions.index(max(predictions))
                    if max_prob_index < len(self.command_vocabulary):
                        predicted_cmd = list(self.command_vocabulary)[max_prob_index]
                        
                        return CommandPrediction(
                            predicted_command=predicted_cmd,
                            probability=max(predictions),
                            reasoning=["ML model prediction based on context"]
                        )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to predict next command: {e}")
            return None
    
    async def _build_vocabulary_from_history(self):
        """Build command vocabulary from user interaction history"""
        try:
            # Get recent command interactions
            recent_interactions = await self.behavior_tracker.get_recent_patterns(
                hours=168,  # Last week
                interaction_types=['command_execution']
            )
            
            # Build vocabulary and patterns
            command_sequence = []
            
            for interaction in recent_interactions:
                if interaction.command:
                    command = interaction.command.strip()
                    
                    # Add to vocabulary
                    self.command_vocabulary.add(command)
                    
                    # Update frequency
                    self.command_frequency[command] += 1
                    
                    # Update success rate
                    if command in self.command_success_rates:
                        current_rate = self.command_success_rates[command]
                        new_rate = (current_rate + (1.0 if interaction.success else 0.0)) / 2
                        self.command_success_rates[command] = new_rate
                    else:
                        self.command_success_rates[command] = 1.0 if interaction.success else 0.0
                    
                    # Build command sequences for pattern detection
                    if command_sequence and len(command_sequence) > 0:
                        prev_command = command_sequence[-1]
                        self.command_patterns[prev_command].append(command)
                    
                    command_sequence.append(command)
            
            # Keep only most recent commands in sequence (limit memory)
            if len(command_sequence) > 1000:
                command_sequence = command_sequence[-1000:]
            
            self.logger.info(f"Built vocabulary: {len(self.command_vocabulary)} commands")
            
        except Exception as e:
            self.logger.error(f"Failed to build vocabulary: {e}")
    
    async def _train_completion_model(self):
        """Train the command completion model with historical data"""
        try:
            if not self.command_completion_model:
                return
            
            # Get training data from recent interactions
            recent_interactions = await self.behavior_tracker.get_recent_patterns(
                hours=720,  # Last 30 days
                interaction_types=['command_execution']
            )
            
            if len(recent_interactions) < 50:  # Not enough data
                self.logger.info("Not enough training data for command completion model")
                return
            
            # Prepare training data
            features = []
            labels = []
            
            # Create command to index mapping
            command_to_index = {cmd: i for i, cmd in enumerate(sorted(self.command_vocabulary))}
            
            for i in range(len(recent_interactions) - 1):
                current = recent_interactions[i]
                next_command = recent_interactions[i + 1]
                
                if current.command and next_command.command:
                    # Create context from current interaction
                    context = CommandContext(
                        current_directory="/",  # Simplified
                        recent_commands=[current.command],
                        user_skill_level='intermediate'
                    )
                    
                    # Extract features
                    feature_vector = self._encode_command_context(current.command, context)
                    features.append(feature_vector)
                    
                    # Label is the next command index
                    if next_command.command in command_to_index:
                        label_index = command_to_index[next_command.command]
                        labels.append(label_index)
                    else:
                        labels.append(0)  # Unknown command
            
            if len(features) > 10:  # Minimum training data
                training_data = TrainingData(features=features, labels=labels)
                success = await self.model_manager.train_model("command_completer", training_data)
                
                if success:
                    self.logger.info(f"Command completion model trained with {len(features)} examples")
                else:
                    self.logger.warning("Command completion model training failed")
            
        except Exception as e:
            self.logger.error(f"Failed to train completion model: {e}")
    
    async def _load_command_knowledge(self):
        """Load command knowledge base from storage"""
        knowledge_file = self.config_dir / "command_knowledge.json"
        
        try:
            if knowledge_file.exists():
                with open(knowledge_file, 'r') as f:
                    knowledge_data = json.load(f)
                
                self.command_descriptions = knowledge_data.get('descriptions', {})
                self.command_frequency = defaultdict(int, knowledge_data.get('frequency', {}))
                self.command_success_rates = defaultdict(float, knowledge_data.get('success_rates', {}))
                
                # Load command patterns
                patterns_data = knowledge_data.get('patterns', {})
                for cmd, next_cmds in patterns_data.items():
                    self.command_patterns[cmd] = next_cmds
                
                self.logger.info("Command knowledge loaded from storage")
                
        except Exception as e:
            self.logger.warning(f"Failed to load command knowledge: {e}")
    
    async def save_command_knowledge(self):
        """Save command knowledge base to storage"""
        knowledge_file = self.config_dir / "command_knowledge.json"
        
        try:
            knowledge_data = {
                'descriptions': self.command_descriptions,
                'frequency': dict(self.command_frequency),
                'success_rates': dict(self.command_success_rates),
                'patterns': {cmd: list(set(next_cmds)) for cmd, next_cmds in self.command_patterns.items()},
                'vocabulary': list(self.command_vocabulary),
                'last_updated': time.time()
            }
            
            with open(knowledge_file, 'w') as f:
                json.dump(knowledge_data, f, indent=2)
            
            self.logger.debug("Command knowledge saved to storage")
            
        except Exception as e:
            self.logger.error(f"Failed to save command knowledge: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get command intelligence performance metrics"""
        avg_suggestion_time = sum(self.suggestion_times) / len(self.suggestion_times) \
                             if self.suggestion_times else 0
        
        return {
            'vocabulary_size': len(self.command_vocabulary),
            'command_patterns': len(self.command_patterns),
            'avg_suggestion_time_ms': avg_suggestion_time,
            'fps_compliant': all(t <= 16.0 for t in self.suggestion_times),
            'cache_size': len(self.cache),
            'ml_model_available': self.command_completion_model is not None,
            'knowledge_base_size': len(self.command_descriptions)
        }


class IntelligentCommandProcessor:
    """
    High-level interface for intelligent command processing
    """
    
    def __init__(self, 
                 behavior_tracker: BehaviorTracker,
                 model_manager: TensorFlowJSModelManager,
                 config_dir: Optional[Path] = None):
        
        self.engine = CommandIntelligenceEngine(behavior_tracker, model_manager, config_dir)
        self.logger = logging.getLogger("IntelligentCommandProcessor")
        
        # Auto-save knowledge periodically
        asyncio.create_task(self._periodic_knowledge_save())
    
    async def get_completions(self, 
                            partial_command: str,
                            current_directory: str = "/",
                            recent_commands: Optional[List[str]] = None,
                            available_providers: Optional[List[str]] = None,
                            workflow_phase: Optional[str] = None,
                            user_skill_level: str = 'intermediate',
                            max_results: int = 10) -> List[CommandSuggestion]:
        """Get intelligent command completions"""
        
        context = CommandContext(
            current_directory=current_directory,
            recent_commands=recent_commands or [],
            available_providers=available_providers or [],
            workflow_phase=workflow_phase,
            user_skill_level=user_skill_level,
            time_of_day=time.localtime().tm_hour
        )
        
        return await self.engine.get_command_suggestions(partial_command, context, max_results)
    
    async def predict_next_command(self,
                                 recent_commands: List[str],
                                 current_directory: str = "/",
                                 workflow_phase: Optional[str] = None) -> Optional[CommandPrediction]:
        """Predict the most likely next command"""
        
        context = CommandContext(
            current_directory=current_directory,
            recent_commands=recent_commands,
            workflow_phase=workflow_phase,
            time_of_day=time.localtime().tm_hour
        )
        
        return await self.engine.predict_next_command(context)
    
    async def learn_from_command(self, command: str, success: bool, execution_time: float = 0.0):
        """Learn from executed command for better future suggestions"""
        # This is handled automatically by the behavior tracker
        pass
    
    async def _periodic_knowledge_save(self):
        """Periodically save command knowledge"""
        while True:
            try:
                await asyncio.sleep(600)  # Save every 10 minutes
                await self.engine.save_command_knowledge()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Periodic knowledge save failed: {e}")


# Convenience functions
def create_intelligent_command_processor(
    behavior_tracker: BehaviorTracker,
    model_manager: TensorFlowJSModelManager,
    config_dir: Optional[Path] = None
) -> IntelligentCommandProcessor:
    """Create intelligent command processor with dependencies"""
    return IntelligentCommandProcessor(behavior_tracker, model_manager, config_dir)