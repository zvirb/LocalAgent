#!/usr/bin/env python3
"""
CLI Validation Script
Simple validation of LocalAgent CLI components and integration
"""

import sys
import traceback
from pathlib import Path

def test_basic_imports():
    """Test basic module imports"""
    print("🔍 Testing basic imports...")
    
    try:
        # Test core imports
        import typer
        print("  ✅ typer imported successfully")
        
        import rich
        from rich.console import Console
        print("  ✅ rich imported successfully")
        
        import pydantic
        print("  ✅ pydantic imported successfully")
        
        import yaml
        print("  ✅ pyyaml imported successfully")
        
        import aiofiles
        print("  ✅ aiofiles imported successfully")
        
        import keyring
        print("  ✅ keyring imported successfully")
        
        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_cli_structure():
    """Test CLI module structure"""
    print("🔍 Testing CLI module structure...")
    
    try:
        # Test if CLI modules exist
        import app
        print("  ✅ app module exists")
        
        import app.cli
        print("  ✅ app.cli module exists")
        
        import app.cli.core
        print("  ✅ app.cli.core module exists")
        
        # Test configuration module
        from app.cli.core.config import LocalAgentConfig, ProviderConfig
        print("  ✅ Configuration classes imported")
        
        # Test basic config creation
        config = LocalAgentConfig()
        print(f"  ✅ LocalAgentConfig created: {config.default_provider}")
        
        return True
    except ImportError as e:
        print(f"  ❌ CLI structure error: {e}")
        traceback.print_exc()
        return False

def test_typer_app_creation():
    """Test Typer app creation"""
    print("🔍 Testing Typer app creation...")
    
    try:
        # Create a simple typer app to test the framework
        import typer
        from rich.console import Console
        
        test_app = typer.Typer(name="test-app")
        console = Console()
        
        @test_app.command()
        def hello():
            """Test command"""
            console.print("Hello from test CLI!")
        
        print("  ✅ Typer app created successfully")
        return True
    except Exception as e:
        print(f"  ❌ Typer app creation error: {e}")
        traceback.print_exc()
        return False

def test_setup_py_structure():
    """Test setup.py configuration"""
    print("🔍 Testing setup.py structure...")
    
    setup_file = Path("scripts/setup.py")
    if not setup_file.exists():
        print("  ❌ scripts/setup.py not found")
        return False
    
    try:
        # Read scripts/setup.py content
        setup_content = setup_file.read_text()
        
        # Check for essential components
        checks = [
            ("name", "localagent-cli" in setup_content),
            ("version", "version=" in setup_content),
            ("entry_points", "entry_points=" in setup_content),
            ("console_scripts", "console_scripts" in setup_content),
            ("localagent command", "localagent=app.cli.core.app:main" in setup_content)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            if check_result:
                print(f"  ✅ {check_name} found")
            else:
                print(f"  ❌ {check_name} missing")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"  ❌ scripts/setup.py validation error: {e}")
        return False

def test_requirements():
    """Test requirements.txt"""
    print("🔍 Testing requirements.txt...")
    
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("  ❌ requirements.txt not found")
        return False
    
    try:
        requirements = req_file.read_text()
        
        # Check for essential packages
        essential_packages = [
            "typer", "rich", "pydantic", "pyyaml", 
            "aiofiles", "keyring", "click"
        ]
        
        all_found = True
        for package in essential_packages:
            if package in requirements:
                print(f"  ✅ {package} found in requirements")
            else:
                print(f"  ❌ {package} missing from requirements")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"  ❌ requirements.txt validation error: {e}")
        return False

def main():
    """Run all validation tests"""
    console = None
    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        pass
    
    if console:
        console.print("\n[bold blue]🚀 LocalAgent CLI Validation[/bold blue]\n")
    else:
        print("\n🚀 LocalAgent CLI Validation\n")
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("CLI Structure", test_cli_structure),
        ("Typer App Creation", test_typer_app_creation),
        ("setup.py Configuration", test_setup_py_structure),
        ("requirements.txt", test_requirements),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
            if console:
                status = "[green]✅ PASSED[/green]" if result else "[red]❌ FAILED[/red]"
                console.print(f"{status} {test_name}\n")
            else:
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"{status} {test_name}\n")
        except Exception as e:
            results.append(False)
            if console:
                console.print(f"[red]❌ FAILED[/red] {test_name}: {e}\n")
            else:
                print(f"❌ FAILED {test_name}: {e}\n")
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    if console:
        console.print(f"[bold]📊 Summary: {passed}/{total} tests passed[/bold]")
        
        if passed == total:
            console.print("\n[bold green]🎉 All tests passed! CLI is ready.[/bold green]")
            return 0
        else:
            console.print(f"\n[bold red]⚠️  {total - passed} tests failed. Review issues above.[/bold red]")
            return 1
    else:
        print(f"📊 Summary: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed! CLI is ready.")
            return 0
        else:
            print(f"\n⚠️  {total - passed} tests failed. Review issues above.")
            return 1

if __name__ == "__main__":
    sys.exit(main())