"""
Video Management API Routes
视频管理API路由 - 视频下载、预览和管理
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import mimetypes

from database import get_db
from database_models import Episode, Shot

router = APIRouter(prefix="/api/v1/videos", tags=["video-management"])


class VideoInfoResponse(BaseModel):
    """Video information response"""
    episode_id: str
    video_path: str
    video_url: str
    file_size: Optional[int] = None
    duration: Optional[int] = None
    status: str
    created_at: str


class ShotVideoResponse(BaseModel):
    """Shot video response"""
    shot_id: str
    shot_number: int
    video_url: Optional[str] = None
    status: str


@router.get("/episode/{episode_id}/info", response_model=VideoInfoResponse)
async def get_episode_video_info(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    Get video information for an episode
    获取集数的视频信息
    """
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        # Get video path from episode.script field (temporary storage)
        video_path = episode.script or ""
        
        if not video_path:
            raise HTTPException(status_code=404, detail="Video not found for this episode")
        
        # Convert to absolute path
        if not video_path.startswith('/'):
            video_path = os.path.join('.working_dir', video_path)
        
        # Get file info
        file_size = None
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
        
        # Convert to URL
        video_url = f"/media/{video_path.replace('.working_dir/', '')}"
        
        return VideoInfoResponse(
            episode_id=episode_id,
            video_path=video_path,
            video_url=video_url,
            file_size=file_size,
            duration=episode.duration,
            status=episode.status,
            created_at=episode.created_at.isoformat() if episode.created_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/download")
async def download_episode_video(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    Download episode video file
    下载集数视频文件
    """
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        video_path = episode.script or ""
        
        if not video_path:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Convert to absolute path - only add .working_dir if not already there
        if not video_path.startswith('/') and not video_path.startswith('.working_dir'):
            video_path = os.path.join('.working_dir', video_path)
        
        print(f"[Download] Looking for video at: {video_path}")
        
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"Video file not found on disk: {video_path}")
        
        # Determine filename
        filename = f"episode_{episode.episode_number}_{episode.title}.mp4"
        
        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/stream")
async def stream_episode_video(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    Stream episode video
    流式传输集数视频
    """
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        video_path = episode.script or ""
        
        if not video_path:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Convert to absolute path - only add .working_dir if not already there
        if not video_path.startswith('/') and not video_path.startswith('.working_dir'):
            video_path = os.path.join('.working_dir', video_path)
        
        print(f"[Stream] Looking for video at: {video_path}")
        
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"Video file not found on disk: {video_path}")
        
        def iterfile():
            with open(video_path, mode="rb") as file_like:
                yield from file_like
        
        return StreamingResponse(
            iterfile(),
            media_type="video/mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episode/{episode_id}/shots", response_model=List[ShotVideoResponse])
async def get_episode_shot_videos(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all shot videos for an episode
    获取集数的所有分镜视频
    """
    try:
        # Get all shots for the episode
        shots = db.query(Shot).join(Shot.scene).filter(
            Shot.scene.has(episode_id=episode_id)
        ).order_by(Shot.shot_number).all()
        
        shot_videos = []
        for shot in shots:
            video_url = None
            if shot.video_url:
                # Convert to web-accessible URL
                if not shot.video_url.startswith('/media/'):
                    video_url = f"/media/{shot.video_url.replace('.working_dir/', '')}"
                else:
                    video_url = shot.video_url
            
            shot_videos.append(ShotVideoResponse(
                shot_id=shot.id,
                shot_number=shot.shot_number,
                video_url=video_url,
                status=shot.status
            ))
        
        return shot_videos
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/episode/{episode_id}/video")
async def delete_episode_video(
    episode_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete episode video file
    删除集数视频文件
    """
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        
        if not episode:
            raise HTTPException(status_code=404, detail="Episode not found")
        
        video_path = episode.script or ""
        
        if not video_path:
            return {"message": "No video to delete"}
        
        # Convert to absolute path
        if not video_path.startswith('/'):
            video_path = os.path.join('.working_dir', video_path)
        
        # Delete file if exists
        if os.path.exists(video_path):
            os.remove(video_path)
        
        # Clear video path from database
        episode.script = None
        episode.status = "draft"
        db.commit()
        
        return {"message": "Video deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_video_stats(
    db: Session = Depends(get_db)
):
    """
    Get video generation statistics
    获取视频生成统计信息
    """
    try:
        # Count episodes by status
        total_episodes = db.query(Episode).count()
        completed_episodes = db.query(Episode).filter(
            Episode.status == "completed"
        ).count()
        generating_episodes = db.query(Episode).filter(
            Episode.status == "generating"
        ).count()
        failed_episodes = db.query(Episode).filter(
            Episode.status == "failed"
        ).count()
        
        # Calculate total video size
        total_size = 0
        episodes_with_video = db.query(Episode).filter(
            Episode.script.isnot(None)
        ).all()
        
        for episode in episodes_with_video:
            video_path = episode.script
            if video_path and not video_path.startswith('/'):
                video_path = os.path.join('.working_dir', video_path)
            if video_path and os.path.exists(video_path):
                total_size += os.path.getsize(video_path)
        
        return {
            "total_episodes": total_episodes,
            "completed_episodes": completed_episodes,
            "generating_episodes": generating_episodes,
            "failed_episodes": failed_episodes,
            "total_video_size_bytes": total_size,
            "total_video_size_mb": round(total_size / (1024 * 1024), 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))