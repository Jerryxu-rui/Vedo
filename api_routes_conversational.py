"""
Conversational Workflow API Routes
对话式工作流API路由 - 支持分步骤生成视频
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import os

from database import get_db
from database_models import (
    Episode, EpisodeWorkflowSession, EpisodeOutline,
    CharacterDesign, SceneDesign, Character, Scene, Shot, Series
)
from workflows.conversational_episode_workflow import (
    ConversationalEpisodeWorkflow, WorkflowManager, WorkflowMode, WorkflowState,
    WorkflowAction, OutlineData, CharacterData, SceneData, ShotData,
    workflow_manager
)
from workflows.pipeline_adapter import create_adapter
from utils.async_wrapper import ProgressCallback
from utils.websocket_manager import WebSocketManager, ProgressWebSocketCallback

router = APIRouter(prefix="/api/v1/conversational", tags=["conversational-workflow"])

# WebSocket manager for real-time updates
ws_manager = WebSocketManager()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateWorkflowRequest(BaseModel):
    """创建工作流请求"""
    series_id: str
    episode_number: int
    mode: str = Field(..., description="'idea' or 'script'")
    initial_content: str = Field(..., description="User's idea or script")
    style: str = Field(default="写实电影感", description="Visual style")
    title: Optional[str] = None


class WorkflowActionRequest(BaseModel):
    """工作流操作请求"""
    action: str = Field(..., description="confirm, edit, regenerate, cancel, next")
    data: Optional[Dict[str, Any]] = None


class UpdateOutlineRequest(BaseModel):
    """更新大纲请求"""
    title: Optional[str] = None
    genre: Optional[str] = None
    style: Optional[str] = None
    synopsis: Optional[str] = None
    characters_summary: Optional[List[Dict[str, str]]] = None
    plot_summary: Optional[List[Dict[str, str]]] = None
    highlights: Optional[List[str]] = None


class UpdateCharacterRequest(BaseModel):
    """更新角色请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[List[str]] = None


class UpdateSceneRequest(BaseModel):
    """更新场景请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    atmosphere: Optional[str] = None


class WorkflowStateResponse(BaseModel):
    """工作流状态响应"""
    episode_id: str
    workflow_id: str
    state: str
    mode: str
    style: str
    step_info: Dict[str, Any]
    outline: Optional[Dict[str, Any]] = None
    characters: List[Dict[str, Any]] = []
    scenes: List[Dict[str, Any]] = []
    storyboard: List[Dict[str, Any]] = []
    error: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def get_workflow_session(db: Session, episode_id: str) -> EpisodeWorkflowSession:
    """获取工作流会话"""
    session = db.query(EpisodeWorkflowSession).filter(
        EpisodeWorkflowSession.episode_id == episode_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Workflow session not found")
    
    return session


def convert_file_path_to_url(file_path: str) -> str:
    """Convert local file path to web-accessible URL"""
    if not file_path:
        print(f"[URL Conversion] WARNING: Empty file_path provided")
        return None
    
    print(f"[URL Conversion] Input: {file_path}")
    
    # Remove leading ./ or .working_dir/
    if file_path.startswith('./'):
        file_path = file_path[2:]
    if file_path.startswith('.working_dir/'):
        file_path = file_path.replace('.working_dir/', '')
    
    # Add /media/ prefix if not already present
    if not file_path.startswith('/media/'):
        file_path = '/media/' + file_path
    
    print(f"[URL Conversion] Output: {file_path}")
    return file_path


def save_workflow_state(db: Session, workflow: ConversationalEpisodeWorkflow):
    """保存工作流状态到数据库"""
    # CRITICAL: Use episode_id_str from context (UUID) instead of workflow.episode_id (hash)
    episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
    
    session = db.query(EpisodeWorkflowSession).filter(
        EpisodeWorkflowSession.episode_id == episode_id_str
    ).first()
    
    if session:
        session.state = workflow.state
        session.context = workflow.context
        session.error_message = workflow.error
        session.updated_at = datetime.utcnow()
        db.commit()
        print(f"[DEBUG] Saved workflow state: episode={episode_id_str}, state={workflow.state}")
    else:
        print(f"[DEBUG] WARNING: Could not find session for episode={episode_id_str}")


async def generate_outline_async(
    workflow: ConversationalEpisodeWorkflow,
    db: Session
):
    """
    异步生成大纲
    
    Phase 1.1: Generate structured video outline from user input
    - Accepts user idea or script
    - Uses LLM to generate structured outline
    - Includes title, genre, synopsis, character summaries, plot points
    - Saves to database for user review
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
        
        # 创建pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        if not os.path.exists(config_path):
            raise Exception(f"Config file not found: {config_path}")
        
        print(f"[Phase 1.1] Initializing {workflow.mode} pipeline...")
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        
        # 创建进度回调
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
        
        # 调用实际的AI生成逻辑
        print(f"[Phase 1.1] Calling LLM to generate outline...")
        await progress.update(0.1, "Analyzing your input...")
        
        outline = await adapter.generate_outline(
            initial_content,
            workflow.style
        )
        
        await progress.update(0.9, "Finalizing outline structure...")
        
        workflow.outline = outline
        workflow.transition_to(WorkflowState.OUTLINE_GENERATED)
        
        # 保存到数据库
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


async def generate_characters_async(
    workflow: ConversationalEpisodeWorkflow,
    db: Session
):
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
        
        # 创建pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        print(f"[Character Generation] Config path: {config_path}")
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        print(f"[Character Generation] Pipeline initialized")
        
        # 获取内容（从大纲或原始内容）
        # Build full content from outline including characters_summary
        content = workflow.context.get("initial_content", "")
        if workflow.outline:
            # Build comprehensive content from outline
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
        
        # 创建进度回调
        progress = ProgressCallback()
        
        async def on_progress(percentage: float, message: str):
            print(f"[Character Generation] {percentage*100:.1f}%: {message}")
            # Send WebSocket progress update
            await ws_manager.send_progress(
                topic=f"episode.{episode_id_str}.characters",
                percentage=percentage,
                message=message
            )
        
        progress.subscribe(on_progress)
        
        # 调用实际的AI生成逻辑
        print(f"[Character Generation] Calling extract_and_generate_characters...")
        characters = await adapter.extract_and_generate_characters(
            content=content,
            style=workflow.style,
            progress=progress
        )
        print(f"[Character Generation] Extracted {len(characters)} characters")
        
        workflow.characters = characters
        workflow.transition_to(WorkflowState.CHARACTERS_GENERATED)
        
        # 保存到数据库并收集图片URLs
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
            db.flush()  # Get the ID
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


async def generate_scenes_async(
    workflow: ConversationalEpisodeWorkflow,
    db: Session
):
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
        
        # 创建pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        
        # 创建进度回调
        progress = ProgressCallback()
        
        async def on_progress(percentage: float, message: str):
            print(f"[Scene Generation] {percentage*100:.1f}%: {message}")
            # Send WebSocket progress update
            await ws_manager.send_progress(
                topic=f"episode.{episode_id_str}.scenes",
                percentage=percentage,
                message=message
            )
        
        progress.subscribe(on_progress)
        
        # 调用实际的AI生成逻辑
        scenes = await adapter.generate_scenes(
            outline=workflow.outline,
            characters=workflow.characters,
            style=workflow.style,
            progress=progress
        )
        
        workflow.scenes = scenes
        workflow.transition_to(WorkflowState.SCENES_GENERATED)
        
        # 保存到数据库并收集图片URLs
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
            db.flush()  # Get the ID
            
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


async def generate_storyboard_async(
    workflow: ConversationalEpisodeWorkflow,
    db: Session
):
    """异步生成分镜"""
    try:
        workflow.transition_to(WorkflowState.STORYBOARD_GENERATING)
        save_workflow_state(db, workflow)
        
        # 创建pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        
        # 获取script内容
        script = workflow.context.get("initial_content", "")
        
        # 创建进度回调
        progress = ProgressCallback()
        
        async def on_progress(percentage: float, message: str):
            print(f"[Storyboard Generation] {percentage*100:.1f}%: {message}")
        
        progress.subscribe(on_progress)
        
        # 调用实际的AI生成逻辑
        storyboard = await adapter.generate_storyboard(
            outline=workflow.outline,
            characters=workflow.characters,
            scenes=workflow.scenes,
            style=workflow.style,
            script=script,
            progress=progress
        )
        
        workflow.storyboard = storyboard
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

@router.post("/episode/create", response_model=WorkflowStateResponse)
async def create_conversational_episode(
    request: CreateWorkflowRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建对话式集数生产工作流
    
    开始一个新的对话式工作流，用于分步骤生成视频
    """
    # Validate mode
    if request.mode not in ["idea", "script"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {request.mode}. Must be 'idea' or 'script'"
        )
    
    # Validate initial_content
    if not request.initial_content or not request.initial_content.strip():
        raise HTTPException(
            status_code=400,
            detail="initial_content cannot be empty"
        )
    
    try:
        # Auto-create series if it doesn't exist
        series = db.query(Series).filter(Series.id == request.series_id).first()
        if not series:
            series = Series(
                id=request.series_id,
                title=request.title or "Default Series",
                description="Auto-generated series",
                genre="general",
                style_preset=request.style or "cinematic",
                status="in_progress"
            )
            db.add(series)
            db.flush()
        
        # 创建Episode记录
        episode = Episode(
            series_id=series.id,
            episode_number=request.episode_number,
            title=request.title or f"Episode {request.episode_number}",
            status="draft"
        )
        db.add(episode)
        db.flush()
        
        # 创建工作流会话
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
        
        # 创建工作流实例
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
    """获取工作流当前状态"""
    try:
        # 从数据库获取会话
        session = get_workflow_session(db, episode_id)
        
        # 从内存获取工作流实例
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            # 如果内存中没有，从数据库恢复
            workflow = ConversationalEpisodeWorkflow.from_dict({
                "episode_id": int(episode_id) if episode_id.isdigit() else hash(episode_id),
                "mode": session.mode,
                "state": session.state,
                "style": session.style,
                "context": session.context or {},
            })
            workflow_manager.workflows[workflow.episode_id] = workflow
        
        # 获取大纲
        outline_data = None
        print(f"[DEBUG] Checking outline for episode {episode_id}, state: {session.state}")
        print(f"[DEBUG] State check: session.state={session.state}, not in ['initial', 'outline_generating']? {session.state not in ['initial', 'outline_generating']}")
        
        if session.state not in ["initial", "outline_generating"]:
            print(f"[DEBUG] Querying outline from database...")
            db_outline = db.query(EpisodeOutline).filter(
                EpisodeOutline.episode_id == episode_id
            ).first()
            print(f"[DEBUG] Query result: {db_outline}")
            if db_outline:
                outline_data = db_outline.to_dict()
                print(f"[DEBUG] Found outline for episode {episode_id}: {outline_data}")
            else:
                print(f"[DEBUG] No outline found in database for episode {episode_id}")
        else:
            print(f"[DEBUG] Skipping outline query because state is {session.state}")
        
        # 获取角色
        characters_data = []
        if session.state not in [
            "initial", "outline_generating",
            "outline_generated", "outline_confirmed",
            "refining", "refined",
            "characters_generating"
        ]:
            db_characters = db.query(CharacterDesign).filter(
                CharacterDesign.episode_id == episode_id
            ).all()
            characters_data = [c.to_dict() for c in db_characters]
        
        # 获取场景
        scenes_data = []
        if session.state not in [
            "initial", "outline_generating",
            "outline_generated", "outline_confirmed",
            "refining", "refined",
            "characters_generating", "characters_generated",
            "characters_confirmed", "scenes_generating"
        ]:
            db_scenes = db.query(SceneDesign).filter(
                SceneDesign.episode_id == episode_id
            ).all()
            scenes_data = [s.to_dict() for s in db_scenes]
        
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
            storyboard=[shot.dict() for shot in workflow.storyboard],
            video_path=video_path,
            error=workflow.error
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/outline/generate")
async def generate_outline(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """生成剧本大纲"""
    try:
        session = get_workflow_session(db, episode_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found in memory")
        
        # 在后台任务中生成大纲
        background_tasks.add_task(generate_outline_async, workflow, db)
        
        return {"message": "Outline generation started", "state": workflow.state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/episode/{episode_id}/outline")
async def update_outline(
    episode_id: str,
    request: UpdateOutlineRequest,
    db: Session = Depends(get_db)
):
    """更新剧本大纲"""
    try:
        db_outline = db.query(EpisodeOutline).filter(
            EpisodeOutline.episode_id == episode_id
        ).first()
        
        if not db_outline:
            raise HTTPException(status_code=404, detail="Outline not found")
        
        # 更新字段
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
    - User reviews and approves the generated outline
    - Can optionally modify outline before confirmation
    - Triggers automatic content refinement upon confirmation
    """
    try:
        print(f"\n{'='*60}")
        print(f"[Phase 1.2] OUTLINE CONFIRMATION")
        print(f"Episode ID: {episode_id}")
        print(f"{'='*60}\n")
        
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
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


async def refine_content_async(
    workflow: ConversationalEpisodeWorkflow,
    db: Session
):
    """
    异步细化内容
    
    Phase 1.3: Content Refinement
    - Takes confirmed outline and expands it
    - Adds detailed scene descriptions
    - Includes dialogue, narration, and visual directions
    - Prepares content for Phase 2 (character generation)
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


@router.post("/episode/{episode_id}/characters/generate")
async def generate_characters(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """生成角色设计"""
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # 在后台任务中生成角色
        background_tasks.add_task(generate_characters_async, workflow, db)
        
        return {"message": "Character generation started", "state": workflow.state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/characters/confirm")
async def confirm_characters(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """确认角色设计"""
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow.transition_to(WorkflowState.CHARACTERS_CONFIRMED)
        save_workflow_state(db, workflow)
        
        return {"message": "Characters confirmed", "state": workflow.state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/scenes/generate")
async def generate_scenes(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """生成场景设计"""
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # 在后台任务中生成场景
        background_tasks.add_task(generate_scenes_async, workflow, db)
        
        return {"message": "Scene generation started", "state": workflow.state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/scenes/confirm")
async def confirm_scenes(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """确认场景设计"""
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow.transition_to(WorkflowState.SCENES_CONFIRMED)
        save_workflow_state(db, workflow)
        
        return {"message": "Scenes confirmed", "state": workflow.state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/storyboard/generate")
async def generate_storyboard(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """生成分镜剧本"""
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # 在后台任务中生成分镜
        background_tasks.add_task(generate_storyboard_async, workflow, db)
        
        return {"message": "Storyboard generation started", "state": workflow.state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode/{episode_id}/storyboard/confirm")
async def confirm_storyboard(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """确认分镜剧本"""
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow.transition_to(WorkflowState.STORYBOARD_CONFIRMED)
        save_workflow_state(db, workflow)
        
        return {"message": "Storyboard confirmed", "state": workflow.state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_video_async(
    workflow: ConversationalEpisodeWorkflow,
    db: Session
):
    """异步生成视频"""
    try:
        workflow.transition_to(WorkflowState.VIDEO_GENERATING)
        save_workflow_state(db, workflow)
        
        # 创建pipeline adapter
        config_path = f"configs/{workflow.mode.value}2video.yaml"
        adapter = create_adapter(workflow.mode, config_path)
        await adapter.initialize_pipeline()
        
        # 获取episode_id_str
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        
        # 创建WebSocket进度回调
        ws_callback = ProgressWebSocketCallback(
            topic=f"episode.{episode_id_str}.video",
            manager=ws_manager
        )
        
        # 发送开始消息
        await ws_manager.send_status(
            topic=f"episode.{episode_id_str}.video",
            status="started",
            message="Video generation started"
        )
        
        # 调用实际的视频生成逻辑
        result = await adapter.generate_video(
            storyboard=workflow.storyboard,
            characters=workflow.characters,
            scenes=workflow.scenes,
            style=workflow.style,
            episode_id=episode_id_str,
            progress=ws_callback
        )
        
        if result.get("success"):
            workflow.transition_to(WorkflowState.VIDEO_COMPLETED)
            workflow.context["video_path"] = result.get("video_path")
            workflow.context["video_metadata"] = {
                "total_shots": result.get("total_shots"),
                "successful_shots": result.get("successful_shots"),
                "failed_shots": result.get("failed_shots")
            }
            
            # 更新Episode记录
            episode = db.query(Episode).filter(Episode.id == episode_id_str).first()
            if episode:
                episode.status = "completed"
                # Store relative path for video
                video_path = result.get("video_path", "")
                if video_path.startswith('./'):
                    video_path = video_path[2:]
                episode.script = video_path  # Temporarily store in script field
                db.commit()
            
            # 发送完成消息
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
            
            # 发送错误消息
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
        
        # 发送错误消息
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        await ws_manager.send_error(
            topic=f"episode.{episode_id_str}.video",
            error_message="Video generation failed with exception",
            error_details={"error": str(e), "traceback": traceback.format_exc()}
        )


@router.post("/episode/{episode_id}/video/generate")
async def start_video_generation(
    episode_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """开始视频生成"""
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # 在后台任务中生成视频
        background_tasks.add_task(generate_video_async, workflow, db)
        
        return {"message": "Video generation started", "state": workflow.state}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/progress")
async def get_generation_progress(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """获取生成进度"""
    try:
        workflow = workflow_manager.get_workflow(
            int(episode_id) if episode_id.isdigit() else hash(episode_id)
        )
        
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "episode_id": episode_id,
            "state": workflow.state,
            "progress_percentage": workflow._calculate_progress(),
            "step_info": workflow.get_current_step_info(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/episode/{episode_id}/workflow")
async def cancel_workflow(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """取消工作流"""
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
# Image Retrieval Endpoints (Phase 7 - Enhancement)
# ============================================================================

@router.get("/episode/{episode_id}/characters/images")
async def get_character_images(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    获取角色生成的图片列表
    
    Returns list of character images with metadata for display in workflow
    """
    try:
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
                "image_url": char.image_url,  # Already converted to web URL
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


@router.get("/episode/{episode_id}/scenes/images")
async def get_scene_images(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    获取场景生成的图片列表
    
    Returns list of scene images with metadata for display in workflow
    """
    try:
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
                "image_url": scene.image_url,  # Already converted to web URL
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


async def regenerate_character_image_async(
    character_id: str,
    episode_id: str,
    db: Session
):
    """异步重新生成角色图片"""
    char_design = None
    try:
        # Get character design
        char_design = db.query(CharacterDesign).filter(
            CharacterDesign.id == character_id,
            CharacterDesign.episode_id == episode_id
        ).first()
        
        if not char_design:
            print(f"❌ Character {character_id} not found")
            return
        
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
        from interfaces import CharacterInScene
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


async def regenerate_scene_image_async(
    scene_id: str,
    episode_id: str,
    db: Session
):
    """异步重新生成场景图片"""
    scene_design = None
    try:
        # Get scene design
        scene_design = db.query(SceneDesign).filter(
            SceneDesign.id == scene_id,
            SceneDesign.episode_id == episode_id
        ).first()
        
        if not scene_design:
            print(f"❌ Scene {scene_id} not found")
            return
        
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


@router.post("/episode/{episode_id}/characters/{character_id}/regenerate")
async def regenerate_character_image(
    episode_id: str,
    character_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    重新生成指定角色的图片
    
    Allows user to regenerate a specific character image if unsatisfied
    """
    try:
        # Get character design
        char_design = db.query(CharacterDesign).filter(
            CharacterDesign.id == character_id,
            CharacterDesign.episode_id == episode_id
        ).first()
        
        if not char_design:
            raise HTTPException(status_code=404, detail="Character not found")
        
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


@router.post("/episode/{episode_id}/scenes/{scene_id}/regenerate")
async def regenerate_scene_image(
    episode_id: str,
    scene_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    重新生成指定场景的图片
    
    Allows user to regenerate a specific scene image if unsatisfied
    """
    try:
        # Get scene design
        scene_design = db.query(SceneDesign).filter(
            SceneDesign.id == scene_id,
            SceneDesign.episode_id == episode_id
        ).first()
        
        if not scene_design:
            raise HTTPException(status_code=404, detail="Scene not found")
        
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


# ============================================================================
# Library/History Endpoints - View all conversational episodes
# ============================================================================

class EpisodeListItem(BaseModel):
    """Episode list item for library view"""
    id: str
    series_id: str
    episode_number: int
    title: str
    synopsis: Optional[str] = None
    status: str
    mode: Optional[str] = None
    style: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_path: Optional[str] = None
    duration: Optional[int] = None
    created_at: str
    updated_at: str
    character_count: int = 0
    scene_count: int = 0


class EpisodeListResponse(BaseModel):
    """Paginated episode list response"""
    episodes: List[EpisodeListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class EpisodeDetailResponse(BaseModel):
    """Detailed episode information"""
    episode: Dict[str, Any]
    workflow_session: Optional[Dict[str, Any]] = None
    outline: Optional[Dict[str, Any]] = None
    characters: List[Dict[str, Any]] = []
    scenes: List[Dict[str, Any]] = []
    storyboard: List[Dict[str, Any]] = []
    video_info: Optional[Dict[str, Any]] = None


@router.get("/episodes", response_model=EpisodeListResponse)
async def list_episodes(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取所有对话式工作流生成的集数列表
    
    List all conversational workflow episodes with pagination and filtering
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        status: Filter by status (draft, generating, completed, failed)
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
            
            # Get character count
            char_count = db.query(CharacterDesign).filter(
                CharacterDesign.episode_id == ep.id
            ).count()
            
            # Get scene count
            scene_count = db.query(SceneDesign).filter(
                SceneDesign.episode_id == ep.id
            ).count()
            
            # Get thumbnail (first character image or first scene image)
            thumbnail_url = None
            first_char = db.query(CharacterDesign).filter(
                CharacterDesign.episode_id == ep.id,
                CharacterDesign.image_url.isnot(None)
            ).first()
            if first_char and first_char.image_url:
                thumbnail_url = first_char.image_url
            else:
                first_scene = db.query(SceneDesign).filter(
                    SceneDesign.episode_id == ep.id,
                    SceneDesign.image_url.isnot(None)
                ).first()
                if first_scene and first_scene.image_url:
                    thumbnail_url = first_scene.image_url
            
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
    
    Get complete episode details including all generated content
    
    Args:
        episode_id: Episode ID
    """
    try:
        # Get episode
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        # Get workflow session
        session = db.query(EpisodeWorkflowSession).filter(
            EpisodeWorkflowSession.episode_id == episode_id
        ).first()
        
        # Get outline
        outline = db.query(EpisodeOutline).filter(
            EpisodeOutline.episode_id == episode_id
        ).first()
        
        # Get characters
        characters = db.query(CharacterDesign).filter(
            CharacterDesign.episode_id == episode_id
        ).all()
        
        # Get scenes
        scenes = db.query(SceneDesign).filter(
            SceneDesign.episode_id == episode_id
        ).all()
        
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
    
    Delete episode and all related data (cascade delete)
    
    Args:
        episode_id: Episode ID
    """
    try:
        # Get episode
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
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


@router.get("/characters")
async def list_all_characters(
    episode_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取所有角色列表（可选按集数过滤）
    
    List all characters across episodes with optional filtering
    
    Args:
        episode_id: Optional episode ID to filter by
        page: Page number
        page_size: Items per page
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


@router.get("/scenes")
async def list_all_scenes(
    episode_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    获取所有场景列表（可选按集数过滤）
    
    List all scenes across episodes with optional filtering
    
    Args:
        episode_id: Optional episode ID to filter by
        page: Page number
        page_size: Items per page
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