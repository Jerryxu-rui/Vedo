"""
Conversational API - Episodes Module
对话式API - 集数管理模块

Handles episode workflow management including:
- Episode creation and initialization
- Workflow state management
- Episode listing and details
- Episode deletion
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from database_models import Episode, EpisodeWorkflowSession, Series, Scene, Shot
from workflows.conversational_episode_workflow import (
    ConversationalEpisodeWorkflow, WorkflowMode, WorkflowState,
    workflow_manager
)
from services.intent_analyzer_llm import LLMIntentAnalyzer, IntentType

# Import from shared module
from api_routes_conv_shared import (
    # Models
    WorkflowStateResponse,
    CreateWorkflowRequest,
    EpisodeListItem,
    EpisodeListResponse,
    EpisodeDetailResponse,
    
    # Helpers
    get_workflow_session,
    get_or_create_workflow,
    save_workflow_state,
    convert_file_path_to_url,
    validate_episode_exists,
    validate_workflow_mode,
    validate_initial_content,
    get_or_create_series,
    
    # Database Queries
    get_episode_outline,
    get_episode_characters,
    get_episode_scenes,
    
    # WebSocket
    ws_manager
)

# Create router
router = APIRouter(
    prefix="/api/v1/conversational",
    tags=["conversational-episodes"]
)


# ============================================================================
# Episode Creation & Workflow Management
# ============================================================================

@router.post("/episode/create", response_model=WorkflowStateResponse)
async def create_conversational_episode(
    request: CreateWorkflowRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建对话式集数生产工作流
    
    Create a new conversational workflow for step-by-step video generation.
    
    Args:
        request: Workflow creation request with series_id, episode_number, mode, content
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        WorkflowStateResponse with initial workflow state
        
    Raises:
        HTTPException: If validation fails or creation error occurs
    """
    # Validate inputs
    validate_workflow_mode(request.mode)
    validate_initial_content(request.initial_content)
    
    # ============================================================================
    # CONTENT VALIDATION: Use LLM to validate video idea quality
    # ============================================================================
    print(f"[Episode Create] Validating content: {request.initial_content[:100]}...")
    
    try:
        analyzer = LLMIntentAnalyzer(db)
        intent = await analyzer.analyze(
            user_input=request.initial_content,
            context={"mode": request.mode}
        )
        
        print(f"[Episode Create] Intent: {intent.type}, Confidence: {intent.confidence}")
        
        # Check if content is valid for video generation
        if intent.content_validation and not intent.content_validation.is_valid:
            print(f"[Episode Create] Content validation FAILED")
            print(f"  - Missing: {intent.content_validation.missing_elements}")
            print(f"  - Suggestions: {intent.content_validation.suggestions}")
            
            # Return error with helpful guidance
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "content_validation_failed",
                    "message": "视频创意需要更多细节 / Video idea needs more details",
                    "validation": {
                        "is_valid": False,
                        "has_subject": intent.content_validation.has_subject,
                        "has_action": intent.content_validation.has_action,
                        "has_context": intent.content_validation.has_context,
                        "missing_elements": intent.content_validation.missing_elements,
                        "suggestions": intent.content_validation.suggestions
                    },
                    "examples": [
                        "创建一个关于太空探索的科幻视频，宇航员发现古代遗迹",
                        "Make a video about a cat's adventure in the city",
                        "生成一个浪漫爱情故事，两个人在巴黎相遇"
                    ]
                }
            )
        
        # If intent is not video_generation, also reject
        if intent.type != IntentType.VIDEO_GENERATION:
            print(f"[Episode Create] Wrong intent type: {intent.type}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_intent",
                    "message": "请提供具体的视频创意 / Please provide a specific video idea",
                    "detected_intent": intent.type,
                    "reasoning": intent.reasoning,
                    "suggestions": [
                        "描述视频的主题和内容",
                        "说明视频中发生什么",
                        "添加场景、角色或风格描述"
                    ]
                }
            )
        
        print(f"[Episode Create] Content validation PASSED ✓")
        
    except HTTPException:
        raise  # Re-raise validation errors
    except Exception as e:
        print(f"[Episode Create] Validation error (non-critical): {e}")
        # Continue with creation if validation fails (fail-open for now)
        # In production, you might want to fail-closed
    
    # ============================================================================
    # EPISODE CREATION: Proceed with validated content
    # ============================================================================
    
    try:
        # Auto-create series if it doesn't exist
        series = get_or_create_series(
            series_id=request.series_id,
            title=request.title or "Default Series",
            style=request.style,
            db=db
        )
        
        # Create Episode record
        episode = Episode(
            series_id=series.id,
            episode_number=request.episode_number,
            title=request.title or f"Episode {request.episode_number}",
            status="draft"
        )
        db.add(episode)
        db.flush()
        
        # Create workflow session
        workflow_session = EpisodeWorkflowSession(
            episode_id=episode.id,
            mode=request.mode,
            state=WorkflowState.INITIAL,
            style=request.style,
            initial_content=request.initial_content,
            context={
                "created_at": datetime.utcnow().isoformat(),
                "mode": request.mode,
                "style": request.style,
                "episode_id_str": episode.id,  # Store the actual UUID string
                "initial_content": request.initial_content,
            }
        )
        db.add(workflow_session)
        db.commit()
        
        # Create workflow instance
        workflow = workflow_manager.create_workflow(
            episode_id=int(episode.id) if episode.id.isdigit() else hash(episode.id),
            mode=WorkflowMode(request.mode),
            initial_content=request.initial_content,
            style=request.style
        )
        
        # CRITICAL: Set the context with episode_id_str so it's available when saving outline
        workflow.context["episode_id_str"] = episode.id
        
        return WorkflowStateResponse(
            episode_id=episode.id,
            workflow_id=workflow_session.id,
            state=workflow.state,
            mode=workflow.mode,
            style=workflow.style,
            step_info=workflow.get_current_step_info(),
            outline=workflow.outline.dict() if workflow.outline else None,
            characters=[c.dict() for c in workflow.characters],
            scenes=[s.dict() for s in workflow.scenes],
            storyboard=[shot.dict() for shot in workflow.storyboard],
            error=workflow.error
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/state", response_model=WorkflowStateResponse)
async def get_workflow_state(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    获取工作流当前状态
    
    Get current workflow state including all generated content.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        WorkflowStateResponse with complete workflow state
        
    Raises:
        HTTPException: If episode or workflow not found
    """
    try:
        # Get workflow session from database
        session = get_workflow_session(db, episode_id)
        
        # Load or create workflow from database
        episode_id_int = int(episode_id) if episode_id.isdigit() else hash(episode_id)
        workflow = workflow_manager.load_or_create_from_db(episode_id_int, episode_id, db)
        
        if not workflow:
            # If database doesn't have session record, create basic workflow
            workflow = ConversationalEpisodeWorkflow.from_dict({
                "episode_id": episode_id_int,
                "mode": session.mode,
                "state": session.state,
                "style": session.style,
                "context": session.context or {},
            })
            workflow_manager.workflows[workflow.episode_id] = workflow
        
        # Get outline from database
        outline_data = None
        print(f"[DEBUG] Checking outline for episode {episode_id}, state: {session.state}")
        
        if session.state not in ["initial", "outline_generating"]:
            db_outline = get_episode_outline(episode_id, db)
            if db_outline:
                outline_data = db_outline.to_dict()
                print(f"[DEBUG] Found outline for episode {episode_id}")
        
        # Get characters from database
        characters_data = []
        db_characters = get_episode_characters(episode_id, db)
        if db_characters:
            characters_data = [c.to_dict() for c in db_characters]
        
        # Get scenes from database
        scenes_data = []
        db_scenes = get_episode_scenes(episode_id, db)
        if db_scenes:
            scenes_data = [s.to_dict() for s in db_scenes]
        
        # Get storyboard shots from database (not from workflow memory!)
        storyboard_data = []
        db_scenes = db.query(Scene).filter(Scene.episode_id == episode_id).all()
        for scene in db_scenes:
            shots = db.query(Shot).filter(Shot.scene_id == scene.id).order_by(Shot.shot_number).all()
            storyboard_data.extend([shot.to_dict() for shot in shots])
        
        # Get video path if completed
        video_path = None
        if workflow.state == 'video_completed' and workflow.context.get('video_path'):
            video_path = convert_file_path_to_url(workflow.context['video_path'])
        
        return WorkflowStateResponse(
            episode_id=episode_id,
            workflow_id=session.id,
            state=workflow.state,
            mode=workflow.mode,
            style=workflow.style,
            step_info=workflow.get_current_step_info(),
            outline=outline_data,
            characters=characters_data,
            scenes=scenes_data,
            storyboard=storyboard_data,  # Use database data, not workflow memory
            video_path=video_path,
            error=workflow.error
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/episode/{episode_id}/workflow")
async def cancel_workflow(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    取消工作流
    
    Cancel an active workflow and remove it from memory.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if workflow:
            workflow.state = WorkflowState.CANCELLED
            save_workflow_state(db, workflow)
            workflow_manager.remove_workflow(workflow.episode_id)
        
        return {"message": "Workflow cancelled"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Episode Library & Management
# ============================================================================

@router.get("/episodes", response_model=EpisodeListResponse)
async def list_episodes(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    获取所有对话式工作流生成的集数列表
    
    List all conversational workflow episodes with pagination and filtering.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        status: Filter by status (draft, generating, completed, failed)
        db: Database session
        
    Returns:
        EpisodeListResponse with paginated episode list
    """
    try:
        # Build query
        query = db.query(Episode).join(
            EpisodeWorkflowSession,
            Episode.id == EpisodeWorkflowSession.episode_id
        )
        
        # Apply status filter
        if status:
            query = query.filter(Episode.status == status)
        
        # Get total count
        total = query.count()
        
        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size
        offset = (page - 1) * page_size
        
        # Get episodes
        episodes = query.order_by(Episode.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Format response
        episode_items = []
        for ep in episodes:
            # Get workflow session for mode and style
            session = db.query(EpisodeWorkflowSession).filter(
                EpisodeWorkflowSession.episode_id == ep.id
            ).first()
            
            # Get counts
            char_count = len(get_episode_characters(ep.id, db))
            scene_count = len(get_episode_scenes(ep.id, db))
            
            # Get thumbnail (first character image or first scene image)
            thumbnail_url = None
            db_characters = get_episode_characters(ep.id, db)
            if db_characters and db_characters[0].image_url:
                thumbnail_url = db_characters[0].image_url
            else:
                db_scenes = get_episode_scenes(ep.id, db)
                if db_scenes and db_scenes[0].image_url:
                    thumbnail_url = db_scenes[0].image_url
            
            # Get video path from episode.script field (temporary storage)
            video_path = None
            if ep.script and (ep.script.endswith('.mp4') or ep.script.endswith('.webm')):
                video_path = convert_file_path_to_url(ep.script)
            
            episode_items.append(EpisodeListItem(
                id=ep.id,
                series_id=ep.series_id,
                episode_number=ep.episode_number,
                title=ep.title,
                synopsis=ep.synopsis,
                status=ep.status,
                mode=session.mode if session else None,
                style=session.style if session else None,
                thumbnail_url=thumbnail_url,
                video_path=video_path,
                duration=ep.duration,
                created_at=ep.created_at.isoformat() if ep.created_at else "",
                updated_at=ep.updated_at.isoformat() if ep.updated_at else "",
                character_count=char_count,
                scene_count=scene_count
            ))
        
        return EpisodeListResponse(
            episodes=episode_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episodes/{episode_id}", response_model=EpisodeDetailResponse)
async def get_episode_detail(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    获取集数的完整详细信息
    
    Get complete episode details including all generated content.
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        EpisodeDetailResponse with complete episode information
        
    Raises:
        HTTPException: If episode not found
    """
    try:
        # Get episode
        episode = validate_episode_exists(episode_id, db)
        
        # Get workflow session
        session = db.query(EpisodeWorkflowSession).filter(
            EpisodeWorkflowSession.episode_id == episode_id
        ).first()
        
        # Get outline
        outline = get_episode_outline(episode_id, db)
        
        # Get characters
        characters = get_episode_characters(episode_id, db)
        
        # Get scenes
        scenes = get_episode_scenes(episode_id, db)
        
        # Get storyboard shots
        storyboard = []
        db_scenes = db.query(Scene).filter(Scene.episode_id == episode_id).all()
        for scene in db_scenes:
            shots = db.query(Shot).filter(Shot.scene_id == scene.id).all()
            storyboard.extend([shot.to_dict() for shot in shots])
        
        # Get video info
        video_info = None
        if episode.script and (episode.script.endswith('.mp4') or episode.script.endswith('.webm')):
            video_info = {
                "video_path": convert_file_path_to_url(episode.script),
                "duration": episode.duration,
                "status": episode.status
            }
        
        return EpisodeDetailResponse(
            episode=episode.to_dict(),
            workflow_session=session.to_dict() if session else None,
            outline=outline.to_dict() if outline else None,
            characters=[c.to_dict() for c in characters],
            scenes=[s.to_dict() for s in scenes],
            storyboard=storyboard,
            video_info=video_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/episodes/{episode_id}")
async def delete_episode(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    删除集数及其所有相关数据
    
    Delete episode and all related data (cascade delete).
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Success message with deleted episode ID
        
    Raises:
        HTTPException: If episode not found
    """
    try:
        # Get episode
        episode = validate_episode_exists(episode_id, db)
        
        # Delete episode (cascade will handle related records)
        db.delete(episode)
        db.commit()
        
        # Remove from workflow manager if exists
        try:
            workflow_manager.remove_workflow(
                int(episode_id) if episode_id.isdigit() else hash(episode_id)
            )
        except:
            pass  # Workflow may not be in memory
        
        return {
            "message": "Episode deleted successfully",
            "episode_id": episode_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))