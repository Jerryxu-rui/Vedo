"""
Workflows module for ViMax Platform.

Provides high-level workflows for video creation including:
- Idea-guided creation workflow
- Script parsing and analysis
- End-to-end video generation pipelines
"""

from workflows.idea_guided_workflow import (
    IdeaGuidedWorkflow,
    IdeaInput,
    ExpandedIdea,
    CharacterDesign,
    PlotStructure,
    SceneBreakdown,
    VisualStyleGuide,
    WorkflowState,
    WorkflowStage,
    CreativeDirection,
    VisualStyle,
    PacingPreference,
    create_workflow,
    quick_start_from_idea
)

from workflows.script_analyzer import (
    ScriptParser,
    ScriptAnalyzer,
    ScriptAnalysis,
    ParsedScene,
    CharacterProfile,
    DialogueLine,
    SceneElement,
    ScriptFormat,
    ComplexityLevel,
    SceneType,
    parse_and_analyze_script,
    get_script_summary
)

__all__ = [
    # Idea-Guided Workflow
    "IdeaGuidedWorkflow",
    "IdeaInput",
    "ExpandedIdea",
    "CharacterDesign",
    "PlotStructure",
    "SceneBreakdown",
    "VisualStyleGuide",
    "WorkflowState",
    "WorkflowStage",
    "CreativeDirection",
    "VisualStyle",
    "PacingPreference",
    "create_workflow",
    "quick_start_from_idea",
    
    # Script Analysis
    "ScriptParser",
    "ScriptAnalyzer",
    "ScriptAnalysis",
    "ParsedScene",
    "CharacterProfile",
    "DialogueLine",
    "SceneElement",
    "ScriptFormat",
    "ComplexityLevel",
    "SceneType",
    "parse_and_analyze_script",
    "get_script_summary"
]