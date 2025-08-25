#!/bin/bash
# LocalAgent Installation Script
# Automated setup for LocalAgent multi-provider LLM CLI

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOCALAGENT_DIR="${LOCALAGENT_DIR:-$HOME/.localagent}"
INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"
PYTHON_MIN_VERSION="3.8"
REQUIRED_MEMORY_MB=4096
REQUIRED_DISK_MB=10240

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_system_requirements() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "Linux detected"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log_success "macOS detected"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_error "Python 3.8+ required, found $python_version"
        exit 1
    fi
    log_success "Python $python_version detected"
    
    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is required but not installed"
        exit 1
    fi
    log_success "Git detected"
    
    # Check memory
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
        if [ "$available_memory" -lt "$REQUIRED_MEMORY_MB" ]; then
            log_warning "Low memory detected: ${available_memory}MB available, ${REQUIRED_MEMORY_MB}MB recommended"
        fi
    fi
    
    # Check disk space
    available_disk=$(df / | awk 'NR==2{print $4}')
    available_disk_mb=$((available_disk / 1024))
    if [ "$available_disk_mb" -lt "$REQUIRED_DISK_MB" ]; then
        log_error "Insufficient disk space: ${available_disk_mb}MB available, ${REQUIRED_DISK_MB}MB required"
        exit 1
    fi
    
    log_success "System requirements check passed"
}

install_dependencies() {
    log_info "Installing system dependencies..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Detect package manager
        if command -v apt-get &> /dev/null; then
            log_info "Installing dependencies with apt..."
            sudo apt-get update
            sudo apt-get install -y python3-pip python3-venv curl git build-essential libffi-dev libssl-dev
        elif command -v yum &> /dev/null; then
            log_info "Installing dependencies with yum..."
            sudo yum update -y
            sudo yum install -y python3-pip python3-venv curl git gcc openssl-devel libffi-devel
        elif command -v pacman &> /dev/null; then
            log_info "Installing dependencies with pacman..."
            sudo pacman -Sy python-pip curl git base-devel openssl libffi
        else
            log_warning "Package manager not detected. Please install: python3-pip, python3-venv, curl, git, build-essential"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # Check for Homebrew
        if command -v brew &> /dev/null; then
            log_info "Installing dependencies with Homebrew..."
            brew install python git curl
        else
            log_warning "Homebrew not found. Please install manually: python3, git, curl"
        fi
    fi
    
    log_success "Dependencies installed"
}

setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    # Create LocalAgent directory
    mkdir -p "$LOCALAGENT_DIR"
    cd "$LOCALAGENT_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    log_success "Python environment created"
}

clone_repository() {
    log_info "Cloning LocalAgent repository..."
    
    if [ -d "$LOCALAGENT_DIR/LocalAgent" ]; then
        log_info "Repository already exists, updating..."
        cd "$LOCALAGENT_DIR/LocalAgent"
        git pull origin main
    else
        cd "$LOCALAGENT_DIR"
        git clone https://github.com/zvirb/LocalAgent.git
        cd LocalAgent
    fi
    
    # Initialize submodules if present
    if [ -f ".gitmodules" ]; then
        log_info "Initializing submodules..."
        git submodule update --init --recursive
    fi
    
    log_success "Repository cloned/updated"
}

install_python_packages() {
    log_info "Installing Python packages..."
    
    cd "$LOCALAGENT_DIR/LocalAgent"
    source "$LOCALAGENT_DIR/venv/bin/activate"
    
    # Install core dependencies
    pip install -r requirements.txt
    
    # Install UnifiedWorkflow dependencies if present
    if [ -f "UnifiedWorkflow/requirements-core.txt" ]; then
        pip install -r UnifiedWorkflow/requirements-core.txt
    fi
    
    if [ -f "UnifiedWorkflow/requirements-web.txt" ]; then
        pip install -r UnifiedWorkflow/requirements-web.txt
    fi
    
    log_success "Python packages installed"
}

setup_cli_executable() {
    log_info "Setting up CLI executable..."
    
    # Make script executable
    chmod +x "$LOCALAGENT_DIR/LocalAgent/scripts/localagent"
    
    # Create wrapper script for system-wide access
    cat > /tmp/localagent << EOF
#!/bin/bash
# LocalAgent CLI wrapper script
cd "$LOCALAGENT_DIR/LocalAgent"
source "$LOCALAGENT_DIR/venv/bin/activate"
exec python3 scripts/localagent "\$@"
EOF
    
    # Install to system
    if [ -w "$INSTALL_DIR" ]; then
        mv /tmp/localagent "$INSTALL_DIR/localagent"
        chmod +x "$INSTALL_DIR/localagent"
        log_success "LocalAgent installed to $INSTALL_DIR/localagent"
    else
        log_warning "Cannot write to $INSTALL_DIR, installing to ~/bin/"
        mkdir -p ~/bin
        mv /tmp/localagent ~/bin/localagent
        chmod +x ~/bin/localagent
        
        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
            echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
            echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc 2>/dev/null || true
            log_info "Added ~/bin to PATH. Please restart your shell or run: source ~/.bashrc"
        fi
        log_success "LocalAgent installed to ~/bin/localagent"
    fi
}

install_ollama() {
    log_info "Installing Ollama (local LLM server)..."
    
    if command -v ollama &> /dev/null; then
        log_success "Ollama already installed"
        return 0
    fi
    
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Wait for installation
    sleep 2
    
    if command -v ollama &> /dev/null; then
        log_success "Ollama installed successfully"
        
        # Start Ollama service
        log_info "Starting Ollama service..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl enable ollama
            sudo systemctl start ollama
        fi
        
        # Pull a lightweight model
        log_info "Downloading Llama 3.2 model (this may take a few minutes)..."
        ollama pull llama3.2:3b || log_warning "Failed to download model. You can download it later with: ollama pull llama3.2"
        
    else
        log_error "Ollama installation failed"
        exit 1
    fi
}

configure_localagent() {
    log_info "Configuring LocalAgent..."
    
    # Create configuration directory
    mkdir -p "$LOCALAGENT_DIR/config"
    
    # Create default configuration
    cat > "$LOCALAGENT_DIR/config/default.yaml" << EOF
# LocalAgent Default Configuration
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.2:3b"
    enabled: true
  
  openai:
    enabled: false
    # api_key: "your-openai-key-here"
    default_model: "gpt-4o-mini"
  
  gemini:
    enabled: false
    # api_key: "your-gemini-key-here" 
    default_model: "gemini-1.5-flash"
  
  perplexity:
    enabled: false
    # api_key: "your-perplexity-key-here"
    default_model: "sonar"

security:
  use_keyring: true
  encrypt_storage: true

logging:
  level: "INFO"
  file: "$LOCALAGENT_DIR/logs/localagent.log"

workflow:
  unified_workflow_enabled: true
  parallel_execution: true
  max_agents: 10
EOF
    
    # Create logs directory
    mkdir -p "$LOCALAGENT_DIR/logs"
    
    log_success "Configuration created at $LOCALAGENT_DIR/config/default.yaml"
}

run_health_check() {
    log_info "Running health check..."
    
    # Test LocalAgent CLI
    if localagent --help &> /dev/null; then
        log_success "LocalAgent CLI working"
    else
        log_error "LocalAgent CLI not working properly"
        exit 1
    fi
    
    # Test Ollama connection
    if command -v ollama &> /dev/null && ollama list &> /dev/null; then
        log_success "Ollama connection working"
    else
        log_warning "Ollama connection not working. You may need to start the service."
    fi
    
    log_success "Health check completed"
}

show_completion_message() {
    echo
    log_success "🎉 LocalAgent installation completed successfully!"
    echo
    echo -e "${BLUE}Quick Start:${NC}"
    echo "  1. Initialize configuration: ${GREEN}localagent init${NC}"
    echo "  2. Start interactive mode:   ${GREEN}localagent${NC}"
    echo "  3. Check provider status:    ${GREEN}localagent providers${NC}"
    echo "  4. Generate completion:      ${GREEN}localagent complete \"Hello, world!\"${NC}"
    echo
    echo -e "${BLUE}Documentation:${NC}"
    echo "  - Configuration: $LOCALAGENT_DIR/config/default.yaml"
    echo "  - Logs:          $LOCALAGENT_DIR/logs/"
    echo "  - Installation:  $LOCALAGENT_DIR/LocalAgent/"
    echo
    echo -e "${BLUE}Adding API Keys (optional):${NC}"
    echo "  - OpenAI:     export OPENAI_API_KEY='your-key'"
    echo "  - Gemini:     export GEMINI_API_KEY='your-key'"
    echo "  - Perplexity: export PERPLEXITY_API_KEY='your-key'"
    echo
    echo -e "${YELLOW}Note:${NC} If this is your first installation, please restart your shell or run:"
    echo "  ${GREEN}source ~/.bashrc${NC}"
}

# Main installation flow
main() {
    echo -e "${BLUE}LocalAgent Installation Script${NC}"
    echo "=============================="
    echo
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-ollama)
                SKIP_OLLAMA=true
                shift
                ;;
            --install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --help)
                echo "Usage: install.sh [OPTIONS]"
                echo "Options:"
                echo "  --skip-ollama     Skip Ollama installation"
                echo "  --install-dir     Custom installation directory"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Installation steps
    check_system_requirements
    install_dependencies
    setup_python_environment
    clone_repository
    install_python_packages
    setup_cli_executable
    
    if [[ "${SKIP_OLLAMA:-false}" != "true" ]]; then
        install_ollama
    fi
    
    configure_localagent
    run_health_check
    show_completion_message
}

# Run main function
main "$@"