"""
Character model for managing character consistency across shots and episodes
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class CharacterAppearance(BaseModel):
    """Physical appearance attributes of a character"""
    hair_color: Optional[str] = None
    hair_style: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    height: Optional[str] = None
    build: Optional[str] = None
    clothing: Optional[str] = None
    accessories: Optional[List[str]] = []
    distinctive_features: Optional[List[str]] = []


class Character(BaseModel):
    """Character model with appearance and personality traits"""
    character_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Character name")
    description: str = Field(..., description="Character description")
    appearance: CharacterAppearance = Field(default_factory=CharacterAppearance)
    personality_traits: List[str] = Field(default_factory=list)
    reference_images: List[str] = Field(default_factory=list, description="Paths to reference images")
    voice_profile: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    role: Optional[str] = Field(None, description="Character role (protagonist, antagonist, etc.)")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_prompt(self) -> str:
        """Generate a prompt string for image generation"""
        parts = [self.name]
        
        if self.appearance.hair_color or self.appearance.hair_style:
            hair = []
            if self.appearance.hair_color:
                hair.append(self.appearance.hair_color)
            if self.appearance.hair_style:
                hair.append(self.appearance.hair_style)
            parts.append(f"{' '.join(hair)} hair")
        
        if self.appearance.eye_color:
            parts.append(f"{self.appearance.eye_color} eyes")
        
        if self.appearance.clothing:
            parts.append(f"wearing {self.appearance.clothing}")
        
        if self.appearance.accessories:
            parts.append(f"with {', '.join(self.appearance.accessories)}")
        
        if self.appearance.distinctive_features:
            parts.extend(self.appearance.distinctive_features)
        
        return ", ".join(parts)


class CharacterAppearanceRecord(BaseModel):
    """Record of a character's appearance in a specific shot"""
    appearance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    character_id: str
    job_id: str
    shot_idx: int
    scene_idx: Optional[int] = None
    image_path: str
    verified: bool = False
    consistency_score: Optional[float] = None
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CharacterDatabase:
    """In-memory character database (in production, use a real database)"""
    
    def __init__(self):
        self.characters: Dict[str, Character] = {}
        self.appearances: Dict[str, CharacterAppearanceRecord] = {}
    
    def create_character(self, character: Character) -> Character:
        """Create a new character"""
        self.characters[character.character_id] = character
        return character
    
    def get_character(self, character_id: str) -> Optional[Character]:
        """Get a character by ID"""
        return self.characters.get(character_id)
    
    def list_characters(self, limit: int = 50, offset: int = 0) -> List[Character]:
        """List all characters"""
        all_chars = list(self.characters.values())
        return all_chars[offset:offset + limit]
    
    def update_character(self, character_id: str, updates: Dict[str, Any]) -> Optional[Character]:
        """Update a character"""
        character = self.characters.get(character_id)
        if not character:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(character, key):
                setattr(character, key, value)
        
        character.updated_at = datetime.now().isoformat()
        return character
    
    def delete_character(self, character_id: str) -> bool:
        """Delete a character"""
        if character_id in self.characters:
            del self.characters[character_id]
            # Also delete all appearances
            self.appearances = {
                k: v for k, v in self.appearances.items()
                if v.character_id != character_id
            }
            return True
        return False
    
    def add_appearance(self, appearance: CharacterAppearanceRecord) -> CharacterAppearanceRecord:
        """Record a character appearance"""
        self.appearances[appearance.appearance_id] = appearance
        return appearance
    
    def get_character_appearances(self, character_id: str) -> List[CharacterAppearanceRecord]:
        """Get all appearances of a character"""
        return [
            app for app in self.appearances.values()
            if app.character_id == character_id
        ]
    
    def get_job_characters(self, job_id: str) -> List[str]:
        """Get all character IDs that appear in a job"""
        character_ids = set()
        for app in self.appearances.values():
            if app.job_id == job_id:
                character_ids.add(app.character_id)
        return list(character_ids)


# Global character database instance
character_db = CharacterDatabase()