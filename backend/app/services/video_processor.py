"""
Video Processing Service
========================

Isolated module for processing disaster video files.
Extracts frames at regular intervals and saves sample frames.

No dependency on existing auth, persons, matches, or database tables.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import cv2
from datetime import datetime

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_SAMPLE_INTERVAL_SECONDS = 1.0  # IMPROVED: 1 second sampling (was 2) for better coverage
# Why: 2-second interval can miss people visible for only 1 second
# Tradeoff: ~2x more frames, but for disaster scenarios coverage > storage
MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hour max per video
SUPPORTED_FORMATS = ('.mp4', '.avi', '.mov', '.mkv')


class VideoProcessorResult:
    """Result of processing a single video."""
    
    def __init__(self, video_path: str, camera_id: str = "unknown"):
        self.video_path = video_path
        self.video_filename = os.path.basename(video_path)
        self.camera_id = camera_id
        self.duration_seconds: Optional[float] = None
        self.fps: Optional[float] = None
        self.total_frames: Optional[int] = None
        self.sample_interval_seconds: float = DEFAULT_SAMPLE_INTERVAL_SECONDS
        self.frames_processed: int = 0
        self.frames_saved: int = 0
        self.status: str = "pending"
        self.error: Optional[str] = None
        self.saved_frames_dir: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "video": self.video_filename,
            "camera_id": self.camera_id,
            "duration_seconds": self.duration_seconds,
            "fps": self.fps,
            "total_frames": self.total_frames,
            "sample_interval_seconds": self.sample_interval_seconds,
            "frames_processed": self.frames_processed,
            "frames_saved": self.frames_saved,
            "status": self.status,
            "error": self.error,
            "saved_frames_dir": self.saved_frames_dir,
        }


class VideoProcessor:
    """Main video processor service."""
    
    def __init__(
        self,
        video_dir: str = "backend/video_files",
        output_dir: str = "backend/video_frames",
        sample_interval_seconds: float = DEFAULT_SAMPLE_INTERVAL_SECONDS,
    ):
        """
        Initialize video processor.
        
        Args:
            video_dir: Directory containing video files
            output_dir: Directory to save sample frames
            sample_interval_seconds: Process frame every N seconds
        """
        self.video_dir = Path(video_dir)
        self.output_dir = Path(output_dir)
        self.sample_interval_seconds = sample_interval_seconds
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"VideoProcessor initialized: {self.video_dir} -> {self.output_dir}")
    
    def _infer_camera_id(self, video_path: Path) -> str:
        """
        Infer camera ID from directory structure or filename.
        
        All videos directly in video_files directory go to camera_001.
        Videos in subdirectories use the subdirectory name.
        
        Args:
            video_path: Path to video file
        
        Returns:
            Camera ID (camera_XXX format)
        """
        parent = video_path.parent.name
        
        # If parent is video_files, use camera_001 for all videos
        if parent == self.video_dir.name:
            return "camera_001"
        
        # If parent already starts with camera_, use as is
        if parent.startswith("camera_"):
            return parent
        
        # Otherwise, treat parent name as camera identifier
        return f"camera_{parent}"
    
    def process_video(
        self,
        video_path: Path,
        sample_interval_seconds: Optional[float] = None,
    ) -> VideoProcessorResult:
        """
        Process a single video file.
        
        Args:
            video_path: Path to video file
            sample_interval_seconds: Override default sampling interval
        
        Returns:
            VideoProcessorResult with metadata and processing status
        """
        result = VideoProcessorResult(
            str(video_path),
            camera_id=self._infer_camera_id(video_path)
        )
        
        if sample_interval_seconds is not None:
            result.sample_interval_seconds = sample_interval_seconds
        
        logger.info(f"Processing video: {video_path}")
        
        # Open video file
        cap = None
        try:
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                result.status = "failed"
                result.error = "Unable to open video"
                logger.error(f"Failed to open video: {video_path}")
                return result
            
            # Get video metadata
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps <= 0 or frame_count <= 0:
                result.status = "failed"
                result.error = "Invalid video metadata (FPS or frame count)"
                logger.error(f"Invalid metadata: fps={fps}, frames={frame_count}")
                return result
            
            duration_seconds = frame_count / fps
            
            # Check if video exceeds max duration
            if duration_seconds > MAX_VIDEO_DURATION_SECONDS:
                result.status = "failed"
                result.error = f"Video duration exceeds {MAX_VIDEO_DURATION_SECONDS}s"
                logger.error(f"Video too long: {duration_seconds}s")
                return result
            
            result.fps = fps
            result.total_frames = frame_count
            result.duration_seconds = duration_seconds
            
            # Create output directory for this video using camera_id and video_id
            camera_dir = self.output_dir / result.camera_id
            
            # Generate video_id by getting all videos and finding index
            all_videos = []
            for fmt in SUPPORTED_FORMATS:
                all_videos.extend(sorted(self.video_dir.glob(f"**/*{fmt}")))
            
            video_num = all_videos.index(video_path) + 1
            video_id = f"video_{video_num:03d}"
            
            frames_dir = camera_dir / video_id
            frames_dir.mkdir(parents=True, exist_ok=True)
            result.saved_frames_dir = str(frames_dir)
            
            # Calculate frame interval (frames to skip between samples)
            frame_interval = int(fps * result.sample_interval_seconds)
            if frame_interval <= 0:
                frame_interval = 1
            
            # Process frames
            frame_number = 0
            sample_frame_number = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Check if this is a sample frame
                if frame_number % frame_interval == 0:
                    sample_frame_number += 1
                    result.frames_processed += 1
                    
                    # Save frame as JPEG
                    frame_filename = f"frame_{sample_frame_number:06d}.jpg"
                    frame_path = frames_dir / frame_filename
                    
                    success = cv2.imwrite(str(frame_path), frame)
                    if success:
                        result.frames_saved += 1
                    else:
                        logger.warning(f"Failed to save frame: {frame_path}")
                
                frame_number += 1
            
            result.status = "processed"
            logger.info(
                f"Video processed: {video_path} "
                f"({result.frames_processed} frames, {result.frames_saved} saved)"
            )
            
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            logger.error(f"Error processing video: {video_path}: {e}")
        
        finally:
            # Release video capture
            if cap is not None:
                cap.release()
        
        return result
    
    def process_video_directory(
        self,
        sample_interval_seconds: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process all video files in the video directory.
        
        Recursively searches for supported video formats.
        Handles errors gracefully - one video failure doesn't stop processing.
        
        Args:
            sample_interval_seconds: Override default sampling interval
        
        Returns:
            List of processing results (as dictionaries)
        """
        results = []
        
        if not self.video_dir.exists():
            logger.warning(f"Video directory does not exist: {self.video_dir}")
            return results
        
        # Find all video files recursively
        video_files = []
        for fmt in SUPPORTED_FORMATS:
            video_files.extend(self.video_dir.glob(f"**/*{fmt}"))
        
        logger.info(f"Found {len(video_files)} video files")
        
        # Process each video
        for video_path in video_files:
            result = self.process_video(
                video_path,
                sample_interval_seconds=sample_interval_seconds
            )
            results.append(result.to_dict())
        
        return results


# Convenience functions for direct use
_processor: Optional[VideoProcessor] = None


def get_processor(
    video_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> VideoProcessor:
    """Get or create the global video processor instance.
    
    Args:
        video_dir: Path to video directory (defaults to current dir's video_files)
        output_dir: Path to output directory (defaults to current dir's video_frames)
    
    Returns:
        Global VideoProcessor instance
    """
    global _processor
    if _processor is None:
        # If paths not provided, use paths relative to current working directory
        # (which should be the backend directory when running uvicorn)
        if video_dir is None:
            video_dir = str(Path(".") / "video_files")
        if output_dir is None:
            output_dir = str(Path(".") / "video_frames")
        
        # Resolve to absolute paths for reliability
        video_dir = str(Path(video_dir).resolve())
        output_dir = str(Path(output_dir).resolve())
        
        logger.info(f"Initializing VideoProcessor with resolved paths:")
        logger.info(f"  video_dir: {video_dir}")
        logger.info(f"  output_dir: {output_dir}")
        
        _processor = VideoProcessor(video_dir, output_dir)
    return _processor


def process_video(
    video_path: str,
    sample_interval_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Process a single video file.
    
    Args:
        video_path: Path to video file
        sample_interval_seconds: Override default sampling interval
    
    Returns:
        Processing result as dictionary
    """
    processor = get_processor()
    result = processor.process_video(
        Path(video_path),
        sample_interval_seconds=sample_interval_seconds
    )
    return result.to_dict()


def process_video_directory(
    sample_interval_seconds: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Process all videos in the default video directory.
    
    Args:
        sample_interval_seconds: Override default sampling interval
    
    Returns:
        List of processing results
    """
    processor = get_processor()
    return processor.process_video_directory(sample_interval_seconds)
