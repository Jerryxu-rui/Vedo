"""
Video Generation Adapter for Conversational Workflow
视频生成适配器 - 将分镜转换为视频
"""

from typing import List, Dict, Any, Optional, Callable
import asyncio
import os
from pathlib import Path
import logging

from workflows.conversational_episode_workflow import ShotData, CharacterData, SceneData
from interfaces.video_output import VideoOutput
from utils.async_wrapper import ProgressCallback
from utils.video import concatenate_videos
from utils.error_handling import (
    ViMaxError, GenerationError, ResourceError, TimeoutError as ViMaxTimeoutError
)
from utils.error_recovery import safe_execute, with_retry

logger = logging.getLogger(__name__)


class VideoGenerationProgress:
    """Video generation progress tracker"""
    
    def __init__(self, total_shots: int):
        self.total_shots = total_shots
        self.completed_shots = 0
        self.current_shot = 0
        self.phase = "initializing"
        self.errors: List[Dict[str, Any]] = []
    
    def update_shot(self, shot_number: int, status: str, message: str = ""):
        """Update progress for a specific shot"""
        self.current_shot = shot_number
        self.phase = status
        if status == "completed":
            self.completed_shots += 1
    
    def get_progress_percentage(self) -> float:
        """Calculate overall progress percentage"""
        if self.total_shots == 0:
            return 0.0
        return (self.completed_shots / self.total_shots) * 100
    
    def add_error(self, shot_number: int, error: str):
        """Record an error for a shot"""
        self.errors.append({
            "shot_number": shot_number,
            "error": error
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_shots": self.total_shots,
            "completed_shots": self.completed_shots,
            "current_shot": self.current_shot,
            "phase": self.phase,
            "progress_percentage": self.get_progress_percentage(),
            "errors": self.errors
        }


class VideoGenerationAdapter:
    """
    Video generation adapter for conversational workflow
    Handles shot-by-shot video generation and concatenation
    """
    
    def __init__(
        self,
        video_generator,
        image_generator,
        working_dir: str = ".working_dir",
        max_concurrent_shots: int = 2
    ):
        """
        Initialize video generation adapter
        
        Args:
            video_generator: Video generator tool (e.g., VideoGeneratorVeoYunwuAPI)
            image_generator: Image generator tool for reference frames
            working_dir: Working directory for temporary files
            max_concurrent_shots: Maximum number of concurrent video generations
        """
        self.video_generator = video_generator
        self.image_generator = image_generator
        self.working_dir = working_dir
        self.max_concurrent_shots = max_concurrent_shots
        
        # Create working directories
        self.shots_dir = os.path.join(working_dir, "shots")
        self.videos_dir = os.path.join(working_dir, "videos")
        os.makedirs(self.shots_dir, exist_ok=True)
        os.makedirs(self.videos_dir, exist_ok=True)
    
    async def generate_reference_frame(
        self,
        shot: ShotData,
        characters: List[CharacterData],
        scenes: List[SceneData],
        style: str
    ) -> str:
        """
        Generate reference frame image for a shot
        
        Args:
            shot: Shot data
            characters: List of characters
            scenes: List of scenes
            style: Visual style
            
        Returns:
            Path to generated reference frame
        """
        # Build prompt from shot description
        prompt = f"{shot.visual_desc}. "
        prompt += f"Camera: {shot.camera_angle}, {shot.camera_movement}. "
        prompt += f"Style: {style}."
        
        # Add character information if available
        if shot.character_action:
            prompt += f" Character action: {shot.character_action}."
        
        logger.info(f"Generating reference frame for shot {shot.shot_number}")
        logger.debug(f"Prompt: {prompt}")
        
        # Generate image
        image_output = await self.image_generator.generate_single_image(
            prompt=prompt,
            aspect_ratio="16:9"
        )
        
        # Save image
        frame_path = os.path.join(
            self.shots_dir,
            f"shot_{shot.shot_number:03d}_frame.{image_output.ext}"
        )
        image_output.save(frame_path)
        
        logger.info(f"Reference frame saved to {frame_path}")
        return frame_path
    
    @with_retry(max_attempts=3, delay=2.0)
    async def generate_shot_video(
        self,
        shot: ShotData,
        reference_frames: List[str],
        style: str,
        duration: int = 5
    ) -> VideoOutput:
        """
        Generate video for a single shot
        
        Args:
            shot: Shot data
            reference_frames: List of reference frame paths (1 or 2 images)
            style: Visual style
            duration: Video duration in seconds
            
        Returns:
            VideoOutput object
        """
        # Build video generation prompt
        prompt = f"{shot.visual_desc}. "
        prompt += f"Camera movement: {shot.camera_movement}. "
        prompt += f"Style: {style}."
        
        if shot.dialogue:
            prompt += f" Dialogue: {shot.dialogue}."
        
        logger.info(f"Generating video for shot {shot.shot_number}")
        logger.debug(f"Prompt: {prompt}")
        logger.debug(f"Reference frames: {reference_frames}")
        
        # Generate video
        video_output = await self.video_generator.generate_single_video(
            prompt=prompt,
            reference_image_paths=reference_frames,
            aspect_ratio="16:9",
            duration=duration
        )
        
        logger.info(f"Video generated for shot {shot.shot_number}")
        return video_output
    
    async def generate_single_shot(
        self,
        shot: ShotData,
        characters: List[CharacterData],
        scenes: List[SceneData],
        style: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Dict[str, Any]:
        """
        Generate complete video for a single shot
        
        Args:
            shot: Shot data
            characters: List of characters
            scenes: List of scenes
            style: Visual style
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with video path and metadata
        """
        try:
            # Update progress
            if progress_callback:
                await progress_callback.update(
                    0.0,
                    f"Starting shot {shot.shot_number}: {shot.visual_desc[:50]}..."
                )
            
            # Step 1: Generate reference frame
            if progress_callback:
                await progress_callback.update(
                    0.2,
                    f"Generating reference frame for shot {shot.shot_number}..."
                )
            
            reference_frame = await self.generate_reference_frame(
                shot, characters, scenes, style
            )
            
            # Step 2: Generate video
            if progress_callback:
                await progress_callback.update(
                    0.5,
                    f"Generating video for shot {shot.shot_number}..."
                )
            
            video_output = await self.generate_shot_video(
                shot=shot,
                reference_frames=[reference_frame],
                style=style,
                duration=5
            )
            
            # Step 3: Save video
            if progress_callback:
                await progress_callback.update(
                    0.8,
                    f"Saving video for shot {shot.shot_number}..."
                )
            
            video_path = os.path.join(
                self.videos_dir,
                f"shot_{shot.shot_number:03d}.mp4"
            )
            
            if video_output.fmt == "url":
                # Download video from URL
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(video_output.data) as response:
                        with open(video_path, 'wb') as f:
                            f.write(await response.read())
            else:
                # Save directly
                video_output.save(video_path)
            
            if progress_callback:
                await progress_callback.update(
                    1.0,
                    f"Shot {shot.shot_number} completed"
                )
            
            return {
                "shot_number": shot.shot_number,
                "video_path": video_path,
                "reference_frame": reference_frame,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Error generating shot {shot.shot_number}: {e}")
            raise GenerationError(
                message=f"Failed to generate video for shot {shot.shot_number}",
                generation_type="shot_video",
                details={"shot_number": shot.shot_number, "error": str(e)}
            )
    
    async def generate_all_shots(
        self,
        storyboard: List[ShotData],
        characters: List[CharacterData],
        scenes: List[SceneData],
        style: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate videos for all shots in the storyboard
        
        Args:
            storyboard: List of shot data
            characters: List of characters
            scenes: List of scenes
            style: Visual style
            progress_callback: Optional progress callback
            
        Returns:
            List of shot results with video paths
        """
        total_shots = len(storyboard)
        progress_tracker = VideoGenerationProgress(total_shots)
        
        logger.info(f"Starting video generation for {total_shots} shots")
        
        # Create semaphore for concurrent generation
        semaphore = asyncio.Semaphore(self.max_concurrent_shots)
        
        async def generate_with_semaphore(shot: ShotData) -> Dict[str, Any]:
            async with semaphore:
                try:
                    # Create shot-specific progress callback
                    shot_progress = ProgressCallback()
                    
                    async def on_shot_progress(percentage: float, message: str):
                        progress_tracker.update_shot(
                            shot.shot_number,
                            "generating",
                            message
                        )
                        
                        # Update overall progress
                        if progress_callback:
                            overall_progress = (
                                (progress_tracker.completed_shots + percentage) / 
                                total_shots
                            )
                            await progress_callback.update(
                                overall_progress,
                                f"Shot {shot.shot_number}/{total_shots}: {message}"
                            )
                    
                    shot_progress.subscribe(on_shot_progress)
                    
                    # Generate shot
                    result = await self.generate_single_shot(
                        shot, characters, scenes, style, shot_progress
                    )
                    
                    progress_tracker.update_shot(shot.shot_number, "completed")
                    return result
                    
                except Exception as e:
                    logger.error(f"Failed to generate shot {shot.shot_number}: {e}")
                    progress_tracker.add_error(shot.shot_number, str(e))
                    return {
                        "shot_number": shot.shot_number,
                        "status": "failed",
                        "error": str(e)
                    }
        
        # Generate all shots concurrently
        tasks = [generate_with_semaphore(shot) for shot in storyboard]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        shot_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Shot generation exception: {result}")
                shot_results.append({
                    "status": "failed",
                    "error": str(result)
                })
            else:
                shot_results.append(result)
        
        logger.info(f"Completed {progress_tracker.completed_shots}/{total_shots} shots")
        
        return shot_results
    
    async def concatenate_shot_videos(
        self,
        shot_results: List[Dict[str, Any]],
        output_path: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> str:
        """
        Concatenate all shot videos into final video
        
        Args:
            shot_results: List of shot results with video paths
            output_path: Output path for final video
            progress_callback: Optional progress callback
            
        Returns:
            Path to final concatenated video
        """
        if progress_callback:
            await progress_callback.update(0.0, "Preparing video concatenation...")
        
        # Filter successful shots and sort by shot number
        successful_shots = [
            r for r in shot_results 
            if r.get("status") == "completed" and r.get("video_path")
        ]
        successful_shots.sort(key=lambda x: x["shot_number"])
        
        if not successful_shots:
            raise ResourceError("No successful shots to concatenate")
        
        video_paths = [shot["video_path"] for shot in successful_shots]
        
        logger.info(f"Concatenating {len(video_paths)} videos...")
        
        if progress_callback:
            await progress_callback.update(0.3, f"Concatenating {len(video_paths)} videos...")
        
        # Use video utility to concatenate
        final_video_path = await asyncio.to_thread(
            concatenate_videos,
            video_paths,
            output_path
        )
        
        if progress_callback:
            await progress_callback.update(1.0, "Video concatenation completed")
        
        logger.info(f"Final video saved to {final_video_path}")
        return final_video_path
    
    async def generate_episode_video(
        self,
        storyboard: List[ShotData],
        characters: List[CharacterData],
        scenes: List[SceneData],
        style: str,
        episode_id: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Dict[str, Any]:
        """
        Generate complete video for an episode
        
        Args:
            storyboard: List of shot data
            characters: List of characters
            scenes: List of scenes
            style: Visual style
            episode_id: Episode ID for naming
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with final video path and metadata
        """
        try:
            # Step 1: Generate all shots (80% of progress)
            if progress_callback:
                await progress_callback.update(0.0, "Starting video generation...")
            
            shot_progress = ProgressCallback()
            
            async def on_shot_progress(percentage: float, message: str):
                if progress_callback:
                    # Map shot progress to 0-80% of overall progress
                    overall_progress = percentage * 0.8
                    await progress_callback.update(overall_progress, message)
            
            shot_progress.subscribe(on_shot_progress)
            
            shot_results = await self.generate_all_shots(
                storyboard, characters, scenes, style, shot_progress
            )
            
            # Step 2: Concatenate videos (20% of progress)
            if progress_callback:
                await progress_callback.update(0.8, "Concatenating videos...")
            
            concat_progress = ProgressCallback()
            
            async def on_concat_progress(percentage: float, message: str):
                if progress_callback:
                    # Map concat progress to 80-100% of overall progress
                    overall_progress = 0.8 + (percentage * 0.2)
                    await progress_callback.update(overall_progress, message)
            
            concat_progress.subscribe(on_concat_progress)
            
            final_video_path = os.path.join(
                self.videos_dir,
                f"episode_{episode_id}_final.mp4"
            )
            
            final_path = await self.concatenate_shot_videos(
                shot_results, final_video_path, concat_progress
            )
            
            # Calculate statistics
            successful_shots = len([r for r in shot_results if r.get("status") == "completed"])
            failed_shots = len([r for r in shot_results if r.get("status") == "failed"])
            
            if progress_callback:
                await progress_callback.update(1.0, "Video generation completed!")
            
            return {
                "success": True,
                "video_path": final_path,
                "total_shots": len(storyboard),
                "successful_shots": successful_shots,
                "failed_shots": failed_shots,
                "shot_results": shot_results
            }
            
        except Exception as e:
            logger.error(f"Error generating episode video: {e}")
            raise GenerationError(
                message="Failed to generate episode video",
                generation_type="episode_video",
                details={"episode_id": episode_id, "error": str(e)}
            )


def create_video_adapter(
    video_generator,
    image_generator,
    working_dir: str = ".working_dir",
    max_concurrent_shots: int = 2
) -> VideoGenerationAdapter:
    """
    Factory function to create video generation adapter
    
    Args:
        video_generator: Video generator tool
        image_generator: Image generator tool
        working_dir: Working directory
        max_concurrent_shots: Maximum concurrent shots
        
    Returns:
        VideoGenerationAdapter instance
    """
    return VideoGenerationAdapter(
        video_generator=video_generator,
        image_generator=image_generator,
        working_dir=working_dir,
        max_concurrent_shots=max_concurrent_shots
    )