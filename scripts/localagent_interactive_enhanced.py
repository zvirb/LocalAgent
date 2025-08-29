#!/usr/bin/env python3
"""
LocalAgent Enhanced Interactive CLI - With full workflow and context awareness
"""

import click
import requests
import json
import asyncio
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console()

class EnhancedInteractiveCLI:
    """Enhanced interactive CLI with full workflow and context awareness"""
    
    def __init__(self):
        self.console = console
        self.ollama_url = None
        self.current_model = None
        self.config = None
        self.workflow_engine = None
        self.agent_adapter = None
        self.context_manager = None
        self.orchestrator = None
        self.search_manager = None
        self.file_ops_manager = None
        self.initialized = False
        self.current_directory = Path.cwd()
        self.project_context = None
        self.mcp_integration = None
        self.memory_mcp = None
        self.redis_mcp = None
        self.hrm_server = None  # HRM MCP server
        self.task_mcp = None  # Task Management MCP
        self.coord_mcp = None  # Coordination MCP
        self.workflow_state_mcp = None  # Workflow State MCP
        self.pattern_selector = None  # Intelligent pattern selector
        self.pattern_registry = None  # Pattern registry
        self.github_mcp = None  # GitHub MCP server
        
    def get_ollama_url(self):
        """Try to find a working Ollama instance"""
        urls = [
            "http://alienware.local:11434",
            "http://localhost:11434", 
            "http://ollama:11434"
        ]
        
        for url in urls:
            try:
                response = requests.get(f"{url}/api/tags", timeout=2)
                if response.status_code == 200:
                    self.console.print(f"[green]✓ Connected to Ollama at {url}[/green]")
                    return url
            except:
                continue
        return None
        
    def get_available_models(self):
        """Get list of available models from Ollama"""
        if not self.ollama_url:
            return []
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m['name'] for m in models]
        except:
            pass
        return []
        
    def analyze_project_context(self):
        """Analyze current directory for project context"""
        context = {
            "current_directory": str(self.current_directory),
            "project_name": self.current_directory.name,
            "files": [],
            "project_type": "unknown",
            "key_files": {}
        }
        
        # Check for key files
        key_files_to_check = [
            ("README.md", "readme"),
            ("docker-compose.yml", "docker_config"),
            ("package.json", "node_config"),
            ("requirements.txt", "python_requirements"),
            ("setup.py", "python_setup"),
            ("CLAUDE.md", "claude_instructions"),
            (".gitignore", "gitignore"),
            ("pyproject.toml", "python_project")
        ]
        
        for filename, key in key_files_to_check:
            filepath = self.current_directory / filename
            if filepath.exists():
                context["key_files"][key] = str(filepath)
                # Detect project type
                if key == "python_requirements" or key == "python_setup":
                    context["project_type"] = "python"
                elif key == "node_config":
                    context["project_type"] = "node"
                    
        # Get list of directories and files (top level only)
        try:
            for item in self.current_directory.iterdir():
                if not item.name.startswith('.'):
                    context["files"].append({
                        "name": item.name,
                        "type": "dir" if item.is_dir() else "file"
                    })
        except:
            pass
            
        # Read README if exists
        readme_path = self.current_directory / "README.md"
        if readme_path.exists():
            try:
                with open(readme_path, 'r') as f:
                    lines = f.readlines()[:10]  # First 10 lines
                    context["readme_preview"] = "".join(lines)
            except:
                pass
                
        # Read CLAUDE.md if exists for instructions
        claude_path = self.current_directory / "CLAUDE.md"
        if claude_path.exists():
            try:
                with open(claude_path, 'r') as f:
                    lines = f.readlines()[:50]  # First 50 lines for workflow info
                    context["claude_instructions"] = "".join(lines)
            except:
                pass
                
        self.project_context = context
        return context
        
    async def lazy_initialize(self):
        """Lazy initialization of heavy components"""
        try:
            # Only import what we need when we need it
            from app.cli.core.config import ConfigurationManager
            from app.llm_providers.provider_manager import ProviderManager
            
            # Initialize configuration
            self.console.print("[dim]Loading configuration...[/dim]")
            config_manager = ConfigurationManager()
            self.config = await config_manager.load_configuration()
            
            # Initialize provider manager
            provider_manager = ProviderManager(self.config.providers if hasattr(self.config, 'providers') else {})
            await provider_manager.initialize_providers()
            
            # Try to initialize orchestration components
            try:
                from app.orchestration.orchestration_integration import LocalAgentOrchestrator
                from app.orchestration.workflow_engine import WorkflowEngine
                from app.orchestration.agent_adapter import AgentProviderAdapter
                from app.orchestration.context_manager import ContextManager
                
                # Initialize orchestrator
                self.orchestrator = LocalAgentOrchestrator()
                await self.orchestrator.initialize(provider_manager)
                
                # Get components from orchestrator
                self.workflow_engine = self.orchestrator.workflow_engine
                self.agent_adapter = self.orchestrator.agent_adapter
                self.context_manager = self.orchestrator.context_manager
                
                self.console.print("[green]✓ Full workflow engine initialized[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Workflow engine error: {e}[/yellow]")
                # Fallback to basic initialization
                try:
                    from app.orchestration.workflow_engine import WorkflowEngine
                    from app.orchestration.context_manager import ContextManager
                    from app.orchestration.agent_adapter import AgentProviderAdapter
                    
                    self.workflow_engine = WorkflowEngine()
                    self.agent_adapter = AgentProviderAdapter()
                    config_dict = self.config.model_dump() if hasattr(self.config, 'model_dump') else self.config.dict()
                    self.context_manager = ContextManager(config_dict)
                    self.console.print("[yellow]✓ Basic workflow engine initialized[/yellow]")
                except Exception as e2:
                    self.console.print(f"[red]Workflow not available: {e2}[/red]")
                
            # Try to initialize MCP features
            try:
                from app.orchestration.mcp_integration import OrchestrationMCP
                
                self.mcp_integration = OrchestrationMCP()
                await self.mcp_integration.initialize()
                self.memory_mcp = self.mcp_integration.memory_mcp
                self.redis_mcp = self.mcp_integration.redis_mcp
                
                if self.redis_mcp and self.redis_mcp.redis:
                    self.console.print("[green]✓ Redis MCP connected for coordination[/green]")
                if self.memory_mcp:
                    self.console.print("[green]✓ Memory MCP initialized for persistence[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ MCP features limited: {e}[/yellow]")
                
            # Try to initialize HRM MCP
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from mcp.hrm_mcp import create_hrm_server
                
                self.hrm_server = await create_hrm_server({'state_file': '.hrm_state.json'})
                self.console.print("[green]✓ HRM MCP initialized for hierarchical reasoning[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ HRM MCP not available: {e}[/yellow]")
                
            # Try to initialize Task MCP
            try:
                from mcp.task_mcp import create_task_server
                
                self.task_mcp = await create_task_server({'state_file': '.task_state.json'})
                self.console.print("[green]✓ Task MCP initialized for task management[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Task MCP not available: {e}[/yellow]")
                
            # Try to initialize Coordination MCP
            try:
                from mcp.coordination_mcp import create_coordination_server
                
                self.coord_mcp = await create_coordination_server({'state_file': '.coordination_state.json'})
                self.console.print("[green]✓ Coordination MCP initialized for agent coordination[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Coordination MCP not available: {e}[/yellow]")
                
            # Try to initialize Workflow State MCP
            try:
                from mcp.workflow_state_mcp import create_workflow_state_server
                
                self.workflow_state_mcp = await create_workflow_state_server({'state_file': '.workflow_state.json'})
                self.console.print("[green]✓ Workflow State MCP initialized for workflow tracking[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Workflow State MCP not available: {e}[/yellow]")
                
            # Try to initialize Pattern System
            try:
                from mcp.patterns import pattern_registry, intelligent_selector
                
                self.pattern_registry = pattern_registry
                self.pattern_selector = intelligent_selector
                self.console.print(f"[green]✓ Pattern System initialized with {len(pattern_registry.patterns)} patterns[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Pattern System not available: {e}[/yellow]")
                
            # Try to initialize GitHub MCP
            try:
                from mcp.github_mcp import create_github_server
                
                self.github_mcp = await create_github_server({'cli_path': 'gh'})
                if self.github_mcp:
                    auth_status = await self.github_mcp.check_auth()
                    if auth_status.get('authenticated', False):
                        self.console.print(f"[green]✓ GitHub MCP initialized - authenticated as {auth_status.get('username', 'unknown')}[/green]")
                    else:
                        self.console.print(f"[yellow]✓ GitHub MCP initialized - not authenticated (use 'gh auth login')[/yellow]")
                else:
                    self.console.print(f"[yellow]⚠ GitHub MCP not available: gh CLI not found[/yellow]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ GitHub MCP not available: {e}[/yellow]")
                
            # Try to initialize tools (optional)
            try:
                from app.cli.tools.search import SearchManager
                from app.cli.tools.file_ops import FileOperationsManager
                
                self.search_manager = SearchManager(self.console)
                self.file_ops_manager = FileOperationsManager(self.console)
                self.console.print("[green]✓ Tools initialized[/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠ Tools not available: {e}[/yellow]")
                
            self.initialized = True
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error during initialization: {e}[/red]")
            import traceback
            if "--debug" in sys.argv:
                traceback.print_exc()
            return False
            
    async def process_with_workflow(self, prompt: str):
        """Process prompt through actual workflow engine"""
        if not self.workflow_engine:
            return "Workflow engine not available. Type 'init' first."
            
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                
                # Load workflow configuration if not loaded
                if not hasattr(self.workflow_engine, 'workflow_config') or not self.workflow_engine.workflow_config:
                    workflow_path = Path(__file__).parent.parent / "workflows" / "12-phase-workflow.yaml"
                    if workflow_path.exists():
                        task = progress.add_task("Loading workflow configuration...", total=1)
                        await self.workflow_engine.load_workflow(str(workflow_path))
                        progress.update(task, completed=1)
                    else:
                        return "Workflow configuration not found"
                        
                # Execute workflow with context
                task = progress.add_task("Executing 12-phase workflow...", total=12)
                
                # Add project context to prompt
                enhanced_prompt = f"""
Task: {prompt}

Project Context:
- Current Directory: {self.current_directory}
- Project Type: {self.project_context.get('project_type', 'unknown')}
- Key Files: {', '.join(self.project_context.get('key_files', {}).keys())}

Please execute this task following the 12-phase workflow.
"""
                
                # Create workflow execution
                execution = await self.workflow_engine.execute_workflow(
                    task_description=enhanced_prompt,
                    provider_config={
                        "type": "ollama",
                        "base_url": self.ollama_url,
                        "model": self.current_model
                    }
                )
                
                progress.update(task, completed=12)
                
                # Format results
                if execution and hasattr(execution, 'phase_results'):
                    results = []
                    for phase_result in execution.phase_results:
                        results.append(f"✓ {phase_result.phase_id}: {phase_result.status.value}")
                    return "\n".join(results)
                else:
                    return f"Workflow completed with status: {execution.status if execution else 'unknown'}"
                    
        except Exception as e:
            return f"Workflow error: {str(e)}"
            
    async def process_with_tools(self, prompt: str):
        """Process prompt to detect and execute tool commands"""
        prompt_lower = prompt.lower()
        
        # Search commands
        if any(cmd in prompt_lower for cmd in ['search', 'find', 'grep', 'locate']):
            if self.search_manager:
                self.console.print("[cyan]Starting search interface...[/cyan]")
                try:
                    await self.search_manager.interactive_search()
                    return "Search completed"
                except Exception as e:
                    return f"Search error: {str(e)}"
            else:
                return "Search tools not available"
                
        # File operations
        if any(cmd in prompt_lower for cmd in ['create file', 'edit file', 'delete file']):
            if self.file_ops_manager:
                self.console.print("[cyan]Starting file operations...[/cyan]")
                try:
                    await self.file_ops_manager.interactive_operations()
                    return "File operation completed"
                except Exception as e:
                    return f"File operation error: {str(e)}"
            else:
                return "File tools not available"
                
        return None
        
    async def web_search(self, query: str):
        """Perform web search using requests (simpler than MCP web search)"""
        try:
            # Use DuckDuckGo HTML version for simple search
            import requests
            from bs4 import BeautifulSoup
            
            url = f"https://html.duckduckgo.com/html/?q={query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                for result in soup.find_all('div', class_='result')[:5]:  # Top 5 results
                    title_elem = result.find('a', class_='result__a')
                    snippet_elem = result.find('a', class_='result__snippet')
                    
                    if title_elem:
                        results.append({
                            'title': title_elem.get_text(strip=True),
                            'url': title_elem.get('href', ''),
                            'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ''
                        })
                        
                return results
            else:
                return []
        except Exception as e:
            self.console.print(f"[red]Web search error: {e}[/red]")
            return []
            
    async def memory_store(self, key: str, value: str):
        """Store data in memory MCP"""
        if self.memory_mcp:
            try:
                await self.memory_mcp.store_entity(
                    entity_type="user-data",
                    entity_id=key,
                    content=value,
                    metadata={"timestamp": str(datetime.now())}
                )
                return f"Stored '{key}' in memory"
            except Exception as e:
                return f"Memory error: {e}"
        return "Memory MCP not available"
        
    async def memory_recall(self, key: str):
        """Recall data from memory MCP"""
        if self.memory_mcp:
            try:
                entity = await self.memory_mcp.retrieve_entity(key)
                if entity:
                    return entity.content
                else:
                    return f"No memory found for '{key}'"
            except Exception as e:
                return f"Memory error: {e}"
        return "Memory MCP not available"
        
    async def hrm_reason(self, query: str, level: int = 0):
        """Use HRM MCP for hierarchical reasoning"""
        if self.hrm_server:
            try:
                # Get project context for reasoning
                context = {
                    "project_type": self.project_context.get('project_type', 'unknown'),
                    "current_directory": str(self.current_directory),
                    "key_files": list(self.project_context.get('key_files', {}).keys())
                }
                
                # Perform reasoning
                result = await self.hrm_server.reason(query, context, level)
                
                # Get explanation
                explanation = await self.hrm_server.explain_reasoning(result.node_id)
                
                return explanation
            except Exception as e:
                return f"HRM reasoning error: {e}"
        return "HRM MCP not available"
        
    def chat_with_model(self, prompt: str):
        """Send a chat request to Ollama with context"""
        # Add project context to prompt
        context_prompt = f"""
You are helping with a project in {self.current_directory}.
Project type: {self.project_context.get('project_type', 'unknown')}
Key files present: {', '.join(self.project_context.get('key_files', {}).keys())}

{self.project_context.get('readme_preview', '')}

User question: {prompt}
"""
        
        try:
            response = requests.post(f"{self.ollama_url}/api/generate", 
                json={
                    "model": self.current_model,
                    "prompt": context_prompt,
                    "stream": False
                },
                timeout=180  # Increased timeout for complex prompts
            )
            
            if response.status_code == 200:
                return response.json().get('response', 'No response')
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
            
    def show_context(self):
        """Show current project context"""
        tree = Tree(f"[bold cyan]📁 {self.current_directory.name}[/bold cyan]")
        
        # Add key files
        if self.project_context.get('key_files'):
            files_branch = tree.add("[green]Key Files[/green]")
            for key, path in self.project_context['key_files'].items():
                files_branch.add(f"📄 {Path(path).name}")
                
        # Add directories
        dirs = [f for f in self.project_context.get('files', []) if f['type'] == 'dir']
        if dirs:
            dirs_branch = tree.add("[yellow]Directories[/yellow]")
            for d in dirs[:10]:  # Show first 10
                dirs_branch.add(f"📁 {d['name']}")
                
        self.console.print(tree)
        self.console.print(f"\n[cyan]Project Type:[/cyan] {self.project_context.get('project_type', 'unknown')}")
        
    def show_help(self):
        """Show available commands and features"""
        help_table = Table(title="Available Commands & Features", show_header=True)
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")
        help_table.add_column("Status", style="green")
        
        commands = [
            ("search [query]", "Search files and content", "✓" if self.search_manager else "✗"),
            ("find [pattern]", "Find files by pattern", "✓" if self.search_manager else "✗"),
            ("web [query]", "Search the web", "✓"),
            ("remember [key] [value]", "Store in memory", "✓" if self.memory_mcp else "✗"),
            ("recall [key]", "Recall from memory", "✓" if self.memory_mcp else "✗"),
            ("reason [query]", "Hierarchical reasoning", "✓" if self.hrm_server else "✗"),
            ("strategic [query]", "Strategic reasoning", "✓" if self.hrm_server else "✗"),
            ("tactical [query]", "Tactical reasoning", "✓" if self.hrm_server else "✗"),
            ("task create [title]", "Create a task", "✓" if self.task_mcp else "✗"),
            ("task list", "List all tasks", "✓" if self.task_mcp else "✗"),
            ("task complete [id]", "Complete a task", "✓" if self.task_mcp else "✗"),
            ("coord status", "Coordination status", "✓" if self.coord_mcp else "✗"),
            ("workflow status", "Workflow status", "✓" if self.workflow_state_mcp else "✗"),
            ("pattern list", "List available patterns", "✓" if self.pattern_registry else "✗"),
            ("pattern recommend [task]", "Get pattern recommendation", "✓" if self.pattern_selector else "✗"),
            ("pattern execute [id]", "Execute a pattern", "✓" if self.pattern_registry else "✗"),
            ("gh repo list", "List GitHub repositories", "✓" if hasattr(self, 'github_mcp') and self.github_mcp else "✗"),
            ("gh repo create [name]", "Create GitHub repository", "✓" if hasattr(self, 'github_mcp') and self.github_mcp else "✗"),
            ("gh issue list", "List GitHub issues", "✓" if hasattr(self, 'github_mcp') and self.github_mcp else "✗"),
            ("gh issue create [title]", "Create GitHub issue", "✓" if hasattr(self, 'github_mcp') and self.github_mcp else "✗"),
            ("gh pr list", "List GitHub pull requests", "✓" if hasattr(self, 'github_mcp') and self.github_mcp else "✗"),
            ("gh pr create", "Create GitHub pull request", "✓" if hasattr(self, 'github_mcp') and self.github_mcp else "✗"),
            ("gh auth status", "Check GitHub authentication", "✓" if hasattr(self, 'github_mcp') and self.github_mcp else "✗"),
            ("create file", "Create new file", "✓" if self.file_ops_manager else "✗"),
            ("edit file", "Edit existing file", "✓" if self.file_ops_manager else "✗"),
            ("workflow [task]", "Execute 12-phase workflow", "✓" if self.workflow_engine else "✗"),
            ("context", "Show project context", "✓"),
            ("init", "Initialize advanced features", "✓" if self.initialized else "✗"),
            ("model", "Switch AI model", "✓"),
            ("config", "Show configuration", "✓" if self.config else "✗"),
            ("clear", "Clear screen", "✓"),
            ("help", "Show this help", "✓"),
            ("exit/quit/bye", "Exit the CLI", "✓")
        ]
        
        for cmd, desc, status in commands:
            help_table.add_row(cmd, desc, status)
            
        self.console.print(help_table)
        
    async def run(self):
        """Main interactive loop"""
        # Welcome message
        self.console.print(Panel.fit(
            "[bold cyan]🤖 LocalAgent Enhanced Interactive CLI[/bold cyan]\n"
            "[dim]Full workflow engine with context awareness[/dim]",
            border_style="cyan"
        ))
        
        # Analyze project context
        self.console.print("[cyan]Analyzing project context...[/cyan]")
        self.analyze_project_context()
        self.console.print(f"[green]✓ Working in: {self.current_directory}[/green]")
        self.console.print(f"[green]✓ Project type: {self.project_context.get('project_type', 'unknown')}[/green]")
        
        # Find Ollama
        self.ollama_url = self.get_ollama_url()
        if not self.ollama_url:
            self.console.print("[red]❌ Could not connect to Ollama[/red]")
            self.console.print("[yellow]Make sure Ollama is running:[/yellow]")
            self.console.print("[yellow]docker-compose up -d[/yellow]")
            sys.exit(1)
            
        # Get available models
        models = self.get_available_models()
        
        if not models:
            self.console.print("[red]❌ No models installed. Please run:[/red]")
            self.console.print("[yellow]docker exec localagent-ollama ollama pull tinyllama:latest[/yellow]")
            sys.exit(1)
            
        # Select model
        if len(models) == 1:
            self.current_model = models[0]
            self.console.print(f"[green]Using model: {self.current_model}[/green]\n")
        else:
            self.console.print("[cyan]Available models:[/cyan]")
            for i, m in enumerate(models, 1):
                self.console.print(f"  {i}. {m}")
                
            choice = Prompt.ask(
                "Select a model",
                choices=[str(i) for i in range(1, len(models)+1)],
                default="1"
            )
            self.current_model = models[int(choice)-1]
            self.console.print(f"[green]Selected: {self.current_model}[/green]\n")
            
        # Instructions
        self.console.print("[dim]Type 'help' to see available commands[/dim]")
        self.console.print("[dim]Type 'init' to initialize advanced features[/dim]")
        self.console.print("[dim]Type 'context' to see project context[/dim]")
        self.console.print("[dim]Type 'exit', 'quit', or 'bye' to end the session[/dim]\n")
        
        # Chat loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("[bold blue]You[/bold blue]")
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    self.console.print("\n[cyan]👋 Goodbye![/cyan]")
                    break
                    
                if user_input.lower() == 'clear':
                    self.console.clear()
                    continue
                    
                if user_input.lower() == 'help':
                    self.show_help()
                    continue
                    
                if user_input.lower() == 'context':
                    self.show_context()
                    continue
                    
                if user_input.lower() == 'init':
                    self.console.print("[cyan]Initializing advanced features...[/cyan]")
                    success = await self.lazy_initialize()
                    if success:
                        self.console.print("[green]✓ Advanced features ready![/green]")
                    else:
                        self.console.print("[yellow]Some features may not be available[/yellow]")
                    continue
                    
                if user_input.lower() == 'config':
                    if self.config:
                        self.console.print(Panel(
                            json.dumps(self.config.model_dump() if hasattr(self.config, 'model_dump') else {}, indent=2),
                            title="Current Configuration",
                            border_style="green"
                        ))
                    else:
                        self.console.print("[yellow]Configuration not loaded. Type 'init' first.[/yellow]")
                    continue
                    
                if user_input.lower() == 'model':
                    self.console.print("[cyan]Available models:[/cyan]")
                    for i, m in enumerate(models, 1):
                        self.console.print(f"  {i}. {m}")
                    choice = Prompt.ask("Select a model", default="1")
                    self.current_model = models[int(choice)-1] if choice.isdigit() else models[0]
                    self.console.print(f"[green]Switched to: {self.current_model}[/green]\n")
                    continue
                    
                # Web search command
                if user_input.lower().startswith('web '):
                    query = user_input[4:].strip()
                    if query:
                        self.console.print(f"[cyan]Searching web for: {query}[/cyan]")
                        results = await self.web_search(query)
                        if results:
                            for i, result in enumerate(results, 1):
                                self.console.print(Panel(
                                    f"[bold]{result['title']}[/bold]\n"
                                    f"[dim]{result['url']}[/dim]\n\n"
                                    f"{result['snippet']}",
                                    title=f"Result {i}",
                                    border_style="blue"
                                ))
                        else:
                            self.console.print("[yellow]No results found[/yellow]")
                    continue
                    
                # Memory commands
                if user_input.lower().startswith('remember '):
                    parts = user_input[9:].split(' ', 1)
                    if len(parts) == 2:
                        key, value = parts
                        result = await self.memory_store(key, value)
                        self.console.print(f"[green]{result}[/green]")
                    else:
                        self.console.print("[yellow]Usage: remember <key> <value>[/yellow]")
                    continue
                    
                if user_input.lower().startswith('recall '):
                    key = user_input[7:].strip()
                    if key:
                        result = await self.memory_recall(key)
                        self.console.print(Panel(
                            result,
                            title=f"Memory: {key}",
                            border_style="green"
                        ))
                    else:
                        self.console.print("[yellow]Usage: recall <key>[/yellow]")
                    continue
                    
                # HRM reasoning commands
                if user_input.lower().startswith('reason '):
                    query = user_input[7:].strip()
                    if query:
                        self.console.print(f"[cyan]Performing hierarchical reasoning...[/cyan]")
                        result = await self.hrm_reason(query, level=0)
                        self.console.print(Panel(
                            Markdown(result),
                            title="HRM Reasoning Result",
                            border_style="magenta"
                        ))
                    else:
                        self.console.print("[yellow]Usage: reason <query>[/yellow]")
                    continue
                    
                if user_input.lower().startswith('strategic '):
                    query = user_input[10:].strip()
                    if query:
                        self.console.print(f"[cyan]Strategic reasoning...[/cyan]")
                        result = await self.hrm_reason(query, level=0)
                        self.console.print(Panel(
                            Markdown(result),
                            title="Strategic Analysis",
                            border_style="magenta"
                        ))
                    else:
                        self.console.print("[yellow]Usage: strategic <query>[/yellow]")
                    continue
                    
                if user_input.lower().startswith('tactical '):
                    query = user_input[9:].strip()
                    if query:
                        self.console.print(f"[cyan]Tactical reasoning...[/cyan]")
                        result = await self.hrm_reason(query, level=1)
                        self.console.print(Panel(
                            Markdown(result),
                            title="Tactical Analysis",
                            border_style="magenta"
                        ))
                    else:
                        self.console.print("[yellow]Usage: tactical <query>[/yellow]")
                    continue
                    
                # Task management commands
                if user_input.lower().startswith('task create '):
                    title = user_input[12:].strip()
                    if title and self.task_mcp:
                        task = await self.task_mcp.create_task(title)
                        self.console.print(Panel(
                            f"Created task: {task.task_id}\n"
                            f"Title: {task.title}\n"
                            f"Status: {task.status}\n"
                            f"Priority: {task.priority}",
                            title="Task Created",
                            border_style="green"
                        ))
                    elif not self.task_mcp:
                        self.console.print("[yellow]Task MCP not available. Type 'init' first.[/yellow]")
                    else:
                        self.console.print("[yellow]Usage: task create <title>[/yellow]")
                    continue
                    
                if user_input.lower() == 'task list':
                    if self.task_mcp:
                        tasks = await self.task_mcp.list_tasks(include_completed=False)
                        if tasks:
                            table = Table(title="Active Tasks", show_header=True)
                            table.add_column("ID", style="cyan")
                            table.add_column("Title", style="white")
                            table.add_column("Status", style="yellow")
                            table.add_column("Priority", style="green")
                            
                            for task in tasks[:10]:  # Show first 10
                                table.add_row(
                                    task.task_id,
                                    task.title[:50],
                                    task.status,
                                    task.priority
                                )
                            self.console.print(table)
                        else:
                            self.console.print("[dim]No active tasks[/dim]")
                    else:
                        self.console.print("[yellow]Task MCP not available. Type 'init' first.[/yellow]")
                    continue
                    
                if user_input.lower().startswith('task complete '):
                    task_id = user_input[14:].strip()
                    if task_id and self.task_mcp:
                        updated = await self.task_mcp.update_task(task_id, status="completed")
                        if updated:
                            self.console.print(f"[green]✓ Task {task_id} marked as completed[/green]")
                        else:
                            self.console.print(f"[red]Task {task_id} not found[/red]")
                    elif not self.task_mcp:
                        self.console.print("[yellow]Task MCP not available. Type 'init' first.[/yellow]")
                    else:
                        self.console.print("[yellow]Usage: task complete <task_id>[/yellow]")
                    continue
                    
                # Coordination status command
                if user_input.lower() == 'coord status':
                    if self.coord_mcp:
                        stats = await self.coord_mcp.get_coordination_stats()
                        self.console.print(Panel(
                            json.dumps(stats, indent=2),
                            title="Coordination Status",
                            border_style="blue"
                        ))
                    else:
                        self.console.print("[yellow]Coordination MCP not available. Type 'init' first.[/yellow]")
                    continue
                    
                # Workflow status command
                if user_input.lower() == 'workflow status':
                    if self.workflow_state_mcp and self.workflow_state_mcp.active_execution:
                        progress = await self.workflow_state_mcp.get_execution_progress(
                            self.workflow_state_mcp.active_execution
                        )
                        self.console.print(Panel(
                            json.dumps(progress, indent=2),
                            title="Workflow Progress",
                            border_style="magenta"
                        ))
                    elif self.workflow_state_mcp:
                        self.console.print("[dim]No active workflow execution[/dim]")
                    else:
                        self.console.print("[yellow]Workflow State MCP not available. Type 'init' first.[/yellow]")
                    continue
                    
                # Pattern commands
                if user_input.lower() == 'pattern list':
                    if self.pattern_registry:
                        from rich.table import Table
                        
                        patterns = self.pattern_registry.list_patterns()
                        table = Table(title="Available MCP Patterns", show_header=True)
                        table.add_column("ID", style="cyan")
                        table.add_column("Name", style="white")
                        table.add_column("Category", style="yellow")
                        
                        for pattern in patterns[:15]:  # Show first 15
                            table.add_row(
                                pattern.pattern_id,
                                pattern.name[:40],
                                pattern.category.value
                            )
                        
                        self.console.print(table)
                    else:
                        self.console.print("[yellow]Pattern System not available. Type 'init' first.[/yellow]")
                    continue
                    
                if user_input.lower().startswith('pattern recommend '):
                    task_desc = user_input[18:].strip()
                    if task_desc and self.pattern_selector:
                        from mcp.patterns import PatternSelectionContext
                        
                        self.console.print(f"[cyan]Analyzing task: {task_desc}[/cyan]")
                        
                        context = PatternSelectionContext(
                            query=task_desc,
                            available_mcps=['hrm', 'task', 'coordination', 'workflow_state']
                        )
                        
                        recommendation = await self.pattern_selector.select_pattern(context)
                        
                        self.console.print(Panel(
                            f"[bold]Pattern:[/bold] {recommendation.pattern_name}\n"
                            f"[bold]ID:[/bold] {recommendation.pattern_id}\n"
                            f"[bold]Confidence:[/bold] {recommendation.confidence:.2%}\n\n"
                            f"[bold]Reasoning:[/bold]\n" + 
                            '\n'.join(f"• {r}" for r in recommendation.reasoning[:3]),
                            title="Pattern Recommendation",
                            border_style="green"
                        ))
                    elif not self.pattern_selector:
                        self.console.print("[yellow]Pattern System not available. Type 'init' first.[/yellow]")
                    else:
                        self.console.print("[yellow]Usage: pattern recommend <task description>[/yellow]")
                    continue
                    
                if user_input.lower().startswith('pattern execute '):
                    pattern_id = user_input[16:].strip()
                    if pattern_id and self.pattern_registry:
                        if pattern_id in self.pattern_registry.patterns:
                            pattern_def = self.pattern_registry.patterns[pattern_id]
                            self.console.print(f"[cyan]Executing pattern: {pattern_def.name}[/cyan]")
                            
                            try:
                                pattern = self.pattern_registry.get_pattern(pattern_id)
                                if await pattern.validate_prerequisites():
                                    result = await pattern.execute({'query': f'Execute {pattern_id}'})
                                    
                                    self.console.print(Panel(
                                        json.dumps(result, indent=2)[:500],  # Truncate for display
                                        title=f"Pattern Execution: {pattern_def.name}",
                                        border_style="green"
                                    ))
                                else:
                                    self.console.print("[red]Pattern prerequisites not met[/red]")
                            except Exception as e:
                                self.console.print(f"[red]Pattern execution error: {e}[/red]")
                        else:
                            self.console.print(f"[red]Pattern '{pattern_id}' not found[/red]")
                    elif not self.pattern_registry:
                        self.console.print("[yellow]Pattern System not available. Type 'init' first.[/yellow]")
                    else:
                        self.console.print("[yellow]Usage: pattern execute <pattern_id>[/yellow]")
                    continue
                    
                # GitHub commands
                if user_input.lower() == 'gh auth status':
                    if hasattr(self, 'github_mcp') and self.github_mcp:
                        auth_status = await self.github_mcp.check_auth()
                        if auth_status.get('authenticated', False):
                            self.console.print(f"[green]✓ Authenticated as: {auth_status.get('username', 'unknown')}[/green]")
                            self.console.print(f"[dim]Token valid for: {auth_status.get('scopes', [])}[/dim]")
                        else:
                            self.console.print("[yellow]Not authenticated with GitHub[/yellow]")
                            self.console.print("[dim]Run: gh auth login[/dim]")
                    else:
                        self.console.print("[yellow]GitHub MCP not available. Type 'init' first.[/yellow]")
                    continue
                    
                if user_input.lower() == 'gh repo list':
                    if hasattr(self, 'github_mcp') and self.github_mcp:
                        repos = await self.github_mcp.repo_list(limit=10)
                        if repos:
                            table = Table(title="Your GitHub Repositories (latest 10)", show_header=True)
                            table.add_column("Name", style="cyan")
                            table.add_column("Description", style="white")
                            table.add_column("Private", style="yellow")
                            table.add_column("Stars", style="green")
                            
                            for repo in repos:
                                table.add_row(
                                    repo.name,
                                    repo.description[:50] + "..." if repo.description and len(repo.description) > 50 else (repo.description or ""),
                                    "Yes" if repo.private else "No",
                                    str(repo.stargazers_count)
                                )
                            self.console.print(table)
                        else:
                            self.console.print("[yellow]No repositories found or GitHub not authenticated[/yellow]")
                    else:
                        self.console.print("[yellow]GitHub MCP not available. Type 'init' first.[/yellow]")
                    continue
                    
                if user_input.lower().startswith('gh repo create '):
                    repo_name = user_input[15:].strip()
                    if repo_name and hasattr(self, 'github_mcp') and self.github_mcp:
                        self.console.print(f"[cyan]Creating repository: {repo_name}[/cyan]")
                        result = await self.github_mcp.repo_create(
                            name=repo_name,
                            description=f"Created via LocalAgent CLI",
                            private=False
                        )
                        if result:
                            self.console.print(f"[green]✓ Repository '{repo_name}' created successfully![/green]")
                            self.console.print(f"[dim]URL: {result.html_url}[/dim]")
                        else:
                            self.console.print(f"[red]Failed to create repository '{repo_name}'[/red]")
                    elif not hasattr(self, 'github_mcp') or not self.github_mcp:
                        self.console.print("[yellow]GitHub MCP not available. Type 'init' first.[/yellow]")
                    else:
                        self.console.print("[yellow]Usage: gh repo create <repository_name>[/yellow]")
                    continue
                    
                if user_input.lower() == 'gh issue list':
                    if hasattr(self, 'github_mcp') and self.github_mcp:
                        issues = await self.github_mcp.issue_list(state="open", limit=10)
                        if issues:
                            table = Table(title="GitHub Issues (latest 10 open)", show_header=True)
                            table.add_column("Number", style="cyan")
                            table.add_column("Title", style="white")
                            table.add_column("State", style="yellow")
                            table.add_column("Labels", style="green")
                            
                            for issue in issues:
                                table.add_row(
                                    str(issue.number),
                                    issue.title[:50] + "..." if len(issue.title) > 50 else issue.title,
                                    issue.state,
                                    ", ".join(issue.labels) if issue.labels else ""
                                )
                            self.console.print(table)
                        else:
                            self.console.print("[yellow]No issues found or not in a GitHub repository[/yellow]")
                    else:
                        self.console.print("[yellow]GitHub MCP not available. Type 'init' first.[/yellow]")
                    continue
                    
                if user_input.lower().startswith('gh issue create '):
                    issue_title = user_input[16:].strip()
                    if issue_title and hasattr(self, 'github_mcp') and self.github_mcp:
                        body = Prompt.ask("Issue description (optional)", default="")
                        labels_input = Prompt.ask("Labels (comma-separated, optional)", default="")
                        labels = [label.strip() for label in labels_input.split(",") if label.strip()] if labels_input else []
                        
                        self.console.print(f"[cyan]Creating issue: {issue_title}[/cyan]")
                        result = await self.github_mcp.issue_create(
                            title=issue_title,
                            body=body if body else "",
                            labels=labels
                        )
                        if result:
                            self.console.print(f"[green]✓ Issue #{result.number} created successfully![/green]")
                            self.console.print(f"[dim]URL: {result.html_url}[/dim]")
                        else:
                            self.console.print(f"[red]Failed to create issue '{issue_title}'[/red]")
                    elif not hasattr(self, 'github_mcp') or not self.github_mcp:
                        self.console.print("[yellow]GitHub MCP not available. Type 'init' first.[/yellow]")
                    else:
                        self.console.print("[yellow]Usage: gh issue create <issue_title>[/yellow]")
                    continue
                    
                if user_input.lower() == 'gh pr list':
                    if hasattr(self, 'github_mcp') and self.github_mcp:
                        prs = await self.github_mcp.pr_list(state="open", limit=10)
                        if prs:
                            table = Table(title="GitHub Pull Requests (latest 10 open)", show_header=True)
                            table.add_column("Number", style="cyan")
                            table.add_column("Title", style="white")
                            table.add_column("Author", style="yellow")
                            table.add_column("Base", style="green")
                            
                            for pr in prs:
                                table.add_row(
                                    str(pr.number),
                                    pr.title[:50] + "..." if len(pr.title) > 50 else pr.title,
                                    pr.user.login if pr.user else "unknown",
                                    pr.base.ref if pr.base else "unknown"
                                )
                            self.console.print(table)
                        else:
                            self.console.print("[yellow]No pull requests found or not in a GitHub repository[/yellow]")
                    else:
                        self.console.print("[yellow]GitHub MCP not available. Type 'init' first.[/yellow]")
                    continue
                    
                if user_input.lower() == 'gh pr create':
                    if hasattr(self, 'github_mcp') and self.github_mcp:
                        title = Prompt.ask("PR title")
                        body = Prompt.ask("PR description (optional)", default="")
                        base = Prompt.ask("Base branch", default="main")
                        draft = Prompt.ask("Create as draft?", choices=["y", "n"], default="n") == "y"
                        
                        if title:
                            self.console.print(f"[cyan]Creating pull request: {title}[/cyan]")
                            result = await self.github_mcp.pr_create(
                                title=title,
                                body=body if body else "",
                                base=base,
                                draft=draft
                            )
                            if result:
                                self.console.print(f"[green]✓ Pull request #{result.number} created successfully![/green]")
                                self.console.print(f"[dim]URL: {result.html_url}[/dim]")
                            else:
                                self.console.print("[red]Failed to create pull request[/red]")
                        else:
                            self.console.print("[red]PR title is required[/red]")
                    else:
                        self.console.print("[yellow]GitHub MCP not available. Type 'init' first.[/yellow]")
                    continue
                    
                # Check for tool commands if initialized
                if self.initialized:
                    tool_result = await self.process_with_tools(user_input)
                    if tool_result:
                        self.console.print(f"\n[green]{tool_result}[/green]\n")
                        continue
                        
                    # Check for workflow activation
                    if "workflow" in user_input.lower() or "orchestrate" in user_input.lower():
                        result = await self.process_with_workflow(user_input)
                        self.console.print(Panel(
                            Markdown(result) if isinstance(result, str) else str(result),
                            title="Workflow Result",
                            border_style="green"
                        ))
                        continue
                        
                # Standard chat with context
                with self.console.status("[dim]Thinking...[/dim]", spinner="dots"):
                    response = self.chat_with_model(user_input)
                    
                # Display response
                self.console.print("\n[bold green]Assistant:[/bold green]")
                self.console.print(Panel(
                    Markdown(response) if isinstance(response, str) else str(response),
                    border_style="green",
                    padding=(1, 2)
                ))
                self.console.print()
                
            except KeyboardInterrupt:
                self.console.print("\n\n[cyan]👋 Interrupted. Goodbye![/cyan]")
                break
            except Exception as e:
                self.console.print(f"\n[red]Error: {e}[/red]\n")
                if "--debug" in sys.argv:
                    import traceback
                    traceback.print_exc()

@click.command()
@click.option('--model', '-m', help='Model to use (default: auto-detect)')
@click.option('--debug', is_flag=True, help='Enable debug output')
def interactive_enhanced(model=None, debug=False):
    """Start an enhanced interactive chat session with full features"""
    if debug:
        sys.argv.append("--debug")
    cli = EnhancedInteractiveCLI()
    if model:
        cli.current_model = model
    asyncio.run(cli.run())

def main():
    """Main entry point for console script"""
    interactive_enhanced()

if __name__ == '__main__':
    interactive_enhanced()