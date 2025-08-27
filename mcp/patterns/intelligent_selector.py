#!/usr/bin/env python3
"""
Intelligent Pattern Selector - Uses HRM and other MCPs to select optimal patterns
Analyzes context, requirements, and constraints to choose the best orchestration pattern
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re

from mcp.patterns.pattern_registry import (
    pattern_registry, 
    PatternDefinition, 
    PatternCategory,
    BasePattern
)

@dataclass
class PatternSelectionContext:
    """Context for pattern selection"""
    query: str
    task_type: Optional[str] = None
    performance_requirements: Dict[str, Any] = field(default_factory=dict)
    docker_constraints: Dict[str, Any] = field(default_factory=dict)
    available_mcps: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    historical_performance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PatternRecommendation:
    """Pattern recommendation with reasoning"""
    pattern_id: str
    pattern_name: str
    confidence: float
    reasoning: List[str]
    alternative_patterns: List[Tuple[str, float]]  # (pattern_id, confidence)
    execution_plan: Dict[str, Any]
    estimated_performance: Dict[str, Any]

class IntelligentPatternSelector:
    """
    Intelligent pattern selection using HRM reasoning and multi-criteria analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger("IntelligentSelector")
        self.selection_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Dict[str, float]] = {}
        
    async def select_pattern(
        self, 
        context: PatternSelectionContext
    ) -> PatternRecommendation:
        """
        Select the optimal pattern for the given context
        Uses HRM for reasoning and multiple analysis strategies
        """
        
        # Step 1: Analyze query intent using HRM
        intent_analysis = await self._analyze_intent(context)
        
        # Step 2: Filter applicable patterns
        candidate_patterns = await self._filter_candidates(context, intent_analysis)
        
        # Step 3: Score patterns using multiple criteria
        scored_patterns = await self._score_patterns(candidate_patterns, context, intent_analysis)
        
        # Step 4: Select best pattern with HRM consensus
        best_pattern = await self._select_best_pattern(scored_patterns, context)
        
        # Step 5: Generate execution plan
        execution_plan = await self._generate_execution_plan(best_pattern, context)
        
        # Record selection
        self._record_selection(context, best_pattern)
        
        return best_pattern
    
    async def _analyze_intent(self, context: PatternSelectionContext) -> Dict[str, Any]:
        """Analyze query intent using HRM"""
        try:
            from mcp.hrm_mcp import create_hrm_server
            
            hrm = await create_hrm_server()
            
            # Strategic reasoning about the query
            analysis_query = f"""
            Analyze this task and determine the best orchestration approach:
            Task: {context.query}
            
            Consider:
            1. Is this a sequential or parallel task?
            2. Does it require consensus or coordination?
            3. What is the complexity level?
            4. What are the performance requirements?
            """
            
            result = await hrm.reason(
                analysis_query,
                {"query": context.query, "context": context.metadata},
                level=0  # Strategic level
            )
            
            # Extract intent from HRM reasoning
            intent = {
                'decision': result.decision,
                'confidence': result.confidence,
                'evidence': result.evidence,
                'complexity': self._extract_complexity(result.decision),
                'parallelizable': 'parallel' in result.decision.lower(),
                'requires_consensus': 'consensus' in result.decision.lower(),
                'requires_coordination': 'coordinat' in result.decision.lower(),
                'is_iterative': 'iterative' in result.decision.lower() or 'retry' in result.decision.lower()
            }
            
            return intent
            
        except Exception as e:
            self.logger.warning(f"HRM analysis failed: {e}, using fallback")
            return self._fallback_intent_analysis(context)
    
    def _extract_complexity(self, decision: str) -> str:
        """Extract complexity level from decision text"""
        if any(word in decision.lower() for word in ['simple', 'basic', 'straightforward']):
            return 'low'
        elif any(word in decision.lower() for word in ['complex', 'sophisticated', 'intricate']):
            return 'high'
        return 'medium'
    
    def _fallback_intent_analysis(self, context: PatternSelectionContext) -> Dict[str, Any]:
        """Fallback intent analysis without HRM"""
        query_lower = context.query.lower()
        
        return {
            'decision': 'Fallback analysis',
            'confidence': 0.5,
            'evidence': [],
            'complexity': 'medium',
            'parallelizable': any(word in query_lower for word in ['parallel', 'concurrent', 'simultaneous']),
            'requires_consensus': any(word in query_lower for word in ['consensus', 'agree', 'vote']),
            'requires_coordination': any(word in query_lower for word in ['coordinate', 'sync', 'communicate']),
            'is_iterative': any(word in query_lower for word in ['iterate', 'retry', 'repeat'])
        }
    
    async def _filter_candidates(
        self, 
        context: PatternSelectionContext,
        intent: Dict[str, Any]
    ) -> List[PatternDefinition]:
        """Filter candidate patterns based on context and intent"""
        
        all_patterns = pattern_registry.list_patterns()
        candidates = []
        
        for pattern in all_patterns:
            # Check MCP availability
            if not all(mcp in context.available_mcps for mcp in pattern.required_mcps):
                continue
            
            # Check Docker constraints
            if not self._check_docker_constraints(pattern, context.docker_constraints):
                continue
            
            # Check intent alignment
            if self._aligns_with_intent(pattern, intent):
                candidates.append(pattern)
        
        return candidates
    
    def _check_docker_constraints(
        self, 
        pattern: PatternDefinition,
        constraints: Dict[str, Any]
    ) -> bool:
        """Check if pattern fits within Docker constraints"""
        if not constraints:
            return True
        
        pattern_reqs = pattern.docker_requirements
        
        # Check memory
        if 'memory' in constraints:
            pattern_mem = self._parse_memory(pattern_reqs.get('memory', '0'))
            max_mem = self._parse_memory(constraints['memory'])
            if pattern_mem > max_mem:
                return False
        
        # Check CPU
        if 'cpu' in constraints:
            pattern_cpu = float(pattern_reqs.get('cpu', 0))
            max_cpu = float(constraints['cpu'])
            if pattern_cpu > max_cpu:
                return False
        
        return True
    
    def _parse_memory(self, mem_str: str) -> int:
        """Parse memory string to bytes"""
        if isinstance(mem_str, (int, float)):
            return int(mem_str)
        
        mem_str = mem_str.upper()
        if 'GB' in mem_str:
            return int(float(mem_str.replace('GB', '')) * 1024 * 1024 * 1024)
        elif 'MB' in mem_str:
            return int(float(mem_str.replace('MB', '')) * 1024 * 1024)
        elif 'KB' in mem_str:
            return int(float(mem_str.replace('KB', '')) * 1024)
        
        return int(mem_str)
    
    def _aligns_with_intent(self, pattern: PatternDefinition, intent: Dict[str, Any]) -> bool:
        """Check if pattern aligns with analyzed intent"""
        
        # Category alignment
        if intent['parallelizable'] and pattern.category == PatternCategory.PARALLEL:
            return True
        
        if intent['requires_consensus'] and pattern.category == PatternCategory.CONSENSUS:
            return True
        
        if intent['requires_coordination'] and pattern.category in [
            PatternCategory.MESH, 
            PatternCategory.EVENT_DRIVEN,
            PatternCategory.HIERARCHICAL
        ]:
            return True
        
        if intent['is_iterative'] and pattern.category == PatternCategory.EVENT_DRIVEN:
            return True
        
        # Use case alignment
        query_words = set(intent.get('query', '').lower().split())
        for use_case in pattern.use_cases:
            use_case_words = set(use_case.lower().split())
            if query_words & use_case_words:  # Intersection
                return True
        
        # Default: include if no specific exclusion
        return True
    
    async def _score_patterns(
        self,
        candidates: List[PatternDefinition],
        context: PatternSelectionContext,
        intent: Dict[str, Any]
    ) -> List[Tuple[PatternDefinition, float]]:
        """Score candidate patterns using multiple criteria"""
        
        scored = []
        
        for pattern in candidates:
            score = 0.0
            
            # Performance score
            perf_score = self._calculate_performance_score(pattern, context.performance_requirements)
            score += perf_score * 0.3
            
            # Intent alignment score
            intent_score = self._calculate_intent_score(pattern, intent)
            score += intent_score * 0.3
            
            # Historical performance score
            hist_score = self._calculate_historical_score(pattern, context.historical_performance)
            score += hist_score * 0.2
            
            # Complexity match score
            complexity_score = self._calculate_complexity_score(pattern, intent.get('complexity', 'medium'))
            score += complexity_score * 0.2
            
            scored.append((pattern, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored
    
    def _calculate_performance_score(
        self,
        pattern: PatternDefinition,
        requirements: Dict[str, Any]
    ) -> float:
        """Calculate performance alignment score"""
        if not requirements:
            return 0.5  # Neutral score
        
        score = 0.0
        count = 0
        
        profile = pattern.performance_profile
        
        # Latency requirement
        if 'latency' in requirements:
            req_latency = requirements['latency']
            pattern_latency = profile.get('latency', 'medium')
            
            latency_map = {'very low': 1.0, 'low': 0.8, 'medium': 0.5, 'high': 0.3, 'variable': 0.4}
            score += latency_map.get(pattern_latency, 0.5)
            count += 1
        
        # Throughput requirement
        if 'throughput' in requirements:
            req_throughput = requirements['throughput']
            pattern_throughput = profile.get('throughput', 'medium')
            
            throughput_map = {'very high': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.3}
            score += throughput_map.get(pattern_throughput, 0.5)
            count += 1
        
        return score / count if count > 0 else 0.5
    
    def _calculate_intent_score(self, pattern: PatternDefinition, intent: Dict[str, Any]) -> float:
        """Calculate intent alignment score"""
        score = 0.0
        
        # Category match
        if intent['parallelizable'] and pattern.category == PatternCategory.PARALLEL:
            score += 0.3
        
        if intent['requires_consensus'] and pattern.category == PatternCategory.CONSENSUS:
            score += 0.3
        
        if intent['requires_coordination'] and 'coord' in pattern.pattern_id:
            score += 0.2
        
        if intent['is_iterative'] and 'iterative' in pattern.pattern_id:
            score += 0.2
        
        # Confidence from HRM
        score += intent.get('confidence', 0.5) * 0.2
        
        return min(score, 1.0)
    
    def _calculate_historical_score(
        self,
        pattern: PatternDefinition,
        historical: Dict[str, Any]
    ) -> float:
        """Calculate score based on historical performance"""
        if pattern.pattern_id not in self.performance_metrics:
            return 0.5  # No history
        
        metrics = self.performance_metrics[pattern.pattern_id]
        
        # Average success rate
        success_rate = metrics.get('success_rate', 0.5)
        
        # Average execution time vs expected
        time_ratio = metrics.get('time_ratio', 1.0)  # actual/expected
        time_score = 1.0 / (1.0 + abs(1.0 - time_ratio))  # Best at ratio = 1.0
        
        return (success_rate * 0.7 + time_score * 0.3)
    
    def _calculate_complexity_score(self, pattern: PatternDefinition, complexity: str) -> float:
        """Calculate complexity alignment score"""
        
        # Simple heuristic based on pattern category
        pattern_complexity = {
            PatternCategory.SEQUENTIAL: 'low',
            PatternCategory.PIPELINE: 'low',
            PatternCategory.PARALLEL: 'medium',
            PatternCategory.HIERARCHICAL: 'medium',
            PatternCategory.EVENT_DRIVEN: 'medium',
            PatternCategory.SCATTER_GATHER: 'high',
            PatternCategory.MESH: 'high',
            PatternCategory.CONSENSUS: 'high'
        }
        
        pattern_comp = pattern_complexity.get(pattern.category, 'medium')
        
        if pattern_comp == complexity:
            return 1.0
        elif (pattern_comp == 'low' and complexity == 'medium') or \
             (pattern_comp == 'medium' and complexity in ['low', 'high']) or \
             (pattern_comp == 'high' and complexity == 'medium'):
            return 0.7
        else:
            return 0.4
    
    async def _select_best_pattern(
        self,
        scored_patterns: List[Tuple[PatternDefinition, float]],
        context: PatternSelectionContext
    ) -> PatternRecommendation:
        """Select the best pattern using HRM consensus if needed"""
        
        if not scored_patterns:
            raise ValueError("No suitable patterns found")
        
        best_pattern, best_score = scored_patterns[0]
        
        # Get alternatives
        alternatives = [(p.pattern_id, s) for p, s in scored_patterns[1:4]]  # Top 3 alternatives
        
        # Build reasoning
        reasoning = [
            f"Selected based on query: {context.query}",
            f"Pattern category: {best_pattern.category.value}",
            f"Confidence score: {best_score:.2f}",
            f"Required MCPs: {', '.join(best_pattern.required_mcps)}"
        ]
        
        # Add use cases
        reasoning.append(f"Suitable for: {', '.join(best_pattern.use_cases[:2])}")
        
        # Performance profile
        perf = best_pattern.performance_profile
        reasoning.append(f"Performance: Latency={perf.get('latency')}, Throughput={perf.get('throughput')}")
        
        # Create recommendation
        recommendation = PatternRecommendation(
            pattern_id=best_pattern.pattern_id,
            pattern_name=best_pattern.name,
            confidence=best_score,
            reasoning=reasoning,
            alternative_patterns=alternatives,
            execution_plan={},
            estimated_performance=best_pattern.performance_profile
        )
        
        return recommendation
    
    async def _generate_execution_plan(
        self,
        recommendation: PatternRecommendation,
        context: PatternSelectionContext
    ) -> PatternRecommendation:
        """Generate detailed execution plan for the pattern"""
        
        pattern = pattern_registry.patterns[recommendation.pattern_id]
        
        execution_plan = {
            'pattern_id': recommendation.pattern_id,
            'steps': [],
            'docker_config': pattern.docker_requirements,
            'required_services': pattern.required_mcps,
            'estimated_duration': 'variable',
            'monitoring': {
                'metrics': ['execution_time', 'success_rate', 'resource_usage'],
                'alerts': ['failure', 'timeout', 'resource_exhaustion']
            }
        }
        
        # Pattern-specific execution steps
        if pattern.category == PatternCategory.SEQUENTIAL:
            execution_plan['steps'] = [
                "Initialize required MCP services",
                "Execute tasks sequentially",
                "Collect results",
                "Cleanup resources"
            ]
        elif pattern.category == PatternCategory.PARALLEL:
            execution_plan['steps'] = [
                "Initialize MCP services",
                "Spawn parallel executors",
                "Distribute work",
                "Synchronize results",
                "Aggregate outputs",
                "Cleanup resources"
            ]
        elif pattern.category == PatternCategory.CONSENSUS:
            execution_plan['steps'] = [
                "Initialize consensus participants",
                "Propose action",
                "Collect votes",
                "Determine consensus",
                "Execute decision",
                "Record outcome"
            ]
        else:
            execution_plan['steps'] = [
                "Initialize pattern",
                "Execute main logic",
                "Validate results",
                "Cleanup"
            ]
        
        recommendation.execution_plan = execution_plan
        
        return recommendation
    
    def _record_selection(self, context: PatternSelectionContext, recommendation: PatternRecommendation):
        """Record pattern selection for learning"""
        
        selection = {
            'timestamp': datetime.now().isoformat(),
            'query': context.query,
            'selected_pattern': recommendation.pattern_id,
            'confidence': recommendation.confidence,
            'alternatives': recommendation.alternative_patterns,
            'context': {
                'task_type': context.task_type,
                'available_mcps': context.available_mcps
            }
        }
        
        self.selection_history.append(selection)
        
        # Keep only last 100 selections
        if len(self.selection_history) > 100:
            self.selection_history = self.selection_history[-100:]
    
    async def learn_from_execution(
        self,
        pattern_id: str,
        execution_result: Dict[str, Any]
    ):
        """Learn from pattern execution results"""
        
        if pattern_id not in self.performance_metrics:
            self.performance_metrics[pattern_id] = {
                'executions': 0,
                'successes': 0,
                'failures': 0,
                'total_time': 0,
                'success_rate': 0.5,
                'time_ratio': 1.0
            }
        
        metrics = self.performance_metrics[pattern_id]
        metrics['executions'] += 1
        
        if execution_result.get('success', False):
            metrics['successes'] += 1
        else:
            metrics['failures'] += 1
        
        metrics['success_rate'] = metrics['successes'] / metrics['executions']
        
        # Update time metrics
        if 'execution_time' in execution_result:
            metrics['total_time'] += execution_result['execution_time']
            avg_time = metrics['total_time'] / metrics['executions']
            expected_time = execution_result.get('expected_time', avg_time)
            metrics['time_ratio'] = avg_time / expected_time if expected_time > 0 else 1.0
    
    async def recommend_patterns_for_task(self, task_description: str) -> List[PatternRecommendation]:
        """Recommend multiple patterns for a task"""
        
        # Create context from task description
        context = PatternSelectionContext(
            query=task_description,
            available_mcps=['hrm', 'task', 'coordination', 'workflow_state', 'memory', 'redis']
        )
        
        # Get intent
        intent = await self._analyze_intent(context)
        
        # Get all candidates
        candidates = await self._filter_candidates(context, intent)
        
        # Score them
        scored = await self._score_patterns(candidates, context, intent)
        
        # Create recommendations for top 3
        recommendations = []
        for pattern, score in scored[:3]:
            rec = PatternRecommendation(
                pattern_id=pattern.pattern_id,
                pattern_name=pattern.name,
                confidence=score,
                reasoning=[f"Score: {score:.2f}", f"Category: {pattern.category.value}"],
                alternative_patterns=[],
                execution_plan={},
                estimated_performance=pattern.performance_profile
            )
            recommendations.append(rec)
        
        return recommendations

# Singleton instance
intelligent_selector = IntelligentPatternSelector()

async def select_and_execute_pattern(query: str, **kwargs) -> Dict[str, Any]:
    """
    High-level function to select and execute the best pattern for a query
    """
    
    # Create context
    context = PatternSelectionContext(
        query=query,
        available_mcps=kwargs.get('available_mcps', ['hrm', 'task', 'coordination', 'workflow_state']),
        performance_requirements=kwargs.get('performance_requirements', {}),
        docker_constraints=kwargs.get('docker_constraints', {}),
        user_preferences=kwargs.get('user_preferences', {}),
        metadata=kwargs
    )
    
    # Select pattern
    recommendation = await intelligent_selector.select_pattern(context)
    
    # Get pattern instance
    pattern = pattern_registry.get_pattern(recommendation.pattern_id)
    
    if not pattern:
        raise ValueError(f"Pattern {recommendation.pattern_id} not found")
    
    # Validate prerequisites
    if not await pattern.validate_prerequisites():
        raise RuntimeError(f"Pattern {recommendation.pattern_id} prerequisites not met")
    
    # Execute pattern
    result = await pattern.execute(context.__dict__)
    
    # Learn from execution
    await intelligent_selector.learn_from_execution(
        recommendation.pattern_id,
        {'success': True, 'execution_time': 1.0}  # Would get actual metrics
    )
    
    return {
        'pattern': recommendation.pattern_id,
        'confidence': recommendation.confidence,
        'reasoning': recommendation.reasoning,
        'result': result
    }

if __name__ == "__main__":
    # Test intelligent selection
    async def test():
        # Test various queries
        queries = [
            "Process multiple files in parallel and aggregate results",
            "Reach consensus among multiple agents for critical decision",
            "Execute build pipeline with dependency management",
            "Coordinate microservices using event-driven architecture",
            "Plan project architecture using strategic reasoning"
        ]
        
        for query in queries:
            print(f"\nQuery: {query}")
            print("-" * 50)
            
            context = PatternSelectionContext(
                query=query,
                available_mcps=['hrm', 'task', 'coordination', 'workflow_state']
            )
            
            recommendation = await intelligent_selector.select_pattern(context)
            
            print(f"Selected: {recommendation.pattern_name}")
            print(f"Confidence: {recommendation.confidence:.2f}")
            print("Reasoning:")
            for reason in recommendation.reasoning:
                print(f"  - {reason}")
            
            if recommendation.alternative_patterns:
                print("Alternatives:")
                for alt_id, alt_score in recommendation.alternative_patterns:
                    print(f"  - {alt_id}: {alt_score:.2f}")
    
    asyncio.run(test())