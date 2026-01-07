"""
Agent Orchestrator Service
Manages multi-agent workflows for video generation using LLM coordination
"""
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
from enum import Enum
import json
from sqlalchemy.orm import Session

from services.chat_service import ChatService
from services.llm_registry import LLMRegistry
from database_models import AgentTask, ConversationThread, Episode
from utils.error_handling import handle_agent_error


class AgentType(str, Enum):
    """Types of specialized agents"""
    DIALOGUE_INTERPRETER = "dialogue_interpreter"
    SCENE_DESIGNER = "scene_designer"
    STYLE_DETERMINER = "style_determiner"
    VIDEO_COORDINATOR = "video_coordinator"
    POST_PROCESSOR = "post_processor"


class WorkflowStage(str, Enum):
    """Stages in the video generation workflow"""
    INTERPRETATION = "interpretation"
    PLANNING = "planning"
    SCENE_DESIGN = "scene_design"
    GENERATION = "generation"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"


class AgentOrchestrator:
    """Orchestrates multi-agent workflows for video generation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.chat_service = ChatService(db)
        self.llm_registry = LLMRegistry()
        self.agents = self._initialize_agents()
    
    def _initialize_agents(self) -> Dict[AgentType, Dict[str, Any]]:
        """Initialize agent configurations"""
        return {
            AgentType.DIALOGUE_INTERPRETER: {
                'name': 'Dialogue Interpreter',
                'description': 'Extracts video generation parameters from natural language',
                'system_prompt': """You are a dialogue interpretation agent. Your role is to:
1. Understand user requests for video generation
2. Extract key parameters: style, duration, mood, characters, scenes
3. Identify constraints and preferences
4. Structure the request for downstream agents
Be precise and thorough in your analysis."""
            },
            AgentType.SCENE_DESIGNER: {
                'name': 'Scene Designer',
                'description': 'Generates detailed scene descriptions and visual specifications',
                'system_prompt': """You are a scene design agent. Your role is to:
1. Create detailed scene descriptions from story requirements
2. Specify visual elements: lighting, composition, camera angles
3. Maintain consistency across scenes
4. Generate prompts for image/video generation
Be creative and cinematically minded."""
            },
            AgentType.STYLE_DETERMINER: {
                'name': 'Style Determiner',
                'description': 'Analyzes preferences and determines visual styles',
                'system_prompt': """You are a style determination agent. Your role is to:
1. Analyze user preferences and content requirements
2. Determine appropriate visual styles (cinematic, anime, realistic, etc.)
3. Specify color palettes, mood, and artistic direction
4. Ensure style consistency across the project
Be artistic and detail-oriented."""
            },
            AgentType.VIDEO_COORDINATOR: {
                'name': 'Video Generation Coordinator',
                'description': 'Manages API calls to video generation models',
                'system_prompt': """You are a video generation coordinator. Your role is to:
1. Select appropriate video generation models
2. Prepare and validate generation parameters
3. Monitor generation progress
4. Handle fallbacks and retries
Be efficient and reliable."""
            },
            AgentType.POST_PROCESSOR: {
                'name': 'Post-Processing Agent',
                'description': 'Handles video refinement and final output',
                'system_prompt': """You are a post-processing agent. Your role is to:
1. Review generated videos for quality
2. Apply refinements and edits
3. Ensure format compatibility
4. Prepare final deliverables
Be meticulous and quality-focused."""
            }
        }
    
    async def create_workflow(
        self,
        user_id: str,
        llm_model: str,
        user_request: str,
        episode_id: Optional[str] = None
    ) -> ConversationThread:
        """Create a new multi-agent workflow"""
        
        # Create conversation thread
        thread = await self.chat_service.create_thread(
            user_id=user_id,
            llm_model=llm_model,
            episode_id=episode_id,
            title=f"Video Generation: {user_request[:50]}...",
            system_prompt=self._get_orchestrator_system_prompt(),
            context={
                'workflow_stage': WorkflowStage.INTERPRETATION.value,
                'user_request': user_request,
                'active_agents': []
            }
        )
        
        return thread
    
    async def execute_workflow(
        self,
        thread_id: str,
        user_request: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute multi-agent workflow with streaming updates
        
        Yields:
            Status updates from each agent as they work
        """
        
        # Get thread
        thread = self.db.query(ConversationThread).filter(
            ConversationThread.id == thread_id
        ).first()
        
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")
        
        try:
            # Stage 1: Dialogue Interpretation
            yield {'stage': 'interpretation', 'status': 'started', 'message': 'Analyzing your request...'}
            interpretation = await self._run_agent(
                thread_id,
                AgentType.DIALOGUE_INTERPRETER,
                {'user_request': user_request}
            )
            yield {'stage': 'interpretation', 'status': 'completed', 'data': interpretation}
            
            # Stage 2: Style Determination
            yield {'stage': 'style', 'status': 'started', 'message': 'Determining visual style...'}
            style = await self._run_agent(
                thread_id,
                AgentType.STYLE_DETERMINER,
                {'interpretation': interpretation}
            )
            yield {'stage': 'style', 'status': 'completed', 'data': style}
            
            # Stage 3: Scene Design
            yield {'stage': 'scene_design', 'status': 'started', 'message': 'Designing scenes...'}
            scenes = await self._run_agent(
                thread_id,
                AgentType.SCENE_DESIGNER,
                {'interpretation': interpretation, 'style': style}
            )
            yield {'stage': 'scene_design', 'status': 'completed', 'data': scenes}
            
            # Stage 4: Video Generation Coordination
            yield {'stage': 'generation', 'status': 'started', 'message': 'Generating videos...'}
            videos = await self._run_agent(
                thread_id,
                AgentType.VIDEO_COORDINATOR,
                {'scenes': scenes, 'style': style}
            )
            yield {'stage': 'generation', 'status': 'completed', 'data': videos}
            
            # Stage 5: Post-Processing
            yield {'stage': 'post_processing', 'status': 'started', 'message': 'Finalizing output...'}
            final_output = await self._run_agent(
                thread_id,
                AgentType.POST_PROCESSOR,
                {'videos': videos}
            )
            yield {'stage': 'post_processing', 'status': 'completed', 'data': final_output}
            
            # Workflow completed
            yield {'stage': 'completed', 'status': 'success', 'data': final_output}
            
        except Exception as e:
            yield {'stage': 'error', 'status': 'failed', 'error': str(e)}
            raise
    
    async def _run_agent(
        self,
        thread_id: str,
        agent_type: AgentType,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a specific agent task"""
        
        # Get thread
        thread = self.db.query(ConversationThread).filter(
            ConversationThread.id == thread_id
        ).first()
        
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")
        
        # Get agent config
        agent_config = self.agents[agent_type]
        
        # Create agent task
        task = AgentTask(
            thread_id=thread_id,
            episode_id=thread.episode_id,
            task_type=agent_type.value,
            agent_name=agent_config['name'],
            input_data=input_data,
            status='in_progress',
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        try:
            # Create agent-specific prompt
            prompt = self._build_agent_prompt(agent_config, input_data)
            
            # Get response from LLM
            response = await self.chat_service.chat(
                thread_id=thread_id,
                user_message=prompt,
                temperature=0.7
            )
            
            # Parse response
            output_data = self._parse_agent_response(agent_type, response)
            
            # Update task
            task.output_data = output_data
            task.status = 'completed'
            task.progress_percentage = 100
            task.completed_at = datetime.utcnow()
            self.db.commit()
            
            return output_data
            
        except Exception as e:
            # Update task with error
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            self.db.commit()
            raise
    
    def _build_agent_prompt(
        self,
        agent_config: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> str:
        """Build prompt for agent based on input data"""
        
        prompt = f"{agent_config['system_prompt']}\n\n"
        prompt += "Input Data:\n"
        prompt += json.dumps(input_data, indent=2, ensure_ascii=False)
        prompt += "\n\nPlease analyze the input and provide your response in JSON format."
        
        return prompt
    
    def _parse_agent_response(
        self,
        agent_type: AgentType,
        response: str
    ) -> Dict[str, Any]:
        """Parse agent response into structured data"""
        
        # Try to extract JSON from response
        try:
            # Look for JSON block in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # If no JSON found, return as text
                return {'response': response}
        except json.JSONDecodeError:
            # If JSON parsing fails, return as text
            return {'response': response}
    
    def _get_orchestrator_system_prompt(self) -> str:
        """Get system prompt for the orchestrator"""
        return """You are the orchestrator for a multi-agent video generation system.
You coordinate between specialized agents to create high-quality videos from user requests.

Your responsibilities:
1. Understand user requirements
2. Coordinate agent activities
3. Maintain workflow state
4. Provide status updates
5. Ensure quality output

Be professional, efficient, and user-focused."""
    
    async def get_workflow_status(self, thread_id: str) -> Dict[str, Any]:
        """Get current status of workflow"""
        
        # Get thread
        thread = self.db.query(ConversationThread).filter(
            ConversationThread.id == thread_id
        ).first()
        
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")
        
        # Get all tasks for this thread
        tasks = self.db.query(AgentTask).filter(
            AgentTask.thread_id == thread_id
        ).order_by(AgentTask.created_at.asc()).all()
        
        return {
            'thread_id': thread_id,
            'workflow_stage': thread.context.get('workflow_stage'),
            'tasks': [task.to_dict() for task in tasks],
            'status': thread.status
        }
    
    async def cancel_workflow(self, thread_id: str):
        """Cancel an ongoing workflow"""
        
        # Get thread
        thread = self.db.query(ConversationThread).filter(
            ConversationThread.id == thread_id
        ).first()
        
        if not thread:
            raise ValueError(f"Thread not found: {thread_id}")
        
        # Update thread status
        thread.status = 'cancelled'
        thread.updated_at = datetime.utcnow()
        
        # Cancel all pending tasks
        tasks = self.db.query(AgentTask).filter(
            AgentTask.thread_id == thread_id,
            AgentTask.status.in_(['pending', 'in_progress'])
        ).all()
        
        for task in tasks:
            task.status = 'cancelled'
            task.completed_at = datetime.utcnow()
        
        self.db.commit()