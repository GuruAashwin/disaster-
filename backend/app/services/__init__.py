"""
Services module for isolated feature implementations.
"""

from .video_processor import (
    VideoProcessor,
    VideoProcessorResult,
    process_video,
    process_video_directory,
    get_processor,
)

from .person_detector import (
    PersonDetector,
    PersonDetection,
    PersonDetectorResult,
    detect_frame,
    detect_frames_batch,
    get_detector,
    DEFAULT_CONFIDENCE_THRESHOLD,
)

__all__ = [
    # Video Processing (STEP 4)
    "VideoProcessor",
    "VideoProcessorResult",
    "process_video",
    "process_video_directory",
    "get_processor",
    # Person Detection (STEP 5)
    "PersonDetector",
    "PersonDetection",
    "PersonDetectorResult",
    "detect_frame",
    "detect_frames_batch",
    "get_detector",
    "DEFAULT_CONFIDENCE_THRESHOLD",
]
