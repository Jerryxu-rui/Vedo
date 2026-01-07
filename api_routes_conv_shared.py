"""
Shared Components for Conversational API Modules
共享组件 - 用于对话式API模块

This module contains common models, utilities, and dependencies
used across all conversational workflow API modules.
"""

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from database import get_db
from database_models import (
    Episode, EpisodeWorkflowSession, EpisodeOutline,
    CharacterDesign, SceneDesign, Series
)
from workflows.conversational_episode_workflow import (
    ConversationalEpisodeWorkflow, WorkflowManager, WorkflowMode, WorkflowState,
    workflow_manager
)
from utils.websocket_manager import WebSocketManager

# ============================================================================
# Shared WebSocket Manager
# ============================================================================

ws_manager = WebSocketManager()


# ============================================================================
# Shared Pydantic Models
# ============================================================================

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
    video_path: Optional[str] = None
    error: Optional[str] = None


class CreateWorkflowRequest(BaseModel):
    """创建工作流请求"""
    series_id: Optional[str] = Field(default="default-series", description="Series ID (auto-generated if not provided)")
    episode_number: int = Field(default=1, description="Episode number")
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
    """更新单个角色请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[List[str]] = None
    role: Optional[str] = None


class UpdateSceneRequest(BaseModel):
    """更新单个场景请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    atmosphere: Optional[str] = None


class UpdateShotRequest(BaseModel):
    """更新单个分镜请求"""
    visual_desc: Optional[str] = None
    camera_angle: Optional[str] = None
    camera_movement: Optional[str] = None
    dialogue: Optional[str] = None
    voice_actor: Optional[str] = None


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


# ============================================================================
# Shared Helper Functions
# ============================================================================

def get_workflow_session(db: Session, episode_id: str) -> EpisodeWorkflowSession:
    """
    获取工作流会话
    
    Args:
        db: Database session
        episode_id: Episode ID
        
    Returns:
        EpisodeWorkflowSession object
        
    Raises:
        HTTPException: If session not found
    """
    session = db.query(EpisodeWorkflowSession).filter(
        EpisodeWorkflowSession.episode_id == episode_id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Workflow session not found")
    
    return session


def get_or_create_workflow(
    episode_id: str,
    db: Session
) -> ConversationalEpisodeWorkflow:
    """
    获取或创建工作流实例
    
    Args:
        episode_id: Episode ID (UUID string)
        db: Database session
        
    Returns:
        ConversationalEpisodeWorkflow instance
        
    Raises:
        HTTPException: 404 if workflow cannot be found or created
    """
    # Convert episode_id to int for workflow manager
    episode_id_int = int(episode_id) if episode_id.isdigit() else hash(episode_id)
    
    # Try to get from memory
    workflow = workflow_manager.get_workflow(episode_id_int)
    
    # If not in memory, try to restore from database
    if not workflow:
        workflow = workflow_manager.load_or_create_from_db(episode_id_int, episode_id, db)
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflow


def save_workflow_state(db: Session, workflow: ConversationalEpisodeWorkflow):
    """
    保存工作流状态到数据库
    
    Args:
        db: Database session
        workflow: Workflow instance to save
    """
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


def convert_file_path_to_url(file_path: str) -> str:
    """
    Convert local file path to web-accessible URL
    
    Args:
        file_path: Local file path
        
    Returns:
        Web-accessible URL
    """
    if not file_path:
        print(f"[URL Conversion] WARNING: Empty file_path provided")
        return None
    
    print(f"[URL Conversion] Input: {file_path}")
    
    # If already an external URL (http/https), return as-is
    if file_path.startswith('http://') or file_path.startswith('https://'):
        print(f"[URL Conversion] External URL, returning as-is: {file_path}")
        return file_path
    
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


def validate_episode_exists(episode_id: str, db: Session) -> Episode:
    """
    验证集数是否存在
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        Episode object
        
    Raises:
        HTTPException: If episode not found
    """
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


def validate_workflow_mode(mode: str):
    """
    验证工作流模式
    
    Args:
        mode: Workflow mode string
        
    Raises:
        HTTPException: If mode is invalid
    """
    if mode not in ["idea", "script"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {mode}. Must be 'idea' or 'script'"
        )


def validate_initial_content(content: str):
    """
    验证初始内容
    
    Args:
        content: Initial content string
        
    Raises:
        HTTPException: If content is empty
    """
    if not content or not content.strip():
        raise HTTPException(
            status_code=400,
            detail="initial_content cannot be empty"
        )


def get_or_create_series(series_id: str, title: str, style: str, db: Session) -> Series:
    """
    获取或创建系列
    
    Args:
        series_id: Series ID
        title: Series title
        style: Visual style
        db: Database session
        
    Returns:
        Series object
    """
    series = db.query(Series).filter(Series.id == series_id).first()
    if not series:
        series = Series(
            id=series_id,
            title=title or "Default Series",
            description="Auto-generated series",
            genre="general",
            style_preset=style or "cinematic",
            status="in_progress"
        )
        db.add(series)
        db.flush()
    return series


def handle_workflow_error(
    workflow: ConversationalEpisodeWorkflow,
    error: Exception,
    db: Session,
    topic: str = None
):
    """
    处理工作流错误
    
    Args:
        workflow: Workflow instance
        error: Exception that occurred
        db: Database session
        topic: WebSocket topic for error notification
    """
    import traceback
    
    print(f"❌ Workflow error: {error}")
    traceback.print_exc()
    
    workflow.error = str(error)
    workflow.transition_to(WorkflowState.FAILED)
    save_workflow_state(db, workflow)
    db.commit()
    
    # Send WebSocket error if topic provided
    if topic:
        episode_id_str = workflow.context.get("episode_id_str", str(workflow.episode_id))
        import asyncio
        asyncio.create_task(
            ws_manager.send_error(
                topic=topic,
                error_message="Operation failed",
                error_details={"error": str(error)}
            )
        )


# ============================================================================
# Shared Database Queries
# ============================================================================

def get_episode_outline(episode_id: str, db: Session) -> Optional[EpisodeOutline]:
    """
    获取集数大纲
    
    Args:
        episode_id: Episode ID
        db: Database session
        
    Returns:
        EpisodeOutline or None if not found
    """
    return db.query(EpisodeOutline).filter(
        EpisodeOutline.episode_id == episode_id
    ).first()


def get_episode_characters(episode_id: str, db: Session) -> List[CharacterDesign]:
    """获取集数角色列表"""
    return db.query(CharacterDesign).filter(
        CharacterDesign.episode_id == episode_id
    ).all()


def get_episode_scenes(episode_id: str, db: Session) -> List[SceneDesign]:
    """获取集数场景列表"""
    return db.query(SceneDesign).filter(
        SceneDesign.episode_id == episode_id
    ).all()


def get_character_by_id(character_id: str, episode_id: str, db: Session) -> CharacterDesign:
    """
    获取指定角色
    
    Raises:
        HTTPException: If character not found
    """
    character = db.query(CharacterDesign).filter(
        CharacterDesign.id == character_id,
        CharacterDesign.episode_id == episode_id
    ).first()
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return character


def get_scene_by_id(scene_id: str, episode_id: str, db: Session) -> SceneDesign:
    """
    获取指定场景
    
    Raises:
        HTTPException: If scene not found
    """
    scene = db.query(SceneDesign).filter(
        SceneDesign.id == scene_id,
        SceneDesign.episode_id == episode_id
    ).first()
    
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    return scene


# ============================================================================
# Export All
# ============================================================================

__all__ = [
    # WebSocket
    'ws_manager',
    
    # Models
    'WorkflowStateResponse',
    'CreateWorkflowRequest',
    'WorkflowActionRequest',
    'UpdateOutlineRequest',
    'UpdateCharacterRequest',
    'UpdateSceneRequest',
    'UpdateShotRequest',
    'EpisodeListItem',
    'EpisodeListResponse',
    'EpisodeDetailResponse',
    
    # Helper Functions
    'get_workflow_session',
    'get_or_create_workflow',
    'save_workflow_state',
    'convert_file_path_to_url',
    'validate_episode_exists',
    'validate_workflow_mode',
    'validate_initial_content',
    'get_or_create_series',
    'handle_workflow_error',
    
    # Database Queries
    'get_episode_outline',
    'get_episode_characters',
    'get_episode_scenes',
    'get_character_by_id',
    'get_scene_by_id',
]