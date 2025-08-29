"""
Agent Provider Adapter Bridge for LocalAgent Integration
Connects LocalAgent's provider system with agent orchestration
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import time

@dataclass
class AgentRequest:
    """Standardized agent request format"""
    agent_type: str
    subagent_type: str
    description: str
    prompt: str
    context: Dict[str, Any]
    max_tokens: int = 4000
    temperature: float = 0.1
    stream: bool = False
    provider_preference: Optional[str] = None

@dataclass
class AgentResponse:
    """Standardized agent response format"""
    success: bool
    content: str
    metadata: Dict[str, Any]
    evidence: List[Dict[str, Any]]
    execution_time: float
    token_usage: Dict[str, int]
    provider_used: str
    error: Optional[str] = None

class AgentProviderAdapter:
    """
    Bridge between LocalAgent's LLM providers and agent system
    Provides unified interface for agent orchestration with local/remote flexibility
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.provider_manager = None
        self.agents_registry = {}
        self.execution_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'provider_usage': {}
        }
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration for agent-provider integration"""
        default_config = {
            'providers': {
                'ollama': {
                    'base_url': 'http://localhost:11434',
                    'default_model': 'llama3.1:latest',
                    'timeout': 120
                }
            },
            'agents': {
                'max_parallel': 10,
                'default_tokens': 4000,
                'context_compression_threshold': 3500
            },
            'workflow': {
                'enable_evidence_collection': True,
                'enable_parallel_execution': True,
                'max_retries': 2
            }
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
                
        return default_config
    
    async def initialize(self, provider_manager):
        """Initialize the adapter with a provider manager"""
        self.provider_manager = provider_manager
        await self._load_agents_registry()
        self.logger.info("Agent Provider Adapter initialized successfully")
        
    async def _load_agents_registry(self):
        """Load and validate agents registry from local agents directory"""
        agents_dir = Path("agents")
        if not agents_dir.exists():
            agents_dir = Path("/mnt/7ac3bfed-9d8e-4829-b134-b5e98ff7c013/programming/LocalProgramming/agents")
            
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                agent_name = agent_file.stem
                try:
                    content = agent_file.read_text()
                    # Extract frontmatter
                    if content.startswith('---\n'):
                        end_idx = content.find('\n---\n', 4)
                        if end_idx > 0:
                            frontmatter = yaml.safe_load(content[4:end_idx])
                            if 'name' in frontmatter and 'description' in frontmatter:
                                self.agents_registry[agent_name] = {
                                    'name': frontmatter['name'],
                                    'description': frontmatter['description'],
                                    'content': content[end_idx + 5:],
                                    'file_path': str(agent_file)
                                }
                except Exception as e:
                    self.logger.warning(f"Failed to load agent {agent_name}: {e}")
        
        self.logger.info(f"Loaded {len(self.agents_registry)} agents into registry")
    
    async def execute_agent(self, request: AgentRequest) -> AgentResponse:
        """Execute an agent request through the provider system"""
        start_time = time.time()
        self.execution_stats['total_requests'] += 1
        
        try:
            # Get agent definition
            agent_spec = self.agents_registry.get(request.subagent_type)
            if not agent_spec:
                raise ValueError(f"Agent '{request.subagent_type}' not found in registry")
            
            # Build agent prompt
            agent_prompt = self._build_agent_prompt(agent_spec, request)
            
            # Create completion request
            completion_request = self._create_completion_request(agent_prompt, request)
            
            # Execute through provider manager
            response = await self.provider_manager.complete_with_fallback(
                completion_request, 
                preferred_provider=request.provider_preference
            )
            
            # Process response
            agent_response = self._process_agent_response(response, start_time)
            
            self.execution_stats['successful_requests'] += 1
            self._update_provider_stats(agent_response.provider_used)
            
            return agent_response
            
        except Exception as e:
            self.execution_stats['failed_requests'] += 1
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=False,
                content="",
                metadata={'agent_type': request.subagent_type},
                evidence=[],
                execution_time=execution_time,
                token_usage={'total_tokens': 0},
                provider_used="",
                error=str(e)
            )
    
    def _build_agent_prompt(self, agent_spec: Dict[str, Any], request: AgentRequest) -> str:
        """Build comprehensive agent prompt with context and instructions"""
        prompt_parts = [
            f"# {agent_spec['name']} Agent",
            f"## Description: {agent_spec['description']}",
            "",
            "## Agent Specification:",
            agent_spec['content'],
            "",
            "## Current Task:",
            f"**Task Type**: {request.agent_type}",
            f"**Description**: {request.description}",
            f"**Specific Instructions**: {request.prompt}",
            "",
            "## Context Information:",
            json.dumps(request.context, indent=2),
            "",
            "## Requirements:",
            "- Provide specific, actionable results",
            "- Include concrete evidence where applicable", 
            "- Focus on the task boundaries defined in the agent specification",
            "- Return structured output with clear success/failure indicators",
            "- Optimize for token efficiency while maintaining completeness",
            "",
            "## Response Format:",
            "Please structure your response with:",
            "1. **Summary**: Brief overview of actions taken",
            "2. **Results**: Specific findings or outputs",
            "3. **Evidence**: Concrete proof of work (file paths, commands, etc.)",
            "4. **Status**: SUCCESS or FAILURE with brief reason",
            "",
            "Begin your specialized agent work:"
        ]
        
        return "\n".join(prompt_parts)
    
    def _create_completion_request(self, prompt: str, request: AgentRequest):
        """Create a completion request for the provider system"""
        # Import here to avoid circular imports
        from app.llm_providers.base_provider import CompletionRequest
        
        return CompletionRequest(
            prompt=prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            model=None  # Let provider choose best model
        )
    
    def _process_agent_response(self, response, start_time: float) -> AgentResponse:
        """Process provider response into standardized agent response"""
        execution_time = time.time() - start_time
        
        # Extract evidence from response content
        evidence = self._extract_evidence(response.content)
        
        # Determine success based on content analysis
        success = self._assess_response_success(response.content)
        
        return AgentResponse(
            success=success,
            content=response.content,
            metadata={
                'model_used': response.model,
                'finish_reason': getattr(response, 'finish_reason', 'unknown')
            },
            evidence=evidence,
            execution_time=execution_time,
            token_usage={
                'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                'total_tokens': response.usage.total_tokens if response.usage else 0
            },
            provider_used=getattr(response, 'provider', 'unknown')
        )
    
    def _extract_evidence(self, content: str) -> List[Dict[str, Any]]:
        """Extract evidence markers from agent response"""
        evidence = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Look for evidence patterns
            if any(marker in line.lower() for marker in ['evidence:', '**evidence**', 'proof:', 'file:', 'command:']):
                evidence.append({
                    'line_number': i + 1,
                    'content': line.strip(),
                    'type': 'text_evidence'
                })
                
        return evidence
    
    def _assess_response_success(self, content: str) -> bool:
        """Assess if the agent response indicates success"""
        content_lower = content.lower()
        
        # Explicit success indicators
        if any(indicator in content_lower for indicator in ['status: success', 'success:', 'completed successfully']):
            return True
            
        # Explicit failure indicators
        if any(indicator in content_lower for indicator in ['status: failure', 'failed:', 'error:', 'unable to']):
            return False
            
        # Default to success if response has substantial content
        return len(content.strip()) > 100
    
    def _update_provider_stats(self, provider_name: str):
        """Update provider usage statistics"""
        if provider_name not in self.execution_stats['provider_usage']:
            self.execution_stats['provider_usage'][provider_name] = 0
        self.execution_stats['provider_usage'][provider_name] += 1
        
        # Update average response time
        total_requests = self.execution_stats['successful_requests']
        if total_requests > 0:
            # This is a simplified average - in production would use running average
            pass
    
    async def execute_parallel_agents(self, requests: List[AgentRequest]) -> List[AgentResponse]:
        """Execute multiple agents in parallel"""
        max_parallel = self.config['agents']['max_parallel']
        
        # Create semaphore to limit concurrent executions
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def bounded_execute(request):
            async with semaphore:
                return await self.execute_agent(request)
        
        # Execute all requests in parallel
        tasks = [bounded_execute(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error responses
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                processed_responses.append(AgentResponse(
                    success=False,
                    content="",
                    metadata={'agent_type': requests[i].subagent_type},
                    evidence=[],
                    execution_time=0.0,
                    token_usage={'total_tokens': 0},
                    provider_used="",
                    error=str(response)
                ))
            else:
                processed_responses.append(response)
                
        return processed_responses
    
    def get_available_agents(self) -> List[Dict[str, str]]:
        """Get list of available agents"""
        return [
            {
                'name': agent_name,
                'description': spec['description']
            }
            for agent_name, spec in self.agents_registry.items()
        ]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.execution_stats.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of the adapter and underlying providers"""
        health_data = {
            'adapter_healthy': True,
            'agents_loaded': len(self.agents_registry),
            'execution_stats': self.execution_stats,
            'providers': {}
        }
        
        if self.provider_manager:
            provider_health = await self.provider_manager.health_check_all()
            health_data['providers'] = provider_health
            
            # Determine overall health
            healthy_providers = sum(1 for p in provider_health.values() if p.get('healthy', False))
            health_data['healthy_providers'] = healthy_providers
            health_data['adapter_healthy'] = healthy_providers > 0
            
        return health_data