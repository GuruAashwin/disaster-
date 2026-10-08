"""
Clothing Region Extraction Service (STEP 6)
============================================

Isolated module for extracting approximate clothing regions from detected people.
Uses proportional coordinate calculations based on person bounding boxes.

No dependency on:
- existing auth, persons, matches, or database tables
- GPU or external models
- face recognition or clothing detection (comes in later steps)
- color analysis or matching (STEP 7+)

Extracts two regions per person:
1. Upper-body / shirt region
2. Lower-body / pants region

These regions are designed for STEP 7 (clothing color analysis).

IMPORTANT: This is approximate region extraction, not perfect pose segmentation.
People may be sitting, crouching, wearing long coats, partially hidden, etc.
The goal is a stable MVP region for downstream color analysis.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import cv2
import numpy as np
from uuid import uuid4

logger = logging.getLogger(__name__)

# Region extraction proportions (as ratios of person bounding box height)
# These are configurable constants, not magic numbers scattered in code

# Head/neck exclusion: exclude top 15% of bounding box (head/neck area)
HEAD_EXCLUSION_RATIO = 0.15

# Upper-body (shirt) region: starts after head, occupies middle 35% of box
UPPER_BODY_START_RATIO = 0.15  # Start after head
UPPER_BODY_HEIGHT_RATIO = 0.35  # Height as % of bbox height

# Lower-body (pants) region: starts after upper body, occupies remaining 50%
LOWER_BODY_START_RATIO = 0.50  # Start from middle of bbox
LOWER_BODY_HEIGHT_RATIO = 0.50  # Height as % of bbox height

# Horizontal margins (as ratio of person bbox width)
HORIZONTAL_MARGIN_RATIO = 0.1  # 10% margin on left/right sides


class ClothingRegion:
    """Single clothing region (upper or lower body)."""
    
    def __init__(
        self,
        region_type: str,  # "upper_body" or "lower_body"
        x: int,
        y: int,
        width: int,
        height: int,
        region_id: Optional[str] = None,
    ):
        """
        Initialize a clothing region.
        
        Args:
            region_type: "upper_body" or "lower_body"
            x: Region top-left x coordinate (in original frame)
            y: Region top-left y coordinate (in original frame)
            width: Region width in pixels
            height: Region height in pixels
            region_id: Unique region ID (auto-generated if None)
        """
        self.region_id = region_id or str(uuid4())
        self.region_type = region_type
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert region to dictionary."""
        return {
            "region_id": self.region_id,
            "region_type": self.region_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


class RegionExtractionResult:
    """Result of extracting clothing regions from one person detection."""
    
    def __init__(
        self,
        detection_id: str,
        frame_path: str,
        person_bbox: Dict[str, int],
        frame_width: int,
        frame_height: int,
    ):
        """
        Initialize extraction result.
        
        Args:
            detection_id: ID from STEP 5 person detection
            frame_path: Path to the frame image
            person_bbox: Person detection bbox {x, y, width, height}
            frame_width: Original frame width in pixels
            frame_height: Original frame height in pixels
        """
        self.detection_id = detection_id
        self.frame_path = frame_path
        self.frame_filename = Path(frame_path).name
        self.person_bbox = person_bbox
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        self.upper_body_region: Optional[ClothingRegion] = None
        self.lower_body_region: Optional[ClothingRegion] = None
        
        self.status: str = "pending"
        self.error: Optional[str] = None
    
    def set_upper_body_region(self, region: ClothingRegion) -> None:
        """Set upper-body region."""
        self.upper_body_region = region
    
    def set_lower_body_region(self, region: ClothingRegion) -> None:
        """Set lower-body region."""
        self.lower_body_region = region
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "detection_id": self.detection_id,
            "frame": self.frame_filename,
            "person_bbox": self.person_bbox,
            "regions": {
                "upper_body": self.upper_body_region.to_dict() if self.upper_body_region else None,
                "lower_body": self.lower_body_region.to_dict() if self.lower_body_region else None,
            },
            "status": self.status,
            "error": self.error,
        }


class ClothingRegionExtractor:
    """Main clothing region extraction service."""
    
    def __init__(
        self,
        debug_mode: bool = False,
        debug_output_dir: str = "backend/video_frames_debug",
    ):
        """
        Initialize region extractor.
        
        Args:
            debug_mode: If True, create debug visualization images
            debug_output_dir: Directory to save debug images
        """
        self.debug_mode = debug_mode
        self.debug_output_dir = Path(debug_output_dir)
        
        if self.debug_mode:
            self.debug_output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Debug mode enabled: {self.debug_output_dir}")
        
        logger.info(
            f"ClothingRegionExtractor initialized: "
            f"debug_mode={self.debug_mode}, "
            f"head_exclusion={HEAD_EXCLUSION_RATIO*100:.0f}%, "
            f"upper_body={UPPER_BODY_HEIGHT_RATIO*100:.0f}%, "
            f"lower_body={LOWER_BODY_HEIGHT_RATIO*100:.0f}%"
        )
    
    def _ensure_coordinates_in_bounds(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        frame_width: int,
        frame_height: int,
    ) -> Tuple[int, int, int, int]:
        """
        Ensure region coordinates stay within frame boundaries.
        
        Args:
            x, y, width, height: Region coordinates
            frame_width: Original frame width
            frame_height: Original frame height
        
        Returns:
            (x, y, width, height) adjusted to frame bounds
        """
        # Clamp top-left corner
        x = max(0, int(x))
        y = max(0, int(y))
        
        # Clamp bottom-right corner
        right = min(frame_width, int(x + width))
        bottom = min(frame_height, int(y + height))
        
        # Recalculate width/height
        width = max(1, right - x)
        height = max(1, bottom - y)
        
        return x, y, width, height
    
    def _ensure_region_in_person_bbox(
        self,
        region_x: float,
        region_y: float,
        region_width: float,
        region_height: float,
        person_bbox: Dict[str, int],
    ) -> Tuple[int, int, int, int]:
        """
        Ensure region stays inside person bounding box.
        
        Args:
            region_x, region_y, region_width, region_height: Region coordinates
            person_bbox: Person detection bbox {x, y, width, height}
        
        Returns:
            (x, y, width, height) adjusted to person bbox bounds
        """
        px = person_bbox["x"]
        py = person_bbox["y"]
        pw = person_bbox["width"]
        ph = person_bbox["height"]
        
        # Ensure region starts inside person bbox
        x = max(px, int(region_x))
        y = max(py, int(region_y))
        
        # Ensure region ends inside person bbox
        right = min(px + pw, int(region_x + region_width))
        bottom = min(py + ph, int(region_y + region_height))
        
        # Recalculate width/height
        width = max(1, right - x)
        height = max(1, bottom - y)
        
        return x, y, width, height
    
    def extract_regions(
        self,
        frame_path: Path,
        detection_id: str,
        person_bbox: Dict[str, int],
    ) -> RegionExtractionResult:
        """
        Extract upper and lower clothing regions from a person detection.
        
        Args:
            frame_path: Path to frame image
            detection_id: ID from STEP 5 person detection
            person_bbox: Person detection {x, y, width, height}
        
        Returns:
            RegionExtractionResult with extracted regions
        """
        # Read image to get dimensions
        try:
            image = cv2.imread(str(frame_path))
            if image is None:
                result = RegionExtractionResult(
                    detection_id, str(frame_path), person_bbox, 0, 0
                )
                result.status = "failed"
                result.error = "Unable to read image file"
                logger.error(f"Failed to read image: {frame_path}")
                return result
        except Exception as e:
            result = RegionExtractionResult(
                detection_id, str(frame_path), person_bbox, 0, 0
            )
            result.status = "failed"
            result.error = f"Error reading image: {str(e)}"
            logger.error(f"Error reading {frame_path}: {e}")
            return result
        
        frame_height, frame_width = image.shape[:2]
        
        result = RegionExtractionResult(
            detection_id, str(frame_path), person_bbox, frame_width, frame_height
        )
        
        # Validate person bounding box
        if not person_bbox or "x" not in person_bbox or "y" not in person_bbox:
            result.status = "failed"
            result.error = "Invalid person bounding box: missing x or y"
            return result
        
        if "width" not in person_bbox or "height" not in person_bbox:
            result.status = "failed"
            result.error = "Invalid person bounding box: missing width or height"
            return result
        
        px = person_bbox["x"]
        py = person_bbox["y"]
        pw = person_bbox["width"]
        ph = person_bbox["height"]
        
        # Validate box dimensions
        if pw <= 0 or ph <= 0:
            result.status = "failed"
            result.error = f"Invalid person bounding box: zero or negative size ({pw}x{ph})"
            return result
        
        # Check if box is entirely outside frame
        if px >= frame_width or py >= frame_height:
            result.status = "failed"
            result.error = "Person bounding box entirely outside frame"
            return result
        
        try:
            # Extract upper-body region (shirt)
            upper_start = py + int(ph * UPPER_BODY_START_RATIO)
            upper_height = int(ph * UPPER_BODY_HEIGHT_RATIO)
            upper_x = px + int(pw * HORIZONTAL_MARGIN_RATIO)
            upper_width = pw - int(2 * pw * HORIZONTAL_MARGIN_RATIO)
            
            # Ensure bounds
            upper_x, upper_start, upper_width, upper_height = \
                self._ensure_coordinates_in_bounds(
                    upper_x, upper_start, upper_width, upper_height,
                    frame_width, frame_height
                )
            upper_x, upper_start, upper_width, upper_height = \
                self._ensure_region_in_person_bbox(
                    upper_x, upper_start, upper_width, upper_height,
                    person_bbox
                )
            
            upper_region = ClothingRegion(
                region_type="upper_body",
                x=upper_x,
                y=upper_start,
                width=upper_width,
                height=upper_height,
            )
            result.set_upper_body_region(upper_region)
            
            # Extract lower-body region (pants)
            lower_start = py + int(ph * LOWER_BODY_START_RATIO)
            lower_height = int(ph * LOWER_BODY_HEIGHT_RATIO)
            lower_x = px + int(pw * HORIZONTAL_MARGIN_RATIO)
            lower_width = pw - int(2 * pw * HORIZONTAL_MARGIN_RATIO)
            
            # Ensure bounds
            lower_x, lower_start, lower_width, lower_height = \
                self._ensure_coordinates_in_bounds(
                    lower_x, lower_start, lower_width, lower_height,
                    frame_width, frame_height
                )
            lower_x, lower_start, lower_width, lower_height = \
                self._ensure_region_in_person_bbox(
                    lower_x, lower_start, lower_width, lower_height,
                    person_bbox
                )
            
            lower_region = ClothingRegion(
                region_type="lower_body",
                x=lower_x,
                y=lower_start,
                width=lower_width,
                height=lower_height,
            )
            result.set_lower_body_region(lower_region)
            
            result.status = "processed"
            logger.debug(
                f"Extracted regions for detection {detection_id}: "
                f"upper ({upper_width}x{upper_height}) lower ({lower_width}x{lower_height})"
            )
            
            # Generate debug visualization if enabled
            if self.debug_mode:
                self._generate_debug_image(
                    image, frame_path, detection_id, person_bbox,
                    upper_region, lower_region
                )
            
        except Exception as e:
            result.status = "failed"
            result.error = f"Error extracting regions: {str(e)}"
            logger.error(f"Error extracting regions for {detection_id}: {e}")
        
        return result
    
    def extract_regions_batch(
        self,
        frame_path: Path,
        detections: List[Dict[str, Any]],
    ) -> List[RegionExtractionResult]:
        """
        Extract regions for multiple people in one frame.
        
        Args:
            frame_path: Path to frame image
            detections: List of detection dicts {detection_id, x, y, width, height}
        
        Returns:
            List of RegionExtractionResult objects
        """
        results = []
        for detection in detections:
            detection_id = detection.get("detection_id", str(uuid4()))
            person_bbox = {
                "x": detection.get("x", 0),
                "y": detection.get("y", 0),
                "width": detection.get("width", 0),
                "height": detection.get("height", 0),
            }
            result = self.extract_regions(frame_path, detection_id, person_bbox)
            results.append(result)
        
        return results
    
    def _generate_debug_image(
        self,
        image: np.ndarray,
        frame_path: Path,
        detection_id: str,
        person_bbox: Dict[str, int],
        upper_region: ClothingRegion,
        lower_region: ClothingRegion,
    ) -> None:
        """
        Generate debug visualization with regions drawn.
        
        Args:
            image: Image array (BGR)
            frame_path: Original frame path
            detection_id: Person detection ID
            person_bbox: Person bounding box
            upper_region: Upper-body region
            lower_region: Lower-body region
        """
        try:
            debug_image = image.copy()
            
            # Draw person bounding box
            px, py = person_bbox["x"], person_bbox["y"]
            pw, ph = person_bbox["width"], person_bbox["height"]
            cv2.rectangle(
                debug_image,
                (px, py),
                (px + pw, py + ph),
                (0, 255, 0),  # Green
                2
            )
            
            # Draw upper-body region
            ux, uy = upper_region.x, upper_region.y
            uw, uh = upper_region.width, upper_region.height
            cv2.rectangle(
                debug_image,
                (ux, uy),
                (ux + uw, uy + uh),
                (255, 0, 0),  # Blue
                2
            )
            cv2.putText(
                debug_image, "SHIRT",
                (ux + 5, uy + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                1
            )
            
            # Draw lower-body region
            lx, ly = lower_region.x, lower_region.y
            lw, lh = lower_region.width, lower_region.height
            cv2.rectangle(
                debug_image,
                (lx, ly),
                (lx + lw, ly + lh),
                (0, 0, 255),  # Red
                2
            )
            cv2.putText(
                debug_image, "PANTS",
                (lx + 5, ly + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1
            )
            
            # Label person
            cv2.putText(
                debug_image,
                f"PERSON {detection_id[:8]}",
                (px, py - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
            
            # Save debug image
            debug_path = self._get_debug_path(frame_path)
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(debug_path), debug_image)
            logger.debug(f"Saved debug image: {debug_path}")
            
        except Exception as e:
            logger.warning(f"Failed to generate debug image: {e}")
    
    def _get_debug_path(self, frame_path: Path) -> Path:
        """
        Get debug output path based on original frame path.
        
        Args:
            frame_path: Original frame path
        
        Returns:
            Debug image path
        """
        frame_path = Path(frame_path)
        # Extract camera_id and video_name from path
        # Expected: .../video_frames/camera_01/video_001/frame_000001.jpg
        parts = frame_path.parts
        
        if "video_frames" in parts:
            idx = parts.index("video_frames")
            if idx + 2 < len(parts):
                camera_id = parts[idx + 1]
                video_name = parts[idx + 2]
                frame_name = parts[idx + 3]
                
                # Create path: debug_output_dir/camera_id/video_name/frame_name_regions.jpg
                debug_name = frame_name.replace(".jpg", "_regions.jpg")
                return self.debug_output_dir / camera_id / video_name / debug_name
        
        # Fallback: use original filename with _regions suffix
        return self.debug_output_dir / f"{frame_path.stem}_regions.jpg"


# Singleton instance
_extractor_instance: Optional[ClothingRegionExtractor] = None


def get_extractor(
    debug_mode: bool = False,
    debug_output_dir: str = "backend/video_frames_debug",
) -> ClothingRegionExtractor:
    """
    Get or create the global ClothingRegionExtractor instance.
    
    Args:
        debug_mode: Enable debug visualization
        debug_output_dir: Directory for debug images
    
    Returns:
        ClothingRegionExtractor instance
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = ClothingRegionExtractor(
            debug_mode=debug_mode,
            debug_output_dir=debug_output_dir,
        )
    return _extractor_instance


def extract_regions(
    frame_path: Path,
    detection_id: str,
    person_bbox: Dict[str, int],
    debug_mode: bool = False,
) -> RegionExtractionResult:
    """
    Convenience function to extract regions for one person.
    
    Args:
        frame_path: Path to frame image
        detection_id: Person detection ID from STEP 5
        person_bbox: Person bounding box {x, y, width, height}
        debug_mode: Enable debug visualization
    
    Returns:
        RegionExtractionResult
    """
    extractor = get_extractor(debug_mode=debug_mode)
    return extractor.extract_regions(frame_path, detection_id, person_bbox)


def extract_regions_batch(
    frame_path: Path,
    detections: List[Dict[str, Any]],
    debug_mode: bool = False,
) -> List[RegionExtractionResult]:
    """
    Convenience function to extract regions for multiple people.
    
    Args:
        frame_path: Path to frame image
        detections: List of detection dicts
        debug_mode: Enable debug visualization
    
    Returns:
        List of RegionExtractionResult objects
    """
    extractor = get_extractor(debug_mode=debug_mode)
    return extractor.extract_regions_batch(frame_path, detections)
