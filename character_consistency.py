"""
Character Consistency Engine
Handles character prompt injection and consistency maintenance across shots
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database_models import Character, CharacterShot, Shot, Scene, Episode


class CharacterConsistencyEngine:
    """
    Engine for maintaining character consistency across shots
    Injects character descriptions and reference images into generation prompts
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_shot_characters(self, shot_id: str) -> List[Dict]:
        """
        Get all characters assigned to a shot with their details
        
        Returns:
            List of character dictionaries with role_in_shot
        """
        assignments = self.db.query(CharacterShot).filter(
            CharacterShot.shot_id == shot_id
        ).all()
        
        characters = []
        for assignment in assignments:
            character = self.db.query(Character).filter(
                Character.id == assignment.character_id
            ).first()
            
            if character:
                characters.append({
                    'character': character,
                    'role_in_shot': assignment.role_in_shot,
                    'assignment_id': assignment.id
                })
        
        return characters
    
    def build_character_prompt(
        self, 
        character: Character, 
        role_in_shot: str = "main"
    ) -> str:
        """
        Build a character description prompt for generation
        
        Args:
            character: Character model instance
            role_in_shot: Role of character in this shot (main/supporting/background)
        
        Returns:
            Formatted character prompt string
        """
        prompt_parts = []
        
        # Character name and role
        if character.name:
            prompt_parts.append(f"角色：{character.name}")
        
        if character.role:
            prompt_parts.append(f"定位：{character.role}")
        
        # Appearance details (most important for consistency)
        if character.appearance_details:
            prompt_parts.append(f"外貌：{character.appearance_details}")
        
        # Use custom consistency prompt if available
        if character.consistency_prompt:
            prompt_parts.append(character.consistency_prompt)
        else:
            # Build from description
            if character.description:
                prompt_parts.append(character.description)
        
        # Adjust detail level based on role in shot
        if role_in_shot == "background":
            # Less detail for background characters
            prompt_parts = prompt_parts[:2]  # Just name and basic appearance
        
        return "，".join(prompt_parts)
    
    def inject_character_consistency(
        self,
        shot_id: str,
        base_prompt: str,
        style_preset: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Inject character consistency information into a shot generation prompt
        
        Args:
            shot_id: ID of the shot
            base_prompt: Base visual description prompt
            style_preset: Optional style preset (e.g., "都市韩漫风格")
        
        Returns:
            Dictionary with enhanced prompt and reference images
        """
        # Get characters in this shot
        shot_characters = self.get_shot_characters(shot_id)
        
        if not shot_characters:
            # No characters assigned, return base prompt
            return {
                'prompt': base_prompt,
                'reference_images': [],
                'characters': []
            }
        
        # Build character prompts
        character_prompts = []
        reference_images = []
        character_info = []
        
        for char_data in shot_characters:
            character = char_data['character']
            role = char_data['role_in_shot']
            
            # Build character prompt
            char_prompt = self.build_character_prompt(character, role)
            character_prompts.append(char_prompt)
            
            # Collect reference images
            if character.reference_images:
                reference_images.extend(character.reference_images)
            
            # Store character info
            character_info.append({
                'id': character.id,
                'name': character.name,
                'role_in_shot': role
            })
        
        # Combine prompts
        enhanced_prompt_parts = []
        
        # Add style preset first
        if style_preset:
            enhanced_prompt_parts.append(style_preset)
        
        # Add character descriptions
        if character_prompts:
            enhanced_prompt_parts.append("人物：" + "；".join(character_prompts))
        
        # Add base scene/shot description
        enhanced_prompt_parts.append(base_prompt)
        
        enhanced_prompt = "，".join(enhanced_prompt_parts)
        
        return {
            'prompt': enhanced_prompt,
            'reference_images': reference_images,
            'characters': character_info,
            'character_count': len(shot_characters)
        }
    
    def get_series_style_preset(self, shot_id: str) -> Optional[str]:
        """
        Get the style preset from the series for a given shot
        
        Args:
            shot_id: ID of the shot
        
        Returns:
            Style preset string or None
        """
        try:
            # Navigate: Shot -> Scene -> Episode -> Series
            shot = self.db.query(Shot).filter(Shot.id == shot_id).first()
            if not shot:
                return None
            
            scene = self.db.query(Scene).filter(Scene.id == shot.scene_id).first()
            if not scene:
                return None
            
            episode = self.db.query(Episode).filter(Episode.id == scene.episode_id).first()
            if not episode:
                return None
            
            from database_models import Series
            series = self.db.query(Series).filter(Series.id == episode.series_id).first()
            if not series:
                return None
            
            return series.style_preset
        
        except Exception:
            return None
    
    def generate_shot_with_consistency(
        self,
        shot_id: str,
        image_generator,
        video_generator=None
    ) -> Dict[str, str]:
        """
        Generate a shot with character consistency
        
        Args:
            shot_id: ID of the shot to generate
            image_generator: Image generation function/service
            video_generator: Optional video generation function/service
        
        Returns:
            Dictionary with generated URLs
        """
        # Get shot details
        shot = self.db.query(Shot).filter(Shot.id == shot_id).first()
        if not shot:
            raise ValueError(f"Shot {shot_id} not found")
        
        # Get style preset
        style_preset = self.get_series_style_preset(shot_id)
        
        # Build enhanced prompt with character consistency
        consistency_data = self.inject_character_consistency(
            shot_id=shot_id,
            base_prompt=shot.visual_desc or "",
            style_preset=style_preset
        )
        
        # Generate frame image
        frame_url = image_generator.generate(
            prompt=consistency_data['prompt'],
            reference_images=consistency_data['reference_images']
        )
        
        # Update shot with generated frame
        shot.frame_url = frame_url
        shot.status = 'generating_video' if video_generator else 'completed'
        self.db.commit()
        
        result = {
            'frame_url': frame_url,
            'prompt_used': consistency_data['prompt'],
            'characters': consistency_data['characters']
        }
        
        # Generate video if generator provided
        if video_generator and frame_url:
            video_url = video_generator.generate(
                prompt=consistency_data['prompt'],
                first_frame=frame_url,
                camera_movement=shot.camera_movement
            )
            
            shot.video_url = video_url
            shot.status = 'completed'
            self.db.commit()
            
            result['video_url'] = video_url
        
        return result
    
    def batch_assign_characters(
        self,
        shot_ids: List[str],
        character_id: str,
        role_in_shot: str = "main"
    ) -> int:
        """
        Assign a character to multiple shots at once
        
        Args:
            shot_ids: List of shot IDs
            character_id: Character to assign
            role_in_shot: Role in shots
        
        Returns:
            Number of assignments created
        """
        count = 0
        
        for shot_id in shot_ids:
            # Check if already assigned
            existing = self.db.query(CharacterShot).filter(
                CharacterShot.shot_id == shot_id,
                CharacterShot.character_id == character_id
            ).first()
            
            if not existing:
                import uuid
                assignment = CharacterShot(
                    id=str(uuid.uuid4()),
                    character_id=character_id,
                    shot_id=shot_id,
                    role_in_shot=role_in_shot
                )
                self.db.add(assignment)
                count += 1
        
        self.db.commit()
        return count
    
    def analyze_character_consistency(
        self,
        character_id: str,
        episode_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Analyze character consistency across shots
        
        Args:
            character_id: Character to analyze
            episode_id: Optional episode to limit analysis
        
        Returns:
            Consistency analysis report
        """
        # Get all shots with this character
        query = self.db.query(CharacterShot).filter(
            CharacterShot.character_id == character_id
        )
        
        assignments = query.all()
        
        # Group by episode
        episodes = {}
        total_shots = len(assignments)
        
        for assignment in assignments:
            shot = self.db.query(Shot).filter(Shot.id == assignment.shot_id).first()
            if not shot:
                continue
            
            scene = self.db.query(Scene).filter(Scene.id == shot.scene_id).first()
            if not scene:
                continue
            
            ep_id = scene.episode_id
            
            if episode_id and ep_id != episode_id:
                continue
            
            if ep_id not in episodes:
                episodes[ep_id] = {
                    'episode_id': ep_id,
                    'shot_count': 0,
                    'roles': {}
                }
            
            episodes[ep_id]['shot_count'] += 1
            
            role = assignment.role_in_shot
            episodes[ep_id]['roles'][role] = episodes[ep_id]['roles'].get(role, 0) + 1
        
        return {
            'character_id': character_id,
            'total_shots': total_shots,
            'episodes': list(episodes.values()),
            'episode_count': len(episodes)
        }


# Helper functions for easy integration

def enhance_shot_prompt(
    db: Session,
    shot_id: str,
    base_prompt: str
) -> str:
    """
    Quick helper to enhance a shot prompt with character consistency
    
    Args:
        db: Database session
        shot_id: Shot ID
        base_prompt: Base visual description
    
    Returns:
        Enhanced prompt string
    """
    engine = CharacterConsistencyEngine(db)
    result = engine.inject_character_consistency(shot_id, base_prompt)
    return result['prompt']


def get_character_reference_images(
    db: Session,
    shot_id: str
) -> List[str]:
    """
    Get all character reference images for a shot
    
    Args:
        db: Database session
        shot_id: Shot ID
    
    Returns:
        List of reference image URLs
    """
    engine = CharacterConsistencyEngine(db)
    result = engine.inject_character_consistency(shot_id, "")
    return result['reference_images']