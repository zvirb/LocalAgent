"""
Intelligence Integration Manager
===============================

Integrates all AI intelligence components with existing MCP services,
pattern systems, and CLI infrastructure for seamless operation.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import json

# Import all intelligence components
from .behavior_tracker import BehaviorTracker, get_behavior_tracker
from .ml_models import TensorFlowJSModelManager
from .adaptive_interface import AdaptiveInterfaceManager, create_adaptive_interface_manager
from .command_intelligence import IntelligentCommandProcessor, create_intelligent_command_processor
from .nlp_processor import NaturalLanguageProcessor, create_nlp_processor
from .personalization import PersonalizationEngine, create_personalization_engine, generate_user_id
from .performance_predictor import PerformancePredictionModel, create_performance_predictor

# Import MCP integrations
try:
    from ...mcp.patterns.intelligent_selector import intelligent_selector
    from ...mcp.coordination_mcp import get_coordination_client
    from ...mcp.workflow_state_mcp import get_workflow_state_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Import CLI components
try:
    from ..ui.themes import get_theme_manager
    from ..core.config import LocalAgentConfig
    CLI_COMPONENTS_AVAILABLE = True
except ImportError:
    CLI_COMPONENTS_AVAILABLE = False

@dataclass
class IntelligenceConfig:
    """Configuration for intelligence system"""
    enable_behavior_tracking: bool = True
    enable_ml_models: bool = True
    enable_adaptive_interface: bool = True
    enable_command_intelligence: bool = True
    enable_nlp_processing: bool = True
    enable_personalization: bool = True
    enable_performance_prediction: bool = True
    performance_target_fps: int = 60
    memory_limit_mb: int = 500
    learning_enabled: bool = True
    user_privacy_mode: bool = True

@dataclass
class SystemStatus:
    """Status of intelligence system components"""
    behavior_tracker_active: bool = False
    ml_models_loaded: int = 0
    adaptive_interface_active: bool = False
    command_intelligence_active: bool = False
    nlp_processor_active: bool = False
    personalization_active: bool = False
    performance_predictor_active: bool = False
    mcp_integration_active: bool = False
    total_memory_usage_mb: float = 0.0
    avg_response_time_ms: float = 0.0
    fps_compliant: bool = True

class IntelligenceIntegrationManager:
    """
    Central manager that integrates all AI intelligence components
    with existing systems and provides unified interface
    """
    
    def __init__(self, config: IntelligenceConfig, config_dir: Optional[Path] = None):
        self.config = config
        self.config_dir = config_dir or Path.home() / ".localagent" / "intelligence"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("IntelligenceIntegrationManager")
        
        # Component instances
        self.behavior_tracker: Optional[BehaviorTracker] = None
        self.model_manager: Optional[TensorFlowJSModelManager] = None
        self.adaptive_interface: Optional[AdaptiveInterfaceManager] = None
        self.command_intelligence: Optional[IntelligentCommandProcessor] = None
        self.nlp_processor: Optional[NaturalLanguageProcessor] = None
        self.personalization_engine: Optional[PersonalizationEngine] = None
        self.performance_predictor: Optional[PerformancePredictionModel] = None
        
        # Integration state
        self.current_user_id: Optional[str] = None
        self.system_status = SystemStatus()
        self.integration_tasks: List[asyncio.Task] = []
        
        # Performance monitoring
        self.performance_metrics = {
            'requests_processed': 0,
            'avg_response_time': 0.0,
            'memory_usage_history': [],
            'fps_violations': 0
        }
    
    async def initialize(self, user_identifier: Optional[str] = None) -> bool:
        """Initialize the complete intelligence system"""
        try:
            self.logger.info("Initializing AI intelligence system...")
            
            # Generate user ID
            self.current_user_id = generate_user_id(user_identifier)
            
            # Initialize components in dependency order
            success = True
            
            # 1. Behavior tracking (foundation for all learning)
            if self.config.enable_behavior_tracking:
                success &= await self._initialize_behavior_tracking()
            
            # 2. ML models manager
            if self.config.enable_ml_models:
                success &= await self._initialize_ml_models()
            
            # 3. Intelligence components that depend on behavior tracking
            if self.config.enable_command_intelligence:
                success &= await self._initialize_command_intelligence()
            
            if self.config.enable_nlp_processing:
                success &= await self._initialize_nlp_processor()
            
            if self.config.enable_personalization:
                success &= await self._initialize_personalization()
            
            if self.config.enable_performance_prediction:
                success &= await self._initialize_performance_prediction()
            
            # 4. Adaptive interface (depends on most other components)
            if self.config.enable_adaptive_interface:
                success &= await self._initialize_adaptive_interface()
            
            # 5. Integration with external systems
            await self._setup_mcp_integration()
            await self._setup_cli_integration()
            
            # 6. Start background services
            await self._start_background_services()
            
            # Update system status
            await self._update_system_status()
            
            self.logger.info(f"Intelligence system initialized: {'success' if success else 'partial'}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to initialize intelligence system: {e}")
            return False
    
    async def _initialize_behavior_tracking(self) -> bool:
        """Initialize behavior tracking system"""
        try:
            self.behavior_tracker = get_behavior_tracker(self.config_dir)
            
            # Start user session
            session_id = self.behavior_tracker.start_session({
                'user_id': self.current_user_id,
                'intelligence_enabled': True,
                'privacy_mode': self.config.user_privacy_mode
            })
            
            self.system_status.behavior_tracker_active = True
            self.logger.info(f"Behavior tracking initialized with session: {session_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize behavior tracking: {e}")
            return False
    
    async def _initialize_ml_models(self) -> bool:
        """Initialize TensorFlow.js ML models"""
        try:
            models_dir = self.config_dir / "models"
            self.model_manager = TensorFlowJSModelManager(models_dir)
            
            # Initialize core models
            core_models = []
            
            # Behavior prediction model
            try:
                from .ml_models import create_behavior_prediction_model
                behavior_model = await create_behavior_prediction_model(self.model_manager)
                core_models.append(behavior_model)
            except Exception as e:
                self.logger.warning(f"Failed to create behavior prediction model: {e}")
            
            # Command completion model
            try:
                from .ml_models import create_command_completion_model
                command_model = await create_command_completion_model(self.model_manager)
                core_models.append(command_model)
            except Exception as e:
                self.logger.warning(f"Failed to create command completion model: {e}")
            
            # UI adaptation model
            try:
                from .ml_models import create_ui_adaptation_model
                ui_model = await create_ui_adaptation_model(self.model_manager)
                core_models.append(ui_model)
            except Exception as e:
                self.logger.warning(f"Failed to create UI adaptation model: {e}")
            
            self.system_status.ml_models_loaded = len(core_models)
            self.logger.info(f"ML models initialized: {len(core_models)} models loaded")
            
            return len(core_models) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ML models: {e}")
            return False
    
    async def _initialize_command_intelligence(self) -> bool:
        """Initialize intelligent command processing"""
        try:
            if not self.behavior_tracker:
                self.logger.warning("Command intelligence requires behavior tracker")
                return False
            
            self.command_intelligence = create_intelligent_command_processor(
                self.behavior_tracker,
                self.model_manager,
                self.config_dir
            )
            
            self.system_status.command_intelligence_active = True
            self.logger.info("Command intelligence initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize command intelligence: {e}")
            return False
    
    async def _initialize_nlp_processor(self) -> bool:
        """Initialize natural language processor"""
        try:
            self.nlp_processor = create_nlp_processor(
                self.behavior_tracker,
                self.config_dir
            )
            
            self.system_status.nlp_processor_active = True
            self.logger.info("NLP processor initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NLP processor: {e}")
            return False
    
    async def _initialize_personalization(self) -> bool:
        """Initialize personalization engine"""
        try:
            if not self.behavior_tracker:
                self.logger.warning("Personalization requires behavior tracker")
                return False
            
            self.personalization_engine = create_personalization_engine(
                self.behavior_tracker,
                self.model_manager,
                self.config_dir
            )
            
            self.system_status.personalization_active = True
            self.logger.info("Personalization engine initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize personalization: {e}")
            return False
    
    async def _initialize_performance_prediction(self) -> bool:
        """Initialize performance prediction models"""
        try:
            if not self.behavior_tracker:
                self.logger.warning("Performance prediction requires behavior tracker")
                return False
            
            self.performance_predictor = create_performance_predictor(
                self.behavior_tracker,
                self.model_manager,
                self.config_dir
            )
            
            self.system_status.performance_predictor_active = True
            self.logger.info("Performance predictor initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize performance prediction: {e}")
            return False
    
    async def _initialize_adaptive_interface(self) -> bool:
        """Initialize adaptive interface manager"""
        try:
            if not self.behavior_tracker or not self.model_manager:
                self.logger.warning("Adaptive interface requires behavior tracker and ML models")
                return False
            
            self.adaptive_interface = create_adaptive_interface_manager(
                self.behavior_tracker,
                self.model_manager,
                self.config_dir
            )
            
            self.system_status.adaptive_interface_active = True
            self.logger.info("Adaptive interface initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adaptive interface: {e}")
            return False
    
    async def _setup_mcp_integration(self):
        """Setup integration with MCP services"""
        try:
            if not MCP_AVAILABLE:
                self.logger.info("MCP services not available for integration")
                return
            
            # Integration with intelligent pattern selector
            if hasattr(intelligent_selector, 'set_behavior_tracker'):
                intelligent_selector.set_behavior_tracker(self.behavior_tracker)
            
            # Integration with coordination MCP
            coordination_client = await get_coordination_client()
            if coordination_client and self.behavior_tracker:
                # Register intelligence events
                await coordination_client.register_event_handler(
                    'user_interaction',
                    self._handle_coordination_event
                )
            
            # Integration with workflow state MCP
            workflow_client = await get_workflow_state_client()
            if workflow_client and self.performance_predictor:
                # Register for workflow state changes
                await workflow_client.register_state_change_handler(
                    self._handle_workflow_state_change
                )
            
            self.system_status.mcp_integration_active = True
            self.logger.info("MCP integration setup complete")
            
        except Exception as e:
            self.logger.warning(f"MCP integration setup failed: {e}")
    
    async def _setup_cli_integration(self):
        """Setup integration with CLI components"""
        try:
            if not CLI_COMPONENTS_AVAILABLE:
                self.logger.info("CLI components not available for integration")
                return
            
            # Integration with theme manager
            theme_manager = get_theme_manager()
            if theme_manager and self.adaptive_interface:
                # Connect adaptive interface to theme system
                pass  # Implementation would depend on theme manager API
            
            self.logger.info("CLI integration setup complete")
            
        except Exception as e:
            self.logger.warning(f"CLI integration setup failed: {e}")
    
    async def _start_background_services(self):
        """Start background intelligence services"""
        try:
            # Performance monitoring task
            monitoring_task = asyncio.create_task(self._performance_monitoring_loop())
            self.integration_tasks.append(monitoring_task)
            
            # Periodic intelligence updates
            intelligence_task = asyncio.create_task(self._intelligence_update_loop())
            self.integration_tasks.append(intelligence_task)
            
            # Memory management task
            memory_task = asyncio.create_task(self._memory_management_loop())
            self.integration_tasks.append(memory_task)
            
            self.logger.info("Background services started")
            
        except Exception as e:
            self.logger.error(f"Failed to start background services: {e}")
    
    # Public API methods
    
    async def get_command_suggestions(self, 
                                    partial_command: str,
                                    context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get intelligent command suggestions"""
        start_time = time.time()
        
        try:
            if not self.command_intelligence:
                return []
            
            # Get suggestions from command intelligence
            suggestions = await self.command_intelligence.get_completions(
                partial_command=partial_command,
                current_directory=context.get('current_directory', '/') if context else '/',
                recent_commands=context.get('recent_commands', []) if context else [],
                available_providers=context.get('available_providers', []) if context else [],
                workflow_phase=context.get('workflow_phase') if context else None,
                user_skill_level=context.get('user_skill_level', 'intermediate') if context else 'intermediate'
            )
            
            # Convert to dict format
            suggestions_data = []
            for suggestion in suggestions:
                suggestions_data.append({
                    'command': suggestion.command,
                    'confidence': suggestion.confidence,
                    'source': suggestion.source,
                    'description': suggestion.description,
                    'usage_count': suggestion.usage_count,
                    'success_rate': suggestion.success_rate
                })
            
            # Track performance
            response_time = (time.time() - start_time) * 1000
            self._track_request_performance(response_time)
            
            return suggestions_data
            
        except Exception as e:
            self.logger.error(f"Failed to get command suggestions: {e}")
            return []
    
    async def parse_natural_language(self,
                                   text: str,
                                   context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Parse natural language into command"""
        start_time = time.time()
        
        try:
            if not self.nlp_processor:
                return None
            
            translation = await self.nlp_processor.parse_natural_language(text, context)
            
            # Convert to dict format
            result = {
                'original_text': translation.original_text,
                'suggested_command': translation.suggested_command,
                'confidence': translation.confidence,
                'alternatives': translation.alternatives,
                'explanation': translation.explanation,
                'intent': {
                    'action': translation.parsed_intent.action,
                    'target': translation.parsed_intent.target,
                    'modifiers': translation.parsed_intent.modifiers,
                    'parameters': translation.parsed_intent.parameters
                }
            }
            
            # Track performance
            response_time = (time.time() - start_time) * 1000
            self._track_request_performance(response_time)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to parse natural language: {e}")
            return None
    
    async def get_personalized_workspace(self, 
                                       workspace_name: str = "default") -> Optional[Dict[str, Any]]:
        """Get or create personalized workspace configuration"""
        try:
            if not self.personalization_engine or not self.current_user_id:
                return None
            
            workspace = await self.personalization_engine.create_personalized_workspace(
                self.current_user_id, workspace_name
            )
            
            return {
                'config_id': workspace.config_id,
                'name': workspace.name,
                'description': workspace.description,
                'settings': workspace.settings,
                'shortcuts': workspace.shortcuts,
                'aliases': workspace.aliases,
                'default_providers': workspace.default_providers,
                'workflow_presets': workspace.workflow_presets,
                'ui_customizations': workspace.ui_customizations
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get personalized workspace: {e}")
            return None
    
    async def predict_workflow_performance(self,
                                         workflow_type: str,
                                         context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Predict workflow performance"""
        try:
            if not self.performance_predictor:
                return None
            
            from .performance_predictor import create_performance_context
            
            perf_context = create_performance_context(
                workflow_type=workflow_type,
                user_skill_level=context.get('user_skill_level', 'intermediate') if context else 'intermediate',
                system_load=context.get('system_load', 0.5) if context else 0.5,
                available_resources=context.get('available_resources', {}) if context else {},
                provider_status=context.get('provider_status', {}) if context else {},
                complexity_factors=context.get('complexity_factors', {}) if context else {}
            )
            
            prediction = await self.performance_predictor.predict_workflow_performance(
                workflow_type, perf_context
            )
            
            return {
                'workflow_id': prediction.workflow_id,
                'workflow_type': prediction.workflow_type,
                'overall_score': prediction.overall_score,
                'estimated_completion_time': prediction.estimated_completion_time,
                'risk_factors': prediction.risk_factors,
                'optimization_suggestions': prediction.optimization_suggestions,
                'predictions': {
                    metric_type.value: {
                        'predicted_value': pred.predicted_value,
                        'confidence': pred.confidence,
                        'confidence_interval': pred.confidence_interval,
                        'factors': pred.factors,
                        'recommendations': pred.recommendations
                    }
                    for metric_type, pred in prediction.predictions.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to predict workflow performance: {e}")
            return None
    
    async def apply_adaptive_interface(self) -> List[Dict[str, Any]]:
        """Apply adaptive interface changes"""
        try:
            if not self.adaptive_interface or not self.current_user_id:
                return []
            
            adaptations = await self.adaptive_interface.analyze_and_adapt()
            
            return [
                {
                    'type': adaptation.get('type'),
                    'confidence': adaptation.get('confidence'),
                    'source': adaptation.get('source'),
                    'reason': adaptation.get('reason'),
                    'action': adaptation.get('action')
                }
                for adaptation in adaptations
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to apply adaptive interface: {e}")
            return []
    
    async def track_user_interaction(self,
                                   interaction_type: str,
                                   context: Dict[str, Any]):
        """Track user interaction for learning"""
        try:
            if not self.behavior_tracker:
                return
            
            self.behavior_tracker.track_interaction(
                interaction_type=interaction_type,
                command=context.get('command'),
                context=context,
                response_time=context.get('response_time', 0.0),
                success=context.get('success', True),
                error_message=context.get('error_message'),
                ui_state=context.get('ui_state')
            )
            
        except Exception as e:
            self.logger.error(f"Failed to track user interaction: {e}")
    
    # Background service methods
    
    async def _performance_monitoring_loop(self):
        """Monitor system performance continuously"""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                await self._update_system_status()
                
                # Check for performance violations
                if self.system_status.avg_response_time_ms > 16.0:
                    self.performance_metrics['fps_violations'] += 1
                    self.logger.warning(f"Performance violation: {self.system_status.avg_response_time_ms:.1f}ms")
                
                # Check memory usage
                if self.system_status.total_memory_usage_mb > self.config.memory_limit_mb:
                    self.logger.warning(f"Memory usage high: {self.system_status.total_memory_usage_mb:.1f}MB")
                    await self._trigger_memory_cleanup()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")
    
    async def _intelligence_update_loop(self):
        """Periodically update intelligence components"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Update adaptive interface if user is active
                if (self.adaptive_interface and 
                    self.behavior_tracker and 
                    self.behavior_tracker.current_session):
                    
                    recent_interactions = len(self.behavior_tracker.current_session.interactions)
                    if recent_interactions > 0:
                        await self.adaptive_interface.analyze_and_adapt()
                
                # Update personalization
                if self.personalization_engine and self.current_user_id:
                    await self.personalization_engine.analyze_user_patterns(self.current_user_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Intelligence update error: {e}")
    
    async def _memory_management_loop(self):
        """Manage memory usage of intelligence components"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                
                # Clear caches in components
                if self.command_intelligence:
                    # Clear old cache entries
                    current_time = time.time()
                    cache = self.command_intelligence.engine.cache
                    old_keys = [
                        key for key, (_, timestamp) in cache.items()
                        if current_time - timestamp > 300  # 5 minutes old
                    ]
                    for key in old_keys:
                        del cache[key]
                
                if self.nlp_processor:
                    # Clear old NLP cache
                    current_time = time.time()
                    cache = self.nlp_processor.translation_cache
                    old_keys = [
                        key for key, (_, timestamp) in cache.items()
                        if current_time - timestamp > 300
                    ]
                    for key in old_keys:
                        del cache[key]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Memory management error: {e}")
    
    async def _update_system_status(self):
        """Update system status metrics"""
        try:
            # Calculate memory usage
            total_memory = 0.0
            
            if self.model_manager:
                model_metrics = self.model_manager.get_performance_summary()
                total_memory += model_metrics.get('total_memory_usage', 0)
            
            self.system_status.total_memory_usage_mb = total_memory
            
            # Calculate average response time
            if hasattr(self, '_recent_response_times'):
                self.system_status.avg_response_time_ms = (
                    sum(self._recent_response_times) / len(self._recent_response_times)
                    if self._recent_response_times else 0
                )
            
            # Check FPS compliance
            self.system_status.fps_compliant = self.system_status.avg_response_time_ms <= 16.0
            
        except Exception as e:
            self.logger.error(f"Failed to update system status: {e}")
    
    def _track_request_performance(self, response_time_ms: float):
        """Track performance of individual requests"""
        self.performance_metrics['requests_processed'] += 1
        
        # Keep recent response times for averaging
        if not hasattr(self, '_recent_response_times'):
            self._recent_response_times = []
        
        self._recent_response_times.append(response_time_ms)
        
        # Keep only recent measurements
        if len(self._recent_response_times) > 100:
            self._recent_response_times = self._recent_response_times[-100:]
        
        # Update average
        self.performance_metrics['avg_response_time'] = (
            sum(self._recent_response_times) / len(self._recent_response_times)
        )
    
    async def _trigger_memory_cleanup(self):
        """Trigger memory cleanup across components"""
        try:
            # Force garbage collection in ML models
            if self.model_manager:
                for model_id in self.model_manager.models:
                    # Trigger model optimization
                    await self.model_manager.optimize_model(model_id)
            
            # Clear behavior tracker buffer
            if self.behavior_tracker:
                # Reduce buffer size temporarily
                self.behavior_tracker.interaction_buffer.maxlen = 500
                
            self.logger.info("Memory cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Memory cleanup failed: {e}")
    
    async def _handle_coordination_event(self, event: Dict[str, Any]):
        """Handle coordination MCP events"""
        try:
            if event.get('type') == 'user_interaction' and self.behavior_tracker:
                # Track interaction from coordination system
                self.behavior_tracker.track_interaction(
                    interaction_type=event.get('interaction_type', 'unknown'),
                    context=event.get('context', {})
                )
                
        except Exception as e:
            self.logger.error(f"Failed to handle coordination event: {e}")
    
    async def _handle_workflow_state_change(self, state_change: Dict[str, Any]):
        """Handle workflow state change events"""
        try:
            if self.performance_predictor and state_change.get('type') == 'workflow_completed':
                # Record actual performance for learning
                workflow_id = state_change.get('workflow_id')
                metrics = state_change.get('performance_metrics', {})
                
                if workflow_id and metrics:
                    from .performance_predictor import MetricType
                    
                    # Convert metrics to MetricType format
                    metric_dict = {}
                    for key, value in metrics.items():
                        try:
                            metric_type = MetricType(key)
                            metric_dict[metric_type] = value
                        except ValueError:
                            continue
                    
                    await self.performance_predictor.record_actual_performance(
                        workflow_id, metric_dict
                    )
                
        except Exception as e:
            self.logger.error(f"Failed to handle workflow state change: {e}")
    
    # Utility methods
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'behavior_tracker_active': self.system_status.behavior_tracker_active,
            'ml_models_loaded': self.system_status.ml_models_loaded,
            'adaptive_interface_active': self.system_status.adaptive_interface_active,
            'command_intelligence_active': self.system_status.command_intelligence_active,
            'nlp_processor_active': self.system_status.nlp_processor_active,
            'personalization_active': self.system_status.personalization_active,
            'performance_predictor_active': self.system_status.performance_predictor_active,
            'mcp_integration_active': self.system_status.mcp_integration_active,
            'total_memory_usage_mb': self.system_status.total_memory_usage_mb,
            'avg_response_time_ms': self.system_status.avg_response_time_ms,
            'fps_compliant': self.system_status.fps_compliant,
            'current_user_id': self.current_user_id,
            'requests_processed': self.performance_metrics['requests_processed'],
            'fps_violations': self.performance_metrics['fps_violations']
        }
    
    async def shutdown(self):
        """Shutdown intelligence system gracefully"""
        try:
            self.logger.info("Shutting down intelligence system...")
            
            # Cancel background tasks
            for task in self.integration_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # End behavior tracking session
            if self.behavior_tracker:
                self.behavior_tracker.end_session()
            
            # Save component states
            if self.command_intelligence:
                await self.command_intelligence.engine.save_command_knowledge()
            
            if self.personalization_engine:
                await self.personalization_engine._save_user_profiles()
            
            if self.performance_predictor:
                await self.performance_predictor._save_performance_history()
            
            self.logger.info("Intelligence system shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


# Convenience functions

def create_intelligence_config(**kwargs) -> IntelligenceConfig:
    """Create intelligence configuration with custom settings"""
    return IntelligenceConfig(**kwargs)

async def create_intelligence_manager(
    config: Optional[IntelligenceConfig] = None,
    config_dir: Optional[Path] = None,
    user_identifier: Optional[str] = None
) -> IntelligenceIntegrationManager:
    """Create and initialize intelligence integration manager"""
    
    if config is None:
        config = IntelligenceConfig()
    
    manager = IntelligenceIntegrationManager(config, config_dir)
    
    success = await manager.initialize(user_identifier)
    if not success:
        logging.warning("Intelligence manager initialized with limited functionality")
    
    return manager