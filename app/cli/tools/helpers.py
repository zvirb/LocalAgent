"""
CLI Helper Functions
Common utilities for CLI operations
"""

import os
import sys
import json
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from rich.console import Console

class CLIHelpers:
    """Collection of CLI helper functions"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    @staticmethod
    def get_project_root() -> Path:
        """Get the project root directory"""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / "setup.py").exists() or (parent / "pyproject.toml").exists():
                return parent
        return current
    
    @staticmethod
    def load_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load JSON file safely"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"error": str(e)}
    
    @staticmethod
    def load_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load YAML file safely"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            return {"error": str(e)}
    
    @staticmethod
    def save_json_file(data: Dict[str, Any], file_path: Union[str, Path]) -> bool:
        """Save data to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception:
            return False
    
    @staticmethod
    def save_yaml_file(data: Dict[str, Any], file_path: Union[str, Path]) -> bool:
        """Save data to YAML file"""
        try:
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
            return True
        except Exception:
            return False
    
    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Confirm action with user"""
        from rich.prompt import Confirm
        return Confirm.ask(message, default=default, console=self.console)
    
    def select_from_list(self, options: List[str], title: str = "Select option") -> Optional[str]:
        """Select item from list"""
        if not options:
            return None
        
        self.console.print(f"\n[bold cyan]{title}:[/bold cyan]")
        for i, option in enumerate(options, 1):
            self.console.print(f"  {i}. {option}")
        
        from rich.prompt import IntPrompt
        try:
            selection = IntPrompt.ask(
                "Choice",
                default=1,
                console=self.console,
                choices=[str(i) for i in range(1, len(options) + 1)]
            )
            return options[selection - 1]
        except (KeyboardInterrupt, ValueError):
            return None
    
    def get_input_with_validation(self, prompt: str, validator=None, default=None) -> Optional[str]:
        """Get user input with optional validation"""
        from rich.prompt import Prompt
        
        while True:
            try:
                value = Prompt.ask(prompt, default=default, console=self.console)
                if validator and not validator(value):
                    self.console.print("[red]Invalid input. Please try again.[/red]")
                    continue
                return value
            except KeyboardInterrupt:
                return None
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get basic system information"""
        import platform
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "cwd": str(Path.cwd())
        }