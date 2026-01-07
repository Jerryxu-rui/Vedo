"""
Tests for Parameter Extractor Service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from services.parameter_extractor import (
    ParameterExtractor,
    VideoParameters
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def parameter_extractor(mock_db):
    """Create ParameterExtractor instance"""
    return ParameterExtractor(mock_db)


class TestFallbackExtraction:
    """Test fallback extraction methods"""
    
    def test_extract_style_fallback(self, parameter_extractor):
        """Test fallback style extraction"""
        test_cases = [
            ("Create a cinematic video", "cinematic"),
            ("Make an anime style clip", "anime"),
            ("Realistic footage", "realistic"),
            ("Simple video", None),
        ]
        
        for text, expected in test_cases:
            style = parameter_extractor._extract_style_fallback(text)
            assert style == expected
    
    def test_extract_duration_fallback(self, parameter_extractor):
        """Test fallback duration extraction"""
        test_cases = [
            ("Create a 2 min video", 120),
            ("Make a 30 sec clip", 30),
            ("Generate a 1:30 video", 90),
            ("Create a video", None),
        ]
        
        for text, expected in test_cases:
            duration = parameter_extractor._extract_duration_fallback(text)
            assert duration == expected
    
    def test_extract_mood_fallback(self, parameter_extractor):
        """Test fallback mood extraction"""
        test_cases = [
            ("Create a happy video", "happy"),
            ("Make a sad story", "sad"),
            ("Suspenseful thriller", "suspenseful"),
            ("Simple video", None),
        ]
        
        for text, expected in test_cases:
            mood = parameter_extractor._extract_mood_fallback(text)
            assert mood == expected


class TestParameterValidation:
    """Test parameter validation"""
    
    def test_validate_empty_theme(self, parameter_extractor):
        """Test validation adds default theme if empty"""
        params = {"theme": ""}
        validated = parameter_extractor._validate_parameters(params)
        assert validated["theme"] == "Untitled Video"
    
    def test_validate_duration(self, parameter_extractor):
        """Test duration validation"""
        test_cases = [
            ({"duration": 120}, 120),
            ({"duration": 120.5}, 120),
            ({"duration": -10}, None),
            ({"duration": "invalid"}, None),
        ]
        
        for params, expected in test_cases:
            validated = parameter_extractor._validate_parameters(params)
            assert validated.get("duration") == expected
    
    def test_validate_lists(self, parameter_extractor):
        """Test list field validation"""
        params = {
            "theme": "test",
            "characters": "not a list",
            "scenes": None,
            "special_requirements": []
        }
        
        validated = parameter_extractor._validate_parameters(params)
        assert isinstance(validated["characters"], list)
        assert isinstance(validated["scenes"], list)
        assert isinstance(validated["special_requirements"], list)


class TestSceneEstimation:
    """Test scene and shot count estimation"""
    
    def test_estimate_scene_count_explicit(self, parameter_extractor):
        """Test scene count with explicit scenes"""
        params = VideoParameters(
            theme="test",
            scenes=[
                {"name": "Scene 1", "description": "First scene", "atmosphere": "calm"},
                {"name": "Scene 2", "description": "Second scene", "atmosphere": "tense"}
            ]
        )
        
        count = parameter_extractor.estimate_scene_count(params)
        assert count == 2
    
    def test_estimate_scene_count_duration(self, parameter_extractor):
        """Test scene count estimation from duration"""
        params = VideoParameters(
            theme="test",
            duration=120  # 2 minutes
        )
        
        count = parameter_extractor.estimate_scene_count(params)
        assert 3 <= count <= 6  # Should estimate 4-5 scenes for 2 minutes
    
    def test_estimate_scene_count_characters(self, parameter_extractor):
        """Test scene count estimation from characters"""
        params = VideoParameters(
            theme="test",
            characters=[
                {"name": "Hero", "description": "Main character", "role": "protagonist"},
                {"name": "Villain", "description": "Antagonist", "role": "antagonist"}
            ]
        )
        
        count = parameter_extractor.estimate_scene_count(params)
        assert count == 3  # 2 characters + 1
    
    def test_estimate_scene_count_default(self, parameter_extractor):
        """Test default scene count"""
        params = VideoParameters(theme="test")
        
        count = parameter_extractor.estimate_scene_count(params)
        assert count == 3  # Default
    
    def test_estimate_shot_count(self, parameter_extractor):
        """Test shot count estimation"""
        # Dramatic mood = more shots
        params_dramatic = VideoParameters(
            theme="test",
            scenes=[{"name": "Scene 1", "description": "Test", "atmosphere": "tense"}],
            mood="dramatic"
        )
        shots_dramatic = parameter_extractor.estimate_shot_count(params_dramatic)
        
        # Peaceful mood = fewer shots
        params_peaceful = VideoParameters(
            theme="test",
            scenes=[{"name": "Scene 1", "description": "Test", "atmosphere": "calm"}],
            mood="peaceful"
        )
        shots_peaceful = parameter_extractor.estimate_shot_count(params_peaceful)
        
        assert shots_dramatic > shots_peaceful


class TestVideoParameters:
    """Test VideoParameters model"""
    
    def test_create_minimal_parameters(self):
        """Test creating parameters with minimal data"""
        params = VideoParameters(theme="Test Video")
        
        assert params.theme == "Test Video"
        assert params.style is None
        assert params.characters == []
        assert params.scenes == []
        assert params.duration is None
    
    def test_create_full_parameters(self):
        """Test creating parameters with all fields"""
        params = VideoParameters(
            theme="Epic Adventure",
            style="cinematic",
            characters=[
                {"name": "Hero", "description": "Brave warrior", "role": "protagonist"}
            ],
            scenes=[
                {"name": "Castle", "description": "Medieval castle", "atmosphere": "grand"}
            ],
            duration=120,
            mood="exciting",
            special_requirements=["dramatic lighting", "epic music"],
            narration="Once upon a time...",
            music_style="orchestral",
            aspect_ratio="16:9",
            quality="high"
        )
        
        assert params.theme == "Epic Adventure"
        assert params.style == "cinematic"
        assert len(params.characters) == 1
        assert len(params.scenes) == 1
        assert params.duration == 120
        assert params.mood == "exciting"
        assert len(params.special_requirements) == 2
        assert params.narration == "Once upon a time..."
        assert params.music_style == "orchestral"
        assert params.aspect_ratio == "16:9"
        assert params.quality == "high"


# Integration test data
EXTRACTION_TEST_CASES = [
    {
        "input": "Create a 2-minute cinematic video about space exploration",
        "expected": {
            "theme_contains": "space",
            "style": "cinematic",
            "duration": 120,
        }
    },
    {
        "input": "Make a short anime video about a magical girl",
        "expected": {
            "theme_contains": "magical girl",
            "style": "anime",
        }
    },
    {
        "input": "Generate a realistic documentary about wildlife with calm music",
        "expected": {
            "theme_contains": "wildlife",
            "style": "realistic",
            "music_style_contains": "calm",
        }
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize("test_case", EXTRACTION_TEST_CASES)
async def test_parameter_extraction_integration(parameter_extractor, test_case):
    """Integration test for parameter extraction"""
    # Note: This test requires actual LLM API access
    # In CI/CD, mock the LLM response
    
    user_input = test_case["input"]
    expected = test_case["expected"]
    
    # Mock LLM response for testing
    with patch.object(parameter_extractor, '_llm_extract_parameters') as mock_llm:
        # Create mock response based on expected values
        mock_response = {
            "theme": user_input,
            "style": expected.get("style"),
            "characters": [],
            "scenes": [],
            "duration": expected.get("duration"),
            "mood": None,
            "special_requirements": [],
            "narration": None,
            "music_style": expected.get("music_style_contains"),
            "aspect_ratio": None,
            "quality": None
        }
        mock_llm.return_value = mock_response
        
        params = await parameter_extractor.extract(user_input)
        
        # Verify expected values
        if "theme_contains" in expected:
            assert expected["theme_contains"].lower() in params.theme.lower()
        
        if "style" in expected:
            assert params.style == expected["style"]
        
        if "duration" in expected:
            assert params.duration == expected["duration"]
        
        if "music_style_contains" in expected:
            assert expected["music_style_contains"] in (params.music_style or "")


class TestEdgeCases:
    """Test edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_input(self, parameter_extractor):
        """Test handling of empty input"""
        with patch.object(parameter_extractor, '_llm_extract_parameters') as mock_llm:
            mock_llm.return_value = {"theme": ""}
            params = await parameter_extractor.extract("")
            assert params.theme == "Untitled Video"  # Should use default
    
    @pytest.mark.asyncio
    async def test_very_long_input(self, parameter_extractor):
        """Test handling of very long input"""
        long_input = "Create a video " + "about space " * 100
        
        with patch.object(parameter_extractor, '_llm_extract_parameters') as mock_llm:
            mock_llm.return_value = {"theme": long_input[:100]}
            params = await parameter_extractor.extract(long_input)
            assert params.theme is not None
    
    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self, parameter_extractor):
        """Test fallback when LLM fails"""
        with patch.object(parameter_extractor, '_llm_extract_parameters', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API error")
            
            params = await parameter_extractor.extract("Create a cinematic video")
            
            # Should fall back to basic extraction
            assert params.theme is not None
            assert params.style == "cinematic"  # Fallback should still extract this


if __name__ == "__main__":
    pytest.main([__file__, "-v"])