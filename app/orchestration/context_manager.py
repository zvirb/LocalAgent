"""
Context Manager for LocalAgent Integration
Manages context packages, token compression, and cross-session continuity
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import re

@dataclass
class ContextPackage:
    """Standardized context package with token management"""
    package_id: str
    package_type: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    token_count: int
    created_at: float
    expires_at: Optional[float] = None
    compressed: bool = False

class TokenCounter:
    """Approximate token counting for context management"""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """Rough token approximation (1 token ≈ 4 characters)"""
        # More sophisticated than simple word count
        # Account for whitespace, punctuation, code patterns
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Count tokens based on characters with adjustments
        base_count = len(text) // 4
        
        # Adjust for code patterns (more tokens)
        code_patterns = len(re.findall(r'[{}()[\]<>]', text))
        base_count += code_patterns * 0.3
        
        # Adjust for common words (fewer tokens)
        common_words = len(re.findall(r'\b(the|and|or|in|on|at|to|for|of|with|by)\b', text.lower()))
        base_count -= common_words * 0.2
        
        return max(1, int(base_count))
    
    @staticmethod
    def count_dict_tokens(data: Dict[str, Any]) -> int:
        """Count tokens in dictionary content"""
        return TokenCounter.count_tokens(json.dumps(data, separators=(',', ':')))

class ContextCompressor:
    """Intelligent context compression while preserving essential information"""
    
    def __init__(self):
        self.compression_strategies = {
            'strategic_context': self._compress_strategic,
            'technical_context': self._compress_technical,
            'frontend_context': self._compress_frontend,
            'security_context': self._compress_security,
            'performance_context': self._compress_performance,
            'database_context': self._compress_database
        }
    
    def compress_package(self, package: ContextPackage, target_tokens: int) -> ContextPackage:
        """Compress context package to target token count"""
        if package.token_count <= target_tokens:
            return package
            
        # Select compression strategy based on package type
        strategy = self.compression_strategies.get(
            package.package_type, 
            self._compress_generic
        )
        
        compressed_content = strategy(package.content, target_tokens)
        compressed_package = ContextPackage(
            package_id=package.package_id,
            package_type=package.package_type,
            content=compressed_content,
            metadata={
                **package.metadata,
                'original_tokens': package.token_count,
                'compression_ratio': target_tokens / package.token_count
            },
            token_count=TokenCounter.count_dict_tokens(compressed_content),
            created_at=package.created_at,
            expires_at=package.expires_at,
            compressed=True
        )
        
        return compressed_package
    
    def _compress_strategic(self, content: Dict[str, Any], target_tokens: int) -> Dict[str, Any]:
        """Compress strategic context - preserve high-level architecture"""
        return {
            'architecture_overview': content.get('architecture_overview', '')[:500],
            'key_decisions': content.get('key_decisions', [])[:3],
            'integration_points': content.get('integration_points', [])[:5],
            'success_criteria': content.get('success_criteria', [])[:3],
            'constraints': content.get('constraints', [])[:3],
            '_compression_note': 'Strategic context compressed - detailed implementation available in technical context'
        }
    
    def _compress_technical(self, content: Dict[str, Any], target_tokens: int) -> Dict[str, Any]:
        """Compress technical context - preserve implementation details"""
        return {
            'key_components': content.get('key_components', [])[:5],
            'implementation_patterns': content.get('implementation_patterns', [])[:3],
            'dependencies': content.get('dependencies', [])[:10],
            'critical_files': content.get('critical_files', [])[:8],
            'api_endpoints': content.get('api_endpoints', [])[:10],
            'configuration': self._compress_config(content.get('configuration', {})),
            '_compression_note': 'Technical details compressed - full codebase analysis available'
        }
    
    def _compress_frontend(self, content: Dict[str, Any], target_tokens: int) -> Dict[str, Any]:
        """Compress frontend context - preserve UI patterns"""
        return {
            'ui_components': content.get('ui_components', [])[:8],
            'styling_approach': content.get('styling_approach', ''),
            'state_management': content.get('state_management', ''),
            'routing_config': content.get('routing_config', {}),
            'key_interactions': content.get('key_interactions', [])[:5],
            '_compression_note': 'UI details compressed - component library available'
        }
    
    def _compress_security(self, content: Dict[str, Any], target_tokens: int) -> Dict[str, Any]:
        """Compress security context - preserve critical vulnerabilities"""
        return {
            'critical_vulnerabilities': content.get('critical_vulnerabilities', [])[:5],
            'auth_patterns': content.get('auth_patterns', [])[:3],
            'security_headers': content.get('security_headers', {}),
            'input_validation': content.get('input_validation', [])[:5],
            'mitigation_strategies': content.get('mitigation_strategies', [])[:5],
            '_compression_note': 'Security analysis compressed - full audit available'
        }
    
    def _compress_performance(self, content: Dict[str, Any], target_tokens: int) -> Dict[str, Any]:
        """Compress performance context - preserve bottlenecks"""
        return {
            'bottlenecks': content.get('bottlenecks', [])[:5],
            'performance_metrics': content.get('performance_metrics', {})[:5],
            'optimization_opportunities': content.get('optimization_opportunities', [])[:5],
            'resource_usage': content.get('resource_usage', {}),
            '_compression_note': 'Performance data compressed - detailed metrics available'
        }
    
    def _compress_database(self, content: Dict[str, Any], target_tokens: int) -> Dict[str, Any]:
        """Compress database context - preserve schema essentials"""
        return {
            'key_tables': content.get('key_tables', [])[:10],
            'relationships': content.get('relationships', [])[:8],
            'indexes': content.get('indexes', [])[:5],
            'query_patterns': content.get('query_patterns', [])[:5],
            'migrations': content.get('migrations', [])[:3],
            '_compression_note': 'Database schema compressed - full DDL available'
        }
    
    def _compress_generic(self, content: Dict[str, Any], target_tokens: int) -> Dict[str, Any]:
        """Generic compression strategy"""
        # Keep essential keys and truncate content
        essential_keys = ['summary', 'key_points', 'findings', 'recommendations', 'status']
        compressed = {}
        
        for key in essential_keys:
            if key in content:
                value = content[key]
                if isinstance(value, list):
                    compressed[key] = value[:5]
                elif isinstance(value, str):
                    compressed[key] = value[:500]
                else:
                    compressed[key] = value
                    
        # Add compression metadata
        compressed['_compression_note'] = 'Generic compression applied'
        compressed['_available_keys'] = list(content.keys())
        
        return compressed
    
    def _compress_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Compress configuration data"""
        # Keep only essential config keys
        essential_config = {}
        important_keys = ['host', 'port', 'database', 'timeout', 'max_connections', 'auth_type']
        
        for key, value in config.items():
            if key in important_keys or len(str(value)) < 50:
                essential_config[key] = value
                
        return essential_config

class ContextManager:
    """
    Comprehensive context management for workflow execution
    Handles package creation, compression, storage, and retrieval
    """
    
    def __init__(self, config: Dict[str, Any], mcp_integration=None):
        self.config = config
        self.mcp_integration = mcp_integration
        self.packages: Dict[str, ContextPackage] = {}
        self.compressor = ContextCompressor()
        self.logger = logging.getLogger(__name__)
        
        # Token limits from config
        self.token_limits = {
            'strategic_context': config.get('strategic_context_tokens', 3000),
            'technical_context': config.get('technical_context_tokens', 4000),
            'frontend_context': config.get('frontend_context_tokens', 3000),
            'security_context': config.get('security_context_tokens', 3000),
            'performance_context': config.get('performance_context_tokens', 3000),
            'database_context': config.get('database_context_tokens', 3500),
            'default': config.get('default_context_tokens', 4000)
        }
    
    async def create_context_package(
        self,
        package_id: str,
        package_type: str,
        content: Dict[str, Any],
        metadata: Dict[str, Any] = None,
        expires_in: Optional[float] = None
    ) -> ContextPackage:
        """Create a new context package with automatic token management"""
        
        metadata = metadata or {}
        token_count = TokenCounter.count_dict_tokens(content)
        
        # Determine token limit for this package type
        token_limit = self.token_limits.get(package_type, self.token_limits['default'])
        
        # Create initial package
        package = ContextPackage(
            package_id=package_id,
            package_type=package_type,
            content=content,
            metadata=metadata,
            token_count=token_count,
            created_at=time.time(),
            expires_at=time.time() + expires_in if expires_in else None
        )
        
        # Compress if needed
        if token_count > token_limit:
            package = self.compressor.compress_package(package, token_limit)
            self.logger.info(f"Compressed package {package_id} from {token_count} to {package.token_count} tokens")
        
        # Store locally
        self.packages[package_id] = package
        
        # Store in MCP if available
        if self.mcp_integration:
            await self.mcp_integration.store_context_package(
                package_id, 
                asdict(package),
                token_limit
            )
        
        return package
    
    async def retrieve_context_package(self, package_id: str) -> Optional[ContextPackage]:
        """Retrieve a context package by ID"""
        # Try local cache first
        if package_id in self.packages:
            package = self.packages[package_id]
            
            # Check expiration
            if package.expires_at and time.time() > package.expires_at:
                del self.packages[package_id]
                return None
                
            return package
        
        # Try MCP storage
        if self.mcp_integration:
            entity = await self.mcp_integration.memory_mcp.retrieve_entity(package_id)
            if entity:
                try:
                    package_data = json.loads(entity.content)
                    package = ContextPackage(**package_data)
                    self.packages[package_id] = package  # Cache locally
                    return package
                except Exception as e:
                    self.logger.error(f"Failed to deserialize package {package_id}: {e}")
        
        return None
    
    async def store_context_package(
        self, 
        package_id: str, 
        content: Dict[str, Any],
        max_tokens: int = 4000,
        package_type: str = 'generic'
    ) -> bool:
        """Store context package with token management"""
        try:
            package = await self.create_context_package(
                package_id=package_id,
                package_type=package_type,
                content=content,
                metadata={'max_tokens': max_tokens}
            )
            
            return package.token_count <= max_tokens
            
        except Exception as e:
            self.logger.error(f"Failed to store context package {package_id}: {e}")
            return False
    
    async def create_agent_context(
        self,
        agent_name: str,
        workflow_context: Dict[str, Any],
        agent_specific_data: Dict[str, Any],
        max_tokens: int = 4000
    ) -> ContextPackage:
        """Create agent-specific context package"""
        
        # Build agent context from workflow and agent-specific data
        context_content = {
            'agent_name': agent_name,
            'workflow_context': {
                'current_phase': workflow_context.get('current_phase'),
                'workflow_id': workflow_context.get('workflow_id'),
                'user_request': workflow_context.get('user_request'),
                'success_criteria': workflow_context.get('success_criteria', [])
            },
            'agent_data': agent_specific_data,
            'context_created': time.time()
        }
        
        package_id = f"agent_{agent_name}_{int(time.time())}"
        
        return await self.create_context_package(
            package_id=package_id,
            package_type='agent_context',
            content=context_content,
            metadata={'agent_name': agent_name, 'max_tokens': max_tokens},
            expires_in=3600  # 1 hour expiration
        )
    
    async def merge_context_packages(self, package_ids: List[str], merged_id: str) -> Optional[ContextPackage]:
        """Merge multiple context packages into one"""
        packages = []
        
        for package_id in package_ids:
            package = await self.retrieve_context_package(package_id)
            if package:
                packages.append(package)
        
        if not packages:
            return None
        
        # Merge content
        merged_content = {
            'merged_from': package_ids,
            'packages': [
                {
                    'id': p.package_id,
                    'type': p.package_type,
                    'content': p.content,
                    'compressed': p.compressed
                }
                for p in packages
            ]
        }
        
        # Create merged package with higher token limit
        return await self.create_context_package(
            package_id=merged_id,
            package_type='merged_context',
            content=merged_content,
            metadata={'source_packages': len(packages)},
            expires_in=7200  # 2 hour expiration
        )
    
    async def get_workflow_context_summary(self, workflow_id: str) -> Dict[str, Any]:
        """Get summary of all context packages for a workflow"""
        workflow_packages = []
        
        for package in self.packages.values():
            if workflow_id in package.package_id:
                workflow_packages.append({
                    'id': package.package_id,
                    'type': package.package_type,
                    'tokens': package.token_count,
                    'compressed': package.compressed,
                    'created': package.created_at,
                    'expires': package.expires_at
                })
        
        total_tokens = sum(p['tokens'] for p in workflow_packages)
        
        return {
            'workflow_id': workflow_id,
            'total_packages': len(workflow_packages),
            'total_tokens': total_tokens,
            'packages': workflow_packages,
            'summary_created': time.time()
        }
    
    async def cleanup_expired_packages(self) -> int:
        """Remove expired packages"""
        expired_ids = []
        current_time = time.time()
        
        for package_id, package in self.packages.items():
            if package.expires_at and current_time > package.expires_at:
                expired_ids.append(package_id)
        
        for package_id in expired_ids:
            del self.packages[package_id]
        
        if expired_ids:
            self.logger.info(f"Cleaned up {len(expired_ids)} expired context packages")
        
        return len(expired_ids)
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get context storage statistics"""
        package_types = {}
        total_tokens = 0
        compressed_count = 0
        
        for package in self.packages.values():
            pkg_type = package.package_type
            if pkg_type not in package_types:
                package_types[pkg_type] = {'count': 0, 'tokens': 0}
            
            package_types[pkg_type]['count'] += 1
            package_types[pkg_type]['tokens'] += package.token_count
            total_tokens += package.token_count
            
            if package.compressed:
                compressed_count += 1
        
        return {
            'total_packages': len(self.packages),
            'total_tokens': total_tokens,
            'compressed_packages': compressed_count,
            'compression_rate': compressed_count / len(self.packages) if self.packages else 0,
            'package_types': package_types,
            'token_limits': self.token_limits
        }