"""
Google Gemini Provider for LocalAgent
Interfaces with Google Gemini API
"""

import os
from typing import Dict, Any, AsyncIterator, List
import google.generativeai as genai
from .base_provider import BaseProvider, ModelInfo, CompletionRequest, CompletionResponse

class GeminiProvider(BaseProvider):
    """Provider for Google Gemini models"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('GEMINI_API_KEY')
        self.is_local = False
        self.requires_api_key = True
        self.model = None
        
    async def initialize(self) -> bool:
        """Initialize Gemini client"""
        if not self.api_key:
            return False
        
        try:
            genai.configure(api_key=self.api_key)
            # Test connection
            models = genai.list_models()
            return True
        except Exception as e:
            print(f"Failed to initialize Gemini: {e}")
            return False
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Gemini models"""
        models = []
        model_list = [
            ('gemini-1.5-pro', 1048576, ['chat', 'completion', 'vision', 'code_execution']),
            ('gemini-1.5-flash', 1048576, ['chat', 'completion', 'vision']),
            ('gemini-pro', 32768, ['chat', 'completion']),
        ]
        
        for name, context, capabilities in model_list:
            models.append(ModelInfo(
                name=name,
                provider='gemini',
                context_length=context,
                capabilities=capabilities
            ))
        
        return models
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion using Gemini"""
        model = genai.GenerativeModel(request.model)
        
        # Convert messages to Gemini format
        prompt = self._convert_messages(request.messages)
        
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens
            )
        )
        
        return CompletionResponse(
            content=response.text,
            model=request.model,
            provider='gemini',
            usage={'total_tokens': response.usage_metadata.total_token_count}
        )
    
    async def stream_complete(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Stream completion from Gemini"""
        model = genai.GenerativeModel(request.model)
        
        # Convert messages to Gemini format
        prompt = self._convert_messages(request.messages)
        
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens
            ),
            stream=True
        )
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Gemini API health"""
        try:
            is_healthy = await self.initialize()
            return {
                'healthy': is_healthy,
                'provider': 'gemini',
                'api_key_set': bool(self.api_key),
                'models_available': 3 if is_healthy else 0
            }
        except Exception as e:
            return {
                'healthy': False,
                'provider': 'gemini',
                'error': str(e)
            }
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style messages to Gemini format"""
        # Simple conversion - can be enhanced
        prompt_parts = []
        for msg in messages:
            role = msg['role']
            content = msg['content']
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(prompt_parts)