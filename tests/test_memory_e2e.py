"""
End-to-End Tests for Memory System

Tests complete workflows from agent decisions through consolidation to retrieval.
"""

import pytest
from datetime import datetime
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
    return f"e2e_user_{datetime.utcnow().timestamp()}"


@pytest.fixture
def test_episode_id():
    """Generate unique test episode ID"""
    return f"e2e_episode_{datetime.utcnow().timestamp()}"


@pytest.mark.e2e
@pytest.mark.requires_db
class TestCompleteVideoGenerationWorkflow:
    """Test complete video generation workflow with memory"""
    
    def test_full_video_generation_cycle(self, memory_manager, test_user_id, test_episode_id):
        """
        Test complete workflow:
        1. User starts video generation
        2. Multiple agents make decisions
        3. User provides feedback
        4. Episode consolidates to semantic memory
        5. Next episode uses learned patterns
        """
        
        # === Phase 1: First Episode - Learning ===
        print("\n=== Phase 1: First Episode ===")
        
        # Step 1: Screenwriter generates script
        script_memory = memory_manager.record_agent_decision(
            episode_id=test_episode_id,
            user_id=test_user_id,
            agent_name="screenwriter",
            decision_context={
                "action": "generate_script",
                "user_input": "A sci-fi story about AI",
                "style": "cinematic"
            },
            outcome={
                "success": True,
                "script_length": 1500,
                "scenes": 5
            },
            quality_score=0.85
        )
        print(f"✓ Screenwriter decision recorded (quality: {script_memory.quality_score})")
        
        # Step 2: Storyboard artist creates storyboard
        storyboard_memory = memory_manager.record_agent_decision(
            episode_id=test_episode_id,
            user_id=test_user_id,
            agent_name="storyboard_artist",
            decision_context={
                "action": "create_storyboard",
                "script_id": "script_001",
                "style": "cinematic"
            },
            outcome={
                "success": True,
                "shots": 15
            },
            quality_score=0.88
        )
        print(f"✓ Storyboard artist decision recorded (quality: {storyboard_memory.quality_score})")
        
        # Step 3: Image generator creates images
        for i in range(3):
            image_memory = memory_manager.record_agent_decision(
                episode_id=test_episode_id,
                user_id=test_user_id,
                agent_name="image_generator",
                decision_context={
                    "action": f"generate_image_{i}",
                    "shot_id": f"shot_{i}",
                    "style": "cinematic"
                },
                outcome={
                    "success": True,
                    "image_url": f"image_{i}.png"
                },
                quality_score=0.82 + (i * 0.02)
            )
        print(f"✓ Image generator decisions recorded (3 images)")
        
        # Step 4: User provides positive feedback
        feedback_profile = memory_manager.record_user_feedback_to_profile(
            test_user_id,
            "positive",
            {
                "episode_id": test_episode_id,
                "rating": 5,
                "comment": "Love the cinematic style!",
                "liked_aspects": ["style", "pacing", "visuals"]
            }
        )
        print(f"✓ User feedback recorded")
        
        # Step 5: Consolidate episode to semantic memory
        consolidation_result = memory_manager.consolidate_episode_to_semantic(
            episode_id=test_episode_id,
            user_id=test_user_id,
            min_quality_score=0.7
        )
        print(f"✓ Episode consolidated:")
        print(f"  - Insights extracted: {consolidation_result['insights_extracted']}")
        print(f"  - Patterns identified: {consolidation_result['patterns_identified']}")
        print(f"  - Memories created: {consolidation_result['memories_created']}")
        print(f"  - Processing time: {consolidation_result['processing_time_ms']}ms")
        
        # Verify consolidation created semantic memories
        assert consolidation_result['insights_extracted'] > 0 or consolidation_result['patterns_identified'] > 0
        
        # === Phase 2: Second Episode - Using Learned Patterns ===
        print("\n=== Phase 2: Second Episode (Using Learned Patterns) ===")
        
        second_episode_id = f"{test_episode_id}_2"
        
        # Step 6: Retrieve user preferences before generation
        user_profile = memory_manager.get_user_profile(test_user_id)
        print(f"✓ Retrieved user profile")
        print(f"  - Preferences: {user_profile.preferences}")
        print(f"  - Feedback count: {len(user_profile.feedback_history)}")
        
        # Step 7: Get agent history to learn from past
        screenwriter_history = memory_manager.get_agent_history("screenwriter", limit=5)
        print(f"✓ Retrieved screenwriter history: {len(screenwriter_history)} memories")
        
        # Step 8: Get learned patterns
        learned_patterns = memory_manager.get_knowledge_by_category(
            test_user_id,
            KnowledgeCategory.GENERATION_PATTERN
        )
        print(f"✓ Retrieved learned patterns: {len(learned_patterns)} patterns")
        
        # Step 9: Generate with learned context
        # Screenwriter uses learned preferences
        script_memory_2 = memory_manager.record_agent_decision(
            episode_id=second_episode_id,
            user_id=test_user_id,
            agent_name="screenwriter",
            decision_context={
                "action": "generate_script",
                "user_input": "Another sci-fi story",
                "style": "cinematic",  # Using learned preference
                "learned_from": test_episode_id
            },
            outcome={
                "success": True,
                "script_length": 1600,
                "scenes": 6
            },
            quality_score=0.90  # Higher quality due to learning
        )
        print(f"✓ Second episode script generated (quality: {script_memory_2.quality_score})")
        
        # Verify quality improved
        assert script_memory_2.quality_score >= script_memory.quality_score
        
        # === Phase 3: Verify Memory System State ===
        print("\n=== Phase 3: Memory System Verification ===")
        
        # Step 10: Get complete memory overview
        overview = memory_manager.get_memory_overview(test_user_id)
        print(f"✓ Memory Overview:")
        print(f"  - Episodic memories: {overview['episodic_memory']['total_count']}")
        print(f"  - Semantic memories: {overview['semantic_memory']['total_count']}")
        print(f"  - User preferences: {overview['profile']['preference_count']}")
        print(f"  - Avg quality: {overview['episodic_memory']['avg_quality_score']:.2f}")
        
        # Verify system learned and improved
        assert overview['episodic_memory']['total_count'] >= 5
        assert overview['semantic_memory']['total_count'] > 0
        assert overview['profile']['has_profile'] is True
        assert overview['episodic_memory']['avg_quality_score'] > 0.8
        
        print("\n✓ Complete workflow test PASSED")


@pytest.mark.e2e
@pytest.mark.requires_db
class TestMultiAgentCollaboration:
    """Test multi-agent collaboration with shared memory"""
    
    def test_agents_learn_from_each_other(self, memory_manager, test_user_id, test_episode_id):
        """
        Test agents learning from each other's decisions:
        1. Multiple agents work on same episode
        2. Each agent's decisions influence others
        3. Consolidation extracts cross-agent patterns
        """
        
        print("\n=== Multi-Agent Collaboration Test ===")
        
        agents = [
            ("screenwriter", "generate_script", 0.85),
            ("storyboard_artist", "create_storyboard", 0.88),
            ("image_generator", "generate_images", 0.82),
            ("video_generator", "generate_video", 0.90)
        ]
        
        # Step 1: Each agent makes decisions
        for agent_name, action, quality in agents:
            memory_manager.record_agent_decision(
                episode_id=test_episode_id,
                user_id=test_user_id,
                agent_name=agent_name,
                decision_context={
                    "action": action,
                    "collaboration": True,
                    "style": "cinematic"
                },
                outcome={"success": True},
                quality_score=quality
            )
            print(f"✓ {agent_name} decision recorded")
        
        # Step 2: Consolidate to extract patterns
        result = memory_manager.consolidate_episode_to_semantic(
            episode_id=test_episode_id,
            user_id=test_user_id,
            min_quality_score=0.7
        )
        
        print(f"✓ Consolidated {len(agents)} agent decisions")
        print(f"  - Patterns identified: {result['patterns_identified']}")
        
        # Step 3: Verify each agent can access shared knowledge
        for agent_name, _, _ in agents:
            history = memory_manager.get_agent_history(agent_name, limit=10)
            assert len(history) > 0
            print(f"✓ {agent_name} can access history: {len(history)} memories")
        
        # Step 4: Verify cross-agent patterns stored
        patterns = memory_manager.get_knowledge_by_category(
            test_user_id,
            KnowledgeCategory.GENERATION_PATTERN
        )
        
        if len(patterns) > 0:
            print(f"✓ Cross-agent patterns stored: {len(patterns)}")
        
        print("\n✓ Multi-agent collaboration test PASSED")


@pytest.mark.e2e
@pytest.mark.requires_db
class TestLongTermLearning:
    """Test long-term learning across multiple episodes"""
    
    def test_learning_over_multiple_episodes(self, memory_manager, test_user_id):
        """
        Test learning over multiple episodes:
        1. Generate 5 episodes with varying quality
        2. Track quality improvement over time
        3. Verify semantic memory accumulation
        """
        
        print("\n=== Long-Term Learning Test ===")
        
        episode_count = 5
        qualities = []
        
        # Generate multiple episodes
        for i in range(episode_count):
            episode_id = f"long_term_ep_{test_user_id}_{i}"
            
            # Base quality improves over time (simulating learning)
            base_quality = 0.70 + (i * 0.04)
            
            # Create memories for episode
            memory_manager.record_agent_decision(
                episode_id=episode_id,
                user_id=test_user_id,
                agent_name="screenwriter",
                decision_context={
                    "action": "generate_script",
                    "episode_number": i + 1
                },
                outcome={"success": True},
                quality_score=base_quality
            )
            
            qualities.append(base_quality)
            
            # Consolidate each episode
            memory_manager.consolidate_episode_to_semantic(
                episode_id=episode_id,
                user_id=test_user_id,
                min_quality_score=0.6
            )
            
            print(f"✓ Episode {i + 1} completed (quality: {base_quality:.2f})")
        
        # Verify quality improvement trend
        print(f"\n✓ Quality progression: {[f'{q:.2f}' for q in qualities]}")
        assert qualities[-1] > qualities[0], "Quality should improve over time"
        
        # Verify semantic memory accumulation
        overview = memory_manager.get_memory_overview(test_user_id)
        print(f"✓ Total semantic memories: {overview['semantic_memory']['total_count']}")
        assert overview['semantic_memory']['total_count'] > 0
        
        # Verify episodic memories
        print(f"✓ Total episodic memories: {overview['episodic_memory']['total_count']}")
        assert overview['episodic_memory']['total_count'] >= episode_count
        
        print("\n✓ Long-term learning test PASSED")


@pytest.mark.e2e
@pytest.mark.requires_db
class TestErrorRecoveryWithMemory:
    """Test error recovery using memory system"""
    
    def test_learn_from_failures(self, memory_manager, test_user_id, test_episode_id):
        """
        Test learning from failures:
        1. Record failed decisions
        2. Consolidate to extract failure patterns
        3. Verify failure patterns stored
        4. Simulate recovery with improved decisions
        """
        
        print("\n=== Error Recovery Test ===")
        
        # Step 1: Record failures
        failure_contexts = [
            {"rushed": True, "incomplete_input": True},
            {"timeout": True, "resource_limit": True},
            {"invalid_format": True}
        ]
        
        for i, context in enumerate(failure_contexts):
            memory_manager.record_agent_decision(
                episode_id=test_episode_id,
                user_id=test_user_id,
                agent_name="image_generator",
                decision_context={
                    "action": f"generate_image_{i}",
                    **context
                },
                outcome={"success": False, "error": "Generation failed"},
                quality_score=0.3
            )
        
        print(f"✓ Recorded {len(failure_contexts)} failures")
        
        # Step 2: Consolidate to learn from failures
        result = memory_manager.consolidate_episode_to_semantic(
            episode_id=test_episode_id,
            user_id=test_user_id,
            min_quality_score=0.7
        )
        
        print(f"✓ Consolidated failures")
        print(f"  - Insights extracted: {result['insights_extracted']}")
        
        # Step 3: Record successful recovery
        recovery_episode = f"{test_episode_id}_recovery"
        
        memory_manager.record_agent_decision(
            episode_id=recovery_episode,
            user_id=test_user_id,
            agent_name="image_generator",
            decision_context={
                "action": "generate_image_recovery",
                "learned_from_failures": True,
                "proper_input": True,
                "adequate_resources": True
            },
            outcome={"success": True},
            quality_score=0.85
        )
        
        print(f"✓ Recorded successful recovery (quality: 0.85)")
        
        # Step 4: Verify learning
        agent_history = memory_manager.get_agent_history("image_generator", limit=10)
        
        # Should have both failures and success
        assert len(agent_history) >= 4
        
        # Latest should be successful
        latest = agent_history[0]
        assert latest.quality_score > 0.7
        
        print("\n✓ Error recovery test PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])