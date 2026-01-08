"""
Integration Tests for Memory Services

Tests memory services working together with real database.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import get_db
from services.memory import (
    MemoryManager,
    MemoryType,
    KnowledgeCategory,
)


@pytest.fixture
def db_session():
    """Get a real database session"""
    return next(get_db())


@pytest.fixture
def memory_manager(db_session):
    """Create a MemoryManager instance"""
    return MemoryManager(db_session)


@pytest.fixture
def test_user_id():
    """Generate unique test user ID"""
    return f"test_user_{datetime.utcnow().timestamp()}"


@pytest.fixture
def test_episode_id():
    """Generate unique test episode ID"""
    return f"test_episode_{datetime.utcnow().timestamp()}"


@pytest.mark.integration
@pytest.mark.requires_db
class TestEpisodicMemoryIntegration:
    """Integration tests for episodic memory"""
    
    def test_create_and_retrieve_memory(self, memory_manager, test_user_id, test_episode_id):
        """Test creating and retrieving episodic memory"""
        # Create memory
        memory = memory_manager.record_agent_decision(
            episode_id=test_episode_id,
            user_id=test_user_id,
            agent_name="screenwriter",
            decision_context={
                "action": "generate_script",
                "input": "A story about AI"
            },
            outcome={"success": True, "length": 1500},
            quality_score=0.85
        )
        
        assert memory is not None
        assert memory.episode_id == test_episode_id
        assert memory.agent_name == "screenwriter"
        assert memory.quality_score == 0.85
        
        # Retrieve memories
        memories = memory_manager.get_episode_context(test_episode_id)
        assert len(memories) > 0
        assert memories[0].episode_id == test_episode_id
    
    def test_agent_history(self, memory_manager, test_user_id, test_episode_id):
        """Test retrieving agent history"""
        # Create multiple memories
        for i in range(3):
            memory_manager.record_agent_decision(
                episode_id=f"{test_episode_id}_{i}",
                user_id=test_user_id,
                agent_name="storyboard_artist",
                decision_context={"scene": i + 1},
                quality_score=0.8 + (i * 0.05)
            )
        
        # Get agent history
        history = memory_manager.get_agent_history("storyboard_artist", limit=10)
        assert len(history) >= 3
        
        # Verify ordering (most recent first)
        for i in range(len(history) - 1):
            assert history[i].created_at >= history[i + 1].created_at


@pytest.mark.integration
@pytest.mark.requires_db
class TestSemanticMemoryIntegration:
    """Integration tests for semantic memory"""
    
    def test_store_and_retrieve_knowledge(self, memory_manager, test_user_id, test_episode_id):
        """Test storing and retrieving semantic knowledge"""
        # Store knowledge
        knowledge = memory_manager.store_learned_knowledge(
            user_id=test_user_id,
            category=KnowledgeCategory.USER_PREFERENCE,
            knowledge_key="preferred_genre",
            knowledge_value={
                "genre": "sci-fi",
                "sub_genres": ["cyberpunk", "space opera"]
            },
            source_episode=test_episode_id,
            confidence=0.9,
            importance=0.8
        )
        
        assert knowledge is not None
        assert knowledge.knowledge_key == "preferred_genre"
        assert knowledge.confidence_score == 0.9
        
        # Retrieve knowledge
        retrieved = memory_manager.retrieve_knowledge(test_user_id, "preferred_genre")
        assert retrieved is not None
        assert retrieved.knowledge_key == "preferred_genre"
        assert retrieved.knowledge_value["genre"] == "sci-fi"
    
    def test_knowledge_by_category(self, memory_manager, test_user_id, test_episode_id):
        """Test retrieving knowledge by category"""
        # Store multiple knowledge items
        categories = [
            KnowledgeCategory.USER_PREFERENCE,
            KnowledgeCategory.GENERATION_PATTERN,
            KnowledgeCategory.USER_PREFERENCE
        ]
        
        for i, category in enumerate(categories):
            memory_manager.store_learned_knowledge(
                user_id=test_user_id,
                category=category,
                knowledge_key=f"test_key_{i}",
                knowledge_value={"data": i},
                confidence=0.8,
                importance=0.7
            )
        
        # Get by category
        preferences = memory_manager.get_knowledge_by_category(
            test_user_id,
            KnowledgeCategory.USER_PREFERENCE
        )
        
        assert len(preferences) >= 2
        for pref in preferences:
            assert pref.category == KnowledgeCategory.USER_PREFERENCE.value
    
    def test_update_existing_knowledge(self, memory_manager, test_user_id):
        """Test updating existing knowledge"""
        # Store initial knowledge
        initial = memory_manager.store_learned_knowledge(
            user_id=test_user_id,
            category=KnowledgeCategory.USER_PREFERENCE,
            knowledge_key="video_style",
            knowledge_value={"style": "cinematic"},
            confidence=0.7,
            importance=0.6
        )
        
        # Store again with same key - should retrieve existing
        updated = memory_manager.store_learned_knowledge(
            user_id=test_user_id,
            category=KnowledgeCategory.USER_PREFERENCE,
            knowledge_key="video_style",
            knowledge_value={"style": "cinematic", "quality": "high"},
            confidence=0.9,
            importance=0.8
        )
        
        # Retrieve to verify
        retrieved = memory_manager.retrieve_knowledge(test_user_id, "video_style")
        assert retrieved is not None
        # Knowledge key should match
        assert retrieved.knowledge_key == "video_style"
        # Should have been accessed (increments access count)
        assert retrieved.access_count >= 1


@pytest.mark.integration
@pytest.mark.requires_db
class TestUserProfileIntegration:
    """Integration tests for user profile"""
    
    def test_create_and_get_profile(self, memory_manager, test_user_id):
        """Test creating and retrieving user profile"""
        # Get or create profile
        profile = memory_manager.get_user_profile(test_user_id)
        
        assert profile is not None
        assert profile.user_id == test_user_id
        assert profile.preferences is not None
    
    def test_update_preferences(self, memory_manager, test_user_id):
        """Test updating user preferences"""
        # First ensure profile exists
        profile = memory_manager.get_user_profile(test_user_id)
        assert profile is not None
        
        # Update preference
        updated = memory_manager.update_user_preference(
            test_user_id,
            "video_style",
            "cinematic"
        )
        
        # May return None if profile doesn't exist, but we created it above
        # Retrieve preference to verify
        style = memory_manager.get_user_preference(test_user_id, "video_style")
        assert style == "cinematic"
    
    def test_record_feedback(self, memory_manager, test_user_id, test_episode_id):
        """Test recording user feedback"""
        # First ensure profile exists
        profile = memory_manager.get_user_profile(test_user_id)
        assert profile is not None
        
        # Record positive feedback
        updated_profile = memory_manager.record_user_feedback_to_profile(
            test_user_id,
            "positive",
            {
                "episode_id": test_episode_id,
                "rating": 5,
                "comment": "Excellent!"
            }
        )
        
        # Verify feedback was recorded by retrieving profile again
        profile_after = memory_manager.get_user_profile(test_user_id)
        assert profile_after is not None
        assert len(profile_after.feedback_history) > 0
        
        # Check if positive feedback exists
        assert "positive" in profile_after.feedback_history


@pytest.mark.integration
@pytest.mark.requires_db
class TestConsolidationIntegration:
    """Integration tests for memory consolidation"""
    
    def test_consolidate_episode(self, memory_manager, test_user_id, test_episode_id):
        """Test consolidating episode to semantic memory"""
        # Create multiple high-quality memories
        for i in range(5):
            memory_manager.record_agent_decision(
                episode_id=test_episode_id,
                user_id=test_user_id,
                agent_name="screenwriter",
                decision_context={
                    "action": f"generate_scene_{i}",
                    "style": "cinematic",
                    "scene": i + 1
                },
                outcome={"success": True},
                quality_score=0.8 + (i * 0.02)
            )
        
        # Consolidate
        result = memory_manager.consolidate_episode_to_semantic(
            episode_id=test_episode_id,
            user_id=test_user_id,
            min_quality_score=0.7
        )
        
        assert result is not None
        assert result['episode_id'] == test_episode_id
        assert result['insights_extracted'] >= 0
        assert result['patterns_identified'] >= 0
        assert 'processing_time_ms' in result
    
    def test_consolidation_with_failures(self, memory_manager, test_user_id, test_episode_id):
        """Test consolidation with both success and failure patterns"""
        # Create mixed quality memories
        qualities = [0.9, 0.85, 0.4, 0.3, 0.88]
        
        for i, quality in enumerate(qualities):
            memory_manager.record_agent_decision(
                episode_id=test_episode_id,
                user_id=test_user_id,
                agent_name="image_generator",
                decision_context={
                    "action": f"generate_image_{i}",
                    "rushed": quality < 0.5
                },
                outcome={"success": quality >= 0.5},
                quality_score=quality
            )
        
        # Consolidate
        result = memory_manager.consolidate_episode_to_semantic(
            episode_id=test_episode_id,
            user_id=test_user_id,
            min_quality_score=0.7
        )
        
        # Should extract both success and failure patterns
        assert result['insights_extracted'] > 0
    
    def test_consolidation_history(self, memory_manager, test_user_id, test_episode_id):
        """Test retrieving consolidation history"""
        # Create and consolidate episode
        memory_manager.record_agent_decision(
            episode_id=test_episode_id,
            user_id=test_user_id,
            agent_name="screenwriter",
            decision_context={"action": "generate"},
            quality_score=0.85
        )
        
        memory_manager.consolidate_episode_to_semantic(
            episode_id=test_episode_id,
            user_id=test_user_id
        )
        
        # Get history (returns list of dicts, not objects)
        history = memory_manager.get_consolidation_history(
            episode_id=test_episode_id,
            limit=10
        )
        
        assert len(history) > 0
        # History items are dicts, not objects
        assert history[0]['episode_id'] == test_episode_id


@pytest.mark.integration
@pytest.mark.requires_db
class TestMemoryOverviewIntegration:
    """Integration tests for memory overview"""
    
    def test_complete_overview(self, memory_manager, test_user_id, test_episode_id):
        """Test getting complete memory overview"""
        # First ensure profile exists
        profile = memory_manager.get_user_profile(test_user_id)
        assert profile is not None
        
        # Create episodic memories
        memory_manager.record_agent_decision(
            episode_id=test_episode_id,
            user_id=test_user_id,
            agent_name="screenwriter",
            decision_context={"action": "generate"},
            quality_score=0.85
        )
        
        # Store semantic knowledge
        memory_manager.store_learned_knowledge(
            user_id=test_user_id,
            category=KnowledgeCategory.USER_PREFERENCE,
            knowledge_key="test_pref",
            knowledge_value={"data": "test"},
            confidence=0.9,
            importance=0.8
        )
        
        # Update profile preference
        memory_manager.update_user_preference(test_user_id, "style", "cinematic")
        
        # Get overview
        overview = memory_manager.get_memory_overview(test_user_id)
        
        assert overview is not None
        assert overview['user_id'] == test_user_id
        assert 'episodic_memory' in overview
        assert 'semantic_memory' in overview
        assert 'profile' in overview
        
        # Verify counts
        assert overview['episodic_memory']['total_count'] > 0
        assert overview['semantic_memory']['total_count'] > 0
        # Profile should exist since we created it at the start
        assert overview['profile']['has_profile'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])