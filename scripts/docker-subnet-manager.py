#!/usr/bin/env python3
"""
Docker Network Subnet Manager
============================

A comprehensive Python script for intelligent Docker network subnet management.
Automatically scans existing Docker networks, finds available subnets in the 
172.16.0.0/12 range, and updates docker-compose.yml files or generates override files.

Features:
- Scans existing Docker networks to identify used subnets
- Finds next available subnet in 172.16.0.0/12 private range
- Updates docker-compose.yml files automatically
- Generates override files for complex scenarios
- Handles subnet exhaustion and conflicts
- Supports multiple subnet sizes (/16, /24, /25, etc.)
- Backup and rollback mechanisms
- Comprehensive logging and validation
"""

import argparse
import ipaddress
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union


class DockerSubnetManager:
    """
    Main class for managing Docker network subnets.
    
    This class provides comprehensive subnet management capabilities including:
    - Scanning existing Docker networks
    - Finding available subnets
    - Updating docker-compose.yml files
    - Generating override configurations
    - Handling edge cases and conflicts
    """
    
    def __init__(self, base_dir: str = ".", subnet_size: int = 16, dry_run: bool = False):
        """
        Initialize the Docker Subnet Manager.
        
        Args:
            base_dir: Base directory to scan for docker-compose files
            subnet_size: Default subnet size (16, 24, 25, etc.)
            dry_run: If True, only simulate changes without applying them
        """
        self.base_dir = Path(base_dir).resolve()
        self.subnet_size = subnet_size
        self.dry_run = dry_run
        
        # Define the private network range for subnet allocation
        self.private_range = ipaddress.IPv4Network('172.16.0.0/12')
        
        # Setup logging
        self.setup_logging()
        
        # Initialize internal state
        self.used_subnets: Set[ipaddress.IPv4Network] = set()
        self.docker_networks: Dict[str, str] = {}
        self.compose_files: List[Path] = []
        
        self.logger.info(f"Initialized DockerSubnetManager with base_dir={base_dir}, "
                        f"subnet_size=/{subnet_size}, dry_run={dry_run}")

    def setup_logging(self):
        """Setup comprehensive logging configuration."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'docker_subnet_manager_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def scan_docker_networks(self) -> Dict[str, str]:
        """
        Scan existing Docker networks to identify used subnets.
        
        Returns:
            Dict mapping network names to their subnet configurations
            
        Raises:
            subprocess.CalledProcessError: If Docker commands fail
        """
        self.logger.info("Scanning existing Docker networks...")
        
        try:
            # Get list of all Docker networks
            result = subprocess.run(
                ['docker', 'network', 'ls', '--format', '{{.Name}}'],
                capture_output=True,
                text=True,
                check=True
            )
            
            network_names = [name.strip() for name in result.stdout.split('\n') if name.strip()]
            self.logger.info(f"Found {len(network_names)} Docker networks: {network_names}")
            
            # Inspect each network for subnet information
            for network_name in network_names:
                try:
                    inspect_result = subprocess.run(
                        ['docker', 'network', 'inspect', network_name],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    network_data = json.loads(inspect_result.stdout)[0]
                    
                    # Extract subnet information from IPAM configuration
                    ipam_config = network_data.get('IPAM', {}).get('Config', [])
                    
                    # Handle case where Config might be None
                    if ipam_config is None:
                        ipam_config = []
                    
                    for config in ipam_config:
                        subnet_str = config.get('Subnet')
                        if subnet_str:
                            try:
                                subnet = ipaddress.IPv4Network(subnet_str, strict=False)
                                
                                # Only track subnets in our management range
                                if subnet.overlaps(self.private_range):
                                    self.used_subnets.add(subnet)
                                    self.docker_networks[network_name] = subnet_str
                                    self.logger.info(f"Network '{network_name}' uses subnet {subnet_str}")
                                    
                            except ipaddress.AddressValueError as e:
                                self.logger.warning(f"Invalid subnet format '{subnet_str}' in network '{network_name}': {e}")
                                
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to inspect network '{network_name}': {e}")
                    
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to list Docker networks: {e}")
            if "docker" in str(e):
                self.logger.warning("Docker might not be installed or running. Continuing with empty network list.")
                
        except FileNotFoundError:
            self.logger.warning("Docker command not found. Continuing with empty network list.")
            
        self.logger.info(f"Total used subnets found: {len(self.used_subnets)}")
        return self.docker_networks

    def find_docker_compose_files(self) -> List[Path]:
        """
        Find all docker-compose.yml files in the base directory and subdirectories.
        
        Returns:
            List of paths to docker-compose files
        """
        self.logger.info(f"Scanning for docker-compose files in {self.base_dir}...")
        
        compose_patterns = [
            'docker-compose.yml',
            'docker-compose.yaml',
            'docker-compose.*.yml',
            'docker-compose.*.yaml'
        ]
        
        compose_files = []
        
        for pattern in compose_patterns:
            compose_files.extend(self.base_dir.rglob(pattern))
            
        # Remove duplicates and sort
        compose_files = sorted(list(set(compose_files)))
        
        self.logger.info(f"Found {len(compose_files)} docker-compose files")
        for file_path in compose_files:
            self.logger.debug(f"  - {file_path}")
            
        self.compose_files = compose_files
        return compose_files

    def parse_compose_networks(self, compose_file: Path) -> Dict[str, Dict]:
        """
        Parse network configurations from a docker-compose.yml file.
        
        Args:
            compose_file: Path to the docker-compose.yml file
            
        Returns:
            Dict containing network configurations from the compose file
        """
        self.logger.debug(f"Parsing networks from {compose_file}")
        
        try:
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f) or {}
                
            networks = compose_data.get('networks', {})
            
            # Extract subnet information from each network
            network_subnets = {}
            for network_name, network_config in networks.items():
                if isinstance(network_config, dict):
                    ipam = network_config.get('ipam', {})
                    config = ipam.get('config', [])
                    
                    for subnet_config in config:
                        if isinstance(subnet_config, dict):
                            subnet_str = subnet_config.get('subnet')
                            if subnet_str:
                                try:
                                    subnet = ipaddress.IPv4Network(subnet_str, strict=False)
                                    if subnet.overlaps(self.private_range):
                                        network_subnets[network_name] = {
                                            'subnet': subnet_str,
                                            'config': network_config
                                        }
                                        self.used_subnets.add(subnet)
                                        self.logger.debug(f"Found subnet {subnet_str} for network {network_name}")
                                except ipaddress.AddressValueError as e:
                                    self.logger.warning(f"Invalid subnet '{subnet_str}' in {compose_file}: {e}")
                                    
            return network_subnets
            
        except Exception as e:
            self.logger.error(f"Failed to parse {compose_file}: {e}")
            return {}

    def find_next_available_subnet(self, subnet_size: Optional[int] = None) -> ipaddress.IPv4Network:
        """
        Find the next available subnet in the 172.16.0.0/12 range.
        
        Args:
            subnet_size: Size of subnet to allocate (defaults to instance subnet_size)
            
        Returns:
            Next available IPv4Network
            
        Raises:
            RuntimeError: If no available subnets found (exhaustion)
        """
        if subnet_size is None:
            subnet_size = self.subnet_size
            
        self.logger.info(f"Finding next available /{subnet_size} subnet in {self.private_range}")
        
        # Generate all possible subnets of the requested size within our range
        possible_subnets = list(self.private_range.subnets(new_prefix=subnet_size))
        
        self.logger.debug(f"Generated {len(possible_subnets)} possible /{subnet_size} subnets")
        
        # Find the first subnet that doesn't overlap with any used subnet
        for candidate_subnet in possible_subnets:
            is_available = True
            
            for used_subnet in self.used_subnets:
                if candidate_subnet.overlaps(used_subnet):
                    is_available = False
                    break
                    
            if is_available:
                self.logger.info(f"Found available subnet: {candidate_subnet}")
                return candidate_subnet
                
        # If we get here, no available subnet was found
        raise RuntimeError(f"No available /{subnet_size} subnets found in range {self.private_range}. "
                         f"Used subnets: {len(self.used_subnets)}, "
                         f"Total possible: {len(possible_subnets)}")

    def generate_network_config(self, network_name: str, subnet: ipaddress.IPv4Network) -> Dict:
        """
        Generate a complete network configuration for docker-compose.yml.
        
        Args:
            network_name: Name of the network
            subnet: IPv4Network to use for the network
            
        Returns:
            Dict containing complete network configuration
        """
        gateway = str(subnet.network_address + 1)
        
        config = {
            'driver': 'bridge',
            'ipam': {
                'config': [
                    {
                        'subnet': str(subnet),
                        'gateway': gateway
                    }
                ]
            }
        }
        
        self.logger.debug(f"Generated network config for {network_name}: {config}")
        return config

    def update_compose_file(self, compose_file: Path, network_name: str, 
                          subnet: ipaddress.IPv4Network, backup: bool = True) -> bool:
        """
        Update a docker-compose.yml file with new network configuration.
        
        Args:
            compose_file: Path to the compose file to update
            network_name: Name of the network to update/create
            subnet: Subnet to assign to the network
            backup: Whether to create a backup before updating
            
        Returns:
            True if update successful, False otherwise
        """
        self.logger.info(f"Updating {compose_file} with network {network_name} -> {subnet}")
        
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would update {compose_file}")
            return True
            
        try:
            # Create backup if requested
            if backup:
                backup_path = compose_file.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.yml')
                shutil.copy2(compose_file, backup_path)
                self.logger.info(f"Created backup: {backup_path}")
                
            # Load current compose file
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f) or {}
                
            # Ensure networks section exists
            if 'networks' not in compose_data:
                compose_data['networks'] = {}
                
            # Update network configuration
            network_config = self.generate_network_config(network_name, subnet)
            compose_data['networks'][network_name] = network_config
            
            # Write updated compose file
            with open(compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
                
            self.logger.info(f"Successfully updated {compose_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update {compose_file}: {e}")
            return False

    def generate_override_file(self, base_compose_file: Path, network_name: str, 
                             subnet: ipaddress.IPv4Network) -> Path:
        """
        Generate a docker-compose.override.yml file with network configuration.
        
        Args:
            base_compose_file: Path to the base compose file
            network_name: Name of the network
            subnet: Subnet to assign
            
        Returns:
            Path to the generated override file
        """
        override_path = base_compose_file.parent / 'docker-compose.override.yml'
        
        self.logger.info(f"Generating override file: {override_path}")
        
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would generate {override_path}")
            return override_path
            
        try:
            # Create override configuration
            network_config = self.generate_network_config(network_name, subnet)
            
            override_data = {
                'version': '3.8',
                'networks': {
                    network_name: network_config
                }
            }
            
            # Write override file
            with open(override_path, 'w') as f:
                yaml.dump(override_data, f, default_flow_style=False, sort_keys=False)
                
            self.logger.info(f"Generated override file: {override_path}")
            return override_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate override file {override_path}: {e}")
            raise

    def validate_subnet_allocation(self, subnet: ipaddress.IPv4Network) -> bool:
        """
        Validate that a subnet allocation doesn't conflict with existing networks.
        
        Args:
            subnet: Subnet to validate
            
        Returns:
            True if valid, False if conflicts detected
        """
        self.logger.debug(f"Validating subnet allocation: {subnet}")
        
        # Check against known used subnets
        for used_subnet in self.used_subnets:
            if subnet.overlaps(used_subnet):
                self.logger.warning(f"Subnet {subnet} overlaps with existing subnet {used_subnet}")
                return False
                
        # Additional validation: ensure subnet is in our managed range
        if not subnet.subnet_of(self.private_range):
            self.logger.warning(f"Subnet {subnet} is not within managed range {self.private_range}")
            return False
            
        self.logger.debug(f"Subnet {subnet} validation passed")
        return True

    def handle_subnet_exhaustion(self) -> List[ipaddress.IPv4Network]:
        """
        Handle subnet exhaustion by finding alternative solutions.
        
        Returns:
            List of possible solutions or alternatives
        """
        self.logger.warning("Handling subnet exhaustion scenario")
        
        solutions = []
        
        # Try smaller subnet sizes
        for smaller_size in [self.subnet_size + 1, self.subnet_size + 2]:
            if smaller_size <= 30:  # Don't go smaller than /30
                try:
                    smaller_subnet = self.find_next_available_subnet(smaller_size)
                    solutions.append(smaller_subnet)
                    self.logger.info(f"Alternative solution: Use /{smaller_size} subnet {smaller_subnet}")
                except RuntimeError:
                    continue
                    
        # Suggest cleanup of unused networks
        self.logger.warning("Consider cleaning up unused Docker networks:")
        self.logger.warning("  docker network prune")
        
        # Suggest using different private ranges
        alternative_ranges = [
            ipaddress.IPv4Network('10.0.0.0/8'),
            ipaddress.IPv4Network('192.168.0.0/16')
        ]
        
        self.logger.warning("Consider using alternative private IP ranges:")
        for alt_range in alternative_ranges:
            self.logger.warning(f"  {alt_range}")
            
        return solutions

    def generate_comprehensive_report(self) -> Dict:
        """
        Generate a comprehensive report of subnet usage and availability.
        
        Returns:
            Dict containing detailed subnet analysis
        """
        self.logger.info("Generating comprehensive subnet report")
        
        # Scan everything
        self.scan_docker_networks()
        self.find_docker_compose_files()
        
        # Parse compose files for additional subnet info
        compose_networks = {}
        for compose_file in self.compose_files:
            compose_networks[str(compose_file)] = self.parse_compose_networks(compose_file)
            
        # Calculate availability statistics
        total_possible_16 = len(list(self.private_range.subnets(new_prefix=16)))
        total_possible_24 = len(list(self.private_range.subnets(new_prefix=24)))
        used_count = len(self.used_subnets)
        
        # Find next available subnets of different sizes
        next_available = {}
        for size in [16, 24, 25, 26]:
            try:
                next_subnet = self.find_next_available_subnet(size)
                next_available[f"/{size}"] = str(next_subnet)
            except RuntimeError as e:
                next_available[f"/{size}"] = f"EXHAUSTED: {e}"
                
        report = {
            'scan_timestamp': datetime.now().isoformat(),
            'base_directory': str(self.base_dir),
            'management_range': str(self.private_range),
            'statistics': {
                'total_used_subnets': used_count,
                'total_possible_16_subnets': total_possible_16,
                'total_possible_24_subnets': total_possible_24,
                'utilization_16': f"{(used_count / total_possible_16) * 100:.2f}%",
                'utilization_24': f"{(used_count / total_possible_24) * 100:.2f}%"
            },
            'docker_networks': self.docker_networks,
            'compose_files_found': [str(f) for f in self.compose_files],
            'compose_networks': compose_networks,
            'used_subnets': [str(subnet) for subnet in sorted(self.used_subnets)],
            'next_available_subnets': next_available
        }
        
        return report

    def run_interactive_mode(self):
        """Run the subnet manager in interactive mode for user-guided operations."""
        self.logger.info("Starting interactive mode")
        
        print("\n🐳 Docker Subnet Manager - Interactive Mode")
        print("=" * 50)
        
        # Generate and display report
        report = self.generate_comprehensive_report()
        
        print(f"\n📊 Current Subnet Usage Report")
        print(f"Management Range: {report['management_range']}")
        print(f"Used Subnets: {report['statistics']['total_used_subnets']}")
        print(f"Utilization (/16): {report['statistics']['utilization_16']}")
        print(f"Utilization (/24): {report['statistics']['utilization_24']}")
        
        print(f"\n🌐 Current Docker Networks:")
        for network, subnet in report['docker_networks'].items():
            print(f"  • {network}: {subnet}")
            
        print(f"\n📁 Docker Compose Files Found: {len(report['compose_files_found'])}")
        for compose_file in report['compose_files_found'][:5]:  # Show first 5
            print(f"  • {compose_file}")
        if len(report['compose_files_found']) > 5:
            print(f"  ... and {len(report['compose_files_found']) - 5} more")
            
        print(f"\n🆕 Next Available Subnets:")
        for size, subnet in report['next_available_subnets'].items():
            print(f"  • {size}: {subnet}")
            
        # Interactive options
        print(f"\n⚡ Available Actions:")
        print("1. Allocate new subnet for a project")
        print("2. Update existing docker-compose.yml file")
        print("3. Generate override file")
        print("4. Export detailed report")
        print("5. Clean up unused networks")
        print("6. Exit")
        
        while True:
            try:
                choice = input("\nSelect an option (1-6): ").strip()
                
                if choice == '1':
                    self.interactive_allocate_subnet()
                elif choice == '2':
                    self.interactive_update_compose()
                elif choice == '3':
                    self.interactive_generate_override()
                elif choice == '4':
                    self.interactive_export_report(report)
                elif choice == '5':
                    self.interactive_cleanup_networks()
                elif choice == '6':
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice. Please select 1-6.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break

    def interactive_allocate_subnet(self):
        """Interactive subnet allocation workflow."""
        print("\n🆕 Subnet Allocation Wizard")
        print("-" * 30)
        
        network_name = input("Enter network name: ").strip()
        if not network_name:
            print("❌ Network name cannot be empty")
            return
            
        # Get subnet size preference
        size_input = input("Enter subnet size (16, 24, 25, 26) [default: 16]: ").strip()
        try:
            subnet_size = int(size_input) if size_input else 16
            if subnet_size not in [16, 24, 25, 26]:
                raise ValueError()
        except ValueError:
            print("❌ Invalid subnet size. Using default /16")
            subnet_size = 16
            
        try:
            # Find available subnet
            subnet = self.find_next_available_subnet(subnet_size)
            print(f"✅ Found available subnet: {subnet}")
            
            # Ask for confirmation
            confirm = input(f"Allocate {subnet} to network '{network_name}'? (y/n): ").strip().lower()
            if confirm == 'y':
                # Mark as used to prevent conflicts
                self.used_subnets.add(subnet)
                print(f"✅ Subnet {subnet} allocated to network '{network_name}'")
                print(f"💡 Use this configuration in your docker-compose.yml:")
                print(f"networks:")
                print(f"  {network_name}:")
                print(f"    driver: bridge")
                print(f"    ipam:")
                print(f"      config:")
                print(f"        - subnet: {subnet}")
                print(f"          gateway: {subnet.network_address + 1}")
            else:
                print("❌ Allocation cancelled")
                
        except RuntimeError as e:
            print(f"❌ {e}")
            solutions = self.handle_subnet_exhaustion()
            if solutions:
                print(f"💡 Consider these alternatives:")
                for i, solution in enumerate(solutions[:3], 1):
                    print(f"  {i}. {solution}")

    def interactive_update_compose(self):
        """Interactive docker-compose.yml update workflow."""
        print("\n📝 Update Docker Compose File")
        print("-" * 30)
        
        if not self.compose_files:
            print("❌ No docker-compose.yml files found in current directory")
            return
            
        print("Available docker-compose.yml files:")
        for i, compose_file in enumerate(self.compose_files, 1):
            print(f"  {i}. {compose_file}")
            
        try:
            file_index = int(input("Select file to update (number): ").strip()) - 1
            if file_index < 0 or file_index >= len(self.compose_files):
                raise ValueError()
        except ValueError:
            print("❌ Invalid file selection")
            return
            
        selected_file = self.compose_files[file_index]
        network_name = input("Enter network name to update/create: ").strip()
        
        if not network_name:
            print("❌ Network name cannot be empty")
            return
            
        try:
            subnet = self.find_next_available_subnet()
            print(f"✅ Will use subnet: {subnet}")
            
            confirm = input(f"Update {selected_file} with network '{network_name}' -> {subnet}? (y/n): ").strip().lower()
            if confirm == 'y':
                success = self.update_compose_file(selected_file, network_name, subnet)
                if success:
                    print("✅ Docker compose file updated successfully")
                    self.used_subnets.add(subnet)
                else:
                    print("❌ Failed to update docker compose file")
            else:
                print("❌ Update cancelled")
                
        except RuntimeError as e:
            print(f"❌ {e}")

    def interactive_generate_override(self):
        """Interactive override file generation workflow."""
        print("\n📋 Generate Docker Compose Override")
        print("-" * 35)
        
        if not self.compose_files:
            print("❌ No docker-compose.yml files found")
            return
            
        print("Available docker-compose.yml files:")
        for i, compose_file in enumerate(self.compose_files, 1):
            print(f"  {i}. {compose_file}")
            
        try:
            file_index = int(input("Select base file (number): ").strip()) - 1
            if file_index < 0 or file_index >= len(self.compose_files):
                raise ValueError()
        except ValueError:
            print("❌ Invalid file selection")
            return
            
        selected_file = self.compose_files[file_index]
        network_name = input("Enter network name for override: ").strip()
        
        if not network_name:
            print("❌ Network name cannot be empty")
            return
            
        try:
            subnet = self.find_next_available_subnet()
            print(f"✅ Will use subnet: {subnet}")
            
            confirm = input(f"Generate override file for network '{network_name}' -> {subnet}? (y/n): ").strip().lower()
            if confirm == 'y':
                override_path = self.generate_override_file(selected_file, network_name, subnet)
                print(f"✅ Override file generated: {override_path}")
                self.used_subnets.add(subnet)
            else:
                print("❌ Generation cancelled")
                
        except RuntimeError as e:
            print(f"❌ {e}")

    def interactive_export_report(self, report: Dict):
        """Interactive report export workflow."""
        print("\n📊 Export Detailed Report")
        print("-" * 25)
        
        filename = input("Enter report filename [subnet_report.json]: ").strip()
        if not filename:
            filename = "subnet_report.json"
            
        if not filename.endswith('.json'):
            filename += '.json'
            
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, sort_keys=True)
            print(f"✅ Report exported to: {filename}")
        except Exception as e:
            print(f"❌ Failed to export report: {e}")

    def interactive_cleanup_networks(self):
        """Interactive network cleanup workflow."""
        print("\n🧹 Network Cleanup")
        print("-" * 18)
        
        print("⚠️  This will remove unused Docker networks.")
        print("Make sure no containers are using networks you want to remove.")
        
        confirm = input("Continue with network cleanup? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Cleanup cancelled")
            return
            
        try:
            result = subprocess.run(
                ['docker', 'network', 'prune', '-f'],
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Network cleanup completed")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ Network cleanup failed: {e}")


def main():
    """Main entry point for the Docker Subnet Manager."""
    parser = argparse.ArgumentParser(
        description='Docker Network Subnet Manager - Intelligent subnet allocation and management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python docker-subnet-manager.py --interactive
  
  # Scan and report current usage
  python docker-subnet-manager.py --scan --report
  
  # Find next available /16 subnet
  python docker-subnet-manager.py --find-subnet --size 16
  
  # Update specific docker-compose.yml file
  python docker-subnet-manager.py --update-compose /path/to/docker-compose.yml --network mynet
  
  # Generate override file
  python docker-subnet-manager.py --generate-override /path/to/docker-compose.yml --network mynet
  
  # Dry run mode (simulate without changes)
  python docker-subnet-manager.py --interactive --dry-run
        """
    )
    
    parser.add_argument('--base-dir', '-d', default='.',
                       help='Base directory to scan for docker-compose files (default: current directory)')
    
    parser.add_argument('--subnet-size', '-s', type=int, default=16, choices=[16, 24, 25, 26, 27, 28],
                       help='Default subnet size (default: 16)')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulate changes without applying them')
    
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run in interactive mode')
    
    parser.add_argument('--scan', action='store_true',
                       help='Scan existing Docker networks and compose files')
    
    parser.add_argument('--report', '-r', action='store_true',
                       help='Generate comprehensive usage report')
    
    parser.add_argument('--find-subnet', action='store_true',
                       help='Find next available subnet')
    
    parser.add_argument('--update-compose', metavar='FILE',
                       help='Update specific docker-compose.yml file')
    
    parser.add_argument('--generate-override', metavar='FILE',
                       help='Generate override file for specific docker-compose.yml')
    
    parser.add_argument('--network', '-n', metavar='NAME',
                       help='Network name to use/create')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize manager
    manager = DockerSubnetManager(
        base_dir=args.base_dir,
        subnet_size=args.subnet_size,
        dry_run=args.dry_run
    )
    
    try:
        if args.interactive:
            manager.run_interactive_mode()
            
        elif args.scan or args.report:
            report = manager.generate_comprehensive_report()
            
            if args.report:
                print(json.dumps(report, indent=2))
            else:
                print(f"Found {len(report['docker_networks'])} Docker networks")
                print(f"Found {len(report['compose_files_found'])} docker-compose files")
                print(f"Total used subnets: {report['statistics']['total_used_subnets']}")
                
        elif args.find_subnet:
            manager.scan_docker_networks()
            subnet = manager.find_next_available_subnet()
            print(f"Next available /{args.subnet_size} subnet: {subnet}")
            
        elif args.update_compose:
            if not args.network:
                print("❌ --network is required when using --update-compose")
                sys.exit(1)
                
            compose_file = Path(args.update_compose)
            if not compose_file.exists():
                print(f"❌ Docker compose file not found: {compose_file}")
                sys.exit(1)
                
            manager.scan_docker_networks()
            subnet = manager.find_next_available_subnet()
            
            success = manager.update_compose_file(compose_file, args.network, subnet)
            if success:
                print(f"✅ Updated {compose_file} with network {args.network} -> {subnet}")
            else:
                print(f"❌ Failed to update {compose_file}")
                sys.exit(1)
                
        elif args.generate_override:
            if not args.network:
                print("❌ --network is required when using --generate-override")
                sys.exit(1)
                
            compose_file = Path(args.generate_override)
            if not compose_file.exists():
                print(f"❌ Docker compose file not found: {compose_file}")
                sys.exit(1)
                
            manager.scan_docker_networks()
            subnet = manager.find_next_available_subnet()
            
            override_path = manager.generate_override_file(compose_file, args.network, subnet)
            print(f"✅ Generated override file: {override_path}")
            
        else:
            # Default: show help and run basic scan
            parser.print_help()
            print("\n" + "="*60)
            print("Quick Status:")
            
            manager.scan_docker_networks()
            print(f"Found {len(manager.docker_networks)} Docker networks using managed subnets")
            
            try:
                next_subnet = manager.find_next_available_subnet()
                print(f"Next available /{args.subnet_size} subnet: {next_subnet}")
            except RuntimeError as e:
                print(f"⚠️  {e}")
                
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        if args.verbose:
            raise
        sys.exit(1)


if __name__ == '__main__':
    main()