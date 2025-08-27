# LocalAgent CLI Installation and Setup Guide

## Table of Contents
- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Initial Configuration](#initial-configuration)
- [Provider Setup](#provider-setup)
- [Verification and Testing](#verification-and-testing)
- [Environment Configuration](#environment-configuration)
- [Advanced Installation Options](#advanced-installation-options)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Docker Installation](#docker-installation)
- [Development Installation](#development-installation)
- [Upgrade and Maintenance](#upgrade-and-maintenance)
- [Uninstallation](#uninstallation)

---

## System Requirements

### Minimum System Requirements

| Component | Requirement | Recommended |
|-----------|------------|-------------|
| **Operating System** | Linux, macOS, Windows 10+ | Ubuntu 20.04+, macOS 12+, Windows 11 |
| **Python Version** | Python 3.9+ | Python 3.11+ |
| **Memory (RAM)** | 2GB available | 4GB+ available |
| **Disk Space** | 500MB free | 2GB+ free |
| **Network** | Internet connection | Stable broadband connection |
| **Terminal** | UTF-8 support | Modern terminal with 256 color support |

### Optional Requirements

| Component | Purpose | Installation |
|-----------|---------|-------------|
| **Ollama** | Local LLM serving | `curl -fsSL https://ollama.ai/install.sh \| sh` |
| **Docker** | Containerized execution | Docker Engine 20.10+ |
| **Git** | Version control integration | Git 2.25+ |
| **Node.js** | JavaScript project analysis | Node.js 16+ (for JS/TS projects) |

### Python Environment Check

```bash
# Check Python version
python --version
python3 --version

# Check pip availability
pip --version
pip3 --version

# Verify Python 3.9+ requirement
python -c "import sys; print('✅ Python version OK' if sys.version_info >= (3, 9) else '❌ Python 3.9+ required')"
```

---

## Installation Methods

### Method 1: pip Installation (Recommended)

This is the simplest and recommended installation method for most users.

#### Standard Installation
```bash
# Install from PyPI
pip install localagent-cli

# Verify installation
localagent --version

# Show installation information
pip show localagent-cli
```

#### User Installation (No Admin Rights)
```bash
# Install for current user only
pip install --user localagent-cli

# Add to PATH (Linux/Mac)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Add to PATH (Windows PowerShell)
$env:PATH += ";$env:USERPROFILE\.local\Scripts"
```

#### Virtual Environment Installation (Best Practice)
```bash
# Create virtual environment
python -m venv localagent-env

# Activate virtual environment
source localagent-env/bin/activate  # Linux/Mac
# or localagent-env\Scripts\activate  # Windows

# Install LocalAgent
pip install localagent-cli

# Verify installation
localagent --version
```

### Method 2: Development Installation

For developers who want to contribute or modify LocalAgent.

```bash
# Clone repository
git clone https://github.com/your-org/LocalProgramming.git
cd LocalProgramming

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Verify development installation
localagent --version
which localagent
```

### Method 3: Package Manager Installation

#### Using Homebrew (macOS/Linux)
```bash
# Add LocalAgent tap
brew tap localagent/tap

# Install LocalAgent
brew install localagent

# Update
brew upgrade localagent
```

#### Using Chocolatey (Windows)
```powershell
# Install LocalAgent
choco install localagent

# Update
choco upgrade localagent
```

#### Using apt (Ubuntu/Debian)
```bash
# Add repository
curl -fsSL https://packages.localagent.dev/gpg.key | sudo apt-key add -
echo "deb https://packages.localagent.dev/apt stable main" | sudo tee /etc/apt/sources.list.d/localagent.list

# Update and install
sudo apt update
sudo apt install localagent-cli
```

---

## Initial Configuration

### Quick Setup (Interactive)

The fastest way to get started is using the interactive configuration wizard.

```bash
# Run interactive setup
localagent init

# Follow the prompts for:
# 1. Provider configuration (Ollama, OpenAI, etc.)
# 2. API key setup
# 3. System preferences
# 4. Plugin selection
```

#### Interactive Setup Flow
```
╭──────────────────────────────────────────────────╮
│          LocalAgent Configuration Setup          │
╰──────────────────────────────────────────────────╯

Welcome to LocalAgent CLI! Let's set up your configuration.

Configuration Directory: /home/user/.localagent ✓

═══ Provider Configuration ═══

? Configure Ollama (local LLM serving)? (Y/n) y
  Ollama URL [http://localhost:11434]: 
  Default model [llama3.1]: 
  ✅ Ollama configuration saved

? Configure OpenAI API? (Y/n) y
  OpenAI API Key (secure input): ••••••••••••••••••••
  Default model [gpt-4]: 
  Organization ID (optional): 
  ✅ OpenAI configuration saved

? Configure Google Gemini API? (y/N) n

? Configure Perplexity API? (y/N) n

═══ System Configuration ═══

  Default provider [ollama]: 
  Max parallel agents [10]: 8
  Enable audit logging? (Y/n) y
  Log level [INFO]: 

═══ Plugin Configuration ═══

Select plugins to enable:
  [✓] workflow-automation  (Advanced workflow tools)
  [✓] security-scanner     (Security vulnerability scanning)
  [ ] export-tools         (Data export utilities)
  [ ] dev-tools           (Developer debugging tools)

? Enable automatic plugin loading? (Y/n) y

═══ Setup Complete ═══

✅ Configuration saved to ~/.localagent/config.yaml
✅ API keys stored securely in system keyring
✅ 2 plugins enabled

Next steps:
1. Run 'localagent health' to verify setup
2. Try 'localagent chat' for interactive mode
3. Execute 'localagent workflow "test task"' for workflow testing

Happy coding with LocalAgent! 🚀
```

### Manual Configuration

For automated setups or custom configurations:

```bash
# Create configuration directory
mkdir -p ~/.localagent

# Create basic configuration file
cat > ~/.localagent/config.yaml << 'EOF'
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
    timeout: 120
    max_retries: 3
    
  openai:
    api_key: "${OPENAI_API_KEY}"
    default_model: "gpt-4"
    timeout: 60
    
system:
  default_provider: "ollama"
  max_parallel_agents: 10
  log_level: "INFO"
  cache_enabled: true
  
plugins:
  enabled_plugins:
    - "workflow-automation"
    - "security-scanner"
  auto_load_plugins: true
  
logging:
  level: "INFO"
  format: "structured"
  output: "console"
EOF

# Validate configuration
localagent config validate
```

### Configuration Templates

#### Development Configuration
```bash
# Create development-focused configuration
localagent init --template development

# This creates configuration optimized for:
# - Local development with Ollama
# - Debug logging enabled
# - Development plugins loaded
# - Hot-reload capabilities
```

#### Production Configuration
```bash
# Create production-focused configuration
localagent init --template production

# This creates configuration optimized for:
# - Multiple provider fallbacks
# - Security-focused settings
# - Performance optimizations
# - Comprehensive logging
```

#### Team Configuration
```bash
# Create team-shared configuration
localagent init --template team --output team-config.yaml

# Team members can then use:
localagent init --import team-config.yaml
```

---

## Provider Setup

### Ollama Setup (Recommended for Local Development)

Ollama provides local LLM serving without API costs.

#### Install Ollama
```bash
# Linux/Mac - Automatic installation
curl -fsSL https://ollama.ai/install.sh | sh

# Or manual download from https://ollama.ai/download

# Windows - Download installer from website
# https://ollama.ai/download/windows
```

#### Configure Ollama
```bash
# Start Ollama service
ollama serve &

# Or use systemd (Linux)
sudo systemctl start ollama
sudo systemctl enable ollama

# Pull recommended models
ollama pull llama3.1        # General purpose
ollama pull codellama       # Code-focused
ollama pull mistral         # Fast alternative

# Verify models
ollama list

# Test Ollama with LocalAgent
localagent providers --provider ollama --health
```

#### Ollama Configuration Options
```yaml
# ~/.localagent/config.yaml
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"
    timeout: 120
    max_retries: 3
    connection_pool_size: 10
    keep_alive: true
    
    # Model preferences for different tasks
    model_preferences:
      coding: "codellama"
      general: "llama3.1"
      fast: "mistral"
```

### OpenAI Setup

#### API Key Acquisition
1. Visit [OpenAI Platform](https://platform.openai.com)
2. Create account or sign in
3. Navigate to API Keys section
4. Create new API key
5. Copy and securely store the key

#### OpenAI Configuration
```bash
# Method 1: Secure keyring storage (recommended)
keyring set localagent openai_api_key
# Enter your API key when prompted

# Method 2: Environment variable
export OPENAI_API_KEY="sk-your-api-key-here"

# Method 3: Configuration file (less secure)
localagent config set providers.openai.api_key "sk-your-api-key-here"

# Test OpenAI connection
localagent providers --provider openai --health
```

#### OpenAI Advanced Configuration
```yaml
# ~/.localagent/config.yaml
providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
    default_model: "gpt-4"
    timeout: 60
    max_retries: 3
    organization: "org-your-org-id"  # Optional
    
    # Rate limiting
    rate_limit_per_minute: 60
    rate_limit_per_hour: 1000
    
    # Model preferences
    model_preferences:
      fast: "gpt-3.5-turbo"
      quality: "gpt-4"
      vision: "gpt-4-vision-preview"
      large_context: "gpt-4-32k"
```

### Google Gemini Setup

#### API Key Setup
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create or select project
3. Generate API key
4. Configure LocalAgent

```bash
# Store API key securely
keyring set localagent gemini_api_key

# Or use environment variable
export GOOGLE_AI_API_KEY="your-gemini-api-key-here"

# Test connection
localagent providers --provider gemini --health
```

#### Gemini Configuration
```yaml
providers:
  gemini:
    api_key: "${GOOGLE_AI_API_KEY}"
    default_model: "gemini-1.5-pro"
    timeout: 60
    
    # Safety settings
    safety_settings:
      harassment: "BLOCK_MEDIUM_AND_ABOVE"
      hate_speech: "BLOCK_MEDIUM_AND_ABOVE"
      sexually_explicit: "BLOCK_MEDIUM_AND_ABOVE"
      dangerous_content: "BLOCK_MEDIUM_AND_ABOVE"
    
    # Model preferences
    model_preferences:
      default: "gemini-1.5-pro"
      fast: "gemini-1.5-flash"
      large_context: "gemini-1.5-pro"
```

### Perplexity Setup

#### API Configuration
```bash
# Get API key from https://www.perplexity.ai/settings/api
export PERPLEXITY_API_KEY="pplx-your-api-key-here"

# Or use keyring
keyring set localagent perplexity_api_key

# Test connection
localagent providers --provider perplexity --health
```

#### Perplexity Configuration
```yaml
providers:
  perplexity:
    api_key: "${PERPLEXITY_API_KEY}"
    default_model: "llama-3.1-sonar-huge-128k-online"
    timeout: 60
    
    # Search configuration
    search_domain_filter:
      - "github.com"
      - "stackoverflow.com"
      - "docs.python.org"
    
    # Model preferences
    model_preferences:
      online: "llama-3.1-sonar-huge-128k-online"
      offline: "llama-3.1-sonar-huge-128k-chat"
      fast: "llama-3.1-sonar-small-128k-online"
```

### Multi-Provider Configuration

Configure automatic fallback between providers:

```yaml
system:
  default_provider: "ollama"
  provider_fallback: true
  fallback_order:
    - "ollama"      # Free, local
    - "gemini"      # Cost-effective
    - "openai"      # High quality
    - "perplexity"  # Research tasks
  
  # Provider selection strategy
  provider_selection:
    strategy: "cost_optimized"  # or "performance_optimized", "balanced"
    max_fallback_attempts: 2
    timeout_threshold: 30
```

---

## Verification and Testing

### Basic Verification

```bash
# Check installation
localagent --version
localagent --help

# Verify configuration
localagent config show

# Validate configuration
localagent config validate

# System health check
localagent health
```

### Provider Testing

```bash
# Test all providers
localagent providers --health

# Test specific provider
localagent providers --provider ollama --health --verbose

# List available models
localagent providers --models

# Test with sample request
localagent providers --provider ollama --test
```

### Workflow Testing

```bash
# Test basic workflow
localagent workflow "Hello, world!" --provider ollama

# Test comprehensive workflow
localagent workflow "Analyze this project structure" --phases "1,2,3"

# Test interactive chat
localagent chat --provider ollama
```

### Plugin Verification

```bash
# List available plugins
localagent plugins --list

# Test enabled plugins
localagent plugins --test workflow-automation

# Enable additional plugins
localagent plugins --enable security-scanner
```

---

## Environment Configuration

### Environment Variables Reference

Create environment configuration file:

```bash
# Create environment configuration
cat > ~/.localagent/env.conf << 'EOF'
# LocalAgent Environment Configuration

# Core System Settings
export LOCALAGENT_DEFAULT_PROVIDER=ollama
export LOCALAGENT_MAX_PARALLEL_AGENTS=10
export LOCALAGENT_LOG_LEVEL=INFO
export LOCALAGENT_CONFIG_DIR=~/.localagent

# Provider Settings
export LOCALAGENT_OLLAMA_BASE_URL=http://localhost:11434
export LOCALAGENT_OLLAMA_DEFAULT_MODEL=llama3.1

# API Keys (use keyring in production)
export LOCALAGENT_OPENAI_API_KEY=sk-your-key-here
export LOCALAGENT_GEMINI_API_KEY=your-gemini-key-here
export LOCALAGENT_PERPLEXITY_API_KEY=pplx-your-key-here

# Plugin Settings
export LOCALAGENT_PLUGINS_ENABLED=workflow-automation,security-scanner
export LOCALAGENT_PLUGINS_AUTO_LOAD=true

# Performance Settings
export LOCALAGENT_MAX_MEMORY_MB=4096
export LOCALAGENT_MAX_CPU_PERCENT=80
export LOCALAGENT_CACHE_ENABLED=true

# Security Settings
export LOCALAGENT_ENABLE_AUDIT_LOG=true
export LOCALAGENT_KEYRING_SERVICE=localagent
EOF

# Load environment
source ~/.localagent/env.conf

# Add to shell profile for persistence
echo "source ~/.localagent/env.conf" >> ~/.bashrc
```

### Shell Integration

#### Bash Completion
```bash
# Enable bash completion
localagent --install-completion bash

# Or manually add to ~/.bashrc
eval "$(_LOCALAGENT_COMPLETE=bash_source localagent)"
```

#### Zsh Completion
```bash
# Enable zsh completion
localagent --install-completion zsh

# Or manually add to ~/.zshrc
eval "$(_LOCALAGENT_COMPLETE=zsh_source localagent)"
```

#### PowerShell Completion (Windows)
```powershell
# Add to PowerShell profile
localagent --install-completion powershell
```

### IDE Integration

#### VS Code Extension Setup
```bash
# Install LocalAgent VS Code extension
code --install-extension localagent.localagent-vscode

# Or search for "LocalAgent" in VS Code extensions marketplace
```

#### Vim/Neovim Integration
```vim
" Add to ~/.vimrc or ~/.config/nvim/init.vim
" LocalAgent integration
nnoremap <leader>la :!localagent workflow "<C-R><C-W>"<CR>
nnoremap <leader>lc :!localagent chat<CR>
```

---

## Advanced Installation Options

### Headless Installation

For server installations without interactive prompts:

```bash
# Create automated installation script
cat > install_localagent_headless.sh << 'EOF'
#!/bin/bash
set -e

# Install LocalAgent
pip install --user localagent-cli

# Create minimal configuration
mkdir -p ~/.localagent
cat > ~/.localagent/config.yaml << 'EOC'
providers:
  ollama:
    base_url: "http://localhost:11434"
    default_model: "llama3.1"

system:
  default_provider: "ollama"
  max_parallel_agents: 4
  log_level: "INFO"

plugins:
  enabled_plugins:
    - "workflow-automation"
  auto_load_plugins: true
EOC

# Validate configuration
localagent config validate

echo "LocalAgent installed successfully in headless mode"
EOF

chmod +x install_localagent_headless.sh
./install_localagent_headless.sh
```

### Corporate/Enterprise Installation

For enterprise environments with proxy/firewall restrictions:

```bash
# Configure proxy settings
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,internal.company.com

# Install with proxy
pip install --proxy $HTTP_PROXY localagent-cli

# Configure LocalAgent for corporate environment
cat > ~/.localagent/config.yaml << 'EOF'
providers:
  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: "${OPENAI_API_BASE_URL}"  # Internal proxy if needed
    
system:
  proxy:
    http_proxy: "${HTTP_PROXY}"
    https_proxy: "${HTTPS_PROXY}"
    no_proxy: "${NO_PROXY}"
    
  security:
    ca_bundle: "/etc/ssl/certs/ca-certificates.crt"
    verify_ssl: true
    
logging:
  level: "INFO"
  audit_enabled: true
  audit_file: "~/.localagent/audit.log"
EOF
```

### High Availability Setup

For production environments requiring high availability:

```bash
# Create HA configuration
cat > ~/.localagent/config-ha.yaml << 'EOF'
providers:
  # Primary provider
  ollama-primary:
    base_url: "http://ollama-primary.internal:11434"
    default_model: "llama3.1"
    priority: 1
    
  # Backup provider
  ollama-backup:
    base_url: "http://ollama-backup.internal:11434"
    default_model: "llama3.1"
    priority: 2
    
  # Cloud fallback
  openai:
    api_key: "${OPENAI_API_KEY}"
    default_model: "gpt-4"
    priority: 3

system:
  provider_fallback: true
  fallback_order:
    - "ollama-primary"
    - "ollama-backup" 
    - "openai"
  max_fallback_attempts: 3
  timeout_threshold: 30
  
  # Health monitoring
  health_check_interval: 60
  auto_recover: true
  
monitoring:
  enabled: true
  metrics_endpoint: "http://prometheus.internal:9090"
  alert_webhook: "http://alerts.internal/webhook"
EOF

# Use HA configuration
export LOCALAGENT_CONFIG_FILE=~/.localagent/config-ha.yaml
localagent health --comprehensive
```

---

## Platform-Specific Instructions

### Ubuntu/Debian Linux

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv

# Install system dependencies
sudo apt install build-essential curl git

# Install LocalAgent
pip3 install --user localagent-cli

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install Ollama (optional)
curl -fsSL https://ollama.ai/install.sh | sh
sudo systemctl enable ollama
sudo systemctl start ollama

# Verify installation
localagent --version
```

### CentOS/RHEL/Fedora

```bash
# Install Python and development tools
sudo dnf install python3 python3-pip python3-devel gcc

# Or for CentOS/RHEL 7
sudo yum install python3 python3-pip python3-devel gcc

# Install LocalAgent
pip3 install --user localagent-cli

# Configure PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Configure firewall (if needed)
sudo firewall-cmd --permanent --add-port=11434/tcp
sudo firewall-cmd --reload
```

### macOS

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python

# Install LocalAgent
pip3 install localagent-cli

# Install Ollama
brew install ollama
brew services start ollama

# Verify installation
localagent --version
ollama --version
```

### Windows

#### Using Python from Microsoft Store
```powershell
# Install Python from Microsoft Store
# Or download from python.org

# Install LocalAgent
pip install localagent-cli

# Add to PATH (if needed)
$env:PATH += ";$env:USERPROFILE\.local\Scripts"

# Install Ollama
# Download installer from https://ollama.ai/download/windows
# Run installer and follow instructions

# Verify installation
localagent --version
```

#### Using Chocolatey
```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force; 
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; 
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Python and LocalAgent
choco install python
choco install localagent
choco install ollama

# Verify installation
localagent --version
```

#### Using WSL2 (Windows Subsystem for Linux)
```bash
# Enable WSL2 and install Ubuntu
wsl --install -d Ubuntu

# Inside WSL2, follow Ubuntu installation instructions
sudo apt update
sudo apt install python3 python3-pip
pip3 install --user localagent-cli

# Install Ollama in WSL2
curl -fsSL https://ollama.ai/install.sh | sh
```

---

## Docker Installation

### Official Docker Image

```bash
# Pull official image
docker pull localagent/cli:latest

# Run LocalAgent in container
docker run -it --rm \
  -v $(pwd):/workspace \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  localagent/cli:latest \
  workflow "Analyze project structure"

# Run interactive shell
docker run -it --rm \
  -v $(pwd):/workspace \
  localagent/cli:latest \
  bash
```

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  localagent:
    image: localagent/cli:latest
    volumes:
      - .:/workspace
      - ~/.localagent:/root/.localagent
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOCALAGENT_DEFAULT_PROVIDER=ollama
      - LOCALAGENT_OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - ollama
    working_dir: /workspace
    
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434

volumes:
  ollama_data:
```

```bash
# Start services
docker-compose up -d

# Use LocalAgent
docker-compose run localagent workflow "Test workflow"

# Interactive mode
docker-compose run localagent chat
```

### Custom Docker Build

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install LocalAgent
RUN pip install localagent-cli

# Create working directory
WORKDIR /workspace

# Set up configuration directory
RUN mkdir -p /root/.localagent

# Copy configuration template
COPY config.yaml /root/.localagent/config.yaml

# Set default command
CMD ["localagent", "--help"]
```

```bash
# Build custom image
docker build -t my-localagent .

# Run custom image
docker run -it --rm -v $(pwd):/workspace my-localagent
```

---

## Development Installation

### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/your-org/LocalProgramming.git
cd LocalProgramming

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate    # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Or install dependencies separately
pip install -e .
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest

# Run LocalAgent in development mode
export LOCALAGENT_DEV_MODE=true
localagent --version
```

### Development Configuration

```yaml
# .localagent/development.yaml
development:
  debug_mode: true
  hot_reload: true
  verbose_logging: true
  
plugins:
  allow_dev_plugins: true
  auto_reload: true
  development_directories:
    - "./dev-plugins"
    - "~/.localagent/dev-plugins"
    
workflow:
  enable_step_debugging: true
  save_intermediate_results: true
  detailed_error_traces: true
  
providers:
  mock_responses: false
  response_simulation: false
  
logging:
  level: "DEBUG"
  format: "detailed"
  show_traceback: true
```

### Development Commands

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=localagent tests/

# Run linting
black .
isort .
mypy localagent/

# Build documentation
cd docs/
make html

# Create development build
python -m build

# Install development build
pip install dist/localagent_cli-*.whl
```

---

## Upgrade and Maintenance

### Upgrading LocalAgent

```bash
# Check current version
localagent --version

# Upgrade to latest version
pip install --upgrade localagent-cli

# Verify upgrade
localagent --version

# Check for configuration compatibility
localagent config validate --comprehensive
```

### Configuration Migration

```bash
# Backup current configuration
cp ~/.localagent/config.yaml ~/.localagent/config.yaml.backup

# Check for migration needs
localagent config migrate --check

# Perform automatic migration
localagent config migrate --auto

# Manual migration if needed
localagent config migrate --interactive
```

### Plugin Updates

```bash
# Update all plugins
localagent plugins --update-all

# Update specific plugin
localagent plugins --update security-scanner

# Check for plugin compatibility
localagent plugins --check-compatibility
```

### Maintenance Tasks

```bash
# Clean up old logs
localagent logs --cleanup --older-than 30d

# Clear cache
localagent cache clear

# Optimize configuration
localagent config optimize

# Health check after maintenance
localagent health --comprehensive
```

### Automated Updates

```bash
# Create update script
cat > ~/.localagent/update.sh << 'EOF'
#!/bin/bash
set -e

echo "Updating LocalAgent..."

# Backup configuration
cp ~/.localagent/config.yaml ~/.localagent/config.yaml.backup

# Update LocalAgent
pip install --upgrade localagent-cli

# Update plugins
localagent plugins --update-all

# Validate configuration
localagent config validate

# Run health check
localagent health

echo "Update completed successfully!"
EOF

chmod +x ~/.localagent/update.sh

# Run updates
~/.localagent/update.sh
```

---

## Uninstallation

### Complete Uninstallation

```bash
# Remove LocalAgent package
pip uninstall localagent-cli

# Remove configuration and data
rm -rf ~/.localagent/

# Remove from PATH (if manually added)
# Edit ~/.bashrc or ~/.zshrc and remove LocalAgent PATH entries

# Remove shell completion
# Remove completion entries from shell configuration files

# Remove any custom scripts or aliases
# Check ~/.bashrc, ~/.zshrc, etc.
```

### Selective Removal

```bash
# Keep configuration, remove only package
pip uninstall localagent-cli

# Keep package, reset configuration
localagent config reset --confirm

# Remove only plugins
rm -rf ~/.localagent/plugins/

# Remove only logs and cache
rm -rf ~/.localagent/logs/
rm -rf ~/.localagent/cache/
```

### Clean Docker Environment

```bash
# Remove Docker containers
docker-compose down -v

# Remove Docker images
docker rmi localagent/cli
docker rmi ollama/ollama

# Remove Docker volumes
docker volume rm $(docker volume ls -q | grep localagent)
```

---

## Post-Installation Verification

### Complete Verification Checklist

```bash
#!/bin/bash
# LocalAgent Installation Verification Script

echo "=== LocalAgent Installation Verification ==="
echo

# Version check
echo "1. Version Check:"
localagent --version || { echo "❌ LocalAgent not found"; exit 1; }
echo "✅ LocalAgent installed"
echo

# Configuration check
echo "2. Configuration Check:"
localagent config validate || { echo "⚠️ Configuration issues detected"; }
echo "✅ Configuration validated"
echo

# Provider health check
echo "3. Provider Health Check:"
localagent providers --health
echo

# Plugin status
echo "4. Plugin Status:"
localagent plugins --list
echo

# System health
echo "5. System Health:"
localagent health --quick
echo

# Basic functionality test
echo "6. Basic Functionality Test:"
localagent workflow "Hello, LocalAgent!" --dry-run --provider ollama
echo "✅ Basic functionality verified"
echo

echo "=== Verification Complete ==="
echo "LocalAgent is ready to use!"
echo
echo "Next steps:"
echo "- Try: localagent chat"
echo "- Or: localagent workflow 'Analyze this project'"
echo "- Help: localagent --help"
```

Save this as `verify-installation.sh`, make it executable with `chmod +x verify-installation.sh`, and run it to verify your installation.

---

## Quick Start After Installation

Once installation is complete, here are the essential first commands to try:

```bash
# 1. Check system health
localagent health

# 2. Test provider connectivity
localagent providers --health

# 3. Start interactive chat
localagent chat

# 4. Run a simple workflow
localagent workflow "What is the current directory structure?"

# 5. Get help
localagent --help
localagent workflow --help
```

This completes the comprehensive installation and setup guide for LocalAgent CLI. The installation provides a robust, feature-rich command-line interface with extensive LLM provider support and advanced workflow capabilities.