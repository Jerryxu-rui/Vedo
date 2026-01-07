"""
LLM Registry Service
Manages available Large Language Models for chat and agent orchestration
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class LLMProvider(str, Enum):
    GOOGLE = "google"
    ALIBABA = "alibaba"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


@dataclass
class LLMCapability:
    """LLM capability specification"""
    name: str
    display_name: str
    provider: LLMProvider
    api_endpoint: str
    description: str
    capabilities: List[str]  # e.g., ['chat', 'streaming', 'vision', 'function-calling']
    context_window: int  # Maximum context length
    max_output_tokens: int
    supports_streaming: bool
    supports_vision: bool
    supports_function_calling: bool
    rate_limit_per_minute: Optional[int]
    rate_limit_per_day: Optional[int]
    cost_per_1k_input_tokens: Optional[float]
    cost_per_1k_output_tokens: Optional[float]


class LLMRegistry:
    """Registry of available LLM models for chat and orchestration"""
    
    CHAT_MODELS = {
        "gemini-2.5-flash": LLMCapability(
            name="gemini-2.5-flash",
            display_name="Gemini 2.5 Flash",
            provider=LLMProvider.GOOGLE,
            api_endpoint="https://yunwu.ai/v1",
            description="Google's latest multimodal AI model via Yunwu - Fast, efficient, and powerful",
            capabilities=["chat", "streaming", "vision", "function-calling", "multimodal"],
            context_window=1000000,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_vision=True,
            supports_function_calling=True,
            rate_limit_per_minute=15,
            rate_limit_per_day=1500,
            cost_per_1k_input_tokens=0.0,
            cost_per_1k_output_tokens=0.0
        ),
        "gemini-2.0-flash-exp": LLMCapability(
            name="gemini-2.0-flash-exp",
            display_name="Gemini 2.0 Flash (Experimental)",
            provider=LLMProvider.GOOGLE,
            api_endpoint="https://generativelanguage.googleapis.com/v1beta",
            description="Google's latest multimodal AI model - Fast, efficient, and powerful",
            capabilities=["chat", "streaming", "vision", "function-calling", "multimodal"],
            context_window=1000000,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_vision=True,
            supports_function_calling=True,
            rate_limit_per_minute=15,
            rate_limit_per_day=1500,
            cost_per_1k_input_tokens=0.0,  # Free tier
            cost_per_1k_output_tokens=0.0
        ),
        "gemini-1.5-pro": LLMCapability(
            name="gemini-1.5-pro",
            display_name="Gemini 1.5 Pro",
            provider=LLMProvider.GOOGLE,
            api_endpoint="https://generativelanguage.googleapis.com/v1beta",
            description="Advanced reasoning with 2M token context window",
            capabilities=["chat", "streaming", "vision", "function-calling", "long-context"],
            context_window=2000000,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_vision=True,
            supports_function_calling=True,
            rate_limit_per_minute=10,
            rate_limit_per_day=1000,
            cost_per_1k_input_tokens=0.00125,
            cost_per_1k_output_tokens=0.005
        ),
        "gemini-1.5-flash": LLMCapability(
            name="gemini-1.5-flash",
            display_name="Gemini 1.5 Flash",
            provider=LLMProvider.GOOGLE,
            api_endpoint="https://generativelanguage.googleapis.com/v1beta",
            description="Fast and efficient for high-frequency tasks",
            capabilities=["chat", "streaming", "vision", "function-calling"],
            context_window=1000000,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_vision=True,
            supports_function_calling=True,
            rate_limit_per_minute=15,
            rate_limit_per_day=1500,
            cost_per_1k_input_tokens=0.000075,
            cost_per_1k_output_tokens=0.0003
        ),
        "qwen-max": LLMCapability(
            name="qwen-max",
            display_name="Qwen Max",
            provider=LLMProvider.ALIBABA,
            api_endpoint="https://dashscope.aliyuncs.com/api/v1",
            description="Alibaba's most powerful model - Excellent for Chinese and English",
            capabilities=["chat", "streaming", "function-calling"],
            context_window=32000,
            max_output_tokens=8000,
            supports_streaming=True,
            supports_vision=False,
            supports_function_calling=True,
            rate_limit_per_minute=60,
            rate_limit_per_day=10000,
            cost_per_1k_input_tokens=0.002,
            cost_per_1k_output_tokens=0.006
        ),
        "qwen-turbo": LLMCapability(
            name="qwen-turbo",
            display_name="Qwen Turbo",
            provider=LLMProvider.ALIBABA,
            api_endpoint="https://dashscope.aliyuncs.com/api/v1",
            description="Fast and cost-effective for general tasks",
            capabilities=["chat", "streaming"],
            context_window=8000,
            max_output_tokens=2000,
            supports_streaming=True,
            supports_vision=False,
            supports_function_calling=False,
            rate_limit_per_minute=120,
            rate_limit_per_day=20000,
            cost_per_1k_input_tokens=0.0002,
            cost_per_1k_output_tokens=0.0006
        ),
        "claude-3-5-sonnet": LLMCapability(
            name="claude-3-5-sonnet",
            display_name="Claude 3.5 Sonnet",
            provider=LLMProvider.ANTHROPIC,
            api_endpoint="https://api.anthropic.com/v1",
            description="Anthropic's balanced model - Great for complex reasoning",
            capabilities=["chat", "streaming", "vision", "function-calling"],
            context_window=200000,
            max_output_tokens=8192,
            supports_streaming=True,
            supports_vision=True,
            supports_function_calling=True,
            rate_limit_per_minute=50,
            rate_limit_per_day=5000,
            cost_per_1k_input_tokens=0.003,
            cost_per_1k_output_tokens=0.015
        ),
        "gpt-4-turbo": LLMCapability(
            name="gpt-4-turbo",
            display_name="GPT-4 Turbo",
            provider=LLMProvider.OPENAI,
            api_endpoint="https://api.openai.com/v1",
            description="OpenAI's advanced reasoning model",
            capabilities=["chat", "streaming", "vision", "function-calling"],
            context_window=128000,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_vision=True,
            supports_function_calling=True,
            rate_limit_per_minute=500,
            rate_limit_per_day=10000,
            cost_per_1k_input_tokens=0.01,
            cost_per_1k_output_tokens=0.03
        ),
        "gpt-4o": LLMCapability(
            name="gpt-4o",
            display_name="GPT-4o",
            provider=LLMProvider.OPENAI,
            api_endpoint="https://api.openai.com/v1",
            description="OpenAI's multimodal flagship model",
            capabilities=["chat", "streaming", "vision", "function-calling", "audio"],
            context_window=128000,
            max_output_tokens=16384,
            supports_streaming=True,
            supports_vision=True,
            supports_function_calling=True,
            rate_limit_per_minute=500,
            rate_limit_per_day=10000,
            cost_per_1k_input_tokens=0.0025,
            cost_per_1k_output_tokens=0.01
        ),
        "deepseek-chat": LLMCapability(
            name="deepseek-chat",
            display_name="DeepSeek Chat",
            provider=LLMProvider.DEEPSEEK,
            api_endpoint="https://api.deepseek.com/v1",
            description="Cost-effective model with strong reasoning capabilities",
            capabilities=["chat", "streaming", "function-calling"],
            context_window=64000,
            max_output_tokens=4096,
            supports_streaming=True,
            supports_vision=False,
            supports_function_calling=True,
            rate_limit_per_minute=60,
            rate_limit_per_day=10000,
            cost_per_1k_input_tokens=0.00014,
            cost_per_1k_output_tokens=0.00028
        ),
    }
    
    @classmethod
    def get_all_models(cls) -> Dict[str, LLMCapability]:
        """Get all available LLM models"""
        return cls.CHAT_MODELS
    
    @classmethod
    def get_model(cls, model_name: str) -> Optional[LLMCapability]:
        """Get specific LLM model by name"""
        return cls.CHAT_MODELS.get(model_name)
    
    @classmethod
    def get_models_by_provider(cls, provider: LLMProvider) -> Dict[str, LLMCapability]:
        """Get all models from a specific provider"""
        return {
            name: model 
            for name, model in cls.CHAT_MODELS.items() 
            if model.provider == provider
        }
    
    @classmethod
    def get_models_with_capability(cls, capability: str) -> Dict[str, LLMCapability]:
        """Get all models that support a specific capability"""
        return {
            name: model 
            for name, model in cls.CHAT_MODELS.items() 
            if capability in model.capabilities
        }
    
    @classmethod
    def list_all_models(cls) -> List[Dict]:
        """List all LLM models with their basic info"""
        models = []
        for model_name, capability in cls.CHAT_MODELS.items():
            models.append({
                "name": model_name,
                "display_name": capability.display_name,
                "provider": capability.provider.value,
                "description": capability.description,
                "capabilities": capability.capabilities,
                "context_window": capability.context_window,
                "supports_streaming": capability.supports_streaming,
                "supports_vision": capability.supports_vision,
                "supports_function_calling": capability.supports_function_calling,
            })
        return models
    
    @classmethod
    def get_default_model(cls) -> str:
        """Get the default LLM model name"""
        return "gemini-2.5-flash"