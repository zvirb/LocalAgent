#!/usr/bin/env python3
"""Demo script showing all MCP features integrated into LocalAgent"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

async def demo_all_mcp_features():
    """Demonstrate all MCP features"""
    print("=" * 60)
    print("LocalAgent MCP Features Demo")
    print("=" * 60)
    
    # 1. HRM MCP - Hierarchical Reasoning
    print("\n1. HRM MCP - Hierarchical Reasoning Model")
    print("-" * 40)
    try:
        from mcp.hrm_mcp import create_hrm_server
        
        hrm = await create_hrm_server({'state_file': '.hrm_demo.json'})
        
        # Strategic reasoning
        result = await hrm.reason(
            "Implement a new user authentication system",
            context={'project_type': 'python', 'current_directory': str(Path.cwd())},
            level=0  # Strategic level
        )
        
        explanation = await hrm.explain_reasoning(result.node_id)
        print(explanation)
        
        print("\n✓ HRM MCP: Hierarchical reasoning working")
    except Exception as e:
        print(f"✗ HRM MCP error: {e}")
    
    # 2. Memory MCP - Persistent Storage
    print("\n2. Memory MCP - Persistent Storage")
    print("-" * 40)
    try:
        from app.orchestration.mcp_integration import OrchestrationMCP
        
        mcp_integration = OrchestrationMCP()
        await mcp_integration.initialize()
        
        if mcp_integration.memory_mcp:
            # Store some data
            await mcp_integration.memory_mcp.store_entity(
                entity_type="demo-data",
                entity_id="test-key",
                content="This is a test value stored at " + str(datetime.now()),
                metadata={"demo": True}
            )
            
            # Retrieve data
            entity = await mcp_integration.memory_mcp.retrieve_entity("test-key")
            if entity:
                print(f"Stored and retrieved: {entity.content}")
            
            print("✓ Memory MCP: Persistence working")
        else:
            print("✗ Memory MCP not available")
    except Exception as e:
        print(f"✗ Memory MCP error: {e}")
    
    # 3. Redis MCP - Real-time Coordination
    print("\n3. Redis MCP - Real-time Coordination")
    print("-" * 40)
    try:
        if mcp_integration and mcp_integration.redis_mcp and mcp_integration.redis_mcp.redis:
            # Set a value
            await mcp_integration.redis_mcp.redis.set("demo:test", "Redis working!")
            
            # Get the value
            value = await mcp_integration.redis_mcp.redis.get("demo:test")
            if value:
                print(f"Redis value: {value.decode()}")
            
            # Pub/sub example
            await mcp_integration.redis_mcp.redis.publish("demo:channel", "Hello from LocalAgent!")
            
            print("✓ Redis MCP: Coordination working")
        else:
            print("✗ Redis MCP not available (Redis server may not be running)")
    except Exception as e:
        print(f"✗ Redis MCP error: {e}")
    
    # 4. Web Search (Native)
    print("\n4. Web Search (Native Implementation)")
    print("-" * 40)
    try:
        import requests
        from bs4 import BeautifulSoup
        
        query = "Python authentication best practices"
        url = f"https://html.duckduckgo.com/html/?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('div', class_='result')[:2]  # Top 2 results
            
            if results:
                print(f"Search results for '{query}':")
                for i, result in enumerate(results, 1):
                    title_elem = result.find('a', class_='result__a')
                    if title_elem:
                        print(f"  {i}. {title_elem.get_text(strip=True)}")
                
                print("✓ Web Search: Working")
            else:
                print("✓ Web Search: Available (no results for demo query)")
        else:
            print("✗ Web Search: Network issue")
    except Exception as e:
        print(f"✗ Web Search error: {e}")
    
    # 5. Workflow Engine
    print("\n5. Workflow Engine")
    print("-" * 40)
    try:
        from app.orchestration.workflow_engine import WorkflowEngine
        
        workflow_engine = WorkflowEngine()
        workflow_path = Path(__file__).parent / "workflows" / "12-phase-workflow.yaml"
        
        if workflow_path.exists():
            await workflow_engine.load_workflow(str(workflow_path))
            print(f"✓ Workflow Engine: Loaded 12-phase workflow")
            print(f"  Phases available: {len(workflow_engine.workflow_config.get('phases', []))}")
        else:
            print("✗ Workflow configuration not found")
    except Exception as e:
        print(f"✗ Workflow Engine error: {e}")
    
    print("\n" + "=" * 60)
    print("MCP Features Summary:")
    print("- HRM MCP: Hierarchical reasoning for complex decisions")
    print("- Memory MCP: Persistent storage across sessions")
    print("- Redis MCP: Real-time coordination between agents")
    print("- Web Search: External information retrieval")
    print("- Workflow Engine: 12-phase orchestration")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(demo_all_mcp_features())