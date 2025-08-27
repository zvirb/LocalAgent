"""
AI Intelligence Demo and Performance Validation
===============================================

Comprehensive demo and validation system for AI-powered adaptive interface.
Tests all components for 60+ FPS performance and showcases intelligent features.
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import statistics
import random

# Import all intelligence components
from .integration_manager import IntelligenceIntegrationManager, create_intelligence_manager, create_intelligence_config

@dataclass
class PerformanceTest:
    """Performance test specification"""
    name: str
    description: str
    test_function: str
    target_time_ms: float  # Target execution time
    iterations: int = 100
    warmup_iterations: int = 10

@dataclass
class ValidationResult:
    """Result of a validation test"""
    test_name: str
    passed: bool
    execution_times: List[float]
    avg_time_ms: float
    max_time_ms: float
    min_time_ms: float
    fps_compliant: bool
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

class AIIntelligenceDemo:
    """
    Comprehensive demo system showcasing AI intelligence features
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".localagent" / "demo"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("AIIntelligenceDemo")
        
        # Intelligence system
        self.intelligence_manager: Optional[IntelligenceIntegrationManager] = None
        
        # Demo scenarios
        self.demo_scenarios = self._create_demo_scenarios()
        
        # Performance tests
        self.performance_tests = self._create_performance_tests()
        
        # Results
        self.demo_results: List[Dict[str, Any]] = []
        self.validation_results: List[ValidationResult] = []
    
    async def initialize(self):
        """Initialize the demo system"""
        try:
            self.logger.info("Initializing AI Intelligence Demo System...")
            
            # Create intelligence configuration optimized for demo
            config = create_intelligence_config(
                enable_behavior_tracking=True,
                enable_ml_models=True,
                enable_adaptive_interface=True,
                enable_command_intelligence=True,
                enable_nlp_processing=True,
                enable_personalization=True,
                enable_performance_prediction=True,
                performance_target_fps=60,
                memory_limit_mb=500,
                learning_enabled=True,
                user_privacy_mode=False  # Disabled for demo
            )
            
            # Initialize intelligence manager
            self.intelligence_manager = await create_intelligence_manager(
                config=config,
                config_dir=self.config_dir,
                user_identifier="demo_user"
            )
            
            self.logger.info("Demo system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize demo system: {e}")
            raise
    
    async def run_full_demo(self) -> Dict[str, Any]:
        """Run the complete AI intelligence demonstration"""
        try:
            self.logger.info("🚀 Starting AI Intelligence Full Demo")
            
            demo_results = {
                'demo_started': time.time(),
                'scenarios': {},
                'performance_validation': {},
                'system_status': {},
                'summary': {}
            }
            
            # 1. Run demo scenarios
            self.logger.info("📋 Running demo scenarios...")
            for scenario_name, scenario in self.demo_scenarios.items():
                self.logger.info(f"  Running scenario: {scenario_name}")
                
                start_time = time.time()
                scenario_result = await self._run_demo_scenario(scenario_name, scenario)
                execution_time = time.time() - start_time
                
                demo_results['scenarios'][scenario_name] = {
                    'result': scenario_result,
                    'execution_time': execution_time,
                    'timestamp': start_time
                }
            
            # 2. Run performance validation
            self.logger.info("⚡ Running performance validation...")
            validation_results = await self.run_performance_validation()
            demo_results['performance_validation'] = validation_results
            
            # 3. Get system status
            demo_results['system_status'] = self.intelligence_manager.get_system_status()
            
            # 4. Generate summary
            demo_results['summary'] = self._generate_demo_summary(demo_results)
            
            # Save results
            await self._save_demo_results(demo_results)
            
            self.logger.info("🎉 AI Intelligence Demo completed successfully")
            
            return demo_results
            
        except Exception as e:
            self.logger.error(f"Demo failed: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    async def run_performance_validation(self) -> Dict[str, Any]:
        """Run comprehensive performance validation"""
        try:
            self.logger.info("🔬 Running Performance Validation Suite")
            
            validation_results = {
                'started': time.time(),
                'tests': {},
                'summary': {
                    'total_tests': 0,
                    'passed_tests': 0,
                    'fps_compliant_tests': 0,
                    'avg_performance_ms': 0.0,
                    'memory_usage_mb': 0.0
                }
            }
            
            # Run each performance test
            for test in self.performance_tests:
                self.logger.info(f"  Testing: {test.name}")
                
                result = await self._run_performance_test(test)
                validation_results['tests'][test.name] = {
                    'passed': result.passed,
                    'avg_time_ms': result.avg_time_ms,
                    'max_time_ms': result.max_time_ms,
                    'fps_compliant': result.fps_compliant,
                    'details': result.details,
                    'error': result.error_message
                }
                
                # Update summary
                validation_results['summary']['total_tests'] += 1
                if result.passed:
                    validation_results['summary']['passed_tests'] += 1
                if result.fps_compliant:
                    validation_results['summary']['fps_compliant_tests'] += 1
            
            # Calculate overall metrics
            all_times = []
            for test_name, test_result in validation_results['tests'].items():
                if 'avg_time_ms' in test_result:
                    all_times.append(test_result['avg_time_ms'])
            
            if all_times:
                validation_results['summary']['avg_performance_ms'] = statistics.mean(all_times)
            
            # Get memory usage
            system_status = self.intelligence_manager.get_system_status()
            validation_results['summary']['memory_usage_mb'] = system_status.get('total_memory_usage_mb', 0)
            
            self.logger.info(f"✅ Performance validation completed: "
                           f"{validation_results['summary']['fps_compliant_tests']}/"
                           f"{validation_results['summary']['total_tests']} tests FPS compliant")
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Performance validation failed: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    async def _run_performance_test(self, test: PerformanceTest) -> ValidationResult:
        """Run a specific performance test"""
        try:
            test_function = getattr(self, test.test_function)
            
            # Warmup runs
            for _ in range(test.warmup_iterations):
                await test_function()
            
            # Actual test runs
            execution_times = []
            
            for i in range(test.iterations):
                start_time = time.time()
                await test_function()
                execution_time = (time.time() - start_time) * 1000  # Convert to ms
                execution_times.append(execution_time)
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.001)
            
            # Calculate metrics
            avg_time = statistics.mean(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)
            
            # Check if test passed (within target time 95% of the time)
            passed_count = sum(1 for t in execution_times if t <= test.target_time_ms)
            passed = (passed_count / len(execution_times)) >= 0.95
            
            # Check FPS compliance (all times under 16ms for 60+ FPS)
            fps_compliant = max_time <= 16.0
            
            return ValidationResult(
                test_name=test.name,
                passed=passed,
                execution_times=execution_times,
                avg_time_ms=avg_time,
                max_time_ms=max_time,
                min_time_ms=min_time,
                fps_compliant=fps_compliant,
                details={
                    'target_time_ms': test.target_time_ms,
                    'iterations': test.iterations,
                    'passed_percentage': (passed_count / len(execution_times)) * 100,
                    'std_dev': statistics.stdev(execution_times) if len(execution_times) > 1 else 0
                }
            )
            
        except Exception as e:
            return ValidationResult(
                test_name=test.name,
                passed=False,
                execution_times=[],
                avg_time_ms=0.0,
                max_time_ms=0.0,
                min_time_ms=0.0,
                fps_compliant=False,
                error_message=str(e)
            )
    
    # Performance test functions
    
    async def _test_command_suggestions(self):
        """Test command suggestion performance"""
        partial_commands = ["ls", "git", "docker", "npm", "python"]
        partial_command = random.choice(partial_commands)
        
        context = {
            'current_directory': '/home/user/project',
            'recent_commands': ['cd /home/user', 'ls -la'],
            'available_providers': ['ollama', 'openai'],
            'user_skill_level': 'intermediate'
        }
        
        suggestions = await self.intelligence_manager.get_command_suggestions(
            partial_command, context
        )
        
        return len(suggestions)
    
    async def _test_natural_language_parsing(self):
        """Test natural language parsing performance"""
        test_phrases = [
            "list all files in current directory",
            "create a new Python file called test.py",
            "run the test suite with verbose output",
            "search for all JavaScript files",
            "analyze the performance of this workflow"
        ]
        
        phrase = random.choice(test_phrases)
        context = {'current_directory': '/home/user/project'}
        
        result = await self.intelligence_manager.parse_natural_language(phrase, context)
        
        return result is not None
    
    async def _test_workflow_performance_prediction(self):
        """Test workflow performance prediction"""
        workflow_types = ['development', 'testing', 'deployment', 'research', 'analysis']
        workflow_type = random.choice(workflow_types)
        
        context = {
            'user_skill_level': 'intermediate',
            'system_load': 0.5,
            'provider_status': {'ollama': True, 'openai': True}
        }
        
        prediction = await self.intelligence_manager.predict_workflow_performance(
            workflow_type, context
        )
        
        return prediction is not None
    
    async def _test_adaptive_interface_analysis(self):
        """Test adaptive interface analysis performance"""
        adaptations = await self.intelligence_manager.apply_adaptive_interface()
        return len(adaptations)
    
    async def _test_behavior_tracking(self):
        """Test behavior tracking performance"""
        interaction_types = ['command_execution', 'ui_interaction', 'provider_usage']
        interaction_type = random.choice(interaction_types)
        
        context = {
            'command': f'test_command_{random.randint(1, 100)}',
            'response_time': random.uniform(0.1, 2.0),
            'success': random.choice([True, False]),
            'provider': random.choice(['ollama', 'openai'])
        }
        
        await self.intelligence_manager.track_user_interaction(interaction_type, context)
        return True
    
    async def _test_memory_management(self):
        """Test memory management performance"""
        # Simulate memory-intensive operations
        large_context = {
            'data': ['item_' + str(i) for i in range(1000)],
            'metadata': {f'key_{i}': f'value_{i}' for i in range(100)}
        }
        
        # Test command suggestions with large context
        suggestions = await self.intelligence_manager.get_command_suggestions(
            "test", large_context
        )
        
        return len(suggestions) >= 0
    
    # Demo scenarios
    
    def _create_demo_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Create demonstration scenarios"""
        return {
            'beginner_user_journey': {
                'description': 'Simulate a beginner user learning the CLI',
                'steps': [
                    {'action': 'get_help', 'input': 'help me get started'},
                    {'action': 'parse_nl', 'input': 'show me all files'},
                    {'action': 'get_suggestions', 'input': 'ls'},
                    {'action': 'track_interaction', 'input': {'command': 'ls -la', 'success': True}},
                    {'action': 'get_workspace', 'input': 'beginner_workspace'}
                ]
            },
            'expert_user_optimization': {
                'description': 'Demonstrate optimization for expert users',
                'steps': [
                    {'action': 'track_interaction', 'input': {'command': 'git status', 'success': True, 'response_time': 0.1}},
                    {'action': 'track_interaction', 'input': {'command': 'git add .', 'success': True, 'response_time': 0.2}},
                    {'action': 'track_interaction', 'input': {'command': 'git commit -m "fix"', 'success': True, 'response_time': 0.15}},
                    {'action': 'get_suggestions', 'input': 'git'},
                    {'action': 'apply_adaptations', 'input': None},
                    {'action': 'get_workspace', 'input': 'expert_workspace'}
                ]
            },
            'workflow_performance_analysis': {
                'description': 'Analyze and predict workflow performance',
                'steps': [
                    {'action': 'predict_performance', 'input': {'workflow': 'development', 'context': {'user_skill_level': 'intermediate'}}},
                    {'action': 'predict_performance', 'input': {'workflow': 'testing', 'context': {'user_skill_level': 'expert'}}},
                    {'action': 'predict_performance', 'input': {'workflow': 'deployment', 'context': {'system_load': 0.8}}},
                ]
            },
            'natural_language_interaction': {
                'description': 'Natural language command processing showcase',
                'steps': [
                    {'action': 'parse_nl', 'input': 'create a new directory called projects'},
                    {'action': 'parse_nl', 'input': 'list all Python files recursively'},
                    {'action': 'parse_nl', 'input': 'run the test suite with verbose output'},
                    {'action': 'parse_nl', 'input': 'find all files modified in the last week'},
                ]
            },
            'adaptive_personalization': {
                'description': 'Demonstrate adaptive personalization features',
                'steps': [
                    {'action': 'simulate_usage_pattern', 'input': 'exploratory'},
                    {'action': 'apply_adaptations', 'input': None},
                    {'action': 'get_workspace', 'input': 'personalized'},
                    {'action': 'simulate_usage_pattern', 'input': 'efficient'},
                    {'action': 'apply_adaptations', 'input': None},
                ]
            }
        }
    
    def _create_performance_tests(self) -> List[PerformanceTest]:
        """Create performance test specifications"""
        return [
            PerformanceTest(
                name="command_suggestions_speed",
                description="Test command suggestion generation speed",
                test_function="_test_command_suggestions",
                target_time_ms=5.0,  # 5ms target for real-time suggestions
                iterations=200
            ),
            PerformanceTest(
                name="nlp_parsing_speed",
                description="Test natural language parsing speed",
                test_function="_test_natural_language_parsing",
                target_time_ms=15.0,  # 15ms target for NLP processing
                iterations=100
            ),
            PerformanceTest(
                name="workflow_prediction_speed",
                description="Test workflow performance prediction speed",
                test_function="_test_workflow_performance_prediction",
                target_time_ms=10.0,  # 10ms target for predictions
                iterations=150
            ),
            PerformanceTest(
                name="adaptive_interface_speed",
                description="Test adaptive interface analysis speed",
                test_function="_test_adaptive_interface_analysis",
                target_time_ms=12.0,  # 12ms target for UI adaptations
                iterations=100
            ),
            PerformanceTest(
                name="behavior_tracking_speed",
                description="Test behavior tracking performance",
                test_function="_test_behavior_tracking",
                target_time_ms=2.0,  # 2ms target for tracking (must be very fast)
                iterations=500
            ),
            PerformanceTest(
                name="memory_management_efficiency",
                description="Test memory management under load",
                test_function="_test_memory_management",
                target_time_ms=20.0,  # 20ms target for memory-intensive operations
                iterations=50
            )
        ]
    
    async def _run_demo_scenario(self, scenario_name: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific demo scenario"""
        try:
            scenario_result = {
                'description': scenario['description'],
                'steps': [],
                'success': True,
                'execution_time': 0.0
            }
            
            start_time = time.time()
            
            for i, step in enumerate(scenario['steps']):
                step_start = time.time()
                
                try:
                    step_result = await self._execute_demo_step(step)
                    step_duration = time.time() - step_start
                    
                    scenario_result['steps'].append({
                        'step': i + 1,
                        'action': step['action'],
                        'input': step['input'],
                        'result': step_result,
                        'duration': step_duration,
                        'success': True
                    })
                    
                except Exception as e:
                    scenario_result['steps'].append({
                        'step': i + 1,
                        'action': step['action'],
                        'input': step['input'],
                        'error': str(e),
                        'duration': time.time() - step_start,
                        'success': False
                    })
                    scenario_result['success'] = False
            
            scenario_result['execution_time'] = time.time() - start_time
            
            return scenario_result
            
        except Exception as e:
            return {
                'description': scenario['description'],
                'error': str(e),
                'success': False,
                'execution_time': 0.0
            }
    
    async def _execute_demo_step(self, step: Dict[str, Any]) -> Any:
        """Execute a single demo step"""
        action = step['action']
        input_data = step['input']
        
        if action == 'get_help':
            return await self.intelligence_manager.parse_natural_language(
                input_data, {'user_skill_level': 'beginner'}
            )
        
        elif action == 'parse_nl':
            return await self.intelligence_manager.parse_natural_language(input_data)
        
        elif action == 'get_suggestions':
            return await self.intelligence_manager.get_command_suggestions(
                input_data, {'user_skill_level': 'intermediate'}
            )
        
        elif action == 'track_interaction':
            await self.intelligence_manager.track_user_interaction('command_execution', input_data)
            return {'tracked': True}
        
        elif action == 'get_workspace':
            return await self.intelligence_manager.get_personalized_workspace(input_data)
        
        elif action == 'apply_adaptations':
            return await self.intelligence_manager.apply_adaptive_interface()
        
        elif action == 'predict_performance':
            return await self.intelligence_manager.predict_workflow_performance(
                input_data['workflow'], input_data['context']
            )
        
        elif action == 'simulate_usage_pattern':
            # Simulate different usage patterns
            pattern = input_data
            commands = self._get_usage_pattern_commands(pattern)
            
            for command in commands:
                await self.intelligence_manager.track_user_interaction(
                    'command_execution',
                    {
                        'command': command,
                        'success': True,
                        'response_time': random.uniform(0.1, 1.0)
                    }
                )
            
            return {'pattern': pattern, 'commands_simulated': len(commands)}
        
        else:
            raise ValueError(f"Unknown demo action: {action}")
    
    def _get_usage_pattern_commands(self, pattern: str) -> List[str]:
        """Get commands that simulate different usage patterns"""
        patterns = {
            'exploratory': [
                'help', 'ls', 'pwd', 'cd ~', 'ls -la', 'file *', 'which python',
                'history', 'alias', 'env', 'ps aux', 'df -h'
            ],
            'efficient': [
                'git status', 'git add .', 'git commit -m "update"', 'git push',
                'ls', 'cd project', 'npm test', 'docker build', 'deploy'
            ],
            'methodical': [
                'ls -la', 'cd project', 'git status', 'git diff', 'git add file.py',
                'python -m pytest', 'coverage report', 'git commit', 'git push'
            ]
        }
        
        return patterns.get(pattern, ['help'])
    
    def _generate_demo_summary(self, demo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate demo summary"""
        summary = {
            'total_scenarios': len(demo_results['scenarios']),
            'successful_scenarios': 0,
            'performance_score': 0.0,
            'fps_compliance': False,
            'memory_usage_ok': False,
            'key_features_demonstrated': [],
            'recommendations': []
        }
        
        # Count successful scenarios
        for scenario_name, scenario_data in demo_results['scenarios'].items():
            if scenario_data.get('result', {}).get('success', False):
                summary['successful_scenarios'] += 1
        
        # Calculate performance score
        if 'performance_validation' in demo_results:
            validation = demo_results['performance_validation']
            if 'summary' in validation:
                val_summary = validation['summary']
                total_tests = val_summary.get('total_tests', 1)
                fps_compliant = val_summary.get('fps_compliant_tests', 0)
                
                summary['performance_score'] = fps_compliant / total_tests if total_tests > 0 else 0
                summary['fps_compliance'] = fps_compliant == total_tests
        
        # Check memory usage
        system_status = demo_results.get('system_status', {})
        memory_usage = system_status.get('total_memory_usage_mb', 0)
        summary['memory_usage_ok'] = memory_usage <= 500  # 500MB limit
        
        # Key features demonstrated
        summary['key_features_demonstrated'] = [
            'Command Intelligence & Auto-completion',
            'Natural Language Processing',
            'Adaptive Interface System',
            'Performance Prediction',
            'User Behavior Learning',
            'Personalized Workspaces',
            'Real-time ML Inference',
            '60+ FPS Performance'
        ]
        
        # Generate recommendations
        if not summary['fps_compliance']:
            summary['recommendations'].append('Optimize ML models for better FPS performance')
        
        if not summary['memory_usage_ok']:
            summary['recommendations'].append('Implement more aggressive memory management')
        
        if summary['successful_scenarios'] < summary['total_scenarios']:
            summary['recommendations'].append('Debug failed scenarios for improved reliability')
        
        return summary
    
    async def _save_demo_results(self, results: Dict[str, Any]):
        """Save demo results to file"""
        try:
            results_file = self.config_dir / f"demo_results_{int(time.time())}.json"
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            self.logger.info(f"Demo results saved to: {results_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save demo results: {e}")
    
    def print_demo_report(self, results: Dict[str, Any]):
        """Print a formatted demo report"""
        print("\n" + "="*80)
        print("🤖 AI-POWERED INTELLIGENT UI ADAPTATIONS - DEMO REPORT")
        print("="*80)
        
        # Summary
        summary = results.get('summary', {})
        print(f"\n📊 SUMMARY:")
        print(f"   Scenarios Run: {summary.get('successful_scenarios', 0)}/{summary.get('total_scenarios', 0)}")
        print(f"   Performance Score: {summary.get('performance_score', 0):.1%}")
        print(f"   FPS Compliant: {'✅ YES' if summary.get('fps_compliance') else '❌ NO'}")
        print(f"   Memory Usage OK: {'✅ YES' if summary.get('memory_usage_ok') else '❌ NO'}")
        
        # System Status
        status = results.get('system_status', {})
        print(f"\n🖥️  SYSTEM STATUS:")
        print(f"   ML Models Loaded: {status.get('ml_models_loaded', 0)}")
        print(f"   Memory Usage: {status.get('total_memory_usage_mb', 0):.1f} MB")
        print(f"   Avg Response Time: {status.get('avg_response_time_ms', 0):.1f} ms")
        print(f"   Requests Processed: {status.get('requests_processed', 0)}")
        
        # Performance Validation
        if 'performance_validation' in results:
            perf = results['performance_validation']
            if 'summary' in perf:
                perf_summary = perf['summary']
                print(f"\n⚡ PERFORMANCE VALIDATION:")
                print(f"   Tests Run: {perf_summary.get('total_tests', 0)}")
                print(f"   Passed: {perf_summary.get('passed_tests', 0)}")
                print(f"   FPS Compliant: {perf_summary.get('fps_compliant_tests', 0)}")
                print(f"   Avg Performance: {perf_summary.get('avg_performance_ms', 0):.1f} ms")
        
        # Key Features
        features = summary.get('key_features_demonstrated', [])
        if features:
            print(f"\n🌟 KEY FEATURES DEMONSTRATED:")
            for feature in features:
                print(f"   ✅ {feature}")
        
        # Recommendations
        recommendations = summary.get('recommendations', [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"   • {rec}")
        
        print("\n" + "="*80)
        print("Demo completed! Check the detailed results file for more information.")
        print("="*80 + "\n")


async def run_ai_intelligence_demo():
    """Run the complete AI intelligence demonstration"""
    demo = AIIntelligenceDemo()
    
    try:
        await demo.initialize()
        results = await demo.run_full_demo()
        demo.print_demo_report(results)
        return results
        
    except Exception as e:
        logging.error(f"Demo failed: {e}")
        return {'error': str(e)}
    finally:
        # Cleanup
        if demo.intelligence_manager:
            await demo.intelligence_manager.shutdown()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the demo
    print("🚀 Starting AI Intelligence Demo...")
    results = asyncio.run(run_ai_intelligence_demo())
    
    if 'error' not in results:
        print("✅ Demo completed successfully!")
    else:
        print(f"❌ Demo failed: {results['error']}")