#!/usr/bin/env python3
"""
Test script for Mangle integration with LocalAgent CLI
"""

import json
from pathlib import Path
from app.cli.mangle_integration import MangleIntegration, MangleAgentAnalyzer

def test_basic_mangle_integration():
    """Test basic Mangle functionality"""
    print("Testing Mangle Integration...")
    
    # Initialize Mangle
    mangle = MangleIntegration()
    print(f"✓ Mangle initialized with interpreter at: {mangle.mangle_path}")
    
    # Test agent performance analysis
    print("\n1. Testing Agent Performance Analysis...")
    
    execution_data = [
        {
            'agent_name': 'codebase-research-analyst',
            'task_id': 'task_1',
            'duration_ms': 3500,
            'success': True,
            'timestamp': 1000
        },
        {
            'agent_name': 'security-validator',
            'task_id': 'task_2',
            'duration_ms': 8500,
            'success': True,
            'timestamp': 4500
        },
        {
            'agent_name': 'test-automation-engineer',
            'task_id': 'task_3',
            'duration_ms': 12000,
            'success': False,
            'timestamp': 13000
        },
        {
            'agent_name': 'deployment-orchestrator',
            'task_id': 'task_4',
            'duration_ms': 6000,
            'success': True,
            'timestamp': 25000
        }
    ]
    
    result = mangle.analyze_agent_performance(execution_data)
    
    if result.success:
        print("  ✓ Performance analysis completed")
        print(f"  Found {len(result.facts)} analysis facts")
        
        # Display some results
        slow_agents = [f for f in result.facts if f['predicate'] == 'SlowExecution']
        bottlenecks = [f for f in result.facts if f['predicate'] == 'BottleneckAgent']
        
        if slow_agents:
            print(f"  - Slow agents detected: {len(slow_agents)}")
            for fact in slow_agents[:3]:
                print(f"    • {fact['arguments'][0]} on {fact['arguments'][1]}")
        
        if bottlenecks:
            print(f"  - Bottleneck agents: {len(bottlenecks)}")
            for fact in bottlenecks:
                print(f"    • {fact['arguments'][0]}")
    else:
        print(f"  ✗ Analysis failed: {result.error}")
    
    # Test workflow optimization
    print("\n2. Testing Workflow Optimization Analysis...")
    
    workflow_data = {
        'phases': [
            {'id': 'phase_0', 'name': 'Interactive Prompt Engineering', 'order': 0},
            {'id': 'phase_1', 'name': 'Parallel Research', 'order': 1},
            {'id': 'phase_2', 'name': 'Strategic Planning', 'order': 2},
            {'id': 'phase_3', 'name': 'Context Creation', 'order': 3},
            {'id': 'phase_4', 'name': 'Parallel Execution', 'order': 4}
        ],
        'executions': [
            {'phase_id': 'phase_0', 'start_time': 0, 'end_time': 5000, 'success': True},
            {'phase_id': 'phase_1', 'start_time': 5000, 'end_time': 45000, 'success': True},
            {'phase_id': 'phase_2', 'start_time': 45000, 'end_time': 55000, 'success': True},
            {'phase_id': 'phase_3', 'start_time': 55000, 'end_time': 60000, 'success': True},
            {'phase_id': 'phase_4', 'start_time': 60000, 'end_time': 120000, 'success': True}
        ],
        'resources': [
            {'phase_id': 'phase_1', 'cpu_percent': 85.5, 'memory_mb': 2500, 'io_ops': 1000},
            {'phase_id': 'phase_4', 'cpu_percent': 92.0, 'memory_mb': 3000, 'io_ops': 5000}
        ]
    }
    
    result = mangle.analyze_workflow_optimization(workflow_data)
    
    if result.success:
        print("  ✓ Workflow optimization analysis completed")
        
        slow_phases = [f for f in result.facts if f['predicate'] == 'SlowPhase']
        resource_intensive = [f for f in result.facts if f['predicate'] == 'ResourceIntensive']
        optimizations = [f for f in result.facts if f['predicate'] == 'OptimizationCandidate']
        
        if slow_phases:
            print(f"  - Slow phases detected: {len(slow_phases)}")
            for fact in slow_phases:
                print(f"    • {fact['arguments'][0]}")
        
        if resource_intensive:
            print(f"  - Resource-intensive phases: {len(resource_intensive)}")
            for fact in resource_intensive:
                print(f"    • {fact['arguments'][0]}")
        
        if optimizations:
            print(f"  - Optimization candidates: {len(optimizations)}")
            for fact in optimizations:
                print(f"    • {fact['arguments'][0]}: {fact['arguments'][1]}")
    else:
        print(f"  ✗ Workflow analysis failed: {result.error}")
    
    # Test agent analyzer
    print("\n3. Testing Agent Chain Analysis...")
    
    analyzer = MangleAgentAnalyzer(mangle)
    
    agents = ['research-agent', 'planning-agent', 'implementation-agent', 'testing-agent']
    execution_times = {
        'research-agent': 2.5,
        'planning-agent': 1.8,
        'implementation-agent': 5.2,
        'testing-agent': 3.1
    }
    
    insights = analyzer.analyze_agent_chain(agents, execution_times)
    
    print("  ✓ Agent chain analysis completed")
    print(f"  - Slow agents: {len(insights['slow_agents'])}")
    print(f"  - Bottlenecks: {len(insights['bottlenecks'])}")
    print(f"  - Parallelization opportunities: {len(insights['parallel_opportunities'])}")
    print(f"  - Optimization score: {insights['optimization_score']:.1%}")
    
    # Test agent suggestions
    print("\n4. Testing Agent Composition Suggestions...")
    
    available_agents = [
        'codebase-research-analyst',
        'security-validator',
        'test-automation-engineer',
        'deployment-orchestrator',
        'monitoring-analyst'
    ]
    
    for task_type in ['debug', 'implement', 'deploy']:
        suggested = analyzer.suggest_agent_composition(task_type, available_agents)
        print(f"  - {task_type}: {' → '.join(suggested) if suggested else 'No suggestions'}")
    
    print("\n✅ All Mangle integration tests completed!")

def test_custom_mangle_rules():
    """Test custom Mangle rules"""
    print("\n5. Testing Custom Mangle Rules...")
    
    mangle = MangleIntegration()
    
    # Simple custom rules for testing
    rules = """
    # Test rules
    Task(id string, name string, priority int).
    Dependency(task1 string, task2 string).
    
    HighPriority(task) :- Task(task, _, priority), priority > 7.
    HasDependency(task) :- Dependency(task, _).
    """
    
    facts = [
        'Task("t1", "Research", 9).',
        'Task("t2", "Planning", 5).',
        'Task("t3", "Implementation", 8).',
        'Dependency("t3", "t2").',
        'Dependency("t2", "t1").'
    ]
    
    queries = ['HighPriority(task)', 'HasDependency(task)']
    
    result = mangle.custom_query(rules, facts, queries)
    
    if result.success:
        print("  ✓ Custom query executed successfully")
        print(f"  - High priority tasks: {sum(1 for f in result.facts if f['predicate'] == 'HighPriority')}")
        print(f"  - Tasks with dependencies: {sum(1 for f in result.facts if f['predicate'] == 'HasDependency')}")
    else:
        print(f"  ✗ Custom query failed: {result.error}")

if __name__ == "__main__":
    print("=" * 60)
    print("LocalAgent CLI - Google Mangle Integration Test Suite")
    print("=" * 60)
    
    try:
        test_basic_mangle_integration()
        test_custom_mangle_rules()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()