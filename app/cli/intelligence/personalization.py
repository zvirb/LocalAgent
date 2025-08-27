"""
Personalization Engine for Adaptive CLI Experiences
===================================================

Creates personalized workspace configurations, preferences, and customizations
based on user behavior patterns and machine learning insights.
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
import hashlib

# Import behavior tracking and ML models
from .behavior_tracker import BehaviorTracker, UserBehaviorAnalyzer
from .ml_models import TensorFlowJSModelManager

class PersonalizationLevel(Enum):
    """Levels of personalization intensity"""
    MINIMAL = "minimal"
    MODERATE = "moderate" 
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"

@dataclass
class UserProfile:
    """Complete user profile with preferences and patterns"""
    user_id: str
    skill_level: str = 'intermediate'  # beginner, intermediate, expert
    interaction_style: str = 'balanced'  # efficient, exploratory, methodical, creative
    preferred_providers: List[str] = field(default_factory=list)
    command_preferences: Dict[str, Any] = field(default_factory=dict)
    workflow_patterns: Dict[str, Any] = field(default_factory=dict)
    ui_preferences: Dict[str, Any] = field(default_factory=dict)
    performance_preferences: Dict[str, Any] = field(default_factory=dict)
    learning_preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    
    def update_timestamp(self):
        self.last_updated = time.time()

@dataclass
class PersonalizationInsight:
    """Insight derived from user behavior"""
    insight_type: str  # 'efficiency', 'preference', 'pattern', 'skill'
    description: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    recommendation: str = ""
    impact_score: float = 0.0  # Expected improvement impact
    
@dataclass
class WorkspaceConfiguration:
    """Personalized workspace configuration"""
    config_id: str
    name: str
    description: str
    settings: Dict[str, Any] = field(default_factory=dict)
    shortcuts: Dict[str, str] = field(default_factory=dict)
    aliases: Dict[str, str] = field(default_factory=dict)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    default_providers: List[str] = field(default_factory=list)
    workflow_presets: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    ui_customizations: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0
    effectiveness_score: float = 0.0

class PersonalizationEngine:
    """
    Core personalization engine that learns user preferences and creates
    customized CLI experiences
    """
    
    def __init__(self,
                 behavior_tracker: BehaviorTracker,
                 model_manager: Optional[TensorFlowJSModelManager] = None,
                 config_dir: Optional[Path] = None):
        
        self.behavior_tracker = behavior_tracker
        self.model_manager = model_manager
        self.config_dir = config_dir or Path.home() / ".localagent"
        
        self.logger = logging.getLogger("PersonalizationEngine")
        
        # User profiles and configurations
        self.user_profiles: Dict[str, UserProfile] = {}
        self.workspace_configurations: Dict[str, WorkspaceConfiguration] = {}
        self.personalization_insights: List[PersonalizationInsight] = []
        
        # Personalization settings
        self.personalization_level = PersonalizationLevel.MODERATE
        self.learning_enabled = True
        self.min_data_points = 10  # Minimum interactions before personalization
        
        # Performance tracking
        self.analysis_times = deque(maxlen=100)
        self.personalization_cache = {}
        
        # Initialize system
        asyncio.create_task(self._initialize_personalization_system())
    
    async def _initialize_personalization_system(self):
        """Initialize the personalization engine"""
        try:
            # Load existing user profiles
            await self._load_user_profiles()
            
            # Load workspace configurations
            await self._load_workspace_configurations()
            
            # Load personalization insights
            await self._load_personalization_insights()
            
            # Start background learning process
            asyncio.create_task(self._continuous_learning_loop())
            
            self.logger.info("Personalization engine initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize personalization system: {e}")
    
    async def analyze_user_patterns(self, user_id: str, force_update: bool = False) -> UserProfile:
        """Analyze user behavior patterns and update profile"""
        start_time = time.time()
        
        try:
            # Get or create user profile
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = UserProfile(user_id=user_id)
            
            profile = self.user_profiles[user_id]
            
            # Check if analysis is needed
            if not force_update and time.time() - profile.last_updated < 1800:  # 30 minutes
                return profile
            
            # Get behavior analyzer
            analyzer = UserBehaviorAnalyzer(self.behavior_tracker)
            
            # Analyze different behavior aspects
            command_patterns = await analyzer.analyze_command_patterns(hours=168)
            provider_patterns = await analyzer.analyze_provider_patterns(hours=168)
            ui_patterns = await analyzer.analyze_ui_patterns(hours=72)
            workflow_patterns = await analyzer.analyze_workflow_patterns(hours=336)
            
            # Update profile based on analysis
            await self._update_user_profile(profile, command_patterns, provider_patterns, ui_patterns, workflow_patterns)
            
            # Generate insights
            insights = await self._generate_personalization_insights(profile, {
                'command_patterns': command_patterns,
                'provider_patterns': provider_patterns,
                'ui_patterns': ui_patterns,
                'workflow_patterns': workflow_patterns
            })
            
            self.personalization_insights.extend(insights)
            
            # Update profile timestamp
            profile.update_timestamp()
            
            # Save updated profile
            await self._save_user_profiles()
            
            # Track performance
            analysis_time = (time.time() - start_time) * 1000
            self.analysis_times.append(analysis_time)
            
            if analysis_time > 100:  # Should be fast for good UX
                self.logger.warning(f"User analysis took {analysis_time:.1f}ms")
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to analyze user patterns: {e}")
            return self.user_profiles.get(user_id, UserProfile(user_id=user_id))
    
    async def _update_user_profile(self, profile: UserProfile,
                                 command_patterns: Dict[str, Any],
                                 provider_patterns: Dict[str, Any],
                                 ui_patterns: Dict[str, Any],
                                 workflow_patterns: Dict[str, Any]):
        """Update user profile based on behavior analysis"""
        
        # Determine skill level
        total_commands = command_patterns.get('total_commands', 0)
        unique_commands = command_patterns.get('unique_commands', 0)
        efficiency_score = command_patterns.get('efficiency_score', 0.5)
        
        if total_commands > 200 and unique_commands > 50 and efficiency_score > 0.8:
            profile.skill_level = 'expert'
        elif total_commands > 50 and unique_commands > 20 and efficiency_score > 0.6:
            profile.skill_level = 'intermediate'
        else:
            profile.skill_level = 'beginner'
        
        # Determine interaction style
        command_sequences = len(command_patterns.get('command_sequences', []))
        most_used_count = len(command_patterns.get('most_used_commands', []))
        
        if command_sequences > 10 and most_used_count < 5:
            profile.interaction_style = 'exploratory'
        elif efficiency_score > 0.8 and most_used_count > 10:
            profile.interaction_style = 'efficient'
        elif command_sequences > 5 and efficiency_score > 0.7:
            profile.interaction_style = 'methodical'
        else:
            profile.interaction_style = 'creative'
        
        # Update provider preferences
        preferred_provider = provider_patterns.get('preferred_provider')
        if preferred_provider and preferred_provider not in profile.preferred_providers:
            profile.preferred_providers.insert(0, preferred_provider)
        
        # Update command preferences
        most_used_commands = command_patterns.get('most_used_commands', [])
        profile.command_preferences = {
            'frequently_used': [cmd for cmd, count in most_used_commands[:10]],
            'command_sequences': command_patterns.get('command_sequences', [])[:5],
            'efficiency_score': efficiency_score,
            'preferred_time_patterns': command_patterns.get('time_patterns', {})
        }
        
        # Update workflow patterns
        profile.workflow_patterns = {
            'workflow_frequency': workflow_patterns.get('workflow_frequency', {}),
            'phase_success_rates': workflow_patterns.get('phase_success_rates', {}),
            'agent_usage': workflow_patterns.get('agent_usage', {}),
            'preferred_workflow_types': []
        }
        
        # Determine preferred workflow types
        workflow_freq = workflow_patterns.get('workflow_frequency', {})
        if workflow_freq:
            sorted_workflows = sorted(workflow_freq.items(), key=lambda x: x[1], reverse=True)
            profile.workflow_patterns['preferred_workflow_types'] = [wf[0] for wf in sorted_workflows[:3]]
        
        # Update UI preferences
        ui_efficiency = ui_patterns.get('ui_efficiency', 0.8)
        element_frequency = ui_patterns.get('element_frequency', {})
        
        profile.ui_preferences = {
            'ui_efficiency': ui_efficiency,
            'preferred_elements': list(element_frequency.keys())[:5],
            'layout_preference': 'compact' if ui_efficiency > 0.8 else 'detailed',
            'help_level': profile.skill_level
        }
        
        # Update performance preferences
        avg_response_times = ui_patterns.get('avg_response_times', {})
        if avg_response_times:
            avg_ui_response = sum(avg_response_times.values()) / len(avg_response_times)
            
            profile.performance_preferences = {
                'speed_priority': avg_ui_response > 2.0,  # User seems to prefer speed
                'detail_vs_speed': 'speed' if avg_ui_response > 2.0 else 'detail',
                'animation_preference': ui_efficiency > 0.7
            }
        
        # Update learning preferences based on skill progression
        profile.learning_preferences = {
            'show_tips': profile.skill_level == 'beginner',
            'contextual_help': profile.skill_level in ['beginner', 'intermediate'],
            'advanced_features': profile.skill_level == 'expert',
            'learning_mode': 'active' if efficiency_score < 0.6 else 'passive'
        }
    
    async def _generate_personalization_insights(self, profile: UserProfile, 
                                               analysis_data: Dict[str, Any]) -> List[PersonalizationInsight]:
        """Generate actionable personalization insights"""
        insights = []
        
        # Skill level insights
        if profile.skill_level == 'expert':
            insights.append(PersonalizationInsight(
                insight_type='skill',
                description='User demonstrates expert-level CLI proficiency',
                confidence=0.9,
                evidence=[
                    f"High efficiency score: {profile.command_preferences.get('efficiency_score', 0)}",
                    f"Uses {len(profile.command_preferences.get('frequently_used', []))} commands regularly",
                    f"Shows consistent workflow patterns"
                ],
                recommendation='Enable advanced features and reduce help prompts',
                impact_score=0.8
            ))
        elif profile.skill_level == 'beginner':
            insights.append(PersonalizationInsight(
                insight_type='skill',
                description='User would benefit from guided learning',
                confidence=0.8,
                evidence=[
                    f"Low efficiency score: {profile.command_preferences.get('efficiency_score', 0)}",
                    'Limited command vocabulary',
                    'Inconsistent usage patterns'
                ],
                recommendation='Enable contextual help and command suggestions',
                impact_score=0.9
            ))
        
        # Efficiency insights
        efficiency = profile.command_preferences.get('efficiency_score', 0.5)
        if efficiency < 0.6:
            insights.append(PersonalizationInsight(
                insight_type='efficiency',
                description='User efficiency could be improved',
                confidence=0.7,
                evidence=[
                    f"Efficiency score below threshold: {efficiency}",
                    'Potential for workflow optimization'
                ],
                recommendation='Suggest command shortcuts and workflow automation',
                impact_score=0.7
            ))
        
        # Provider preference insights
        if profile.preferred_providers:
            primary_provider = profile.preferred_providers[0]
            insights.append(PersonalizationInsight(
                insight_type='preference',
                description=f'Strong preference for {primary_provider} provider',
                confidence=0.8,
                evidence=[f'Consistently uses {primary_provider} provider'],
                recommendation=f'Set {primary_provider} as default and optimize its integration',
                impact_score=0.6
            ))
        
        # Interaction style insights
        if profile.interaction_style == 'exploratory':
            insights.append(PersonalizationInsight(
                insight_type='pattern',
                description='User prefers exploring different approaches',
                confidence=0.7,
                evidence=['Diverse command usage patterns', 'Frequent experimentation'],
                recommendation='Provide alternative command suggestions and discovery features',
                impact_score=0.5
            ))
        elif profile.interaction_style == 'efficient':
            insights.append(PersonalizationInsight(
                insight_type='pattern',
                description='User prioritizes efficiency and speed',
                confidence=0.8,
                evidence=['Consistent use of shortcuts', 'High command frequency'],
                recommendation='Optimize for speed, provide more shortcuts and automation',
                impact_score=0.8
            ))
        
        # Performance insights
        if profile.performance_preferences.get('speed_priority', False):
            insights.append(PersonalizationInsight(
                insight_type='performance',
                description='User values response speed over detailed output',
                confidence=0.7,
                evidence=['Fast interaction patterns', 'Minimal UI dwell time'],
                recommendation='Enable performance mode and reduce visual complexity',
                impact_score=0.6
            ))
        
        return insights
    
    async def create_personalized_workspace(self, user_id: str, 
                                          workspace_name: str = "default") -> WorkspaceConfiguration:
        """Create a personalized workspace configuration for the user"""
        
        try:
            # Analyze user patterns first
            profile = await self.analyze_user_patterns(user_id)
            
            # Generate workspace ID
            workspace_id = f"{user_id}_{workspace_name}_{int(time.time())}"
            
            # Create base workspace configuration
            workspace = WorkspaceConfiguration(
                config_id=workspace_id,
                name=workspace_name,
                description=f"Personalized workspace for {profile.skill_level} {profile.interaction_style} user"
            )
            
            # Customize settings based on user profile
            workspace.settings = await self._generate_personalized_settings(profile)
            
            # Create personalized shortcuts
            workspace.shortcuts = await self._generate_personalized_shortcuts(profile)
            
            # Create command aliases
            workspace.aliases = await self._generate_personalized_aliases(profile)
            
            # Set default providers
            workspace.default_providers = profile.preferred_providers[:3]  # Top 3 preferred
            
            # Create workflow presets
            workspace.workflow_presets = await self._generate_workflow_presets(profile)
            
            # Customize UI
            workspace.ui_customizations = await self._generate_ui_customizations(profile)
            
            # Store workspace
            self.workspace_configurations[workspace_id] = workspace
            await self._save_workspace_configurations()
            
            self.logger.info(f"Created personalized workspace: {workspace_id}")
            
            return workspace
            
        except Exception as e:
            self.logger.error(f"Failed to create personalized workspace: {e}")
            raise
    
    async def _generate_personalized_settings(self, profile: UserProfile) -> Dict[str, Any]:
        """Generate personalized settings based on user profile"""
        settings = {}
        
        # Skill-based settings
        if profile.skill_level == 'beginner':
            settings.update({
                'show_command_help': True,
                'confirm_destructive_actions': True,
                'verbose_output': True,
                'auto_suggest_commands': True,
                'show_progress_indicators': True
            })
        elif profile.skill_level == 'expert':
            settings.update({
                'show_command_help': False,
                'confirm_destructive_actions': False,
                'verbose_output': False,
                'auto_suggest_commands': False,
                'compact_output': True,
                'advanced_features': True
            })
        else:  # intermediate
            settings.update({
                'show_command_help': True,
                'confirm_destructive_actions': True,
                'verbose_output': False,
                'auto_suggest_commands': True,
                'balanced_output': True
            })
        
        # Performance-based settings
        if profile.performance_preferences.get('speed_priority', False):
            settings.update({
                'animation_duration': 'fast',
                'reduce_animations': True,
                'instant_feedback': True,
                'parallel_execution': True
            })
        
        # Interaction style settings
        if profile.interaction_style == 'exploratory':
            settings.update({
                'show_alternatives': True,
                'discovery_mode': True,
                'example_suggestions': True
            })
        elif profile.interaction_style == 'efficient':
            settings.update({
                'hotkeys_enabled': True,
                'auto_complete_aggressive': True,
                'skip_confirmations': True
            })
        
        return settings
    
    async def _generate_personalized_shortcuts(self, profile: UserProfile) -> Dict[str, str]:
        """Generate personalized shortcuts based on frequently used commands"""
        shortcuts = {}
        
        frequently_used = profile.command_preferences.get('frequently_used', [])
        
        # Create shortcuts for most used commands
        shortcut_mapping = {
            0: 'ctrl+1', 1: 'ctrl+2', 2: 'ctrl+3', 3: 'ctrl+4', 4: 'ctrl+5',
            5: 'ctrl+6', 6: 'ctrl+7', 7: 'ctrl+8', 8: 'ctrl+9', 9: 'ctrl+0'
        }
        
        for i, command in enumerate(frequently_used[:10]):  # Top 10 commands
            if i in shortcut_mapping:
                shortcuts[shortcut_mapping[i]] = command
        
        # Add command sequences as shortcuts
        sequences = profile.command_preferences.get('command_sequences', [])
        for i, (sequence, count) in enumerate(sequences[:3]):  # Top 3 sequences
            if count > 5:  # Used frequently
                shortcut_key = f'ctrl+shift+{i+1}'
                shortcuts[shortcut_key] = ' && '.join(sequence)
        
        # Add skill-level specific shortcuts
        if profile.skill_level == 'expert':
            shortcuts.update({
                'ctrl+alt+h': 'help --advanced',
                'ctrl+alt+s': 'status --detailed',
                'ctrl+alt+l': 'logs --tail'
            })
        elif profile.skill_level == 'beginner':
            shortcuts.update({
                'ctrl+h': 'help',
                'ctrl+alt+?': 'help getting-started',
                'f1': 'help --interactive'
            })
        
        return shortcuts
    
    async def _generate_personalized_aliases(self, profile: UserProfile) -> Dict[str, str]:
        """Generate personalized command aliases"""
        aliases = {}
        
        # Skill-based aliases
        if profile.skill_level == 'expert':
            aliases.update({
                'q': 'exit',
                's': 'status',
                'l': 'list',
                'r': 'run',
                'a': 'analyze',
                'quick': 'workflow execute --fast'
            })
        
        # Provider-based aliases
        for provider in profile.preferred_providers[:3]:
            aliases[provider[0]] = f'provider {provider}'  # First letter shortcut
        
        # Workflow-based aliases
        preferred_workflows = profile.workflow_patterns.get('preferred_workflow_types', [])
        for i, workflow in enumerate(preferred_workflows[:3]):
            aliases[f'wf{i+1}'] = f'workflow {workflow}'
        
        # Interaction style aliases
        if profile.interaction_style == 'efficient':
            aliases.update({
                'last': 'history --last',
                'repeat': 'history --repeat',
                'undo': 'history --undo'
            })
        
        return aliases
    
    async def _generate_workflow_presets(self, profile: UserProfile) -> Dict[str, Dict[str, Any]]:
        """Generate personalized workflow presets"""
        presets = {}
        
        # Create preset based on skill level
        if profile.skill_level == 'beginner':
            presets['guided'] = {
                'execution_mode': 'guided',
                'show_explanations': True,
                'confirm_steps': True,
                'collect_evidence': True,
                'phases': ['phase_0', 'phase_1', 'phase_2', 'phase_6']  # Simplified workflow
            }
        elif profile.skill_level == 'expert':
            presets['expert'] = {
                'execution_mode': 'automated',
                'show_explanations': False,
                'confirm_steps': False,
                'parallel_execution': True,
                'phases': 'all',
                'advanced_features': True
            }
        
        # Create preset based on interaction style
        if profile.interaction_style == 'efficient':
            presets['fast'] = {
                'execution_mode': 'automated',
                'skip_optional_phases': True,
                'parallel_agents': profile.performance_preferences.get('speed_priority', False),
                'minimal_output': True
            }
        elif profile.interaction_style == 'exploratory':
            presets['detailed'] = {
                'execution_mode': 'interactive',
                'show_alternatives': True,
                'detailed_logging': True,
                'experimental_features': True
            }
        
        # Create preset based on preferred workflow types
        preferred_workflows = profile.workflow_patterns.get('preferred_workflow_types', [])
        for workflow_type in preferred_workflows[:2]:
            presets[workflow_type] = {
                'workflow_type': workflow_type,
                'optimized_for': workflow_type,
                'phase_priorities': self._get_workflow_phase_priorities(workflow_type)
            }
        
        return presets
    
    async def _generate_ui_customizations(self, profile: UserProfile) -> Dict[str, Any]:
        """Generate personalized UI customizations"""
        customizations = {}
        
        # Layout based on skill level
        if profile.skill_level == 'expert':
            customizations.update({
                'layout': 'compact',
                'show_advanced_options': True,
                'hide_beginner_hints': True,
                'terminal_style': 'power_user'
            })
        elif profile.skill_level == 'beginner':
            customizations.update({
                'layout': 'guided',
                'show_help_panels': True,
                'highlight_important_options': True,
                'terminal_style': 'friendly'
            })
        
        # Theme based on preferences
        if profile.ui_preferences.get('layout_preference') == 'compact':
            customizations['theme'] = 'minimal'
        else:
            customizations['theme'] = 'default'
        
        # Performance-based customizations
        if profile.performance_preferences.get('speed_priority', False):
            customizations.update({
                'animations': 'minimal',
                'transitions': 'fast',
                'loading_indicators': 'simple'
            })
        
        # Provider-specific UI
        if profile.preferred_providers:
            customizations['default_provider_ui'] = profile.preferred_providers[0]
            customizations['provider_shortcuts'] = True
        
        return customizations
    
    def _get_workflow_phase_priorities(self, workflow_type: str) -> List[str]:
        """Get phase priorities for specific workflow types"""
        priorities = {
            'development': ['phase_1', 'phase_4', 'phase_6', 'phase_8'],
            'analysis': ['phase_1', 'phase_2', 'phase_7'],
            'deployment': ['phase_4', 'phase_6', 'phase_9'],
            'research': ['phase_1', 'phase_2', 'phase_7'],
            'testing': ['phase_6', 'phase_7']
        }
        
        return priorities.get(workflow_type, ['phase_1', 'phase_4', 'phase_6'])
    
    async def get_personalized_recommendations(self, user_id: str) -> List[PersonalizationInsight]:
        """Get personalized recommendations for the user"""
        try:
            # Ensure user profile is up to date
            await self.analyze_user_patterns(user_id)
            
            # Filter insights for this user
            user_insights = [
                insight for insight in self.personalization_insights
                if hasattr(insight, 'user_id') and insight.user_id == user_id
            ]
            
            # Sort by impact score
            user_insights.sort(key=lambda x: x.impact_score, reverse=True)
            
            return user_insights[:10]  # Top 10 recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to get recommendations for {user_id}: {e}")
            return []
    
    async def apply_personalization(self, user_id: str, workspace_id: Optional[str] = None) -> bool:
        """Apply personalization settings for the user"""
        try:
            # Get user profile
            if user_id not in self.user_profiles:
                await self.analyze_user_patterns(user_id)
            
            profile = self.user_profiles[user_id]
            
            # Get or create workspace
            if workspace_id and workspace_id in self.workspace_configurations:
                workspace = self.workspace_configurations[workspace_id]
            else:
                workspace = await self.create_personalized_workspace(user_id)
            
            # Apply settings to current session
            # This would integrate with the CLI system to actually apply the settings
            
            self.logger.info(f"Applied personalization for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply personalization: {e}")
            return False
    
    async def _continuous_learning_loop(self):
        """Continuous learning process that runs in the background"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                if not self.learning_enabled:
                    continue
                
                # Update all user profiles
                for user_id in self.user_profiles.keys():
                    try:
                        await self.analyze_user_patterns(user_id)
                    except Exception as e:
                        self.logger.warning(f"Failed to update profile for {user_id}: {e}")
                
                # Cleanup old insights
                cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days
                self.personalization_insights = [
                    insight for insight in self.personalization_insights
                    if hasattr(insight, 'created_at') and insight.created_at > cutoff_time
                ]
                
                # Save updated data
                await self._save_user_profiles()
                await self._save_personalization_insights()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Continuous learning error: {e}")
    
    async def _load_user_profiles(self):
        """Load user profiles from storage"""
        profiles_file = self.config_dir / "user_profiles.json"
        
        try:
            if profiles_file.exists():
                with open(profiles_file, 'r') as f:
                    profiles_data = json.load(f)
                
                for user_id, profile_data in profiles_data.items():
                    self.user_profiles[user_id] = UserProfile(**profile_data)
                
                self.logger.info(f"Loaded {len(self.user_profiles)} user profiles")
                
        except Exception as e:
            self.logger.warning(f"Failed to load user profiles: {e}")
    
    async def _save_user_profiles(self):
        """Save user profiles to storage"""
        profiles_file = self.config_dir / "user_profiles.json"
        
        try:
            profiles_data = {
                user_id: asdict(profile)
                for user_id, profile in self.user_profiles.items()
            }
            
            with open(profiles_file, 'w') as f:
                json.dump(profiles_data, f, indent=2)
            
            self.logger.debug("User profiles saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save user profiles: {e}")
    
    async def _load_workspace_configurations(self):
        """Load workspace configurations from storage"""
        workspaces_file = self.config_dir / "workspace_configurations.json"
        
        try:
            if workspaces_file.exists():
                with open(workspaces_file, 'r') as f:
                    workspaces_data = json.load(f)
                
                for config_id, config_data in workspaces_data.items():
                    self.workspace_configurations[config_id] = WorkspaceConfiguration(**config_data)
                
                self.logger.info(f"Loaded {len(self.workspace_configurations)} workspace configurations")
                
        except Exception as e:
            self.logger.warning(f"Failed to load workspace configurations: {e}")
    
    async def _save_workspace_configurations(self):
        """Save workspace configurations to storage"""
        workspaces_file = self.config_dir / "workspace_configurations.json"
        
        try:
            workspaces_data = {
                config_id: asdict(config)
                for config_id, config in self.workspace_configurations.items()
            }
            
            with open(workspaces_file, 'w') as f:
                json.dump(workspaces_data, f, indent=2)
            
            self.logger.debug("Workspace configurations saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save workspace configurations: {e}")
    
    async def _load_personalization_insights(self):
        """Load personalization insights from storage"""
        insights_file = self.config_dir / "personalization_insights.json"
        
        try:
            if insights_file.exists():
                with open(insights_file, 'r') as f:
                    insights_data = json.load(f)
                
                self.personalization_insights = [
                    PersonalizationInsight(**insight_data)
                    for insight_data in insights_data
                ]
                
                self.logger.info(f"Loaded {len(self.personalization_insights)} insights")
                
        except Exception as e:
            self.logger.warning(f"Failed to load personalization insights: {e}")
    
    async def _save_personalization_insights(self):
        """Save personalization insights to storage"""
        insights_file = self.config_dir / "personalization_insights.json"
        
        try:
            insights_data = [asdict(insight) for insight in self.personalization_insights]
            
            with open(insights_file, 'w') as f:
                json.dump(insights_data, f, indent=2)
            
            self.logger.debug("Personalization insights saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save personalization insights: {e}")
    
    def get_personalization_summary(self) -> Dict[str, Any]:
        """Get summary of personalization system status"""
        return {
            'user_profiles_count': len(self.user_profiles),
            'workspace_configurations_count': len(self.workspace_configurations),
            'insights_count': len(self.personalization_insights),
            'personalization_level': self.personalization_level.value,
            'learning_enabled': self.learning_enabled,
            'avg_analysis_time_ms': sum(self.analysis_times) / len(self.analysis_times) if self.analysis_times else 0,
            'cache_size': len(self.personalization_cache)
        }


# Convenience functions
def create_personalization_engine(
    behavior_tracker: BehaviorTracker,
    model_manager: Optional[TensorFlowJSModelManager] = None,
    config_dir: Optional[Path] = None
) -> PersonalizationEngine:
    """Create personalization engine with dependencies"""
    return PersonalizationEngine(behavior_tracker, model_manager, config_dir)

def generate_user_id(identifier: Optional[str] = None) -> str:
    """Generate a unique user ID"""
    if identifier:
        return hashlib.md5(identifier.encode()).hexdigest()[:16]
    else:
        return hashlib.md5(str(time.time()).encode()).hexdigest()[:16]