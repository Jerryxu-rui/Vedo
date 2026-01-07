"""
Conversational API - Outline Module
对话式API - 大纲管理模块

Handles story outline generation and management including:
- Outline generation from idea/script
- Outline editing and updates
- Outline confirmation and progression
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import os

from database import get_db
from database_models import Episode, EpisodeOutline
from workflows.conversational_episode_workflow import WorkflowState
from workflows.pipeline_adapter import create_adapter
from utils.async_wrapper import ProgressCallback

# Import from shared module
from api_routes_conv_shared import (
    # Models
    UpdateOutlineRequest,
    
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
    tags=["conversational-outline"]
)


# ============================================================================
# Async Generation Functions
# ============================================================================

async def generate_outline_async(workflow, db: Session):
    """
    异步生成大纲
    
    Phase 1.1: Generate structured video outline from user input
    """
    try:
        print(f"\n{'='*60}")
        print(f"[Phase 1.1] OUTLINE GENERATION STARTED")
        print(f"Episode ID: {workflow.episode_id}")
        print(f"Mode: {workflow.mode}")
        print(f"{'='*60}\n")
        
        workflow.transition_to(WorkflowState.OUTLINE_GENERATING)
        save_workflow_state(db, workflow)
        
        # Get episode_id_str for WebSocket and database
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        
        # Send WebSocket status update
        await ws_manager.send_status(
            topic=f"episode.{episode_id_str}.outline",
            status="generating",
            message="Starting outline generation from your input"
        )
        
        # Create pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        if not os.path.exists(config_path):
            raise Exception(f"Config file not found: {config_path}")
        
        print(f"[Phase 1.1] Initializing {workflow.mode} pipeline...")
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        
        # Create progress callback
        progress = ProgressCallback()
        
        async def on_progress(percentage: float, message: str):
            print(f"[Phase 1.1] {percentage*100:.1f}%: {message}")
            await ws_manager.send_progress(
                topic=f"episode.{episode_id_str}.outline",
                percentage=percentage,
                message=message
            )
        
        progress.subscribe(on_progress)
        
        # Get initial content
        initial_content = workflow.context.get("initial_content", "")
        print(f"[Phase 1.1] Input content length: {len(initial_content)} characters")
        
        # Call AI generation logic
        print(f"[Phase 1.1] Calling LLM to generate outline...")
        await progress.update(0.1, "Analyzing your input...")
        
        outline = await adapter.generate_outline(
            initial_content,
            workflow.style
        )
        
        await progress.update(0.9, "Finalizing outline structure...")
        
        workflow.outline = outline
        workflow.transition_to(WorkflowState.OUTLINE_GENERATED)
        
        # Save to database
        print(f"[Phase 1.1] Saving outline to database...")
        db_outline = EpisodeOutline(
            episode_id=episode_id_str,
            title=outline.title,
            genre=outline.genre,
            style=outline.style,
            episode_count=outline.episode_count,
            synopsis=outline.synopsis,
            characters_summary=outline.characters_summary,
            plot_summary=outline.plot_summary,
            highlights=outline.highlights
        )
        db.add(db_outline)
        db.commit()
        save_workflow_state(db, workflow)
        
        # Send WebSocket completion
        await ws_manager.send_completion(
            topic=f"episode.{episode_id_str}.outline",
            message="Outline generated successfully",
            result={
                "title": outline.title,
                "genre": outline.genre,
                "character_count": len(outline.characters_summary),
                "plot_points": len(outline.plot_summary)
            }
        )
        
        print(f"✅ [Phase 1.1] Outline generation completed")
        print(f"   Title: {outline.title}")
        print(f"   Genre: {outline.genre}")
        print(f"   Characters: {len(outline.characters_summary)}")
        print(f"   Plot points: {len(outline.plot_summary)}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ [Phase 1.1] Error generating outline: {e}")
        import traceback
        traceback.print_exc()
        workflow.error = str(e)
        workflow.transition_to(WorkflowState.FAILED)
        save_workflow_state(db, workflow)
        db.commit()
        
        # Send WebSocket error
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        await ws_manager.send_error(
            topic=f"episode.{episode_id_str}.outline",
            error_message="Outline generation failed",
            error_details={"error": str(e)}
        )


async def refine_content_async(workflow, db: Session):
    """
    异步细化内容
    
    Phase 1.3: Content Refinement
    """
    try:
        print(f"\n{'='*60}")
        print(f"[Phase 1.3] CONTENT REFINEMENT STARTED")
        print(f"Episode ID: {workflow.episode_id}")
        print(f"{'='*60}\n")
        
        workflow.transition_to(WorkflowState.REFINING)
        save_workflow_state(db, workflow)
        
        # Get episode_id_str for WebSocket
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        
        # Send WebSocket status update
        await ws_manager.send_status(
            topic=f"episode.{episode_id_str}.refine",
            status="refining",
            message="Expanding outline into detailed content"
        )
        
        # Create progress callback
        progress = ProgressCallback()
        
        async def on_progress(percentage: float, message: str):
            print(f"[Phase 1.3] {percentage*100:.1f}%: {message}")
            await ws_manager.send_progress(
                topic=f"episode.{episode_id_str}.refine",
                percentage=percentage,
                message=message
            )
        
        progress.subscribe(on_progress)
        
        # Get outline
        if not workflow.outline:
            raise Exception("No outline available for refinement")
        
        print(f"[Phase 1.3] Refining outline: {workflow.outline.title}")
        await progress.update(0.1, "Analyzing outline structure...")
        
        # Build refined content from outline
        refined_content = f"# {workflow.outline.title}\n\n"
        refined_content += f"**Genre:** {workflow.outline.genre}\n"
        refined_content += f"**Style:** {workflow.outline.style}\n\n"
        
        await progress.update(0.3, "Expanding character descriptions...")
        
        # Add detailed character descriptions
        refined_content += "## Characters\n\n"
        for char_summary in workflow.outline.characters_summary:
            char_name = char_summary.get("name", "Unknown")
            char_role = char_summary.get("role", "")
            char_desc = char_summary.get("description", "")
            refined_content += f"### {char_name} ({char_role})\n"
            refined_content += f"{char_desc}\n\n"
        
        await progress.update(0.5, "Expanding plot details...")
        
        # Add detailed plot with scene descriptions
        refined_content += "## Story\n\n"
        refined_content += f"{workflow.outline.synopsis}\n\n"
        
        refined_content += "## Detailed Plot\n\n"
        for i, plot_point in enumerate(workflow.outline.plot_summary):
            act = plot_point.get("act", f"Act {i+1}")
            description = plot_point.get("description", "")
            refined_content += f"### {act}\n"
            refined_content += f"{description}\n\n"
            
            # Add visual directions
            refined_content += f"**Visual Direction:** "
            if i == 0:
                refined_content += "Opening scene should establish the setting and introduce main characters.\n"
            elif i == len(workflow.outline.plot_summary) - 1:
                refined_content += "Closing scene should provide resolution and emotional impact.\n"
            else:
                refined_content += "Scene should advance the plot and develop character relationships.\n"
            refined_content += "\n"
        
        await progress.update(0.8, "Adding highlights and themes...")
        
        # Add highlights
        if workflow.outline.highlights:
            refined_content += "## Key Highlights\n\n"
            for highlight in workflow.outline.highlights:
                refined_content += f"- {highlight}\n"
            refined_content += "\n"
        
        await progress.update(0.9, "Finalizing refined content...")
        
        # Store refined content
        workflow.refined_content = refined_content
        workflow.context["refined_at"] = datetime.utcnow().isoformat()
        workflow.context["content_length"] = len(refined_content)
        
        # Transition to refined state
        workflow.transition_to(WorkflowState.REFINED)
        save_workflow_state(db, workflow)
        
        # Update episode with refined content
        episode = db.query(Episode).filter(Episode.id == episode_id_str).first()
        if episode:
            episode.synopsis = workflow.outline.synopsis
            episode.visual_style = workflow.outline.style
            db.commit()
        
        # Send WebSocket completion
        await ws_manager.send_completion(
            topic=f"episode.{episode_id_str}.refine",
            message="Content refinement completed",
            result={
                "content_length": len(refined_content),
                "character_count": len(workflow.outline.characters_summary),
                "plot_points": len(workflow.outline.plot_summary)
            }
        )
        
        print(f"✅ [Phase 1.3] Content refinement completed")
        print(f"   Content length: {len(refined_content)} characters")
        print(f"   Ready for Phase 2: Character Generation")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ [Phase 1.3] Error refining content: {e}")
        import traceback
        traceback.print_exc()
        workflow.error = str(e)
        workflow.transition_to(WorkflowState.FAILED)
        save_workflow_state(db, workflow)
        db.commit()
        
        # Send WebSocket error
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        await ws_manager.send_error(
            topic=f"episode.{episode_id_str}.refine",
            error_message="Content refinement failed",
            error_details={"error": str(e)}
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/episode/{episode_id}/outline/generate")
async def generate_outline(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    生成剧本大纲
    
    Generate story outline from initial content.
    
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
        
        # Start outline generation in background
        background_tasks.add_task(generate_outline_async, workflow, db)
        
        return {"message": "Outline generation started", "state": workflow.state}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/episode/{episode_id}/outline")
async def update_outline(
    episode_id: str,
    request: UpdateOutlineRequest,
    db: Session = Depends(get_db)
):
    """
    更新剧本大纲
    
    Update outline fields.
    
    Args:
        episode_id: Episode ID
        request: Update request with optional fields
        db: Database session
        
    Returns:
        Updated outline data
    """
    try:
        validate_episode_exists(episode_id, db)
        
        db_outline = db.query(EpisodeOutline).filter(
            EpisodeOutline.episode_id == episode_id
        ).first()
        
        if not db_outline:
            raise HTTPException(status_code=404, detail="Outline not found")
        
        # Update fields
        if request.title is not None:
            db_outline.title = request.title
        if request.genre is not None:
            db_outline.genre = request.genre
        if request.style is not None:
            db_outline.style = request.style
        if request.synopsis is not None:
            db_outline.synopsis = request.synopsis
        if request.characters_summary is not None:
            db_outline.characters_summary = request.characters_summary
        if request.plot_summary is not None:
            db_outline.plot_summary = request.plot_summary
        if request.highlights is not None:
            db_outline.highlights = request.highlights
        
        db_outline.updated_at = datetime.utcnow()
        db.commit()
        
        return db_outline.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/outline/confirm")
async def confirm_outline(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    确认剧本大纲，并自动开始细化剧情
    
    Phase 1.2: Outline Confirmation Mechanism
    
    Args:
        episode_id: Episode ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Success message with next state
    """
    try:
        print(f"\n{'='*60}")
        print(f"[Phase 1.2] OUTLINE CONFIRMATION")
        print(f"Episode ID: {episode_id}")
        print(f"{'='*60}\n")
        
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        # Validate current state
        if workflow.state != WorkflowState.OUTLINE_GENERATED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm outline in state: {workflow.state}. Must be in 'outline_generated' state."
            )
        
        print(f"[Phase 1.2] User confirmed outline: {workflow.outline.title if workflow.outline else 'N/A'}")
        
        # Transition to confirmed state
        workflow.transition_to(WorkflowState.OUTLINE_CONFIRMED)
        save_workflow_state(db, workflow)
        
        # Get episode_id_str for WebSocket
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        
        # Send WebSocket notification
        await ws_manager.send_status(
            topic=f"episode.{episode_id_str}.outline",
            status="confirmed",
            message="Outline confirmed by user"
        )
        
        # Automatically start content refinement in background
        print(f"[Phase 1.2] Starting content refinement in background...")
        background_tasks.add_task(refine_content_async, workflow, db)
        
        return {
            "message": "Outline confirmed, starting content refinement",
            "state": workflow.state,
            "next_state": "refining"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [Phase 1.2] Error confirming outline: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))