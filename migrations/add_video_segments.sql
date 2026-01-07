-- Migration: Add Video Segments Tables for Step-by-Step Video Generation
-- Date: 2025-12-31
-- Description: Adds tables for granular video segment generation, review, and compilation

-- Video Segments Table
CREATE TABLE IF NOT EXISTS video_segments (
    id VARCHAR(36) PRIMARY KEY,
    episode_id VARCHAR(36),
    scene_id VARCHAR(36),
    shot_id VARCHAR(36),
    
    -- Segment info
    segment_number INTEGER NOT NULL,
    segment_type VARCHAR(50) DEFAULT 'shot',
    
    -- Generation parameters
    generation_params JSON,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    approval_status VARCHAR(50),
    
    -- Generated assets
    video_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    duration FLOAT,
    
    -- Quality metrics
    quality_score FLOAT,
    consistency_score FLOAT,
    
    -- Metadata
    file_size INTEGER,
    resolution VARCHAR(20),
    format VARCHAR(20),
    
    -- Versioning
    version INTEGER DEFAULT 1,
    parent_segment_id VARCHAR(36),
    
    -- User feedback
    user_notes TEXT,
    rejection_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE SET NULL,
    FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_segment_id) REFERENCES video_segments(id) ON DELETE SET NULL
);

-- Indexes for video_segments
CREATE INDEX IF NOT EXISTS idx_video_segments_episode ON video_segments(episode_id, segment_number);
CREATE INDEX IF NOT EXISTS idx_video_segments_status ON video_segments(status);
CREATE INDEX IF NOT EXISTS idx_video_segments_approval ON video_segments(approval_status);
CREATE INDEX IF NOT EXISTS idx_video_segments_scene ON video_segments(scene_id);
CREATE INDEX IF NOT EXISTS idx_video_segments_shot ON video_segments(shot_id);
CREATE INDEX IF NOT EXISTS idx_video_segments_parent ON video_segments(parent_segment_id);

-- Segment Compilation Jobs Table
CREATE TABLE IF NOT EXISTS segment_compilation_jobs (
    id VARCHAR(36) PRIMARY KEY,
    episode_id VARCHAR(36) NOT NULL,
    
    -- Compilation config
    segment_ids JSON,
    transition_style VARCHAR(100) DEFAULT 'cut',
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
);

-- Indexes for segment_compilation_jobs
CREATE INDEX IF NOT EXISTS idx_compilation_jobs_episode ON segment_compilation_jobs(episode_id);
CREATE INDEX IF NOT EXISTS idx_compilation_jobs_status ON segment_compilation_jobs(status);

-- Segment Reviews Table
CREATE TABLE IF NOT EXISTS segment_reviews (
    id VARCHAR(36) PRIMARY KEY,
    segment_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36),
    
    -- Review data
    action VARCHAR(50) NOT NULL,
    rating INTEGER,
    feedback TEXT,
    suggested_changes JSON,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (segment_id) REFERENCES video_segments(id) ON DELETE CASCADE
);

-- Indexes for segment_reviews
CREATE INDEX IF NOT EXISTS idx_segment_reviews_segment ON segment_reviews(segment_id);
CREATE INDEX IF NOT EXISTS idx_segment_reviews_user ON segment_reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_segment_reviews_action ON segment_reviews(action);

-- Add trigger to update updated_at timestamp for video_segments
CREATE TRIGGER IF NOT EXISTS update_video_segments_timestamp 
AFTER UPDATE ON video_segments
FOR EACH ROW
BEGIN
    UPDATE video_segments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Add trigger to update updated_at timestamp for segment_compilation_jobs
CREATE TRIGGER IF NOT EXISTS update_compilation_jobs_timestamp 
AFTER UPDATE ON segment_compilation_jobs
FOR EACH ROW
BEGIN
    UPDATE segment_compilation_jobs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Comments for documentation
COMMENT ON TABLE video_segments IS 'Stores individual video segments for step-by-step generation and review';
COMMENT ON TABLE segment_compilation_jobs IS 'Tracks compilation jobs that combine approved segments into final videos';
COMMENT ON TABLE segment_reviews IS 'Stores user reviews and feedback for video segments';

-- Migration complete
SELECT 'Video segments tables created successfully' AS status;