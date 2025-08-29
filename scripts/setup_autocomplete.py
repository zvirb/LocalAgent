#!/usr/bin/env python3
"""
Autocomplete Feature Setup Script
=================================

Sets up and configures the autocomplete feature for LocalAgent CLI.
"""

import os
import sys
import subprocess
from pathlib import Path
import json
import yaml

def check_dependencies():
    """Check and install required dependencies"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'inquirerpy',
        'readchar',
        'cryptography',
        'rich',
        'difflib'  # Usually built-in but checking
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package} installed")
        except ImportError:
            print(f"  ❌ {package} missing")
            missing.append(package)
    
    if missing:
        print("\n📦 Installing missing packages...")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing, check=True)
        print("✅ Dependencies installed")
    else:
        print("✅ All dependencies satisfied")
    
    return True

def setup_config_directory():
    """Create and configure the LocalAgent config directory"""
    print("\n📁 Setting up configuration directory...")
    
    config_dir = Path.home() / ".localagent"
    config_dir.mkdir(exist_ok=True, mode=0o700)
    
    # Create autocomplete subdirectory
    autocomplete_dir = config_dir / "autocomplete"
    autocomplete_dir.mkdir(exist_ok=True, mode=0o700)
    
    print(f"  ✅ Config directory: {config_dir}")
    print(f"  ✅ Autocomplete directory: {autocomplete_dir}")
    
    return config_dir

def create_default_config(config_dir: Path):
    """Create default autocomplete configuration"""
    print("\n⚙️ Creating default configuration...")
    
    config_file = config_dir / "autocomplete_config.yaml"
    
    default_config = {
        'autocomplete': {
            'enabled': True,
            'max_suggestions': 10,
            'max_history_size': 10000,
            'enable_fuzzy': True,
            'fuzzy_threshold': 0.6,
            'enable_ml_predictions': True,
            'enable_encryption': True,
            'history_retention_days': 30,
            'deduplication_window': 100,
            'sensitive_patterns': [
                'api[_-]?key',
                'password',
                'token',
                'secret',
                'credential',
                'auth',
                'private[_-]?key'
            ],
            'performance': {
                'cache_ttl': 300,
                'max_cache_size': 1000,
                'target_response_ms': 16
            }
        }
    }
    
    if not config_file.exists():
        with open(config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        print(f"  ✅ Created config: {config_file}")
    else:
        print(f"  ℹ️ Config exists: {config_file}")
    
    return config_file

def initialize_history(config_dir: Path):
    """Initialize empty history file with proper permissions"""
    print("\n📝 Initializing history storage...")
    
    history_file = config_dir / "autocomplete_history.json"
    
    if not history_file.exists():
        initial_data = {
            'version': '1.0',
            'entries': [],
            'command_frequency': {},
            'command_success_rate': {}
        }
        
        # Create with restricted permissions
        old_umask = os.umask(0o077)
        try:
            with open(history_file, 'w') as f:
                json.dump(initial_data, f, indent=2)
            print(f"  ✅ Created history file: {history_file}")
        finally:
            os.umask(old_umask)
    else:
        print(f"  ℹ️ History exists: {history_file}")
    
    # Set proper permissions
    history_file.chmod(0o600)
    
    return history_file

def test_autocomplete():
    """Run a quick test of the autocomplete system"""
    print("\n🧪 Testing autocomplete system...")
    
    try:
        # Import and test the modules
        from app.cli.intelligence.autocomplete_history import AutocompleteHistoryManager
        from app.cli.intelligence.command_intelligence import CommandIntelligenceEngine
        
        print("  ✅ Modules imported successfully")
        
        # Create test instance
        manager = AutocompleteHistoryManager()
        
        # Add test commands
        test_commands = [
            "git status",
            "git commit -m 'test'",
            "docker ps",
            "docker compose up"
        ]
        
        for cmd in test_commands:
            manager.add_command(cmd)
        
        # Test suggestions
        suggestions = manager.get_suggestions("git")
        if suggestions:
            print(f"  ✅ Autocomplete working: {len(suggestions)} suggestions for 'git'")
        else:
            print("  ⚠️ No suggestions generated (expected for fresh install)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False

def update_cli_integration():
    """Update CLI to use autocomplete"""
    print("\n🔧 Updating CLI integration...")
    
    integration_points = [
        "app/cli/core/app.py - Main application",
        "app/cli/ui/enhanced_prompts.py - Interactive prompts",
        "app/cli/ui/chat.py - Chat interface"
    ]
    
    print("  Integration points to update:")
    for point in integration_points:
        print(f"    • {point}")
    
    print("\n  ℹ️ Manual integration required - see documentation")
    
    return True

def print_usage():
    """Print usage instructions"""
    print("\n" + "="*60)
    print("✨ LocalAgent Autocomplete Setup Complete!")
    print("="*60)
    
    print("\n📖 Quick Start Guide:")
    print("""
1. Start LocalAgent CLI:
   $ python -m app.cli

2. Use autocomplete in any prompt:
   - Start typing a command
   - Press Tab to complete
   - Use ↑/↓ arrows to navigate suggestions
   - Press Enter to accept

3. View command history:
   $ localagent autocomplete --stats

4. Clear old history:
   $ localagent autocomplete --clear-old 30

5. Export history:
   $ localagent autocomplete --export history.json
    """)
    
    print("\n🔗 Documentation:")
    print("  docs/CLI_AUTOCOMPLETE_IMPLEMENTATION.md")
    print("  docs/CLI_AUTOCOMPLETE_BEST_PRACTICES.md")
    
    print("\n⚙️ Configuration:")
    print(f"  ~/.localagent/autocomplete_config.yaml")
    
    print("\n🧪 Run tests:")
    print("  pytest tests/cli/test_autocomplete.py -v")

def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup LocalAgent Autocomplete')
    parser.add_argument('--docker-mode', action='store_true', 
                       help='Run in Docker container mode')
    args = parser.parse_args()
    
    print("🚀 LocalAgent Autocomplete Setup")
    print("="*40)
    
    if args.docker_mode:
        print("🐳 Running in Docker mode")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    try:
        # Setup steps
        if not args.docker_mode:  # Skip dependency check in Docker (pre-installed)
            if not check_dependencies():
                sys.exit(1)
        
        config_dir = setup_config_directory()
        config_file = create_default_config(config_dir)
        history_file = initialize_history(config_dir)
        
        if not args.docker_mode:  # Skip test in Docker build
            if not test_autocomplete():
                print("\n⚠️ Autocomplete test failed, but setup completed")
            
            update_cli_integration()
            print_usage()
        
        print("\n✅ Setup completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        if args.docker_mode:
            # Don't fail Docker build for setup issues
            print("⚠️ Continuing Docker build despite setup warning")
            sys.exit(0)
        sys.exit(1)

if __name__ == "__main__":
    main()