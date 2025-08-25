"""
OpenAI Provider for LocalAgent
Interfaces with OpenAI API for GPT models
"""

import os
from typing import Dict, Any, AsyncIterator, List, Optional
from openai import AsyncOpenAI
from .base_provider import BaseProvider, ModelInfo, CompletionRequest, CompletionResponse

class OpenAIProvider(BaseProvider):
    """Provider for OpenAI GPT models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        self.client = None
        self.is_local = False
        self.requires_api_key = True
        
        # Model pricing (per 1K tokens)
        self.pricing = {
            'gpt-4o': {'input': 0.005, 'output': 0.015},
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015}
        }
    
    async def initialize(self) -> bool:
        """Initialize OpenAI client"""
        if not self.api_key:
            return False
        
        try:
            self.client = AsyncOpenAI(api_key=self.api_key)
            # Test connection
            models = await self.client.models.list()
            return True
        except Exception as e:
            print(f"Failed to initialize OpenAI: {e}")
            return False
    
    async def list_models(self) -> List[ModelInfo]:
        """List available OpenAI models"""
        models = []
        model_list = [
            ('gpt-4o', 128000, ['chat', 'completion', 'function_calling', 'vision']),
            ('gpt-4o-mini', 128000, ['chat', 'completion', 'function_calling']),
            ('gpt-4-turbo', 128000, ['chat', 'completion', 'function_calling', 'vision']),
            ('gpt-3.5-turbo', 16385, ['chat', 'completion', 'function_calling'])
        ]
        
        for name, context, capabilities in model_list:
            models.append(ModelInfo(
                name=name,
                provider='openai',
                context_length=context,
                capabilities=capabilities,
                cost_per_token=self.pricing.get(name, {}).get('input', 0)
            ))
        
        return models
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion using OpenAI"""
        if not self.client:
            await self.initialize()
        
        response = await self.client.chat.completions.create(
            model=request.model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False
        )
        
        usage = response.usage
        cost = self._calculate_cost(
            usage.prompt_tokens, 
            usage.completion_tokens,
            request.model
        )
        
        return CompletionResponse(
            content=response.choices[0].message.content,
            model=request.model,
            provider='openai',
            usage={
                'prompt_tokens': usage.prompt_tokens,
                'completion_tokens': usage.completion_tokens,
                'total_tokens': usage.total_tokens
            },
            cost=cost
        )
    
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion from OpenAI"""
        if not self.client:
            await self.initialize()
        
        stream = await self.client.chat.completions.create(
            model=request.model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API health"""
        try:
            is_healthy = await self.initialize()
            return {
                'healthy': is_healthy,
                'provider': 'openai',
                'api_key_set': bool(self.api_key),
                'models_available': 4 if is_healthy else 0
            }
        except Exception as e:
            return {
                'healthy': False,
                'provider': 'openai',
                'error': str(e)
            }
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate cost for token usage"""
        if model not in self.pricing:
            return 0.0
        
        input_cost = (input_tokens / 1000) * self.pricing[model]['input']
        output_cost = (output_tokens / 1000) * self.pricing[model]['output']
        return input_cost + output_cost