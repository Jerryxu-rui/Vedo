"""
Episodic Memory Service
Manages session-based memories for episode generation
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database_models import EpisodeMemory
from services.memory.memory_types import (
    EpisodicMemoryData,
    MemoryType,
)
import uuid


class EpisodicMemoryService:
    """Service for managing episodic memories"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_memory(
        self,
        episode_id: str,
        user_id: str,
        memory_type: MemoryType,
        agent_name: str,
        context: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None
    ) -> EpisodicMemoryData:
        """
        Create a new episodic memory
        
        Args:
            episode_id: Episode ID
            user_id: User ID
            memory_type: Type of memory (decision, feedback, outcome, interaction)
            agent_name: Name of the agent
            context: Context data
            outcome: Optional outcome data
            quality_score: Optional quality score (0-1)
        
        Returns:
            Created memory data
        """
        memory = EpisodeMemory(
            id=str(uuid.uuid4()),
            episode_id=episode_id,
            user_id=user_id,
            memory_type=memory_type.value,
            agent_name=agent_name,
            context=context,
            outcome=outcome,
            quality_score=quality_score,
            created_at=datetime.utcnow()
        )
        
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        
        return self._to_data(memory)
    
    def get_memory(self, memory_id: str) -> Optional[EpisodicMemoryData]:
        """Get a memory by ID"""
        memory = self.db.query(EpisodeMemory).filter(
            EpisodeMemory.id == memory_id
        ).first()
        
        return self._to_data(memory) if memory else None
    
    def get_episode_memories(
        self,
        episode_id: str,
        memory_type: Optional[MemoryType] = None,
        agent_name: Optional[str] = None
    ) -> List[EpisodicMemoryData]:
        """
        Get all memories for an episode
        
        Args:
            episode_id: Episode ID
            memory_type: Optional filter by memory type
            agent_name: Optional filter by agent name
        
        Returns:
            List of memories
        """
        query = self.db.query(EpisodeMemory).filter(
            EpisodeMemory.episode_id == episode_id
        )
        
        if memory_type:
            query = query.filter(EpisodeMemory.memory_type == memory_type.value)
        
        if agent_name:
            query = query.filter(EpisodeMemory.agent_name == agent_name)
        
        memories = query.order_by(EpisodeMemory.created_at.desc()).all()
        
        return [self._to_data(m) for m in memories]
    
    def get_user_memories(
        self,
        user_id: str,
        limit: int = 100,
        memory_type: Optional[MemoryType] = None
    ) -> List[EpisodicMemoryData]:
        """
        Get memories for a user across all episodes
        
        Args:
            user_id: User ID
            limit: Maximum number of memories to return
            memory_type: Optional filter by memory type
        
        Returns:
            List of memories
        """
        query = self.db.query(EpisodeMemory).filter(
            EpisodeMemory.user_id == user_id
        )
        
        if memory_type:
            query = query.filter(EpisodeMemory.memory_type == memory_type.value)
        
        memories = query.order_by(
            EpisodeMemory.created_at.desc()
        ).limit(limit).all()
        
        return [self._to_data(m) for m in memories]
    
    def get_agent_memories(
        self,
        agent_name: str,
        episode_id: Optional[str] = None,
        limit: int = 100
    ) -> List[EpisodicMemoryData]:
        """
        Get memories for a specific agent
        
        Args:
            agent_name: Agent name
            episode_id: Optional filter by episode
            limit: Maximum number of memories to return
        
        Returns:
            List of memories
        """
        query = self.db.query(EpisodeMemory).filter(
            EpisodeMemory.agent_name == agent_name
        )
        
        if episode_id:
            query = query.filter(EpisodeMemory.episode_id == episode_id)
        
        memories = query.order_by(
            EpisodeMemory.created_at.desc()
        ).limit(limit).all()
        
        return [self._to_data(m) for m in memories]
    
    def update_memory(
        self,
        memory_id: str,
        outcome: Optional[Dict[str, Any]] = None,
        quality_score: Optional[float] = None
    ) -> Optional[EpisodicMemoryData]:
        """
        Update a memory's outcome and quality score
        
        Args:
            memory_id: Memory ID
            outcome: Optional outcome data
            quality_score: Optional quality score
        
        Returns:
            Updated memory data or None if not found
        """
        memory = self.db.query(EpisodeMemory).filter(
            EpisodeMemory.id == memory_id
        ).first()
        
        if not memory:
            return None
        
        if outcome is not None:
            memory.outcome = outcome
        
        if quality_score is not None:
            memory.quality_score = quality_score
        
        self.db.commit()
        self.db.refresh(memory)
        
        return self._to_data(memory)
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory
        
        Args:
            memory_id: Memory ID
        
        Returns:
            True if deleted, False if not found
        """
        memory = self.db.query(EpisodeMemory).filter(
            EpisodeMemory.id == memory_id
        ).first()
        
        if not memory:
            return False
        
        self.db.delete(memory)
        self.db.commit()
        
        return True
    
    def delete_episode_memories(self, episode_id: str) -> int:
        """
        Delete all memories for an episode
        
        Args:
            episode_id: Episode ID
        
        Returns:
            Number of memories deleted
        """
        count = self.db.query(EpisodeMemory).filter(
            EpisodeMemory.episode_id == episode_id
        ).delete()
        
        self.db.commit()
        
        return count
    
    def get_memory_statistics(
        self,
        episode_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about memories
        
        Args:
            episode_id: Optional filter by episode
            user_id: Optional filter by user
            agent_name: Optional filter by agent
        
        Returns:
            Dictionary with statistics
        """
        query = self.db.query(EpisodeMemory)
        
        if episode_id:
            query = query.filter(EpisodeMemory.episode_id == episode_id)
        
        if user_id:
            query = query.filter(EpisodeMemory.user_id == user_id)
        
        if agent_name:
            query = query.filter(EpisodeMemory.agent_name == agent_name)
        
        total_count = query.count()
        
        # Count by type
        type_counts = {}
        for memory_type in MemoryType:
            count = query.filter(
                EpisodeMemory.memory_type == memory_type.value
            ).count()
            type_counts[memory_type.value] = count
        
        # Average quality score
        memories_with_scores = query.filter(
            EpisodeMemory.quality_score.isnot(None)
        ).all()
        
        avg_quality = None
        if memories_with_scores:
            avg_quality = sum(m.quality_score for m in memories_with_scores) / len(memories_with_scores)
        
        return {
            'total_count': total_count,
            'type_counts': type_counts,
            'avg_quality_score': avg_quality,
            'memories_with_scores': len(memories_with_scores)
        }
    
    def _to_data(self, memory: EpisodeMemory) -> EpisodicMemoryData:
        """Convert database model to data class"""
        return EpisodicMemoryData(
            id=memory.id,
            episode_id=memory.episode_id,
            user_id=memory.user_id,
            memory_type=MemoryType(memory.memory_type),
            agent_name=memory.agent_name,
            context=memory.context or {},
            outcome=memory.outcome,
            quality_score=memory.quality_score,
            created_at=memory.created_at
        )