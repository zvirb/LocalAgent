#!/usr/bin/env python3
"""Test script for HRM integration in CLI"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def test_hrm():
    """Test HRM MCP integration"""
    from mcp.hrm_mcp import create_hrm_server
    
    # Initialize HRM server
    hrm = await create_hrm_server({'state_file': '.hrm_state_test.json'})
    print("✓ HRM MCP initialized")
    
    # Test strategic reasoning
    result = await hrm.reason(
        "Fix the authentication bug in the login system",
        context={'project_type': 'python'},
        level=0
    )
    
    explanation = await hrm.explain_reasoning(result.node_id)
    print("\n" + "="*50)
    print("HRM Reasoning Result:")
    print("="*50)
    print(explanation)
    
    # Show confidence metrics
    metrics = await hrm.get_confidence_metrics()
    print("\n" + "="*50)
    print("Confidence Metrics:")
    print("="*50)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    
    # Save state
    await hrm.save_state()
    print("\n✓ HRM state saved")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_hrm())
    if success:
        print("\n✓ HRM integration test completed successfully!")
    else:
        print("\n✗ HRM integration test failed")
        sys.exit(1)