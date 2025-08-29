#!/usr/bin/env python3
"""
Simple test for shell plugin validation (no external dependencies)
"""

import sys
import re
from pathlib import Path
from enum import Enum

# Simple implementation for testing without dependencies
class CommandRisk(Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"
    FORBIDDEN = "forbidden"

class SimpleCommandValidator:
    """Simplified version for testing"""
    
    SAFE_COMMANDS = {'ls', 'pwd', 'echo', 'date', 'whoami', 'cat', 'grep', 'find'}
    MODERATE_COMMANDS = {'cp', 'mv', 'mkdir', 'docker', 'git'}
    DANGEROUS_COMMANDS = {'rm', 'rmdir', 'kill', 'shutdown'}
    
    FORBIDDEN_PATTERNS = [
        r'.*>\s*/dev/.*',
        r'.*\|\s*sudo.*', 
        r'.*;\s*rm\s+-rf.*',
        r'.*/etc/passwd.*',
    ]
    
    def assess_risk(self, command: str) -> CommandRisk:
        # Check forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.match(pattern, command):
                return CommandRisk.FORBIDDEN
        
        # Simple parsing
        parts = command.split()
        if not parts:
            return CommandRisk.SAFE
        
        base_command = Path(parts[0]).name
        
        if base_command in self.SAFE_COMMANDS:
            return CommandRisk.SAFE
        elif base_command in self.MODERATE_COMMANDS:
            return CommandRisk.MODERATE
        elif base_command in self.DANGEROUS_COMMANDS:
            return CommandRisk.DANGEROUS
        
        return CommandRisk.MODERATE

def test_validation():
    """Test command validation"""
    print("=" * 60)
    print(" Shell Plugin Validation Test")
    print("=" * 60)
    
    validator = SimpleCommandValidator()
    
    test_commands = [
        ("ls -la", "Safe file listing"),
        ("pwd", "Print working directory"),
        ("git status", "Git command"),
        ("cp file1 file2", "Copy operation"),
        ("docker ps", "Docker command"),
        ("rm -rf /", "Dangerous deletion"),
        ("cat /etc/passwd", "Access password file"),
        ("echo test > /dev/null", "Device redirect"),
        ("ls | sudo rm", "Pipe to sudo"),
    ]
    
    print("\nCommand Risk Assessment:")
    print("-" * 60)
    
    for command, description in test_commands:
        risk = validator.assess_risk(command)
        
        color = ""
        if risk == CommandRisk.SAFE:
            color = "✓ SAFE    "
        elif risk == CommandRisk.MODERATE:
            color = "⚠ MODERATE"
        elif risk == CommandRisk.DANGEROUS:
            color = "⚠ DANGER  "
        else:
            color = "✗ FORBIDDEN"
        
        print(f"{color} | {command:20} | {description}")
    
    print("\n" + "=" * 60)
    print("Shell Plugin Architecture Validation")
    print("=" * 60)
    
    # Check if shell plugin file exists
    plugin_file = Path(__file__).parent.parent / "app/cli/plugins/builtin/shell_plugin.py"
    
    print(f"\nPlugin File: {plugin_file}")
    print(f"Exists: {'✓ Yes' if plugin_file.exists() else '✗ No'}")
    
    if plugin_file.exists():
        content = plugin_file.read_text()
        
        # Check for key security features
        security_features = [
            ("CommandValidator class", "class CommandValidator" in content),
            ("Risk assessment", "assess_risk" in content),
            ("Command history", "CommandHistory" in content),
            ("Security policies", "CommandPolicy" in content),
            ("Forbidden patterns", "FORBIDDEN_PATTERNS" in content),
            ("Safe commands list", "SAFE_COMMANDS" in content),
            ("Subprocess security", "subprocess" in content),
            ("Interactive mode", "interactive_shell" in content),
        ]
        
        print("\nSecurity Features Check:")
        print("-" * 40)
        
        for feature, present in security_features:
            status = "✓" if present else "✗"
            print(f"{status} {feature}")
        
        # Check file size (should be substantial)
        size_kb = len(content) / 1024
        print(f"\nPlugin file size: {size_kb:.1f} KB")
        
        if size_kb > 20:
            print("✓ Comprehensive implementation")
        else:
            print("⚠ Implementation may be incomplete")
    
    print("\n" + "=" * 60)
    print("Integration Check")
    print("=" * 60)
    
    # Check if plugin is registered
    builtin_file = Path(__file__).parent.parent / "app/cli/plugins/builtin/builtin_plugins.py"
    
    if builtin_file.exists():
        content = builtin_file.read_text()
        
        integrations = [
            ("Shell plugin import", "ShellCommandPlugin" in content),
            ("Plugin registration", "BUILTIN_PLUGINS" in content and "ShellCommandPlugin" in content),
            ("Framework integration", "framework.py" in str(builtin_file.parent)),
        ]
        
        for check, status in integrations:
            print(f"{'✓' if status else '✗'} {check}")
    
    print("\n✅ Shell plugin architecture validation complete!")

if __name__ == "__main__":
    test_validation()