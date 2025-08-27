# Docker Network Subnet Manager

A comprehensive solution for intelligent Docker network subnet management, providing automated subnet allocation, conflict detection, and docker-compose.yml file management.

## 🚀 Overview

The Docker Subnet Manager provides both Python and Bash implementations for:

- **Subnet Scanning**: Automatically discovers existing Docker network subnets
- **Intelligent Allocation**: Finds next available subnet in the 172.16.0.0/12 private range
- **Compose Integration**: Updates docker-compose.yml files or generates override files
- **Conflict Prevention**: Validates subnet assignments to prevent IP conflicts
- **Edge Case Handling**: Manages subnet exhaustion and provides alternative solutions

## 📁 Files

```
scripts/
├── docker-subnet-manager.py    # Full-featured Python implementation
├── docker-subnet-manager.sh    # Bash implementation for lightweight usage
└── test_subnet_manager.py      # Comprehensive test suite
```

## 🔧 Installation & Dependencies

### Python Implementation

**Required:**
- Python 3.7+
- Docker (for network scanning)

**Optional (for enhanced functionality):**
- `pyyaml` - Better YAML parsing
- `docker` Python library - Enhanced Docker integration

```bash
# Install Python dependencies
pip3 install pyyaml docker

# Make scripts executable
chmod +x scripts/docker-subnet-manager.py
chmod +x scripts/docker-subnet-manager.sh
```

### Bash Implementation

**Required:**
- Docker
- `jq` (for JSON parsing)

**Optional:**
- `yq` (for YAML parsing - highly recommended)

```bash
# Ubuntu/Debian
sudo apt-get install jq yq

# macOS
brew install jq yq

# CentOS/RHEL
sudo yum install jq
```

## 🎯 Quick Start

### Interactive Mode (Recommended)

```bash
# Python version
python3 scripts/docker-subnet-manager.py --interactive

# Bash version
scripts/docker-subnet-manager.sh --interactive
```

### Command Line Usage

```bash
# Scan existing networks
python3 scripts/docker-subnet-manager.py --scan

# Find next available subnet
python3 scripts/docker-subnet-manager.py --find-subnet
scripts/docker-subnet-manager.sh --find-subnet 24

# Update docker-compose.yml file
python3 scripts/docker-subnet-manager.py --update-compose ./docker-compose.yml --network mynetwork
scripts/docker-subnet-manager.sh --update-compose ./docker-compose.yml --network mynetwork

# Generate override file
python3 scripts/docker-subnet-manager.py --generate-override ./docker-compose.yml --network mynetwork

# Generate detailed report
python3 scripts/docker-subnet-manager.py --report subnet_analysis.json
```

## 📊 Features & Capabilities

### 1. Network Scanning & Discovery

**Python Implementation:**
```python
from docker_subnet_manager import DockerSubnetManager

manager = DockerSubnetManager()
networks = manager.scan_docker_networks()
```

**Bash Implementation:**
```bash
./scripts/docker-subnet-manager.sh --scan --verbose
```

**Output Example:**
```
Found 7 networks using managed subnets:
  • bridge: 172.17.0.0/16
  • localprogramming_localagent-network: 172.22.0.0/16
  • songnodes_musicdb-backend: 172.28.0.0/16
  • songnodes_musicdb-frontend: 172.18.0.0/16
  • songnodes_musicdb-monitoring: 172.19.0.0/16
  • unifiedworkflow_ai_workflow_engine_net: 172.21.0.0/16
  • webdevelopment_default: 172.20.0.0/16
```

### 2. Intelligent Subnet Allocation

The system automatically finds the next available subnet while avoiding conflicts:

```bash
# Find different subnet sizes
python3 scripts/docker-subnet-manager.py --find-subnet --subnet-size 16
python3 scripts/docker-subnet-manager.py --find-subnet --subnet-size 24

# Bash equivalent
scripts/docker-subnet-manager.sh --find-subnet 16
scripts/docker-subnet-manager.sh --find-subnet 24
```

**Algorithm Features:**
- **Conflict Detection**: Checks against all existing Docker networks
- **Range Validation**: Ensures subnets are within 172.16.0.0/12 range
- **Size Flexibility**: Supports /16, /24, /25, /26, /27, /28 subnet sizes
- **Exhaustion Handling**: Provides alternatives when subnets are exhausted

### 3. Docker Compose Integration

#### Automatic File Updates

```bash
# Update existing docker-compose.yml
python3 scripts/docker-subnet-manager.py \
    --update-compose ./docker-compose.yml \
    --network production-network \
    --subnet-size 24
```

**Before:**
```yaml
version: '3.8'
services:
  web:
    image: nginx

networks:
  production-network:
    driver: bridge
```

**After:**
```yaml
version: '3.8'
services:
  web:
    image: nginx

networks:
  production-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.16.0.0/24
          gateway: 172.16.0.1
```

#### Override File Generation

```bash
# Generate docker-compose.override.yml
python3 scripts/docker-subnet-manager.py \
    --generate-override ./docker-compose.yml \
    --network overlay-network
```

**Generated docker-compose.override.yml:**
```yaml
version: '3.8'

# Auto-generated Docker Compose override for network subnet management
# Generated by: docker-subnet-manager.py
# Timestamp: 2025-08-26T08:57:34

networks:
  overlay-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.23.0.0/16
          gateway: 172.23.0.1
```

### 4. Comprehensive Reporting

```bash
# Generate detailed JSON report
python3 scripts/docker-subnet-manager.py --report detailed_analysis.json
```

**Sample Report:**
```json
{
  "scan_timestamp": "2025-08-26T08:57:34",
  "base_directory": "/home/user/project",
  "management_range": "172.16.0.0/12",
  "statistics": {
    "total_used_subnets": 7,
    "total_possible_16_subnets": 4096,
    "total_possible_24_subnets": 1048576,
    "utilization_16": "0.17%",
    "utilization_24": "0.00%"
  },
  "docker_networks": {
    "bridge": "172.17.0.0/16",
    "localprogramming_localagent-network": "172.22.0.0/16",
    "songnodes_musicdb-backend": "172.28.0.0/16"
  },
  "compose_files_found": [
    "/home/user/project/docker-compose.yml",
    "/home/user/project/docker-compose.dev.yml"
  ],
  "next_available_subnets": {
    "/16": "172.16.0.0/16",
    "/24": "172.16.0.0/24",
    "/25": "172.16.0.0/25",
    "/26": "172.16.0.0/26"
  }
}
```

## 🛡️ Edge Cases & Error Handling

### 1. Subnet Exhaustion

When no subnets are available, the system provides intelligent alternatives:

```bash
# This will show exhaustion handling
python3 scripts/docker-subnet-manager.py --find-subnet --subnet-size 16
```

**Exhaustion Response:**
```
❌ No available /16 subnets found in range 172.16.0.0/12

⚠️ Subnet Exhaustion Solutions:
1. Try smaller subnet sizes:
   ✅ Available /17 subnet: 172.30.0.0/17
   ✅ Available /18 subnet: 172.30.0.0/18

2. Clean up unused Docker networks:
   docker network prune -f

3. Consider alternative private IP ranges:
   • 10.0.0.0/8 (Class A)
   • 192.168.0.0/16 (Class C)
```

### 2. Docker Unavailable

Both implementations gracefully handle Docker unavailability:

```bash
# When Docker is not running
python3 scripts/docker-subnet-manager.py --scan
# Output: "Docker might not be installed or running. Continuing with empty network list."
```

### 3. Invalid Compose Files

The system safely handles malformed YAML files:

```bash
# With invalid docker-compose.yml
python3 scripts/docker-subnet-manager.py --scan
# Logs: "Failed to parse ./docker-compose.yml: Invalid YAML syntax"
```

### 4. Permission Issues

Includes proper error handling for file system permissions and Docker access rights.

## 🧪 Testing & Validation

### Run Test Suite

```bash
# Run comprehensive unit tests
python3 scripts/test_subnet_manager.py

# Run with verbose output
python3 scripts/test_subnet_manager.py --verbose

# Run performance tests
python3 scripts/test_subnet_manager.py --performance

# Run integration tests (requires Docker)
python3 scripts/test_subnet_manager.py --integration
```

### Test Coverage

- **Unit Tests**: Core algorithms and functions
- **Integration Tests**: Docker interaction (when available)
- **Performance Tests**: Subnet allocation with large datasets
- **Error Handling Tests**: Edge cases and failure scenarios
- **Validation Tests**: Network configuration correctness

## 📋 Command Reference

### Python Implementation

```bash
# Basic operations
python3 scripts/docker-subnet-manager.py --scan
python3 scripts/docker-subnet-manager.py --find-subnet
python3 scripts/docker-subnet-manager.py --report [filename]

# File operations
python3 scripts/docker-subnet-manager.py --update-compose FILE --network NAME
python3 scripts/docker-subnet-manager.py --generate-override FILE --network NAME

# Configuration
python3 scripts/docker-subnet-manager.py --base-dir DIR --subnet-size SIZE
python3 scripts/docker-subnet-manager.py --dry-run --verbose

# Interactive mode
python3 scripts/docker-subnet-manager.py --interactive
```

### Bash Implementation

```bash
# Basic operations
scripts/docker-subnet-manager.sh --scan
scripts/docker-subnet-manager.sh --find-subnet [SIZE]
scripts/docker-subnet-manager.sh --report [filename]

# File operations
scripts/docker-subnet-manager.sh --update-compose FILE --network NAME
scripts/docker-subnet-manager.sh --generate-override FILE --network NAME

# Configuration
scripts/docker-subnet-manager.sh --base-dir DIR --subnet-size SIZE
scripts/docker-subnet-manager.sh --dry-run --verbose

# Interactive mode
scripts/docker-subnet-manager.sh --interactive

# Cleanup
scripts/docker-subnet-manager.sh --cleanup
```

## 🔧 Advanced Configuration

### Custom Subnet Ranges

While the default range is 172.16.0.0/12, you can modify the scripts for custom ranges:

**Python:**
```python
# Modify in DockerSubnetManager class
self.private_range = ipaddress.IPv4Network('10.0.0.0/8')  # Use 10.x.x.x range
```

**Bash:**
```bash
# Modify variables at top of script
readonly PRIVATE_RANGE_START="10.0.0.0"
readonly PRIVATE_RANGE_BITS="8"
```

### Integration with CI/CD

```yaml
# GitHub Actions example
- name: Allocate Docker Network Subnet
  run: |
    python3 scripts/docker-subnet-manager.py \
      --update-compose ./docker-compose.yml \
      --network ${{ env.SERVICE_NAME }}-network \
      --dry-run
```

### Docker Compose Template Integration

```bash
# Generate network configs for multiple environments
for env in dev staging prod; do
  python3 scripts/docker-subnet-manager.py \
    --generate-override docker-compose.${env}.yml \
    --network ${env}-network
done
```

## 🚀 Use Cases

### 1. Multi-Project Development

When working with multiple Docker projects, avoid subnet conflicts:

```bash
# Project 1
cd /path/to/project1
python3 ../scripts/docker-subnet-manager.py --update-compose . --network proj1-net

# Project 2  
cd /path/to/project2
python3 ../scripts/docker-subnet-manager.py --update-compose . --network proj2-net
```

### 2. Microservices Architecture

Allocate dedicated subnets for each microservice:

```bash
for service in auth user payment notification; do
  python3 scripts/docker-subnet-manager.py \
    --generate-override docker-compose.yml \
    --network ${service}-network
done
```

### 3. Environment Isolation

Separate network ranges for different environments:

```bash
# Development (use /24 subnets)
python3 scripts/docker-subnet-manager.py --subnet-size 24 --update-compose docker-compose.dev.yml --network dev-net

# Production (use /16 subnets for more IPs)
python3 scripts/docker-subnet-manager.py --subnet-size 16 --update-compose docker-compose.prod.yml --network prod-net
```

### 4. Network Infrastructure Audit

Generate comprehensive reports for infrastructure documentation:

```bash
# Weekly network audit
python3 scripts/docker-subnet-manager.py --report "network-audit-$(date +%Y%m%d).json"

# Quick status check
scripts/docker-subnet-manager.sh --scan
```

## 🐛 Troubleshooting

### Common Issues

**1. "No available subnets found"**
```bash
# Check current usage
python3 scripts/docker-subnet-manager.py --scan --verbose

# Try smaller subnet size
python3 scripts/docker-subnet-manager.py --find-subnet --subnet-size 24

# Clean up unused networks
docker network prune -f
```

**2. "Docker daemon not running"**
```bash
# Start Docker
sudo systemctl start docker

# Or run in dry-run mode for testing
python3 scripts/docker-subnet-manager.py --dry-run --scan
```

**3. "Permission denied on compose file"**
```bash
# Check file permissions
ls -la docker-compose.yml

# Fix permissions
chmod 644 docker-compose.yml
```

**4. "YAML parsing errors"**
```bash
# Install yq for better YAML support
sudo apt-get install yq

# Validate YAML syntax
yq eval '.' docker-compose.yml
```

## 📈 Performance Considerations

### Large-Scale Deployments

For environments with hundreds of networks:

```bash
# Use caching to avoid repeated Docker API calls
python3 scripts/docker-subnet-manager.py --scan > network_cache.json

# Generate reports periodically rather than on-demand
crontab -e
# Add: 0 2 * * * /path/to/scripts/docker-subnet-manager.py --report weekly-report.json
```

### Memory Usage

The Python implementation is optimized for memory usage:
- Subnet calculations use generators where possible
- Network data is processed in streams
- Temporary files are cleaned up automatically

## 🔐 Security Considerations

### File Permissions

```bash
# Secure script permissions
chmod 750 scripts/docker-subnet-manager.py
chmod 750 scripts/docker-subnet-manager.sh

# Secure backup files
find . -name "*.backup.*" -exec chmod 600 {} \;
```

### Docker Socket Access

The scripts require Docker socket access. In production:

```bash
# Add user to docker group (less secure but convenient)
sudo usermod -aG docker $USER

# Or use Docker context for remote access
docker context create remote --docker host=ssh://user@remote-host
docker context use remote
```

### Network Isolation

When allocating subnets for sensitive applications:

```bash
# Use smaller, isolated subnets
python3 scripts/docker-subnet-manager.py --subnet-size 26 --network secure-app-net

# Document security boundaries
python3 scripts/docker-subnet-manager.py --report security-audit.json
```

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone [repository-url]
cd docker-subnet-manager

# Install development dependencies
pip3 install pytest pyyaml docker

# Run tests
python3 scripts/test_subnet_manager.py

# Run with coverage
python3 -m pytest scripts/test_subnet_manager.py --cov=docker_subnet_manager
```

### Adding Features

1. **Python Implementation**: Add to `DockerSubnetManager` class
2. **Bash Implementation**: Add functions to main script
3. **Tests**: Add corresponding test cases
4. **Documentation**: Update this README

### Code Quality

```bash
# Format Python code
black scripts/docker-subnet-manager.py

# Lint bash script
shellcheck scripts/docker-subnet-manager.sh

# Run security analysis
bandit scripts/docker-subnet-manager.py
```

## 📄 License

This project is part of the LocalProgramming UnifiedWorkflow system and follows the project's licensing terms.

## 🆘 Support

For issues, questions, or contributions:

1. Check the troubleshooting section above
2. Review test cases for usage examples  
3. Run with `--verbose` flag for detailed logging
4. Generate reports for analysis: `--report debug-report.json`

---

*Generated by Docker Network Subnet Manager - Intelligent subnet allocation for Docker Compose environments*