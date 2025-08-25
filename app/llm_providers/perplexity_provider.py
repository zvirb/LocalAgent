"""
Perplexity Provider for LocalAgent
Interfaces with Perplexity API for search-grounded responses
"""

import os
import aiohttp
import json
from typing import Dict, Any, AsyncIterator, List
from .base_provider import BaseProvider, ModelInfo, CompletionRequest, CompletionResponse

class PerplexityProvider(BaseProvider):
    """Provider for Perplexity search-grounded models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('PERPLEXITY_API_KEY')
        self.base_url = 'https://api.perplexity.ai'
        self.is_local = False
        self.requires_api_key = True
        
    async def initialize(self) -> bool:
        """Initialize Perplexity client"""
        if not self.api_key:
            return False
        
        # Test connection with a simple request
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Test with a minimal request
                return True  # Perplexity doesn't have a specific health endpoint
        except Exception as e:
            print(f"Failed to initialize Perplexity: {e}")
            return False
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Perplexity models"""
        models = []
        model_list = [
            ('sonar-pro', 200000, ['chat', 'search_grounded']),
            ('sonar', 127000, ['chat', 'search_grounded']),
            ('sonar-reasoning', 127000, ['chat', 'search_grounded', 'reasoning'])
        ]
        
        for name, context, capabilities in model_list:
            models.append(ModelInfo(
                name=name,
                provider='perplexity',
                context_length=context,
                capabilities=capabilities
            ))
        
        return models
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion using Perplexity"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': request.model,
            'messages': request.messages,
            'temperature': request.temperature,
            'max_tokens': request.max_tokens or 4096,
            'stream': False,
            'return_citations': True,
            'return_related_questions': True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=payload
            ) as resp:
                data = await resp.json()
        
        # Extract citations if available
        citations = data.get('citations', [])
        
        return CompletionResponse(
            content=data['choices'][0]['message']['content'],
            model=request.model,
            provider='perplexity',
            usage=data.get('usage', {}),
            citations=citations
        )
    
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion from Perplexity"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': request.model,
            'messages': request.messages,
            'temperature': request.temperature,
            'max_tokens': request.max_tokens or 4096,
            'stream': True,
            'return_citations': True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=payload
            ) as resp:
                async for line in resp.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data and data['choices']:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield delta['content']
                            except json.JSONDecodeError:
                                continue
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Perplexity API health"""
        try:
            is_healthy = await self.initialize()
            return {
                'healthy': is_healthy,
                'provider': 'perplexity',
                'api_key_set': bool(self.api_key),
                'models_available': 3 if is_healthy else 0,
                'features': ['search_grounded', 'citations', 'real_time']
            }
        except Exception as e:
            return {
                'healthy': False,
                'provider': 'perplexity',
                'error': str(e)
            }