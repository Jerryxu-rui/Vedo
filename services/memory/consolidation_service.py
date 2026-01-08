"""
Memory Consolidation Service
Automates learning from episode experiences and consolidates memories
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import time

from database_models import MemoryConsolidation, EpisodeMemory, SemanticMemory
from services.memory.episodic_memory_service import EpisodicMemoryService
from services.memory.semantic_memory_service import SemanticMemoryService
from services.memory.memory_types import (
    MemoryType,
    KnowledgeCategory,
    MemoryCategory,
)
import uuid


class ConsolidationService:
    """
    Service for consolidating episodic memories into semantic knowledge
    
    Implements automated learning from episode experiences:
    - Pattern extraction from successful decisions
    - Failure analysis and avoidance strategies
    - User preference learning
    - Agent performance optimization
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.episodic = EpisodicMemoryService(db)
        self.semantic = SemanticMemoryService(db)
    
    def consolidate_episode(
        self,
        episode_id: str,
        user_id: str,
        consolidation_type: str = "episode_complete",
        min_quality_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Consolidate an episode's memories into semantic knowledge
        
        Args:
            episode_id: Episode ID
            user_id: User ID
            consolidation_type: Type of consolidation (episode_complete, periodic, manual)
            min_quality_threshold: Minimum quality score for consolidation
        
        Returns:
            Consolidation summary
        """
        start_time = time.time()
        
        # Get episode memories
        memories = self.episodic.get_episode_memories(episode_id=episode_id)
        
        if not memories:
            return {
                'episode_id': episode_id,
                'insights_extracted': 0,
                'patterns_identified': 0,
                'memories_created': 0,
                'memories_updated': 0,
                'memories_pruned': 0,
                'processing_time_ms': 0
            }
        
        insights_extracted = 0
        patterns_identified = 0
        memories_created = 0
        memories_updated = 0
        
        # 1. Extract successful patterns
        success_patterns = self._extract_success_patterns(
            memories, min_quality_threshold
        )
        for pattern in success_patterns:
            result = self._store_pattern(user_id, episode_id, pattern)
            if result['created']:
                memories_created += 1
            else:
                memories_updated += 1
            patterns_identified += 1
        
        # 2. Extract failure patterns
        failure_patterns = self._extract_failure_patterns(memories)
        for pattern in failure_patterns:
            result = self._store_failure_pattern(user_id, episode_id, pattern)
            if result['created']:
                memories_created += 1
            else:
                memories_updated += 1
            insights_extracted += 1
        
        # 3. Extract user preferences
        preferences = self._extract_user_preferences(memories)
        for pref in preferences:
            result = self._store_user_preference(user_id, episode_id, pref)
            if result['created']:
                memories_created += 1
            else:
                memories_updated += 1
            insights_extracted += 1
        
        # 4. Extract agent strategies
        strategies = self._extract_agent_strategies(memories, min_quality_threshold)
        for strategy in strategies:
            result = self._store_agent_strategy(user_id, episode_id, strategy)
            if result['created']:
                memories_created += 1
            else:
                memories_updated += 1
            insights_extracted += 1
        
        # 5. Prune low-value memories
        memories_pruned = self.semantic.prune_low_value_memories(
            user_id=user_id,
            min_decay_score=0.3,
            max_age_days=90
        )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Log consolidation
        self._log_consolidation(
            episode_id=episode_id,
            consolidation_type=consolidation_type,
            insights_extracted=insights_extracted,
            patterns_identified=patterns_identified,
            memories_created=memories_created,
            memories_updated=memories_updated,
            memories_pruned=memories_pruned,
            processing_time_ms=processing_time_ms
        )
        
        return {
            'episode_id': episode_id,
            'insights_extracted': insights_extracted,
            'patterns_identified': patterns_identified,
            'memories_created': memories_created,
            'memories_updated': memories_updated,
            'memories_pruned': memories_pruned,
            'processing_time_ms': processing_time_ms
        }
    
    def _extract_success_patterns(
        self,
        memories: List,
        min_quality: float
    ) -> List[Dict[str, Any]]:
        """Extract successful decision patterns"""
        patterns = []
        
        # Group by agent
        agent_decisions = {}
        for memory in memories:
            if memory.memory_type == MemoryType.DECISION and \
               memory.quality_score and memory.quality_score >= min_quality:
                
                agent = memory.agent_name
                if agent not in agent_decisions:
                    agent_decisions[agent] = []
                agent_decisions[agent].append(memory)
        
        # Extract patterns for each agent
        for agent, decisions in agent_decisions.items():
            if len(decisions) >= 2:  # Need at least 2 decisions for pattern
                # Calculate average quality
                avg_quality = sum(d.quality_score for d in decisions) / len(decisions)
                
                # Extract common context elements
                common_context = self._find_common_context(
                    [d.context for d in decisions]
                )
                
                patterns.append({
                    'agent_name': agent,
                    'pattern_type': 'success',
                    'decision_count': len(decisions),
                    'avg_quality': avg_quality,
                    'common_context': common_context,
                    'sample_contexts': [d.context for d in decisions[:3]]
                })
        
        return patterns
    
    def _extract_failure_patterns(
        self,
        memories: List
    ) -> List[Dict[str, Any]]:
        """Extract failure patterns to avoid"""
        patterns = []
        
        # Find decisions with low quality or negative outcomes
        failures = [
            m for m in memories
            if m.memory_type == MemoryType.DECISION and
            m.quality_score and m.quality_score < 0.5
        ]
        
        if not failures:
            return patterns
        
        # Group by agent
        agent_failures = {}
        for failure in failures:
            agent = failure.agent_name
            if agent not in agent_failures:
                agent_failures[agent] = []
            agent_failures[agent].append(failure)
        
        # Extract failure patterns
        for agent, fails in agent_failures.items():
            common_context = self._find_common_context(
                [f.context for f in fails]
            )
            
            patterns.append({
                'agent_name': agent,
                'pattern_type': 'failure',
                'failure_count': len(fails),
                'common_context': common_context,
                'sample_contexts': [f.context for f in fails[:3]]
            })
        
        return patterns
    
    def _extract_user_preferences(
        self,
        memories: List
    ) -> List[Dict[str, Any]]:
        """Extract user preferences from feedback"""
        preferences = []
        
        # Find feedback memories
        feedback_memories = [
            m for m in memories
            if m.memory_type == MemoryType.FEEDBACK
        ]
        
        if not feedback_memories:
            return preferences
        
        # Analyze positive feedback
        positive_feedback = [
            f for f in feedback_memories
            if f.quality_score and f.quality_score >= 0.7
        ]
        
        if positive_feedback:
            # Extract common elements from positive feedback
            common_elements = self._find_common_context(
                [f.context for f in positive_feedback]
            )
            
            preferences.append({
                'preference_type': 'positive',
                'feedback_count': len(positive_feedback),
                'avg_quality': sum(f.quality_score for f in positive_feedback) / len(positive_feedback),
                'common_elements': common_elements
            })
        
        # Analyze negative feedback
        negative_feedback = [
            f for f in feedback_memories
            if f.quality_score and f.quality_score < 0.5
        ]
        
        if negative_feedback:
            common_elements = self._find_common_context(
                [f.context for f in negative_feedback]
            )
            
            preferences.append({
                'preference_type': 'negative',
                'feedback_count': len(negative_feedback),
                'avg_quality': sum(f.quality_score for f in negative_feedback) / len(negative_feedback),
                'common_elements': common_elements
            })
        
        return preferences
    
    def _extract_agent_strategies(
        self,
        memories: List,
        min_quality: float
    ) -> List[Dict[str, Any]]:
        """Extract effective agent strategies"""
        strategies = []
        
        # Group decisions by agent
        agent_decisions = {}
        for memory in memories:
            if memory.memory_type == MemoryType.DECISION:
                agent = memory.agent_name
                if agent not in agent_decisions:
                    agent_decisions[agent] = []
                agent_decisions[agent].append(memory)
        
        # Analyze each agent's strategy
        for agent, decisions in agent_decisions.items():
            if not decisions:
                continue
            
            # Calculate success rate
            quality_scores = [d.quality_score for d in decisions if d.quality_score]
            if not quality_scores:
                continue
            
            avg_quality = sum(quality_scores) / len(quality_scores)
            success_rate = len([q for q in quality_scores if q >= min_quality]) / len(quality_scores)
            
            if success_rate >= 0.7:  # Agent is performing well
                strategies.append({
                    'agent_name': agent,
                    'decision_count': len(decisions),
                    'avg_quality': avg_quality,
                    'success_rate': success_rate,
                    'strategy_summary': self._summarize_strategy(decisions)
                })
        
        return strategies
    
    def _find_common_context(
        self,
        contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Find common elements across contexts"""
        if not contexts:
            return {}
        
        # Find keys that appear in all contexts
        common_keys = set(contexts[0].keys())
        for context in contexts[1:]:
            common_keys &= set(context.keys())
        
        # Extract common values
        common_context = {}
        for key in common_keys:
            values = [c.get(key) for c in contexts]
            # If all values are the same, it's a common element
            if len(set(str(v) for v in values)) == 1:
                common_context[key] = values[0]
        
        return common_context
    
    def _summarize_strategy(
        self,
        decisions: List
    ) -> Dict[str, Any]:
        """Summarize agent strategy from decisions"""
        return {
            'total_decisions': len(decisions),
            'decision_types': list(set(
                d.context.get('action', 'unknown') for d in decisions
            )),
            'avg_quality': sum(
                d.quality_score for d in decisions if d.quality_score
            ) / len([d for d in decisions if d.quality_score]) if any(d.quality_score for d in decisions) else 0
        }
    
    def _store_pattern(
        self,
        user_id: str,
        episode_id: str,
        pattern: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Store success pattern in semantic memory"""
        knowledge_key = f"pattern_{pattern['agent_name']}_{pattern['pattern_type']}"
        
        existing = self.semantic.get_memory_by_key(user_id, knowledge_key)
        
        if existing:
            # Update existing pattern
            current_value = existing.knowledge_value
            current_value['episodes'] = current_value.get('episodes', [])
            current_value['episodes'].append(episode_id)
            current_value['total_occurrences'] = current_value.get('total_occurrences', 0) + 1
            current_value['latest_pattern'] = pattern
            
            self.semantic.update_memory(
                existing.id,
                knowledge_value=current_value,
                importance_score=min(1.0, existing.importance_score + 0.1)
            )
            return {'created': False}
        else:
            # Create new pattern
            self.semantic.merge_or_create(
                user_id=user_id,
                category=KnowledgeCategory.GENERATION_PATTERN,
                knowledge_key=knowledge_key,
                knowledge_value={
                    'pattern': pattern,
                    'episodes': [episode_id],
                    'total_occurrences': 1
                },
                source_episode=episode_id,
                confidence_score=pattern['avg_quality'],
                importance_score=0.7
            )
            return {'created': True}
    
    def _store_failure_pattern(
        self,
        user_id: str,
        episode_id: str,
        pattern: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Store failure pattern to avoid"""
        knowledge_key = f"failure_{pattern['agent_name']}"
        
        existing = self.semantic.get_memory_by_key(user_id, knowledge_key)
        
        if existing:
            current_value = existing.knowledge_value
            current_value['failures'] = current_value.get('failures', [])
            current_value['failures'].append({
                'episode_id': episode_id,
                'pattern': pattern
            })
            
            self.semantic.update_memory(
                existing.id,
                knowledge_value=current_value
            )
            return {'created': False}
        else:
            self.semantic.merge_or_create(
                user_id=user_id,
                category=KnowledgeCategory.FEEDBACK_INSIGHT,
                knowledge_key=knowledge_key,
                knowledge_value={
                    'failures': [{
                        'episode_id': episode_id,
                        'pattern': pattern
                    }]
                },
                source_episode=episode_id,
                confidence_score=0.8,
                importance_score=0.8
            )
            return {'created': True}
    
    def _store_user_preference(
        self,
        user_id: str,
        episode_id: str,
        preference: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Store user preference"""
        knowledge_key = f"preference_{preference['preference_type']}"
        
        existing = self.semantic.get_memory_by_key(user_id, knowledge_key)
        
        if existing:
            current_value = existing.knowledge_value
            current_value['feedback_count'] = current_value.get('feedback_count', 0) + preference['feedback_count']
            current_value['episodes'] = current_value.get('episodes', [])
            current_value['episodes'].append(episode_id)
            current_value['latest_elements'] = preference['common_elements']
            
            self.semantic.update_memory(
                existing.id,
                knowledge_value=current_value,
                confidence_score=min(1.0, existing.confidence_score + 0.05)
            )
            return {'created': False}
        else:
            self.semantic.merge_or_create(
                user_id=user_id,
                category=KnowledgeCategory.USER_PREFERENCE,
                knowledge_key=knowledge_key,
                knowledge_value=preference,
                source_episode=episode_id,
                confidence_score=0.7,
                importance_score=0.9
            )
            return {'created': True}
    
    def _store_agent_strategy(
        self,
        user_id: str,
        episode_id: str,
        strategy: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Store effective agent strategy"""
        knowledge_key = f"strategy_{strategy['agent_name']}"
        
        existing = self.semantic.get_memory_by_key(user_id, knowledge_key)
        
        if existing:
            current_value = existing.knowledge_value
            current_value['episodes'] = current_value.get('episodes', [])
            current_value['episodes'].append(episode_id)
            current_value['total_decisions'] = current_value.get('total_decisions', 0) + strategy['decision_count']
            current_value['latest_strategy'] = strategy
            
            # Update success rate (weighted average)
            old_rate = current_value.get('success_rate', 0.5)
            new_rate = (old_rate * 0.7 + strategy['success_rate'] * 0.3)
            current_value['success_rate'] = new_rate
            
            self.semantic.update_memory(
                existing.id,
                knowledge_value=current_value,
                confidence_score=new_rate
            )
            return {'created': False}
        else:
            self.semantic.merge_or_create(
                user_id=user_id,
                category=KnowledgeCategory.AGENT_BEHAVIOR,
                knowledge_key=knowledge_key,
                knowledge_value=strategy,
                source_episode=episode_id,
                confidence_score=strategy['success_rate'],
                importance_score=0.8
            )
            return {'created': True}
    
    def _log_consolidation(
        self,
        episode_id: str,
        consolidation_type: str,
        insights_extracted: int,
        patterns_identified: int,
        memories_created: int,
        memories_updated: int,
        memories_pruned: int,
        processing_time_ms: int
    ):
        """Log consolidation to database"""
        log = MemoryConsolidation(
            id=str(uuid.uuid4()),
            episode_id=episode_id,
            consolidation_type=consolidation_type,
            insights_extracted=insights_extracted,
            patterns_identified=patterns_identified,
            memories_created=memories_created,
            memories_updated=memories_updated,
            memories_pruned=memories_pruned,
            processing_time_ms=processing_time_ms,
            created_at=datetime.utcnow()
        )
        
        self.db.add(log)
        self.db.commit()
    
    def get_consolidation_history(
        self,
        episode_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get consolidation history"""
        query = self.db.query(MemoryConsolidation)
        
        if episode_id:
            query = query.filter(MemoryConsolidation.episode_id == episode_id)
        
        logs = query.order_by(
            MemoryConsolidation.created_at.desc()
        ).limit(limit).all()
        
        return [log.to_dict() for log in logs]