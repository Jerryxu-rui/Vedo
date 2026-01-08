import logging
from typing import Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from openai import RateLimitError, APIError



system_prompt_template_develop_story = \
"""
[Role]
You are a Creative Screenwriter specializing in heartwarming short films and visual storytelling. You possess the following core skills:
- Idea Expansion and Conceptualization: The ability to expand a vague idea, a one-line inspiration, or a concept into a fleshed-out, logically coherent story world with rich sensory details.
- Story Structure Design: Mastery of the three-act structure (Setup, Development, Resolution), enabling you to construct engaging story arcs with clear emotional beats and character growth.
- Character Development: Expertise in creating three-dimensional characters (including animals as full characters) with specific visual descriptions, motivations, personality traits, and emotional arcs.
- Scene Depiction and Pacing: The skill to vividly depict 5-8 distinct scenes with specific actions, environmental details (lighting, weather, props), and emotional progression.
- Visual Storytelling: The ability to write "filmable" content - using concrete actions instead of abstract emotions, incorporating camera-ready descriptions.
- Emotional Depth: Creating natural conflict/resolution and ending with emotional payoff.

[Task]
Your core task is to expand the user's brief concept into a fully developed 3-act narrative with emotional depth and visual richness, suitable for video production.

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
You must output a well-structured story with the following sections:

1. **Story Title**: An engaging, specific title (not generic like "新故事")

2. **Story Summary** (100-200 words): Cover the complete arc - setup, conflict, climax, resolution

3. **Main Characters** (ALL characters including animals):
   For each character provide:
   - Name (specific, not "主角" or "角色")
   - Age/Species (for animals: breed, age)
   - Physical appearance (clothing, build, distinctive features)
   - Personality traits (3-5 specific traits)
   - Motivation (what drives them in this story)
   - Relationship to other characters

4. **Full Story Narrative** - Divided into 5-8 distinct scenes:
   
   **Scene Structure** (for each scene):
   - Scene Title: [Specific location] - [Time of day]
   - Setting Details: Describe lighting, weather, environmental elements
   - Character Actions: Specific, filmable actions (not abstract emotions)
   - Dialogue: Natural conversations that reveal character
   - Emotional Beat: What changes emotionally in this scene
   - Visual Elements: Key props, colors, movements
   - Transition: How this scene leads to the next

   **Example Scene Format**:
   Scene 1: Beach Arrival - Golden Hour
   The sun hangs low over the empty beach, casting long shadows across the sand. Sarah, a 32-year-old woman in casual linen shorts and a tank top, unclips the leash from Max, her energetic 3-year-old Golden Retriever. Max's tail wags furiously as he immediately sprints toward the crashing waves, kicking up sand. Sarah laughs, her hair catching the breeze, and jogs after him, her bare feet leaving prints in the wet sand. The sound of waves and seagulls fills the air. (Emotion: Joyful anticipation and freedom)

5. **Story Arc Summary**:
   - Act 1 (Setup): [What happens]
   - Act 2 (Development): [3-4 scenes of escalating action]
   - Act 3 (Resolution): [Emotional conclusion]

[Guidelines]
- **Language**: Output in the same language as the input
- **Idea-Centric**: Expand the user's core idea with rich details while staying true to its essence
- **Minimum 5 Scenes**: Always create at least 5 distinct scenes showing clear progression
- **Specific Details**: Every element must be concrete and specific:
  - Character names (not "主角", "角色", "人物")
  - Locations (not "场景", "地点" - use actual place names)
  - Actions (not "做某事" - describe the exact action)
  - Appearances (not "待定" - provide full descriptions)
- **Show, Don't Tell**: Use concrete actions and sensory details:
  - ✅ "She bites her lip, hands trembling"
  - ❌ "She feels nervous"
  - ✅ "He slams the door, fists clenched"
  - ❌ "He is angry"
- **Visual Filmability**: Every description must be something a camera can capture
- **Cause and Effect**: Each scene naturally leads to the next
- **Emotional Progression**: Clear emotional arc from beginning to end
- **Character Consistency**: Maintain character traits and motivations throughout

**FORBIDDEN**:
- Generic placeholders: "主角", "角色", "待定", "开端", "发展"
- Repeating user input verbatim without expansion
- Abstract emotions without physical manifestation
- Single-scene stories or stories with fewer than 5 scenes
- Vague descriptions that aren't filmable
"""

human_prompt_template_develop_story = \
"""
<IDEA>
{idea}
</IDEA>

<USER_REQUIREMENT>
{user_requirement}
</USER_REQUIREMENT>
"""



system_prompt_template_write_script_based_on_story = \
"""
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


human_prompt_template_write_script_based_on_story = \
"""
<STORY>
{story}
</STORY>

<USER_REQUIREMENT>
{user_requirement}
</USER_REQUIREMENT>
"""


class Screenwriter:
    def __init__(
        self,
        chat_model: Any,
        fallback_chat_model: Optional[Any] = None,
    ):
        self.chat_model = chat_model
        self.fallback_chat_model = fallback_chat_model

    async def develop_story(
        self,
        idea: str,
        user_requirement: Optional[str] = None,
    ) -> str:
        print(f"\n{'='*80}")
        print(f"[Screenwriter.develop_story] CALLED")
        print(f"{'='*80}")
        print(f"[Screenwriter.develop_story] Input idea length: {len(idea)} chars")
        print(f"[Screenwriter.develop_story] Input idea preview: {idea[:200]}...")
        print(f"[Screenwriter.develop_story] User requirement length: {len(user_requirement) if user_requirement else 0} chars")
        if user_requirement:
            print(f"[Screenwriter.develop_story] User requirement preview: {user_requirement[:300]}...")
        print(f"[Screenwriter.develop_story] Chat model type: {type(self.chat_model).__name__}")
        print(f"[Screenwriter.develop_story] Chat model: {self.chat_model}")
        
        messages = [
            ("system", system_prompt_template_develop_story),
            ("human", human_prompt_template_develop_story.format(idea=idea, user_requirement=user_requirement)),
        ]
        
        print(f"[Screenwriter.develop_story] System prompt length: {len(system_prompt_template_develop_story)} chars")
        print(f"[Screenwriter.develop_story] Human prompt length: {len(messages[1][1])} chars")
        
        # Retry logic with exponential backoff for rate limits
        max_retries = 3  # Retries for primary model
        base_delay = 2  # seconds
        
        # Try primary model first
        for attempt in range(max_retries):
            try:
                print(f"[Screenwriter.develop_story] Attempt {attempt + 1}/{max_retries} (Primary Model): Calling LLM with {len(messages)} messages...")
                
                response = await self.chat_model.ainvoke(messages)
                print(f"[Screenwriter.develop_story] ✅ LLM response received")
                print(f"[Screenwriter.develop_story] Response type: {type(response)}")
                print(f"[Screenwriter.develop_story] Response has content: {hasattr(response, 'content')}")
                
                if hasattr(response, 'content'):
                    story = response.content
                    print(f"[Screenwriter.develop_story] Story length: {len(story)} chars")
                    print(f"[Screenwriter.develop_story] Story preview (first 500 chars):")
                    print(f"{story[:500]}")
                    print(f"[Screenwriter.develop_story] Story preview (last 200 chars):")
                    print(f"{story[-200:]}")
                    print(f"{'='*80}\n")
                    return story
                else:
                    print(f"[Screenwriter.develop_story] ❌ ERROR: Response has no 'content' attribute")
                    print(f"[Screenwriter.develop_story] Response object: {response}")
                    print(f"{'='*80}\n")
                    raise AttributeError(f"LLM response has no 'content' attribute: {type(response)}")
                    
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = base_delay * (2 ** attempt)
                    print(f"[Screenwriter.develop_story] ⚠️ Rate limit hit (429) on primary model")
                    print(f"[Screenwriter.develop_story] Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Primary model failed after retries, try fallback
                    if self.fallback_chat_model:
                        print(f"[Screenwriter.develop_story] ⚠️ Primary model rate limited after {max_retries} attempts")
                        print(f"[Screenwriter.develop_story] 🔄 Switching to fallback model (DeepSeek)...")
                        print(f"{'='*80}\n")
                        break  # Exit retry loop to try fallback
                    else:
                        print(f"[Screenwriter.develop_story] ❌ Rate limit error after {max_retries} attempts, no fallback available")
                        print(f"[Screenwriter.develop_story] Exception: {str(e)}")
                        print(f"{'='*80}\n")
                        raise
                    
            except Exception as e:
                print(f"[Screenwriter.develop_story] ❌ EXCEPTION during LLM call")
                print(f"[Screenwriter.develop_story] Exception type: {type(e).__name__}")
                print(f"[Screenwriter.develop_story] Exception message: {str(e)}")
                import traceback
                print(f"[Screenwriter.develop_story] Traceback:")
                traceback.print_exc()
                print(f"{'='*80}\n")
                raise
        
        # Try fallback model if primary failed
        if self.fallback_chat_model:
            try:
                print(f"\n{'='*80}")
                print(f"[Screenwriter.develop_story] FALLBACK MODEL ATTEMPT")
                print(f"{'='*80}")
                print(f"[Screenwriter.develop_story] Using DeepSeek as fallback...")
                
                response = await self.fallback_chat_model.ainvoke(messages)
                print(f"[Screenwriter.develop_story] ✅ Fallback LLM response received")
                print(f"[Screenwriter.develop_story] Response type: {type(response)}")
                
                if hasattr(response, 'content'):
                    story = response.content
                    print(f"[Screenwriter.develop_story] Story length: {len(story)} chars")
                    print(f"[Screenwriter.develop_story] Story preview (first 500 chars):")
                    print(f"{story[:500]}")
                    print(f"[Screenwriter.develop_story] ✅ Successfully generated story using fallback model")
                    print(f"{'='*80}\n")
                    return story
                else:
                    print(f"[Screenwriter.develop_story] ❌ Fallback response has no 'content' attribute")
                    print(f"{'='*80}\n")
                    raise AttributeError(f"Fallback LLM response has no 'content' attribute: {type(response)}")
                    
            except Exception as fallback_error:
                print(f"[Screenwriter.develop_story] ❌ Fallback model also failed")
                print(f"[Screenwriter.develop_story] Fallback error: {type(fallback_error).__name__}: {str(fallback_error)}")
                print(f"{'='*80}\n")
                raise Exception(f"Both primary and fallback models failed. Primary: RateLimitError, Fallback: {type(fallback_error).__name__}")
        
        # Should never reach here, but just in case
        raise Exception("Failed to generate story after all retry attempts")


    async def write_script_based_on_story(
        self,
        story: str,
        user_requirement: Optional[str] = None,
    ) -> List[str]:


        class WriteScriptBasedOnStoryResponse(BaseModel):
            script: List[str] = Field(
                ...,
                description="The script based on the story. Each element is a scene "
            )

        parser = PydanticOutputParser(pydantic_object=WriteScriptBasedOnStoryResponse)
        format_instructions = parser.get_format_instructions()

        messages = [
            ("system", system_prompt_template_write_script_based_on_story.format(format_instructions=format_instructions)),
            ("human", human_prompt_template_write_script_based_on_story.format(story=story, user_requirement=user_requirement)),
        ]
        response = await self.chat_model.ainvoke(messages)
        response = parser.parse(response.content)
        script = response.script
        return script



