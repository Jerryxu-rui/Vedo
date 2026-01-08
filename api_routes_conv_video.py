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
        
        # Extract shot IDs and workflow mode for background task
        shot_ids = [shot.id for shot in all_shots]
        workflow_mode = workflow.mode.value
        workflow_style = workflow.style
        
        # Generate videos in background
        async def generate_all_videos():
            # ⚠️ CRITICAL: Create NEW database session for background task
            # The original session is request-scoped and will be closed
            from database import SessionLocal
            bg_db = SessionLocal()
            
            try:
                # Get workflow with new session
                bg_workflow = get_or_create_workflow(episode_id, bg_db)
                
                # Transition to VIDEO_GENERATING state first
                bg_workflow.transition_to(WorkflowState.VIDEO_GENERATING)
                save_workflow_state(bg_db, bg_workflow)
                
                # Initialize pipeline
                config_path = f"configs/{workflow_mode}2video.yaml"
                adapter = create_adapter(bg_workflow.mode, config_path)
                await adapter.initialize_pipeline()
                
                pipeline = adapter.pipeline
                video_generator = pipeline.video_generator
                working_dir = pipeline.working_dir
                
                logger.info(f"[Shot Videos] Pipeline initialized, working_dir: {working_dir}")
                
                # Get shots with new session
                for idx, shot_id in enumerate(shot_ids):
                    try:
                        # Fetch shot from database with new session
                        shot = bg_db.query(Shot).filter(Shot.id == shot_id).first()
                        if not shot:
                            logger.error(f"[Shot Videos] Shot {shot_id} not found")
                            continue
                        
                        logger.info(f"[Shot Videos] Generating video {idx + 1}/{len(shot_ids)} for shot {shot.shot_number}")
                        
                        # Update status
                        shot.status = 'generating_video'
                        bg_db.commit()
                        logger.info(f"[Shot Videos] Status updated to generating_video for shot {shot.id}")
                        
                        # Generate video
                        video_path = await generate_video_for_shot(
                            shot=shot,
                            style=workflow_style,
                            video_generator=video_generator,
                            working_dir=working_dir
                        )
                        
                        # Update shot with video URL
                        shot.video_url = video_path
                        shot.status = 'completed'
                        bg_db.commit()
                        
                        logger.info(f"[Shot Videos] ✅ Shot {idx + 1}/{len(shot_ids)} completed, video_url saved: {video_path}")
                        
                    except Exception as e:
                        logger.error(f"[Shot Videos] ❌ Shot {idx + 1} failed: {e}")
                        import traceback
                        traceback.print_exc()
                        
                        # Update shot status to failed
                        try:
                            shot = bg_db.query(Shot).filter(Shot.id == shot_id).first()
                            if shot:
                                shot.status = 'failed'
                                bg_db.commit()
                        except Exception as update_error:
                            logger.error(f"[Shot Videos] Failed to update shot status: {update_error}")
                        continue
                
                # Update workflow state
                bg_workflow.transition_to(WorkflowState.VIDEO_COMPLETED)
                save_workflow_state(bg_db, bg_workflow)
                
                logger.info(f"[Shot Videos] ✅ All videos generated for episode {episode_id}")
                
            except Exception as e:
                logger.error(f"[Shot Videos] ❌ Generation failed: {e}")
                import traceback
                traceback.print_exc()
                
                try:
                    bg_workflow = get_or_create_workflow(episode_id, bg_db)
                    bg_workflow.error = str(e)
                    save_workflow_state(bg_db, bg_workflow)
                except Exception as save_error:
                    logger.error(f"[Shot Videos] Failed to save error state: {save_error}")
            finally:
                # Always close the background session
                bg_db.close()
                logger.info(f"[Shot Videos] Background database session closed")
        
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


@router.post("/episode/{episode_id}/shots/{shot_id}/regenerate-video")
async def regenerate_shot_video(
    episode_id: str,
    shot_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Regenerate video for a single shot
    
    Allows user to regenerate a specific shot's video if unsatisfied.
    
    Args:
        episode_id: Episode ID
        shot_id: Shot ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Success message with regeneration status
    """
    try:
        logger.info(f"[Shot Regenerate] Starting for shot: {shot_id}")
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        # Get the shot
        shot = db.query(Shot).filter(Shot.id == shot_id).first()
        if not shot:
            raise HTTPException(status_code=404, detail="Shot not found")
        
        # Verify shot belongs to this episode
        scene = db.query(Scene).filter(Scene.id == shot.scene_id).first()
        if not scene or scene.episode_id != episode_id:
            raise HTTPException(status_code=404, detail="Shot not found in this episode")
        
        logger.info(f"[Shot Regenerate] Found shot {shot.shot_number}: {shot.visual_desc[:50]}...")
        
        # Mark as regenerating
        shot.status = 'generating_video'
        db.commit()
        
        # Extract data for background task
        workflow_mode = workflow.mode.value
        workflow_style = workflow.style
        
        async def regenerate_video():
            # ⚠️ CRITICAL: Create NEW database session for background task
            from database import SessionLocal
            bg_db = SessionLocal()
            
            try:
                # Get shot with new session
                shot = bg_db.query(Shot).filter(Shot.id == shot_id).first()
                if not shot:
                    logger.error(f"[Shot Regenerate] Shot {shot_id} not found in background task")
                    return
                
                # Initialize pipeline
                config_path = f"configs/{workflow_mode}2video.yaml"
                bg_workflow = get_or_create_workflow(episode_id, bg_db)
                adapter = create_adapter(bg_workflow.mode, config_path)
                await adapter.initialize_pipeline()
                
                pipeline = adapter.pipeline
                video_generator = pipeline.video_generator
                working_dir = pipeline.working_dir
                
                logger.info(f"[Shot Regenerate] Pipeline initialized")
                
                # Generate video
                video_path = await generate_video_for_shot(
                    shot=shot,
                    style=workflow_style,
                    video_generator=video_generator,
                    working_dir=working_dir
                )
                
                # Update shot with new video URL
                shot.video_url = video_path
                shot.status = 'completed'
                bg_db.commit()
                
                logger.info(f"[Shot Regenerate] ✅ Completed: {video_path}, video_url saved to database")
                
            except Exception as e:
                logger.error(f"[Shot Regenerate] ❌ Failed: {e}")
                import traceback
                traceback.print_exc()
                
                try:
                    shot = bg_db.query(Shot).filter(Shot.id == shot_id).first()
                    if shot:
                        shot.status = 'failed'
                        bg_db.commit()
                except Exception as update_error:
                    logger.error(f"[Shot Regenerate] Failed to update shot status: {update_error}")
            finally:
                # Always close the background session
                bg_db.close()
                logger.info(f"[Shot Regenerate] Background database session closed")
        
        # Start regeneration in background
        background_tasks.add_task(regenerate_video)
        
        return {
            "message": "Shot video regeneration started",
            "shot_id": shot_id,
            "shot_number": shot.shot_number,
            "status": "generating"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Shot Regenerate] Error: {e}")
        db.rollback()
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
                logger.info(f"[Compilation {job_id}] Starting compilation")
                logger.info(f"[Compilation {job_id}] Video paths: {video_paths}")
                
                # Check if all video files exist
                missing_files = []
                for path in video_paths:
                    if not os.path.exists(path):
                        missing_files.append(path)
                        logger.error(f"[Compilation {job_id}] Missing video file: {path}")
                
                if missing_files:
                    raise Exception(f"Missing video files: {missing_files}")
                
                from moviepy.editor import VideoFileClip, concatenate_videoclips
                
                logger.info(f"[Compilation {job_id}] Loading {len(video_paths)} video clips")
                
                # Load video clips
                clips = []
                for idx, path in enumerate(video_paths):
                    try:
                        logger.info(f"[Compilation {job_id}] Loading clip {idx + 1}/{len(video_paths)}: {path}")
                        clip = VideoFileClip(path)
                        clips.append(clip)
                        logger.info(f"[Compilation {job_id}] ✅ Loaded clip {idx + 1}: duration={clip.duration}s")
                    except Exception as e:
                        logger.error(f"[Compilation {job_id}] ❌ Failed to load {path}: {e}")
                        continue
                
                if not clips:
                    raise Exception("No valid video clips to compile")
                
                logger.info(f"[Compilation {job_id}] Concatenating {len(clips)} clips")
                
                # Concatenate
                final_clip = concatenate_videoclips(clips, method="compose")
                logger.info(f"[Compilation {job_id}] ✅ Concatenated, total duration: {final_clip.duration}s")
                
                # Save
                output_dir = f".working_dir/episodes/{episode_id}"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, "final_video.mp4")
                
                logger.info(f"[Compilation {job_id}] Writing final video to {output_path}")
                final_clip.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    verbose=True,
                    logger='bar'
                )
                
                # Clean up
                logger.info(f"[Compilation {job_id}] Cleaning up clips")
                for clip in clips:
                    clip.close()
                final_clip.close()
                
                # Update workflow
                logger.info(f"[Compilation {job_id}] Updating workflow state")
                workflow = get_or_create_workflow(episode_id, db)
                workflow.context["video_path"] = output_path
                workflow.context["compilation_job_id"] = job_id
                workflow.transition_to(WorkflowState.VIDEO_COMPLETED)
                save_workflow_state(db, workflow)
                
                # Update episode
                episode = db.query(Episode).filter(Episode.id == episode_id).first()
                if episode:
                    episode.status = "completed"
                    db.commit()
                
                logger.info(f"[Compilation {job_id}] ✅ Completed: {output_path}")
                
            except Exception as e:
                logger.error(f"[Compilation {job_id}] ❌ Failed: {e}")
                import traceback
                traceback.print_exc()
                
                # Update workflow with error
                try:
                    workflow = get_or_create_workflow(episode_id, db)
                    workflow.error = str(e)
                    workflow.context["compilation_error"] = str(e)
                    workflow.context["compilation_job_id"] = job_id
                    save_workflow_state(db, workflow)
                except Exception as save_error:
                    logger.error(f"[Compilation {job_id}] Failed to save error state: {save_error}")
        
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