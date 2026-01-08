"""
Memory Types and Data Classes
Defines the data structures for the memory system
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryTier(str, Enum):
    """Memory hierarchy tiers"""
    WORKING = "working"      # Ultra short-term (in-memory)
    EPISODIC = "episodic"    # Session-based (database)
    SEMANTIC = "semantic"    # Cross-session (long-term)


class MemoryCategory(str, Enum):
    """Semantic memory categories"""
    PATTERN = "pattern"           # Successful generation patterns
    PREFERENCE = "preference"     # User preferences
    STRATEGY = "strategy"         # Agent strategies
    FAILURE = "failure"           # Failure patterns to avoid
    FEEDBACK = "feedback"         # User feedback insights


class KnowledgeCategory(str, Enum):
    """Knowledge categories for semantic memory"""
    USER_PREFERENCE = "user_preference"
    AGENT_BEHAVIOR = "agent_behavior"
    GENERATION_PATTERN = "generation_pattern"
    STYLE_PATTERN = "style_pattern"
    FEEDBACK_INSIGHT = "feedback_insight"
    DOMAIN_KNOWLEDGE = "domain_knowledge"


class MemoryType(str, Enum):
    """Episodic memory types"""
    DECISION = "decision"         # Agent decision
    FEEDBACK = "feedback"         # User feedback
    OUTCOME = "outcome"           # Generation outcome
    INTERACTION = "interaction"   # User interaction


class EpisodicMemoryData(BaseModel):
    """Episodic memory data structure"""
    id: Optional[str] = None
    episode_id: str
    user_id: str
    memory_type: MemoryType
    agent_name: str
    context: Dict[str, Any] = Field(default_factory=dict)
    outcome: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None
    created_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class SemanticMemoryData(BaseModel):
    """Semantic memory data structure"""
    id: Optional[str] = None
    user_id: str
    category: KnowledgeCategory
    knowledge_key: str
    knowledge_value: Dict[str, Any] = Field(default_factory=dict)
    source_episodes: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0
    importance_score: float = 0.5
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class UserMemoryProfileData(BaseModel):
    """User memory profile data structure"""
    id: Optional[str] = None
    user_id: str
    preferences: Dict[str, Any] = Field(default_factory=dict)
    style_patterns: Dict[str, Any] = Field(default_factory=dict)
    feedback_history: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MemoryConsolidationResult(BaseModel):
    """Result of memory consolidation process"""
    episode_id: str
    consolidation_type: str
    insights_extracted: int = 0
    patterns_identified: int = 0
    memories_created: int = 0
    memories_updated: int = 0
    memories_pruned: int = 0
    processing_time_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemorySearchQuery(BaseModel):
    """Query parameters for memory search"""
    query_text: str
    user_id: Optional[str] = None
    agent_name: Optional[str] = None
    memory_category: Optional[MemoryCategory] = None
    top_k: int = 5
    similarity_threshold: float = 0.7
    
    class Config:
        use_enum_values = True


class MemorySearchResult(BaseModel):
    """Result of memory search"""
    memory_id: str
    content: Dict[str, Any]
    similarity_score: float
    usage_count: int
    success_rate: float
    memory_category: MemoryCategory
    agent_name: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AgentPerformanceMetricData(BaseModel):
    """Agent performance metric data"""
    id: Optional[str] = None
    agent_name: str
    episode_id: Optional[str] = None
    metric_type: str  # quality, speed, accuracy, user_satisfaction
    metric_value: float
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None