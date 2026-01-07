"""
API routes for model management and selection
Provides endpoints for listing available models and managing user preferences
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database import get_db
from database_models import UserModelPreference, AvailableModel
from services.model_registry import ModelRegistry, ModelCategory
from services.llm_registry import LLMRegistry
from datetime import datetime

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class ModelInfo(BaseModel):
    """Model information response"""
    name: str
    category: str
    provider: str
    description: str
    features: List[str]
    max_resolution: Optional[str] = None
    supported_resolutions: Optional[List[str]] = None
    supported_aspect_ratios: Optional[List[str]] = None
    default_resolution: Optional[str] = None
    default_aspect_ratio: Optional[str] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    # LLM-specific fields
    context_window: Optional[int] = None
    input_cost_per_1m_tokens: Optional[float] = None
    output_cost_per_1m_tokens: Optional[float] = None
    capabilities: Optional[List[str]] = None


class ModelPreferenceRequest(BaseModel):
    """Request to update model preferences"""
    video_model: Optional[str] = Field(None, description="Preferred video generation model")
    image_model: Optional[str] = Field(None, description="Preferred image generation model")
    chat_model: Optional[str] = Field(None, description="Preferred chat model")


class ModelPreferenceResponse(BaseModel):
    """Model preference response"""
    user_id: str
    video_model: Optional[str]
    image_model: Optional[str]
    chat_model: Optional[str]
    created_at: str
    updated_at: str


@router.get("/available", response_model=Dict[str, List[ModelInfo]])
async def get_available_models():
    """
    Get all available models grouped by category
    
    Returns:
        Dictionary with categories as keys and lists of models as values
    """
    try:
        video_models = []
        for model_name, capability in ModelRegistry.get_video_models().items():
            video_models.append(ModelInfo(
                name=capability.name,
                category=capability.category.value,
                provider=capability.provider,
                description=capability.description,
                features=capability.features,
                max_resolution=capability.max_resolution,
                supported_resolutions=capability.supported_resolutions,
                supported_aspect_ratios=capability.supported_aspect_ratios,
                default_resolution=capability.default_resolution,
                default_aspect_ratio=capability.default_aspect_ratio,
                rate_limit_per_minute=capability.rate_limit_per_minute,
                rate_limit_per_day=capability.rate_limit_per_day,
            ))
        
        image_models = []
        for model_name, capability in ModelRegistry.get_image_models().items():
            image_models.append(ModelInfo(
                name=capability.name,
                category=capability.category.value,
                provider=capability.provider,
                description=capability.description,
                features=capability.features,
                max_resolution=capability.max_resolution,
                supported_resolutions=capability.supported_resolutions,
                supported_aspect_ratios=capability.supported_aspect_ratios,
                default_resolution=capability.default_resolution,
                default_aspect_ratio=capability.default_aspect_ratio,
                rate_limit_per_minute=capability.rate_limit_per_minute,
                rate_limit_per_day=capability.rate_limit_per_day,
            ))
        
        # Get LLM models
        llm_models = []
        for model_name, capability in LLMRegistry.get_all_models().items():
            # Convert cost from per 1k to per 1M tokens
            input_cost_per_1m = capability.cost_per_1k_input_tokens * 1000 if capability.cost_per_1k_input_tokens else None
            output_cost_per_1m = capability.cost_per_1k_output_tokens * 1000 if capability.cost_per_1k_output_tokens else None
            
            llm_models.append(ModelInfo(
                name=capability.name,
                category="llm",
                provider=capability.provider.value,
                description=f"Context: {capability.context_window:,} tokens",
                features=capability.capabilities,
                context_window=capability.context_window,
                input_cost_per_1m_tokens=input_cost_per_1m,
                output_cost_per_1m_tokens=output_cost_per_1m,
                capabilities=capability.capabilities,
            ))
        
        return {
            "video": video_models,
            "image": image_models,
            "llm": llm_models,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@router.get("/available/{category}")
async def get_models_by_category(category: str):
    """
    Get available models for a specific category
    
    Args:
        category: Model category (video, image, chat)
    """
    try:
        if category == "video":
            models = ModelRegistry.get_video_models()
            result = []
            for model_name, capability in models.items():
                result.append({
                    "name": capability.name,
                    "description": capability.description,
                    "features": capability.features,
                    "max_resolution": capability.max_resolution,
                    "supported_resolutions": capability.supported_resolutions,
                    "supported_aspect_ratios": capability.supported_aspect_ratios,
                    "default_resolution": capability.default_resolution,
                    "default_aspect_ratio": capability.default_aspect_ratio,
                    "rate_limits": {
                        "per_minute": capability.rate_limit_per_minute,
                        "per_day": capability.rate_limit_per_day,
                    }
                })
        elif category == "image":
            models = ModelRegistry.get_image_models()
            result = []
            for model_name, capability in models.items():
                result.append({
                    "name": capability.name,
                    "description": capability.description,
                    "features": capability.features,
                    "max_resolution": capability.max_resolution,
                    "supported_resolutions": capability.supported_resolutions,
                    "supported_aspect_ratios": capability.supported_aspect_ratios,
                    "default_resolution": capability.default_resolution,
                    "default_aspect_ratio": capability.default_aspect_ratio,
                    "rate_limits": {
                        "per_minute": capability.rate_limit_per_minute,
                        "per_day": capability.rate_limit_per_day,
                    }
                })
        elif category == "llm":
            models = LLMRegistry.get_all_models()
            result = []
            for model_name, capability in models.items():
                # Convert cost from per 1k to per 1M tokens
                input_cost_per_1m = capability.cost_per_1k_input_tokens * 1000 if capability.cost_per_1k_input_tokens else None
                output_cost_per_1m = capability.cost_per_1k_output_tokens * 1000 if capability.cost_per_1k_output_tokens else None
                
                result.append({
                    "name": capability.name,
                    "provider": capability.provider.value,
                    "description": f"Context: {capability.context_window:,} tokens",
                    "capabilities": capability.capabilities,
                    "context_window": capability.context_window,
                    "costs": {
                        "input_per_1m_tokens": input_cost_per_1m,
                        "output_per_1m_tokens": output_cost_per_1m,
                    }
                })
        else:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}. Must be 'video', 'image', or 'llm'")
        
        return {
            "category": category,
            "models": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")


@router.get("/model/{model_name}")
async def get_model_details(model_name: str):
    """
    Get detailed information about a specific model
    
    Args:
        model_name: Name of the model
    """
    try:
        # Try video/image models first
        capability = ModelRegistry.get_model(model_name)
        if capability:
            return {
                "name": capability.name,
                "category": capability.category.value,
                "provider": capability.provider,
                "description": capability.description,
                "features": capability.features,
                "api_endpoint": capability.api_endpoint,
                "specifications": {
                    "supported_resolutions": capability.supported_resolutions,
                    "supported_aspect_ratios": capability.supported_aspect_ratios,
                    "supported_fps": capability.supported_fps,
                    "supported_durations": capability.supported_durations,
                    "max_resolution": capability.max_resolution,
                    "defaults": {
                        "resolution": capability.default_resolution,
                        "aspect_ratio": capability.default_aspect_ratio,
                        "fps": capability.default_fps,
                        "duration": capability.default_duration,
                    }
                },
                "rate_limits": {
                    "per_minute": capability.rate_limit_per_minute,
                    "per_day": capability.rate_limit_per_day,
                }
            }
        
        # Try LLM models
        llm_capability = LLMRegistry.get_model(model_name)
        if llm_capability:
            # Convert cost from per 1k to per 1M tokens
            input_cost_per_1m = llm_capability.cost_per_1k_input_tokens * 1000 if llm_capability.cost_per_1k_input_tokens else None
            output_cost_per_1m = llm_capability.cost_per_1k_output_tokens * 1000 if llm_capability.cost_per_1k_output_tokens else None
            
            return {
                "name": llm_capability.name,
                "category": "llm",
                "provider": llm_capability.provider.value,
                "description": f"Context: {llm_capability.context_window:,} tokens",
                "capabilities": llm_capability.capabilities,
                "context_window": llm_capability.context_window,
                "costs": {
                    "input_per_1m_tokens": input_cost_per_1m,
                    "output_per_1m_tokens": output_cost_per_1m,
                }
            }
        
        raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch model details: {str(e)}")


@router.get("/preferences/{user_id}", response_model=ModelPreferenceResponse)
async def get_user_preferences(user_id: str, db: Session = Depends(get_db)):
    """
    Get user's model preferences
    
    Args:
        user_id: User ID
    """
    try:
        preference = db.query(UserModelPreference).filter(
            UserModelPreference.user_id == user_id
        ).first()
        
        if not preference:
            # Return default preferences
            return ModelPreferenceResponse(
                user_id=user_id,
                video_model="veo3-fast",
                image_model="doubao-seedream-4-0-250828",
                chat_model="gemini-2.0-flash-001",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
        
        return ModelPreferenceResponse(
            user_id=preference.user_id,
            video_model=preference.video_model,
            image_model=preference.image_model,
            chat_model=preference.chat_model,
            created_at=preference.created_at.isoformat() if preference.created_at else None,
            updated_at=preference.updated_at.isoformat() if preference.updated_at else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch preferences: {str(e)}")


@router.put("/preferences/{user_id}", response_model=ModelPreferenceResponse)
async def update_user_preferences(
    user_id: str,
    request: ModelPreferenceRequest,
    db: Session = Depends(get_db)
):
    """
    Update user's model preferences
    
    Args:
        user_id: User ID
        request: Model preference update request
    """
    try:
        # Validate models exist
        if request.video_model and not ModelRegistry.get_model(request.video_model):
            raise HTTPException(status_code=400, detail=f"Invalid video model: {request.video_model}")
        if request.image_model and not ModelRegistry.get_model(request.image_model):
            raise HTTPException(status_code=400, detail=f"Invalid image model: {request.image_model}")
        
        # Get or create preference
        preference = db.query(UserModelPreference).filter(
            UserModelPreference.user_id == user_id
        ).first()
        
        if not preference:
            preference = UserModelPreference(
                user_id=user_id,
                video_model=request.video_model or "veo3-fast",
                image_model=request.image_model or "doubao-seedream-4-0-250828",
                chat_model=request.chat_model or "gemini-2.0-flash-001",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(preference)
        else:
            if request.video_model:
                preference.video_model = request.video_model
            if request.image_model:
                preference.image_model = request.image_model
            if request.chat_model:
                preference.chat_model = request.chat_model
            preference.updated_at = datetime.now()
        
        db.commit()
        db.refresh(preference)
        
        return ModelPreferenceResponse(
            user_id=preference.user_id,
            video_model=preference.video_model,
            image_model=preference.image_model,
            chat_model=preference.chat_model,
            created_at=preference.created_at.isoformat() if preference.created_at else None,
            updated_at=preference.updated_at.isoformat() if preference.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


@router.get("/defaults")
async def get_default_models():
    """Get default model selections"""
    return {
        "video_model": "veo3-fast",
        "image_model": "doubao-seedream-4-0-250828",
        "chat_model": "gemini-2.0-flash-001",
        "description": "Default models for new users"
    }