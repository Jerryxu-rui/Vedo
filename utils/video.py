import logging
import requests
import subprocess
from pathlib import Path
from typing import List
from tenacity import retry


@retry
def download_video(url, save_path):
    try:
        logging.info(f"Downloading video from {url} to {save_path}")

        response = requests.get(url, stream=True)
        response.raise_for_status()  # 检查请求是否成功
    
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logging.info(f"Video downloaded successfully to {save_path}")
    
    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        raise e


def concatenate_videos(video_paths: List[str], output_path: str) -> str:
    """
    Concatenate multiple video files into a single video using ffmpeg.
    
    Args:
        video_paths: List of paths to video files to concatenate
        output_path: Path where the concatenated video will be saved
        
    Returns:
        Path to the concatenated video file
        
    Raises:
        RuntimeError: If ffmpeg concatenation fails
    """
    try:
        logging.info(f"Concatenating {len(video_paths)} videos to {output_path}")
        
        # Filter out None or empty paths
        valid_paths = [p for p in video_paths if p and Path(p).exists()]
        
        if not valid_paths:
            raise ValueError("No valid video paths provided for concatenation")
        
        if len(valid_paths) == 1:
            # If only one video, just copy it
            import shutil
            shutil.copy(valid_paths[0], output_path)
            logging.info(f"Single video copied to {output_path}")
            return output_path
        
        # Create a temporary file list for ffmpeg
        list_file = Path(output_path).parent / "concat_list.txt"
        with open(list_file, 'w') as f:
            for video_path in valid_paths:
                # Use absolute paths and escape special characters
                abs_path = Path(video_path).absolute()
                f.write(f"file '{abs_path}'\n")
        
        # Use ffmpeg to concatenate videos
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file),
            '-c', 'copy',
            '-y',  # Overwrite output file if it exists
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Clean up temporary file
        list_file.unlink(missing_ok=True)
        
        logging.info(f"Videos concatenated successfully to {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr}")
        raise RuntimeError(f"Failed to concatenate videos: {e.stderr}")
    except Exception as e:
        logging.error(f"Error concatenating videos: {e}")
        raise e
