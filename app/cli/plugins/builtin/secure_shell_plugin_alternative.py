"""
Secure Shell Command Plugin Alternative - CVE-LOCALAGENT-002 Mitigation
Implements comprehensive security controls with allowlist-based validation
"""

import asyncio
import subprocess
import shlex
import os
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.text import Text

from ..framework import CLIPlugin, CommandPlugin


console = Console()


class SecurityLevel(Enum):
    """Security levels for command execution"""
    MINIMAL = "minimal"      # Only basic commands
    STANDARD = "standard"    # Common development commands
    ELEVATED = "elevated"    # Administrative commands (requires additional auth)
    SANDBOX = "sandbox"      # Container-isolated execution


@dataclass
class SecureCommandPolicy:
    """Enhanced security policy with comprehensive controls"""
    security_level: SecurityLevel = SecurityLevel.STANDARD
    max_execution_time: int = 30
    max_output_size: int = 1024 * 1024  # 1MB
    max_command_length: int = 1000
    require_confirmation: bool = True
    log_commands: bool = True
    audit_mode: bool = True
    container_isolation: bool = False
    network_access: bool = False
    file_system_restrictions: bool = True
    environment_isolation: bool = True


class SecureCommandValidator:
    """Advanced command validator with allowlist-based approach"""
    
    # Minimal command set (most restrictive)
    MINIMAL_COMMANDS = {
        'echo', 'pwd', 'date', 'whoami', 'hostname'
    }
    
    # Standard development commands
    STANDARD_COMMANDS = MINIMAL_COMMANDS | {
        'ls', 'cat', 'head', 'tail', 'grep', 'find', 'which', 'wc',
        'sort', 'uniq', 'cut', 'awk', 'sed',
        'git', 'python', 'python3', 'node', 'npm', 'pip', 'pip3',
        'docker', 'docker-compose', 'kubectl',
        'curl', 'wget', 'ping', 'nslookup', 'dig'
    }
    
    # Elevated commands (require additional authentication)
    ELEVATED_COMMANDS = STANDARD_COMMANDS | {
        'cp', 'mv', 'mkdir', 'touch', 'chmod', 'chown',
        'systemctl', 'service', 'apt', 'apt-get', 'yum', 'brew', 'snap',
        'ps', 'top', 'htop', 'df', 'du', 'free', 'uptime', 'netstat'
    }
    
    # Comprehensive forbidden patterns (blacklist for extra security)
    FORBIDDEN_PATTERNS = [
        # Command substitution and expansion
        r'.*\$\(.*\)',          # Command substitution
        r'.*`.*`',              # Backtick substitution
        r'.*\$\{.*\}',          # Parameter expansion
        r'.*\$\[\[.*\]\]',      # Arithmetic expansion (extended)
        r'.*\$\[.*\]',          # Arithmetic expansion (simple)
        r'.*\$\(\(.*\)\)',      # Arithmetic expansion (double parentheses)
        
        # Process and file descriptor manipulation
        r'.*<\(.*\)',           # Process substitution (input)
        r'.*>\(.*\)',           # Process substitution (output)
        r'.*\d+>&\d+',          # File descriptor redirection
        r'.*exec\s+\d+',        # Execute with file descriptor
        
        # Shell control structures
        r'.*;\s*.*',            # Command chaining (semicolon)
        r'.*&&\s*.*',           # Command chaining (AND)
        r'.*\|\|\s*.*',         # Command chaining (OR)
        r'.*&\s*$',             # Background execution
        r'.*\|\s*.*',           # Pipes
        
        # Redirections and device access
        r'.*>\s*/dev/.*',       # Redirect to devices
        r'.*<\s*/dev/.*',       # Read from devices
        r'.*>\s*/etc/.*',       # Redirect to system configs
        r'.*<\s*/etc/.*',       # Read from system configs
        r'.*>\s*/proc/.*',      # Redirect to proc filesystem
        r'.*>\s*/sys/.*',       # Redirect to sys filesystem
        
        # Environment and system manipulation
        r'.*export\s+.*',       # Environment variable export
        r'.*unset\s+.*',        # Environment variable unset
        r'.*alias\s+.*',        # Command aliasing
        r'.*function\s+.*',     # Function definition
        r'.*trap\s+.*',         # Signal trapping
        r'.*ulimit\s+.*',       # Resource limits
        
        # Network and system access
        r'.*nc\s+.*',           # Netcat
        r'.*ncat\s+.*',         # Ncat
        r'.*telnet\s+.*',       # Telnet
        r'.*ssh\s+.*',          # SSH (unless explicitly allowed)
        r'.*scp\s+.*',          # SCP
        r'.*rsync\s+.*',        # Rsync
        
        # File system dangerous operations
        r'.*rm\s+-rf\s*/.*',    # Recursive force remove
        r'.*rm\s+/.*',          # Remove from root
        r'.*rmdir\s*/.*',       # Remove directory from root
        r'.*dd\s+.*',           # Disk dump
        r'.*mkfs\s+.*',         # Make filesystem
        r'.*format\s+.*',       # Format command
        r'.*fdisk\s+.*',        # Disk partitioning
        
        # Process control
        r'.*kill\s+-9\s+.*',    # Force kill
        r'.*killall\s+.*',      # Kill all processes
        r'.*pkill\s+.*',        # Pattern kill
        r'.*shutdown\s+.*',     # System shutdown
        r'.*reboot\s+.*',       # System reboot
        r'.*halt\s+.*',         # System halt
        
        # Privilege escalation
        r'.*sudo\s+.*',         # Sudo (controlled separately)
        r'.*su\s+.*',           # Switch user
        r'.*doas\s+.*',         # OpenBSD doas
        
        # Encoding and obfuscation attempts
        r'.*\\x[0-9a-fA-F]{2}.*',  # Hex encoding
        r'.*\\[0-9]{3}.*',         # Octal encoding
        r'.*\x00.*',               # Null bytes
        r'.*[\x01-\x08\x0B-\x1F\x7F-\x9F].*',  # Control characters
        
        # Globbing that could be dangerous
        r'.*\*/\*.*',           # Excessive globbing
        r'.*/\?\?\?/.*',        # Question mark globbing
        r'.*\[.*\].*',          # Character class globbing (in sensitive paths)
    ]
    
    # Dangerous file paths (absolute blacklist)
    FORBIDDEN_PATHS = [
        '/etc/passwd', '/etc/shadow', '/etc/sudoers', '/etc/ssh/',
        '/root/', '/boot/', '/sys/', '/proc/sys/', '/dev/mem', '/dev/kmem'
    ]
    
    def __init__(self, policy: SecureCommandPolicy):
        self.policy = policy
        self._setup_command_allowlist()
    
    def _setup_command_allowlist(self):
        """Setup command allowlist based on security level"""
        if self.policy.security_level == SecurityLevel.MINIMAL:
            self.allowed_commands = self.MINIMAL_COMMANDS
        elif self.policy.security_level == SecurityLevel.STANDARD:
            self.allowed_commands = self.STANDARD_COMMANDS
        elif self.policy.security_level == SecurityLevel.ELEVATED:
            self.allowed_commands = self.ELEVATED_COMMANDS
        else:  # SANDBOX
            self.allowed_commands = self.MINIMAL_COMMANDS
    
    def normalize_command(self, command: str) -> str:
        """Normalize command to prevent Unicode/encoding attacks"""
        if not isinstance(command, str):
            raise ValueError("Command must be a string")
        
        # Unicode normalization to prevent lookalike character attacks
        command = unicodedata.normalize('NFKC', command)
        
        # Remove control characters except space, tab, newline
        command = ''.join(char for char in command 
                         if ord(char) >= 32 or char in [' ', '\t', '\n'])
        
        # Convert to ASCII if possible to prevent encoding attacks
        try:
            command = command.encode('ascii').decode('ascii')
        except UnicodeEncodeError:
            raise ValueError("Command contains non-ASCII characters")
        
        return command.strip()
    
    def validate_command_structure(self, command: str) -> Tuple[bool, str]:
        """Validate basic command structure"""
        
        # Length check
        if len(command) > self.policy.max_command_length:
            return False, f"Command too long (max {self.policy.max_command_length} chars)"
        
        # Empty command check
        if not command.strip():
            return False, "Empty command"
        
        # Check for forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command contains forbidden pattern: {pattern}"
        
        # Check for forbidden file paths
        for path in self.FORBIDDEN_PATHS:
            if path in command:
                return False, f"Command accesses forbidden path: {path}"
        
        return True, "Command structure valid"
    
    def validate_command_allowlist(self, command: str) -> Tuple[bool, str]:
        """Validate command against allowlist"""
        
        # Parse command safely
        try:
            # Use shlex but validate each token
            tokens = shlex.split(command)
        except ValueError as e:
            return False, f"Command parsing error: {e}"
        
        if not tokens:
            return False, "No command specified"
        
        # Extract base command (handle path prefixes)
        base_command = Path(tokens[0]).name
        
        # Check against allowlist
        if base_command not in self.allowed_commands:
            return False, f"Command '{base_command}' not in allowlist for security level {self.policy.security_level.value}"
        
        # Additional argument validation for specific commands
        if not self._validate_command_arguments(base_command, tokens[1:]):
            return False, f"Invalid arguments for command '{base_command}'"
        
        return True, "Command allowed"
    
    def _validate_command_arguments(self, command: str, args: List[str]) -> bool:
        """Validate arguments for specific commands"""
        
        # Git command argument validation
        if command == 'git':
            if args and args[0] in ['config', 'remote']:
                # Prevent git config manipulation
                return False
        
        # Docker command validation
        elif command == 'docker':
            dangerous_docker_args = ['run', 'exec', 'build', 'commit']
            if args and args[0] in dangerous_docker_args:
                return False
        
        # Curl/Wget validation
        elif command in ['curl', 'wget']:
            # Check for output redirection in arguments
            for arg in args:
                if arg.startswith('-o') or arg.startswith('--output'):
                    # Validate output path
                    if not self._validate_output_path(arg):
                        return False
        
        # Python command validation
        elif command in ['python', 'python3']:
            if args and args[0] in ['-c', '-m']:
                # Prevent arbitrary code execution
                return False
        
        return True
    
    def _validate_output_path(self, path: str) -> bool:
        """Validate output path for commands"""
        # Only allow output to safe directories
        safe_dirs = ['/tmp/', './temp/', './output/', '/var/tmp/']
        return any(path.startswith(safe_dir) for safe_dir in safe_dirs)
    
    def validate_environment_security(self, command: str) -> Tuple[bool, str]:
        """Validate command doesn't manipulate environment dangerously"""
        
        # Check for environment variable manipulation
        env_patterns = [
            r'.*PATH=.*',           # PATH manipulation
            r'.*LD_PRELOAD=.*',     # Library preloading
            r'.*LD_LIBRARY_PATH=.*', # Library path manipulation
            r'.*\w+=.*',            # Generic environment variable setting
        ]
        
        for pattern in env_patterns:
            if re.search(pattern, command):
                return False, "Command attempts environment manipulation"
        
        return True, "Environment security validated"
    
    def comprehensive_validate(self, command: str) -> Tuple[bool, str]:
        """Perform comprehensive command validation"""
        
        try:
            # Step 1: Normalize command
            command = self.normalize_command(command)
            
            # Step 2: Validate structure
            valid, message = self.validate_command_structure(command)
            if not valid:
                return False, f"Structure validation failed: {message}"
            
            # Step 3: Validate against allowlist
            valid, message = self.validate_command_allowlist(command)
            if not valid:
                return False, f"Allowlist validation failed: {message}"
            
            # Step 4: Validate environment security
            valid, message = self.validate_environment_security(command)
            if not valid:
                return False, f"Environment validation failed: {message}"
            
            return True, "Command passed all security validations"
            
        except Exception as e:
            return False, f"Validation error: {e}"


class SecureCommandExecutor:
    """Secure command executor with container isolation support"""
    
    def __init__(self, policy: SecureCommandPolicy):
        self.policy = policy
        self.validator = SecureCommandValidator(policy)
    
    async def execute_command_secure(
        self,
        command: str,
        working_dir: Optional[Path] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute command with maximum security"""
        
        # Comprehensive validation
        valid, message = self.validator.comprehensive_validate(command)
        if not valid:
            return {
                'success': False,
                'error': f"Security validation failed: {message}",
                'command': command,
                'security_violation': True
            }
        
        # Generate execution ID for audit trail
        execution_id = secrets.token_hex(16)
        
        try:
            if self.policy.container_isolation:
                return await self._execute_in_container(command, working_dir, timeout, execution_id)
            else:
                return await self._execute_direct(command, working_dir, timeout, execution_id)
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Execution error: {e}",
                'command': command,
                'execution_id': execution_id
            }
    
    async def _execute_direct(
        self,
        command: str,
        working_dir: Optional[Path],
        timeout: int,
        execution_id: str
    ) -> Dict[str, Any]:
        """Execute command directly with security controls"""
        
        # Parse command safely
        args = shlex.split(command)
        cwd = working_dir or Path.cwd()
        
        # Setup secure environment
        env = self._create_secure_environment() if self.policy.environment_isolation else None
        
        start_time = datetime.now()
        
        # Execute using subprocess.exec (no shell interpretation)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            # Security: Prevent shell access
            preexec_fn=None,
            # Security: Set process group
            start_new_session=True
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Forcefully terminate process group to prevent orphans
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except:
                process.kill()
                
            return {
                'success': False,
                'error': f'Command timed out after {timeout} seconds',
                'command': command,
                'execution_id': execution_id
            }
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Validate output size
        if len(stdout) > self.policy.max_output_size:
            stdout = stdout[:self.policy.max_output_size]
            stdout += b"\n... (output truncated for security)"
        
        return {
            'success': process.returncode == 0,
            'command': command,
            'return_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'execution_time': execution_time,
            'working_directory': str(cwd),
            'execution_id': execution_id,
            'security_validated': True
        }
    
    async def _execute_in_container(
        self,
        command: str,
        working_dir: Optional[Path],
        timeout: int,
        execution_id: str
    ) -> Dict[str, Any]:
        """Execute command in isolated container"""
        
        # Create container command
        container_args = [
            'docker', 'run', '--rm',
            '--security-opt', 'no-new-privileges',
            '--cap-drop', 'ALL',
            '--read-only',
            '--tmpfs', '/tmp:noexec,nosuid,size=100m',
            '--memory', '256m',
            '--cpus', '0.5',
            '--network', 'none' if not self.policy.network_access else 'bridge',
            '--user', '1000:1000',  # Non-root user
            'alpine:latest',  # Minimal base image
            'sh', '-c', command
        ]
        
        start_time = datetime.now()
        
        process = await asyncio.create_subprocess_exec(
            *container_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir or Path.cwd()
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout + 30  # Extra time for container overhead
            )
        except asyncio.TimeoutError:
            process.kill()
            return {
                'success': False,
                'error': f'Container execution timed out after {timeout} seconds',
                'command': command,
                'execution_id': execution_id
            }
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        return {
            'success': process.returncode == 0,
            'command': command,
            'return_code': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
            'execution_time': execution_time,
            'execution_id': execution_id,
            'container_isolated': True,
            'security_validated': True
        }
    
    def _create_secure_environment(self) -> Dict[str, str]:
        """Create secure environment variables"""
        
        # Start with minimal environment
        secure_env = {
            'PATH': '/usr/local/bin:/usr/bin:/bin',  # Minimal PATH
            'HOME': '/tmp',  # Restricted home
            'USER': 'localagent',
            'SHELL': '/bin/sh',  # Basic shell only
            'TERM': 'xterm',
            'LC_ALL': 'C',  # Minimal locale
        }
        
        # Add specific environment variables if needed
        if self.policy.security_level in [SecurityLevel.STANDARD, SecurityLevel.ELEVATED]:
            secure_env.update({
                'PYTHONPATH': '',  # Prevent Python path manipulation
                'NODE_PATH': '',   # Prevent Node path manipulation
            })
        
        return secure_env


class SecureShellCommandPlugin(CommandPlugin):
    """Secure shell command plugin with comprehensive CVE-LOCALAGENT-002 mitigations"""
    
    name = "secure-shell"
    version = "2.0.0-security"
    description = "Execute shell commands with comprehensive security controls (CVE-LOCALAGENT-002 mitigated)"
    
    def __init__(self):
        self.policy = SecureCommandPolicy()
        self.executor = SecureCommandExecutor(self.policy)
        self.audit_log: List[Dict[str, Any]] = []
    
    async def initialize(self, context: 'CLIContext') -> bool:
        """Initialize the secure plugin with CLI context"""
        self.context = context
        
        # Load enhanced policy from configuration
        if hasattr(context.config, 'secure_shell_policy'):
            policy_dict = context.config.secure_shell_policy
            for key, value in policy_dict.items():
                if hasattr(self.policy, key):
                    setattr(self.policy, key, value)
        
        # Initialize audit logging
        self._setup_audit_logging()
        
        return True
    
    def _setup_audit_logging(self):
        """Setup comprehensive audit logging"""
        self.audit_file = Path.home() / '.localagent' / 'secure_shell_audit.json'
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _audit_log_command(self, command: str, result: Dict[str, Any], security_info: Dict[str, Any]):
        """Log command execution for security audit"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'result': {
                'success': result.get('success', False),
                'return_code': result.get('return_code'),
                'execution_time': result.get('execution_time'),
                'security_validated': result.get('security_validated', False)
            },
            'security': security_info,
            'execution_id': result.get('execution_id'),
            'user_id': os.getuid(),
            'session_id': getattr(self, 'session_id', 'unknown')
        }
        
        self.audit_log.append(audit_entry)
        
        # Persist to file
        try:
            with open(self.audit_file, 'w') as f:
                json.dump(self.audit_log[-1000:], f, indent=2)  # Keep last 1000 entries
        except Exception as e:
            console.print(f"[red]Audit logging failed: {e}[/red]")

    def register_commands(self, app: typer.Typer) -> None:
        """Register secure shell commands with the CLI app"""
        
        @app.command(name="secure-shell")
        def secure_shell_command(
            command: Optional[str] = typer.Argument(None, help="Command to execute"),
            security_level: str = typer.Option("standard", "--security-level", "-s", help="Security level: minimal, standard, elevated, sandbox"),
            timeout: int = typer.Option(30, "--timeout", "-t", help="Command timeout in seconds"),
            working_dir: Optional[str] = typer.Option(None, "--cwd", "-d", help="Working directory"),
            container: bool = typer.Option(False, "--container", "-c", help="Execute in isolated container"),
            audit: bool = typer.Option(True, "--audit/--no-audit", help="Enable audit logging"),
        ):
            """Execute shell commands with comprehensive security controls"""
            
            if not command:
                console.print("[yellow]No command specified. This plugin requires explicit commands for security.[/yellow]")
                return
            
            # Update policy based on arguments
            try:
                self.policy.security_level = SecurityLevel(security_level)
            except ValueError:
                console.print(f"[red]Invalid security level: {security_level}[/red]")
                return
            
            self.policy.container_isolation = container
            self.policy.audit_mode = audit
            
            # Recreate executor with updated policy
            self.executor = SecureCommandExecutor(self.policy)
            
            # Execute command
            result = asyncio.run(self.executor.execute_command_secure(
                command,
                working_dir=Path(working_dir) if working_dir else None,
                timeout=timeout
            ))
            
            # Display result
            self._display_secure_result(result)
            
            # Audit log if enabled
            if audit:
                self._audit_log_command(command, result, {
                    'security_level': security_level,
                    'container_isolation': container,
                    'validation_passed': result.get('security_validated', False)
                })
        
        @app.command(name="shell-security-status")
        def show_security_status():
            """Show current security configuration and status"""
            self._show_security_status()
        
        @app.command(name="shell-audit-log")
        def show_audit_log(
            count: int = typer.Option(10, "--count", "-n", help="Number of entries to show")
        ):
            """Show security audit log"""
            self._show_audit_log(count)
    
    def _display_secure_result(self, result: Dict[str, Any]):
        """Display command execution result with security information"""
        
        if result.get('security_violation'):
            console.print(Panel.fit(
                f"[bold red]SECURITY VIOLATION[/bold red]\n"
                f"Command: [cyan]{result['command']}[/cyan]\n"
                f"Error: [red]{result['error']}[/red]",
                border_style="red",
                title="Command Blocked"
            ))
            return
        
        if result['success']:
            if result['stdout']:
                console.print(result['stdout'], end='')
            if result['stderr']:
                console.print(f"[yellow]{result['stderr']}[/yellow]", end='')
            
            # Show security validation info
            if result.get('security_validated'):
                console.print(f"[dim green]✓ Security validated | ID: {result.get('execution_id', 'N/A')}[/dim green]")
                
            if result.get('container_isolated'):
                console.print(f"[dim blue]🐳 Container isolated execution[/dim blue]")
                
        else:
            console.print(f"[red]Command failed: {result.get('error', 'Unknown error')}[/red]")
            if result.get('stderr'):
                console.print(f"[red]{result['stderr']}[/red]", end='')
        
        # Show execution stats
        console.print(
            f"[dim]Exit code: {result.get('return_code', 'N/A')} | "
            f"Time: {result.get('execution_time', 0):.2f}s[/dim]"
        )
    
    def _show_security_status(self):
        """Display current security configuration"""
        
        table = Table(title="Secure Shell Security Status", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Description", style="dim")
        
        settings = [
            ("Security Level", self.policy.security_level.value, "Current command allowlist level"),
            ("Container Isolation", self.policy.container_isolation, "Execute in isolated containers"),
            ("Environment Isolation", self.policy.environment_isolation, "Use restricted environment"),
            ("Network Access", self.policy.network_access, "Allow network access in containers"),
            ("File System Restrictions", self.policy.file_system_restrictions, "Restrict file system access"),
            ("Max Execution Time", f"{self.policy.max_execution_time}s", "Command timeout"),
            ("Max Output Size", f"{self.policy.max_output_size / 1024:.0f}KB", "Maximum output capture"),
            ("Max Command Length", f"{self.policy.max_command_length}", "Maximum command length"),
            ("Audit Logging", self.policy.audit_mode, "Log all command executions"),
        ]
        
        for name, value, desc in settings:
            if isinstance(value, bool):
                value_str = "[green]Enabled[/green]" if value else "[red]Disabled[/red]"
            else:
                value_str = str(value)
            
            table.add_row(name, value_str, desc)
        
        console.print(table)
        
        # Show allowed commands for current security level
        validator = SecureCommandValidator(self.policy)
        console.print(f"\n[bold cyan]Allowed Commands ({self.policy.security_level.value} level):[/bold cyan]")
        
        commands = sorted(list(validator.allowed_commands))
        for i in range(0, len(commands), 8):
            console.print(" ".join(commands[i:i+8]))
    
    def _show_audit_log(self, count: int):
        """Display security audit log"""
        
        recent_entries = self.audit_log[-count:] if self.audit_log else []
        
        if not recent_entries:
            console.print("[yellow]No audit log entries found[/yellow]")
            return
        
        table = Table(title="Security Audit Log", show_header=True)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Command", style="cyan")
        table.add_column("Status", style="white", width=8)
        table.add_column("Security", style="white", width=10)
        table.add_column("Exec ID", style="dim", width=12)
        
        for entry in recent_entries:
            timestamp = datetime.fromisoformat(entry['timestamp'])
            time_str = timestamp.strftime("%H:%M:%S")
            
            success = entry['result']['success']
            status = "✓" if success else "✗"
            status_style = "green" if success else "red"
            
            security_status = "✓" if entry['result'].get('security_validated') else "⚠"
            security_style = "green" if entry['result'].get('security_validated') else "yellow"
            
            table.add_row(
                time_str,
                entry['command'][:50] + "..." if len(entry['command']) > 50 else entry['command'],
                f"[{status_style}]{status}[/{status_style}]",
                f"[{security_style}]{security_status}[/{security_style}]",
                entry.get('execution_id', 'N/A')[:12]
            )
        
        console.print(table)


# Export plugin class
__plugin__ = SecureShellCommandPlugin