# Docker Deployment Guide for LocalAgent CLI with Autocomplete

## Quick Start

### 1. Build and Run

```bash
# Build the Docker image with autocomplete
make -f Makefile.autocomplete build

# Start all services (Ollama, Redis, CLI)
make -f Makefile.autocomplete run

# Or use docker-compose directly
docker-compose -f docker-compose.cli-autocomplete.yml up -d
```

### 2. Attach to Interactive CLI

```bash
# Attach to running container
docker attach localagent-cli-autocomplete

# Or start a new interactive session
docker run -it --rm \
  --network localagent-network \
  localagent:cli-autocomplete
```

## Architecture

```
┌─────────────────────────────────────────┐
│     LocalAgent CLI with Autocomplete     │
│                                          │
│  ┌────────────┐  ┌──────────────────┐  │
│  │ Autocomplete│  │ Command Intel    │  │
│  │ History Mgr │  │ Engine          │  │
│  └────────────┘  └──────────────────┘  │
│         │               │                │
│         └───────┬───────┘                │
│                 │                        │
│       ┌─────────▼──────────┐            │
│       │  Secure Storage    │            │
│       │  (Encrypted)       │            │
│       └────────────────────┘            │
└─────────────────────────────────────────┘
           │              │
           ▼              ▼
    ┌──────────┐    ┌──────────┐
    │  Redis   │    │  Ollama  │
    │  Cache   │    │  LLM     │
    └──────────┘    └──────────┘
```

## Docker Images

### Production Image
- **Base**: `python:3.11-slim`
- **Size**: ~250MB
- **Features**: Full autocomplete, encryption, multi-provider support

### Files
- `docker/Dockerfile.cli-autocomplete` - Multi-stage Dockerfile
- `docker-compose.cli-autocomplete.yml` - Complete stack configuration
- `docker/entrypoint-autocomplete.sh` - Container initialization
- `docker/config/autocomplete_config.yaml` - Default configuration

## Environment Variables

### Required
```bash
# Redis connection
REDIS_URL=redis://redis:6379/0

# Ollama connection
OLLAMA_BASE_URL=http://ollama:11434
```

### Autocomplete Configuration
```bash
# Enable/disable autocomplete
LOCALAGENT_AUTOCOMPLETE_ENABLED=true

# Security
LOCALAGENT_AUTOCOMPLETE_ENCRYPT=true

# History settings
LOCALAGENT_AUTOCOMPLETE_MAX_HISTORY=10000
LOCALAGENT_AUTOCOMPLETE_HISTORY_RETENTION_DAYS=30

# Fuzzy matching
LOCALAGENT_AUTOCOMPLETE_FUZZY=true
LOCALAGENT_AUTOCOMPLETE_FUZZY_THRESHOLD=0.6

# Performance
LOCALAGENT_AUTOCOMPLETE_CACHE_TTL=300
```

### Optional API Providers
```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
PERPLEXITY_API_KEY=pplx-...
```

## Volumes

### Persistent Data
```yaml
volumes:
  localagent-autocomplete:   # History and encryption keys
  localagent-config:         # Configuration files
  localagent-cache:          # Performance cache
  localagent-logs:           # Application logs
  redis-data:                # Redis persistence
  ollama-data:               # Ollama models
```

### Volume Locations (Inside Container)
- `/home/localagent/.localagent` - User config and history
- `/app/config` - Application configuration
- `/app/.cache` - Cache directory
- `/app/logs` - Log files

## Commands

### Using Makefile

```bash
# Core operations
make -f Makefile.autocomplete build      # Build image
make -f Makefile.autocomplete run        # Start services
make -f Makefile.autocomplete stop       # Stop services
make -f Makefile.autocomplete clean      # Remove everything

# Testing
make -f Makefile.autocomplete test       # Run tests
make -f Makefile.autocomplete demo       # Run demo

# Maintenance
make -f Makefile.autocomplete logs       # View logs
make -f Makefile.autocomplete shell      # Open shell
make -f Makefile.autocomplete stats      # Show statistics

# History management
make -f Makefile.autocomplete backup-history    # Backup history
make -f Makefile.autocomplete restore-history   # Restore from backup
make -f Makefile.autocomplete clean-history     # Clear history

# Development
make -f Makefile.autocomplete dev-run    # Run with mounted source
```

### Using Docker Compose

```bash
# Start services
docker-compose -f docker-compose.cli-autocomplete.yml up -d

# View logs
docker-compose -f docker-compose.cli-autocomplete.yml logs -f

# Stop services
docker-compose -f docker-compose.cli-autocomplete.yml down

# Remove volumes
docker-compose -f docker-compose.cli-autocomplete.yml down -v
```

### Direct Docker Commands

```bash
# Interactive session
docker run -it --rm \
  --network localagent-network \
  -v localagent-autocomplete:/home/localagent/.localagent \
  localagent:cli-autocomplete

# Execute specific command
docker exec localagent-cli-autocomplete \
  python -m app.cli workflow "test command"

# View autocomplete statistics
docker exec localagent-cli-autocomplete \
  python -c "from app.cli.intelligence.autocomplete_history import AutocompleteHistoryManager; \
  m = AutocompleteHistoryManager(); \
  print(m.get_statistics())"
```

## Security Considerations

### 1. Encryption
- History files encrypted with AES-256
- Keys stored with 600 permissions
- Automatic key generation on first run

### 2. Data Sanitization
- API keys automatically redacted
- Passwords masked in history
- Sensitive patterns filtered

### 3. Container Security
- Non-root user (`localagent`)
- Minimal base image
- No unnecessary packages
- Read-only root filesystem compatible

### 4. Network Security
- Internal Docker network
- No exposed ports for CLI
- Redis/Ollama on separate containers

## Performance Tuning

### Redis Configuration
```yaml
command: redis-server \
  --maxmemory 256mb \
  --maxmemory-policy allkeys-lru
```

### Resource Limits
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Cache Settings
- TTL: 300 seconds (5 minutes)
- Max cache size: 1000 entries
- LRU eviction policy

## Troubleshooting

### Issue: Autocomplete not working

```bash
# Check if modules load correctly
docker exec localagent-cli-autocomplete python -c \
  "from app.cli.intelligence.autocomplete_history import AutocompleteHistoryManager; \
   print('OK')"

# Check history file
docker exec localagent-cli-autocomplete ls -la /home/localagent/.localagent/
```

### Issue: Slow suggestions

```bash
# Monitor performance
docker exec localagent-cli-autocomplete python -c \
  "import time; \
   from app.cli.intelligence.autocomplete_history import AutocompleteHistoryManager; \
   m = AutocompleteHistoryManager(); \
   start = time.time(); \
   m.get_suggestions('git'); \
   print(f'Time: {(time.time()-start)*1000:.2f}ms')"
```

### Issue: History not persisting

```bash
# Check volume mounting
docker inspect localagent-cli-autocomplete | grep -A 5 Mounts

# Check permissions
docker exec localagent-cli-autocomplete \
  stat /home/localagent/.localagent/autocomplete_history.json
```

### Issue: Terminal display problems

```bash
# Set proper terminal
export TERM=xterm-256color

# Or in docker run
docker run -it --rm \
  -e TERM=xterm-256color \
  -e COLUMNS=120 \
  -e LINES=40 \
  localagent:cli-autocomplete
```

## Development Mode

### Mount Source Code
```bash
docker run -it --rm \
  -v $(PWD)/app:/app/app:ro \
  -v $(PWD)/scripts:/app/scripts:ro \
  -v $(PWD)/tests:/app/tests:ro \
  -v localagent-autocomplete-dev:/home/localagent/.localagent \
  localagent:cli-autocomplete
```

### Live Reload
```bash
# Install development dependencies
docker exec localagent-cli-autocomplete \
  pip install watchdog

# Run with auto-reload
docker exec localagent-cli-autocomplete \
  python -m app.cli --reload
```

## Monitoring

### Health Checks
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "from app.cli.intelligence.autocomplete_history import AutocompleteHistoryManager; print('OK')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Metrics
```bash
# Performance metrics
make -f Makefile.autocomplete monitor

# Usage statistics
make -f Makefile.autocomplete stats

# Container metrics
docker stats localagent-cli-autocomplete
```

## Backup and Recovery

### Backup History
```bash
# Automated backup
make -f Makefile.autocomplete backup-history

# Manual backup
docker cp localagent-cli-autocomplete:/home/localagent/.localagent/autocomplete_history.json ./backup.json
```

### Restore History
```bash
# Restore from backup
make -f Makefile.autocomplete restore-history

# Manual restore
docker cp ./backup.json localagent-cli-autocomplete:/home/localagent/.localagent/autocomplete_history.json
```

## Production Deployment

### 1. Use Docker Secrets
```yaml
secrets:
  openai_key:
    external: true
  gemini_key:
    external: true

services:
  localagent-cli-autocomplete:
    secrets:
      - openai_key
      - gemini_key
```

### 2. Enable Swarm Mode
```bash
docker stack deploy -c docker-compose.cli-autocomplete.yml localagent
```

### 3. Configure Logging
```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

### 4. Set Up Monitoring
- Prometheus metrics endpoint
- Grafana dashboards
- Alert rules for performance

## Kubernetes Deployment

See `k8s/autocomplete/` directory for:
- `deployment.yaml` - Kubernetes deployment
- `configmap.yaml` - Configuration
- `secret.yaml` - API keys
- `pvc.yaml` - Persistent volume claims
- `service.yaml` - Service definition

## Support

For issues or questions:
1. Check logs: `make -f Makefile.autocomplete logs`
2. Run diagnostics: `make -f Makefile.autocomplete test`
3. Review documentation: `docs/CLI_AUTOCOMPLETE_IMPLEMENTATION.md`

---

*Last Updated: 2025-08-27*