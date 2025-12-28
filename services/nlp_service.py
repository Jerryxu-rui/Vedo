"""
Natural Language Processing Service for ViMax
Handles intent detection, command parsing, and context management for conversational AI
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass


class Intent(str, Enum):
    """User intent types"""
    CREATE_VIDEO = "create_video"
    EDIT_SHOT = "edit_shot"
    QUERY_STATUS = "query_status"
    HELP = "help"
    UNKNOWN = "unknown"


class EditAction(str, Enum):
    """Types of editing actions"""
    CHANGE_VISUAL = "change_visual"
    CHANGE_MOTION = "change_motion"
    CHANGE_AUDIO = "change_audio"
    CHANGE_CAMERA = "change_camera"
    CHANGE_LIGHTING = "change_lighting"
    CHANGE_CHARACTER = "change_character"
    CHANGE_BACKGROUND = "change_background"


@dataclass
class ParsedCommand:
    """Parsed natural language command"""
    intent: Intent
    action: Optional[EditAction] = None
    target_shot: Optional[int] = None
    target_scene: Optional[int] = None
    parameters: Dict[str, Any] = None
    confidence: float = 0.0
    raw_text: str = ""
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class NLPService:
    """Natural Language Processing service for conversational AI"""
    
    def __init__(self):
        # Intent detection patterns
        self.intent_patterns = {
            Intent.CREATE_VIDEO: [
                r"create.*video",
                r"generate.*video",
                r"make.*video",
                r"new video",
                r"start.*project",
            ],
            Intent.EDIT_SHOT: [
                r"edit.*shot",
                r"change.*shot",
                r"modify.*shot",
                r"update.*shot",
                r"make.*brighter",
                r"make.*darker",
                r"change.*color",
                r"add.*background",
                r"change.*character",
            ],
            Intent.QUERY_STATUS: [
                r"status",
                r"progress",
                r"how.*doing",
                r"is.*ready",
                r"when.*complete",
                r"show.*video",
            ],
            Intent.HELP: [
                r"help",
                r"what can you do",
                r"how.*work",
                r"tutorial",
                r"guide",
            ],
        }
        
        # Edit action patterns
        self.edit_patterns = {
            EditAction.CHANGE_VISUAL: [
                r"change.*appearance",
                r"modify.*look",
                r"update.*visual",
                r"make.*look",
            ],
            EditAction.CHANGE_MOTION: [
                r"change.*movement",
                r"modify.*motion",
                r"make.*move",
                r"add.*animation",
            ],
            EditAction.CHANGE_AUDIO: [
                r"change.*sound",
                r"modify.*audio",
                r"add.*music",
                r"change.*voice",
            ],
            EditAction.CHANGE_CAMERA: [
                r"change.*camera",
                r"modify.*angle",
                r"zoom.*in",
                r"zoom.*out",
                r"pan.*left",
                r"pan.*right",
            ],
            EditAction.CHANGE_LIGHTING: [
                r"make.*brighter",
                r"make.*darker",
                r"change.*lighting",
                r"add.*light",
                r"more.*light",
                r"less.*light",
            ],
            EditAction.CHANGE_CHARACTER: [
                r"change.*character",
                r"modify.*character",
                r"change.*clothing",
                r"change.*hair",
                r"change.*expression",
            ],
            EditAction.CHANGE_BACKGROUND: [
                r"change.*background",
                r"modify.*background",
                r"add.*background",
                r"change.*setting",
                r"change.*location",
            ],
        }
        
        # Shot/scene reference patterns
        self.shot_patterns = [
            r"shot\s+(\d+)",
            r"the\s+(\d+)(?:st|nd|rd|th)\s+shot",
            r"shot\s+number\s+(\d+)",
            r"first\s+shot",
            r"last\s+shot",
        ]
        
        self.scene_patterns = [
            r"scene\s+(\d+)",
            r"the\s+(\d+)(?:st|nd|rd|th)\s+scene",
            r"scene\s+number\s+(\d+)",
        ]
    
    def detect_intent(self, text: str) -> Tuple[Intent, float]:
        """Detect user intent from text
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (intent, confidence_score)
        """
        text_lower = text.lower()
        best_intent = Intent.UNKNOWN
        best_confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    confidence = 0.8  # Base confidence for pattern match
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence
        
        return best_intent, best_confidence
    
    def detect_edit_action(self, text: str) -> Optional[EditAction]:
        """Detect specific editing action from text
        
        Args:
            text: User input text
            
        Returns:
            EditAction or None
        """
        text_lower = text.lower()
        
        for action, patterns in self.edit_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return action
        
        return None
    
    def extract_shot_reference(self, text: str) -> Optional[int]:
        """Extract shot number from text
        
        Args:
            text: User input text
            
        Returns:
            Shot number or None
        """
        text_lower = text.lower()
        
        # Check for "first shot"
        if re.search(r"first\s+shot", text_lower):
            return 0
        
        # Check for numbered shots
        for pattern in self.shot_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except (IndexError, ValueError):
                    continue
        
        return None
    
    def extract_scene_reference(self, text: str) -> Optional[int]:
        """Extract scene number from text
        
        Args:
            text: User input text
            
        Returns:
            Scene number or None
        """
        text_lower = text.lower()
        
        for pattern in self.scene_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except (IndexError, ValueError):
                    continue
        
        return None
    
    def extract_parameters(self, text: str, action: Optional[EditAction]) -> Dict[str, Any]:
        """Extract parameters for editing actions
        
        Args:
            text: User input text
            action: Detected edit action
            
        Returns:
            Dictionary of parameters
        """
        params = {}
        text_lower = text.lower()
        
        if action == EditAction.CHANGE_LIGHTING:
            # Extract brightness level
            if "brighter" in text_lower or "more light" in text_lower:
                params["brightness"] = "increase"
            elif "darker" in text_lower or "less light" in text_lower:
                params["brightness"] = "decrease"
        
        elif action == EditAction.CHANGE_CAMERA:
            # Extract camera movement
            if "zoom in" in text_lower:
                params["camera_movement"] = "zoom_in"
            elif "zoom out" in text_lower:
                params["camera_movement"] = "zoom_out"
            elif "pan left" in text_lower:
                params["camera_movement"] = "pan_left"
            elif "pan right" in text_lower:
                params["camera_movement"] = "pan_right"
        
        elif action == EditAction.CHANGE_CHARACTER:
            # Extract character attributes
            if "clothing" in text_lower or "clothes" in text_lower:
                params["attribute"] = "clothing"
            elif "hair" in text_lower:
                params["attribute"] = "hair"
            elif "expression" in text_lower or "face" in text_lower:
                params["attribute"] = "expression"
        
        # Extract color mentions
        colors = ["red", "blue", "green", "yellow", "black", "white", "purple", "orange", "pink", "brown"]
        for color in colors:
            if color in text_lower:
                params["color"] = color
                break
        
        return params
    
    def parse_command(self, text: str, context: Optional[Dict[str, Any]] = None) -> ParsedCommand:
        """Parse natural language command into structured format
        
        Args:
            text: User input text
            context: Optional context (current job, shot, etc.)
            
        Returns:
            ParsedCommand object
        """
        # Detect intent
        intent, confidence = self.detect_intent(text)
        
        # Initialize command
        command = ParsedCommand(
            intent=intent,
            confidence=confidence,
            raw_text=text
        )
        
        # If editing intent, extract more details
        if intent == Intent.EDIT_SHOT:
            command.action = self.detect_edit_action(text)
            command.target_shot = self.extract_shot_reference(text)
            command.target_scene = self.extract_scene_reference(text)
            command.parameters = self.extract_parameters(text, command.action)
            
            # Use context if no explicit shot reference
            if command.target_shot is None and context:
                command.target_shot = context.get("current_shot")
        
        return command
    
    def generate_edit_prompt(self, command: ParsedCommand, original_prompt: str) -> str:
        """Generate modified prompt based on natural language command
        
        Args:
            command: Parsed command
            original_prompt: Original shot prompt
            
        Returns:
            Modified prompt
        """
        if not command.action or not command.parameters:
            return original_prompt
        
        modified_prompt = original_prompt
        
        if command.action == EditAction.CHANGE_LIGHTING:
            if command.parameters.get("brightness") == "increase":
                modified_prompt += ", brighter lighting, well-lit, increased brightness"
            elif command.parameters.get("brightness") == "decrease":
                modified_prompt += ", darker lighting, dim, reduced brightness"
        
        elif command.action == EditAction.CHANGE_BACKGROUND:
            if "color" in command.parameters:
                color = command.parameters["color"]
                modified_prompt += f", {color} background"
        
        elif command.action == EditAction.CHANGE_CHARACTER:
            if command.parameters.get("attribute") == "clothing":
                if "color" in command.parameters:
                    color = command.parameters["color"]
                    modified_prompt += f", wearing {color} clothing"
            elif command.parameters.get("attribute") == "hair":
                if "color" in command.parameters:
                    color = command.parameters["color"]
                    modified_prompt += f", {color} hair"
        
        elif command.action == EditAction.CHANGE_CAMERA:
            movement = command.parameters.get("camera_movement")
            if movement:
                modified_prompt += f", camera {movement.replace('_', ' ')}"
        
        return modified_prompt
    
    def generate_suggestions(self, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate context-aware suggestions for user
        
        Args:
            context: Optional context (current job, shot, etc.)
            
        Returns:
            List of suggested commands
        """
        suggestions = []
        
        if not context or not context.get("current_job"):
            # No active job - suggest creation
            suggestions = [
                "Create a video about a person doing yoga",
                "Generate a video from my script",
                "Make a cartoon-style video",
                "Start a new video project",
            ]
        else:
            # Active job - suggest editing
            suggestions = [
                "Make the first shot brighter",
                "Change the background to blue",
                "Add more movement to shot 2",
                "Change character's clothing to red",
                "Show me the video status",
            ]
            
            if context.get("current_shot") is not None:
                shot_num = context["current_shot"]
                suggestions.insert(0, f"Edit shot {shot_num}")
        
        return suggestions


# Global instance
nlp_service = NLPService()