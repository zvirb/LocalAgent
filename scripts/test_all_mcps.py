#!/usr/bin/env python3
"""
Comprehensive test of all MCP servers implemented for LocalAgent
Tests: HRM, Task, Coordination, and Workflow State MCPs
"""

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

async def test_all_mcps():
    """Test all MCP servers"""
    print("=" * 70)
    print("LocalAgent MCP Servers Comprehensive Test")
    print("=" * 70)
    
    success_count = 0
    total_tests = 4
    
    # 1. Test HRM MCP
    print("\n1. Testing HRM MCP (Hierarchical Reasoning Model)")
    print("-" * 50)
    try:
        from mcp.hrm_mcp import create_hrm_server
        
        hrm = await create_hrm_server({'state_file': '.test_hrm.json'})
        
        # Test reasoning
        result = await hrm.reason(
            "Implement user authentication with JWT tokens",
            context={'project_type': 'python'},
            level=0
        )
        
        explanation = await hrm.explain_reasoning(result.node_id)
        print(f"✓ HRM Reasoning: {result.decision}")
        print(f"  Confidence: {result.confidence:.2%}")
        print(f"  Children: {len(result.children)} sub-decisions")
        
        await hrm.save_state()
        success_count += 1
        print("✅ HRM MCP: PASSED")
    except Exception as e:
        print(f"❌ HRM MCP: FAILED - {e}")
    
    # 2. Test Task MCP
    print("\n2. Testing Task MCP (Task Management)")
    print("-" * 50)
    try:
        from mcp.task_mcp import create_task_server
        
        task_mcp = await create_task_server({'state_file': '.test_tasks.json'})
        
        # Create tasks
        task1 = await task_mcp.create_task(
            "Implement JWT authentication",
            "Add JWT-based authentication to the API",
            priority="high"
        )
        
        task2 = await task_mcp.create_task(
            "Write unit tests for auth",
            "Test the authentication system",
            priority="medium",
            dependencies=[task1.task_id]
        )
        
        # List tasks
        tasks = await task_mcp.list_tasks()
        print(f"✓ Created {len(tasks)} tasks")
        
        # Update task status
        await task_mcp.update_task(task1.task_id, status="in_progress")
        
        # Analyze workload
        analysis = await task_mcp.analyze_workload()
        print(f"✓ Workload Analysis:")
        print(f"  Total tasks: {analysis['total_tasks']}")
        print(f"  Status distribution: {analysis['status_distribution']}")
        print(f"  Completion rate: {analysis['completion_rate']}%")
        
        await task_mcp.save_state()
        success_count += 1
        print("✅ Task MCP: PASSED")
    except Exception as e:
        print(f"❌ Task MCP: FAILED - {e}")
    
    # 3. Test Coordination MCP
    print("\n3. Testing Coordination MCP (Agent Coordination)")
    print("-" * 50)
    try:
        from mcp.coordination_mcp import create_coordination_server
        
        coord = await create_coordination_server({'state_file': '.test_coord.json'})
        
        # Register agents
        agent1 = await coord.register_agent(
            "test_agent_001",
            "research",
            capabilities=["search", "analysis"]
        )
        
        agent2 = await coord.register_agent(
            "test_agent_002",
            "implementation",
            capabilities=["coding", "testing"]
        )
        
        print(f"✓ Registered 2 agents")
        
        # Send message
        msg_id = await coord.send_message(
            "test_agent_001",
            "test_agent_002",
            "task_request",
            {"task": "Implement authentication module"}
        )
        print(f"✓ Sent message: {msg_id}")
        
        # Create workflow stream
        stream = await coord.create_stream(
            "Authentication Implementation",
            agents=["test_agent_001", "test_agent_002"],
            shared_context={"project": "LocalAgent"}
        )
        print(f"✓ Created stream: {stream.stream_id}")
        
        # Get coordination stats
        stats = await coord.get_coordination_stats()
        print(f"✓ Coordination Stats:")
        print(f"  Active agents: {stats['active_agents']}")
        print(f"  Pending messages: {stats['pending_messages']}")
        print(f"  Active streams: {stats['active_streams']}")
        
        await coord.save_state()
        success_count += 1
        print("✅ Coordination MCP: PASSED")
    except Exception as e:
        print(f"❌ Coordination MCP: FAILED - {e}")
    
    # 4. Test Workflow State MCP
    print("\n4. Testing Workflow State MCP (Workflow Tracking)")
    print("-" * 50)
    try:
        from mcp.workflow_state_mcp import create_workflow_state_server
        
        workflow_state = await create_workflow_state_server({'state_file': '.test_workflow.json'})
        
        # Create workflow execution
        execution = await workflow_state.create_execution(
            "Authentication System Implementation",
            context={"project": "LocalAgent", "priority": "high"}
        )
        print(f"✓ Created execution: {execution.execution_id}")
        
        # Start and complete phases
        phase1 = await workflow_state.start_phase(
            execution.execution_id,
            "0A_prompt_engineering"
        )
        
        await workflow_state.add_evidence(
            execution.execution_id,
            "0A_prompt_engineering",
            "user_approval",
            "User approved: Implement JWT authentication"
        )
        
        await workflow_state.complete_phase(
            execution.execution_id,
            "0A_prompt_engineering",
            evidence=[{"type": "confirmation", "data": "Requirements clarified"}]
        )
        
        # Start research phase
        phase2 = await workflow_state.start_phase(
            execution.execution_id,
            "1_research_discovery"
        )
        
        await workflow_state.complete_phase(
            execution.execution_id,
            "1_research_discovery",
            evidence=[{"type": "research", "data": "JWT best practices collected"}]
        )
        
        # Get progress
        progress = await workflow_state.get_execution_progress(execution.execution_id)
        print(f"✓ Workflow Progress:")
        print(f"  Status: {progress['status']}")
        print(f"  Progress: {progress['progress_percentage']}%")
        print(f"  Phases completed: {progress['phases_completed']}/{progress['total_phases']}")
        
        await workflow_state.save_state()
        success_count += 1
        print("✅ Workflow State MCP: PASSED")
    except Exception as e:
        print(f"❌ Workflow State MCP: FAILED - {e}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    print(f"Passed: {success_count}/{total_tests}")
    print(f"Success Rate: {(success_count/total_tests*100):.0f}%")
    
    if success_count == total_tests:
        print("\n🎉 All MCP servers are working correctly!")
        print("\nAvailable MCP Servers:")
        print("1. HRM MCP - Hierarchical reasoning and decision-making")
        print("2. Task MCP - Task management and tracking")
        print("3. Coordination MCP - Agent coordination and messaging")
        print("4. Workflow State MCP - Workflow execution tracking")
        print("\nThese MCPs are now integrated into the enhanced CLI.")
        print("Run 'clix' and type 'init' to initialize all features.")
    else:
        print(f"\n⚠️ {total_tests - success_count} MCP server(s) failed tests.")
        print("Please check the error messages above.")
    
    return success_count == total_tests

if __name__ == "__main__":
    success = asyncio.run(test_all_mcps())
    sys.exit(0 if success else 1)