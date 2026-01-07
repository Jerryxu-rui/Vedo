"""
Conversational API - Progress Module
对话式API - 进度跟踪模块

Handles progress tracking and monitoring including:
- Real-time progress tracking
- Phase status monitoring
- Error reporting
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db

# Import from shared module
from api_routes_conv_shared import (
    # Helpers
    get_or_create_workflow,
    validate_episode_exists
)

# Create router
router = APIRouter(
    prefix="/api/v1/conversational",
    tags=["conversational-progress"]
)


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/episode/{episode_id}/progress")
async def get_generation_progress(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    获取生成进度
    
    Get real-time generation progress for an episode.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Progress information including state, percentage, and step info
    """
    try:
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        return {
            "episode_id": episode_id,
            "state": workflow.state,
            "progress_percentage": workflow._calculate_progress(),
            "step_info": workflow.get_current_step_info(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))