"""
LLM-Based Intent Analyzer Service
Pure LLM approach for intent detection using chat models with structured prompts

This replaces the inefficient rule-based keyword matching with intelligent
LLM-based classification that understands context and nuance.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.orm import Session
import json
import re
from functools import lru_cache
import hashlib

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


class ContentValidation(BaseModel):
    """Content validation result"""
    is_valid: bool
    has_subject: bool = False
    has_action: bool = False
    has_context: bool = False
    missing_elements: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    reasoning: str = ""


class Intent(BaseModel):
    """Structured intent representation"""
    type: IntentType
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    complexity: Optional[ComplexityLevel] = None
    required_agents: List[str] = Field(default_factory=list)
    reasoning: str = Field(default="", description="Why this intent was chosen")
    content_validation: Optional[ContentValidation] = None


class LLMIntentAnalyzer:
    """
    Pure LLM-based intent analyzer
    
    Uses chat models with carefully crafted prompts to:
    1. Classify user intent with high accuracy
    2. Validate content quality for video generation
    3. Extract parameters intelligently
    4. Provide helpful suggestions
    
    No keyword matching, no regex patterns - just intelligent LLM analysis.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.chat_service = ChatService(db)
        self._cache = {}  # Simple in-memory cache
    
    async def analyze(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> Intent:
        """
        Analyze user input using LLM
        
        Args:
            user_input: User's message
            context: Conversation context (history, current state, etc.)
        
        Returns:
            Intent object with type, confidence, parameters, and validation
        
        Raises:
            ValueError: If LLM API keys are not configured
        """
        
        if not user_input or not user_input.strip():
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning="Empty input"
            )
        
        context = context or {}
        
        # Check cache first
        cache_key = self._get_cache_key(user_input, context)
        if cache_key in self._cache:
            print(f"[LLMIntentAnalyzer] Cache hit for: {user_input[:50]}...")
            return self._cache[cache_key]
        
        try:
            # Use LLM for intelligent classification
            intent = await self._llm_classify_and_validate(user_input, context)
            
            # Cache result
            self._cache[cache_key] = intent
            
            # Limit cache size
            if len(self._cache) > 100:
                # Remove oldest entries
                keys_to_remove = list(self._cache.keys())[:20]
                for key in keys_to_remove:
                    del self._cache[key]
            
            return intent
        
        except Exception as e:
            print(f"[LLMIntentAnalyzer] LLM classification failed: {e}")
            # Re-raise with clear error message for API key configuration
            raise ValueError(
                f"Intent classification requires LLM API keys. "
                f"Please set DEEPSEEK_API_KEY environment variable for DeepSeek model. "
                f"Error: {str(e)}"
            )
    
    async def _llm_classify_and_validate(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Intent:
        """
        Use LLM to classify intent AND validate content quality
        
        This is the core of the new approach - a single LLM call that:
        1. Classifies the intent
        2. Validates content quality (for video generation)
        3. Extracts parameters
        4. Provides suggestions
        """
        
        # Build comprehensive prompt
        system_prompt = self._build_classification_prompt()
        user_prompt = self._build_user_prompt(user_input, context)
        
        # Create temporary thread for classification
        temp_thread = await self.chat_service.create_thread(
            user_id="system_intent_analyzer",
            llm_model="deepseek-chat",  # Fast and reliable model for classification
            title="Intent Classification",
            system_prompt=system_prompt
        )
        
        try:
            # Get LLM response
            response = await self.chat_service.chat(
                thread_id=temp_thread.id,
                user_message=user_prompt,
                temperature=0.1,  # Low temperature for consistency
                max_tokens=500
            )
            
            # Parse structured response
            intent = self._parse_llm_response(response, user_input)
            
            return intent
        
        finally:
            # Clean up temporary thread
            try:
                from database_models import ConversationThread
                self.db.query(ConversationThread).filter(
                    ConversationThread.id == temp_thread.id
                ).delete()
                self.db.commit()
            except Exception as e:
                print(f"[LLMIntentAnalyzer] Warning: Failed to cleanup thread: {e}")
    
    def _build_classification_prompt(self) -> str:
        """Build system prompt for intent classification"""
        
        return """You are an intelligent intent classification system for a video generation assistant called ViMax.

Your task is to analyze user messages and determine:
1. **Intent Type**: What does the user want to do?
2. **Content Quality**: Is the input specific enough for video generation?
3. **Parameters**: What details can be extracted?
4. **Suggestions**: How can we help the user?

**Intent Categories:**

1. **chat** - User wants to:
   - Ask questions about the system
   - Get help or explanations
   - Have a conversation
   - Understand capabilities
   - Express general interest without specific details

2. **video_generation** - User wants to create a video AND provides:
   - Specific subject/topic (what the video is about)
   - Action or story (what happens)
   - Context or details (setting, characters, style)
   - Example: "Create a sci-fi video about space exploration with astronauts"

3. **modification** - User wants to change existing content:
   - Adjust visual style, timing, or effects
   - Requires existing content in context

4. **review** - User wants to check/approve generated content

5. **export** - User wants to download/save results

**Critical Distinction for Video Generation:**

❌ **Intent-Only (classify as CHAT)**:
- "创建精彩的视频内容" (create wonderful video content)
- "I want to make a video"
- "Generate something cool"
- "制作视频" (make video)
→ These express INTENT but lack CONTENT. User needs guidance.

✅ **Intent + Content (classify as VIDEO_GENERATION)**:
- "创建一个关于太空探索的科幻视频" (create a sci-fi video about space exploration)
- "Make a video about a cat's adventure in the city"
- "生成一个浪漫爱情故事，两个人在巴黎相遇" (generate a romantic love story, two people meet in Paris)
→ These have SUBJECT + ACTION/CONTEXT. Ready for generation.

**Content Validation for Video Generation:**

Check if the input has:
- ✅ **Subject**: What/who is the video about?
- ✅ **Action**: What happens? What's the story?
- ✅ **Context**: Setting, style, mood, or details?

If missing 2+ elements → classify as CHAT and provide guidance.

**Response Format:**

Return ONLY a JSON object (no markdown, no explanation):

```json
{
  "intent": "chat" | "video_generation" | "modification" | "review" | "export",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation of classification",
  "content_validation": {
    "is_valid": true/false,
    "has_subject": true/false,
    "has_action": true/false,
    "has_context": true/false,
    "missing_elements": ["subject", "action", "context"],
    "suggestions": ["Add specific topic", "Describe what happens", "Include setting/style"]
  },
  "parameters": {
    "theme": "extracted theme",
    "style": "visual style if mentioned",
    "duration": seconds if mentioned,
    "mood": "mood/atmosphere if mentioned",
    "characters": ["character descriptions"],
    "scenes": ["scene descriptions"]
  }
}
```

**Examples:**

Input: "创建精彩的视频内容"
→ Intent: chat (intent-only, no content)
→ Validation: is_valid=false, missing subject/action/context
→ Suggestions: ["请描述视频的具体主题", "告诉我视频讲什么故事", "添加场景或风格描述"]

Input: "Create a sci-fi video about astronauts exploring Mars"
→ Intent: video_generation
→ Validation: is_valid=true, has all elements
→ Parameters: theme="astronauts exploring Mars", style="sci-fi"

Input: "What can you do?"
→ Intent: chat (question about capabilities)
→ Confidence: 0.95

Be precise, intelligent, and helpful in your analysis."""
    
    def _build_user_prompt(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> str:
        """Build user prompt with context"""
        
        context_str = ""
        if context:
            # Include relevant context
            if context.get("has_existing_content"):
                context_str += "\n- User has existing content (episode_id present)"
            if context.get("last_intent"):
                context_str += f"\n- Previous intent: {context.get('last_intent')}"
            if context.get("message_count", 0) > 0:
                context_str += f"\n- Conversation history: {context.get('message_count')} messages"
        
        prompt = f"""Analyze this user message:

**User Input:** "{user_input}"

**Context:**{context_str if context_str else " (new conversation)"}

Classify the intent and validate content quality. Return JSON only."""
        
        return prompt
    
    def _parse_llm_response(self, response: str, user_input: str) -> Intent:
        """Parse LLM response into Intent object"""
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            # First try to extract from ```json ... ``` blocks
            json_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
            if json_block_match:
                json_str = json_block_match.group(1)
            else:
                # Fallback to finding raw JSON
                json_match = re.search(r'\{[\s\S]*\}', response)
                if not json_match:
                    raise ValueError("No JSON found in response")
                json_str = json_match.group()
            
            result = json.loads(json_str)
            
            # Parse intent type
            intent_type = IntentType(result.get("intent", "unknown"))
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "LLM classification")
            
            # Parse content validation
            content_validation = None
            if "content_validation" in result:
                cv = result["content_validation"]
                content_validation = ContentValidation(
                    is_valid=cv.get("is_valid", False),
                    has_subject=cv.get("has_subject", False),
                    has_action=cv.get("has_action", False),
                    has_context=cv.get("has_context", False),
                    missing_elements=cv.get("missing_elements", []),
                    suggestions=cv.get("suggestions", []),
                    reasoning=cv.get("reasoning", "")
                )
            
            # Parse parameters
            parameters = result.get("parameters", {})
            
            # If video_generation but content invalid, downgrade to chat
            if intent_type == IntentType.VIDEO_GENERATION:
                if content_validation and not content_validation.is_valid:
                    print(f"[LLMIntentAnalyzer] Downgrading to CHAT: content validation failed")
                    intent_type = IntentType.CHAT
                    reasoning = "Video idea needs more details"
                    # Keep validation info in parameters for response
                    parameters["needs_clarification"] = True
                    parameters["validation"] = content_validation.dict()
            
            return Intent(
                type=intent_type,
                confidence=confidence,
                reasoning=reasoning,
                parameters=parameters,
                content_validation=content_validation
            )
        
        except Exception as e:
            print(f"[LLMIntentAnalyzer] Parse error: {e}")
            print(f"[LLMIntentAnalyzer] Response was: {response[:200]}...")
            # Re-raise with clear error message
            raise ValueError(
                f"Failed to parse LLM response. Please set DEEPSEEK_API_KEY environment variable for DeepSeek model. "
                f"Error: {e}"
            )
    
    def _get_cache_key(self, user_input: str, context: Dict[str, Any]) -> str:
        """Generate cache key for input + context"""
        
        # Create hash of input + relevant context
        context_str = json.dumps({
            "has_existing_content": context.get("has_existing_content", False),
            "last_intent": context.get("last_intent"),
        }, sort_keys=True)
        
        combined = f"{user_input}|{context_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    async def extract_parameters(
        self,
        user_input: str,
        intent_type: IntentType
    ) -> Dict[str, Any]:
        """
        Extract video generation parameters using LLM
        
        This is now integrated into the main analyze() call,
        but kept for backward compatibility.
        """
        
        if intent_type != IntentType.VIDEO_GENERATION:
            return {}
        
        # Parameters are already extracted in analyze()
        # This method is kept for API compatibility
        intent = await self.analyze(user_input)
        return intent.parameters
    
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