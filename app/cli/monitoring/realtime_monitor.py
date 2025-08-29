"""
Real-time Monitoring System for CLI Orchestration
Provides live workflow execution tracking and progress displays
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.text import Text
import websockets
import redis.asyncio as redis

console = Console()

class WorkflowMonitor:
    """Real-time workflow execution monitor with Rich displays"""
    
    def __init__(self):
        self.phases_status = {i: "pending" for i in range(13)}
        self.agent_status = {}
        self.current_phase = 0
        self.workflow_id = None
        self.start_time = None
        self.redis_client = None
        self.websocket = None
        self.monitoring_task = None
        
    async def initialize(self, workflow_id: str):
        """Initialize monitoring for a workflow"""
        self.workflow_id = workflow_id
        self.start_time = datetime.now()
        
        # Connect to Redis for coordination
        try:
            self.redis_client = await redis.from_url(
                "redis://localhost:6379",
                decode_responses=True
            )
            await self.redis_client.ping()
        except Exception as e:
            console.print(f"[yellow]Redis connection failed (non-critical): {e}[/yellow]")
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitor_loop())
    
    def create_dashboard_layout(self) -> Layout:
        """Create Rich layout for monitoring dashboard"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="phases", ratio=1),
            Layout(name="agents", ratio=1)
        )
        
        return layout
    
    def generate_phases_table(self) -> Table:
        """Generate table showing phase statuses"""
        table = Table(title="Workflow Phases", show_header=True)
        table.add_column("Phase", style="cyan", width=8)
        table.add_column("Name", style="white", width=30)
        table.add_column("Status", style="white", width=15)
        table.add_column("Evidence", style="dim", width=20)
        
        phase_names = {
            0: "Interactive Prompt Engineering",
            1: "Parallel Research & Discovery",
            2: "Strategic Planning",
            3: "Context Package Creation",
            4: "Parallel Stream Execution",
            5: "Integration & Merge",
            6: "Comprehensive Testing",
            7: "Audit & Learning",
            8: "Cleanup & Documentation",
            9: "Development Deployment",
            10: "Production Deployment",
            11: "Production Validation",
            12: "Monitoring & Loop Control"
        }
        
        for phase, name in phase_names.items():
            status = self.phases_status.get(phase, "pending")
            
            # Status styling
            if status == "completed":
                status_display = Text("✓ Completed", style="green")
            elif status == "running":
                status_display = Text("⚡ Running", style="yellow")
            elif status == "failed":
                status_display = Text("✗ Failed", style="red")
            else:
                status_display = Text("⏳ Pending", style="dim")
            
            evidence = "✓" if phase < self.current_phase else "-"
            
            table.add_row(
                f"Phase {phase}",
                name,
                status_display,
                evidence
            )
        
        return table
    
    def generate_agents_table(self) -> Table:
        """Generate table showing agent execution status"""
        table = Table(title="Agent Execution", show_header=True)
        table.add_column("Agent", style="cyan", width=35)
        table.add_column("Status", style="white", width=15)
        table.add_column("Duration", style="dim", width=10)
        
        for agent_name, status_info in self.agent_status.items():
            status = status_info.get('status', 'pending')
            duration = status_info.get('duration', '-')
            
            # Status styling
            if status == "completed":
                status_display = Text("✓ Done", style="green")
            elif status == "running":
                status_display = Text("⚡ Running", style="yellow")
            elif status == "failed":
                status_display = Text("✗ Failed", style="red")
            else:
                status_display = Text("⏳ Waiting", style="dim")
            
            table.add_row(agent_name, status_display, str(duration))
        
        return table
    
    def generate_header(self) -> Panel:
        """Generate header panel with workflow info"""
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
        else:
            elapsed_str = "0s"
        
        header_text = Text()
        header_text.append("Workflow ID: ", style="bold")
        header_text.append(f"{self.workflow_id}\n", style="cyan")
        header_text.append("Current Phase: ", style="bold")
        header_text.append(f"Phase {self.current_phase}\n", style="yellow")
        header_text.append("Elapsed Time: ", style="bold")
        header_text.append(elapsed_str, style="green")
        
        return Panel(header_text, title="[bold cyan]CLI Orchestration Monitor[/bold cyan]")
    
    def generate_footer(self) -> Panel:
        """Generate footer panel with statistics"""
        completed_phases = sum(1 for s in self.phases_status.values() if s == "completed")
        active_agents = sum(1 for a in self.agent_status.values() if a.get('status') == 'running')
        
        footer_text = Text()
        footer_text.append(f"Phases Completed: {completed_phases}/13 | ", style="green")
        footer_text.append(f"Active Agents: {active_agents} | ", style="yellow")
        footer_text.append("Press Ctrl+C to exit", style="dim")
        
        return Panel(footer_text, style="dim")
    
    async def display_live_dashboard(self):
        """Display live updating dashboard"""
        layout = self.create_dashboard_layout()
        
        with Live(layout, refresh_per_second=2, screen=True) as live:
            while True:
                # Update layout components
                layout["header"].update(self.generate_header())
                layout["phases"].update(self.generate_phases_table())
                layout["agents"].update(self.generate_agents_table())
                layout["footer"].update(self.generate_footer())
                
                await asyncio.sleep(0.5)
    
    async def _monitor_loop(self):
        """Background monitoring loop"""
        if not self.redis_client:
            return
        
        # Subscribe to orchestration events
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(
            'orchestration:phase:start',
            'orchestration:phase:complete',
            'orchestration:agent:start',
            'orchestration:agent:complete'
        )
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    await self._handle_event(message['channel'], message['data'])
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe()
    
    async def _handle_event(self, channel: str, data: str):
        """Handle orchestration events"""
        try:
            event_data = json.loads(data)
            
            if channel == 'orchestration:phase:start':
                phase = event_data.get('phase', 0)
                self.phases_status[phase] = 'running'
                self.current_phase = phase
                
            elif channel == 'orchestration:phase:complete':
                phase = event_data.get('phase', 0)
                success = event_data.get('success', False)
                self.phases_status[phase] = 'completed' if success else 'failed'
                
            elif channel == 'orchestration:agent:start':
                agent = event_data.get('agent', 'unknown')
                self.agent_status[agent] = {
                    'status': 'running',
                    'start_time': datetime.now()
                }
                
            elif channel == 'orchestration:agent:complete':
                agent = event_data.get('agent', 'unknown')
                if agent in self.agent_status:
                    start_time = self.agent_status[agent].get('start_time')
                    if start_time:
                        duration = (datetime.now() - start_time).total_seconds()
                        self.agent_status[agent]['duration'] = f"{duration:.1f}s"
                    self.agent_status[agent]['status'] = 'completed'
                    
        except Exception as e:
            console.print(f"[red]Error handling event: {e}[/red]")
    
    async def cleanup(self):
        """Cleanup monitoring resources"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()


class ProgressTracker:
    """Track and display progress for CLI operations"""
    
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        )
        self.tasks = {}
        
    def add_phase_task(self, phase: int, description: str) -> int:
        """Add a phase tracking task"""
        task_id = self.progress.add_task(f"[cyan]Phase {phase}: {description}", total=100)
        self.tasks[f"phase_{phase}"] = task_id
        return task_id
    
    def add_agent_task(self, agent: str, description: str) -> int:
        """Add an agent tracking task"""
        task_id = self.progress.add_task(f"[yellow]{agent}: {description}", total=100)
        self.tasks[f"agent_{agent}"] = task_id
        return task_id
    
    def update_task(self, task_key: str, completed: int):
        """Update task progress"""
        if task_key in self.tasks:
            self.progress.update(self.tasks[task_key], completed=completed)
    
    def complete_task(self, task_key: str):
        """Mark task as complete"""
        if task_key in self.tasks:
            self.progress.update(self.tasks[task_key], completed=100)
    
    async def display_with_callback(self, callback: Callable):
        """Display progress with a callback function"""
        with self.progress:
            await callback()


class RealtimeNotifier:
    """Send real-time notifications for workflow events"""
    
    def __init__(self):
        self.websocket_clients = []
        self.event_queue = asyncio.Queue()
        
    async def connect_client(self, websocket):
        """Connect a WebSocket client for notifications"""
        self.websocket_clients.append(websocket)
        
    async def disconnect_client(self, websocket):
        """Disconnect a WebSocket client"""
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)
    
    async def notify_phase_start(self, phase: int, description: str):
        """Notify phase start"""
        event = {
            'type': 'phase_start',
            'phase': phase,
            'description': description,
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast_event(event)
    
    async def notify_phase_complete(self, phase: int, success: bool, evidence: Any = None):
        """Notify phase completion"""
        event = {
            'type': 'phase_complete',
            'phase': phase,
            'success': success,
            'evidence': evidence,
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast_event(event)
    
    async def notify_agent_status(self, agent: str, status: str, details: Any = None):
        """Notify agent status change"""
        event = {
            'type': 'agent_status',
            'agent': agent,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        await self.broadcast_event(event)
    
    async def broadcast_event(self, event: Dict[str, Any]):
        """Broadcast event to all connected clients"""
        message = json.dumps(event)
        
        # Send to WebSocket clients
        disconnected = []
        for client in self.websocket_clients:
            try:
                await client.send(message)
            except:
                disconnected.append(client)
        
        # Remove disconnected clients
        for client in disconnected:
            await self.disconnect_client(client)
        
        # Add to event queue for other consumers
        await self.event_queue.put(event)
    
    async def get_next_event(self) -> Dict[str, Any]:
        """Get next event from queue"""
        return await self.event_queue.get()