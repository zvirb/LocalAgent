"""
Ollama Provider for LocalAgent
Interfaces with local Ollama server for LLM operations
"""

import aiohttp
import asyncio
from typing import Dict, Any, AsyncIterator, List
from .base_provider import BaseProvider, ModelInfo, CompletionRequest, CompletionResponse
import json

class OllamaProvider(BaseProvider):
    """Provider for local Ollama models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.is_local = True
        self.requires_api_key = False
        
    async def initialize(self) -> bool:
        """Verify Ollama server is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    return resp.status == 200
        except:
            return False
    
    async def list_models(self) -> List[ModelInfo]:
        """List installed Ollama models"""
        models = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    data = await resp.json()
                    for model in data.get('models', []):
                        models.append(ModelInfo(
                            name=model['name'],
                            provider='ollama',
                            context_length=4096,  # Default, varies by model
                            capabilities=['chat', 'completion']
                        ))
        except Exception as e:
            print(f"Error listing Ollama models: {e}")
        return models
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion using Ollama"""
        payload = {
            'model': request.model,
            'messages': request.messages,
            'temperature': request.temperature,
            'stream': False
        }
        
        if request.system_prompt:
            payload['system'] = request.system_prompt
            
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                data = await resp.json()
                
        return CompletionResponse(
            content=data['message']['content'],
            model=request.model,
            provider='ollama',
            usage={'total_tokens': data.get('eval_count', 0)},
            cost=0.0  # Local models are free
        )
    
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion from Ollama"""
        payload = {
            'model': request.model,
            'messages': request.messages,
            'temperature': request.temperature,
            'stream': True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as resp:
                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if 'message' in data:
                                yield data['message']['content']
                        except json.JSONDecodeError:
                            continue
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama server health"""
        try:
            is_healthy = await self.initialize()
            models = await self.list_models() if is_healthy else []
            return {
                'healthy': is_healthy,
                'provider': 'ollama',
                'models_available': len(models),
                'models': [m.name for m in models]
            }
        except Exception as e:
            return {
                'healthy': False,
                'provider': 'ollama',
                'error': str(e)
            }
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        payload = {'name': model_name, 'stream': False}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/pull",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=3600)
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Error pulling model {model_name}: {e}")
            return False