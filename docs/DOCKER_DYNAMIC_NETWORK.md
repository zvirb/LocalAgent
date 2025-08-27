# Docker Dynamic Network Assignment

## Overview

This solution provides automatic dynamic network subnet assignment for Docker Compose deployments, preventing the common "Pool overlaps with other one on this address space" error.

## Problem Solved

Docker uses the 172.16.0.0/12 private IP range for bridge networks. When multiple projects use hardcoded subnets (like 172.20.0.0/16), conflicts occur when trying to create networks with overlapping IP ranges.

## Solution Components

### 1. `docker-dynamic-network.py`
Core Python script that:
- Scans existing Docker networks to identify used subnets
- Finds next available subnet in the 172.16.0.0/12 range
- Updates docker-compose.yml files with available subnets
- Generates override files for complex scenarios
- Provides network usage statistics

### 2. `docker-compose-auto`
Bash wrapper script that:
- Integrates dynamic network assignment with docker-compose commands
- Automatically generates override files when needed
- Provides a drop-in replacement for docker-compose

## Installation

```bash
# Make scripts executable
chmod +x scripts/docker-dynamic-network.py
chmod +x scripts/docker-compose-auto

# Install Python dependencies (if needed)
pip3 install pyyaml
```

## Usage

### Basic Commands

#### Check Network Status
```bash
# Show current network usage
python3 scripts/docker-dynamic-network.py --status

# Using wrapper
./scripts/docker-compose-auto --status
```

#### Find Available Subnet
```bash
# Find available /16 subnet
python3 scripts/docker-dynamic-network.py --find-subnet 16

# Find available /24 subnet (smaller)
python3 scripts/docker-dynamic-network.py --find-subnet 24
```

#### Update Compose File
```bash
# Update docker-compose.yml with available subnet
python3 scripts/docker-dynamic-network.py --update-compose docker-compose.yml

# Update specific network
python3 scripts/docker-dynamic-network.py --update-compose docker-compose.yml --network mynetwork

# Update without backup
python3 scripts/docker-dynamic-network.py --update-compose docker-compose.yml --no-backup
```

#### Generate Override File
```bash
# Generate docker-compose.override.yml
python3 scripts/docker-dynamic-network.py --generate-override docker-compose.yml
```

### Using the Wrapper Script

The wrapper script (`docker-compose-auto`) provides seamless integration:

```bash
# Start services with automatic network assignment
./scripts/docker-compose-auto up -d

# Stop services
./scripts/docker-compose-auto down

# View logs
./scripts/docker-compose-auto logs -f

# Any docker-compose command works
./scripts/docker-compose-auto ps
./scripts/docker-compose-auto restart
```

## How It Works

### 1. Network Discovery
The script queries Docker to find all existing networks and their subnets:
```python
docker network ls
docker network inspect [network_name]
```

### 2. Subnet Allocation Algorithm
- Scans the 172.16.0.0/12 range (172.16.0.0 - 172.31.255.255)
- Identifies used subnets
- Finds first available subnet of requested size
- Supports /16 through /28 prefix lengths

### 3. File Modification
When updating compose files:
1. Creates backup (unless --no-backup specified)
2. Parses YAML structure
3. Updates network configuration with available subnet
4. Preserves all other settings

### 4. Override Generation
For complex scenarios, generates docker-compose.override.yml:
- Keeps original compose file unchanged
- Adds network configuration in override
- Docker Compose automatically merges both files

## Integration Patterns

### Pattern 1: Manual Update
Update compose file once, then use normally:
```bash
# One-time update
python3 scripts/docker-dynamic-network.py --update-compose docker-compose.yml

# Use normally
docker compose up -d
```

### Pattern 2: Override File
Keep original compose clean, use override:
```bash
# Generate override
python3 scripts/docker-dynamic-network.py --generate-override docker-compose.yml

# Docker automatically uses both files
docker compose up -d
```

### Pattern 3: Wrapper Script
Replace docker-compose with wrapper:
```bash
# Instead of: docker compose up -d
./scripts/docker-compose-auto up -d
```

### Pattern 4: CI/CD Integration
```yaml
# In CI/CD pipeline
steps:
  - name: Assign Dynamic Network
    run: |
      python3 scripts/docker-dynamic-network.py \
        --update-compose docker-compose.yml \
        --network production-network
  
  - name: Deploy Services
    run: docker compose up -d
```

## Advanced Features

### Custom Subnet Sizes
```bash
# Use smaller subnets for more networks
python3 scripts/docker-dynamic-network.py --find-subnet 24  # 256 IPs
python3 scripts/docker-dynamic-network.py --find-subnet 25  # 128 IPs
python3 scripts/docker-dynamic-network.py --find-subnet 26  # 64 IPs
```

### Multiple Networks
The script handles compose files with multiple networks:
```yaml
networks:
  frontend:  # Will get 172.16.0.0/16
    driver: bridge
  backend:   # Will get 172.23.0.0/16
    driver: bridge
  database:  # Will get 172.24.0.0/16
    driver: bridge
```

### Network Usage Analytics
```bash
python3 scripts/docker-dynamic-network.py --status
```
Output shows:
- Total IP usage percentage
- List of used subnets
- Next available subnets of different sizes
- Network count

## Troubleshooting

### Error: No available subnets
**Cause**: All subnets in 172.16.0.0/12 range are used
**Solution**: 
- Use smaller subnet sizes (--find-subnet 24)
- Clean up unused Docker networks: `docker network prune`
- Consider using different IP ranges

### Error: Cannot connect to Docker
**Cause**: Docker daemon not running or permission issues
**Solution**:
- Start Docker: `sudo systemctl start docker`
- Add user to docker group: `sudo usermod -aG docker $USER`

### YAML formatting changes
**Cause**: Python YAML library reformats file
**Solution**: 
- Use --generate-override to keep original unchanged
- Backups are created automatically

## Best Practices

1. **Use Override Files**: Keep original compose files clean
2. **Regular Cleanup**: Run `docker network prune` periodically
3. **Consistent Sizing**: Use same subnet size across projects
4. **Document Networks**: Add comments explaining network purpose
5. **Version Control**: Commit override files for reproducibility

## Architecture Decision

### Why 172.16.0.0/12?
- Docker's default range for bridge networks
- Provides 1,048,576 IP addresses
- Avoids conflicts with common corporate networks
- RFC 1918 private address space

### Why Python + Bash?
- **Python**: Robust YAML/JSON parsing, IP address math
- **Bash**: Universal availability, easy integration
- **Combined**: Best of both worlds

## Security Considerations

1. **Network Isolation**: Each network is isolated by default
2. **IP Spoofing**: Private IPs not routable on internet
3. **Container Communication**: Only containers on same network can communicate
4. **File Backups**: Automatic backups prevent data loss

## Performance Impact

- **Network Creation**: One-time operation, no runtime impact
- **IP Assignment**: Kernel-level, negligible overhead
- **Script Execution**: < 1 second for typical operations
- **Memory Usage**: Minimal, script exits after execution

## Future Enhancements

Potential improvements:
- [ ] Support for IPv6 networks
- [ ] Custom IP ranges beyond 172.16.0.0/12
- [ ] Network reservation system
- [ ] Web UI for network management
- [ ] Kubernetes network integration
- [ ] Multi-host overlay network support

## Contributing

To contribute to this solution:
1. Test with your Docker setup
2. Report issues with network configurations
3. Suggest improvements to allocation algorithm
4. Add support for additional Docker Compose versions

## License

This solution is provided as part of the LocalAgent project under the same license terms.