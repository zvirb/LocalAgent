#!/bin/bash
#
# LocalAgent CLI Installation Script
# Installs the modern CLI toolkit with all dependencies
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_color "$BLUE" "🚀 LocalAgent CLI Installation"
print_color "$BLUE" "=================================="

# Check Python version
if ! command -v python3 &> /dev/null; then
    print_color "$RED" "❌ Python 3 is required but not found"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
print_color "$GREEN" "✅ Python $PYTHON_VERSION found"

# Check if we need a virtual environment
if [[ "${VIRTUAL_ENV:-}" == "" ]]; then
    VENV_PATH="$PROJECT_ROOT/.venv"
    
    if [[ ! -d "$VENV_PATH" ]]; then
        print_color "$YELLOW" "📦 Creating virtual environment..."
        python3 -m venv "$VENV_PATH"
    fi
    
    print_color "$YELLOW" "🔧 Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
    print_color "$GREEN" "✅ Virtual environment activated: $VENV_PATH"
else
    print_color "$GREEN" "✅ Using existing virtual environment: $VIRTUAL_ENV"
fi

# Upgrade pip
print_color "$YELLOW" "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
    print_color "$YELLOW" "📚 Installing dependencies..."
    pip install -r "$PROJECT_ROOT/requirements.txt"
else
    print_color "$YELLOW" "📚 Installing core dependencies..."
    pip install typer rich pydantic aiofiles keyring inquirerpy
fi

# Install CLI in development mode
print_color "$YELLOW" "🔧 Installing LocalAgent CLI..."
cd "$PROJECT_ROOT"
pip install -e .

# Verify installation
print_color "$BLUE" "🔍 Verifying installation..."

if command -v localagent &> /dev/null; then
    print_color "$GREEN" "✅ localagent command available"
    LOCALAGENT_PATH=$(which localagent)
    print_color "$GREEN" "   Path: $LOCALAGENT_PATH"
else
    print_color "$RED" "❌ localagent command not found"
    print_color "$YELLOW" "💡 You may need to activate the virtual environment:"
    print_color "$YELLOW" "   source $VENV_PATH/bin/activate"
fi

if command -v la &> /dev/null; then
    print_color "$GREEN" "✅ la (short alias) command available"
else
    print_color "$YELLOW" "⚠️  la alias not found (this is normal in some environments)"
fi

# Test basic functionality
print_color "$BLUE" "🧪 Testing basic functionality..."

if localagent --help &> /dev/null; then
    print_color "$GREEN" "✅ CLI help system working"
else
    print_color "$RED" "❌ CLI help system failed"
fi

# Create activation script
ACTIVATE_SCRIPT="$PROJECT_ROOT/activate-cli.sh"
cat > "$ACTIVATE_SCRIPT" << 'EOF'
#!/bin/bash
# LocalAgent CLI Environment Activation
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_ROOT/.venv/bin/activate"
echo "LocalAgent CLI environment activated!"
echo "Available commands: localagent, la"
echo "Try: localagent --help"
EOF
chmod +x "$ACTIVATE_SCRIPT"

print_color "$GREEN" "✅ Created activation script: $ACTIVATE_SCRIPT"

# Success message
print_color "$GREEN" ""
print_color "$GREEN" "🎉 LocalAgent CLI Installation Complete!"
print_color "$GREEN" "======================================"
print_color "$BLUE" ""
print_color "$BLUE" "📋 Next Steps:"
print_color "$BLUE" "1. Activate environment: source $ACTIVATE_SCRIPT"
print_color "$BLUE" "2. Initialize configuration: localagent init"
print_color "$BLUE" "3. Check system health: localagent health"
print_color "$BLUE" "4. View available commands: localagent --help"
print_color "$BLUE" ""
print_color "$YELLOW" "📚 Documentation available in: docs/"
print_color "$YELLOW" "🔧 Configuration files: ~/.config/localagent/"
print_color "$YELLOW" "🔑 Secure credentials stored via system keyring"
print_color "$BLUE" ""

# Show current status
if [[ "${VIRTUAL_ENV:-}" != "" ]]; then
    print_color "$GREEN" "✅ Virtual environment is active - you can use the CLI now!"
    print_color "$BLUE" "   Try: localagent --help"
else
    print_color "$YELLOW" "⚠️  To use the CLI, activate the environment first:"
    print_color "$YELLOW" "   source $ACTIVATE_SCRIPT"
fi