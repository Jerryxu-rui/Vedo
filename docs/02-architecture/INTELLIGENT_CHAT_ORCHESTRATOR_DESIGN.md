# Intelligent Chat Orchestrator - Design Document

## Executive Summary

Design an intelligent chat model that understands user intent and dynamically routes requests to appropriate agents or workflows to complete video generation tasks. The system analyzes user input, determines goals, selects suitable agents/tools, and coordinates multi-step workflows to deliver video outputs efficiently.

---

## System Architecture

### 1. Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input Layer                          │
│  "Create a video about a magical forest with butterflies"   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Intent Analysis Engine (LLM)                    │
│  • Classify intent type (chat, video, modification, etc.)   │
│  • Extract key parameters (theme, style, characters, etc.)  │
│  • Determine complexity level (simple, medium, complex)     │
│  • Identify required agents/workflows                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestration Decision Layer                    │
│  • Route to appropriate workflow                            │
│  • Select agent combination                                 │
│  • Plan execution sequence                                  │
│  • Allocate resources                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Chat Agent   │ │ Video Agent  │ │ Multi-Agent  │
│              │ │              │ │ Workflow     │
│ • Q&A        │ │ • Idea2Video │ │ • Complex    │
│ • Guidance   │ │ • Script2Vid │ │   Tasks      │
│ • Feedback   │ │ • Modify     │ │ • Iterative  │
└──────────────┘ └──────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Execution Layer                           │
│  12 Specialized Agents:                                     │
│  • Screenwriter, Storyboard Artist, Character Extractor     │
│  • Scene Extractor, Image Generator, Video Generator        │
│  • Script Enhancer, Novel Compressor, etc.                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Output Delivery Layer                           │
│  • Video files, Images, Scripts, Feedback                   │
│  • Progress updates, Error handling, Quality checks         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Intent Analysis Engine

### 2.1 Intent Classification

**Primary Intent Types:**
1. **Chat Intent** - User wants information, guidance, or conversation
2. **Video Generation Intent** - User wants to create a video
3. **Modification Intent** - User wants to modify existing content
4. **Review Intent** - User wants to review/approve generated content
5. **Export Intent** - User wants to download/export results

**Classification Algorithm:**
```python
class IntentClassifier:
    def classify(self, user_input: str, context: dict) -> Intent:
        # Layer 1: Quick rule-based detection
        quick_intent = self.quick_rules(user_input)
        if quick_intent.confidence > 0.9:
            return quick_intent
        
        # Layer 2: LLM-based classification
        llm_intent = self.llm_classify(user_input, context)
        if llm_intent.confidence > 0.7:
            return llm_intent
        
        # Layer 3: Contextual analysis
        return self.contextual_classify(user_input, context, llm_intent)
    
    def extract_parameters(self, user_input: str, intent: Intent) -> dict:
        """Extract key parameters from user input"""
        return {
            'theme': self.extract_theme(user_input),
            'style': self.extract_style(user_input),
            'characters': self.extract_characters(user_input),
            'scenes': self.extract_scenes(user_input),
            'duration': self.extract_duration(user_input),
            'mood': self.extract_mood(user_input),
            'special_requirements': self.extract_requirements(user_input)
        }
```

### 2.2 Complexity Assessment

**Complexity Levels:**
- **Simple** (1-2 agents): Basic chat, single image generation
- **Medium** (3-5 agents): Standard video generation (Idea2Video)
- **Complex** (6+ agents): Multi-scene videos, character consistency, custom workflows

**Assessment Criteria:**
```python
def assess_complexity(parameters: dict) -> ComplexityLevel:
    score = 0
    
    # Factor 1: Number of scenes
    if parameters.get('scenes'):
        score += len(parameters['scenes']) * 2
    
    # Factor 2: Character count
    if parameters.get('characters'):
        score += len(parameters['characters']) * 3
    
    # Factor 3: Special requirements
    if parameters.get('special_requirements'):
        score += len(parameters['special_requirements']) * 5
    
    # Factor 4: Duration
    duration = parameters.get('duration', 0)
    if duration > 60:
        score += 10
    
    if score < 10:
        return ComplexityLevel.SIMPLE
    elif score < 30:
        return ComplexityLevel.MEDIUM
    else:
        return ComplexityLevel.COMPLEX
```

---

## 3. Orchestration Decision Layer

### 3.1 Workflow Selection

**Available Workflows:**

1. **Chat Workflow**
   - Single agent: Chat Service
   - Use case: Q&A, guidance, explanations
   - Execution time: < 5 seconds

2. **Idea2Video Workflow**
   - Agents: Screenwriter → Character Extractor → Scene Extractor → Storyboard Artist → Image Generator → Video Generator
   - Use case: Create video from text description
   - Execution time: 2-5 minutes

3. **Script2Video Workflow**
   - Agents: Script Enhancer → Storyboard Artist → Image Generator → Video Generator
   - Use case: Create video from existing script
   - Execution time: 1-3 minutes

4. **Iterative Refinement Workflow**
   - Agents: Dynamic based on user feedback
   - Use case: Modify existing content
   - Execution time: 30 seconds - 2 minutes

5. **Multi-Episode Workflow**
   - Agents: Novel Compressor → Multiple Idea2Video instances
   - Use case: Create series from long content
   - Execution time: 10-30 minutes

### 3.2 Agent Selection Logic

```python
class AgentOrchestrator:
    def select_agents(self, intent: Intent, parameters: dict, complexity: ComplexityLevel) -> List[Agent]:
        """Dynamically select agents based on requirements"""
        
        agents = []
        
        if intent.type == 'video_generation':
            # Core agents for video generation
            agents.append(ScreenwriterAgent())
            
            # Add character agent if characters mentioned
            if parameters.get('characters'):
                agents.append(CharacterExtractorAgent())
                agents.append(CharacterPortraitsGeneratorAgent())
            
            # Add scene agent if scenes mentioned
            if parameters.get('scenes'):
                agents.append(SceneExtractorAgent())
                agents.append(SceneImageGeneratorAgent())
            
            # Always add storyboard and video generation
            agents.append(StoryboardArtistAgent())
            agents.append(CameraImageGeneratorAgent())
            agents.append(VideoGeneratorAgent())
            
            # Add enhancement if quality requirements high
            if parameters.get('quality') == 'high':
                agents.append(ScriptEnhancerAgent())
        
        return agents
    
    def plan_execution(self, agents: List[Agent]) -> ExecutionPlan:
        """Create execution plan with dependencies"""
        
        plan = ExecutionPlan()
        
        # Build dependency graph
        for agent in agents:
            dependencies = agent.get_dependencies()
            plan.add_step(agent, dependencies)
        
        # Optimize execution order
        plan.optimize()
        
        return plan
```

---

## 4. Intelligent Routing Examples

### Example 1: Simple Chat
**User Input:** "What can you do?"

**Processing:**
```
Intent: chat
Confidence: 0.95
Parameters: {}
Complexity: simple
Route: Chat Agent
Response: "I can help you create videos..."
```

### Example 2: Basic Video Generation
**User Input:** "Create a video about a magical forest"

**Processing:**
```
Intent: video_generation
Confidence: 0.88
Parameters: {
  theme: "magical forest",
  style: "cinematic",
  mood: "mystical"
}
Complexity: medium
Route: Idea2Video Workflow
Agents: [Screenwriter, SceneExtractor, StoryboardArtist, ImageGenerator, VideoGenerator]
```

### Example 3: Complex Multi-Character Video
**User Input:** "Create a 2-minute video about three friends exploring an ancient temple, with dramatic lighting and suspenseful music"

**Processing:**
```
Intent: video_generation
Confidence: 0.92
Parameters: {
  theme: "ancient temple exploration",
  characters: ["friend 1", "friend 2", "friend 3"],
  duration: 120,
  style: "cinematic",
  mood: "suspenseful",
  lighting: "dramatic",
  music: "suspenseful"
}
Complexity: complex
Route: Enhanced Idea2Video Workflow
Agents: [
  Screenwriter,
  CharacterExtractor,
  CharacterPortraitsGenerator,
  PersonalityExtractor,
  SceneExtractor,
  SceneImageGenerator,
  StoryboardArtist,
  CameraImageGenerator,
  VideoGenerator
]
Execution Plan:
  1. Screenwriter generates script
  2. CharacterExtractor identifies 3 characters
  3. PersonalityExtractor defines personalities
  4. CharacterPortraitsGenerator creates character images
  5. SceneExtractor identifies temple scenes
  6. SceneImageGenerator creates scene backgrounds
  7. StoryboardArtist creates shot sequence
  8. CameraImageGenerator generates frames
  9. VideoGenerator compiles final video
```

### Example 4: Modification Request
**User Input:** "Make the forest darker and add fog"

**Processing:**
```
Intent: modification
Confidence: 0.85
Parameters: {
  modifications: ["darker lighting", "add fog"],
  target: "current_video"
}
Complexity: simple
Route: Iterative Refinement Workflow
Agents: [SceneImageGenerator, VideoGenerator]
Context: Uses existing storyboard, only regenerates affected frames
```

---

## 5. Implementation Plan

### Phase 1: Enhanced Intent Analysis (Week 1-2)
**Files to modify:**
- `services/chat_service.py` - Add parameter extraction
- `api_routes_chat.py` - Add complexity assessment endpoint
- `frontend/src/pages/Idea2Video.tsx` - Enhanced intent detection

**New files:**
- `services/intent_analyzer.py` - Comprehensive intent analysis
- `services/parameter_extractor.py` - Extract video parameters from text

### Phase 2: Orchestration Engine (Week 3-4)
**Files to create:**
- `services/orchestrator.py` - Main orchestration logic
- `services/agent_selector.py` - Dynamic agent selection
- `services/execution_planner.py` - Execution plan optimization
- `workflows/dynamic_workflow.py` - Dynamic workflow execution

### Phase 3: Agent Integration (Week 5-6)
**Files to modify:**
- All agent files in `agents/` - Add dependency declarations
- `services/agent_orchestrator.py` - Enhanced coordination
- `workflows/conversational_episode_workflow.py` - Dynamic routing

### Phase 4: Context Management (Week 7-8)
**Files to create:**
- `services/context_manager.py` - Conversation context tracking
- `services/state_manager.py` - Workflow state management
- `database_models.py` - Add context storage models

### Phase 5: Testing & Optimization (Week 9-10)
- End-to-end workflow testing
- Performance optimization
- Error handling enhancement
- User experience refinement

---

## 6. Key Features

### 6.1 Intelligent Understanding
- **Natural Language Processing**: Understand complex, multi-part requests
- **Context Awareness**: Remember previous interactions and build on them
- **Ambiguity Resolution**: Ask clarifying questions when needed
- **Parameter Inference**: Infer missing parameters from context

### 6.2 Dynamic Routing
- **Real-time Decision Making**: Choose optimal workflow based on current state
- **Adaptive Execution**: Adjust plan based on intermediate results
- **Fallback Mechanisms**: Handle failures gracefully with alternative approaches
- **Resource Optimization**: Balance quality vs. speed based on requirements

### 6.3 Seamless Coordination
- **Agent Communication**: Agents share information efficiently
- **Dependency Management**: Automatic handling of agent dependencies
- **Parallel Execution**: Run independent agents concurrently
- **Progress Tracking**: Real-time updates on workflow progress

### 6.4 Quality Assurance
- **Output Validation**: Check quality at each step
- **Error Recovery**: Automatic retry with adjustments
- **User Feedback Loop**: Incorporate user feedback for improvements
- **Consistency Checks**: Ensure character/scene consistency across frames

---

## 7. API Design

### 7.1 Intelligent Chat Endpoint

```python
@router.post("/api/v1/intelligent-chat")
async def intelligent_chat(request: IntelligentChatRequest):
    """
    Main endpoint for intelligent chat orchestration
    
    Request:
    {
        "message": "Create a video about...",
        "context": {
            "conversation_id": "uuid",
            "previous_outputs": [...],
            "user_preferences": {...}
        }
    }
    
    Response:
    {
        "intent": {
            "type": "video_generation",
            "confidence": 0.92,
            "parameters": {...}
        },
        "execution_plan": {
            "workflow": "idea2video",
            "agents": [...],
            "estimated_time": 180
        },
        "response": "I'll create that video for you...",
        "actions": [
            {"type": "start_workflow", "workflow_id": "uuid"}
        ]
    }
    """
    # 1. Analyze intent
    intent = await intent_analyzer.analyze(request.message, request.context)
    
    # 2. Select workflow and agents
    plan = await orchestrator.create_plan(intent)
    
    # 3. Generate response
    response = await chat_service.generate_response(intent, plan)
    
    # 4. Execute if appropriate
    if intent.requires_execution:
        workflow_id = await orchestrator.execute(plan)
        return {
            "intent": intent,
            "execution_plan": plan,
            "response": response,
            "workflow_id": workflow_id
        }
    
    return {
        "intent": intent,
        "response": response
    }
```

### 7.2 Workflow Status Endpoint

```python
@router.get("/api/v1/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """
    Get real-time workflow status
    
    Response:
    {
        "workflow_id": "uuid",
        "status": "executing",
        "current_step": "generating_storyboard",
        "progress": 0.45,
        "completed_agents": ["screenwriter", "character_extractor"],
        "active_agents": ["storyboard_artist"],
        "pending_agents": ["image_generator", "video_generator"],
        "estimated_completion": "2024-12-29T12:15:00Z",
        "outputs": {
            "script": {...},
            "characters": [...]
        }
    }
    """
    return await orchestrator.get_status(workflow_id)
```

---

## 8. Success Metrics

### 8.1 Performance Metrics
- **Intent Classification Accuracy**: > 95%
- **Parameter Extraction Accuracy**: > 90%
- **Workflow Selection Accuracy**: > 92%
- **Average Response Time**: < 3 seconds for routing decision
- **Video Generation Success Rate**: > 85%

### 8.2 User Experience Metrics
- **User Satisfaction**: > 4.5/5
- **Task Completion Rate**: > 80%
- **Retry Rate**: < 15%
- **Average Iterations to Satisfaction**: < 2

---

## 9. Example Conversations

### Conversation 1: Progressive Refinement
```
User: "I want to create a video"
System: "I'd be happy to help! What would you like the video to be about?"

User: "A story about a robot learning to paint"
System: "Great idea! I'll create a video about a robot learning to paint. 
        Would you like it to be:
        1. Short and simple (30 seconds)
        2. Standard length (1-2 minutes)
        3. Detailed story (3-5 minutes)"

User: "Standard length"
System: "Perfect! I'm creating a 1-2 minute video about a robot learning to paint.
        [Starting Idea2Video workflow...]
        [Progress: Generating script... 20%]
        [Progress: Creating characters... 40%]
        [Progress: Designing scenes... 60%]
        [Progress: Generating storyboard... 80%]
        [Progress: Creating video... 100%]
        Your video is ready! [Preview]"
```

### Conversation 2: Complex Multi-Step
```
User: "Create a 3-part series about space exploration"
System: "Excellent! I'll create a 3-part space exploration series. 
        Let me break this down:
        
        Episode 1: Launch and Journey
        Episode 2: Discovery
        Episode 3: Return Home
        
        Each episode will be about 2 minutes. Should I proceed?"

User: "Yes, but make episode 2 longer and more dramatic"
System: "Got it! I'll make Episode 2 about 3 minutes with dramatic elements.
        [Starting Multi-Episode workflow...]
        [Episode 1: Generating... 33%]
        [Episode 2: Generating... 66%]
        [Episode 3: Generating... 100%]
        All 3 episodes are ready!"
```

---

## 10. Next Steps

### Immediate (This Week)
1. ✅ Fix chat response display bug
2. ✅ Implement basic intent detection
3. [ ] Create `IntentAnalyzer` service
4. [ ] Add parameter extraction logic

### Short Term (Next 2 Weeks)
1. [ ] Implement `Orchestrator` service
2. [ ] Create dynamic workflow execution
3. [ ] Add agent dependency management
4. [ ] Implement context tracking

### Medium Term (Next Month)
1. [ ] Full multi-agent coordination
2. [ ] Advanced error recovery
3. [ ] Performance optimization
4. [ ] Comprehensive testing

### Long Term (Next Quarter)
1. [ ] Machine learning for intent prediction
2. [ ] Personalized workflow optimization
3. [ ] Advanced quality assurance
4. [ ] Multi-language support

---

## Conclusion

This intelligent chat orchestrator will transform the ViMax system into a truly intelligent video generation platform that understands user intent, dynamically selects the best approach, and seamlessly coordinates multiple agents to deliver high-quality video outputs efficiently.

The system is designed to be:
- **Intelligent**: Understands complex, natural language requests
- **Adaptive**: Adjusts approach based on requirements and context
- **Efficient**: Optimizes resource usage and execution time
- **Reliable**: Handles errors gracefully with fallback mechanisms
- **Scalable**: Easily extensible with new agents and workflows

**Current Status**: Foundation complete, ready for Phase 1 implementation.