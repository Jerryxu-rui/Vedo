"""
API Routes for Video Segment Review and Approval
Handles user review, approval, and rejection of video segments
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database import get_db
from database_models import VideoSegment, SegmentReview
from services.segment_review_service import SegmentReviewService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/segment-review", tags=["segment-review"])


# Request/Response Models
class ApproveSegmentRequest(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1-5 stars")
    feedback: Optional[str] = None


class RejectSegmentRequest(BaseModel):
    reason: str = Field(..., description="Reason for rejection")
    suggested_changes: Optional[Dict[str, Any]] = Field(default_factory=dict)


class RequestRegenerationRequest(BaseModel):
    changes: Dict[str, Any] = Field(..., description="Changes to apply for regeneration")
    feedback: Optional[str] = None


class BulkApproveRequest(BaseModel):
    segment_ids: List[str] = Field(..., description="List of segment IDs to approve")
    feedback: Optional[str] = None


class AddNotesRequest(BaseModel):
    notes: str = Field(..., description="Notes to add to segment")


class CompareSegmentsRequest(BaseModel):
    segment_id_1: str
    segment_id_2: str


class ReviewResponse(BaseModel):
    id: str
    segment_id: str
    user_id: str
    action: str
    rating: Optional[int]
    feedback: Optional[str]
    suggested_changes: Dict[str, Any]
    created_at: str
    
    class Config:
        from_attributes = True


class SegmentWithReviewsResponse(BaseModel):
    id: str
    episode_id: str
    segment_number: int
    status: str
    approval_status: Optional[str]
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    duration: Optional[float]
    quality_score: Optional[float]
    reviews: List[Dict[str, Any]]
    review_count: int
    average_rating: Optional[float]


# Helper function to get service
def get_review_service(db: Session = Depends(get_db)) -> SegmentReviewService:
    """Get segment review service instance"""
    return SegmentReviewService(db)


# Endpoints

@router.post("/{segment_id}/approve")
async def approve_segment(
    segment_id: str,
    request: ApproveSegmentRequest,
    user_id: str = "default_user",  # TODO: Get from auth
    service: SegmentReviewService = Depends(get_review_service)
):
    """
    Approve a video segment
    
    - **segment_id**: Segment ID to approve
    - **rating**: Optional rating (1-5 stars)
    - **feedback**: Optional feedback text
    """
    try:
        logger.info(f"Approving segment: {segment_id} by user: {user_id}")
        
        segment = service.approve_segment(
            segment_id=segment_id,
            user_id=user_id,
            rating=request.rating,
            feedback=request.feedback
        )
        
        return {
            "status": "approved",
            "segment_id": segment.id,
            "approval_status": segment.approval_status,
            "approved_at": segment.approved_at.isoformat() if segment.approved_at else None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to approve segment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{segment_id}/reject")
async def reject_segment(
    segment_id: str,
    request: RejectSegmentRequest,
    user_id: str = "default_user",  # TODO: Get from auth
    service: SegmentReviewService = Depends(get_review_service)
):
    """
    Reject a video segment
    
    - **segment_id**: Segment ID to reject
    - **reason**: Reason for rejection
    - **suggested_changes**: Optional suggestions for improvement
    """
    try:
        logger.info(f"Rejecting segment: {segment_id} by user: {user_id}")
        
        segment = service.reject_segment(
            segment_id=segment_id,
            user_id=user_id,
            reason=request.reason,
            suggested_changes=request.suggested_changes
        )
        
        return {
            "status": "rejected",
            "segment_id": segment.id,
            "approval_status": segment.approval_status,
            "rejection_reason": segment.rejection_reason
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reject segment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{segment_id}/request-regeneration")
async def request_regeneration(
    segment_id: str,
    request: RequestRegenerationRequest,
    user_id: str = "default_user",  # TODO: Get from auth
    service: SegmentReviewService = Depends(get_review_service)
):
    """
    Request regeneration of a segment with specific changes
    
    - **segment_id**: Segment ID to regenerate
    - **changes**: Dictionary of changes to apply
    - **feedback**: Optional feedback text
    """
    try:
        logger.info(f"Requesting regeneration for segment: {segment_id}")
        
        result = service.request_regeneration(
            segment_id=segment_id,
            user_id=user_id,
            changes=request.changes,
            feedback=request.feedback
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to request regeneration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{segment_id}/reviews", response_model=List[ReviewResponse])
async def get_segment_reviews(
    segment_id: str,
    service: SegmentReviewService = Depends(get_review_service)
):
    """Get all reviews for a segment"""
    try:
        reviews = service.get_segment_reviews(segment_id)
        return [ReviewResponse(**review) for review in reviews]
        
    except Exception as e:
        logger.error(f"Failed to get segment reviews: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{segment_id}/with-reviews", response_model=SegmentWithReviewsResponse)
async def get_segment_with_reviews(
    segment_id: str,
    service: SegmentReviewService = Depends(get_review_service)
):
    """Get segment with all its reviews"""
    try:
        segment_data = service.get_segment_with_reviews(segment_id)
        return SegmentWithReviewsResponse(**segment_data)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get segment with reviews: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_segments(
    request: CompareSegmentsRequest,
    service: SegmentReviewService = Depends(get_review_service)
):
    """
    Compare two segments (useful for comparing versions)
    
    - **segment_id_1**: First segment ID
    - **segment_id_2**: Second segment ID
    """
    try:
        comparison = service.compare_segments(
            segment_id_1=request.segment_id_1,
            segment_id_2=request.segment_id_2
        )
        
        return comparison
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to compare segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/statistics")
async def get_approval_statistics(
    episode_id: str,
    service: SegmentReviewService = Depends(get_review_service)
):
    """
    Get approval statistics for an episode
    
    Returns:
    - Total segments
    - Approved/rejected/pending counts
    - Approval/rejection rates
    - Average rating and quality scores
    """
    try:
        stats = service.get_approval_statistics(episode_id)
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get approval statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-approve")
async def bulk_approve_segments(
    request: BulkApproveRequest,
    user_id: str = "default_user",  # TODO: Get from auth
    service: SegmentReviewService = Depends(get_review_service)
):
    """
    Approve multiple segments at once
    
    - **segment_ids**: List of segment IDs to approve
    - **feedback**: Optional feedback for all segments
    """
    try:
        logger.info(f"Bulk approving {len(request.segment_ids)} segments")
        
        approved_segments = service.bulk_approve_segments(
            segment_ids=request.segment_ids,
            user_id=user_id,
            feedback=request.feedback
        )
        
        return {
            "status": "completed",
            "total_requested": len(request.segment_ids),
            "total_approved": len(approved_segments),
            "approved_segment_ids": [s.id for s in approved_segments]
        }
        
    except Exception as e:
        logger.error(f"Failed to bulk approve segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{segment_id}/notes")
async def add_user_notes(
    segment_id: str,
    request: AddNotesRequest,
    user_id: str = "default_user",  # TODO: Get from auth
    service: SegmentReviewService = Depends(get_review_service)
):
    """
    Add user notes to a segment without changing approval status
    
    - **segment_id**: Segment ID
    - **notes**: Notes text
    """
    try:
        segment = service.add_user_notes(
            segment_id=segment_id,
            user_id=user_id,
            notes=request.notes
        )
        
        return {
            "status": "notes_added",
            "segment_id": segment.id,
            "user_notes": segment.user_notes
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add user notes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/pending")
async def get_pending_reviews(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """Get all segments pending review for an episode"""
    try:
        segments = db.query(VideoSegment).filter(
            VideoSegment.episode_id == episode_id,
            VideoSegment.status == 'completed',
            VideoSegment.approval_status.is_(None)
        ).order_by(VideoSegment.segment_number).all()
        
        return {
            "episode_id": episode_id,
            "pending_count": len(segments),
            "segments": [s.to_dict() for s in segments]
        }
        
    except Exception as e:
        logger.error(f"Failed to get pending reviews: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/approved")
async def get_approved_segments(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """Get all approved segments for an episode"""
    try:
        segments = db.query(VideoSegment).filter(
            VideoSegment.episode_id == episode_id,
            VideoSegment.approval_status == 'approved'
        ).order_by(VideoSegment.segment_number).all()
        
        return {
            "episode_id": episode_id,
            "approved_count": len(segments),
            "segments": [s.to_dict() for s in segments]
        }
        
    except Exception as e:
        logger.error(f"Failed to get approved segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/rejected")
async def get_rejected_segments(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """Get all rejected segments for an episode"""
    try:
        segments = db.query(VideoSegment).filter(
            VideoSegment.episode_id == episode_id,
            VideoSegment.approval_status == 'rejected'
        ).order_by(VideoSegment.segment_number).all()
        
        return {
            "episode_id": episode_id,
            "rejected_count": len(segments),
            "segments": [s.to_dict() for s in segments]
        }
        
    except Exception as e:
        logger.error(f"Failed to get rejected segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))