"""
Memory Services Package

Provides hierarchical memory management for the agent system:
- Episodic Memory: Session-based memories
- Semantic Memory: Long-term cross-session knowledge
- User Profiles: Personalization data
- Embedding Service: Vector embeddings for semantic search

Usage:
    from services.memory import MemoryManager
    from database import get_db
    
    db = next(get_db())
    memory = MemoryManager(db)
    
    # Record agent decision
    memory.record_agent_decision(
        episode_id="ep123",
        user_id="user456",
        agent_name="screenwriter",
        decision_context={"action": "generate_script"},
        quality_score=0.85
    )
    
    # Store learned knowledge with embedding
    memory.store_learned_knowledge(
        user_id="user456",
        category=KnowledgeCategory.USER_PREFERENCE,
        knowledge_key="preferred_genre",
        knowledge_value={"genre": "sci-fi", "confidence": 0.9},
        generate_embedding=True
    )
    
    # Semantic search
    results = memory.search_similar_memories(
        query_text="science fiction preferences",
        user_id="user456"
    )
"""

from services.memory.memory_types import (
    # Enums
    MemoryType,
    KnowledgeCategory,
    
    # Data classes
    EpisodicMemoryData,
    SemanticMemoryData,
    UserMemoryProfileData,
    MemorySearchQuery,
    MemorySearchResult,
)

from services.memory.episodic_memory_service import EpisodicMemoryService
from services.memory.semantic_memory_service import SemanticMemoryService
from services.memory.user_profile_service import UserProfileService
from services.memory.embedding_service import EmbeddingService
from services.memory.consolidation_service import ConsolidationService
from services.memory.memory_manager import MemoryManager

__all__ = [
    # Main interface
    'MemoryManager',
    
    # Individual services
    'EpisodicMemoryService',
    'SemanticMemoryService',
    'UserProfileService',
    'EmbeddingService',
    'ConsolidationService',
    
    # Enums
    'MemoryType',
    'KnowledgeCategory',
    
    # Data classes
    'EpisodicMemoryData',
    'SemanticMemoryData',
    'UserMemoryProfileData',
    'MemorySearchQuery',
    'MemorySearchResult',
]