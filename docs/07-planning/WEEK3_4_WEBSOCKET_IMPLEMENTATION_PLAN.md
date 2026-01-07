# Week 3-4: Frontend WebSocket Integration - Implementation Plan

**Duration**: 24 hours (estimated)  
**Status**: 📋 PLANNING  
**Dependencies**: Week 2 A2A Protocol (✅ Complete)

---

## Overview

Implement real-time WebSocket communication between frontend and backend to provide:
- Live progress updates during video generation
- Agent status monitoring
- Interactive workflow control
- Performance metrics dashboard

---

## Architecture Design

### Current State

```
Frontend (React)          Backend (FastAPI)
     │                          │
     │    HTTP REST API         │
     └─────────────────────────►│
           (polling)            │
                                │
                         A2A Coordinator
                         Agent Registry
```

**Issues**:
- No real-time updates
- Polling overhead
- Poor user experience during long operations
- No visibility into agent status

### Target State

```
Frontend (React)          Backend (FastAPI)
     │                          │
     │    HTTP REST API         │
     ├─────────────────────────►│
     │                          │
     │    WebSocket             │
     ├◄────────────────────────►│ WebSocket Manager
     │    (real-time)           │        │
     │                          │        ▼
     │                    Progress Broadcaster
     │                          │        │
     │                          │        ▼
     │                    A2A Coordinator
     │                    Agent Registry
     │                          │
     └──────────────────────────┘
```

**Benefits**:
- ✅ Real-time progress updates
- ✅ Live agent status
- ✅ Bidirectional communication
- ✅ Reduced server load
- ✅ Better user experience

---

## Implementation Phases

### Phase 1: Backend WebSocket Infrastructure (8h)

#### 1.1 Enhanced WebSocket Manager (3h)

**File**: `utils/websocket_manager.py` (enhance existing)

**Features**:
- Connection pooling with room support
- Message broadcasting to rooms
- Connection lifecycle management
- Heartbeat/ping-pong for connection health
- Automatic reconnection handling

**API**:
```python
class WebSocketManager:
    async def connect(self, websocket: WebSocket, client_id: str, room: str)
    async def disconnect(self, client_id: str)
    async def broadcast_to_room(self, room: str, message: dict)
    async def send_personal(self, client_id: str, message: dict)
    async def get_room_clients(self, room: str) -> List[str]
```

#### 1.2 Progress Broadcaster Service (3h)

**File**: `services/progress_broadcaster.py` (NEW)

**Purpose**: Bridge between A2A Coordinator and WebSocket clients

**Features**:
- Subscribe to A2A Coordinator events
- Transform A2A messages to WebSocket format
- Route messages to appropriate rooms
- Buffer messages for disconnected clients

**API**:
```python
class ProgressBroadcaster:
    async def subscribe_to_workflow(self, workflow_id: str, room: str)
    async def subscribe_to_agent(self, agent_name: str, room: str)
    async def broadcast_progress(self, workflow_id: str, progress: dict)
    async def broadcast_agent_status(self, agent_name: str, status: dict)
```

#### 1.3 WebSocket API Routes (2h)

**File**: `api_routes_websocket_enhanced.py` (NEW)

**Endpoints**:
```python
@router.websocket("/ws/workflow/{workflow_id}")
async def workflow_progress_stream(websocket: WebSocket, workflow_id: str)

@router.websocket("/ws/agent/{agent_name}")
async def agent_status_stream(websocket: WebSocket, agent_name: str)

@router.websocket("/ws/coordinator")
async def coordinator_metrics_stream(websocket: WebSocket)
```

**Message Types**:
```typescript
// Client → Server
{
  "type": "subscribe",
  "target": "workflow" | "agent" | "coordinator",
  "id": "workflow_id | agent_name"
}

{
  "type": "control",
  "action": "pause" | "resume" | "cancel",
  "workflow_id": "..."
}

// Server → Client
{
  "type": "progress",
  "workflow_id": "...",
  "progress": 0.5,
  "stage": "generating_images",
  "message": "Processing scene 3/5"
}

{
  "type": "agent_status",
  "agent_name": "screenwriter",
  "status": "busy" | "idle" | "error",
  "metrics": {...}
}

{
  "type": "error",
  "message": "...",
  "retryable": true
}
```

---

### Phase 2: Frontend WebSocket Client (8h)

#### 2.1 WebSocket Hook (3h)

**File**: `frontend/src/hooks/useWebSocket.ts` (NEW)

**Features**:
- Automatic connection management
- Reconnection with exponential backoff
- Message queue for offline mode
- Type-safe message handling
- React state integration

**API**:
```typescript
interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Error) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
}

function useWebSocket(options: UseWebSocketOptions) {
  return {
    isConnected: boolean;
    send: (message: any) => void;
    subscribe: (type: string, handler: Function) => void;
    unsubscribe: (type: string) => void;
  };
}
```

#### 2.2 Progress Components (3h)

**Files**:
- `frontend/src/components/ProgressBar.tsx` (NEW)
- `frontend/src/components/WorkflowProgress.tsx` (NEW)
- `frontend/src/components/AgentStatusCard.tsx` (NEW)

**Features**:
- Real-time progress visualization
- Stage-by-stage breakdown
- Estimated time remaining
- Error display with retry options
- Cancellation controls

#### 2.3 Agent Monitor Dashboard (2h)

**File**: `frontend/src/pages/AgentMonitor.tsx` (NEW)

**Features**:
- Live agent registry display
- Health status indicators
- Performance metrics (message count, error rate, avg time)
- Capability listing
- Manual agent control (future)

---

### Phase 3: Integration & Testing (8h)

#### 3.1 A2A Coordinator Integration (3h)

**Modify**: `services/a2a_agent_coordinator.py`

**Changes**:
- Add progress callback support
- Emit events on workflow state changes
- Emit events on agent status changes
- Integrate with ProgressBroadcaster

**Example**:
```python
class A2AAgentCoordinator:
    def __init__(self, progress_broadcaster: Optional[ProgressBroadcaster] = None):
        self.progress_broadcaster = progress_broadcaster
    
    async def execute_workflow(self, workflow: WorkflowDefinition):
        # Emit workflow started
        if self.progress_broadcaster:
            await self.progress_broadcaster.broadcast_progress(
                workflow.workflow_id,
                {"state": "started", "progress": 0.0}
            )
        
        # ... execute workflow ...
        
        # Emit progress updates
        for stage_idx, stage_tasks in enumerate(stages):
            if self.progress_broadcaster:
                await self.progress_broadcaster.broadcast_progress(
                    workflow.workflow_id,
                    {
                        "state": "running",
                        "progress": stage_idx / len(stages),
                        "stage": f"Stage {stage_idx + 1}/{len(stages)}",
                        "tasks": stage_tasks
                    }
                )
```

#### 3.2 Frontend Integration (2h)

**Modify**: Existing pages to use WebSocket

**Changes**:
- `frontend/src/pages/Idea2Video.tsx` - Add real-time progress
- `frontend/src/pages/Script2Video.tsx` - Add real-time progress
- `frontend/src/components/Layout.tsx` - Add agent status indicator

**Example**:
```typescript
function Idea2Video() {
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  
  const { isConnected, subscribe } = useWebSocket({
    url: `ws://localhost:3001/ws/workflow/${workflowId}`,
    onMessage: (msg) => {
      if (msg.type === 'progress') {
        setProgress(msg.progress);
      }
    }
  });
  
  return (
    <div>
      {isConnected && <WorkflowProgress progress={progress} />}
    </div>
  );
}
```

#### 3.3 Testing (3h)

**Test Files**:
- `tests/test_websocket_manager.py` (NEW)
- `tests/test_progress_broadcaster.py` (NEW)
- `frontend/src/hooks/__tests__/useWebSocket.test.ts` (NEW)

**Test Coverage**:
- WebSocket connection lifecycle
- Message broadcasting
- Reconnection logic
- Progress updates
- Error handling
- Room management

---

## Detailed Task Breakdown

### Week 3: Backend Implementation

#### Day 1-2: WebSocket Infrastructure (8h)

**Tasks**:
1. ✅ Enhance `utils/websocket_manager.py` with room support
2. ✅ Add connection pooling and lifecycle management
3. ✅ Implement heartbeat mechanism
4. ✅ Create `services/progress_broadcaster.py`
5. ✅ Integrate with A2A Coordinator
6. ✅ Write unit tests

**Deliverables**:
- Enhanced WebSocket Manager (200 lines)
- Progress Broadcaster Service (300 lines)
- Unit tests (150 lines)

#### Day 3: WebSocket API Routes (4h)

**Tasks**:
1. ✅ Create `api_routes_websocket_enhanced.py`
2. ✅ Implement workflow progress endpoint
3. ✅ Implement agent status endpoint
4. ✅ Implement coordinator metrics endpoint
5. ✅ Add authentication/authorization
6. ✅ Write integration tests

**Deliverables**:
- WebSocket API routes (250 lines)
- Integration tests (100 lines)

#### Day 4: A2A Integration (4h)

**Tasks**:
1. ✅ Modify A2A Coordinator to emit events
2. ✅ Add progress callback support
3. ✅ Connect to Progress Broadcaster
4. ✅ Test end-to-end flow
5. ✅ Performance testing

**Deliverables**:
- Modified A2A Coordinator (50 lines added)
- Integration tests (100 lines)

### Week 4: Frontend Implementation

#### Day 5-6: WebSocket Client (8h)

**Tasks**:
1. ✅ Create `useWebSocket` hook
2. ✅ Implement reconnection logic
3. ✅ Add message queue for offline mode
4. ✅ Create progress components
5. ✅ Create agent status components
6. ✅ Write component tests

**Deliverables**:
- useWebSocket hook (200 lines)
- Progress components (300 lines)
- Component tests (150 lines)

#### Day 7: Agent Monitor Dashboard (4h)

**Tasks**:
1. ✅ Create AgentMonitor page
2. ✅ Display live agent registry
3. ✅ Show performance metrics
4. ✅ Add health indicators
5. ✅ Style and polish

**Deliverables**:
- Agent Monitor page (250 lines)
- CSS styling (100 lines)

#### Day 8: Integration & Polish (4h)

**Tasks**:
1. ✅ Integrate WebSocket into existing pages
2. ✅ Add loading states
3. ✅ Add error handling
4. ✅ End-to-end testing
5. ✅ Documentation

**Deliverables**:
- Updated pages (100 lines modified)
- E2E tests (100 lines)
- Documentation (1 file)

---

## Technical Specifications

### WebSocket Message Protocol

#### Client → Server Messages

```typescript
// Subscribe to updates
{
  "type": "subscribe",
  "target": "workflow" | "agent" | "coordinator",
  "id": "target_id"
}

// Unsubscribe
{
  "type": "unsubscribe",
  "target": "workflow" | "agent" | "coordinator",
  "id": "target_id"
}

// Control workflow
{
  "type": "control",
  "action": "pause" | "resume" | "cancel",
  "workflow_id": "uuid"
}

// Heartbeat
{
  "type": "ping"
}
```

#### Server → Client Messages

```typescript
// Progress update
{
  "type": "progress",
  "workflow_id": "uuid",
  "state": "pending" | "running" | "completed" | "failed",
  "progress": 0.0-1.0,
  "stage": "stage_name",
  "message": "Human readable message",
  "timestamp": "ISO8601"
}

// Agent status
{
  "type": "agent_status",
  "agent_name": "string",
  "status": "idle" | "busy" | "error" | "offline",
  "metrics": {
    "message_count": 42,
    "error_count": 2,
    "error_rate": 0.048,
    "avg_execution_time": 1.23,
    "is_healthy": true
  },
  "timestamp": "ISO8601"
}

// Coordinator metrics
{
  "type": "coordinator_metrics",
  "total_messages": 1000,
  "total_workflows": 50,
  "registered_agents": 13,
  "healthy_agents": 12,
  "active_workflows": 3,
  "timestamp": "ISO8601"
}

// Error
{
  "type": "error",
  "message": "Error description",
  "error_type": "ErrorType",
  "retryable": true,
  "timestamp": "ISO8601"
}

// Heartbeat response
{
  "type": "pong"
}
```

### Connection Lifecycle

```
Client                          Server
  │                               │
  ├──── WebSocket Connect ───────►│
  │                               │
  │◄──── Connection Accepted ─────┤
  │                               │
  ├──── Subscribe Message ────────►│
  │                               │
  │◄──── Subscription Confirmed ──┤
  │                               │
  │◄──── Progress Updates ────────┤ (continuous)
  │                               │
  ├──── Ping ─────────────────────►│
  │◄──── Pong ─────────────────────┤
  │                               │
  ├──── Unsubscribe ──────────────►│
  │                               │
  ├──── WebSocket Close ──────────►│
  │                               │
```

### Error Handling

**Connection Errors**:
- Automatic reconnection with exponential backoff
- Max 5 retry attempts
- Backoff: 1s, 2s, 4s, 8s, 16s

**Message Errors**:
- Invalid message format → Send error response
- Unknown message type → Log and ignore
- Processing error → Send error with retry flag

**Subscription Errors**:
- Invalid target → Send error response
- Target not found → Send error response
- Permission denied → Send error response

---

## Performance Considerations

### Scalability

**Current Capacity**:
- 100 concurrent WebSocket connections per server
- 1000 messages/second throughput
- <10ms message latency

**Optimization Strategies**:
- Message batching for high-frequency updates
- Compression for large messages
- Connection pooling
- Load balancing across servers

### Resource Usage

**Memory**:
- ~1KB per WebSocket connection
- ~500 bytes per subscription
- ~100 bytes per queued message

**CPU**:
- Minimal overhead (<1% per 100 connections)
- Message serialization is main cost

**Network**:
- ~100 bytes per progress update
- ~500 bytes per agent status update
- Heartbeat every 30 seconds (~50 bytes)

---

## Security Considerations

### Authentication

- Reuse existing JWT tokens
- Validate token on WebSocket connection
- Refresh token mechanism for long-lived connections

### Authorization

- Room-based access control
- Users can only subscribe to their own workflows
- Admin users can subscribe to all agents

### Rate Limiting

- Max 10 subscriptions per client
- Max 100 messages/minute per client
- Automatic disconnection on abuse

---

## Testing Strategy

### Unit Tests

- WebSocket Manager connection lifecycle
- Progress Broadcaster message routing
- Message serialization/deserialization
- Reconnection logic

### Integration Tests

- End-to-end workflow progress updates
- Agent status broadcasting
- Multiple client subscriptions
- Error handling and recovery

### Load Tests

- 100 concurrent connections
- 1000 messages/second
- Connection stability over 1 hour
- Memory leak detection

### E2E Tests

- User starts video generation
- Progress updates appear in real-time
- User cancels workflow
- Agent monitor shows live status

---

## Success Criteria

### Functional Requirements

- ✅ Real-time progress updates during video generation
- ✅ Live agent status display
- ✅ Workflow control (pause, resume, cancel)
- ✅ Agent monitoring dashboard
- ✅ Automatic reconnection on disconnect

### Performance Requirements

- ✅ <100ms latency for progress updates
- ✅ Support 100+ concurrent connections
- ✅ <1% CPU overhead
- ✅ <10MB memory per 100 connections

### Quality Requirements

- ✅ 90%+ test coverage
- ✅ Zero memory leaks
- ✅ Graceful degradation on connection loss
- ✅ Clear error messages

---

## Risks & Mitigation

### Risk 1: WebSocket Connection Instability

**Impact**: High  
**Probability**: Medium  
**Mitigation**:
- Implement robust reconnection logic
- Add heartbeat mechanism
- Buffer messages during disconnection
- Fallback to HTTP polling if needed

### Risk 2: Message Flooding

**Impact**: Medium  
**Probability**: Low  
**Mitigation**:
- Implement rate limiting
- Add message batching
- Use compression for large messages
- Monitor and alert on high traffic

### Risk 3: Browser Compatibility

**Impact**: Low  
**Probability**: Low  
**Mitigation**:
- Use standard WebSocket API
- Test on major browsers
- Provide fallback for old browsers
- Clear browser requirements

---

## Dependencies

### Backend

- FastAPI WebSocket support (✅ available)
- A2A Coordinator (✅ complete)
- Existing WebSocket Manager (✅ available)

### Frontend

- React 18+ (✅ available)
- TypeScript (✅ available)
- WebSocket API (✅ browser native)

### Infrastructure

- No additional infrastructure needed
- Works with existing deployment

---

## Deliverables

### Code

1. Enhanced WebSocket Manager (200 lines)
2. Progress Broadcaster Service (300 lines)
3. WebSocket API Routes (250 lines)
4. useWebSocket Hook (200 lines)
5. Progress Components (300 lines)
6. Agent Monitor Dashboard (250 lines)

**Total**: ~1,500 lines of production code

### Tests

1. Unit tests (400 lines)
2. Integration tests (200 lines)
3. E2E tests (100 lines)

**Total**: ~700 lines of test code

### Documentation

1. WebSocket API documentation
2. Frontend integration guide
3. Deployment guide
4. Troubleshooting guide

---

## Timeline

**Week 3** (Days 1-4): Backend Implementation  
**Week 4** (Days 5-8): Frontend Implementation  
**Total**: 24 hours estimated

---

## Next Actions

1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1: Backend WebSocket Infrastructure
4. Daily progress updates

---

**Plan Created**: December 30, 2024  
**Author**: Kilo Code  
**Version**: 1.0  
**Status**: 📋 READY FOR REVIEW