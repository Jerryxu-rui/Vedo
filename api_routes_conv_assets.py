"""
Conversational API - Assets Module
对话式API - 资产管理模块

Handles asset management and library including:
- Shot management
- Cross-episode asset management
- Asset reuse
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from database import get_db
from database_models import Shot, Scene

# Import from shared module
from api_routes_conv_shared import (
    # Models
    UpdateShotRequest,
    
    # Helpers
    validate_episode_exists
)

# Create router
router = APIRouter(
    prefix="/api/v1/conversational",
    tags=["conversational-assets"]
)


# ============================================================================
# Request Models
# ============================================================================

class CreateShotRequest(BaseModel):
    """Request model for creating a new shot"""
    scene_id: str
    shot_number: int
    visual_desc: str
    camera_angle: str = "MEDIUM SHOT"
    camera_movement: Optional[str] = "STATIC"
    dialogue: Optional[str] = None
    voice_actor: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/episode/{episode_id}/shots")
async def create_shot(
    episode_id: str,
    request: CreateShotRequest,
    db: Session = Depends(get_db)
):
    """
    创建新分镜
    
    Create a new shot in the storyboard.
    
    Args:
        episode_id: Episode ID
        request: Shot creation request
        db: Database session
        
    Returns:
        Created shot data
    """
    try:
        validate_episode_exists(episode_id, db)
        
        # Verify scene exists and belongs to this episode
        scene = db.query(Scene).filter(Scene.id == request.scene_id).first()
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        if scene.episode_id != episode_id:
            raise HTTPException(status_code=400, detail="Scene does not belong to this episode")
        
        # Create new shot
        new_shot = Shot(
            scene_id=request.scene_id,
            shot_number=request.shot_number,
            visual_desc=request.visual_desc,
            camera_angle=request.camera_angle,
            camera_movement=request.camera_movement,
            dialogue=request.dialogue,
            voice_actor=request.voice_actor,
            status="pending"
        )
        
        db.add(new_shot)
        db.commit()
        db.refresh(new_shot)
        
        return {"message": "Shot created", "shot": new_shot.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/episode/{episode_id}/shots/{shot_id}")
async def update_shot(
    episode_id: str,
    shot_id: str,
    request: UpdateShotRequest,
    db: Session = Depends(get_db)
):
    """
    编辑单个分镜的属性
    
    Update a single shot's properties.
    
    Args:
        episode_id: Episode ID
        shot_id: Shot ID
        request: Update request with optional fields
        db: Database session
        
    Returns:
        Updated shot data
    """
    try:
        validate_episode_exists(episode_id, db)
        
        shot = db.query(Shot).filter(Shot.id == shot_id).first()
        
        if not shot:
            raise HTTPException(status_code=404, detail="Shot not found")
        
        # Verify shot belongs to this episode
        scene = db.query(Scene).filter(Scene.id == shot.scene_id).first()
        if not scene or scene.episode_id != episode_id:
            raise HTTPException(status_code=404, detail="Shot not found in this episode")
        
        # Update only provided fields
        if request.visual_desc is not None:
            shot.visual_desc = request.visual_desc
        if request.camera_angle is not None:
            shot.camera_angle = request.camera_angle
        if request.camera_movement is not None:
            shot.camera_movement = request.camera_movement
        if request.dialogue is not None:
            shot.dialogue = request.dialogue
        if request.voice_actor is not None:
            shot.voice_actor = request.voice_actor
        
        shot.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Shot updated", "shot": shot.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/episode/{episode_id}/shots/{shot_id}")
async def delete_shot(
    episode_id: str,
    shot_id: str,
    db: Session = Depends(get_db)
):
    """
    删除单个分镜
    
    Delete a single shot.
    
    Args:
        episode_id: Episode ID
        shot_id: Shot ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        validate_episode_exists(episode_id, db)
        
        shot = db.query(Shot).filter(Shot.id == shot_id).first()
        
        if not shot:
            raise HTTPException(status_code=404, detail="Shot not found")
        
        # Verify shot belongs to this episode
        scene = db.query(Scene).filter(Scene.id == shot.scene_id).first()
        if not scene or scene.episode_id != episode_id:
            raise HTTPException(status_code=404, detail="Shot not found in this episode")
        
        db.delete(shot)
        db.commit()
        
        return {"message": "Shot deleted", "shot_id": shot_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))