"""
Semantic Memory Service
Manages long-term cross-session knowledge
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from database_models import SemanticMemory
from services.memory.memory_types import (
    SemanticMemoryData,
    KnowledgeCategory,
    MemoryCategory,
)
import uuid


class SemanticMemoryService:
    """Service for managing semantic memories"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_memory(
        self,
        user_id: str,
        category: KnowledgeCategory,
        knowledge_key: str,
        knowledge_value: Dict[str, Any],
        source_episodes: Optional[List[str]] = None,
        confidence_score: float = 1.0,
        importance_score: float = 0.5
    ) -> SemanticMemoryData:
        """
        Create a new semantic memory
        
        Args:
            user_id: User ID
            category: Knowledge category
            knowledge_key: Unique key for this knowledge
            knowledge_value: Knowledge data
            source_episodes: Optional list of source episode IDs
            confidence_score: Confidence in this knowledge (0-1)
            importance_score: Importance score (0-1)
        
        Returns:
            Created memory data
        """
        # Map KnowledgeCategory to MemoryCategory
        category_map = {
            KnowledgeCategory.USER_PREFERENCE: MemoryCategory.PREFERENCE,
            KnowledgeCategory.AGENT_BEHAVIOR: MemoryCategory.STRATEGY,
            KnowledgeCategory.GENERATION_PATTERN: MemoryCategory.PATTERN,
            KnowledgeCategory.STYLE_PATTERN: MemoryCategory.PATTERN,
            KnowledgeCategory.FEEDBACK_INSIGHT: MemoryCategory.FEEDBACK,
            KnowledgeCategory.DOMAIN_KNOWLEDGE: MemoryCategory.STRATEGY,
        }
        
        memory_category = category_map.get(category, MemoryCategory.PATTERN)
        
        # Store metadata in content
        content = {
            'knowledge_key': knowledge_key,
            'knowledge_value': knowledge_value,
            'source_episodes': source_episodes or [],
            'confidence_score': confidence_score,
            'importance_score': importance_score,
        }
        
        memory = SemanticMemory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            memory_category=memory_category.value,
            content=content,
            embedding_text=str(knowledge_value),
            usage_count=0,
            success_rate=confidence_score,
            last_used_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            decay_score=importance_score
        )
        
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        
        return self._to_data(memory)
    
    def get_memory(self, memory_id: str) -> Optional[SemanticMemoryData]:
        """
        Get a memory by ID and increment access count
        
        Args:
            memory_id: Memory ID
        
        Returns:
            Memory data or None if not found
        """
        memory = self.db.query(SemanticMemory).filter(
            SemanticMemory.id == memory_id
        ).first()
        
        if not memory:
            return None
        
        # Increment access count
        memory.access_count += 1
        memory.last_accessed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(memory)
        
        return self._to_data(memory)
    
    def get_memory_by_key(
        self,
        user_id: str,
        knowledge_key: str
    ) -> Optional[SemanticMemoryData]:
        """
        Get a memory by knowledge key
        
        Args:
            user_id: User ID
            knowledge_key: Knowledge key
        
        Returns:
            Memory data or None if not found
        """
        # Search in content JSON for knowledge_key
        memories = self.db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id
        ).all()
        
        for memory in memories:
            if memory.content and memory.content.get('knowledge_key') == knowledge_key:
                # Increment usage count
                memory.usage_count += 1
                memory.last_used_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(memory)
                return self._to_data(memory)
        
        return None
    
    def get_memories_by_category(
        self,
        user_id: str,
        category: KnowledgeCategory,
        limit: int = 100
    ) -> List[SemanticMemoryData]:
        """
        Get memories by category
        
        Args:
            user_id: User ID
            category: Knowledge category
            limit: Maximum number of memories to return
        
        Returns:
            List of memories
        """
        # Map KnowledgeCategory to MemoryCategory
        category_map = {
            KnowledgeCategory.USER_PREFERENCE: MemoryCategory.PREFERENCE,
            KnowledgeCategory.AGENT_BEHAVIOR: MemoryCategory.STRATEGY,
            KnowledgeCategory.GENERATION_PATTERN: MemoryCategory.PATTERN,
            KnowledgeCategory.STYLE_PATTERN: MemoryCategory.PATTERN,
            KnowledgeCategory.FEEDBACK_INSIGHT: MemoryCategory.FEEDBACK,
            KnowledgeCategory.DOMAIN_KNOWLEDGE: MemoryCategory.STRATEGY,
        }
        
        memory_category = category_map.get(category, MemoryCategory.PATTERN)
        
        memories = self.db.query(SemanticMemory).filter(
            and_(
                SemanticMemory.user_id == user_id,
                SemanticMemory.memory_category == memory_category.value
            )
        ).order_by(
            desc(SemanticMemory.decay_score),
            desc(SemanticMemory.success_rate)
        ).limit(limit).all()
        
        return [self._to_data(m) for m in memories]
    
    def get_user_memories(
        self,
        user_id: str,
        min_confidence: float = 0.0,
        min_importance: float = 0.0,
        limit: int = 100
    ) -> List[SemanticMemoryData]:
        """
        Get all memories for a user with optional filters
        
        Args:
            user_id: User ID
            min_confidence: Minimum confidence score (mapped to success_rate)
            min_importance: Minimum importance score (mapped to decay_score)
            limit: Maximum number of memories to return
        
        Returns:
            List of memories
        """
        query = self.db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id
        )
        
        if min_confidence > 0:
            query = query.filter(SemanticMemory.success_rate >= min_confidence)
        
        if min_importance > 0:
            query = query.filter(SemanticMemory.decay_score >= min_importance)
        
        memories = query.order_by(
            desc(SemanticMemory.decay_score),
            desc(SemanticMemory.success_rate)
        ).limit(limit).all()
        
        return [self._to_data(m) for m in memories]
    
    def update_memory(
        self,
        memory_id: str,
        knowledge_value: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        importance_score: Optional[float] = None,
        add_source_episode: Optional[str] = None
    ) -> Optional[SemanticMemoryData]:
        """
        Update a semantic memory
        
        Args:
            memory_id: Memory ID
            knowledge_value: Optional new knowledge value
            confidence_score: Optional new confidence score
            importance_score: Optional new importance score
            add_source_episode: Optional episode ID to add to sources
        
        Returns:
            Updated memory data or None if not found
        """
        memory = self.db.query(SemanticMemory).filter(
            SemanticMemory.id == memory_id
        ).first()
        
        if not memory:
            return None
        
        content = memory.content or {}
        
        if knowledge_value is not None:
            content['knowledge_value'] = knowledge_value
            memory.embedding_text = str(knowledge_value)
        
        if confidence_score is not None:
            content['confidence_score'] = confidence_score
            memory.success_rate = confidence_score
        
        if importance_score is not None:
            content['importance_score'] = importance_score
            memory.decay_score = importance_score
        
        if add_source_episode:
            source_episodes = content.get('source_episodes', [])
            if add_source_episode not in source_episodes:
                source_episodes.append(add_source_episode)
                content['source_episodes'] = source_episodes
        
        memory.content = content
        memory.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(memory)
        
        return self._to_data(memory)
    
    def merge_or_create(
        self,
        user_id: str,
        category: KnowledgeCategory,
        knowledge_key: str,
        knowledge_value: Dict[str, Any],
        source_episode: Optional[str] = None,
        confidence_score: float = 1.0,
        importance_score: float = 0.5
    ) -> SemanticMemoryData:
        """
        Merge with existing memory or create new one
        
        Args:
            user_id: User ID
            category: Knowledge category
            knowledge_key: Knowledge key
            knowledge_value: Knowledge value
            source_episode: Optional source episode ID
            confidence_score: Confidence score
            importance_score: Importance score
        
        Returns:
            Memory data (existing or new)
        """
        existing = self.get_memory_by_key(user_id, knowledge_key)
        
        if existing:
            # Merge knowledge values
            merged_value = {**existing.knowledge_value, **knowledge_value}
            
            # Average confidence scores
            new_confidence = (existing.confidence_score + confidence_score) / 2
            
            # Take max importance
            new_importance = max(existing.importance_score, importance_score)
            
            return self.update_memory(
                existing.id,
                knowledge_value=merged_value,
                confidence_score=new_confidence,
                importance_score=new_importance,
                add_source_episode=source_episode
            )
        else:
            return self.create_memory(
                user_id=user_id,
                category=category,
                knowledge_key=knowledge_key,
                knowledge_value=knowledge_value,
                source_episodes=[source_episode] if source_episode else None,
                confidence_score=confidence_score,
                importance_score=importance_score
            )
    
    def calculate_decay_score(
        self,
        memory: SemanticMemory,
        decay_rate: float = 0.1
    ) -> float:
        """
        Calculate decay score based on time and access patterns
        
        Args:
            memory: Memory object
            decay_rate: Decay rate per day (0-1)
        
        Returns:
            Decay score (0-1, lower means more decayed)
        """
        # Time since last access (use last_used_at from database)
        if memory.last_used_at:
            days_since_access = (datetime.utcnow() - memory.last_used_at).days
        else:
            days_since_access = 0
        
        # Time-based decay
        time_decay = max(0, 1 - (days_since_access * decay_rate))
        
        # Access frequency boost (use usage_count from database)
        access_boost = min(1, memory.usage_count / 10)  # Cap at 10 accesses
        
        # Combine with importance (decay_score) and confidence (success_rate)
        decay_score = (
            time_decay * 0.4 +
            access_boost * 0.2 +
            memory.decay_score * 0.2 +
            memory.success_rate * 0.2
        )
        
        return decay_score
    
    def prune_low_value_memories(
        self,
        user_id: str,
        min_decay_score: float = 0.3,
        max_age_days: int = 90
    ) -> int:
        """
        Prune memories with low decay scores or too old
        
        Args:
            user_id: User ID
            min_decay_score: Minimum decay score to keep
            max_age_days: Maximum age in days
        
        Returns:
            Number of memories pruned
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        memories = self.db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id
        ).all()
        
        pruned_count = 0
        
        for memory in memories:
            decay_score = self.calculate_decay_score(memory)
            
            # Prune if decay score too low or too old
            if decay_score < min_decay_score or memory.created_at < cutoff_date:
                self.db.delete(memory)
                pruned_count += 1
        
        self.db.commit()
        
        return pruned_count
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory
        
        Args:
            memory_id: Memory ID
        
        Returns:
            True if deleted, False if not found
        """
        memory = self.db.query(SemanticMemory).filter(
            SemanticMemory.id == memory_id
        ).first()
        
        if not memory:
            return False
        
        self.db.delete(memory)
        self.db.commit()
        
        return True
    
    def get_memory_statistics(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get statistics about semantic memories
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with statistics
        """
        memories = self.db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id
        ).all()
        
        if not memories:
            return {
                'total_count': 0,
                'by_category': {},
                'avg_confidence': 0,
                'avg_importance': 0,
                'avg_access_count': 0,
                'avg_decay_score': 0
            }
        
        # Count by memory_category (database column)
        category_counts = {}
        for memory in memories:
            cat = memory.memory_category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Calculate averages using database columns
        avg_confidence = sum(m.success_rate for m in memories) / len(memories)
        avg_importance = sum(m.decay_score for m in memories) / len(memories)
        avg_access_count = sum(m.usage_count for m in memories) / len(memories)
        
        # Calculate average decay score
        decay_scores = [self.calculate_decay_score(m) for m in memories]
        avg_decay_score = sum(decay_scores) / len(decay_scores)
        
        return {
            'total_count': len(memories),
            'by_category': category_counts,
            'avg_confidence': avg_confidence,
            'avg_importance': avg_importance,
            'avg_access_count': avg_access_count,
            'avg_decay_score': avg_decay_score
        }
    
    def _to_data(self, memory: SemanticMemory) -> SemanticMemoryData:
        """Convert database model to data class"""
        content = memory.content or {}
        
        # Map MemoryCategory back to KnowledgeCategory
        category_reverse_map = {
            MemoryCategory.PREFERENCE.value: KnowledgeCategory.USER_PREFERENCE,
            MemoryCategory.STRATEGY.value: KnowledgeCategory.AGENT_BEHAVIOR,
            MemoryCategory.PATTERN.value: KnowledgeCategory.GENERATION_PATTERN,
            MemoryCategory.FEEDBACK.value: KnowledgeCategory.FEEDBACK_INSIGHT,
            MemoryCategory.FAILURE.value: KnowledgeCategory.DOMAIN_KNOWLEDGE,
        }
        
        category = category_reverse_map.get(
            memory.memory_category,
            KnowledgeCategory.DOMAIN_KNOWLEDGE
        )
        
        return SemanticMemoryData(
            id=memory.id,
            user_id=memory.user_id,
            category=category,
            knowledge_key=content.get('knowledge_key', ''),
            knowledge_value=content.get('knowledge_value', {}),
            source_episodes=content.get('source_episodes', []),
            confidence_score=content.get('confidence_score', memory.success_rate),
            importance_score=content.get('importance_score', memory.decay_score),
            access_count=memory.usage_count,
            last_accessed_at=memory.last_used_at,
            created_at=memory.created_at,
            updated_at=memory.updated_at
        )