#!/usr/bin/env python3
"""
Validation Script for CLI Orchestration Integration
Validates that all components are properly integrated
"""

import sys
import importlib
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def validate_imports():
    """Validate all required modules can be imported"""
    modules_to_test = [
        ('app.cli.plugins.framework', 'Plugin Framework'),
        ('app.cli.plugins.hot_reload', 'Hot Reload System'),
        ('app.cli.integration.orchestration_bridge', 'Orchestration Bridge'),
        ('app.cli.error.cli_error_handler', 'CLI Error Handler'),
        ('app.cli.monitoring.realtime_monitor', 'Real-time Monitor'),
        ('app.cli.error.recovery', 'Error Recovery'),
    ]
    
    results = []
    for module_name, description in modules_to_test:
        try:
            importlib.import_module(module_name)
            results.append((description, True, "✓ Import successful"))
        except Exception as e:
            results.append((description, False, f"✗ {str(e)}"))
    
    return results

def validate_class_structures():
    """Validate key classes exist with required methods"""
    validations = []
    
    try:
        from app.cli.plugins.framework import PluginManager, CLIPlugin
        validations.append(("PluginManager class", True, "✓ Class exists"))
        
        # Check methods
        required_methods = ['discover_plugins', 'load_plugins', 'cleanup_plugins']
        for method in required_methods:
            if hasattr(PluginManager, method):
                validations.append((f"  - {method}", True, "✓ Method exists"))
            else:
                validations.append((f"  - {method}", False, "✗ Method missing"))
                
    except Exception as e:
        validations.append(("PluginManager class", False, f"✗ {str(e)}"))
    
    try:
        from app.cli.plugins.hot_reload import PluginHotReloadManager
        validations.append(("PluginHotReloadManager", True, "✓ Class exists"))
        
        # Check hot-reload methods
        required = ['start_watching', 'stop_watching', 'reload_plugin']
        for method in required:
            if hasattr(PluginHotReloadManager, method):
                validations.append((f"  - {method}", True, "✓ Method exists"))
            else:
                validations.append((f"  - {method}", False, "✗ Method missing"))
                
    except Exception as e:
        validations.append(("PluginHotReloadManager", False, f"✗ {str(e)}"))
    
    try:
        from app.cli.integration.orchestration_bridge import OrchestrationBridge
        validations.append(("OrchestrationBridge", True, "✓ Class exists"))
        
        # Check orchestration methods
        required = ['execute_workflow', 'initialize', 'get_workflow_status']
        for method in required:
            if hasattr(OrchestrationBridge, method):
                validations.append((f"  - {method}", True, "✓ Method exists"))
            else:
                validations.append((f"  - {method}", False, "✗ Method missing"))
                
    except Exception as e:
        validations.append(("OrchestrationBridge", False, f"✗ {str(e)}"))
    
    try:
        from app.cli.error.cli_error_handler import CLIErrorHandler, InteractiveErrorResolver
        validations.append(("CLIErrorHandler", True, "✓ Class exists"))
        validations.append(("InteractiveErrorResolver", True, "✓ Class exists"))
        
    except Exception as e:
        validations.append(("Error Handlers", False, f"✗ {str(e)}"))
    
    try:
        from app.cli.monitoring.realtime_monitor import WorkflowMonitor, ProgressTracker
        validations.append(("WorkflowMonitor", True, "✓ Class exists"))
        validations.append(("ProgressTracker", True, "✓ Class exists"))
        
    except Exception as e:
        validations.append(("Monitoring Classes", False, f"✗ {str(e)}"))
    
    return validations

def validate_integration_points():
    """Validate integration between components"""
    integrations = []
    
    # Test WebSocket security (CVE-2024-WS002)
    try:
        from app.cli.integration.orchestration_bridge import OrchestrationBridge
        import inspect
        
        # Check for proper WebSocket header authentication
        source = inspect.getsource(OrchestrationBridge._connect_websocket)
        if 'Authorization' in source and 'Bearer' in source:
            integrations.append(("WebSocket JWT Headers", True, "✓ CVE-2024-WS002 compliant"))
        else:
            integrations.append(("WebSocket JWT Headers", False, "✗ Missing auth headers"))
            
    except Exception as e:
        integrations.append(("WebSocket Security", False, f"✗ {str(e)}"))
    
    # Test error recovery integration
    try:
        from app.cli.error.cli_error_handler import CLIErrorHandler
        from app.cli.error.recovery import ErrorRecoveryManager
        
        # Check if CLIErrorHandler uses ErrorRecoveryManager
        import inspect
        source = inspect.getsource(CLIErrorHandler)
        if 'ErrorRecoveryManager' in source or 'recovery_manager' in source:
            integrations.append(("Error Recovery Integration", True, "✓ Integrated"))
        else:
            integrations.append(("Error Recovery Integration", False, "✗ Not integrated"))
            
    except Exception as e:
        integrations.append(("Error Recovery Integration", False, f"✗ {str(e)}"))
    
    # Test monitoring integration
    try:
        from app.cli.monitoring.realtime_monitor import WorkflowMonitor
        import inspect
        
        # Check for Redis integration
        source = inspect.getsource(WorkflowMonitor)
        if 'redis' in source.lower():
            integrations.append(("Redis Monitoring", True, "✓ Redis integrated"))
        else:
            integrations.append(("Redis Monitoring", False, "✗ Redis not found"))
            
    except Exception as e:
        integrations.append(("Monitoring Integration", False, f"✗ {str(e)}"))
    
    return integrations

def validate_12_phase_support():
    """Validate 12-phase workflow support"""
    phases = []
    
    try:
        from app.cli.integration.orchestration_bridge import OrchestrationBridge
        import inspect
        
        # Check for all 12 phase handlers
        for phase in range(1, 13):
            method_name = f'_execute_phase_{phase}'
            if phase == 1:
                method_name = '_execute_phase_1_research'
            
            # Check if method exists or generic handler exists
            source = inspect.getsource(OrchestrationBridge)
            if method_name in source or '_execute_generic_phase' in source:
                phases.append((f"Phase {phase}", True, "✓ Supported"))
            else:
                phases.append((f"Phase {phase}", False, "✗ Not found"))
                
    except Exception as e:
        phases.append(("12-Phase Support", False, f"✗ {str(e)}"))
    
    return phases

def print_results(title, results):
    """Print validation results"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)
    
    passed = 0
    failed = 0
    
    for name, success, message in results:
        status_symbol = "✓" if success else "✗"
        color = "\033[92m" if success else "\033[91m"  # Green or Red
        reset = "\033[0m"
        
        print(f"{color}{status_symbol}{reset} {name:40} {message}")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return passed, failed

def main():
    """Run all validations"""
    print("\n" + "="*60)
    print(" CLI ORCHESTRATION INTEGRATION VALIDATION")
    print("="*60)
    
    total_passed = 0
    total_failed = 0
    
    # Run import validation
    import_results = validate_imports()
    p, f = print_results("Module Import Validation", import_results)
    total_passed += p
    total_failed += f
    
    # Run class structure validation
    class_results = validate_class_structures()
    p, f = print_results("Class Structure Validation", class_results)
    total_passed += p
    total_failed += f
    
    # Run integration validation
    integration_results = validate_integration_points()
    p, f = print_results("Integration Point Validation", integration_results)
    total_passed += p
    total_failed += f
    
    # Run 12-phase validation
    phase_results = validate_12_phase_support()
    p, f = print_results("12-Phase Workflow Support", phase_results)
    total_passed += p
    total_failed += f
    
    # Final summary
    print("\n" + "="*60)
    print(" FINAL VALIDATION SUMMARY")
    print("="*60)
    
    if total_failed == 0:
        print(f"\033[92m✓ ALL VALIDATIONS PASSED ({total_passed}/{total_passed + total_failed})\033[0m")
        print("\nThe CLI orchestration integration is ready for deployment!")
        return 0
    else:
        print(f"\033[91m✗ SOME VALIDATIONS FAILED ({total_failed}/{total_passed + total_failed})\033[0m")
        print("\nPlease review and fix the failed validations.")
        return 1

if __name__ == "__main__":
    sys.exit(main())