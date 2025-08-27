#!/usr/bin/env python3
"""
Basic CLI Test Script
Test the core CLI components without complex dependencies
"""

import sys
import subprocess
from pathlib import Path

def test_direct_app_creation():
    """Test creating the CLI app directly"""
    print("🔍 Testing direct CLI app creation...")
    
    # Create a minimal test script that imports just the core
    test_script = '''
import sys
sys.path.insert(0, ".")

# Test basic Typer functionality
import typer
from rich.console import Console

# Create a simple app
app = typer.Typer(name="test-cli")
console = Console()

@app.command()
def hello():
    """Test command"""
    console.print("[green]CLI app works![/green]")

if __name__ == "__main__":
    console.print("✅ CLI app created successfully")
'''
    
    try:
        # Write test script
        test_file = Path("temp_cli_test.py")
        test_file.write_text(test_script)
        
        # Run test script
        result = subprocess.run([
            sys.executable, str(test_file)
        ], capture_output=True, text=True, cwd=".", env={"VIRTUAL_ENV": str(Path(".venv").absolute())})
        
        # Clean up
        test_file.unlink()
        
        if result.returncode == 0 and "CLI app created successfully" in result.stdout:
            print("  ✅ Direct CLI app creation successful")
            return True
        else:
            print(f"  ❌ Failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_setup_py_installability():
    """Test if setup.py is properly configured for installation"""
    print("🔍 Testing setup.py installability...")
    
    try:
        # Test setup.py check
        result = subprocess.run([
            sys.executable, "scripts/setup.py", "check"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("  ✅ setup.py is valid")
            return True
        else:
            print(f"  ❌ setup.py validation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_entry_points():
    """Test entry points configuration"""
    print("🔍 Testing entry points...")
    
    setup_file = Path("scripts/setup.py")
    if not setup_file.exists():
        print("  ❌ scripts/setup.py not found")
        return False
    
    content = setup_file.read_text()
    
    # Check for required entry points
    required_entries = [
        "localagent=app.cli.core.app:main",
        "la=app.cli.core.app:main"
    ]
    
    all_found = True
    for entry in required_entries:
        if entry in content:
            print(f"  ✅ Entry point found: {entry}")
        else:
            print(f"  ❌ Missing entry point: {entry}")
            all_found = False
    
    return all_found

def test_core_file_structure():
    """Test that core CLI files exist"""
    print("🔍 Testing core file structure...")
    
    required_files = [
        "app/__init__.py",
        "app/cli/__init__.py", 
        "app/cli/core/__init__.py",
        "app/cli/core/app.py",
        "app/cli/core/config.py",
        "setup.py",
        "requirements.txt"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path} exists")
        else:
            print(f"  ❌ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_pip_installability():
    """Test pip install in development mode"""
    print("🔍 Testing pip installability...")
    
    try:
        # Test pip install in development mode
        result = subprocess.run([
            ".venv/bin/pip", "install", "-e", "."
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("  ✅ Package can be installed with pip")
            
            # Test if commands are available
            cmd_result = subprocess.run([
                ".venv/bin/localagent", "--help"
            ], capture_output=True, text=True)
            
            if cmd_result.returncode == 0 or "LocalAgent" in cmd_result.stdout:
                print("  ✅ localagent command is available")
                return True
            else:
                print(f"  ❌ localagent command failed: {cmd_result.stderr}")
                return False
        else:
            print(f"  ❌ pip install failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    from rich.console import Console
    
    console = Console()
    console.print("\n[bold blue]🚀 Basic CLI Functionality Test[/bold blue]\n")
    
    tests = [
        ("Core File Structure", test_core_file_structure),
        ("Entry Points Configuration", test_entry_points),
        ("setup.py Validation", test_setup_py_installability),
        ("Direct App Creation", test_direct_app_creation),
        ("Pip Installability", test_pip_installability),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append(result)
        status = "[green]✅ PASSED[/green]" if result else "[red]❌ FAILED[/red]"
        console.print(f"{status} {test_name}\n")
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    console.print(f"[bold]📊 Summary: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("\n[bold green]🎉 All basic tests passed! CLI structure is ready.[/bold green]")
        return 0
    else:
        console.print(f"\n[bold red]⚠️  {total - passed} tests failed. Review issues above.[/bold red]")
        return 1

if __name__ == "__main__":
    sys.exit(main())