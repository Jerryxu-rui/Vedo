# Step-by-Step Video Generation Workflow Design

**Feature**: Granular Video Segment Preview & Editing  
**Priority**: HIGH  
**Estimated Effort**: 3-4 weeks (120-160 hours)  
**Status**: Design Phase

---

## 🎯 Overview

This feature transforms the current monolithic video generation pipeline into a **step-by-step workflow** where users can:
1. **Preview** each generated video segment individually
2. **Review** and approve/reject each segment before proceeding
3. **Edit** or **regenerate** specific segments without affecting others
4. **Compile** approved segments into the final long-form video

### Current vs. Proposed Flow

#### Current Flow (Monolithic)
```
Idea → Story → Script → [Generate All Scenes] → Concatenate → Final Video
                              ↓
                    (No intermediate review)
```

#### Proposed Flow (Step-by-Step)
```
Idea → Story → Script → Scene 1 → [Preview] → Approve/Edit
                      ↓
                    Scene 2 → [Preview] → Approve/Edit
                      ↓
                    Scene 3 → [Preview] → Approve/Edit
                      ↓
                    [Compile Approved Scenes] → Final Video
```

---

## 📋 Requirements

### Functional Requirements

#### FR1: Segment-Level Generation
- Generate video segments one at a time (or in small batches)
- Each segment corresponds to a scene or shot
- Store segment metadata (duration, status, quality metrics)

#### FR2: Preview Interface
- Display generated video segment with playback controls
- Show segment metadata (scene number, duration, characters, dialogue)
- Provide visual quality indicators

#### FR3: Review & Approval
- User can approve, reject, or request regeneration
- User can edit segment parameters (prompt, style, duration)
- System tracks approval status for each segment

#### FR4: Regeneration
- Regenerate specific segments without affecting others
- Maintain character/scene consistency across regenerations
- Support multiple regeneration attempts with variation

#### FR5: Compilation
- Compile only approved segments into final video
- Support custom ordering of segments
- Add transitions between segments
- Generate final video metadata

### Non-Functional Requirements

#### NFR1: Performance
- Segment generation time: < 2 minutes per 5-second segment
- Preview loading time: < 3 seconds
- Compilation time: < 30 seconds for 10 segments

#### NFR2: Storage
- Store all segment versions for comparison
- Implement cleanup policy for old versions
- Support cloud storage for scalability

#### NFR3: User Experience
- Real-time progress updates via WebSocket
- Responsive preview interface
- Clear status indicators for each segment

---

## 🏗️ Architecture Design

### Database Schema Extensions

#### New Tables

```sql
-- Video segments table
CREATE TABLE video_segments (
    id VARCHAR(36) PRIMARY KEY,
    episode_id VARCHAR(36) REFERENCES episodes(id),
    scene_id VARCHAR(36) REFERENCES scenes(id),
    shot_id VARCHAR(36) REFERENCES shots(id),
    
    -- Segment info
    segment_number INTEGER NOT NULL,
    segment_type VARCHAR(50), -- 'scene', 'shot', 'transition'
    
    -- Generation parameters
    generation_params JSON, -- Stores prompt, style, seed, etc.
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- pending, generating, completed, approved, rejected, failed
    approval_status VARCHAR(50), -- null, approved, rejected, needs_revision
    
    -- Generated assets
    video_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    duration FLOAT, -- in seconds
    
    -- Quality metrics
    quality_score FLOAT,
    consistency_score FLOAT,
    
    -- Metadata
    file_size INTEGER,
    resolution VARCHAR(20), -- e.g., "1920x1080"
    format VARCHAR(20), -- e.g., "mp4"
    
    -- Versioning
    version INTEGER DEFAULT 1,
    parent_segment_id VARCHAR(36) REFERENCES video_segments(id),
    
    -- User feedback
    user_notes TEXT,
    rejection_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    
    INDEX idx_episode_segment (episode_id, segment_number),
    INDEX idx_status (status),
    INDEX idx_approval (approval_status)
);

-- Segment compilation jobs
CREATE TABLE segment_compilation_jobs (
    id VARCHAR(36) PRIMARY KEY,
    episode_id VARCHAR(36) REFERENCES episodes(id),
    
    -- Compilation config
    segment_ids JSON, -- Array of segment IDs in order
    transition_style VARCHAR(100),
    audio_config JSON,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    
    -- Output
    output_video_url VARCHAR(500),
    output_duration FLOAT,
    output_file_size INTEGER,
    
    -- Error tracking
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Segment review history
CREATE TABLE segment_reviews (
    id VARCHAR(36) PRIMARY KEY,
    segment_id VARCHAR(36) REFERENCES video_segments(id),
    user_id VARCHAR(36),
    
    -- Review data
    action VARCHAR(50), -- 'approve', 'reject', 'request_regeneration'
    rating INTEGER, -- 1-5 stars
    feedback TEXT,
    suggested_changes JSON,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints

#### Segment Generation

```python
# Start segment-by-segment generation
POST /api/v1/episodes/{episode_id}/generate-segments
{
    "mode": "sequential",  # or "parallel"
    "batch_size": 1,  # Number of segments to generate at once
    "start_from": 0,  # Resume from specific segment
    "auto_approve": false  # Auto-approve segments (for testing)
}

Response:
{
    "job_id": "uuid",
    "total_segments": 10,
    "status": "started"
}

# Get segment generation status
GET /api/v1/episodes/{episode_id}/segments/status

Response:
{
    "total_segments": 10,
    "completed": 3,
    "approved": 2,
    "rejected": 0,
    "pending": 7,
    "current_segment": 4,
    "segments": [
        {
            "id": "seg-1",
            "segment_number": 1,
            "status": "completed",
            "approval_status": "approved",
            "video_url": "...",
            "thumbnail_url": "...",
            "duration": 5.2,
            "quality_score": 0.85
        },
        ...
    ]
}
```

#### Segment Review

```python
# Get segment details for review
GET /api/v1/segments/{segment_id}

Response:
{
    "id": "seg-1",
    "segment_number": 1,
    "scene_info": {
        "scene_number": 1,
        "location": "公司会议室",
        "description": "..."
    },
    "video_url": "...",
    "thumbnail_url": "...",
    "duration": 5.2,
    "generation_params": {
        "prompt": "...",
        "style": "写实电影感",
        "seed": 12345
    },
    "quality_metrics": {
        "overall_score": 0.85,
        "consistency_score": 0.90,
        "visual_quality": 0.82
    },
    "status": "completed",
    "approval_status": null,
    "version": 1,
    "previous_versions": []
}

# Approve segment
POST /api/v1/segments/{segment_id}/approve
{
    "rating": 5,
    "feedback": "Looks great!"
}

# Reject segment
POST /api/v1/segments/{segment_id}/reject
{
    "reason": "Character appearance inconsistent",
    "suggested_changes": {
        "character_prompt": "更强调角色的眼镜特征"
    }
}

# Request regeneration
POST /api/v1/segments/{segment_id}/regenerate
{
    "changes": {
        "prompt_modifications": "...",
        "style_adjustments": "...",
        "seed": 67890  # New seed for variation
    },
    "keep_original": true  # Keep original as version
}
```

#### Compilation

```python
# Compile approved segments
POST /api/v1/episodes/{episode_id}/compile
{
    "segment_ids": ["seg-1", "seg-2", "seg-3"],  # Optional: custom order
    "transition_style": "fade",  # fade, cut, dissolve
    "audio_config": {
        "background_music": true,
        "volume_normalization": true
    }
}

Response:
{
    "compilation_job_id": "uuid",
    "status": "started",
    "estimated_duration": 45  # seconds
}

# Get compilation status
GET /api/v1/compilation-jobs/{job_id}

Response:
{
    "id": "uuid",
    "status": "completed",
    "progress": 100,
    "output_video_url": "...",
    "output_duration": 32.5,
    "segments_included": 10
}
```

---

## 🔧 Implementation Plan

### Phase 1: Backend Infrastructure (Week 1, 40h)

#### Task 1.1: Database Schema (8h)
- [ ] Create migration for new tables
- [ ] Add indexes for performance
- [ ] Update SQLAlchemy models
- [ ] Write database tests

**Files to Create/Modify:**
- `migrations/add_video_segments.sql`
- `database_models.py` (add VideoSegment, SegmentCompilationJob, SegmentReview)
- `tests/test_segment_models.py`

#### Task 1.2: Segment Generation Service (16h)
- [ ] Create `SegmentGenerationService` class
- [ ] Implement sequential generation logic
- [ ] Add segment status tracking
- [ ] Integrate with existing pipeline

**Files to Create:**
- `services/segment_generation_service.py`
- `services/segment_storage_service.py`
- `tests/test_segment_generation.py`

```python
# services/segment_generation_service.py
class SegmentGenerationService:
    async def generate_segment(
        self,
        episode_id: str,
        segment_number: int,
        scene_script: Dict,
        generation_params: Dict
    ) -> VideoSegment:
        """Generate a single video segment"""
        pass
    
    async def generate_segments_sequential(
        self,
        episode_id: str,
        scene_scripts: List[Dict],
        callback: Optional[Callable] = None
    ) -> List[VideoSegment]:
        """Generate segments one by one"""
        pass
    
    async def regenerate_segment(
        self,
        segment_id: str,
        changes: Dict
    ) -> VideoSegment:
        """Regenerate a specific segment with modifications"""
        pass
```

#### Task 1.3: Segment Review Service (8h)
- [ ] Create `SegmentReviewService` class
- [ ] Implement approval/rejection logic
- [ ] Add review history tracking
- [ ] Quality metrics calculation

**Files to Create:**
- `services/segment_review_service.py`
- `tests/test_segment_review.py`

#### Task 1.4: Compilation Service (8h)
- [ ] Create `SegmentCompilationService` class
- [ ] Implement video concatenation with transitions
- [ ] Add audio mixing capabilities
- [ ] Handle compilation job queue

**Files to Create:**
- `services/segment_compilation_service.py`
- `utils/video_compilation.py`
- `tests/test_compilation.py`

---

### Phase 2: API Layer (Week 2, 32h)

#### Task 2.1: Segment Generation Endpoints (12h)
- [ ] Implement generation endpoints
- [ ] Add WebSocket progress updates
- [ ] Error handling and retry logic
- [ ] Rate limiting

**Files to Create/Modify:**
- `api_routes_segments.py`
- `api_server.py` (register routes)

#### Task 2.2: Review & Approval Endpoints (8h)
- [ ] Implement review endpoints
- [ ] Add validation logic
- [ ] User permission checks

**Files to Create:**
- `api_routes_segment_review.py`

#### Task 2.3: Compilation Endpoints (8h)
- [ ] Implement compilation endpoints
- [ ] Add job status tracking
- [ ] Result delivery

**Files to Create:**
- `api_routes_compilation.py`

#### Task 2.4: Integration Testing (4h)
- [ ] End-to-end API tests
- [ ] Load testing
- [ ] Error scenario testing

---

### Phase 3: Frontend Interface (Week 3, 40h)

#### Task 3.1: Segment Preview Component (16h)
- [ ] Create `SegmentPreview.tsx` component
- [ ] Video player with controls
- [ ] Metadata display
- [ ] Quality indicators

**Files to Create:**
- `frontend/src/components/SegmentPreview.tsx`
- `frontend/src/components/SegmentPreview.css`
- `frontend/src/components/SegmentPlayer.tsx`

```typescript
// frontend/src/components/SegmentPreview.tsx
interface SegmentPreviewProps {
    segment: VideoSegment;
    onApprove: (segmentId: string, feedback: string) => void;
    onReject: (segmentId: string, reason: string) => void;
    onRegenerate: (segmentId: string, changes: any) => void;
}

export const SegmentPreview: React.FC<SegmentPreviewProps> = ({
    segment,
    onApprove,
    onReject,
    onRegenerate
}) => {
    return (
        <div className="segment-preview">
            <div className="segment-header">
                <h3>Segment {segment.segment_number}</h3>
                <span className="status-badge">{segment.status}</span>
            </div>
            
            <SegmentPlayer videoUrl={segment.video_url} />
            
            <div className="segment-metadata">
                <p>Duration: {segment.duration}s</p>
                <p>Quality Score: {segment.quality_score}</p>
            </div>
            
            <div className="segment-actions">
                <button onClick={() => onApprove(segment.id, "")}>
                    ✓ Approve
                </button>
                <button onClick={() => onReject(segment.id, "")}>
                    ✗ Reject
                </button>
                <button onClick={() => onRegenerate(segment.id, {})}>
                    ↻ Regenerate
                </button>
            </div>
        </div>
    );
};
```

#### Task 3.2: Segment Timeline View (12h)
- [ ] Create timeline component
- [ ] Drag-and-drop reordering
- [ ] Status visualization
- [ ] Batch operations

**Files to Create:**
- `frontend/src/components/SegmentTimeline.tsx`
- `frontend/src/components/SegmentCard.tsx`

#### Task 3.3: Review Interface (8h)
- [ ] Review form with rating
- [ ] Feedback text area
- [ ] Suggested changes editor
- [ ] Review history display

**Files to Create:**
- `frontend/src/components/SegmentReviewForm.tsx`

#### Task 3.4: Compilation Interface (4h)
- [ ] Compilation configuration
- [ ] Progress tracking
- [ ] Final video preview

**Files to Create:**
- `frontend/src/components/CompilationPanel.tsx`

---

### Phase 4: Integration & Polish (Week 4, 24h)

#### Task 4.1: Pipeline Integration (8h)
- [ ] Integrate with existing Idea2Video pipeline
- [ ] Update conversational workflow
- [ ] Backward compatibility

**Files to Modify:**
- `pipelines/idea2video_pipeline.py`
- `workflows/conversational_episode_workflow.py`

#### Task 4.2: WebSocket Real-time Updates (6h)
- [ ] Segment generation progress
- [ ] Review notifications
- [ ] Compilation status

**Files to Modify:**
- `utils/websocket_manager.py`
- `services/progress_broadcaster.py`

#### Task 4.3: Testing & Bug Fixes (6h)
- [ ] Integration testing
- [ ] User acceptance testing
- [ ] Bug fixes

#### Task 4.4: Documentation (4h)
- [ ] API documentation
- [ ] User guide
- [ ] Developer guide

---

## 🎨 User Experience Flow

### Step 1: Initiate Generation
```
User: "Generate video from my idea"
System: "Starting segment-by-segment generation..."
        "Total segments: 10"
```

### Step 2: Generate First Segment
```
System: "Generating Segment 1/10..."
        [Progress bar: 0% → 100%]
        "Segment 1 completed! Ready for review."
```

### Step 3: Review Segment
```
User views:
- Video player with segment
- Scene info (location, characters, dialogue)
- Quality metrics
- Actions: Approve | Reject | Regenerate
```

### Step 4: User Decision

#### Option A: Approve
```
User: [Clicks Approve]
System: "Segment 1 approved!"
        "Generating Segment 2/10..."
```

#### Option B: Reject & Regenerate
```
User: [Clicks Reject]
      "Character appearance doesn't match"
      [Suggests changes]
System: "Regenerating Segment 1 with your feedback..."
        [Progress bar]
        "New version ready for review!"
```

#### Option C: Edit Parameters
```
User: [Clicks Edit]
      [Modifies prompt/style]
      [Clicks Regenerate]
System: "Regenerating with new parameters..."
```

### Step 5: Continue Until All Approved
```
System: "All 10 segments approved!"
        "Ready to compile final video?"
User: [Clicks Compile]
System: "Compiling final video..."
        [Progress bar]
        "Final video ready!"
```

---

## 📊 Success Metrics

### Quantitative Metrics
- **Segment Approval Rate**: Target > 80% first-time approval
- **Regeneration Rate**: Target < 20% of segments need regeneration
- **Time to Final Video**: Target < 30 minutes for 10-segment video
- **User Satisfaction**: Target > 4.5/5 stars

### Qualitative Metrics
- User feedback on control and flexibility
- Reduction in post-production edits
- Increase in final video quality ratings

---

## 🔒 Technical Considerations

### Storage Management
- **Segment Storage**: ~50MB per 5-second segment
- **Version Storage**: Keep last 3 versions per segment
- **Cleanup Policy**: Delete rejected versions after 7 days
- **Cloud Storage**: Use S3/GCS for scalability

### Performance Optimization
- **Parallel Generation**: Generate multiple segments in parallel (with rate limiting)
- **Caching**: Cache character/scene references for consistency
- **Lazy Loading**: Load segment videos on-demand
- **Thumbnail Generation**: Generate thumbnails for quick preview

### Error Handling
- **Generation Failures**: Automatic retry with exponential backoff
- **Partial Failures**: Continue with other segments
- **Rollback**: Ability to revert to previous approved version
- **User Notification**: Clear error messages with recovery options

---

## 🚀 Migration Strategy

### Backward Compatibility
- Keep existing monolithic pipeline as fallback
- Add feature flag for step-by-step mode
- Gradual rollout to users

### Data Migration
- No migration needed for existing videos
- New videos use new workflow
- Option to "upgrade" old videos to segmented format

---

## 📝 Future Enhancements

### Phase 5: Advanced Features (Future)
- **AI-Powered Suggestions**: Suggest improvements for rejected segments
- **Batch Editing**: Edit multiple segments at once
- **Template Library**: Save approved segment patterns as templates
- **Collaborative Review**: Multiple users can review segments
- **A/B Testing**: Generate multiple versions, let users choose
- **Auto-Enhancement**: AI automatically improves low-quality segments

---

## 🎯 Implementation Priority

### Must-Have (MVP)
1. ✅ Sequential segment generation
2. ✅ Basic preview interface
3. ✅ Approve/Reject functionality
4. ✅ Simple regeneration
5. ✅ Basic compilation

### Should-Have (V1.1)
6. Parallel generation (with rate limiting)
7. Advanced editing interface
8. Quality metrics display
9. Version comparison
10. Drag-and-drop reordering

### Nice-to-Have (V2.0)
11. AI-powered suggestions
12. Batch operations
13. Template library
14. Collaborative review
15. A/B testing

---

**Last Updated**: 2025-12-31  
**Next Review**: After Phase 1 completion  
**Owner**: Development Team