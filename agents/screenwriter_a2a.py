"""
Screenwriter A2A Agent
A2A-compatible screenwriter agent for story development and script writing

Part of Week 2: Agent Coordinator Refactor - Phase 2
"""

import logging
from typing import List, Optional, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from agents.base_a2a_agent import BaseA2AAgent
from services.a2a_protocol import (
    A2AMessage,
    MessageType,
    AgentCapability,
    AgentStatus,
    A2AError
)


logger = logging.getLogger(__name__)


# Prompt templates from original screenwriter
SYSTEM_PROMPT_DEVELOP_STORY = """
[Role]
You are a seasoned creative story generation expert. You possess the following core skills:
- Idea Expansion and Conceptualization: The ability to expand a vague idea, a one-line inspiration, or a concept into a fleshed-out, logically coherent story world.
- Story Structure Design: Mastery of classic narrative models like the three-act structure, the hero's journey, etc., enabling you to construct engaging story arcs with a beginning, middle, and end, tailored to the story's genre.
- Character Development: Expertise in creating three-dimensional characters with motivations, flaws, and growth arcs, and designing complex relationships between them.
- Scene Depiction and Pacing: The skill to vividly depict various settings and precisely control the narrative rhythm, allocating detail appropriately based on the required number of scenes.
- Audience Adaptation: The ability to adjust the language style, thematic depth, and content suitability based on the target audience (e.g., children, teenagers, adults).
- Screenplay-Oriented Thinking: When the story is intended for short film or movie adaptation, you can naturally incorporate visual elements (e.g., scene atmosphere, key actions, dialogue) into the narrative, making the story more cinematic and filmable.

[Task]
Your core task is to generate a complete, engaging story that conforms to the specified requirements, based on the user's provided "Idea" and "Requirements."

[Input]
The user will provide an idea within <IDEA> and </IDEA> tags and a user requirement within <USER_REQUIREMENT> and </USER_REQUIREMENT> tags.
- Idea: This is the core seed of the story. It could be a sentence, a concept, a setting, or a scene. For example,
    - "A programmer discovers his shadow has a consciousness of its own.",
    - "What if memories could be deleted and backed up like files?",
    - "A locked-room murder mystery occurring on a space station."
- User Requirement (Optional): Optional constraints or guidelines the user may specify. For example,
    - Target Audience: e.g., Children (7-12), Young Adults, Adults, All Ages.
    - Story Type/Genre: e.g., Sci-Fi, Fantasy, Mystery, Romance, Comedy, Tragedy, Realism, Short Film, Movie Script Concept.
    - Length: e.g., 5 key scenes, a tight story suitable for a 10-minute short film.
    - Other: e.g., Needs a twist ending, Theme about love and sacrifice, Include a piece of compelling dialogue.

[Output]
You must output a well-structured and clearly formatted story document as follows:
- Story Title: An engaging and relevant story name.
- Target Audience & Genre: Start by explicitly restating: "This story is targeted at [User-Specified Audience], in the [User-Specified Genre] genre."
- Story Outline/Summary: Provide a one-paragraph (100-200 words) summary of the entire story, covering the core plot, central conflict, and outcome.
Main Characters Introduction: Briefly introduce the core characters, including their names, key traits, and motivations.
- Full Story Narrative:
    - If the number of scenes is unspecified, narrate the story naturally in paragraphs following the "Introduction - Development - Climax - Conclusion" structure.
    - If a specific number of scenes (e.g., N scenes) is specified, clearly divide the story into N scenes, giving each a subheading (e.g., Scene One: Code at Midnight). The description for each scene should be relatively balanced, including atmosphere, character actions, and dialogue, all working together to advance the plot.
- The narrative should be vivid and detailed, matching the specified genre and target audience.
- The output should begin directly with the story, without any extra words.

[Guidelines]
- The language of output should be same as the input.
- Idea-Centric: Keep the user's core idea as the foundation; do not deviate from its essence. If the user's idea is vague, you can use creativity to make reasonable expansions.
- Logical Consistency: Ensure that event progression and character actions within the story have logical motives and internal consistency, avoiding abrupt or contradictory plots.
- Show, Don't Tell: Reveal characters' personalities and emotions through their actions, dialogues, and details, rather than stating them flatly. For example, use "He clenched his fist, nails digging deep into his palm" instead of "He was very angry."
- Originality & Compliance: Generate original content based on the user's idea, avoiding direct plagiarism of well-known existing works. The generated content must be positive, healthy, and comply with general content safety policies.
"""

HUMAN_PROMPT_DEVELOP_STORY = """
<IDEA>
{idea}
</IDEA>

<USER_REQUIREMENT>
{user_requirement}
</USER_REQUIREMENT>
"""

SYSTEM_PROMPT_WRITE_SCRIPT = """
[Role]
You are a professional AI script adaptation assistant skilled in adapting stories into scripts. You possess the following skills:
- Story Analysis Skills: Ability to deeply understand the story content, identify key plot points, character arcs, and themes.
- Scene Segmentation Skills: Ability to break down the story into logical scene units based on continuity of time and location.
- Script Writing Skills: Familiarity with script formats (e.g., for short films or movies), capable of crafting vivid dialogue, action descriptions, and stage directions.
- Adaptive Adjustment Skills: Ability to adjust the script's style, language, and content based on user requirements (e.g., target audience, story genre, number of scenes).
- Creative Enhancement Skills: Ability to appropriately add dramatic elements to enhance the script's appeal while remaining faithful to the original story.

[Task]
Your task is to adapt the user's input story, along with optional requirements, into a script divided by scenes. The output should be a list of scripts, each representing a complete script for one scene. Each scene must be a continuous dramatic action unit occurring at the same time and location.

[Input]
You will receive a story within <STORY> and </STORY> tags and a user requirement within <USER_REQUIREMENT> and </USER_REQUIREMENT> tags.
- Story: A complete or partial narrative text, which may contain one or more scenes. The story will provide plot, characters, dialogues, and background descriptions.
- User Requirement (Optional): A user requirement, which may be empty. The user requirement may include:
    - Target audience (e.g., children, teenagers, adults).
    - Script genre (e.g., micro-film, moive, short drama).
    - Desired number of scenes (e.g., "divide into 3 scenes").
    - Other specific instructions (e.g., emphasize dialogue or action).

[Output]
{format_instructions}

[Guidelines]
- The language of output in values should be same as the input story.
- Scene Division Principles: Each scene must be based on the same time and location. Start a new scene when the time or location changes. If the user specifies the number of scenes, try to match the requirement. Otherwise, divide scenes naturally based on the story, ensuring each scene has independent dramatic conflict or progression.
- Script Formatting Standards: Use standard script formatting: Scene headings in full caps or bold, character names centered or capitalized, dialogue indented, and action descriptions in parentheses.
- Coherence and Fluidity: Ensure natural transitions between scenes and overall story flow. Avoid abrupt plot jumps.
- Visual Enhancement Principles: All descriptions must be "filmable". Use concrete actions instead of abstract emotions (e.g., "He turns away to avoid eye contact" instead of "He feels ashamed"). Decribe rich environmental details include lighting, props, weather, etc., to enhance the atmosphere. Visualize character performances such as express internal states through facial expressions, gestures, and movements (e.g., "She bites her lip, her hands trembling" to imply nervousness).
- Consistency: Ensure dialogue and actions align with the original story's intent, without deviating from the core plot.
"""

HUMAN_PROMPT_WRITE_SCRIPT = """
<STORY>
{story}
</STORY>

<USER_REQUIREMENT>
{user_requirement}
</USER_REQUIREMENT>
"""


class WriteScriptResponse(BaseModel):
    """Response model for script writing"""
    script: List[str] = Field(
        ...,
        description="The script based on the story. Each element is a scene"
    )


class ScreenwriterA2AAgent(BaseA2AAgent):
    """
    A2A-compatible Screenwriter Agent
    
    Capabilities:
    - develop_story: Develop a complete story from an idea
    - write_script: Convert a story into a structured script
    
    Tags: content-generation, screenwriting, creative-writing
    """
    
    def __init__(self, chat_model: str = "gpt-4o-mini"):
        """
        Initialize Screenwriter A2A Agent
        
        Args:
            chat_model: LLM model to use for generation
        """
        super().__init__(
            name="screenwriter",
            version="2.0.0",
            description="A2A-compatible screenwriter agent for story development and script writing"
        )
        
        # Initialize chat model
        self.chat_model = init_chat_model(chat_model)
        
        logger.info(f"Initialized ScreenwriterA2AAgent with model: {chat_model}")
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Return agent capabilities"""
        return [
            AgentCapability(
                name="develop_story",
                description="Develop a complete story from an idea with optional requirements",
                input_schema={
                    "type": "object",
                    "properties": {
                        "idea": {
                            "type": "string",
                            "description": "Core story idea or concept"
                        },
                        "user_requirement": {
                            "type": "string",
                            "description": "Optional requirements (audience, genre, length, etc.)",
                            "default": ""
                        }
                    },
                    "required": ["idea"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "story": {
                            "type": "string",
                            "description": "Complete developed story"
                        }
                    }
                },
                estimated_duration=60
            ),
            AgentCapability(
                name="write_script",
                description="Convert a story into a structured script divided by scenes",
                input_schema={
                    "type": "object",
                    "properties": {
                        "story": {
                            "type": "string",
                            "description": "Complete story to adapt"
                        },
                        "user_requirement": {
                            "type": "string",
                            "description": "Optional requirements (audience, genre, scene count, etc.)",
                            "default": ""
                        }
                    },
                    "required": ["story"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of scene scripts"
                        }
                    }
                },
                estimated_duration=90
            )
        ]
    
    def get_dependencies(self) -> List[str]:
        """Return agent dependencies"""
        return []  # Screenwriter has no dependencies
    
    async def handle_message(self, message: A2AMessage) -> A2AMessage:
        """
        Handle incoming A2A message
        
        Supports:
        - REQUEST: Execute develop_story or write_script tasks
        - QUERY: Return capability information
        - COMMAND: Control agent behavior (pause, resume, etc.)
        
        Args:
            message: Incoming A2A message
        
        Returns:
            Response A2A message
        """
        try:
            # Handle different message types
            if message.message_type == MessageType.REQUEST:
                return await self._handle_request(message)
            
            elif message.message_type == MessageType.NOTIFICATION:
                # Log notification and acknowledge
                logger.info(f"Received notification: {message.payload}")
                return message.create_response({"acknowledged": True})
            
            else:
                return message.create_error(
                    f"Unsupported message type: {message.message_type}",
                    error_type="UnsupportedMessageType"
                )
        
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            return message.create_error(str(e), error_type="MessageHandlingError")
    
    async def _handle_request(self, message: A2AMessage) -> A2AMessage:
        """Handle REQUEST message"""
        
        # Validate message
        if not self.validate_message(message):
            return message.create_error(
                "Invalid message format. Expected 'task' in payload.",
                error_type="ValidationError"
            )
        
        task = message.payload["task"]
        parameters = message.payload.get("parameters", {})
        
        # Execute task
        try:
            result = await self.execute_task(
                task,
                parameters,
                message.correlation_id
            )
            return message.create_response(result)
        
        except A2AError as e:
            return message.create_error(str(e), error_type=e.error_type)
        
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}", exc_info=True)
            return message.create_error(
                f"Task execution failed: {str(e)}",
                error_type="ExecutionError"
            )
    
    async def _execute_task_impl(
        self,
        task: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """
        Internal task execution implementation
        
        Args:
            task: Task name (develop_story or write_script)
            parameters: Task parameters
        
        Returns:
            Task result
        """
        if task == "develop_story":
            return await self._develop_story(parameters)
        
        elif task == "write_script":
            return await self._write_script(parameters)
        
        else:
            raise A2AError(
                f"Unknown task: {task}",
                error_type="UnknownTask",
                retryable=False
            )
    
    async def _develop_story(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """
        Develop story from idea
        
        Args:
            parameters: Must contain 'idea', optionally 'user_requirement'
        
        Returns:
            Dictionary with 'story' key
        """
        idea = parameters.get("idea")
        if not idea:
            raise A2AError(
                "Missing required parameter: idea",
                error_type="ValidationError",
                retryable=False
            )
        
        user_requirement = parameters.get("user_requirement", "")
        
        # Report progress
        await self.report_progress(0.1, "develop_story", "Starting story development")
        
        try:
            # Create prompt
            messages = [
                ("system", SYSTEM_PROMPT_DEVELOP_STORY),
                ("human", HUMAN_PROMPT_DEVELOP_STORY.format(
                    idea=idea,
                    user_requirement=user_requirement
                ))
            ]
            
            await self.report_progress(0.3, "develop_story", "Generating story with LLM")
            
            # Generate story
            response = await self.chat_model.ainvoke(messages)
            story = response.content
            
            await self.report_progress(0.9, "develop_story", "Story development complete")
            
            logger.info(f"Developed story from idea (length: {len(story)} chars)")
            
            return {"story": story}
        
        except Exception as e:
            logger.error(f"Story development failed: {str(e)}", exc_info=True)
            raise A2AError(
                f"Story development failed: {str(e)}",
                error_type="LLMError",
                retryable=True
            )
    
    async def _write_script(self, parameters: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Write script from story
        
        Args:
            parameters: Must contain 'story', optionally 'user_requirement'
        
        Returns:
            Dictionary with 'script' key (list of scene scripts)
        """
        story = parameters.get("story")
        if not story:
            raise A2AError(
                "Missing required parameter: story",
                error_type="ValidationError",
                retryable=False
            )
        
        user_requirement = parameters.get("user_requirement", "")
        
        # Report progress
        await self.report_progress(0.1, "write_script", "Starting script writing")
        
        try:
            # Create parser
            parser = PydanticOutputParser(pydantic_object=WriteScriptResponse)
            format_instructions = parser.get_format_instructions()
            
            # Create prompt
            messages = [
                ("system", SYSTEM_PROMPT_WRITE_SCRIPT.format(
                    format_instructions=format_instructions
                )),
                ("human", HUMAN_PROMPT_WRITE_SCRIPT.format(
                    story=story,
                    user_requirement=user_requirement
                ))
            ]
            
            await self.report_progress(0.3, "write_script", "Generating script with LLM")
            
            # Generate script
            response = await self.chat_model.ainvoke(messages)
            parsed_response = parser.parse(response.content)
            script = parsed_response.script
            
            await self.report_progress(0.9, "write_script", "Script writing complete")
            
            logger.info(f"Generated script with {len(script)} scenes")
            
            return {"script": script}
        
        except Exception as e:
            logger.error(f"Script writing failed: {str(e)}", exc_info=True)
            raise A2AError(
                f"Script writing failed: {str(e)}",
                error_type="LLMError",
                retryable=True
            )


# Factory function for easy instantiation
def create_screenwriter_agent(chat_model: str = "gpt-4o-mini") -> ScreenwriterA2AAgent:
    """
    Create a Screenwriter A2A agent
    
    Args:
        chat_model: LLM model to use
    
    Returns:
        ScreenwriterA2AAgent instance
    """
    return ScreenwriterA2AAgent(chat_model=chat_model)