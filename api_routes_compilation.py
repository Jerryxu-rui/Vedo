"""
API Routes for Video Segment Compilation
Handles compilation of approved video segments into final video
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database import get_db
from database_models import SegmentCompilationJob, Episode
from services.segment_compilation_service import SegmentCompilationService
from utils.websocket_manager import ws_manager
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compilation", tags=["compilation"])


# Request/Response Models
class CompileSegmentsRequest(BaseModel):
    episode_id: str
    segment_ids: Optional[List[str]] = Field(None, description="Optional list of segment IDs (if None, uses all approved)")
    transition_style: str = Field(default='cut', description="Transition style: cut, fade, dissolve")
    audio_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Audio configuration")


class RecompileRequest(BaseModel):
    changes: Dict[str, Any] = Field(..., description="Changes to apply (transition_style, audio_config, segment_ids)")


class CompilationJobResponse(BaseModel):
    id: str
    episode_id: str
    segment_ids: List[str]
    transition_style: str
    audio_config: Dict[str, Any]
    status: str
    progress: float
    output_video_url: Optional[str]
    output_duration: Optional[float]
    output_file_size: Optional[int]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]
    
    class Config:
        from_attributes = True


class CompilationStatisticsResponse(BaseModel):
    total_jobs: int
    completed: int
    failed: int
    processing: int
    success_rate: float
    average_compilation_time_seconds: Optional[float]
    total_output_size_bytes: int
    total_output_size_mb: float


# Helper function to get service
def get_compilation_service(db: Session = Depends(get_db)) -> SegmentCompilationService:
    """Get segment compilation service instance"""
    output_dir = os.path.join(os.getcwd(), ".working_dir", "compilations")
    return SegmentCompilationService(db, output_dir)


# WebSocket progress callback
async def compilation_progress_callback(job_id: str, status: str, progress: float, message: str):
    """Send compilation progress updates via WebSocket"""
    try:
        await ws_manager.broadcast_to_room(
            room=f"compilation_{job_id}",
            message={
                "type": "compilation_progress",
                "job_id": job_id,
                "status": status,
                "progress": progress,
                "message": message
            }
        )
    except Exception as e:
        logger.error(f"Failed to send compilation progress update: {e}")


# Endpoints

@router.post("/compile", response_model=CompilationJobResponse)
async def compile_segments(
    request: CompileSegmentsRequest,
    background_tasks: BackgroundTasks,
    service: SegmentCompilationService = Depends(get_compilation_service),
    db: Session = Depends(get_db)
):
    """
    Compile approved segments into final video
    
    - **episode_id**: Episode ID
    - **segment_ids**: Optional list of segment IDs (if None, uses all approved segments)
    - **transition_style**: Transition style (cut, fade, dissolve)
    - **audio_config**: Audio configuration (volume_normalization, background_music, etc.)
    """
    try:
        logger.info(f"Starting compilation for episode: {request.episode_id}")
        
        # Verify episode exists
        episode = db.query(Episode).filter(Episode.id == request.episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail=f"Episode not found: {request.episode_id}")
        
        # Start compilation in background
        async def compile_task():
            try:
                job = await service.compile_segments(
                    episode_id=request.episode_id,
                    segment_ids=request.segment_ids,
                    transition_style=request.transition_style,
                    audio_config=request.audio_config,
                    progress_callback=compilation_progress_callback
                )
                logger.info(f"Compilation completed: {job.id}")
            except Exception as e:
                logger.error(f"Compilation failed: {e}", exc_info=True)
        
        # Create initial job record
        from database_models import SegmentCompilationJob
        job = SegmentCompilationJob(
            episode_id=request.episode_id,
            segment_ids=request.segment_ids or [],
            transition_style=request.transition_style,
            audio_config=request.audio_config,
            status='pending'
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Run compilation in background
        background_tasks.add_task(compile_task)
        
        return CompilationJobResponse.model_validate(job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start compilation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=CompilationJobResponse)
async def get_compilation_job(
    job_id: str,
    service: SegmentCompilationService = Depends(get_compilation_service)
):
    """Get compilation job status"""
    try:
        status = service.get_compilation_status(job_id)
        return CompilationJobResponse(**status)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get compilation job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/jobs", response_model=List[CompilationJobResponse])
async def list_compilation_jobs(
    episode_id: str,
    service: SegmentCompilationService = Depends(get_compilation_service),
    db: Session = Depends(get_db)
):
    """List all compilation jobs for an episode"""
    try:
        # Verify episode exists
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail=f"Episode not found: {episode_id}")
        
        jobs = service.list_compilation_jobs(episode_id)
        return [CompilationJobResponse(**job) for job in jobs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list compilation jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
async def cancel_compilation(
    job_id: str,
    service: SegmentCompilationService = Depends(get_compilation_service)
):
    """Cancel a running compilation job"""
    try:
        job = service.cancel_compilation(job_id)
        
        return {
            "status": "cancelled",
            "job_id": job.id,
            "message": "Compilation job cancelled"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to cancel compilation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}/output")
async def delete_compilation_output(
    job_id: str,
    service: SegmentCompilationService = Depends(get_compilation_service)
):
    """Delete compilation output file"""
    try:
        success = service.delete_compilation_output(job_id)
        
        if success:
            return {
                "status": "deleted",
                "job_id": job_id,
                "message": "Compilation output deleted"
            }
        else:
            return {
                "status": "not_found",
                "job_id": job_id,
                "message": "Output file not found or already deleted"
            }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete compilation output: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/download")
async def download_compilation(
    job_id: str,
    service: SegmentCompilationService = Depends(get_compilation_service)
):
    """Download compiled video file"""
    try:
        status = service.get_compilation_status(job_id)
        
        if status['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Compilation not completed. Current status: {status['status']}"
            )
        
        if not status['output_video_url'] or not os.path.exists(status['output_video_url']):
            raise HTTPException(status_code=404, detail="Output video file not found")
        
        filename = os.path.basename(status['output_video_url'])
        
        return FileResponse(
            status['output_video_url'],
            media_type="video/mp4",
            filename=filename
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to download compilation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/recompile", response_model=CompilationJobResponse)
async def recompile_with_changes(
    job_id: str,
    request: RecompileRequest,
    background_tasks: BackgroundTasks,
    service: SegmentCompilationService = Depends(get_compilation_service)
):
    """
    Recompile with different settings
    
    - **job_id**: Original job ID
    - **changes**: Changes to apply (transition_style, audio_config, segment_ids)
    """
    try:
        logger.info(f"Recompiling job: {job_id}")
        
        # Start recompilation in background
        async def recompile_task():
            try:
                new_job = await service.recompile_with_changes(
                    job_id=job_id,
                    changes=request.changes,
                    progress_callback=compilation_progress_callback
                )
                logger.info(f"Recompilation completed: {new_job.id}")
            except Exception as e:
                logger.error(f"Recompilation failed: {e}", exc_info=True)
        
        # Get original job to create initial record
        original_status = service.get_compilation_status(job_id)
        
        from database_models import SegmentCompilationJob
        from database import get_db
        db = next(get_db())
        
        new_job = SegmentCompilationJob(
            episode_id=original_status['episode_id'],
            segment_ids=request.changes.get('segment_ids', original_status['segment_ids']),
            transition_style=request.changes.get('transition_style', original_status['transition_style']),
            audio_config=request.changes.get('audio_config', original_status['audio_config']),
            status='pending'
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        
        # Run recompilation in background
        background_tasks.add_task(recompile_task)
        
        return CompilationJobResponse.model_validate(new_job)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to recompile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/statistics", response_model=CompilationStatisticsResponse)
async def get_compilation_statistics(
    episode_id: str,
    service: SegmentCompilationService = Depends(get_compilation_service),
    db: Session = Depends(get_db)
):
    """
    Get compilation statistics for an episode
    
    Returns:
    - Total jobs
    - Completed/failed/processing counts
    - Success rate
    - Average compilation time
    - Total output size
    """
    try:
        # Verify episode exists
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail=f"Episode not found: {episode_id}")
        
        stats = service.get_compilation_statistics(episode_id)
        return CompilationStatisticsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get compilation statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/latest")
async def get_latest_compilation(
    episode_id: str,
    service: SegmentCompilationService = Depends(get_compilation_service),
    db: Session = Depends(get_db)
):
    """Get the latest completed compilation for an episode"""
    try:
        jobs = service.list_compilation_jobs(episode_id)
        
        # Filter completed jobs and get the latest
        completed_jobs = [j for j in jobs if j['status'] == 'completed']
        
        if not completed_jobs:
            raise HTTPException(status_code=404, detail="No completed compilations found")
        
        # Sort by completed_at descending
        latest_job = max(completed_jobs, key=lambda x: x['completed_at'] or '')
        
        return CompilationJobResponse(**latest_job)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest compilation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/quick-compile")
async def quick_compile(
    episode_id: str,
    background_tasks: BackgroundTasks,
    service: SegmentCompilationService = Depends(get_compilation_service),
    db: Session = Depends(get_db)
):
    """
    Quick compile with default settings (all approved segments, cut transitions)
    
    This is a convenience endpoint for fast compilation with default settings.
    """
    try:
        logger.info(f"Quick compiling episode: {episode_id}")
        
        # Verify episode exists
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail=f"Episode not found: {episode_id}")
        
        # Start compilation with default settings
        async def compile_task():
            try:
                job = await service.compile_segments(
                    episode_id=episode_id,
                    segment_ids=None,  # Use all approved
                    transition_style='cut',
                    audio_config={},
                    progress_callback=compilation_progress_callback
                )
                logger.info(f"Quick compilation completed: {job.id}")
            except Exception as e:
                logger.error(f"Quick compilation failed: {e}", exc_info=True)
        
        # Create initial job record
        from database_models import SegmentCompilationJob
        job = SegmentCompilationJob(
            episode_id=episode_id,
            segment_ids=[],
            transition_style='cut',
            audio_config={},
            status='pending'
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Run in background
        background_tasks.add_task(compile_task)
        
        return {
            "status": "started",
            "job_id": job.id,
            "episode_id": episode_id,
            "message": "Quick compilation started with default settings"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start quick compilation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))