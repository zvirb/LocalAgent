#!/usr/bin/env python3
"""
Test script for the secure shell command plugin
"""

import asyncio
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.cli.plugins.builtin.shell_plugin import ShellCommandPlugin, CommandPolicy, CommandValidator


async def test_command_validation():
    """Test command validation and risk assessment"""
    print("\n=== Testing Command Validation ===\n")
    
    policy = CommandPolicy()
    validator = CommandValidator(policy)
    
    test_commands = [
        ("ls -la", "Safe command"),
        ("pwd", "Safe command"),
        ("git status", "Safe command"),
        ("cp file1 file2", "Moderate command"),
        ("docker ps", "Moderate command"),
        ("rm -rf /", "Dangerous command"),
        ("sudo rm -rf /*", "Forbidden command"),
        ("cat /etc/passwd", "Forbidden pattern"),
        ("echo test > /dev/null", "Redirect command"),
        ("ls | grep test", "Pipe command"),
    ]
    
    for command, description in test_commands:
        risk = validator.assess_risk(command)
        valid, message = validator.validate_command(command)
        
        print(f"Command: {command}")
        print(f"  Description: {description}")
        print(f"  Risk Level: {risk.value}")
        print(f"  Valid: {valid}")
        print(f"  Message: {message}")
        print()


async def test_command_execution():
    """Test actual command execution"""
    print("\n=== Testing Command Execution ===\n")
    
    plugin = ShellCommandPlugin()
    
    # Test safe commands
    safe_commands = [
        "echo 'Hello from LocalAgent Shell Plugin!'",
        "pwd",
        "date",
        "ls -la | head -5"  # This will fail if pipes not allowed
    ]
    
    for cmd in safe_commands:
        print(f"\nExecuting: {cmd}")
        result = await plugin.execute_command(cmd, safe_mode=True, timeout=5)
        
        if result['success']:
            print(f"✓ Success: {result.get('stdout', '').strip()}")
        else:
            print(f"✗ Failed: {result.get('error', 'Unknown error')}")
        
        if result.get('execution_time'):
            print(f"  Time: {result['execution_time']:.2f}s")


async def test_security_policies():
    """Test security policy configurations"""
    print("\n=== Testing Security Policies ===\n")
    
    # Test with strict policy
    strict_policy = CommandPolicy(
        allow_shell=False,
        allow_pipes=False,
        allow_redirects=False,
        allow_sudo=False,
        sandbox_mode=True
    )
    
    validator = CommandValidator(strict_policy)
    
    print("Strict Policy Tests:")
    strict_tests = [
        "ls | grep test",
        "echo test > file.txt",
        "sudo ls",
        "rm file.txt"
    ]
    
    for cmd in strict_tests:
        risk = validator.assess_risk(cmd)
        valid, message = validator.validate_command(cmd)
        print(f"  {cmd}: Risk={risk.value}, Valid={valid}")
    
    # Test with relaxed policy
    relaxed_policy = CommandPolicy(
        allow_shell=True,
        allow_pipes=True,
        allow_redirects=True,
        allow_sudo=False,
        sandbox_mode=False,
        require_confirmation=False
    )
    
    validator = CommandValidator(relaxed_policy)
    
    print("\nRelaxed Policy Tests:")
    for cmd in strict_tests:
        risk = validator.assess_risk(cmd)
        valid, message = validator.validate_command(cmd)
        print(f"  {cmd}: Risk={risk.value}, Valid={valid}")


async def test_interactive_features():
    """Test interactive shell features"""
    print("\n=== Testing Interactive Features ===\n")
    
    plugin = ShellCommandPlugin()
    
    # Test command history
    print("Testing command history...")
    
    # Execute some commands to build history
    test_commands = [
        "echo 'Test 1'",
        "echo 'Test 2'",
        "pwd"
    ]
    
    for cmd in test_commands:
        await plugin.execute_command(cmd, safe_mode=True)
    
    # Get recent history
    recent = plugin.history.get_recent(5)
    print(f"Recent commands in history: {len(recent)}")
    for entry in recent:
        print(f"  - {entry['command']} ({entry['result'].get('success', False)})")
    
    # Test directory change
    print("\nTesting directory change...")
    original_dir = plugin.current_directory
    plugin.change_directory("/tmp")
    print(f"  Changed from {original_dir} to {plugin.current_directory}")
    plugin.change_directory(str(original_dir))
    print(f"  Changed back to {plugin.current_directory}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print(" LocalAgent Shell Plugin Test Suite")
    print("=" * 60)
    
    await test_command_validation()
    await test_command_execution()
    await test_security_policies()
    await test_interactive_features()
    
    print("\n" + "=" * 60)
    print(" All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())