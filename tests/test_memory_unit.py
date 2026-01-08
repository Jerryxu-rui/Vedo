"""
Unit Tests for Memory Services

Tests individual memory service components in isolation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.memory import (
    MemoryType,
    KnowledgeCategory,
)
from services.memory.memory_types import (
    EpisodicMemoryCreate,
    SemanticMemoryCreate,
    UserProfileUpdate,
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


@pytest.mark.unit
class TestMemoryTypes:
    """Test memory type models and enums"""
    
    def test_memory_type_enum(self):
        """Test MemoryType enum values"""
        assert MemoryType.AGENT_DECISION.value == "agent_decision"
        assert MemoryType.USER_FEEDBACK.value == "user_feedback"
        assert MemoryType.SYSTEM_EVENT.value == "system_event"
    
    def test_knowledge_category_enum(self):
        """Test KnowledgeCategory enum values"""
        assert KnowledgeCategory.USER_PREFERENCE.value == "user_preference"
        assert KnowledgeCategory.GENERATION_PATTERN.value == "generation_pattern"
        assert KnowledgeCategory.AGENT_STRATEGY.value == "agent_strategy"
    
    def test_episodic_memory_create(self):
        """Test EpisodicMemoryCreate model"""
        memory = EpisodicMemoryCreate(
            episode_id="ep123",
            user_id="user456",
            memory_type=MemoryType.AGENT_DECISION,
            agent_name="screenwriter",
            content={"action": "generate"},
            context={"style": "cinematic"},
            quality_score=0.85
        )
        
        assert memory.episode_id == "ep123"
        assert memory.user_id == "user456"
        assert memory.memory_type == MemoryType.AGENT_DECISION
        assert memory.quality_score == 0.85
    
    def test_semantic_memory_create(self):
        """Test SemanticMemoryCreate model"""
        memory = SemanticMemoryCreate(
            user_id="user456",
            category=KnowledgeCategory.USER_PREFERENCE,
            knowledge_key="preferred_style",
            knowledge_value={"style": "cinematic"},
            confidence_score=0.9,
            importance_score=0.8
        )
        
        assert memory.user_id == "user456"
        assert memory.category == KnowledgeCategory.USER_PREFERENCE
        assert memory.confidence_score == 0.9
        assert memory.importance_score == 0.8


@pytest.mark.unit
class TestEpisodicMemoryService:
    """Test EpisodicMemoryService"""
    
    def test_create_memory(self, mock_db_session):
        """Test creating episodic memory"""
        from services.memory.episodic_memory_service import EpisodicMemoryService
        from database_models import EpisodeMemory
        
        service = EpisodicMemoryService(mock_db_session)
        
        # Mock the database model
        mock_memory = EpisodeMemory(
            id=1,
            episode_id="ep123",
            user_id="user456",
            memory_type="agent_decision",
            agent_name="screenwriter",
            content={"action": "generate"},
            context={"style": "cinematic"},
            quality_score=0.85,
            created_at=datetime.utcnow()
        )
        
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.side_effect = lambda x: setattr(x, 'id', 1)
        
        # Create memory
        memory_data = EpisodicMemoryCreate(
            episode_id="ep123",
            user_id="user456",
            memory_type=MemoryType.AGENT_DECISION,
            agent_name="screenwriter",
            content={"action": "generate"},
            context={"style": "cinematic"},
            quality_score=0.85
        )
        
        result = service.create_memory(memory_data)
        
        # Verify database operations
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
    
    def test_get_episode_memories(self, mock_db_session):
        """Test retrieving episode memories"""
        from services.memory.episodic_memory_service import EpisodicMemoryService
        from database_models import EpisodeMemory
        
        service = EpisodicMemoryService(mock_db_session)
        
        # Mock query results
        mock_memories = [
            EpisodeMemory(
                id=1,
                episode_id="ep123",
                user_id="user456",
                memory_type="agent_decision",
                agent_name="screenwriter",
                content={"action": "generate"},
                quality_score=0.85,
                created_at=datetime.utcnow()
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_memories
        
        # Get memories
        memories = service.get_episode_memories("ep123")
        
        assert len(memories) == 1
        assert memories[0].episode_id == "ep123"


@pytest.mark.unit
class TestSemanticMemoryService:
    """Test SemanticMemoryService"""
    
    def test_store_knowledge(self, mock_db_session):
        """Test storing semantic knowledge"""
        from services.memory.semantic_memory_service import SemanticMemoryService
        
        service = SemanticMemoryService(mock_db_session)
        
        memory_data = SemanticMemoryCreate(
            user_id="user456",
            category=KnowledgeCategory.USER_PREFERENCE,
            knowledge_key="preferred_style",
            knowledge_value={"style": "cinematic"},
            confidence_score=0.9,
            importance_score=0.8
        )
        
        result = service.store_knowledge(memory_data)
        
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
    
    def test_calculate_decay_score(self, mock_db_session):
        """Test decay score calculation"""
        from services.memory.semantic_memory_service import SemanticMemoryService
        from database_models import SemanticMemory
        
        service = SemanticMemoryService(mock_db_session)
        
        # Create memory with known age
        old_memory = SemanticMemory(
            id=1,
            user_id="user456",
            category="user_preference",
            knowledge_key="test",
            knowledge_value={},
            confidence_score=0.9,
            importance_score=0.8,
            access_count=5,
            created_at=datetime.utcnow() - timedelta(days=30),
            last_accessed_at=datetime.utcnow() - timedelta(days=15)
        )
        
        score = service._calculate_decay_score(old_memory)
        
        # Score should be between 0 and 1
        assert 0 <= score <= 1
        # Higher importance and access should increase score
        assert score > 0


@pytest.mark.unit
class TestConsolidationService:
    """Test ConsolidationService"""
    
    def test_extract_success_patterns(self, mock_db_session):
        """Test success pattern extraction"""
        from services.memory.consolidation_service import ConsolidationService
        from database_models import EpisodeMemory
        
        service = ConsolidationService(mock_db_session)
        
        # Create high-quality memories
        memories = [
            EpisodeMemory(
                id=1,
                episode_id="ep123",
                user_id="user456",
                memory_type="agent_decision",
                agent_name="screenwriter",
                content={"action": "generate"},
                context={"style": "cinematic"},
                quality_score=0.85,
                created_at=datetime.utcnow()
            ),
            EpisodeMemory(
                id=2,
                episode_id="ep123",
                user_id="user456",
                memory_type="agent_decision",
                agent_name="screenwriter",
                content={"action": "generate"},
                context={"style": "cinematic"},
                quality_score=0.90,
                created_at=datetime.utcnow()
            )
        ]
        
        patterns = service._extract_success_patterns(memories, min_quality=0.7)
        
        # Should identify pattern for screenwriter
        assert len(patterns) > 0
        assert patterns[0]['agent_name'] == "screenwriter"
        assert patterns[0]['avg_quality'] >= 0.7
    
    def test_extract_failure_patterns(self, mock_db_session):
        """Test failure pattern extraction"""
        from services.memory.consolidation_service import ConsolidationService
        from database_models import EpisodeMemory
        
        service = ConsolidationService(mock_db_session)
        
        # Create low-quality memories
        memories = [
            EpisodeMemory(
                id=1,
                episode_id="ep123",
                user_id="user456",
                memory_type="agent_decision",
                agent_name="screenwriter",
                content={"action": "generate"},
                context={"rushed": True},
                quality_score=0.3,
                created_at=datetime.utcnow()
            )
        ]
        
        patterns = service._extract_failure_patterns(memories)
        
        # Should identify failure pattern
        assert len(patterns) > 0
        assert patterns[0]['agent_name'] == "screenwriter"


@pytest.mark.unit
class TestMemoryManager:
    """Test MemoryManager unified interface"""
    
    def test_initialization(self, mock_db_session):
        """Test MemoryManager initialization"""
        from services.memory.memory_manager import MemoryManager
        
        manager = MemoryManager(mock_db_session)
        
        assert manager.db == mock_db_session
        assert manager.episodic_service is not None
        assert manager.semantic_service is not None
        assert manager.user_profile_service is not None
        assert manager.consolidation_service is not None
    
    def test_record_agent_decision(self, mock_db_session):
        """Test recording agent decision"""
        from services.memory.memory_manager import MemoryManager
        
        manager = MemoryManager(mock_db_session)
        
        # Mock the episodic service
        with patch.object(manager.episodic_service, 'create_memory') as mock_create:
            mock_create.return_value = Mock(id=1, episode_id="ep123")
            
            result = manager.record_agent_decision(
                episode_id="ep123",
                user_id="user456",
                agent_name="screenwriter",
                decision_context={"action": "generate"},
                quality_score=0.85
            )
            
            assert mock_create.called
            assert result.episode_id == "ep123"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])