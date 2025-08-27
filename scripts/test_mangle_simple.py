#!/usr/bin/env python3
"""
Simple test for Mangle integration without full CLI dependencies
"""

import subprocess
import tempfile
import os

def test_mangle_interpreter():
    """Test if Mangle interpreter is available"""
    print("Testing Mangle Interpreter Installation...")
    
    # Check if mg command is available
    result = subprocess.run(["which", "mg"], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Mangle interpreter found at: {result.stdout.strip()}")
        return result.stdout.strip()
    else:
        print("✗ Mangle interpreter (mg) not found")
        print("  To install: go install github.com/google/mangle/interpreter/mg@latest")
        
        # Check if it exists in the submodule
        submodule_path = "libs/mangle/interpreter/mg/mg"
        if os.path.exists(submodule_path):
            print(f"  Found in submodule at: {submodule_path}")
            print("  Building from source...")
            
            # Try to build it
            build_result = subprocess.run(
                ["go", "build", "-o", "mg", "."],
                cwd="libs/mangle/interpreter/mg",
                capture_output=True,
                text=True
            )
            
            if build_result.returncode == 0:
                print("  ✓ Successfully built Mangle interpreter")
                return os.path.abspath("libs/mangle/interpreter/mg/mg")
            else:
                print(f"  ✗ Failed to build: {build_result.stderr}")
        
        return None

def test_simple_mangle_query(mg_path):
    """Test a simple Mangle query"""
    print("\nTesting Simple Mangle Query...")
    
    # Create a simple Mangle program
    mangle_code = """
    # Simple test facts and rules
    Agent(name string, type string).
    Task(id string, agent string, duration int).
    
    # Facts
    Agent("research-bot", "analyzer").
    Agent("test-bot", "validator").
    Agent("deploy-bot", "orchestrator").
    
    Task("task1", "research-bot", 3000).
    Task("task2", "test-bot", 5500).
    Task("task3", "deploy-bot", 2000).
    
    # Rules
    SlowTask(id, agent) :- Task(id, agent, duration), duration > 5000.
    FastTask(id, agent) :- Task(id, agent, duration), duration < 3000.
    
    # Queries
    ?SlowTask(id, agent)
    ?FastTask(id, agent)
    ?Agent(name, type)
    """
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mg', delete=False) as f:
        f.write(mangle_code)
        temp_file = f.name
    
    try:
        # Execute Mangle
        result = subprocess.run(
            [mg_path, temp_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("  ✓ Mangle query executed successfully")
            print("\n  Results:")
            
            # Parse output
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    print(f"    • {line}")
        else:
            print(f"  ✗ Mangle execution failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("  ✗ Mangle query timed out")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    finally:
        # Clean up
        try:
            os.unlink(temp_file)
        except:
            pass

def test_agent_analysis_rules(mg_path):
    """Test agent performance analysis rules"""
    print("\nTesting Agent Performance Analysis Rules...")
    
    mangle_code = """
    # Agent performance analysis
    AgentExecution(agent string, task string, duration_ms int, success bool).
    
    # Test data
    AgentExecution("codebase-analyst", "scan_files", 3500, true).
    AgentExecution("security-validator", "check_vulnerabilities", 8500, true).
    AgentExecution("test-runner", "run_tests", 12000, false).
    AgentExecution("deploy-bot", "deploy_service", 6000, true).
    AgentExecution("monitor", "check_health", 500, true).
    
    # Analysis rules
    SlowExecution(agent, task) :- 
        AgentExecution(agent, task, duration, true),
        duration > 5000.
    
    FailedExecution(agent, task) :-
        AgentExecution(agent, task, _, false).
    
    FastExecution(agent, task) :-
        AgentExecution(agent, task, duration, true),
        duration < 1000.
    
    BottleneckAgent(agent) :-
        AgentExecution(agent, _, duration, _),
        duration > 10000.
    
    ReliableAgent(agent) :-
        AgentExecution(agent, _, _, true),
        !AgentExecution(agent, _, _, false).
    
    # Queries
    ?SlowExecution(agent, task)
    ?FailedExecution(agent, task)
    ?FastExecution(agent, task)
    ?BottleneckAgent(agent)
    ?ReliableAgent(agent)
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mg', delete=False) as f:
        f.write(mangle_code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            [mg_path, temp_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("  ✓ Agent analysis rules executed successfully")
            
            # Parse and categorize results
            lines = result.stdout.strip().split('\n')
            categories = {
                'SlowExecution': [],
                'FailedExecution': [],
                'FastExecution': [],
                'BottleneckAgent': [],
                'ReliableAgent': []
            }
            
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    for category in categories:
                        if line.startswith(category):
                            categories[category].append(line)
            
            # Display categorized results
            print("\n  Analysis Results:")
            for category, results in categories.items():
                if results:
                    print(f"\n    {category}:")
                    for result in results:
                        print(f"      • {result}")
        else:
            print(f"  ✗ Analysis failed: {result.stderr}")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
    finally:
        try:
            os.unlink(temp_file)
        except:
            pass

if __name__ == "__main__":
    print("=" * 60)
    print("Google Mangle Integration - Simple Test Suite")
    print("=" * 60)
    
    # Test Mangle interpreter
    mg_path = test_mangle_interpreter()
    
    if mg_path:
        # Run tests
        test_simple_mangle_query(mg_path)
        test_agent_analysis_rules(mg_path)
        
        print("\n" + "=" * 60)
        print("✅ Mangle integration testing completed!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  Mangle interpreter not available")
        print("Please install with: go install github.com/google/mangle/interpreter/mg@latest")
        print("=" * 60)