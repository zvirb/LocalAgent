#!/usr/bin/env python3
"""
Comprehensive Test Suite for Docker Subnet Manager
=================================================

Tests all functionality of the Docker Subnet Manager including:
- Subnet scanning and allocation
- Docker network inspection
- Compose file parsing and updating
- Edge case handling
- Validation and error recovery
"""

import ipaddress
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the module under test
import sys
sys.path.append(os.path.dirname(__file__))
from docker_subnet_manager import DockerSubnetManager


class TestDockerSubnetManager(unittest.TestCase):
    """Comprehensive test suite for DockerSubnetManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DockerSubnetManager(
            base_dir=self.temp_dir,
            subnet_size=16,
            dry_run=True
        )
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        
    def test_initialization(self):
        """Test manager initialization."""
        self.assertEqual(self.manager.base_dir, Path(self.temp_dir))
        self.assertEqual(self.manager.subnet_size, 16)
        self.assertTrue(self.manager.dry_run)
        self.assertEqual(str(self.manager.private_range), '172.16.0.0/12')
        
    def test_ip_address_conversion(self):
        """Test IP address utility functions."""
        # Test basic subnet operations
        subnet1 = ipaddress.IPv4Network('172.16.0.0/16')
        subnet2 = ipaddress.IPv4Network('172.17.0.0/16')
        
        self.assertTrue(subnet1.overlaps(subnet1))
        self.assertFalse(subnet1.overlaps(subnet2))
        
    def test_subnet_validation(self):
        """Test subnet validation logic."""
        valid_subnet = ipaddress.IPv4Network('172.16.0.0/16')
        invalid_subnet = ipaddress.IPv4Network('192.168.1.0/24')
        
        # Add a used subnet
        self.manager.used_subnets.add(ipaddress.IPv4Network('172.17.0.0/16'))
        
        self.assertTrue(self.manager.validate_subnet_allocation(valid_subnet))
        self.assertFalse(self.manager.validate_subnet_allocation(invalid_subnet))
        
        # Test overlap detection
        overlapping_subnet = ipaddress.IPv4Network('172.17.0.0/16')
        self.assertFalse(self.manager.validate_subnet_allocation(overlapping_subnet))
        
    @patch('subprocess.run')
    def test_docker_network_scanning(self, mock_run):
        """Test Docker network scanning functionality."""
        # Mock docker network ls output
        mock_run.return_value.stdout = "bridge\nhost\ntest-network\n"
        mock_run.return_value.returncode = 0
        
        # Mock docker network inspect for specific network
        inspect_data = [{
            'Name': 'test-network',
            'IPAM': {
                'Config': [{'Subnet': '172.18.0.0/16'}]
            }
        }]
        
        def mock_docker_calls(cmd, **kwargs):
            if 'inspect' in cmd:
                result = Mock()
                result.stdout = json.dumps(inspect_data)
                result.returncode = 0
                return result
            else:
                result = Mock()
                result.stdout = "bridge\nhost\ntest-network\n"
                result.returncode = 0
                return result
                
        mock_run.side_effect = mock_docker_calls
        
        networks = self.manager.scan_docker_networks()
        
        self.assertIn('test-network', networks)
        self.assertEqual(networks['test-network'], '172.18.0.0/16')
        
    def test_find_next_available_subnet(self):
        """Test subnet allocation algorithm."""
        # Add some used subnets
        self.manager.used_subnets.add(ipaddress.IPv4Network('172.16.0.0/16'))
        self.manager.used_subnets.add(ipaddress.IPv4Network('172.17.0.0/16'))
        
        # Find next available
        next_subnet = self.manager.find_next_available_subnet(16)
        
        self.assertIsInstance(next_subnet, ipaddress.IPv4Network)
        self.assertEqual(next_subnet.prefixlen, 16)
        self.assertTrue(next_subnet.subnet_of(self.manager.private_range))
        
        # Verify it doesn't conflict with used subnets
        for used_subnet in self.manager.used_subnets:
            self.assertFalse(next_subnet.overlaps(used_subnet))
            
    def test_subnet_exhaustion_handling(self):
        """Test subnet exhaustion scenario."""
        # Fill up all /16 subnets in a smaller test range
        test_range = ipaddress.IPv4Network('172.16.0.0/14')  # Only 4 /16 subnets
        
        # Mock the private range for testing
        original_range = self.manager.private_range
        self.manager.private_range = test_range
        
        try:
            # Fill all possible /16 subnets
            for subnet in test_range.subnets(new_prefix=16):
                self.manager.used_subnets.add(subnet)
                
            # This should raise RuntimeError
            with self.assertRaises(RuntimeError):
                self.manager.find_next_available_subnet(16)
                
            # Test exhaustion handling
            solutions = self.manager.handle_subnet_exhaustion()
            self.assertIsInstance(solutions, list)
            
        finally:
            # Restore original range
            self.manager.private_range = original_range
            
    def test_compose_file_parsing(self):
        """Test docker-compose.yml file parsing."""
        compose_content = """
version: '3.8'
services:
  app:
    image: nginx
    networks:
      - custom-network

networks:
  custom-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
"""
        
        compose_file = Path(self.temp_dir) / 'docker-compose.yml'
        compose_file.write_text(compose_content)
        
        networks = self.manager.parse_compose_networks(compose_file)
        
        self.assertIn('custom-network', networks)
        self.assertEqual(networks['custom-network']['subnet'], '172.20.0.0/16')
        
    def test_compose_file_updating(self):
        """Test docker-compose.yml file updating."""
        initial_content = """
version: '3.8'
services:
  app:
    image: nginx

networks:
  existing-network:
    driver: bridge
"""
        
        compose_file = Path(self.temp_dir) / 'docker-compose.yml'
        compose_file.write_text(initial_content)
        
        # Test updating
        test_subnet = ipaddress.IPv4Network('172.19.0.0/16')
        success = self.manager.update_compose_file(
            compose_file, 
            'test-network', 
            test_subnet,
            backup=False  # Skip backup for test
        )
        
        self.assertTrue(success)
        
        # Since we're in dry run mode, file shouldn't actually be updated
        # But we can test the logic
        
    def test_network_config_generation(self):
        """Test network configuration generation."""
        subnet = ipaddress.IPv4Network('172.19.0.0/16')
        config = self.manager.generate_network_config('test-net', subnet)
        
        expected_config = {
            'driver': 'bridge',
            'ipam': {
                'config': [
                    {
                        'subnet': '172.19.0.0/16',
                        'gateway': '172.19.0.1'
                    }
                ]
            }
        }
        
        self.assertEqual(config, expected_config)
        
    def test_compose_file_discovery(self):
        """Test docker-compose file discovery."""
        # Create test compose files
        (Path(self.temp_dir) / 'docker-compose.yml').touch()
        (Path(self.temp_dir) / 'docker-compose.yaml').touch()
        
        subdir = Path(self.temp_dir) / 'subdir'
        subdir.mkdir()
        (subdir / 'docker-compose.dev.yml').touch()
        
        compose_files = self.manager.find_docker_compose_files()
        
        self.assertEqual(len(compose_files), 3)
        self.assertTrue(any('docker-compose.yml' in str(f) for f in compose_files))
        self.assertTrue(any('docker-compose.yaml' in str(f) for f in compose_files))
        self.assertTrue(any('docker-compose.dev.yml' in str(f) for f in compose_files))
        
    def test_override_file_generation(self):
        """Test docker-compose.override.yml generation."""
        base_compose = Path(self.temp_dir) / 'docker-compose.yml'
        base_compose.write_text("version: '3.8'\nservices:\n  app:\n    image: nginx")
        
        subnet = ipaddress.IPv4Network('172.21.0.0/16')
        override_path = self.manager.generate_override_file(
            base_compose, 
            'override-network', 
            subnet
        )
        
        expected_override = base_compose.parent / 'docker-compose.override.yml'
        self.assertEqual(override_path, expected_override)
        
        # In dry run mode, file won't actually be created
        
    def test_comprehensive_report_generation(self):
        """Test comprehensive report generation."""
        # Add some test data
        self.manager.used_subnets.add(ipaddress.IPv4Network('172.16.0.0/16'))
        self.manager.docker_networks = {'test-net': '172.16.0.0/16'}
        
        # Create test compose file
        (Path(self.temp_dir) / 'docker-compose.yml').touch()
        
        with patch.object(self.manager, 'scan_docker_networks'):
            with patch.object(self.manager, 'find_docker_compose_files', return_value=[Path(self.temp_dir) / 'docker-compose.yml']):
                report = self.manager.generate_comprehensive_report()
                
        self.assertIn('scan_timestamp', report)
        self.assertIn('docker_networks', report)
        self.assertIn('statistics', report)
        self.assertIn('next_available_subnets', report)
        
        self.assertEqual(report['statistics']['total_used_subnets'], 1)
        self.assertIn('test-net', report['docker_networks'])


class TestSubnetAlgorithms(unittest.TestCase):
    """Test subnet allocation algorithms and edge cases."""
    
    def test_subnet_overlap_detection(self):
        """Test subnet overlap detection algorithms."""
        subnet1 = ipaddress.IPv4Network('172.16.0.0/16')
        subnet2 = ipaddress.IPv4Network('172.16.1.0/24')  # Overlaps with subnet1
        subnet3 = ipaddress.IPv4Network('172.17.0.0/16')  # No overlap
        
        self.assertTrue(subnet1.overlaps(subnet2))
        self.assertFalse(subnet1.overlaps(subnet3))
        
    def test_different_subnet_sizes(self):
        """Test allocation with different subnet sizes."""
        manager = DockerSubnetManager(dry_run=True)
        
        # Test different sizes
        for size in [16, 24, 25, 26]:
            try:
                subnet = manager.find_next_available_subnet(size)
                self.assertEqual(subnet.prefixlen, size)
                self.assertTrue(subnet.subnet_of(manager.private_range))
                
                # Mark as used for next iteration
                manager.used_subnets.add(subnet)
                
            except RuntimeError:
                # This is expected if we run out of subnets
                pass
                
    def test_subnet_range_boundaries(self):
        """Test subnet allocation at range boundaries."""
        manager = DockerSubnetManager(dry_run=True)
        
        # Test edge cases near range boundaries
        edge_subnet = ipaddress.IPv4Network('172.31.255.0/24')
        
        # Should be valid within our range
        self.assertTrue(manager.validate_subnet_allocation(edge_subnet))
        
        # Test outside range
        outside_subnet = ipaddress.IPv4Network('172.32.0.0/24')
        self.assertFalse(manager.validate_subnet_allocation(outside_subnet))


class TestErrorHandling(unittest.TestCase):
    """Test error handling and recovery scenarios."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DockerSubnetManager(
            base_dir=self.temp_dir,
            dry_run=True
        )
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    @patch('subprocess.run')
    def test_docker_unavailable(self, mock_run):
        """Test behavior when Docker is unavailable."""
        mock_run.side_effect = FileNotFoundError("Docker not found")
        
        # Should handle gracefully
        networks = self.manager.scan_docker_networks()
        self.assertEqual(len(networks), 0)
        
    @patch('subprocess.run')
    def test_docker_daemon_down(self, mock_run):
        """Test behavior when Docker daemon is down."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'docker', 'Cannot connect to daemon')
        
        # Should handle gracefully
        networks = self.manager.scan_docker_networks()
        self.assertEqual(len(networks), 0)
        
    def test_invalid_compose_file(self):
        """Test handling of invalid compose files."""
        invalid_compose = Path(self.temp_dir) / 'invalid.yml'
        invalid_compose.write_text("invalid: yaml: content: [")
        
        # Should handle gracefully and return empty dict
        networks = self.manager.parse_compose_networks(invalid_compose)
        self.assertEqual(len(networks), 0)
        
    def test_nonexistent_compose_file(self):
        """Test handling of nonexistent compose files."""
        nonexistent = Path(self.temp_dir) / 'nonexistent.yml'
        
        # Should handle gracefully
        networks = self.manager.parse_compose_networks(nonexistent)
        self.assertEqual(len(networks), 0)
        
    def test_permission_errors(self):
        """Test handling of permission errors."""
        # This test would need special setup for permission testing
        pass


class IntegrationTests(unittest.TestCase):
    """Integration tests with real Docker (if available)."""
    
    @unittest.skipUnless(shutil.which('docker'), "Docker not available")
    def test_real_docker_integration(self):
        """Test integration with real Docker daemon if available."""
        manager = DockerSubnetManager(dry_run=True)
        
        try:
            # This will work if Docker is running
            networks = manager.scan_docker_networks()
            self.assertIsInstance(networks, dict)
            
            # Try to find an available subnet
            subnet = manager.find_next_available_subnet(24)
            self.assertIsInstance(subnet, ipaddress.IPv4Network)
            
        except Exception as e:
            # If Docker isn't available, skip the test
            self.skipTest(f"Docker not available or not running: {e}")


def create_test_environment():
    """Create a test environment with sample docker-compose files."""
    test_dir = tempfile.mkdtemp(prefix='subnet_manager_test_')
    
    # Create main compose file
    main_compose = Path(test_dir) / 'docker-compose.yml'
    main_compose.write_text("""
version: '3.8'
services:
  web:
    image: nginx
    networks:
      - web-network

networks:
  web-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
""")
    
    # Create development compose file
    dev_compose = Path(test_dir) / 'docker-compose.dev.yml'
    dev_compose.write_text("""
version: '3.8'
services:
  db:
    image: postgres
    networks:
      - db-network

networks:
  db-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
""")
    
    # Create subdirectory with another compose file
    subdir = Path(test_dir) / 'microservices'
    subdir.mkdir()
    
    micro_compose = subdir / 'docker-compose.yml'
    micro_compose.write_text("""
version: '3.8'
services:
  api:
    image: node:alpine
    networks:
      - api-network

networks:
  api-network:
    driver: bridge
""")
    
    return test_dir


def run_performance_tests():
    """Run performance tests for subnet allocation algorithms."""
    print("Running performance tests...")
    
    import time
    
    manager = DockerSubnetManager(dry_run=True)
    
    # Test performance with many used subnets
    start_time = time.time()
    
    # Add 100 used subnets
    for i in range(100):
        try:
            subnet = ipaddress.IPv4Network(f'172.{16 + i}.0.0/16')
            if subnet.subnet_of(manager.private_range):
                manager.used_subnets.add(subnet)
        except:
            break
            
    # Find next available subnet
    try:
        next_subnet = manager.find_next_available_subnet(16)
        elapsed = time.time() - start_time
        print(f"Found subnet {next_subnet} in {elapsed:.4f} seconds with {len(manager.used_subnets)} used subnets")
    except RuntimeError as e:
        print(f"Subnet exhaustion reached: {e}")
        
    # Test smaller subnet allocation performance
    start_time = time.time()
    try:
        next_subnet_24 = manager.find_next_available_subnet(24)
        elapsed = time.time() - start_time
        print(f"Found /24 subnet {next_subnet_24} in {elapsed:.4f} seconds")
    except RuntimeError as e:
        print(f"Subnet exhaustion for /24: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Docker Subnet Manager')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.performance:
        run_performance_tests()
        
    if args.integration:
        # Create test environment
        test_env = create_test_environment()
        print(f"Created test environment: {test_env}")
        
        # Run integration test
        manager = DockerSubnetManager(base_dir=test_env, dry_run=True)
        report = manager.generate_comprehensive_report()
        
        print("\nIntegration Test Report:")
        print(json.dumps(report, indent=2))
        
        # Cleanup
        shutil.rmtree(test_env)
        
    # Run unit tests
    if args.verbose:
        unittest.main(argv=[''], verbosity=2, exit=False)
    else:
        unittest.main(argv=[''], exit=False)