# LocalAgent - Deployment and Development Makefile

.PHONY: help install test lint format type-check clean docker-build docker-up docker-down docs security deploy

# Configuration
PYTHON_VERSION ?= 3.11
REGISTRY ?= ghcr.io/zvirb/localagent
IMAGE_TAG ?= latest
DEPLOYMENT_ENV ?= development

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# Default target
help:
	@echo "$(BLUE)LocalAgent Development & Deployment Commands$(NC)"
	@echo "============================================="
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  install      - Install development dependencies"
	@echo "  config-import- Import example config to ~/.localagent"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"
	@echo "  type-check   - Run type checking"
	@echo "  clean        - Clean build artifacts"
	@echo "  security     - Run security checks"
	@echo "  docs         - Build documentation"
	@echo ""
	@echo "$(GREEN)Docker & Deployment:$(NC)"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-up    - Start Docker services"
	@echo "  docker-down  - Stop Docker services"
	@echo "  deploy-dev   - Deploy to development environment"
	@echo "  deploy-prod  - Deploy to production environment"
	@echo ""
	@echo "$(GREEN)Quality Assurance:$(NC)"
	@echo "  check        - Run all quality checks"
	@echo "  pre-commit   - Run pre-commit checks"
	@echo ""
	@echo "$(GREEN)Environment Variables:$(NC)"
	@echo "  REGISTRY     - Container registry ($(REGISTRY))"
	@echo "  IMAGE_TAG    - Image tag ($(IMAGE_TAG))"
	@echo "  PYTHON_VERSION - Python version ($(PYTHON_VERSION))"

# Development setup
install:
	@echo "$(BLUE)Installing LocalAgent dependencies...$(NC)"
	@if [ ! -d ".venv" ]; then \
		python$(PYTHON_VERSION) -m venv .venv; \
	fi
	@. .venv/bin/activate && \
		python -m pip install --upgrade pip setuptools wheel && \
		pip install -r requirements.txt && \
		if [ -f "UnifiedWorkflow/requirements-core.txt" ]; then \
			pip install -r UnifiedWorkflow/requirements-core.txt; \
		fi && \
		if [ -f "UnifiedWorkflow/requirements-web.txt" ]; then \
			pip install -r UnifiedWorkflow/requirements-web.txt; \
		fi && \
		pip install \
			pytest>=7.0.0 \
			pytest-asyncio>=0.21.0 \
			pytest-cov>=4.0.0 \
			black>=23.0.0 \
			isort>=5.12.0 \
			pylint>=3.0.0 \
			mypy>=1.0.0 \
			bandit>=1.7.0 \
			safety>=2.3.0
	@echo "$(GREEN)✓ Dependencies installed successfully$(NC)"

# Setup development environment
setup-dev:
	@echo "$(BLUE)Setting up development environment...$(NC)"
	./scripts/setup-dev.sh
	@echo "$(GREEN)✓ Development environment ready$(NC)"

# Testing
test:
	@echo "$(BLUE)Running tests...$(NC)"
	@. .venv/bin/activate && pytest tests/ -v

test-cov:
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	@. .venv/bin/activate && \
		pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-integration:
	@echo "$(BLUE)Running integration tests...$(NC)"
	@. .venv/bin/activate && \
		pytest tests/integration/ -v -m integration

test-unit:
	@echo "$(BLUE)Running unit tests...$(NC)"
	@. .venv/bin/activate && \
		pytest tests/unit/ -v -m unit

# Code quality
lint:
	@echo "$(BLUE)Running linting...$(NC)"
	@. .venv/bin/activate && \
		pylint app/ || true && \
		flake8 app/ scripts/ tests/ || true

format:
	@echo "$(BLUE)Formatting code...$(NC)"
	@. .venv/bin/activate && \
		black app/ scripts/ tests/ && \
		isort app/ scripts/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check:
	@echo "$(BLUE)Running type checking...$(NC)"
	@. .venv/bin/activate && mypy app/ || true

# Security checks
security:
	@echo "$(BLUE)Running security checks...$(NC)"
	@. .venv/bin/activate && \
		bandit -r app/ || true && \
		safety check || true

# Documentation
docs:
	@echo "$(BLUE)Building documentation...$(NC)"
	@if [ -d "docs/" ]; then \
		cd docs && make html; \
	else \
		echo "$(YELLOW)Documentation directory not found$(NC)"; \
	fi

# Docker operations
docker-build:
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t $(REGISTRY):$(IMAGE_TAG) .
	@echo "$(GREEN)✓ Docker image built: $(REGISTRY):$(IMAGE_TAG)$(NC)"

docker-build-dev:
	@echo "$(BLUE)Building development Docker image...$(NC)"
	docker build -f Dockerfile.dev -t $(REGISTRY):dev .
	@echo "$(GREEN)✓ Development Docker image built$(NC)"

docker-up:
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(YELLOW)LocalAgent CLI: docker exec -it localagent-cli localagent$(NC)"
	@echo "$(YELLOW)Ollama: http://localhost:11434$(NC)"
	@echo "$(YELLOW)Redis: localhost:6379$(NC)"

docker-up-dev:
	@echo "$(BLUE)Starting development Docker services...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "$(GREEN)✓ Development services started$(NC)"

docker-down:
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-logs:
	@echo "$(BLUE)Showing Docker logs...$(NC)"
	docker-compose logs -f

docker-clean:
	@echo "$(BLUE)Cleaning Docker resources...$(NC)"
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "$(GREEN)✓ Docker resources cleaned$(NC)"

# Monitoring
monitoring-up:
	@echo "$(BLUE)Starting monitoring stack...$(NC)"
	docker-compose --profile monitoring up -d
	@echo "$(GREEN)✓ Monitoring stack started$(NC)"
	@echo "$(YELLOW)Prometheus: http://localhost:9090$(NC)"
	@echo "$(YELLOW)Grafana: http://localhost:3000 (admin/localagent123)$(NC)"

# Deployment
deploy-dev:
	@echo "$(BLUE)Deploying to development environment...$(NC)"
	@export IMAGE_TAG=$(IMAGE_TAG) && \
		docker-compose -f docker-compose.yml up -d
	@echo "$(GREEN)✓ Deployed to development$(NC)"

deploy-staging:
	@echo "$(BLUE)Deploying to staging environment...$(NC)"
	@export IMAGE_TAG=$(IMAGE_TAG) && \
		export DEPLOYMENT_ENV=staging && \
		./scripts/deploy-production.sh --image-tag $(IMAGE_TAG)
	@echo "$(GREEN)✓ Deployed to staging$(NC)"

deploy-prod:
	@echo "$(BLUE)Deploying to production environment...$(NC)"
	@if [ -z "$(IMAGE_TAG)" ] || [ "$(IMAGE_TAG)" = "latest" ]; then \
		echo "$(RED)ERROR: Specific IMAGE_TAG required for production deployment$(NC)"; \
		exit 1; \
	fi
	@export IMAGE_TAG=$(IMAGE_TAG) && \
		export DEPLOYMENT_ENV=production && \
		./scripts/deploy-production.sh --image-tag $(IMAGE_TAG)
	@echo "$(GREEN)✓ Deployed to production$(NC)"

rollback:
	@echo "$(YELLOW)Rolling back production deployment...$(NC)"
	./scripts/deploy-production.sh --rollback
	@echo "$(GREEN)✓ Rollback completed$(NC)"

# Installation
install-local:
	@echo "$(BLUE)Installing LocalAgent locally...$(NC)"
	./scripts/install.sh
	@echo "$(GREEN)✓ LocalAgent installed locally$(NC)"

# Quality assurance
check: format lint type-check test
	@echo "$(GREEN)✓ All quality checks passed$(NC)"

pre-commit:
	@echo "$(BLUE)Running pre-commit checks...$(NC)"
	@. .venv/bin/activate && \
		black --check app/ scripts/ tests/ && \
		isort --check-only app/ scripts/ tests/ && \
		pylint app/ && \
		mypy app/ && \
		pytest tests/ -x -q
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

# Cleanup
clean:
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf .coverage htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf logs/*.log
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

# Health checks
health-check:
	@echo "$(BLUE)Running health checks...$(NC)"
	@if docker ps | grep -q localagent; then \
		docker exec localagent-cli localagent providers && \
		echo "$(GREEN)✓ LocalAgent is healthy$(NC)"; \
	else \
		echo "$(YELLOW)LocalAgent containers not running$(NC)"; \
	fi

# Development workflow helpers
dev-start: docker-up
	@echo "$(GREEN)LocalAgent development environment is ready!$(NC)"
	@echo ""
	@echo "$(BLUE)Quick commands:$(NC)"
	@echo "  Interactive mode: docker exec -it localagent-cli localagent"
	@echo "  Check providers:  docker exec -it localagent-cli localagent providers"
	@echo "  View logs:       docker-compose logs -f"

dev-stop: docker-down
	@echo "$(GREEN)Development environment stopped$(NC)"

# Full development cycle
dev-cycle: clean install test lint docker-build docker-up
	@echo "$(GREEN)✓ Full development cycle completed$(NC)"

# Release preparation
pre-release: clean check security docs
	@echo "$(GREEN)✓ Pre-release checks completed successfully!$(NC)"
	@echo "$(YELLOW)Ready for release. Don't forget to:$(NC)"
	@echo "  1. Update version in setup files"
	@echo "  2. Create git tag"
	@echo "  3. Push to trigger CI/CD pipeline"

# Version management
version:
	@echo "$(BLUE)LocalAgent Version Information$(NC)"
	@echo "=============================="
	@echo "Registry: $(REGISTRY)"
	@echo "Image Tag: $(IMAGE_TAG)"
	@echo "Python Version: $(PYTHON_VERSION)"
	@if [ -f "app/__init__.py" ]; then \
		echo "App Version: $$(grep -E '__version__' app/__init__.py | cut -d'=' -f2 | tr -d ' \"')"; \
	fi
	@echo "Git Commit: $$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
	@echo "Git Branch: $$(git branch --show-current 2>/dev/null || echo 'N/A')"

# Comprehensive pipeline
pipeline: clean install test lint type-check security docker-build
	@echo "$(GREEN)✓ Complete CI pipeline executed successfully$(NC)"

# Config helpers
config-import:
	@echo "$(BLUE)Importing example LocalAgent configuration...$(NC)"
	@bash scripts/import-config
	@echo "$(GREEN)✓ Configuration import finished$(NC)"
