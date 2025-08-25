"""
Mock HTTP Server for Integration Testing
"""

import json
import asyncio
import threading
from typing import Dict, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socketserver


class MockLLMHandler(BaseHTTPRequestHandler):
    """HTTP handler for mock LLM API endpoints"""
    
    def __init__(self, *args, scenario_manager=None, **kwargs):
        self.scenario_manager = scenario_manager
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/tags':
            self._handle_list_models()
        elif parsed_path.path == '/health':
            self._handle_health_check()
        elif parsed_path.path.startswith('/api/models'):
            self._handle_model_info()
        else:
            self._send_error(404, "Endpoint not found")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/chat':
            self._handle_chat_completion()
        elif parsed_path.path == '/api/completions':
            self._handle_text_completion()
        elif parsed_path.path == '/api/pull':
            self._handle_model_pull()
        else:
            self._send_error(404, "Endpoint not found")
    
    def _handle_list_models(self):
        """Handle model listing endpoint"""
        if not self.scenario_manager:
            models = {
                "models": [
                    {
                        "name": "mock-model:latest",
                        "modified_at": "2024-01-01T00:00:00Z",
                        "size": 1000000,
                        "digest": "mock-digest"
                    },
                    {
                        "name": "mock-model-large:latest", 
                        "modified_at": "2024-01-01T00:00:00Z",
                        "size": 5000000,
                        "digest": "mock-digest-large"
                    }
                ]
            }
        else:
            scenario = self.scenario_manager.get_current_scenario()
            if scenario.should_fail and scenario.failure_type == "model_list":
                self._send_error(500, "Failed to list models")
                return
            
            models = scenario.custom_response or {
                "models": [
                    {"name": f"mock-{scenario.name}:latest", "size": 1000000}
                ]
            }
        
        self._send_json_response(models)
    
    def _handle_health_check(self):
        """Handle health check endpoint"""
        if self.scenario_manager:
            scenario = self.scenario_manager.get_current_scenario()
            if scenario.should_fail and scenario.failure_type == "health":
                self._send_error(503, "Service unavailable")
                return
        
        health = {"status": "healthy", "message": "Mock server running"}
        self._send_json_response(health)
    
    def _handle_chat_completion(self):
        """Handle chat completion endpoint"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            if self.scenario_manager:
                scenario = self.scenario_manager.get_current_scenario()
                
                # Simulate delay
                if scenario.response_delay > 0:
                    import time
                    time.sleep(scenario.response_delay)
                
                # Handle failure scenarios
                if scenario.should_fail:
                    if scenario.failure_type == "network":
                        # Simulate connection drop
                        self.wfile.close()
                        return
                    elif scenario.failure_type == "auth":
                        self._send_error(401, "Authentication failed")
                        return
                    elif scenario.failure_type == "rate_limit":
                        self._send_error(429, "Rate limit exceeded")
                        return
                    elif scenario.failure_type == "model_error":
                        self._send_error(500, "Model inference error")
                        return
                
                # Use scenario response
                response_content = scenario.response_content
                if "{request}" in response_content:
                    user_message = ""
                    if request_data.get('messages'):
                        user_message = request_data['messages'][-1].get('content', '')
                    response_content = response_content.format(request=user_message)
                
                response = {
                    "model": request_data.get('model', 'mock-model'),
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "eval_count": scenario.usage_tokens,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            else:
                # Default response
                response = {
                    "model": request_data.get('model', 'mock-model'),
                    "message": {
                        "role": "assistant", 
                        "content": "This is a mock response from the test server."
                    },
                    "eval_count": 100,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            
            # Handle streaming
            if request_data.get('stream', False):
                self._handle_streaming_response(response)
            else:
                self._send_json_response(response)
                
        except Exception as e:
            self._send_error(500, f"Server error: {str(e)}")
    
    def _handle_streaming_response(self, response):
        """Handle streaming chat completion"""
        if self.scenario_manager:
            scenario = self.scenario_manager.get_current_scenario()
            chunks = scenario.streaming_chunks or [response["message"]["content"]]
        else:
            chunks = ["Mock ", "streaming ", "response"]
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/x-ndjson')
        self.end_headers()
        
        for chunk in chunks:
            chunk_response = {
                "model": response["model"],
                "message": {
                    "role": "assistant",
                    "content": chunk
                },
                "done": False
            }
            
            chunk_json = json.dumps(chunk_response) + '\n'
            self.wfile.write(chunk_json.encode('utf-8'))
            self.wfile.flush()
            
            # Simulate streaming delay
            if self.scenario_manager:
                scenario = self.scenario_manager.get_current_scenario()
                if scenario.response_delay > 0:
                    import time
                    time.sleep(scenario.response_delay / len(chunks))
        
        # Send final chunk
        final_chunk = {
            "model": response["model"],
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "eval_count": response.get("eval_count", 0)
        }
        final_json = json.dumps(final_chunk) + '\n'
        self.wfile.write(final_json.encode('utf-8'))
    
    def _handle_text_completion(self):
        """Handle text completion endpoint"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            response = {
                "id": "mock-completion-001",
                "object": "text_completion",
                "model": request_data.get('model', 'mock-model'),
                "choices": [{
                    "text": "Mock completion response",
                    "index": 0,
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 20,
                    "total_tokens": 70
                }
            }
            
            self._send_json_response(response)
        except Exception as e:
            self._send_error(500, f"Server error: {str(e)}")
    
    def _handle_model_pull(self):
        """Handle model pull endpoint"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            if self.scenario_manager:
                scenario = self.scenario_manager.get_current_scenario()
                if scenario.should_fail and scenario.failure_type == "model_pull":
                    self._send_error(500, "Failed to pull model")
                    return
            
            # Simulate pull progress
            model_name = request_data.get('name', 'mock-model')
            
            if request_data.get('stream', True):
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-ndjson')
                self.end_headers()
                
                progress_updates = [
                    {"status": "pulling manifest"},
                    {"status": "pulling", "completed": 1000, "total": 10000},
                    {"status": "pulling", "completed": 5000, "total": 10000},
                    {"status": "pulling", "completed": 10000, "total": 10000},
                    {"status": "success"}
                ]
                
                for update in progress_updates:
                    update_json = json.dumps(update) + '\n'
                    self.wfile.write(update_json.encode('utf-8'))
                    self.wfile.flush()
                    import time
                    time.sleep(0.1)
            else:
                response = {"status": "success"}
                self._send_json_response(response)
                
        except Exception as e:
            self._send_error(500, f"Server error: {str(e)}")
    
    def _handle_model_info(self):
        """Handle model info endpoint"""
        model_info = {
            "modelfile": "FROM mock-base\nSYSTEM You are a helpful assistant",
            "parameters": "temperature 0.7",
            "template": "{{ .System }}{{ .Prompt }}",
            "details": {
                "format": "gguf",
                "family": "mock",
                "families": ["mock"],
                "parameter_size": "7B",
                "quantization_level": "Q4_0"
            }
        }
        self._send_json_response(model_info)
    
    def _send_json_response(self, data: Dict[str, Any]):
        """Send JSON response"""
        response_json = json.dumps(data, indent=2)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_error(self, code: int, message: str):
        """Send error response"""
        error_response = {"error": {"message": message, "code": code}}
        response_json = json.dumps(error_response)
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to suppress default HTTP server logging"""
        pass


class MockScenarioManager:
    """Manages test scenarios for mock server"""
    
    def __init__(self):
        from tests.mocks.mock_provider import MockScenario
        self.scenarios = {
            "default": MockScenario(
                name="default",
                response_content="Default mock server response",
                response_delay=0.1,
                usage_tokens=100
            )
        }
        self.current_scenario = "default"
    
    def add_scenario(self, name: str, scenario):
        """Add a new scenario"""
        self.scenarios[name] = scenario
    
    def set_scenario(self, name: str):
        """Set the current scenario"""
        if name in self.scenarios:
            self.current_scenario = name
        else:
            raise ValueError(f"Scenario '{name}' not found")
    
    def get_current_scenario(self):
        """Get the current scenario"""
        return self.scenarios[self.current_scenario]


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """HTTP server that handles requests in separate threads"""
    daemon_threads = True
    allow_reuse_address = True


class MockServer:
    """Mock HTTP server for integration testing"""
    
    def __init__(self, host='localhost', port=0):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.scenario_manager = MockScenarioManager()
    
    def start(self) -> str:
        """Start the mock server and return its URL"""
        # Create handler class with scenario manager
        def handler_factory(*args, **kwargs):
            return MockLLMHandler(*args, scenario_manager=self.scenario_manager, **kwargs)
        
        # Create and start server
        self.server = ThreadingHTTPServer((self.host, self.port), handler_factory)
        
        # Get assigned port if port was 0
        if self.port == 0:
            self.port = self.server.server_address[1]
        
        # Start server in background thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        return f"http://{self.host}:{self.port}"
    
    def stop(self):
        """Stop the mock server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        if self.server_thread:
            self.server_thread.join(timeout=5.0)
    
    def set_scenario(self, scenario_name: str):
        """Set the current test scenario"""
        self.scenario_manager.set_scenario(scenario_name)
    
    def add_scenario(self, name: str, scenario):
        """Add a new test scenario"""
        self.scenario_manager.add_scenario(name, scenario)
    
    def get_url(self) -> str:
        """Get the server URL"""
        return f"http://{self.host}:{self.port}"


class MockServerFactory:
    """Factory for creating configured mock servers"""
    
    @staticmethod
    def create_ollama_server(port=0):
        """Create a mock server that mimics Ollama API"""
        server = MockServer(port=port)
        
        from tests.mocks.mock_provider import MockScenario
        
        # Add Ollama-specific scenarios
        server.add_scenario("ollama_healthy", MockScenario(
            name="ollama_healthy",
            response_content="Ollama mock response: {request}",
            response_delay=0.2,
            usage_tokens=150,
            streaming_chunks=["Ollama ", "mock ", "response: ", "{request}"]
        ))
        
        server.add_scenario("ollama_slow", MockScenario(
            name="ollama_slow",
            response_content="Slow Ollama response",
            response_delay=2.0,
            usage_tokens=200
        ))
        
        server.add_scenario("ollama_error", MockScenario(
            name="ollama_error",
            should_fail=True,
            failure_type="model_error"
        ))
        
        return server
    
    @staticmethod
    def create_openai_server(port=0):
        """Create a mock server that mimics OpenAI API"""
        server = MockServer(port=port)
        
        from tests.mocks.mock_provider import MockScenario
        
        server.add_scenario("openai_gpt4", MockScenario(
            name="openai_gpt4",
            response_content="OpenAI GPT-4 mock response",
            response_delay=1.0,
            usage_tokens=500,
            cost=0.03,
            streaming_chunks=["OpenAI ", "GPT-4 ", "mock ", "response"]
        ))
        
        server.add_scenario("openai_rate_limit", MockScenario(
            name="openai_rate_limit",
            should_fail=True,
            failure_type="rate_limit"
        ))
        
        return server
    
    @staticmethod
    def create_multi_model_server(port=0):
        """Create a mock server with multiple model types"""
        server = MockServer(port=port)
        
        from tests.mocks.mock_provider import MockScenario
        
        # Text model
        server.add_scenario("text_model", MockScenario(
            name="text_model", 
            response_content="Text generation response",
            usage_tokens=300
        ))
        
        # Chat model
        server.add_scenario("chat_model", MockScenario(
            name="chat_model",
            response_content="Chat completion response",
            usage_tokens=250,
            streaming_chunks=["Chat ", "completion ", "response"]
        ))
        
        # Vision model
        server.add_scenario("vision_model", MockScenario(
            name="vision_model",
            response_content="Vision analysis response",
            usage_tokens=800,
            cost=0.05
        ))
        
        return server