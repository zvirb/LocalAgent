"""
Adaptive Interface Management System
====================================

Dynamically adapts the CLI interface based on user behavior patterns,
preferences, and ML predictions. Optimizes layout, shortcuts, and workflows
for individual users while maintaining 60+ FPS performance.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

# Import behavior tracking and ML models
from .behavior_tracker import BehaviorTracker, UserBehaviorAnalyzer, UserInteraction
from .ml_models import TensorFlowJSModelManager, AdaptiveUIModel, TrainingData

# Import UI components
try:
    from ..ui.themes import get_theme_manager, ClaudeThemeManager, CLAUDE_COLORS
    from ..ui.enhanced_prompts import ModernInteractivePrompts
    THEMES_AVAILABLE = True
except ImportError:
    THEMES_AVAILABLE = False

class AdaptationType(Enum):
    """Types of UI adaptations"""
    LAYOUT_OPTIMIZATION = "layout_optimization"
    COMMAND_SHORTCUTS = "command_shortcuts" 
    PROVIDER_PREFERENCES = "provider_preferences"
    WORKFLOW_CUSTOMIZATION = "workflow_customization"
    THEME_ADJUSTMENT = "theme_adjustment"
    HELP_LEVEL_ADAPTATION = "help_level_adaptation"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"

@dataclass
class AdaptationRule:
    """Rule for UI adaptation"""
    rule_id: str
    adaptation_type: AdaptationType
    trigger_conditions: Dict[str, Any]
    adaptation_actions: Dict[str, Any]
    priority: int = 1  # 1=highest, 10=lowest
    confidence_threshold: float = 0.7
    enabled: bool = True
    usage_count: int = 0
    success_rate: float = 0.0

@dataclass
class UIState:
    """Current UI state and configuration"""
    theme: str = "default"
    layout_mode: str = "standard"  # standard, compact, minimal, power-user
    help_level: str = "intermediate"  # beginner, intermediate, expert
    shortcuts: Dict[str, str] = field(default_factory=dict)
    preferred_providers: List[str] = field(default_factory=list)
    workflow_presets: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    performance_mode: str = "balanced"  # fast, balanced, detailed
    customizations: Dict[str, Any] = field(default_factory=dict)

class AdaptiveInterfaceManager:
    """
    Manages dynamic UI adaptations based on user behavior and ML predictions
    """
    
    def __init__(self, 
                 behavior_tracker: BehaviorTracker,
                 model_manager: TensorFlowJSModelManager,
                 config_dir: Optional[Path] = None):
        
        self.behavior_tracker = behavior_tracker
        self.model_manager = model_manager
        self.config_dir = config_dir or Path.home() / ".localagent"
        
        self.logger = logging.getLogger("AdaptiveInterfaceManager")
        
        # UI state management
        self.current_ui_state = UIState()
        self.adaptation_rules: List[AdaptationRule] = []
        
        # ML models for adaptation
        self.ui_adaptation_model: Optional[AdaptiveUIModel] = None
        
        # Performance tracking
        self.adaptation_history: List[Dict[str, Any]] = []
        self.performance_metrics = {
            'adaptations_applied': 0,
            'adaptation_time_ms': [],
            'user_satisfaction_score': 0.0,
            'fps_maintained': True
        }
        
        # Theme manager
        self.theme_manager: Optional[ClaudeThemeManager] = None
        if THEMES_AVAILABLE:
            self.theme_manager = get_theme_manager()
        
        # Initialize adaptation system
        asyncio.create_task(self._initialize_adaptive_system())
    
    async def _initialize_adaptive_system(self):
        """Initialize the adaptive interface system"""
        try:
            # Load UI state from storage
            await self._load_ui_state()
            
            # Load adaptation rules
            await self._load_adaptation_rules()
            
            # Initialize ML model for UI adaptation
            await self._initialize_ui_adaptation_model()
            
            # Start background adaptation monitoring
            asyncio.create_task(self._adaptation_monitoring_loop())
            
            self.logger.info("Adaptive interface system initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adaptive system: {e}")
    
    async def _initialize_ui_adaptation_model(self):
        """Initialize ML model for UI adaptations"""
        try:
            # Try to load existing model
            self.ui_adaptation_model = await self.model_manager.load_model("ui_adapter")
            
            # Create new model if none exists
            if not self.ui_adaptation_model:
                from .ml_models import create_ui_adaptation_model
                self.ui_adaptation_model = await create_ui_adaptation_model(
                    self.model_manager,
                    ui_features=30,  # User behavior features
                    adaptation_types=len(AdaptationType)
                )
            
        except Exception as e:
            self.logger.warning(f"UI adaptation model not available: {e}")
    
    async def analyze_and_adapt(self, force_analysis: bool = False) -> List[Dict[str, Any]]:
        """Analyze user behavior and apply adaptive changes"""
        start_time = time.time()
        adaptations_applied = []
        
        try:
            # Get recent user behavior patterns
            analyzer = UserBehaviorAnalyzer(self.behavior_tracker)
            
            # Analyze different behavior patterns
            command_patterns = await analyzer.analyze_command_patterns(hours=48)
            provider_patterns = await analyzer.analyze_provider_patterns(hours=72)
            ui_patterns = await analyzer.analyze_ui_patterns(hours=24)
            workflow_patterns = await analyzer.analyze_workflow_patterns(hours=168)
            
            # Generate feature vector for ML model
            features = self._extract_behavior_features(
                command_patterns, provider_patterns, ui_patterns, workflow_patterns
            )
            
            # Get ML predictions if model is available
            ml_adaptations = []
            if self.ui_adaptation_model and features:
                ml_predictions = await self.model_manager.predict(
                    "ui_adapter", features, timeout_ms=5
                )
                
                if ml_predictions:
                    ml_adaptations = self._interpret_ml_predictions(ml_predictions)
            
            # Apply rule-based adaptations
            rule_adaptations = await self._apply_adaptation_rules(
                command_patterns, provider_patterns, ui_patterns, workflow_patterns
            )
            
            # Combine and prioritize adaptations
            all_adaptations = ml_adaptations + rule_adaptations
            selected_adaptations = self._select_adaptations(all_adaptations)
            
            # Apply selected adaptations
            for adaptation in selected_adaptations:
                if await self._apply_adaptation(adaptation):
                    adaptations_applied.append(adaptation)
            
            # Update performance metrics
            adaptation_time = (time.time() - start_time) * 1000
            self.performance_metrics['adaptation_time_ms'].append(adaptation_time)
            self.performance_metrics['adaptations_applied'] += len(adaptations_applied)
            self.performance_metrics['fps_maintained'] = adaptation_time <= 16.0  # 60 FPS
            
            if adaptation_time > 16.0:
                self.logger.warning(f"Adaptation analysis took {adaptation_time:.1f}ms (target: <16ms)")
            
            # Record adaptations
            self._record_adaptations(adaptations_applied, {
                'command_patterns': command_patterns,
                'provider_patterns': provider_patterns,
                'ui_patterns': ui_patterns,
                'analysis_time_ms': adaptation_time
            })
            
            return adaptations_applied
            
        except Exception as e:
            self.logger.error(f"Adaptation analysis failed: {e}")
            return []
    
    def _extract_behavior_features(self, command_patterns: Dict[str, Any],
                                 provider_patterns: Dict[str, Any],
                                 ui_patterns: Dict[str, Any],
                                 workflow_patterns: Dict[str, Any]) -> List[float]:
        """Extract numerical features from behavior patterns for ML model"""
        features = []
        
        # Command usage features (10 features)
        features.extend([
            command_patterns.get('total_commands', 0) / 1000.0,  # Normalized
            command_patterns.get('unique_commands', 0) / 100.0,
            command_patterns.get('efficiency_score', 0.0),
            len(command_patterns.get('most_used_commands', [])) / 20.0,
            len(command_patterns.get('command_sequences', [])) / 50.0,
        ])
        
        # Add time-based patterns
        time_patterns = command_patterns.get('time_patterns', {})
        peak_hours = time_patterns.get('peak_hours', [])
        if peak_hours:
            features.extend([
                peak_hours[0][0] / 24.0,  # Primary peak hour (normalized)
                peak_hours[0][1] / max(1, command_patterns.get('total_commands', 1))  # Peak intensity
            ])
        else:
            features.extend([0.0, 0.0])
        
        # Add more command features to reach 10
        features.extend([0.0, 0.0, 0.0])
        
        # Provider usage features (10 features)
        provider_diversity = provider_patterns.get('provider_diversity', 0)
        features.extend([
            provider_diversity / 10.0,  # Normalized
            1.0 if provider_patterns.get('preferred_provider') else 0.0,
            len(provider_patterns.get('performance_ranking', [])) / 10.0,
        ])
        
        # Average provider performance
        provider_prefs = provider_patterns.get('provider_preferences', {})
        if provider_prefs:
            avg_success_rate = sum(p['success_rate'] for p in provider_prefs.values()) / len(provider_prefs)
            avg_response_time = sum(p['avg_response_time'] for p in provider_prefs.values()) / len(provider_prefs)
            features.extend([
                avg_success_rate,
                min(avg_response_time / 10.0, 1.0)  # Capped at 10s
            ])
        else:
            features.extend([0.0, 0.0])
        
        # Add more provider features to reach 10
        features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
        
        # UI interaction features (10 features) 
        ui_efficiency = ui_patterns.get('ui_efficiency', 0.0)
        element_count = len(ui_patterns.get('element_frequency', {}))
        action_count = len(ui_patterns.get('action_frequency', {}))
        
        features.extend([
            ui_efficiency,
            element_count / 50.0,  # Normalized
            action_count / 20.0,
        ])
        
        # Average response times
        avg_response_times = ui_patterns.get('avg_response_times', {})
        if avg_response_times:
            avg_ui_response = sum(avg_response_times.values()) / len(avg_response_times)
            features.append(min(avg_ui_response / 5.0, 1.0))  # Capped at 5s
        else:
            features.append(0.0)
        
        # Add more UI features to reach 10
        features.extend([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        
        # Ensure exactly 30 features
        while len(features) < 30:
            features.append(0.0)
        
        return features[:30]
    
    def _interpret_ml_predictions(self, predictions: List[float]) -> List[Dict[str, Any]]:
        """Interpret ML model predictions as adaptation recommendations"""
        adaptations = []
        
        adaptation_types = list(AdaptationType)
        
        for i, confidence in enumerate(predictions):
            if i < len(adaptation_types) and confidence > 0.7:  # High confidence threshold
                adaptations.append({
                    'type': adaptation_types[i].value,
                    'confidence': confidence,
                    'source': 'ml_model',
                    'priority': int((1.0 - confidence) * 10) + 1  # Higher confidence = higher priority
                })
        
        return adaptations
    
    async def _apply_adaptation_rules(self, command_patterns: Dict[str, Any],
                                    provider_patterns: Dict[str, Any],
                                    ui_patterns: Dict[str, Any],
                                    workflow_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply rule-based adaptation logic"""
        adaptations = []
        
        # Rule: Frequent command users get power-user layout
        if command_patterns.get('total_commands', 0) > 100:
            if command_patterns.get('efficiency_score', 0) > 0.8:
                adaptations.append({
                    'type': AdaptationType.LAYOUT_OPTIMIZATION.value,
                    'action': {'layout_mode': 'power-user'},
                    'confidence': 0.85,
                    'source': 'rule_based',
                    'priority': 2,
                    'reason': 'High command usage with good efficiency'
                })
        
        # Rule: Users with low efficiency get more help
        if command_patterns.get('efficiency_score', 1.0) < 0.6:
            adaptations.append({
                'type': AdaptationType.HELP_LEVEL_ADAPTATION.value,
                'action': {'help_level': 'beginner', 'show_tips': True},
                'confidence': 0.9,
                'source': 'rule_based', 
                'priority': 1,
                'reason': 'Low efficiency score detected'
            })
        
        # Rule: Provider preferences
        preferred_provider = provider_patterns.get('preferred_provider')
        if preferred_provider:
            adaptations.append({
                'type': AdaptationType.PROVIDER_PREFERENCES.value,
                'action': {'default_provider': preferred_provider},
                'confidence': 0.8,
                'source': 'rule_based',
                'priority': 3,
                'reason': f'User prefers {preferred_provider} provider'
            })
        
        # Rule: Slow UI interactions need performance mode
        ui_efficiency = ui_patterns.get('ui_efficiency', 1.0)
        if ui_efficiency < 0.7:
            adaptations.append({
                'type': AdaptationType.PERFORMANCE_OPTIMIZATION.value,
                'action': {'performance_mode': 'fast', 'reduce_animations': True},
                'confidence': 0.75,
                'source': 'rule_based',
                'priority': 2,
                'reason': 'UI performance issues detected'
            })
        
        # Rule: Command sequences become shortcuts
        sequences = command_patterns.get('command_sequences', [])
        for sequence, count in sequences[:3]:  # Top 3 sequences
            if count > 5 and len(sequence) > 1:  # Used frequently enough
                shortcut_name = f"seq_{'_'.join(sequence[:2])}"
                adaptations.append({
                    'type': AdaptationType.COMMAND_SHORTCUTS.value,
                    'action': {
                        'shortcut_name': shortcut_name,
                        'command_sequence': sequence
                    },
                    'confidence': min(0.9, count / 20.0),
                    'source': 'rule_based',
                    'priority': 4,
                    'reason': f'Frequent command sequence: {" -> ".join(sequence[:2])}'
                })
        
        return adaptations
    
    def _select_adaptations(self, adaptations: List[Dict[str, Any]], max_adaptations: int = 5) -> List[Dict[str, Any]]:
        """Select the best adaptations to apply"""
        # Filter by confidence threshold
        high_confidence = [a for a in adaptations if a.get('confidence', 0) > 0.6]
        
        # Sort by priority (lower number = higher priority) and confidence
        high_confidence.sort(key=lambda x: (x.get('priority', 10), -x.get('confidence', 0)))
        
        # Limit to max adaptations to avoid overwhelming the user
        return high_confidence[:max_adaptations]
    
    async def _apply_adaptation(self, adaptation: Dict[str, Any]) -> bool:
        """Apply a specific adaptation to the UI"""
        try:
            adaptation_type = adaptation.get('type')
            action = adaptation.get('action', {})
            
            if adaptation_type == AdaptationType.LAYOUT_OPTIMIZATION.value:
                return await self._apply_layout_adaptation(action)
            elif adaptation_type == AdaptationType.COMMAND_SHORTCUTS.value:
                return await self._apply_shortcut_adaptation(action)
            elif adaptation_type == AdaptationType.PROVIDER_PREFERENCES.value:
                return await self._apply_provider_adaptation(action)
            elif adaptation_type == AdaptationType.HELP_LEVEL_ADAPTATION.value:
                return await self._apply_help_level_adaptation(action)
            elif adaptation_type == AdaptationType.PERFORMANCE_OPTIMIZATION.value:
                return await self._apply_performance_adaptation(action)
            elif adaptation_type == AdaptationType.THEME_ADJUSTMENT.value:
                return await self._apply_theme_adaptation(action)
            else:
                self.logger.warning(f"Unknown adaptation type: {adaptation_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to apply adaptation: {e}")
            return False
    
    async def _apply_layout_adaptation(self, action: Dict[str, Any]) -> bool:
        """Apply layout optimization adaptations"""
        new_layout = action.get('layout_mode')
        if new_layout and new_layout != self.current_ui_state.layout_mode:
            self.current_ui_state.layout_mode = new_layout
            
            # Apply layout-specific changes
            if new_layout == 'power-user':
                self.current_ui_state.customizations['show_advanced_options'] = True
                self.current_ui_state.customizations['compact_menus'] = True
            elif new_layout == 'minimal':
                self.current_ui_state.customizations['hide_decorations'] = True
                self.current_ui_state.customizations['essential_only'] = True
            
            await self._save_ui_state()
            self.logger.info(f"Applied layout adaptation: {new_layout}")
            return True
        
        return False
    
    async def _apply_shortcut_adaptation(self, action: Dict[str, Any]) -> bool:
        """Apply command shortcut adaptations"""
        shortcut_name = action.get('shortcut_name')
        command_sequence = action.get('command_sequence', [])
        
        if shortcut_name and command_sequence:
            self.current_ui_state.shortcuts[shortcut_name] = ' && '.join(command_sequence)
            await self._save_ui_state()
            self.logger.info(f"Created shortcut '{shortcut_name}' for sequence: {command_sequence}")
            return True
        
        return False
    
    async def _apply_provider_adaptation(self, action: Dict[str, Any]) -> bool:
        """Apply provider preference adaptations"""
        default_provider = action.get('default_provider')
        if default_provider:
            # Update preferred providers list
            if default_provider not in self.current_ui_state.preferred_providers:
                self.current_ui_state.preferred_providers.insert(0, default_provider)
            
            await self._save_ui_state()
            self.logger.info(f"Set preferred provider: {default_provider}")
            return True
        
        return False
    
    async def _apply_help_level_adaptation(self, action: Dict[str, Any]) -> bool:
        """Apply help level adaptations"""
        new_help_level = action.get('help_level')
        show_tips = action.get('show_tips', False)
        
        if new_help_level and new_help_level != self.current_ui_state.help_level:
            self.current_ui_state.help_level = new_help_level
            
            if show_tips:
                self.current_ui_state.customizations['show_contextual_tips'] = True
                self.current_ui_state.customizations['detailed_error_messages'] = True
            
            await self._save_ui_state()
            self.logger.info(f"Adapted help level: {new_help_level}")
            return True
        
        return False
    
    async def _apply_performance_adaptation(self, action: Dict[str, Any]) -> bool:
        """Apply performance optimization adaptations"""
        performance_mode = action.get('performance_mode')
        reduce_animations = action.get('reduce_animations', False)
        
        if performance_mode:
            self.current_ui_state.performance_mode = performance_mode
            
            if reduce_animations:
                self.current_ui_state.customizations['disable_animations'] = True
                self.current_ui_state.customizations['fast_rendering'] = True
            
            await self._save_ui_state()
            self.logger.info(f"Applied performance adaptation: {performance_mode}")
            return True
        
        return False
    
    async def _apply_theme_adaptation(self, action: Dict[str, Any]) -> bool:
        """Apply theme adaptations"""
        theme = action.get('theme')
        if theme and self.theme_manager:
            self.current_ui_state.theme = theme
            
            if theme == 'dark':
                self.theme_manager.apply_dark_mode()
            else:
                self.theme_manager.apply_light_mode()
            
            await self._save_ui_state()
            self.logger.info(f"Applied theme adaptation: {theme}")
            return True
        
        return False
    
    async def _adaptation_monitoring_loop(self):
        """Background loop for monitoring and applying adaptations"""
        while True:
            try:
                # Wait for 5 minutes between adaptation checks
                await asyncio.sleep(300)
                
                # Only analyze if there's been recent user activity
                if self.behavior_tracker.current_session:
                    recent_interactions = len(self.behavior_tracker.current_session.interactions)
                    if recent_interactions > 0:
                        # Run analysis in background
                        asyncio.create_task(self.analyze_and_adapt())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Adaptation monitoring error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    def _record_adaptations(self, adaptations: List[Dict[str, Any]], context: Dict[str, Any]):
        """Record adaptation history for learning"""
        record = {
            'timestamp': time.time(),
            'adaptations': adaptations,
            'context': context,
            'ui_state': {
                'layout_mode': self.current_ui_state.layout_mode,
                'help_level': self.current_ui_state.help_level,
                'performance_mode': self.current_ui_state.performance_mode,
                'shortcut_count': len(self.current_ui_state.shortcuts)
            }
        }
        
        self.adaptation_history.append(record)
        
        # Keep only last 100 adaptations
        if len(self.adaptation_history) > 100:
            self.adaptation_history = self.adaptation_history[-100:]
    
    async def _load_ui_state(self):
        """Load UI state from storage"""
        state_file = self.config_dir / "ui_state.json"
        
        try:
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Update current UI state
                self.current_ui_state.theme = state_data.get('theme', 'default')
                self.current_ui_state.layout_mode = state_data.get('layout_mode', 'standard')
                self.current_ui_state.help_level = state_data.get('help_level', 'intermediate')
                self.current_ui_state.shortcuts = state_data.get('shortcuts', {})
                self.current_ui_state.preferred_providers = state_data.get('preferred_providers', [])
                self.current_ui_state.workflow_presets = state_data.get('workflow_presets', {})
                self.current_ui_state.performance_mode = state_data.get('performance_mode', 'balanced')
                self.current_ui_state.customizations = state_data.get('customizations', {})
                
                self.logger.info("UI state loaded from storage")
        except Exception as e:
            self.logger.warning(f"Failed to load UI state: {e}")
    
    async def _save_ui_state(self):
        """Save current UI state to storage"""
        state_file = self.config_dir / "ui_state.json"
        
        try:
            state_data = {
                'theme': self.current_ui_state.theme,
                'layout_mode': self.current_ui_state.layout_mode,
                'help_level': self.current_ui_state.help_level,
                'shortcuts': self.current_ui_state.shortcuts,
                'preferred_providers': self.current_ui_state.preferred_providers,
                'workflow_presets': self.current_ui_state.workflow_presets,
                'performance_mode': self.current_ui_state.performance_mode,
                'customizations': self.current_ui_state.customizations,
                'last_updated': time.time()
            }
            
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            self.logger.debug("UI state saved to storage")
            
        except Exception as e:
            self.logger.error(f"Failed to save UI state: {e}")
    
    async def _load_adaptation_rules(self):
        """Load adaptation rules from storage"""
        rules_file = self.config_dir / "adaptation_rules.json"
        
        # Create default rules if file doesn't exist
        if not rules_file.exists():
            await self._create_default_adaptation_rules()
        
        try:
            with open(rules_file, 'r') as f:
                rules_data = json.load(f)
            
            self.adaptation_rules = []
            for rule_data in rules_data:
                rule = AdaptationRule(
                    rule_id=rule_data['rule_id'],
                    adaptation_type=AdaptationType(rule_data['adaptation_type']),
                    trigger_conditions=rule_data['trigger_conditions'],
                    adaptation_actions=rule_data['adaptation_actions'],
                    priority=rule_data.get('priority', 5),
                    confidence_threshold=rule_data.get('confidence_threshold', 0.7),
                    enabled=rule_data.get('enabled', True),
                    usage_count=rule_data.get('usage_count', 0),
                    success_rate=rule_data.get('success_rate', 0.0)
                )
                self.adaptation_rules.append(rule)
            
            self.logger.info(f"Loaded {len(self.adaptation_rules)} adaptation rules")
            
        except Exception as e:
            self.logger.error(f"Failed to load adaptation rules: {e}")
    
    async def _create_default_adaptation_rules(self):
        """Create default adaptation rules"""
        default_rules = [
            {
                'rule_id': 'power_user_layout',
                'adaptation_type': AdaptationType.LAYOUT_OPTIMIZATION.value,
                'trigger_conditions': {
                    'total_commands': {'min': 50},
                    'efficiency_score': {'min': 0.8}
                },
                'adaptation_actions': {'layout_mode': 'power-user'},
                'priority': 2,
                'confidence_threshold': 0.8
            },
            {
                'rule_id': 'beginner_help',
                'adaptation_type': AdaptationType.HELP_LEVEL_ADAPTATION.value,
                'trigger_conditions': {
                    'efficiency_score': {'max': 0.6},
                    'error_rate': {'min': 0.2}
                },
                'adaptation_actions': {'help_level': 'beginner', 'show_tips': True},
                'priority': 1,
                'confidence_threshold': 0.9
            }
        ]
        
        rules_file = self.config_dir / "adaptation_rules.json"
        with open(rules_file, 'w') as f:
            json.dump(default_rules, f, indent=2)
    
    def get_current_ui_state(self) -> UIState:
        """Get current UI state"""
        return self.current_ui_state
    
    def get_adaptation_summary(self) -> Dict[str, Any]:
        """Get summary of adaptive interface system"""
        return {
            'current_ui_state': {
                'theme': self.current_ui_state.theme,
                'layout_mode': self.current_ui_state.layout_mode,
                'help_level': self.current_ui_state.help_level,
                'shortcuts_count': len(self.current_ui_state.shortcuts),
                'performance_mode': self.current_ui_state.performance_mode
            },
            'performance_metrics': self.performance_metrics.copy(),
            'adaptation_rules_count': len(self.adaptation_rules),
            'ml_model_available': self.ui_adaptation_model is not None,
            'recent_adaptations': len(self.adaptation_history),
            'system_status': 'active' if self.ui_adaptation_model else 'limited'
        }


# Convenience function
def create_adaptive_interface_manager(
    behavior_tracker: BehaviorTracker,
    model_manager: TensorFlowJSModelManager,
    config_dir: Optional[Path] = None
) -> AdaptiveInterfaceManager:
    """Create adaptive interface manager with dependencies"""
    return AdaptiveInterfaceManager(behavior_tracker, model_manager, config_dir)