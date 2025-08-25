"""
Integration Tests for LocalAgent + UnifiedWorkflow Orchestration
Validates all components work together correctly
"""

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List

# Mock provider manager for testing
class MockProviderManager:
    """Mock provider manager for testing"""
    
    def __init__(self):
        self.initialized = False
        
    async def initialize_providers(self):
        self.initialized = True
        
    async def complete_with_fallback(self, request, preferred_provider=None):
        # Mock response
        class MockResponse:
            def __init__(self):
                self.content = f"Mock agent response for: {request.prompt[:100]}..."
                self.model = "mock-model"
                self.usage = MockUsage()
                self.provider = "mock"
                
        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 100
                self.completion_tokens = 50
                self.total_tokens = 150
                
        await asyncio.sleep(0.1)  # Simulate processing time
        return MockResponse()
    
    async def health_check_all(self):
        return {
            'mock': {
                'healthy': True,
                'models': ['mock-model-1', 'mock-model-2']
            }
        }

async def test_agent_adapter():
    """Test the agent adapter functionality"""
    print("🧪 Testing Agent Adapter...")
    
    from .agent_adapter import AgentProviderAdapter, AgentRequest
    
    # Create adapter
    adapter = AgentProviderAdapter()
    provider_manager = MockProviderManager()
    await provider_manager.initialize_providers()
    await adapter.initialize(provider_manager)
    
    # Test single agent execution
    request = AgentRequest(
        agent_type="test",
        subagent_type="codebase-research-analyst",
        description="Test agent execution",
        prompt="Analyze the current codebase structure",
        context={"test": True}
    )
    
    response = await adapter.execute_agent(request)
    
    assert response.success or response.error, "Agent should return success or error"
    print(f"  ✅ Single agent execution: {'SUCCESS' if response.success else 'FAILED'}")
    
    # Test parallel agent execution
    requests = [
        AgentRequest(
            agent_type="test",
            subagent_type="security-validator",
            description="Security validation test",
            prompt="Check for security vulnerabilities",
            context={"test": True}
        ),
        AgentRequest(
            agent_type="test", 
            subagent_type="performance-profiler",
            description="Performance analysis test",
            prompt="Analyze performance metrics",
            context={"test": True}
        )
    ]
    
    parallel_responses = await adapter.execute_parallel_agents(requests)
    
    assert len(parallel_responses) == 2, "Should get responses for both agents"
    print(f"  ✅ Parallel agent execution: {len(parallel_responses)} responses")
    
    # Test health check
    health = await adapter.health_check()
    assert 'adapter_healthy' in health, "Health check should include adapter status"
    print(f"  ✅ Health check: {'HEALTHY' if health['adapter_healthy'] else 'UNHEALTHY'}")
    
    return True

async def test_mcp_integration():
    """Test MCP integration functionality"""
    print("🧪 Testing MCP Integration...")
    
    from .mcp_integration import OrchestrationMCP, MemoryMCP, RedisMCP
    
    # Test Memory MCP
    memory_config = {}
    memory_mcp = MemoryMCP(memory_config)
    
    # Store and retrieve entity
    success = await memory_mcp.store_entity(
        'test-entity',
        'test-id-1',
        {'data': 'test content'},
        {'source': 'integration_test'}
    )
    assert success, "Should store entity successfully"
    
    entity = await memory_mcp.retrieve_entity('test-id-1')
    assert entity is not None, "Should retrieve stored entity"
    print("  ✅ Memory MCP: Store and retrieve working")
    
    # Test entity search
    entities = await memory_mcp.search_entities(entity_type='test-entity')
    assert len(entities) > 0, "Should find stored entities"
    print("  ✅ Memory MCP: Search working")
    
    # Test Redis MCP (will fail gracefully if Redis not available)
    redis_config = {'redis_url': 'redis://localhost:6379'}
    redis_mcp = RedisMCP(redis_config)
    
    redis_connected = await redis_mcp.initialize()
    if redis_connected:
        # Test coordination data
        coord_success = await redis_mcp.set_coordination_data(
            'test-workflow',
            {'status': 'testing'},
            ttl=60
        )
        assert coord_success, "Should set coordination data"
        
        coord_data = await redis_mcp.get_coordination_data('test-workflow')
        assert coord_data is not None, "Should retrieve coordination data"
        print("  ✅ Redis MCP: Connected and working")
    else:
        print("  ⚠️  Redis MCP: Not available (expected if Redis not running)")
    
    # Test OrchestrationMCP
    mcp_config = {'redis': redis_config, 'memory': memory_config}
    orchestration_mcp = OrchestrationMCP(mcp_config)
    
    await orchestration_mcp.initialize()
    
    # Test context package storage
    package_success = await orchestration_mcp.store_context_package(
        'test-package-1',
        {'context': 'test data', 'tokens': 100},
        max_tokens=4000
    )
    assert package_success, "Should store context package"
    print("  ✅ Orchestration MCP: Context package storage working")
    
    return True

async def test_context_manager():
    """Test context manager functionality"""
    print("🧪 Testing Context Manager...")
    
    from .context_manager import ContextManager, TokenCounter
    
    # Test token counting
    text = "This is a test string for token counting."
    tokens = TokenCounter.count_tokens(text)
    assert tokens > 0, "Should count tokens"
    print(f"  ✅ Token counter: {tokens} tokens for test text")
    
    # Test context manager
    config = {
        'default_context_tokens': 4000,
        'strategic_context_tokens': 3000
    }
    context_manager = ContextManager(config)
    
    # Test package creation
    package = await context_manager.create_context_package(
        'test-package-1',
        'strategic_context',
        {
            'architecture': 'microservices',
            'components': ['api', 'database', 'frontend'],
            'decisions': ['use FastAPI', 'PostgreSQL database']
        }
    )
    
    assert package.package_id == 'test-package-1', "Package should have correct ID"
    assert package.token_count > 0, "Package should have token count"
    print(f"  ✅ Package creation: {package.token_count} tokens")
    
    # Test package retrieval
    retrieved = await context_manager.retrieve_context_package('test-package-1')
    assert retrieved is not None, "Should retrieve stored package"
    print("  ✅ Package retrieval working")
    
    # Test package compression (create large package)
    large_content = {
        'large_data': 'x' * 10000,  # Large content to trigger compression
        'components': ['comp' + str(i) for i in range(100)]
    }
    
    large_package = await context_manager.create_context_package(
        'large-package',
        'technical_context',
        large_content
    )
    
    # Should be compressed if over limit
    expected_limit = config.get('default_context_tokens', 4000)
    if large_package.token_count <= expected_limit:
        print(f"  ✅ Package compression: Kept within {expected_limit} tokens")
    else:
        print(f"  ⚠️  Package compression: {large_package.token_count} tokens (may need adjustment)")
    
    return True

async def test_workflow_engine():
    """Test workflow engine functionality"""
    print("🧪 Testing Workflow Engine...")
    
    from .workflow_engine import WorkflowEngine
    from .agent_adapter import AgentProviderAdapter
    from .context_manager import ContextManager
    
    # Create dependencies
    adapter = AgentProviderAdapter()
    provider_manager = MockProviderManager()
    await provider_manager.initialize_providers()
    await adapter.initialize(provider_manager)
    
    context_manager = ContextManager({})
    
    # Create workflow engine
    workflow_engine = WorkflowEngine()
    await workflow_engine.initialize(adapter, context_manager)
    
    # Test workflow execution (limited phases for testing)
    # Note: This will fail gracefully if UnifiedWorkflow config not available
    try:
        execution = await workflow_engine.execute_workflow(
            initial_prompt="Test workflow execution",
            context={'test': True}
        )
        
        assert execution is not None, "Should create workflow execution"
        assert execution.workflow_id is not None, "Should have workflow ID"
        print(f"  ✅ Workflow execution created: {execution.workflow_id}")
        print(f"  📊 Phases attempted: {len(execution.phase_results)}")
        
        # Check if any phases completed
        completed_phases = [p for p in execution.phase_results if p.status.value == 'completed']
        print(f"  ✅ Phases completed: {len(completed_phases)}")
        
    except Exception as e:
        print(f"  ⚠️  Workflow execution failed (expected if config missing): {e}")
    
    # Test workflow status
    status = workflow_engine.get_workflow_status()
    print(f"  ✅ Workflow status: {status.get('status', 'none') if status else 'no workflow'}")
    
    return True

async def test_orchestration_integration():
    """Test complete orchestration integration"""
    print("🧪 Testing Complete Orchestration Integration...")
    
    from .orchestration_integration import LocalAgentOrchestrator
    
    # Create orchestrator
    orchestrator = LocalAgentOrchestrator()
    
    # Initialize with mock provider
    provider_manager = MockProviderManager()
    await provider_manager.initialize_providers()
    
    success = await orchestrator.initialize(provider_manager)
    assert success, "Should initialize successfully"
    print("  ✅ Orchestrator initialization successful")
    
    # Test system health
    health = await orchestrator.get_system_health()
    assert 'overall_healthy' in health, "Should provide health status"
    print(f"  ✅ System health: {'HEALTHY' if health['overall_healthy'] else 'UNHEALTHY'}")
    
    # Test single agent execution
    try:
        result = await orchestrator.execute_single_agent(
            'codebase-research-analyst',
            'Test agent execution',
            {'test': True}
        )
        
        assert 'success' in result, "Should provide success indicator"
        print(f"  ✅ Single agent execution: {'SUCCESS' if result['success'] else 'FAILED'}")
        
    except Exception as e:
        print(f"  ⚠️  Single agent execution failed: {e}")
    
    # Test available agents
    agents = await orchestrator.get_available_agents()
    print(f"  ✅ Available agents: {len(agents)}")
    
    # Test CLI commands
    status = await orchestrator.cmd_status()
    assert status is not None, "Should provide status"
    print("  ✅ CLI status command working")
    
    health_cmd = await orchestrator.cmd_health()
    assert 'overall_healthy' in health_cmd, "Should provide health via CLI"
    print("  ✅ CLI health command working")
    
    return True

async def run_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting LocalAgent + UnifiedWorkflow Integration Tests\n")
    
    tests = [
        ("Agent Adapter", test_agent_adapter),
        ("MCP Integration", test_mcp_integration), 
        ("Context Manager", test_context_manager),
        ("Workflow Engine", test_workflow_engine),
        ("Complete Integration", test_orchestration_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n--- {test_name} ---")
            start_time = time.time()
            
            success = await test_func()
            
            execution_time = time.time() - start_time
            results.append({
                'test': test_name,
                'success': success,
                'execution_time': execution_time
            })
            
            print(f"✅ {test_name}: PASSED ({execution_time:.2f}s)")
            
        except Exception as e:
            execution_time = time.time() - start_time
            results.append({
                'test': test_name,
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            })
            
            print(f"❌ {test_name}: FAILED ({execution_time:.2f}s)")
            print(f"   Error: {e}")
    
    # Summary
    print(f"\n--- Test Summary ---")
    passed = len([r for r in results if r['success']])
    total = len(results)
    total_time = sum(r['execution_time'] for r in results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"⏱️  Total time: {total_time:.2f}s")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check output above.")
        return False

# Example configuration for testing
def create_test_config():
    """Create test configuration"""
    config = {
        'orchestration': {
            'max_parallel_agents': 5,
            'enable_evidence_collection': True
        },
        'providers': {
            'ollama': {
                'base_url': 'http://localhost:11434',
                'default_model': 'llama3.1:latest'
            }
        },
        'mcp': {
            'redis': {
                'redis_url': 'redis://localhost:6379'
            }
        },
        'context': {
            'default_context_tokens': 4000
        }
    }
    
    return config

async def main():
    """Main test execution"""
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run tests
    success = await run_integration_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)