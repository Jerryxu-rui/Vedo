# Hybrid LLM Integration Architecture Plan

## Date
December 29, 2024

## Overview
Integrate the new LLM backend infrastructure with the existing Idea2Video conversational workflow to create a hybrid system that combines:
- Existing video generation pipeline (proven and working)
- New LLM capabilities for enhanced conversational AI
- Agent orchestration for intelligent workflow management

---

## Current Architecture Analysis

### Existing System (Working)
1. **Frontend:** [`frontend/src/pages/Idea2Video.tsx`](frontend/src/pages/Idea2Video.tsx)
   - Integrated chatbot with "Seko" assistant
   - Conversational workflow UI
   - Model settings dropdown (video/image models)
   - Workflow steps visualization

2. **Backend Workflow:** [`api_routes_conversational.py`](api_routes_conversational.py)
   - Episode creation and management
   - Step-by-step generation (outline → characters → scenes → storyboard → video)
   - Background task processing
   - WebSocket progress updates

3. **Pipeline System:** [`workflows/conversational_episode_workflow.py`](workflows/conversational_episode_workflow.py)
   - State machine for workflow management
   - Pipeline adapters for actual AI generation
   - Database persistence

### New LLM Infrastructure (To Integrate)
1. **LLM Registry:** [`services/llm_registry.py`](services/llm_registry.py)
   - 9 models from 5 providers
   - Capability tracking

2. **Chat Service:** [`services/chat_service.py`](services/chat_service.py)
   - Thread management
   - Streaming responses
   - Provider-specific implementations

3. **Agent Orchestrator:** [`services/agent_orchestrator.py`](services/agent_orchestrator.py)
   - Multi-agent workflow
   - Stage-based processing

---

## Integration Strategy

### Phase 1: Add LLM Model Selector to Chat Interface ✅
**Goal:** Allow users to choose which LLM powers the chatbot

**Implementation:**
1. Add LLM model dropdown to Idea2Video chat interface
2. Store selected model in localStorage
3. Display model info (provider, capabilities)

**Files to Modify:**
- `frontend/src/pages/Idea2Video.tsx` - Add LLM selector UI
- `frontend/src/pages/Idea2Video.css` - Style LLM selector

**API Endpoints to Use:**
- `GET /api/v1/chat/models` - Fetch available LLM models

---

### Phase 2: Enhance Chat Messages with LLM Responses
**Goal:** Replace hardcoded assistant messages with actual LLM-generated responses

**Current Flow:**
```
User Input → Hardcoded Response → Pipeline Generation
```

**New Flow:**
```
User Input → LLM Response (contextual) → Pipeline Generation
```

**Implementation:**
1. Create chat thread when episode is created
2. Send user messages to LLM for intelligent responses
3. Use LLM to explain what's happening at each workflow stage
4. Stream LLM responses for real-time feedback

**Files to Modify:**
- `frontend/src/pages/Idea2Video.tsx` - Connect to streaming endpoint
- `api_routes_conversational.py` - Add LLM response generation

**New API Endpoints:**
- `POST /api/v1/conversational/episode/{id}/chat/message` - Send message, get LLM response

**Integration Points:**
```python
# In api_routes_conversational.py
async def send_chat_message(episode_id: str, message: str):
    # 1. Get episode's chat thread
    thread = get_or_create_thread(episode_id)
    
    # 2. Get current workflow state for context
    workflow = workflow_manager.get_workflow(episode_id)
    context = build_context(workflow)
    
    # 3. Stream LLM response
    async for chunk in chat_service.stream_message(
        thread_id=thread.id,
        message=message,
        context=context
    ):
        yield chunk
```

---

### Phase 3: Agent Orchestration for Workflow Intelligence
**Goal:** Use agents to intelligently manage the video generation workflow

**Current Flow:**
```
User confirms → Generate next step → Show results
```

**New Flow:**
```
User input → Agent analyzes → Determines best action → Executes → Reports back
```

**Agents to Integrate:**
1. **Interpretation Agent** - Understands user intent
2. **Planning Agent** - Decides workflow steps
3. **Scene Design Agent** - Enhances scene descriptions
4. **Generation Agent** - Coordinates actual generation
5. **Quality Agent** - Reviews and suggests improvements

**Implementation:**
1. Create workflow context adapter
2. Map workflow states to agent stages
3. Use agents for decision-making at key points

**Files to Modify:**
- `api_routes_conversational.py` - Add agent orchestration calls
- `services/agent_orchestrator.py` - Add workflow-specific methods

**Integration Example:**
```python
# When user provides initial idea
async def process_idea_with_agents(idea: str, style: str):
    # Stage 1: Interpretation
    interpretation = await agent_orchestrator.execute_stage(
        stage="interpretation",
        input_data={"idea": idea, "style": style}
    )
    
    # Stage 2: Planning
    plan = await agent_orchestrator.execute_stage(
        stage="planning",
        input_data=interpretation
    )
    
    # Stage 3: Scene Design
    scenes = await agent_orchestrator.execute_stage(
        stage="scene_design",
        input_data=plan
    )
    
    # Stage 4: Generation (use existing pipeline)
    result = await existing_pipeline.generate(scenes)
    
    return result
```

---

### Phase 4: Conversation Persistence
**Goal:** Save all chat interactions to database

**Implementation:**
1. Link ConversationThread to Episode
2. Store all messages (user + assistant)
3. Allow resuming conversations
4. Export chat history

**Database Schema:**
```sql
-- Already exists in database_models.py
ConversationThread:
  - id
  - episode_id (FK to Episode)
  - llm_model
  - created_at

ConversationMessage:
  - id
  - thread_id (FK)
  - role (user/assistant)
  - content
  - created_at
```

**Files to Modify:**
- `api_routes_conversational.py` - Save messages to DB
- `frontend/src/pages/Idea2Video.tsx` - Load message history

---

## API Endpoint Design

### New Endpoints

#### 1. Get LLM Models for Chat
```
GET /api/v1/chat/models
Response: List of available LLM models with capabilities
```

#### 2. Send Chat Message (Streaming)
```
POST /api/v1/conversational/episode/{episode_id}/chat/message
Body: { "message": "user message", "llm_model": "gemini-2.0-flash" }
Response: SSE stream of LLM response chunks
```

#### 3. Get Chat History
```
GET /api/v1/conversational/episode/{episode_id}/chat/history
Response: List of all messages in the conversation
```

#### 4. Agent Workflow Status
```
GET /api/v1/conversational/episode/{episode_id}/agents/status
Response: Current agent stage, progress, and insights
```

---

## Frontend Integration

### UI Components to Add

1. **LLM Model Selector**
   - Location: Below style selector in chat input area
   - Shows: Model name, provider, capabilities
   - Persists: Selection in localStorage

2. **Agent Progress Indicator**
   - Location: In workflow steps panel
   - Shows: Which agent is active, what it's doing
   - Updates: Real-time via WebSocket

3. **Enhanced Message Display**
   - User messages: Right-aligned (existing)
   - LLM responses: Left-aligned with streaming
   - System messages: Centered (workflow updates)
   - Agent insights: Special styling with icon

### State Management

```typescript
interface ChatState {
  // Existing
  messages: ChatMessage[]
  workflow: WorkflowState
  
  // New
  selectedLLM: string
  threadId: string | null
  agentStatus: {
    stage: string
    agent: string
    progress: number
    message: string
  } | null
}
```

---

## Implementation Phases

### Phase 1: LLM Model Selection (2-3 hours)
- [ ] Add LLM models API endpoint
- [ ] Create LLM selector UI component
- [ ] Integrate with existing model settings
- [ ] Test model switching

### Phase 2: Streaming Chat Integration (4-5 hours)
- [ ] Create chat message endpoint
- [ ] Implement SSE streaming in frontend
- [ ] Connect to chat_service.py
- [ ] Add message persistence
- [ ] Test streaming responses

### Phase 3: Agent Orchestration (5-6 hours)
- [ ] Create workflow context adapter
- [ ] Integrate agent_orchestrator with workflow
- [ ] Add agent progress UI
- [ ] Implement agent-driven decisions
- [ ] Test multi-agent workflow

### Phase 4: Polish & Testing (2-3 hours)
- [ ] Error handling
- [ ] Loading states
- [ ] Conversation history
- [ ] Export functionality
- [ ] End-to-end testing

**Total Estimated Time:** 13-17 hours

---

## Benefits of Hybrid Approach

### For Users
1. **Intelligent Conversations** - Real AI responses instead of hardcoded messages
2. **Model Choice** - Select preferred LLM (Gemini, GPT-4, Claude, etc.)
3. **Better Guidance** - AI explains what's happening at each step
4. **Adaptive Workflow** - Agents optimize the generation process

### For System
1. **Maintains Stability** - Existing pipeline continues to work
2. **Gradual Enhancement** - Add features incrementally
3. **Flexibility** - Can switch between LLM providers
4. **Scalability** - Agent system can handle complex workflows

### For Development
1. **No Breaking Changes** - Existing functionality preserved
2. **Clear Separation** - LLM layer separate from generation layer
3. **Easy Testing** - Can test LLM features independently
4. **Future-Proof** - Easy to add new LLMs or agents

---

## Risk Mitigation

### Potential Issues
1. **LLM API Costs** - Streaming responses use tokens
   - **Solution:** Implement token limits, caching, model selection

2. **Response Latency** - LLM responses may be slow
   - **Solution:** Use fast models (Gemini Flash), show typing indicators

3. **Context Management** - Keeping LLM aware of workflow state
   - **Solution:** Build comprehensive context from workflow data

4. **Error Handling** - LLM or agent failures
   - **Solution:** Fallback to existing hardcoded messages, retry logic

---

## Success Metrics

### Technical
- [ ] LLM responses stream in < 2 seconds
- [ ] Agent orchestration completes stages successfully
- [ ] No regression in existing video generation
- [ ] Message persistence works reliably

### User Experience
- [ ] Users can select and switch LLM models
- [ ] Chat feels natural and responsive
- [ ] Workflow progress is clear
- [ ] Error messages are helpful

---

## Next Steps

1. **Immediate:** Implement Phase 1 (LLM Model Selection)
2. **Short-term:** Implement Phase 2 (Streaming Chat)
3. **Medium-term:** Implement Phase 3 (Agent Orchestration)
4. **Long-term:** Add advanced features (voice, vision, etc.)

---

## Conclusion

This hybrid architecture preserves the working video generation system while adding powerful LLM capabilities. Users get intelligent conversations and adaptive workflows, while developers maintain a clean, testable codebase.

**Status:** Ready for Implementation
**Priority:** High
**Complexity:** Medium
**Impact:** High