"""
Conversational API - Characters Module
对话式API - 角色管理模块

Handles character design and management including:
- Character extraction and generation
- Character portrait generation
- Character image management
- Character updates and regeneration
- Character deletion
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import os

from database import get_db
from database_models import CharacterDesign, EpisodeWorkflowSession
from workflows.conversational_episode_workflow import WorkflowState, WorkflowMode
from workflows.pipeline_adapter import create_adapter
from utils.async_wrapper import ProgressCallback
from interfaces import CharacterInScene

# Import from shared module
from api_routes_conv_shared import (
    # Models
    UpdateCharacterRequest,
    
    # Helpers
    get_or_create_workflow,
    save_workflow_state,
    convert_file_path_to_url,
    validate_episode_exists,
    get_character_by_id,
    
    # WebSocket
    ws_manager
)

# Create router
router = APIRouter(
    prefix="/api/v1/conversational",
    tags=["conversational-characters"]
)


# ============================================================================
# Async Generation Functions
# ============================================================================

async def generate_characters_async(workflow, db: Session):
    """异步生成角色"""
    try:
        print(f"\n{'='*60}")
        print(f"[Character Generation] STARTING for episode {workflow.episode_id}")
        print(f"{'='*60}")
        
        workflow.transition_to(WorkflowState.CHARACTERS_GENERATING)
        save_workflow_state(db, workflow)
        
        # Get episode_id_str for WebSocket topic
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        print(f"[Character Generation] Episode ID: {episode_id_str}")
        
        # Send WebSocket status update
        await ws_manager.send_status(
            topic=f"episode.{episode_id_str}.characters",
            status="generating",
            message="Starting character generation"
        )
        
        # Create pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        print(f"[Character Generation] Config path: {config_path}")
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        print(f"[Character Generation] Pipeline initialized")
        
        # Build full content from outline including characters_summary
        content = workflow.context.get("initial_content", "")
        if workflow.outline:
            parts = []
            if workflow.outline.title:
                parts.append(f"标题: {workflow.outline.title}")
            if workflow.outline.synopsis:
                parts.append(f"剧情概要: {workflow.outline.synopsis}")
            
            # Include character summaries from outline
            if workflow.outline.characters_summary:
                parts.append("\n角色列表:")
                for char_info in workflow.outline.characters_summary:
                    if isinstance(char_info, dict):
                        name = char_info.get("name", "")
                        role = char_info.get("role", "")
                        desc = char_info.get("description", "")
                        parts.append(f"- {name} ({role}): {desc}")
            
            # Include plot summary
            if workflow.outline.plot_summary:
                parts.append("\n剧情结构:")
                for plot_point in workflow.outline.plot_summary:
                    if isinstance(plot_point, dict):
                        act = plot_point.get("act", "")
                        desc = plot_point.get("description", "")
                        parts.append(f"- {act}: {desc}")
            
            content = "\n".join(parts)
        print(f"[Character Generation] Content length: {len(content)} chars")
        
        # Create progress callback
        progress = ProgressCallback()
        
        async def on_progress(percentage: float, message: str):
            print(f"[Character Generation] {percentage*100:.1f}%: {message}")
            await ws_manager.send_progress(
                topic=f"episode.{episode_id_str}.characters",
                percentage=percentage,
                message=message
            )
        
        progress.subscribe(on_progress)
        
        # Call AI generation logic
        print(f"[Character Generation] Calling extract_and_generate_characters...")
        characters = await adapter.extract_and_generate_characters(
            content=content,
            style=workflow.style,
            progress=progress
        )
        print(f"[Character Generation] Extracted {len(characters)} characters")
        
        # If no characters were extracted, create a default protagonist
        if len(characters) == 0:
            print(f"[Character Generation] No characters extracted, creating default protagonist...")
            from workflows.conversational_episode_workflow import CharacterInfo
            
            default_name = "主角"
            default_role = "protagonist"
            default_desc = "故事的主要人物"
            
            # Try to extract character info from outline
            if workflow.outline and workflow.outline.characters_summary:
                for char_info in workflow.outline.characters_summary:
                    if isinstance(char_info, dict):
                        default_name = char_info.get("name", default_name)
                        default_role = char_info.get("role", default_role)
                        default_desc = char_info.get("description", default_desc)
                        break
            
            default_character = CharacterInfo(
                name=default_name,
                role=default_role,
                description=default_desc,
                appearance="未指定外貌",
                personality="待定性格",
                image_url=None
            )
            characters = [default_character]
            print(f"[Character Generation] Created default character: {default_name}")
        
        workflow.characters = characters
        workflow.transition_to(WorkflowState.CHARACTERS_GENERATED)
        
        # Check if we should clear existing or merge
        existing_count = db.query(CharacterDesign).filter(CharacterDesign.episode_id == episode_id_str).count()
        if existing_count > 0:
            # Re-generation - delete old characters (full regenerate mode)
            db.query(CharacterDesign).filter(CharacterDesign.episode_id == episode_id_str).delete()
            db.flush()
        
        # Save to database and collect image URLs
        character_images = []
        print(f"[Character Generation] Saving to database...")
        for i, char in enumerate(characters):
            print(f"[Character {i+1}] Name: {char.name}")
            print(f"[Character {i+1}] Role: {char.role}")
            print(f"[Character {i+1}] Image URL (raw): {char.image_url}")
            
            # Convert URL
            converted_url = convert_file_path_to_url(char.image_url)
            print(f"[Character {i+1}] Image URL (converted): {converted_url}")
            
            db_char = CharacterDesign(
                episode_id=episode_id_str,
                name=char.name,
                role=char.role,
                description=char.description,
                appearance=char.appearance,
                personality=char.personality,
                image_url=converted_url,
                status="completed"
            )
            db.add(db_char)
            db.flush()
            print(f"[Character {i+1}] Saved to DB with ID: {db_char.id}")
            
            character_images.append({
                "id": db_char.id,
                "name": char.name,
                "image_url": db_char.image_url,
                "role": char.role
            })
        
        db.commit()
        print(f"[Character Generation] Database commit successful")
        save_workflow_state(db, workflow)
        
        # Send WebSocket completion with image data
        print(f"[Character Generation] Sending WebSocket completion...")
        await ws_manager.send_completion(
            topic=f"episode.{episode_id_str}.characters",
            message=f"Generated {len(characters)} characters",
            result={
                "count": len(characters),
                "characters": character_images
            }
        )
        
        print(f"✅ Generated {len(characters)} characters for episode {workflow.episode_id}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error generating characters: {e}")
        import traceback
        traceback.print_exc()
        workflow.error = str(e)
        workflow.transition_to(WorkflowState.FAILED)
        save_workflow_state(db, workflow)
        db.commit()
        
        # Send WebSocket error
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        await ws_manager.send_error(
            topic=f"episode.{episode_id_str}.characters",
            error_message="Character generation failed",
            error_details={"error": str(e)}
        )


async def regenerate_character_image_async(character_id: str, episode_id: str, db: Session):
    """异步重新生成角色图片"""
    char_design = None
    try:
        # Get character design
        char_design = get_character_by_id(character_id, episode_id, db)
        
        # Send WebSocket start notification
        await ws_manager.send_status(
            topic=f"episode.{episode_id}.character.{character_id}",
            status="regenerating",
            message=f"Regenerating {char_design.name}"
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
        
        # Generate new image using pipeline's character generation
        print(f"[Regenerate] Generating new image for {char_design.name}")
        
        # Convert to CharacterInScene format for pipeline
        char_in_scene = CharacterInScene(
            idx=0,
            identifier_in_scene=char_design.name,
            static_features=char_design.description,
            dynamic_features=char_design.appearance,
            is_visible=True
        )
        
        # Generate portrait using pipeline
        character_portraits_registry = await adapter.pipeline.generate_character_portraits(
            characters=[char_in_scene],
            character_portraits_registry=None,
            style=session.style
        )
        
        # Get the generated image path
        portrait_info = character_portraits_registry.get(char_design.name, {})
        front_portrait = portrait_info.get("front", {})
        image_path = front_portrait.get("path", "")
        
        if not image_path:
            raise Exception("Failed to generate character image")
        
        # Update database
        char_design.image_url = convert_file_path_to_url(image_path)
        char_design.status = "completed"
        char_design.updated_at = datetime.utcnow()
        db.commit()
        
        # Send WebSocket completion
        await ws_manager.send_completion(
            topic=f"episode.{episode_id}.character.{character_id}",
            message=f"Regenerated {char_design.name}",
            result={
                "character_id": character_id,
                "name": char_design.name,
                "image_url": char_design.image_url
            }
        )
        
        # Also send to general characters topic
        await ws_manager.send_status(
            topic=f"episode.{episode_id}.characters",
            status="updated",
            message=f"Character {char_design.name} regenerated",
            details={"character_id": character_id}
        )
        
        print(f"✅ Regenerated character {char_design.name}")
        
    except Exception as e:
        print(f"❌ Error regenerating character: {e}")
        import traceback
        traceback.print_exc()
        
        # Update status to failed
        if char_design:
            char_design.status = "failed"
            db.commit()
        
        # Send WebSocket error
        await ws_manager.send_error(
            topic=f"episode.{episode_id}.character.{character_id}",
            error_message="Character regeneration failed",
            error_details={"error": str(e)}
        )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/episode/{episode_id}/characters/generate")
async def generate_characters(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    生成角色设计
    
    Generate character designs with portraits.
    
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
        
        # Start character generation in background
        background_tasks.add_task(generate_characters_async, workflow, db)
        
        return {"message": "Character generation started", "state": workflow.state}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/characters/confirm")
async def confirm_characters(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    确认角色设计
    
    Confirm character designs and proceed to next step.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Success message with workflow state
    """
    try:
        validate_episode_exists(episode_id, db)
        workflow = get_or_create_workflow(episode_id, db)
        
        workflow.transition_to(WorkflowState.CHARACTERS_CONFIRMED)
        save_workflow_state(db, workflow)
        
        return {"message": "Characters confirmed", "state": workflow.state}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/characters/images")
async def get_character_images(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    获取角色生成的图片列表
    
    Returns list of character images with metadata for display in workflow.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Character images list with metadata
    """
    try:
        validate_episode_exists(episode_id, db)
        
        # Query character designs for this episode
        db_characters = db.query(CharacterDesign).filter(
            CharacterDesign.episode_id == episode_id,
            CharacterDesign.status == "completed"
        ).all()
        
        if not db_characters:
            return {
                "episode_id": episode_id,
                "characters": [],
                "count": 0,
                "message": "No character images found"
            }
        
        # Format character data for frontend display
        characters = []
        for char in db_characters:
            characters.append({
                "id": char.id,
                "name": char.name,
                "role": char.role,
                "description": char.description,
                "appearance": char.appearance,
                "personality": char.personality or [],
                "image_url": char.image_url,
                "status": char.status,
                "created_at": char.created_at.isoformat() if char.created_at else None
            })
        
        return {
            "episode_id": episode_id,
            "characters": characters,
            "count": len(characters),
            "message": f"Found {len(characters)} character(s)"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/characters/{character_id}/regenerate")
async def regenerate_character_image(
    episode_id: str,
    character_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    重新生成指定角色的图片
    
    Allows user to regenerate a specific character image if unsatisfied.
    
    Args:
        episode_id: Episode ID
        character_id: Character ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Success message with regeneration status
    """
    try:
        validate_episode_exists(episode_id, db)
        char_design = get_character_by_id(character_id, episode_id, db)
        
        # Mark as regenerating
        char_design.status = "generating"
        db.commit()
        
        # Add background task to regenerate character image
        background_tasks.add_task(regenerate_character_image_async, character_id, episode_id, db)
        
        return {
            "message": "Character image regeneration started",
            "character_id": character_id,
            "character_name": char_design.name,
            "status": "generating"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/episode/{episode_id}/characters/{character_id}")
async def update_character(
    episode_id: str,
    character_id: str,
    request: UpdateCharacterRequest,
    db: Session = Depends(get_db)
):
    """
    编辑单个角色的属性（不重新生成图片）
    
    Update a single character's properties without regenerating the image.
    
    Args:
        episode_id: Episode ID
        character_id: Character ID
        request: Update request with optional fields
        db: Database session
        
    Returns:
        Updated character data
    """
    try:
        validate_episode_exists(episode_id, db)
        character = get_character_by_id(character_id, episode_id, db)
        
        # Update only provided fields
        if request.name is not None:
            character.name = request.name
        if request.description is not None:
            character.description = request.description
        if request.appearance is not None:
            character.appearance = request.appearance
        if request.personality is not None:
            character.personality = request.personality
        if request.role is not None:
            character.role = request.role
        
        character.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Character updated", "character": character.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/episode/{episode_id}/characters/{character_id}")
async def delete_character(
    episode_id: str,
    character_id: str,
    db: Session = Depends(get_db)
):
    """
    删除单个角色
    
    Delete a single character.
    
    Args:
        episode_id: Episode ID
        character_id: Character ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        validate_episode_exists(episode_id, db)
        character = get_character_by_id(character_id, episode_id, db)
        
        db.delete(character)
        db.commit()
        
        return {"message": "Character deleted", "character_id": character_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters")
async def list_all_characters(
    episode_id: str = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取所有角色列表（可选按集数过滤）
    
    List all characters across episodes with optional filtering.
    
    Args:
        episode_id: Optional episode ID to filter by
        page: Page number
        page_size: Items per page
        db: Database session
        
    Returns:
        Paginated character list
    """
    try:
        query = db.query(CharacterDesign)
        
        if episode_id:
            query = query.filter(CharacterDesign.episode_id == episode_id)
        
        total = query.count()
        total_pages = (total + page_size - 1) // page_size
        offset = (page - 1) * page_size
        
        characters = query.order_by(CharacterDesign.created_at.desc()).offset(offset).limit(page_size).all()
        
        return {
            "characters": [c.to_dict() for c in characters],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))