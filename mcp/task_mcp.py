#!/usr/bin/env python3
"""
Task Management MCP (Model Context Protocol) Server
Independent implementation for LocalAgent project
Provides task creation, tracking, prioritization, and analysis
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import uuid

@dataclass
class Task:
    """Individual task representation"""
    task_id: str
    title: str
    description: str
    status: str  # todo, in_progress, blocked, completed, cancelled
    priority: str  # low, medium, high, urgent
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        data = asdict(self)
        # Convert datetime objects to ISO format
        for key in ['created_at', 'updated_at', 'due_date', 'completed_at']:
            if data[key]:
                data[key] = data[key].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        # Convert ISO strings back to datetime
        for key in ['created_at', 'updated_at', 'due_date', 'completed_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)

class TaskStatus(str, Enum):
    """Task status states"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskMCP:
    """
    Task Management MCP Server
    Provides comprehensive task tracking and management capabilities
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tasks: Dict[str, Task] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
        self.state_file = Path(self.config.get('state_file', '.task_state.json'))
        
    async def initialize(self):
        """Initialize the Task MCP server"""
        self.logger.info("Initializing Task MCP Server")
        
        # Load saved state
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    # Restore tasks
                    for task_data in state.get('tasks', []):
                        task = Task.from_dict(task_data)
                        self.tasks[task.task_id] = task
                    self.task_history = state.get('history', [])
                    self.logger.info(f"Loaded {len(self.tasks)} tasks from state")
            except Exception as e:
                self.logger.warning(f"Could not load state: {e}")
                
        return True
    
    async def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: Optional[datetime] = None,
        tags: List[str] = None,
        dependencies: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Task:
        """Create a new task"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        
        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            status=TaskStatus.TODO.value,
            priority=priority,
            created_at=now,
            updated_at=now,
            due_date=due_date,
            tags=tags or [],
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task
        
        # Record in history
        self._record_history("create", task_id, {"title": title, "priority": priority})
        
        self.logger.info(f"Created task {task_id}: {title}")
        return task
    
    async def update_task(
        self,
        task_id: str,
        **updates: Any
    ) -> Optional[Task]:
        """Update an existing task"""
        if task_id not in self.tasks:
            self.logger.warning(f"Task {task_id} not found")
            return None
        
        task = self.tasks[task_id]
        old_status = task.status
        
        # Update fields
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        task.updated_at = datetime.now()
        
        # Handle status transitions
        if 'status' in updates:
            new_status = updates['status']
            if new_status == TaskStatus.COMPLETED.value and old_status != TaskStatus.COMPLETED.value:
                task.completed_at = datetime.now()
            elif old_status == TaskStatus.COMPLETED.value and new_status != TaskStatus.COMPLETED.value:
                task.completed_at = None
        
        # Record in history
        self._record_history("update", task_id, updates)
        
        self.logger.info(f"Updated task {task_id}")
        return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task"""
        return self.tasks.get(task_id)
    
    async def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None,
        assigned_to: Optional[str] = None,
        include_completed: bool = False
    ) -> List[Task]:
        """List tasks with filters"""
        results = []
        
        for task in self.tasks.values():
            # Filter by status
            if status and task.status != status:
                continue
            
            # Skip completed unless requested
            if not include_completed and task.status == TaskStatus.COMPLETED.value:
                continue
            
            # Filter by priority
            if priority and task.priority != priority:
                continue
            
            # Filter by tags (any match)
            if tags and not any(tag in task.tags for tag in tags):
                continue
            
            # Filter by assignment
            if assigned_to and task.assigned_to != assigned_to:
                continue
            
            results.append(task)
        
        # Sort by priority and creation date
        priority_order = {
            TaskPriority.URGENT.value: 0,
            TaskPriority.HIGH.value: 1,
            TaskPriority.MEDIUM.value: 2,
            TaskPriority.LOW.value: 3
        }
        
        results.sort(key=lambda t: (priority_order.get(t.priority, 99), t.created_at))
        return results
    
    async def analyze_workload(self) -> Dict[str, Any]:
        """Analyze current workload and provide insights"""
        total_tasks = len(self.tasks)
        
        # Status distribution
        status_counts = {}
        for status in TaskStatus:
            count = sum(1 for t in self.tasks.values() if t.status == status.value)
            status_counts[status.value] = count
        
        # Priority distribution
        priority_counts = {}
        for priority in TaskPriority:
            count = sum(1 for t in self.tasks.values() if t.priority == priority.value)
            priority_counts[priority.value] = count
        
        # Calculate completion rate
        completed = status_counts.get(TaskStatus.COMPLETED.value, 0)
        completion_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        # Find overdue tasks
        now = datetime.now()
        overdue_tasks = []
        for task in self.tasks.values():
            if (task.due_date and 
                task.due_date < now and 
                task.status not in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]):
                overdue_tasks.append({
                    'task_id': task.task_id,
                    'title': task.title,
                    'days_overdue': (now - task.due_date).days
                })
        
        # Find blocked tasks
        blocked_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.BLOCKED.value]
        
        return {
            'total_tasks': total_tasks,
            'status_distribution': status_counts,
            'priority_distribution': priority_counts,
            'completion_rate': round(completion_rate, 2),
            'overdue_count': len(overdue_tasks),
            'overdue_tasks': overdue_tasks[:5],  # Top 5 overdue
            'blocked_count': len(blocked_tasks),
            'blocked_tasks': [{'id': t.task_id, 'title': t.title} for t in blocked_tasks[:5]]
        }
    
    async def get_task_dependencies(self, task_id: str) -> Dict[str, Any]:
        """Get task dependency information"""
        if task_id not in self.tasks:
            return {'error': 'Task not found'}
        
        task = self.tasks[task_id]
        
        # Get direct dependencies
        dependencies = []
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                dep_task = self.tasks[dep_id]
                dependencies.append({
                    'task_id': dep_id,
                    'title': dep_task.title,
                    'status': dep_task.status,
                    'is_blocking': dep_task.status != TaskStatus.COMPLETED.value
                })
        
        # Get tasks that depend on this task
        dependents = []
        for other_task in self.tasks.values():
            if task_id in other_task.dependencies:
                dependents.append({
                    'task_id': other_task.task_id,
                    'title': other_task.title,
                    'status': other_task.status
                })
        
        return {
            'task_id': task_id,
            'title': task.title,
            'dependencies': dependencies,
            'dependents': dependents,
            'can_start': all(d['status'] == TaskStatus.COMPLETED.value 
                           for d in dependencies)
        }
    
    async def bulk_update_status(
        self,
        task_ids: List[str],
        new_status: str
    ) -> Dict[str, bool]:
        """Bulk update task status"""
        results = {}
        
        for task_id in task_ids:
            task = await self.update_task(task_id, status=new_status)
            results[task_id] = task is not None
        
        return results
    
    async def create_subtask(
        self,
        parent_id: str,
        title: str,
        description: str = "",
        **kwargs
    ) -> Optional[Task]:
        """Create a subtask under a parent task"""
        if parent_id not in self.tasks:
            self.logger.warning(f"Parent task {parent_id} not found")
            return None
        
        # Create the subtask
        subtask = await self.create_task(
            title=title,
            description=description,
            **kwargs
        )
        
        # Link to parent
        parent = self.tasks[parent_id]
        parent.subtasks.append(subtask.task_id)
        
        # Add dependency on parent
        subtask.dependencies.append(parent_id)
        subtask.metadata['parent_id'] = parent_id
        
        return subtask
    
    async def get_task_timeline(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get task timeline for the next N days"""
        now = datetime.now()
        end_date = now + timedelta(days=days)
        
        timeline = []
        
        for task in self.tasks.values():
            # Skip completed/cancelled tasks
            if task.status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
                continue
            
            # Check if task falls within timeline
            if task.due_date and now <= task.due_date <= end_date:
                timeline.append({
                    'task_id': task.task_id,
                    'title': task.title,
                    'due_date': task.due_date.isoformat(),
                    'days_until_due': (task.due_date - now).days,
                    'priority': task.priority,
                    'status': task.status
                })
        
        # Sort by due date
        timeline.sort(key=lambda x: x['due_date'])
        return timeline
    
    def _record_history(self, action: str, task_id: str, details: Dict[str, Any]):
        """Record task history"""
        self.task_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'task_id': task_id,
            'details': details
        })
        
        # Keep only last 1000 history items
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-1000:]
    
    async def save_state(self):
        """Save current state to disk"""
        try:
            state = {
                'tasks': [task.to_dict() for task in self.tasks.values()],
                'history': self.task_history[-100:],  # Save last 100 history items
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.logger.info(f"Saved task state to {self.state_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False
    
    async def export_markdown(self) -> str:
        """Export tasks as markdown"""
        md_lines = ["# Task List\n"]
        md_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        # Group by status
        for status in [TaskStatus.URGENT, TaskStatus.IN_PROGRESS, TaskStatus.TODO, 
                      TaskStatus.BLOCKED, TaskStatus.COMPLETED]:
            tasks_in_status = [t for t in self.tasks.values() if t.status == status.value]
            
            if tasks_in_status:
                md_lines.append(f"\n## {status.value.replace('_', ' ').title()}\n")
                
                for task in tasks_in_status:
                    checkbox = "[x]" if task.status == TaskStatus.COMPLETED.value else "[ ]"
                    priority_emoji = {
                        "urgent": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢"
                    }.get(task.priority, "")
                    
                    md_lines.append(f"- {checkbox} {priority_emoji} **{task.title}**")
                    if task.description:
                        md_lines.append(f"  - {task.description}")
                    if task.due_date:
                        md_lines.append(f"  - Due: {task.due_date.strftime('%Y-%m-%d')}")
                    if task.tags:
                        md_lines.append(f"  - Tags: {', '.join(task.tags)}")
                    md_lines.append("")
        
        return "\n".join(md_lines)

# Convenience function for standalone usage
async def create_task_server(config: Dict[str, Any] = None):
    """Create and initialize a Task MCP server"""
    server = TaskMCP(config)
    await server.initialize()
    return server

if __name__ == "__main__":
    # Test the Task MCP
    async def test():
        task_mcp = await create_task_server()
        
        # Create some test tasks
        task1 = await task_mcp.create_task(
            "Implement authentication system",
            "Add JWT-based auth to the API",
            priority="high",
            tags=["security", "backend"]
        )
        
        task2 = await task_mcp.create_task(
            "Write unit tests",
            "Add tests for auth system",
            priority="medium",
            dependencies=[task1.task_id]
        )
        
        task3 = await task_mcp.create_task(
            "Update documentation",
            "Document the new auth endpoints",
            priority="low",
            dependencies=[task1.task_id]
        )
        
        # Analyze workload
        analysis = await task_mcp.analyze_workload()
        print("Workload Analysis:", json.dumps(analysis, indent=2))
        
        # Get timeline
        timeline = await task_mcp.get_task_timeline(30)
        print("\nUpcoming Tasks:", json.dumps(timeline, indent=2))
        
        # Export to markdown
        markdown = await task_mcp.export_markdown()
        print("\nMarkdown Export:\n", markdown)
        
        # Save state
        await task_mcp.save_state()
    
    asyncio.run(test())