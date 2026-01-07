# Next Steps Implementation Plan

**Based on**: [Architectural Analysis Report](../02-architecture/ARCHITECTURAL_ANALYSIS_REPORT.md)  
**Date**: 2025-12-30  
**Priority**: HIGH - Critical Path Implementation

---

## Executive Decision: Priority 1 Implementation

Based on the architectural analysis, we need to implement the **missing orchestration layer** which is the core architectural gap (0% implemented). This is blocking the system from becoming truly intelligent and conversational.

---

## Phase 1: Critical Path (Next 4 Weeks)

### Week 1: Conversational Orchestrator Foundation

#### Task 1.1: Create Intent Analyzer Service (16 hours)

**Goal**: Build comprehensive intent understanding system

**Implementation**:

```python
# File: services/intent_analyzer.py

from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from enum import Enum

class IntentType(str, Enum):
    CHAT = "chat"
    VIDEO_GENERATION = "video_generation"
    MODIFICATION = "modification"
    REVIEW = "review"
    EXPORT = "export"

class ComplexityLevel(str, Enum):
    SIMPLE = "simple"      # 1-2 agents
    MEDIUM = "medium"      # 3-5 agents
    COMPLEX = "complex"    # 6+ agents

class Intent(BaseModel):
    type: IntentType
    confidence: float
    parameters: Dict[str, Any]
    complexity: ComplexityLevel
    required_agents: List[str]

class IntentAnalyzer:
    """Analyzes user input to determine intent and extract parameters"""
    
    async def analyze(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Intent:
        """
        Analyze user input and return structured intent
        
        Steps:
        1. Quick rule-based detection (>0.9 confidence)
        2. LLM-based classification (>0.7 confidence)
        3. Contextual analysis (fallback)
        """
        pass
    
    async def extract_parameters(
        self,
        user_input: str,
        intent_type: IntentType
    ) -> Dict[str, Any]:
        """
        Extract video generation parameters:
        - theme: str
        - style: str
        - characters: List[str]
        - scenes: List[str]
        - duration: int
        - mood: str
        - special_requirements: List[str]
        """
        pass
    
    def assess_complexity(
        self,
        parameters: Dict[str, Any]
    ) -> ComplexityLevel:
        """
        Assess complexity based on:
        - Number of scenes
        - Number of characters
        - Special requirements
        - Duration
        """
        pass
```

**Files to Create**:
- `services/intent_analyzer.py` (300 lines)
- `tests/test_intent_analyzer.py` (150 lines)

**Deliverables**:
- ✅ Intent classification with 95%+ accuracy
- ✅ Parameter extraction from natural language
- ✅ Complexity assessment algorithm

**Testing**:
```python
# Test cases
test_cases = [
    {
        "input": "Create a 2-minute video about space exploration",
        "expected_intent": "video_generation",
        "expected_params": {
            "theme": "space exploration",
            "duration": 120,
            "complexity": "medium"
        }
    },
    {
        "input": "What can you do?",
        "expected_intent": "chat",
        "expected_complexity": "simple"
    }
]
```

#### Task 1.2: Create Parameter Extractor (16 hours)

**Goal**: Extract structured parameters from natural language

**Implementation**:

```python
# File: services/parameter_extractor.py

class ParameterExtractor:
    """Extracts video generation parameters from natural language"""
    
    async def extract_theme(self, text: str) -> str:
        """Extract main theme/topic"""
        pass
    
    async def extract_style(self, text: str) -> str:
        """Extract visual style (cinematic, anime, realistic, etc.)"""
        pass
    
    async def extract_characters(self, text: str) -> List[Dict[str, str]]:
        """Extract character descriptions"""
        pass
    
    async def extract_scenes(self, text: str) -> List[Dict[str, str]]:
        """Extract scene descriptions"""
        pass
    
    async def extract_duration(self, text: str) -> Optional[int]:
        """Extract video duration in seconds"""
        pass
    
    async def extract_mood(self, text: str) -> str:
        """Extract mood/atmosphere"""
        pass
```

**Files to Create**:
- `services/parameter_extractor.py` (250 lines)
- `tests/test_parameter_extractor.py` (100 lines)

#### Task 1.3: Create Conversational Orchestrator (32 hours)

**Goal**: Central orchestrator that coordinates all components

**Implementation**:

```python
# File: services/conversational_orchestrator.py

from services.intent_analyzer import IntentAnalyzer, Intent
from services.parameter_extractor import ParameterExtractor
from services.agent_coordinator import AgentCoordinator
from workflows.conversational_episode_workflow import WorkflowManager

class ConversationalOrchestrator:
    """
    Central orchestrator for conversational video generation
    
    Responsibilities:
    1. Understand user intent
    2. Extract parameters
    3. Select appropriate workflow
    4. Coordinate agents
    5. Manage conversation context
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.intent_analyzer = IntentAnalyzer(db)
        self.parameter_extractor = ParameterExtractor(db)
        self.agent_coordinator = AgentCoordinator(db)
        self.workflow_manager = WorkflowManager()
        self.context_manager = ConversationContextManager()
    
    async def process_message(
        self,
        user_message: str,
        conversation_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user messages
        
        Flow:
        1. Analyze intent
        2. Extract parameters
        3. Select workflow
        4. Execute workflow
        5. Return response
        """
        
        # 1. Analyze intent
        intent = await self.intent_analyzer.analyze(
            user_message,
            context
        )
        
        # 2. Route based on intent
        if intent.type == IntentType.CHAT:
            return await self._handle_chat(user_message, context)
        
        elif intent.type == IntentType.VIDEO_GENERATION:
            return await self._handle_video_generation(
                intent,
                user_message,
                context
            )
        
        elif intent.type == IntentType.MODIFICATION:
            return await self._handle_modification(
                intent,
                user_message,
                context
            )
        
        else:
            return await self._handle_unknown(user_message, context)
    
    async def _handle_video_generation(
        self,
        intent: Intent,
        user_message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle video generation requests"""
        
        # Select workflow based on complexity
        workflow = self._select_workflow(intent)
        
        # Select agents based on requirements
        agents = await self.agent_coordinator.select_agents(
            intent.parameters,
            intent.complexity
        )
        
        # Create execution plan
        plan = await self.agent_coordinator.create_execution_plan(
            agents,
            intent.parameters
        )
        
        # Execute workflow
        result = await workflow.execute(plan)
        
        return result
    
    def _select_workflow(self, intent: Intent) -> Workflow:
        """Select appropriate workflow based on intent"""
        
        if intent.complexity == ComplexityLevel.SIMPLE:
            return SimpleVideoWorkflow()
        elif intent.complexity == ComplexityLevel.MEDIUM:
            return StandardVideoWorkflow()
        else:
            return ComplexVideoWorkflow()
```

**Files to Create**:
- `services/conversational_orchestrator.py` (500 lines)
- `services/conversation_context_manager.py` (300 lines)
- `tests/test_conversational_orchestrator.py` (200 lines)

**Deliverables**:
- ✅ Working orchestrator
- ✅ Intent-based routing
- ✅ Context management
- ✅ Workflow selection logic

---

### Week 2: Agent Coordinator Refactor (32 hours)

#### Task 2.1: Rewrite Agent Coordinator

**Goal**: Enable dynamic agent selection and coordination

**Current File**: [`services/agent_orchestrator.py`](../../services/agent_orchestrator.py) (361 lines, incomplete)

**New Implementation**:

```python
# File: services/agent_coordinator.py (replaces agent_orchestrator.py)

from typing import List, Dict, Any
from agents.base_agent import BaseAgent

class AgentCoordinator:
    """Coordinates multiple agents for video generation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.agents = self._initialize_agents()
    
    def _initialize_agents(self) -> Dict[str, BaseAgent]:
        """Initialize all available agents"""
        return {
            "screenwriter": ScreenwriterAgent(),
            "character_extractor": CharacterExtractorAgent(),
            "character_portraits": CharacterPortraitsGeneratorAgent(),
            "scene_extractor": SceneExtractorAgent(),
            "scene_image": SceneImageGeneratorAgent(),
            "storyboard": StoryboardArtistAgent(),
            "camera_image": CameraImageGeneratorAgent(),
            # ... all 13 agents
        }
    
    async def select_agents(
        self,
        parameters: Dict[str, Any],
        complexity: ComplexityLevel
    ) -> List[BaseAgent]:
        """
        Dynamically select agents based on requirements
        
        Logic:
        - Always: Screenwriter, Storyboard, Video Generator
        - If characters mentioned: Character agents
        - If scenes mentioned: Scene agents
        - If high quality: Enhancement agents
        """
        
        selected = []
        
        # Core agents (always needed)
        selected.append(self.agents["screenwriter"])
        selected.append(self.agents["storyboard"])
        
        # Conditional agents
        if parameters.get("characters"):
            selected.append(self.agents["character_extractor"])
            selected.append(self.agents["character_portraits"])
        
        if parameters.get("scenes"):
            selected.append(self.agents["scene_extractor"])
            selected.append(self.agents["scene_image"])
        
        if complexity == ComplexityLevel.COMPLEX:
            selected.append(self.agents["script_enhancer"])
        
        return selected
    
    async def create_execution_plan(
        self,
        agents: List[BaseAgent],
        parameters: Dict[str, Any]
    ) -> ExecutionPlan:
        """
        Create execution plan with dependencies
        
        Returns:
            ExecutionPlan with:
            - Task sequence
            - Dependencies
            - Parallel execution groups
        """
        
        plan = ExecutionPlan()
        
        # Build dependency graph
        for agent in agents:
            dependencies = agent.get_dependencies()
            plan.add_task(agent, dependencies)
        
        # Optimize for parallel execution
        plan.optimize()
        
        return plan
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute the plan with progress tracking"""
        
        results = {}
        
        for stage in plan.stages:
            # Execute tasks in parallel within stage
            stage_results = await asyncio.gather(*[
                self._execute_agent_task(task, results)
                for task in stage.tasks
            ])
            
            results.update(stage_results)
            
            if progress_callback:
                await progress_callback(stage.progress)
        
        return results
```

**Files to Create/Modify**:
- `services/agent_coordinator.py` (600 lines, replaces agent_orchestrator.py)
- `services/execution_plan.py` (200 lines, new)
- `agents/base_agent.py` (150 lines, new)
- `tests/test_agent_coordinator.py` (250 lines)

**Deliverables**:
- ✅ Dynamic agent selection
- ✅ Dependency management
- ✅ Parallel execution support
- ✅ Progress tracking

#### Task 2.2: Create Base Agent Interface

**Goal**: Standardize agent communication

```python
# File: agents/base_agent.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseAgent(ABC):
    """Base class for all agents"""
    
    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agent task"""
        pass
    
    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Return list of agent names this agent depends on"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        pass
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        return True
    
    def format_output(self, result: Any) -> Dict[str, Any]:
        """Format output in standard format"""
        return {
            "agent": self.__class__.__name__,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

### Week 3-4: Frontend WebSocket Integration (24 hours)

#### Task 3.1: Create WebSocket Hooks

**Files to Create**:

```typescript
// File: frontend/src/hooks/useWebSocket.ts

import { useEffect, useState, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  data: any;
}

export function useWebSocket(url: string) {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const websocket = new WebSocket(url);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages(prev => [...prev, message]);
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [url]);

  const sendMessage = useCallback((message: any) => {
    if (ws && isConnected) {
      ws.send(JSON.stringify(message));
    }
  }, [ws, isConnected]);

  return { messages, sendMessage, isConnected };
}
```

```typescript
// File: frontend/src/hooks/useProgress.ts

import { useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

interface ProgressUpdate {
  stage: string;
  progress: number;
  message: string;
  data?: any;
}

export function useProgress(episodeId: string) {
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const { messages } = useWebSocket(
    `ws://localhost:3001/api/v1/ws/progress/${episodeId}`
  );

  useEffect(() => {
    const latestMessage = messages[messages.length - 1];
    if (latestMessage && latestMessage.type === 'progress') {
      setProgress(latestMessage.data);
    }
  }, [messages]);

  return progress;
}
```

#### Task 3.2: Update Idea2Video Component

**File to Modify**: [`frontend/src/pages/Idea2Video.tsx`](../../frontend/src/pages/Idea2Video.tsx)

**Changes**:
1. Replace polling with WebSocket
2. Add real-time progress visualization
3. Show agent activity indicators

```typescript
// Add to Idea2Video.tsx

import { useProgress } from '../hooks/useProgress';

function Idea2Video() {
  const progress = useProgress(episodeId);

  return (
    <div>
      {progress && (
        <ProgressBar
          stage={progress.stage}
          progress={progress.progress}
          message={progress.message}
        />
      )}
      {/* ... rest of component */}
    </div>
  );
}
```

**Files to Create/Modify**:
- `frontend/src/hooks/useWebSocket.ts` (100 lines)
- `frontend/src/hooks/useProgress.ts` (80 lines)
- `frontend/src/components/ProgressBar.tsx` (150 lines)
- `frontend/src/pages/Idea2Video.tsx` (modify, add WebSocket)

**Deliverables**:
- ✅ Real-time progress updates
- ✅ WebSocket connection management
- ✅ Progress visualization
- ✅ Agent activity indicators

---

## Implementation Checklist

### Week 1: Orchestrator Foundation
- [ ] Create `services/intent_analyzer.py`
- [ ] Create `services/parameter_extractor.py`
- [ ] Create `services/conversational_orchestrator.py`
- [ ] Create `services/conversation_context_manager.py`
- [ ] Write tests for all new services
- [ ] Integration test: Intent analysis → Parameter extraction

### Week 2: Agent Coordination
- [ ] Create `agents/base_agent.py`
- [ ] Create `services/agent_coordinator.py`
- [ ] Create `services/execution_plan.py`
- [ ] Refactor existing agents to use BaseAgent
- [ ] Write tests for agent coordination
- [ ] Integration test: Agent selection → Execution

### Week 3-4: Frontend Integration
- [ ] Create `frontend/src/hooks/useWebSocket.ts`
- [ ] Create `frontend/src/hooks/useProgress.ts`
- [ ] Create `frontend/src/components/ProgressBar.tsx`
- [ ] Update `Idea2Video.tsx` to use WebSocket
- [ ] Test WebSocket connection
- [ ] Test real-time progress updates

### Integration Testing
- [ ] End-to-end test: User message → Video generation
- [ ] Test all intent types
- [ ] Test parameter extraction accuracy
- [ ] Test agent coordination
- [ ] Test WebSocket reliability
- [ ] Performance testing

---

## Success Criteria

### Week 1 Success Metrics
- ✅ Intent classification accuracy > 95%
- ✅ Parameter extraction accuracy > 90%
- ✅ Orchestrator routes requests correctly
- ✅ All tests passing

### Week 2 Success Metrics
- ✅ Dynamic agent selection working
- ✅ Agents execute in correct order
- ✅ Parallel execution functional
- ✅ All tests passing

### Week 3-4 Success Metrics
- ✅ WebSocket connection stable
- ✅ Real-time progress updates working
- ✅ UI responsive and smooth
- ✅ No polling, only WebSocket

### Overall Phase 1 Success
- ✅ User can create video through natural conversation
- ✅ System understands complex requests
- ✅ Agents coordinate automatically
- ✅ Real-time feedback to user
- ✅ 80%+ test coverage for new code

---

## Risk Mitigation

### Risk 1: LLM API Costs
**Mitigation**:
- Implement caching for similar requests
- Use cheaper models for simple tasks
- Add token limits

### Risk 2: WebSocket Reliability
**Mitigation**:
- Implement reconnection logic
- Fallback to polling if WebSocket fails
- Add connection status indicator

### Risk 3: Agent Coordination Complexity
**Mitigation**:
- Start with simple sequential execution
- Add parallel execution incrementally
- Extensive testing at each step

### Risk 4: Integration Issues
**Mitigation**:
- Incremental integration
- Comprehensive integration tests
- Rollback plan for each component

---

## Next Steps After Phase 1

Once Phase 1 is complete (4 weeks), proceed to:

1. **Phase 2: Enhancement** (4 weeks)
   - Implement missing agents (Style Determiner, Post-Processor)
   - Add Iterative Refinement workflow
   - Consolidate redundant APIs

2. **Phase 3: Polish** (2 weeks)
   - Comprehensive testing
   - Performance optimization
   - Documentation

---

## Immediate Action Items (This Week)

### Day 1-2: Setup
1. Create new branch: `feature/orchestration-layer`
2. Set up development environment
3. Review architectural analysis report
4. Create detailed task breakdown

### Day 3-5: Intent Analyzer
1. Implement `IntentAnalyzer` class
2. Write unit tests
3. Test with sample inputs
4. Integrate with existing chat API

### Day 6-7: Parameter Extractor
1. Implement `ParameterExtractor` class
2. Write unit tests
3. Test extraction accuracy
4. Document parameter format

---

## Conclusion

This plan implements the **critical missing orchestration layer** identified in the architectural analysis. By following this 4-week plan, we will:

1. ✅ Close the 0% → 95% orchestration gap
2. ✅ Enable intelligent, conversational video generation
3. ✅ Improve agent coordination from 30% → 90%
4. ✅ Add real-time user feedback via WebSocket
5. ✅ Increase overall design coverage from 52% → 75%

**Start Date**: 2025-12-30  
**Target Completion**: 2026-01-27  
**Total Effort**: 120 hours over 4 weeks

Let's begin with Week 1, Task 1.1: Intent Analyzer implementation.