"""
Memory Manager
Unified interface for all memory operations
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from services.memory.episodic_memory_service import EpisodicMemoryService
from services.memory.user_profile_service import UserProfileService
from services.memory.semantic_memory_service import SemanticMemoryService
from services.memory.embedding_service import EmbeddingService
from services.memory.consolidation_service import ConsolidationService
from services.memory.memory_types import (
    EpisodicMemoryData,
    SemanticMemoryData,
    UserMemoryProfileData,
    MemoryType,
    KnowledgeCategory,
)


class MemoryManager:
    """
    Unified memory manager coordinating all memory services
    
    This class provides a single interface for:
    - Episodic memory (session-based)
    - Semantic memory (long-term knowledge)
    - User profiles (personalization)
    """
    
    def __init__(
        self,
        db: Session,
        enable_embeddings: bool = True,
        embedding_provider: str = "openai",
        embedding_model: str = "text-embedding-3-small"
    ):
        """
        Initialize memory manager with database session
        
        Args:
            db: SQLAlchemy database session
            enable_embeddings: Enable embedding generation
            embedding_provider: Embedding provider (openai, local)
            embedding_model: Embedding model name
        """
        self.db = db
        self.episodic = EpisodicMemoryService(db)
        self.semantic = SemanticMemoryService(db)
        self.profile = UserProfileService(db)
        self.consolidation = ConsolidationService(db)
        
        # Initialize embedding service if enabled
        self.enable_embeddings = enable_embeddings
        if enable_embeddings:
            try:
                self.embedding = EmbeddingService(db, embedding_provider, embedding_model)
            except Exception as e:
                print(f"Warning: Failed to initialize embedding service: {str(e)}")
                self.enable_embeddings = False
                self.embedding = None
        else:
            self.embedding = None
    
    # ==================== Episodic Memory Operations ====================
    
    def record_agent_decision(
        self,
        episode_id: str,
        user_id: str,
        agent_name: str,
        decision_context: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None
    ) -> EpisodicMemoryData:
        """
        Record an agent decision in episodic memory
        
        Args:
            episode_id: Episode ID
            user_id: User ID
            agent_name: Agent name
            decision_context: Context of the decision
            outcome: Optional outcome data
            quality_score: Optional quality score
        
        Returns:
            Created memory data
        """
        return self.episodic.create_memory(
            episode_id=episode_id,
            user_id=user_id,
            memory_type=MemoryType.DECISION,
            agent_name=agent_name,
            context=decision_context,
            outcome=outcome,
            quality_score=quality_score
        )
    
    def record_user_feedback(
        self,
        episode_id: str,
        user_id: str,
        agent_name: str,
        feedback_context: Dict[str, Any],
        quality_score: float
    ) -> EpisodicMemoryData:
        """
        Record user feedback in episodic memory
        
        Args:
            episode_id: Episode ID
            user_id: User ID
            agent_name: Agent name receiving feedback
            feedback_context: Feedback context
            quality_score: Quality score from feedback
        
        Returns:
            Created memory data
        """
        return self.episodic.create_memory(
            episode_id=episode_id,
            user_id=user_id,
            memory_type=MemoryType.FEEDBACK,
            agent_name=agent_name,
            context=feedback_context,
            quality_score=quality_score
        )
    
    def get_episode_context(
        self,
        episode_id: str,
        agent_name: Optional[str] = None
    ) -> List[EpisodicMemoryData]:
        """
        Get all context for an episode
        
        Args:
            episode_id: Episode ID
            agent_name: Optional filter by agent
        
        Returns:
            List of episodic memories
        """
        return self.episodic.get_episode_memories(
            episode_id=episode_id,
            agent_name=agent_name
        )
    
    def get_agent_history(
        self,
        agent_name: str,
        episode_id: Optional[str] = None,
        limit: int = 50
    ) -> List[EpisodicMemoryData]:
        """
        Get historical memories for an agent
        
        Args:
            agent_name: Agent name
            episode_id: Optional filter by episode
            limit: Maximum memories to return
        
        Returns:
            List of episodic memories
        """
        return self.episodic.get_agent_memories(
            agent_name=agent_name,
            episode_id=episode_id,
            limit=limit
        )
    
    # ==================== Semantic Memory Operations ====================
    
    def store_learned_knowledge(
        self,
        user_id: str,
        category: KnowledgeCategory,
        knowledge_key: str,
        knowledge_value: Dict[str, Any],
        source_episode: Optional[str] = None,
        confidence: float = 1.0,
        importance: float = 0.5,
        generate_embedding: bool = True
    ) -> SemanticMemoryData:
        """
        Store learned knowledge in semantic memory
        
        Args:
            user_id: User ID
            category: Knowledge category
            knowledge_key: Unique knowledge key
            knowledge_value: Knowledge data
            source_episode: Optional source episode
            confidence: Confidence score (0-1)
            importance: Importance score (0-1)
            generate_embedding: Generate embedding for semantic search
        
        Returns:
            Semantic memory data
        """
        memory = self.semantic.merge_or_create(
            user_id=user_id,
            category=category,
            knowledge_key=knowledge_key,
            knowledge_value=knowledge_value,
            source_episode=source_episode,
            confidence_score=confidence,
            importance_score=importance
        )
        
        # Generate embedding if enabled
        if generate_embedding and self.enable_embeddings and self.embedding:
            try:
                self.embedding.embed_semantic_memory(memory.id)
            except Exception as e:
                print(f"Warning: Failed to generate embedding: {str(e)}")
        
        return memory
    
    def retrieve_knowledge(
        self,
        user_id: str,
        knowledge_key: str
    ) -> Optional[SemanticMemoryData]:
        """
        Retrieve knowledge by key
        
        Args:
            user_id: User ID
            knowledge_key: Knowledge key
        
        Returns:
            Semantic memory data or None
        """
        return self.semantic.get_memory_by_key(user_id, knowledge_key)
    
    def get_knowledge_by_category(
        self,
        user_id: str,
        category: KnowledgeCategory,
        limit: int = 50
    ) -> List[SemanticMemoryData]:
        """
        Get knowledge by category
        
        Args:
            user_id: User ID
            category: Knowledge category
            limit: Maximum memories to return
        
        Returns:
            List of semantic memories
        """
        return self.semantic.get_memories_by_category(
            user_id=user_id,
            category=category,
            limit=limit
        )
    
    def prune_old_knowledge(
        self,
        user_id: str,
        min_decay_score: float = 0.3,
        max_age_days: int = 90
    ) -> int:
        """
        Prune old or low-value knowledge
        
        Args:
            user_id: User ID
            min_decay_score: Minimum decay score to keep
            max_age_days: Maximum age in days
        
        Returns:
            Number of memories pruned
        """
        return self.semantic.prune_low_value_memories(
            user_id=user_id,
            min_decay_score=min_decay_score,
            max_age_days=max_age_days
        )
    
    # ==================== User Profile Operations ====================
    
    def get_user_profile(self, user_id: str) -> UserMemoryProfileData:
        """
        Get or create user profile
        
        Args:
            user_id: User ID
        
        Returns:
            User profile data
        """
        return self.profile.get_or_create_profile(user_id)
    
    def update_user_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: Any
    ) -> Optional[UserMemoryProfileData]:
        """
        Update a user preference
        
        Args:
            user_id: User ID
            preference_key: Preference key
            preference_value: Preference value
        
        Returns:
            Updated profile or None
        """
        return self.profile.update_preferences(
            user_id=user_id,
            preferences={preference_key: preference_value},
            merge=True
        )
    
    def get_user_preference(
        self,
        user_id: str,
        preference_key: str,
        default: Any = None
    ) -> Any:
        """
        Get a user preference
        
        Args:
            user_id: User ID
            preference_key: Preference key
            default: Default value if not found
        
        Returns:
            Preference value or default
        """
        return self.profile.get_preference(user_id, preference_key, default)
    
    def record_user_feedback_to_profile(
        self,
        user_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any]
    ) -> Optional[UserMemoryProfileData]:
        """
        Record feedback to user profile
        
        Args:
            user_id: User ID
            feedback_type: Feedback type (positive, negative, neutral)
            feedback_data: Feedback data
        
        Returns:
            Updated profile or None
        """
        return self.profile.add_feedback(
            user_id=user_id,
            feedback_type=feedback_type,
            feedback_data=feedback_data
        )
    
    # ==================== Cross-Memory Operations ====================
    
    def consolidate_episode_to_semantic(
        self,
        episode_id: str,
        user_id: str,
        min_quality_score: float = 0.7,
        consolidation_type: str = "episode_complete"
    ) -> Dict[str, Any]:
        """
        Consolidate episodic memories into semantic knowledge
        
        This is a key operation that learns from episode experiences
        and stores valuable patterns in long-term memory.
        
        Uses the advanced ConsolidationService for comprehensive learning.
        
        Args:
            episode_id: Episode ID to consolidate
            user_id: User ID
            min_quality_score: Minimum quality score to consolidate
            consolidation_type: Type of consolidation (episode_complete, periodic, manual)
        
        Returns:
            Consolidation summary
        """
        return self.consolidation.consolidate_episode(
            episode_id=episode_id,
            user_id=user_id,
            consolidation_type=consolidation_type,
            min_quality_threshold=min_quality_score
        )
    
    def get_consolidation_history(
        self,
        episode_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get consolidation history
        
        Args:
            episode_id: Optional filter by episode
            limit: Maximum number of records to return
        
        Returns:
            List of consolidation records
        """
        return self.consolidation.get_consolidation_history(
            episode_id=episode_id,
            limit=limit
        )
    
    def get_memory_overview(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive memory overview for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Memory overview with statistics
        """
        # Get statistics from each service
        episodic_stats = self.episodic.get_memory_statistics(user_id=user_id)
        semantic_stats = self.semantic.get_memory_statistics(user_id=user_id)
        profile = self.profile.get_profile(user_id)
        
        return {
            'user_id': user_id,
            'episodic_memory': episodic_stats,
            'semantic_memory': semantic_stats,
            'profile': {
                'has_profile': profile is not None,
                'preference_count': len(profile.preferences) if profile else 0,
                'style_pattern_count': len(profile.style_patterns) if profile else 0,
                'feedback_count': sum(
                    len(items) for items in profile.feedback_history.values()
                ) if profile and profile.feedback_history else 0
            }
        }
    
    def cleanup_user_memories(
        self,
        user_id: str,
        keep_recent_episodes: int = 10
    ) -> Dict[str, int]:
        """
        Cleanup old memories for a user
        
        Args:
            user_id: User ID
            keep_recent_episodes: Number of recent episodes to keep
        
        Returns:
            Cleanup summary
        """
        # Get recent episodes
        recent_memories = self.episodic.get_user_memories(
            user_id=user_id,
            limit=1000
        )
        
        # Get unique episode IDs
        episode_ids = list(set(m.episode_id for m in recent_memories))
        episode_ids.sort(key=lambda eid: max(
            m.created_at for m in recent_memories if m.episode_id == eid
        ), reverse=True)
        
        # Keep only recent episodes
        episodes_to_keep = set(episode_ids[:keep_recent_episodes])
        episodes_to_delete = set(episode_ids[keep_recent_episodes:])
        
        # Delete old episodes
        episodic_deleted = 0
        for episode_id in episodes_to_delete:
            episodic_deleted += self.episodic.delete_episode_memories(episode_id)
        
        # Prune semantic memories
        semantic_deleted = self.semantic.prune_low_value_memories(user_id=user_id)
        
        return {
            'episodic_deleted': episodic_deleted,
            'semantic_deleted': semantic_deleted,
            'episodes_kept': len(episodes_to_keep),
            'episodes_deleted': len(episodes_to_delete)
        }
    
    # ==================== Embedding Operations ====================
    
    def search_similar_memories(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories using semantic search
        
        Args:
            query_text: Query text
            user_id: Optional filter by user
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of similar memories with scores
        """
        if not self.enable_embeddings or not self.embedding:
            raise RuntimeError("Embedding service not enabled")
        
        return self.embedding.search_similar_memories(
            query_text=query_text,
            user_id=user_id,
            top_k=top_k,
            min_similarity=min_similarity
        )
    
    def generate_embeddings_for_all_memories(
        self,
        user_id: Optional[str] = None,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate embeddings for all semantic memories
        
        Args:
            user_id: Optional filter by user
            force_regenerate: Force regeneration even if exists
        
        Returns:
            Summary of embedding generation
        """
        if not self.enable_embeddings or not self.embedding:
            raise RuntimeError("Embedding service not enabled")
        
        return self.embedding.embed_all_semantic_memories(
            user_id=user_id,
            force_regenerate=force_regenerate
        )
    
    def get_embedding_for_memory(
        self,
        semantic_memory_id: str
    ) -> Optional[List[float]]:
        """
        Get embedding vector for a semantic memory
        
        Args:
            semantic_memory_id: Semantic memory ID
        
        Returns:
            Embedding vector or None
        """
        if not self.enable_embeddings or not self.embedding:
            return None
        
        return self.embedding.get_embedding(semantic_memory_id)