"""
Model Registry Service
Manages available models for video and image generation
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ModelCategory(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    CHAT = "chat"


@dataclass
class ModelCapability:
    """Model capability specification"""
    name: str
    category: ModelCategory
    provider: str
    api_endpoint: str
    supported_resolutions: List[str]
    supported_aspect_ratios: List[str]
    supported_fps: List[int]
    supported_durations: List[int]
    max_resolution: str
    default_resolution: str
    default_aspect_ratio: str
    default_fps: int
    default_duration: int
    rate_limit_per_minute: Optional[int]
    rate_limit_per_day: Optional[int]
    description: str
    features: List[str]


class ModelRegistry:
    """Registry of available models with their capabilities"""
    
    VIDEO_MODELS = {
        "veo3-fast": ModelCapability(
            name="veo3-fast",
            category=ModelCategory.VIDEO,
            provider="yunwu",
            api_endpoint="https://yunwu.ai",
            supported_resolutions=["480p", "720p", "1080p"],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_fps=[16, 24, 30],
            supported_durations=[5, 10],
            max_resolution="1080p",
            default_resolution="720p",
            default_aspect_ratio="16:9",
            default_fps=24,
            default_duration=5,
            rate_limit_per_minute=10,
            rate_limit_per_day=100,
            description="Fast video generation with Veo 3",
            features=["text-to-video", "image-to-video", "fast-generation"]
        ),
        "veo3-pro-frames": ModelCapability(
            name="veo3-pro-frames",
            category=ModelCategory.VIDEO,
            provider="yunwu",
            api_endpoint="https://yunwu.ai",
            supported_resolutions=["720p", "1080p", "4K"],
            supported_aspect_ratios=["16:9", "9:16", "1:1", "21:9"],
            supported_fps=[24, 30, 60],
            supported_durations=[5, 10, 15],
            max_resolution="4K",
            default_resolution="1080p",
            default_aspect_ratio="16:9",
            default_fps=30,
            default_duration=10,
            rate_limit_per_minute=5,
            rate_limit_per_day=50,
            description="Professional video generation with Veo 3 Pro",
            features=["text-to-video", "image-to-video", "high-quality", "frame-interpolation"]
        ),
        "veo_3_1-fast": ModelCapability(
            name="veo_3_1-fast",
            category=ModelCategory.VIDEO,
            provider="yunwu",
            api_endpoint="https://yunwu.ai",
            supported_resolutions=["480p", "720p", "1080p"],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_fps=[24, 30],
            supported_durations=[5, 10],
            max_resolution="1080p",
            default_resolution="720p",
            default_aspect_ratio="16:9",
            default_fps=24,
            default_duration=5,
            rate_limit_per_minute=10,
            rate_limit_per_day=100,
            description="Latest Veo 3.1 fast generation model",
            features=["text-to-video", "image-to-video", "improved-quality", "fast-generation"]
        ),
        "sora-2-all": ModelCapability(
            name="sora-2-all",
            category=ModelCategory.VIDEO,
            provider="yunwu",
            api_endpoint="https://yunwu.ai",
            supported_resolutions=["720p", "1080p", "4K"],
            supported_aspect_ratios=["16:9", "9:16", "1:1", "21:9"],
            supported_fps=[24, 30],
            supported_durations=[5, 10, 20],
            max_resolution="4K",
            default_resolution="1080p",
            default_aspect_ratio="16:9",
            default_fps=24,
            default_duration=10,
            rate_limit_per_minute=3,
            rate_limit_per_day=30,
            description="OpenAI Sora 2 - Advanced video generation",
            features=["text-to-video", "image-to-video", "long-duration", "cinematic-quality"]
        ),
        "MiniMax-Hailuo-02": ModelCapability(
            name="MiniMax-Hailuo-02",
            category=ModelCategory.VIDEO,
            provider="yunwu",
            api_endpoint="https://yunwu.ai",
            supported_resolutions=["720p", "1080p"],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_fps=[24, 30],
            supported_durations=[5, 10],
            max_resolution="1080p",
            default_resolution="720p",
            default_aspect_ratio="16:9",
            default_fps=24,
            default_duration=5,
            rate_limit_per_minute=8,
            rate_limit_per_day=80,
            description="MiniMax Hailuo 02 - Efficient video generation",
            features=["text-to-video", "image-to-video", "fast-processing"]
        ),
        "wan2.6-i2v": ModelCapability(
            name="wan2.6-i2v",
            category=ModelCategory.VIDEO,
            provider="yunwu",
            api_endpoint="https://yunwu.ai",
            supported_resolutions=["720p", "1080p"],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_fps=[24, 30],
            supported_durations=[5, 10],
            max_resolution="1080p",
            default_resolution="720p",
            default_aspect_ratio="16:9",
            default_fps=24,
            default_duration=5,
            rate_limit_per_minute=10,
            rate_limit_per_day=100,
            description="Wan 2.6 Image-to-Video specialized model",
            features=["image-to-video", "smooth-motion", "style-preservation"]
        ),
        "runwayml-gen3a_turbo-5": ModelCapability(
            name="runwayml-gen3a_turbo-5",
            category=ModelCategory.VIDEO,
            provider="yunwu",
            api_endpoint="https://yunwu.ai",
            supported_resolutions=["720p", "1080p"],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_fps=[24, 30],
            supported_durations=[5],
            max_resolution="1080p",
            default_resolution="720p",
            default_aspect_ratio="16:9",
            default_fps=24,
            default_duration=5,
            rate_limit_per_minute=12,
            rate_limit_per_day=120,
            description="RunwayML Gen-3 Alpha Turbo - Fast generation",
            features=["text-to-video", "image-to-video", "turbo-speed", "creative-control"]
        ),
    }
    
    IMAGE_MODELS = {
        "doubao-seedream-4-0-250828": ModelCapability(
            name="doubao-seedream-4-0-250828",
            category=ModelCategory.IMAGE,
            provider="yunwu",
            api_endpoint="https://yunwu.ai/v1/images/generations",
            supported_resolutions=["1024x1024", "2048x2048", "4096x4096"],
            supported_aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4"],
            supported_fps=[],
            supported_durations=[],
            max_resolution="4096x4096",
            default_resolution="1024x1024",
            default_aspect_ratio="1:1",
            default_fps=0,
            default_duration=0,
            rate_limit_per_minute=10,
            rate_limit_per_day=500,
            description="Doubao Seedream 4.0 - High quality image generation",
            features=["text-to-image", "image-to-image", "high-resolution", "style-control"]
        ),
        "nanobanana": ModelCapability(
            name="nanobanana",
            category=ModelCategory.IMAGE,
            provider="yunwu",
            api_endpoint="https://yunwu.ai",
            supported_resolutions=["1024x1024", "2048x2048"],
            supported_aspect_ratios=["1:1", "16:9", "9:16"],
            supported_fps=[],
            supported_durations=[],
            max_resolution="2048x2048",
            default_resolution="1024x1024",
            default_aspect_ratio="1:1",
            default_fps=0,
            default_duration=0,
            rate_limit_per_minute=10,
            rate_limit_per_day=50,
            description="Nanobanana - Fast image generation",
            features=["text-to-image", "fast-generation"]
        ),
        "gemini-3-pro-image-preview": ModelCapability(
            name="gemini-3-pro-image-preview",
            category=ModelCategory.IMAGE,
            provider="yunwu",
            api_endpoint="https://yunwu.ai/v1/images/generations",
            supported_resolutions=["1024x1024", "2048x2048", "4096x4096"],
            supported_aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"],
            supported_fps=[],
            supported_durations=[],
            max_resolution="4096x4096",
            default_resolution="2048x2048",
            default_aspect_ratio="1:1",
            default_fps=0,
            default_duration=0,
            rate_limit_per_minute=15,
            rate_limit_per_day=200,
            description="Gemini 3 Pro Image Preview - Advanced image generation",
            features=["text-to-image", "image-to-image", "ultra-high-resolution", "photorealistic"]
        ),
        "gemini-2.5-flash-image-preview": ModelCapability(
            name="gemini-2.5-flash-image-preview",
            category=ModelCategory.IMAGE,
            provider="yunwu",
            api_endpoint="https://yunwu.ai/v1/images/generations",
            supported_resolutions=["1024x1024", "2048x2048"],
            supported_aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4"],
            supported_fps=[],
            supported_durations=[],
            max_resolution="2048x2048",
            default_resolution="1024x1024",
            default_aspect_ratio="1:1",
            default_fps=0,
            default_duration=0,
            rate_limit_per_minute=20,
            rate_limit_per_day=300,
            description="Gemini 2.5 Flash Image Preview - Fast image generation",
            features=["text-to-image", "fast-generation", "good-quality"]
        ),
    }
    
    @classmethod
    def get_video_models(cls) -> Dict[str, ModelCapability]:
        """Get all available video generation models"""
        return cls.VIDEO_MODELS
    
    @classmethod
    def get_image_models(cls) -> Dict[str, ModelCapability]:
        """Get all available image generation models"""
        return cls.IMAGE_MODELS
    
    @classmethod
    def get_model(cls, model_name: str) -> Optional[ModelCapability]:
        """Get specific model by name"""
        if model_name in cls.VIDEO_MODELS:
            return cls.VIDEO_MODELS[model_name]
        if model_name in cls.IMAGE_MODELS:
            return cls.IMAGE_MODELS[model_name]
        return None
    
    @classmethod
    def get_models_by_category(cls, category: ModelCategory) -> Dict[str, ModelCapability]:
        """Get all models in a specific category"""
        if category == ModelCategory.VIDEO:
            return cls.VIDEO_MODELS
        elif category == ModelCategory.IMAGE:
            return cls.IMAGE_MODELS
        return {}
    
    @classmethod
    def list_all_models(cls) -> List[Dict]:
        """List all models with their basic info"""
        models = []
        for model_name, capability in {**cls.VIDEO_MODELS, **cls.IMAGE_MODELS}.items():
            models.append({
                "name": model_name,
                "category": capability.category.value,
                "provider": capability.provider,
                "description": capability.description,
                "features": capability.features,
                "max_resolution": capability.max_resolution,
            })
        return models