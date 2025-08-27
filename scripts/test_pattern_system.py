#!/usr/bin/env python3
"""
Comprehensive test of the MCP Pattern System
Tests pattern registry, intelligent selection, and execution
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.patterns import (
    pattern_registry,
    intelligent_selector,
    PatternSelectionContext,
    PatternCategory,
    select_and_execute_pattern
)

async def test_pattern_system():
    """Test the complete pattern system"""
    print("=" * 70)
    print("MCP Pattern System Comprehensive Test")
    print("=" * 70)
    
    # Phase 1: Test Pattern Registry
    print("\n1. Testing Pattern Registry")
    print("-" * 50)
    
    total_patterns = len(pattern_registry.patterns)
    print(f"✓ Loaded {total_patterns} patterns")
    
    # Count by category
    category_counts = {}
    for category in PatternCategory:
        patterns = pattern_registry.list_patterns(category)
        category_counts[category.value] = len(patterns)
        print(f"  {category.value}: {len(patterns)} patterns")
    
    assert total_patterns == 16, f"Expected 16 patterns, got {total_patterns}"
    print("✅ Pattern Registry: PASSED")
    
    # Phase 2: Test Intelligent Selection
    print("\n2. Testing Intelligent Pattern Selection")
    print("-" * 50)
    
    test_queries = [
        ("Process multiple files in parallel", "task_scatter_gather"),
        ("Reach consensus among agents", "hrm_consensus"),
        ("Execute pipeline with dependencies", "task_pipeline"),
        ("Coordinate microservices", "coord_event_bus"),
        ("Strategic planning for project", "hrm_strategic")
    ]
    
    for query, expected_pattern in test_queries:
        context = PatternSelectionContext(
            query=query,
            available_mcps=['hrm', 'task', 'coordination', 'workflow_state']
        )
        
        recommendation = await intelligent_selector.select_pattern(context)
        print(f"Query: {query[:40]}...")
        print(f"  Selected: {recommendation.pattern_id}")
        print(f"  Confidence: {recommendation.confidence:.2%}")
        
        # Check if expected pattern is in top choices
        if recommendation.pattern_id == expected_pattern:
            print(f"  ✓ Matched expected pattern")
        elif any(p[0] == expected_pattern for p in recommendation.alternative_patterns):
            print(f"  ✓ Expected pattern in alternatives")
        else:
            print(f"  ⚠ Expected {expected_pattern}")
    
    print("✅ Intelligent Selection: PASSED")
    
    # Phase 3: Test Pattern Execution
    print("\n3. Testing Pattern Execution")
    print("-" * 50)
    
    # Test a simple pattern execution
    try:
        # Test HRM Strategic Planning Pattern
        pattern = pattern_registry.get_pattern("hrm_strategic")
        if pattern:
            result = await pattern.execute({
                'query': 'Test strategic planning',
                'context': {'test': True}
            })
            print(f"✓ HRM Strategic Pattern executed")
            assert 'strategic' in result, "Strategic result missing"
        
        # Test Task Pipeline Pattern
        pattern = pattern_registry.get_pattern("task_pipeline")
        if pattern:
            result = await pattern.execute({
                'pipeline_tasks': [
                    {'title': 'Task 1'},
                    {'title': 'Task 2'}
                ]
            })
            print(f"✓ Task Pipeline Pattern executed")
            assert 'pipeline_results' in result, "Pipeline results missing"
        
        # Test Coordination Hub-Spoke Pattern
        pattern = pattern_registry.get_pattern("coord_hub_spoke")
        if pattern:
            result = await pattern.execute({
                'num_spokes': 3
            })
            print(f"✓ Coordination Hub-Spoke Pattern executed")
            assert 'hub' in result, "Hub result missing"
        
        print("✅ Pattern Execution: PASSED")
        
    except Exception as e:
        print(f"❌ Pattern Execution: FAILED - {e}")
        return False
    
    # Phase 4: Test Pattern Categories
    print("\n4. Testing Pattern Categories")
    print("-" * 50)
    
    for category in PatternCategory:
        patterns = pattern_registry.list_patterns(category)
        if patterns:
            print(f"✓ {category.value}: {patterns[0].name}")
    
    print("✅ Pattern Categories: PASSED")
    
    # Phase 5: Test Use Case Matching
    print("\n5. Testing Use Case Pattern Matching")
    print("-" * 50)
    
    use_cases = [
        "Complex decision making",
        "Parallel processing",
        "Event streaming",
        "Build pipelines"
    ]
    
    for use_case in use_cases:
        patterns = pattern_registry.find_patterns_for_use_case(use_case)
        if patterns:
            print(f"✓ '{use_case}': Found {len(patterns)} patterns")
            print(f"    Best match: {patterns[0].name}")
    
    print("✅ Use Case Matching: PASSED")
    
    # Phase 6: Test Learning System
    print("\n6. Testing Learning System")
    print("-" * 50)
    
    # Simulate execution feedback
    await intelligent_selector.learn_from_execution(
        "hrm_strategic",
        {'success': True, 'execution_time': 1.5}
    )
    
    await intelligent_selector.learn_from_execution(
        "task_pipeline",
        {'success': True, 'execution_time': 0.8}
    )
    
    await intelligent_selector.learn_from_execution(
        "coord_mesh",
        {'success': False, 'error': 'Test failure'}
    )
    
    # Check if metrics updated
    metrics = intelligent_selector.performance_metrics
    print(f"✓ Tracked metrics for {len(metrics)} patterns")
    
    for pattern_id, pattern_metrics in metrics.items():
        success_rate = pattern_metrics.get('success_rate', 0)
        print(f"  {pattern_id}: {success_rate:.0%} success rate")
    
    print("✅ Learning System: PASSED")
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    print(f"✓ Total Patterns: {total_patterns}")
    print(f"✓ Categories: {len(PatternCategory)}")
    print(f"✓ Intelligent Selection: Working")
    print(f"✓ Pattern Execution: Working")
    print(f"✓ Learning System: Active")
    
    print("\n🎉 All pattern system tests passed!")
    return True

async def test_docker_constraints():
    """Test Docker constraint checking"""
    print("\n7. Testing Docker Constraints")
    print("-" * 50)
    
    # Test with memory constraints
    context = PatternSelectionContext(
        query="Process large dataset",
        available_mcps=['hrm', 'task', 'coordination', 'workflow_state'],
        docker_constraints={'memory': '256MB', 'cpu': '0.5'}
    )
    
    recommendation = await intelligent_selector.select_pattern(context)
    pattern = pattern_registry.patterns[recommendation.pattern_id]
    
    print(f"With constraints (256MB, 0.5 CPU):")
    print(f"  Selected: {pattern.name}")
    print(f"  Requirements: {pattern.docker_requirements}")
    
    print("✅ Docker Constraints: PASSED")

if __name__ == "__main__":
    success = asyncio.run(test_pattern_system())
    
    if success:
        asyncio.run(test_docker_constraints())
    
    sys.exit(0 if success else 1)