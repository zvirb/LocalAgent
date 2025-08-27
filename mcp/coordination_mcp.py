#!/usr/bin/env python3
"""
Coordination MCP (Model Context Protocol) Server
Independent implementation for LocalAgent project
Provides agent coordination, messaging, and synchronization capabilities
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import uuid
from collections import defaultdict

@dataclass
class CoordinationMessage:
    """Message for inter-agent communication"""
    message_id: str
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    message_type: str
    content: Any
    timestamp: datetime
    priority: int = 0  # Higher priority messages processed first
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data

@dataclass 
class AgentRegistration:
    """Agent registration information"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    status: str  # idle, busy, offline
    registered_at: datetime
    last_heartbeat: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    current_task: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registration to dictionary"""
        data = asdict(self)
        data['registered_at'] = data['registered_at'].isoformat()
        data['last_heartbeat'] = data['last_heartbeat'].isoformat()
        return data

@dataclass
class WorkflowStream:
    """Workflow execution stream"""
    stream_id: str
    stream_name: str
    agents: List[str]
    status: str  # pending, active, completed, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stream to dictionary"""
        data = asdict(self)
        data['created_at'] = data['created_at'].isoformat()
        if data['completed_at']:
            data['completed_at'] = data['completed_at'].isoformat()
        return data

class MessageType(str, Enum):
    """Types of coordination messages"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    SYNC_REQUEST = "sync_request"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

class AgentStatus(str, Enum):
    """Agent status states"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class CoordinationMCP:
    """
    Coordination MCP Server
    Manages agent registration, messaging, and workflow coordination
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agents: Dict[str, AgentRegistration] = {}
        self.messages: Dict[str, List[CoordinationMessage]] = defaultdict(list)
        self.streams: Dict[str, WorkflowStream] = {}
        self.shared_scratch: Dict[str, Any] = {}  # Shared scratch pad
        self.locks: Dict[str, asyncio.Lock] = {}  # Resource locks
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # Topic subscriptions
        self.logger = logging.getLogger(__name__)
        self.state_file = Path(self.config.get('state_file', '.coordination_state.json'))
        self.heartbeat_timeout = timedelta(seconds=self.config.get('heartbeat_timeout', 60))
        
    async def initialize(self):
        """Initialize the Coordination MCP server"""
        self.logger.info("Initializing Coordination MCP Server")
        
        # Load saved state
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.shared_scratch = state.get('scratch', {})
                    self.logger.info(f"Loaded coordination state")
            except Exception as e:
                self.logger.warning(f"Could not load state: {e}")
        
        # Start heartbeat monitor
        asyncio.create_task(self._monitor_heartbeats())
        
        return True
    
    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> AgentRegistration:
        """Register a new agent"""
        now = datetime.now()
        
        registration = AgentRegistration(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or [],
            status=AgentStatus.IDLE.value,
            registered_at=now,
            last_heartbeat=now,
            metadata=metadata or {}
        )
        
        self.agents[agent_id] = registration
        self.logger.info(f"Registered agent {agent_id} of type {agent_type}")
        
        # Broadcast registration to other agents
        await self.broadcast_message(
            sender_id="system",
            message_type=MessageType.STATUS_UPDATE,
            content={
                'event': 'agent_registered',
                'agent_id': agent_id,
                'agent_type': agent_type
            }
        )
        
        return registration
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        if agent_id not in self.agents:
            return False
        
        del self.agents[agent_id]
        
        # Clean up messages
        if agent_id in self.messages:
            del self.messages[agent_id]
        
        # Remove from subscriptions
        for topic_subscribers in self.subscriptions.values():
            topic_subscribers.discard(agent_id)
        
        self.logger.info(f"Unregistered agent {agent_id}")
        
        # Broadcast unregistration
        await self.broadcast_message(
            sender_id="system",
            message_type=MessageType.STATUS_UPDATE,
            content={
                'event': 'agent_unregistered',
                'agent_id': agent_id
            }
        )
        
        return True
    
    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        content: Any,
        priority: int = 0,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Send a message to a specific agent"""
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        
        message = CoordinationMessage(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            timestamp=datetime.now(),
            priority=priority,
            metadata=metadata or {}
        )
        
        # Add to recipient's message queue
        self.messages[recipient_id].append(message)
        
        # Sort by priority (higher first) and timestamp
        self.messages[recipient_id].sort(
            key=lambda m: (-m.priority, m.timestamp)
        )
        
        self.logger.debug(f"Message {message_id} sent from {sender_id} to {recipient_id}")
        return message_id
    
    async def broadcast_message(
        self,
        sender_id: str,
        message_type: str,
        content: Any,
        exclude: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Broadcast a message to all agents"""
        message_id = f"broadcast_{uuid.uuid4().hex[:8]}"
        exclude = exclude or []
        
        message = CoordinationMessage(
            message_id=message_id,
            sender_id=sender_id,
            recipient_id=None,
            message_type=message_type,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Send to all registered agents except excluded
        for agent_id in self.agents:
            if agent_id not in exclude and agent_id != sender_id:
                self.messages[agent_id].append(message)
        
        self.logger.debug(f"Broadcast {message_id} from {sender_id}")
        return message_id
    
    async def get_messages(
        self,
        agent_id: str,
        limit: int = 10,
        message_type: Optional[str] = None
    ) -> List[CoordinationMessage]:
        """Get messages for an agent"""
        messages = self.messages.get(agent_id, [])
        
        # Filter by type if specified
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        
        # Return limited number of messages
        result = messages[:limit]
        
        # Remove retrieved messages from queue
        self.messages[agent_id] = messages[limit:]
        
        return result
    
    async def update_agent_status(
        self,
        agent_id: str,
        status: str,
        current_task: Optional[str] = None
    ) -> bool:
        """Update agent status"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        agent.status = status
        agent.last_heartbeat = datetime.now()
        agent.current_task = current_task
        
        self.logger.debug(f"Agent {agent_id} status updated to {status}")
        return True
    
    async def heartbeat(self, agent_id: str) -> bool:
        """Record agent heartbeat"""
        if agent_id not in self.agents:
            return False
        
        self.agents[agent_id].last_heartbeat = datetime.now()
        return True
    
    async def _monitor_heartbeats(self):
        """Monitor agent heartbeats and mark offline agents"""
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            now = datetime.now()
            for agent_id, agent in self.agents.items():
                if agent.status != AgentStatus.OFFLINE.value:
                    if now - agent.last_heartbeat > self.heartbeat_timeout:
                        agent.status = AgentStatus.OFFLINE.value
                        self.logger.warning(f"Agent {agent_id} marked offline (no heartbeat)")
                        
                        # Notify other agents
                        await self.broadcast_message(
                            sender_id="system",
                            message_type=MessageType.STATUS_UPDATE,
                            content={
                                'event': 'agent_offline',
                                'agent_id': agent_id
                            }
                        )
    
    async def create_stream(
        self,
        stream_name: str,
        agents: List[str],
        dependencies: List[str] = None,
        shared_context: Dict[str, Any] = None
    ) -> WorkflowStream:
        """Create a workflow stream"""
        stream_id = f"stream_{uuid.uuid4().hex[:8]}"
        
        stream = WorkflowStream(
            stream_id=stream_id,
            stream_name=stream_name,
            agents=agents,
            status="pending",
            created_at=datetime.now(),
            dependencies=dependencies or [],
            shared_context=shared_context or {}
        )
        
        self.streams[stream_id] = stream
        self.logger.info(f"Created stream {stream_id}: {stream_name}")
        
        # Notify agents in stream
        for agent_id in agents:
            await self.send_message(
                sender_id="system",
                recipient_id=agent_id,
                message_type=MessageType.TASK_REQUEST,
                content={
                    'stream_id': stream_id,
                    'stream_name': stream_name,
                    'action': 'join_stream'
                }
            )
        
        return stream
    
    async def update_stream_status(
        self,
        stream_id: str,
        status: str,
        completed: bool = False
    ) -> bool:
        """Update stream status"""
        if stream_id not in self.streams:
            return False
        
        stream = self.streams[stream_id]
        stream.status = status
        
        if completed:
            stream.completed_at = datetime.now()
        
        self.logger.info(f"Stream {stream_id} status updated to {status}")
        return True
    
    async def get_stream_context(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get shared context for a stream"""
        if stream_id not in self.streams:
            return None
        
        return self.streams[stream_id].shared_context
    
    async def update_stream_context(
        self,
        stream_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update shared context for a stream"""
        if stream_id not in self.streams:
            return False
        
        self.streams[stream_id].shared_context.update(updates)
        
        # Notify agents in stream
        for agent_id in self.streams[stream_id].agents:
            await self.send_message(
                sender_id="system",
                recipient_id=agent_id,
                message_type=MessageType.SYNC_REQUEST,
                content={
                    'stream_id': stream_id,
                    'context_updated': True,
                    'updates': list(updates.keys())
                }
            )
        
        return True
    
    async def set_scratch_data(self, key: str, value: Any) -> bool:
        """Set data in shared scratch pad"""
        self.shared_scratch[key] = value
        self.logger.debug(f"Scratch data set: {key}")
        return True
    
    async def get_scratch_data(self, key: str) -> Any:
        """Get data from shared scratch pad"""
        return self.shared_scratch.get(key)
    
    async def acquire_lock(self, resource_id: str, timeout: float = 5.0) -> bool:
        """Acquire a resource lock"""
        if resource_id not in self.locks:
            self.locks[resource_id] = asyncio.Lock()
        
        lock = self.locks[resource_id]
        
        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            self.logger.warning(f"Failed to acquire lock for {resource_id}")
            return False
    
    async def release_lock(self, resource_id: str) -> bool:
        """Release a resource lock"""
        if resource_id in self.locks:
            lock = self.locks[resource_id]
            if lock.locked():
                lock.release()
                return True
        return False
    
    async def subscribe_topic(self, agent_id: str, topic: str) -> bool:
        """Subscribe agent to a topic"""
        self.subscriptions[topic].add(agent_id)
        self.logger.debug(f"Agent {agent_id} subscribed to {topic}")
        return True
    
    async def unsubscribe_topic(self, agent_id: str, topic: str) -> bool:
        """Unsubscribe agent from a topic"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(agent_id)
            return True
        return False
    
    async def publish_to_topic(
        self,
        topic: str,
        sender_id: str,
        content: Any,
        metadata: Dict[str, Any] = None
    ) -> int:
        """Publish message to topic subscribers"""
        subscribers = self.subscriptions.get(topic, set())
        count = 0
        
        for agent_id in subscribers:
            if agent_id != sender_id:  # Don't send to self
                await self.send_message(
                    sender_id=sender_id,
                    recipient_id=agent_id,
                    message_type=MessageType.BROADCAST,
                    content=content,
                    metadata={'topic': topic, **(metadata or {})}
                )
                count += 1
        
        self.logger.debug(f"Published to {topic}, reached {count} agents")
        return count
    
    async def get_active_agents(self, agent_type: Optional[str] = None) -> List[AgentRegistration]:
        """Get list of active agents"""
        active = []
        
        for agent in self.agents.values():
            if agent.status != AgentStatus.OFFLINE.value:
                if agent_type is None or agent.agent_type == agent_type:
                    active.append(agent)
        
        return active
    
    async def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination statistics"""
        total_agents = len(self.agents)
        active_agents = sum(1 for a in self.agents.values() 
                          if a.status != AgentStatus.OFFLINE.value)
        busy_agents = sum(1 for a in self.agents.values() 
                         if a.status == AgentStatus.BUSY.value)
        
        total_messages = sum(len(msgs) for msgs in self.messages.values())
        active_streams = sum(1 for s in self.streams.values() 
                           if s.status == "active")
        
        return {
            'total_agents': total_agents,
            'active_agents': active_agents,
            'busy_agents': busy_agents,
            'idle_agents': active_agents - busy_agents,
            'offline_agents': total_agents - active_agents,
            'pending_messages': total_messages,
            'active_streams': active_streams,
            'total_streams': len(self.streams),
            'locked_resources': sum(1 for lock in self.locks.values() if lock.locked()),
            'topics': len(self.subscriptions),
            'scratch_keys': len(self.shared_scratch)
        }
    
    async def save_state(self):
        """Save current state to disk"""
        try:
            state = {
                'scratch': self.shared_scratch,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            self.logger.info(f"Saved coordination state to {self.state_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False

# Convenience function for standalone usage
async def create_coordination_server(config: Dict[str, Any] = None):
    """Create and initialize a Coordination MCP server"""
    server = CoordinationMCP(config)
    await server.initialize()
    return server

if __name__ == "__main__":
    # Test the Coordination MCP
    async def test():
        coord = await create_coordination_server()
        
        # Register some agents
        agent1 = await coord.register_agent(
            "agent_001",
            "research",
            capabilities=["search", "analysis"]
        )
        
        agent2 = await coord.register_agent(
            "agent_002", 
            "implementation",
            capabilities=["coding", "testing"]
        )
        
        # Send messages
        await coord.send_message(
            "agent_001",
            "agent_002",
            MessageType.TASK_REQUEST,
            {"task": "Implement authentication"}
        )
        
        # Create a stream
        stream = await coord.create_stream(
            "Authentication Implementation",
            agents=["agent_001", "agent_002"],
            shared_context={"project": "LocalAgent"}
        )
        
        # Get stats
        stats = await coord.get_coordination_stats()
        print("Coordination Stats:", json.dumps(stats, indent=2))
        
        # Save state
        await coord.save_state()
    
    asyncio.run(test())