#!/usr/bin/env python3
"""
Docker Dynamic Network Assignment
Automatically assigns non-conflicting subnets to Docker networks
"""

import json
import subprocess
import sys
import ipaddress
import yaml
import argparse
from pathlib import Path
from typing import List, Optional, Dict, Tuple

class DockerNetworkManager:
    """Manages Docker network subnet allocation dynamically"""
    
    def __init__(self):
        self.docker_range = ipaddress.ip_network('172.16.0.0/12')
        self.reserved_subnets = []
        
    def get_existing_subnets(self) -> List[ipaddress.IPv4Network]:
        """Get all existing Docker network subnets"""
        subnets = []
        
        try:
            # Get all Docker networks
            result = subprocess.run(
                ['docker', 'network', 'ls', '--format', '{{.Name}}'],
                capture_output=True,
                text=True,
                check=True
            )
            
            networks = result.stdout.strip().split('\n')
            
            for network in networks:
                if not network:
                    continue
                    
                # Inspect each network
                try:
                    inspect_result = subprocess.run(
                        ['docker', 'network', 'inspect', network],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    network_data = json.loads(inspect_result.stdout)
                    
                    # Extract subnet if exists
                    for net in network_data:
                        if 'IPAM' in net and 'Config' in net['IPAM'] and net['IPAM']['Config']:
                            for config in net['IPAM']['Config']:
                                if config and 'Subnet' in config:
                                    try:
                                        subnet = ipaddress.ip_network(config['Subnet'])
                                        if subnet.overlaps(self.docker_range):
                                            subnets.append(subnet)
                                    except Exception:
                                        pass
                                        
                except subprocess.CalledProcessError:
                    continue
                    
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not list Docker networks: {e}", file=sys.stderr)
            
        return sorted(subnets)
    
    def find_available_subnet(self, prefix_len: int = 16) -> Optional[ipaddress.IPv4Network]:
        """Find next available subnet with specified prefix length"""
        
        if prefix_len < 16 or prefix_len > 28:
            raise ValueError("Prefix length must be between 16 and 28")
            
        existing = self.get_existing_subnets()
        
        # Generate all possible subnets of the requested size
        possible_subnets = list(self.docker_range.subnets(new_prefix=prefix_len))
        
        # Find first available subnet
        for subnet in possible_subnets:
            is_available = True
            
            for existing_subnet in existing:
                if subnet.overlaps(existing_subnet):
                    is_available = False
                    break
                    
            if is_available:
                return subnet
                
        return None
    
    def update_compose_file(self, compose_path: str, network_name: str = None, 
                          subnet: str = None, backup: bool = True) -> bool:
        """Update docker-compose.yml with dynamic subnet"""
        
        compose_path = Path(compose_path)
        
        if not compose_path.exists():
            print(f"Error: {compose_path} does not exist", file=sys.stderr)
            return False
            
        # Find available subnet if not specified
        if not subnet:
            available_subnet = self.find_available_subnet()
            if not available_subnet:
                print("Error: No available subnets in 172.16.0.0/12 range", file=sys.stderr)
                return False
            subnet = str(available_subnet)
        
        # Read compose file
        with open(compose_path, 'r') as f:
            compose_data = yaml.safe_load(f)
            
        # Create backup if requested
        if backup:
            backup_path = compose_path.with_suffix('.yml.backup')
            with open(backup_path, 'w') as f:
                yaml.safe_dump(compose_data, f)
            print(f"Backup created: {backup_path}")
        
        # Update networks section
        if 'networks' not in compose_data:
            compose_data['networks'] = {}
            
        # Find network to update
        if not network_name:
            # Get first network or create default
            if compose_data['networks']:
                network_name = list(compose_data['networks'].keys())[0]
            else:
                network_name = 'default_network'
                
        # Update network configuration
        compose_data['networks'][network_name] = {
            'driver': 'bridge',
            'ipam': {
                'config': [{
                    'subnet': subnet
                }]
            }
        }
        
        # Write updated compose file
        with open(compose_path, 'w') as f:
            yaml.safe_dump(compose_data, f, default_flow_style=False, sort_keys=False)
            
        print(f"Updated {compose_path}")
        print(f"  Network: {network_name}")
        print(f"  Subnet: {subnet}")
        
        return True
    
    def generate_override_file(self, base_compose: str, output_path: str = None) -> bool:
        """Generate docker-compose.override.yml with dynamic network"""
        
        base_path = Path(base_compose)
        
        if not base_path.exists():
            print(f"Error: {base_path} does not exist", file=sys.stderr)
            return False
            
        if not output_path:
            output_path = base_path.parent / 'docker-compose.override.yml'
        else:
            output_path = Path(output_path)
            
        # Find available subnet
        available_subnet = self.find_available_subnet()
        if not available_subnet:
            print("Error: No available subnets", file=sys.stderr)
            return False
            
        # Read base compose to get network names
        with open(base_path, 'r') as f:
            base_data = yaml.safe_load(f)
            
        # Create override structure
        override_data = {
            'version': base_data.get('version', '3.8'),
            'networks': {}
        }
        
        # Add dynamic subnets for each network
        if 'networks' in base_data:
            for network_name in base_data['networks']:
                # Find new subnet for each network
                subnet = self.find_available_subnet()
                if subnet:
                    override_data['networks'][network_name] = {
                        'ipam': {
                            'config': [{
                                'subnet': str(subnet)
                            }]
                        }
                    }
                    # Mark this subnet as used for next iteration
                    self.reserved_subnets.append(subnet)
                    
        # Write override file
        with open(output_path, 'w') as f:
            yaml.safe_dump(override_data, f, default_flow_style=False, sort_keys=False)
            
        print(f"Generated override file: {output_path}")
        for net_name, net_config in override_data['networks'].items():
            subnet = net_config['ipam']['config'][0]['subnet']
            print(f"  {net_name}: {subnet}")
            
        return True
        
    def status_report(self) -> Dict:
        """Generate status report of network usage"""
        
        existing = self.get_existing_subnets()
        
        # Calculate usage
        total_ips = int(self.docker_range.num_addresses)
        used_ips = sum(int(subnet.num_addresses) for subnet in existing)
        
        report = {
            'docker_range': str(self.docker_range),
            'total_ips': total_ips,
            'used_ips': used_ips,
            'usage_percentage': (used_ips / total_ips) * 100,
            'networks_count': len(existing),
            'used_subnets': [str(s) for s in existing],
            'next_available': {
                '/16': str(self.find_available_subnet(16)) if self.find_available_subnet(16) else None,
                '/24': str(self.find_available_subnet(24)) if self.find_available_subnet(24) else None,
            }
        }
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description='Docker Dynamic Network Assignment - Prevents subnet conflicts'
    )
    
    parser.add_argument(
        '--update-compose',
        metavar='PATH',
        help='Update docker-compose.yml file with available subnet'
    )
    
    parser.add_argument(
        '--network',
        metavar='NAME',
        help='Network name to update (default: first network in file)'
    )
    
    parser.add_argument(
        '--generate-override',
        metavar='PATH',
        help='Generate docker-compose.override.yml from base compose file'
    )
    
    parser.add_argument(
        '--find-subnet',
        metavar='PREFIX',
        type=int,
        default=16,
        help='Find available subnet with prefix length (default: 16)'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show network usage status report'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backup when updating files'
    )
    
    args = parser.parse_args()
    
    manager = DockerNetworkManager()
    
    # Status report
    if args.status:
        report = manager.status_report()
        print("\n=== Docker Network Status Report ===")
        print(f"Docker Range: {report['docker_range']}")
        print(f"Networks in use: {report['networks_count']}")
        print(f"IP usage: {report['used_ips']:,} / {report['total_ips']:,} ({report['usage_percentage']:.2f}%)")
        print(f"\nUsed subnets:")
        for subnet in report['used_subnets']:
            print(f"  - {subnet}")
        print(f"\nNext available:")
        for prefix, subnet in report['next_available'].items():
            print(f"  {prefix}: {subnet}")
        return 0
    
    # Update compose file
    if args.update_compose:
        success = manager.update_compose_file(
            args.update_compose,
            network_name=args.network,
            backup=not args.no_backup
        )
        return 0 if success else 1
    
    # Generate override file
    if args.generate_override:
        success = manager.generate_override_file(args.generate_override)
        return 0 if success else 1
    
    # Find available subnet
    if args.find_subnet:
        subnet = manager.find_available_subnet(args.find_subnet)
        if subnet:
            print(f"Available subnet (/{args.find_subnet}): {subnet}")
            return 0
        else:
            print(f"No available subnet with prefix /{args.find_subnet}", file=sys.stderr)
            return 1
    
    # Default: show help
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())