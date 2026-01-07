"""
Tests for Intent Analyzer Service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from services.intent_analyzer import (
    IntentAnalyzer,
    IntentType,
    ComplexityLevel,
    Intent
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def intent_analyzer(mock_db):
    """Create IntentAnalyzer instance"""
    return IntentAnalyzer(mock_db)


class TestQuickRuleBasedDetection:
    """Test quick rule-based intent detection"""
    
    def test_video_generation_intent(self, intent_analyzer):
        """Test detection of video generation intent"""
        test_cases = [
            "Create a video about space exploration",
            "Make a film about robots",
            "Generate a short clip of nature",
            "创建一个关于太空的视频",
        ]
        
        for text in test_cases:
            intent = intent_analyzer._quick_rule_based_detection(text, {})
            assert intent.type == IntentType.VIDEO_GENERATION
            assert intent.confidence > 0.9
    
    def test_chat_intent(self, intent_analyzer):
        """Test detection of chat intent"""
        test_cases = [
            "What can you do?",
            "How does this work?",
            "Help me understand",
            "Tell me about your features",
            "你能做什么？",
        ]
        
        for text in test_cases:
            intent = intent_analyzer._quick_rule_based_detection(text, {})
            assert intent.type == IntentType.CHAT
            assert intent.confidence > 0.9
    
    def test_modification_intent(self, intent_analyzer):
        """Test detection of modification intent"""
        test_cases = [
            "Make it darker",
            "Change the color to blue",
            "Edit the scene",
            "Adjust the brightness",
        ]
        
        context = {"has_existing_content": True}
        
        for text in test_cases:
            intent = intent_analyzer._quick_rule_based_detection(text, context)
            assert intent.type == IntentType.MODIFICATION
            assert intent.confidence > 0.9
    
    def test_ambiguous_input(self, intent_analyzer):
        """Test handling of ambiguous input"""
        text = "I want something"
        intent = intent_analyzer._quick_rule_based_detection(text, {})
        assert intent.confidence < 0.9


class TestParameterExtraction:
    """Test parameter extraction from user input"""
    
    def test_extract_duration(self, intent_analyzer):
        """Test duration extraction"""
        test_cases = [
            ("Create a 2 minute video", 120),
            ("Make a 30 second clip", 30),
            ("Generate a 1:30 video", 90),
            ("Create a video", None),
        ]
        
        for text, expected in test_cases:
            duration = intent_analyzer._extract_duration(text)
            assert duration == expected
    
    def test_extract_characters(self, intent_analyzer):
        """Test character extraction"""
        test_cases = [
            ("Video with three friends", ["three friend"]),
            ("Story about a hero and villain", ["hero", "villain"]),
            ("Create video with 2 characters", ["2 character"]),
            ("Simple video", []),
        ]
        
        for text, expected in test_cases:
            characters = intent_analyzer._extract_character_mentions(text)
            assert len(characters) == len(expected)
    
    def test_extract_theme(self, intent_analyzer):
        """Test theme extraction"""
        test_cases = [
            ("Create a video about space exploration", "space exploration"),
            ("Story of a magical forest", "a magical forest"),
            ("Video about ancient temples", "ancient temples"),
        ]
        
        for text, expected in test_cases:
            theme = intent_analyzer._extract_theme(text)
            assert expected in theme.lower()
    
    def test_extract_style(self, intent_analyzer):
        """Test style extraction"""
        test_cases = [
            ("Create a cinematic video", "cinematic"),
            ("Make an anime style clip", "anime"),
            ("Realistic footage", "realistic"),
            ("Simple video", None),
        ]
        
        for text, expected in test_cases:
            style = intent_analyzer._extract_style(text)
            assert style == expected
    
    def test_extract_mood(self, intent_analyzer):
        """Test mood extraction"""
        test_cases = [
            ("Create a happy video", "happy"),
            ("Make a suspenseful thriller", "suspenseful"),
            ("Peaceful nature scene", "peaceful"),
            ("Simple video", None),
        ]
        
        for text, expected in test_cases:
            mood = intent_analyzer._extract_mood(text)
            assert mood == expected


class TestComplexityAssessment:
    """Test complexity assessment"""
    
    def test_simple_complexity(self, intent_analyzer):
        """Test simple complexity assessment"""
        parameters = {
            "theme": "flower",
            "duration": 30
        }
        
        complexity = intent_analyzer.assess_complexity(parameters)
        assert complexity == ComplexityLevel.SIMPLE
    
    def test_medium_complexity(self, intent_analyzer):
        """Test medium complexity assessment"""
        parameters = {
            "theme": "space exploration",
            "characters": ["astronaut", "alien"],
            "scenes": ["spaceship", "planet"],
            "duration": 60
        }
        
        complexity = intent_analyzer.assess_complexity(parameters)
        assert complexity == ComplexityLevel.MEDIUM
    
    def test_complex_complexity(self, intent_analyzer):
        """Test complex complexity assessment"""
        parameters = {
            "theme": "epic adventure",
            "characters": ["hero", "villain", "sidekick", "mentor"],
            "scenes": ["castle", "forest", "mountain", "cave", "city"],
            "duration": 120,
            "special_requirements": ["dramatic lighting", "special effects"]
        }
        
        complexity = intent_analyzer.assess_complexity(parameters)
        assert complexity == ComplexityLevel.COMPLEX


class TestIntegration:
    """Integration tests for full intent analysis"""
    
    @pytest.mark.asyncio
    async def test_simple_video_request(self, intent_analyzer):
        """Test analysis of simple video request"""
        user_input = "Create a video about a flower blooming"
        
        intent = await intent_analyzer.analyze(user_input, {})
        
        assert intent.type == IntentType.VIDEO_GENERATION
        assert intent.confidence > 0.9
    
    @pytest.mark.asyncio
    async def test_complex_video_request(self, intent_analyzer):
        """Test analysis of complex video request"""
        user_input = "Create a 2-minute cinematic video about three friends exploring an ancient temple with dramatic lighting"
        
        intent = await intent_analyzer.analyze(user_input, {})
        
        assert intent.type == IntentType.VIDEO_GENERATION
        assert intent.confidence > 0.9
        
        # Extract parameters
        parameters = await intent_analyzer.extract_parameters(user_input, intent.type)
        
        assert parameters.get("duration") == 120
        assert "temple" in parameters.get("theme", "").lower()
        assert parameters.get("style") == "cinematic"
        
        # Assess complexity
        complexity = intent_analyzer.assess_complexity(parameters)
        assert complexity in [ComplexityLevel.MEDIUM, ComplexityLevel.COMPLEX]
    
    @pytest.mark.asyncio
    async def test_chat_request(self, intent_analyzer):
        """Test analysis of chat request"""
        user_input = "What can you help me with?"
        
        intent = await intent_analyzer.analyze(user_input, {})
        
        assert intent.type == IntentType.CHAT
        assert intent.confidence > 0.9
    
    @pytest.mark.asyncio
    async def test_empty_input(self, intent_analyzer):
        """Test handling of empty input"""
        intent = await intent_analyzer.analyze("", {})
        
        assert intent.type == IntentType.UNKNOWN
        assert intent.confidence == 0.0


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_very_long_input(self, intent_analyzer):
        """Test handling of very long input"""
        long_text = "Create a video " + "about space " * 100
        intent = intent_analyzer._quick_rule_based_detection(long_text, {})
        assert intent.type == IntentType.VIDEO_GENERATION
    
    def test_mixed_language(self, intent_analyzer):
        """Test handling of mixed language input"""
        text = "Create a video 关于 space exploration"
        intent = intent_analyzer._quick_rule_based_detection(text, {})
        assert intent.type == IntentType.VIDEO_GENERATION
    
    def test_special_characters(self, intent_analyzer):
        """Test handling of special characters"""
        text = "Create a video!!! @#$% about space???"
        intent = intent_analyzer._quick_rule_based_detection(text, {})
        assert intent.type == IntentType.VIDEO_GENERATION


# Test data for comprehensive testing
COMPREHENSIVE_TEST_CASES = [
    # (input, expected_intent, expected_confidence_threshold)
    ("Create a video about space", IntentType.VIDEO_GENERATION, 0.9),
    ("What can you do?", IntentType.CHAT, 0.9),
    ("Make it darker", IntentType.MODIFICATION, 0.6),  # Needs context
    ("Generate a 2-minute film about robots", IntentType.VIDEO_GENERATION, 0.9),
    ("How do I create a video?", IntentType.CHAT, 0.9),
    ("创建一个视频", IntentType.VIDEO_GENERATION, 0.9),
    ("帮助", IntentType.CHAT, 0.9),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("user_input,expected_intent,min_confidence", COMPREHENSIVE_TEST_CASES)
async def test_comprehensive_intent_detection(intent_analyzer, user_input, expected_intent, min_confidence):
    """Comprehensive test of intent detection"""
    context = {"has_existing_content": True} if expected_intent == IntentType.MODIFICATION else {}
    
    intent = await intent_analyzer.analyze(user_input, context)
    
    assert intent.type == expected_intent
    assert intent.confidence >= min_confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])