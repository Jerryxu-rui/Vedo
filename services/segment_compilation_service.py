"""
Segment Compilation Service
Handles compilation of approved video segments into final video
"""

import os
import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime
import asyncio
from database_models import VideoSegment, SegmentCompilationJob, Episode
from sqlalchemy.orm import Session
from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.fx.FadeIn import FadeIn
from moviepy.video.fx.FadeOut import FadeOut

logger = logging.getLogger(__name__)


class SegmentCompilationService:
    """Service for compiling approved video segments into final video"""
    
    def __init__(self, db_session: Session, output_dir: str):
        self.db = db_session
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"SegmentCompilationService initialized with output_dir: {output_dir}")
    
    async def compile_segments(
        self,
        episode_id: str,
        segment_ids: Optional[List[str]] = None,
        transition_style: str = 'cut',
        audio_config: Optional[Dict] = None,
        progress_callback: Optional[Callable] = None
    ) -> SegmentCompilationJob:
        """
        Compile approved segments into final video
        
        Args:
            episode_id: Episode ID
            segment_ids: Optional list of segment IDs (if None, uses all approved segments)
            transition_style: Transition style ('cut', 'fade', 'dissolve')
            audio_config: Audio configuration
            progress_callback: Optional callback for progress updates
            
        Returns:
            SegmentCompilationJob: Compilation job with results
        """
        logger.info(f"Starting compilation for episode: {episode_id}")
        
        try:
            # Create compilation job
            job = SegmentCompilationJob(
                episode_id=episode_id,
                segment_ids=segment_ids or [],
                transition_style=transition_style,
                audio_config=audio_config or {},
                status='processing',
                progress=0.0
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            
            if progress_callback:
                await progress_callback(job.id, 'processing', 0, "Starting compilation...")
            
            # Get segments to compile
            if segment_ids:
                segments = self.db.query(VideoSegment).filter(
                    VideoSegment.id.in_(segment_ids)
                ).order_by(VideoSegment.segment_number).all()
            else:
                # Get all approved segments
                segments = self.db.query(VideoSegment).filter(
                    VideoSegment.episode_id == episode_id,
                    VideoSegment.approval_status == 'approved'
                ).order_by(VideoSegment.segment_number).all()
            
            if not segments:
                raise ValueError("No segments found for compilation")
            
            logger.info(f"Compiling {len(segments)} segments")
            
            # Update job with segment IDs
            job.segment_ids = [s.id for s in segments]
            self.db.commit()
            
            if progress_callback:
                await progress_callback(job.id, 'processing', 10, f"Loading {len(segments)} segments...")
            
            # Load video clips
            clips = []
            for idx, segment in enumerate(segments):
                if not segment.video_url or not os.path.exists(segment.video_url):
                    logger.warning(f"Segment {segment.id} video not found: {segment.video_url}")
                    continue
                
                try:
                    clip = VideoFileClip(segment.video_url)
                    clips.append(clip)
                    
                    progress = 10 + (idx / len(segments)) * 30
                    if progress_callback:
                        await progress_callback(
                            job.id,
                            'processing',
                            progress,
                            f"Loaded segment {idx + 1}/{len(segments)}"
                        )
                except Exception as e:
                    logger.error(f"Failed to load segment {segment.id}: {e}")
                    continue
            
            if not clips:
                raise ValueError("No valid video clips found")
            
            if progress_callback:
                await progress_callback(job.id, 'processing', 40, "Applying transitions...")
            
            # Apply transitions
            processed_clips = await self._apply_transitions(
                clips,
                transition_style,
                progress_callback,
                job.id
            )
            
            if progress_callback:
                await progress_callback(job.id, 'processing', 70, "Concatenating videos...")
            
            # Concatenate clips
            final_clip = concatenate_videoclips(processed_clips, method='compose')
            
            if progress_callback:
                await progress_callback(job.id, 'processing', 80, "Processing audio...")
            
            # Apply audio configuration
            if audio_config:
                final_clip = await self._apply_audio_config(final_clip, audio_config)
            
            # Generate output filename
            episode = self.db.query(Episode).filter(Episode.id == episode_id).first()
            episode_title = episode.title if episode else "episode"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{episode_title}_{timestamp}_final.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
            
            if progress_callback:
                await progress_callback(job.id, 'processing', 85, "Writing final video...")
            
            # Write final video
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                fps=24
            )
            
            # Get output metadata
            output_duration = final_clip.duration
            output_file_size = os.path.getsize(output_path)
            
            # Close clips
            for clip in clips:
                clip.close()
            final_clip.close()
            
            # Update job
            job.status = 'completed'
            job.progress = 100.0
            job.output_video_url = output_path
            job.output_duration = output_duration
            job.output_file_size = output_file_size
            job.completed_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(job)
            
            if progress_callback:
                await progress_callback(job.id, 'completed', 100, "Compilation completed!")
            
            logger.info(f"Compilation completed: {output_path}")
            return job
            
        except Exception as e:
            logger.error(f"Compilation failed: {e}", exc_info=True)
            
            # Update job status
            if 'job' in locals():
                job.status = 'failed'
                job.error_message = str(e)
                self.db.commit()
            
            if progress_callback:
                await progress_callback(
                    job.id if 'job' in locals() else None,
                    'failed',
                    0,
                    f"Compilation failed: {str(e)}"
                )
            
            raise
    
    async def _apply_transitions(
        self,
        clips: List[VideoFileClip],
        transition_style: str,
        progress_callback: Optional[Callable],
        job_id: str
    ) -> List[VideoFileClip]:
        """Apply transitions between clips"""
        
        if transition_style == 'cut':
            # No transitions, just return clips as-is
            return clips
        
        elif transition_style == 'fade':
            # Apply fade in/out transitions
            transition_duration = 0.5  # seconds
            processed_clips = []
            
            for idx, clip in enumerate(clips):
                # Fade in for first clip
                if idx == 0:
                    clip = clip.fx(FadeIn, transition_duration)
                
                # Fade out for last clip
                if idx == len(clips) - 1:
                    clip = clip.fx(FadeOut, transition_duration)
                
                # Crossfade between clips (overlap)
                if idx > 0:
                    # This is a simplified version - full crossfade requires more complex logic
                    clip = clip.fx(FadeIn, transition_duration)
                
                processed_clips.append(clip)
                
                if progress_callback:
                    progress = 40 + (idx / len(clips)) * 30
                    await progress_callback(
                        job_id,
                        'processing',
                        progress,
                        f"Applied transition {idx + 1}/{len(clips)}"
                    )
            
            return processed_clips
        
        elif transition_style == 'dissolve':
            # Similar to fade but with different timing
            return await self._apply_transitions(clips, 'fade', progress_callback, job_id)
        
        else:
            logger.warning(f"Unknown transition style: {transition_style}, using 'cut'")
            return clips
    
    async def _apply_audio_config(
        self,
        clip: VideoFileClip,
        audio_config: Dict
    ) -> VideoFileClip:
        """Apply audio configuration to clip"""
        
        try:
            # Volume normalization
            if audio_config.get('volume_normalization', False):
                # Normalize audio volume
                if clip.audio:
                    target_volume = audio_config.get('target_volume', 0.8)
                    clip = clip.volumex(target_volume)
            
            # Background music
            if audio_config.get('background_music'):
                music_path = audio_config['background_music']
                if os.path.exists(music_path):
                    from moviepy import AudioFileClip
                    music = AudioFileClip(music_path)
                    
                    # Loop music if shorter than video
                    if music.duration < clip.duration:
                        music = music.loop(duration=clip.duration)
                    else:
                        music = music.subclip(0, clip.duration)
                    
                    # Mix with original audio
                    music_volume = audio_config.get('music_volume', 0.3)
                    music = music.volumex(music_volume)
                    
                    if clip.audio:
                        from moviepy.audio.AudioClip import CompositeAudioClip
                        final_audio = CompositeAudioClip([clip.audio, music])
                        clip = clip.set_audio(final_audio)
                    else:
                        clip = clip.set_audio(music)
            
            return clip
            
        except Exception as e:
            logger.warning(f"Failed to apply audio config: {e}")
            return clip
    
    def get_compilation_status(self, job_id: str) -> Dict:
        """Get compilation job status"""
        job = self.db.query(SegmentCompilationJob).filter(
            SegmentCompilationJob.id == job_id
        ).first()
        
        if not job:
            raise ValueError(f"Compilation job not found: {job_id}")
        
        return job.to_dict()
    
    def list_compilation_jobs(self, episode_id: str) -> List[Dict]:
        """List all compilation jobs for an episode"""
        jobs = self.db.query(SegmentCompilationJob).filter(
            SegmentCompilationJob.episode_id == episode_id
        ).order_by(SegmentCompilationJob.created_at.desc()).all()
        
        return [job.to_dict() for job in jobs]
    
    def cancel_compilation(self, job_id: str) -> SegmentCompilationJob:
        """Cancel a running compilation job"""
        job = self.db.query(SegmentCompilationJob).filter(
            SegmentCompilationJob.id == job_id
        ).first()
        
        if not job:
            raise ValueError(f"Compilation job not found: {job_id}")
        
        if job.status not in ['pending', 'processing']:
            raise ValueError(f"Cannot cancel job with status: {job.status}")
        
        job.status = 'cancelled'
        job.error_message = "Cancelled by user"
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Compilation job cancelled: {job_id}")
        return job
    
    def delete_compilation_output(self, job_id: str) -> bool:
        """Delete compilation output file"""
        job = self.db.query(SegmentCompilationJob).filter(
            SegmentCompilationJob.id == job_id
        ).first()
        
        if not job:
            raise ValueError(f"Compilation job not found: {job_id}")
        
        if job.output_video_url and os.path.exists(job.output_video_url):
            try:
                os.remove(job.output_video_url)
                logger.info(f"Deleted compilation output: {job.output_video_url}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete output file: {e}")
                return False
        
        return False
    
    async def recompile_with_changes(
        self,
        job_id: str,
        changes: Dict,
        progress_callback: Optional[Callable] = None
    ) -> SegmentCompilationJob:
        """
        Recompile with different settings
        
        Args:
            job_id: Original job ID
            changes: Changes to apply (transition_style, audio_config, segment_order)
            progress_callback: Optional callback for progress updates
            
        Returns:
            SegmentCompilationJob: New compilation job
        """
        # Get original job
        original_job = self.db.query(SegmentCompilationJob).filter(
            SegmentCompilationJob.id == job_id
        ).first()
        
        if not original_job:
            raise ValueError(f"Compilation job not found: {job_id}")
        
        # Apply changes
        segment_ids = changes.get('segment_ids', original_job.segment_ids)
        transition_style = changes.get('transition_style', original_job.transition_style)
        audio_config = changes.get('audio_config', original_job.audio_config)
        
        # Recompile
        new_job = await self.compile_segments(
            episode_id=original_job.episode_id,
            segment_ids=segment_ids,
            transition_style=transition_style,
            audio_config=audio_config,
            progress_callback=progress_callback
        )
        
        return new_job
    
    def get_compilation_statistics(self, episode_id: str) -> Dict:
        """Get compilation statistics for an episode"""
        jobs = self.db.query(SegmentCompilationJob).filter(
            SegmentCompilationJob.episode_id == episode_id
        ).all()
        
        total_jobs = len(jobs)
        completed = sum(1 for j in jobs if j.status == 'completed')
        failed = sum(1 for j in jobs if j.status == 'failed')
        processing = sum(1 for j in jobs if j.status == 'processing')
        
        # Calculate average compilation time
        completed_jobs = [j for j in jobs if j.status == 'completed' and j.completed_at]
        if completed_jobs:
            compilation_times = [
                (j.completed_at - j.created_at).total_seconds()
                for j in completed_jobs
            ]
            avg_compilation_time = sum(compilation_times) / len(compilation_times)
        else:
            avg_compilation_time = None
        
        # Calculate total output size
        total_output_size = sum(
            j.output_file_size for j in jobs
            if j.output_file_size
        )
        
        return {
            'total_jobs': total_jobs,
            'completed': completed,
            'failed': failed,
            'processing': processing,
            'success_rate': (completed / total_jobs * 100) if total_jobs > 0 else 0,
            'average_compilation_time_seconds': round(avg_compilation_time, 2) if avg_compilation_time else None,
            'total_output_size_bytes': total_output_size,
            'total_output_size_mb': round(total_output_size / (1024 * 1024), 2) if total_output_size else 0
        }