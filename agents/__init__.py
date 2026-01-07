# Legacy agents (require langchain)
try:
    from .screenwriter import Screenwriter
    from .storyboard_artist import StoryboardArtist
    from .camera_image_generator import CameraImageGenerator
    from .character_extractor import CharacterExtractor
    from .character_portraits_generator import CharacterPortraitsGenerator
    from .reference_image_selector import ReferenceImageSelector
    LEGACY_AGENTS_AVAILABLE = True
except ImportError:
    LEGACY_AGENTS_AVAILABLE = False

# A2A Protocol agents (new architecture)
from .base_a2a_agent import BaseA2AAgent, SimpleA2AAgent, create_simple_agent
from .screenwriter_a2a import ScreenwriterA2AAgent, create_screenwriter_agent

__all__ = [
    # A2A Protocol
    "BaseA2AAgent",
    "SimpleA2AAgent",
    "create_simple_agent",
    "ScreenwriterA2AAgent",
    "create_screenwriter_agent",
]

# Add legacy agents if available
if LEGACY_AGENTS_AVAILABLE:
    __all__.extend([
        "Screenwriter",
        "StoryboardArtist",
        "CameraImageGenerator",
        "CharacterExtractor",
        "CharacterPortraitsGenerator",
        "ReferenceImageSelector",
    ])