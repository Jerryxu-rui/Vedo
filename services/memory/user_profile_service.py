"""
User Profile Service
Manages user memory profiles for personalization
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from database_models import UserMemoryProfile
from services.memory.memory_types import (
    UserMemoryProfileData,
)
import uuid


class UserProfileService:
    """Service for managing user memory profiles"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_profile(
        self,
        user_id: str,
        preferences: Optional[Dict[str, Any]] = None,
        style_patterns: Optional[Dict[str, Any]] = None,
        feedback_history: Optional[Dict[str, Any]] = None
    ) -> UserMemoryProfileData:
        """
        Create a new user profile
        
        Args:
            user_id: User ID
            preferences: User preferences (stored in generation_preferences)
            style_patterns: Style patterns (stored in preferred_styles)
            feedback_history: Feedback history (stored in feedback_patterns)
        
        Returns:
            Created profile data
        """
        profile = UserMemoryProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            preferred_styles=style_patterns.get('styles', []) if style_patterns else [],
            preferred_genres=preferences.get('genres', []) if preferences else [],
            common_themes=[],
            generation_preferences=preferences or {},
            feedback_patterns=feedback_history or {},
            total_episodes=0,
            avg_quality_score=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        return self._to_data(profile)
    
    def get_profile(self, user_id: str) -> Optional[UserMemoryProfileData]:
        """
        Get user profile by user ID
        
        Args:
            user_id: User ID
        
        Returns:
            Profile data or None if not found
        """
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        return self._to_data(profile) if profile else None
    
    def get_or_create_profile(self, user_id: str) -> UserMemoryProfileData:
        """
        Get existing profile or create new one
        
        Args:
            user_id: User ID
        
        Returns:
            Profile data
        """
        profile = self.get_profile(user_id)
        
        if profile:
            return profile
        
        return self.create_profile(user_id)
    
    def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        merge: bool = True
    ) -> Optional[UserMemoryProfileData]:
        """
        Update user preferences
        
        Args:
            user_id: User ID
            preferences: New preferences
            merge: If True, merge with existing preferences; if False, replace
        
        Returns:
            Updated profile data or None if not found
        """
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not profile:
            return None
        
        if merge:
            current_prefs = profile.generation_preferences or {}
            current_prefs.update(preferences)
            profile.generation_preferences = current_prefs
        else:
            profile.generation_preferences = preferences
        
        profile.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(profile)
        
        return self._to_data(profile)
    
    def update_style_patterns(
        self,
        user_id: str,
        style_patterns: Dict[str, Any],
        merge: bool = True
    ) -> Optional[UserMemoryProfileData]:
        """
        Update user style patterns
        
        Args:
            user_id: User ID
            style_patterns: New style patterns (stored in preferred_styles)
            merge: If True, merge with existing patterns; if False, replace
        
        Returns:
            Updated profile data or None if not found
        """
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not profile:
            return None
        
        if 'styles' in style_patterns:
            if merge:
                current_styles = profile.preferred_styles or []
                new_styles = style_patterns['styles']
                # Merge unique styles
                profile.preferred_styles = list(set(current_styles + new_styles))
            else:
                profile.preferred_styles = style_patterns['styles']
        
        profile.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(profile)
        
        return self._to_data(profile)
    
    def add_feedback(
        self,
        user_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any]
    ) -> Optional[UserMemoryProfileData]:
        """
        Add feedback to user's feedback history
        
        Args:
            user_id: User ID
            feedback_type: Type of feedback (e.g., 'positive', 'negative', 'neutral')
            feedback_data: Feedback data
        
        Returns:
            Updated profile data or None if not found
        """
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not profile:
            return None
        
        feedback_patterns = profile.feedback_patterns or {}
        
        # Initialize feedback type list if not exists
        if feedback_type not in feedback_patterns:
            feedback_patterns[feedback_type] = []
        
        # Add timestamp to feedback
        feedback_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            **feedback_data
        }
        
        feedback_patterns[feedback_type].append(feedback_entry)
        
        # Keep only last 100 feedback entries per type
        if len(feedback_patterns[feedback_type]) > 100:
            feedback_patterns[feedback_type] = feedback_patterns[feedback_type][-100:]
        
        profile.feedback_patterns = feedback_patterns
        profile.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(profile)
        
        return self._to_data(profile)
    
    def get_preference(
        self,
        user_id: str,
        preference_key: str,
        default: Any = None
    ) -> Any:
        """
        Get a specific preference value
        
        Args:
            user_id: User ID
            preference_key: Preference key
            default: Default value if not found
        
        Returns:
            Preference value or default
        """
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not profile or not profile.generation_preferences:
            return default
        
        return profile.generation_preferences.get(preference_key, default)
    
    def get_style_pattern(
        self,
        user_id: str,
        pattern_key: str,
        default: Any = None
    ) -> Any:
        """
        Get a specific style pattern
        
        Args:
            user_id: User ID
            pattern_key: Pattern key (e.g., 'styles')
            default: Default value if not found
        
        Returns:
            Pattern value or default
        """
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not profile:
            return default
        
        if pattern_key == 'styles':
            return profile.preferred_styles or default
        
        return default
    
    def get_feedback_summary(
        self,
        user_id: str,
        feedback_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary of user feedback
        
        Args:
            user_id: User ID
            feedback_type: Optional filter by feedback type
        
        Returns:
            Feedback summary
        """
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not profile or not profile.feedback_patterns:
            return {
                'total_count': 0,
                'by_type': {},
                'recent_feedback': []
            }
        
        feedback_patterns = profile.feedback_patterns
        
        if feedback_type:
            feedback_list = feedback_patterns.get(feedback_type, [])
            return {
                'total_count': len(feedback_list),
                'by_type': {feedback_type: len(feedback_list)},
                'recent_feedback': feedback_list[-10:]  # Last 10
            }
        
        # All feedback types
        total_count = sum(len(items) for items in feedback_patterns.values())
        by_type = {k: len(v) for k, v in feedback_patterns.items()}
        
        # Get recent feedback from all types
        all_feedback = []
        for feedback_type, items in feedback_patterns.items():
            for item in items:
                all_feedback.append({
                    'type': feedback_type,
                    **item
                })
        
        # Sort by timestamp and get last 10
        all_feedback.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        recent_feedback = all_feedback[:10]
        
        return {
            'total_count': total_count,
            'by_type': by_type,
            'recent_feedback': recent_feedback
        }
    
    def delete_profile(self, user_id: str) -> bool:
        """
        Delete user profile
        
        Args:
            user_id: User ID
        
        Returns:
            True if deleted, False if not found
        """
        profile = self.db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
        
        if not profile:
            return False
        
        self.db.delete(profile)
        self.db.commit()
        
        return True
    
    def list_all_profiles(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserMemoryProfileData]:
        """
        List all user profiles
        
        Args:
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
        
        Returns:
            List of profile data
        """
        profiles = self.db.query(UserMemoryProfile).order_by(
            UserMemoryProfile.updated_at.desc()
        ).limit(limit).offset(offset).all()
        
        return [self._to_data(p) for p in profiles]
    
    def _to_data(self, profile: UserMemoryProfile) -> UserMemoryProfileData:
        """Convert database model to data class"""
        return UserMemoryProfileData(
            id=profile.id,
            user_id=profile.user_id,
            preferences=profile.generation_preferences or {},
            style_patterns={'styles': profile.preferred_styles or []},
            feedback_history=profile.feedback_patterns or {},
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )