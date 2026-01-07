"""
API Routes for Video Segment Generation
Handles step-by-step video segment generation with preview capabilities
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database import get_db
from database_models import VideoSegment, Episode
from services.segment_generation_service import SegmentGenerationService
from utils.websocket_manager import ws_manager
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/segments", tags=["segments"])


# Request/Response Models
class GenerateSegmentRequest(BaseModel):
    episode_id: str
    segment_number: int
    scene_script: Dict[str, Any]
    generation_params: Dict[str, Any] = Field(default_factory=dict)


class GenerateSegmentsRequest(BaseModel):
    episode_id: str
    scene_scripts: List[Dict[str, Any]]
    generation_params: Dict[str, Any] = Field(default_factory=dict)
    mode: str = Field(default="sequential", description="Generation mode: sequential or parallel")
    start_from: int = Field(default=0, description="Start from specific segment (for resume)")
    auto_approve: bool = Field(default=False, description="Auto-approve segments after generation")


class RegenerateSegmentRequest(BaseModel):
    changes: Dict[str, Any] = Field(default_factory=dict)


class SegmentResponse(BaseModel):
    id: str
    episode_id: str
    segment_number: int
    status: str
    approval_status: Optional[str]
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    duration: Optional[float]
    quality_score: Optional[float]
    version: int
    created_at: str
    
    class Config:
        from_attributes = True


class SegmentStatusResponse(BaseModel):
    total_segments: int
    completed: int
    approved: int
    rejected: int
    pending: int
    segments: List[Dict[str, Any]]


# Helper function to get service
def get_segment_service(db: Session = Depends(get_db)) -> SegmentGenerationService:
    """Get segment generation service instance"""
    from pipelines.idea2video_pipeline import Idea2VideoPipeline
    
    # Initialize pipeline from config
    pipeline = Idea2VideoPipeline.init_from_config("configs/idea2video.yaml")
    
    # Create service
    service = SegmentGenerationService(
        chat_model=pipeline.chat_model,
        image_generator=pipeline.image_generator,
        video_generator=pipeline.video_generator,
        working_dir=pipeline.working_dir,
        db_session=db
    )
    
    return service


# WebSocket progress callback
async def segment_progress_callback(segment_id: Optional[str], status: str, progress: float, message: str):
    """Send progress updates via WebSocket"""
    try:
        await ws_manager.broadcast_to_room(
            room=f"segment_{segment_id}" if segment_id else "segments",
            message={
                "type": "segment_progress",
                "segment_id": segment_id,
                "status": status,
                "progress": progress,
                "message": message
            }
        )
    except Exception as e:
        logger.error(f"Failed to send progress update: {e}")


# Endpoints

@router.post("/generate", response_model=SegmentResponse)
async def generate_segment(
    request: GenerateSegmentRequest,
    background_tasks: BackgroundTasks,
    service: SegmentGenerationService = Depends(get_segment_service),
    db: Session = Depends(get_db)
):
    """
    Generate a single video segment
    
    - **episode_id**: Episode ID
    - **segment_number**: Segment number in sequence
    - **scene_script**: Scene script data
    - **generation_params**: Generation parameters (style, seed, etc.)
    """
    try:
        logger.info(f"Generating segment {request.segment_number} for episode {request.episode_id}")
        
        # Generate segment
        segment = await service.generate_segment(
            episode_id=request.episode_id,
            segment_number=request.segment_number,
            scene_script=request.scene_script,
            generation_params=request.generation_params,
            progress_callback=segment_progress_callback
        )
        
        return SegmentResponse.model_validate(segment)
        
    except Exception as e:
        logger.error(f"Failed to generate segment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-batch")
async def generate_segments_batch(
    request: GenerateSegmentsRequest,
    background_tasks: BackgroundTasks,
    service: SegmentGenerationService = Depends(get_segment_service),
    db: Session = Depends(get_db)
):
    """
    Generate multiple segments in sequence or parallel
    
    - **episode_id**: Episode ID
    - **scene_scripts**: List of scene scripts
    - **generation_params**: Generation parameters
    - **mode**: Generation mode (sequential or parallel)
    - **start_from**: Start from specific segment (for resume)
    - **auto_approve**: Auto-approve segments after generation
    """
    try:
        logger.info(f"Starting batch generation: {len(request.scene_scripts)} segments, mode={request.mode}")
        
        # Verify episode exists
        episode = db.query(Episode).filter(Episode.id == request.episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail=f"Episode not found: {request.episode_id}")
        
        # Start generation in background
        async def generate_task():
            try:
                segments = await service.generate_segments_sequential(
                    episode_id=request.episode_id,
                    scene_scripts=request.scene_scripts,
                    generation_params=request.generation_params,
                    progress_callback=segment_progress_callback,
                    start_from=request.start_from
                )
                
                # Auto-approve if requested
                if request.auto_approve:
                    from services.segment_review_service import SegmentReviewService
                    review_service = SegmentReviewService(db)
                    for segment in segments:
                        review_service.approve_segment(
                            segment_id=segment.id,
                            user_id="system",
                            feedback="Auto-approved"
                        )
                
                logger.info(f"Batch generation completed: {len(segments)} segments")
                
            except Exception as e:
                logger.error(f"Batch generation failed: {e}", exc_info=True)
                await segment_progress_callback(None, 'failed', 0, f"Batch generation failed: {str(e)}")
        
        # Run in background
        background_tasks.add_task(generate_task)
        
        return {
            "status": "started",
            "episode_id": request.episode_id,
            "total_segments": len(request.scene_scripts),
            "mode": request.mode,
            "message": "Segment generation started in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start batch generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{segment_id}", response_model=SegmentResponse)
async def get_segment(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """Get segment details by ID"""
    segment = db.query(VideoSegment).filter(VideoSegment.id == segment_id).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail=f"Segment not found: {segment_id}")
    
    return SegmentResponse.model_validate(segment)


@router.get("/{segment_id}/video")
async def get_segment_video(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """Download segment video file"""
    segment = db.query(VideoSegment).filter(VideoSegment.id == segment_id).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail=f"Segment not found: {segment_id}")
    
    if not segment.video_url or not os.path.exists(segment.video_url):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        segment.video_url,
        media_type="video/mp4",
        filename=f"segment_{segment.segment_number}.mp4"
    )


@router.get("/{segment_id}/thumbnail")
async def get_segment_thumbnail(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """Download segment thumbnail image"""
    segment = db.query(VideoSegment).filter(VideoSegment.id == segment_id).first()
    
    if not segment:
        raise HTTPException(status_code=404, detail=f"Segment not found: {segment_id}")
    
    if not segment.thumbnail_url or not os.path.exists(segment.thumbnail_url):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(
        segment.thumbnail_url,
        media_type="image/jpeg",
        filename=f"segment_{segment.segment_number}_thumb.jpg"
    )


@router.post("/{segment_id}/regenerate", response_model=SegmentResponse)
async def regenerate_segment(
    segment_id: str,
    request: RegenerateSegmentRequest,
    background_tasks: BackgroundTasks,
    service: SegmentGenerationService = Depends(get_segment_service),
    db: Session = Depends(get_db)
):
    """
    Regenerate a specific segment with modifications
    
    - **segment_id**: Segment ID to regenerate
    - **changes**: Dictionary of changes to apply
    """
    try:
        logger.info(f"Regenerating segment: {segment_id}")
        
        # Verify segment exists
        segment = db.query(VideoSegment).filter(VideoSegment.id == segment_id).first()
        if not segment:
            raise HTTPException(status_code=404, detail=f"Segment not found: {segment_id}")
        
        # Regenerate segment
        new_segment = await service.regenerate_segment(
            segment_id=segment_id,
            changes=request.changes,
            progress_callback=segment_progress_callback
        )
        
        return SegmentResponse.model_validate(new_segment)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate segment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/status", response_model=SegmentStatusResponse)
async def get_episode_segments_status(
    episode_id: str,
    service: SegmentGenerationService = Depends(get_segment_service),
    db: Session = Depends(get_db)
):
    """
    Get status of all segments for an episode
    
    Returns statistics and list of all segments
    """
    try:
        # Verify episode exists
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail=f"Episode not found: {episode_id}")
        
        status = service.get_segment_status(episode_id)
        return SegmentStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get segment status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/list")
async def list_episode_segments(
    episode_id: str,
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all segments for an episode with optional filtering
    
    - **status**: Filter by status (pending, generating, completed, failed)
    - **approval_status**: Filter by approval status (approved, rejected, null)
    """
    try:
        query = db.query(VideoSegment).filter(VideoSegment.episode_id == episode_id)
        
        if status:
            query = query.filter(VideoSegment.status == status)
        
        if approval_status:
            if approval_status == "null":
                query = query.filter(VideoSegment.approval_status.is_(None))
            else:
                query = query.filter(VideoSegment.approval_status == approval_status)
        
        segments = query.order_by(VideoSegment.segment_number).all()
        
        return {
            "episode_id": episode_id,
            "total": len(segments),
            "segments": [s.to_dict() for s in segments]
        }
        
    except Exception as e:
        logger.error(f"Failed to list segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{segment_id}")
async def delete_segment(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """Delete a segment and its files"""
    try:
        segment = db.query(VideoSegment).filter(VideoSegment.id == segment_id).first()
        
        if not segment:
            raise HTTPException(status_code=404, detail=f"Segment not found: {segment_id}")
        
        # Delete files
        if segment.video_url and os.path.exists(segment.video_url):
            os.remove(segment.video_url)
        
        if segment.thumbnail_url and os.path.exists(segment.thumbnail_url):
            os.remove(segment.thumbnail_url)
        
        # Delete from database
        db.delete(segment)
        db.commit()
        
        logger.info(f"Segment deleted: {segment_id}")
        
        return {"status": "deleted", "segment_id": segment_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete segment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{segment_id}/versions")
async def get_segment_versions(
    segment_id: str,
    db: Session = Depends(get_db)
):
    """Get all versions of a segment (including regenerations)"""
    try:
        from services.segment_review_service import SegmentReviewService
        review_service = SegmentReviewService(db)
        
        versions = review_service.get_segment_versions(segment_id)
        
        return {
            "segment_id": segment_id,
            "total_versions": len(versions),
            "versions": versions
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get segment versions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))