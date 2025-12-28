"""
Scene Image Generator Agent
Generates concept art images for scenes based on descriptions
"""

import logging
from typing import Optional
from tenacity import retry, stop_after_attempt
from interfaces.image_output import ImageOutput
from utils.retry import after_func


class SceneImageGenerator:
    """
    Agent for generating scene concept art images
    Uses the same image generation API as character portraits
    """
    
    def __init__(self, image_generator):
        """
        Initialize scene image generator
        
        Args:
            image_generator: Image generation tool (e.g., ImageGeneratorDoubaoSeedreamYunwuAPI)
        """
        self.image_generator = image_generator
    
    @retry(stop=stop_after_attempt(3), after=after_func, reraise=True)
    async def generate_scene_image(
        self,
        scene_name: str,
        scene_description: str,
        atmosphere: str,
        style: str = "写实电影感",
        size: Optional[str] = None
    ) -> ImageOutput:
        """
        Generate a concept art image for a scene
        
        Args:
            scene_name: Name of the scene
            scene_description: Detailed description of the scene
            atmosphere: Atmosphere/mood (e.g., "紧张", "温馨", "神秘")
            style: Visual style
            size: Image size (default: 1024x1024)
        
        Returns:
            ImageOutput with the generated scene image
        """
        # Build comprehensive prompt for scene generation
        prompt = self._build_scene_prompt(
            scene_name=scene_name,
            description=scene_description,
            atmosphere=atmosphere,
            style=style
        )
        
        logging.info(f"Generating scene image for: {scene_name}")
        logging.debug(f"Scene prompt: {prompt}")
        
        try:
            image_output = await self.image_generator.generate_single_image(
                prompt=prompt,
                size=size or "1024x1024"
            )
            return image_output
        except Exception as e:
            logging.error(f"Failed to generate scene image for {scene_name}: {e}")
            raise
    
    def _build_scene_prompt(
        self,
        scene_name: str,
        description: str,
        atmosphere: str,
        style: str
    ) -> str:
        """
        Build a detailed prompt for scene image generation
        
        Args:
            scene_name: Name of the scene
            description: Scene description
            atmosphere: Atmosphere/mood
            style: Visual style
        
        Returns:
            Formatted prompt string
        """
        # Map Chinese atmosphere terms to English descriptors
        atmosphere_map = {
            "紧张": "tense, dramatic lighting, high contrast",
            "温馨": "warm, cozy, soft lighting, inviting",
            "悲伤": "melancholic, muted colors, somber mood",
            "神秘": "mysterious, atmospheric fog, dramatic shadows",
            "平静": "peaceful, serene, balanced composition",
            "欢快": "cheerful, bright colors, energetic",
            "恐怖": "horror, dark, ominous atmosphere",
            "浪漫": "romantic, soft focus, dreamy lighting",
            "激烈": "intense, dynamic, high energy",
            "宁静": "tranquil, calm, harmonious"
        }
        
        atmosphere_desc = atmosphere_map.get(atmosphere, atmosphere)
        
        # Build the prompt
        prompt = f"""Create a cinematic concept art image for a scene titled "{scene_name}".

Scene Description: {description}

Atmosphere: {atmosphere_desc}
Visual Style: {style}

Requirements:
- High quality cinematic composition
- Detailed environment and lighting
- Professional concept art quality
- No characters or people in the scene
- Focus on the environment and setting
- Establish the mood through lighting and composition"""
        
        return prompt
    
    @retry(stop=stop_after_attempt(3), after=after_func, reraise=True)
    async def generate_location_image(
        self,
        location_name: str,
        location_type: str,
        time_of_day: str = "day",
        weather: str = "clear",
        style: str = "写实电影感"
    ) -> ImageOutput:
        """
        Generate an image for a specific location
        
        Args:
            location_name: Name of the location (e.g., "办公室", "公园")
            location_type: Type of location (e.g., "indoor", "outdoor")
            time_of_day: Time of day (e.g., "morning", "day", "evening", "night")
            weather: Weather condition (e.g., "clear", "rainy", "foggy")
            style: Visual style
        
        Returns:
            ImageOutput with the generated location image
        """
        prompt = f"""Create a cinematic establishing shot of a {location_name}.

Location Type: {location_type}
Time of Day: {time_of_day}
Weather: {weather}
Visual Style: {style}

Requirements:
- Professional cinematography
- Detailed environment
- Atmospheric lighting appropriate for time of day
- No people or characters
- Cinematic composition"""
        
        logging.info(f"Generating location image for: {location_name}")
        
        try:
            image_output = await self.image_generator.generate_single_image(
                prompt=prompt,
                size="1024x1024"
            )
            return image_output
        except Exception as e:
            logging.error(f"Failed to generate location image for {location_name}: {e}")
            raise