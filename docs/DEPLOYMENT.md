# LocalAgent Deployment Guide

This comprehensive guide covers all deployment scenarios for LocalAgent, from local development to production environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation Methods](#installation-methods)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Development Environment](#development-environment)
- [Monitoring & Observability](#monitoring--observability)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Local Installation (Recommended for Users)

```bash
# One-liner installation
curl -fsSL https://raw.githubusercontent.com/zvirb/LocalAgent/main/scripts/install.sh | bash

# Or clone and install manually
git clone https://github.com/zvirb/LocalAgent.git
cd LocalAgent
./scripts/install.sh
```

### 2. Docker Installation (Recommended for Containers)

```bash
# Start LocalAgent with all services
docker-compose up -d

# Interactive mode
docker exec -it localagent-cli localagent

# Direct completion
docker exec -it localagent-cli localagent complete "Hello, world!"
```

### 3. Development Setup

```bash
# Setup development environment
make setup-dev

# Start development services
make dev-start

# Run tests
make test
```

---

## Installation Methods

### Method 1: Automated Script Installation

The easiest way to install LocalAgent with all dependencies:

```bash
# Download and run installation script
curl -fsSL https://raw.githubusercontent.com/zvirb/LocalAgent/main/scripts/install.sh | bash

# With options
curl -fsSL https://raw.githubusercontent.com/zvirb/LocalAgent/main/scripts/install.sh | bash -s -- --skip-ollama
```

**What the script does:**
- Installs Python dependencies
- Downloads and installs Ollama
- Sets up the CLI command globally
- Creates default configuration
- Runs health checks

### Method 2: Manual Installation

For more control over the installation process:

```bash
# 1. Clone repository
git clone https://github.com/zvirb/LocalAgent.git
cd LocalAgent

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Ollama separately
curl -fsSL https://ollama.com/install.sh | sh

# 5. Make CLI accessible
chmod +x scripts/localagent
ln -s $(pwd)/scripts/localagent /usr/local/bin/localagent
```

### Method 3: Package Installation (Future)

```bash
# Via pip (when published to PyPI)
pip install localagent

# Via Homebrew (macOS)
brew install localagent

# Via apt (Ubuntu/Debian)
sudo apt install localagent
```

---

## Docker Deployment

### Basic Docker Setup

1. **Clone and Start Services**
   ```bash
   git clone https://github.com/zvirb/LocalAgent.git
   cd LocalAgent
   docker-compose up -d
   ```

2. **Use LocalAgent**
   ```bash
   # Interactive mode
   docker exec -it localagent-cli localagent
   
   # Direct completion
   docker exec -it localagent-cli localagent complete "Explain quantum computing"
   
   # Check providers
   docker exec -it localagent-cli localagent providers
   ```

### Docker Compose Configuration

The `docker-compose.yml` includes:

- **LocalAgent CLI**: Main application container
- **Ollama**: Local LLM inference server
- **Redis**: Memory and coordination backend
- **Prometheus**: Metrics collection (optional)
- **Grafana**: Monitoring dashboards (optional)

### Environment Variables

Configure LocalAgent using environment variables:

```bash
# Create .env file
cat > .env << EOF
# Provider API Keys (optional)
OPENAI_API_KEY=sk-your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here
PERPLEXITY_API_KEY=your-perplexity-key-here

# Service URLs
OLLAMA_BASE_URL=http://ollama:11434
REDIS_URL=redis://redis:6379/0

# Logging
LOCALAGENT_LOG_LEVEL=INFO
EOF
```

### Docker Commands Reference

```bash
# Basic operations
make docker-build    # Build image
make docker-up       # Start services
make docker-down     # Stop services
make docker-logs     # View logs

# Development
make docker-up-dev   # Start with development overrides
make monitoring-up   # Start with monitoring stack

# Maintenance
make docker-clean    # Clean up resources
make health-check    # Check service health
```

---

## Production Deployment

### Prerequisites

- **System Requirements**: 4GB+ RAM, 10GB+ disk space
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Network Access**: For pulling models and images

### Production Deployment Options

#### Option 1: Blue-Green Deployment (Recommended)

Automated blue-green deployment with zero downtime:

```bash
# Deploy new version
export IMAGE_TAG=v1.2.0
./scripts/deploy-production.sh --image-tag v1.2.0

# Rollback if needed
./scripts/deploy-production.sh --rollback
```

**Features:**
- Zero-downtime deployment
- Automatic health checks
- Traffic switching
- Rollback capability
- Backup and restore

#### Option 2: Standard Docker Compose

For simpler production setups:

```bash
# Create production environment file
cat > .env.production << EOF
DEPLOYMENT_ENV=production
IMAGE_TAG=v1.2.0
LOCALAGENT_LOG_LEVEL=INFO

# API Keys
OPENAI_API_KEY=${OPENAI_API_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}
PERPLEXITY_API_KEY=${PERPLEXITY_API_KEY}
EOF

# Deploy
docker-compose --env-file .env.production up -d
```

#### Option 3: Kubernetes Deployment

```yaml
# k8s/localagent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: localagent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: localagent
  template:
    metadata:
      labels:
        app: localagent
    spec:
      containers:
      - name: localagent
        image: ghcr.io/zvirb/localagent:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

### Security Considerations

1. **API Key Management**
   ```bash
   # Use Docker secrets (recommended)
   docker secret create openai_key - <<< "sk-your-key"
   
   # Or environment variables with proper file permissions
   chmod 600 .env.production
   ```

2. **Network Security**
   ```yaml
   # docker-compose.yml network configuration
   networks:
     localagent-network:
       driver: bridge
       internal: true  # No external access
   ```

3. **Resource Limits**
   ```yaml
   services:
     localagent:
       deploy:
         resources:
           limits:
             cpus: '2.0'
             memory: 2G
   ```

### Production Configuration

Create optimized production configuration:

```yaml
# config/production.yaml
providers:
  ollama:
    base_url: "http://ollama:11434"
    timeout: 30
    max_retries: 3
    enabled: true
  
  openai:
    timeout: 30
    max_retries: 3
    rate_limit:
      requests_per_minute: 100
      tokens_per_minute: 50000
    enabled: true

logging:
  level: "INFO"
  format: "json"
  file: "/app/logs/localagent.log"

security:
  use_keyring: false  # Not available in containers
  encrypt_storage: true

monitoring:
  metrics_enabled: true
  health_check_interval: 30

workflow:
  parallel_execution: true
  max_agents: 5
  timeout: 300
```

---

## Development Environment

### Setup Development Environment

```bash
# One-command setup
make setup-dev

# Or manual setup
./scripts/setup-dev.sh
```

This creates:
- Python virtual environment
- Development dependencies
- Pre-commit hooks
- VS Code configuration
- Docker development overrides

### Development Workflow

```bash
# Start development environment
make dev-start

# Code and test cycle
make format        # Format code
make lint         # Run linting
make test         # Run tests
make type-check   # Type checking

# Full quality check
make check

# Build and test Docker image
make docker-build
make docker-up

# Clean up
make clean
```

### Development Tools

The development setup includes:

- **Testing**: pytest, coverage, async testing
- **Code Quality**: black, isort, pylint, mypy
- **Security**: bandit, safety
- **Development**: ipython, jupyter, debugpy
- **Documentation**: sphinx

### VS Code Integration

Configuration for VS Code includes:
- Python interpreter path
- Debugging configuration
- Testing integration
- Code formatting on save
- Extensions recommendations

---

## Monitoring & Observability

### Metrics Collection

LocalAgent provides comprehensive metrics via Prometheus:

```bash
# Start with monitoring
make monitoring-up

# Access dashboards
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (admin/localagent123)
```

### Key Metrics

- **Request Metrics**: Count, duration, error rate by provider
- **Token Usage**: Consumption tracking for cost analysis
- **Provider Health**: Availability and response times
- **System Metrics**: Memory, CPU, disk usage
- **Custom Metrics**: Workflow execution, agent performance

### Logging

Structured logging with multiple output formats:

```python
# Example log output
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "localagent.providers.openai",
  "message": "Completion request successful",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "tokens": 150,
  "duration": 1.2,
  "request_id": "req_123456"
}
```

### Health Checks

Comprehensive health checking:

```bash
# Manual health check
make health-check

# Check specific components
docker exec localagent-cli localagent providers
curl http://localhost:8000/health  # If web interface enabled
```

### Alerting

Configure alerts for critical issues:

```yaml
# prometheus/alert_rules.yml
groups:
  - name: localagent
    rules:
      - alert: HighErrorRate
        expr: rate(localagent_requests_total{status="error"}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
```

---

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Issues

```bash
# Check Ollama service
docker exec -it ollama-container ollama list
curl http://localhost:11434/api/tags

# Restart Ollama
docker restart ollama-container
```

#### 2. Memory Issues

```bash
# Check memory usage
docker stats

# Increase memory limits
# Edit docker-compose.yml memory limits
```

#### 3. API Key Issues

```bash
# Verify API key format
echo $OPENAI_API_KEY | head -c 20

# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

#### 4. Permission Issues

```bash
# Fix file permissions
sudo chown -R $(whoami):$(whoami) ~/.localagent
chmod +x scripts/localagent
```

### Debugging Commands

```bash
# View logs
docker-compose logs -f localagent
docker-compose logs -f ollama

# Debug mode
LOCALAGENT_DEBUG=true docker-compose up

# Container shell access
docker exec -it localagent-cli bash

# Test providers individually
docker exec -it localagent-cli localagent providers
docker exec -it localagent-cli localagent complete "test" --provider ollama
```

### Performance Optimization

```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Optimize Ollama
docker exec ollama-container ollama show llama3.2  # Check model size

# Clean up Docker
docker system prune -f
docker volume prune -f
```

### Log Analysis

```bash
# Find errors
docker logs localagent-cli 2>&1 | grep ERROR

# Monitor API calls
docker logs localagent-cli 2>&1 | grep "provider.*request"

# Performance analysis
docker logs localagent-cli 2>&1 | grep "duration" | tail -20
```

---

## Support and Resources

### Documentation
- [Technical Implementation Guide](docs/TECHNICAL_IMPLEMENTATION_GUIDE.md)
- [API Documentation](docs/API_DOCUMENTATION.md)
- [Architecture Overview](docs/SYSTEM_ARCHITECTURE.md)

### Community
- GitHub Issues: Report bugs and request features
- Discussions: Community support and questions
- Contributing: See CONTRIBUTING.md

### Professional Support
- Commercial support available for enterprise deployments
- Custom integrations and consulting services
- Training and workshops

---

## Appendices

### A. Configuration Reference

Complete configuration options available in [config/](config/) directory.

### B. API Reference

REST API endpoints and WebSocket connections documented in API docs.

### C. Security Guidelines

Security best practices and compliance information.

### D. Performance Tuning

Optimization guidelines for different deployment scales.

---

*This deployment guide is continuously updated. Check the latest version in the repository.*