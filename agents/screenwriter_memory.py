"""
Memory-Enhanced Screenwriter Agent

Extends the original Screenwriter with memory capabilities:
- Learns from past successful story patterns
- Remembers user preferences for style and genre
- Improves over time based on feedback
- Uses past experiences to generate better stories
"""

import logging
from typing import List, Optional, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import asyncio

from agents.memory_augmented_agent import MemoryAugmentedAgent, MemoryConfig
from agents.screenwriter import (
    system_prompt_template_develop_story,
    human_prompt_template_develop_story,
    system_prompt_template_write_script_based_on_story,
    human_prompt_template_write_script_based_on_story,
)

logger = logging.getLogger(__name__)


class ScreenwriterMemory(MemoryAugmentedAgent):
    """
    Memory-enhanced screenwriter agent
    
    Capabilities:
    - Remembers successful story patterns
    - Learns user preferences (genre, style, themes)
    - Improves story quality over time
    - Adapts to user feedback
    """
    
    def __init__(
        self,
        chat_model,
        fallback_chat_model: Optional[Any] = None,
        memory_config: Optional[MemoryConfig] = None
    ):
        """
        Initialize memory-enhanced screenwriter
        
        Args:
            chat_model: Primary LLM model
            fallback_chat_model: Fallback LLM model
            memory_config: Memory configuration
        """
        # Initialize memory capabilities
        config = memory_config or MemoryConfig.default()
        super().__init__(
            agent_name="screenwriter",
            enable_memory=config.enable_memory,
            max_memory_context=config.max_memory_context,
            min_relevance_score=config.min_relevance_score
        )
        
        self.chat_model = chat_model
        self.fallback_chat_model = fallback_chat_model
        self.memory_config = config
        
        logger.info(f"[ScreenwriterMemory] Initialized with memory_enabled={self.enable_memory}")
    
    async def develop_story(
        self,
        idea: str,
        user_requirement: Optional[str] = None,
        user_id: Optional[str] = None,
        episode_id: Optional[str] = None
    ) -> str:
        """
        Develop story from idea with memory enhancement
        
        Args:
            idea: Story idea
            user_requirement: Optional user requirements
            user_id: User ID for memory retrieval
            episode_id: Episode ID for memory recording
        
        Returns:
            Developed story
        """
        logger.info(f"[ScreenwriterMemory] develop_story called")
        logger.info(f"  - Idea length: {len(idea)} chars")
        logger.info(f"  - User ID: {user_id}")
        logger.info(f"  - Episode ID: {episode_id}")
        logger.info(f"  - Memory enabled: {self.enable_memory}")
        
        # Build context for memory retrieval
        context = {
            'task': 'develop_story',
            'idea': idea[:200],  # First 200 chars
            'user_requirement': user_requirement
        }
        
        # Get user preferences if available
        user_prefs = {}
        if user_id and self.enable_memory:
            user_prefs = self.get_user_preferences(user_id)
            logger.info(f"[ScreenwriterMemory] Retrieved user preferences: {list(user_prefs.keys())}")
        
        # Augment system prompt with memory context
        system_prompt = system_prompt_template_develop_story
        
        if user_id and self.memory_config.augment_prompts:
            system_prompt = self.augment_prompt_with_memory(
                base_prompt=system_prompt,
                user_id=user_id,
                context=context
            )
            logger.info(f"[ScreenwriterMemory] Prompt augmented with memory context")
        
        # Add user preferences to requirements if available
        enhanced_requirement = user_requirement or ""
        if user_prefs:
            pref_text = self._format_preferences_for_prompt(user_prefs)
            if pref_text:
                enhanced_requirement = f"{enhanced_requirement}\n\n{pref_text}".strip()
                logger.info(f"[ScreenwriterMemory] Added user preferences to requirements")
        
        # Prepare messages
        messages = [
            ("system", system_prompt),
            ("human", human_prompt_template_develop_story.format(
                idea=idea,
                user_requirement=enhanced_requirement
            )),
        ]
        
        # Call LLM with retry logic
        story = await self._call_llm_with_retry(messages)
        
        # Record decision if memory enabled
        if user_id and episode_id and self.memory_config.record_decisions:
            self.record_decision(
                episode_id=episode_id,
                user_id=user_id,
                decision_context={
                    'task': 'develop_story',
                    'idea_length': len(idea),
                    'has_requirements': bool(user_requirement),
                    'used_memory': self.enable_memory,
                    'used_preferences': bool(user_prefs)
                },
                outcome={
                    'success': True,
                    'story_length': len(story)
                },
                quality_score=None  # Will be set based on user feedback
            )
            logger.info(f"[ScreenwriterMemory] Decision recorded for episode {episode_id}")
        
        return story
    
    async def write_script_based_on_story(
        self,
        story: str,
        user_requirement: Optional[str] = None,
        user_id: Optional[str] = None,
        episode_id: Optional[str] = None
    ) -> List[str]:
        """
        Write script based on story with memory enhancement
        
        Args:
            story: Story text
            user_requirement: Optional user requirements
            user_id: User ID for memory retrieval
            episode_id: Episode ID for memory recording
        
        Returns:
            List of scene scripts
        """
        logger.info(f"[ScreenwriterMemory] write_script_based_on_story called")
        logger.info(f"  - Story length: {len(story)} chars")
        logger.info(f"  - User ID: {user_id}")
        logger.info(f"  - Episode ID: {episode_id}")
        
        # Build context
        context = {
            'task': 'write_script',
            'story_length': len(story),
            'user_requirement': user_requirement
        }
        
        # Get user preferences
        user_prefs = {}
        if user_id and self.enable_memory:
            user_prefs = self.get_user_preferences(user_id)
        
        # Prepare parser
        class WriteScriptBasedOnStoryResponse(BaseModel):
            script: List[str] = Field(
                ...,
                description="The script based on the story. Each element is a scene"
            )
        
        parser = PydanticOutputParser(pydantic_object=WriteScriptBasedOnStoryResponse)
        format_instructions = parser.get_format_instructions()
        
        # Augment system prompt if memory enabled
        system_prompt = system_prompt_template_write_script_based_on_story.format(
            format_instructions=format_instructions
        )
        
        if user_id and self.memory_config.augment_prompts:
            system_prompt = self.augment_prompt_with_memory(
                base_prompt=system_prompt,
                user_id=user_id,
                context=context
            )
        
        # Prepare messages
        messages = [
            ("system", system_prompt),
            ("human", human_prompt_template_write_script_based_on_story.format(
                story=story,
                user_requirement=user_requirement or ""
            )),
        ]
        
        # Call LLM
        response = await self._call_llm_with_retry(messages)
        parsed_response = parser.parse(response)
        script = parsed_response.script
        
        # Record decision
        if user_id and episode_id and self.memory_config.record_decisions:
            self.record_decision(
                episode_id=episode_id,
                user_id=user_id,
                decision_context={
                    'task': 'write_script',
                    'story_length': len(story),
                    'used_memory': self.enable_memory
                },
                outcome={
                    'success': True,
                    'scene_count': len(script)
                },
                quality_score=None
            )
        
        return script
    
    async def _call_llm_with_retry(
        self,
        messages: List[tuple],
        max_retries: int = 3,
        base_delay: int = 2
    ) -> str:
        """
        Call LLM with retry logic and fallback
        
        Args:
            messages: Messages to send to LLM
            max_retries: Maximum retry attempts
            base_delay: Base delay for exponential backoff
        
        Returns:
            LLM response content
        """
        from openai import RateLimitError
        
        # Try primary model
        for attempt in range(max_retries):
            try:
                logger.info(f"[ScreenwriterMemory] LLM call attempt {attempt + 1}/{max_retries}")
                response = await self.chat_model.ainvoke(messages)
                
                if hasattr(response, 'content'):
                    logger.info(f"[ScreenwriterMemory] LLM response received ({len(response.content)} chars)")
                    return response.content
                else:
                    raise AttributeError(f"LLM response has no 'content' attribute")
                    
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"[ScreenwriterMemory] Rate limit hit, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Try fallback
                    if self.fallback_chat_model:
                        logger.info(f"[ScreenwriterMemory] Switching to fallback model...")
                        break
                    else:
                        raise
        
        # Try fallback model
        if self.fallback_chat_model:
            try:
                logger.info(f"[ScreenwriterMemory] Using fallback model")
                response = await self.fallback_chat_model.ainvoke(messages)
                
                if hasattr(response, 'content'):
                    logger.info(f"[ScreenwriterMemory] Fallback response received")
                    return response.content
                else:
                    raise AttributeError(f"Fallback response has no 'content' attribute")
                    
            except Exception as e:
                logger.error(f"[ScreenwriterMemory] Fallback model failed: {e}")
                raise Exception(f"Both primary and fallback models failed")
        
        raise Exception("Failed to generate response after all retries")
    
    def _format_preferences_for_prompt(self, preferences: Dict[str, Any]) -> str:
        """Format user preferences for inclusion in prompt"""
        if not preferences:
            return ""
        
        pref_lines = ["User Preferences (learned from past interactions):"]
        
        for key, value in preferences.items():
            if isinstance(value, (str, int, float)):
                pref_lines.append(f"- {key}: {value}")
            elif isinstance(value, list):
                pref_lines.append(f"- {key}: {', '.join(str(v) for v in value[:3])}")
        
        return "\n".join(pref_lines) if len(pref_lines) > 1 else ""
    
    def update_quality_score(
        self,
        episode_id: str,
        user_id: str,
        quality_score: float,
        feedback_type: str = "neutral"
    ) -> bool:
        """
        Update quality score for a decision based on feedback
        
        Args:
            episode_id: Episode ID
            user_id: User ID
            quality_score: Quality score (0-1)
            feedback_type: Type of feedback (positive, negative, neutral)
        
        Returns:
            True if updated successfully
        """
        if not self.enable_memory:
            return False
        
        try:
            # Record feedback
            if self.memory_config.learn_from_feedback:
                self.learn_from_feedback(
                    user_id=user_id,
                    feedback_type=feedback_type,
                    feedback_data={
                        'episode_id': episode_id,
                        'quality_score': quality_score,
                        'agent': self.agent_name
                    }
                )
            
            logger.info(f"[ScreenwriterMemory] Quality score updated: {quality_score}")
            return True
            
        except Exception as e:
            logger.error(f"[ScreenwriterMemory] Error updating quality score: {e}")
            return False


# Factory function for easy creation
def create_memory_screenwriter(
    chat_model,
    fallback_chat_model: Optional[Any] = None,
    enable_memory: bool = True
) -> ScreenwriterMemory:
    """
    Create a memory-enhanced screenwriter agent
    
    Args:
        chat_model: Primary LLM model
        fallback_chat_model: Fallback LLM model
        enable_memory: Whether to enable memory features
    
    Returns:
        ScreenwriterMemory instance
    """
    config = MemoryConfig.default() if enable_memory else MemoryConfig.disabled()
    return ScreenwriterMemory(
        chat_model=chat_model,
        fallback_chat_model=fallback_chat_model,
        memory_config=config
    )