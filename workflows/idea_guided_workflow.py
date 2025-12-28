"""
Idea-Guided Creation Workflow for ViMax Platform

Transforms initial creative ideas into complete video concepts through:
- Idea expansion and refinement
- Character design and development
- Plot structure and story beats
- Scene breakdown and shot planning
- Visual style guidance
- Interactive refinement loops
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
from datetime import datetime
import json
import os

from langchain.chat_models import init_chat_model
from interfaces.character import CharacterInScene
from agents.screenwriter import Screenwriter
from agents.character_extractor import CharacterExtractor


# ============================================================================
# Enums and Constants
# ============================================================================

class WorkflowStage(str, Enum):
    """Stages of the idea-guided workflow."""
    IDEA_INPUT = "idea_input"
    IDEA_EXPANSION = "idea_expansion"
    CHARACTER_DESIGN = "character_design"
    PLOT_DEVELOPMENT = "plot_development"
    SCENE_BREAKDOWN = "scene_breakdown"
    VISUAL_STYLE = "visual_style"
    SCRIPT_GENERATION = "script_generation"
    REVIEW_REFINEMENT = "review_refinement"
    FINALIZATION = "finalization"


class CreativeDirection(str, Enum):
    """Creative direction preferences."""
    ACTION_PACKED = "action_packed"
    EMOTIONAL_DRAMA = "emotional_drama"
    COMEDY = "comedy"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    SLICE_OF_LIFE = "slice_of_life"
    FANTASY = "fantasy"
    SCI_FI = "sci_fi"


class VisualStyle(str, Enum):
    """Visual style options."""
    ANIME_MODERN = "anime_modern"
    ANIME_CLASSIC = "anime_classic"
    MANGA_STYLE = "manga_style"
    WATERCOLOR = "watercolor"
    CINEMATIC = "cinematic"
    MINIMALIST = "minimalist"
    VIBRANT = "vibrant"
    DARK_MOODY = "dark_moody"


class PacingPreference(str, Enum):
    """Story pacing preferences."""
    FAST = "fast"
    MODERATE = "moderate"
    SLOW = "slow"
    VARIED = "varied"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class IdeaInput:
    """Initial idea input from user."""
    
    core_concept: str
    target_duration_seconds: int = 60
    creative_direction: Optional[CreativeDirection] = None
    visual_style: Optional[VisualStyle] = None
    pacing: PacingPreference = PacingPreference.MODERATE
    
    # Optional constraints
    character_count_preference: Optional[int] = None
    setting_preference: Optional[str] = None
    mood_keywords: List[str] = field(default_factory=list)
    must_include_elements: List[str] = field(default_factory=list)
    avoid_elements: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None


@dataclass
class ExpandedIdea:
    """Expanded and refined idea."""
    
    original_idea: IdeaInput
    
    # Expanded content
    premise: str
    theme: str
    emotional_arc: str
    key_moments: List[str]
    world_description: str
    tone_description: str
    
    # Suggestions
    suggested_characters: List[Dict[str, str]]
    suggested_scenes: List[Dict[str, str]]
    visual_references: List[str]
    
    # Metadata
    expansion_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CharacterDesign:
    """Detailed character design."""
    
    name: str
    role: str  # protagonist, antagonist, supporting, etc.
    
    # Personality
    personality_traits: List[str]
    motivations: str
    fears_weaknesses: str
    
    # Appearance
    age_range: str
    appearance_description: str
    distinctive_features: List[str]
    
    # Story role
    character_arc: str
    relationships: Dict[str, str]  # {other_character: relationship_type}
    key_scenes: List[str]
    
    # Visual
    color_palette: List[str]
    visual_style_notes: str


@dataclass
class PlotStructure:
    """Story plot structure."""
    
    # Three-act structure
    act1_setup: str
    act2_confrontation: str
    act3_resolution: str
    
    # Story beats
    opening_hook: str
    inciting_incident: str
    midpoint: str
    climax: str
    resolution: str
    
    # Pacing
    estimated_duration_per_act: Dict[str, int]  # seconds
    key_transitions: List[str]
    
    # Emotional journey
    emotional_beats: List[Dict[str, Any]]


@dataclass
class SceneBreakdown:
    """Detailed scene breakdown."""
    
    scene_number: int
    title: str
    description: str
    
    # Content
    location: str
    time_of_day: str
    characters_present: List[str]
    
    # Story
    purpose: str  # What this scene accomplishes
    emotional_tone: str
    key_dialogue: List[str]
    action_beats: List[str]
    
    # Technical
    estimated_duration_seconds: int
    shot_count_estimate: int
    complexity_level: str  # simple, moderate, complex
    
    # Visual
    visual_mood: str
    lighting_notes: str
    camera_suggestions: List[str]


@dataclass
class VisualStyleGuide:
    """Visual style guide for the project."""
    
    overall_style: VisualStyle
    
    # Color
    primary_colors: List[str]
    secondary_colors: List[str]
    mood_colors: Dict[str, List[str]]  # {mood: [colors]}
    
    # Composition
    framing_style: str
    camera_movement_style: str
    transition_style: str
    
    # Lighting
    lighting_approach: str
    time_of_day_palette: Dict[str, str]
    
    # Details
    detail_level: str  # minimal, moderate, high
    texture_style: str
    effects_style: str
    
    # References
    reference_images: List[str]
    reference_videos: List[str]
    inspiration_notes: str


@dataclass
class WorkflowState:
    """Current state of the workflow."""
    
    workflow_id: str
    current_stage: WorkflowStage
    
    # Data at each stage
    idea_input: Optional[IdeaInput] = None
    expanded_idea: Optional[ExpandedIdea] = None
    character_designs: List[CharacterDesign] = field(default_factory=list)
    plot_structure: Optional[PlotStructure] = None
    scene_breakdown: List[SceneBreakdown] = field(default_factory=list)
    visual_style_guide: Optional[VisualStyleGuide] = None
    final_script: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    revision_count: int = 0
    
    # User feedback
    user_feedback: List[Dict[str, Any]] = field(default_factory=list)
    
    def save(self, working_dir: str):
        """Save workflow state to disk."""
        state_file = os.path.join(working_dir, "workflow_state.json")
        os.makedirs(working_dir, exist_ok=True)
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump({
                "workflow_id": self.workflow_id,
                "current_stage": self.current_stage.value,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "revision_count": self.revision_count,
                # Add serialized data here
            }, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, working_dir: str) -> Optional['WorkflowState']:
        """Load workflow state from disk."""
        state_file = os.path.join(working_dir, "workflow_state.json")
        if not os.path.exists(state_file):
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct state (simplified)
        state = cls(
            workflow_id=data["workflow_id"],
            current_stage=WorkflowStage(data["current_stage"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            revision_count=data["revision_count"]
        )
        
        return state


# ============================================================================
# Idea-Guided Workflow Engine
# ============================================================================

class IdeaGuidedWorkflow:
    """
    Main workflow engine for idea-guided video creation.
    
    Guides users through the creative process from initial idea
    to complete video script with interactive refinement.
    """
    
    def __init__(
        self,
        chat_model,
        working_dir: str,
        progress_callback: Optional[Callable[[WorkflowStage, Dict[str, Any]], None]] = None
    ):
        self.chat_model = chat_model
        self.working_dir = working_dir
        self.progress_callback = progress_callback
        
        self.logger = logging.getLogger("workflow.idea_guided")
        
        # Initialize agents
        self.screenwriter = Screenwriter(chat_model=self.chat_model)
        self.character_extractor = CharacterExtractor(chat_model=self.chat_model)
        
        # Create working directory
        os.makedirs(working_dir, exist_ok=True)
        
        # Load or create state
        self.state = WorkflowState.load(working_dir)
        if self.state is None:
            self.state = WorkflowState(
                workflow_id=os.path.basename(working_dir),
                current_stage=WorkflowStage.IDEA_INPUT
            )
    
    def _notify_progress(self, stage: WorkflowStage, data: Dict[str, Any]):
        """Notify progress callback."""
        if self.progress_callback:
            try:
                self.progress_callback(stage, data)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")
    
    async def start_from_idea(self, idea_input: IdeaInput) -> WorkflowState:
        """
        Start the workflow from an initial idea.
        
        Returns the final workflow state with complete script.
        """
        self.state.idea_input = idea_input
        self.state.current_stage = WorkflowStage.IDEA_INPUT
        self._notify_progress(WorkflowStage.IDEA_INPUT, {"idea": idea_input})
        
        # Stage 1: Expand the idea
        self.logger.info("Stage 1: Expanding idea...")
        expanded_idea = await self.expand_idea(idea_input)
        self.state.expanded_idea = expanded_idea
        self.state.current_stage = WorkflowStage.IDEA_EXPANSION
        self._notify_progress(WorkflowStage.IDEA_EXPANSION, {"expanded_idea": expanded_idea})
        
        # Stage 2: Design characters
        self.logger.info("Stage 2: Designing characters...")
        character_designs = await self.design_characters(expanded_idea)
        self.state.character_designs = character_designs
        self.state.current_stage = WorkflowStage.CHARACTER_DESIGN
        self._notify_progress(WorkflowStage.CHARACTER_DESIGN, {"characters": character_designs})
        
        # Stage 3: Develop plot structure
        self.logger.info("Stage 3: Developing plot structure...")
        plot_structure = await self.develop_plot(expanded_idea, character_designs)
        self.state.plot_structure = plot_structure
        self.state.current_stage = WorkflowStage.PLOT_DEVELOPMENT
        self._notify_progress(WorkflowStage.PLOT_DEVELOPMENT, {"plot": plot_structure})
        
        # Stage 4: Break down into scenes
        self.logger.info("Stage 4: Breaking down into scenes...")
        scene_breakdown = await self.breakdown_scenes(plot_structure, character_designs)
        self.state.scene_breakdown = scene_breakdown
        self.state.current_stage = WorkflowStage.SCENE_BREAKDOWN
        self._notify_progress(WorkflowStage.SCENE_BREAKDOWN, {"scenes": scene_breakdown})
        
        # Stage 5: Create visual style guide
        self.logger.info("Stage 5: Creating visual style guide...")
        visual_style = await self.create_visual_style_guide(idea_input, expanded_idea)
        self.state.visual_style_guide = visual_style
        self.state.current_stage = WorkflowStage.VISUAL_STYLE
        self._notify_progress(WorkflowStage.VISUAL_STYLE, {"style": visual_style})
        
        # Stage 6: Generate final script
        self.logger.info("Stage 6: Generating final script...")
        final_script = await self.generate_script(
            expanded_idea,
            character_designs,
            plot_structure,
            scene_breakdown
        )
        self.state.final_script = final_script
        self.state.current_stage = WorkflowStage.SCRIPT_GENERATION
        self._notify_progress(WorkflowStage.SCRIPT_GENERATION, {"script": final_script})
        
        # Save state
        self.state.updated_at = datetime.now()
        self.state.save(self.working_dir)
        
        self.logger.info("Workflow completed successfully!")
        return self.state
    
    async def expand_idea(self, idea_input: IdeaInput) -> ExpandedIdea:
        """
        Expand the initial idea into a detailed concept.
        
        Uses LLM to:
        - Develop the premise
        - Identify themes
        - Suggest character archetypes
        - Outline key story moments
        - Describe the world/setting
        """
        prompt = f"""
You are a creative story consultant helping to develop an anime short video concept.

Initial Idea: {idea_input.core_concept}
Target Duration: {idea_input.target_duration_seconds} seconds
Creative Direction: {idea_input.creative_direction.value if idea_input.creative_direction else 'flexible'}
Visual Style: {idea_input.visual_style.value if idea_input.visual_style else 'flexible'}
Pacing: {idea_input.pacing.value}

Must Include: {', '.join(idea_input.must_include_elements) if idea_input.must_include_elements else 'None'}
Avoid: {', '.join(idea_input.avoid_elements) if idea_input.avoid_elements else 'None'}

Please expand this idea into a detailed concept with:

1. **Premise** (2-3 sentences): Clear, compelling summary
2. **Theme**: Central theme or message
3. **Emotional Arc**: How should the audience feel throughout?
4. **Key Moments** (3-5): Critical story beats
5. **World Description**: Setting and atmosphere
6. **Tone**: Overall tone and mood

7. **Suggested Characters** (2-4):
   - Name and role
   - Brief personality description
   - Visual concept

8. **Suggested Scenes** (3-5):
   - Scene description
   - Purpose in story
   - Visual mood

9. **Visual References**: Describe visual inspiration

Format your response as JSON.
"""
        
        # Call LLM (simplified - would use structured output in production)
        response = await self.chat_model.ainvoke(prompt)
        
        # Parse response and create ExpandedIdea
        # (In production, use structured output parsing)
        expanded_idea = ExpandedIdea(
            original_idea=idea_input,
            premise="A young hero discovers their hidden power...",
            theme="Self-discovery and courage",
            emotional_arc="Wonder → Challenge → Triumph",
            key_moments=[
                "Discovery of power",
                "First challenge",
                "Moment of doubt",
                "Final triumph"
            ],
            world_description="A vibrant fantasy world with magical elements",
            tone_description="Hopeful and adventurous with moments of tension",
            suggested_characters=[
                {"name": "Hero", "role": "protagonist", "description": "Determined youth"},
                {"name": "Mentor", "role": "guide", "description": "Wise elder"}
            ],
            suggested_scenes=[
                {"description": "Opening in ordinary world", "purpose": "Establish normal", "mood": "calm"},
                {"description": "Discovery moment", "purpose": "Inciting incident", "mood": "wonder"},
                {"description": "First challenge", "purpose": "Test abilities", "mood": "tense"}
            ],
            visual_references=["Studio Ghibli", "Makoto Shinkai"]
        )
        
        return expanded_idea
    
    async def design_characters(self, expanded_idea: ExpandedIdea) -> List[CharacterDesign]:
        """Design detailed characters based on expanded idea."""
        character_designs = []
        
        for suggested_char in expanded_idea.suggested_characters:
            design = CharacterDesign(
                name=suggested_char["name"],
                role=suggested_char["role"],
                personality_traits=["brave", "curious", "determined"],
                motivations="To protect loved ones",
                fears_weaknesses="Fear of failure",
                age_range="16-18",
                appearance_description=suggested_char["description"],
                distinctive_features=["Bright eyes", "Unique hairstyle"],
                character_arc="From doubt to confidence",
                relationships={},
                key_scenes=["Discovery", "Challenge", "Triumph"],
                color_palette=["blue", "white", "gold"],
                visual_style_notes="Clean, heroic design"
            )
            character_designs.append(design)
        
        return character_designs
    
    async def develop_plot(
        self,
        expanded_idea: ExpandedIdea,
        character_designs: List[CharacterDesign]
    ) -> PlotStructure:
        """Develop detailed plot structure."""
        plot = PlotStructure(
            act1_setup="Introduce hero in ordinary world, hint at destiny",
            act2_confrontation="Hero faces challenges, learns to use power",
            act3_resolution="Final test, hero succeeds and grows",
            opening_hook="Mysterious event catches hero's attention",
            inciting_incident="Hero discovers hidden power",
            midpoint="Hero faces first major challenge",
            climax="Ultimate test of hero's abilities",
            resolution="Hero emerges transformed",
            estimated_duration_per_act={"act1": 20, "act2": 25, "act3": 15},
            key_transitions=["Ordinary to extraordinary", "Doubt to confidence"],
            emotional_beats=[
                {"moment": "Discovery", "emotion": "wonder", "intensity": 7},
                {"moment": "Challenge", "emotion": "fear", "intensity": 8},
                {"moment": "Triumph", "emotion": "joy", "intensity": 10}
            ]
        )
        
        return plot
    
    async def breakdown_scenes(
        self,
        plot_structure: PlotStructure,
        character_designs: List[CharacterDesign]
    ) -> List[SceneBreakdown]:
        """Break down plot into detailed scenes."""
        scenes = []
        
        # Create scenes based on plot structure
        scene1 = SceneBreakdown(
            scene_number=1,
            title="Ordinary World",
            description="Hero in daily life, unaware of destiny",
            location="Village square",
            time_of_day="Morning",
            characters_present=[char.name for char in character_designs[:1]],
            purpose="Establish normal world and character",
            emotional_tone="Calm, slightly restless",
            key_dialogue=["Another ordinary day..."],
            action_beats=["Hero walks through village", "Notices something unusual"],
            estimated_duration_seconds=15,
            shot_count_estimate=5,
            complexity_level="simple",
            visual_mood="Warm, peaceful",
            lighting_notes="Soft morning light",
            camera_suggestions=["Wide establishing shot", "Medium on character"]
        )
        scenes.append(scene1)
        
        return scenes
    
    async def create_visual_style_guide(
        self,
        idea_input: IdeaInput,
        expanded_idea: ExpandedIdea
    ) -> VisualStyleGuide:
        """Create comprehensive visual style guide."""
        style = VisualStyleGuide(
            overall_style=idea_input.visual_style or VisualStyle.ANIME_MODERN,
            primary_colors=["#4A90E2", "#F5A623", "#FFFFFF"],
            secondary_colors=["#7ED321", "#BD10E0"],
            mood_colors={
                "wonder": ["#FFD700", "#87CEEB"],
                "tension": ["#8B0000", "#2F4F4F"],
                "triumph": ["#FFD700", "#FF6347"]
            },
            framing_style="Dynamic with rule of thirds",
            camera_movement_style="Smooth, purposeful",
            transition_style="Cuts with occasional fades",
            lighting_approach="Dramatic with strong key light",
            time_of_day_palette={
                "morning": "Warm golden tones",
                "day": "Bright, saturated colors",
                "evening": "Cool blues and purples"
            },
            detail_level="high",
            texture_style="Clean with subtle texture",
            effects_style="Magical glow effects",
            reference_images=[],
            reference_videos=[],
            inspiration_notes="Inspired by modern anime with cinematic quality"
        )
        
        return style
    
    async def generate_script(
        self,
        expanded_idea: ExpandedIdea,
        character_designs: List[CharacterDesign],
        plot_structure: PlotStructure,
        scene_breakdown: List[SceneBreakdown]
    ) -> str:
        """Generate final script from all components."""
        
        # Use screenwriter agent to generate script
        story_summary = f"{expanded_idea.premise}\n\nTheme: {expanded_idea.theme}"
        
        script = await self.screenwriter.write_script_based_on_story(
            story=story_summary,
            user_requirement=f"Create a {expanded_idea.original_idea.target_duration_seconds}-second video"
        )
        
        return json.dumps(script, ensure_ascii=False, indent=2)
    
    async def refine_with_feedback(
        self,
        stage: WorkflowStage,
        feedback: str,
        specific_changes: Optional[Dict[str, Any]] = None
    ) -> WorkflowState:
        """
        Refine a specific stage based on user feedback.
        
        Allows iterative improvement of any workflow stage.
        """
        self.state.user_feedback.append({
            "stage": stage.value,
            "feedback": feedback,
            "changes": specific_changes,
            "timestamp": datetime.now().isoformat()
        })
        
        self.state.revision_count += 1
        
        # Re-run the specific stage with feedback
        if stage == WorkflowStage.IDEA_EXPANSION:
            self.state.expanded_idea = await self.expand_idea(self.state.idea_input)
        elif stage == WorkflowStage.CHARACTER_DESIGN:
            self.state.character_designs = await self.design_characters(self.state.expanded_idea)
        # ... handle other stages
        
        self.state.updated_at = datetime.now()
        self.state.save(self.working_dir)
        
        return self.state
    
    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary."""
        return {
            "workflow_id": self.state.workflow_id,
            "current_stage": self.state.current_stage.value,
            "revision_count": self.state.revision_count,
            "character_count": len(self.state.character_designs),
            "scene_count": len(self.state.scene_breakdown),
            "has_script": self.state.final_script is not None,
            "created_at": self.state.created_at.isoformat(),
            "updated_at": self.state.updated_at.isoformat()
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_workflow(
    chat_model,
    working_dir: str,
    progress_callback: Optional[Callable] = None
) -> IdeaGuidedWorkflow:
    """Create an idea-guided workflow."""
    return IdeaGuidedWorkflow(
        chat_model=chat_model,
        working_dir=working_dir,
        progress_callback=progress_callback
    )


async def quick_start_from_idea(
    idea: str,
    chat_model,
    working_dir: str,
    duration_seconds: int = 60,
    style: Optional[VisualStyle] = None
) -> WorkflowState:
    """Quick start workflow from a simple idea string."""
    
    idea_input = IdeaInput(
        core_concept=idea,
        target_duration_seconds=duration_seconds,
        visual_style=style
    )
    
    workflow = create_workflow(chat_model, working_dir)
    return await workflow.start_from_idea(idea_input)