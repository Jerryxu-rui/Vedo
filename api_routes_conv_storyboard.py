"""
Conversational API - Storyboard Module
对话式API - 分镜管理模块

Handles storyboard generation including:
- Storyboard generation from scenes
- Shot-level planning
- Storyboard confirmation
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from database_models import Scene, Shot
from workflows.conversational_episode_workflow import WorkflowState
from workflows.pipeline_adapter import create_adapter
from utils.async_wrapper import ProgressCallback

# Import from shared module
from api_routes_conv_shared import (
    # Helpers
    get_or_create_workflow,
    save_workflow_state,
    validate_episode_exists,
    
    # WebSocket
    ws_manager
)

# Create router
router = APIRouter(
    prefix="/api/v1/conversational",
    tags=["conversational-storyboard"]
)


# ============================================================================
# Async Generation Functions
# ============================================================================

async def generate_storyboard_async(workflow, db: Session):
    """异步生成分镜"""
    try:
        workflow.transition_to(WorkflowState.STORYBOARD_GENERATING)
        save_workflow_state(db, workflow)
        
        # Create pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        
        # Get script content
        script = workflow.context.get("initial_content", "")
        
        # Create progress callback
        progress = ProgressCallback()
        
        async def on_progress(percentage: float, message: str):
            print(f"[Storyboard Generation] {percentage*100:.1f}%: {message}")
        
        progress.subscribe(on_progress)
        
        # Call AI generation logic
        storyboard = await adapter.generate_storyboard(
            outline=workflow.outline,
            characters=workflow.characters,
            scenes=workflow.scenes,
            style=workflow.style,
            script=script,
            progress=progress
        )
        
        workflow.storyboard = storyboard
        
        # Save storyboard shots to database
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        
        # Check if we should clear existing or merge
        existing_count = db.query(Scene).filter(Scene.episode_id == episode_id_str).count()
        if existing_count > 0:
            # Re-generation - delete old storyboard scenes/shots
            old_scenes = db.query(Scene).filter(Scene.episode_id == episode_id_str).all()
            for old_scene in old_scenes:
                db.query(Shot).filter(Shot.scene_id == old_scene.id).delete()
            db.query(Scene).filter(Scene.episode_id == episode_id_str).delete()
            db.flush()
        
        # Group shots by scene name
        scene_shots = {}
        for shot in storyboard:
            scene_name = shot.scene_name
            if scene_name not in scene_shots:
                scene_shots[scene_name] = []
            scene_shots[scene_name].append(shot)
        
        # Create Scene and Shot records
        for scene_idx, (scene_name, shots) in enumerate(scene_shots.items()):
            # Create or get scene
            db_scene = db.query(Scene).filter(
                Scene.episode_id == episode_id_str,
                Scene.scene_number == scene_idx + 1
            ).first()
            
            if not db_scene:
                db_scene = Scene(
                    episode_id=episode_id_str,
                    scene_number=scene_idx + 1,
                    location=scene_name,
                    description=f"Scene: {scene_name}"
                )
                db.add(db_scene)
                db.flush()
            
            # Create shot records
            for shot in shots:
                db_shot = Shot(
                    scene_id=db_scene.id,
                    shot_number=shot.shot_number,
                    visual_desc=shot.visual_desc,
                    camera_angle=shot.camera_angle,
                    camera_movement=shot.camera_movement,
                    dialogue=shot.dialogue,
                    voice_actor=shot.voice_actor,
                    status="completed"
                )
                db.add(db_shot)
        
        db.commit()
        print(f"[Storyboard] Saved {len(storyboard)} shots to database")
        
        workflow.transition_to(WorkflowState.STORYBOARD_GENERATED)
        save_workflow_state(db, workflow)
        
        print(f"✅ Generated {len(storyboard)} shots for episode {workflow.episode_id}")
        
    except Exception as e:
        print(f"❌ Error generating storyboard: {e}")
        import traceback
        traceback.print_exc()
        workflow.error = str(e)
        workflow.transition_to(WorkflowState.FAILED)
        save_workflow_state(db, workflow)
        db.commit()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/episode/{episode_id}/storyboard/generate")
async def generate_storyboard(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    生成分镜剧本
    
    Generate storyboard with shot-level details.
    
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
        
        # Start storyboard generation in background
        background_tasks.add_task(generate_storyboard_async, workflow, db)
        
        return {"message": "Storyboard generation started", "state": workflow.state}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/storyboard/confirm")
async def confirm_storyboard(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    确认分镜剧本
    
    Confirm storyboard and proceed to video generation.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Success message with workflow state
    """
    try:
        print(f"[Storyboard Confirm] Starting for episode: {episode_id}")
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        print(f"[Storyboard Confirm] Current state: {workflow.state}")
        print(f"[Storyboard Confirm] Storyboard count: {len(workflow.storyboard)}")
        
        # Check if we can transition to STORYBOARD_CONFIRMED
        if workflow.state == WorkflowState.STORYBOARD_GENERATED:
            workflow.transition_to(WorkflowState.STORYBOARD_CONFIRMED)
            save_workflow_state(db, workflow)
            print(f"[Storyboard Confirm] Successfully transitioned to STORYBOARD_CONFIRMED")
        elif workflow.state == WorkflowState.STORYBOARD_CONFIRMED:
            # Already confirmed, just return success
            print(f"[Storyboard Confirm] Already in STORYBOARD_CONFIRMED state")
        else:
            # Try to force transition if storyboard exists
            if len(workflow.storyboard) > 0:
                print(f"[Storyboard Confirm] Forcing transition from {workflow.state} to STORYBOARD_CONFIRMED")
                workflow.state = WorkflowState.STORYBOARD_CONFIRMED
                save_workflow_state(db, workflow)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot confirm storyboard in current state: {workflow.state}. Storyboard must be generated first."
                )
        
        return {"message": "Storyboard confirmed", "state": workflow.state}
        
    except HTTPException:
        raise
    except ValueError as e:
        # State transition error
        print(f"[Storyboard Confirm] State transition error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[Storyboard Confirm] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# NOTE: Shot deletion endpoint moved to api_routes_conv_assets.py
# Use: DELETE /api/v1/conversational/episode/{episode_id}/shots/{shot_id}