"""
Segment Review Service
Handles user review, approval, and rejection of video segments
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from database_models import VideoSegment, SegmentReview
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SegmentReviewService:
    """Service for reviewing and managing video segment approvals"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        logger.info("SegmentReviewService initialized")
    
    def approve_segment(
        self,
        segment_id: str,
        user_id: str,
        rating: Optional[int] = None,
        feedback: Optional[str] = None
    ) -> VideoSegment:
        """
        Approve a video segment
        
        Args:
            segment_id: Segment ID to approve
            user_id: User performing the approval
            rating: Optional rating (1-5 stars)
            feedback: Optional feedback text
            
        Returns:
            VideoSegment: Updated segment
        """
        logger.info(f"Approving segment: {segment_id} by user: {user_id}")
        
        # Get segment
        segment = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id
        ).first()
        
        if not segment:
            raise ValueError(f"Segment not found: {segment_id}")
        
        if segment.status != 'completed':
            raise ValueError(f"Cannot approve segment with status: {segment.status}")
        
        # Update segment
        segment.approval_status = 'approved'
        segment.approved_at = datetime.utcnow()
        
        # Create review record
        review = SegmentReview(
            segment_id=segment_id,
            user_id=user_id,
            action='approve',
            rating=rating,
            feedback=feedback
        )
        
        self.db.add(review)
        self.db.commit()
        self.db.refresh(segment)
        
        logger.info(f"Segment approved: {segment_id}")
        return segment
    
    def reject_segment(
        self,
        segment_id: str,
        user_id: str,
        reason: str,
        suggested_changes: Optional[Dict] = None
    ) -> VideoSegment:
        """
        Reject a video segment
        
        Args:
            segment_id: Segment ID to reject
            user_id: User performing the rejection
            reason: Reason for rejection
            suggested_changes: Optional suggestions for improvement
            
        Returns:
            VideoSegment: Updated segment
        """
        logger.info(f"Rejecting segment: {segment_id} by user: {user_id}")
        
        # Get segment
        segment = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id
        ).first()
        
        if not segment:
            raise ValueError(f"Segment not found: {segment_id}")
        
        if segment.status != 'completed':
            raise ValueError(f"Cannot reject segment with status: {segment.status}")
        
        # Update segment
        segment.approval_status = 'rejected'
        segment.rejection_reason = reason
        
        # Create review record
        review = SegmentReview(
            segment_id=segment_id,
            user_id=user_id,
            action='reject',
            feedback=reason,
            suggested_changes=suggested_changes or {}
        )
        
        self.db.add(review)
        self.db.commit()
        self.db.refresh(segment)
        
        logger.info(f"Segment rejected: {segment_id}")
        return segment
    
    def request_regeneration(
        self,
        segment_id: str,
        user_id: str,
        changes: Dict,
        feedback: Optional[str] = None
    ) -> Dict:
        """
        Request regeneration of a segment with specific changes
        
        Args:
            segment_id: Segment ID to regenerate
            user_id: User requesting regeneration
            changes: Dictionary of changes to apply
            feedback: Optional feedback text
            
        Returns:
            Dict: Regeneration request details
        """
        logger.info(f"Requesting regeneration for segment: {segment_id}")
        
        # Get segment
        segment = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id
        ).first()
        
        if not segment:
            raise ValueError(f"Segment not found: {segment_id}")
        
        # Create review record
        review = SegmentReview(
            segment_id=segment_id,
            user_id=user_id,
            action='request_regeneration',
            feedback=feedback,
            suggested_changes=changes
        )
        
        self.db.add(review)
        self.db.commit()
        
        logger.info(f"Regeneration requested for segment: {segment_id}")
        
        return {
            'segment_id': segment_id,
            'review_id': review.id,
            'changes': changes,
            'status': 'regeneration_requested'
        }
    
    def get_segment_reviews(self, segment_id: str) -> List[Dict]:
        """
        Get all reviews for a segment
        
        Args:
            segment_id: Segment ID
            
        Returns:
            List[Dict]: List of reviews
        """
        reviews = self.db.query(SegmentReview).filter(
            SegmentReview.segment_id == segment_id
        ).order_by(SegmentReview.created_at.desc()).all()
        
        return [review.to_dict() for review in reviews]
    
    def get_segment_with_reviews(self, segment_id: str) -> Dict:
        """
        Get segment with all its reviews
        
        Args:
            segment_id: Segment ID
            
        Returns:
            Dict: Segment data with reviews
        """
        segment = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id
        ).first()
        
        if not segment:
            raise ValueError(f"Segment not found: {segment_id}")
        
        reviews = self.get_segment_reviews(segment_id)
        
        segment_data = segment.to_dict()
        segment_data['reviews'] = reviews
        segment_data['review_count'] = len(reviews)
        
        # Calculate average rating
        ratings = [r['rating'] for r in reviews if r.get('rating')]
        segment_data['average_rating'] = sum(ratings) / len(ratings) if ratings else None
        
        return segment_data
    
    def get_segment_versions(self, segment_id: str) -> List[Dict]:
        """
        Get all versions of a segment (including regenerations)
        
        Args:
            segment_id: Original segment ID
            
        Returns:
            List[Dict]: List of segment versions
        """
        # Get original segment
        original = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id
        ).first()
        
        if not original:
            raise ValueError(f"Segment not found: {segment_id}")
        
        # Get all child versions
        versions = self.db.query(VideoSegment).filter(
            VideoSegment.parent_segment_id == segment_id
        ).order_by(VideoSegment.version).all()
        
        # Include original
        all_versions = [original] + versions
        
        return [v.to_dict() for v in all_versions]
    
    def compare_segments(self, segment_id_1: str, segment_id_2: str) -> Dict:
        """
        Compare two segments (useful for comparing versions)
        
        Args:
            segment_id_1: First segment ID
            segment_id_2: Second segment ID
            
        Returns:
            Dict: Comparison data
        """
        segment1 = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id_1
        ).first()
        
        segment2 = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id_2
        ).first()
        
        if not segment1 or not segment2:
            raise ValueError("One or both segments not found")
        
        return {
            'segment_1': segment1.to_dict(),
            'segment_2': segment2.to_dict(),
            'differences': {
                'duration_diff': abs(segment1.duration - segment2.duration) if segment1.duration and segment2.duration else None,
                'quality_diff': abs(segment1.quality_score - segment2.quality_score) if segment1.quality_score and segment2.quality_score else None,
                'file_size_diff': abs(segment1.file_size - segment2.file_size) if segment1.file_size and segment2.file_size else None,
                'version_diff': abs(segment1.version - segment2.version),
                'params_changed': segment1.generation_params != segment2.generation_params
            }
        }
    
    def get_approval_statistics(self, episode_id: str) -> Dict:
        """
        Get approval statistics for an episode
        
        Args:
            episode_id: Episode ID
            
        Returns:
            Dict: Approval statistics
        """
        segments = self.db.query(VideoSegment).filter(
            VideoSegment.episode_id == episode_id
        ).all()
        
        total = len(segments)
        approved = sum(1 for s in segments if s.approval_status == 'approved')
        rejected = sum(1 for s in segments if s.approval_status == 'rejected')
        pending = sum(1 for s in segments if s.approval_status is None)
        
        # Calculate average ratings
        all_reviews = []
        for segment in segments:
            reviews = self.db.query(SegmentReview).filter(
                SegmentReview.segment_id == segment.id,
                SegmentReview.rating.isnot(None)
            ).all()
            all_reviews.extend(reviews)
        
        ratings = [r.rating for r in all_reviews if r.rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Calculate quality scores
        quality_scores = [s.quality_score for s in segments if s.quality_score]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        return {
            'total_segments': total,
            'approved': approved,
            'rejected': rejected,
            'pending_review': pending,
            'approval_rate': (approved / total * 100) if total > 0 else 0,
            'rejection_rate': (rejected / total * 100) if total > 0 else 0,
            'average_rating': round(avg_rating, 2) if avg_rating else None,
            'average_quality_score': round(avg_quality, 2) if avg_quality else None,
            'total_reviews': len(all_reviews)
        }
    
    def bulk_approve_segments(
        self,
        segment_ids: List[str],
        user_id: str,
        feedback: Optional[str] = None
    ) -> List[VideoSegment]:
        """
        Approve multiple segments at once
        
        Args:
            segment_ids: List of segment IDs to approve
            user_id: User performing the approval
            feedback: Optional feedback for all segments
            
        Returns:
            List[VideoSegment]: List of approved segments
        """
        logger.info(f"Bulk approving {len(segment_ids)} segments")
        
        approved_segments = []
        
        for segment_id in segment_ids:
            try:
                segment = self.approve_segment(
                    segment_id=segment_id,
                    user_id=user_id,
                    feedback=feedback
                )
                approved_segments.append(segment)
            except Exception as e:
                logger.error(f"Failed to approve segment {segment_id}: {e}")
                continue
        
        logger.info(f"Bulk approval completed: {len(approved_segments)}/{len(segment_ids)} segments approved")
        return approved_segments
    
    def add_user_notes(
        self,
        segment_id: str,
        user_id: str,
        notes: str
    ) -> VideoSegment:
        """
        Add user notes to a segment without changing approval status
        
        Args:
            segment_id: Segment ID
            user_id: User adding notes
            notes: Notes text
            
        Returns:
            VideoSegment: Updated segment
        """
        segment = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id
        ).first()
        
        if not segment:
            raise ValueError(f"Segment not found: {segment_id}")
        
        # Append to existing notes
        if segment.user_notes:
            segment.user_notes += f"\n\n[{datetime.utcnow().isoformat()}] {user_id}: {notes}"
        else:
            segment.user_notes = f"[{datetime.utcnow().isoformat()}] {user_id}: {notes}"
        
        self.db.commit()
        self.db.refresh(segment)
        
        return segment