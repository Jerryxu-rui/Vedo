"""
Conversational Orchestrator Service
Central coordinator for conversational video generation

This is the main orchestration layer that:
1. Understands user intent
2. Extracts parameters
3. Selects appropriate workflow
4. Coordinates agents
5. Manages conversation context

Part of Week 1, Task 1.3 of the Orchestration Layer Implementation
"""

from typing import Dict, Any, Optional, List, Callable
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import json

from services.intent_analyzer_llm import LLMIntentAnalyzer as IntentAnalyzer, Intent, IntentType, ComplexityLevel
from services.parameter_extractor import ParameterExtractor, VideoParameters
from services.chat_service import ChatService
from database_models import ConversationThread, ConversationMessage


class ConversationContext:
    """Manages conversation context and history"""
    
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.current_intent: Optional[Intent] = None
        self.current_parameters: Optional[VideoParameters] = None
        self.workflow_state: Dict[str, Any] = {}
        self.user_preferences: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add message to conversation history"""
        self.history.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_recent_history(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history"""
        return self.history[-count:] if self.history else []
    
    def update_intent(self, intent: Intent):
        """Update current intent"""
        self.current_intent = intent
    
    def update_parameters(self, parameters: VideoParameters):
        """Update current parameters"""
        self.current_parameters = parameters
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context"""
        return {
            "has_existing_content": bool(self.workflow_state.get("episode_id")),
            "last_intent": self.current_intent.type if self.current_intent else None,
            "message_count": len(self.history),
            "workflow_state": self.workflow_state,
            "user_preferences": self.user_preferences
        }


class ConversationalOrchestrator:
    """
    Central orchestrator for conversational video generation
    
    This is the main entry point for all conversational interactions.
    It coordinates between intent analysis, parameter extraction, workflow
    selection, and agent execution.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.intent_analyzer = IntentAnalyzer(db)
        self.parameter_extractor = ParameterExtractor(db)
        self.chat_service = ChatService(db)
        
        # Context management
        self.contexts: Dict[str, ConversationContext] = {}
    
    def get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """Get or create conversation context"""
        if conversation_id not in self.contexts:
            self.contexts[conversation_id] = ConversationContext()
        return self.contexts[conversation_id]
    
    async def process_message(
        self,
        user_message: str,
        conversation_id: str,
        thread_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user messages
        
        Args:
            user_message: User's natural language input
            conversation_id: Unique conversation identifier
            thread_id: Optional chat thread ID
            progress_callback: Optional callback for progress updates
        
        Returns:
            Response dictionary with:
            - type: Response type (chat, video_generation, etc.)
            - content: Response content
            - metadata: Additional metadata
        """
        
        # Get conversation context
        context = self.get_or_create_context(conversation_id)
        context.add_message("user", user_message)
        
        # Get context summary for intent analysis
        context_summary = context.get_context_summary()
        
        try:
            # Step 1: Analyze intent
            if progress_callback:
                await progress_callback({
                    "stage": "intent_analysis",
                    "progress": 0.1,
                    "message": "Understanding your request..."
                })
            
            intent = await self.intent_analyzer.analyze(
                user_message,
                context_summary
            )
            
            context.update_intent(intent)
            
            # Step 2: Route based on intent
            if intent.type == IntentType.CHAT:
                response = await self._handle_chat(
                    user_message,
                    thread_id,
                    context
                )
            
            elif intent.type == IntentType.VIDEO_GENERATION:
                response = await self._handle_video_generation(
                    intent,
                    user_message,
                    context,
                    progress_callback
                )
            
            elif intent.type == IntentType.MODIFICATION:
                response = await self._handle_modification(
                    intent,
                    user_message,
                    context,
                    progress_callback
                )
            
            elif intent.type == IntentType.REVIEW:
                response = await self._handle_review(
                    user_message,
                    context
                )
            
            elif intent.type == IntentType.EXPORT:
                response = await self._handle_export(
                    user_message,
                    context
                )
            
            else:
                response = await self._handle_unknown(
                    user_message,
                    context
                )
            
            # Add response to context
            context.add_message(
                "assistant",
                response.get("content", ""),
                response.get("metadata", {})
            )
            
            return response
        
        except Exception as e:
            print(f"[ConversationalOrchestrator] Error processing message: {e}")
            return {
                "type": "error",
                "content": f"I encountered an error processing your request: {str(e)}",
                "metadata": {
                    "error": str(e),
                    "intent": intent.type if 'intent' in locals() else "unknown"
                }
            }
    
    async def _handle_chat(
        self,
        user_message: str,
        thread_id: Optional[str],
        context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Handle general chat/questions
        
        Uses the chat service to provide helpful responses about
        the system's capabilities, answer questions, etc.
        
        Also handles cases where video generation intent was detected
        but content validation failed (needs clarification).
        """
        
        # Check if this is a failed video generation attempt (needs clarification)
        intent = context.current_intent
        if intent and intent.parameters.get("needs_clarification"):
            return await self._handle_clarification_needed(intent, user_message, context)
        
        # If no thread exists, create one
        if not thread_id:
            thread = await self.chat_service.create_thread(
                user_id=context.workflow_state.get("user_id", "anonymous"),
                llm_model="gemini-2.0-flash-exp",
                title="Conversation",
                system_prompt=self._get_system_prompt()
            )
            thread_id = thread.id
            context.workflow_state["thread_id"] = thread_id
        
        # Get chat response
        response = await self.chat_service.chat(
            thread_id=thread_id,
            user_message=user_message,
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "type": "chat",
            "content": response,
            "metadata": {
                "thread_id": thread_id,
                "intent": "chat"
            }
        }
    
    async def _handle_clarification_needed(
        self,
        intent: Intent,
        user_message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Handle cases where user expressed video generation intent
        but didn't provide enough details
        
        Provides helpful guidance and suggestions
        """
        
        validation = intent.parameters.get("validation", {})
        missing_elements = validation.get("missing_elements", [])
        suggestions = validation.get("suggestions", [])
        
        # Build helpful response
        response_parts = [
            "I understand you want to create a video! 🎬",
            "",
            "To help you create the best video possible, I need a bit more information:"
        ]
        
        # Add specific guidance based on what's missing
        if "subject" in missing_elements:
            response_parts.append("\n📝 **What should the video be about?**")
            response_parts.append("   Example: \"a space adventure\", \"a romantic story\", \"a cooking tutorial\"")
        
        if "action" in missing_elements:
            response_parts.append("\n🎭 **What happens in the video?**")
            response_parts.append("   Example: \"astronauts explore Mars\", \"two people fall in love\", \"chef makes pasta\"")
        
        if "context" in missing_elements:
            response_parts.append("\n🎨 **Any specific style, setting, or mood?**")
            response_parts.append("   Example: \"sci-fi style\", \"in Paris\", \"suspenseful atmosphere\"")
        
        response_parts.append("\n" + "─" * 50)
        response_parts.append("\n💡 **Example of a complete idea:**")
        response_parts.append("\"Create a sci-fi video about astronauts exploring Mars, discovering ancient ruins\"")
        response_parts.append("\"制作一个浪漫爱情故事，两个人在巴黎的咖啡馆相遇\"")
        
        response_parts.append("\n✨ **Try again with more details!**")
        
        content = "\n".join(response_parts)
        
        return {
            "type": "clarification",
            "content": content,
            "metadata": {
                "intent": "clarification_needed",
                "original_message": user_message,
                "missing_elements": missing_elements,
                "suggestions": suggestions,
                "validation": validation
            }
        }
    
    async def _handle_video_generation(
        self,
        intent: Intent,
        user_message: str,
        context: ConversationContext,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Handle video generation requests
        
        Flow:
        1. Extract parameters
        2. Select workflow based on complexity
        3. Create execution plan
        4. Execute workflow
        5. Return results
        """
        
        # Step 1: Extract parameters
        if progress_callback:
            await progress_callback({
                "stage": "parameter_extraction",
                "progress": 0.2,
                "message": "Extracting video parameters..."
            })
        
        parameters = await self.parameter_extractor.extract(
            user_message,
            context.get_context_summary()
        )
        
        context.update_parameters(parameters)
        
        # Step 2: Assess complexity
        complexity = self.intent_analyzer.assess_complexity({
            "theme": parameters.theme,
            "characters": parameters.characters,
            "scenes": parameters.scenes,
            "duration": parameters.duration,
            "special_requirements": parameters.special_requirements
        })
        
        # Step 3: Select workflow
        workflow_type = self._select_workflow(complexity)
        
        if progress_callback:
            await progress_callback({
                "stage": "workflow_selection",
                "progress": 0.3,
                "message": f"Selected {workflow_type} workflow for {complexity} complexity"
            })
        
        # Step 4: Prepare response with workflow information
        # Note: Actual workflow execution will be handled by the API endpoint
        # This orchestrator prepares the plan and returns it
        
        return {
            "type": "video_generation",
            "content": self._format_video_generation_response(parameters, complexity),
            "metadata": {
                "intent": "video_generation",
                "parameters": parameters.dict(),
                "complexity": complexity,
                "workflow_type": workflow_type,
                "estimated_scenes": self.parameter_extractor.estimate_scene_count(parameters),
                "estimated_shots": self.parameter_extractor.estimate_shot_count(parameters)
            }
        }
    
    async def _handle_modification(
        self,
        intent: Intent,
        user_message: str,
        context: ConversationContext,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Handle modification requests
        
        Modifies existing content based on user feedback
        """
        
        if not context.workflow_state.get("episode_id"):
            return {
                "type": "error",
                "content": "I don't see any existing content to modify. Please create a video first.",
                "metadata": {"intent": "modification", "error": "no_existing_content"}
            }
        
        # Extract modification parameters
        modification_params = await self._extract_modification_params(user_message)
        
        return {
            "type": "modification",
            "content": f"I'll modify the video: {modification_params.get('description', user_message)}",
            "metadata": {
                "intent": "modification",
                "episode_id": context.workflow_state.get("episode_id"),
                "modification_params": modification_params
            }
        }
    
    async def _handle_review(
        self,
        user_message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle review/approval requests"""
        
        if not context.workflow_state.get("episode_id"):
            return {
                "type": "error",
                "content": "I don't see any content to review. Please create a video first.",
                "metadata": {"intent": "review", "error": "no_content"}
            }
        
        return {
            "type": "review",
            "content": "Let me show you the current progress...",
            "metadata": {
                "intent": "review",
                "episode_id": context.workflow_state.get("episode_id")
            }
        }
    
    async def _handle_export(
        self,
        user_message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle export/download requests"""
        
        if not context.workflow_state.get("episode_id"):
            return {
                "type": "error",
                "content": "I don't see any content to export. Please create a video first.",
                "metadata": {"intent": "export", "error": "no_content"}
            }
        
        return {
            "type": "export",
            "content": "Preparing your video for download...",
            "metadata": {
                "intent": "export",
                "episode_id": context.workflow_state.get("episode_id")
            }
        }
    
    async def _handle_unknown(
        self,
        user_message: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle unknown intents"""
        
        return {
            "type": "clarification",
            "content": "I'm not sure what you'd like me to do. Could you please clarify? I can help you:\n\n"
                      "• Create videos from ideas\n"
                      "• Modify existing videos\n"
                      "• Review your content\n"
                      "• Export finished videos\n"
                      "• Answer questions about the system",
            "metadata": {
                "intent": "unknown",
                "suggestions": [
                    "Create a video about...",
                    "Make it more dramatic",
                    "Show me the current progress",
                    "What can you do?"
                ]
            }
        }
    
    def _select_workflow(self, complexity: ComplexityLevel) -> str:
        """
        Select appropriate workflow based on complexity
        
        Returns workflow type identifier
        """
        
        if complexity == ComplexityLevel.SIMPLE:
            return "simple_video"
        elif complexity == ComplexityLevel.MEDIUM:
            return "standard_video"
        else:
            return "complex_video"
    
    def _format_video_generation_response(
        self,
        parameters: VideoParameters,
        complexity: ComplexityLevel
    ) -> str:
        """Format a friendly response for video generation"""
        
        response_parts = [
            f"Great! I'll create a video about: **{parameters.theme}**"
        ]
        
        if parameters.style:
            response_parts.append(f"Style: {parameters.style}")
        
        if parameters.duration:
            minutes = parameters.duration // 60
            seconds = parameters.duration % 60
            duration_str = f"{minutes}:{seconds:02d}" if minutes > 0 else f"{seconds}s"
            response_parts.append(f"Duration: {duration_str}")
        
        if parameters.characters:
            char_count = len(parameters.characters)
            response_parts.append(f"Characters: {char_count}")
        
        if parameters.mood:
            response_parts.append(f"Mood: {parameters.mood}")
        
        response_parts.append(f"\nComplexity: {complexity}")
        response_parts.append("\nStarting video generation...")
        
        return "\n".join(response_parts)
    
    async def _extract_modification_params(self, user_message: str) -> Dict[str, Any]:
        """Extract modification parameters from user message"""
        
        # Simple extraction for now
        # TODO: Use LLM for more sophisticated extraction
        
        params = {
            "description": user_message,
            "type": "general"
        }
        
        # Detect modification type
        if any(word in user_message.lower() for word in ["darker", "brighter", "color", "lighting"]):
            params["type"] = "visual"
        elif any(word in user_message.lower() for word in ["longer", "shorter", "duration", "speed"]):
            params["type"] = "timing"
        elif any(word in user_message.lower() for word in ["music", "sound", "audio"]):
            params["type"] = "audio"
        
        return params
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for chat interactions"""
        
        return """You are a helpful AI assistant for a video generation system called ViMax.

Your capabilities:
- Create videos from text descriptions
- Modify existing videos based on feedback
- Answer questions about the system
- Guide users through the video creation process

Be friendly, concise, and helpful. When users ask about creating videos, 
encourage them to describe what they want in natural language."""
    
    def clear_context(self, conversation_id: str):
        """Clear conversation context"""
        if conversation_id in self.contexts:
            del self.contexts[conversation_id]
    
    def get_context_info(self, conversation_id: str) -> Dict[str, Any]:
        """Get information about conversation context"""
        if conversation_id not in self.contexts:
            return {"exists": False}
        
        context = self.contexts[conversation_id]
        return {
            "exists": True,
            "message_count": len(context.history),
            "current_intent": context.current_intent.type if context.current_intent else None,
            "has_parameters": context.current_parameters is not None,
            "workflow_state": context.workflow_state
        }