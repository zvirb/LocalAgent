"""
MCP (Model Context Protocol) Integration for LocalAgent + UnifiedWorkflow
Provides Memory MCP, Redis MCP, and Orchestration MCP server connections
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import aioredis
from datetime import datetime, timedelta

@dataclass
class MCPEntity:
    """Standardized entity for Memory MCP storage"""
    entity_type: str
    entity_id: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None

class MemoryMCP:
    """
    Memory MCP integration for persistent context and evidence storage
    Handles entity storage with retention policies and cross-session continuity
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.entities: Dict[str, MCPEntity] = {}
        self.retention_policies = {
            'agent-output': timedelta(days=30),
            'context-package': timedelta(days=7),
            'documentation': None,  # Indefinite
            'workflow-state': timedelta(days=14),
            'security-audit': timedelta(days=90),
            'deployment-evidence': timedelta(days=90),
            'todo-context': timedelta(days=365)  # Long retention for todos
        }
        self.logger = logging.getLogger(__name__)
        
    async def store_entity(
        self, 
        entity_type: str, 
        entity_id: str, 
        content: Union[str, Dict[str, Any]], 
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Store an entity with automatic retention policy"""
        try:
            # Convert content to string if needed
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)
                
            metadata = metadata or {}
            created_at = datetime.now()
            
            # Apply retention policy
            expires_at = None
            if entity_type in self.retention_policies:
                retention_period = self.retention_policies[entity_type]
                if retention_period:
                    expires_at = created_at + retention_period
            
            entity = MCPEntity(
                entity_type=entity_type,
                entity_id=entity_id,
                content=content,
                metadata=metadata,
                created_at=created_at,
                expires_at=expires_at
            )
            
            self.entities[entity_id] = entity
            self.logger.debug(f"Stored entity {entity_id} of type {entity_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store entity {entity_id}: {e}")
            return False
    
    async def retrieve_entity(self, entity_id: str) -> Optional[MCPEntity]:
        """Retrieve an entity by ID"""
        entity = self.entities.get(entity_id)
        
        if entity and self._is_expired(entity):
            # Remove expired entity
            del self.entities[entity_id]
            return None
            
        return entity
    
    async def search_entities(
        self, 
        entity_type: Optional[str] = None,
        content_pattern: Optional[str] = None,
        metadata_filter: Dict[str, Any] = None,
        limit: int = 100
    ) -> List[MCPEntity]:
        """Search entities with filters"""
        results = []
        metadata_filter = metadata_filter or {}
        
        for entity in self.entities.values():
            # Skip expired entities
            if self._is_expired(entity):
                continue
                
            # Apply filters
            if entity_type and entity.entity_type != entity_type:
                continue
                
            if content_pattern and content_pattern.lower() not in entity.content.lower():
                continue
                
            # Check metadata filters
            metadata_match = True
            for key, value in metadata_filter.items():
                if key not in entity.metadata or entity.metadata[key] != value:
                    metadata_match = False
                    break
                    
            if not metadata_match:
                continue
                
            results.append(entity)
            
            if len(results) >= limit:
                break
                
        return results
    
    async def cleanup_expired(self) -> int:
        """Remove expired entities and return count"""
        expired_ids = []
        
        for entity_id, entity in self.entities.items():
            if self._is_expired(entity):
                expired_ids.append(entity_id)
        
        for entity_id in expired_ids:
            del self.entities[entity_id]
            
        if expired_ids:
            self.logger.info(f"Cleaned up {len(expired_ids)} expired entities")
            
        return len(expired_ids)
    
    def _is_expired(self, entity: MCPEntity) -> bool:
        """Check if entity is expired"""
        if not entity.expires_at:
            return False
        return datetime.now() > entity.expires_at
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        entity_counts = {}
        total_size = 0
        
        for entity in self.entities.values():
            entity_type = entity.entity_type
            if entity_type not in entity_counts:
                entity_counts[entity_type] = 0
            entity_counts[entity_type] += 1
            total_size += len(entity.content)
            
        return {
            'total_entities': len(self.entities),
            'entity_counts': entity_counts,
            'total_size_bytes': total_size,
            'retention_policies': {k: str(v) if v else 'indefinite' for k, v in self.retention_policies.items()}
        }

class RedisMCP:
    """
    Redis MCP integration for real-time coordination and scratch pad functionality
    Handles agent coordination, notifications, and timeline tracking
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_url = config.get('redis_url', 'redis://localhost:6379')
        self.redis: Optional[aioredis.Redis] = None
        self.logger = logging.getLogger(__name__)
        
        # Namespace organization
        self.namespaces = {
            'coord': 'Agent coordination data',
            'scratch': 'Shared workspace information', 
            'notify': 'Agent notifications',
            'timeline': 'Chronological event tracking',
            'state': 'Workflow state management'
        }
        
    async def initialize(self) -> bool:
        """Initialize Redis connection"""
        try:
            self.redis = aioredis.from_url(self.redis_url, encoding='utf-8', decode_responses=True)
            # Test connection
            await self.redis.ping()
            self.logger.info("Redis MCP connection established")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def set_coordination_data(self, key: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Set coordination data with TTL"""
        try:
            full_key = f"coord:{key}"
            await self.redis.setex(full_key, ttl, json.dumps(data))
            return True
        except Exception as e:
            self.logger.error(f"Failed to set coordination data {key}: {e}")
            return False
    
    async def get_coordination_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get coordination data"""
        try:
            full_key = f"coord:{key}"
            data = await self.redis.get(full_key)
            return json.loads(data) if data else None
        except Exception as e:
            self.logger.error(f"Failed to get coordination data {key}: {e}")
            return None
    
    async def update_scratch_pad(self, stream_name: str, data: Dict[str, Any]) -> bool:
        """Update shared scratch pad for stream coordination"""
        try:
            key = f"scratch:{stream_name}"
            # Merge with existing data
            existing = await self.redis.get(key)
            if existing:
                existing_data = json.loads(existing)
                existing_data.update(data)
                data = existing_data
            
            await self.redis.setex(key, 1800, json.dumps(data))  # 30 minute TTL
            return True
        except Exception as e:
            self.logger.error(f"Failed to update scratch pad {stream_name}: {e}")
            return False
    
    async def get_scratch_pad(self, stream_name: str) -> Optional[Dict[str, Any]]:
        """Get scratch pad data for stream"""
        try:
            key = f"scratch:{stream_name}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            self.logger.error(f"Failed to get scratch pad {stream_name}: {e}")
            return None
    
    async def publish_notification(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish notification to agents"""
        try:
            full_channel = f"notify:{channel}"
            await self.redis.publish(full_channel, json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"Failed to publish notification to {channel}: {e}")
            return False
    
    async def add_timeline_event(self, workflow_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Add event to workflow timeline"""
        try:
            timeline_key = f"timeline:{workflow_id}"
            event = {
                'timestamp': time.time(),
                'event_type': event_type,
                'data': data
            }
            await self.redis.lpush(timeline_key, json.dumps(event))
            await self.redis.expire(timeline_key, 86400)  # 24 hour TTL
            return True
        except Exception as e:
            self.logger.error(f"Failed to add timeline event: {e}")
            return False
    
    async def get_timeline(self, workflow_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get workflow timeline events"""
        try:
            timeline_key = f"timeline:{workflow_id}"
            events = await self.redis.lrange(timeline_key, 0, limit - 1)
            return [json.loads(event) for event in events]
        except Exception as e:
            self.logger.error(f"Failed to get timeline: {e}")
            return []
    
    async def set_workflow_state(self, workflow_id: str, state: Dict[str, Any]) -> bool:
        """Set workflow state"""
        try:
            key = f"state:{workflow_id}"
            await self.redis.setex(key, 7200, json.dumps(state))  # 2 hour TTL
            return True
        except Exception as e:
            self.logger.error(f"Failed to set workflow state: {e}")
            return False
    
    async def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow state"""
        try:
            key = f"state:{workflow_id}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            self.logger.error(f"Failed to get workflow state: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            if not self.redis:
                return {'healthy': False, 'error': 'Not initialized'}
            
            latency = await self.redis.ping()
            info = await self.redis.info()
            
            return {
                'healthy': True,
                'latency_ms': latency * 1000 if isinstance(latency, (int, float)) else 0,
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'redis_version': info.get('redis_version', 'unknown')
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}


class ComputerControlMCP:
    """Manage external computer-control-mcp server"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.logger = logging.getLogger(__name__)

    async def start(self) -> bool:
        command = self.config.get('command', 'computer-control-mcp')
        args = self.config.get('args', [])
        try:
            self.process = await asyncio.create_subprocess_exec(
                command, *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            self.logger.info('Computer Control MCP server started')
            return True
        except Exception as e:
            self.logger.error(f'Failed to start Computer Control MCP: {e}')
            return False

    async def stop(self) -> None:
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.logger.info('Computer Control MCP server stopped')

class OrchestrationMCP:
    """
    Orchestration MCP for workflow management and agent coordination
    Combines Memory and Redis MCP functionality for complete orchestration support
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.memory_mcp = MemoryMCP(config.get('memory', {}))
        self.redis_mcp = RedisMCP(config.get('redis', {}))
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self) -> bool:
        """Initialize all MCP servers"""
        redis_success = await self.redis_mcp.initialize()
        
        # Memory MCP is always available (in-memory)
        memory_success = True
        
        self.logger.info(f"OrchestrationMCP initialized - Redis: {redis_success}, Memory: {memory_success}")
        return redis_success  # Redis is critical for coordination
    
    async def store_context_package(self, package_id: str, content: Dict[str, Any], max_tokens: int = 4000) -> bool:
        """Store context package with token compression"""
        try:
            # Convert to string and check token count (rough approximation)
            content_str = json.dumps(content, indent=2)
            estimated_tokens = len(content_str.split())
            
            # Compress if needed
            if estimated_tokens > max_tokens:
                content = self._compress_context_package(content, max_tokens)
                content_str = json.dumps(content, indent=2)
            
            # Store in Memory MCP
            success = await self.memory_mcp.store_entity(
                entity_type='context-package',
                entity_id=package_id,
                content=content_str,
                metadata={
                    'estimated_tokens': min(estimated_tokens, max_tokens),
                    'compressed': estimated_tokens > max_tokens
                }
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to store context package {package_id}: {e}")
            return False
    
    async def store_agent_output(self, workflow_id: str, agent_name: str, output: Dict[str, Any]) -> bool:
        """Store agent output for cross-session continuity"""
        entity_id = f"{workflow_id}_{agent_name}_{int(time.time())}"
        
        return await self.memory_mcp.store_entity(
            entity_type='agent-output',
            entity_id=entity_id,
            content=output,
            metadata={
                'workflow_id': workflow_id,
                'agent_name': agent_name,
                'timestamp': time.time()
            }
        )
    
    async def store_evidence(self, workflow_id: str, evidence: List[Dict[str, Any]]) -> bool:
        """Store workflow evidence"""
        entity_id = f"{workflow_id}_evidence_{int(time.time())}"
        
        return await self.memory_mcp.store_entity(
            entity_type='deployment-evidence',
            entity_id=entity_id,
            content={'evidence': evidence},
            metadata={
                'workflow_id': workflow_id,
                'evidence_count': len(evidence),
                'timestamp': time.time()
            }
        )
    
    async def coordinate_agents(self, workflow_id: str, coordination_data: Dict[str, Any]) -> bool:
        """Coordinate agents through Redis"""
        return await self.redis_mcp.set_coordination_data(
            f"workflow-{workflow_id}",
            coordination_data,
            ttl=3600
        )
    
    async def update_agent_status(self, agent_name: str, status: Dict[str, Any]) -> bool:
        """Update agent status for monitoring"""
        return await self.redis_mcp.set_coordination_data(
            f"agent-{agent_name}-status",
            status,
            ttl=300  # 5 minute TTL
        )
    
    async def get_agent_coordination(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get agent coordination data"""
        return await self.redis_mcp.get_coordination_data(f"workflow-{workflow_id}")
    
    async def log_workflow_event(self, workflow_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Log workflow event to timeline"""
        return await self.redis_mcp.add_timeline_event(workflow_id, event_type, data)
    
    def _compress_context_package(self, content: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
        """Compress context package to fit token limits"""
        # Simple compression strategy - prioritize critical fields
        compressed = {
            'summary': content.get('summary', ''),
            'key_findings': content.get('key_findings', [])[:5],  # Limit findings
            'metadata': content.get('metadata', {})
        }
        
        # Add compressed version indicator
        compressed['_compressed'] = True
        compressed['_original_size'] = len(json.dumps(content))
        
        return compressed
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all MCP servers"""
        redis_health = await self.redis_mcp.health_check()
        memory_stats = await self.memory_mcp.get_storage_stats()
        
        return {
            'overall_healthy': redis_health['healthy'],
            'redis': redis_health,
            'memory': {
                'healthy': True,
                'stats': memory_stats
            }
        }