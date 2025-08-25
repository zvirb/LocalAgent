"""
Base Provider Interface for LocalAgent
Defines the contract all LLM providers must implement
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator, Optional, List
from dataclasses import dataclass
import asyncio

@dataclass
class ModelInfo:
    """Information about an available model"""
    name: str
    provider: str
    context_length: int
    capabilities: List[str]  # ['chat', 'completion', 'function_calling', 'vision']
    cost_per_token: Optional[float] = None

@dataclass
class CompletionRequest:
    """Unified request format across providers"""
    messages: List[Dict[str, str]]
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    functions: Optional[List[Dict]] = None
    system_prompt: Optional[str] = None

@dataclass
class CompletionResponse:
    """Unified response format"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int]  # tokens used
    cost: Optional[float] = None
    citations: Optional[List[Dict]] = None  # For Perplexity

class BaseProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.replace('Provider', '')
        self.is_local = False
        self.requires_api_key = True
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider and verify connectivity"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """List available models from this provider"""
        pass
    
    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate a completion (non-streaming)"""
        pass
    
    @abstractmethod
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Generate a streaming completion"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health and status"""
        pass
    
    async def count_tokens(self, text: str, model: str) -> int:
        """Count tokens for the given text and model"""
        # Default implementation - providers can override
        return len(text.split()) * 1.3  # Rough estimate
    
    async def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost for token usage"""
        return 0.0  # Default for local providers