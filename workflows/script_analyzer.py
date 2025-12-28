"""
Script Parsing and Analysis Module for ViMax Platform

Provides comprehensive script analysis including:
- Script structure parsing
- Character analysis and tracking
- Scene complexity assessment
- Dialogue extraction and analysis
- Visual requirements identification
- Technical feasibility scoring
- Cost estimation
- Timeline prediction
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import json


# ============================================================================
# Enums and Constants
# ============================================================================

class ScriptFormat(str, Enum):
    """Supported script formats."""
    SCREENPLAY = "screenplay"
    NOVEL = "novel"
    OUTLINE = "outline"
    JSON = "json"
    PLAIN_TEXT = "plain_text"


class ComplexityLevel(str, Enum):
    """Complexity levels for scenes."""
    SIMPLE = "simple"  # 1-2 characters, simple action
    MODERATE = "moderate"  # 3-4 characters, moderate action
    COMPLEX = "complex"  # 5+ characters, complex action
    VERY_COMPLEX = "very_complex"  # Large cast, intricate choreography


class SceneType(str, Enum):
    """Types of scenes."""
    DIALOGUE = "dialogue"
    ACTION = "action"
    TRANSITION = "transition"
    ESTABLISHING = "establishing"
    MONTAGE = "montage"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class DialogueLine:
    """A single line of dialogue."""
    character: str
    text: str
    emotion: Optional[str] = None
    action: Optional[str] = None  # Parenthetical action
    line_number: int = 0


@dataclass
class SceneElement:
    """An element within a scene."""
    element_type: str  # dialogue, action, description
    content: str
    characters_involved: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ParsedScene:
    """A parsed scene from the script."""
    
    scene_number: int
    heading: str
    location: str
    time_of_day: str
    
    # Content
    description: str
    dialogue_lines: List[DialogueLine] = field(default_factory=list)
    action_lines: List[str] = field(default_factory=list)
    elements: List[SceneElement] = field(default_factory=list)
    
    # Characters
    characters_present: List[str] = field(default_factory=list)
    character_actions: Dict[str, List[str]] = field(default_factory=dict)
    
    # Analysis
    scene_type: SceneType = SceneType.DIALOGUE
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    estimated_duration_seconds: int = 30
    
    # Visual requirements
    required_props: List[str] = field(default_factory=list)
    required_effects: List[str] = field(default_factory=list)
    camera_suggestions: List[str] = field(default_factory=list)
    
    # Technical
    shot_count_estimate: int = 5
    difficulty_score: float = 1.0  # 1.0 = easy, 5.0 = very difficult


@dataclass
class CharacterProfile:
    """Profile of a character in the script."""
    
    name: str
    aliases: List[str] = field(default_factory=list)
    
    # Appearance
    total_scenes: int = 0
    scene_numbers: List[int] = field(default_factory=list)
    first_appearance: Optional[int] = None
    last_appearance: Optional[int] = None
    
    # Dialogue
    total_dialogue_lines: int = 0
    dialogue_samples: List[str] = field(default_factory=list)
    speaking_style: Optional[str] = None
    
    # Relationships
    interactions_with: Dict[str, int] = field(default_factory=dict)  # {character: count}
    
    # Analysis
    importance_score: float = 0.0  # Based on screen time, dialogue, etc.
    character_arc: Optional[str] = None


@dataclass
class ScriptAnalysis:
    """Comprehensive script analysis results."""
    
    # Basic info
    title: Optional[str] = None
    format: ScriptFormat = ScriptFormat.PLAIN_TEXT
    total_scenes: int = 0
    total_pages: int = 0
    
    # Parsed content
    scenes: List[ParsedScene] = field(default_factory=list)
    characters: Dict[str, CharacterProfile] = field(default_factory=dict)
    
    # Structure
    act_breaks: List[int] = field(default_factory=list)  # Scene numbers where acts break
    key_moments: List[Dict[str, Any]] = field(default_factory=list)
    
    # Statistics
    total_dialogue_lines: int = 0
    total_action_lines: int = 0
    average_scene_length: float = 0.0
    
    # Complexity
    overall_complexity: ComplexityLevel = ComplexityLevel.MODERATE
    complexity_distribution: Dict[ComplexityLevel, int] = field(default_factory=dict)
    
    # Technical requirements
    unique_locations: List[str] = field(default_factory=list)
    required_props: List[str] = field(default_factory=list)
    required_effects: List[str] = field(default_factory=list)
    
    # Estimates
    estimated_total_duration_seconds: int = 0
    estimated_shot_count: int = 0
    estimated_cost_usd: float = 0.0
    estimated_production_days: int = 0
    
    # Feasibility
    feasibility_score: float = 0.0  # 0-100
    technical_challenges: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# ============================================================================
# Script Parser
# ============================================================================

class ScriptParser:
    """Parses scripts in various formats."""
    
    def __init__(self):
        self.logger = logging.getLogger("script_parser")
    
    def parse(self, script_text: str, format: ScriptFormat = ScriptFormat.PLAIN_TEXT) -> ScriptAnalysis:
        """Parse script and return analysis."""
        
        if format == ScriptFormat.JSON:
            return self._parse_json(script_text)
        elif format == ScriptFormat.SCREENPLAY:
            return self._parse_screenplay(script_text)
        elif format == ScriptFormat.NOVEL:
            return self._parse_novel(script_text)
        else:
            return self._parse_plain_text(script_text)
    
    def _parse_json(self, script_text: str) -> ScriptAnalysis:
        """Parse JSON format script."""
        try:
            data = json.loads(script_text)
            analysis = ScriptAnalysis(format=ScriptFormat.JSON)
            
            # Parse scenes from JSON
            for i, scene_data in enumerate(data):
                scene = ParsedScene(
                    scene_number=i,
                    heading=scene_data.get("heading", f"Scene {i}"),
                    location=scene_data.get("location", "Unknown"),
                    time_of_day=scene_data.get("time", "Day"),
                    description=scene_data.get("description", "")
                )
                analysis.scenes.append(scene)
            
            analysis.total_scenes = len(analysis.scenes)
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON script: {e}")
            return ScriptAnalysis()
    
    def _parse_screenplay(self, script_text: str) -> ScriptAnalysis:
        """Parse screenplay format (Fountain, Final Draft, etc.)."""
        analysis = ScriptAnalysis(format=ScriptFormat.SCREENPLAY)
        
        lines = script_text.split('\n')
        current_scene = None
        scene_number = 0
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            if not line:
                continue
            
            # Scene heading (INT./EXT.)
            if self._is_scene_heading(line):
                if current_scene:
                    analysis.scenes.append(current_scene)
                
                location, time = self._parse_scene_heading(line)
                current_scene = ParsedScene(
                    scene_number=scene_number,
                    heading=line,
                    location=location,
                    time_of_day=time,
                    description=""
                )
                scene_number += 1
            
            # Character name (all caps, centered)
            elif line.isupper() and len(line) < 30 and current_scene:
                character = line.strip()
                if character not in analysis.characters:
                    analysis.characters[character] = CharacterProfile(name=character)
                
                if character not in current_scene.characters_present:
                    current_scene.characters_present.append(character)
            
            # Dialogue or action
            elif current_scene:
                current_scene.description += line + " "
        
        if current_scene:
            analysis.scenes.append(current_scene)
        
        analysis.total_scenes = len(analysis.scenes)
        return analysis
    
    def _parse_novel(self, script_text: str) -> ScriptAnalysis:
        """Parse novel/prose format."""
        analysis = ScriptAnalysis(format=ScriptFormat.NOVEL)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in script_text.split('\n\n') if p.strip()]
        
        # Simple scene detection based on paragraph breaks
        scene_number = 0
        for para in paragraphs:
            if len(para) > 50:  # Substantial paragraph
                scene = ParsedScene(
                    scene_number=scene_number,
                    heading=f"Scene {scene_number}",
                    location="Unknown",
                    time_of_day="Unknown",
                    description=para
                )
                
                # Extract character names (capitalized words)
                characters = self._extract_character_names(para)
                scene.characters_present = characters
                
                for char in characters:
                    if char not in analysis.characters:
                        analysis.characters[char] = CharacterProfile(name=char)
                
                analysis.scenes.append(scene)
                scene_number += 1
        
        analysis.total_scenes = len(analysis.scenes)
        return analysis
    
    def _parse_plain_text(self, script_text: str) -> ScriptAnalysis:
        """Parse plain text format."""
        analysis = ScriptAnalysis(format=ScriptFormat.PLAIN_TEXT)
        
        # Simple parsing: split by double newlines or scene markers
        sections = re.split(r'\n\n+|Scene \d+', script_text)
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            scene = ParsedScene(
                scene_number=i,
                heading=f"Scene {i}",
                location="Unknown",
                time_of_day="Unknown",
                description=section.strip()
            )
            
            # Extract characters
            characters = self._extract_character_names(section)
            scene.characters_present = characters
            
            for char in characters:
                if char not in analysis.characters:
                    analysis.characters[char] = CharacterProfile(name=char)
            
            analysis.scenes.append(scene)
        
        analysis.total_scenes = len(analysis.scenes)
        return analysis
    
    def _is_scene_heading(self, line: str) -> bool:
        """Check if line is a scene heading."""
        return bool(re.match(r'^(INT\.|EXT\.|INT/EXT\.)', line.upper()))
    
    def _parse_scene_heading(self, heading: str) -> Tuple[str, str]:
        """Parse location and time from scene heading."""
        # Example: "INT. COFFEE SHOP - DAY"
        parts = heading.split('-')
        location = parts[0].strip() if parts else "Unknown"
        time = parts[1].strip() if len(parts) > 1 else "Day"
        return location, time
    
    def _extract_character_names(self, text: str) -> List[str]:
        """Extract character names from text."""
        # Simple heuristic: capitalized words that appear multiple times
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        
        # Count occurrences
        word_counts = {}
        for word in words:
            if len(word) > 2:  # Ignore short words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Return words that appear 2+ times (likely character names)
        characters = [word for word, count in word_counts.items() if count >= 2]
        return characters[:10]  # Limit to top 10


# ============================================================================
# Script Analyzer
# ============================================================================

class ScriptAnalyzer:
    """Analyzes parsed scripts for complexity, feasibility, and requirements."""
    
    def __init__(self):
        self.logger = logging.getLogger("script_analyzer")
    
    def analyze(self, parsed_script: ScriptAnalysis) -> ScriptAnalysis:
        """Perform comprehensive analysis on parsed script."""
        
        # Analyze each scene
        for scene in parsed_script.scenes:
            self._analyze_scene(scene)
        
        # Analyze characters
        self._analyze_characters(parsed_script)
        
        # Calculate statistics
        self._calculate_statistics(parsed_script)
        
        # Assess complexity
        self._assess_complexity(parsed_script)
        
        # Identify requirements
        self._identify_requirements(parsed_script)
        
        # Estimate costs and timeline
        self._estimate_production(parsed_script)
        
        # Calculate feasibility
        self._calculate_feasibility(parsed_script)
        
        # Generate recommendations
        self._generate_recommendations(parsed_script)
        
        return parsed_script
    
    def _analyze_scene(self, scene: ParsedScene):
        """Analyze a single scene."""
        
        # Determine scene type
        dialogue_ratio = len(scene.dialogue_lines) / max(len(scene.elements), 1)
        if dialogue_ratio > 0.7:
            scene.scene_type = SceneType.DIALOGUE
        elif len(scene.action_lines) > len(scene.dialogue_lines):
            scene.scene_type = SceneType.ACTION
        else:
            scene.scene_type = SceneType.DIALOGUE
        
        # Assess complexity
        char_count = len(scene.characters_present)
        action_count = len(scene.action_lines)
        
        if char_count <= 2 and action_count <= 3:
            scene.complexity = ComplexityLevel.SIMPLE
            scene.difficulty_score = 1.0
        elif char_count <= 4 and action_count <= 6:
            scene.complexity = ComplexityLevel.MODERATE
            scene.difficulty_score = 2.0
        elif char_count <= 6 and action_count <= 10:
            scene.complexity = ComplexityLevel.COMPLEX
            scene.difficulty_score = 3.5
        else:
            scene.complexity = ComplexityLevel.VERY_COMPLEX
            scene.difficulty_score = 5.0
        
        # Estimate duration (rough heuristic)
        dialogue_time = len(scene.dialogue_lines) * 3  # 3 seconds per line
        action_time = len(scene.action_lines) * 5  # 5 seconds per action
        scene.estimated_duration_seconds = max(10, dialogue_time + action_time)
        
        # Estimate shot count
        scene.shot_count_estimate = max(3, char_count * 2 + action_count)
    
    def _analyze_characters(self, analysis: ScriptAnalysis):
        """Analyze character profiles."""
        
        for scene in analysis.scenes:
            for char_name in scene.characters_present:
                if char_name in analysis.characters:
                    char = analysis.characters[char_name]
                    char.total_scenes += 1
                    char.scene_numbers.append(scene.scene_number)
                    
                    if char.first_appearance is None:
                        char.first_appearance = scene.scene_number
                    char.last_appearance = scene.scene_number
                    
                    # Count dialogue
                    char.total_dialogue_lines += len([
                        d for d in scene.dialogue_lines if d.character == char_name
                    ])
        
        # Calculate importance scores
        for char in analysis.characters.values():
            # Score based on scenes, dialogue, and span
            scene_score = char.total_scenes / max(analysis.total_scenes, 1)
            dialogue_score = char.total_dialogue_lines / max(analysis.total_dialogue_lines, 1)
            char.importance_score = (scene_score + dialogue_score) / 2
    
    def _calculate_statistics(self, analysis: ScriptAnalysis):
        """Calculate script statistics."""
        
        analysis.total_dialogue_lines = sum(
            len(scene.dialogue_lines) for scene in analysis.scenes
        )
        
        analysis.total_action_lines = sum(
            len(scene.action_lines) for scene in analysis.scenes
        )
        
        if analysis.scenes:
            total_duration = sum(s.estimated_duration_seconds for s in analysis.scenes)
            analysis.average_scene_length = total_duration / len(analysis.scenes)
            analysis.estimated_total_duration_seconds = total_duration
            analysis.estimated_shot_count = sum(s.shot_count_estimate for s in analysis.scenes)
    
    def _assess_complexity(self, analysis: ScriptAnalysis):
        """Assess overall script complexity."""
        
        # Count complexity distribution
        complexity_counts = {level: 0 for level in ComplexityLevel}
        for scene in analysis.scenes:
            complexity_counts[scene.complexity] += 1
        
        analysis.complexity_distribution = complexity_counts
        
        # Determine overall complexity
        if complexity_counts[ComplexityLevel.VERY_COMPLEX] > len(analysis.scenes) * 0.3:
            analysis.overall_complexity = ComplexityLevel.VERY_COMPLEX
        elif complexity_counts[ComplexityLevel.COMPLEX] > len(analysis.scenes) * 0.4:
            analysis.overall_complexity = ComplexityLevel.COMPLEX
        elif complexity_counts[ComplexityLevel.SIMPLE] > len(analysis.scenes) * 0.6:
            analysis.overall_complexity = ComplexityLevel.SIMPLE
        else:
            analysis.overall_complexity = ComplexityLevel.MODERATE
    
    def _identify_requirements(self, analysis: ScriptAnalysis):
        """Identify technical requirements."""
        
        # Collect unique locations
        locations = set()
        props = set()
        effects = set()
        
        for scene in analysis.scenes:
            locations.add(scene.location)
            props.update(scene.required_props)
            effects.update(scene.required_effects)
        
        analysis.unique_locations = list(locations)
        analysis.required_props = list(props)
        analysis.required_effects = list(effects)
    
    def _estimate_production(self, analysis: ScriptAnalysis):
        """Estimate production costs and timeline."""
        
        # Cost estimation (rough)
        base_cost_per_scene = 50  # USD
        complexity_multipliers = {
            ComplexityLevel.SIMPLE: 1.0,
            ComplexityLevel.MODERATE: 1.5,
            ComplexityLevel.COMPLEX: 2.5,
            ComplexityLevel.VERY_COMPLEX: 4.0
        }
        
        total_cost = 0
        for scene in analysis.scenes:
            multiplier = complexity_multipliers[scene.complexity]
            scene_cost = base_cost_per_scene * multiplier
            total_cost += scene_cost
        
        analysis.estimated_cost_usd = total_cost
        
        # Timeline estimation
        # Assume 5-10 scenes per day depending on complexity
        avg_scenes_per_day = 7
        analysis.estimated_production_days = max(1, len(analysis.scenes) // avg_scenes_per_day)
    
    def _calculate_feasibility(self, analysis: ScriptAnalysis):
        """Calculate feasibility score."""
        
        score = 100.0
        
        # Penalize for high complexity
        if analysis.overall_complexity == ComplexityLevel.VERY_COMPLEX:
            score -= 30
            analysis.technical_challenges.append("Very high overall complexity")
        elif analysis.overall_complexity == ComplexityLevel.COMPLEX:
            score -= 15
        
        # Penalize for too many characters
        if len(analysis.characters) > 10:
            score -= 20
            analysis.technical_challenges.append(f"Large cast ({len(analysis.characters)} characters)")
        
        # Penalize for too many locations
        if len(analysis.unique_locations) > 15:
            score -= 15
            analysis.technical_challenges.append(f"Many locations ({len(analysis.unique_locations)})")
        
        # Penalize for long duration
        if analysis.estimated_total_duration_seconds > 300:  # 5 minutes
            score -= 10
            analysis.technical_challenges.append("Long duration")
        
        analysis.feasibility_score = max(0, score)
    
    def _generate_recommendations(self, analysis: ScriptAnalysis):
        """Generate recommendations for improvement."""
        
        if analysis.feasibility_score < 50:
            analysis.recommendations.append("Consider simplifying the script")
        
        if len(analysis.characters) > 10:
            analysis.recommendations.append("Consider reducing the number of characters")
        
        if analysis.overall_complexity == ComplexityLevel.VERY_COMPLEX:
            analysis.recommendations.append("Break complex scenes into simpler shots")
        
        if len(analysis.unique_locations) > 15:
            analysis.recommendations.append("Consolidate scenes to fewer locations")
        
        if analysis.estimated_total_duration_seconds > 300:
            analysis.recommendations.append("Consider shortening the script for better pacing")


# ============================================================================
# Convenience Functions
# ============================================================================

def parse_and_analyze_script(
    script_text: str,
    format: ScriptFormat = ScriptFormat.PLAIN_TEXT
) -> ScriptAnalysis:
    """Parse and analyze a script in one step."""
    
    parser = ScriptParser()
    analyzer = ScriptAnalyzer()
    
    parsed = parser.parse(script_text, format)
    analyzed = analyzer.analyze(parsed)
    
    return analyzed


def get_script_summary(analysis: ScriptAnalysis) -> Dict[str, Any]:
    """Get a summary of script analysis."""
    
    return {
        "title": analysis.title,
        "format": analysis.format.value,
        "total_scenes": analysis.total_scenes,
        "total_characters": len(analysis.characters),
        "estimated_duration_minutes": analysis.estimated_total_duration_seconds / 60,
        "estimated_shot_count": analysis.estimated_shot_count,
        "overall_complexity": analysis.overall_complexity.value,
        "feasibility_score": analysis.feasibility_score,
        "estimated_cost_usd": analysis.estimated_cost_usd,
        "estimated_production_days": analysis.estimated_production_days,
        "technical_challenges": analysis.technical_challenges,
        "recommendations": analysis.recommendations
    }