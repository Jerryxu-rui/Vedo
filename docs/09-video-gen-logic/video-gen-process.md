Here’s a refined version of your text, improving clarity and flow while maintaining the technical depth:

---

Based on your insightful root cause analysis, it’s clear that the core issue lies in your LLM agents not being properly guided to generate expansive, creative content. Here’s how you can apply prompt engineering best practices to implement the fixes you’ve recommended:

## Fix 1: Refined Screenwriter Agent Prompt
Your screenwriter agent requires **clear, detailed instructions** to ensure it can generate a well-structured narrative. Instead of a generic prompt, use the following:

```
Role: Creative Screenwriter specializing in heartwarming short films
Task: Expand the user’s brief concept into a fully developed 3-act narrative with emotional depth
Requirements:
- Develop 5-8 distinct scenes with a solid story arc (beginning, middle, end)
- Include sensory details (e.g., golden hour lighting, the sound of waves, wet sand underfoot)
- Weave in character emotions and growth arcs
- Ensure natural conflict/resolution (e.g., a dog chasing waves, creating playful tension)
- End with an emotional payoff (e.g., a peaceful sunset moment)
Example structure:
Act 1: Setup - [A detailed arrival scene with character introduction]
Act 2: Development - [3-4 scenes of escalating action/joy]
Act 3: Resolution - [A fulfilling conclusion with character growth]
```

## Fix 2: Enhanced Character Extraction
Your character extraction prompt should guide the agent to generate **richer, more vivid responses** by adding context and examples:

```
Role: Character Development Specialist for visual storytelling
Task: Extract and enhance ALL characters from the scene, including animals as full-fledged characters
Requirements:
- Identify every entity (human and animal characters alike)
- Provide detailed visual characteristics: age, clothing, physical traits, breed (for animals)
- Incorporate personality traits that drive the narrative (e.g., playful, protective, energetic)
- Explore emotional motivations (e.g., why is the character at the beach? What are they seeking?)
- Define relationship dynamics between characters
Example output for 'woman with dog on beach':
Character 1: Sarah, 32, athletic build, wearing casual beach attire (linen shorts, tank top), joyful expression, hair slightly windswept
Character 2: Max, 3-year-old Golden Retriever, energetic and playful, wet fur from the ocean, wagging tail, loves chasing waves
```

## Fix 3: Scene Generation with Few-Shot Examples
Provide **few-shot examples** to illustrate the desired level of creativity and detail expected from the scene generator:

```
Role: Visual Storyboard Artist
Task: Create multiple distinct scenes that show progression and emotional beats
Requirements:
- A minimum of 5 scenes demonstrating clear narrative progression
- Each scene must detail: specific action, camera angle, emotional state, and environmental elements
- Ensure cause-and-effect between scenes (e.g., Scene 1 naturally leads into Scene 2)
- Include visual variety (wide shots, close-ups, medium shots)
- Specify lighting, weather, and time of day to set the atmosphere
Example scenes for the beach story:
Scene 1: WIDE SHOT - Golden hour, empty beach. Sarah unclipping Max’s leash, who immediately sprints towards the waves, tail wagging furiously. Sarah laughs, jogging after him. (Emotion: joyful anticipation)
Scene 2: MEDIUM SHOT - Max barking at the incoming wave, paws splashing. Sarah catches up, breathless but smiling. (Emotion: playful excitement)
[Continue with 3 more specific scenes...]
```

## Fix 4: Detailed Storyboarding with System Instructions
Enforce **rigorous output structures** and **system instructions** to ensure consistency and detail in the storyboarding process:

```
System Role: Professional Cinematographer
Output Format Requirements:
- Shot number and title (e.g., "Shot 1: Arrival at Beach")
- Camera specifications: angle, movement, lens type
- Specific character actions: detailed, visual actions (avoid vague descriptions)
- Environmental elements: time of day, weather, lighting conditions
- Emotional cues: character expressions, body language
- Sound design: ambient noises, character dialogue
- Transition notes to the next shot
Forbidden: Generic terms like "beginning," "protagonist," or "TBD" - every field must be filled with specific details
```

## Best Practices for Implementation
1. **Iterative refinement** is essential. Start with minimal inputs, test, and improve based on feedback.
2. Add **contextual information** to define the desired tone and audience (e.g., “heartwarming family-friendly story”).
3. Use **role-based prompts** consistently across agents to maintain narrative cohesion.
4. Implement **validation checks** to reject placeholder content, ensuring the system generates fully fleshed-out details.

Your technical infrastructure is solid, and by applying these prompt engineering improvements, you can transform your system from a placeholder generator into a powerful storytelling tool. The key lies in providing your LLM agents with **clear creative constraints** and **contextual examples**, guiding them toward the rich, detailed narratives your users expect.