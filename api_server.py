"""
FastAPI server for ViMax video generation API
Provides endpoints for idea2video and script2video pipelines with shot-level tracking
Includes Seko multi-episode series management
"""
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime
import os
import json
from pathlib import Path
from pipelines.idea2video_pipeline import Idea2VideoPipeline
from pipelines.script2video_pipeline import Script2VideoPipeline
from services.nlp_service import nlp_service, Intent, EditAction
from services.character_service import character_service
from models.character import Character, CharacterAppearance, CharacterAppearanceRecord

# Import Seko routes, conversational routes, direct pipeline routes, WebSocket routes, video routes, and database
from seko_api_routes import router as seko_router
from api_routes_conversational import router as conversational_router
from api_routes_direct_pipeline import router as direct_pipeline_router
from api_routes_websocket import router as websocket_router
from api_routes_video import router as video_router
from database import init_db

app = FastAPI(
    title="ViMax Video Generation API",
    description="API for generating videos from ideas and scripts with shot-level tracking and multi-episode series management",
    version="3.0.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup"""
    print("🚀 Starting ViMax API Server...")
    init_db()
    print("✅ Database initialized")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Seko router for series/episode management
app.include_router(seko_router)

# Include conversational workflow router
app.include_router(conversational_router)

# Include direct pipeline router
app.include_router(direct_pipeline_router)

# Include WebSocket router
app.include_router(websocket_router)

# Include video management router
app.include_router(video_router)

# Add validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom handler for validation errors to provide better debugging info"""
    print(f"[ERROR] Validation error on {request.method} {request.url}")
    print(f"[ERROR] Request body: {await request.body()}")
    print(f"[ERROR] Validation errors: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": str(await request.body()),
            "message": "Request validation failed. Check the error details."
        }
    )

# Mount static files for serving generated media
if os.path.exists(".working_dir"):
    app.mount("/media", StaticFiles(directory=".working_dir"), name="media")

# In-memory storage for job status (in production, use a database)
jobs: Dict[str, Dict[str, Any]] = {}


class ShotInfo(BaseModel):
    """Information about a single shot"""
    shot_idx: int
    status: str  # "pending", "generating_frames", "generating_video", "completed", "failed"
    first_frame_path: Optional[str] = None
    last_frame_path: Optional[str] = None
    video_path: Optional[str] = None
    description: Optional[str] = None
    visual_desc: Optional[str] = None
    motion_desc: Optional[str] = None
    audio_desc: Optional[str] = None
    camera_idx: Optional[int] = None
    variation_type: Optional[str] = None
    error: Optional[str] = None
    scene_idx: Optional[int] = None  # For idea2video shots


class ShotUpdateRequest(BaseModel):
    """Request model for updating shot prompts"""
    visual_desc: Optional[str] = None
    motion_desc: Optional[str] = None
    audio_desc: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat message model"""
    message: str = Field(..., description="User message", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context (job_id, shot_idx, etc.)")


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    intent: str
    action: Optional[str] = None
    suggestions: List[str] = []
    data: Optional[Dict[str, Any]] = None


class NaturalLanguageEditRequest(BaseModel):
    """Request for natural language editing"""
    job_id: str = Field(..., description="Job ID to edit")
    command: str = Field(..., description="Natural language editing command", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")


class CharacterCreateRequest(BaseModel):
    """Request to create a character"""
    name: str = Field(..., description="Character name", min_length=1)
    description: str = Field(..., description="Character description")
    appearance: Optional[Dict[str, Any]] = Field(None, description="Appearance attributes")
    personality_traits: Optional[List[str]] = Field(None, description="Personality traits")
    age: Optional[str] = None
    gender: Optional[str] = None
    role: Optional[str] = None


class CharacterUpdateRequest(BaseModel):
    """Request to update a character"""
    name: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[Dict[str, Any]] = None
    personality_traits: Optional[List[str]] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    role: Optional[str] = None


class CharacterResponse(BaseModel):
    """Response model for character"""
    character_id: str
    name: str
    description: str
    appearance: Dict[str, Any]
    personality_traits: List[str]
    reference_images: List[str]
    age: Optional[str]
    gender: Optional[str]
    role: Optional[str]
    created_at: str
    updated_at: str


class Idea2VideoRequest(BaseModel):
    """Request model for idea to video generation"""
    idea: str = Field(..., description="The video idea/concept", min_length=10)
    user_requirement: str = Field(
        default="For adults, do not exceed 3 scenes. Each scene should be no more than 5 shots.",
        description="User requirements for the video"
    )
    style: str = Field(default="Cartoon style", description="Visual style of the video")
    project_title: Optional[str] = Field(None, description="Optional project title")


class Script2VideoRequest(BaseModel):
    """Request model for script to video generation"""
    script: str = Field(..., description="The video script", min_length=50)
    user_requirement: str = Field(
        default="Fast-paced with no more than 15 shots.",
        description="User requirements for the video"
    )
    style: str = Field(default="Anime Style", description="Visual style of the video")
    project_title: Optional[str] = Field(None, description="Optional project title")


class JobResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    status: str
    message: str
    created_at: str
    working_dir: str


class JobStatusResponse(BaseModel):
    """Response model for job status with shot-level details"""
    job_id: str
    status: str
    progress: Optional[float] = None
    current_stage: Optional[str] = None
    shots: List[ShotInfo] = []
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    working_dir: Optional[str] = None


def scan_working_directory(working_dir: str) -> List[ShotInfo]:
    """Scan working directory to extract shot information
    
    Handles two directory structures:
    1. script2video: working_dir/shots/0, working_dir/shots/1, ...
    2. idea2video: working_dir/scene_0/shots/0, working_dir/scene_1/shots/0, ...
    """
    shots = []
    
    # Check for direct shots directory (script2video structure)
    shots_dir = os.path.join(working_dir, "shots")
    if os.path.exists(shots_dir):
        shots.extend(_scan_shots_directory(shots_dir))
    
    # Check for scene directories (idea2video structure)
    if os.path.exists(working_dir):
        for item in os.listdir(working_dir):
            item_path = os.path.join(working_dir, item)
            if os.path.isdir(item_path) and item.startswith("scene_"):
                scene_shots_dir = os.path.join(item_path, "shots")
                if os.path.exists(scene_shots_dir):
                    shots.extend(_scan_shots_directory(scene_shots_dir))
    
    # Sort shots by shot_idx
    shots.sort(key=lambda x: x.shot_idx)
    
    return shots


def _scan_shots_directory(shots_dir: str) -> List[ShotInfo]:
    """Helper function to scan a shots directory and extract shot information"""
    shots = []
    
    # Get all shot directories
    shot_dirs = sorted([d for d in os.listdir(shots_dir) if os.path.isdir(os.path.join(shots_dir, d))])
    
    for shot_dir in shot_dirs:
        try:
            shot_idx = int(shot_dir)
            shot_path = os.path.join(shots_dir, shot_dir)
            
            # Read shot description if available
            shot_desc_path = os.path.join(shot_path, "shot_description.json")
            shot_desc = None
            if os.path.exists(shot_desc_path):
                with open(shot_desc_path, 'r', encoding='utf-8') as f:
                    shot_desc = json.load(f)
            
            # Check for frames and video
            first_frame_path = os.path.join(shot_path, "first_frame.png")
            last_frame_path = os.path.join(shot_path, "last_frame.png")
            video_path = os.path.join(shot_path, "video.mp4")
            
            # Determine status
            status = "pending"
            if os.path.exists(video_path):
                status = "completed"
            elif os.path.exists(first_frame_path):
                status = "generating_video"
            else:
                status = "generating_frames"
            
            # Create relative paths for API
            first_frame_rel = f"/media/{os.path.relpath(first_frame_path, '.working_dir')}" if os.path.exists(first_frame_path) else None
            last_frame_rel = f"/media/{os.path.relpath(last_frame_path, '.working_dir')}" if os.path.exists(last_frame_path) else None
            video_rel = f"/media/{os.path.relpath(video_path, '.working_dir')}" if os.path.exists(video_path) else None
            
            shot_info = ShotInfo(
                shot_idx=shot_idx,
                status=status,
                first_frame_path=first_frame_rel,
                last_frame_path=last_frame_rel,
                video_path=video_rel,
                visual_desc=shot_desc.get("visual_desc") if shot_desc else None,
                motion_desc=shot_desc.get("motion_desc") if shot_desc else None,
                audio_desc=shot_desc.get("audio_desc") if shot_desc else None,
                camera_idx=shot_desc.get("cam_idx") if shot_desc else None,
                variation_type=shot_desc.get("variation_type") if shot_desc else None,
            )
            shots.append(shot_info)
        except (ValueError, Exception) as e:
            print(f"[WARNING] Failed to process shot directory {shot_dir}: {e}")
            continue
    
    return shots


async def run_idea2video_pipeline(job_id: str, request: Idea2VideoRequest):
    """Background task to run idea2video pipeline"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["current_stage"] = "Developing story"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        pipeline = Idea2VideoPipeline.init_from_config(
            config_path="configs/idea2video.yaml"
        )
        
        # Update working directory in job
        jobs[job_id]["working_dir"] = pipeline.working_dir
        
        result = await pipeline(
            idea=request.idea,
            user_requirement=request.user_requirement,
            style=request.style
        )
        
        # Scan for shots
        shots = scan_working_directory(pipeline.working_dir)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["shots"] = [shot.dict() for shot in shots]
        jobs[job_id]["result"] = {
            "message": "Video generated successfully",
            "project_title": request.project_title or "Untitled Project",
            "final_video_path": f"/media/{os.path.relpath(result, '.working_dir')}",
            "total_shots": len(shots)
        }
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()


async def run_script2video_pipeline(job_id: str, request: Script2VideoRequest):
    """Background task to run script2video pipeline"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["current_stage"] = "Extracting characters"
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
        pipeline = Script2VideoPipeline.init_from_config(
            config_path="configs/script2video.yaml"
        )
        
        # Update working directory in job
        jobs[job_id]["working_dir"] = pipeline.working_dir
        
        result = await pipeline(
            script=request.script,
            user_requirement=request.user_requirement,
            style=request.style
        )
        
        # Scan for shots
        shots = scan_working_directory(pipeline.working_dir)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["shots"] = [shot.dict() for shot in shots]
        jobs[job_id]["result"] = {
            "message": "Video generated successfully",
            "project_title": request.project_title or "Untitled Project",
            "final_video_path": f"/media/{os.path.relpath(result, '.working_dir')}",
            "total_shots": len(shots)
        }
        jobs[job_id]["updated_at"] = datetime.now().isoformat()
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["updated_at"] = datetime.now().isoformat()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ViMax Video Generation API v3.0",
        "version": "3.0.0",
        "features": [
            "Shot-level tracking",
            "Real-time progress via WebSocket",
            "Media serving",
            "Multi-episode series management",
            "Character consistency tracking",
            "Conversational workflow (step-by-step generation)",
            "Direct pipeline execution (idea2video & script2video)",
            "Comprehensive error handling and recovery",
            "Video generation with shot-by-shot progress",
            "Video download and streaming"
        ],
        "endpoints": {
            "idea2video": "/api/v1/generate/idea2video",
            "script2video": "/api/v1/generate/script2video",
            "direct_idea2video": "/api/v1/direct-pipeline/idea2video",
            "direct_script2video": "/api/v1/direct-pipeline/script2video",
            "job_status": "/api/v1/jobs/{job_id}",
            "shot_details": "/api/v1/jobs/{job_id}/shots",
            "seko_series": "/api/v1/seko/series",
            "conversational_workflow": "/api/v1/conversational/episode/create",
            "conversational_video_generate": "/api/v1/conversational/episode/{episode_id}/video/generate",
            "direct_pipeline_jobs": "/api/v1/direct-pipeline/jobs",
            "video_info": "/api/v1/videos/episode/{episode_id}/info",
            "video_download": "/api/v1/videos/episode/{episode_id}/download",
            "video_stream": "/api/v1/videos/episode/{episode_id}/stream",
            "video_stats": "/api/v1/videos/stats",
            "websocket": "ws://localhost:3001/api/v1/ws/connect",
            "websocket_stats": "/api/v1/ws/stats",
            "seko_docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    }


@app.post("/api/v1/generate/idea2video", response_model=JobResponse)
async def generate_idea2video(
    request: Idea2VideoRequest,
    background_tasks: BackgroundTasks
):
    """Generate video from an idea with shot-level tracking"""
    # Log incoming request for debugging
    print(f"[DEBUG] Received idea2video request: {request.dict()}")
    print(f"[DEBUG] Idea length: {len(request.idea)}")
    print(f"[DEBUG] User requirement: {request.user_requirement}")
    print(f"[DEBUG] Style: {request.style}")
    print(f"[DEBUG] Project title: {request.project_title}")
    
    job_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    # Create working directory
    working_dir = f".working_dir/idea2video/{job_id}"
    
    jobs[job_id] = {
        "job_id": job_id,
        "type": "idea2video",
        "status": "queued",
        "created_at": created_at,
        "updated_at": created_at,
        "request": request.dict(),
        "working_dir": working_dir,
        "shots": []
    }
    
    background_tasks.add_task(run_idea2video_pipeline, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Video generation job created successfully",
        created_at=created_at,
        working_dir=working_dir
    )


@app.post("/api/v1/generate/script2video", response_model=JobResponse)
async def generate_script2video(
    request: Script2VideoRequest,
    background_tasks: BackgroundTasks
):
    """Generate video from a script with shot-level tracking"""
    # Log incoming request for debugging
    print(f"[DEBUG] Received script2video request: {request.dict()}")
    print(f"[DEBUG] Script length: {len(request.script)}")
    print(f"[DEBUG] User requirement: {request.user_requirement}")
    print(f"[DEBUG] Style: {request.style}")
    print(f"[DEBUG] Project title: {request.project_title}")
    
    job_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    # Create working directory
    working_dir = f".working_dir/script2video/{job_id}"
    
    jobs[job_id] = {
        "job_id": job_id,
        "type": "script2video",
        "status": "queued",
        "created_at": created_at,
        "updated_at": created_at,
        "request": request.dict(),
        "working_dir": working_dir,
        "shots": []
    }
    
    background_tasks.add_task(run_script2video_pipeline, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Video generation job created successfully",
        created_at=created_at,
        working_dir=working_dir
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of a video generation job with shot details"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    # Scan working directory for latest shot information
    if job.get("working_dir") and os.path.exists(job["working_dir"]):
        shots = scan_working_directory(job["working_dir"])
        job["shots"] = [shot.dict() for shot in shots]
        
        # Calculate progress based on shots
        if shots:
            completed_shots = sum(1 for shot in shots if shot.status == "completed")
            job["progress"] = (completed_shots / len(shots)) * 100
    
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress"),
        current_stage=job.get("current_stage"),
        shots=[ShotInfo(**shot) for shot in job.get("shots", [])],
        result=job.get("result"),
        error=job.get("error"),
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        working_dir=job.get("working_dir")
    )


@app.get("/api/v1/jobs/{job_id}/shots")
async def get_job_shots(job_id: str):
    """Get detailed shot information for a job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if not job.get("working_dir") or not os.path.exists(job["working_dir"]):
        return {"shots": []}
    
    shots = scan_working_directory(job["working_dir"])
    
    return {
        "job_id": job_id,
        "total_shots": len(shots),
        "shots": [shot.dict() for shot in shots]
    }


@app.get("/api/v1/jobs")
async def list_jobs(limit: int = 50, offset: int = 0):
    """List all video generation jobs"""
    all_jobs = list(jobs.values())
    total = len(all_jobs)
    
    # Sort by created_at descending
    all_jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    paginated_jobs = all_jobs[offset:offset + limit]
    
    return {
        "jobs": paginated_jobs,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    }


@app.delete("/api/v1/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from the system"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del jobs[job_id]
    
    return {"message": "Job deleted successfully", "job_id": job_id}


@app.put("/api/v1/jobs/{job_id}/shots/{shot_idx}")
async def update_shot(job_id: str, shot_idx: int, update: ShotUpdateRequest):
    """Update shot prompt/description"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    working_dir = job.get("working_dir")
    
    if not working_dir or not os.path.exists(working_dir):
        raise HTTPException(status_code=404, detail="Working directory not found")
    
    # Find the shot description file
    shot_desc_path = None
    
    # Check script2video structure
    direct_shot_path = os.path.join(working_dir, "shots", str(shot_idx), "shot_description.json")
    if os.path.exists(direct_shot_path):
        shot_desc_path = direct_shot_path
    else:
        # Check idea2video structure (scene folders)
        for item in os.listdir(working_dir):
            if item.startswith("scene_"):
                scene_shot_path = os.path.join(working_dir, item, "shots", str(shot_idx), "shot_description.json")
                if os.path.exists(scene_shot_path):
                    shot_desc_path = scene_shot_path
                    break
    
    if not shot_desc_path:
        raise HTTPException(status_code=404, detail=f"Shot {shot_idx} not found")
    
    # Read existing description
    with open(shot_desc_path, 'r', encoding='utf-8') as f:
        shot_desc = json.load(f)
    
    # Update fields
    if update.visual_desc is not None:
        shot_desc["visual_desc"] = update.visual_desc
    if update.motion_desc is not None:
        shot_desc["motion_desc"] = update.motion_desc
    if update.audio_desc is not None:
        shot_desc["audio_desc"] = update.audio_desc
    
    # Write back
    with open(shot_desc_path, 'w', encoding='utf-8') as f:
        json.dump(shot_desc, f, indent=2, ensure_ascii=False)
    
    return {
        "message": "Shot updated successfully",
        "job_id": job_id,
        "shot_idx": shot_idx,
        "updated_fields": update.model_dump(exclude_none=True)
    }


@app.post("/api/v1/chat/message", response_model=ChatResponse)
async def chat_message(request: ChatMessage):
    """Process natural language chat message with intent detection"""
    try:
        # Parse the command
        parsed = nlp_service.parse_command(request.message, request.context)
        
        # Generate response based on intent
        response_text = ""
        action_str = parsed.action.value if parsed.action else None
        data = {}
        
        if parsed.intent == Intent.CREATE_VIDEO:
            response_text = "I can help you create a video! Would you like to:\n\n"
            response_text += "1. Generate from an idea (describe your concept)\n"
            response_text += "2. Generate from a script (provide detailed script)\n\n"
            response_text += "Just tell me your idea or paste your script, and I'll get started!"
            
        elif parsed.intent == Intent.EDIT_SHOT:
            if parsed.target_shot is not None:
                response_text = f"I'll help you edit shot {parsed.target_shot}. "
                if parsed.action:
                    response_text += f"I detected you want to {parsed.action.value.replace('_', ' ')}. "
                    if parsed.parameters:
                        response_text += f"Parameters: {parsed.parameters}. "
                response_text += "\n\nTo apply these changes, I'll need the job ID. "
                response_text += "You can use the natural language edit endpoint with your job ID."
            else:
                response_text = "I can help you edit a shot! Please specify which shot you'd like to edit. "
                response_text += "For example: 'Edit shot 1' or 'Change the first shot'"
                
        elif parsed.intent == Intent.QUERY_STATUS:
            if request.context and request.context.get("job_id"):
                job_id = request.context["job_id"]
                if job_id in jobs:
                    job = jobs[job_id]
                    response_text = f"Job Status: {job['status']}\n"
                    if job.get("progress"):
                        response_text += f"Progress: {job['progress']:.1f}%\n"
                    if job.get("current_stage"):
                        response_text += f"Current Stage: {job['current_stage']}\n"
                    data = {"job": job}
                else:
                    response_text = "Job not found. Please provide a valid job ID."
            else:
                response_text = "Please provide a job ID to check status."
                
        elif parsed.intent == Intent.HELP:
            response_text = "I'm your AI video creation assistant! Here's what I can do:\n\n"
            response_text += "🎬 **Create Videos**\n"
            response_text += "- 'Create a video about...'\n"
            response_text += "- 'Generate a video from my script'\n\n"
            response_text += "✏️ **Edit Shots**\n"
            response_text += "- 'Make shot 1 brighter'\n"
            response_text += "- 'Change the background to blue'\n"
            response_text += "- 'Add more movement to shot 2'\n\n"
            response_text += "📊 **Check Status**\n"
            response_text += "- 'What's the status?'\n"
            response_text += "- 'Is my video ready?'\n\n"
            response_text += "Just ask me in natural language!"
            
        else:
            response_text = "I'm not sure what you'd like to do. Try asking me to:\n"
            response_text += "- Create a video\n"
            response_text += "- Edit a shot\n"
            response_text += "- Check video status\n"
            response_text += "- Get help\n\n"
            response_text += "Or just describe what you want in your own words!"
        
        # Generate suggestions
        suggestions = nlp_service.generate_suggestions(request.context)
        
        return ChatResponse(
            response=response_text,
            intent=parsed.intent.value,
            action=action_str,
            suggestions=suggestions,
            data=data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.post("/api/v1/chat/edit")
async def natural_language_edit(request: NaturalLanguageEditRequest):
    """Apply natural language editing command to a job"""
    try:
        # Check if job exists
        if request.job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs[request.job_id]
        
        # Parse the command
        parsed = nlp_service.parse_command(request.command, request.context)
        
        if parsed.intent != Intent.EDIT_SHOT:
            return {
                "success": False,
                "message": "Command is not an editing command. Please specify what you'd like to edit.",
                "parsed_intent": parsed.intent.value
            }
        
        if parsed.target_shot is None:
            return {
                "success": False,
                "message": "Please specify which shot to edit (e.g., 'shot 1', 'first shot')",
                "parsed_command": parsed.__dict__
            }
        
        # Get the shot description
        working_dir = job.get("working_dir")
        if not working_dir or not os.path.exists(working_dir):
            raise HTTPException(status_code=404, detail="Working directory not found")
        
        # Find shot description file
        shot_desc_path = None
        shot_idx = parsed.target_shot
        
        # Check script2video structure
        direct_shot_path = os.path.join(working_dir, "shots", str(shot_idx), "shot_description.json")
        if os.path.exists(direct_shot_path):
            shot_desc_path = direct_shot_path
        else:
            # Check idea2video structure
            for item in os.listdir(working_dir):
                if item.startswith("scene_"):
                    scene_shot_path = os.path.join(working_dir, item, "shots", str(shot_idx), "shot_description.json")
                    if os.path.exists(scene_shot_path):
                        shot_desc_path = scene_shot_path
                        break
        
        if not shot_desc_path:
            raise HTTPException(status_code=404, detail=f"Shot {shot_idx} not found")
        
        # Read existing description
        with open(shot_desc_path, 'r', encoding='utf-8') as f:
            shot_desc = json.load(f)
        
        # Generate modified prompt
        original_visual = shot_desc.get("visual_desc", "")
        modified_visual = nlp_service.generate_edit_prompt(parsed, original_visual)
        
        # Update the description
        shot_desc["visual_desc"] = modified_visual
        
        # Write back
        with open(shot_desc_path, 'w', encoding='utf-8') as f:
            json.dump(shot_desc, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": f"Shot {shot_idx} updated successfully",
            "job_id": request.job_id,
            "shot_idx": shot_idx,
            "parsed_command": {
                "intent": parsed.intent.value,
                "action": parsed.action.value if parsed.action else None,
                "parameters": parsed.parameters
            },
            "original_prompt": original_visual,
            "modified_prompt": modified_visual
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


@app.get("/api/v1/chat/suggestions")
async def get_chat_suggestions(job_id: Optional[str] = None, shot_idx: Optional[int] = None):
    """Get context-aware chat suggestions"""
    context = {}
    
    if job_id:
        context["current_job"] = job_id
        if job_id in jobs:
            context["job_status"] = jobs[job_id].get("status")
    
    if shot_idx is not None:
        context["current_shot"] = shot_idx
    
    suggestions = nlp_service.generate_suggestions(context)
    
    return {
        "suggestions": suggestions,
        "context": context
    }


@app.post("/api/v1/characters", response_model=CharacterResponse)
async def create_character(request: CharacterCreateRequest):
    """Create a new character"""
    try:
        character = character_service.create_character(
            name=request.name,
            description=request.description,
            appearance=request.appearance,
            personality_traits=request.personality_traits or [],
            age=request.age,
            gender=request.gender,
            role=request.role
        )
        
        return CharacterResponse(
            character_id=character.character_id,
            name=character.name,
            description=character.description,
            appearance=character.appearance.dict(),
            personality_traits=character.personality_traits,
            reference_images=character.reference_images,
            age=character.age,
            gender=character.gender,
            role=character.role,
            created_at=character.created_at,
            updated_at=character.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create character: {str(e)}")


@app.get("/api/v1/characters")
async def list_characters(limit: int = 50, offset: int = 0):
    """List all characters"""
    try:
        characters = character_service.list_characters(limit, offset)
        total = len(character_service.db.characters)
        
        return {
            "characters": [
                {
                    "character_id": char.character_id,
                    "name": char.name,
                    "description": char.description,
                    "appearance": char.appearance.dict(),
                    "personality_traits": char.personality_traits,
                    "reference_images": char.reference_images,
                    "age": char.age,
                    "gender": char.gender,
                    "role": char.role,
                    "created_at": char.created_at,
                    "updated_at": char.updated_at
                }
                for char in characters
            ],
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list characters: {str(e)}")


@app.get("/api/v1/characters/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: str):
    """Get a character by ID"""
    character = character_service.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return CharacterResponse(
        character_id=character.character_id,
        name=character.name,
        description=character.description,
        appearance=character.appearance.dict(),
        personality_traits=character.personality_traits,
        reference_images=character.reference_images,
        age=character.age,
        gender=character.gender,
        role=character.role,
        created_at=character.created_at,
        updated_at=character.updated_at
    )


@app.put("/api/v1/characters/{character_id}", response_model=CharacterResponse)
async def update_character(character_id: str, request: CharacterUpdateRequest):
    """Update a character"""
    updates = request.dict(exclude_none=True)
    
    character = character_service.update_character(character_id, updates)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return CharacterResponse(
        character_id=character.character_id,
        name=character.name,
        description=character.description,
        appearance=character.appearance.dict(),
        personality_traits=character.personality_traits,
        reference_images=character.reference_images,
        age=character.age,
        gender=character.gender,
        role=character.role,
        created_at=character.created_at,
        updated_at=character.updated_at
    )


@app.delete("/api/v1/characters/{character_id}")
async def delete_character(character_id: str):
    """Delete a character"""
    success = character_service.delete_character(character_id)
    if not success:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return {"message": "Character deleted successfully", "character_id": character_id}


@app.get("/api/v1/characters/{character_id}/appearances")
async def get_character_appearances(character_id: str):
    """Get all appearances of a character"""
    character = character_service.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    appearances = character_service.get_character_appearances(character_id)
    
    return {
        "character_id": character_id,
        "character_name": character.name,
        "total_appearances": len(appearances),
        "appearances": [app.dict() for app in appearances]
    }


@app.get("/api/v1/characters/{character_id}/consistency")
async def check_character_consistency(character_id: str):
    """Check consistency of a character across all appearances"""
    report = character_service.check_consistency(character_id)
    
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    
    return report


@app.post("/api/v1/characters/{character_id}/appearances")
async def record_character_appearance(
    character_id: str,
    job_id: str,
    shot_idx: int,
    image_path: str,
    scene_idx: Optional[int] = None
):
    """Record a character appearance in a shot"""
    character = character_service.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    appearance = character_service.record_appearance(
        character_id=character_id,
        job_id=job_id,
        shot_idx=shot_idx,
        image_path=image_path,
        scene_idx=scene_idx
    )
    
    return appearance.dict()


@app.get("/api/v1/jobs/{job_id}/characters")
async def get_job_characters(job_id: str):
    """Get all characters that appear in a job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    characters = character_service.get_job_characters(job_id)
    
    return {
        "job_id": job_id,
        "total_characters": len(characters),
        "characters": [
            {
                "character_id": char.character_id,
                "name": char.name,
                "description": char.description,
                "appearance": char.appearance.dict()
            }
            for char in characters
        ]
    }


@app.post("/api/v1/characters/extract")
async def extract_characters_from_script(script: str):
    """Extract characters from a script"""
    try:
        characters = character_service.extract_characters_from_script(script)
        
        return {
            "total_characters": len(characters),
            "characters": [
                {
                    "name": char.name,
                    "description": char.description,
                    "appearance": char.appearance.dict() if char.appearance else {},
                    "personality_traits": char.personality_traits
                }
                for char in characters
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract characters: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)