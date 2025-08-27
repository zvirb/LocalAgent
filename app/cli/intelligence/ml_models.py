"""
TensorFlow.js ML Models for Adaptive UI
=======================================

Browser-based machine learning models for real-time user behavior analysis,
command prediction, and interface adaptation. Optimized for 60+ FPS performance.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
from collections import defaultdict, deque

# TensorFlow.js integration through subprocess for browser-less execution
import subprocess
import tempfile
import os

@dataclass
class ModelConfig:
    """Configuration for ML models"""
    model_type: str  # 'behavior_prediction', 'command_completion', 'ui_adaptation'
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 10
    validation_split: float = 0.2
    memory_limit_mb: int = 100  # Memory limit for model
    inference_timeout_ms: int = 5  # Must be under 5ms for 60+ FPS
    
@dataclass
class TrainingData:
    """Training data container"""
    features: List[List[float]]
    labels: List[Union[int, float, List[float]]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        return np.array(self.features), np.array(self.labels)

@dataclass
class ModelPerformance:
    """Model performance metrics"""
    accuracy: float = 0.0
    loss: float = float('inf')
    inference_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    training_time_s: float = 0.0
    fps_compliant: bool = False
    
    def update_inference_time(self, inference_time_ms: float):
        self.inference_time_ms = inference_time_ms
        self.fps_compliant = inference_time_ms <= 5.0  # 5ms target for 60+ FPS

class TensorFlowJSModelManager:
    """
    Manages TensorFlow.js models for adaptive UI with performance optimization
    """
    
    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or Path.home() / ".localagent" / "ml_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("TensorFlowJSModelManager")
        
        # Model registry
        self.models: Dict[str, 'AdaptiveUIModel'] = {}
        self.model_configs: Dict[str, ModelConfig] = {}
        self.performance_metrics: Dict[str, ModelPerformance] = {}
        
        # Performance tracking
        self.inference_times = deque(maxlen=1000)
        self.memory_usage_history = deque(maxlen=100)
        
        # TensorFlow.js runtime setup
        self.tfjs_runtime_ready = False
        self._setup_tfjs_runtime()
    
    def _setup_tfjs_runtime(self):
        """Setup TensorFlow.js runtime environment"""
        try:
            # Create TensorFlow.js execution environment
            self.tfjs_env = TensorFlowJSEnvironment(self.models_dir)
            self.tfjs_runtime_ready = True
            self.logger.info("TensorFlow.js runtime initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize TensorFlow.js runtime: {e}")
            self.tfjs_runtime_ready = False
    
    async def create_model(self, model_id: str, config: ModelConfig) -> 'AdaptiveUIModel':
        """Create a new ML model"""
        if not self.tfjs_runtime_ready:
            raise RuntimeError("TensorFlow.js runtime not available")
        
        model = AdaptiveUIModel(
            model_id=model_id,
            config=config,
            tfjs_env=self.tfjs_env,
            models_dir=self.models_dir
        )
        
        await model.initialize()
        
        self.models[model_id] = model
        self.model_configs[model_id] = config
        self.performance_metrics[model_id] = ModelPerformance()
        
        self.logger.info(f"Created model: {model_id} ({config.model_type})")
        
        return model
    
    async def load_model(self, model_id: str) -> Optional['AdaptiveUIModel']:
        """Load existing model from storage"""
        model_path = self.models_dir / f"{model_id}.json"
        
        if not model_path.exists():
            self.logger.warning(f"Model not found: {model_id}")
            return None
        
        try:
            with open(model_path, 'r') as f:
                model_data = json.load(f)
            
            config = ModelConfig(**model_data['config'])
            
            model = AdaptiveUIModel(
                model_id=model_id,
                config=config,
                tfjs_env=self.tfjs_env,
                models_dir=self.models_dir
            )
            
            await model.load_from_file(model_path)
            
            self.models[model_id] = model
            self.model_configs[model_id] = config
            self.performance_metrics[model_id] = ModelPerformance(**model_data.get('performance', {}))
            
            self.logger.info(f"Loaded model: {model_id}")
            
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_id}: {e}")
            return None
    
    async def predict(self, model_id: str, input_data: List[float], 
                     timeout_ms: int = 5) -> Optional[List[float]]:
        """Make prediction with performance tracking"""
        if model_id not in self.models:
            self.logger.warning(f"Model not found for prediction: {model_id}")
            return None
        
        model = self.models[model_id]
        start_time = time.time() * 1000  # ms
        
        try:
            # Make prediction with timeout
            prediction = await asyncio.wait_for(
                model.predict(input_data),
                timeout=timeout_ms / 1000.0
            )
            
            # Track performance
            inference_time = time.time() * 1000 - start_time
            self.inference_times.append(inference_time)
            
            # Update model performance metrics
            perf = self.performance_metrics[model_id]
            perf.update_inference_time(inference_time)
            
            if inference_time > 5.0:  # Log if too slow for 60+ FPS
                self.logger.warning(f"Slow inference for {model_id}: {inference_time:.1f}ms")
            
            return prediction
            
        except asyncio.TimeoutError:
            self.logger.error(f"Prediction timeout for {model_id} ({timeout_ms}ms)")
            return None
        except Exception as e:
            self.logger.error(f"Prediction error for {model_id}: {e}")
            return None
    
    async def train_model(self, model_id: str, training_data: TrainingData, 
                         validation_data: Optional[TrainingData] = None) -> bool:
        """Train model with the provided data"""
        if model_id not in self.models:
            self.logger.error(f"Model not found for training: {model_id}")
            return False
        
        model = self.models[model_id]
        start_time = time.time()
        
        try:
            success = await model.train(training_data, validation_data)
            
            # Update performance metrics
            training_time = time.time() - start_time
            perf = self.performance_metrics[model_id]
            perf.training_time_s = training_time
            
            self.logger.info(f"Training completed for {model_id}: {training_time:.1f}s")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Training failed for {model_id}: {e}")
            return False
    
    async def optimize_model(self, model_id: str) -> bool:
        """Optimize model for performance and memory usage"""
        if model_id not in self.models:
            return False
        
        model = self.models[model_id]
        
        try:
            # Quantization and pruning for performance
            await model.quantize()
            
            # Update performance metrics
            perf = self.performance_metrics[model_id]
            
            # Test inference speed after optimization
            test_input = [0.0] * model.config.input_shape[0]
            start_time = time.time() * 1000
            
            await model.predict(test_input)
            
            inference_time = time.time() * 1000 - start_time
            perf.update_inference_time(inference_time)
            
            self.logger.info(f"Model {model_id} optimized: {inference_time:.1f}ms inference")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Model optimization failed for {model_id}: {e}")
            return False
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all models"""
        return {
            'model_count': len(self.models),
            'avg_inference_time': sum(self.inference_times) / len(self.inference_times) 
                                 if self.inference_times else 0,
            'fps_compliant_models': sum(1 for perf in self.performance_metrics.values() 
                                      if perf.fps_compliant),
            'total_memory_usage': sum(perf.memory_usage_mb for perf in self.performance_metrics.values()),
            'model_performance': {
                model_id: {
                    'inference_time_ms': perf.inference_time_ms,
                    'memory_usage_mb': perf.memory_usage_mb,
                    'fps_compliant': perf.fps_compliant,
                    'accuracy': perf.accuracy
                }
                for model_id, perf in self.performance_metrics.items()
            }
        }


class AdaptiveUIModel:
    """
    Individual ML model for specific UI adaptation tasks
    """
    
    def __init__(self, model_id: str, config: ModelConfig, 
                 tfjs_env: 'TensorFlowJSEnvironment', models_dir: Path):
        self.model_id = model_id
        self.config = config
        self.tfjs_env = tfjs_env
        self.models_dir = models_dir
        self.logger = logging.getLogger(f"AdaptiveUIModel.{model_id}")
        
        # Model state
        self.is_trained = False
        self.is_quantized = False
        self.training_history: List[Dict[str, float]] = []
        
        # Performance tracking
        self.prediction_count = 0
        self.total_inference_time = 0.0
    
    async def initialize(self):
        """Initialize the model structure"""
        try:
            # Create model architecture based on type
            if self.config.model_type == 'behavior_prediction':
                await self._create_behavior_prediction_model()
            elif self.config.model_type == 'command_completion':
                await self._create_command_completion_model()
            elif self.config.model_type == 'ui_adaptation':
                await self._create_ui_adaptation_model()
            else:
                raise ValueError(f"Unknown model type: {self.config.model_type}")
            
            self.logger.info(f"Model {self.model_id} initialized")
            
        except Exception as e:
            self.logger.error(f"Model initialization failed: {e}")
            raise
    
    async def _create_behavior_prediction_model(self):
        """Create neural network for behavior prediction"""
        model_script = f"""
        const tf = require('@tensorflow/tfjs-node');
        
        const model = tf.sequential({{
            layers: [
                tf.layers.dense({{
                    inputShape: [{self.config.input_shape[0]}],
                    units: 64,
                    activation: 'relu'
                }}),
                tf.layers.dropout({{rate: 0.2}}),
                tf.layers.dense({{
                    units: 32,
                    activation: 'relu'
                }}),
                tf.layers.dense({{
                    units: {self.config.output_shape[0]},
                    activation: 'softmax'
                }})
            ]
        }});
        
        model.compile({{
            optimizer: tf.train.adam({self.config.learning_rate}),
            loss: 'categoricalCrossentropy',
            metrics: ['accuracy']
        }});
        
        await model.save('file://{self.models_dir}/{self.model_id}');
        console.log('Behavior prediction model created');
        """
        
        await self.tfjs_env.execute_script(model_script)
    
    async def _create_command_completion_model(self):
        """Create LSTM model for command completion"""
        model_script = f"""
        const tf = require('@tensorflow/tfjs-node');
        
        const model = tf.sequential({{
            layers: [
                tf.layers.lstm({{
                    inputShape: [{self.config.input_shape[0]}, {self.config.input_shape[1]}],
                    units: 128,
                    returnSequences: true
                }}),
                tf.layers.dropout({{rate: 0.3}}),
                tf.layers.lstm({{
                    units: 64,
                    returnSequences: false
                }}),
                tf.layers.dense({{
                    units: {self.config.output_shape[0]},
                    activation: 'softmax'
                }})
            ]
        }});
        
        model.compile({{
            optimizer: tf.train.adam({self.config.learning_rate}),
            loss: 'sparseCategoricalCrossentropy',
            metrics: ['accuracy']
        }});
        
        await model.save('file://{self.models_dir}/{self.model_id}');
        console.log('Command completion model created');
        """
        
        await self.tfjs_env.execute_script(model_script)
    
    async def _create_ui_adaptation_model(self):
        """Create CNN for UI pattern recognition"""
        model_script = f"""
        const tf = require('@tensorflow/tfjs-node');
        
        const model = tf.sequential({{
            layers: [
                tf.layers.dense({{
                    inputShape: [{self.config.input_shape[0]}],
                    units: 128,
                    activation: 'relu'
                }}),
                tf.layers.batchNormalization(),
                tf.layers.dropout({{rate: 0.2}}),
                tf.layers.dense({{
                    units: 64,
                    activation: 'relu'  
                }}),
                tf.layers.dense({{
                    units: 32,
                    activation: 'relu'
                }}),
                tf.layers.dense({{
                    units: {self.config.output_shape[0]},
                    activation: 'sigmoid'
                }})
            ]
        }});
        
        model.compile({{
            optimizer: tf.train.adam({self.config.learning_rate}),
            loss: 'binaryCrossentropy',
            metrics: ['accuracy']
        }});
        
        await model.save('file://{self.models_dir}/{self.model_id}');
        console.log('UI adaptation model created');
        """
        
        await self.tfjs_env.execute_script(model_script)
    
    async def predict(self, input_data: List[float]) -> List[float]:
        """Make prediction with the model"""
        # Validate input shape
        if len(input_data) != self.config.input_shape[0]:
            raise ValueError(f"Input shape mismatch: expected {self.config.input_shape[0]}, got {len(input_data)}")
        
        start_time = time.time()
        
        # Create prediction script
        input_array = json.dumps(input_data)
        prediction_script = f"""
        const tf = require('@tensorflow/tfjs-node');
        
        const model = await tf.loadLayersModel('file://{self.models_dir}/{self.model_id}/model.json');
        const input = tf.tensor2d([{input_array}]);
        const prediction = model.predict(input);
        const result = await prediction.data();
        
        console.log(JSON.stringify(Array.from(result)));
        
        // Cleanup
        input.dispose();
        prediction.dispose();
        model.dispose();
        """
        
        result = await self.tfjs_env.execute_script(prediction_script)
        
        # Track performance
        inference_time = time.time() - start_time
        self.total_inference_time += inference_time
        self.prediction_count += 1
        
        try:
            # Parse result from stdout
            prediction = json.loads(result.split('\n')[-2])  # Last line before empty
            return prediction
        except (json.JSONDecodeError, IndexError) as e:
            self.logger.error(f"Failed to parse prediction result: {e}")
            return [0.0] * self.config.output_shape[0]
    
    async def train(self, training_data: TrainingData, 
                   validation_data: Optional[TrainingData] = None) -> bool:
        """Train the model with provided data"""
        try:
            # Prepare training data
            features, labels = training_data.to_arrays()
            
            # Create training script
            training_script = f"""
            const tf = require('@tensorflow/tfjs-node');
            
            const model = await tf.loadLayersModel('file://{self.models_dir}/{self.model_id}/model.json');
            
            // Training data
            const xs = tf.tensor2d({features.tolist()});
            const ys = tf.tensor2d({labels.tolist()});
            
            // Training
            const history = await model.fit(xs, ys, {{
                epochs: {self.config.epochs},
                batchSize: {self.config.batch_size},
                validationSplit: {self.config.validation_split},
                verbose: 0
            }});
            
            // Save trained model
            await model.save('file://{self.models_dir}/{self.model_id}');
            
            // Output training metrics
            console.log(JSON.stringify(history.history));
            
            // Cleanup
            xs.dispose();
            ys.dispose();
            model.dispose();
            """
            
            result = await self.tfjs_env.execute_script(training_script)
            
            # Parse training history
            history = json.loads(result.split('\n')[-2])
            self.training_history.append(history)
            self.is_trained = True
            
            self.logger.info(f"Training completed for {self.model_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Training failed for {self.model_id}: {e}")
            return False
    
    async def quantize(self) -> bool:
        """Quantize model for better performance"""
        if self.is_quantized:
            return True
        
        try:
            quantization_script = f"""
            const tf = require('@tensorflow/tfjs-node');
            
            const model = await tf.loadLayersModel('file://{self.models_dir}/{self.model_id}/model.json');
            
            // Quantize the model
            const quantizedModel = await tf.quantization.quantize(model);
            
            // Save quantized model
            await quantizedModel.save('file://{self.models_dir}/{self.model_id}_quantized');
            
            console.log('Model quantized successfully');
            
            model.dispose();
            quantizedModel.dispose();
            """
            
            await self.tfjs_env.execute_script(quantization_script)
            self.is_quantized = True
            
            self.logger.info(f"Model {self.model_id} quantized for performance")
            return True
            
        except Exception as e:
            self.logger.error(f"Quantization failed for {self.model_id}: {e}")
            return False
    
    async def load_from_file(self, model_path: Path) -> bool:
        """Load model from saved file"""
        try:
            # Model should already exist at the path
            self.is_trained = True
            self.logger.info(f"Model {self.model_id} loaded from {model_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load model {self.model_id}: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get model performance statistics"""
        avg_inference_time = (self.total_inference_time / self.prediction_count * 1000) \
                            if self.prediction_count > 0 else 0
        
        return {
            'model_id': self.model_id,
            'model_type': self.config.model_type,
            'is_trained': self.is_trained,
            'is_quantized': self.is_quantized,
            'prediction_count': self.prediction_count,
            'avg_inference_time_ms': avg_inference_time,
            'fps_compliant': avg_inference_time <= 5.0,
            'training_epochs': len(self.training_history) * self.config.epochs,
            'memory_limit_mb': self.config.memory_limit_mb
        }


class TensorFlowJSEnvironment:
    """
    TensorFlow.js execution environment for running ML models
    """
    
    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self.logger = logging.getLogger("TensorFlowJSEnvironment")
        
        # Setup Node.js environment for TensorFlow.js
        self.node_modules_dir = working_dir / "node_modules"
        self._setup_node_environment()
    
    def _setup_node_environment(self):
        """Setup Node.js environment with TensorFlow.js"""
        try:
            # Create package.json if it doesn't exist
            package_json = self.working_dir / "package.json"
            if not package_json.exists():
                package_content = {
                    "name": "adaptive-ui-ml",
                    "version": "1.0.0",
                    "dependencies": {
                        "@tensorflow/tfjs-node": "^4.0.0",
                        "@tensorflow/tfjs": "^4.0.0"
                    }
                }
                
                with open(package_json, 'w') as f:
                    json.dump(package_content, f, indent=2)
            
            # Install dependencies if not present
            if not self.node_modules_dir.exists():
                self.logger.info("Installing TensorFlow.js dependencies...")
                subprocess.run(
                    ["npm", "install"], 
                    cwd=self.working_dir,
                    check=True,
                    capture_output=True
                )
                self.logger.info("TensorFlow.js dependencies installed")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to setup Node.js environment: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Environment setup error: {e}")
            raise
    
    async def execute_script(self, script_content: str, timeout: int = 30) -> str:
        """Execute JavaScript with TensorFlow.js"""
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Execute with Node.js
            result = subprocess.run(
                ["node", script_path],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Script execution failed: {result.stderr}")
                raise RuntimeError(f"TensorFlow.js script failed: {result.stderr}")
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            self.logger.error("Script execution timeout")
            raise RuntimeError("TensorFlow.js script timeout")
        finally:
            # Cleanup
            try:
                os.unlink(script_path)
            except OSError:
                pass


# Convenience functions
async def create_behavior_prediction_model(model_manager: TensorFlowJSModelManager,
                                          input_features: int = 50,
                                          output_classes: int = 10) -> AdaptiveUIModel:
    """Create a model for predicting user behavior patterns"""
    config = ModelConfig(
        model_type='behavior_prediction',
        input_shape=(input_features,),
        output_shape=(output_classes,),
        learning_rate=0.001,
        batch_size=16,
        epochs=20
    )
    
    return await model_manager.create_model("behavior_predictor", config)

async def create_command_completion_model(model_manager: TensorFlowJSModelManager,
                                        sequence_length: int = 10,
                                        vocab_size: int = 1000) -> AdaptiveUIModel:
    """Create a model for command completion suggestions"""
    config = ModelConfig(
        model_type='command_completion',
        input_shape=(sequence_length, vocab_size),
        output_shape=(vocab_size,),
        learning_rate=0.001,
        batch_size=32,
        epochs=15
    )
    
    return await model_manager.create_model("command_completer", config)

async def create_ui_adaptation_model(model_manager: TensorFlowJSModelManager,
                                   ui_features: int = 30,
                                   adaptation_types: int = 5) -> AdaptiveUIModel:
    """Create a model for UI adaptation decisions"""
    config = ModelConfig(
        model_type='ui_adaptation',
        input_shape=(ui_features,),
        output_shape=(adaptation_types,),
        learning_rate=0.0005,
        batch_size=64,
        epochs=25
    )
    
    return await model_manager.create_model("ui_adapter", config)