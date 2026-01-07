"""
Conversational API - Video Module
对话式API - 视频生成模块

Handles video generation including:
- Final video generation
- Shot-by-shot video creation
- Video assembly
- Direct shot-based video generation (NEW)
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import logging

from database import get_db
from database_models import Episode, Shot, Scene
from workflows.conversational_episode_workflow import WorkflowState
from workflows.pipeline_adapter import create_adapter
from utils.websocket_manager import ProgressWebSocketCallback

logger = logging.getLogger(__name__)

# Import from shared module
from api_routes_conv_shared import (
    # Helpers
    get_or_create_workflow,
    save_workflow_state,
    convert_file_path_to_url,
    validate_episode_exists,
    
    # WebSocket
    ws_manager
)

# Create router
router = APIRouter(
    prefix="/api/v1/conversational",
    tags=["conversational-video"]
)


# ============================================================================
# Async Generation Functions
# ============================================================================

async def generate_video_async(workflow, db: Session):
    """异步生成视频"""
    try:
        print(f"[Video Generation] Starting video generation for episode {workflow.episode_id}")
        workflow.transition_to(WorkflowState.VIDEO_GENERATING)
        save_workflow_state(db, workflow)
        
        # Create pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        print(f"[Video Generation] Loading config from {config_path}")
        adapter = create_adapter(workflow.mode, config_path)
        print(f"[Video Generation] Initializing pipeline...")
        await adapter.initialize_pipeline()
        print(f"[Video Generation] Pipeline initialized successfully")
        
        # Get episode_id_str
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        
        # Create WebSocket progress callback
        ws_callback = ProgressWebSocketCallback(
            topic=f"episode.{episode_id_str}.video",
            manager=ws_manager
        )
        
        # Send start message
        await ws_manager.send_status(
            topic=f"episode.{episode_id_str}.video",
            status="started",
            message="Video generation started"
        )
        
        # Call actual video generation logic
        print(f"[Video Generation] Calling adapter.generate_video with {len(workflow.storyboard)} shots, {len(workflow.characters)} characters, {len(workflow.scenes)} scenes")
        result = await adapter.generate_video(
            storyboard=workflow.storyboard,
            characters=workflow.characters,
            scenes=workflow.scenes,
            style=workflow.style,
            episode_id=episode_id_str,
            progress=ws_callback
        )
        print(f"[Video Generation] Result: {result}")
        
        if result.get("success"):
            workflow.transition_to(WorkflowState.VIDEO_COMPLETED)
            workflow.context["video_path"] = result.get("video_path")
            workflow.context["video_metadata"] = {
                "total_shots": result.get("total_shots"),
                "successful_shots": result.get("successful_shots"),
                "failed_shots": result.get("failed_shots")
            }
            
            # Update Episode record
            episode = db.query(Episode).filter(Episode.id == episode_id_str).first()
            if episode:
                episode.status = "completed"
                # Store relative path for video
                video_path = result.get("video_path", "")
                if video_path.startswith('./'):
                    video_path = video_path[2:]
                episode.script = video_path  # Temporarily store in script field
                db.commit()
            
            # Send completion message
            await ws_manager.send_completion(
                topic=f"episode.{episode_id_str}.video",
                result={
                    "video_path": convert_file_path_to_url(result.get("video_path")),
                    "metadata": workflow.context["video_metadata"]
                },
                message="Video generation completed successfully"
            )
            
            print(f"✅ Generated video for episode {workflow.episode_id}")
        else:
            workflow.error = result.get("error", "Unknown error")
            workflow.transition_to(WorkflowState.FAILED)
            
            # Send error message
            await ws_manager.send_error(
                topic=f"episode.{episode_id_str}.video",
                error_message="Video generation failed",
                error_details={"error": workflow.error}
            )
        
        save_workflow_state(db, workflow)
        
    except Exception as e:
        print(f"❌ Error generating video: {e}")
        import traceback
        traceback.print_exc()
        workflow.error = str(e)
        workflow.transition_to(WorkflowState.FAILED)
        save_workflow_state(db, workflow)
        db.commit()
        
        # Send error message
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        await ws_manager.send_error(
            topic=f"episode.{episode_id_str}.video",
            error_message="Video generation failed with exception",
            error_details={"error": str(e), "traceback": traceback.format_exc()}
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/episode/{episode_id}/video/generate")
async def start_video_generation(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    开始视频生成
    
    Start final video generation from storyboard.
    
    Args:
        episode_id: Episode ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Success message with workflow state
    """
    try:
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        # Start video generation in background
        background_tasks.add_task(generate_video_async, workflow, db)
        
        return {"message": "Video generation started", "state": workflow.state}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NEW: Direct Shot-Based Video Generation (Best Solution)
# ============================================================================

class CompileRequest(BaseModel):
    """Request model for video compilation"""
    shot_ids: List[str]
    transition_style: Optional[str] = 'fade'
    audio_config: Optional[dict] = None


async def generate_video_for_shot(
    shot: Shot,
    style: str,
    video_generator,
    working_dir: str
) -> str:
    """Generate video for a single shot"""
    try:
        # Create shot directory
        shot_dir = os.path.join(working_dir, f"shot_{shot.shot_number}")
        os.makedirs(shot_dir, exist_ok=True)
        
        # Prepare prompt
        prompt = f"{shot.visual_desc}. Camera: {shot.camera_angle}."
        if shot.camera_movement:
            prompt += f" Movement: {shot.camera_movement}."
        
        logger.info(f"[Shot Video] Generating for shot {shot.shot_number}: {prompt[:100]}...")
        
        # Generate video using the correct method name
        from PIL import Image
        import requests
        from io import BytesIO
        
        # Download the frame image if it's a URL
        reference_images = []
        if shot.frame_url:
            try:
                if shot.frame_url.startswith('http'):
                    response = requests.get(shot.frame_url)
                    img = Image.open(BytesIO(response.content))
                else:
                    img = Image.open(shot.frame_url)
                reference_images.append(img)
            except Exception as e:
                logger.warning(f"Could not load reference image: {e}")
        
        # Generate video
        video_output = await video_generator.generate_single_video(
            prompt=prompt,
            reference_image_paths=reference_images,
            aspect_ratio="9:16"
        )
        
        # Save video from URL or data
        if video_output.fmt == "url":
            # Download video from URL
            video_response = requests.get(video_output.data)
            video_path = os.path.join(shot_dir, "video.mp4")
            with open(video_path, 'wb') as f:
                f.write(video_response.content)
        else:
            video_path = os.path.join(shot_dir, "video.mp4")
            with open(video_path, 'wb') as f:
                f.write(video_output.data)
        
        logger.info(f"[Shot Video] ✅ Generated: {video_path}")
        return video_path
        
    except Exception as e:
        logger.error(f"[Shot Video] ❌ Failed for shot {shot.shot_number}: {e}")
        raise


@router.post("/episode/{episode_id}/shots/generate-videos")
async def generate_videos_for_shots(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate videos directly for all shots in the storyboard
    
    This is the CORRECT endpoint to use for shot-based video generation.
    It generates videos directly for shots and updates Shot.video_url.
    
    Args:
        episode_id: Episode ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Success message with shot count
    """
    try:
        logger.info(f"[Shot Videos] Starting generation for episode: {episode_id}")
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        # Get all shots from database using episode_id
        # First get all scenes for this episode
        scenes = db.query(Scene).filter(
            Scene.episode_id == episode_id
        ).all()
        
        # Then get all shots for these scenes
        all_shots = []
        for scene in scenes:
            scene_shots = db.query(Shot).filter(
                Shot.scene_id == scene.id
            ).order_by(Shot.shot_number).all()
            all_shots.extend(scene_shots)
        
        if not all_shots:
            raise HTTPException(status_code=404, detail="No shots found in storyboard")
        
        logger.info(f"[Shot Videos] Found {len(all_shots)} shots to generate")
        
        # Generate videos in background
        async def generate_all_videos():
            try:
                # Initialize pipeline
                config_path = f"configs/{workflow.mode.value}2video.yaml"
                adapter = create_adapter(workflow.mode, config_path)
                await adapter.initialize_pipeline()
                
                pipeline = adapter.pipeline
                video_generator = pipeline.video_generator
                working_dir = pipeline.working_dir
                
                logger.info(f"[Shot Videos] Pipeline initialized, working_dir: {working_dir}")
                
                for idx, shot in enumerate(all_shots):
                    try:
                        logger.info(f"[Shot Videos] Generating video {idx + 1}/{len(all_shots)} for shot {shot.shot_number}")
                        
                        # Update status
                        shot.status = 'generating_video'
                        db.commit()
                        
                        # Generate video
                        video_path = await generate_video_for_shot(
                            shot=shot,
                            style=workflow.style,
                            video_generator=video_generator,
                            working_dir=working_dir
                        )
                        
                        # Update shot with video URL
                        shot.video_url = video_path
                        shot.status = 'completed'
                        db.commit()
                        
                        logger.info(f"[Shot Videos] ✅ Shot {idx + 1}/{len(all_shots)} completed")
                        
                    except Exception as e:
                        logger.error(f"[Shot Videos] ❌ Shot {idx + 1} failed: {e}")
                        shot.status = 'failed'
                        db.commit()
                        continue
                
                # Update workflow state
                workflow.transition_to(WorkflowState.VIDEO_COMPLETED)
                save_workflow_state(db, workflow)
                
                logger.info(f"[Shot Videos] ✅ All videos generated for episode {episode_id}")
                
            except Exception as e:
                logger.error(f"[Shot Videos] ❌ Generation failed: {e}")
                import traceback
                traceback.print_exc()
                workflow.error = str(e)
                # Don't transition to FAILED, just log the error
                # The workflow can stay in current state
                save_workflow_state(db, workflow)
        
        # Start generation in background
        background_tasks.add_task(generate_all_videos)
        
        return {
            "message": "Video generation started",
            "total_shots": len(all_shots),
            "episode_id": episode_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Shot Videos] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/shots/video-status")
async def get_video_generation_status(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    Get video generation status for all shots
    
    Returns detailed status for each shot including video URLs.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Status summary and shot details
    """
    try:
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        # Get all shots from database using episode_id
        # First get all scenes for this episode
        scenes = db.query(Scene).filter(
            Scene.episode_id == episode_id
        ).all()
        
        # Then get all shots for these scenes
        all_shots = []
        for scene in scenes:
            scene_shots = db.query(Shot).filter(
                Shot.scene_id == scene.id
            ).order_by(Shot.shot_number).all()
            all_shots.extend(scene_shots)
        
        # Calculate statistics
        total = len(all_shots)
        completed = sum(1 for s in all_shots if s.status == 'completed' and s.video_url)
        generating = sum(1 for s in all_shots if s.status == 'generating_video')
        failed = sum(1 for s in all_shots if s.status == 'failed')
        pending = total - completed - generating - failed
        
        return {
            "episode_id": episode_id,
            "total_shots": total,
            "completed": completed,
            "generating": generating,
            "failed": failed,
            "pending": pending,
            "all_done": completed + failed == total,
            "shots": [
                {
                    "id": shot.id,
                    "shot_number": shot.shot_number,
                    "status": shot.status,
                    "video_url": convert_file_path_to_url(shot.video_url) if shot.video_url else None,
                    "frame_url": convert_file_path_to_url(shot.frame_url) if shot.frame_url else None,
                    "visual_desc": shot.visual_desc,
                    "camera_angle": shot.camera_angle,
                    "camera_movement": shot.camera_movement
                }
                for shot in all_shots
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Shot Videos] Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/video/compile")
async def compile_shot_videos(
    episode_id: str,
    request: CompileRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Compile shot videos into final video
    
    Takes a list of shot IDs and compiles their videos into a single final video.
    
    Args:
        episode_id: Episode ID
        request: Compilation request with shot IDs and settings
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Job ID for tracking compilation progress
    """
    try:
        validate_episode_exists(episode_id, db)
        
        if not request.shot_ids:
            raise HTTPException(status_code=400, detail="No shots provided")
        
        # Get shots
        shots = db.query(Shot).filter(
            Shot.id.in_(request.shot_ids)
        ).order_by(Shot.shot_number).all()
        
        # Get video paths
        video_paths = [shot.video_url for shot in shots if shot.video_url]
        
        if not video_paths:
            raise HTTPException(status_code=400, detail="No videos to compile")
        
        logger.info(f"[Compilation] Starting for {len(video_paths)} videos")
        
        # Create compilation job
        job_id = str(uuid.uuid4())
        
        async def compile_videos():
            try:
                from moviepy.editor import VideoFileClip, concatenate_videoclips
                
                logger.info(f"[Compilation] Loading {len(video_paths)} video clips")
                
                # Load video clips
                clips = []
                for path in video_paths:
                    try:
                        clip = VideoFileClip(path)
                        clips.append(clip)
                    except Exception as e:
                        logger.error(f"[Compilation] Failed to load {path}: {e}")
                        continue
                
                if not clips:
                    raise Exception("No valid video clips to compile")
                
                logger.info(f"[Compilation] Concatenating {len(clips)} clips")
                
                # Concatenate
                final_clip = concatenate_videoclips(clips, method="compose")
                
                # Save
                output_dir = f".working_dir/episodes/{episode_id}"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, "final_video.mp4")
                
                logger.info(f"[Compilation] Writing final video to {output_path}")
                final_clip.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True
                )
                
                # Clean up
                for clip in clips:
                    clip.close()
                final_clip.close()
                
                # Update workflow
                workflow = get_or_create_workflow(episode_id, db)
                workflow.context["video_path"] = output_path
                workflow.transition_to(WorkflowState.VIDEO_COMPLETED)
                save_workflow_state(db, workflow)
                
                # Update episode
                episode = db.query(Episode).filter(Episode.id == episode_id).first()
                if episode:
                    episode.status = "completed"
                    db.commit()
                
                logger.info(f"[Compilation] ✅ Completed: {output_path}")
                
            except Exception as e:
                logger.error(f"[Compilation] ❌ Failed: {e}")
                import traceback
                traceback.print_exc()
        
        background_tasks.add_task(compile_videos)
        
        return {
            "job_id": job_id,
            "message": "Compilation started",
            "total_shots": len(video_paths),
            "episode_id": episode_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Compilation] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/video/compilation-status/{job_id}")
async def get_compilation_status(
    episode_id: str,
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get compilation job status
    
    Args:
        episode_id: Episode ID
        job_id: Compilation job ID
        db: Database session
        
    Returns:
        Compilation status and result
    """
    try:
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        # Check if compilation is complete
        video_path = workflow.context.get("video_path")
        
        if video_path and os.path.exists(video_path):
            return {
                "job_id": job_id,
                "status": "completed",
                "output_path": convert_file_path_to_url(video_path),
                "message": "Compilation completed successfully"
            }
        elif workflow.state == WorkflowState.VIDEO_COMPLETED:
            return {
                "job_id": job_id,
                "status": "completed",
                "output_path": convert_file_path_to_url(video_path) if video_path else None,
                "message": "Compilation completed"
            }
        elif workflow.state == WorkflowState.FAILED:
            return {
                "job_id": job_id,
                "status": "failed",
                "error": workflow.error,
                "message": "Compilation failed"
            }
        else:
            return {
                "job_id": job_id,
                "status": "processing",
                "message": "Compilation in progress"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Compilation] Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))