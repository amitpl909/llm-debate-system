"""
LLM Client module for interfacing with language models
Supports OpenAI API and Anthropic API
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import logging

try:
    from openai import OpenAI, RateLimitError, APIError
except ImportError:
    OpenAI = None

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)


# ============================================================================
# ABSTRACT BASE CLIENT
# ============================================================================

class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 500):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.total_tokens_used = 0
        self.total_api_calls = 0
    
    @abstractmethod
    def generate(self, 
                 system_prompt: str, 
                 user_prompt: str,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None) -> str:
        """Generate text from the LLM"""
        pass
    
    @abstractmethod
    def get_token_count(self) -> int:
        """Get total tokens used"""
        pass


# ============================================================================
# ANTHROPIC CLIENT IMPLEMENTATION
# ============================================================================

class AnthropicClient(LLMClient):
    """Client for Anthropic Claude models"""
    
    def __init__(self, 
                 model: str, 
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 500,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        super().__init__(model, temperature, max_tokens)
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.tokens_used = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
    
    def generate(self, 
                 system_prompt: str, 
                 user_prompt: str,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None) -> str:
        """
        Generate text using Anthropic API with retry logic
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=tokens,
                    temperature=temp,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                # Track token usage
                self.tokens_used["input_tokens"] += response.usage.input_tokens
                self.tokens_used["output_tokens"] += response.usage.output_tokens
                self.tokens_used["total_tokens"] += response.usage.input_tokens + response.usage.output_tokens
                self.total_tokens_used += response.usage.input_tokens + response.usage.output_tokens
                self.total_api_calls += 1
                
                logger.info(f"Anthropic API call successful. Tokens used: {response.usage.input_tokens + response.usage.output_tokens}")
                
                return response.content[0].text
            
            except anthropic.RateLimitError as e:
                last_error = e
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = self.retry_delay * (2 ** (retry_count - 1))
                    logger.warning(f"Rate limit hit. Retrying in {wait_time}s... (Attempt {retry_count}/{self.max_retries})")
                    time.sleep(wait_time)
            
            except anthropic.APIError as e:
                last_error = e
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = self.retry_delay
                    logger.warning(f"API error: {str(e)}. Retrying in {wait_time}s... (Attempt {retry_count}/{self.max_retries})")
                    time.sleep(wait_time)
        
        raise ValueError(f"Failed to get response after {self.max_retries} retries. Last error: {str(last_error)}")
    
    def get_token_count(self) -> int:
        """Get total tokens used"""
        return self.total_tokens_used
    
    def get_token_usage_breakdown(self) -> Dict[str, int]:
        """Get breakdown of token usage"""
        return self.tokens_used.copy()
    
    def reset_token_count(self):
        """Reset token usage tracking"""
        self.tokens_used = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        self.total_tokens_used = 0


# ============================================================================
# OPENAI CLIENT IMPLEMENTATION
# ============================================================================

class OpenAIClient(LLMClient):
    """Client for OpenAI models (GPT-3.5, GPT-4, etc.)"""
    
    def __init__(self, 
                 model: str, 
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 500,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 top_p: float = 0.95):
        super().__init__(model, temperature, max_tokens)
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.top_p = top_p
        self.tokens_used = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    
    def generate(self, 
                 system_prompt: str, 
                 user_prompt: str,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None) -> str:
        """
        Generate text using OpenAI API with retry logic
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temp,
                    max_tokens=tokens,
                    top_p=self.top_p,
                )
                
                # Track token usage
                self.tokens_used["prompt_tokens"] += response.usage.prompt_tokens
                self.tokens_used["completion_tokens"] += response.usage.completion_tokens
                self.tokens_used["total_tokens"] += response.usage.total_tokens
                self.total_tokens_used += response.usage.total_tokens
                self.total_api_calls += 1
                
                logger.info(f"API call successful. Tokens used: {response.usage.total_tokens}")
                
                return response.choices[0].message.content
            
            except RateLimitError as e:
                last_error = e
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = self.retry_delay * (2 ** (retry_count - 1))
                    logger.warning(f"Rate limit hit. Retrying in {wait_time}s... (Attempt {retry_count}/{self.max_retries})")
                    time.sleep(wait_time)
            
            except APIError as e:
                last_error = e
                retry_count += 1
                if retry_count < self.max_retries:
                    wait_time = self.retry_delay
                    logger.warning(f"API error: {str(e)}. Retrying in {wait_time}s... (Attempt {retry_count}/{self.max_retries})")
                    time.sleep(wait_time)
        
        # If we've exhausted retries, raise the last error
        raise ValueError(f"Failed to get response after {self.max_retries} retries. Last error: {str(last_error)}")
    
    def get_token_count(self) -> int:
        """Get total tokens used"""
        return self.total_tokens_used
    
    def get_token_usage_breakdown(self) -> Dict[str, int]:
        """Get breakdown of token usage"""
        return self.tokens_used.copy()
    
    def reset_token_count(self):
        """Reset token usage tracking"""
        self.tokens_used = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }


# ============================================================================
# MOCK CLIENT FOR TESTING
# ============================================================================

class MockLLMClient(LLMClient):
    """Mock client for testing without API calls"""
    
    def __init__(self, model: str = "mock-model", temperature: float = 0.7, max_tokens: int = 500):
        super().__init__(model, temperature, max_tokens)
        self.responses = {}
        self.call_count = 0
    
    def set_response(self, prompt_hash: str, response: str):
        """Set a predefined response for a given prompt"""
        self.responses[prompt_hash] = response
    
    def generate(self, 
                 system_prompt: str, 
                 user_prompt: str,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None) -> str:
        """Generate mock response"""
        self.call_count += 1
        self.total_api_calls += 1
        
        # Create a mock response structure
        mock_response = f"""ANSWER: Yes
CONFIDENCE: 4
REASONING: This is a mock response for testing purposes."""
        
        return mock_response
    
    def get_token_count(self) -> int:
        """Return mock token count"""
        return self.call_count * 100  # Mock: assume 100 tokens per call


# ============================================================================
# CLIENT FACTORY
# ============================================================================

def create_llm_client(model: str,
                     api_key: Optional[str] = None,
                     temperature: float = 0.7,
                     max_tokens: int = 500,
                     provider: str = "anthropic",
                     **kwargs) -> LLMClient:
    """
    Factory function to create an LLM client
    
    Args:
        model: Model name (e.g., "claude-3-sonnet-20240229", "gpt-4")
        api_key: API key for the provider
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        provider: Provider name ("anthropic", "openai", "mock")
        **kwargs: Additional arguments for the specific provider
    
    Returns:
        LLMClient instance
    """
    
    if provider.lower() == "anthropic":
        if anthropic is None:
            raise ImportError("Anthropic library not installed. Install with: pip install anthropic")
        return AnthropicClient(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    elif provider.lower() == "openai":
        if OpenAI is None:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        return OpenAIClient(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    elif provider.lower() == "mock":
        return MockLLMClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ============================================================================
# BATCH PROCESSING
# ============================================================================

class BatchLLMProcessor:
    """Processor for batching multiple LLM requests"""
    
    def __init__(self, client: LLMClient, delay_between_calls: float = 0.1):
        self.client = client
        self.delay = delay_between_calls
        self.results = []
        self.errors = []
    
    def process_batch(self, 
                     prompts: List[Dict[str, str]],
                     system_prompt: str,
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None) -> List[str]:
        """
        Process a batch of prompts
        
        Args:
            prompts: List of dicts with 'user' key containing the user prompt
            system_prompt: System prompt for all requests
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
        
        Returns:
            List of responses
        """
        results = []
        
        for i, prompt_dict in enumerate(prompts):
            try:
                response = self.client.generate(
                    system_prompt=system_prompt,
                    user_prompt=prompt_dict.get('user', ''),
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                results.append(response)
                logger.info(f"Batch item {i+1}/{len(prompts)} processed successfully")
                
                # Add delay between calls
                if i < len(prompts) - 1:
                    time.sleep(self.delay)
            
            except Exception as e:
                error_msg = f"Error processing batch item {i+1}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
                results.append(None)
        
        self.results = results
        return results
