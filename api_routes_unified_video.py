"""
Unified Video Generation API Routes
统一视频生成API - 整合所有视频生成端点

This module consolidates:
- /api/v1/generate/idea2video (api_server.py) - DEPRECATED
- /api/v1/generate/script2video (api_server.py) - DEPRECATED
- /api/v1/direct-pipeline/idea2video (api_routes_direct_pipeline.py) - DEPRECATED
- /api/v1/direct-pipeline/script2video (api_routes_direct_pipeline.py) - DEPRECATED

New unified endpoint: POST /api/v1/videos/generate
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum
import uuid
import os

from database import get_db
from database_models import Episode, GenerationProgress
from pipelines.idea2video_pipeline import Idea2VideoPipeline
from pipelines.script2video_pipeline import Script2VideoPipeline
from services.job_manager import job_manager

router = APIRouter(prefix="/api/v1/videos", tags=["videos-unified"])


# ============================================================================
# Enums and Constants
# ============================================================================

class GenerationMode(str, Enum):
    """Video generation mode"""
    IDEA = "idea"  # Generate from creative idea
    SCRIPT = "script"  # Generate from complete script


class JobStatus(str, Enum):
    """Job status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Request/Response Models
# ============================================================================

class UnifiedVideoGenerationRequest(BaseModel):
    """Unified video generation request"""
    mode: GenerationMode = Field(..., description="Generation mode: 'idea' or 'script'")
    content: str = Field(..., min_length=10, description="Idea or script content")
    user_requirement: str = Field(
        default="For adults, do not exceed 3 scenes. Each scene should be no more than 5 shots.",
        description="User requirements for the video"
    )
    style: str = Field(default="Cartoon style", description="Visual style")
    
    # Optional metadata
    title: Optional[str] = Field(None, description="Video title")
    series_id: Optional[str] = Field(None, description="Series ID for multi-episode projects")
    episode_number: Optional[int] = Field(None, ge=1, description="Episode number")
    
    # Advanced options
    use_conversational_workflow: bool = Field(
        default=False,
        description="Use step-by-step conversational workflow instead of direct pipeline"
    )


class VideoGenerationResponse(BaseModel):
    """Video generation response"""
    job_id: str
    status: JobStatus
    message: str
    mode: GenerationMode
    episode_id: Optional[str] = None
    created_at: str
    working_dir: str
    
    # Deprecation warnings
    deprecated_endpoints: Optional[List[str]] = Field(
        default=None,
        description="List of deprecated endpoints that should be replaced"
    )


class VideoJobStatusResponse(BaseModel):
    """Video job status response"""
    job_id: str
    status: JobStatus
    mode: GenerationMode
    progress: Optional[float] = Field(None, ge=0.0, le=100.0, description="Progress percentage")
    current_stage: Optional[str] = None
    
    # Results
    video_path: Optional[str] = None
    working_dir: Optional[str] = None
    total_shots: Optional[int] = None
    
    # Error handling
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    
    # Metadata
    episode_id: Optional[str] = None
    title: Optional[str] = None


# ============================================================================
# Job Storage (Database-backed via job_manager service)
# ============================================================================
# Note: Using global job_manager from services.job_manager
# This provides database persistence for all video generation jobs


# ============================================================================
# Background Tasks
# ============================================================================

async def run_video_generation_pipeline(
    job_id: str,
    mode: GenerationMode,
    content: str,
    user_requirement: str,
    style: str
):
    """Background task to run video generation pipeline"""
    try:
        job_manager.update_job(
            job_id,
            {
                'status': 'processing',
                'current_stage': "Initializing pipeline",
                'progress': 5.0
            }
        )
        
        # Get job data
        job = job_manager.get_job(job_id)
        if not job:
            raise Exception("Job not found")
        
        working_dir = job["working_dir"]
        
        # Initialize appropriate pipeline
        if mode == GenerationMode.IDEA:
            job_manager.update_job(job_id, {'current_stage': "Developing story", 'progress': 10.0})
            
            pipeline = Idea2VideoPipeline.init_from_config(
                config_path="configs/idea2video.yaml"
            )
            pipeline.working_dir = working_dir
            
            final_video_path = await pipeline(
                idea=content,
                user_requirement=user_requirement,
                style=style
            )
            
        else:  # SCRIPT mode
            job_manager.update_job(job_id, {'current_stage': "Extracting characters", 'progress': 10.0})
            
            pipeline = Script2VideoPipeline.init_from_config(
                config_path="configs/script2video.yaml"
            )
            pipeline.working_dir = working_dir
            
            final_video_path = await pipeline(
                script=content,
                user_requirement=user_requirement,
                style=style
            )
        
        # Convert to relative path for API
        video_rel_path = f"/media/{os.path.relpath(final_video_path, '.working_dir')}"
        
        # Count shots (scan working directory)
        total_shots = 0
        shots_dir = os.path.join(working_dir, "shots")
        if os.path.exists(shots_dir):
            total_shots = len([d for d in os.listdir(shots_dir) if os.path.isdir(os.path.join(shots_dir, d))])
        
        # Update job as completed
        job_manager.mark_completed(
            job_id,
            result_data={
                'message': "Video generated successfully",
                'video_path': video_rel_path,
                'total_shots': total_shots
            }
        )
        
        print(f"[Unified Video Generation] Job {job_id} completed successfully")
        print(f"[Unified Video Generation] Video: {video_rel_path}")
        
    except Exception as e:
        print(f"[Unified Video Generation] Job {job_id} failed: {e}")
        import traceback
        traceback.print_exc()
        
        job_manager.mark_failed(job_id, str(e))


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(
    request: UnifiedVideoGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    **Unified Video Generation Endpoint**
    
    Generate videos from either ideas or scripts using a single unified API.
    
    **Modes:**
    - `idea`: Generate video from a creative concept/idea
    - `script`: Generate video from a complete script
    
    **Features:**
    - Unified request/response format
    - Database-backed job storage
    - Progress tracking
    - Error handling and recovery
    - Optional conversational workflow
    
    **Deprecation Notice:**
    This endpoint replaces the following deprecated endpoints:
    - POST /api/v1/generate/idea2video
    - POST /api/v1/generate/script2video
    - POST /api/v1/direct-pipeline/idea2video
    - POST /api/v1/direct-pipeline/script2video
    
    **Example Request (Idea Mode):**
    ```json
    {
        "mode": "idea",
        "content": "A story about a brave knight saving a kingdom",
        "style": "Cartoon style",
        "title": "The Brave Knight"
    }
    ```
    
    **Example Request (Script Mode):**
    ```json
    {
        "mode": "script",
        "content": "INT. CASTLE - DAY\\nThe knight enters...",
        "style": "Anime Style",
        "user_requirement": "Fast-paced with no more than 15 shots"
    }
    ```
    """
    try:
        # Validate content length based on mode
        if request.mode == GenerationMode.IDEA and len(request.content) < 10:
            raise HTTPException(
                status_code=400,
                detail="Idea must be at least 10 characters long"
            )
        elif request.mode == GenerationMode.SCRIPT and len(request.content) < 50:
            raise HTTPException(
                status_code=400,
                detail="Script must be at least 50 characters long"
            )
        
        # Create Episode record if series_id provided
        episode_id = None
        if request.series_id and request.episode_number:
            try:
                episode = Episode(
                    series_id=request.series_id,
                    episode_number=request.episode_number,
                    title=request.title or f"Episode {request.episode_number}",
                    status="generating"
                )
                db.add(episode)
                db.commit()
                db.refresh(episode)
                episode_id = episode.id
            except Exception as e:
                print(f"[WARNING] Failed to create episode record: {e}")
                db.rollback()
        
        # Create working directory
        job_id = str(uuid.uuid4())
        working_dir = f".working_dir/{request.mode.value}2video/{job_id}"
        os.makedirs(working_dir, exist_ok=True)
        
        # Create job in database
        job_data = job_manager.create_job(
            job_id=job_id,
            job_type=f"{request.mode.value}2video",
            content=request.content,
            user_requirement=request.user_requirement,
            style=request.style,
            project_title=request.title,
            mode=request.mode.value,
            request_data={
                'mode': request.mode.value,
                'content': request.content,
                'user_requirement': request.user_requirement,
                'style': request.style,
                'title': request.title,
                'series_id': request.series_id,
                'episode_number': request.episode_number
            },
            working_dir=working_dir,
            db=db
        )
        
        # Start background task
        background_tasks.add_task(
            run_video_generation_pipeline,
            job_id=job_id,
            mode=request.mode,
            content=request.content,
            user_requirement=request.user_requirement,
            style=request.style
        )
        
        return VideoGenerationResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message=f"Video generation job created successfully ({request.mode.value} mode)",
            mode=request.mode,
            episode_id=episode_id,
            created_at=job_data["created_at"],
            working_dir=job_data["working_dir"],
            deprecated_endpoints=[
                "/api/v1/generate/idea2video",
                "/api/v1/generate/script2video",
                "/api/v1/direct-pipeline/idea2video",
                "/api/v1/direct-pipeline/script2video"
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create video generation job: {str(e)}")


@router.get("/jobs/{job_id}", response_model=VideoJobStatusResponse)
async def get_video_job_status(job_id: str):
    """
    Get video generation job status
    
    Returns detailed information about a video generation job including:
    - Current status and progress
    - Video path (when completed)
    - Error details (if failed)
    - Timestamps
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Extract video path from result_data if available
    video_path = None
    if job.get("result"):
        video_path = job["result"].get("video_path")
    
    return VideoJobStatusResponse(
        job_id=job["job_id"],
        status=JobStatus(job["status"]),
        mode=GenerationMode(job["mode"]),
        progress=job.get("progress"),
        current_stage=job.get("current_stage"),
        video_path=video_path,
        working_dir=job.get("working_dir"),
        total_shots=job.get("total_shots"),
        error=job.get("error"),
        error_details=None,
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        completed_at=job.get("completed_at"),
        episode_id=job.get("episode_id"),
        title=job.get("project_title")
    )


@router.get("/jobs", response_model=List[VideoJobStatusResponse])
async def list_video_jobs(
    mode: Optional[GenerationMode] = None,
    status: Optional[JobStatus] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List video generation jobs
    
    **Query Parameters:**
    - `mode`: Filter by generation mode (idea/script)
    - `status`: Filter by job status
    - `limit`: Maximum number of jobs to return (default: 50)
    - `offset`: Pagination offset (default: 0)
    """
    result = job_manager.list_jobs(
        limit=limit,
        offset=offset,
        status=status.value if status else None,
        job_type=f"{mode.value}2video" if mode else None
    )
    
    jobs = result['jobs']
    
    return [
        VideoJobStatusResponse(
            job_id=job["job_id"],
            status=JobStatus(job["status"]),
            mode=GenerationMode(job["mode"]),
            progress=job.get("progress"),
            current_stage=job.get("current_stage"),
            video_path=job.get("result", {}).get("video_path") if job.get("result") else None,
            working_dir=job.get("working_dir"),
            total_shots=job.get("total_shots"),
            error=job.get("error"),
            error_details=None,
            created_at=job["created_at"],
            updated_at=job["updated_at"],
            completed_at=job.get("completed_at"),
            episode_id=job.get("episode_id"),
            title=job.get("project_title")
        )
        for job in jobs
    ]


@router.delete("/jobs/{job_id}")
async def delete_video_job(job_id: str):
    """
    Delete a video generation job
    
    **Note:** This only deletes the job record, not the generated files.
    """
    success = job_manager.delete_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "message": "Job deleted successfully",
        "job_id": job_id
    }


@router.get("/health")
async def health_check():
    """Health check for unified video generation service"""
    result = job_manager.list_jobs(limit=1000)
    all_jobs = result['jobs']
    
    return {
        "status": "healthy",
        "service": "unified-video-generation",
        "storage": "database-backed",
        "total_jobs": len(all_jobs),
        "active_jobs": len([j for j in all_jobs if j["status"] == "processing"]),
        "queued_jobs": len([j for j in all_jobs if j["status"] == "queued"]),
        "completed_jobs": len([j for j in all_jobs if j["status"] == "completed"]),
        "failed_jobs": len([j for j in all_jobs if j["status"] == "failed"])
    }