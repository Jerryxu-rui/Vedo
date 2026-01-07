"""
Segment Generation Service
Handles step-by-step video segment generation with preview capabilities
"""

import os
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime
import asyncio
import hashlib
from database_models import VideoSegment, Episode, Scene, Shot
from sqlalchemy.orm import Session
from pipelines.script2video_pipeline import Script2VideoPipeline

logger = logging.getLogger(__name__)


class SegmentGenerationService:
    """Service for generating video segments one at a time"""
    
    def __init__(
        self,
        chat_model,
        image_generator,
        video_generator,
        working_dir: str,
        db_session: Session
    ):
        self.chat_model = chat_model
        self.image_generator = image_generator
        self.video_generator = video_generator
        self.working_dir = working_dir
        self.db = db_session
        
        os.makedirs(self.working_dir, exist_ok=True)
        logger.info(f"SegmentGenerationService initialized with working_dir: {working_dir}")
    
    async def generate_segment(
        self,
        episode_id: str,
        segment_number: int,
        scene_script: Dict,
        generation_params: Dict,
        progress_callback: Optional[Callable] = None
    ) -> VideoSegment:
        """
        Generate a single video segment
        
        Args:
            episode_id: Episode ID
            segment_number: Segment number in sequence
            scene_script: Scene script data
            generation_params: Generation parameters (style, seed, etc.)
            progress_callback: Optional callback for progress updates
            
        Returns:
            VideoSegment: Generated segment with metadata
        """
        logger.info(f"Starting segment generation: episode={episode_id}, segment={segment_number}")
        
        try:
            # Create segment record
            segment = VideoSegment(
                episode_id=episode_id,
                segment_number=segment_number,
                segment_type='scene',
                generation_params=generation_params,
                status='generating'
            )
            self.db.add(segment)
            self.db.commit()
            self.db.refresh(segment)
            
            if progress_callback:
                await progress_callback(segment.id, 'generating', 0, "Starting segment generation...")
            
            # Create segment working directory
            segment_dir = os.path.join(self.working_dir, f"segment_{segment_number}")
            os.makedirs(segment_dir, exist_ok=True)
            
            # Initialize Script2Video pipeline for this segment
            pipeline = Script2VideoPipeline(
                chat_model=self.chat_model,
                image_generator=self.image_generator,
                video_generator=self.video_generator,
                working_dir=segment_dir
            )
            
            if progress_callback:
                await progress_callback(segment.id, 'generating', 20, "Generating scene video...")
            
            # Generate video for this scene
            video_path = await pipeline(
                script=scene_script,
                user_requirement=generation_params.get('user_requirement', ''),
                style=generation_params.get('style', '写实电影感'),
                characters=generation_params.get('characters', []),
                character_portraits_registry=generation_params.get('character_portraits_registry', {})
            )
            
            if progress_callback:
                await progress_callback(segment.id, 'generating', 80, "Generating thumbnail...")
            
            # Generate thumbnail
            thumbnail_path = await self._generate_thumbnail(video_path, segment_dir)
            
            # Get video metadata
            duration, file_size, resolution = await self._get_video_metadata(video_path)
            
            # Update segment with results
            segment.video_url = video_path
            segment.thumbnail_url = thumbnail_path
            segment.duration = duration
            segment.file_size = file_size
            segment.resolution = resolution
            segment.format = 'mp4'
            segment.status = 'completed'
            segment.quality_score = await self._calculate_quality_score(video_path)
            
            self.db.commit()
            self.db.refresh(segment)
            
            if progress_callback:
                await progress_callback(segment.id, 'completed', 100, "Segment generation completed!")
            
            logger.info(f"Segment {segment_number} generated successfully: {video_path}")
            return segment
            
        except Exception as e:
            logger.error(f"Error generating segment {segment_number}: {e}", exc_info=True)
            
            # Update segment status to failed
            if 'segment' in locals():
                segment.status = 'failed'
                segment.rejection_reason = str(e)
                self.db.commit()
            
            if progress_callback:
                await progress_callback(
                    segment.id if 'segment' in locals() else None,
                    'failed',
                    0,
                    f"Generation failed: {str(e)}"
                )
            
            raise
    
    async def generate_segments_sequential(
        self,
        episode_id: str,
        scene_scripts: List[Dict],
        generation_params: Dict,
        progress_callback: Optional[Callable] = None,
        start_from: int = 0
    ) -> List[VideoSegment]:
        """
        Generate segments one by one in sequence
        
        Args:
            episode_id: Episode ID
            scene_scripts: List of scene scripts
            generation_params: Generation parameters
            progress_callback: Optional callback for progress updates
            start_from: Start from specific segment number (for resume)
            
        Returns:
            List[VideoSegment]: List of generated segments
        """
        logger.info(f"Starting sequential generation: {len(scene_scripts)} segments, start_from={start_from}")
        
        segments = []
        total_segments = len(scene_scripts)
        
        for idx, scene_script in enumerate(scene_scripts[start_from:], start=start_from):
            try:
                logger.info(f"Generating segment {idx + 1}/{total_segments}")
                
                # Generate segment
                segment = await self.generate_segment(
                    episode_id=episode_id,
                    segment_number=idx,
                    scene_script=scene_script,
                    generation_params=generation_params,
                    progress_callback=progress_callback
                )
                
                segments.append(segment)
                
                # Notify overall progress
                if progress_callback:
                    overall_progress = ((idx + 1) / total_segments) * 100
                    await progress_callback(
                        None,
                        'in_progress',
                        overall_progress,
                        f"Completed {idx + 1}/{total_segments} segments"
                    )
                
            except Exception as e:
                logger.error(f"Failed to generate segment {idx}: {e}")
                # Continue with next segment or stop based on configuration
                if generation_params.get('stop_on_error', False):
                    raise
                continue
        
        logger.info(f"Sequential generation completed: {len(segments)} segments generated")
        return segments
    
    async def regenerate_segment(
        self,
        segment_id: str,
        changes: Dict,
        progress_callback: Optional[Callable] = None
    ) -> VideoSegment:
        """
        Regenerate a specific segment with modifications
        
        Args:
            segment_id: Segment ID to regenerate
            changes: Dictionary of changes to apply
            progress_callback: Optional callback for progress updates
            
        Returns:
            VideoSegment: New segment version
        """
        logger.info(f"Regenerating segment: {segment_id}")
        
        # Get original segment
        original_segment = self.db.query(VideoSegment).filter(
            VideoSegment.id == segment_id
        ).first()
        
        if not original_segment:
            raise ValueError(f"Segment not found: {segment_id}")
        
        # Create new version
        new_version = original_segment.version + 1
        
        # Merge changes with original params
        generation_params = original_segment.generation_params.copy()
        generation_params.update(changes.get('generation_params', {}))
        
        # Update seed for variation if not explicitly provided
        if 'seed' not in changes.get('generation_params', {}):
            import random
            generation_params['seed'] = random.randint(0, 999999)
        
        # Get scene script (reconstruct from original or use provided)
        scene_script = changes.get('scene_script') or self._reconstruct_scene_script(original_segment)
        
        # Generate new segment
        new_segment = await self.generate_segment(
            episode_id=original_segment.episode_id,
            segment_number=original_segment.segment_number,
            scene_script=scene_script,
            generation_params=generation_params,
            progress_callback=progress_callback
        )
        
        # Update versioning
        new_segment.version = new_version
        new_segment.parent_segment_id = segment_id
        self.db.commit()
        
        logger.info(f"Segment regenerated: {segment_id} -> {new_segment.id} (v{new_version})")
        return new_segment
    
    async def _generate_thumbnail(self, video_path: str, output_dir: str) -> str:
        """Generate thumbnail from video"""
        try:
            from moviepy import VideoFileClip
            import numpy as np
            from PIL import Image
            
            thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")
            
            # Extract frame at 1 second or middle of video
            with VideoFileClip(video_path) as clip:
                frame_time = min(1.0, clip.duration / 2)
                frame = clip.get_frame(frame_time)
                
                # Convert to PIL Image and save
                img = Image.fromarray(frame.astype('uint8'))
                img.thumbnail((320, 180))  # Resize to thumbnail size
                img.save(thumbnail_path, 'JPEG', quality=85)
            
            return thumbnail_path
            
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
            return None
    
    async def _get_video_metadata(self, video_path: str) -> tuple:
        """Get video metadata (duration, file_size, resolution)"""
        try:
            from moviepy import VideoFileClip
            
            with VideoFileClip(video_path) as clip:
                duration = clip.duration
                resolution = f"{clip.w}x{clip.h}"
            
            file_size = os.path.getsize(video_path)
            
            return duration, file_size, resolution
            
        except Exception as e:
            logger.warning(f"Failed to get video metadata: {e}")
            return None, None, None
    
    async def _calculate_quality_score(self, video_path: str) -> float:
        """
        Calculate quality score for video
        This is a placeholder - can be enhanced with actual quality metrics
        """
        try:
            # Basic quality score based on file size and duration
            duration, file_size, resolution = await self._get_video_metadata(video_path)
            
            if not duration or not file_size:
                return 0.5
            
            # Simple heuristic: bitrate-based quality
            bitrate = (file_size * 8) / duration / 1000  # kbps
            
            # Normalize to 0-1 scale (assuming 500-5000 kbps range)
            quality = min(max((bitrate - 500) / 4500, 0), 1)
            
            return round(quality, 2)
            
        except Exception as e:
            logger.warning(f"Failed to calculate quality score: {e}")
            return 0.5
    
    def _reconstruct_scene_script(self, segment: VideoSegment) -> Dict:
        """Reconstruct scene script from segment data"""
        # This is a placeholder - implement based on your scene script structure
        return segment.generation_params.get('scene_script', {})
    
    def get_segment_status(self, episode_id: str) -> Dict:
        """
        Get status of all segments for an episode
        
        Returns:
            Dict with segment statistics and list
        """
        segments = self.db.query(VideoSegment).filter(
            VideoSegment.episode_id == episode_id
        ).order_by(VideoSegment.segment_number).all()
        
        total = len(segments)
        completed = sum(1 for s in segments if s.status == 'completed')
        approved = sum(1 for s in segments if s.approval_status == 'approved')
        rejected = sum(1 for s in segments if s.approval_status == 'rejected')
        pending = total - completed
        
        return {
            'total_segments': total,
            'completed': completed,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'segments': [s.to_dict() for s in segments]
        }