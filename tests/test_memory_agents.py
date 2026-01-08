"""
Test Memory-Augmented Agents

Tests the integration of memory system with agents.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from database import get_db
from services.memory import MemoryManager
from agents.memory_augmented_agent import MemoryAugmentedAgent, MemoryConfig


def test_memory_augmented_agent_initialization():
    """Test basic initialization of memory-augmented agent"""
    print("\n=== Testing Memory-Augmented Agent Initialization ===")
    
    # Test with memory enabled
    agent = MemoryAugmentedAgent(
        agent_name="test_agent",
        enable_memory=True
    )
    
    print(f"✓ Agent created: {agent.agent_name}")
    print(f"  - Memory enabled: {agent.enable_memory}")
    print(f"  - Max context: {agent.max_memory_context}")
    print(f"  - Min relevance: {agent.min_relevance_score}")
    
    assert agent.agent_name == "test_agent"
    assert agent.enable_memory is True
    
    # Test with memory disabled
    agent_disabled = MemoryAugmentedAgent(
        agent_name="test_agent_disabled",
        enable_memory=False
    )
    
    print(f"✓ Agent created with memory disabled")
    assert agent_disabled.enable_memory is False
    
    print("✓ Initialization test PASSED\n")
    return True


def test_memory_recording():
    """Test recording agent decisions"""
    print("\n=== Testing Memory Recording ===")
    
    agent = MemoryAugmentedAgent(
        agent_name="test_recorder",
        enable_memory=True
    )
    
    # Generate unique IDs
    timestamp = datetime.utcnow().timestamp()
    episode_id = f"test_episode_{timestamp}"
    user_id = f"test_user_{timestamp}"
    
    # Record a decision
    success = agent.record_decision(
        episode_id=episode_id,
        user_id=user_id,
        decision_context={
            "action": "test_action",
            "input": "test input"
        },
        outcome={
            "success": True,
            "result": "test result"
        },
        quality_score=0.85
    )
    
    print(f"✓ Decision recorded: {success}")
    assert success is True
    
    # Retrieve the decision
    if agent.memory_manager:
        memories = agent.memory_manager.get_episode_context(episode_id)
        print(f"✓ Retrieved {len(memories)} memories")
        assert len(memories) > 0
        assert memories[0].agent_name == "test_recorder"
        assert memories[0].quality_score == 0.85
    
    print("✓ Memory recording test PASSED\n")
    return True


def test_memory_retrieval():
    """Test retrieving relevant memories"""
    print("\n=== Testing Memory Retrieval ===")
    
    agent = MemoryAugmentedAgent(
        agent_name="test_retriever",
        enable_memory=True
    )
    
    timestamp = datetime.utcnow().timestamp()
    episode_id = f"test_episode_{timestamp}"
    user_id = f"test_user_{timestamp}"
    
    # Record multiple decisions
    for i in range(3):
        agent.record_decision(
            episode_id=f"{episode_id}_{i}",
            user_id=user_id,
            decision_context={
                "action": f"action_{i}",
                "iteration": i
            },
            outcome={"success": True},
            quality_score=0.7 + (i * 0.1)
        )
    
    print(f"✓ Recorded 3 decisions")
    
    # Retrieve relevant memories
    memories = agent.get_relevant_memories(
        user_id=user_id,
        context={"action": "test"}
    )
    
    print(f"✓ Retrieved {len(memories)} relevant memories")
    
    # Verify memories are filtered by quality
    for memory in memories:
        if memory.get('type') == 'agent_decision':
            assert memory['quality_score'] >= agent.min_relevance_score
    
    print("✓ Memory retrieval test PASSED\n")
    return True


def test_prompt_augmentation():
    """Test prompt augmentation with memory"""
    print("\n=== Testing Prompt Augmentation ===")
    
    agent = MemoryAugmentedAgent(
        agent_name="test_augmenter",
        enable_memory=True
    )
    
    timestamp = datetime.utcnow().timestamp()
    user_id = f"test_user_{timestamp}"
    
    # Record a high-quality decision
    agent.record_decision(
        episode_id=f"test_ep_{timestamp}",
        user_id=user_id,
        decision_context={
            "action": "generate_content",
            "style": "creative"
        },
        outcome={"success": True},
        quality_score=0.9
    )
    
    # Test prompt augmentation
    base_prompt = "Generate creative content."
    augmented_prompt = agent.augment_prompt_with_memory(
        base_prompt=base_prompt,
        user_id=user_id,
        context={"action": "generate"}
    )
    
    print(f"✓ Base prompt length: {len(base_prompt)} chars")
    print(f"✓ Augmented prompt length: {len(augmented_prompt)} chars")
    
    # Augmented prompt should be longer (contains memory context)
    if agent.enable_memory:
        assert len(augmented_prompt) >= len(base_prompt)
        assert "MEMORY_CONTEXT" in augmented_prompt or augmented_prompt == base_prompt
    
    print("✓ Prompt augmentation test PASSED\n")
    return True


def test_user_preferences():
    """Test user preference retrieval"""
    print("\n=== Testing User Preferences ===")
    
    agent = MemoryAugmentedAgent(
        agent_name="test_prefs",
        enable_memory=True
    )
    
    timestamp = datetime.utcnow().timestamp()
    user_id = f"test_user_{timestamp}"
    
    # Get or create user profile
    if agent.memory_manager:
        profile = agent.memory_manager.get_user_profile(user_id)
        print(f"✓ User profile created: {profile.user_id}")
        
        # Update preferences
        agent.memory_manager.update_user_preference(
            user_id=user_id,
            preference_key="style",
            preference_value="cinematic"
        )
        
        # Retrieve preferences
        prefs = agent.get_user_preferences(user_id)
        print(f"✓ Retrieved preferences: {list(prefs.keys())}")
        
        if prefs:
            assert "style" in prefs
            assert prefs["style"] == "cinematic"
    
    print("✓ User preferences test PASSED\n")
    return True


def test_agent_statistics():
    """Test agent statistics"""
    print("\n=== Testing Agent Statistics ===")
    
    agent = MemoryAugmentedAgent(
        agent_name="test_stats",
        enable_memory=True
    )
    
    timestamp = datetime.utcnow().timestamp()
    user_id = f"test_user_{timestamp}"
    
    # Record some decisions
    for i in range(5):
        agent.record_decision(
            episode_id=f"test_ep_{timestamp}_{i}",
            user_id=user_id,
            decision_context={"iteration": i},
            outcome={"success": True},
            quality_score=0.7 + (i * 0.05)
        )
    
    # Get statistics
    stats = agent.get_agent_statistics()
    
    print(f"✓ Agent statistics:")
    print(f"  - Memory enabled: {stats.get('memory_enabled')}")
    print(f"  - Total decisions: {stats.get('total_decisions', 0)}")
    print(f"  - Avg quality: {stats.get('avg_quality', 0):.2f}")
    print(f"  - High quality rate: {stats.get('high_quality_rate', 0):.2f}")
    
    assert stats['memory_enabled'] is True
    assert stats['total_decisions'] >= 5
    
    print("✓ Agent statistics test PASSED\n")
    return True


def test_memory_config():
    """Test memory configuration"""
    print("\n=== Testing Memory Configuration ===")
    
    # Test default config
    config_default = MemoryConfig.default()
    print(f"✓ Default config:")
    print(f"  - Enable memory: {config_default.enable_memory}")
    print(f"  - Max context: {config_default.max_memory_context}")
    
    assert config_default.enable_memory is True
    assert config_default.max_memory_context == 5
    
    # Test disabled config
    config_disabled = MemoryConfig.disabled()
    print(f"✓ Disabled config:")
    print(f"  - Enable memory: {config_disabled.enable_memory}")
    
    assert config_disabled.enable_memory is False
    
    # Test minimal config
    config_minimal = MemoryConfig.minimal()
    print(f"✓ Minimal config:")
    print(f"  - Max context: {config_minimal.max_memory_context}")
    print(f"  - Min relevance: {config_minimal.min_relevance_score}")
    
    assert config_minimal.max_memory_context == 3
    assert config_minimal.min_relevance_score == 0.8
    
    print("✓ Memory configuration test PASSED\n")
    return True


def main():
    """Run all tests"""
    print("=" * 70)
    print("Memory-Augmented Agents Test Suite")
    print("=" * 70)
    
    tests = [
        ("Initialization", test_memory_augmented_agent_initialization),
        ("Memory Recording", test_memory_recording),
        ("Memory Retrieval", test_memory_retrieval),
        ("Prompt Augmentation", test_prompt_augmentation),
        ("User Preferences", test_user_preferences),
        ("Agent Statistics", test_agent_statistics),
        ("Memory Configuration", test_memory_config),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} test PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} test FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} test FAILED with error:")
            print(f"  {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print(f"Test Summary: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)