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
            'composition': self.composition,
            'camera_angle': self.camera_angle,
            'camera_movement': self.camera_movement,
            'dialogue': self.dialogue,
            'voice_actor': self.voice_actor,
            'audio_desc': self.audio_desc,
            'frame_url': self.frame_url,
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