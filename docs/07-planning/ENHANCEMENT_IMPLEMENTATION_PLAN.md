# ViMax Video Generation System Enhancement Plan

## Overview
Comprehensive enhancement to add model selection, improved dialogue processing, step-by-step editing, and multi-API key management.

## Current System Architecture

### Models in Use:
- **Chat Models**: gemini-2.0-flash-001, gemini-2.5-flash-nothinking
- **Image Generators**: 
  - doubao-seedream-4-0-250828 (Idea2Video)
  - nanobanana (Script2Video)
- **Video Generators**: veo3-fast, veo3-pro-frames

### API Configuration:
- Single API key from environment: `YUNWU_API_KEY`
- Rate limiting configured per service
- Base URL: https://yunwu.ai

## Implementation Phases

### Phase 1: Model Selection Interface ✓ (Starting)

#### Backend Components:
1. **Model Configuration Service** (`services/model_config_service.py`)
   - Store available models for each category
   - User preference persistence in database
   - Model capability metadata

2. **Database Models** (extend `database_models.py`)
   ```python
   class UserModelPreference(Base):
       user_id, chat_model, image_model, video_model
   
   class AvailableModel(Base):
       model_id, category, name, provider, capabilities
   ```

3. **API Endpoints** (new router: `api_routes_models.py`)
   - `GET /api/v1/models/available` - List all available models
   - `GET /api/v1/models/preferences` - Get user preferences
   - `PUT /api/v1/models/preferences` - Update preferences

#### Frontend Components:
1. **Settings Page** (`frontend/src/pages/Settings.tsx`)
   - Model selection dropdowns
   - Save preferences button
   - Model capability display

2. **Model Selector Component** (`frontend/src/components/ModelSelector.tsx`)
   - Reusable dropdown component
   - Shows model capabilities
   - Persists to localStorage + backend

### Phase 2: Dialogue-to-Video Conversion Enhancement

#### Current Issues Analysis:
- NLP service in `services/nlp_service.py`
- Intent recognition needs improvement
- Limited context tracking

#### Improvements:
1. **Enhanced NLP Service** (`services/nlp_service_v2.py`)
   - Better intent classification
   - Multi-turn conversation context
   - Ambiguity detection
   - Structured error messages

2. **Conversation Manager** (`services/conversation_manager.py`)
   - Session-based context tracking
   - Conversation history
   - Intent disambiguation

3. **Validation Layer** (`utils/input_validation.py`)
   - Request validation
   - Constraint checking
   - Helpful error messages

### Phase 3: Step-by-Step Video Generation Editor

#### Components:
1. **Generation Workflow State Machine** (`workflows/generation_state_machine.py`)
   - States: script_review, scene_generation, timeline_editing, audio_customization
   - Transitions and validations
   - Checkpoint system

2. **Editor API Endpoints** (`api_routes_editor.py`)
   - `GET /api/v1/editor/episode/{id}/state` - Get current state
   - `POST /api/v1/editor/episode/{id}/script` - Update script
   - `POST /api/v1/editor/episode/{id}/scene/{scene_id}/regenerate` - Regenerate scene
   - `PUT /api/v1/editor/episode/{id}/timeline` - Update timeline
   - `POST /api/v1/editor/episode/{id}/audio` - Customize audio

3. **Frontend Editor** (`frontend/src/pages/VideoEditor.tsx`)
   - Multi-step wizard interface
   - Scene preview grid
   - Timeline editor
   - Audio controls
   - Regeneration buttons

### Phase 4: Multi-API Key Management System

#### Backend Components:
1. **API Key Pool Manager** (`services/api_key_pool.py`)
   ```python
   class APIKeyPool:
       - keys: List[APIKey]
       - load_balancer: LoadBalancer
       - health_monitor: HealthMonitor
       - rate_limiter: DistributedRateLimiter
   ```

2. **Load Balancer** (`services/load_balancer.py`)
   - Round-robin distribution
   - Least-loaded selection
   - Failover logic

3. **Health Monitor** (`services/health_monitor.py`)
   - API key status tracking
   - Rate limit monitoring
   - Automatic failover

4. **Concurrent Generation Manager** (`services/concurrent_generator.py`)
   - Parallel task execution
   - Queue management
   - Progress aggregation

5. **Database Models** (extend `database_models.py`)
   ```python
   class APIKey(Base):
       key_id, service_type, key_value, status, rate_limit_info
   
   class APIKeyUsage(Base):
       key_id, timestamp, request_count, success_count
   ```

6. **API Endpoints** (`api_routes_api_keys.py`)
   - `GET /api/v1/api-keys` - List keys with status
   - `POST /api/v1/api-keys` - Add new key
   - `DELETE /api/v1/api-keys/{id}` - Remove key
   - `GET /api/v1/api-keys/stats` - Usage statistics

#### Frontend Components:
1. **API Key Management Page** (`frontend/src/pages/APIKeyManagement.tsx`)
   - Key list with status indicators
   - Add/remove keys
   - Usage statistics
   - Health monitoring dashboard

## Integration Points

### Database Schema Extensions:
```sql
-- User preferences
CREATE TABLE user_model_preferences (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    chat_model VARCHAR(100),
    image_model VARCHAR(100),
    video_model VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Available models
CREATE TABLE available_models (
    id VARCHAR(36) PRIMARY KEY,
    category VARCHAR(50), -- chat, image, video
    name VARCHAR(100),
    provider VARCHAR(100),
    capabilities JSON,
    is_active BOOLEAN
);

-- API keys
CREATE TABLE api_keys (
    id VARCHAR(36) PRIMARY KEY,
    service_type VARCHAR(50), -- yunwu, openai, etc
    key_value VARCHAR(255) ENCRYPTED,
    status VARCHAR(50), -- active, rate_limited, failed
    rate_limit_per_minute INTEGER,
    rate_limit_per_day INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- API key usage
CREATE TABLE api_key_usage (
    id VARCHAR(36) PRIMARY KEY,
    key_id VARCHAR(36) REFERENCES api_keys(id),
    timestamp TIMESTAMP,
    request_count INTEGER,
    success_count INTEGER,
    error_count INTEGER
);

-- Generation checkpoints
CREATE TABLE generation_checkpoints (
    id VARCHAR(36) PRIMARY KEY,
    episode_id VARCHAR(36) REFERENCES episodes(id),
    stage VARCHAR(50), -- script, scenes, timeline, audio
    data JSON,
    created_at TIMESTAMP
);
```

### API Compatibility:
- All new endpoints follow `/api/v1/` pattern
- Maintains compatibility with existing Series/Episodes system
- WebSocket support for real-time updates

## Implementation Priority

### High Priority (Week 1):
1. ✅ Model selection interface (backend + frontend)
2. ✅ API key pool basic implementation
3. ✅ Database schema updates

### Medium Priority (Week 2):
1. Enhanced NLP service
2. Step-by-step editor (basic version)
3. Concurrent generation

### Lower Priority (Week 3):
1. Advanced editor features
2. Health monitoring dashboard
3. Analytics and reporting

## Testing Strategy

### Unit Tests:
- Model selection service
- API key pool logic
- Load balancer algorithms
- NLP improvements

### Integration Tests:
- End-to-end video generation
- Multi-key concurrent generation
- Editor workflow

### Performance Tests:
- Concurrent generation throughput
- API key failover speed
- Editor responsiveness

## Deployment Considerations

1. **Environment Variables**:
   - Multiple API keys support
   - Feature flags for gradual rollout

2. **Database Migration**:
   - Backward compatible schema changes
   - Data migration scripts

3. **Monitoring**:
   - API key usage metrics
   - Generation success rates
   - Performance metrics

## Next Steps

1. Create database migration script
2. Implement model configuration service
3. Build model selection UI
4. Add API key management backend
5. Create API key management UI
6. Enhance NLP service
7. Build step-by-step editor
8. Integration testing
9. Documentation
10. Deployment

---

**Status**: Phase 1 in progress
**Last Updated**: 2025-12-28