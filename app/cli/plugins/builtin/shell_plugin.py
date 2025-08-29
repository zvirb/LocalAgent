"""
Secure Shell Command Plugin for LocalAgent CLI
Provides controlled shell command execution with safety features
"""

import asyncio
import subprocess
import shlex
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.text import Text

from ..framework import CLIPlugin, CommandPlugin


console = Console()


class CommandRisk(Enum):
    """Risk levels for commands"""
    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"
    FORBIDDEN = "forbidden"


@dataclass
class CommandPolicy:
    """Security policy for command execution"""
    allow_shell: bool = False
    allow_pipes: bool = False
    allow_redirects: bool = False
    allow_sudo: bool = False
    max_execution_time: int = 30
    max_output_size: int = 1024 * 1024  # 1MB
    require_confirmation: bool = True
    log_commands: bool = True
    sandbox_mode: bool = False


class CommandValidator:
    """Validates commands against security policies"""
    
    # Safe commands that can be executed without confirmation
    SAFE_COMMANDS = {
        'ls', 'pwd', 'echo', 'date', 'whoami', 'hostname', 
        'cat', 'head', 'tail', 'grep', 'find', 'which',
        'ps', 'top', 'df', 'du', 'free', 'uptime',
        'git', 'python', 'node', 'npm', 'pip', 'curl', 'wget'
    }
    
    # Commands that need confirmation
    MODERATE_COMMANDS = {
        'cp', 'mv', 'mkdir', 'touch', 'chmod', 'chown',
        'docker', 'docker-compose', 'systemctl', 'service',
        'apt', 'apt-get', 'yum', 'brew', 'snap'
    }
    
    # Dangerous commands that are blocked by default
    DANGEROUS_COMMANDS = {
        'rm', 'rmdir', 'dd', 'format', 'mkfs', 'fdisk',
        'kill', 'killall', 'shutdown', 'reboot', 'halt'
    }
    
    # Absolutely forbidden commands and patterns
    # CVE-LOCALAGENT-002 MITIGATION: Comprehensive attack pattern prevention
    FORBIDDEN_PATTERNS = [
        # Original patterns
        r'.*>\s*/dev/.*',  # Redirect to devices
        r'.*\|\s*sudo.*',  # Pipe to sudo
        r'.*;\s*rm\s+-rf.*',  # rm -rf in command chain
        r'.*/etc/passwd.*',  # Password file access
        r'.*/etc/shadow.*',  # Shadow file access
        r'.*\$\(.*\)',  # Command substitution
        r'.*`.*`',  # Backtick substitution
        
        # CVE-LOCALAGENT-002: Environment variable injection attacks
        r'.*\$\{[^}]*\}.*',  # Variable expansion ${...}
        r'.*\$[A-Z_][A-Z0-9_]*=.*',  # Environment variable assignment
        
        # Process substitution attacks  
        r'.*<\([^)]*\).*',   # Process substitution <(...)
        r'.*>\([^)]*\).*',   # Process substitution >(...)
        
        # Arithmetic expansion injection
        r'.*\$\(\([^)]*\)\).*',  # Arithmetic expansion $((...)
        r'.*\$\[[^\]]*\].*',     # Alternative arithmetic $[...]
        
        # Alternative command chaining
        r'.*[;&|]\s*(rm|dd|format|mkfs|shutdown|reboot).*',  # Dangerous commands after separators
        r'.*\\\n.*',         # Line continuation attacks
        r'.*\x00.*',         # Null byte injection
        
        # Additional sensitive paths  
        r'.*/etc/sudoers.*',
        r'.*/root/.*',
        r'.*/home/[^/]+/\.ssh/.*',
        r'.*\.aws/credentials.*',
        r'.*\.docker/config\.json.*'
    ]
    
    # CVE-LOCALAGENT-002: Allowlist-based validation (more secure than blocklist)
    ALLOWED_COMMANDS = {
        # File operations (read-only safe)
        'ls', 'pwd', 'cat', 'head', 'tail', 'less', 'more', 'file', 'stat',
        'find', 'locate', 'which', 'whereis', 'realpath', 'readlink',
        
        # System information (safe)  
        'date', 'uptime', 'whoami', 'hostname', 'uname', 'id', 'groups',
        'ps', 'top', 'htop', 'df', 'du', 'free', 'lscpu', 'lsblk',
        
        # Text processing (safe)
        'grep', 'egrep', 'fgrep', 'awk', 'sed', 'sort', 'uniq', 'wc',
        'cut', 'tr', 'echo', 'printf',
        
        # Development tools (generally safe)
        'git', 'python', 'python3', 'node', 'npm', 'pip', 'pip3',
        'curl', 'wget', 'ssh', 'scp', 'rsync',
        
        # Container tools (with restrictions)
        'docker', 'docker-compose', 'kubectl', 'helm'
    }
    
    def __init__(self, policy: CommandPolicy):
        self.policy = policy
    
    def assess_risk(self, command: str) -> CommandRisk:
        """Assess the risk level of a command"""
        
        # Check for forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.match(pattern, command):
                return CommandRisk.FORBIDDEN
        
        # Parse command
        try:
            parts = shlex.split(command)
            if not parts:
                return CommandRisk.SAFE
            
            base_command = Path(parts[0]).name
            
            # Check command categories
            if base_command in self.SAFE_COMMANDS:
                return CommandRisk.SAFE
            elif base_command in self.MODERATE_COMMANDS:
                return CommandRisk.MODERATE
            elif base_command in self.DANGEROUS_COMMANDS:
                return CommandRisk.DANGEROUS
            
            # Check for sudo
            if base_command == 'sudo' or 'sudo' in parts:
                if not self.policy.allow_sudo:
                    return CommandRisk.FORBIDDEN
                return CommandRisk.DANGEROUS
            
            # Check for pipes and redirects
            if not self.policy.allow_pipes and '|' in command:
                return CommandRisk.MODERATE
            if not self.policy.allow_redirects and ('>' in command or '<' in command):
                return CommandRisk.MODERATE
            
            # Default to moderate for unknown commands
            return CommandRisk.MODERATE
            
        except Exception:
            # If we can't parse it, it's suspicious
            return CommandRisk.DANGEROUS
    
    def validate_command(self, command: str) -> Tuple[bool, str]:
        """Validate if a command can be executed"""
        
        risk = self.assess_risk(command)
        
        if risk == CommandRisk.FORBIDDEN:
            return False, "Command is forbidden by security policy"
        
        if risk == CommandRisk.DANGEROUS and self.policy.sandbox_mode:
            return False, "Dangerous commands are not allowed in sandbox mode"
        
        if self.policy.require_confirmation and risk != CommandRisk.SAFE:
            # Will need user confirmation
            return True, f"Command requires confirmation (risk: {risk.value})"
        
        return True, "Command validated"


class CommandHistory:
    """Manages command history"""
    
    def __init__(self, history_file: Path = None):
        self.history_file = history_file or Path.home() / '.localagent' / 'shell_history.json'
        self.history: List[Dict[str, Any]] = []
        self.load_history()
    
    def load_history(self):
        """Load command history from file"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
    
    def save_history(self):
        """Save command history to file"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump(self.history[-1000:], f, indent=2)  # Keep last 1000 commands
    
    def add_command(self, command: str, result: Dict[str, Any]):
        """Add command to history"""
        self.history.append({
            'command': command,
            'timestamp': datetime.now().isoformat(),
            'result': result
        })
        self.save_history()
    
    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent commands"""
        return self.history[-count:]


class ShellCommandPlugin(CommandPlugin):
    """Plugin that provides secure shell command execution"""
    
    name = "shell"
    version = "1.0.0"
    description = "Execute shell commands with security controls"
    
    def __init__(self):
        self.policy = CommandPolicy()
        self.validator = CommandValidator(self.policy)
        self.history = CommandHistory()
        self.current_directory = Path.cwd()
    
    async def initialize(self, context: 'CLIContext') -> bool:
        """Initialize the plugin with CLI context"""
        self.context = context
        
        # Load policy from configuration
        if hasattr(context.config, 'shell_policy'):
            policy_dict = context.config.shell_policy
            for key, value in policy_dict.items():
                if hasattr(self.policy, key):
                    setattr(self.policy, key, value)
        
        return True
    
    def register_commands(self, app: typer.Typer) -> None:
        """Register shell commands with the CLI app"""
        
        @app.command(name="shell")
        def shell_command(
            command: Optional[str] = typer.Argument(None, help="Command to execute"),
            interactive: bool = typer.Option(False, "--interactive", "-i", help="Start interactive shell"),
            safe_mode: bool = typer.Option(True, "--safe/--unsafe", help="Enable safety checks"),
            timeout: int = typer.Option(30, "--timeout", "-t", help="Command timeout in seconds"),
            working_dir: Optional[str] = typer.Option(None, "--cwd", "-d", help="Working directory"),
        ):
            """Execute shell commands with security controls"""
            
            if interactive:
                asyncio.run(self.interactive_shell(safe_mode))
            elif command:
                result = asyncio.run(self.execute_command(
                    command,
                    safe_mode=safe_mode,
                    timeout=timeout,
                    working_dir=Path(working_dir) if working_dir else None
                ))
                self.display_result(result)
            else:
                console.print("[yellow]No command specified. Use -i for interactive mode.[/yellow]")
        
        @app.command(name="sh")
        def shell_shortcut(
            command: str = typer.Argument(..., help="Command to execute")
        ):
            """Quick shell command execution (alias for shell)"""
            result = asyncio.run(self.execute_command(command, safe_mode=True))
            self.display_result(result)
        
        @app.command(name="shell-history")
        def show_history(
            count: int = typer.Option(10, "--count", "-n", help="Number of commands to show"),
            search: Optional[str] = typer.Option(None, "--search", "-s", help="Search pattern")
        ):
            """Show command history"""
            self.show_command_history(count, search)
        
        @app.command(name="shell-policy")
        def show_policy():
            """Show current security policy"""
            self.show_security_policy()
    
    async def execute_command(
        self,
        command: str,
        safe_mode: bool = True,
        timeout: int = 30,
        working_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Execute a shell command with security controls"""
        
        # Update policy for this execution
        original_timeout = self.policy.max_execution_time
        self.policy.max_execution_time = timeout
        
        try:
            # Validate command
            if safe_mode:
                valid, message = self.validator.validate_command(command)
                if not valid:
                    return {
                        'success': False,
                        'error': message,
                        'command': command
                    }
                
                # Check risk and confirm if needed
                risk = self.validator.assess_risk(command)
                if risk != CommandRisk.SAFE and self.policy.require_confirmation:
                    console.print(f"\n[yellow]Command risk level: {risk.value}[/yellow]")
                    console.print(f"Command: [cyan]{command}[/cyan]")
                    
                    if not Confirm.ask("Execute this command?"):
                        return {
                            'success': False,
                            'error': 'Command cancelled by user',
                            'command': command
                        }
            
            # Prepare execution
            cwd = working_dir or self.current_directory
            
            # Log command if policy requires
            if self.policy.log_commands:
                console.print(f"[dim]Executing: {command} (in {cwd})[/dim]")
            
            # Execute command
            start_time = datetime.now()
            
            if self.policy.allow_shell and not safe_mode:
                # Shell mode (less secure)
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd
                )
            else:
                # No shell mode (more secure)
                args = shlex.split(command)
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd
                )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.policy.max_execution_time
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    'success': False,
                    'error': f'Command timed out after {timeout} seconds',
                    'command': command
                }
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Check output size
            if len(stdout) > self.policy.max_output_size:
                stdout = stdout[:self.policy.max_output_size]
                stdout += b"\n... (output truncated)"
            
            result = {
                'success': process.returncode == 0,
                'command': command,
                'return_code': process.returncode,
                'stdout': stdout.decode('utf-8', errors='replace'),
                'stderr': stderr.decode('utf-8', errors='replace'),
                'execution_time': execution_time,
                'working_directory': str(cwd)
            }
            
            # Add to history
            self.history.add_command(command, result)
            
            return result
            
        finally:
            # Restore original timeout
            self.policy.max_execution_time = original_timeout
    
    async def interactive_shell(self, safe_mode: bool = True):
        """Start an interactive shell session"""
        
        console.print(Panel.fit(
            "[bold cyan]LocalAgent Interactive Shell[/bold cyan]\n"
            f"[dim]Safety mode: {'ON' if safe_mode else 'OFF'} | "
            f"Type 'exit' to quit | 'help' for commands[/dim]",
            border_style="cyan"
        ))
        
        while True:
            try:
                # Show current directory in prompt
                prompt_text = f"[cyan]{self.current_directory}[/cyan] [bold blue]$[/bold blue] "
                command = Prompt.ask(prompt_text)
                
                # Handle special commands
                if command.lower() in ['exit', 'quit']:
                    break
                elif command.lower() == 'help':
                    self.show_help()
                    continue
                elif command.startswith('cd '):
                    self.change_directory(command[3:].strip())
                    continue
                elif command == 'pwd':
                    console.print(str(self.current_directory))
                    continue
                elif command == 'clear':
                    console.clear()
                    continue
                
                # Execute command
                result = await self.execute_command(
                    command,
                    safe_mode=safe_mode,
                    working_dir=self.current_directory
                )
                
                self.display_result(result)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    def display_result(self, result: Dict[str, Any]):
        """Display command execution result"""
        
        if result['success']:
            if result['stdout']:
                console.print(result['stdout'], end='')
            if result['stderr']:
                console.print(f"[yellow]{result['stderr']}[/yellow]", end='')
        else:
            console.print(f"[red]Command failed: {result.get('error', 'Unknown error')}[/red]")
            if result.get('stderr'):
                console.print(f"[red]{result['stderr']}[/red]", end='')
        
        if self.policy.log_commands:
            console.print(
                f"[dim]Exit code: {result.get('return_code', 'N/A')} | "
                f"Time: {result.get('execution_time', 0):.2f}s[/dim]"
            )
    
    def change_directory(self, path: str):
        """Change current directory"""
        try:
            new_path = Path(path).expanduser()
            if not new_path.is_absolute():
                new_path = self.current_directory / new_path
            
            new_path = new_path.resolve()
            
            if new_path.exists() and new_path.is_dir():
                self.current_directory = new_path
                console.print(f"[green]Changed directory to: {new_path}[/green]")
            else:
                console.print(f"[red]Directory not found: {path}[/red]")
        except Exception as e:
            console.print(f"[red]Error changing directory: {e}[/red]")
    
    def show_help(self):
        """Show interactive shell help"""
        
        help_table = Table(title="Interactive Shell Commands", show_header=True)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")
        
        commands = [
            ("exit/quit", "Exit interactive shell"),
            ("help", "Show this help message"),
            ("cd <path>", "Change directory"),
            ("pwd", "Show current directory"),
            ("clear", "Clear screen"),
            ("history", "Show recent commands"),
            ("Any shell command", "Execute in current directory")
        ]
        
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
        
        console.print(help_table)
    
    def show_command_history(self, count: int = 10, search: Optional[str] = None):
        """Display command history"""
        
        history = self.history.get_recent(count * 2)  # Get extra for filtering
        
        if search:
            history = [h for h in history if search in h['command']]
        
        history = history[-count:]  # Limit after filtering
        
        if not history:
            console.print("[yellow]No matching commands in history[/yellow]")
            return
        
        table = Table(title="Command History", show_header=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Command", style="cyan")
        table.add_column("Status", style="white", width=8)
        
        for idx, entry in enumerate(history, 1):
            timestamp = datetime.fromisoformat(entry['timestamp'])
            time_str = timestamp.strftime("%H:%M:%S")
            
            status = "✓" if entry['result'].get('success', False) else "✗"
            status_style = "green" if entry['result'].get('success', False) else "red"
            
            table.add_row(
                str(idx),
                time_str,
                entry['command'],
                f"[{status_style}]{status}[/{status_style}]"
            )
        
        console.print(table)
    
    def show_security_policy(self):
        """Display current security policy settings"""
        
        table = Table(title="Shell Security Policy", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Description", style="dim")
        
        policies = [
            ("Allow Shell", self.policy.allow_shell, "Use shell for command execution"),
            ("Allow Pipes", self.policy.allow_pipes, "Allow pipe operators"),
            ("Allow Redirects", self.policy.allow_redirects, "Allow input/output redirection"),
            ("Allow Sudo", self.policy.allow_sudo, "Allow sudo commands"),
            ("Max Execution Time", f"{self.policy.max_execution_time}s", "Command timeout"),
            ("Max Output Size", f"{self.policy.max_output_size / 1024:.0f}KB", "Maximum output capture"),
            ("Require Confirmation", self.policy.require_confirmation, "Confirm risky commands"),
            ("Log Commands", self.policy.log_commands, "Log command execution"),
            ("Sandbox Mode", self.policy.sandbox_mode, "Extra restrictions enabled")
        ]
        
        for name, value, desc in policies:
            if isinstance(value, bool):
                value_str = "[green]Yes[/green]" if value else "[red]No[/red]"
            else:
                value_str = str(value)
            
            table.add_row(name, value_str, desc)
        
        console.print(table)
        
        # Show risk categories
        console.print("\n[bold cyan]Command Risk Categories:[/bold cyan]")
        console.print("[green]Safe:[/green] ls, pwd, echo, date, cat, grep, git, etc.")
        console.print("[yellow]Moderate:[/yellow] cp, mv, mkdir, docker, apt, etc.")
        console.print("[red]Dangerous:[/red] rm, rmdir, dd, shutdown, reboot, etc.")
        console.print("[bold red]Forbidden:[/bold red] Commands with dangerous patterns")


# Export plugin class
__plugin__ = ShellCommandPlugin