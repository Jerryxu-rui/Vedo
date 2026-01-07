"""
Tests for Conversational Orchestrator Service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from services.conversational_orchestrator import (
    ConversationalOrchestrator,
    ConversationContext
)
from services.intent_analyzer import Intent, IntentType, ComplexityLevel
from services.parameter_extractor import VideoParameters


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def orchestrator(mock_db):
    """Create ConversationalOrchestrator instance"""
    return ConversationalOrchestrator(mock_db)


@pytest.fixture
def conversation_context():
    """Create ConversationContext instance"""
    return ConversationContext()


class TestConversationContext:
    """Test ConversationContext class"""
    
    def test_create_context(self, conversation_context):
        """Test context creation"""
        assert conversation_context.history == []
        assert conversation_context.current_intent is None
        assert conversation_context.current_parameters is None
    
    def test_add_message(self, conversation_context):
        """Test adding messages to context"""
        conversation_context.add_message("user", "Hello")
        conversation_context.add_message("assistant", "Hi there!")
        
        assert len(conversation_context.history) == 2
        assert conversation_context.history[0]["role"] == "user"
        assert conversation_context.history[0]["content"] == "Hello"
        assert conversation_context.history[1]["role"] == "assistant"
    
    def test_get_recent_history(self, conversation_context):
        """Test getting recent history"""
        for i in range(10):
            conversation_context.add_message("user", f"Message {i}")
        
        recent = conversation_context.get_recent_history(count=3)
        assert len(recent) == 3
        assert recent[-1]["content"] == "Message 9"
    
    def test_update_intent(self, conversation_context):
        """Test updating intent"""
        intent = Intent(
            type=IntentType.VIDEO_GENERATION,
            confidence=0.95,
            complexity=ComplexityLevel.MEDIUM
        )
        
        conversation_context.update_intent(intent)
        assert conversation_context.current_intent == intent
    
    def test_update_parameters(self, conversation_context):
        """Test updating parameters"""
        params = VideoParameters(theme="Test video")
        
        conversation_context.update_parameters(params)
        assert conversation_context.current_parameters == params
    
    def test_get_context_summary(self, conversation_context):
        """Test getting context summary"""
        conversation_context.add_message("user", "Hello")
        conversation_context.workflow_state["episode_id"] = "test123"
        
        summary = conversation_context.get_context_summary()
        
        assert summary["has_existing_content"] is True
        assert summary["message_count"] == 1
        assert "workflow_state" in summary


class TestOrchestratorBasics:
    """Test basic orchestrator functionality"""
    
    def test_create_orchestrator(self, orchestrator):
        """Test orchestrator creation"""
        assert orchestrator.intent_analyzer is not None
        assert orchestrator.parameter_extractor is not None
        assert orchestrator.chat_service is not None
        assert orchestrator.contexts == {}
    
    def test_get_or_create_context(self, orchestrator):
        """Test context creation and retrieval"""
        context1 = orchestrator.get_or_create_context("conv1")
        context2 = orchestrator.get_or_create_context("conv1")
        context3 = orchestrator.get_or_create_context("conv2")
        
        assert context1 is context2  # Same context
        assert context1 is not context3  # Different context
        assert len(orchestrator.contexts) == 2
    
    def test_clear_context(self, orchestrator):
        """Test clearing context"""
        orchestrator.get_or_create_context("conv1")
        assert "conv1" in orchestrator.contexts
        
        orchestrator.clear_context("conv1")
        assert "conv1" not in orchestrator.contexts
    
    def test_get_context_info(self, orchestrator):
        """Test getting context info"""
        # Non-existent context
        info = orchestrator.get_context_info("nonexistent")
        assert info["exists"] is False
        
        # Existing context
        context = orchestrator.get_or_create_context("conv1")
        context.add_message("user", "Hello")
        
        info = orchestrator.get_context_info("conv1")
        assert info["exists"] is True
        assert info["message_count"] == 1


class TestIntentRouting:
    """Test intent-based routing"""
    
    @pytest.mark.asyncio
    async def test_handle_chat_intent(self, orchestrator):
        """Test handling chat intent"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            with patch.object(orchestrator.chat_service, 'create_thread') as mock_create:
                with patch.object(orchestrator.chat_service, 'chat') as mock_chat:
                    # Mock intent analysis
                    mock_analyze.return_value = Intent(
                        type=IntentType.CHAT,
                        confidence=0.95,
                        complexity=ComplexityLevel.SIMPLE
                    )
                    
                    # Mock thread creation
                    mock_thread = Mock()
                    mock_thread.id = "thread123"
                    mock_create.return_value = mock_thread
                    
                    # Mock chat response
                    mock_chat.return_value = "I can help you create videos!"
                    
                    # Process message
                    response = await orchestrator.process_message(
                        user_message="What can you do?",
                        conversation_id="conv1"
                    )
                    
                    assert response["type"] == "chat"
                    assert "help" in response["content"].lower()
                    assert "thread_id" in response["metadata"]
    
    @pytest.mark.asyncio
    async def test_handle_video_generation_intent(self, orchestrator):
        """Test handling video generation intent"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            with patch.object(orchestrator.parameter_extractor, 'extract') as mock_extract:
                with patch.object(orchestrator.intent_analyzer, 'assess_complexity') as mock_complexity:
                    # Mock intent analysis
                    mock_analyze.return_value = Intent(
                        type=IntentType.VIDEO_GENERATION,
                        confidence=0.95,
                        complexity=ComplexityLevel.MEDIUM
                    )
                    
                    # Mock parameter extraction
                    mock_extract.return_value = VideoParameters(
                        theme="space exploration",
                        style="cinematic",
                        duration=120
                    )
                    
                    # Mock complexity assessment
                    mock_complexity.return_value = ComplexityLevel.MEDIUM
                    
                    # Process message
                    response = await orchestrator.process_message(
                        user_message="Create a 2-minute cinematic video about space exploration",
                        conversation_id="conv1"
                    )
                    
                    assert response["type"] == "video_generation"
                    assert "space exploration" in response["content"]
                    assert response["metadata"]["complexity"] == ComplexityLevel.MEDIUM
                    assert response["metadata"]["workflow_type"] == "standard_video"
    
    @pytest.mark.asyncio
    async def test_handle_modification_without_content(self, orchestrator):
        """Test handling modification when no content exists"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            # Mock intent analysis
            mock_analyze.return_value = Intent(
                type=IntentType.MODIFICATION,
                confidence=0.92,
                complexity=ComplexityLevel.SIMPLE
            )
            
            # Process message
            response = await orchestrator.process_message(
                user_message="Make it darker",
                conversation_id="conv1"
            )
            
            assert response["type"] == "error"
            assert "existing content" in response["content"].lower()
    
    @pytest.mark.asyncio
    async def test_handle_modification_with_content(self, orchestrator):
        """Test handling modification when content exists"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            # Mock intent analysis
            mock_analyze.return_value = Intent(
                type=IntentType.MODIFICATION,
                confidence=0.92,
                complexity=ComplexityLevel.SIMPLE
            )
            
            # Set up context with existing content
            context = orchestrator.get_or_create_context("conv1")
            context.workflow_state["episode_id"] = "episode123"
            
            # Process message
            response = await orchestrator.process_message(
                user_message="Make it darker",
                conversation_id="conv1"
            )
            
            assert response["type"] == "modification"
            assert response["metadata"]["episode_id"] == "episode123"
    
    @pytest.mark.asyncio
    async def test_handle_unknown_intent(self, orchestrator):
        """Test handling unknown intent"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            # Mock intent analysis
            mock_analyze.return_value = Intent(
                type=IntentType.UNKNOWN,
                confidence=0.3,
                complexity=ComplexityLevel.SIMPLE
            )
            
            # Process message
            response = await orchestrator.process_message(
                user_message="Something unclear",
                conversation_id="conv1"
            )
            
            assert response["type"] == "clarification"
            assert "not sure" in response["content"].lower()
            assert "suggestions" in response["metadata"]


class TestWorkflowSelection:
    """Test workflow selection logic"""
    
    def test_select_simple_workflow(self, orchestrator):
        """Test selection of simple workflow"""
        workflow = orchestrator._select_workflow(ComplexityLevel.SIMPLE)
        assert workflow == "simple_video"
    
    def test_select_medium_workflow(self, orchestrator):
        """Test selection of medium workflow"""
        workflow = orchestrator._select_workflow(ComplexityLevel.MEDIUM)
        assert workflow == "standard_video"
    
    def test_select_complex_workflow(self, orchestrator):
        """Test selection of complex workflow"""
        workflow = orchestrator._select_workflow(ComplexityLevel.COMPLEX)
        assert workflow == "complex_video"


class TestResponseFormatting:
    """Test response formatting"""
    
    def test_format_video_generation_response_minimal(self, orchestrator):
        """Test formatting with minimal parameters"""
        params = VideoParameters(theme="nature")
        response = orchestrator._format_video_generation_response(
            params,
            ComplexityLevel.SIMPLE
        )
        
        assert "nature" in response
        assert "simple" in response.lower()
    
    def test_format_video_generation_response_full(self, orchestrator):
        """Test formatting with full parameters"""
        params = VideoParameters(
            theme="space exploration",
            style="cinematic",
            duration=120,
            characters=[{"name": "Astronaut", "role": "protagonist"}],
            mood="exciting"
        )
        
        response = orchestrator._format_video_generation_response(
            params,
            ComplexityLevel.COMPLEX
        )
        
        assert "space exploration" in response
        assert "cinematic" in response
        assert "2:00" in response or "120" in response
        assert "Characters: 1" in response
        assert "exciting" in response
        assert "complex" in response.lower()


class TestProgressCallback:
    """Test progress callback functionality"""
    
    @pytest.mark.asyncio
    async def test_progress_callback_called(self, orchestrator):
        """Test that progress callback is called during processing"""
        progress_updates = []
        
        async def progress_callback(update):
            progress_updates.append(update)
        
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            with patch.object(orchestrator.parameter_extractor, 'extract') as mock_extract:
                with patch.object(orchestrator.intent_analyzer, 'assess_complexity') as mock_complexity:
                    # Mock responses
                    mock_analyze.return_value = Intent(
                        type=IntentType.VIDEO_GENERATION,
                        confidence=0.95,
                        complexity=ComplexityLevel.MEDIUM
                    )
                    mock_extract.return_value = VideoParameters(theme="test")
                    mock_complexity.return_value = ComplexityLevel.MEDIUM
                    
                    # Process with callback
                    await orchestrator.process_message(
                        user_message="Create a video",
                        conversation_id="conv1",
                        progress_callback=progress_callback
                    )
                    
                    # Verify callbacks were made
                    assert len(progress_updates) > 0
                    assert any("intent" in update["stage"] for update in progress_updates)


class TestErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_handle_intent_analysis_error(self, orchestrator):
        """Test handling of intent analysis errors"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            # Mock error
            mock_analyze.side_effect = Exception("Intent analysis failed")
            
            # Process message
            response = await orchestrator.process_message(
                user_message="Test message",
                conversation_id="conv1"
            )
            
            assert response["type"] == "error"
            assert "error" in response["content"].lower()
    
    @pytest.mark.asyncio
    async def test_handle_parameter_extraction_error(self, orchestrator):
        """Test handling of parameter extraction errors"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            with patch.object(orchestrator.parameter_extractor, 'extract') as mock_extract:
                # Mock intent success but parameter extraction failure
                mock_analyze.return_value = Intent(
                    type=IntentType.VIDEO_GENERATION,
                    confidence=0.95,
                    complexity=ComplexityLevel.MEDIUM
                )
                mock_extract.side_effect = Exception("Parameter extraction failed")
                
                # Process message
                response = await orchestrator.process_message(
                    user_message="Create a video",
                    conversation_id="conv1"
                )
                
                assert response["type"] == "error"


class TestContextManagement:
    """Test conversation context management"""
    
    @pytest.mark.asyncio
    async def test_context_persists_across_messages(self, orchestrator):
        """Test that context persists across multiple messages"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            with patch.object(orchestrator.chat_service, 'create_thread') as mock_create:
                with patch.object(orchestrator.chat_service, 'chat') as mock_chat:
                    # Setup mocks
                    mock_analyze.return_value = Intent(
                        type=IntentType.CHAT,
                        confidence=0.95,
                        complexity=ComplexityLevel.SIMPLE
                    )
                    mock_thread = Mock()
                    mock_thread.id = "thread123"
                    mock_create.return_value = mock_thread
                    mock_chat.return_value = "Response"
                    
                    # Send multiple messages
                    await orchestrator.process_message("Message 1", "conv1")
                    await orchestrator.process_message("Message 2", "conv1")
                    await orchestrator.process_message("Message 3", "conv1")
                    
                    # Check context
                    context = orchestrator.get_or_create_context("conv1")
                    assert len(context.history) == 6  # 3 user + 3 assistant messages
    
    @pytest.mark.asyncio
    async def test_separate_contexts_for_different_conversations(self, orchestrator):
        """Test that different conversations have separate contexts"""
        with patch.object(orchestrator.intent_analyzer, 'analyze') as mock_analyze:
            with patch.object(orchestrator.chat_service, 'create_thread') as mock_create:
                with patch.object(orchestrator.chat_service, 'chat') as mock_chat:
                    # Setup mocks
                    mock_analyze.return_value = Intent(
                        type=IntentType.CHAT,
                        confidence=0.95,
                        complexity=ComplexityLevel.SIMPLE
                    )
                    mock_thread = Mock()
                    mock_thread.id = "thread123"
                    mock_create.return_value = mock_thread
                    mock_chat.return_value = "Response"
                    
                    # Send messages to different conversations
                    await orchestrator.process_message("Message 1", "conv1")
                    await orchestrator.process_message("Message 2", "conv2")
                    
                    # Check contexts are separate
                    context1 = orchestrator.get_or_create_context("conv1")
                    context2 = orchestrator.get_or_create_context("conv2")
                    
                    assert len(context1.history) == 2  # 1 user + 1 assistant
                    assert len(context2.history) == 2  # 1 user + 1 assistant
                    assert context1 is not context2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])