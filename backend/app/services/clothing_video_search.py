"""
Clothing-Based Video Search Service (STEP 8)
==============================================

Orchestrates STEPS 4-7 to search disaster video frames for clothing matches.

Pipeline:
  1. Frame discovery (STEP 4 outputs): recursive scan backend/video_frames/
  2. Person detection (STEP 5): contour-based detection on each frame
  3. Clothing region extraction (STEP 6): proportional upper/lower body regions
  4. Color analysis (STEP 7): HSV-based dominant color detection
  5. Scoring: Transparent match scoring (50/50 upper/lower or 100 if single)
  6. Ranking: By match score, confidence, timestamp

No dependency on:
- existing auth, persons, matches, or database tables
- identity verification (returns "possible_sighting", "verification_required": true)
- GPU or external models
- cloud APIs or external services

TERMINOLOGY:
- "possible_sighting": Indicates a clothing match for investigation
- "verification_required": True on ALL candidates (clothing ≠ identity confirmation)
- Not called "match" or "found" or "confirmed" (prevents false claims)
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
import cv2
import numpy as np
from enum import Enum

from .video_processor import VideoProcessor
from .person_detector import PersonDetector
from .clothing_region_extractor import ClothingRegionExtractor
from .clothing_color_analyzer import ClothingColorAnalyzer

logger = logging.getLogger(__name__)

# Configuration
MIN_MATCH_SCORE = 35.0  # Lowered from 60 for real-world robustness (video compression, lighting variations)
DEFAULT_MAX_RESULTS = 100
FRAME_DISCOVERY_PATTERN = "frame_*.jpg"  # Pattern for frame files
# Resolve video frames directory relative to current working directory (backend/)
VIDEO_FRAMES_DIR = str(Path(".") / "video_frames")

# Scoring constants
UPPER_BODY_WEIGHT = 0.5  # 50% if both colors requested
LOWER_BODY_WEIGHT = 0.5  # 50% if both colors requested
SINGLE_BODY_WEIGHT = 1.0  # 100% if single color requested


class SightingStatus(str, Enum):
    """Status indicator for clothing match results"""
    POSSIBLE_SIGHTING = "possible_sighting"
    NO_MATCH = "no_match"
    ERROR = "error"


@dataclass
class ClothingCandidate:
    """Individual clothing match candidate from a frame"""
    
    frame_path: str
    camera_id: str
    frame_number: int
    timestamp_seconds: float
    person_id: int  # Person detection index in the frame
    match_score: float  # 0-100 (int)
    upper_body_detected: Optional[str]  # Color name or None
    upper_body_confidence: float
    lower_body_detected: Optional[str]  # Color name or None
    lower_body_confidence: float
    status: str = SightingStatus.POSSIBLE_SIGHTING
    verification_required: bool = True
    debug_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict"""
        data = asdict(self)
        data["match_score"] = int(self.match_score)  # Ensure int
        data["status"] = self.status
        data["verification_required"] = self.verification_required
        return data


@dataclass
class VideoSearchResult:
    """Result of clothing-based video search"""
    
    query: Dict[str, Any]  # Original search query (normalized)
    candidates: List[ClothingCandidate] = field(default_factory=list)
    total_candidates: int = 0
    status: str = "processed"
    frames_scanned: int = 0
    errors: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dict"""
        return {
            "query": self.query,
            "candidates": [c.to_dict() for c in self.candidates],
            "total_candidates": len(self.candidates),
            "status": self.status,
            "frames_scanned": self.frames_scanned,
            "errors": self.errors,
            "config": self.config,
        }


class ClothingVideoSearcher:
    """Orchestrates STEPS 4-7 for clothing-based video search"""
    
    def __init__(
        self,
        min_match_score: float = MIN_MATCH_SCORE,
        max_results: int = DEFAULT_MAX_RESULTS,
        confidence_threshold: float = 0.3,  # For detector & analyzer
        video_frames_dir: str = VIDEO_FRAMES_DIR,
        debug: bool = False,
    ):
        """
        Initialize the searcher with orchestrated services
        
        Args:
            min_match_score: Minimum score (0-100) to include in results
            max_results: Maximum candidates to return
            confidence_threshold: Detection confidence threshold (passed to STEP 5 & 7)
            video_frames_dir: Root directory for frame discovery
            debug: Enable debug logging
        """
        self.min_match_score = min_match_score
        self.max_results = max_results
        self.video_frames_dir = Path(video_frames_dir)
        self.debug = debug
        
        # Initialize orchestrated services
        self.person_detector = PersonDetector(confidence_threshold=confidence_threshold)
        self.region_extractor = ClothingRegionExtractor()
        self.color_analyzer = ClothingColorAnalyzer(confidence_threshold=confidence_threshold)
        
        logger.info(
            f"ClothingVideoSearcher initialized: "
            f"min_score={min_match_score}, max_results={max_results}, "
            f"frames_dir={video_frames_dir}"
        )
    
    def _normalize_query(
        self,
        upper_body_color: Optional[str] = None,
        lower_body_color: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Normalize color names to lowercase, validate they are supported
        
        Args:
            upper_body_color: Requested upper body color or None
            lower_body_color: Requested lower body color or None
            
        Returns:
            Tuple of (normalized_upper, normalized_lower)
            
        Raises:
            ValueError if color is not supported
        """
        from .clothing_color_analyzer import SUPPORTED_COLORS
        
        upper = None
        lower = None
        
        if upper_body_color is not None:
            upper = upper_body_color.lower().strip()
            if upper not in SUPPORTED_COLORS:
                raise ValueError(
                    f"Unsupported upper_body_color: {upper_body_color}. "
                    f"Supported: {', '.join(SUPPORTED_COLORS)}"
                )
        
        if lower_body_color is not None:
            lower = lower_body_color.lower().strip()
            if lower not in SUPPORTED_COLORS:
                raise ValueError(
                    f"Unsupported lower_body_color: {lower_body_color}. "
                    f"Supported: {', '.join(SUPPORTED_COLORS)}"
                )
        
        # At least one color must be specified
        if upper is None and lower is None:
            raise ValueError("At least one of upper_body_color or lower_body_color must be specified")
        
        return upper, lower
    
    def _discover_frames(self) -> List[Path]:
        """
        Discover all frame files recursively
        
        Pattern: backend/video_frames/camera_*/video_*/frame_*.jpg
        
        Returns:
            List of frame file paths, sorted chronologically
        """
        if not self.video_frames_dir.exists():
            logger.warning(f"Video frames directory not found: {self.video_frames_dir}")
            return []
        
        # Recursive glob for frames
        frames = list(self.video_frames_dir.glob(f"camera_*/video_*/{FRAME_DISCOVERY_PATTERN}"))
        
        # Sort by path for consistent ordering (camera_id, video_id, frame_number)
        frames.sort()
        
        logger.info(f"Discovered {len(frames)} frames for search")
        return frames
    
    def _extract_frame_metadata(self, frame_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from frame file path
        
        Path format: .../camera_XXX/video_YYY/frame_ZZZ.jpg
        
        Args:
            frame_path: Path to frame file
            
        Returns:
            Dict with camera_id, video_id, frame_number, timestamp_seconds
        """
        parts = frame_path.parts
        
        # Walk backward from filename
        frame_filename = parts[-1]  # frame_ZZZ.jpg
        frame_number = int(frame_filename.replace("frame_", "").replace(".jpg", ""))
        
        video_id = parts[-2]  # video_YYY
        camera_id = parts[-3]  # camera_XXX
        
        # Estimate timestamp (assuming 2-second frame intervals from STEP 4)
        timestamp_seconds = frame_number * 2.0
        
        return {
            "camera_id": camera_id,
            "video_id": video_id,
            "frame_number": frame_number,
            "timestamp_seconds": timestamp_seconds,
        }
    
    def _calculate_match_score(
        self,
        query_upper: Optional[str],
        query_lower: Optional[str],
        detected_upper: Optional[str],
        detected_upper_conf: float,
        detected_lower: Optional[str],
        detected_lower_conf: float,
    ) -> float:
        """
        Calculate transparent match score (0-100, int)
        
        Scoring rules:
        - If both colors requested: upper_score + lower_score (50/50 split)
        - If single color requested: single_score * confidence
        - ONLY returns score if colors match (no partial scores)
        
        Args:
            query_upper: Requested upper body color (or None)
            query_lower: Requested lower body color (or None)
            detected_upper: Detected upper body color (or None)
            detected_upper_conf: Detection confidence (0-1)
            detected_lower: Detected lower body color (or None)
            detected_lower_conf: Detection confidence (0-1)
            
        Returns:
            Score as float 0-100 (only for matching colors)
        """
        score = 0.0
        
        # Case 1: Both colors requested
        if query_upper is not None and query_lower is not None:
            # Upper body score (50 points if match)
            if detected_upper is not None and detected_upper.lower() == query_upper.lower():
                score += 50.0 * detected_upper_conf
            
            # Lower body score (50 points if match)
            if detected_lower is not None and detected_lower.lower() == query_lower.lower():
                score += 50.0 * detected_lower_conf
        
        # Case 2: Only upper body color requested
        elif query_upper is not None:
            if detected_upper is not None and detected_upper.lower() == query_upper.lower():
                score = 100.0 * detected_upper_conf
        
        # Case 3: Only lower body color requested
        elif query_lower is not None:
            if detected_lower is not None and detected_lower.lower() == query_lower.lower():
                score = 100.0 * detected_lower_conf
        
        # Clamp to 0-100
        return min(100.0, max(0.0, score))
    
    def _process_frame(
        self,
        frame_path: Path,
        query_upper: Optional[str],
        query_lower: Optional[str],
    ) -> List[ClothingCandidate]:
        """
        Process a single frame through STEPS 5-7, returning candidates
        
        Orchestration:
        1. Read frame image
        2. Detect persons (STEP 5)
        3. For each person: extract regions (STEP 6) → analyze colors (STEP 7)
        4. Score matches and create candidates
        
        Args:
            frame_path: Path to frame file
            query_upper: Requested upper body color
            query_lower: Requested lower body color
            
        Returns:
            List of ClothingCandidate objects (may be empty)
        """
        candidates = []
        
        try:
            # Read frame
            image = cv2.imread(str(frame_path))
            if image is None:
                logger.warning(f"Failed to read frame: {frame_path}")
                return candidates
            
            # Extract metadata
            metadata = self._extract_frame_metadata(frame_path)
            
            # STEP 5: Detect persons
            detection_result = self.person_detector.detect_frame(frame_path)
            
            if not detection_result.detections:
                # No persons in frame, skip
                return candidates
            
            # STEP 6 & 7: For each detected person
            for person_idx, detection in enumerate(detection_result.detections):
                try:
                    # Extract bounding box from detection object attributes
                    x = detection.x
                    y = detection.y
                    w = detection.width
                    h = detection.height
                    person_bbox = {"x": x, "y": y, "width": w, "height": h}
                    
                    # STEP 6: Extract clothing regions
                    detection_id = f"person_{person_idx}"
                    region_result = self.region_extractor.extract_regions(
                        frame_path=frame_path,
                        detection_id=detection_id,
                        person_bbox=person_bbox,
                    )
                    
                    # Extract crop images from regions
                    upper_crop = None
                    lower_crop = None
                    if region_result.upper_body_region:
                        region = region_result.upper_body_region
                        upper_crop = image[region.y:region.y+region.height, region.x:region.x+region.width]
                    if region_result.lower_body_region:
                        region = region_result.lower_body_region
                        lower_crop = image[region.y:region.y+region.height, region.x:region.x+region.width]
                    
                    # STEP 7: Analyze colors
                    color_result = self.color_analyzer.analyze_clothing_from_crops(
                        upper_body_crop=upper_crop,
                        lower_body_crop=lower_crop,
                        detection_id=detection_id,
                    )
                    
                    # Extract detected colors (use .color not .color_name)
                    detected_upper = color_result.upper_body_color.color if color_result.upper_body_color else None
                    detected_upper_conf = color_result.upper_body_color.confidence if color_result.upper_body_color else 0.0
                    detected_lower = color_result.lower_body_color.color if color_result.lower_body_color else None
                    detected_lower_conf = color_result.lower_body_color.confidence if color_result.lower_body_color else 0.0
                    
                    # Calculate score
                    score = self._calculate_match_score(
                        query_upper=query_upper,
                        query_lower=query_lower,
                        detected_upper=detected_upper,
                        detected_upper_conf=detected_upper_conf,
                        detected_lower=detected_lower,
                        detected_lower_conf=detected_lower_conf,
                    )
                    
                    # Create candidate if score meets threshold
                    if score >= self.min_match_score:
                        candidate = ClothingCandidate(
                            frame_path=str(frame_path),
                            camera_id=metadata["camera_id"],
                            frame_number=metadata["frame_number"],
                            timestamp_seconds=metadata["timestamp_seconds"],
                            person_id=person_idx,
                            match_score=score,
                            upper_body_detected=detected_upper,
                            upper_body_confidence=detected_upper_conf,
                            lower_body_detected=detected_lower,
                            lower_body_confidence=detected_lower_conf,
                            status=SightingStatus.POSSIBLE_SIGHTING,
                            verification_required=True,
                            debug_info={
                                "person_bbox": person_bbox,
                                "detection_confidence": detection.confidence,
                            },
                        )
                        candidates.append(candidate)
                
                except Exception as e:
                    logger.warning(f"Error processing person {person_idx} in {frame_path}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error processing frame {frame_path}: {e}")
            return candidates
        
        return candidates
    
    def search(
        self,
        upper_body_color: Optional[str] = None,
        lower_body_color: Optional[str] = None,
    ) -> VideoSearchResult:
        """
        Main search entry point: orchestrate full pipeline
        
        Args:
            upper_body_color: Requested upper body color (case-insensitive)
            lower_body_color: Requested lower body color (case-insensitive)
            
        Returns:
            VideoSearchResult with candidates ranked by score
            
        Raises:
            ValueError if query is invalid
        """
        # Normalize and validate query
        try:
            query_upper, query_lower = self._normalize_query(
                upper_body_color=upper_body_color,
                lower_body_color=lower_body_color,
            )
        except ValueError as e:
            logger.error(f"Invalid search query: {e}")
            return VideoSearchResult(
                query={
                    "upper_body_color": upper_body_color,
                    "lower_body_color": lower_body_color,
                },
                status="failed",
                errors=[str(e)],
                config={"min_match_score": self.min_match_score},
            )
        
        # Discover frames
        frames = self._discover_frames()
        
        # Process all frames
        all_candidates = []
        errors = []
        
        for i, frame_path in enumerate(frames):
            if self.debug and i % 100 == 0:
                logger.debug(f"Processing frame {i+1}/{len(frames)}: {frame_path}")
            
            try:
                candidates = self._process_frame(
                    frame_path=frame_path,
                    query_upper=query_upper,
                    query_lower=query_lower,
                )
                all_candidates.extend(candidates)
            except Exception as e:
                logger.warning(f"Error processing frame {frame_path}: {e}")
                errors.append(f"Frame {frame_path}: {str(e)}")
                continue
        
        # Rank candidates: score DESC, confidence DESC, timestamp ASC
        all_candidates.sort(
            key=lambda c: (
                -c.match_score,  # Higher score first
                -(max(c.upper_body_confidence, c.lower_body_confidence)),  # Higher confidence first
                c.timestamp_seconds,  # Earlier timestamp first
            )
        )
        
        # Limit results
        ranked_candidates = all_candidates[:self.max_results]
        
        # Build result
        result = VideoSearchResult(
            query={
                "upper_body_color": query_upper,
                "lower_body_color": query_lower,
            },
            candidates=ranked_candidates,
            total_candidates=len(ranked_candidates),
            status="processed",
            frames_scanned=len(frames),
            errors=errors,
            config={
                "min_match_score": self.min_match_score,
                "max_results": self.max_results,
                "threshold_applied": self.min_match_score,
            },
        )
        
        logger.info(
            f"Search complete: scanned {len(frames)} frames, "
            f"found {len(ranked_candidates)} candidates (threshold: {self.min_match_score})"
        )
        
        return result


def get_searcher(
    min_match_score: float = MIN_MATCH_SCORE,
    max_results: int = DEFAULT_MAX_RESULTS,
    confidence_threshold: float = 0.3,
    video_frames_dir: Optional[str] = None,
    debug: bool = False,
) -> ClothingVideoSearcher:
    """Factory function to create a searcher instance.
    
    Args:
        min_match_score: Minimum match score threshold (default 60.0)
        max_results: Maximum results to return (default 100)
        confidence_threshold: Detection confidence threshold (default 0.3)
        video_frames_dir: Path to video frames directory (defaults to ./video_frames)
        debug: Enable debug logging (default False)
        
    Returns:
        ClothingVideoSearcher instance with resolved absolute paths
    """
    if video_frames_dir is None:
        video_frames_dir = str(Path(VIDEO_FRAMES_DIR).resolve())
    else:
        video_frames_dir = str(Path(video_frames_dir).resolve())
    
    logger.info(f"Creating searcher with video_frames_dir: {video_frames_dir}")
    
    return ClothingVideoSearcher(
        min_match_score=min_match_score,
        max_results=max_results,
        confidence_threshold=confidence_threshold,
        video_frames_dir=video_frames_dir,
        debug=debug,
    )


# Entry point for standalone search
def search_by_clothing(
    upper_body_color: Optional[str] = None,
    lower_body_color: Optional[str] = None,
    min_match_score: float = MIN_MATCH_SCORE,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> Dict[str, Any]:
    """
    Convenient entry point for clothing-based search
    
    Returns search result as dict
    """
    searcher = get_searcher(
        min_match_score=min_match_score,
        max_results=max_results,
    )
    result = searcher.search(
        upper_body_color=upper_body_color,
        lower_body_color=lower_body_color,
    )
    return result.to_dict()
