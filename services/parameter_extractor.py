"""
Parameter Extractor Service
Extracts structured video generation parameters from natural language using LLM

Part of the Conversational Orchestrator system
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json
import re

from services.chat_service import ChatService


class VideoParameters(BaseModel):
    """Structured video generation parameters"""
    theme: str = Field(description="Main theme/topic of the video")
    style: Optional[str] = Field(None, description="Visual style (cinematic, anime, realistic, etc.)")
    characters: List[Dict[str, str]] = Field(default_factory=list, description="Character descriptions")
    scenes: List[Dict[str, str]] = Field(default_factory=list, description="Scene descriptions")
    duration: Optional[int] = Field(None, description="Video duration in seconds")
    mood: Optional[str] = Field(None, description="Mood/atmosphere (happy, sad, suspenseful, etc.)")
    special_requirements: List[str] = Field(default_factory=list, description="Special requirements or constraints")
    narration: Optional[str] = Field(None, description="Narration or voice-over text")
    music_style: Optional[str] = Field(None, description="Music style preference")
    aspect_ratio: Optional[str] = Field(None, description="Aspect ratio (16:9, 9:16, 1:1, etc.)")
    quality: Optional[str] = Field(None, description="Quality level (standard, high, ultra)")


class ParameterExtractor:
    """
    Extracts video generation parameters from natural language
    
    Uses LLM for intelligent extraction with structured output
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.chat_service = ChatService(db)
    
    async def extract(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> VideoParameters:
        """
        Extract all video parameters from user input
        
        Args:
            user_input: User's natural language request
            context: Additional context (conversation history, etc.)
        
        Returns:
            VideoParameters object with extracted values
        """
        
        try:
            # Use LLM for comprehensive extraction
            extracted = await self._llm_extract_parameters(user_input, context)
        except Exception as e:
            print(f"[ParameterExtractor] LLM extraction failed in extract(): {e}")
            # Fallback to basic extraction
            extracted = self._fallback_extraction(user_input)
        
        # Validate and clean extracted parameters
        validated = self._validate_parameters(extracted)
        
        return VideoParameters(**validated)
    
    async def _llm_extract_parameters(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to extract parameters with high accuracy
        """
        
        system_prompt = """You are a parameter extraction system for video generation.

Your task: Extract video generation parameters from user requests.

Extract these parameters:
1. theme: Main topic/subject (REQUIRED)
2. style: Visual style (cinematic, anime, realistic, artistic, sci-fi, fantasy, etc.)
3. characters: List of character descriptions with details
4. scenes: List of scene descriptions with details
5. duration: Video duration in seconds (extract from "X minutes", "X seconds", "X:XX" format)
6. mood: Atmosphere/mood (happy, sad, suspenseful, peaceful, exciting, dramatic, etc.)
7. special_requirements: Any special requests (lighting, effects, transitions, etc.)
8. narration: Any narration or voice-over text mentioned
9. music_style: Music preference (epic, calm, upbeat, classical, etc.)
10. aspect_ratio: Aspect ratio if mentioned (16:9, 9:16, 1:1, 4:3)
11. quality: Quality level if mentioned (standard, high, ultra, 4K, HD)

Return ONLY a JSON object with this structure:
{
  "theme": "string (REQUIRED)",
  "style": "string or null",
  "characters": [
    {"name": "string", "description": "string", "role": "protagonist/antagonist/supporting"}
  ],
  "scenes": [
    {"name": "string", "description": "string", "atmosphere": "string"}
  ],
  "duration": number or null (in seconds),
  "mood": "string or null",
  "special_requirements": ["string"],
  "narration": "string or null",
  "music_style": "string or null",
  "aspect_ratio": "string or null",
  "quality": "string or null"
}

Examples:

Input: "Create a 2-minute cinematic video about three friends exploring an ancient temple with dramatic lighting"
Output:
{
  "theme": "three friends exploring an ancient temple",
  "style": "cinematic",
  "characters": [
    {"name": "Friend 1", "description": "Explorer", "role": "protagonist"},
    {"name": "Friend 2", "description": "Explorer", "role": "supporting"},
    {"name": "Friend 3", "description": "Explorer", "role": "supporting"}
  ],
  "scenes": [
    {"name": "Ancient Temple", "description": "Mysterious ancient temple interior", "atmosphere": "dramatic"}
  ],
  "duration": 120,
  "mood": "suspenseful",
  "special_requirements": ["dramatic lighting"],
  "narration": null,
  "music_style": null,
  "aspect_ratio": null,
  "quality": null
}

Input: "Make a short anime-style video about a magical girl fighting evil"
Output:
{
  "theme": "magical girl fighting evil",
  "style": "anime",
  "characters": [
    {"name": "Magical Girl", "description": "Heroic magical girl with powers", "role": "protagonist"},
    {"name": "Evil Force", "description": "Antagonistic evil entity", "role": "antagonist"}
  ],
  "scenes": [
    {"name": "Battle Scene", "description": "Epic battle between good and evil", "atmosphere": "intense"}
  ],
  "duration": null,
  "mood": "exciting",
  "special_requirements": [],
  "narration": null,
  "music_style": null,
  "aspect_ratio": null,
  "quality": null
}

Be thorough and extract as much detail as possible from the user's request."""

        user_prompt = f"""User request: "{user_input}"

Context: {json.dumps(context, ensure_ascii=False) if context else "No additional context"}

Extract all video generation parameters:"""
        
        # Create temporary thread for extraction
        temp_thread = await self.chat_service.create_thread(
            user_id="system",
            llm_model="gemini-2.0-flash-exp",  # Fast model for extraction
            title="Parameter Extraction",
            system_prompt=system_prompt
        )
        
        try:
            # Get LLM response
            response = await self.chat_service.chat(
                thread_id=temp_thread.id,
                user_message=user_prompt,
                temperature=0.2,  # Low temperature for consistency
                max_tokens=1000
            )
            
            # Parse JSON response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                raise ValueError("No JSON found in LLM response")
        
        except Exception as e:
            print(f"[ParameterExtractor] LLM extraction failed: {e}")
            # Fallback to basic extraction
            return self._fallback_extraction(user_input)
        
        finally:
            # Clean up temporary thread
            from database_models import ConversationThread
            self.db.query(ConversationThread).filter(
                ConversationThread.id == temp_thread.id
            ).delete()
            self.db.commit()
    
    def _fallback_extraction(self, user_input: str) -> Dict[str, Any]:
        """
        Fallback extraction using simple pattern matching
        """
        
        return {
            "theme": user_input[:100],  # Use input as theme
            "style": self._extract_style_fallback(user_input),
            "characters": [],
            "scenes": [],
            "duration": self._extract_duration_fallback(user_input),
            "mood": self._extract_mood_fallback(user_input),
            "special_requirements": [],
            "narration": None,
            "music_style": None,
            "aspect_ratio": None,
            "quality": None
        }
    
    def _extract_style_fallback(self, text: str) -> Optional[str]:
        """Fallback style extraction"""
        style_keywords = {
            "cinematic": ["cinematic", "film", "movie"],
            "anime": ["anime", "animated"],
            "realistic": ["realistic", "real"],
        }
        
        text_lower = text.lower()
        for style, keywords in style_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return style
        return None
    
    def _extract_duration_fallback(self, text: str) -> Optional[int]:
        """Fallback duration extraction"""
        patterns = [
            (r'(\d+)\s*min', 60),
            (r'(\d+)\s*sec', 1),
            (r'(\d+):(\d+)', None),
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, text.lower())
            if match:
                if multiplier:
                    return int(match.group(1)) * multiplier
                else:
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    return minutes * 60 + seconds
        return None
    
    def _extract_mood_fallback(self, text: str) -> Optional[str]:
        """Fallback mood extraction"""
        mood_keywords = {
            "happy": ["happy", "joyful"],
            "sad": ["sad", "melancholy"],
            "suspenseful": ["suspenseful", "dramatic"],
        }
        
        text_lower = text.lower()
        for mood, keywords in mood_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return mood
        return None
    
    def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean extracted parameters
        
        Ensures:
        - Theme is not empty
        - Duration is positive
        - Lists are properly formatted
        - Enums are valid values
        """
        
        validated = params.copy()
        
        # Ensure theme exists
        if not validated.get("theme"):
            validated["theme"] = "Untitled Video"
        
        # Validate duration
        if validated.get("duration"):
            duration = validated["duration"]
            if isinstance(duration, (int, float)) and duration > 0:
                validated["duration"] = int(duration)
            else:
                validated["duration"] = None
        
        # Ensure lists are lists
        for list_field in ["characters", "scenes", "special_requirements"]:
            if not isinstance(validated.get(list_field), list):
                validated[list_field] = []
        
        # Validate style enum
        valid_styles = ["cinematic", "anime", "realistic", "artistic", "sci-fi", "fantasy", "documentary"]
        if validated.get("style") and validated["style"].lower() not in valid_styles:
            # Keep custom style but log it
            print(f"[ParameterExtractor] Custom style: {validated['style']}")
        
        # Validate mood enum
        valid_moods = ["happy", "sad", "suspenseful", "peaceful", "exciting", "dramatic", "mysterious"]
        if validated.get("mood") and validated["mood"].lower() not in valid_moods:
            print(f"[ParameterExtractor] Custom mood: {validated['mood']}")
        
        # Validate aspect ratio
        valid_ratios = ["16:9", "9:16", "1:1", "4:3", "21:9"]
        if validated.get("aspect_ratio") and validated["aspect_ratio"] not in valid_ratios:
            print(f"[ParameterExtractor] Custom aspect ratio: {validated['aspect_ratio']}")
        
        return validated
    
    async def extract_theme(self, text: str) -> str:
        """Extract main theme/topic"""
        params = await self.extract(text)
        return params.theme
    
    async def extract_style(self, text: str) -> Optional[str]:
        """Extract visual style"""
        params = await self.extract(text)
        return params.style
    
    async def extract_characters(self, text: str) -> List[Dict[str, str]]:
        """Extract character descriptions"""
        params = await self.extract(text)
        return params.characters
    
    async def extract_scenes(self, text: str) -> List[Dict[str, str]]:
        """Extract scene descriptions"""
        params = await self.extract(text)
        return params.scenes
    
    async def extract_duration(self, text: str) -> Optional[int]:
        """Extract video duration in seconds"""
        params = await self.extract(text)
        return params.duration
    
    async def extract_mood(self, text: str) -> Optional[str]:
        """Extract mood/atmosphere"""
        params = await self.extract(text)
        return params.mood
    
    def estimate_scene_count(self, parameters: VideoParameters) -> int:
        """
        Estimate number of scenes based on parameters
        
        Rules:
        - Explicit scenes: Use count
        - Duration-based: 1 scene per 20-30 seconds
        - Character-based: 1 scene per character interaction
        - Default: 3 scenes
        """
        
        # If scenes explicitly mentioned
        if parameters.scenes:
            return len(parameters.scenes)
        
        # Estimate from duration
        if parameters.duration:
            # Assume 20-30 seconds per scene
            estimated = parameters.duration // 25
            return max(1, min(estimated, 10))  # Cap at 10 scenes
        
        # Estimate from characters
        if parameters.characters:
            # More characters = more scenes for interactions
            return min(len(parameters.characters) + 1, 5)
        
        # Default
        return 3
    
    def estimate_shot_count(self, parameters: VideoParameters) -> int:
        """
        Estimate number of shots/frames
        
        Rules:
        - 3-5 shots per scene
        - More for complex/dramatic content
        - Fewer for simple content
        """
        
        scene_count = self.estimate_scene_count(parameters)
        
        # Base shots per scene
        shots_per_scene = 4
        
        # Adjust based on mood
        if parameters.mood in ["dramatic", "suspenseful", "exciting"]:
            shots_per_scene = 5  # More cuts for drama
        elif parameters.mood in ["peaceful", "calm"]:
            shots_per_scene = 3  # Fewer cuts for calm
        
        return scene_count * shots_per_scene