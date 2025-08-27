#!/usr/bin/env python3
"""
Test MCP and Tools Integration for LocalAgent CLI
Verifies that agents can access all tools and MCP services
"""

import asyncio
import sys
import json
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.cli.mcp_integration import MCPIntegration, AgentToolAccess


def test_mcp_services():
    """Test MCP services availability"""
    print("=" * 60)
    print("Testing MCP Services Integration")
    print("=" * 60)
    
    mcp = MCPIntegration()
    
    print("\n1. Available MCP Services:")
    services = ['coordination', 'hrm', 'task', 'workflow_state']
    for service in services:
        if service in mcp.services:
            print(f"  ✓ {service}: Active")
        else:
            print(f"  ✗ {service}: Not available")
    
    print(f"\nTotal services: {len(mcp.services)}/{len(services)}")
    return mcp


def test_available_tools(mcp):
    """Test available tools"""
    print("\n" + "=" * 60)
    print("Testing Available Tools")
    print("=" * 60)
    
    # Get tools by category
    categories = {}
    for tool in mcp.tools.values():
        if tool.category not in categories:
            categories[tool.category] = []
        categories[tool.category].append(tool)
    
    print("\nTools by Category:")
    for category, tools in sorted(categories.items()):
        print(f"\n  [{category}] - {len(tools)} tools:")
        for tool in tools[:3]:  # Show first 3 tools per category
            print(f"    • {tool.name}: {tool.description}")
        if len(tools) > 3:
            print(f"    ... and {len(tools) - 3} more")
    
    print(f"\nTotal tools available: {len(mcp.tools)}")
    return categories


def test_agent_permissions(mcp):
    """Test agent permissions for tools"""
    print("\n" + "=" * 60)
    print("Testing Agent Permissions")
    print("=" * 60)
    
    agent_access = AgentToolAccess(mcp)
    
    # Test different agent types
    test_agents = [
        'codebase-research-analyst',
        'security-validator',
        'deployment-orchestrator',
        'test-automation-engineer'
    ]
    
    print("\nAgent Tool Access:")
    for agent in test_agents:
        available = agent_access.get_available_tools_for_agent(agent)
        print(f"\n  {agent}:")
        print(f"    • Can access: {len(available)} tools")
        
        # Check specific permissions
        critical_tools = ['read_file', 'write_file', 'execute_command', 'delete_path']
        for tool in critical_tools:
            can_use = agent_access.can_use_tool(agent, tool)
            status = "✓" if can_use else "✗"
            print(f"    {status} {tool}")
    
    return agent_access


async def test_file_operations(mcp, agent_access):
    """Test file operations through agent access"""
    print("\n" + "=" * 60)
    print("Testing File Operations")
    print("=" * 60)
    
    test_dir = Path("/tmp/localagent_mcp_test")
    test_file = test_dir / "test.txt"
    
    agent = "codebase-research-analyst"
    print(f"\nTesting as agent: {agent}")
    
    results = []
    
    try:
        # Test 1: Create directory
        print("\n1. Creating directory...")
        try:
            result = await agent_access.invoke_tool_as_agent(
                agent, 'create_directory', path=str(test_dir)
            )
            print(f"   ✓ Directory created: {test_dir}")
            results.append(("Create Directory", True))
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            results.append(("Create Directory", False))
        
        # Test 2: Write file
        print("\n2. Writing file...")
        try:
            content = "Test content from MCP integration test"
            result = await agent_access.invoke_tool_as_agent(
                agent, 'write_file', 
                path=str(test_file),
                content=content
            )
            print(f"   ✓ File written: {test_file}")
            results.append(("Write File", True))
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            results.append(("Write File", False))
        
        # Test 3: Read file
        print("\n3. Reading file...")
        try:
            read_content = await agent_access.invoke_tool_as_agent(
                agent, 'read_file', path=str(test_file)
            )
            if "Test content" in read_content:
                print(f"   ✓ File read successfully")
                results.append(("Read File", True))
            else:
                print(f"   ✗ Content mismatch")
                results.append(("Read File", False))
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            results.append(("Read File", False))
        
        # Test 4: List directory
        print("\n4. Listing directory...")
        try:
            files = await agent_access.invoke_tool_as_agent(
                agent, 'list_directory', path=str(test_dir)
            )
            if 'test.txt' in files:
                print(f"   ✓ Directory listed: {files}")
                results.append(("List Directory", True))
            else:
                print(f"   ✗ File not found in listing")
                results.append(("List Directory", False))
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            results.append(("List Directory", False))
        
        # Test 5: Permission check - try to delete as security-validator (should fail)
        print("\n5. Testing permission denial...")
        security_agent = "security-validator"
        try:
            await agent_access.invoke_tool_as_agent(
                security_agent, 'delete_path', path=str(test_file)
            )
            print(f"   ✗ Security agent shouldn't be able to delete!")
            results.append(("Permission Check", False))
        except PermissionError:
            print(f"   ✓ Permission correctly denied for {security_agent}")
            results.append(("Permission Check", True))
        
        # Test 6: Delete with proper agent
        print("\n6. Cleaning up...")
        deploy_agent = "deployment-orchestrator"
        try:
            await agent_access.invoke_tool_as_agent(
                deploy_agent, 'delete_path', path=str(test_file)
            )
            await agent_access.invoke_tool_as_agent(
                deploy_agent, 'delete_path', path=str(test_dir), recursive=True
            )
            print(f"   ✓ Cleanup completed")
            results.append(("Cleanup", True))
        except Exception as e:
            print(f"   ✗ Cleanup failed: {e}")
            results.append(("Cleanup", False))
            
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    
    return results


async def test_system_tools(mcp, agent_access):
    """Test system tools access"""
    print("\n" + "=" * 60)
    print("Testing System Tools")
    print("=" * 60)
    
    agent = "deployment-orchestrator"
    print(f"\nTesting as agent: {agent}")
    
    # Test environment variables
    print("\n1. Getting environment variables...")
    try:
        env = await agent_access.invoke_tool_as_agent(
            agent, 'get_environment', key='PATH'
        )
        if env:
            print(f"   ✓ PATH variable retrieved (length: {len(env)})")
        else:
            print(f"   ✗ No PATH variable found")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    # Test command execution
    print("\n2. Executing system command...")
    try:
        result = await agent_access.invoke_tool_as_agent(
            agent, 'execute_command', command='echo "Hello from LocalAgent CLI"'
        )
        if result.get('stdout'):
            print(f"   ✓ Command executed: {result['stdout'].strip()}")
        else:
            print(f"   ✗ No output from command")
    except Exception as e:
        print(f"   ✗ Failed: {e}")


def print_summary(file_results):
    """Print test summary"""
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if file_results:
        passed = sum(1 for _, success in file_results if success)
        total = len(file_results)
        
        print("\nFile Operation Tests:")
        for test_name, success in file_results:
            status = "✓ Passed" if success else "✗ Failed"
            print(f"  {status}: {test_name}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n✅ All tests passed successfully!")
        else:
            print(f"\n⚠️  Some tests failed ({total - passed} failures)")
    else:
        print("\n⚠️  No test results available")


async def main():
    """Main test runner"""
    print("\n" + "🚀 LocalAgent CLI - MCP & Tools Integration Test Suite")
    print("=" * 60)
    
    # Test MCP services
    mcp = test_mcp_services()
    
    # Test available tools
    categories = test_available_tools(mcp)
    
    # Test agent permissions
    agent_access = test_agent_permissions(mcp)
    
    # Test file operations
    file_results = await test_file_operations(mcp, agent_access)
    
    # Test system tools
    await test_system_tools(mcp, agent_access)
    
    # Print summary
    print_summary(file_results)
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())