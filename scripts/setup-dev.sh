#!/bin/bash
# LocalAgent Development Environment Setup
# Automated development environment setup with testing and debugging tools

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_VERSION="python3.11"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prerequisites() {
    log_info "Checking development prerequisites..."
    
    # Check Python version
    if ! command -v $PYTHON_VERSION &> /dev/null; then
        if command -v python3 &> /dev/null; then
            PYTHON_VERSION="python3"
            log_warning "Python 3.11 not found, using $(python3 --version)"
        else
            log_error "Python 3 is required but not installed"
            exit 1
        fi
    fi
    
    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is required but not installed"
        exit 1
    fi
    
    # Check Docker (optional but recommended)
    if command -v docker &> /dev/null; then
        log_success "Docker detected"
        DOCKER_AVAILABLE=true
    else
        log_warning "Docker not found. Some development features will be limited."
        DOCKER_AVAILABLE=false
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null || command -v docker &> /dev/null && docker compose version &> /dev/null; then
        log_success "Docker Compose detected"
        COMPOSE_AVAILABLE=true
    else
        log_warning "Docker Compose not found"
        COMPOSE_AVAILABLE=false
    fi
    
    log_success "Prerequisites check completed"
}

setup_virtual_environment() {
    log_info "Setting up Python virtual environment..."
    
    cd "$PROJECT_ROOT"
    
    # Remove existing venv if requested
    if [[ "${FORCE_RECREATE:-false}" == "true" ]] && [[ -d "$VENV_DIR" ]]; then
        log_info "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    fi
    
    # Create virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        $PYTHON_VERSION -m venv "$VENV_DIR"
        log_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip and install build tools
    pip install --upgrade pip setuptools wheel build
    
    log_success "Virtual environment ready"
}

install_development_dependencies() {
    log_info "Installing development dependencies..."
    
    source "$VENV_DIR/bin/activate"
    
    # Core LocalAgent dependencies
    log_info "Installing core dependencies..."
    pip install -r requirements.txt
    
    # UnifiedWorkflow dependencies
    if [[ -f "UnifiedWorkflow/requirements-core.txt" ]]; then
        log_info "Installing UnifiedWorkflow core dependencies..."
        pip install -r UnifiedWorkflow/requirements-core.txt
    fi
    
    if [[ -f "UnifiedWorkflow/requirements-web.txt" ]]; then
        log_info "Installing UnifiedWorkflow web dependencies..."
        pip install -r UnifiedWorkflow/requirements-web.txt
    fi
    
    # Development and testing tools
    log_info "Installing development tools..."
    pip install \
        # Testing frameworks
        pytest>=7.0.0 \
        pytest-asyncio>=0.21.0 \
        pytest-cov>=4.0.0 \
        pytest-mock>=3.10.0 \
        pytest-timeout>=2.1.0 \
        # Code quality tools
        black>=23.0.0 \
        isort>=5.12.0 \
        pylint>=3.0.0 \
        flake8>=6.0.0 \
        mypy>=1.0.0 \
        # Documentation tools
        sphinx>=6.0.0 \
        sphinx-rtd-theme>=1.2.0 \
        myst-parser>=1.0.0 \
        # Development utilities
        ipython>=8.0.0 \
        jupyter>=1.0.0 \
        rich>=13.0.0 \
        typer>=0.9.0 \
        watchdog>=3.0.0 \
        # Security scanning
        bandit>=1.7.0 \
        safety>=2.3.0 \
        # Performance profiling
        py-spy>=0.3.0 \
        memory-profiler>=0.61.0 \
        # API testing
        httpx>=0.27.0 \
        responses>=0.23.0
    
    log_success "Development dependencies installed"
}

setup_git_hooks() {
    log_info "Setting up Git hooks..."
    
    cd "$PROJECT_ROOT"
    
    # Create pre-commit hook
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# LocalAgent pre-commit hook

set -e

echo "Running pre-commit checks..."

# Activate virtual environment
if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
fi

# Run code formatting
echo "Running code formatting..."
black --check app/ scripts/ tests/ || {
    echo "Code formatting issues found. Run: black app/ scripts/ tests/"
    exit 1
}

# Run import sorting
echo "Checking import sorting..."
isort --check-only app/ scripts/ tests/ || {
    echo "Import sorting issues found. Run: isort app/ scripts/ tests/"
    exit 1
}

# Run linting
echo "Running linting..."
pylint app/ || {
    echo "Linting issues found"
    exit 1
}

# Run type checking
echo "Running type checking..."
mypy app/ || {
    echo "Type checking issues found"
    exit 1
}

# Run tests
echo "Running tests..."
pytest tests/ -x -q || {
    echo "Tests failed"
    exit 1
}

echo "All pre-commit checks passed!"
EOF
    
    chmod +x .git/hooks/pre-commit
    log_success "Git pre-commit hook installed"
}

create_development_configs() {
    log_info "Creating development configuration files..."
    
    cd "$PROJECT_ROOT"
    
    # Create pytest configuration
    cat > pytest.ini << 'EOF'
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --timeout=60
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    network: Tests requiring network access
EOF
    
    # Create Black configuration
    cat > pyproject.toml << 'EOF'
[tool.black]
line-length = 88
target-version = ['py38', 'py39', 'py310', 'py311']
include = '\.pyi?$'
exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
  | UnifiedWorkflow
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
line_length = 88
skip_gitignore = true
extend_skip = ["UnifiedWorkflow"]

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
exclude = ["UnifiedWorkflow/"]

[tool.pylint]
disable = ["C0114", "C0115", "C0116"]
max-line-length = 88
good-names = ["i", "j", "k", "ex", "Run", "_", "id", "db", "ai"]

[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm[toml]>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "localagent"
description = "Multi-provider LLM orchestration CLI"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [
    {name = "LocalAgent Development Team"},
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]
dynamic = ["version"]
dependencies = [
    "click>=8.1.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "aiohttp>=3.9.0",
    "openai>=1.0.0",
    "google-generativeai>=0.3.0",
    "anthropic>=0.3.0",
    "cryptography>=41.0.0",
    "keyring>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "pylint>=3.0.0",
    "mypy>=1.0.0",
]

[project.scripts]
localagent = "app.cli:main"

[project.urls]
Homepage = "https://github.com/zvirb/LocalAgent"
Repository = "https://github.com/zvirb/LocalAgent.git"
Issues = "https://github.com/zvirb/LocalAgent/issues"
EOF
    
    # Create .env.example for development
    cat > .env.example << 'EOF'
# LocalAgent Development Environment Configuration

# Provider API Keys (optional)
OPENAI_API_KEY=sk-your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here
PERPLEXITY_API_KEY=your-perplexity-key-here

# Local Services
OLLAMA_BASE_URL=http://localhost:11434
REDIS_URL=redis://localhost:6379/0

# Logging Configuration
LOCALAGENT_LOG_LEVEL=DEBUG
LOCALAGENT_LOG_FILE=logs/localagent-dev.log

# Development Settings
LOCALAGENT_DEV_MODE=true
LOCALAGENT_DEBUG_PROVIDERS=true
LOCALAGENT_CACHE_ENABLED=false

# UnifiedWorkflow Settings
UNIFIED_WORKFLOW_ENABLED=true
MCP_MEMORY_URL=redis://localhost:6379/1
MCP_COORDINATION_URL=redis://localhost:6379/2

# Testing Configuration
PYTEST_TIMEOUT=120
TEST_PROVIDER_MOCK=true
EOF
    
    log_success "Development configuration files created"
}

setup_vscode_config() {
    log_info "Setting up VS Code configuration..."
    
    mkdir -p .vscode
    
    # VS Code settings
    cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.testing.unittestEnabled": false,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/htmlcov": true,
        "**/.coverage": true,
        "**/UnifiedWorkflow": false
    }
}
EOF
    
    # VS Code launch configuration for debugging
    cat > .vscode/launch.json << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "LocalAgent CLI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/scripts/localagent",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "LOCALAGENT_DEV_MODE": "true"
            },
            "args": []
        },
        {
            "name": "LocalAgent Interactive",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/scripts/localagent",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "LOCALAGENT_DEV_MODE": "true"
            },
            "args": []
        },
        {
            "name": "PyTest Current File",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["${file}", "-v"],
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal"
        }
    ]
}
EOF
    
    log_success "VS Code configuration created"
}

create_makefile() {
    log_info "Creating development Makefile..."
    
    cat > Makefile << 'EOF'
# LocalAgent Development Makefile

.PHONY: help install test lint format type-check clean docker-build docker-up docker-down docs

# Default target
help:
	@echo "LocalAgent Development Commands"
	@echo "=============================="
	@echo "install      - Install development dependencies"
	@echo "test         - Run tests"
	@echo "test-cov     - Run tests with coverage"
	@echo "lint         - Run linting"
	@echo "format       - Format code"
	@echo "type-check   - Run type checking"
	@echo "clean        - Clean build artifacts"
	@echo "docker-build - Build Docker image"
	@echo "docker-up    - Start Docker services"
	@echo "docker-down  - Stop Docker services"
	@echo "docs         - Build documentation"
	@echo "security     - Run security checks"

# Development setup
install:
	python -m pip install --upgrade pip setuptools wheel
	pip install -r requirements.txt
	pip install -e .[dev]

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-integration:
	pytest tests/integration/ -v -m integration

test-unit:
	pytest tests/unit/ -v -m unit

# Code quality
lint:
	pylint app/
	flake8 app/

format:
	black app/ scripts/ tests/
	isort app/ scripts/ tests/

type-check:
	mypy app/

# Security
security:
	bandit -r app/
	safety check

# Docker
docker-build:
	docker build -t localagent:dev .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Documentation
docs:
	cd docs && make html

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf .coverage htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# Development workflow
dev-setup: install
	pre-commit install
	@echo "Development environment ready!"

# Full quality check
check: format lint type-check test

# Release preparation
pre-release: clean check security docs
	@echo "Pre-release checks completed successfully!"
EOF
    
    log_success "Makefile created"
}

setup_docker_development() {
    if [[ "$DOCKER_AVAILABLE" == "false" ]]; then
        log_warning "Docker not available, skipping Docker development setup"
        return
    fi
    
    log_info "Setting up Docker development environment..."
    
    # Create development Docker Compose override
    cat > docker-compose.dev.yml << 'EOF'
version: '3.8'

# Development overrides for LocalAgent
services:
  localagent:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      # Mount source code for hot reloading
      - ./app:/app/app:ro
      - ./scripts:/app/scripts:ro
      - ./config:/app/config:ro
      # Development data persistence
      - ./data/dev-config:/app/config
      - ./data/dev-cache:/app/.cache
      - ./data/dev-logs:/app/logs
    environment:
      - LOCALAGENT_DEV_MODE=true
      - LOCALAGENT_LOG_LEVEL=DEBUG
    ports:
      - "8000:8000"  # Development API port
    
  # Development database
  postgres-dev:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=localagent_dev
      - POSTGRES_USER=localagent
      - POSTGRES_PASSWORD=dev_password
    volumes:
      - postgres-dev-data:/var/lib/postgresql/data
    ports:
      - "5433:5432"  # Non-standard port to avoid conflicts

volumes:
  postgres-dev-data:
EOF
    
    # Create development Dockerfile
    cat > Dockerfile.dev << 'EOF'
# Development Dockerfile with debugging tools
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:/app/UnifiedWorkflow"

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    vim \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies
RUN pip install --no-cache-dir \
    debugpy \
    ipython \
    pytest \
    pytest-asyncio \
    black \
    isort \
    pylint \
    mypy

# Copy source code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 developer && chown -R developer:developer /app
USER developer

EXPOSE 8000 5678

CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "scripts/localagent"]
EOF
    
    log_success "Docker development environment configured"
}

finalize_setup() {
    log_info "Finalizing development setup..."
    
    cd "$PROJECT_ROOT"
    
    # Create necessary directories
    mkdir -p logs data/dev-{config,cache,logs} docs tests/{unit,integration,mocks}
    
    # Create initial test files if they don't exist
    if [[ ! -f "tests/__init__.py" ]]; then
        touch tests/__init__.py
        touch tests/unit/__init__.py
        touch tests/integration/__init__.py
        touch tests/mocks/__init__.py
    fi
    
    # Create .gitignore additions for development
    cat >> .gitignore << 'EOF'

# Development environment
.venv/
*.egg-info/
htmlcov/
.coverage
.pytest_cache/
.mypy_cache/
data/dev-*/
logs/*.log
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# macOS
.DS_Store

# Windows
Thumbs.db
desktop.ini
EOF
    
    # Make scripts executable
    find scripts/ -name "*.sh" -exec chmod +x {} \;
    chmod +x scripts/localagent
    
    log_success "Development environment setup completed"
}

show_completion_message() {
    echo
    log_success "🎉 LocalAgent development environment ready!"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Activate environment:  ${GREEN}source .venv/bin/activate${NC}"
    echo "  2. Run tests:            ${GREEN}make test${NC}"
    echo "  3. Start development:    ${GREEN}make docker-up${NC}"
    echo "  4. Code formatting:      ${GREEN}make format${NC}"
    echo "  5. Full quality check:   ${GREEN}make check${NC}"
    echo
    echo -e "${BLUE}Development commands:${NC}"
    echo "  • ${GREEN}make help${NC}           - Show all available commands"
    echo "  • ${GREEN}make test${NC}           - Run test suite"
    echo "  • ${GREEN}make format${NC}         - Format code with Black"
    echo "  • ${GREEN}make lint${NC}           - Run linting"
    echo "  • ${GREEN}make docker-build${NC}   - Build development container"
    echo
    echo -e "${BLUE}Files created:${NC}"
    echo "  • pyproject.toml        - Project configuration"
    echo "  • pytest.ini           - Test configuration"
    echo "  • Makefile              - Development commands"
    echo "  • docker-compose.dev.yml - Development containers"
    echo "  • .vscode/              - VS Code configuration"
    echo
    echo -e "${YELLOW}Don't forget:${NC}"
    echo "  • Copy .env.example to .env and configure your API keys"
    echo "  • Install pre-commit hooks: ${GREEN}pre-commit install${NC}"
}

# Main setup flow
main() {
    echo -e "${BLUE}LocalAgent Development Environment Setup${NC}"
    echo "========================================"
    echo
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force-recreate)
                FORCE_RECREATE=true
                shift
                ;;
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            --help)
                echo "Usage: setup-dev.sh [OPTIONS]"
                echo "Options:"
                echo "  --force-recreate  Recreate virtual environment"
                echo "  --skip-docker     Skip Docker setup"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Setup steps
    check_prerequisites
    setup_virtual_environment
    install_development_dependencies
    setup_git_hooks
    create_development_configs
    setup_vscode_config
    create_makefile
    
    if [[ "${SKIP_DOCKER:-false}" != "true" ]]; then
        setup_docker_development
    fi
    
    finalize_setup
    show_completion_message
}

# Run main function
main "$@"