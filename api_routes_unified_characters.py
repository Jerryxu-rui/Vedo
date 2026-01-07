"""
Unified Character Management API
Consolidates character endpoints from api_server.py and seko_api_routes.py
Provides both standalone and series-scoped character management with database persistence
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import os
import aiofiles

# Import database models and dependencies
from database_models import Character as DBCharacter, CharacterShot, Series
from database import get_db

# Import character service for legacy compatibility
from services.character_service import character_service
from models.character import Character, CharacterAppearance, CharacterAppearanceRecord

# Create router
router = APIRouter(prefix="/api/v1/characters", tags=["characters"])


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class CharacterCreateRequest(BaseModel):
    """Unified request to create a character"""
    name: str = Field(..., description="Character name", min_length=1, max_length=100)
    description: str = Field(..., description="Character description")
    
    # Series context (optional - for series-scoped characters)
    series_id: Optional[str] = Field(None, description="Series ID if character belongs to a series")
    
    # Basic attributes
    role: Optional[str] = Field("配角", description="Character role: 主角, 女主角, 反派, 配角")
    age: Optional[str] = None
    gender: Optional[str] = None
    
    # Detailed attributes
    background: Optional[str] = Field(None, description="Character background story")
    personality: Optional[str] = Field(None, description="Personality description")
    personality_traits: Optional[List[str]] = Field(None, description="List of personality traits")
    
    # Appearance
    appearance: Optional[Dict[str, Any]] = Field(None, description="Appearance attributes (structured)")
    appearance_details: Optional[str] = Field(None, description="Appearance details (text)")
    consistency_prompt: Optional[str] = Field(None, description="Prompt for consistent generation")


class CharacterUpdateRequest(BaseModel):
    """Unified request to update a character"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    role: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    background: Optional[str] = None
    personality: Optional[str] = None
    personality_traits: Optional[List[str]] = None
    appearance: Optional[Dict[str, Any]] = None
    appearance_details: Optional[str] = None
    consistency_prompt: Optional[str] = None


class CharacterResponse(BaseModel):
    """Unified response model for character"""
    character_id: str
    name: str
    description: str
    
    # Context
    series_id: Optional[str] = None
    series_title: Optional[str] = None
    
    # Basic attributes
    role: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    
    # Detailed attributes
    background: Optional[str] = None
    personality: Optional[str] = None
    personality_traits: List[str] = []
    
    # Appearance
    appearance: Dict[str, Any] = {}
    appearance_details: Optional[str] = None
    consistency_prompt: Optional[str] = None
    
    # Media
    reference_images: List[str] = []
    
    # Metadata
    created_at: str
    updated_at: str
    
    # Statistics
    total_appearances: Optional[int] = None
    
    class Config:
        from_attributes = True


class CharacterAppearanceResponse(BaseModel):
    """Response model for character appearance record"""
    appearance_id: str
    character_id: str
    job_id: str
    shot_idx: int
    scene_idx: Optional[int] = None
    image_path: str
    timestamp: str


class ConsistencyReport(BaseModel):
    """Character consistency analysis report"""
    character_id: str
    character_name: str
    total_appearances: int
    consistency_score: float
    issues: List[Dict[str, Any]] = []
    recommendations: List[str] = []


# ============================================================================
# Character CRUD Endpoints
# ============================================================================

@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(
    request: CharacterCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new character (standalone or series-scoped)
    
    **Features:**
    - Standalone characters (no series_id)
    - Series-scoped characters (with series_id)
    - Database persistence
    - Dual storage (DB + in-memory service for legacy compatibility)
    """
    try:
        # Validate series if provided
        if request.series_id:
            series = db.query(Series).filter(Series.id == request.series_id).first()
            if not series:
                raise HTTPException(status_code=404, detail="Series not found")
        
        # Create database character
        character_id = str(uuid.uuid4())
        
        # Merge personality fields
        personality_text = request.personality or ""
        if request.personality_traits:
            personality_text += "\n" + ", ".join(request.personality_traits)
        
        # Merge appearance fields
        appearance_text = request.appearance_details or ""
        if request.appearance:
            appearance_text += "\n" + str(request.appearance)
        
        db_character = DBCharacter(
            id=character_id,
            series_id=request.series_id,
            name=request.name,
            role=request.role,
            description=request.description,
            background=request.background,
            personality=personality_text,
            appearance_details=appearance_text,
            consistency_prompt=request.consistency_prompt,
            reference_images=[]
        )
        
        db.add(db_character)
        db.commit()
        db.refresh(db_character)
        
        # Also create in character_service for legacy compatibility
        try:
            character_service.create_character(
                name=request.name,
                description=request.description,
                appearance=request.appearance,
                personality_traits=request.personality_traits or [],
                age=request.age,
                gender=request.gender,
                role=request.role
            )
        except Exception as e:
            print(f"[WARNING] Failed to sync to character_service: {e}")
        
        # Build response
        series_title = None
        if request.series_id and series:
            series_title = series.title
        
        return CharacterResponse(
            character_id=db_character.id,
            name=db_character.name,
            description=db_character.description,
            series_id=db_character.series_id,
            series_title=series_title,
            role=db_character.role,
            age=request.age,
            gender=request.gender,
            background=db_character.background,
            personality=db_character.personality,
            personality_traits=request.personality_traits or [],
            appearance=request.appearance or {},
            appearance_details=db_character.appearance_details,
            consistency_prompt=db_character.consistency_prompt,
            reference_images=db_character.reference_images or [],
            created_at=db_character.created_at.isoformat(),
            updated_at=db_character.updated_at.isoformat(),
            total_appearances=0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create character: {str(e)}")


@router.get("", response_model=List[CharacterResponse])
async def list_characters(
    series_id: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all characters with optional filtering
    
    **Query Parameters:**
    - `series_id`: Filter by series (optional)
    - `role`: Filter by role (optional)
    - `limit`: Max results (default: 50)
    - `offset`: Pagination offset (default: 0)
    """
    try:
        query = db.query(DBCharacter)
        
        # Apply filters
        if series_id:
            query = query.filter(DBCharacter.series_id == series_id)
        if role:
            query = query.filter(DBCharacter.role == role)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        characters = query.offset(offset).limit(limit).all()
        
        # Build responses
        responses = []
        for char in characters:
            # Get series title if applicable
            series_title = None
            if char.series_id:
                series = db.query(Series).filter(Series.id == char.series_id).first()
                if series:
                    series_title = series.title
            
            # Count appearances
            appearances_count = db.query(CharacterShot).filter(
                CharacterShot.character_id == char.id
            ).count()
            
            responses.append(CharacterResponse(
                character_id=char.id,
                name=char.name,
                description=char.description,
                series_id=char.series_id,
                series_title=series_title,
                role=char.role,
                background=char.background,
                personality=char.personality,
                personality_traits=[],
                appearance={},
                appearance_details=char.appearance_details,
                consistency_prompt=char.consistency_prompt,
                reference_images=char.reference_images or [],
                created_at=char.created_at.isoformat(),
                updated_at=char.updated_at.isoformat(),
                total_appearances=appearances_count
            ))
        
        return responses
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list characters: {str(e)}")


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Get character details by ID"""
    try:
        character = db.query(DBCharacter).filter(DBCharacter.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Get series title if applicable
        series_title = None
        if character.series_id:
            series = db.query(Series).filter(Series.id == character.series_id).first()
            if series:
                series_title = series.title
        
        # Count appearances
        appearances_count = db.query(CharacterShot).filter(
            CharacterShot.character_id == character_id
        ).count()
        
        return CharacterResponse(
            character_id=character.id,
            name=character.name,
            description=character.description,
            series_id=character.series_id,
            series_title=series_title,
            role=character.role,
            background=character.background,
            personality=character.personality,
            personality_traits=[],
            appearance={},
            appearance_details=character.appearance_details,
            consistency_prompt=character.consistency_prompt,
            reference_images=character.reference_images or [],
            created_at=character.created_at.isoformat(),
            updated_at=character.updated_at.isoformat(),
            total_appearances=appearances_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get character: {str(e)}")


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    request: CharacterUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update character details"""
    try:
        character = db.query(DBCharacter).filter(DBCharacter.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        
        # Handle personality_traits merge
        if "personality_traits" in update_data:
            traits = update_data.pop("personality_traits")
            if traits:
                character.personality = (character.personality or "") + "\n" + ", ".join(traits)
        
        # Handle appearance merge
        if "appearance" in update_data:
            appearance = update_data.pop("appearance")
            if appearance:
                character.appearance_details = (character.appearance_details or "") + "\n" + str(appearance)
        
        # Apply remaining updates
        for field, value in update_data.items():
            if hasattr(character, field):
                setattr(character, field, value)
        
        character.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(character)
        
        # Get series title
        series_title = None
        if character.series_id:
            series = db.query(Series).filter(Series.id == character.series_id).first()
            if series:
                series_title = series.title
        
        # Count appearances
        appearances_count = db.query(CharacterShot).filter(
            CharacterShot.character_id == character_id
        ).count()
        
        return CharacterResponse(
            character_id=character.id,
            name=character.name,
            description=character.description,
            series_id=character.series_id,
            series_title=series_title,
            role=character.role,
            background=character.background,
            personality=character.personality,
            personality_traits=[],
            appearance={},
            appearance_details=character.appearance_details,
            consistency_prompt=character.consistency_prompt,
            reference_images=character.reference_images or [],
            created_at=character.created_at.isoformat(),
            updated_at=character.updated_at.isoformat(),
            total_appearances=appearances_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update character: {str(e)}")


@router.delete("/{character_id}", status_code=204)
async def delete_character(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Delete a character"""
    try:
        character = db.query(DBCharacter).filter(DBCharacter.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        db.delete(character)
        db.commit()
        
        # Also delete from character_service for legacy compatibility
        try:
            character_service.delete_character(character_id)
        except Exception as e:
            print(f"[WARNING] Failed to sync deletion to character_service: {e}")
        
        return {"message": "Character deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete character: {str(e)}")


# ============================================================================
# Reference Image Management
# ============================================================================

@router.post("/{character_id}/reference", status_code=201)
async def upload_reference_image(
    character_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a reference image for a character"""
    try:
        character = db.query(DBCharacter).filter(DBCharacter.id == character_id).first()
        
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
            "total_images": len(character.reference_images)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upload reference image: {str(e)}")


@router.get("/{character_id}/reference")
async def list_reference_images(
    character_id: str,
    db: Session = Depends(get_db)
):
    """List all reference images for a character"""
    try:
        character = db.query(DBCharacter).filter(DBCharacter.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return {
            "character_id": character_id,
            "character_name": character.name,
            "reference_images": character.reference_images or [],
            "total_images": len(character.reference_images or [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reference images: {str(e)}")


# ============================================================================
# Character Appearance Tracking
# ============================================================================

@router.post("/{character_id}/appearances", status_code=201)
async def record_character_appearance(
    character_id: str,
    job_id: str,
    shot_idx: int,
    image_path: str,
    scene_idx: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Record a character appearance in a shot"""
    try:
        character = db.query(DBCharacter).filter(DBCharacter.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Record in character_service for legacy compatibility
        try:
            appearance = character_service.record_appearance(
                character_id=character_id,
                job_id=job_id,
                shot_idx=shot_idx,
                image_path=image_path,
                scene_idx=scene_idx
            )
            
            return {
                "message": "Appearance recorded successfully",
                "appearance": appearance.model_dump()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to record appearance: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record appearance: {str(e)}")


@router.get("/{character_id}/appearances")
async def get_character_appearances(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Get all appearances of a character"""
    try:
        character = db.query(DBCharacter).filter(DBCharacter.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Get from character_service
        try:
            appearances = character_service.get_character_appearances(character_id)
            
            return {
                "character_id": character_id,
                "character_name": character.name,
                "total_appearances": len(appearances),
                "appearances": [app.model_dump() for app in appearances]
            }
        except Exception as e:
            # Fallback to empty list if service fails
            return {
                "character_id": character_id,
                "character_name": character.name,
                "total_appearances": 0,
                "appearances": []
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get appearances: {str(e)}")


@router.get("/{character_id}/consistency")
async def check_character_consistency(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Check consistency of a character across all appearances"""
    try:
        character = db.query(DBCharacter).filter(DBCharacter.id == character_id).first()
        
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Get consistency report from character_service
        try:
            report = character_service.check_consistency(character_id)
            
            if "error" in report:
                raise HTTPException(status_code=404, detail=report["error"])
            
            return report
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to check consistency: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check consistency: {str(e)}")


# ============================================================================
# Character Extraction from Script
# ============================================================================

class ScriptExtractionRequest(BaseModel):
    """Request model for character extraction from script"""
    script: str = Field(..., description="Script text to extract characters from", min_length=1)


@router.post("/extract")
async def extract_characters_from_script(
    request: ScriptExtractionRequest
):
    """
    Extract characters from a script using AI
    
    **Note:** This creates character suggestions but does not persist them.
    Use the POST /api/v1/characters endpoint to create actual characters.
    """
    try:
        characters = character_service.extract_characters_from_script(request.script)
        
        return {
            "total_characters": len(characters),
            "characters": [
                {
                    "name": char.name,
                    "description": char.description,
                    "appearance": char.appearance.model_dump() if char.appearance else {},
                    "personality_traits": char.personality_traits,
                    "suggested_role": char.role
                }
                for char in characters
            ],
            "message": "Characters extracted successfully. Use POST /api/v1/characters to create them."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract characters: {str(e)}")


# ============================================================================
# Job-Character Relationship
# ============================================================================

@router.get("/jobs/{job_id}/characters")
async def get_job_characters(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get all characters that appear in a job"""
    try:
        # Get from character_service
        characters = character_service.get_job_characters(job_id)
        
        return {
            "job_id": job_id,
            "total_characters": len(characters),
            "characters": [
                {
                    "character_id": char.character_id,
                    "name": char.name,
                    "description": char.description,
                    "appearance": char.appearance.model_dump() if char.appearance else {}
                }
                for char in characters
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job characters: {str(e)}")


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check for character management system"""
    return {
        "status": "healthy",
        "service": "unified_character_management",
        "features": [
            "Character CRUD operations",
            "Series-scoped characters",
            "Standalone characters",
            "Reference image management",
            "Appearance tracking",
            "Consistency checking",
            "Script character extraction",
            "Database persistence",
            "Legacy service compatibility"
        ],
        "deprecated_endpoints": [
            "POST /api/v1/seko/series/{series_id}/characters",
            "GET /api/v1/seko/series/{series_id}/characters",
            "GET /api/v1/seko/characters/{character_id}",
            "PUT /api/v1/seko/characters/{character_id}",
            "DELETE /api/v1/seko/characters/{character_id}",
            "POST /api/v1/seko/characters/{character_id}/reference"
        ]
    }