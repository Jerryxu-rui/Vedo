"""
Test Memory Services

Basic tests to validate memory service functionality
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from database import get_db
from services.memory import (
    MemoryManager,
    MemoryType,
    KnowledgeCategory,
)


def test_episodic_memory():
    """Test episodic memory operations"""
    print("\n=== Testing Episodic Memory ===")
    
    db = next(get_db())
    memory = MemoryManager(db)
    
    # Create a test memory
    print("Creating episodic memory...")
    episodic = memory.record_agent_decision(
        episode_id="test_episode_001",
        user_id="test_user_001",
        agent_name="screenwriter",
        decision_context={
            "action": "generate_script",
            "input": "A story about AI",
            "timestamp": datetime.utcnow().isoformat()
        },
        outcome={
            "success": True,
            "script_length": 1500
        },
        quality_score=0.85
    )
    
    print(f"✓ Created memory: {episodic.id}")
    print(f"  - Episode: {episodic.episode_id}")
    print(f"  - Agent: {episodic.agent_name}")
    print(f"  - Quality: {episodic.quality_score}")
    
    # Retrieve episode memories
    print("\nRetrieving episode memories...")
    memories = memory.get_episode_context("test_episode_001")
    print(f"✓ Found {len(memories)} memories for episode")
    
    # Get agent history
    print("\nRetrieving agent history...")
    history = memory.get_agent_history("screenwriter", limit=10)
    print(f"✓ Found {len(history)} memories for agent")
    
    return True


def test_semantic_memory():
    """Test semantic memory operations"""
    print("\n=== Testing Semantic Memory ===")
    
    db = next(get_db())
    memory = MemoryManager(db)
    
    # Store knowledge
    print("Storing semantic knowledge...")
    semantic = memory.store_learned_knowledge(
        user_id="test_user_001",
        category=KnowledgeCategory.USER_PREFERENCE,
        knowledge_key="preferred_genre",
        knowledge_value={
            "genre": "sci-fi",
            "sub_genres": ["cyberpunk", "space opera"],
            "confidence": 0.9
        },
        source_episode="test_episode_001",
        confidence=0.9,
        importance=0.8
    )
    
    print(f"✓ Stored knowledge: {semantic.id}")
    print(f"  - Category: {semantic.category.value if hasattr(semantic.category, 'value') else semantic.category}")
    print(f"  - Key: {semantic.knowledge_key}")
    print(f"  - Confidence: {semantic.confidence_score}")
    
    # Retrieve knowledge
    print("\nRetrieving knowledge...")
    retrieved = memory.retrieve_knowledge("test_user_001", "preferred_genre")
    if retrieved:
        print(f"✓ Retrieved knowledge: {retrieved.knowledge_key}")
        print(f"  - Value: {retrieved.knowledge_value}")
    
    # Get by category
    print("\nRetrieving by category...")
    category_memories = memory.get_knowledge_by_category(
        "test_user_001",
        KnowledgeCategory.USER_PREFERENCE
    )
    print(f"✓ Found {len(category_memories)} memories in category")
    
    return True


def test_user_profile():
    """Test user profile operations"""
    print("\n=== Testing User Profile ===")
    
    db = next(get_db())
    memory = MemoryManager(db)
    
    # Get or create profile
    print("Getting user profile...")
    profile = memory.get_user_profile("test_user_001")
    print(f"✓ Profile ID: {profile.id}")
    print(f"  - User ID: {profile.user_id}")
    
    # Update preference
    print("\nUpdating user preference...")
    updated = memory.update_user_preference(
        "test_user_001",
        "video_style",
        "cinematic"
    )
    if updated:
        print(f"✓ Updated preference: video_style = cinematic")
    
    # Record feedback
    print("\nRecording user feedback...")
    feedback_profile = memory.record_user_feedback_to_profile(
        "test_user_001",
        "positive",
        {
            "episode_id": "test_episode_001",
            "rating": 5,
            "comment": "Great script!"
        }
    )
    if feedback_profile:
        print(f"✓ Recorded feedback")
    
    # Get preference
    print("\nRetrieving preference...")
    video_style = memory.get_user_preference("test_user_001", "video_style")
    print(f"✓ Video style preference: {video_style}")
    
    return True


def test_consolidation():
    """Test memory consolidation"""
    print("\n=== Testing Memory Consolidation ===")
    
    db = next(get_db())
    memory = MemoryManager(db)
    
    # Create multiple high-quality memories
    print("Creating multiple memories for consolidation...")
    for i in range(3):
        memory.record_agent_decision(
            episode_id="test_episode_002",
            user_id="test_user_001",
            agent_name="storyboard_artist",
            decision_context={
                "action": f"create_storyboard_{i}",
                "scene": i + 1
            },
            outcome={"success": True},
            quality_score=0.8 + (i * 0.05)
        )
    
    print(f"✓ Created 3 memories")
    
    # Consolidate
    print("\nConsolidating episode to semantic memory...")
    result = memory.consolidate_episode_to_semantic(
        episode_id="test_episode_002",
        user_id="test_user_001",
        min_quality_score=0.7
    )
    
    print(f"✓ Consolidation complete:")
    print(f"  - Insights extracted: {result['insights_extracted']}")
    print(f"  - Patterns identified: {result['patterns_identified']}")
    print(f"  - Memories created: {result['memories_created']}")
    print(f"  - Memories updated: {result['memories_updated']}")
    print(f"  - Memories pruned: {result['memories_pruned']}")
    print(f"  - Processing time: {result['processing_time_ms']}ms")
    
    return True


def test_memory_overview():
    """Test memory overview"""
    print("\n=== Testing Memory Overview ===")
    
    db = next(get_db())
    memory = MemoryManager(db)
    
    overview = memory.get_memory_overview("test_user_001")
    
    print(f"✓ Memory Overview for user: {overview['user_id']}")
    print(f"\nEpisodic Memory:")
    print(f"  - Total: {overview['episodic_memory']['total_count']}")
    print(f"  - By type: {overview['episodic_memory']['type_counts']}")
    print(f"  - Avg quality: {overview['episodic_memory']['avg_quality_score']:.2f}" if overview['episodic_memory']['avg_quality_score'] else "  - Avg quality: N/A")
    
    print(f"\nSemantic Memory:")
    print(f"  - Total: {overview['semantic_memory']['total_count']}")
    print(f"  - By category: {overview['semantic_memory']['by_category']}")
    print(f"  - Avg confidence: {overview['semantic_memory']['avg_confidence']:.2f}" if overview['semantic_memory']['total_count'] > 0 else "  - Avg confidence: N/A")
    
    print(f"\nUser Profile:")
    print(f"  - Has profile: {overview['profile']['has_profile']}")
    print(f"  - Preferences: {overview['profile']['preference_count']}")
    print(f"  - Feedback count: {overview['profile']['feedback_count']}")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Memory Services Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        tests = [
            ("Episodic Memory", test_episodic_memory),
            ("Semantic Memory", test_semantic_memory),
            ("User Profile", test_user_profile),
            ("Memory Consolidation", test_consolidation),
            ("Memory Overview", test_memory_overview),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                    print(f"\n✓ {test_name} test PASSED")
                else:
                    failed += 1
                    print(f"\n✗ {test_name} test FAILED")
            except Exception as e:
                failed += 1
                print(f"\n✗ {test_name} test FAILED with error:")
                print(f"  {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"Test Summary: {passed} passed, {failed} failed")
        print("=" * 60)
        
        return failed == 0
        
    except Exception as e:
        print(f"\n✗ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)