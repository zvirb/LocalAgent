#!/usr/bin/env python3
"""
Container Resource Optimization Testing
=======================================

Tests and validates container resource optimization including:
- Memory limit compliance
- CPU usage efficiency
- Container startup performance
- Resource cleanup validation
- Multi-container coordination
"""

import asyncio
import json
import os
import psutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ContainerResourceResult:
    """Container resource test result"""
    test_name: str
    container_name: str
    duration_seconds: float
    memory_limit_mb: Optional[float]
    memory_peak_mb: float
    memory_avg_mb: float
    cpu_limit_percent: Optional[float]
    cpu_peak_percent: float
    cpu_avg_percent: float
    startup_time_seconds: float
    cleanup_successful: bool
    resource_compliance: bool
    custom_metrics: Dict[str, Any]


class ContainerResourceTester:
    """Container resource optimization testing suite"""
    
    def __init__(self, output_dir: str = "container_resource_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = []
    
    def check_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def test_memory_limit_compliance(self) -> List[ContainerResourceResult]:
        """Test memory limit compliance for containers"""
        print("Testing container memory limit compliance...")
        
        if not self.check_docker_available():
            print("  Docker not available, skipping container tests")
            return []
        
        results = []
        
        # Test different memory limits
        memory_limits = [
            ("128m", 128),  # 128MB
            ("256m", 256),  # 256MB  
            ("512m", 512),  # 512MB
        ]
        
        for limit_str, limit_mb in memory_limits:
            print(f"  Testing memory limit: {limit_str}")
            
            container_name = f"memory_test_{limit_mb}mb"
            
            try:
                # Create test container with memory limit
                create_cmd = [
                    'docker', 'run', '-d', '--rm',
                    '--name', container_name,
                    '--memory', limit_str,
                    '--memory-swap', limit_str,  # Disable swap
                    'python:3.11-slim',
                    'python', '-c', '''
import time
import sys
data = []
# Gradually consume memory
for i in range(100):
    try:
        # Allocate 10MB chunks
        chunk = "x" * (10 * 1024 * 1024)
        data.append(chunk)
        time.sleep(0.1)
    except MemoryError:
        print(f"Memory limit reached at iteration {i}", file=sys.stderr)
        break
time.sleep(30)  # Keep container running for monitoring
'''
                ]
                
                start_time = time.time()
                create_result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=60)
                
                if create_result.returncode != 0:
                    print(f"    Failed to create container: {create_result.stderr}")
                    continue
                
                startup_time = time.time() - start_time
                
                # Monitor container resources
                memory_measurements = []
                cpu_measurements = []
                
                monitor_start = time.time()
                monitor_duration = 10  # Monitor for 10 seconds
                
                while time.time() - monitor_start < monitor_duration:
                    try:
                        # Get container stats
                        stats_cmd = ['docker', 'stats', container_name, '--no-stream', '--format', 'json']
                        stats_result = subprocess.run(stats_cmd, capture_output=True, text=True, timeout=5)
                        
                        if stats_result.returncode == 0:
                            stats_data = json.loads(stats_result.stdout)
                            
                            # Parse memory usage (format like "123.4MiB / 256MiB")
                            memory_str = stats_data.get('MemUsage', '0B / 0B')
                            if ' / ' in memory_str:
                                current_mem_str = memory_str.split(' / ')[0]
                                # Convert to MB
                                if 'MiB' in current_mem_str:
                                    current_mem_mb = float(current_mem_str.replace('MiB', ''))
                                elif 'GiB' in current_mem_str:
                                    current_mem_mb = float(current_mem_str.replace('GiB', '')) * 1024
                                else:
                                    current_mem_mb = 0
                                
                                memory_measurements.append(current_mem_mb)
                            
                            # Parse CPU usage (format like "12.34%")
                            cpu_str = stats_data.get('CPUPerc', '0.00%')
                            cpu_percent = float(cpu_str.replace('%', ''))
                            cpu_measurements.append(cpu_percent)
                    
                    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as e:
                        print(f"    Error getting stats: {e}")
                    
                    await asyncio.sleep(0.5)
                
                # Stop and remove container
                cleanup_successful = True
                try:
                    subprocess.run(['docker', 'stop', container_name], 
                                 capture_output=True, timeout=30)
                except subprocess.TimeoutExpired:
                    cleanup_successful = False
                
                # Analyze results
                monitor_duration_actual = time.time() - monitor_start
                memory_peak = max(memory_measurements) if memory_measurements else 0
                memory_avg = sum(memory_measurements) / len(memory_measurements) if memory_measurements else 0
                cpu_peak = max(cpu_measurements) if cpu_measurements else 0
                cpu_avg = sum(cpu_measurements) / len(cpu_measurements) if cpu_measurements else 0
                
                # Check compliance (memory should not exceed limit + 10% tolerance)
                resource_compliance = memory_peak <= (limit_mb * 1.1)
                
                result = ContainerResourceResult(
                    test_name="memory_limit_compliance",
                    container_name=container_name,
                    duration_seconds=monitor_duration_actual,
                    memory_limit_mb=limit_mb,
                    memory_peak_mb=memory_peak,
                    memory_avg_mb=memory_avg,
                    cpu_limit_percent=None,  # No CPU limit set
                    cpu_peak_percent=cpu_peak,
                    cpu_avg_percent=cpu_avg,
                    startup_time_seconds=startup_time,
                    cleanup_successful=cleanup_successful,
                    resource_compliance=resource_compliance,
                    custom_metrics={
                        'memory_efficiency': memory_avg / limit_mb if limit_mb > 0 else 0,
                        'memory_measurements_count': len(memory_measurements),
                        'memory_limit_exceeded': memory_peak > limit_mb
                    }
                )
                
                results.append(result)
                print(f"    {container_name}: {memory_peak:.1f}MB peak (limit: {limit_mb}MB), compliance: {resource_compliance}")
                
            except Exception as e:
                print(f"    Error testing {container_name}: {e}")
                # Ensure cleanup
                try:
                    subprocess.run(['docker', 'stop', container_name], 
                                 capture_output=True, timeout=10)
                except:
                    pass
        
        return results
    
    async def test_container_startup_performance(self) -> List[ContainerResourceResult]:
        """Test container startup performance"""
        print("Testing container startup performance...")
        
        if not self.check_docker_available():
            print("  Docker not available, skipping startup tests")
            return []
        
        results = []
        
        # Test different container configurations
        test_configs = [
            ("python_slim", "python:3.11-slim", "python --version"),
            ("python_alpine", "python:3.11-alpine", "python --version"),
        ]
        
        for config_name, image, test_command in test_configs:
            print(f"  Testing startup: {config_name}")
            
            startup_times = []
            successful_starts = 0
            
            for i in range(5):  # Test 5 startups
                container_name = f"startup_test_{config_name}_{i}"
                
                try:
                    # Time container startup
                    start_time = time.time()
                    
                    run_cmd = [
                        'docker', 'run', '--rm', '--name', container_name,
                        image, 'sh', '-c', test_command
                    ]
                    
                    result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=60)
                    startup_time = time.time() - start_time
                    
                    if result.returncode == 0:
                        startup_times.append(startup_time)
                        successful_starts += 1
                    else:
                        print(f"    Startup {i} failed: {result.stderr}")
                    
                except subprocess.TimeoutExpired:
                    print(f"    Startup {i} timed out")
                except Exception as e:
                    print(f"    Startup {i} error: {e}")
            
            if startup_times:
                avg_startup = sum(startup_times) / len(startup_times)
                min_startup = min(startup_times)
                max_startup = max(startup_times)
                
                result = ContainerResourceResult(
                    test_name="startup_performance",
                    container_name=config_name,
                    duration_seconds=avg_startup,
                    memory_limit_mb=None,
                    memory_peak_mb=0,  # Not measured
                    memory_avg_mb=0,   # Not measured
                    cpu_limit_percent=None,
                    cpu_peak_percent=0,  # Not measured
                    cpu_avg_percent=0,   # Not measured
                    startup_time_seconds=avg_startup,
                    cleanup_successful=True,  # Containers auto-removed
                    resource_compliance=True,  # No limits to violate
                    custom_metrics={
                        'successful_starts': successful_starts,
                        'total_attempts': 5,
                        'min_startup_time': min_startup,
                        'max_startup_time': max_startup,
                        'startup_time_variance': max_startup - min_startup
                    }
                )
                
                results.append(result)
                print(f"    {config_name}: {avg_startup:.2f}s avg startup ({successful_starts}/5 successful)")
        
        return results
    
    async def test_process_resource_optimization(self) -> List[ContainerResourceResult]:
        """Test process-level resource optimization (fallback when Docker unavailable)"""
        print("Testing process resource optimization...")
        
        results = []
        
        # Test Python process memory efficiency
        test_name = "python_process_memory"
        print(f"  Testing {test_name}...")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        memory_measurements = []
        
        # Simulate memory-intensive task
        data = []
        try:
            for i in range(100):
                # Allocate 1MB chunks
                chunk = "x" * (1024 * 1024)
                data.append(chunk)
                
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_measurements.append(current_memory)
                
                await asyncio.sleep(0.01)  # Small delay
                
                # Clean up every 20 iterations
                if i % 20 == 0:
                    data = data[-10:]  # Keep only last 10 chunks
        
        except MemoryError:
            print("    Hit memory limit during test")
        
        duration = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024
        
        memory_peak = max(memory_measurements) if memory_measurements else final_memory
        memory_avg = sum(memory_measurements) / len(memory_measurements) if memory_measurements else final_memory
        memory_growth = final_memory - initial_memory
        
        result = ContainerResourceResult(
            test_name="process_memory_optimization", 
            container_name="python_process",
            duration_seconds=duration,
            memory_limit_mb=None,
            memory_peak_mb=memory_peak,
            memory_avg_mb=memory_avg,
            cpu_limit_percent=None,
            cpu_peak_percent=0,  # Not measured
            cpu_avg_percent=0,   # Not measured
            startup_time_seconds=0,  # N/A
            cleanup_successful=True,
            resource_compliance=True,  # No limits
            custom_metrics={
                'initial_memory_mb': initial_memory,
                'final_memory_mb': final_memory,
                'memory_growth_mb': memory_growth,
                'memory_cleaned_up': memory_growth < 50,  # Less than 50MB growth
                'chunks_processed': len(memory_measurements)
            }
        )
        
        results.append(result)
        print(f"    {test_name}: {memory_peak:.1f}MB peak, {memory_growth:.1f}MB growth")
        
        return results
    
    def save_results(self, all_results: List[ContainerResourceResult]):
        """Save container resource test results"""
        
        # Convert to JSON format
        json_results = []
        for result in all_results:
            json_results.append({
                'test_name': result.test_name,
                'container_name': result.container_name,
                'duration_seconds': result.duration_seconds,
                'memory_limit_mb': result.memory_limit_mb,
                'memory_peak_mb': result.memory_peak_mb,
                'memory_avg_mb': result.memory_avg_mb,
                'cpu_peak_percent': result.cpu_peak_percent,
                'cpu_avg_percent': result.cpu_avg_percent,
                'startup_time_seconds': result.startup_time_seconds,
                'cleanup_successful': result.cleanup_successful,
                'resource_compliance': result.resource_compliance,
                'custom_metrics': result.custom_metrics
            })
        
        # Save to file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_file = self.output_dir / f"container_resource_results_{timestamp}.json"
        
        with open(json_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'docker_available': self.check_docker_available(),
                'total_tests': len(json_results),
                'results': json_results
            }, f, indent=2)
        
        print(f"Container resource results saved to: {json_file}")
        
        # Generate summary
        self.generate_summary_report(all_results, timestamp)
    
    def generate_summary_report(self, results: List[ContainerResourceResult], timestamp: str):
        """Generate container resource summary report"""
        
        # Calculate summary statistics
        memory_compliance_tests = [r for r in results if r.test_name == "memory_limit_compliance"]
        startup_tests = [r for r in results if r.test_name == "startup_performance"]
        process_tests = [r for r in results if r.test_name == "process_memory_optimization"]
        
        summary = {
            'memory_compliance': {
                'total_tests': len(memory_compliance_tests),
                'compliant_containers': sum(1 for r in memory_compliance_tests if r.resource_compliance),
                'avg_memory_efficiency': sum(r.custom_metrics.get('memory_efficiency', 0) for r in memory_compliance_tests) / len(memory_compliance_tests) if memory_compliance_tests else 0
            },
            'startup_performance': {
                'total_tests': len(startup_tests),
                'avg_startup_time': sum(r.startup_time_seconds for r in startup_tests) / len(startup_tests) if startup_tests else 0,
                'fastest_startup': min(r.startup_time_seconds for r in startup_tests) if startup_tests else 0
            },
            'process_optimization': {
                'total_tests': len(process_tests),
                'memory_cleaned_up': sum(1 for r in process_tests if r.custom_metrics.get('memory_cleaned_up', False))
            }
        }
        
        print(f"\n=== Container Resource Summary ===")
        print(f"Memory compliance: {summary['memory_compliance']['compliant_containers']}/{summary['memory_compliance']['total_tests']} containers compliant")
        if summary['startup_performance']['total_tests'] > 0:
            print(f"Startup performance: {summary['startup_performance']['avg_startup_time']:.2f}s average")
        print(f"Process optimization: {summary['process_optimization']['memory_cleaned_up']}/{summary['process_optimization']['total_tests']} processes cleaned up properly")
        
        # Save summary
        summary_file = self.output_dir / f"container_resource_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)


async def main():
    """Main container resource testing execution"""
    print("=== Container Resource Optimization Testing ===")
    
    tester = ContainerResourceTester()
    all_results = []
    
    try:
        # Test memory limit compliance
        memory_results = await tester.test_memory_limit_compliance()
        all_results.extend(memory_results)
        
        # Test container startup performance
        startup_results = await tester.test_container_startup_performance()
        all_results.extend(startup_results)
        
        # Test process resource optimization (fallback)
        process_results = await tester.test_process_resource_optimization()
        all_results.extend(process_results)
        
        # Save all results
        tester.save_results(all_results)
        
        print(f"\nContainer resource testing completed: {len(all_results)} tests")
        
    except Exception as e:
        print(f"Container resource testing failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())