"""
Accurate Token Counting for Different LLM Providers
Implements provider-specific token counting logic
"""

import re
import json
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseTokenCounter(ABC):
    """Abstract base class for token counting"""
    
    @abstractmethod
    def count_tokens(self, text: str, model: str = None) -> int:
        """Count tokens in text for specific model"""
        pass
    
    @abstractmethod
    def count_message_tokens(self, messages: List[Dict[str, str]], model: str = None) -> int:
        """Count tokens in message array"""
        pass

class GPTTokenCounter(BaseTokenCounter):
    """Token counter for OpenAI GPT models"""
    
    def __init__(self):
        # Approximate token counts per character for different models
        self.model_ratios = {
            'gpt-4': 0.25,          # ~4 chars per token
            'gpt-4-turbo': 0.25,
            'gpt-3.5-turbo': 0.25,
            'text-davinci-003': 0.25,
            'default': 0.25
        }
        
        # System message overhead
        self.system_overhead = 10
        self.message_overhead = 4  # Per message
    
    def count_tokens(self, text: str, model: str = None) -> int:
        """Count tokens using character-based approximation"""
        if not text:
            return 0
        
        model_key = model if model in self.model_ratios else 'default'
        ratio = self.model_ratios[model_key]
        
        # Basic character counting with adjustments
        char_count = len(text)
        
        # Adjust for whitespace and punctuation
        words = len(text.split())
        punctuation = len(re.findall(r'[^\w\s]', text))
        
        # GPT tokenization tends to:
        # - Split on whitespace and punctuation
        # - Use subword tokenization for complex words
        estimated_tokens = int(char_count * ratio + words * 0.1 + punctuation * 0.2)
        
        return max(1, estimated_tokens)
    
    def count_message_tokens(self, messages: List[Dict[str, str]], model: str = None) -> int:
        """Count tokens for message array including formatting overhead"""
        total_tokens = 0
        
        for message in messages:
            content = message.get('content', '')
            role = message.get('role', '')
            
            # Count content tokens
            content_tokens = self.count_tokens(content, model)
            
            # Add message formatting overhead
            total_tokens += content_tokens + self.message_overhead
            
            # System messages have additional overhead
            if role == 'system':
                total_tokens += self.system_overhead
        
        return total_tokens

class OllamaTokenCounter(BaseTokenCounter):
    """Token counter for Ollama models"""
    
    def __init__(self):
        # Ollama uses various models with different tokenization
        self.model_patterns = {
            'llama': 0.28,     # Llama models
            'mistral': 0.26,   # Mistral models  
            'codellama': 0.25, # CodeLlama
            'vicuna': 0.27,    # Vicuna
            'default': 0.27    # Conservative estimate
        }
        
        self.message_overhead = 3
    
    def _get_model_ratio(self, model: str) -> float:
        """Get token ratio for specific model"""
        if not model:
            return self.model_patterns['default']
        
        model_lower = model.lower()
        for pattern, ratio in self.model_patterns.items():
            if pattern in model_lower:
                return ratio
        
        return self.model_patterns['default']
    
    def count_tokens(self, text: str, model: str = None) -> int:
        """Count tokens for Ollama models"""
        if not text:
            return 0
        
        ratio = self._get_model_ratio(model)
        
        # Character-based estimation with word boundary adjustments
        char_count = len(text)
        word_count = len(text.split())
        
        # Ollama models tend to be more efficient with tokenization
        estimated_tokens = int(char_count * ratio + word_count * 0.05)
        
        return max(1, estimated_tokens)
    
    def count_message_tokens(self, messages: List[Dict[str, str]], model: str = None) -> int:
        """Count tokens for Ollama message format"""
        total_tokens = 0
        
        for message in messages:
            content = message.get('content', '')
            content_tokens = self.count_tokens(content, model)
            total_tokens += content_tokens + self.message_overhead
        
        return total_tokens

class GeminiTokenCounter(BaseTokenCounter):
    """Token counter for Google Gemini models"""
    
    def __init__(self):
        self.model_ratios = {
            'gemini-pro': 0.22,        # More efficient tokenization
            'gemini-pro-vision': 0.23,
            'default': 0.22
        }
        
        self.message_overhead = 5
        self.system_overhead = 8
    
    def count_tokens(self, text: str, model: str = None) -> int:
        """Count tokens for Gemini models"""
        if not text:
            return 0
        
        model_key = model if model in self.model_ratios else 'default'
        ratio = self.model_ratios[model_key]
        
        # Gemini has efficient tokenization
        char_count = len(text)
        word_count = len(text.split())
        
        # Account for multilingual content
        non_ascii = len([c for c in text if ord(c) > 127])
        
        estimated_tokens = int(char_count * ratio + word_count * 0.1 + non_ascii * 0.1)
        
        return max(1, estimated_tokens)
    
    def count_message_tokens(self, messages: List[Dict[str, str]], model: str = None) -> int:
        """Count tokens for Gemini message format"""
        total_tokens = 0
        
        for message in messages:
            content = message.get('content', '')
            role = message.get('role', '')
            
            content_tokens = self.count_tokens(content, model)
            total_tokens += content_tokens + self.message_overhead
            
            if role == 'system':
                total_tokens += self.system_overhead
        
        return total_tokens

class PerplexityTokenCounter(BaseTokenCounter):
    """Token counter for Perplexity models"""
    
    def __init__(self):
        # Perplexity uses various underlying models
        self.base_ratio = 0.26
        self.message_overhead = 4
        self.citation_overhead = 2  # Per citation
    
    def count_tokens(self, text: str, model: str = None) -> int:
        """Count tokens for Perplexity models"""
        if not text:
            return 0
        
        char_count = len(text)
        word_count = len(text.split())
        
        # Standard estimation
        estimated_tokens = int(char_count * self.base_ratio + word_count * 0.1)
        
        return max(1, estimated_tokens)
    
    def count_message_tokens(self, messages: List[Dict[str, str]], model: str = None) -> int:
        """Count tokens for Perplexity with citation overhead"""
        total_tokens = 0
        
        for message in messages:
            content = message.get('content', '')
            content_tokens = self.count_tokens(content, model)
            total_tokens += content_tokens + self.message_overhead
            
            # Add citation overhead if content looks like it has citations
            if '[' in content and ']' in content:
                citations = len(re.findall(r'\[\d+\]', content))
                total_tokens += citations * self.citation_overhead
        
        return total_tokens

class TokenCounterManager:
    """
    Manager for provider-specific token counters
    """
    
    def __init__(self):
        self._counters = {
            'openai': GPTTokenCounter(),
            'gpt': GPTTokenCounter(),
            'ollama': OllamaTokenCounter(),
            'gemini': GeminiTokenCounter(),
            'google': GeminiTokenCounter(),
            'perplexity': PerplexityTokenCounter(),
            'anthropic': GPTTokenCounter(),  # Similar tokenization
        }
        
        self._default_counter = GPTTokenCounter()
    
    def get_counter(self, provider: str) -> BaseTokenCounter:
        """Get token counter for provider"""
        provider_key = provider.lower()
        
        # Try exact match first
        if provider_key in self._counters:
            return self._counters[provider_key]
        
        # Try partial matches
        for key, counter in self._counters.items():
            if key in provider_key or provider_key in key:
                return counter
        
        # Default fallback
        logger.debug(f"Using default token counter for provider: {provider}")
        return self._default_counter
    
    def count_tokens(self, provider: str, text: str, model: str = None) -> int:
        """Count tokens for specific provider"""
        counter = self.get_counter(provider)
        return counter.count_tokens(text, model)
    
    def count_message_tokens(self, provider: str, messages: List[Dict[str, str]], model: str = None) -> int:
        """Count tokens for message array"""
        counter = self.get_counter(provider)
        return counter.count_message_tokens(messages, model)
    
    def estimate_cost(self, provider: str, tokens: int, model: str = None, 
                     input_tokens: int = None, output_tokens: int = None) -> float:
        """Estimate cost based on token usage"""
        # Cost per 1K tokens (approximate rates as of 2024)
        cost_rates = {
            'openai': {
                'gpt-4': {'input': 0.03, 'output': 0.06},
                'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
                'gpt-3.5-turbo': {'input': 0.001, 'output': 0.002},
                'default': {'input': 0.01, 'output': 0.03}
            },
            'anthropic': {
                'claude-3': {'input': 0.015, 'output': 0.075},
                'default': {'input': 0.015, 'output': 0.075}
            },
            'gemini': {
                'gemini-pro': {'input': 0.001, 'output': 0.002},
                'default': {'input': 0.001, 'output': 0.002}
            },
            'perplexity': {
                'default': {'input': 0.001, 'output': 0.001}
            }
        }
        
        # Local providers are free
        if provider.lower() in ['ollama']:
            return 0.0
        
        provider_key = provider.lower()
        if provider_key not in cost_rates:
            return 0.0
        
        rates = cost_rates[provider_key]
        model_rates = rates.get(model, rates.get('default', {'input': 0.01, 'output': 0.02}))
        
        if input_tokens is not None and output_tokens is not None:
            # Separate input/output pricing
            cost = (input_tokens / 1000 * model_rates['input'] + 
                   output_tokens / 1000 * model_rates['output'])
        else:
            # Use blended rate (assume 50/50 split)
            blended_rate = (model_rates['input'] + model_rates['output']) / 2
            cost = tokens / 1000 * blended_rate
        
        return cost

# Global token counter manager
_global_token_manager: Optional[TokenCounterManager] = None

def get_global_token_manager() -> TokenCounterManager:
    """Get or create the global token counter manager"""
    global _global_token_manager
    if _global_token_manager is None:
        _global_token_manager = TokenCounterManager()
    return _global_token_manager