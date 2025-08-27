"""
Performance Prediction Models for Workflow Optimization
=======================================================

Uses machine learning to predict workflow performance, execution times,
resource usage, and success rates to optimize user experience.
"""

import asyncio
import time
import logging
import statistics
from typing import Dict, Any, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
import json
import math

# Import behavior tracking and ML models
from .behavior_tracker import BehaviorTracker, UserInteraction
from .ml_models import TensorFlowJSModelManager, AdaptiveUIModel, TrainingData

class MetricType(Enum):
    """Types of performance metrics to predict"""
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    RESOURCE_USAGE = "resource_usage"
    USER_SATISFACTION = "user_satisfaction"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"

@dataclass
class PerformancePrediction:
    """Prediction result for a specific metric"""
    metric_type: MetricType
    predicted_value: float
    confidence: float
    confidence_interval: Tuple[float, float]
    factors: List[str] = field(default_factory=list)  # Contributing factors
    recommendations: List[str] = field(default_factory=list)
    historical_average: Optional[float] = None
    improvement_potential: float = 0.0  # % improvement possible

@dataclass
class WorkflowPrediction:
    """Complete prediction for a workflow execution"""
    workflow_id: str
    workflow_type: str
    predictions: Dict[MetricType, PerformancePrediction] = field(default_factory=dict)
    overall_score: float = 0.0  # 0-1 overall predicted performance
    risk_factors: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    estimated_completion_time: float = 0.0
    predicted_at: float = field(default_factory=time.time)

@dataclass
class PerformanceContext:
    """Context information for performance prediction"""
    workflow_type: str
    user_skill_level: str = 'intermediate'
    system_load: float = 0.5  # 0-1 scale
    available_resources: Dict[str, float] = field(default_factory=dict)
    time_of_day: int = 12
    recent_performance: List[float] = field(default_factory=list)
    provider_status: Dict[str, bool] = field(default_factory=dict)
    complexity_factors: Dict[str, Any] = field(default_factory=dict)

class PerformanceHistoryTracker:
    """Tracks historical performance data for learning"""
    
    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self.execution_history: deque = deque(maxlen=max_history_size)
        self.performance_baselines: Dict[str, Dict[MetricType, float]] = defaultdict(dict)
        
    def record_execution(self, workflow_type: str, metrics: Dict[MetricType, float], 
                        context: PerformanceContext):
        """Record actual execution performance"""
        record = {
            'timestamp': time.time(),
            'workflow_type': workflow_type,
            'metrics': {metric.value: value for metric, value in metrics.items()},
            'context': {
                'user_skill_level': context.user_skill_level,
                'system_load': context.system_load,
                'time_of_day': context.time_of_day,
                'complexity_factors': context.complexity_factors
            }
        }
        
        self.execution_history.append(record)
        self._update_baselines(workflow_type, metrics)
    
    def _update_baselines(self, workflow_type: str, metrics: Dict[MetricType, float]):
        """Update performance baselines"""
        for metric_type, value in metrics.items():
            current_values = [
                record['metrics'].get(metric_type.value, 0)
                for record in self.execution_history
                if record['workflow_type'] == workflow_type
            ]
            
            if current_values:
                self.performance_baselines[workflow_type][metric_type] = statistics.mean(current_values)
    
    def get_baseline(self, workflow_type: str, metric_type: MetricType) -> Optional[float]:
        """Get performance baseline for workflow and metric"""
        return self.performance_baselines.get(workflow_type, {}).get(metric_type)
    
    def get_recent_performance(self, workflow_type: str, metric_type: MetricType, 
                             hours: int = 24) -> List[float]:
        """Get recent performance data"""
        cutoff_time = time.time() - (hours * 3600)
        
        return [
            record['metrics'].get(metric_type.value, 0)
            for record in self.execution_history
            if (record['timestamp'] > cutoff_time and 
                record['workflow_type'] == workflow_type and
                metric_type.value in record['metrics'])
        ]

class PerformancePredictionModel:
    """
    Core performance prediction engine using ML and statistical models
    """
    
    def __init__(self,
                 behavior_tracker: BehaviorTracker,
                 model_manager: Optional[TensorFlowJSModelManager] = None,
                 config_dir: Optional[Path] = None):
        
        self.behavior_tracker = behavior_tracker
        self.model_manager = model_manager
        self.config_dir = config_dir or Path.home() / ".localagent"
        
        self.logger = logging.getLogger("PerformancePredictionModel")
        
        # Performance tracking
        self.history_tracker = PerformanceHistoryTracker()
        
        # ML models for different metrics
        self.prediction_models: Dict[MetricType, Optional[AdaptiveUIModel]] = {
            metric: None for metric in MetricType
        }
        
        # Statistical models (fallback when ML isn't available)
        self.statistical_models: Dict[str, Dict[MetricType, Any]] = defaultdict(dict)
        
        # Performance tracking
        self.prediction_times = deque(maxlen=1000)
        self.accuracy_tracking = defaultdict(list)
        
        # Initialize system
        asyncio.create_task(self._initialize_prediction_system())
    
    async def _initialize_prediction_system(self):
        """Initialize the performance prediction system"""
        try:
            # Load historical performance data
            await self._load_performance_history()
            
            # Initialize ML models if available
            if self.model_manager:
                await self._initialize_ml_models()
            
            # Build statistical models
            await self._build_statistical_models()
            
            # Start background learning
            asyncio.create_task(self._continuous_learning_loop())
            
            self.logger.info("Performance prediction system initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize prediction system: {e}")
    
    async def predict_workflow_performance(self, 
                                         workflow_type: str,
                                         context: PerformanceContext) -> WorkflowPrediction:
        """Predict performance for a workflow execution"""
        start_time = time.time()
        
        try:
            workflow_id = f"{workflow_type}_{int(time.time())}"
            prediction = WorkflowPrediction(
                workflow_id=workflow_id,
                workflow_type=workflow_type
            )
            
            # Predict each metric type
            for metric_type in MetricType:
                metric_prediction = await self._predict_metric(
                    workflow_type, metric_type, context
                )
                prediction.predictions[metric_type] = metric_prediction
            
            # Calculate overall score
            prediction.overall_score = self._calculate_overall_score(prediction.predictions)
            
            # Identify risk factors
            prediction.risk_factors = self._identify_risk_factors(prediction.predictions, context)
            
            # Generate optimization suggestions
            prediction.optimization_suggestions = self._generate_optimization_suggestions(
                prediction.predictions, context
            )
            
            # Estimate completion time
            if MetricType.EXECUTION_TIME in prediction.predictions:
                prediction.estimated_completion_time = prediction.predictions[MetricType.EXECUTION_TIME].predicted_value
            
            # Track prediction performance
            prediction_time = (time.time() - start_time) * 1000
            self.prediction_times.append(prediction_time)
            
            if prediction_time > 16.0:  # Must maintain 60+ FPS
                self.logger.warning(f"Performance prediction took {prediction_time:.1f}ms")
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Failed to predict workflow performance: {e}")
            # Return fallback prediction
            return WorkflowPrediction(
                workflow_id=f"{workflow_type}_fallback",
                workflow_type=workflow_type,
                overall_score=0.5,
                estimated_completion_time=300.0  # 5 minutes default
            )
    
    async def _predict_metric(self,
                            workflow_type: str,
                            metric_type: MetricType,
                            context: PerformanceContext) -> PerformancePrediction:
        """Predict a specific performance metric"""
        
        try:
            # Try ML model first if available
            if (self.model_manager and 
                metric_type in self.prediction_models and 
                self.prediction_models[metric_type]):
                
                ml_prediction = await self._predict_with_ml_model(
                    workflow_type, metric_type, context
                )
                if ml_prediction:
                    return ml_prediction
            
            # Fall back to statistical model
            return await self._predict_with_statistical_model(
                workflow_type, metric_type, context
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to predict {metric_type}: {e}")
            return self._create_fallback_prediction(metric_type)
    
    async def _predict_with_ml_model(self,
                                   workflow_type: str,
                                   metric_type: MetricType,
                                   context: PerformanceContext) -> Optional[PerformancePrediction]:
        """Predict using ML model"""
        try:
            model = self.prediction_models[metric_type]
            if not model:
                return None
            
            # Extract features
            features = self._extract_prediction_features(workflow_type, context)
            
            # Get prediction
            model_id = f"performance_{metric_type.value}"
            prediction_result = await self.model_manager.predict(model_id, features, timeout_ms=5)
            
            if not prediction_result:
                return None
            
            predicted_value = prediction_result[0] if prediction_result else 0.0
            confidence = prediction_result[1] if len(prediction_result) > 1 else 0.7
            
            # Calculate confidence interval
            historical_std = self._get_historical_std(workflow_type, metric_type)
            margin = 1.96 * historical_std * (1.0 - confidence)  # 95% CI
            confidence_interval = (
                max(0, predicted_value - margin),
                predicted_value + margin
            )
            
            return PerformancePrediction(
                metric_type=metric_type,
                predicted_value=predicted_value,
                confidence=confidence,
                confidence_interval=confidence_interval,
                factors=['ml_model', 'historical_data'],
                historical_average=self.history_tracker.get_baseline(workflow_type, metric_type)
            )
            
        except Exception as e:
            self.logger.warning(f"ML prediction failed for {metric_type}: {e}")
            return None
    
    async def _predict_with_statistical_model(self,
                                            workflow_type: str,
                                            metric_type: MetricType,
                                            context: PerformanceContext) -> PerformancePrediction:
        """Predict using statistical model"""
        
        # Get historical data
        recent_values = self.history_tracker.get_recent_performance(
            workflow_type, metric_type, hours=168  # Last week
        )
        
        if not recent_values:
            # No historical data, use defaults
            return self._create_default_prediction(metric_type, workflow_type)
        
        # Calculate base prediction
        base_value = statistics.mean(recent_values)
        std_dev = statistics.stdev(recent_values) if len(recent_values) > 1 else base_value * 0.1
        
        # Apply context adjustments
        adjusted_value = self._apply_context_adjustments(
            base_value, metric_type, context, workflow_type
        )
        
        # Calculate confidence based on data consistency
        confidence = self._calculate_statistical_confidence(recent_values)
        
        # Confidence interval
        margin = 1.96 * std_dev
        confidence_interval = (
            max(0, adjusted_value - margin),
            adjusted_value + margin
        )
        
        # Identify contributing factors
        factors = self._identify_contributing_factors(context, workflow_type)
        
        return PerformancePrediction(
            metric_type=metric_type,
            predicted_value=adjusted_value,
            confidence=confidence,
            confidence_interval=confidence_interval,
            factors=factors,
            historical_average=base_value,
            improvement_potential=self._calculate_improvement_potential(
                adjusted_value, base_value, recent_values
            )
        )
    
    def _apply_context_adjustments(self,
                                 base_value: float,
                                 metric_type: MetricType,
                                 context: PerformanceContext,
                                 workflow_type: str) -> float:
        """Apply context-based adjustments to predictions"""
        
        adjusted_value = base_value
        
        # Skill level adjustments
        if context.user_skill_level == 'expert':
            if metric_type == MetricType.EXECUTION_TIME:
                adjusted_value *= 0.8  # Experts are faster
            elif metric_type == MetricType.SUCCESS_RATE:
                adjusted_value *= 1.1  # Higher success rate
        elif context.user_skill_level == 'beginner':
            if metric_type == MetricType.EXECUTION_TIME:
                adjusted_value *= 1.3  # Beginners are slower
            elif metric_type == MetricType.ERROR_RATE:
                adjusted_value *= 1.2  # Higher error rate
        
        # System load adjustments
        if context.system_load > 0.8:
            if metric_type == MetricType.EXECUTION_TIME:
                adjusted_value *= (1.0 + context.system_load * 0.5)
            elif metric_type == MetricType.SUCCESS_RATE:
                adjusted_value *= 0.95
        
        # Time of day adjustments (assuming peak hours affect performance)
        if 9 <= context.time_of_day <= 17:  # Business hours
            if metric_type == MetricType.RESOURCE_USAGE:
                adjusted_value *= 1.1  # Higher resource contention
        
        # Provider status adjustments
        active_providers = sum(1 for status in context.provider_status.values() if status)
        total_providers = len(context.provider_status)
        
        if total_providers > 0:
            provider_availability = active_providers / total_providers
            if provider_availability < 0.5:
                if metric_type == MetricType.SUCCESS_RATE:
                    adjusted_value *= 0.8
                elif metric_type == MetricType.EXECUTION_TIME:
                    adjusted_value *= 1.2
        
        # Complexity factor adjustments
        complexity_multiplier = 1.0
        for factor, value in context.complexity_factors.items():
            if isinstance(value, (int, float)) and value > 1:
                complexity_multiplier += (value - 1) * 0.1
        
        if metric_type == MetricType.EXECUTION_TIME:
            adjusted_value *= complexity_multiplier
        elif metric_type == MetricType.SUCCESS_RATE:
            adjusted_value /= complexity_multiplier
        
        return max(0.0, adjusted_value)
    
    def _calculate_statistical_confidence(self, values: List[float]) -> float:
        """Calculate confidence based on data consistency"""
        if len(values) < 2:
            return 0.5  # Low confidence with little data
        
        mean_val = statistics.mean(values)
        std_dev = statistics.stdev(values)
        
        # Coefficient of variation (lower is more consistent)
        cv = std_dev / mean_val if mean_val > 0 else 1.0
        
        # Convert to confidence (0-1)
        confidence = 1.0 / (1.0 + cv)
        
        # Adjust for sample size
        size_factor = min(1.0, len(values) / 20.0)  # Full confidence with 20+ samples
        
        return confidence * size_factor
    
    def _identify_contributing_factors(self, context: PerformanceContext, 
                                     workflow_type: str) -> List[str]:
        """Identify factors contributing to the prediction"""
        factors = ['historical_performance']
        
        if context.user_skill_level != 'intermediate':
            factors.append(f'user_skill_{context.user_skill_level}')
        
        if context.system_load > 0.7:
            factors.append('high_system_load')
        
        if context.complexity_factors:
            factors.append('complexity_factors')
        
        if any(not status for status in context.provider_status.values()):
            factors.append('provider_availability')
        
        if context.recent_performance:
            factors.append('recent_performance_trend')
        
        return factors
    
    def _calculate_improvement_potential(self, predicted: float, baseline: float, 
                                       recent_values: List[float]) -> float:
        """Calculate potential for performance improvement"""
        if not recent_values or baseline == 0:
            return 0.0
        
        # Find best recent performance
        best_recent = max(recent_values) if recent_values else baseline
        
        # Calculate improvement potential as % of difference from best
        if predicted < best_recent:
            return ((best_recent - predicted) / best_recent) * 100
        
        return 0.0
    
    def _calculate_overall_score(self, predictions: Dict[MetricType, PerformancePrediction]) -> float:
        """Calculate overall performance score"""
        if not predictions:
            return 0.5
        
        scores = []
        weights = {
            MetricType.SUCCESS_RATE: 0.3,
            MetricType.EXECUTION_TIME: 0.25,
            MetricType.ERROR_RATE: 0.2,
            MetricType.USER_SATISFACTION: 0.15,
            MetricType.RESOURCE_USAGE: 0.1,
            MetricType.THROUGHPUT: 0.1
        }
        
        total_weight = 0.0
        
        for metric_type, prediction in predictions.items():
            weight = weights.get(metric_type, 0.1)
            total_weight += weight
            
            # Normalize different metrics to 0-1 scale
            normalized_score = self._normalize_metric_score(metric_type, prediction.predicted_value)
            
            # Weight by confidence
            weighted_score = normalized_score * prediction.confidence * weight
            scores.append(weighted_score)
        
        return sum(scores) / total_weight if total_weight > 0 else 0.5
    
    def _normalize_metric_score(self, metric_type: MetricType, value: float) -> float:
        """Normalize metric value to 0-1 scale for scoring"""
        
        if metric_type == MetricType.SUCCESS_RATE:
            return min(1.0, max(0.0, value))  # Already 0-1
        elif metric_type == MetricType.ERROR_RATE:
            return max(0.0, 1.0 - min(1.0, value))  # Invert (lower is better)
        elif metric_type == MetricType.EXECUTION_TIME:
            # Normalize based on reasonable time ranges (0-3600 seconds)
            return max(0.0, 1.0 - min(1.0, value / 3600.0))
        elif metric_type == MetricType.RESOURCE_USAGE:
            # Normalize based on 0-100% usage
            return max(0.0, 1.0 - min(1.0, value / 100.0))
        elif metric_type == MetricType.USER_SATISFACTION:
            return min(1.0, max(0.0, value))  # Assume 0-1 scale
        elif metric_type == MetricType.THROUGHPUT:
            # Normalize throughput (higher is better, cap at reasonable maximum)
            return min(1.0, value / 1000.0)
        
        return 0.5  # Default middle score
    
    def _identify_risk_factors(self, predictions: Dict[MetricType, PerformancePrediction],
                             context: PerformanceContext) -> List[str]:
        """Identify potential risk factors"""
        risks = []
        
        # Low success rate prediction
        if MetricType.SUCCESS_RATE in predictions:
            success_pred = predictions[MetricType.SUCCESS_RATE]
            if success_pred.predicted_value < 0.7:
                risks.append(f"Low predicted success rate: {success_pred.predicted_value:.1%}")
        
        # High execution time
        if MetricType.EXECUTION_TIME in predictions:
            time_pred = predictions[MetricType.EXECUTION_TIME]
            if time_pred.predicted_value > 1800:  # 30 minutes
                risks.append(f"Long predicted execution time: {time_pred.predicted_value/60:.1f} minutes")
        
        # High error rate
        if MetricType.ERROR_RATE in predictions:
            error_pred = predictions[MetricType.ERROR_RATE]
            if error_pred.predicted_value > 0.1:
                risks.append(f"High predicted error rate: {error_pred.predicted_value:.1%}")
        
        # High resource usage
        if MetricType.RESOURCE_USAGE in predictions:
            resource_pred = predictions[MetricType.RESOURCE_USAGE]
            if resource_pred.predicted_value > 80:
                risks.append(f"High predicted resource usage: {resource_pred.predicted_value:.1f}%")
        
        # Context-based risks
        if context.system_load > 0.8:
            risks.append("High current system load")
        
        if context.user_skill_level == 'beginner':
            risks.append("User inexperience may affect performance")
        
        # Provider availability risks
        unavailable_providers = [
            provider for provider, status in context.provider_status.items()
            if not status
        ]
        if unavailable_providers:
            risks.append(f"Unavailable providers: {', '.join(unavailable_providers)}")
        
        return risks
    
    def _generate_optimization_suggestions(self, 
                                         predictions: Dict[MetricType, PerformancePrediction],
                                         context: PerformanceContext) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []
        
        # Success rate optimizations
        if MetricType.SUCCESS_RATE in predictions:
            success_pred = predictions[MetricType.SUCCESS_RATE]
            if success_pred.predicted_value < 0.8:
                suggestions.append("Consider running in interactive mode for better success rate")
                if context.user_skill_level == 'beginner':
                    suggestions.append("Enable guided mode for step-by-step assistance")
        
        # Execution time optimizations
        if MetricType.EXECUTION_TIME in predictions:
            time_pred = predictions[MetricType.EXECUTION_TIME]
            if time_pred.predicted_value > 600:  # 10 minutes
                suggestions.append("Consider running workflow in parallel execution mode")
                suggestions.append("Enable background execution to avoid blocking other tasks")
        
        # Resource usage optimizations
        if MetricType.RESOURCE_USAGE in predictions:
            resource_pred = predictions[MetricType.RESOURCE_USAGE]
            if resource_pred.predicted_value > 70:
                suggestions.append("Schedule workflow during off-peak hours")
                suggestions.append("Enable resource-efficient mode")
        
        # Context-based suggestions
        if context.system_load > 0.7:
            suggestions.append("Wait for lower system load before executing")
        
        if context.user_skill_level == 'expert':
            suggestions.append("Enable advanced optimization features")
        
        # Provider-based suggestions
        active_providers = [p for p, status in context.provider_status.items() if status]
        if len(active_providers) > 1:
            suggestions.append("Use provider load balancing for better performance")
        
        return suggestions
    
    def _create_fallback_prediction(self, metric_type: MetricType) -> PerformancePrediction:
        """Create fallback prediction when other methods fail"""
        default_values = {
            MetricType.EXECUTION_TIME: 300.0,  # 5 minutes
            MetricType.SUCCESS_RATE: 0.8,     # 80%
            MetricType.ERROR_RATE: 0.1,       # 10%
            MetricType.RESOURCE_USAGE: 50.0,  # 50%
            MetricType.USER_SATISFACTION: 0.7, # 70%
            MetricType.THROUGHPUT: 10.0       # 10 operations/sec
        }
        
        predicted_value = default_values.get(metric_type, 0.5)
        
        return PerformancePrediction(
            metric_type=metric_type,
            predicted_value=predicted_value,
            confidence=0.3,  # Low confidence for fallback
            confidence_interval=(predicted_value * 0.7, predicted_value * 1.3),
            factors=['fallback_default'],
            recommendations=['Collect more performance data for better predictions']
        )
    
    def _create_default_prediction(self, metric_type: MetricType, 
                                 workflow_type: str) -> PerformancePrediction:
        """Create default prediction for new workflow types"""
        # Workflow-specific defaults
        workflow_defaults = {
            'research': {
                MetricType.EXECUTION_TIME: 600.0,    # 10 minutes
                MetricType.SUCCESS_RATE: 0.85,
                MetricType.RESOURCE_USAGE: 40.0
            },
            'development': {
                MetricType.EXECUTION_TIME: 1800.0,   # 30 minutes
                MetricType.SUCCESS_RATE: 0.75,
                MetricType.RESOURCE_USAGE: 60.0
            },
            'testing': {
                MetricType.EXECUTION_TIME: 300.0,    # 5 minutes
                MetricType.SUCCESS_RATE: 0.9,
                MetricType.RESOURCE_USAGE: 30.0
            }
        }
        
        defaults = workflow_defaults.get(workflow_type, {})
        predicted_value = defaults.get(metric_type, self._create_fallback_prediction(metric_type).predicted_value)
        
        return PerformancePrediction(
            metric_type=metric_type,
            predicted_value=predicted_value,
            confidence=0.5,
            confidence_interval=(predicted_value * 0.8, predicted_value * 1.2),
            factors=['workflow_defaults'],
            recommendations=['Execute similar workflows to improve prediction accuracy']
        )
    
    def _extract_prediction_features(self, workflow_type: str, 
                                   context: PerformanceContext) -> List[float]:
        """Extract features for ML model prediction"""
        features = []
        
        # Workflow type encoding (one-hot style)
        workflow_types = ['research', 'development', 'testing', 'deployment', 'analysis']
        for wf_type in workflow_types:
            features.append(1.0 if workflow_type == wf_type else 0.0)
        
        # User skill level encoding
        skill_levels = {'beginner': 0.0, 'intermediate': 0.5, 'expert': 1.0}
        features.append(skill_levels.get(context.user_skill_level, 0.5))
        
        # System context
        features.extend([
            context.system_load,
            context.time_of_day / 24.0,  # Normalize hour
            len(context.recent_performance) / 10.0,  # Normalize count
        ])
        
        # Recent performance features (if available)
        if context.recent_performance:
            features.extend([
                max(context.recent_performance),
                min(context.recent_performance),
                sum(context.recent_performance) / len(context.recent_performance)
            ])
        else:
            features.extend([0.0, 0.0, 0.0])
        
        # Provider availability
        available_count = sum(1 for status in context.provider_status.values() if status)
        total_count = len(context.provider_status) or 1
        features.append(available_count / total_count)
        
        # Complexity factors
        complexity_score = 0.0
        for factor, value in context.complexity_factors.items():
            if isinstance(value, (int, float)):
                complexity_score += value
        features.append(min(1.0, complexity_score / 10.0))  # Normalize
        
        # Pad or trim to expected size (20 features)
        while len(features) < 20:
            features.append(0.0)
        
        return features[:20]
    
    def _get_historical_std(self, workflow_type: str, metric_type: MetricType) -> float:
        """Get historical standard deviation for metric"""
        recent_values = self.history_tracker.get_recent_performance(
            workflow_type, metric_type, hours=168
        )
        
        if len(recent_values) > 1:
            return statistics.stdev(recent_values)
        else:
            # Default standard deviation as percentage of mean
            baseline = self.history_tracker.get_baseline(workflow_type, metric_type)
            return (baseline * 0.2) if baseline else 1.0
    
    async def record_actual_performance(self, workflow_id: str, 
                                      actual_metrics: Dict[MetricType, float]):
        """Record actual performance for learning"""
        try:
            # This would be called after workflow execution
            # to improve future predictions
            
            # Find the original prediction
            # In a real implementation, you'd store predictions and match them
            
            # Update accuracy tracking
            for metric_type, actual_value in actual_metrics.items():
                self.accuracy_tracking[metric_type].append({
                    'timestamp': time.time(),
                    'actual': actual_value,
                    'workflow_id': workflow_id
                })
            
            self.logger.debug(f"Recorded performance for workflow {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to record actual performance: {e}")
    
    async def _initialize_ml_models(self):
        """Initialize ML models for different metrics"""
        try:
            # For each metric type, try to load or create an ML model
            for metric_type in [MetricType.EXECUTION_TIME, MetricType.SUCCESS_RATE]:
                model_id = f"performance_{metric_type.value}"
                
                # Try to load existing model
                model = await self.model_manager.load_model(model_id)
                
                if not model:
                    # Create new model
                    from .ml_models import ModelConfig
                    config = ModelConfig(
                        model_type='performance_prediction',
                        input_shape=(20,),  # 20 features
                        output_shape=(2,),  # prediction + confidence
                        learning_rate=0.001,
                        batch_size=32,
                        epochs=50
                    )
                    
                    model = await self.model_manager.create_model(model_id, config)
                
                self.prediction_models[metric_type] = model
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize ML models: {e}")
    
    async def _build_statistical_models(self):
        """Build statistical models from historical data"""
        try:
            # Group historical data by workflow type
            workflow_data = defaultdict(lambda: defaultdict(list))
            
            for record in self.history_tracker.execution_history:
                workflow_type = record['workflow_type']
                for metric_name, value in record['metrics'].items():
                    metric_type = MetricType(metric_name)
                    workflow_data[workflow_type][metric_type].append(value)
            
            # Build simple regression models for each workflow-metric combination
            for workflow_type, metrics in workflow_data.items():
                for metric_type, values in metrics.items():
                    if len(values) > 3:
                        # Simple statistical model (mean, std dev, trend)
                        self.statistical_models[workflow_type][metric_type] = {
                            'mean': statistics.mean(values),
                            'std': statistics.stdev(values) if len(values) > 1 else 0,
                            'trend': self._calculate_trend(values),
                            'sample_size': len(values)
                        }
            
            self.logger.info("Built statistical models from historical data")
            
        except Exception as e:
            self.logger.warning(f"Failed to build statistical models: {e}")
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend in values (simple linear regression slope)"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope using least squares
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x_squared = sum(x * x for x in x_values)
        
        denominator = n * sum_x_squared - sum_x * sum_x
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope
    
    async def _continuous_learning_loop(self):
        """Continuous learning from new performance data"""
        while True:
            try:
                await asyncio.sleep(1800)  # Every 30 minutes
                
                # Rebuild statistical models with new data
                await self._build_statistical_models()
                
                # Train ML models if enough new data
                if self.model_manager:
                    await self._train_ml_models_if_needed()
                
                # Save performance history
                await self._save_performance_history()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Continuous learning error: {e}")
    
    async def _train_ml_models_if_needed(self):
        """Train ML models if sufficient new data is available"""
        try:
            # Check if we have enough new training data
            recent_data_count = len([
                record for record in self.history_tracker.execution_history
                if time.time() - record['timestamp'] < 86400  # Last 24 hours
            ])
            
            if recent_data_count < 10:  # Not enough new data
                return
            
            # Prepare training data for each model
            for metric_type, model in self.prediction_models.items():
                if not model:
                    continue
                
                training_features, training_labels = self._prepare_training_data(metric_type)
                
                if len(training_features) > 20:  # Minimum training set
                    training_data = TrainingData(
                        features=training_features,
                        labels=training_labels
                    )
                    
                    model_id = f"performance_{metric_type.value}"
                    success = await self.model_manager.train_model(model_id, training_data)
                    
                    if success:
                        self.logger.info(f"Retrained model for {metric_type}")
                
        except Exception as e:
            self.logger.error(f"ML model training failed: {e}")
    
    def _prepare_training_data(self, metric_type: MetricType) -> Tuple[List[List[float]], List[float]]:
        """Prepare training data for ML model"""
        features = []
        labels = []
        
        for record in self.history_tracker.execution_history:
            if metric_type.value not in record['metrics']:
                continue
            
            # Create context from record
            context = PerformanceContext(
                workflow_type=record['workflow_type'],
                user_skill_level=record['context'].get('user_skill_level', 'intermediate'),
                system_load=record['context'].get('system_load', 0.5),
                time_of_day=record['context'].get('time_of_day', 12),
                complexity_factors=record['context'].get('complexity_factors', {})
            )
            
            # Extract features
            feature_vector = self._extract_prediction_features(record['workflow_type'], context)
            features.append(feature_vector)
            
            # Label is the actual metric value
            labels.append(record['metrics'][metric_type.value])
        
        return features, labels
    
    async def _load_performance_history(self):
        """Load performance history from storage"""
        history_file = self.config_dir / "performance_history.json"
        
        try:
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history_data = json.load(f)
                
                for record in history_data.get('execution_history', []):
                    self.history_tracker.execution_history.append(record)
                
                baselines = history_data.get('baselines', {})
                for workflow_type, metrics in baselines.items():
                    for metric_name, value in metrics.items():
                        metric_type = MetricType(metric_name)
                        self.history_tracker.performance_baselines[workflow_type][metric_type] = value
                
                self.logger.info(f"Loaded {len(self.history_tracker.execution_history)} historical records")
                
        except Exception as e:
            self.logger.warning(f"Failed to load performance history: {e}")
    
    async def _save_performance_history(self):
        """Save performance history to storage"""
        history_file = self.config_dir / "performance_history.json"
        
        try:
            history_data = {
                'execution_history': list(self.history_tracker.execution_history),
                'baselines': {
                    workflow_type: {
                        metric_type.value: value
                        for metric_type, value in metrics.items()
                    }
                    for workflow_type, metrics in self.history_tracker.performance_baselines.items()
                }
            }
            
            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            self.logger.debug("Performance history saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save performance history: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance prediction system metrics"""
        avg_prediction_time = sum(self.prediction_times) / len(self.prediction_times) \
                             if self.prediction_times else 0
        
        return {
            'avg_prediction_time_ms': avg_prediction_time,
            'fps_compliant': all(t <= 16.0 for t in self.prediction_times),
            'historical_records': len(self.history_tracker.execution_history),
            'workflow_baselines': len(self.history_tracker.performance_baselines),
            'ml_models_available': sum(1 for model in self.prediction_models.values() if model),
            'statistical_models': sum(len(metrics) for metrics in self.statistical_models.values()),
            'accuracy_tracking': {
                metric_type.value: len(records)
                for metric_type, records in self.accuracy_tracking.items()
            }
        }


# Convenience functions
def create_performance_predictor(
    behavior_tracker: BehaviorTracker,
    model_manager: Optional[TensorFlowJSModelManager] = None,
    config_dir: Optional[Path] = None
) -> PerformancePredictionModel:
    """Create performance prediction model with dependencies"""
    return PerformancePredictionModel(behavior_tracker, model_manager, config_dir)

def create_performance_context(
    workflow_type: str,
    user_skill_level: str = 'intermediate',
    system_load: float = 0.5,
    available_resources: Optional[Dict[str, float]] = None,
    provider_status: Optional[Dict[str, bool]] = None,
    complexity_factors: Optional[Dict[str, Any]] = None
) -> PerformanceContext:
    """Create performance context for predictions"""
    return PerformanceContext(
        workflow_type=workflow_type,
        user_skill_level=user_skill_level,
        system_load=system_load,
        available_resources=available_resources or {},
        time_of_day=time.localtime().tm_hour,
        provider_status=provider_status or {},
        complexity_factors=complexity_factors or {}
    )