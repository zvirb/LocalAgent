"""
MCP (Model Context Protocol) Integration for LocalAgent CLI
Provides comprehensive access to all MCP services for agent tools
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import logging

# Add MCP directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'mcp'))

# Import all MCP services
try:
    from coordination_mcp import CoordinationMCP
    from hrm_mcp import HRM_MCP
    from task_mcp import TaskMCP
    from workflow_state_mcp import WorkflowStateMCP
except ImportError as e:
    logging.warning(f"Some MCP services not available: {e}")
    # Define placeholder classes
    class CoordinationMCP: pass
    class HRM_MCP: pass
    class TaskMCP: pass
    class WorkflowStateMCP: pass

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Represents a tool that agents can invoke"""
    name: str
    description: str
    handler: Callable
    parameters: Dict[str, Any]
    requires_auth: bool = False
    category: str = "general"


class MCPIntegration:
    """Integrates all MCP services for agent access"""
    
    def __init__(self):
        """Initialize MCP integration with all available services"""
        self.services = {}
        self.tools = {}
        self._initialize_services()
        self._register_tools()
        
    def _initialize_services(self):
        """Initialize all MCP services"""
        try:
            # Coordination MCP for agent coordination
            self.services['coordination'] = CoordinationMCP()
            logger.info("Initialized Coordination MCP")
        except Exception as e:
            logger.warning(f"Failed to initialize Coordination MCP: {e}")
            
        try:
            # HRM MCP for human-readable memory
            self.services['hrm'] = HRM_MCP()
            logger.info("Initialized HRM MCP")
        except Exception as e:
            logger.warning(f"Failed to initialize HRM MCP: {e}")
            
        try:
            # Task MCP for task management
            self.services['task'] = TaskMCP()
            logger.info("Initialized Task MCP")
        except Exception as e:
            logger.warning(f"Failed to initialize Task MCP: {e}")
            
        try:
            # Workflow State MCP for workflow management
            self.services['workflow_state'] = WorkflowStateMCP()
            logger.info("Initialized Workflow State MCP")
        except Exception as e:
            logger.warning(f"Failed to initialize Workflow State MCP: {e}")
    
    def _register_tools(self):
        """Register all tools available to agents"""
        
        # File operation tools
        self._register_file_tools()
        
        # MCP service tools
        self._register_mcp_tools()
        
        # System tools
        self._register_system_tools()
        
        # Network tools
        self._register_network_tools()
        
        # Analysis tools
        self._register_analysis_tools()
    
    def _register_file_tools(self):
        """Register file operation tools"""
        
        # Read file
        self.tools['read_file'] = Tool(
            name="read_file",
            description="Read contents of a file",
            handler=self._read_file,
            parameters={
                "path": {"type": "string", "description": "File path to read"},
                "encoding": {"type": "string", "default": "utf-8"}
            },
            category="file"
        )
        
        # Write file
        self.tools['write_file'] = Tool(
            name="write_file",
            description="Write content to a file",
            handler=self._write_file,
            parameters={
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
                "mode": {"type": "string", "default": "w"},
                "encoding": {"type": "string", "default": "utf-8"}
            },
            category="file"
        )
        
        # List directory
        self.tools['list_directory'] = Tool(
            name="list_directory",
            description="List contents of a directory",
            handler=self._list_directory,
            parameters={
                "path": {"type": "string", "description": "Directory path"},
                "recursive": {"type": "boolean", "default": False}
            },
            category="file"
        )
        
        # Create directory
        self.tools['create_directory'] = Tool(
            name="create_directory",
            description="Create a directory",
            handler=self._create_directory,
            parameters={
                "path": {"type": "string", "description": "Directory path"},
                "parents": {"type": "boolean", "default": True}
            },
            category="file"
        )
        
        # Delete file/directory
        self.tools['delete_path'] = Tool(
            name="delete_path",
            description="Delete a file or directory",
            handler=self._delete_path,
            parameters={
                "path": {"type": "string", "description": "Path to delete"},
                "recursive": {"type": "boolean", "default": False}
            },
            category="file"
        )
        
        # Copy file/directory
        self.tools['copy_path'] = Tool(
            name="copy_path",
            description="Copy a file or directory",
            handler=self._copy_path,
            parameters={
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"},
                "overwrite": {"type": "boolean", "default": False}
            },
            category="file"
        )
    
    def _register_mcp_tools(self):
        """Register MCP service tools"""
        
        # Coordination tools
        if 'coordination' in self.services:
            self.tools['coordinate_agents'] = Tool(
                name="coordinate_agents",
                description="Coordinate agent execution",
                handler=self._coordinate_agents,
                parameters={
                    "agents": {"type": "array", "description": "List of agent names"},
                    "task": {"type": "string", "description": "Task description"},
                    "parallel": {"type": "boolean", "default": False}
                },
                category="mcp"
            )
        
        # HRM tools
        if 'hrm' in self.services:
            self.tools['store_memory'] = Tool(
                name="store_memory",
                description="Store human-readable memory",
                handler=self._store_memory,
                parameters={
                    "key": {"type": "string", "description": "Memory key"},
                    "value": {"type": "any", "description": "Memory value"},
                    "ttl": {"type": "integer", "description": "TTL in seconds", "default": None}
                },
                category="mcp"
            )
            
            self.tools['retrieve_memory'] = Tool(
                name="retrieve_memory",
                description="Retrieve human-readable memory",
                handler=self._retrieve_memory,
                parameters={
                    "key": {"type": "string", "description": "Memory key"}
                },
                category="mcp"
            )
        
        # Task tools
        if 'task' in self.services:
            self.tools['create_task'] = Tool(
                name="create_task",
                description="Create a new task",
                handler=self._create_task,
                parameters={
                    "name": {"type": "string", "description": "Task name"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "integer", "default": 5}
                },
                category="mcp"
            )
            
            self.tools['update_task'] = Tool(
                name="update_task",
                description="Update task status",
                handler=self._update_task,
                parameters={
                    "task_id": {"type": "string", "description": "Task ID"},
                    "status": {"type": "string", "description": "New status"},
                    "progress": {"type": "integer", "description": "Progress percentage"}
                },
                category="mcp"
            )
        
        # Workflow tools
        if 'workflow_state' in self.services:
            self.tools['get_workflow_state'] = Tool(
                name="get_workflow_state",
                description="Get current workflow state",
                handler=self._get_workflow_state,
                parameters={
                    "workflow_id": {"type": "string", "description": "Workflow ID", "default": "current"}
                },
                category="mcp"
            )
            
            self.tools['update_workflow_state'] = Tool(
                name="update_workflow_state",
                description="Update workflow state",
                handler=self._update_workflow_state,
                parameters={
                    "workflow_id": {"type": "string", "description": "Workflow ID"},
                    "phase": {"type": "string", "description": "Current phase"},
                    "data": {"type": "object", "description": "State data"}
                },
                category="mcp"
            )
    
    def _register_system_tools(self):
        """Register system operation tools"""
        
        self.tools['execute_command'] = Tool(
            name="execute_command",
            description="Execute a system command",
            handler=self._execute_command,
            parameters={
                "command": {"type": "string", "description": "Command to execute"},
                "shell": {"type": "boolean", "default": True},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
            },
            category="system"
        )
        
        self.tools['get_environment'] = Tool(
            name="get_environment",
            description="Get environment variables",
            handler=self._get_environment,
            parameters={
                "key": {"type": "string", "description": "Environment variable key", "default": None}
            },
            category="system"
        )
    
    def _register_network_tools(self):
        """Register network operation tools"""
        
        self.tools['http_request'] = Tool(
            name="http_request",
            description="Make an HTTP request",
            handler=self._http_request,
            parameters={
                "url": {"type": "string", "description": "URL to request"},
                "method": {"type": "string", "default": "GET"},
                "headers": {"type": "object", "default": {}},
                "data": {"type": "any", "default": None},
                "timeout": {"type": "integer", "default": 30}
            },
            category="network"
        )
    
    def _register_analysis_tools(self):
        """Register analysis tools"""
        
        self.tools['analyze_code'] = Tool(
            name="analyze_code",
            description="Analyze code for patterns and issues",
            handler=self._analyze_code,
            parameters={
                "code": {"type": "string", "description": "Code to analyze"},
                "language": {"type": "string", "description": "Programming language"},
                "checks": {"type": "array", "description": "Checks to perform", "default": ["syntax", "style"]}
            },
            category="analysis"
        )
    
    # Tool handler implementations
    
    async def _read_file(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file contents"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            raise
    
    async def _write_file(self, path: str, content: str, mode: str = 'w', encoding: str = 'utf-8') -> bool:
        """Write content to file"""
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            return True
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            raise
    
    async def _list_directory(self, path: str, recursive: bool = False) -> List[str]:
        """List directory contents"""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                raise FileNotFoundError(f"Directory not found: {path}")
            
            if recursive:
                return [str(p.relative_to(dir_path)) for p in dir_path.rglob("*")]
            else:
                return [p.name for p in dir_path.iterdir()]
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            raise
    
    async def _create_directory(self, path: str, parents: bool = True) -> bool:
        """Create directory"""
        try:
            Path(path).mkdir(parents=parents, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            raise
    
    async def _delete_path(self, path: str, recursive: bool = False) -> bool:
        """Delete file or directory"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return False
            
            if file_path.is_dir():
                if recursive:
                    import shutil
                    shutil.rmtree(file_path)
                else:
                    file_path.rmdir()
            else:
                file_path.unlink()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            raise
    
    async def _copy_path(self, source: str, destination: str, overwrite: bool = False) -> bool:
        """Copy file or directory"""
        try:
            import shutil
            
            src_path = Path(source)
            dst_path = Path(destination)
            
            if not src_path.exists():
                raise FileNotFoundError(f"Source not found: {source}")
            
            if dst_path.exists() and not overwrite:
                raise FileExistsError(f"Destination exists: {destination}")
            
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src_path, dst_path)
            
            return True
        except Exception as e:
            logger.error(f"Error copying {source} to {destination}: {e}")
            raise
    
    async def _coordinate_agents(self, agents: List[str], task: str, parallel: bool = False) -> Dict[str, Any]:
        """Coordinate agent execution"""
        if 'coordination' not in self.services:
            raise RuntimeError("Coordination MCP not available")
        
        # Implementation would use coordination MCP
        return {
            "agents": agents,
            "task": task,
            "parallel": parallel,
            "status": "coordinated"
        }
    
    async def _store_memory(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store memory in HRM"""
        if 'hrm' not in self.services:
            raise RuntimeError("HRM MCP not available")
        
        # Implementation would use HRM MCP
        return True
    
    async def _retrieve_memory(self, key: str) -> Any:
        """Retrieve memory from HRM"""
        if 'hrm' not in self.services:
            raise RuntimeError("HRM MCP not available")
        
        # Implementation would use HRM MCP
        return None
    
    async def _create_task(self, name: str, description: str, priority: int = 5) -> str:
        """Create a new task"""
        if 'task' not in self.services:
            raise RuntimeError("Task MCP not available")
        
        # Implementation would use Task MCP
        return f"task_{name}"
    
    async def _update_task(self, task_id: str, status: str, progress: int) -> bool:
        """Update task status"""
        if 'task' not in self.services:
            raise RuntimeError("Task MCP not available")
        
        # Implementation would use Task MCP
        return True
    
    async def _get_workflow_state(self, workflow_id: str = "current") -> Dict[str, Any]:
        """Get workflow state"""
        if 'workflow_state' not in self.services:
            raise RuntimeError("Workflow State MCP not available")
        
        # Implementation would use Workflow State MCP
        return {"workflow_id": workflow_id, "state": "active"}
    
    async def _update_workflow_state(self, workflow_id: str, phase: str, data: Dict[str, Any]) -> bool:
        """Update workflow state"""
        if 'workflow_state' not in self.services:
            raise RuntimeError("Workflow State MCP not available")
        
        # Implementation would use Workflow State MCP
        return True
    
    async def _execute_command(self, command: str, shell: bool = True, timeout: int = 30) -> Dict[str, Any]:
        """Execute system command"""
        import subprocess
        
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_environment(self, key: Optional[str] = None) -> Any:
        """Get environment variables"""
        if key:
            return os.environ.get(key)
        return dict(os.environ)
    
    async def _http_request(self, url: str, method: str = "GET", headers: Dict = None, 
                           data: Any = None, timeout: int = 30) -> Dict[str, Any]:
        """Make HTTP request"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers or {},
                    json=data if isinstance(data, dict) else None,
                    data=data if not isinstance(data, dict) else None,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    return {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "text": await response.text(),
                        "url": str(response.url)
                    }
        except Exception as e:
            return {"error": str(e)}
    
    async def _analyze_code(self, code: str, language: str, checks: List[str] = None) -> Dict[str, Any]:
        """Analyze code"""
        checks = checks or ["syntax", "style"]
        
        # Basic implementation - would integrate with actual analysis tools
        return {
            "language": language,
            "checks_performed": checks,
            "lines": len(code.split('\n')),
            "characters": len(code)
        }
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a specific tool by name"""
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category"""
        return [tool for tool in self.tools.values() if tool.category == category]
    
    def list_available_tools(self) -> List[str]:
        """List all available tool names"""
        return list(self.tools.keys())
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all tools"""
        return {name: tool.description for name, tool in self.tools.items()}
    
    async def invoke_tool(self, tool_name: str, **kwargs) -> Any:
        """Invoke a tool by name with parameters"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Validate parameters
        for param, config in tool.parameters.items():
            if param not in kwargs and "default" not in config:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Invoke the tool handler
        return await tool.handler(**kwargs)


class AgentToolAccess:
    """Manages agent access to tools and permissions"""
    
    def __init__(self, mcp_integration: MCPIntegration):
        self.mcp = mcp_integration
        self.permissions = {}
        self._set_default_permissions()
    
    def _set_default_permissions(self):
        """Set default permissions for agents"""
        # All agents can read files and use analysis tools
        self.permissions['*'] = {
            'allowed_categories': ['file', 'analysis', 'mcp'],
            'allowed_tools': ['read_file', 'list_directory', 'analyze_code'],
            'denied_tools': []
        }
        
        # Specific agent permissions
        self.permissions['deployment-orchestrator'] = {
            'allowed_categories': ['*'],  # All categories
            'allowed_tools': ['*'],  # All tools
            'denied_tools': []
        }
        
        self.permissions['security-validator'] = {
            'allowed_categories': ['file', 'analysis', 'system'],
            'allowed_tools': ['*'],
            'denied_tools': ['delete_path', 'execute_command']
        }
    
    def can_use_tool(self, agent_name: str, tool_name: str) -> bool:
        """Check if agent can use a specific tool"""
        # Get agent permissions
        perms = self.permissions.get(agent_name, self.permissions.get('*', {}))
        
        # Check denied tools first
        if tool_name in perms.get('denied_tools', []):
            return False
        
        # Check allowed tools
        if '*' in perms.get('allowed_tools', []):
            return True
        if tool_name in perms.get('allowed_tools', []):
            return True
        
        # Check category permissions
        tool = self.mcp.get_tool(tool_name)
        if tool and ('*' in perms.get('allowed_categories', []) or 
                     tool.category in perms.get('allowed_categories', [])):
            return True
        
        return False
    
    def get_available_tools_for_agent(self, agent_name: str) -> List[str]:
        """Get list of tools available to an agent"""
        available = []
        for tool_name in self.mcp.list_available_tools():
            if self.can_use_tool(agent_name, tool_name):
                available.append(tool_name)
        return available
    
    async def invoke_tool_as_agent(self, agent_name: str, tool_name: str, **kwargs) -> Any:
        """Invoke a tool as a specific agent with permission checking"""
        if not self.can_use_tool(agent_name, tool_name):
            raise PermissionError(f"Agent '{agent_name}' is not allowed to use tool '{tool_name}'")
        
        logger.info(f"Agent '{agent_name}' invoking tool '{tool_name}' with params: {kwargs}")
        
        try:
            result = await self.mcp.invoke_tool(tool_name, **kwargs)
            logger.info(f"Tool '{tool_name}' completed successfully for agent '{agent_name}'")
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed for agent '{agent_name}': {e}")
            raise