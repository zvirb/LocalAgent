"""
Output Formatters and Report Generators
Rich-based output formatting for CLI tools
"""

import json
import yaml
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
from rich.syntax import Syntax

console = Console()

class OutputFormatter:
    """Format output in various styles"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def format_json(self, data: Dict[str, Any], title: str = "JSON Output") -> None:
        """Format and display JSON data"""
        json_obj = JSON.from_data(data)
        panel = Panel(json_obj, title=title, border_style="blue")
        self.console.print(panel)
    
    def format_table(self, data: List[Dict[str, Any]], title: str = "Table") -> None:
        """Format data as a table"""
        if not data:
            self.console.print(f"[yellow]No data for {title}[/yellow]")
            return
        
        # Get headers from first item
        headers = list(data[0].keys())
        table = Table(title=title)
        
        for header in headers:
            table.add_column(header, style="cyan")
        
        for row in data:
            table.add_row(*[str(row.get(h, "")) for h in headers])
        
        self.console.print(table)
    
    def format_yaml(self, data: Dict[str, Any], title: str = "YAML Output") -> None:
        """Format and display YAML data"""
        yaml_str = yaml.dump(data, default_flow_style=False, indent=2)
        syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)
        panel = Panel(syntax, title=title, border_style="green")
        self.console.print(panel)

class ReportGenerator:
    """Generate comprehensive reports"""
    
    def __init__(self, formatter: OutputFormatter = None):
        self.formatter = formatter or OutputFormatter()
    
    def generate_summary_report(self, data: Dict[str, Any]) -> None:
        """Generate a summary report"""
        self.formatter.console.print("[bold blue]📊 Summary Report[/bold blue]\n")
        
        # Basic info
        if "info" in data:
            self.formatter.format_json(data["info"], "Basic Information")
        
        # Statistics
        if "stats" in data:
            self.formatter.format_table([data["stats"]], "Statistics")
        
        # Results
        if "results" in data:
            self.formatter.format_yaml(data["results"], "Results")
    
    def save_report(self, data: Dict[str, Any], file_path: Path, format: str = "json") -> None:
        """Save report to file"""
        if format.lower() == "json":
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        elif format.lower() in ["yaml", "yml"]:
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
        else:
            with open(file_path, 'w') as f:
                f.write(str(data))
        
        self.formatter.console.print(f"[green]✅ Report saved to {file_path}[/green]")