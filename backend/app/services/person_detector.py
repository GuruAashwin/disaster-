"""
Person Detection Service (STEP 5)
==================================

Isolated module for detecting people in video frames.
Uses contour-based detection with morphological operations for CPU-friendly person detection.

No dependency on:
- existing auth, persons, matches, or database tables
- GPU or external model downloads
- MediaPipe, YOLOv8, or other ML frameworks
- face recognition or identity matching
- clothing detection (comes in later steps)

Detection returns bounding boxes with confidence scores.

Approach: Detects potential people by finding large connected components
(contours) that have aspect ratios and sizes consistent with human figures.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import cv2
import numpy as np
from uuid import uuid4

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIDENCE_THRESHOLD = 0.4
MAX_IMAGE_WIDTH = 1920
MAX_IMAGE_HEIGHT = 1440

# Person-like shape parameters
MIN_PERSON_HEIGHT_PX = 40  # Minimum height of person bounding box
MAX_PERSON_HEIGHT_PX = 600  # Maximum height of person bounding box
MIN_PERSON_WIDTH_PX = 25  # Minimum width of person bounding box
MAX_PERSON_WIDTH_PX = 400  # Maximum width of person bounding box
MIN_ASPECT_RATIO = 0.3  # width / height (taller than wide)
MAX_ASPECT_RATIO = 0.8


class PersonDetection:
    """Single person detection result."""
    
    def __init__(
        self,
        frame_number: int,
        timestamp_seconds: float,
        x: int,
        y: int,
        width: int,
        height: int,
        confidence: float,
        detection_id: Optional[str] = None,
    ):
        """
        Initialize a person detection.
        
        Args:
            frame_number: Frame index (0-based)
            timestamp_seconds: Time in seconds from video start
            x: Bounding box top-left x coordinate
            y: Bounding box top-left y coordinate
            width: Bounding box width
            height: Bounding box height
            confidence: Detection confidence (0.0 to 1.0)
            detection_id: Unique detection ID (auto-generated if None)
        """
        self.detection_id = detection_id or str(uuid4())
        self.frame_number = frame_number
        self.timestamp_seconds = timestamp_seconds
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.confidence = float(confidence)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert detection to dictionary."""
        return {
            "detection_id": self.detection_id,
            "frame_number": self.frame_number,
            "timestamp_seconds": self.timestamp_seconds,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
        }


class PersonDetectorResult:
    """Result of detecting people in a frame."""
    
    def __init__(self, frame_path: str, frame_number: int = 0, timestamp_seconds: float = 0.0):
        self.frame_path = frame_path
        self.frame_filename = Path(frame_path).name
        self.frame_number = frame_number
        self.timestamp_seconds = timestamp_seconds
        self.image_width: Optional[int] = None
        self.image_height: Optional[int] = None
        self.detections: List[PersonDetection] = []
        self.people_count: int = 0
        self.status: str = "pending"
        self.error: Optional[str] = None
    
    def add_detection(self, detection: PersonDetection) -> None:
        """Add a detection to the result."""
        self.detections.append(detection)
        self.people_count = len(self.detections)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "frame": self.frame_filename,
            "frame_number": self.frame_number,
            "timestamp_seconds": self.timestamp_seconds,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "people_count": self.people_count,
            "detections": [d.to_dict() for d in self.detections],
            "status": self.status,
            "error": self.error,
        }


class PersonDetector:
    """Main person detection service using contour analysis."""
    
    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD):
        """
        Initialize person detector.
        
        Args:
            confidence_threshold: Minimum confidence for detections (0.0 to 1.0)
        """
        self.confidence_threshold = max(0.0, min(1.0, confidence_threshold))
        logger.info(
            f"PersonDetector initialized: confidence_threshold={self.confidence_threshold}"
        )
    
    def _ensure_image_in_bounds(
        self,
        image: np.ndarray,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> Tuple[int, int, int, int]:
        """
        Ensure bounding box stays within image boundaries.
        
        Args:
            image: Input image array
            x: Bounding box x coordinate
            y: Bounding box y coordinate
            width: Bounding box width
            height: Bounding box height
        
        Returns:
            (x, y, width, height) adjusted to image bounds
        """
        img_height, img_width = image.shape[:2]
        
        # Clamp coordinates
        x = max(0, int(x))
        y = max(0, int(y))
        
        # Ensure right and bottom edges don't exceed image
        right = min(img_width, int(x + width))
        bottom = min(img_height, int(y + height))
        
        # Recalculate width and height
        width = max(1, right - x)
        height = max(1, bottom - y)
        
        return x, y, width, height
    
    def _detect_foreground_objects(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect foreground objects (potential people) using morphological operations.
        
        Args:
            image: Input image (BGR)
        
        Returns:
            List of (x, y, width, height) bounding boxes
        """
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Create a mask for skin-like colors and dark clothing
        # Skin colors typically in HSV: H 0-20, 160-180; S 20-255; V 50-255
        lower_skin1 = np.array([0, 20, 50])
        upper_skin1 = np.array([20, 255, 255])
        lower_skin2 = np.array([160, 20, 50])
        upper_skin2 = np.array([180, 255, 255])
        
        mask_skin1 = cv2.inRange(hsv, lower_skin1, upper_skin1)
        mask_skin2 = cv2.inRange(hsv, lower_skin2, upper_skin2)
        mask_skin = cv2.bitwise_or(mask_skin1, mask_skin2)
        
        # Also detect dark objects (clothing)
        lower_dark = np.array([0, 0, 0])
        upper_dark = np.array([180, 255, 50])
        mask_dark = cv2.inRange(hsv, lower_dark, upper_dark)
        
        # Combine masks
        mask = cv2.bitwise_or(mask_skin, mask_dark)
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size and aspect ratio
        bounding_boxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check size constraints
            if w < MIN_PERSON_WIDTH_PX or h < MIN_PERSON_HEIGHT_PX:
                continue
            if w > MAX_PERSON_WIDTH_PX or h > MAX_PERSON_HEIGHT_PX:
                continue
            
            # Check aspect ratio (width / height)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
                continue
            
            # Check area (must have reasonable fill)
            area = cv2.contourArea(contour)
            min_area = w * h * 0.1  # At least 10% of bounding box filled
            if area < min_area:
                continue
            
            bounding_boxes.append((x, y, w, h))
        
        return bounding_boxes
    
    def detect_frame(
        self,
        frame_path: Path,
        frame_number: int = 0,
        timestamp_seconds: float = 0.0,
    ) -> PersonDetectorResult:
        """
        Detect people in a single frame/image.
        
        Args:
            frame_path: Path to frame image file
            frame_number: Frame index (0-based)
            timestamp_seconds: Time in video (seconds)
        
        Returns:
            PersonDetectorResult with detection metadata and people found
        """
        result = PersonDetectorResult(
            str(frame_path),
            frame_number=frame_number,
            timestamp_seconds=timestamp_seconds,
        )
        
        # Read image
        try:
            image = cv2.imread(str(frame_path))
            if image is None:
                result.status = "failed"
                result.error = "Unable to read image file"
                logger.error(f"Failed to read image: {frame_path}")
                return result
        except Exception as e:
            result.status = "failed"
            result.error = f"Error reading image: {str(e)}"
            logger.error(f"Error reading {frame_path}: {e}")
            return result
        
        # Store image dimensions
        result.image_height, result.image_width = image.shape[:2]
        
        # Skip oversized images
        if result.image_width > MAX_IMAGE_WIDTH or result.image_height > MAX_IMAGE_HEIGHT:
            result.status = "failed"
            result.error = f"Image too large: {result.image_width}x{result.image_height}"
            logger.warning(f"Image too large: {frame_path}")
            return result
        
        # Detect foreground objects
        try:
            bounding_boxes = self._detect_foreground_objects(image)
            
            logger.debug(f"Detected {len(bounding_boxes)} potential person(s) in {frame_path}")
            
            # Process each detection
            for (x, y, w, h) in bounding_boxes:
                # Ensure bounds
                x, y, w, h = self._ensure_image_in_bounds(image, x, y, w, h)
                
                # Calculate confidence based on size and aspect ratio
                area_ratio = (w * h) / (result.image_width * result.image_height)
                area_confidence = min(0.9, area_ratio * 10)
                
                aspect_ratio = w / h if h > 0 else 0
                ideal_aspect_ratio = 0.5
                aspect_diff = abs(aspect_ratio - ideal_aspect_ratio) / ideal_aspect_ratio
                aspect_confidence = max(0.3, 1.0 - aspect_diff)
                
                # Combined confidence
                confidence = (area_confidence + aspect_confidence) / 2
                confidence = min(0.95, max(0.3, confidence))
                
                # Apply confidence threshold
                if confidence >= self.confidence_threshold:
                    detection = PersonDetection(
                        frame_number=frame_number,
                        timestamp_seconds=timestamp_seconds,
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=confidence,
                    )
                    result.add_detection(detection)
            
            result.status = "processed"
            logger.debug(f"Detected {result.people_count} person(s) in {frame_path}")
            
        except Exception as e:
            result.status = "failed"
            result.error = f"Error during detection: {str(e)}"
            logger.error(f"Detection error for {frame_path}: {e}")
        
        return result
    
    def detect_frames_batch(
        self,
        frame_paths: List[Path],
        frame_numbers: Optional[List[int]] = None,
        timestamp_seconds: Optional[List[float]] = None,
    ) -> List[PersonDetectorResult]:
        """
        Detect people in multiple frames (batch processing).
        
        Args:
            frame_paths: List of paths to frame files
            frame_numbers: List of frame indices (auto-generated if None)
            timestamp_seconds: List of timestamps in seconds (auto-generated if None)
        
        Returns:
            List of PersonDetectorResult objects
        """
        if frame_numbers is None:
            frame_numbers = list(range(len(frame_paths)))
        
        if timestamp_seconds is None:
            timestamp_seconds = [0.0] * len(frame_paths)
        
        results = []
        for path, frame_num, ts in zip(frame_paths, frame_numbers, timestamp_seconds):
            result = self.detect_frame(path, frame_number=frame_num, timestamp_seconds=ts)
            results.append(result)
        
        return results
    
    def detect_frame_directory(
        self,
        frames_dir: Path,
        camera_id: str = "unknown",
        video_name: str = "video",
    ) -> List[PersonDetectorResult]:
        """
        Detect people in all frames in a directory.
        
        Expected structure:
            {frames_dir}/{camera_id}/{video_name}/frame_*.jpg
        
        Args:
            frames_dir: Root frames directory
            camera_id: Camera subdirectory name
            video_name: Video subdirectory name
        
        Returns:
            List of PersonDetectorResult objects
        """
        frames_dir = Path(frames_dir)
        video_dir = frames_dir / camera_id / video_name
        
        if not video_dir.exists():
            logger.warning(f"Directory does not exist: {video_dir}")
            return []
        
        # Find all JPEG frames sorted by name
        frame_files = sorted(video_dir.glob("frame_*.jpg"))
        
        if not frame_files:
            logger.warning(f"No frame files found in {video_dir}")
            return []
        
        results = []
        for idx, frame_path in enumerate(frame_files):
            # Extract frame number from filename (frame_000001.jpg -> 1)
            try:
                frame_num = int(frame_path.stem.split("_")[1])
            except (IndexError, ValueError):
                frame_num = idx
            
            result = self.detect_frame(frame_path, frame_number=frame_num, timestamp_seconds=0.0)
            results.append(result)
        
        return results


# Singleton instance
_detector_instance: Optional[PersonDetector] = None


def get_detector(
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> PersonDetector:
    """
    Get or create the global PersonDetector instance.
    
    Args:
        confidence_threshold: Confidence threshold for detections
    
    Returns:
        PersonDetector instance
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = PersonDetector(confidence_threshold=confidence_threshold)
    return _detector_instance


def detect_frame(
    frame_path: Path,
    frame_number: int = 0,
    timestamp_seconds: float = 0.0,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> PersonDetectorResult:
    """
    Convenience function to detect people in a frame.
    
    Args:
        frame_path: Path to frame image
        frame_number: Frame index
        timestamp_seconds: Time in seconds
        confidence_threshold: Detection confidence threshold
    
    Returns:
        PersonDetectorResult
    """
    detector = get_detector(confidence_threshold=confidence_threshold)
    return detector.detect_frame(
        frame_path,
        frame_number=frame_number,
        timestamp_seconds=timestamp_seconds,
    )


def detect_frames_batch(
    frame_paths: List[Path],
    frame_numbers: Optional[List[int]] = None,
    timestamp_seconds: Optional[List[float]] = None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> List[PersonDetectorResult]:
    """
    Convenience function for batch frame detection.
    
    Args:
        frame_paths: List of frame paths
        frame_numbers: List of frame indices
        timestamp_seconds: List of timestamps
        confidence_threshold: Detection confidence threshold
    
    Returns:
        List of PersonDetectorResult objects
    """
    detector = get_detector(confidence_threshold=confidence_threshold)
    return detector.detect_frames_batch(
        frame_paths,
        frame_numbers=frame_numbers,
        timestamp_seconds=timestamp_seconds,
    )
