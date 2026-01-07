"""
Intent Analyzer Service
Analyzes user input to determine intent and extract parameters for video generation

Part of the Conversational Orchestrator system
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.orm import Session
import re
import json

from services.chat_service import ChatService


class IntentType(str, Enum):
    """Types of user intents"""
    CHAT = "chat"                          # General conversation, questions
    VIDEO_GENERATION = "video_generation"  # Create new video
    MODIFICATION = "modification"          # Modify existing content
    REVIEW = "review"                      # Review/approve content
    EXPORT = "export"                      # Download/export results
    UNKNOWN = "unknown"                    # Cannot determine intent


class ComplexityLevel(str, Enum):
    """Complexity levels for video generation"""
    SIMPLE = "simple"      # 1-2 agents: Basic video, single scene
    MEDIUM = "medium"      # 3-5 agents: Standard video with characters/scenes
    COMPLEX = "complex"    # 6+ agents: Multi-scene, multiple characters, special requirements


class Intent(BaseModel):
    """Structured intent representation"""
    type: IntentType
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    complexity: Optional[ComplexityLevel] = None
    required_agents: List[str] = Field(default_factory=list)
    reasoning: str = Field(default="", description="Why this intent was chosen")


class IntentAnalyzer:
    """
    Analyzes user input to determine intent and extract parameters
    
    Uses a three-layer approach:
    1. Quick rule-based detection (>0.9 confidence)
    2. LLM-based classification (>0.7 confidence)
    3. Contextual analysis (fallback)
    """
    
    # Keywords for quick rule-based detection
    VIDEO_KEYWORDS = [
        "create", "make", "generate", "build", "produce",
        "video", "film", "movie", "clip", "footage",
        "创建", "制作", "生成", "视频", "影片", "短片"
    ]
    
    CHAT_KEYWORDS = [
        "what", "how", "why", "when", "where", "who",
        "help", "explain", "tell me", "show me", "tell",
        "can you", "do you", "are you", "?",
        "什么", "怎么", "如何", "为什么", "帮助", "解释", "你能"
    ]
    
    MODIFICATION_KEYWORDS = [
        "change", "modify", "edit", "adjust", "update",
        "make it", "darker", "brighter", "longer", "shorter",
        "修改", "编辑", "调整", "更新", "改变"
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self.chat_service = ChatService(db)
    
    async def analyze(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> Intent:
        """
        Analyze user input and return structured intent
        
        Args:
            user_input: User's message
            context: Conversation context (history, current state, etc.)
        
        Returns:
            Intent object with type, confidence, and parameters
        """
        
        if not user_input or not user_input.strip():
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="Empty input"
            )
        
        context = context or {}
        
        # Layer 1: Quick rule-based detection
        quick_intent = self._quick_rule_based_detection(user_input, context)
        if quick_intent.confidence > 0.9:
            return quick_intent
        
        # Layer 2: LLM-based classification
        try:
            llm_intent = await self._llm_based_classification(user_input, context)
            if llm_intent.confidence > 0.7:
                return llm_intent
        except Exception as e:
            print(f"[IntentAnalyzer] LLM classification failed: {e}")
        
        # Layer 3: Contextual analysis (fallback)
        return self._contextual_analysis(user_input, context, quick_intent)
    
    def _quick_rule_based_detection(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Intent:
        """
        Quick rule-based detection using keywords
        
        Returns intent with confidence > 0.9 if clear match found
        """
        
        text_lower = user_input.lower()
        
        # Check for video generation keywords
        video_score = sum(1 for kw in self.VIDEO_KEYWORDS if kw in text_lower)
        chat_score = sum(1 for kw in self.CHAT_KEYWORDS if kw in text_lower)
        mod_score = sum(1 for kw in self.MODIFICATION_KEYWORDS if kw in text_lower)
        
        # Strong video generation signal (needs at least 2 keywords and more than chat)
        if video_score >= 2 and video_score > chat_score:
            return Intent(
                type=IntentType.VIDEO_GENERATION,
                confidence=0.95,
                reasoning=f"Strong video generation keywords detected ({video_score} matches)"
            )
        
        # Strong chat signal (needs at least 1 keyword, or question mark)
        # Questions are almost always chat
        if "?" in text_lower or (chat_score >= 1 and video_score < 2):
            return Intent(
                type=IntentType.CHAT,
                confidence=0.95,
                reasoning=f"Chat/question detected ({chat_score} matches, has_question={'?' in text_lower})"
            )
        
        # Modification signal (requires existing content in context)
        if mod_score >= 1 and context.get("has_existing_content"):
            return Intent(
                type=IntentType.MODIFICATION,
                confidence=0.92,
                reasoning=f"Modification keywords with existing content"
            )
        
        # No strong signal
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=0.5,
            reasoning="No clear keyword match"
        )
    
    async def _llm_based_classification(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Intent:
        """
        Use LLM to classify intent with high accuracy
        
        Returns intent with confidence > 0.7 if successful
        """
        
        # Build classification prompt
        system_prompt = """You are an intent classification system for a video generation assistant.

Your task: Classify user intent into one of these categories:
1. "chat" - User wants to talk, ask questions, get help, or understand the system
2. "video_generation" - User wants to create/generate/make a new video
3. "modification" - User wants to modify/edit/change existing content
4. "review" - User wants to review/check/approve generated content
5. "export" - User wants to download/save/export results

Return ONLY a JSON object with this exact format:
{
  "intent": "chat" | "video_generation" | "modification" | "review" | "export",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation"
}

Examples:
- "What can you do?" → {"intent": "chat", "confidence": 0.95, "reasoning": "Question about capabilities"}
- "Create a video about space" → {"intent": "video_generation", "confidence": 0.98, "reasoning": "Clear video creation request"}
- "Make it darker" → {"intent": "modification", "confidence": 0.90, "reasoning": "Modification request"}
"""
        
        user_prompt = f"""User message: "{user_input}"

Context: {json.dumps(context, ensure_ascii=False) if context else "No context"}

Classify the intent:"""
        
        # Create temporary thread for classification
        temp_thread = await self.chat_service.create_thread(
            user_id="system",
            llm_model="gemini-2.0-flash-exp",  # Fast model for classification
            title="Intent Classification",
            system_prompt=system_prompt
        )
        
        try:
            # Get LLM response
            response = await self.chat_service.chat(
                thread_id=temp_thread.id,
                user_message=user_prompt,
                temperature=0.1,  # Low temperature for consistency
                max_tokens=150
            )
            
            # Parse JSON response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group())
                
                intent_type = IntentType(result.get("intent", "unknown"))
                confidence = float(result.get("confidence", 0.5))
                reasoning = result.get("reasoning", "LLM classification")
                
                return Intent(
                    type=intent_type,
                    confidence=confidence,
                    reasoning=reasoning
                )
            else:
                raise ValueError("No JSON found in LLM response")
        
        finally:
            # Clean up temporary thread
            self.db.query(self.chat_service.db.query.__self__.__class__).filter(
                self.chat_service.db.query.__self__.__class__.id == temp_thread.id
            ).delete()
            self.db.commit()
        
        # If parsing fails, return low confidence
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=0.5,
            reasoning="Failed to parse LLM response"
        )
    
    def _contextual_analysis(
        self,
        user_input: str,
        context: Dict[str, Any],
        quick_intent: Intent
    ) -> Intent:
        """
        Fallback: Use context to make best guess
        
        Considers:
        - Conversation history
        - Current workflow state
        - Previous intents
        """
        
        # If we have some confidence from quick detection, use it
        if quick_intent.confidence > 0.6:
            return quick_intent
        
        # Check context for clues
        if context.get("last_intent") == IntentType.VIDEO_GENERATION:
            # User might be continuing video generation conversation
            if len(user_input.split()) < 5:  # Short response
                return Intent(
                    type=IntentType.CHAT,
                    confidence=0.7,
                    reasoning="Short response after video generation, likely chat"
                )
        
        # Default to chat for safety (less disruptive than wrong video generation)
        return Intent(
            type=IntentType.CHAT,
            confidence=0.6,
            reasoning="Contextual fallback to chat"
        )
    
    async def extract_parameters(
        self,
        user_input: str,
        intent_type: IntentType
    ) -> Dict[str, Any]:
        """
        Extract video generation parameters from user input
        
        Parameters to extract:
        - theme: Main topic/subject
        - style: Visual style (cinematic, anime, realistic, etc.)
        - characters: List of character descriptions
        - scenes: List of scene descriptions
        - duration: Video duration in seconds
        - mood: Atmosphere/mood (happy, sad, suspenseful, etc.)
        - special_requirements: Any special requests
        
        Args:
            user_input: User's message
            intent_type: Classified intent type
        
        Returns:
            Dictionary of extracted parameters
        """
        
        if intent_type != IntentType.VIDEO_GENERATION:
            return {}
        
        parameters = {}
        
        # Extract duration (look for time mentions)
        duration = self._extract_duration(user_input)
        if duration:
            parameters["duration"] = duration
        
        # Extract character count (look for number mentions)
        characters = self._extract_character_mentions(user_input)
        if characters:
            parameters["characters"] = characters
        
        # Extract theme (main subject)
        theme = self._extract_theme(user_input)
        if theme:
            parameters["theme"] = theme
        
        # Extract style keywords
        style = self._extract_style(user_input)
        if style:
            parameters["style"] = style
        
        # Extract mood keywords
        mood = self._extract_mood(user_input)
        if mood:
            parameters["mood"] = mood
        
        return parameters
    
    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract video duration in seconds"""
        
        # Look for patterns like "2 minutes", "30 seconds", "1:30", "2-minute"
        patterns = [
            (r'(\d+)[-\s]*min', 60),   # "2 minutes" or "2-minute" → 120 seconds
            (r'(\d+)[-\s]*sec', 1),    # "30 seconds" or "30-second" → 30 seconds
            (r'(\d+):(\d+)', None),    # "1:30" → 90 seconds
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, text.lower())
            if match:
                if multiplier:
                    return int(match.group(1)) * multiplier
                else:
                    # Handle mm:ss format
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    return minutes * 60 + seconds
        
        return None
    
    def _extract_character_mentions(self, text: str) -> List[str]:
        """Extract character mentions"""
        
        characters = []
        
        # Look for patterns like "three friends", "2 characters", "hero and villain"
        number_patterns = [
            r'(\d+|one|two|three|four|five)\s+(friend|character|person|people)',
            r'(hero|villain|protagonist|antagonist)',
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        characters.append(" ".join(match))
                    else:
                        characters.append(match)
        
        return characters
    
    def _extract_theme(self, text: str) -> Optional[str]:
        """Extract main theme/topic"""
        
        # Look for "about X", "story of X", "video about X"
        patterns = [
            r'about\s+([^,\.]+)',
            r'story\s+of\s+([^,\.]+)',
            r'video\s+about\s+([^,\.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1).strip()
        
        # Fallback: use the whole input as theme
        return text[:100]  # Limit to 100 chars
    
    def _extract_style(self, text: str) -> Optional[str]:
        """Extract visual style"""
        
        style_keywords = {
            "cinematic": ["cinematic", "film", "movie", "epic"],
            "anime": ["anime", "animated", "cartoon"],
            "realistic": ["realistic", "real", "photorealistic"],
            "artistic": ["artistic", "painterly", "stylized"],
            "sci-fi": ["sci-fi", "science fiction", "futuristic"],
            "fantasy": ["fantasy", "magical", "mystical"],
        }
        
        text_lower = text.lower()
        for style, keywords in style_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return style
        
        return None
    
    def _extract_mood(self, text: str) -> Optional[str]:
        """Extract mood/atmosphere"""
        
        mood_keywords = {
            "happy": ["happy", "joyful", "cheerful", "upbeat"],
            "sad": ["sad", "melancholy", "somber", "tragic"],
            "suspenseful": ["suspenseful", "tense", "thrilling", "dramatic"],
            "peaceful": ["peaceful", "calm", "serene", "tranquil"],
            "exciting": ["exciting", "energetic", "dynamic", "action"],
        }
        
        text_lower = text.lower()
        for mood, keywords in mood_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return mood
        
        return None
    
    def assess_complexity(
        self,
        parameters: Dict[str, Any]
    ) -> ComplexityLevel:
        """
        Assess complexity based on extracted parameters
        
        Scoring:
        - Number of scenes: +2 per scene
        - Number of characters: +3 per character
        - Special requirements: +5 per requirement
        - Duration > 60s: +10
        
        Thresholds:
        - < 10: SIMPLE
        - 10-30: MEDIUM
        - > 30: COMPLEX
        """
        
        score = 0
        
        # Factor 1: Number of scenes
        scenes = parameters.get("scenes", [])
        if isinstance(scenes, list):
            score += len(scenes) * 2
        
        # Factor 2: Number of characters
        characters = parameters.get("characters", [])
        if isinstance(characters, list):
            score += len(characters) * 3
        
        # Factor 3: Special requirements
        special_reqs = parameters.get("special_requirements", [])
        if isinstance(special_reqs, list):
            score += len(special_reqs) * 5
        
        # Factor 4: Duration
        duration = parameters.get("duration", 0)
        if duration > 60:
            score += 10
        
        # Classify based on score
        if score < 10:
            return ComplexityLevel.SIMPLE
        elif score < 30:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.COMPLEX