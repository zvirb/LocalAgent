"""
Mock LLM servers for integration testing
Provides realistic mock implementations of Ollama, OpenAI, Gemini, and Perplexity APIs
"""

from aiohttp import web
import json
import asyncio
import time
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class MockOllamaServer:
    """Mock Ollama server for integration testing"""
    
    def __init__(self, port=11434):
        self.port = port
        self.app = web.Application()
        self.models = [
            {
                "name": "llama2:7b",
                "size": 3825819519,
                "digest": "sha256:abc123def456",
                "modified_at": "2024-01-01T00:00:00Z"
            },
            {
                "name": "codellama:13b",
                "size": 7365960935,
                "digest": "sha256:def456ghi789",
                "modified_at": "2024-01-01T00:00:00Z"
            },
            {
                "name": "mistral:7b",
                "size": 4109000000,
                "digest": "sha256:ghi789jkl012",
                "modified_at": "2024-01-01T00:00:00Z"
            }
        ]
        self.setup_routes()
        
    def setup_routes(self):
        """Setup mock API routes"""
        self.app.router.add_get('/api/tags', self.list_models)
        self.app.router.add_post('/api/generate', self.generate)
        self.app.router.add_post('/api/chat', self.chat)
        self.app.router.add_post('/api/pull', self.pull_model)
        self.app.router.add_delete('/api/delete', self.delete_model)
        
    async def list_models(self, request):
        """Mock model list endpoint"""
        return web.json_response({"models": self.models})
    
    async def generate(self, request):
        """Mock completion endpoint"""
        data = await request.json()
        prompt = data.get('prompt', '')
        model = data.get('model', 'llama2:7b')
        stream = data.get('stream', False)
        
        # Simulate model not found
        if not any(m['name'] == model for m in self.models):
            return web.json_response(
                {"error": f"model '{model}' not found"},
                status=404
            )
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        if stream:
            return await self._stream_generate(data)
        else:
            return web.json_response({
                "response": f"Mock Ollama response for: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
                "model": model,
                "created_at": "2024-08-25T10:00:00Z",
                "done": True,
                "context": [1, 2, 3, 4, 5],
                "total_duration": 1500000000,
                "load_duration": 500000000,
                "prompt_eval_count": len(prompt.split()),
                "prompt_eval_duration": 800000000,
                "eval_count": 25,
                "eval_duration": 700000000
            })
    
    async def chat(self, request):
        """Mock chat endpoint"""
        data = await request.json()
        messages = data.get('messages', [])
        model = data.get('model', 'llama2:7b')
        stream = data.get('stream', False)
        
        # Simulate model not found
        if not any(m['name'] == model for m in self.models):
            return web.json_response(
                {"error": f"model '{model}' not found"},
                status=404
            )
        
        # Get last user message
        last_message = messages[-1]['content'] if messages else "Hello"
        
        await asyncio.sleep(0.1)
        
        if stream:
            return await self._stream_chat(data)
        else:
            return web.json_response({
                "message": {
                    "role": "assistant",
                    "content": f"Mock chat response to: {last_message[:50]}{'...' if len(last_message) > 50 else ''}"
                },
                "model": model,
                "created_at": "2024-08-25T10:00:00Z",
                "done": True,
                "total_duration": 1500000000,
                "load_duration": 500000000,
                "prompt_eval_count": sum(len(msg['content'].split()) for msg in messages),
                "prompt_eval_duration": 800000000,
                "eval_count": 20,
                "eval_duration": 700000000
            })
    
    async def _stream_generate(self, data):
        """Mock streaming generation response"""
        prompt = data.get('prompt', '')
        model = data.get('model', 'llama2:7b')
        
        async def generate_chunks():
            chunks = [
                "Mock ", "streaming ", "Ollama ", "response ", "for: ",
                f"{prompt[:20]}{'...' if len(prompt) > 20 else ''}"
            ]
            
            for i, chunk in enumerate(chunks):
                response_data = {
                    "response": chunk,
                    "model": model,
                    "created_at": "2024-08-25T10:00:00Z",
                    "done": False
                }
                
                yield json.dumps(response_data) + '\n'
                await asyncio.sleep(0.05)
            
            # Final chunk
            final_response = {
                "response": "",
                "model": model,
                "created_at": "2024-08-25T10:00:00Z",
                "done": True,
                "context": [1, 2, 3, 4, 5],
                "total_duration": 1500000000,
                "load_duration": 500000000,
                "prompt_eval_count": len(prompt.split()),
                "prompt_eval_duration": 800000000,
                "eval_count": 25,
                "eval_duration": 700000000
            }
            yield json.dumps(final_response) + '\n'
        
        return web.StreamResponse(
            status=200,
            headers={'Content-Type': 'application/x-ndjson'},
            body=generate_chunks()
        )
    
    async def _stream_chat(self, data):
        """Mock streaming chat response"""
        messages = data.get('messages', [])
        model = data.get('model', 'llama2:7b')
        last_message = messages[-1]['content'] if messages else "Hello"
        
        async def generate_chunks():
            chunks = [
                "Mock ", "streaming ", "chat ", "response ", "to: ",
                f"{last_message[:20]}{'...' if len(last_message) > 20 else ''}"
            ]
            
            for chunk in chunks:
                response_data = {
                    "message": {
                        "role": "assistant",
                        "content": chunk
                    },
                    "model": model,
                    "created_at": "2024-08-25T10:00:00Z",
                    "done": False
                }
                
                yield json.dumps(response_data) + '\n'
                await asyncio.sleep(0.05)
            
            # Final chunk
            final_response = {
                "message": {
                    "role": "assistant",
                    "content": ""
                },
                "model": model,
                "created_at": "2024-08-25T10:00:00Z",
                "done": True,
                "total_duration": 1500000000,
                "load_duration": 500000000,
                "prompt_eval_count": sum(len(msg['content'].split()) for msg in messages),
                "eval_count": 20,
                "eval_duration": 700000000
            }
            yield json.dumps(final_response) + '\n'
        
        return web.StreamResponse(
            status=200,
            headers={'Content-Type': 'application/x-ndjson'},
            body=generate_chunks()
        )
    
    async def pull_model(self, request):
        """Mock model pull endpoint"""
        data = await request.json()
        model_name = data.get('name', '')
        
        # Simulate pull progress
        return web.StreamResponse(
            status=200,
            headers={'Content-Type': 'application/x-ndjson'},
            body=self._mock_pull_progress(model_name)
        )
    
    async def _mock_pull_progress(self, model_name):
        """Mock model pull progress"""
        progress_steps = [
            {"status": "pulling manifest"},
            {"status": "downloading", "digest": "sha256:abc123", "total": 1000000, "completed": 200000},
            {"status": "downloading", "digest": "sha256:abc123", "total": 1000000, "completed": 600000},
            {"status": "downloading", "digest": "sha256:abc123", "total": 1000000, "completed": 1000000},
            {"status": "verifying sha256 digest"},
            {"status": "writing manifest"},
            {"status": "removing any unused layers"},
            {"status": "success"}
        ]
        
        for step in progress_steps:
            yield json.dumps(step) + '\n'
            await asyncio.sleep(0.1)
    
    async def delete_model(self, request):
        """Mock model deletion endpoint"""
        data = await request.json()
        model_name = data.get('name', '')
        
        # Remove from models list
        self.models = [m for m in self.models if m['name'] != model_name]
        
        return web.json_response({"status": "success"})

class MockOpenAIServer:
    """Mock OpenAI server for integration testing"""
    
    def __init__(self, port=8080):
        self.port = port
        self.app = web.Application()
        self.models = [
            {
                "id": "gpt-4o",
                "object": "model",
                "created": 1686935002,
                "owned_by": "openai"
            },
            {
                "id": "gpt-4o-mini",
                "object": "model",
                "created": 1686935002,
                "owned_by": "openai"
            },
            {
                "id": "gpt-4-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai"
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai"
            }
        ]
        self.setup_routes()
    
    def setup_routes(self):
        """Setup mock OpenAI API routes"""
        self.app.router.add_get('/v1/models', self.list_models)
        self.app.router.add_post('/v1/chat/completions', self.chat_completions)
        self.app.router.add_post('/v1/completions', self.completions)
        
    def _check_auth(self, request):
        """Check API key authentication"""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False, "Invalid API key format"
        
        api_key = auth_header[7:]  # Remove 'Bearer '
        if not api_key or api_key == 'invalid':
            return False, "Invalid API key"
        
        return True, None
    
    async def list_models(self, request):
        """Mock models endpoint"""
        valid, error = self._check_auth(request)
        if not valid:
            return web.json_response(
                {"error": {"message": error, "type": "invalid_request_error"}},
                status=401
            )
        
        return web.json_response({
            "object": "list",
            "data": self.models
        })
    
    async def chat_completions(self, request):
        """Mock chat completions endpoint"""
        valid, error = self._check_auth(request)
        if not valid:
            return web.json_response(
                {"error": {"message": error, "type": "invalid_request_error"}},
                status=401
            )
        
        try:
            data = await request.json()
        except:
            return web.json_response(
                {"error": {"message": "Invalid JSON", "type": "invalid_request_error"}},
                status=400
            )
        
        messages = data.get('messages', [])
        model = data.get('model', 'gpt-3.5-turbo')
        stream = data.get('stream', False)
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens')
        
        # Validate model
        if not any(m['id'] == model for m in self.models):
            return web.json_response(
                {"error": {"message": f"Model {model} not found", "type": "invalid_request_error"}},
                status=404
            )
        
        # Validate messages
        if not messages:
            return web.json_response(
                {"error": {"message": "Messages cannot be empty", "type": "invalid_request_error"}},
                status=400
            )
        
        await asyncio.sleep(0.1)  # Simulate API delay
        
        if stream:
            return await self._stream_chat_completion(data)
        else:
            last_message = messages[-1]['content']
            response_content = f"Mock OpenAI response to: {last_message[:50]}{'...' if len(last_message) > 50 else ''}"
            
            # Truncate if max_tokens specified
            if max_tokens and len(response_content.split()) > max_tokens:
                words = response_content.split()[:max_tokens]
                response_content = ' '.join(words)
            
            return web.json_response({
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop" if not max_tokens else "length"
                }],
                "usage": {
                    "prompt_tokens": sum(len(msg['content'].split()) for msg in messages),
                    "completion_tokens": len(response_content.split()),
                    "total_tokens": sum(len(msg['content'].split()) for msg in messages) + len(response_content.split())
                }
            })
    
    async def _stream_chat_completion(self, data):
        """Mock streaming chat completion"""
        messages = data.get('messages', [])
        model = data.get('model', 'gpt-3.5-turbo')
        last_message = messages[-1]['content']
        
        async def generate_chunks():
            # Initial chunk
            initial_chunk = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(initial_chunk)}\n\n"
            
            # Content chunks
            content_chunks = [
                "Mock ", "OpenAI ", "streaming ", "response ", "to: ",
                f"{last_message[:20]}{'...' if len(last_message) > 20 else ''}"
            ]
            
            for chunk in content_chunks:
                chunk_data = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
                await asyncio.sleep(0.05)
            
            # Final chunk
            final_chunk = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            },
            body=generate_chunks()
        )
    
    async def completions(self, request):
        """Mock completions endpoint (legacy)"""
        valid, error = self._check_auth(request)
        if not valid:
            return web.json_response(
                {"error": {"message": error, "type": "invalid_request_error"}},
                status=401
            )
        
        data = await request.json()
        prompt = data.get('prompt', '')
        model = data.get('model', 'gpt-3.5-turbo-instruct')
        
        await asyncio.sleep(0.1)
        
        return web.json_response({
            "id": f"cmpl-{int(time.time())}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "text": f"Mock completion for: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
                "index": 0,
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 20,
                "total_tokens": len(prompt.split()) + 20
            }
        })

class MockGeminiServer:
    """Mock Google Gemini server for integration testing"""
    
    def __init__(self, port=8081):
        self.port = port
        self.app = web.Application()
        self.models = [
            "gemini-1.5-pro",
            "gemini-1.5-flash", 
            "gemini-pro",
            "gemini-pro-vision"
        ]
        self.setup_routes()
    
    def setup_routes(self):
        """Setup mock Gemini API routes"""
        self.app.router.add_get('/v1/models', self.list_models)
        self.app.router.add_post('/v1/models/{model}:generateContent', self.generate_content)
        self.app.router.add_post('/v1/models/{model}:streamGenerateContent', self.stream_generate_content)
    
    def _check_auth(self, request):
        """Check API key authentication"""
        api_key = request.query.get('key') or request.headers.get('x-goog-api-key')
        if not api_key or api_key == 'invalid':
            return False, "Invalid API key"
        return True, None
    
    async def list_models(self, request):
        """Mock models endpoint"""
        valid, error = self._check_auth(request)
        if not valid:
            return web.json_response(
                {"error": {"message": error, "code": 401}},
                status=401
            )
        
        model_data = []
        for model in self.models:
            model_data.append({
                "name": f"models/{model}",
                "displayName": model,
                "description": f"Mock {model} model",
                "inputTokenLimit": 128000,
                "outputTokenLimit": 4096,
                "supportedGenerationMethods": ["generateContent", "streamGenerateContent"]
            })
        
        return web.json_response({"models": model_data})
    
    async def generate_content(self, request):
        """Mock content generation endpoint"""
        valid, error = self._check_auth(request)
        if not valid:
            return web.json_response(
                {"error": {"message": error, "code": 401}},
                status=401
            )
        
        model = request.match_info.get('model')
        if model not in self.models:
            return web.json_response(
                {"error": {"message": f"Model {model} not found", "code": 404}},
                status=404
            )
        
        data = await request.json()
        contents = data.get('contents', [])
        
        if not contents:
            return web.json_response(
                {"error": {"message": "Contents cannot be empty", "code": 400}},
                status=400
            )
        
        await asyncio.sleep(0.1)
        
        # Get last user message
        last_content = contents[-1].get('parts', [{}])[-1].get('text', '')
        
        return web.json_response({
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": f"Mock Gemini response to: {last_content[:50]}{'...' if len(last_content) > 50 else ''}"
                    }],
                    "role": "model"
                },
                "finishReason": "STOP",
                "index": 0,
                "safetyRatings": [
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "probability": "NEGLIGIBLE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "probability": "NEGLIGIBLE"
                    }
                ]
            }],
            "usageMetadata": {
                "promptTokenCount": sum(len(c.get('parts', [{}])[-1].get('text', '').split()) for c in contents),
                "candidatesTokenCount": 25,
                "totalTokenCount": sum(len(c.get('parts', [{}])[-1].get('text', '').split()) for c in contents) + 25
            }
        })
    
    async def stream_generate_content(self, request):
        """Mock streaming content generation"""
        valid, error = self._check_auth(request)
        if not valid:
            return web.json_response(
                {"error": {"message": error, "code": 401}},
                status=401
            )
        
        model = request.match_info.get('model')
        data = await request.json()
        contents = data.get('contents', [])
        last_content = contents[-1].get('parts', [{}])[-1].get('text', '') if contents else ''
        
        async def generate_chunks():
            chunks = [
                "Mock ", "Gemini ", "streaming ", "response ", "to: ",
                f"{last_content[:20]}{'...' if len(last_content) > 20 else ''}"
            ]
            
            for chunk in chunks:
                chunk_data = {
                    "candidates": [{
                        "content": {
                            "parts": [{"text": chunk}],
                            "role": "model"
                        },
                        "finishReason": None,
                        "index": 0
                    }]
                }
                yield json.dumps(chunk_data) + '\n'
                await asyncio.sleep(0.05)
            
            # Final chunk
            final_chunk = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": ""}],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0
                }],
                "usageMetadata": {
                    "promptTokenCount": sum(len(c.get('parts', [{}])[-1].get('text', '').split()) for c in contents),
                    "candidatesTokenCount": 25,
                    "totalTokenCount": sum(len(c.get('parts', [{}])[-1].get('text', '').split()) for c in contents) + 25
                }
            }
            yield json.dumps(final_chunk) + '\n'
        
        return web.StreamResponse(
            status=200,
            headers={'Content-Type': 'application/json'},
            body=generate_chunks()
        )

class MockPerplexityServer:
    """Mock Perplexity server for integration testing"""
    
    def __init__(self, port=8082):
        self.port = port
        self.app = web.Application()
        self.models = [
            "llama-3.1-sonar-small-128k-online",
            "llama-3.1-sonar-large-128k-online",
            "llama-3.1-sonar-huge-128k-online",
            "llama-3.1-8b-instruct",
            "llama-3.1-70b-instruct"
        ]
        self.setup_routes()
    
    def setup_routes(self):
        """Setup mock Perplexity API routes"""
        self.app.router.add_post('/chat/completions', self.chat_completions)
    
    def _check_auth(self, request):
        """Check API key authentication"""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False, "Invalid API key format"
        
        api_key = auth_header[7:]
        if not api_key or api_key == 'invalid':
            return False, "Invalid API key"
        
        return True, None
    
    async def chat_completions(self, request):
        """Mock chat completions endpoint"""
        valid, error = self._check_auth(request)
        if not valid:
            return web.json_response(
                {"error": {"message": error, "type": "invalid_request_error"}},
                status=401
            )
        
        data = await request.json()
        messages = data.get('messages', [])
        model = data.get('model', 'llama-3.1-sonar-small-128k-online')
        stream = data.get('stream', False)
        
        if model not in self.models:
            return web.json_response(
                {"error": {"message": f"Model {model} not found", "type": "invalid_request_error"}},
                status=404
            )
        
        await asyncio.sleep(0.1)
        
        last_message = messages[-1]['content'] if messages else "Hello"
        
        if stream:
            return await self._stream_chat_completion(data)
        else:
            # Perplexity includes citations for online models
            include_citations = "online" in model
            
            response_content = f"Mock Perplexity response to: {last_message[:50]}{'...' if len(last_message) > 50 else ''}"
            
            response_data = {
                "id": f"cmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": sum(len(msg['content'].split()) for msg in messages),
                    "completion_tokens": len(response_content.split()),
                    "total_tokens": sum(len(msg['content'].split()) for msg in messages) + len(response_content.split())
                }
            }
            
            # Add citations for online models
            if include_citations:
                response_data["citations"] = [
                    {
                        "url": "https://example.com/source1",
                        "title": "Mock Source 1",
                        "snippet": "This is a mock citation snippet."
                    },
                    {
                        "url": "https://example.com/source2", 
                        "title": "Mock Source 2",
                        "snippet": "Another mock citation snippet."
                    }
                ]
            
            return web.json_response(response_data)
    
    async def _stream_chat_completion(self, data):
        """Mock streaming chat completion"""
        messages = data.get('messages', [])
        model = data.get('model', 'llama-3.1-sonar-small-128k-online')
        last_message = messages[-1]['content']
        
        async def generate_chunks():
            chunks = [
                "Mock ", "Perplexity ", "streaming ", "response ", "to: ",
                f"{last_message[:20]}{'...' if len(last_message) > 20 else ''}"
            ]
            
            for chunk in chunks:
                chunk_data = {
                    "id": f"cmpl-{int(time.time())}",
                    "object": "chat.completion.chunk", 
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
                await asyncio.sleep(0.05)
            
            # Final chunk with citations for online models
            final_chunk = {
                "id": f"cmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            
            if "online" in model:
                final_chunk["citations"] = [
                    {
                        "url": "https://example.com/source1",
                        "title": "Mock Source 1"
                    }
                ]
            
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            },
            body=generate_chunks()
        )

# Server management utilities
class MockServerManager:
    """Manages multiple mock servers for testing"""
    
    def __init__(self):
        self.servers = {}
        self.runners = {}
        self.sites = {}
    
    async def start_server(self, server_type: str, port: int = None):
        """Start a specific mock server"""
        if server_type in self.servers:
            logger.warning(f"Server {server_type} already running")
            return
        
        server_classes = {
            'ollama': (MockOllamaServer, 11434),
            'openai': (MockOpenAIServer, 8080),  
            'gemini': (MockGeminiServer, 8081),
            'perplexity': (MockPerplexityServer, 8082)
        }
        
        if server_type not in server_classes:
            raise ValueError(f"Unknown server type: {server_type}")
        
        server_class, default_port = server_classes[server_type]
        port = port or default_port
        
        # Create and start server
        server = server_class(port)
        runner = web.AppRunner(server.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        
        self.servers[server_type] = server
        self.runners[server_type] = runner
        self.sites[server_type] = site
        
        logger.info(f"Mock {server_type} server started on port {port}")
    
    async def stop_server(self, server_type: str):
        """Stop a specific mock server"""
        if server_type not in self.servers:
            logger.warning(f"Server {server_type} not running")
            return
        
        await self.runners[server_type].cleanup()
        del self.servers[server_type]
        del self.runners[server_type] 
        del self.sites[server_type]
        
        logger.info(f"Mock {server_type} server stopped")
    
    async def start_all_servers(self):
        """Start all mock servers"""
        await asyncio.gather(
            self.start_server('ollama'),
            self.start_server('openai'),
            self.start_server('gemini'), 
            self.start_server('perplexity'),
            return_exceptions=True
        )
    
    async def stop_all_servers(self):
        """Stop all mock servers"""
        for server_type in list(self.servers.keys()):
            await self.stop_server(server_type)
    
    def get_server_urls(self) -> Dict[str, str]:
        """Get URLs for all running servers"""
        return {
            'ollama': 'http://localhost:11434',
            'openai': 'http://localhost:8080/v1',
            'gemini': 'http://localhost:8081/v1',
            'perplexity': 'http://localhost:8082'
        }

# Test fixture helper
async def setup_mock_servers():
    """Setup mock servers for testing"""
    manager = MockServerManager()
    await manager.start_all_servers()
    return manager