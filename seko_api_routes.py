"""
Seko API Routes - Series/Episode/Character Management
Extends the existing ViMax API with multi-episode support and character consistency
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import json

# Import database models
from database_models import (
    Series, Episode, Scene, Shot, Character, CharacterShot, 
    GenerationProgress, Base
)

# Create router
router = APIRouter(prefix="/api/v1/seko", tags=["seko"])


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class SeriesCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[str] = None
    style_preset: Optional[str] = "都市韩漫风格"
    episode_count: int = Field(default=1, ge=1, le=100)


class SeriesUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    genre: Optional[str] = None
    style_preset: Optional[str] = None
    episode_count: Optional[int] = Field(None, ge=1, le=100)
    status: Optional[str] = None


class SeriesResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    genre: Optional[str]
    style_preset: Optional[str]
    episode_count: int
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class EpisodeCreate(BaseModel):
    episode_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=255)
    synopsis: Optional[str] = None
    script: Optional[str] = None
    highlights: Optional[List[dict]] = None
    visual_style: Optional[str] = None


class EpisodeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    synopsis: Optional[str] = None
    script: Optional[str] = None
    highlights: Optional[List[dict]] = None
    visual_style: Optional[str] = None
    status: Optional[str] = None


class EpisodeResponse(BaseModel):
    id: str
    series_id: str
    episode_number: int
    title: str
    synopsis: Optional[str]
    script: Optional[str]
    highlights: Optional[List[dict]]
    visual_style: Optional[str]
    duration: Optional[int]
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: Optional[str] = "配角"  # 主角, 女主角, 反派, 配角
    description: Optional[str] = None
    background: Optional[str] = None
    personality: Optional[str] = None
    appearance_details: Optional[str] = None
    consistency_prompt: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = None
    description: Optional[str] = None
    background: Optional[str] = None
    personality: Optional[str] = None
    appearance_details: Optional[str] = None
    consistency_prompt: Optional[str] = None


class CharacterResponse(BaseModel):
    id: str
    series_id: str
    name: str
    role: Optional[str]
    description: Optional[str]
    background: Optional[str]
    personality: Optional[str]
    appearance_details: Optional[str]
    consistency_prompt: Optional[str]
    reference_images: List[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class CharacterAssignment(BaseModel):
    character_id: str
    role_in_shot: str = "main"  # main, supporting, background


class SceneCreate(BaseModel):
    scene_number: int = Field(..., ge=1)
    location: Optional[str] = None
    description: Optional[str] = None
    visual_description: Optional[str] = None


class ShotCreate(BaseModel):
    shot_number: int = Field(..., ge=1)
    visual_desc: Optional[str] = None
    composition: Optional[str] = None  # 近景, 中景, 全景, 特写
    camera_angle: Optional[str] = None  # 平视, 俯拍, 仰拍
    camera_movement: Optional[str] = None
    dialogue: Optional[str] = None
    voice_actor: Optional[str] = None
    audio_desc: Optional[str] = None


# ============================================================================
# Database Dependency
# ============================================================================

# Import database dependency from database.py
from database import get_db


# ============================================================================
# Series Management Endpoints
# ============================================================================

@router.post("/series", response_model=SeriesResponse, status_code=201)
async def create_series(
    series: SeriesCreate,
    db: Session = Depends(get_db)
):
    """Create a new series"""
    try:
        new_series = Series(
            id=str(uuid.uuid4()),
            title=series.title,
            description=series.description,
            genre=series.genre,
            style_preset=series.style_preset,
            episode_count=series.episode_count,
            status='draft'
        )
        
        db.add(new_series)
        db.commit()
        db.refresh(new_series)
        
        return new_series.to_dict()
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create series: {str(e)}")


@router.get("/series", response_model=List[SeriesResponse])
async def list_series(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all series with optional filtering"""
    try:
        query = db.query(Series)
        
        if status:
            query = query.filter(Series.status == status)
        
        series_list = query.offset(skip).limit(limit).all()
        return [s.to_dict() for s in series_list]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list series: {str(e)}")


@router.get("/series/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: str,
    db: Session = Depends(get_db)
):
    """Get series details with episodes"""
    try:
        series = db.query(Series).filter(Series.id == series_id).first()
        
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        series_dict = series.to_dict()
        
        # Include episodes
        episodes = db.query(Episode).filter(Episode.series_id == series_id).all()
        series_dict['episodes'] = [e.to_dict() for e in episodes]
        
        # Include characters
        characters = db.query(Character).filter(Character.series_id == series_id).all()
        series_dict['characters'] = [c.to_dict() for c in characters]
        
        return series_dict
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get series: {str(e)}")


@router.put("/series/{series_id}", response_model=SeriesResponse)
async def update_series(
    series_id: str,
    series_update: SeriesUpdate,
    db: Session = Depends(get_db)
):
    """Update series details"""
    try:
        series = db.query(Series).filter(Series.id == series_id).first()
        
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        # Update fields
        update_data = series_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(series, field, value)
        
        series.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(series)
        
        return series.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update series: {str(e)}")


@router.delete("/series/{series_id}", status_code=204)
async def delete_series(
    series_id: str,
    db: Session = Depends(get_db)
):
    """Delete series and all related data (CASCADE)"""
    try:
        series = db.query(Series).filter(Series.id == series_id).first()
        
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        db.delete(series)
        db.commit()
        
        return {"message": "Series deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete series: {str(e)}")


# ============================================================================
# Episode Management Endpoints
# ============================================================================

@router.post("/series/{series_id}/episodes", response_model=EpisodeResponse, status_code=201)
async def create_episode(
    series_id: str,
    episode: EpisodeCreate,
    db: Session = Depends(get_db)
):
    """Create a new episode in a series"""
    try:
        # Verify series exists
        series = db.query(Series).filter(Series.id == series_id).first()
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        # Check if episode number already exists
        existing = db.query(Episode).filter(
            Episode.series_id == series_id,
            Episode.episode_number == episode.episode_number
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Episode {episode.episode_number} already exists"
            )
        
        new_episode = Episode(
            id=str(uuid.uuid4()),
            series_id=series_id,
            episode_number=episode.episode_number,
            title=episode.title,
            synopsis=episode.synopsis,
            script=episode.script,
            highlights=episode.highlights,
            visual_style=episode.visual_style,
            status='draft'
        )
        
        db.add(new_episode)
        db.commit()
        db.refresh(new_episode)
        
        return new_episode.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create episode: {str(e)}")


@router.get("/series/{series_id}/episodes", response_model=List[EpisodeResponse])
async def list_episodes(
    series_id: str,
    db: Session = Depends(get_db)
):
    """List all episodes in a series"""
    try:
        episodes = db.query(Episode).filter(
            Episode.series_id == series_id
        ).order_by(Episode.episode_number).all()
        
        return [e.to_dict() for e in episodes]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list episodes: {str(e)}")


@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """Get episode details with scenes and shots"""
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        episode_dict = episode.to_dict()
        
        # Include scenes
        scenes = db.query(Scene).filter(Scene.episode_id == episode_id).all()
        episode_dict['scenes'] = [s.to_dict() for s in scenes]
        
        # Include shots for each scene
        for scene_dict in episode_dict['scenes']:
            shots = db.query(Shot).filter(Shot.scene_id == scene_dict['id']).all()
            scene_dict['shots'] = [shot.to_dict() for shot in shots]
        
        return episode_dict
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get episode: {str(e)}")


@router.put("/episodes/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    episode_id: str,
    episode_update: EpisodeUpdate,
    db: Session = Depends(get_db)
):
    """Update episode details"""
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        # Update fields
        update_data = episode_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(episode, field, value)
        
        episode.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(episode)
        
        return episode.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update episode: {str(e)}")


@router.delete("/episodes/{episode_id}", status_code=204)
async def delete_episode(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """Delete episode and all related data (CASCADE)"""
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        db.delete(episode)
        db.commit()
        
        return {"message": "Episode deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete episode: {str(e)}")


# ============================================================================
# Character Management Endpoints
# ============================================================================

@router.post("/series/{series_id}/characters", response_model=CharacterResponse, status_code=201)
async def create_character(
    series_id: str,
    character: CharacterCreate,
    db: Session = Depends(get_db)
):
    """Create a new character for a series"""
    try:
        # Verify series exists
        series = db.query(Series).filter(Series.id == series_id).first()
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        
        new_character = Character(
            id=str(uuid.uuid4()),
            series_id=series_id,
            name=character.name,
            role=character.role,
            description=character.description,
            background=character.background,
            personality=character.personality,
            appearance_details=character.appearance_details,
            consistency_prompt=character.consistency_prompt,
            reference_images=[]
        )
        
        db.add(new_character)
        db.commit()
        db.refresh(new_character)
        
        return new_character.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create character: {str(e)}")


@router.get("/series/{series_id}/characters", response_model=List[CharacterResponse])
async def list_characters(
    series_id: str,
    db: Session = Depends(get_db)
):
    """List all characters in a series"""
    try:
        characters = db.query(Character).filter(
            Character.series_id == series_id
        ).all()
        
        return [c.to_dict() for c in characters]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list characters: {str(e)}")


@router.get("/characters/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Get character details"""
    try:
        character = db.query(Character).filter(Character.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return character.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get character: {str(e)}")


@router.put("/characters/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    character_update: CharacterUpdate,
    db: Session = Depends(get_db)
):
    """Update character details"""
    try:
        character = db.query(Character).filter(Character.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Update fields
        update_data = character_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(character, field, value)
        
        character.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(character)
        
        return character.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update character: {str(e)}")


@router.delete("/characters/{character_id}", status_code=204)
async def delete_character(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Delete character"""
    try:
        character = db.query(Character).filter(Character.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        db.delete(character)
        db.commit()
        
        return {"message": "Character deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete character: {str(e)}")


@router.post("/characters/{character_id}/reference")
async def upload_reference_image(
    character_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a reference image for a character"""
    import os
    import aiofiles
    
    try:
        character = db.query(Character).filter(Character.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Create upload directory
        upload_dir = os.path.join(".working_dir", "uploads", "characters", character_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate safe filename
        safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Save file to disk
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # Generate URL for API access
        file_url = f"/media/uploads/characters/{character_id}/{safe_filename}"
        
        # Add to reference images
        if character.reference_images is None:
            character.reference_images = []
        
        character.reference_images.append(file_url)
        character.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(character)
        
        return {
            "message": "Reference image uploaded successfully",
            "url": file_url,
            "character": character.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upload reference image: {str(e)}")


# ============================================================================
# Character-Shot Assignment Endpoints
# ============================================================================

@router.get("/shots/{shot_id}/characters")
async def get_shot_characters(
    shot_id: str,
    db: Session = Depends(get_db)
):
    """Get all characters assigned to a shot"""
    try:
        assignments = db.query(CharacterShot).filter(
            CharacterShot.shot_id == shot_id
        ).all()
        
        result = []
        for assignment in assignments:
            character = db.query(Character).filter(
                Character.id == assignment.character_id
            ).first()
            
            if character:
                result.append({
                    "assignment_id": assignment.id,
                    "character": character.to_dict(),
                    "role_in_shot": assignment.role_in_shot
                })
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get shot characters: {str(e)}")


@router.post("/shots/{shot_id}/characters")
async def assign_character_to_shot(
    shot_id: str,
    assignment: CharacterAssignment,
    db: Session = Depends(get_db)
):
    """Assign a character to a shot"""
    try:
        # Verify shot exists
        shot = db.query(Shot).filter(Shot.id == shot_id).first()
        if not shot:
            raise HTTPException(status_code=404, detail="Shot not found")
        
        # Verify character exists
        character = db.query(Character).filter(Character.id == assignment.character_id).first()
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Check if already assigned
        existing = db.query(CharacterShot).filter(
            CharacterShot.shot_id == shot_id,
            CharacterShot.character_id == assignment.character_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Character already assigned to this shot")
        
        new_assignment = CharacterShot(
            id=str(uuid.uuid4()),
            character_id=assignment.character_id,
            shot_id=shot_id,
            role_in_shot=assignment.role_in_shot
        )
        
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        
        return {
            "message": "Character assigned successfully",
            "assignment": new_assignment.to_dict(),
            "character": character.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to assign character: {str(e)}")


@router.delete("/shots/{shot_id}/characters/{character_id}", status_code=204)
async def remove_character_from_shot(
    shot_id: str,
    character_id: str,
    db: Session = Depends(get_db)
):
    """Remove a character assignment from a shot"""
    try:
        assignment = db.query(CharacterShot).filter(
            CharacterShot.shot_id == shot_id,
            CharacterShot.character_id == character_id
        ).first()
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Character assignment not found")
        
        db.delete(assignment)
        db.commit()
        
        return {"message": "Character removed from shot successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to remove character: {str(e)}")


# ============================================================================
# Generation Progress Endpoints
# ============================================================================

@router.get("/progress/{entity_type}/{entity_id}")
async def get_generation_progress(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db)
):
    """Get generation progress for an entity"""
    try:
        progress_items = db.query(GenerationProgress).filter(
            GenerationProgress.entity_type == entity_type,
            GenerationProgress.entity_id == entity_id
        ).order_by(GenerationProgress.created_at.desc()).all()
        
        return [p.to_dict() for p in progress_items]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.post("/progress")
async def create_progress_entry(
    entity_type: str,
    entity_id: str,
    phase: str,
    status: str = "pending",
    progress_percentage: int = 0,
    message: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new progress entry"""
    try:
        progress = GenerationProgress(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            entity_id=entity_id,
            phase=phase,
            status=status,
            progress_percentage=progress_percentage,
            message=message
        )
        
        db.add(progress)
        db.commit()
        db.refresh(progress)
        
        return progress.to_dict()
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create progress entry: {str(e)}")