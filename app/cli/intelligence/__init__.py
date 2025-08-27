"""
AI-Powered Intelligent UI Adaptations
=====================================

This module provides cutting-edge adaptive interfaces that learn from user behavior
to create personalized, efficient CLI experiences. Features include:

- TensorFlow.js-powered behavior analysis and prediction
- Adaptive interface layouts based on usage patterns  
- Intelligent command completion and suggestions
- Natural language command parsing
- Contextual help that adapts to user skill level
- Personalized workspace configurations
- Performance prediction and optimization
- Real-time learning with 60+ FPS requirements

Architecture:
- behavior_tracker: User interaction monitoring and data collection
- ml_models: TensorFlow.js models for prediction and adaptation  
- adaptive_interface: Dynamic UI modification system
- command_intelligence: Smart completion and suggestions
- nlp_processor: Natural language understanding
- personalization: User-specific customizations
- performance_predictor: Workflow optimization models
"""

from .behavior_tracker import BehaviorTracker, UserBehaviorAnalyzer
from .ml_models import TensorFlowJSModelManager, AdaptiveUIModel
from .adaptive_interface import AdaptiveInterfaceManager
from .command_intelligence import IntelligentCommandProcessor
from .nlp_processor import NaturalLanguageProcessor
from .personalization import PersonalizationEngine
from .performance_predictor import PerformancePredictionModel

__all__ = [
    'BehaviorTracker',
    'UserBehaviorAnalyzer', 
    'TensorFlowJSModelManager',
    'AdaptiveUIModel',
    'AdaptiveInterfaceManager',
    'IntelligentCommandProcessor',
    'NaturalLanguageProcessor',
    'PersonalizationEngine',
    'PerformancePredictionModel',
]