#!/usr/bin/env python3
"""Fix aioredis TimeoutError duplicate base class issue for Python 3.11+"""

import sys
import os

def fix_aioredis_timeout_error():
    """Fix the duplicate base class TimeoutError in aioredis for Python 3.11+"""
    
    # Find the aioredis exceptions file
    aioredis_path = None
    for path in sys.path:
        potential_path = os.path.join(path, 'aioredis', 'exceptions.py')
        if os.path.exists(potential_path):
            aioredis_path = potential_path
            break
    
    if not aioredis_path:
        print("aioredis not found in Python path")
        return False
    
    print(f"Found aioredis at: {aioredis_path}")
    
    # Read the file
    with open(aioredis_path, 'r') as f:
        content = f.read()
    
    # Check Python version
    if sys.version_info >= (3, 11):
        # For Python 3.11+, asyncio.TimeoutError already inherits from builtins.TimeoutError
        # So we only need to inherit from asyncio.TimeoutError and RedisError
        old_line = "class TimeoutError(asyncio.TimeoutError, builtins.TimeoutError, RedisError):"
        new_line = "class TimeoutError(asyncio.TimeoutError, RedisError):"
    else:
        # For older Python versions, keep the original
        print("Python version < 3.11, no fix needed")
        return True
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        
        # Write the fixed content back
        with open(aioredis_path, 'w') as f:
            f.write(content)
        
        print(f"Fixed TimeoutError in {aioredis_path}")
        return True
    elif new_line in content:
        print("TimeoutError already fixed")
        return True
    else:
        print("Unexpected TimeoutError definition in aioredis")
        return False

if __name__ == "__main__":
    success = fix_aioredis_timeout_error()
    sys.exit(0 if success else 1)