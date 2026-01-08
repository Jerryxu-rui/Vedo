"""
Memory-Augmented Agent Base Class

Provides memory capabilities for agents including:
- Memory retrieval and context augmentation
- Decision recording
- Learning from past experiences
- User preference integration
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from database import get_db
from services.memory import (
    MemoryManager,
    MemoryType,
    KnowledgeCategory,
)

logger = logging.getLogger(__name__)


class MemoryAugmentedAgent:
    """
    Base class for agents with memory capabilities.
    
    Provides methods for:
    - Retrieving relevant memories
    - Augmenting prompts with memory context
    - Recording decisions and outcomes
    - Learning from feedback
    """
    
    def __init__(
        self,
        agent_name: str,
        enable_memory: bool = True,
        max_memory_context: int = 5,
        min_relevance_score: float = 0.7
    ):
        """
        Initialize memory-augmented agent
        
        Args:
            agent_name: Name of the agent (e.g., "screenwriter", "storyboard_artist")
            enable_memory: Whether to enable memory features
            max_memory_context: Maximum number of memories to include in context
            min_relevance_score: Minimum relevance score for memory retrieval
        """
        self.agent_name = agent_name
        self.enable_memory = enable_memory
        self.max_memory_context = max_memory_context
        self.min_relevance_score = min_relevance_score
        
        # Initialize memory manager
        self.memory_manager = None
        if self.enable_memory:
            try:
                db = next(get_db())
                self.memory_manager = MemoryManager(db)
                logger.info(f"[{self.agent_name}] Memory system initialized")
            except Exception as e:
                logger.warning(f"[{self.agent_name}] Failed to initialize memory: {e}")
                self.enable_memory = False
    
    def get_relevant_memories(
        self,
        user_id: str,
        context: Dict[str, Any],
        memory_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for current context
        
        Args:
            user_id: User ID
            context: Current context (task, input, etc.)
            memory_types: Optional filter for memory types
        
        Returns:
            List of relevant memories
        """
        if not self.enable_memory or not self.memory_manager:
            return []
        
        try:
            # Get agent's past decisions
            agent_history = self.memory_manager.get_agent_history(
                agent_name=self.agent_name,
                limit=self.max_memory_context
            )
            
            # Filter by quality score
            relevant_memories = [
                {
                    'type': 'agent_decision',
                    'context': m.context,
                    'outcome': m.outcome,
                    'quality_score': m.quality_score,
                    'created_at': m.created_at
                }
                for m in agent_history
                if m.quality_score and m.quality_score >= self.min_relevance_score
            ]
            
            # Get user preferences
            user_profile = self.memory_manager.get_user_profile(user_id)
            if user_profile and user_profile.preferences:
                relevant_memories.append({
                    'type': 'user_preferences',
                    'preferences': user_profile.preferences,
                    'style_patterns': user_profile.style_patterns
                })
            
            # Get learned patterns for this agent
            patterns = self.memory_manager.get_knowledge_by_category(
                user_id=user_id,
                category=KnowledgeCategory.GENERATION_PATTERN
            )
            
            for pattern in patterns[:3]:  # Top 3 patterns
                if self.agent_name in pattern.knowledge_key:
                    relevant_memories.append({
                        'type': 'learned_pattern',
                        'pattern': pattern.knowledge_value,
                        'confidence': pattern.confidence_score
                    })
            
            logger.info(f"[{self.agent_name}] Retrieved {len(relevant_memories)} relevant memories")
            return relevant_memories[:self.max_memory_context]
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error retrieving memories: {e}")
            return []
    
    def augment_prompt_with_memory(
        self,
        base_prompt: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Augment prompt with relevant memory context
        
        Args:
            base_prompt: Original prompt
            user_id: User ID
            context: Current context
        
        Returns:
            Augmented prompt with memory context
        """
        if not self.enable_memory:
            return base_prompt
        
        memories = self.get_relevant_memories(user_id, context)
        
        if not memories:
            return base_prompt
        
        # Format memories for prompt
        memory_context = self._format_memories_for_prompt(memories)
        
        # Augment prompt
        augmented_prompt = f"""{base_prompt}

<MEMORY_CONTEXT>
You have access to relevant past experiences and learned patterns:

{memory_context}

Use this context to inform your decisions and improve quality.
</MEMORY_CONTEXT>"""
        
        logger.info(f"[{self.agent_name}] Prompt augmented with {len(memories)} memories")
        return augmented_prompt
    
    def _format_memories_for_prompt(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories into readable context for prompt"""
        formatted = []
        
        for i, memory in enumerate(memories, 1):
            mem_type = memory.get('type', 'unknown')
            
            if mem_type == 'agent_decision':
                formatted.append(
                    f"{i}. Past Decision (Quality: {memory['quality_score']:.2f}):\n"
                    f"   Context: {memory['context']}\n"
                    f"   Outcome: {memory['outcome']}"
                )
            
            elif mem_type == 'user_preferences':
                prefs = memory.get('preferences', {})
                formatted.append(
                    f"{i}. User Preferences:\n"
                    f"   {self._format_dict(prefs, indent=3)}"
                )
            
            elif mem_type == 'learned_pattern':
                pattern = memory.get('pattern', {})
                formatted.append(
                    f"{i}. Learned Pattern (Confidence: {memory['confidence']:.2f}):\n"
                    f"   {self._format_dict(pattern, indent=3)}"
                )
        
        return "\n\n".join(formatted)
    
    def _format_dict(self, d: Dict[str, Any], indent: int = 0) -> str:
        """Format dictionary for readable display"""
        lines = []
        prefix = " " * indent
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_dict(value, indent + 2))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}: {', '.join(str(v) for v in value[:3])}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)
    
    def record_decision(
        self,
        episode_id: str,
        user_id: str,
        decision_context: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None
    ) -> bool:
        """
        Record agent decision to memory
        
        Args:
            episode_id: Episode ID
            user_id: User ID
            decision_context: Context of the decision
            outcome: Outcome of the decision
            quality_score: Quality score (0-1)
        
        Returns:
            True if recorded successfully
        """
        if not self.enable_memory or not self.memory_manager:
            return False
        
        try:
            memory = self.memory_manager.record_agent_decision(
                episode_id=episode_id,
                user_id=user_id,
                agent_name=self.agent_name,
                decision_context=decision_context,
                outcome=outcome,
                quality_score=quality_score
            )
            
            logger.info(f"[{self.agent_name}] Decision recorded: {memory.id}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error recording decision: {e}")
            return False
    
    def learn_from_feedback(
        self,
        user_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any]
    ) -> bool:
        """
        Learn from user feedback
        
        Args:
            user_id: User ID
            feedback_type: Type of feedback (positive, negative, neutral)
            feedback_data: Feedback data
        
        Returns:
            True if learned successfully
        """
        if not self.enable_memory or not self.memory_manager:
            return False
        
        try:
            # Record feedback to user profile
            profile = self.memory_manager.record_user_feedback_to_profile(
                user_id=user_id,
                feedback_type=feedback_type,
                feedback_data=feedback_data
            )
            
            logger.info(f"[{self.agent_name}] Learned from {feedback_type} feedback")
            return True
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error learning from feedback: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences
        
        Args:
            user_id: User ID
        
        Returns:
            User preferences dictionary
        """
        if not self.enable_memory or not self.memory_manager:
            return {}
        
        try:
            profile = self.memory_manager.get_user_profile(user_id)
            if profile:
                return profile.preferences
            return {}
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error getting preferences: {e}")
            return {}
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """
        Get agent performance statistics
        
        Args:
            None
        
        Returns:
            Statistics dictionary
        """
        if not self.enable_memory or not self.memory_manager:
            return {
                'memory_enabled': False,
                'total_decisions': 0,
                'avg_quality': 0.0
            }
        
        try:
            history = self.memory_manager.get_agent_history(
                agent_name=self.agent_name,
                limit=100
            )
            
            quality_scores = [m.quality_score for m in history if m.quality_score]
            
            return {
                'memory_enabled': True,
                'total_decisions': len(history),
                'avg_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
                'recent_decisions': len([m for m in history[:10]]),
                'high_quality_rate': len([q for q in quality_scores if q >= 0.8]) / len(quality_scores) if quality_scores else 0.0
            }
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error getting statistics: {e}")
            return {
                'memory_enabled': True,
                'error': str(e)
            }


class MemoryConfig:
    """Configuration for memory-augmented agents"""
    
    def __init__(
        self,
        enable_memory: bool = True,
        max_memory_context: int = 5,
        min_relevance_score: float = 0.7,
        record_decisions: bool = True,
        augment_prompts: bool = True,
        learn_from_feedback: bool = True
    ):
        self.enable_memory = enable_memory
        self.max_memory_context = max_memory_context
        self.min_relevance_score = min_relevance_score
        self.record_decisions = record_decisions
        self.augment_prompts = augment_prompts
        self.learn_from_feedback = learn_from_feedback
    
    @classmethod
    def default(cls) -> 'MemoryConfig':
        """Get default configuration"""
        return cls()
    
    @classmethod
    def disabled(cls) -> 'MemoryConfig':
        """Get configuration with memory disabled"""
        return cls(enable_memory=False)
    
    @classmethod
    def minimal(cls) -> 'MemoryConfig':
        """Get minimal memory configuration"""
        return cls(
            max_memory_context=3,
            min_relevance_score=0.8,
            augment_prompts=False
        )