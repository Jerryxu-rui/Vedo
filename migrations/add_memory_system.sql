-- Migration: Add Enhanced Agent Memory System
-- Date: 2026-01-07
-- Description: Adds tables for hierarchical memory architecture (episodic, semantic, user profiles)
-- Phase: 1.1 - Database Schema Migration

-- ============================================================================
-- TIER 2: EPISODIC MEMORY (Session-Based)
-- ============================================================================

CREATE TABLE IF NOT EXISTS episode_memories (
    id VARCHAR(36) PRIMARY KEY,
    episode_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,  -- 'decision', 'feedback', 'outcome', 'interaction'
    agent_name VARCHAR(100) NOT NULL,
    context JSON NOT NULL,
    outcome JSON,
    quality_score FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    INDEX idx_episode_user (episode_id, user_id),
    INDEX idx_agent_type (agent_name, memory_type),
    INDEX idx_created_at (created_at)
);

-- ============================================================================
-- TIER 3: SEMANTIC MEMORY (Cross-Session Long-term Knowledge)
-- ============================================================================

CREATE TABLE IF NOT EXISTS semantic_memories (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255),  -- NULL for global memories
    memory_category VARCHAR(100) NOT NULL,  -- 'pattern', 'preference', 'strategy', 'failure', 'feedback'
    agent_name VARCHAR(100),
    content JSON NOT NULL,
    embedding_text TEXT,  -- Text representation for embedding generation
    usage_count INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    last_used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    decay_score FLOAT DEFAULT 1.0,  -- Memory importance (0-1)
    
    INDEX idx_user_category (user_id, memory_category),
    INDEX idx_agent (agent_name),
    INDEX idx_decay_score (decay_score),
    INDEX idx_last_used (last_used_at)
);

-- Note: Vector embeddings will be added when migrating to PostgreSQL with pgvector
-- For SQLite compatibility, we'll store embedding_text and implement semantic search via external service

-- ============================================================================
-- USER MEMORY PROFILES (Personalization)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_memory_profiles (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    preferred_styles JSON DEFAULT '[]',
    preferred_genres JSON DEFAULT '[]',
    common_themes JSON DEFAULT '[]',
    generation_preferences JSON DEFAULT '{}',
    feedback_patterns JSON DEFAULT '{}',
    total_episodes INTEGER DEFAULT 0,
    avg_quality_score FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id)
);

-- ============================================================================
-- MEMORY CONSOLIDATION LOG (Audit Trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory_consolidations (
    id VARCHAR(36) PRIMARY KEY,
    episode_id VARCHAR(36),
    consolidation_type VARCHAR(50) NOT NULL,  -- 'episode_complete', 'periodic', 'manual'
    insights_extracted INTEGER DEFAULT 0,
    patterns_identified INTEGER DEFAULT 0,
    memories_created INTEGER DEFAULT 0,
    memories_updated INTEGER DEFAULT 0,
    memories_pruned INTEGER DEFAULT 0,
    processing_time_ms INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE SET NULL,
    INDEX idx_episode (episode_id),
    INDEX idx_type (consolidation_type),
    INDEX idx_created_at (created_at)
);

-- ============================================================================
-- MEMORY EMBEDDINGS CACHE (For SQLite compatibility)
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory_embeddings (
    id VARCHAR(36) PRIMARY KEY,
    semantic_memory_id VARCHAR(36) NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,  -- e.g., 'text-embedding-3-small'
    embedding_vector TEXT NOT NULL,  -- JSON array of floats
    dimension INTEGER NOT NULL,  -- e.g., 1536
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (semantic_memory_id) REFERENCES semantic_memories(id) ON DELETE CASCADE,
    UNIQUE INDEX idx_memory_model (semantic_memory_id, embedding_model),
    INDEX idx_model (embedding_model)
);

-- ============================================================================
-- AGENT PERFORMANCE METRICS (For memory-augmented decision tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_performance_metrics (
    id VARCHAR(36) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    episode_id VARCHAR(36),
    metric_type VARCHAR(50) NOT NULL,  -- 'quality', 'speed', 'accuracy', 'user_satisfaction'
    metric_value FLOAT NOT NULL,
    context JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    INDEX idx_agent_type (agent_name, metric_type),
    INDEX idx_episode (episode_id),
    INDEX idx_created_at (created_at)
);

-- ============================================================================
-- MEMORY RETRIEVAL LOG (For analytics and optimization)
-- ============================================================================

CREATE TABLE IF NOT EXISTS memory_retrieval_log (
    id VARCHAR(36) PRIMARY KEY,
    semantic_memory_id VARCHAR(36) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    episode_id VARCHAR(36),
    query_text TEXT,
    similarity_score FLOAT,
    was_useful BOOLEAN,  -- Tracked via feedback
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (semantic_memory_id) REFERENCES semantic_memories(id) ON DELETE CASCADE,
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE SET NULL,
    INDEX idx_memory (semantic_memory_id),
    INDEX idx_agent (agent_name),
    INDEX idx_episode (episode_id),
    INDEX idx_created_at (created_at)
);

-- ============================================================================
-- INITIAL DATA SEEDING
-- ============================================================================

-- Create default global memories for common patterns
INSERT INTO semantic_memories (id, user_id, memory_category, agent_name, content, embedding_text, created_at)
VALUES 
    (
        'global-pattern-001',
        NULL,
        'pattern',
        'StoryboardArtist',
        '{"pattern_type": "shot_composition", "description": "Close-up shots work well for emotional moments", "success_rate": 0.85, "usage_scenarios": ["character_emotion", "dramatic_reveal"]}',
        'Close-up shots work well for emotional moments and dramatic reveals',
        CURRENT_TIMESTAMP
    ),
    (
        'global-pattern-002',
        NULL,
        'pattern',
        'SceneImageGenerator',
        '{"pattern_type": "prompt_structure", "description": "Adding lighting details improves scene atmosphere", "success_rate": 0.78, "usage_scenarios": ["scene_generation", "atmosphere_creation"]}',
        'Adding lighting details like golden hour, soft shadows, dramatic lighting improves scene atmosphere',
        CURRENT_TIMESTAMP
    ),
    (
        'global-strategy-001',
        NULL,
        'strategy',
        'CharacterExtractor',
        '{"strategy_type": "character_consistency", "description": "Maintain consistent character descriptions across scenes", "success_rate": 0.92, "best_practices": ["use_reference_images", "detailed_appearance_notes"]}',
        'Maintain consistent character descriptions across scenes using reference images and detailed appearance notes',
        CURRENT_TIMESTAMP
    );

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================

-- This migration creates the foundation for the enhanced memory system.
-- 
-- IMPORTANT: When migrating to PostgreSQL:
-- 1. Replace VARCHAR(36) with UUID type
-- 2. Add pgvector extension: CREATE EXTENSION vector;
-- 3. Add vector column to semantic_memories: embedding VECTOR(1536)
-- 4. Create vector index: CREATE INDEX ON semantic_memories USING ivfflat (embedding vector_cosine_ops);
-- 5. Remove memory_embeddings table (no longer needed with native vector support)
--
-- For now, this SQLite-compatible schema uses:
-- - JSON columns for structured data
-- - TEXT for embedding storage (as JSON arrays)
-- - Separate embeddings cache table
--
-- Performance Considerations:
-- - Indexes added for common query patterns
-- - Decay score indexed for efficient pruning
-- - Created_at indexed for time-based queries
--
-- Rollback:
-- To rollback this migration, run:
-- DROP TABLE IF EXISTS memory_retrieval_log;
-- DROP TABLE IF EXISTS agent_performance_metrics;
-- DROP TABLE IF EXISTS memory_embeddings;
-- DROP TABLE IF EXISTS memory_consolidations;
-- DROP TABLE IF EXISTS user_memory_profiles;
-- DROP TABLE IF EXISTS semantic_memories;
-- DROP TABLE IF EXISTS episode_memories;