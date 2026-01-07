"""
Conversational API - Scenes Module
对话式API - 场景管理模块

Handles scene design and management including:
- Scene extraction and generation
- Scene concept art generation
- Scene image management
- Scene updates and regeneration
- Scene deletion
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import os

from database import get_db
from database_models import SceneDesign, EpisodeWorkflowSession
from workflows.conversational_episode_workflow import WorkflowState, WorkflowMode
from workflows.pipeline_adapter import create_adapter
from utils.async_wrapper import ProgressCallback

# Import from shared module
from api_routes_conv_shared import (
    # Models
    UpdateSceneRequest,
    
    # Helpers
    get_or_create_workflow,
    save_workflow_state,
    convert_file_path_to_url,
    validate_episode_exists,
    get_scene_by_id,
    
    # WebSocket
    ws_manager
)

# Create router
router = APIRouter(
    prefix="/api/v1/conversational",
    tags=["conversational-scenes"]
)


# ============================================================================
# Async Generation Functions
# ============================================================================

async def generate_scenes_async(workflow, db: Session):
    """异步生成场景"""
    try:
        workflow.transition_to(WorkflowState.SCENES_GENERATING)
        save_workflow_state(db, workflow)
        
        # Get episode_id_str for WebSocket topic
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        
        # Send WebSocket status update
        await ws_manager.send_status(
            topic=f"episode.{episode_id_str}.scenes",
            status="generating",
            message="Starting scene generation"
        )
        
        # Create pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        
        # Create progress callback
        progress = ProgressCallback()
        
        async def on_progress(percentage: float, message: str):
            print(f"[Scene Generation] {percentage*100:.1f}%: {message}")
            await ws_manager.send_progress(
                topic=f"episode.{episode_id_str}.scenes",
                percentage=percentage,
                message=message
            )
        
        progress.subscribe(on_progress)
        
        # Call AI generation logic
        scenes = await adapter.generate_scenes(
            outline=workflow.outline,
            characters=workflow.characters,
            style=workflow.style,
            progress=progress
        )
        
        workflow.scenes = scenes
        workflow.transition_to(WorkflowState.SCENES_GENERATED)
        
        # Check if we should clear existing or merge
        existing_count = db.query(SceneDesign).filter(SceneDesign.episode_id == episode_id_str).count()
        if existing_count > 0:
            # Re-generation - delete old scenes (full regenerate mode)
            db.query(SceneDesign).filter(SceneDesign.episode_id == episode_id_str).delete()
            db.flush()
        
        # Save to database and collect image URLs
        scene_images = []
        for scene in scenes:
            db_scene = SceneDesign(
                episode_id=episode_id_str,
                name=scene.name,
                description=scene.description,
                atmosphere=scene.atmosphere,
                image_url=convert_file_path_to_url(scene.image_url) if scene.image_url else None,
                status="completed"
            )
            db.add(db_scene)
            db.flush()
            
            scene_images.append({
                "id": db_scene.id,
                "name": scene.name,
                "image_url": db_scene.image_url,
                "atmosphere": scene.atmosphere
            })
        
        db.commit()
        save_workflow_state(db, workflow)
        
        # Send WebSocket completion with image data
        await ws_manager.send_completion(
            topic=f"episode.{episode_id_str}.scenes",
            message=f"Generated {len(scenes)} scenes",
            result={
                "count": len(scenes),
                "scenes": scene_images
            }
        )
        
        print(f"✅ Generated {len(scenes)} scenes for episode {workflow.episode_id}")
        
    except Exception as e:
        print(f"❌ Error generating scenes: {e}")
        import traceback
        traceback.print_exc()
        workflow.error = str(e)
        workflow.transition_to(WorkflowState.FAILED)
        save_workflow_state(db, workflow)
        db.commit()
        
        # Send WebSocket error
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        await ws_manager.send_error(
            topic=f"episode.{episode_id_str}.scenes",
            error_message="Scene generation failed",
            error_details={"error": str(e)}
        )


async def regenerate_scene_image_async(scene_id: str, episode_id: str, db: Session):
    """异步重新生成场景图片"""
    scene_design = None
    try:
        # Get scene design
        scene_design = get_scene_by_id(scene_id, episode_id, db)
        
        # Send WebSocket start notification
        await ws_manager.send_status(
            topic=f"episode.{episode_id}.scene.{scene_id}",
            status="regenerating",
            message=f"Regenerating {scene_design.name}"
        )
        
        # Get workflow session to get mode and style
        session = db.query(EpisodeWorkflowSession).filter(
            EpisodeWorkflowSession.episode_id == episode_id
        ).first()
        
        if not session:
            raise Exception("Workflow session not found")
        
        # Create pipeline adapter
        config_path = f"configs/{session.mode}2video.yaml"
        adapter = create_adapter(WorkflowMode(session.mode), config_path)
        await adapter.initialize_pipeline()
        
        # Generate new scene image
        print(f"[Regenerate] Generating new image for {scene_design.name}")
        
        # Use the scene generator from adapter
        if not adapter.scene_generator:
            raise Exception("Scene generator not available")
        
        image_output = await adapter.scene_generator.generate_scene_image(
            scene_name=scene_design.name,
            scene_description=scene_design.description,
            atmosphere=scene_design.atmosphere,
            style=session.style
        )
        
        # Save image
        if image_output.fmt == "url":
            image_url = image_output.data
        else:
            # Save to local
            scene_dir = os.path.join(adapter.pipeline.working_dir, "scenes")
            os.makedirs(scene_dir, exist_ok=True)
            image_path = os.path.join(scene_dir, f"scene_{scene_id}.{image_output.ext}")
            image_output.save(image_path)
            image_url = f"./{os.path.relpath(image_path, '.')}"
        
        # Update database
        scene_design.image_url = convert_file_path_to_url(image_url)
        scene_design.status = "completed"
        scene_design.updated_at = datetime.utcnow()
        db.commit()
        
        # Send WebSocket completion
        await ws_manager.send_completion(
            topic=f"episode.{episode_id}.scene.{scene_id}",
            message=f"Regenerated {scene_design.name}",
            result={
                "scene_id": scene_id,
                "name": scene_design.name,
                "image_url": scene_design.image_url
            }
        )
        
        # Also send to general scenes topic
        await ws_manager.send_status(
            topic=f"episode.{episode_id}.scenes",
            status="updated",
            message=f"Scene {scene_design.name} regenerated",
            details={"scene_id": scene_id}
        )
        
        print(f"✅ Regenerated scene {scene_design.name}")
        
    except Exception as e:
        print(f"❌ Error regenerating scene: {e}")
        import traceback
        traceback.print_exc()
        
        # Update status to failed
        if scene_design:
            scene_design.status = "failed"
            db.commit()
        
        # Send WebSocket error
        await ws_manager.send_error(
            topic=f"episode.{episode_id}.scene.{scene_id}",
            error_message="Scene regeneration failed",
            error_details={"error": str(e)}
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/episode/{episode_id}/scenes/generate")
async def generate_scenes(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    生成场景设计
    
    Generate scene designs with concept art.
    
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
        
        # Start scene generation in background
        background_tasks.add_task(generate_scenes_async, workflow, db)
        
        return {"message": "Scene generation started", "state": workflow.state}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/scenes/confirm")
async def confirm_scenes(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    确认场景设计
    
    Confirm scene designs and proceed to next step.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Success message with workflow state
    """
    try:
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        workflow.transition_to(WorkflowState.SCENES_CONFIRMED)
        save_workflow_state(db, workflow)
        
        return {"message": "Scenes confirmed", "state": workflow.state}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/scenes/images")
async def get_scene_images(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    获取场景生成的图片列表
    
    Returns list of scene images with metadata for display in workflow.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Scene images list with metadata
    """
    try:
        validate_episode_exists(episode_id, db)
        
        # Query scene designs for this episode
        db_scenes = db.query(SceneDesign).filter(
            SceneDesign.episode_id == episode_id,
            SceneDesign.status == "completed"
        ).all()
        
        if not db_scenes:
            return {
                "episode_id": episode_id,
                "scenes": [],
                "count": 0,
                "message": "No scene images found"
            }
        
        # Format scene data for frontend display
        scenes = []
        for scene in db_scenes:
            scenes.append({
                "id": scene.id,
                "name": scene.name,
                "description": scene.description,
                "atmosphere": scene.atmosphere,
                "image_url": scene.image_url,
                "status": scene.status,
                "created_at": scene.created_at.isoformat() if scene.created_at else None
            })
        
        return {
            "episode_id": episode_id,
            "scenes": scenes,
            "count": len(scenes),
            "message": f"Found {len(scenes)} scene(s)"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/scenes/{scene_id}/regenerate")
async def regenerate_scene_image(
    episode_id: str,
    scene_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    重新生成指定场景的图片
    
    Allows user to regenerate a specific scene image if unsatisfied.
    
    Args:
        episode_id: Episode ID
        scene_id: Scene ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Success message with regeneration status
    """
    try:
        validate_episode_exists(episode_id, db)
        scene_design = get_scene_by_id(scene_id, episode_id, db)
        
        # Mark as regenerating
        scene_design.status = "generating"
        db.commit()
        
        # Add background task to regenerate scene image
        background_tasks.add_task(regenerate_scene_image_async, scene_id, episode_id, db)
        
        return {
            "message": "Scene image regeneration started",
            "scene_id": scene_id,
            "scene_name": scene_design.name,
            "status": "generating"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/episode/{episode_id}/scenes/{scene_id}")
async def update_scene(
    episode_id: str,
    scene_id: str,
    request: UpdateSceneRequest,
    db: Session = Depends(get_db)
):
    """
    编辑单个场景的属性（不重新生成图片）
    
    Update a single scene's properties without regenerating the image.
    
    Args:
        episode_id: Episode ID
        scene_id: Scene ID
        request: Update request with optional fields
        db: Database session
        
    Returns:
        Updated scene data
    """
    try:
        validate_episode_exists(episode_id, db)
        scene = get_scene_by_id(scene_id, episode_id, db)
        
        # Update only provided fields
        if request.name is not None:
            scene.name = request.name
        if request.description is not None:
            scene.description = request.description
        if request.atmosphere is not None:
            scene.atmosphere = request.atmosphere
        
        scene.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Scene updated", "scene": scene.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/episode/{episode_id}/scenes/{scene_id}")
async def delete_scene(
    episode_id: str,
    scene_id: str,
    db: Session = Depends(get_db)
):
    """
    删除单个场景
    
    Delete a single scene.
    
    Args:
        episode_id: Episode ID
        scene_id: Scene ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        validate_episode_exists(episode_id, db)
        scene = get_scene_by_id(scene_id, episode_id, db)
        
        db.delete(scene)
        db.commit()
        
        return {"message": "Scene deleted", "scene_id": scene_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenes")
async def list_all_scenes(
    episode_id: str = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取所有场景列表（可选按集数过滤）
    
    List all scenes across episodes with optional filtering.
    
    Args:
        episode_id: Optional episode ID to filter by
        page: Page number
        page_size: Items per page
        db: Database session
        
    Returns:
        Paginated scene list
    """
    try:
        query = db.query(SceneDesign)
        
        if episode_id:
            query = query.filter(SceneDesign.episode_id == episode_id)
        
        total = query.count()
        total_pages = (total + page_size - 1) // page_size
        offset = (page - 1) * page_size
        
        scenes = query.order_by(SceneDesign.created_at.desc()).offset(offset).limit(page_size).all()
        
        return {
            "scenes": [s.to_dict() for s in scenes],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))