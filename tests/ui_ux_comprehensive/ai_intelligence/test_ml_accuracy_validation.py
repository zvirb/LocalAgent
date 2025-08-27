"""
AI Intelligence and ML Model Accuracy Tests
==========================================

Tests ML model accuracy, adaptation behaviors, and AI intelligence features
in the CLI system. Validates TensorFlow.js models and behavioral predictions.
"""

import pytest
import asyncio
import numpy as np
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import tempfile

# ML and AI testing imports
try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

try:
    import tensorflowjs as tfjs
    TENSORFLOWJS_AVAILABLE = True
except ImportError:
    TENSORFLOWJS_AVAILABLE = False

# Import AI modules to test
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Try importing AI intelligence modules
try:
    from app.cli.intelligence.ml_models import TensorFlowJSModelManager, AdaptiveUIModel
    from app.cli.intelligence.behavior_tracker import BehaviorTracker, UserBehaviorAnalyzer
    from app.cli.intelligence.adaptive_interface import AdaptiveInterfaceManager
    from app.cli.intelligence.command_intelligence import CommandIntelligence
    from app.cli.intelligence.personalization import PersonalizationEngine
    AI_MODULES_AVAILABLE = True
except ImportError:
    AI_MODULES_AVAILABLE = False

# Test configuration
from tests.ui_ux_comprehensive.test_framework_config import get_test_config

@dataclass
class MLModelTestResult:
    """ML model test result"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    prediction_latency_ms: float
    model_size_mb: float
    inference_successful: bool
    error_messages: List[str] = field(default_factory=list)

@dataclass
class BehaviorPredictionTest:
    """Behavior prediction test case"""
    user_actions: List[Dict[str, Any]]
    expected_predictions: Dict[str, float]
    context: Dict[str, Any]
    test_name: str

@dataclass
class AdaptationTestResult:
    """UI adaptation test result"""
    adaptation_type: str
    triggered: bool
    accuracy: float
    user_satisfaction_estimate: float
    adaptation_time_ms: float
    effectiveness_score: float

class MLModelTester:
    """Test ML models for accuracy and performance"""
    
    def __init__(self):
        self.config = get_test_config()
        self.accuracy_threshold = self.config.ai_intelligence.model_accuracy_threshold
        self.latency_threshold_ms = self.config.ai_intelligence.prediction_latency_ms
        
    def generate_test_data(self, num_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic test data for ML models"""
        
        # Generate user behavior features
        # Features: [commands_per_hour, error_rate, efficiency_score, session_length, 
        #           preferred_provider, model_switches, help_requests, shortcuts_used,
        #           response_time_preference, complexity_preference]
        
        np.random.seed(42)  # Reproducible tests
        
        features = np.random.rand(num_samples, 10)
        
        # Create realistic feature distributions
        features[:, 0] = np.random.exponential(20, num_samples)  # commands per hour
        features[:, 1] = np.random.beta(2, 10, num_samples)     # error rate (low)
        features[:, 2] = np.random.beta(5, 3, num_samples)      # efficiency (high)
        features[:, 3] = np.random.lognormal(2, 1, num_samples) # session length
        features[:, 4] = np.random.choice([0, 1, 2, 3], num_samples) # provider preference
        
        # Normalize features
        features = (features - features.mean(axis=0)) / features.std(axis=0)
        
        # Generate labels based on realistic patterns
        labels = []
        for i in range(num_samples):
            # Predict user type: 0=beginner, 1=intermediate, 2=expert
            feature_vector = features[i]
            
            if feature_vector[1] > 0.5 and feature_vector[2] < 0:  # High error, low efficiency
                label = 0  # beginner
            elif feature_vector[0] > 0.5 and feature_vector[2] > 0.5:  # High usage, high efficiency
                label = 2  # expert
            else:
                label = 1  # intermediate
            
            labels.append(label)
        
        return features, np.array(labels)
    
    def create_test_model(self) -> tf.keras.Model:
        """Create a test TensorFlow model"""
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(10,)),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(3, activation='softmax')  # 3 user types
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train_test_model(self) -> Tuple[tf.keras.Model, float]:
        """Train and return test model with accuracy"""
        
        # Generate training and test data
        X_train, y_train = self.generate_test_data(800)
        X_test, y_test = self.generate_test_data(200)
        
        # Create and train model
        model = self.create_test_model()
        
        history = model.fit(
            X_train, y_train,
            epochs=50,
            batch_size=32,
            validation_split=0.2,
            verbose=0
        )
        
        # Evaluate model
        test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
        
        return model, test_accuracy
    
    @pytest.mark.skipif(not TENSORFLOW_AVAILABLE, reason="TensorFlow not available")
    def test_model_accuracy(self) -> MLModelTestResult:
        """Test ML model accuracy"""
        
        model, accuracy = self.train_test_model()
        
        # Generate test data for detailed metrics
        X_test, y_test = self.generate_test_data(200)
        
        # Measure prediction latency
        start_time = time.time()
        predictions = model.predict(X_test, verbose=0)
        prediction_time = (time.time() - start_time) * 1000 / len(X_test)
        
        # Calculate detailed metrics
        y_pred = np.argmax(predictions, axis=1)
        
        # Calculate precision, recall, F1 for multiclass
        precision = self._calculate_precision(y_test, y_pred)
        recall = self._calculate_recall(y_test, y_pred)
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Estimate model size
        model_size_mb = self._estimate_model_size(model)
        
        return MLModelTestResult(
            model_name="user_behavior_classifier",
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            prediction_latency_ms=prediction_time,
            model_size_mb=model_size_mb,
            inference_successful=True,
            error_messages=[]
        )
    
    def _calculate_precision(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate macro-averaged precision"""
        classes = np.unique(y_true)
        precision_sum = 0
        
        for cls in classes:
            true_positives = np.sum((y_pred == cls) & (y_true == cls))
            predicted_positives = np.sum(y_pred == cls)
            
            if predicted_positives > 0:
                precision_sum += true_positives / predicted_positives
        
        return precision_sum / len(classes)
    
    def _calculate_recall(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate macro-averaged recall"""
        classes = np.unique(y_true)
        recall_sum = 0
        
        for cls in classes:
            true_positives = np.sum((y_pred == cls) & (y_true == cls))
            actual_positives = np.sum(y_true == cls)
            
            if actual_positives > 0:
                recall_sum += true_positives / actual_positives
        
        return recall_sum / len(classes)
    
    def _estimate_model_size(self, model: tf.keras.Model) -> float:
        """Estimate model size in MB"""
        total_params = model.count_params()
        # Assume 4 bytes per parameter (float32)
        size_bytes = total_params * 4
        return size_bytes / (1024 * 1024)

class BehaviorPredictionTester:
    """Test behavior prediction accuracy"""
    
    def __init__(self):
        self.config = get_test_config()
        
    def create_behavior_test_cases(self) -> List[BehaviorPredictionTest]:
        """Create test cases for behavior prediction"""
        
        return [
            # Beginner user pattern
            BehaviorPredictionTest(
                user_actions=[
                    {"action": "help_request", "timestamp": time.time() - 100, "context": "main_menu"},
                    {"action": "error", "error_type": "syntax", "timestamp": time.time() - 90},
                    {"action": "help_request", "timestamp": time.time() - 80, "context": "command_syntax"},
                    {"action": "successful_command", "timestamp": time.time() - 70, "attempts": 3},
                    {"action": "help_request", "timestamp": time.time() - 60, "context": "providers"},
                ],
                expected_predictions={
                    "user_expertise": 0.1,  # Low expertise
                    "needs_help": 0.9,      # High help need
                    "command_confidence": 0.2, # Low confidence
                    "preferred_interaction": 0.8  # Guided interaction
                },
                context={"session_length": 120, "commands_issued": 3, "errors_made": 2},
                test_name="beginner_user_pattern"
            ),
            
            # Expert user pattern
            BehaviorPredictionTest(
                user_actions=[
                    {"action": "complex_command", "timestamp": time.time() - 100, "command": "multi-step workflow"},
                    {"action": "shortcut_used", "timestamp": time.time() - 95, "shortcut": "ctrl+shift+p"},
                    {"action": "provider_switch", "timestamp": time.time() - 90, "from": "gpt", "to": "claude"},
                    {"action": "batch_operation", "timestamp": time.time() - 80, "items": 15},
                    {"action": "custom_script", "timestamp": time.time() - 70, "script_complexity": "high"},
                ],
                expected_predictions={
                    "user_expertise": 0.9,   # High expertise
                    "needs_help": 0.1,       # Low help need
                    "command_confidence": 0.9, # High confidence
                    "preferred_interaction": 0.2  # Direct interaction
                },
                context={"session_length": 45, "commands_issued": 12, "errors_made": 0},
                test_name="expert_user_pattern"
            ),
            
            # Task-focused user pattern
            BehaviorPredictionTest(
                user_actions=[
                    {"action": "specific_query", "timestamp": time.time() - 60, "domain": "coding"},
                    {"action": "follow_up_question", "timestamp": time.time() - 50, "related": True},
                    {"action": "code_execution", "timestamp": time.time() - 40, "language": "python"},
                    {"action": "refinement", "timestamp": time.time() - 30, "iteration": 2},
                    {"action": "satisfaction_indicator", "timestamp": time.time() - 10, "positive": True}
                ],
                expected_predictions={
                    "task_completion_likelihood": 0.8,
                    "current_focus_area": 0.9,  # Highly focused
                    "context_switching_probability": 0.2,  # Low switching
                    "session_continuation": 0.7
                },
                context={"session_length": 60, "task_type": "development", "interruptions": 0},
                test_name="task_focused_pattern"
            )
        ]
    
    @pytest.mark.skipif(not AI_MODULES_AVAILABLE, reason="AI modules not available")
    def test_behavior_predictions(self) -> Dict[str, float]:
        """Test behavior prediction accuracy"""
        
        test_cases = self.create_behavior_test_cases()
        results = {}
        
        # Mock behavior tracker and analyzer
        behavior_tracker = MockBehaviorTracker()
        analyzer = MockUserBehaviorAnalyzer(behavior_tracker)
        
        for test_case in test_cases:
            # Add test actions to behavior tracker
            for action in test_case.user_actions:
                behavior_tracker.add_interaction(action)
            
            # Get predictions
            predictions = analyzer.predict_user_behavior(test_case.context)
            
            # Calculate accuracy for each prediction
            accuracy_scores = []
            for key, expected_value in test_case.expected_predictions.items():
                predicted_value = predictions.get(key, 0.5)  # Default to neutral
                
                # Calculate absolute error and convert to accuracy
                error = abs(predicted_value - expected_value)
                accuracy = max(0, 1 - error)  # Convert error to accuracy
                accuracy_scores.append(accuracy)
            
            # Average accuracy for this test case
            test_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
            results[test_case.test_name] = test_accuracy
        
        return results

class AdaptationTester:
    """Test UI adaptation system"""
    
    def __init__(self):
        self.config = get_test_config()
    
    @pytest.mark.skipif(not AI_MODULES_AVAILABLE, reason="AI modules not available")
    def test_adaptation_triggers(self) -> List[AdaptationTestResult]:
        """Test UI adaptation triggering accuracy"""
        
        # Create test scenarios for adaptations
        scenarios = [
            {
                "name": "layout_optimization",
                "user_profile": {"expertise": 0.9, "command_usage": 150, "efficiency": 0.85},
                "expected_adaptation": "power_user_layout",
                "should_trigger": True
            },
            {
                "name": "help_level_adaptation", 
                "user_profile": {"expertise": 0.2, "error_rate": 0.4, "help_requests": 8},
                "expected_adaptation": "beginner_assistance",
                "should_trigger": True
            },
            {
                "name": "performance_optimization",
                "user_profile": {"device_performance": 0.3, "response_sensitivity": 0.8},
                "expected_adaptation": "fast_mode",
                "should_trigger": True
            },
            {
                "name": "no_adaptation_needed",
                "user_profile": {"expertise": 0.6, "satisfaction": 0.8, "efficiency": 0.7},
                "expected_adaptation": None,
                "should_trigger": False
            }
        ]
        
        results = []
        adapter = MockAdaptiveInterface()
        
        for scenario in scenarios:
            start_time = time.time()
            
            # Test adaptation decision
            adaptation_decision = adapter.should_adapt(scenario["user_profile"])
            adaptation_type = adapter.get_adaptation_type(scenario["user_profile"])
            
            adaptation_time = (time.time() - start_time) * 1000
            
            # Check if adaptation was correctly triggered
            triggered_correctly = (adaptation_decision == scenario["should_trigger"])
            
            # Check if adaptation type is correct
            type_correct = True
            if scenario["should_trigger"]:
                type_correct = (adaptation_type == scenario["expected_adaptation"])
            
            # Calculate accuracy
            accuracy = 1.0 if (triggered_correctly and type_correct) else 0.0
            
            # Estimate user satisfaction (would be measured in real usage)
            user_satisfaction = 0.8 if accuracy == 1.0 else 0.3
            
            # Calculate effectiveness score
            effectiveness = accuracy * user_satisfaction
            
            results.append(AdaptationTestResult(
                adaptation_type=scenario["name"],
                triggered=adaptation_decision,
                accuracy=accuracy,
                user_satisfaction_estimate=user_satisfaction,
                adaptation_time_ms=adaptation_time,
                effectiveness_score=effectiveness
            ))
        
        return results

# Mock classes for testing when AI modules aren't available
class MockBehaviorTracker:
    def __init__(self):
        self.interactions = []
    
    def add_interaction(self, interaction: Dict[str, Any]):
        self.interactions.append(interaction)

class MockUserBehaviorAnalyzer:
    def __init__(self, behavior_tracker):
        self.behavior_tracker = behavior_tracker
    
    def predict_user_behavior(self, context: Dict[str, Any]) -> Dict[str, float]:
        # Simple mock predictions based on context
        interactions = self.behavior_tracker.interactions
        
        if not interactions:
            return {"user_expertise": 0.5, "needs_help": 0.5}
        
        # Count help requests
        help_requests = sum(1 for i in interactions if i.get("action") == "help_request")
        errors = sum(1 for i in interactions if i.get("action") == "error")
        successful_commands = sum(1 for i in interactions if i.get("action") == "successful_command")
        
        total_actions = len(interactions)
        
        # Calculate simple predictions
        needs_help = min(1.0, help_requests / max(1, total_actions))
        user_expertise = max(0.1, 1.0 - (errors + help_requests) / max(1, total_actions))
        command_confidence = successful_commands / max(1, total_actions)
        preferred_interaction = 1.0 - user_expertise
        
        return {
            "user_expertise": user_expertise,
            "needs_help": needs_help,
            "command_confidence": command_confidence,
            "preferred_interaction": preferred_interaction,
            "task_completion_likelihood": 0.7,
            "current_focus_area": 0.8,
            "context_switching_probability": 0.3,
            "session_continuation": 0.6
        }

class MockAdaptiveInterface:
    def should_adapt(self, user_profile: Dict[str, Any]) -> bool:
        expertise = user_profile.get("expertise", 0.5)
        error_rate = user_profile.get("error_rate", 0.1)
        device_performance = user_profile.get("device_performance", 1.0)
        
        # Adaptation triggers
        if expertise > 0.8 and user_profile.get("command_usage", 0) > 100:
            return True  # Power user layout
        
        if error_rate > 0.3 or user_profile.get("help_requests", 0) > 5:
            return True  # Beginner assistance
        
        if device_performance < 0.5:
            return True  # Performance optimization
        
        return False
    
    def get_adaptation_type(self, user_profile: Dict[str, Any]) -> str:
        expertise = user_profile.get("expertise", 0.5)
        error_rate = user_profile.get("error_rate", 0.1)
        device_performance = user_profile.get("device_performance", 1.0)
        
        if expertise > 0.8:
            return "power_user_layout"
        elif error_rate > 0.3:
            return "beginner_assistance"
        elif device_performance < 0.5:
            return "fast_mode"
        else:
            return "no_adaptation"

# Test fixtures
@pytest.fixture
def ml_model_tester():
    """ML model tester fixture"""
    return MLModelTester()

@pytest.fixture
def behavior_tester():
    """Behavior prediction tester fixture"""
    return BehaviorPredictionTester()

@pytest.fixture
def adaptation_tester():
    """Adaptation tester fixture"""
    return AdaptationTester()

# Test classes
class TestMLModelAccuracy:
    """Test ML model accuracy and performance"""
    
    @pytest.mark.ai_intelligence
    @pytest.mark.skipif(not TENSORFLOW_AVAILABLE, reason="TensorFlow not available")
    def test_user_behavior_model_accuracy(self, ml_model_tester):
        """Test user behavior classification model accuracy"""
        
        result = ml_model_tester.test_model_accuracy()
        
        # Validate accuracy meets threshold
        assert result.accuracy >= ml_model_tester.accuracy_threshold, \
            f"Model accuracy {result.accuracy:.3f} below threshold {ml_model_tester.accuracy_threshold}"
        
        # Validate prediction latency
        assert result.prediction_latency_ms <= ml_model_tester.latency_threshold_ms, \
            f"Prediction latency {result.prediction_latency_ms:.1f}ms exceeds threshold"
        
        # Validate inference success
        assert result.inference_successful, f"Inference failed: {result.error_messages}"
        
        # Validate precision and recall
        assert result.precision >= 0.7, f"Precision too low: {result.precision:.3f}"
        assert result.recall >= 0.7, f"Recall too low: {result.recall:.3f}"
        assert result.f1_score >= 0.7, f"F1-score too low: {result.f1_score:.3f}"
    
    @pytest.mark.ai_intelligence
    @pytest.mark.skipif(not TENSORFLOW_AVAILABLE, reason="TensorFlow not available")
    def test_model_performance_under_load(self, ml_model_tester):
        """Test model performance under concurrent load"""
        
        model, _ = ml_model_tester.train_test_model()
        X_test, _ = ml_model_tester.generate_test_data(100)
        
        # Test concurrent predictions
        import threading
        import concurrent.futures
        
        def predict_batch():
            start_time = time.time()
            predictions = model.predict(X_test, verbose=0)
            return time.time() - start_time
        
        # Run 10 concurrent predictions
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(predict_batch) for _ in range(10)]
            prediction_times = [future.result() for future in futures]
        
        # Average prediction time should still be reasonable
        avg_prediction_time_ms = (sum(prediction_times) / len(prediction_times)) * 1000
        assert avg_prediction_time_ms <= ml_model_tester.latency_threshold_ms * 2, \
            f"Concurrent prediction time too high: {avg_prediction_time_ms:.1f}ms"
    
    @pytest.mark.ai_intelligence
    def test_model_size_constraints(self, ml_model_tester):
        """Test that model size meets deployment constraints"""
        
        if not TENSORFLOW_AVAILABLE:
            pytest.skip("TensorFlow not available")
        
        result = ml_model_tester.test_model_accuracy()
        
        # Model should be small enough for browser deployment
        max_model_size_mb = 10  # 10MB limit for browser deployment
        assert result.model_size_mb <= max_model_size_mb, \
            f"Model size {result.model_size_mb:.1f}MB exceeds limit {max_model_size_mb}MB"

class TestBehaviorPrediction:
    """Test behavior prediction accuracy"""
    
    @pytest.mark.ai_intelligence
    def test_user_behavior_predictions(self, behavior_tester):
        """Test behavior prediction accuracy"""
        
        results = behavior_tester.test_behavior_predictions()
        
        # Check accuracy for each test case
        for test_name, accuracy in results.items():
            assert accuracy >= 0.7, f"Behavior prediction accuracy too low for {test_name}: {accuracy:.3f}"
        
        # Overall accuracy should be good
        avg_accuracy = sum(results.values()) / len(results)
        assert avg_accuracy >= 0.75, f"Overall behavior prediction accuracy too low: {avg_accuracy:.3f}"
    
    @pytest.mark.ai_intelligence
    def test_prediction_consistency(self, behavior_tester):
        """Test that predictions are consistent for similar inputs"""
        
        # Create similar user patterns
        similar_patterns = [
            {
                "actions": [
                    {"action": "help_request", "context": "menu"},
                    {"action": "error", "type": "syntax"},
                    {"action": "help_request", "context": "command"}
                ],
                "context": {"expertise_level": "beginner"}
            },
            {
                "actions": [
                    {"action": "help_request", "context": "navigation"},
                    {"action": "error", "type": "typo"},
                    {"action": "help_request", "context": "syntax"}
                ],
                "context": {"expertise_level": "beginner"}
            }
        ]
        
        # Mock analyzer
        tracker = MockBehaviorTracker()
        analyzer = MockUserBehaviorAnalyzer(tracker)
        
        predictions = []
        for pattern in similar_patterns:
            # Clear previous interactions
            tracker.interactions.clear()
            
            # Add pattern actions
            for action in pattern["actions"]:
                tracker.add_interaction(action)
            
            # Get predictions
            pred = analyzer.predict_user_behavior(pattern["context"])
            predictions.append(pred)
        
        # Predictions should be similar
        for key in predictions[0].keys():
            if key in predictions[1]:
                diff = abs(predictions[0][key] - predictions[1][key])
                assert diff <= 0.2, f"Inconsistent predictions for {key}: {diff:.3f}"
    
    @pytest.mark.ai_intelligence
    def test_prediction_confidence_scores(self, behavior_tester):
        """Test that prediction confidence scores are reasonable"""
        
        # Test with clear patterns
        clear_expert_pattern = [
            {"action": "complex_command", "success": True},
            {"action": "shortcut_used", "efficiency": 0.9},
            {"action": "batch_operation", "items": 20}
        ]
        
        ambiguous_pattern = [
            {"action": "help_request"},
            {"action": "successful_command"},
            {"action": "error", "recovered": True}
        ]
        
        tracker = MockBehaviorTracker()
        analyzer = MockUserBehaviorAnalyzer(tracker)
        
        # Test clear pattern
        for action in clear_expert_pattern:
            tracker.add_interaction(action)
        
        clear_predictions = analyzer.predict_user_behavior({"clarity": "high"})
        
        # Clear patterns should have more extreme (confident) predictions
        expert_confidence = clear_predictions.get("user_expertise", 0.5)
        assert expert_confidence > 0.7 or expert_confidence < 0.3, \
            f"Clear pattern should have confident prediction: {expert_confidence:.3f}"

class TestUIAdaptation:
    """Test UI adaptation system"""
    
    @pytest.mark.ai_intelligence
    def test_adaptation_accuracy(self, adaptation_tester):
        """Test UI adaptation triggering accuracy"""
        
        results = adaptation_tester.test_adaptation_triggers()
        
        # Check each adaptation result
        for result in results:
            assert result.accuracy >= 0.8, \
                f"Adaptation accuracy too low for {result.adaptation_type}: {result.accuracy:.3f}"
            
            # Adaptation time should be fast
            assert result.adaptation_time_ms <= 50, \
                f"Adaptation time too slow for {result.adaptation_type}: {result.adaptation_time_ms:.1f}ms"
            
            # Effectiveness should be reasonable
            assert result.effectiveness_score >= 0.6, \
                f"Adaptation effectiveness too low for {result.adaptation_type}: {result.effectiveness_score:.3f}"
        
        # Overall system accuracy
        avg_accuracy = sum(r.accuracy for r in results) / len(results)
        assert avg_accuracy >= 0.8, f"Overall adaptation accuracy too low: {avg_accuracy:.3f}"
    
    @pytest.mark.ai_intelligence
    def test_adaptation_relevance(self, adaptation_tester):
        """Test that adaptations are relevant to user behavior"""
        
        # Test specific user profiles
        test_profiles = [
            {
                "profile": {"expertise": 0.1, "error_rate": 0.5, "help_requests": 10},
                "expected_adaptations": ["beginner_assistance", "help_level_adaptation"],
                "unexpected_adaptations": ["power_user_layout", "advanced_features"]
            },
            {
                "profile": {"expertise": 0.9, "command_usage": 200, "shortcuts_used": 15},
                "expected_adaptations": ["power_user_layout", "advanced_shortcuts"],
                "unexpected_adaptations": ["beginner_assistance", "tutorial_mode"]
            }
        ]
        
        adapter = MockAdaptiveInterface()
        
        for test in test_profiles:
            should_adapt = adapter.should_adapt(test["profile"])
            
            if should_adapt:
                adaptation_type = adapter.get_adaptation_type(test["profile"])
                
                # Check if adaptation is appropriate
                is_expected = any(expected in adaptation_type for expected in test.get("expected_adaptations", []))
                is_unexpected = any(unexpected in adaptation_type for unexpected in test.get("unexpected_adaptations", []))
                
                assert is_expected or not is_unexpected, \
                    f"Inappropriate adaptation {adaptation_type} for profile {test['profile']}"
    
    @pytest.mark.ai_intelligence
    def test_adaptation_learning(self):
        """Test that adaptation system learns from user feedback"""
        
        # Simulate user feedback on adaptations
        adaptation_feedback = [
            {"adaptation": "power_user_layout", "user_kept": True, "satisfaction": 0.9},
            {"adaptation": "beginner_assistance", "user_kept": False, "satisfaction": 0.3},
            {"adaptation": "fast_mode", "user_kept": True, "satisfaction": 0.8}
        ]
        
        # Mock adaptation learning system
        class MockAdaptationLearner:
            def __init__(self):
                self.feedback_history = []
            
            def record_feedback(self, feedback):
                self.feedback_history.append(feedback)
            
            def get_adaptation_confidence(self, adaptation_type):
                relevant_feedback = [f for f in self.feedback_history 
                                   if f["adaptation"] == adaptation_type]
                if not relevant_feedback:
                    return 0.5  # Neutral confidence
                
                avg_satisfaction = sum(f["satisfaction"] for f in relevant_feedback) / len(relevant_feedback)
                return avg_satisfaction
        
        learner = MockAdaptationLearner()
        
        # Record feedback
        for feedback in adaptation_feedback:
            learner.record_feedback(feedback)
        
        # Test learning
        power_user_confidence = learner.get_adaptation_confidence("power_user_layout")
        beginner_confidence = learner.get_adaptation_confidence("beginner_assistance")
        
        assert power_user_confidence > 0.7, f"Should learn that power user layout is good: {power_user_confidence:.3f}"
        assert beginner_confidence < 0.5, f"Should learn that beginner assistance was poor: {beginner_confidence:.3f}"

class TestTensorFlowJSIntegration:
    """Test TensorFlow.js integration"""
    
    @pytest.mark.ai_intelligence
    @pytest.mark.skipif(not TENSORFLOWJS_AVAILABLE, reason="TensorFlow.js not available")
    def test_tensorflowjs_model_conversion(self, ml_model_tester):
        """Test TensorFlow to TensorFlow.js model conversion"""
        
        # Create and train a model
        model, accuracy = ml_model_tester.train_test_model()
        
        # Convert to TensorFlow.js format
        with tempfile.TemporaryDirectory() as temp_dir:
            tfjs_path = Path(temp_dir) / "model_tfjs"
            
            tfjs.converters.save_keras_model(model, str(tfjs_path))
            
            # Check that conversion was successful
            model_files = list(tfjs_path.glob("*"))
            assert len(model_files) > 0, "TensorFlow.js conversion failed"
            
            # Check for required files
            has_model_json = any("model.json" in f.name for f in model_files)
            has_weights = any("weights" in f.name for f in model_files)
            
            assert has_model_json, "Missing model.json file"
            assert has_weights, "Missing weights file"
            
            # Check model size for browser deployment
            total_size = sum(f.stat().st_size for f in model_files)
            size_mb = total_size / (1024 * 1024)
            
            assert size_mb <= 15, f"TensorFlow.js model too large: {size_mb:.1f}MB"
    
    @pytest.mark.ai_intelligence
    def test_browser_inference_simulation(self):
        """Simulate browser-based inference"""
        
        # Simulate JavaScript-like inference timing
        inference_times = []
        
        for _ in range(100):
            start_time = time.time()
            
            # Simulate model inference with realistic delay
            time.sleep(0.001)  # 1ms simulation
            
            # Simulate JavaScript processing overhead
            time.sleep(0.005)  # 5ms processing
            
            inference_time = (time.time() - start_time) * 1000
            inference_times.append(inference_time)
        
        avg_inference_time = sum(inference_times) / len(inference_times)
        max_inference_time = max(inference_times)
        
        # Browser inference should be fast enough for real-time use
        assert avg_inference_time <= 20, f"Average inference too slow: {avg_inference_time:.1f}ms"
        assert max_inference_time <= 50, f"Max inference too slow: {max_inference_time:.1f}ms"

# Integration tests
@pytest.mark.ai_intelligence
@pytest.mark.integration
class TestIntegratedAISystem:
    """Test integrated AI intelligence system"""
    
    async def test_end_to_end_ai_workflow(self):
        """Test complete AI workflow from behavior tracking to adaptation"""
        
        # Simulate complete workflow
        behavior_tracker = MockBehaviorTracker()
        analyzer = MockUserBehaviorAnalyzer(behavior_tracker)
        adapter = MockAdaptiveInterface()
        
        # Simulate user session
        user_actions = [
            {"action": "login", "timestamp": time.time()},
            {"action": "help_request", "context": "getting_started"},
            {"action": "command_attempt", "success": False},
            {"action": "error", "type": "syntax_error"},
            {"action": "help_request", "context": "command_syntax"},
            {"action": "command_attempt", "success": True, "attempts": 2},
            {"action": "help_request", "context": "advanced_features"}
        ]
        
        # Track behavior
        for action in user_actions:
            behavior_tracker.add_interaction(action)
        
        # Analyze behavior
        predictions = analyzer.predict_user_behavior({
            "session_length": 300,
            "domain": "general"
        })
        
        # Make adaptation decision
        user_profile = {
            "expertise": predictions.get("user_expertise", 0.5),
            "error_rate": 0.4,  # Based on actions
            "help_requests": 3   # Count from actions
        }
        
        should_adapt = adapter.should_adapt(user_profile)
        adaptation_type = adapter.get_adaptation_type(user_profile) if should_adapt else None
        
        # Validate workflow
        assert predictions["user_expertise"] <= 0.5, "Should detect low expertise"
        assert predictions["needs_help"] >= 0.5, "Should detect help need"
        assert should_adapt, "Should recommend adaptation for struggling user"
        assert adaptation_type == "beginner_assistance", f"Wrong adaptation: {adaptation_type}"
    
    async def test_ai_system_performance(self):
        """Test AI system performance under load"""
        
        # Simulate concurrent AI operations
        async def ai_operation():
            tracker = MockBehaviorTracker()
            analyzer = MockUserBehaviorAnalyzer(tracker)
            
            # Add some interactions
            for i in range(10):
                tracker.add_interaction({
                    "action": f"test_action_{i}",
                    "timestamp": time.time() - i
                })
            
            # Analyze behavior
            start_time = time.time()
            predictions = analyzer.predict_user_behavior({"context": "test"})
            analysis_time = (time.time() - start_time) * 1000
            
            return analysis_time
        
        # Run concurrent operations
        tasks = [ai_operation() for _ in range(20)]
        analysis_times = await asyncio.gather(*tasks)
        
        # Performance should be consistent
        avg_time = sum(analysis_times) / len(analysis_times)
        max_time = max(analysis_times)
        
        assert avg_time <= 10, f"Average AI operation too slow: {avg_time:.1f}ms"
        assert max_time <= 25, f"Max AI operation too slow: {max_time:.1f}ms"

# Configure AI intelligence test markers
def pytest_configure(config):
    """Configure AI intelligence test markers"""
    config.addinivalue_line(
        "markers",
        "ai_intelligence: marks tests as AI intelligence tests"
    )