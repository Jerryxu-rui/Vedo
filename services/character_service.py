"""
Character service for managing character consistency
"""
from typing import List, Optional, Dict, Any
from models.character import Character, CharacterAppearance, CharacterAppearanceRecord, character_db
import os
import json


class CharacterService:
    """Service for character management and consistency checking"""
    
    def __init__(self):
        self.db = character_db
    
    def create_character(
        self,
        name: str,
        description: str,
        appearance: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Character:
        """Create a new character
        
        Args:
            name: Character name
            description: Character description
            appearance: Appearance attributes
            **kwargs: Additional character attributes
            
        Returns:
            Created character
        """
        appearance_obj = CharacterAppearance(**(appearance or {}))
        
        character = Character(
            name=name,
            description=description,
            appearance=appearance_obj,
            **kwargs
        )
        
        return self.db.create_character(character)
    
    def get_character(self, character_id: str) -> Optional[Character]:
        """Get a character by ID"""
        return self.db.get_character(character_id)
    
    def list_characters(self, limit: int = 50, offset: int = 0) -> List[Character]:
        """List all characters"""
        return self.db.list_characters(limit, offset)
    
    def update_character(
        self,
        character_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Character]:
        """Update a character
        
        Args:
            character_id: Character ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated character or None if not found
        """
        return self.db.update_character(character_id, updates)
    
    def delete_character(self, character_id: str) -> bool:
        """Delete a character"""
        return self.db.delete_character(character_id)
    
    def add_reference_image(self, character_id: str, image_path: str) -> Optional[Character]:
        """Add a reference image to a character
        
        Args:
            character_id: Character ID
            image_path: Path to reference image
            
        Returns:
            Updated character or None if not found
        """
        character = self.db.get_character(character_id)
        if not character:
            return None
        
        if image_path not in character.reference_images:
            character.reference_images.append(image_path)
        
        return character
    
    def record_appearance(
        self,
        character_id: str,
        job_id: str,
        shot_idx: int,
        image_path: str,
        scene_idx: Optional[int] = None
    ) -> CharacterAppearanceRecord:
        """Record a character appearance in a shot
        
        Args:
            character_id: Character ID
            job_id: Job ID
            shot_idx: Shot index
            image_path: Path to shot image
            scene_idx: Optional scene index
            
        Returns:
            Appearance record
        """
        appearance = CharacterAppearanceRecord(
            character_id=character_id,
            job_id=job_id,
            shot_idx=shot_idx,
            scene_idx=scene_idx,
            image_path=image_path
        )
        
        return self.db.add_appearance(appearance)
    
    def get_character_appearances(self, character_id: str) -> List[CharacterAppearanceRecord]:
        """Get all appearances of a character"""
        return self.db.get_character_appearances(character_id)
    
    def get_job_characters(self, job_id: str) -> List[Character]:
        """Get all characters that appear in a job
        
        Args:
            job_id: Job ID
            
        Returns:
            List of characters
        """
        character_ids = self.db.get_job_characters(job_id)
        characters = []
        
        for char_id in character_ids:
            character = self.db.get_character(char_id)
            if character:
                characters.append(character)
        
        return characters
    
    def verify_appearance(
        self,
        appearance_id: str,
        verified: bool,
        consistency_score: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Optional[CharacterAppearanceRecord]:
        """Verify a character appearance
        
        Args:
            appearance_id: Appearance ID
            verified: Whether appearance is verified
            consistency_score: Optional consistency score (0-1)
            notes: Optional notes
            
        Returns:
            Updated appearance record or None if not found
        """
        appearance = self.db.appearances.get(appearance_id)
        if not appearance:
            return None
        
        appearance.verified = verified
        if consistency_score is not None:
            appearance.consistency_score = consistency_score
        if notes is not None:
            appearance.notes = notes
        
        return appearance
    
    def check_consistency(self, character_id: str) -> Dict[str, Any]:
        """Check consistency of a character across all appearances
        
        Args:
            character_id: Character ID
            
        Returns:
            Consistency report
        """
        character = self.db.get_character(character_id)
        if not character:
            return {"error": "Character not found"}
        
        appearances = self.db.get_character_appearances(character_id)
        
        total_appearances = len(appearances)
        verified_appearances = sum(1 for app in appearances if app.verified)
        
        # Calculate average consistency score
        scores = [app.consistency_score for app in appearances if app.consistency_score is not None]
        avg_score = sum(scores) / len(scores) if scores else None
        
        # Group by job
        jobs = {}
        for app in appearances:
            if app.job_id not in jobs:
                jobs[app.job_id] = []
            jobs[app.job_id].append(app)
        
        return {
            "character_id": character_id,
            "character_name": character.name,
            "total_appearances": total_appearances,
            "verified_appearances": verified_appearances,
            "average_consistency_score": avg_score,
            "jobs": {job_id: len(apps) for job_id, apps in jobs.items()},
            "needs_review": [
                app.appearance_id for app in appearances
                if not app.verified or (app.consistency_score and app.consistency_score < 0.7)
            ]
        }
    
    def extract_characters_from_script(self, script: str) -> List[Dict[str, str]]:
        """Extract character information from a script
        
        Args:
            script: Script text
            
        Returns:
            List of character dictionaries with name and description
        """
        # Simple extraction - look for character names in uppercase
        # In production, use NLP for better extraction
        characters = []
        lines = script.split('\n')
        
        current_char = None
        for line in lines:
            line = line.strip()
            
            # Look for character names (usually in uppercase)
            if line.isupper() and len(line.split()) <= 3 and len(line) > 2:
                if current_char:
                    characters.append(current_char)
                current_char = {"name": line, "description": ""}
            elif current_char and line.startswith('(') and line.endswith(')'):
                # Character description in parentheses
                current_char["description"] += line[1:-1] + " "
        
        if current_char:
            characters.append(current_char)
        
        return characters
    
    def generate_character_prompt(self, character_id: str, context: Optional[str] = None) -> str:
        """Generate a prompt for character image generation
        
        Args:
            character_id: Character ID
            context: Optional context (scene, action, etc.)
            
        Returns:
            Prompt string
        """
        character = self.db.get_character(character_id)
        if not character:
            return ""
        
        prompt = character.to_prompt()
        
        if context:
            prompt = f"{prompt}, {context}"
        
        return prompt


# Global character service instance
character_service = CharacterService()