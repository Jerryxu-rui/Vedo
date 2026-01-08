"""
Database models for Series/Episode hierarchy and Character management
Extends the existing ViMax system with multi-episode support
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())


class Series(Base):
    """Series model - represents a multi-episode video series"""
    __tablename__ = 'series'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    genre = Column(String(100))  # e.g., "都市悬疑", "科幻爽剧"
    style_preset = Column(String(100))  # e.g., "都市韩漫风格"
    episode_count = Column(Integer, default=0)
    status = Column(String(50), default='draft')  # draft, in_progress, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    episodes = relationship("Episode", back_populates="series", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="series", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'genre': self.genre,
            'style_preset': self.style_preset,
            'episode_count': self.episode_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Episode(Base):
    """Episode model - represents a single episode in a series"""
    __tablename__ = 'episodes'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    series_id = Column(String(36), ForeignKey('series.id', ondelete='CASCADE'), nullable=False)
    episode_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    synopsis = Column(Text)  # Story synopsis
    script = Column(Text)  # Full script content
    highlights = Column(JSON)  # Array of dramatic highlights
    visual_style = Column(Text)  # Visual style description
    duration = Column(Integer)  # Duration in seconds
    status = Column(String(50), default='draft')  # draft, generating, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    series = relationship("Series", back_populates="episodes")
    scenes = relationship("Scene", back_populates="episode", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'series_id': self.series_id,
            'episode_number': self.episode_number,
            'title': self.title,
            'synopsis': self.synopsis,
            'script': self.script,
            'highlights': self.highlights,
            'visual_style': self.visual_style,
            'duration': self.duration,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Scene(Base):
    """Scene model - represents a scene within an episode"""
    __tablename__ = 'scenes'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False)
    scene_number = Column(Integer, nullable=False)
    location = Column(String(255))  # e.g., "公司会议室", "李明公寓"
    description = Column(Text)
    visual_description = Column(Text)  # Detailed visual description
    concept_art_url = Column(String(500))  # URL to concept art image
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    episode = relationship("Episode", back_populates="scenes")
    shots = relationship("Shot", back_populates="scene", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'scene_number': self.scene_number,
            'location': self.location,
            'description': self.description,
            'visual_description': self.visual_description,
            'concept_art_url': self.concept_art_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Shot(Base):
    """Shot model - represents a single shot in a scene (storyboard)"""
    __tablename__ = 'shots'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    scene_id = Column(String(36), ForeignKey('scenes.id', ondelete='CASCADE'), nullable=False)
    shot_number = Column(Integer, nullable=False)
    
    # Visual description
    visual_desc = Column(Text)
    composition = Column(String(100))  # 近景, 中景, 全景, 特写
    camera_angle = Column(String(100))  # 平视, 俯拍, 仰拍
    camera_movement = Column(String(255))  # 镜头推近, 平移, 稳定
    
    # Audio
    dialogue = Column(Text)
    voice_actor = Column(String(100))
    audio_desc = Column(Text)
    
    # Generated assets
    frame_url = Column(String(500))  # URL to generated frame image
    video_url = Column(String(500))  # URL to generated video
    
    # Status
    status = Column(String(50), default='pending')  # pending, generating_frame, generating_video, completed, failed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scene = relationship("Scene", back_populates="shots")
    character_assignments = relationship("CharacterShot", back_populates="shot", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'scene_id': self.scene_id,
            'shot_number': self.shot_number,
            'visual_desc': self.visual_desc,
            'description': self.visual_desc,  # Alias for frontend compatibility
            'composition': self.composition,
            'camera_angle': self.camera_angle,
            'camera_movement': self.camera_movement,
            'dialogue': self.dialogue,
            'voice_actor': self.voice_actor,
            'audio_desc': self.audio_desc,
            'frame_url': self.frame_url,
            'image_url': self.frame_url,  # Alias for frontend compatibility
            'video_url': self.video_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Character(Base):
    """Character model - represents a character in a series"""
    __tablename__ = 'characters'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    series_id = Column(String(36), ForeignKey('series.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(50))  # 主角, 女主角, 反派, 配角
    description = Column(Text)  # Character description
    background = Column(Text)  # Character background story
    personality = Column(Text)  # Personality traits
    appearance_details = Column(Text)  # Detailed appearance description
    consistency_prompt = Column(Text)  # Prompt for maintaining consistency
    reference_images = Column(JSON)  # Array of reference image URLs
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    series = relationship("Series", back_populates="characters")
    shot_assignments = relationship("CharacterShot", back_populates="character", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'series_id': self.series_id,
            'name': self.name,
            'role': self.role,
            'description': self.description,
            'background': self.background,
            'personality': self.personality,
            'appearance_details': self.appearance_details,
            'consistency_prompt': self.consistency_prompt,
            'reference_images': self.reference_images or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CharacterShot(Base):
    """Junction table for character-shot assignments"""
    __tablename__ = 'character_shots'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    character_id = Column(String(36), ForeignKey('characters.id', ondelete='CASCADE'), nullable=False)
    shot_id = Column(String(36), ForeignKey('shots.id', ondelete='CASCADE'), nullable=False)
    role_in_shot = Column(String(50))  # main, supporting, background
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    character = relationship("Character", back_populates="shot_assignments")
    shot = relationship("Shot", back_populates="character_assignments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'character_id': self.character_id,
            'shot_id': self.shot_id,
            'role_in_shot': self.role_in_shot,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class GenerationProgress(Base):
    """Track generation progress for async operations"""
    __tablename__ = 'generation_progress'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(50), nullable=False)  # series, episode, scene, shot
    entity_id = Column(String(36), nullable=False)
    phase = Column(String(100))  # e.g., "明确分镜主体", "构思场景背景"
    status = Column(String(50), default='pending')  # pending, in_progress, completed, failed
    progress_percentage = Column(Integer, default=0)
    message = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'phase': self.phase,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'message': self.message,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EpisodeWorkflowSession(Base):
    """Episode workflow session - tracks conversational workflow state"""
    __tablename__ = 'episode_workflow_sessions'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Workflow state
    mode = Column(String(20), nullable=False)  # 'idea' or 'script'
    state = Column(String(50), nullable=False, default='initial')  # WorkflowState enum value
    style = Column(String(100), default='写实电影感')
    
    # Initial content
    initial_content = Column(Text)  # User's initial idea or script
    
    # Workflow context (JSON)
    context = Column(JSON)  # Stores workflow metadata and history
    
    # Error tracking
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'mode': self.mode,
            'state': self.state,
            'style': self.style,
            'initial_content': self.initial_content,
            'context': self.context or {},
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class EpisodeOutline(Base):
    """Episode outline - stores generated story outline"""
    __tablename__ = 'episode_outlines'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Outline content
    title = Column(String(255))
    genre = Column(String(100))
    style = Column(String(100))
    episode_count = Column(Integer, default=1)
    synopsis = Column(Text)  # Story synopsis
    
    # Structured data
    characters_summary = Column(JSON)  # Array of character summaries
    plot_summary = Column(JSON)  # Array of plot points
    highlights = Column(JSON)  # Array of dramatic highlights
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'title': self.title,
            'genre': self.genre,
            'style': self.style,
            'episode_count': self.episode_count,
            'synopsis': self.synopsis,
            'characters_summary': self.characters_summary or [],
            'plot_summary': self.plot_summary or [],
            'highlights': self.highlights or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CharacterDesign(Base):
    """Character design - stores detailed character design with images"""
    __tablename__ = 'character_designs'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False)
    character_id = Column(String(36), ForeignKey('characters.id', ondelete='SET NULL'), nullable=True)
    
    # Character info
    name = Column(String(100), nullable=False)
    role = Column(String(50))  # protagonist, antagonist, supporting
    description = Column(Text)
    appearance = Column(Text)  # Detailed appearance description
    personality = Column(JSON)  # Array of personality traits
    
    # Generated assets
    image_url = Column(String(500))  # Generated character portrait
    consistency_prompt = Column(Text)  # Prompt for maintaining consistency
    
    # Status
    status = Column(String(50), default='pending')  # pending, generating, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'character_id': self.character_id,
            'name': self.name,
            'role': self.role,
            'description': self.description,
            'appearance': self.appearance,
            'personality': self.personality or [],
            'image_url': self.image_url,
            'consistency_prompt': self.consistency_prompt,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SceneDesign(Base):
    """Scene design - stores detailed scene design with images"""
    __tablename__ = 'scene_designs'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False)
    scene_id = Column(String(36), ForeignKey('scenes.id', ondelete='SET NULL'), nullable=True)
    
    # Scene info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    atmosphere = Column(String(255))  # e.g., "温馨", "紧张", "神秘"
    
    # Generated assets
    image_url = Column(String(500))  # Generated scene concept art
    
    # Status
    status = Column(String(50), default='pending')  # pending, generating, completed, failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'scene_id': self.scene_id,
            'name': self.name,
            'description': self.description,
            'atmosphere': self.atmosphere,
            'image_url': self.image_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# Migration support - extend existing Project model
class Project(Base):
    """Extended Project model with series/episode support"""
    __tablename__ = 'projects'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    series_id = Column(String(36), ForeignKey('series.id', ondelete='SET NULL'), nullable=True)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='SET NULL'), nullable=True)
    
    # Existing fields...
    title = Column(String(255))
    description = Column(Text)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'series_id': self.series_id,
            'episode_id': self.episode_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class UserModelPreference(Base):
    """User model preference - stores user's preferred models"""
    __tablename__ = 'user_model_preferences'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, unique=True)
    video_model = Column(String(100), default='veo3-fast')
    image_model = Column(String(100), default='doubao-seedream-4-0-250828')
    chat_model = Column(String(100), default='gemini-2.0-flash-001')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'video_model': self.video_model,
            'image_model': self.image_model,
            'chat_model': self.chat_model,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AvailableModel(Base):
    """Available model - stores information about available models"""
    __tablename__ = 'available_models'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False)  # video, image, chat
    provider = Column(String(100), nullable=False)
    description = Column(Text)
    capabilities = Column(JSON)  # Store model capabilities as JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'provider': self.provider,
            'description': self.description,
            'capabilities': self.capabilities or {},
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationThread(Base):
    """Conversation thread - stores chat conversation history"""
    __tablename__ = 'conversation_threads'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='SET NULL'), nullable=True)
    title = Column(String(255))
    llm_model = Column(String(100), nullable=False)  # Which LLM is being used
    system_prompt = Column(Text)  # System prompt for the conversation
    context = Column(JSON)  # Additional context data
    status = Column(String(50), default='active')  # active, archived, deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("ConversationMessage", back_populates="thread", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'episode_id': self.episode_id,
            'title': self.title,
            'llm_model': self.llm_model,
            'system_prompt': self.system_prompt,
            'context': self.context or {},
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationMessage(Base):
    """Conversation message - individual message in a conversation"""
    __tablename__ = 'conversation_messages'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    thread_id = Column(String(36), ForeignKey('conversation_threads.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON)  # Store additional metadata (tokens, model, etc.) - renamed to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    thread = relationship("ConversationThread", back_populates="messages")
    
    def to_dict(self):
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'role': self.role,
            'content': self.content,
            'metadata': self.message_metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AgentTask(Base):
    """Agent task - tracks multi-agent workflow tasks"""
    __tablename__ = 'agent_tasks'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    thread_id = Column(String(36), ForeignKey('conversation_threads.id', ondelete='CASCADE'), nullable=True)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=True)
    
    # Task info
    task_type = Column(String(100), nullable=False)  # dialogue_interpretation, scene_design, etc.
    agent_name = Column(String(100), nullable=False)  # Which agent is handling this
    input_data = Column(JSON)  # Input parameters for the task
    output_data = Column(JSON)  # Results from the task
    
    # Status tracking
    status = Column(String(50), default='pending')  # pending, in_progress, completed, failed
    progress_percentage = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'episode_id': self.episode_id,
            'task_type': self.task_type,
            'agent_name': self.agent_name,
            'input_data': self.input_data or {},
            'output_data': self.output_data or {},
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class LLMAPIKey(Base):
    """LLM API Key - stores API keys for different LLM providers"""
    __tablename__ = 'llm_api_keys'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False)
    provider = Column(String(50), nullable=False)  # google, alibaba, anthropic, openai, deepseek
    api_key = Column(String(500), nullable=False)  # Encrypted API key
    api_endpoint = Column(String(500))  # Custom endpoint if needed
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'provider': self.provider,
            'api_key': '***' + self.api_key[-4:] if self.api_key else None,  # Masked for security
            'api_endpoint': self.api_endpoint,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VideoGenerationJob(Base):
    """Video generation job - unified storage for all video generation jobs"""
    __tablename__ = 'video_generation_jobs'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    # Job metadata
    job_type = Column(String(50), nullable=False)  # idea2video, script2video, conversational
    mode = Column(String(20))  # idea, script (for unified API)
    status = Column(String(50), default='queued')  # queued, processing, completed, failed, cancelled
    
    # Input data
    content = Column(Text)  # idea or script content
    user_requirement = Column(Text)
    style = Column(String(255))
    project_title = Column(String(255))
    
    # Context and metadata
    request_data = Column(JSON)  # Full request payload
    context = Column(JSON)  # Additional context
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0-100
    current_stage = Column(String(255))
    
    # Results
    working_dir = Column(String(500))
    result_data = Column(JSON)  # Final results
    error_message = Column(Text)
    
    # Shot tracking
    total_shots = Column(Integer, default=0)
    completed_shots = Column(Integer, default=0)
    
    # Relationships
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='SET NULL'), nullable=True)
    series_id = Column(String(36), ForeignKey('series.id', ondelete='SET NULL'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'job_id': self.id,
            'job_type': self.job_type,
            'mode': self.mode,
            'status': self.status,
            'content': self.content,
            'user_requirement': self.user_requirement,
            'style': self.style,
            'project_title': self.project_title,
            'request_data': self.request_data or {},
            'context': self.context or {},
            'progress': self.progress,
            'current_stage': self.current_stage,
            'working_dir': self.working_dir,
            'result': self.result_data,
            'error': self.error_message,
            'total_shots': self.total_shots,
            'completed_shots': self.completed_shots,
            'episode_id': self.episode_id,
            'series_id': self.series_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class VideoSegment(Base):
    """Video segment - represents an individual video segment for step-by-step generation"""
    __tablename__ = 'video_segments'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=True)
    scene_id = Column(String(36), ForeignKey('scenes.id', ondelete='SET NULL'), nullable=True)
    shot_id = Column(String(36), ForeignKey('shots.id', ondelete='SET NULL'), nullable=True)
    
    # Segment info
    segment_number = Column(Integer, nullable=False)
    segment_type = Column(String(50), default='shot')  # 'scene', 'shot', 'transition'
    
    # Generation parameters
    generation_params = Column(JSON)  # Stores prompt, style, seed, etc.
    
    # Status
    status = Column(String(50), default='pending')  # pending, generating, completed, approved, rejected, failed
    approval_status = Column(String(50))  # null, approved, rejected, needs_revision
    
    # Generated assets
    video_url = Column(String(500))
    thumbnail_url = Column(String(500))
    duration = Column(Float)  # in seconds
    
    # Quality metrics
    quality_score = Column(Float)
    consistency_score = Column(Float)
    
    # Metadata
    file_size = Column(Integer)
    resolution = Column(String(20))  # e.g., "1920x1080"
    format = Column(String(20))  # e.g., "mp4"
    
    # Versioning
    version = Column(Integer, default=1)
    parent_segment_id = Column(String(36), ForeignKey('video_segments.id', ondelete='SET NULL'), nullable=True)
    
    # User feedback
    user_notes = Column(Text)
    rejection_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime)
    
    # Relationships
    parent_segment = relationship("VideoSegment", remote_side=[id], backref="child_versions")
    reviews = relationship("SegmentReview", back_populates="segment", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'scene_id': self.scene_id,
            'shot_id': self.shot_id,
            'segment_number': self.segment_number,
            'segment_type': self.segment_type,
            'generation_params': self.generation_params or {},
            'status': self.status,
            'approval_status': self.approval_status,
            'video_url': self.video_url,
            'thumbnail_url': self.thumbnail_url,
            'duration': self.duration,
            'quality_score': self.quality_score,
            'consistency_score': self.consistency_score,
            'file_size': self.file_size,
            'resolution': self.resolution,
            'format': self.format,
            'version': self.version,
            'parent_segment_id': self.parent_segment_id,
            'user_notes': self.user_notes,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
        }


class SegmentCompilationJob(Base):
    """Segment compilation job - tracks compilation of approved segments into final video"""
    __tablename__ = 'segment_compilation_jobs'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False)
    
    # Compilation config
    segment_ids = Column(JSON)  # Array of segment IDs in order
    transition_style = Column(String(100), default='cut')  # cut, fade, dissolve
    audio_config = Column(JSON)  # Audio mixing configuration
    
    # Status
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)  # 0-100
    
    # Output
    output_video_url = Column(String(500))
    output_duration = Column(Float)
    output_file_size = Column(Integer)
    
    # Error tracking
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'segment_ids': self.segment_ids or [],
            'transition_style': self.transition_style,
            'audio_config': self.audio_config or {},
            'status': self.status,
            'progress': self.progress,
            'output_video_url': self.output_video_url,
            'output_duration': self.output_duration,
            'output_file_size': self.output_file_size,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class SegmentReview(Base):
    """Segment review - stores user feedback and review history for video segments"""
    __tablename__ = 'segment_reviews'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    segment_id = Column(String(36), ForeignKey('video_segments.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(36))  # User who performed the review
    
    # Review data
    action = Column(String(50), nullable=False)  # 'approve', 'reject', 'request_regeneration'
    rating = Column(Integer)  # 1-5 stars
    feedback = Column(Text)
    suggested_changes = Column(JSON)  # Structured suggestions for improvement
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    segment = relationship("VideoSegment", back_populates="reviews")
    
    def to_dict(self):
        return {
            'id': self.id,
            'segment_id': self.segment_id,
            'user_id': self.user_id,
            'action': self.action,
            'rating': self.rating,
            'feedback': self.feedback,
            'suggested_changes': self.suggested_changes or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# ENHANCED AGENT MEMORY SYSTEM MODELS
# ============================================================================

class EpisodeMemory(Base):
    """Episodic Memory - Session-based memory for episode generation"""
    __tablename__ = 'episode_memories'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(255), nullable=False)
    memory_type = Column(String(50), nullable=False)  # decision, feedback, outcome, interaction
    agent_name = Column(String(100), nullable=False)
    context = Column(JSON, nullable=False)
    outcome = Column(JSON)
    quality_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'user_id': self.user_id,
            'memory_type': self.memory_type,
            'agent_name': self.agent_name,
            'context': self.context or {},
            'outcome': self.outcome or {},
            'quality_score': self.quality_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SemanticMemory(Base):
    """Semantic Memory - Long-term cross-session knowledge"""
    __tablename__ = 'semantic_memories'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(255))  # NULL for global memories
    memory_category = Column(String(100), nullable=False)  # pattern, preference, strategy, failure, feedback
    agent_name = Column(String(100))
    content = Column(JSON, nullable=False)
    embedding_text = Column(Text)  # Text for embedding generation
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    decay_score = Column(Float, default=1.0)
    
    # Relationships
    embeddings = relationship("MemoryEmbedding", back_populates="semantic_memory", cascade="all, delete-orphan")
    retrieval_logs = relationship("MemoryRetrievalLog", back_populates="semantic_memory", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'memory_category': self.memory_category,
            'agent_name': self.agent_name,
            'content': self.content or {},
            'embedding_text': self.embedding_text,
            'usage_count': self.usage_count,
            'success_rate': self.success_rate,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'decay_score': self.decay_score,
        }


class UserMemoryProfile(Base):
    """User Memory Profile - Personalization data"""
    __tablename__ = 'user_memory_profiles'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(255), unique=True, nullable=False)
    preferred_styles = Column(JSON, default=list)
    preferred_genres = Column(JSON, default=list)
    common_themes = Column(JSON, default=list)
    generation_preferences = Column(JSON, default=dict)
    feedback_patterns = Column(JSON, default=dict)
    total_episodes = Column(Integer, default=0)
    avg_quality_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preferred_styles': self.preferred_styles or [],
            'preferred_genres': self.preferred_genres or [],
            'common_themes': self.common_themes or [],
            'generation_preferences': self.generation_preferences or {},
            'feedback_patterns': self.feedback_patterns or {},
            'total_episodes': self.total_episodes,
            'avg_quality_score': self.avg_quality_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MemoryConsolidation(Base):
    """Memory Consolidation Log - Audit trail for consolidation process"""
    __tablename__ = 'memory_consolidations'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='SET NULL'))
    consolidation_type = Column(String(50), nullable=False)  # episode_complete, periodic, manual
    insights_extracted = Column(Integer, default=0)
    patterns_identified = Column(Integer, default=0)
    memories_created = Column(Integer, default=0)
    memories_updated = Column(Integer, default=0)
    memories_pruned = Column(Integer, default=0)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'episode_id': self.episode_id,
            'consolidation_type': self.consolidation_type,
            'insights_extracted': self.insights_extracted,
            'patterns_identified': self.patterns_identified,
            'memories_created': self.memories_created,
            'memories_updated': self.memories_updated,
            'memories_pruned': self.memories_pruned,
            'processing_time_ms': self.processing_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class MemoryEmbedding(Base):
    """Memory Embedding Cache - Stores vector embeddings for semantic search"""
    __tablename__ = 'memory_embeddings'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    semantic_memory_id = Column(String(36), ForeignKey('semantic_memories.id', ondelete='CASCADE'), nullable=False)
    embedding_model = Column(String(100), nullable=False)
    embedding_vector = Column(Text, nullable=False)  # JSON array of floats
    dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    semantic_memory = relationship("SemanticMemory", back_populates="embeddings")
    
    def to_dict(self):
        return {
            'id': self.id,
            'semantic_memory_id': self.semantic_memory_id,
            'embedding_model': self.embedding_model,
            'dimension': self.dimension,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AgentPerformanceMetric(Base):
    """Agent Performance Metrics - Track agent performance for memory-augmented decisions"""
    __tablename__ = 'agent_performance_metrics'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_name = Column(String(100), nullable=False)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='CASCADE'))
    metric_type = Column(String(50), nullable=False)  # quality, speed, accuracy, user_satisfaction
    metric_value = Column(Float, nullable=False)
    context = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'agent_name': self.agent_name,
            'episode_id': self.episode_id,
            'metric_type': self.metric_type,
            'metric_value': self.metric_value,
            'context': self.context or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class MemoryRetrievalLog(Base):
    """Memory Retrieval Log - Track memory usage for analytics"""
    __tablename__ = 'memory_retrieval_log'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    semantic_memory_id = Column(String(36), ForeignKey('semantic_memories.id', ondelete='CASCADE'), nullable=False)
    agent_name = Column(String(100), nullable=False)
    episode_id = Column(String(36), ForeignKey('episodes.id', ondelete='SET NULL'))
    query_text = Column(Text)
    similarity_score = Column(Float)
    was_useful = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    semantic_memory = relationship("SemanticMemory", back_populates="retrieval_logs")
    
    def to_dict(self):
        return {
            'id': self.id,
            'semantic_memory_id': self.semantic_memory_id,
            'agent_name': self.agent_name,
            'episode_id': self.episode_id,
            'query_text': self.query_text,
            'similarity_score': self.similarity_score,
            'was_useful': self.was_useful,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }