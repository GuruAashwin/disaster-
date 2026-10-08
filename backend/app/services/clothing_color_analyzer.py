"""
Clothing Color Analysis Service (STEP 7) - ENHANCED
====================================================

Isolated module for analyzing dominant clothing colors from cropped regions.

ENHANCED PIPELINE:
  1. Pixel Selection: Center-region sampling + outlier removal
  2. Lighting Normalization: CLAHE for robust brightness handling
  3. Color Analysis: HSV (hue) + LAB (perceptual distance)
  4. Dominant Color: K-means clustering on valid pixels
  5. Confidence: Multi-signal scoring (color agreement + strength + coverage + margin)
  6. Special Cases: Dark colors, bright colors, red wrapping

No GPU, no ML models, CPU-friendly.
Preserves existing interface and output structure.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
import cv2
import numpy as np
from uuid import uuid4

logger = logging.getLogger(__name__)

# Standardized color categories
SUPPORTED_COLORS = [
    "black", "white", "gray", "red", "orange", "yellow",
    "green", "blue", "navy", "purple", "pink", "brown", "beige", "maroon",
]

# ============================================================================
# ENHANCED CONFIGURATION - Tunable parameters
# ============================================================================

# Pixel selection strategy
CENTER_CROP_RATIO = 0.75           # Use central 75% of crop
MIN_VALID_PIXELS = 50              # Minimum pixels for analysis
SKIN_COLOR_LAB_CENTER = np.array([60, 15, 25])  # Skin color in LAB
SKIN_COLOR_LAB_RANGE = 25          # LAB distance threshold for skin detection

# Lighting normalization
USE_CLAHE = True                   # Contrast Limited Adaptive Histogram Equalization
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_SIZE = 8

# Color space analysis
USE_LAB = True                     # Perceptual color distance verification
USE_HSV = True                     # Hue-based classification

# K-means clustering for dominant color
USE_KMEANS = True
KMEANS_K = 3
KMEANS_ATTEMPTS = 3
KMEANS_MAX_ITER = 100

# Confidence calculation signals
CONFIDENCE_THRESHOLD = 0.25
DARK_COLOR_VALUE_THRESHOLD = 80
BRIGHT_COLOR_VALUE_THRESHOLD = 180

# ============================================================================
# ENHANCED HSV COLOR RANGES
# ============================================================================

COLOR_RANGES = {
    "red": {
        "hue_ranges": [(0, 10), (170, 180)],  # Red wraps around
        "sat_min": 30,
        "val_min": 40,
    },
    "maroon": {
        "hue_ranges": [(0, 15), (165, 180)],  # Dark red
        "sat_min": 50,
        "val_range": (30, 100),
    },
    "orange": {
        "hue_ranges": [(10, 25)],
        "sat_min": 50,
        "val_min": 50,
    },
    "brown": {
        "hue_ranges": [(10, 25)],
        "sat_min": 50,
        "val_range": (30, 100),
    },
    "yellow": {
        "hue_ranges": [(20, 35)],
        "sat_min": 30,
        "val_min": 50,
    },
    "green": {
        "hue_ranges": [(35, 90)],
        "sat_min": 30,
        "val_min": 30,
    },
    "blue": {
        "hue_ranges": [(100, 130)],
        "sat_min": 40,
        "val_min": 50,
    },
    "navy": {
        "hue_ranges": [(100, 130)],
        "sat_min": 50,
        "val_range": (30, 100),
    },
    "purple": {
        "hue_ranges": [(130, 170)],
        "sat_min": 40,
        "val_min": 50,
    },
    "pink": {
        "hue_ranges": [(0, 20), (330, 360)],
        "sat_range": (15, 100),
        "val_min": 80,
    },
    "gray": {
        "sat_range": (0, 30),
        "val_range": (50, 200),
    },
    "white": {
        "sat_range": (0, 30),
        "val_min": 200,
    },
    "black": {
        "val_range": (0, 50),
    },
    "beige": {
        "hue_ranges": [(15, 35)],
        "sat_range": (15, 60),
        "val_min": 120,
    },
}

# LAB color reference points (L*, a*, b*) for perceptual verification
COLOR_LAB_REFS = {
    "red": [50, 50, 40],
    "maroon": [40, 45, 35],
    "orange": [60, 35, 50],
    "brown": [45, 25, 35],
    "yellow": [75, -5, 80],
    "green": [60, -50, 50],
    "blue": [50, -20, -50],
    "navy": [35, -10, -30],
    "purple": [45, 30, -50],
    "pink": [70, 30, -10],
    "gray": [128, 0, 0],
    "white": [95, 0, 0],
    "black": [20, 0, 0],
    "beige": [75, 5, 30],
}


class ClothingColor:
    """Single clothing color analysis result."""
    
    def __init__(
        self,
        color: str,
        confidence: float,
        pixel_count: int = 0,
        secondary_color: Optional[str] = None,
    ):
        """
        Initialize clothing color result.
        
        Args:
            color: Standardized color name (e.g., "red", "blue", "unknown")
            confidence: Confidence score 0.0-1.0 (not scientifically calibrated)
            pixel_count: Number of pixels matching this color
            secondary_color: Optional secondary dominant color
        """
        self.color = color
        self.confidence = float(confidence)
        self.pixel_count = int(pixel_count)
        self.secondary_color = secondary_color
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "color": self.color,
            "confidence": self.confidence,
            "pixel_count": self.pixel_count,
        }
        if self.secondary_color:
            result["secondary_color"] = self.secondary_color
        return result


class ClothingColorAnalysisResult:
    """Result of analyzing clothing colors for one person."""
    
    def __init__(self, detection_id: str):
        """
        Initialize analysis result.
        
        Args:
            detection_id: ID from STEP 5 person detection
        """
        self.detection_id = detection_id
        self.upper_body_color: Optional[ClothingColor] = None
        self.lower_body_color: Optional[ClothingColor] = None
        self.status: str = "pending"
        self.error: Optional[str] = None
    
    def set_upper_body_color(self, color: ClothingColor) -> None:
        """Set upper-body clothing color."""
        self.upper_body_color = color
    
    def set_lower_body_color(self, color: ClothingColor) -> None:
        """Set lower-body clothing color."""
        self.lower_body_color = color
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "detection_id": self.detection_id,
            "upper_body": self.upper_body_color.to_dict() if self.upper_body_color else None,
            "lower_body": self.lower_body_color.to_dict() if self.lower_body_color else None,
            "status": self.status,
            "error": self.error,
        }


class ClothingColorAnalyzer:
    """Enhanced clothing color analysis with multi-stage pipeline."""
    
    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        """Initialize analyzer."""
        self.confidence_threshold = max(0.0, min(1.0, confidence_threshold))
        logger.info(
            f"ClothingColorAnalyzer initialized (ENHANCED): "
            f"CLAHE={USE_CLAHE}, LAB={USE_LAB}, K-means={USE_KMEANS}, "
            f"threshold={self.confidence_threshold}"
        )
    
    def _get_center_region(self, image: np.ndarray) -> np.ndarray:
        """Extract center region to reduce border contamination."""
        if image is None or image.size == 0:
            return image
        
        height, width = image.shape[:2]
        center_h = int(height * CENTER_CROP_RATIO)
        center_w = int(width * CENTER_CROP_RATIO)
        
        y_start = (height - center_h) // 2
        x_start = (width - center_w) // 2
        
        return image[y_start:y_start+center_h, x_start:x_start+center_w]
    
    def _remove_skin_pixels(self, image: np.ndarray, hsv: np.ndarray) -> np.ndarray:
        """Remove likely skin-colored pixels (optional)."""
        if image is None or image.size == 0:
            return image
        
        # Skin in HSV typically: H 0-20, S 10-40, V 60-255
        lower_skin = np.array([0, 10, 60])
        upper_skin = np.array([20, 40, 255])
        
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Mark skin pixels as invalid (set to 0 in output)
        result = image.copy()
        result[skin_mask > 0] = 0
        
        return result
    
    def _apply_lighting_normalization(self, image: np.ndarray) -> np.ndarray:
        """Apply CLAHE for lighting robustness."""
        if not USE_CLAHE or image is None or image.size == 0:
            return image
        
        try:
            # Work on V channel of HSV for lighting normalization
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
            v_channel = hsv[:, :, 2].astype(np.uint8)
            
            # Apply CLAHE
            clahe = cv2.createCLAHE(
                clipLimit=CLAHE_CLIP_LIMIT,
                tileGridSize=(CLAHE_TILE_SIZE, CLAHE_TILE_SIZE)
            )
            v_normalized = clahe.apply(v_channel)
            
            # Reconstruct HSV
            hsv[:, :, 2] = v_normalized
            result_hsv = hsv.astype(np.uint8)
            
            # Convert back to BGR
            result_bgr = cv2.cvtColor(result_hsv, cv2.COLOR_HSV2BGR)
            return result_bgr
            
        except Exception as e:
            logger.warning(f"CLAHE normalization failed: {e}")
            return image
    
    def _get_valid_pixel_mask(self, hsv: np.ndarray) -> np.ndarray:
        """
        Get mask of valid clothing pixels (not extreme outliers).
        Returns binary mask where 1 = valid, 0 = invalid.
        
        This is VERY permissive - we want to include all legitimate clothing colors.
        Only filter genuine artifacts.
        """
        if hsv is None or hsv.size == 0:
            return np.array([], dtype=np.uint8)
        
        h, s, v = cv2.split(hsv)
        
        # Start with all pixels valid - this is key!
        valid = np.ones_like(v, dtype=np.uint8)
        
        # We only filter extreme artifacts, not normal colors
        # Normal colors include: black, white, gray, and all saturated colors
        
        # The only thing we want to filter is noise/artifacts:
        # - Extreme shadows: v < 3 (nearly pure black noise)
        # - Extreme noise: v at edges with erratic saturation
        
        # Filter only the most extreme pixels
        very_dark_noise = (v < 3)  # Noise floor
        valid[very_dark_noise] = 0
        
        return valid
    
    def _get_dominant_color_kmeans(self, image_bgr: np.ndarray, mask: np.ndarray) -> Tuple[Tuple[int,int,int], float]:
        """
        Use K-means to find dominant color from valid pixels.
        Returns ((B, G, R), cluster_strength).
        """
        if image_bgr is None or mask is None or mask.size == 0:
            return (128, 128, 128), 0.0
        
        # Get valid pixels
        valid_pixels = image_bgr[mask > 0]
        
        if valid_pixels.size < MIN_VALID_PIXELS * 3:  # Not enough pixels
            return (128, 128, 128), 0.0
        
        try:
            # Reshape for K-means
            data = valid_pixels.reshape((-1, 3)).astype(np.float32)
            
            # K-means clustering
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, KMEANS_MAX_ITER, 1.0)
            _, labels, centers = cv2.kmeans(
                data,
                KMEANS_K,
                None,
                criteria,
                KMEANS_ATTEMPTS,
                cv2.KMEANS_RANDOM_CENTERS
            )
            
            # Find strongest cluster (most pixels)
            unique, counts = np.unique(labels.flatten(), return_counts=True)
            strongest_cluster_idx = unique[np.argmax(counts)]
            strongest_cluster_count = np.max(counts)
            
            # Get dominant color
            dominant_bgr = tuple(centers[strongest_cluster_idx].astype(np.uint8))
            
            # Cluster strength as ratio of strongest cluster
            cluster_strength = strongest_cluster_count / len(data)
            
            return dominant_bgr, cluster_strength
            
        except Exception as e:
            logger.warning(f"K-means failed: {e}")
            return (128, 128, 128), 0.0
    
    def _classify_color_hsv(self, hsv: np.ndarray, mask: np.ndarray) -> Tuple[str, float]:
        """
        Classify color using HSV ranges.
        Returns (color_name, hsv_confidence).
        """
        if hsv is None or mask is None or mask.size == 0:
            return "unknown", 0.0
        
        color_scores = {}
        
        for color_name, color_spec in COLOR_RANGES.items():
            # Build HSV range mask for this color
            color_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            
            h, s, v = cv2.split(hsv)
            
            # Check hue ranges
            if "hue_ranges" in color_spec:
                hue_mask = np.zeros_like(h)
                for h_min, h_max in color_spec["hue_ranges"]:
                    hue_mask |= (h >= h_min) & (h <= h_max)
                color_mask |= hue_mask
            else:
                color_mask = np.ones_like(h)  # All hues valid
            
            # Check saturation range
            if "sat_range" in color_spec:
                s_min, s_max = color_spec["sat_range"]
                color_mask &= (s >= s_min) & (s <= s_max)
            elif "sat_min" in color_spec:
                color_mask &= (s >= color_spec["sat_min"])
            
            # Check value range
            if "val_range" in color_spec:
                v_min, v_max = color_spec["val_range"]
                color_mask &= (v >= v_min) & (v <= v_max)
            elif "val_min" in color_spec:
                color_mask &= (v >= color_spec["val_min"])
            
            # Count matching pixels
            color_mask &= mask  # Only count valid pixels
            match_count = np.count_nonzero(color_mask)
            
            if match_count > 0:
                color_scores[color_name] = match_count
        
        if not color_scores:
            return "unknown", 0.0
        
        # Sorted by match count
        sorted_colors = sorted(color_scores.items(), key=lambda x: x[1], reverse=True)
        dominant_color = sorted_colors[0][0]
        dominant_count = sorted_colors[0][1]
        total_valid = np.count_nonzero(mask)
        
        # HSV confidence as ratio
        hsv_conf = dominant_count / total_valid if total_valid > 0 else 0.0
        
        return dominant_color, hsv_conf
    
    def _classify_color_lab(self, image_bgr: np.ndarray, dominant_bgr: Tuple[int,int,int]) -> Tuple[str, float]:
        """
        Classify color using LAB perceptual distance.
        Returns (color_name, lab_confidence).
        """
        if not USE_LAB or image_bgr is None:
            return "unknown", 0.0
        
        try:
            # Convert dominant color to LAB
            dominant_img = np.uint8([[dominant_bgr]])
            dominant_lab = cv2.cvtColor(dominant_img, cv2.COLOR_BGR2LAB)[0][0]
            
            best_color = "unknown"
            best_distance = float('inf')
            
            for color_name, lab_ref in COLOR_LAB_REFS.items():
                distance = np.linalg.norm(dominant_lab.astype(np.float32) - np.array(lab_ref))
                
                if distance < best_distance:
                    best_distance = distance
                    best_color = color_name
            
            # Convert distance to confidence (inverse: closer = higher confidence)
            # Max reasonable distance ~80, min ~0
            lab_conf = max(0.0, 1.0 - (best_distance / 80.0))
            
            return best_color, lab_conf
            
        except Exception as e:
            logger.warning(f"LAB classification failed: {e}")
            return "unknown", 0.0
    
    def _calculate_confidence(
        self,
        hsv_color: str,
        hsv_conf: float,
        lab_color: str,
        lab_conf: float,
        cluster_strength: float,
        valid_pixel_ratio: float,
    ) -> float:
        """
        Calculate final confidence from multiple signals.
        Weighted to prioritize HSV match (pixel ratio) as primary signal
        while using LAB and clustering for verification.
        """
        # Signal 1: HSV confidence (pixel match ratio) - PRIMARY
        # This is the core measurement
        hsv_signal = hsv_conf * 1.0
        
        # Signal 2: Cluster strength (K-means dominant color)
        # Verification that detected color is coherent
        cluster_signal = cluster_strength * 0.7
        
        # Signal 3: LAB confidence (perceptual distance)
        # Secondary verification
        lab_signal = lab_conf * 0.5
        
        # Signal 4: Color space agreement
        if hsv_color == lab_color and hsv_color != "unknown":
            agreement_signal = 0.8
        else:
            agreement_signal = 0.0
        
        # Signal 5: Pixel coverage
        coverage_signal = min(1.0, valid_pixel_ratio * 1.5) * 0.4
        
        # Weighted average (emphasis on HSV primary measurement)
        signals = [hsv_signal, cluster_signal, lab_signal, agreement_signal, coverage_signal]
        signal_weights = [1.0, 0.7, 0.5, 0.3, 0.4]
        
        weighted_sum = sum(s * w for s, w in zip(signals, signal_weights))
        total_weight = sum(signal_weights)
        
        final_conf = weighted_sum / total_weight
        return float(final_conf)
    
    def analyze_region(self, image: np.ndarray) -> ClothingColor:
        """
        Analyze a clothing region through the enhanced pipeline.
        """
        try:
            if image is None or image.size == 0:
                return ClothingColor("unknown", 0.0, 0)
            
            # Step 1: Center-region sampling
            center_image = self._get_center_region(image)
            
            # Step 2: Lighting normalization
            normalized_image = self._apply_lighting_normalization(center_image)
            
            # Step 3: Get valid pixel mask
            hsv = cv2.cvtColor(normalized_image, cv2.COLOR_BGR2HSV)
            valid_mask = self._get_valid_pixel_mask(hsv)
            
            valid_count = np.count_nonzero(valid_mask)
            if valid_count < MIN_VALID_PIXELS:
                return ClothingColor("unknown", 0.0, 0)
            
            # Step 4: HSV classification
            hsv_color, hsv_conf = self._classify_color_hsv(hsv, valid_mask)
            
            # Step 5: K-means dominant color
            dominant_bgr, cluster_strength = self._get_dominant_color_kmeans(
                normalized_image, valid_mask
            )
            
            # Step 6: LAB classification
            lab_color, lab_conf = self._classify_color_lab(normalized_image, dominant_bgr)
            
            # Step 7: Final color decision
            final_color = hsv_color if hsv_color != "unknown" else lab_color
            
            # Step 8: Confidence calculation
            total_pixels = normalized_image.shape[0] * normalized_image.shape[1]
            valid_pixel_ratio = valid_count / total_pixels
            
            confidence = self._calculate_confidence(
                hsv_color, hsv_conf, lab_color, lab_conf,
                cluster_strength, valid_pixel_ratio
            )
            
            # Step 9: Threshold check
            if confidence < self.confidence_threshold:
                final_color = "unknown"
            
            return ClothingColor(final_color, confidence, valid_count)
            
        except Exception as e:
            logger.error(f"Error analyzing region: {e}")
            return ClothingColor("unknown", 0.0, 0)
    
    def analyze_clothing_from_file(
        self,
        frame_path: Path,
        upper_body_bbox: Dict[str, int],
        lower_body_bbox: Dict[str, int],
        detection_id: str = "unknown",
    ) -> ClothingColorAnalysisResult:
        """
        Analyze clothing colors from STEP 6 regions in a frame file.
        
        Args:
            frame_path: Path to original frame image
            upper_body_bbox: Upper-body region {x, y, width, height}
            lower_body_bbox: Lower-body region {x, y, width, height}
            detection_id: Detection ID from STEP 5
        
        Returns:
            ClothingColorAnalysisResult with upper and lower body colors
        """
        result = ClothingColorAnalysisResult(detection_id)
        
        # Read frame
        try:
            frame = cv2.imread(str(frame_path))
            if frame is None:
                result.status = "failed"
                result.error = "Unable to read frame image"
                logger.error(f"Failed to read frame: {frame_path}")
                return result
        except Exception as e:
            result.status = "failed"
            result.error = f"Error reading frame: {str(e)}"
            logger.error(f"Error reading frame {frame_path}: {e}")
            return result
        
        try:
            # Crop upper-body region
            ux, uy = upper_body_bbox["x"], upper_body_bbox["y"]
            uw, uh = upper_body_bbox["width"], upper_body_bbox["height"]
            upper_crop = frame[uy:uy+uh, ux:ux+uw]
            
            # Crop lower-body region
            lx, ly = lower_body_bbox["x"], lower_body_bbox["y"]
            lw, lh = lower_body_bbox["width"], lower_body_bbox["height"]
            lower_crop = frame[ly:ly+lh, lx:lx+lw]
            
            # Analyze colors
            upper_color = self.analyze_region(upper_crop)
            lower_color = self.analyze_region(lower_crop)
            
            result.set_upper_body_color(upper_color)
            result.set_lower_body_color(lower_color)
            result.status = "processed"
            
            logger.debug(
                f"Analyzed colors for detection {detection_id}: "
                f"upper={upper_color.color} ({upper_color.confidence:.2f}), "
                f"lower={lower_color.color} ({lower_color.confidence:.2f})"
            )
        
        except Exception as e:
            result.status = "failed"
            result.error = f"Error analyzing regions: {str(e)}"
            logger.error(f"Error analyzing regions for {detection_id}: {e}")
        
        return result
    
    def analyze_clothing_from_crops(
        self,
        upper_body_crop: np.ndarray,
        lower_body_crop: np.ndarray,
        detection_id: str = "unknown",
    ) -> ClothingColorAnalysisResult:
        """
        Analyze clothing colors from pre-cropped region arrays.
        
        Args:
            upper_body_crop: Upper-body region image array (BGR)
            lower_body_crop: Lower-body region image array (BGR)
            detection_id: Detection ID from STEP 5
        
        Returns:
            ClothingColorAnalysisResult with upper and lower body colors
        """
        result = ClothingColorAnalysisResult(detection_id)
        
        try:
            upper_color = self.analyze_region(upper_body_crop)
            lower_color = self.analyze_region(lower_body_crop)
            
            result.set_upper_body_color(upper_color)
            result.set_lower_body_color(lower_color)
            result.status = "processed"
            
        except Exception as e:
            result.status = "failed"
            result.error = f"Error analyzing regions: {str(e)}"
            logger.error(f"Error analyzing regions: {e}")
        
        return result


# Singleton instance
_analyzer_instance: Optional[ClothingColorAnalyzer] = None


def get_analyzer(confidence_threshold: float = CONFIDENCE_THRESHOLD) -> ClothingColorAnalyzer:
    """
    Get or create the global ClothingColorAnalyzer instance.
    
    Args:
        confidence_threshold: Confidence threshold for color classification
    
    Returns:
        ClothingColorAnalyzer instance
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ClothingColorAnalyzer(confidence_threshold=confidence_threshold)
    return _analyzer_instance


def analyze_clothing_from_file(
    frame_path: Path,
    upper_body_bbox: Dict[str, int],
    lower_body_bbox: Dict[str, int],
    detection_id: str = "unknown",
) -> ClothingColorAnalysisResult:
    """
    Convenience function to analyze clothing from a frame file.
    
    Args:
        frame_path: Path to original frame image
        upper_body_bbox: Upper-body region {x, y, width, height}
        lower_body_bbox: Lower-body region {x, y, width, height}
        detection_id: Detection ID from STEP 5
    
    Returns:
        ClothingColorAnalysisResult
    """
    analyzer = get_analyzer()
    return analyzer.analyze_clothing_from_file(
        frame_path, upper_body_bbox, lower_body_bbox, detection_id
    )


def analyze_clothing_from_crops(
    upper_body_crop: np.ndarray,
    lower_body_crop: np.ndarray,
    detection_id: str = "unknown",
) -> ClothingColorAnalysisResult:
    """
    Convenience function to analyze clothing from pre-cropped arrays.
    
    Args:
        upper_body_crop: Upper-body region image array (BGR)
        lower_body_crop: Lower-body region image array (BGR)
        detection_id: Detection ID from STEP 5
    
    Returns:
        ClothingColorAnalysisResult
    """
    analyzer = get_analyzer()
    return analyzer.analyze_clothing_from_crops(
        upper_body_crop, lower_body_crop, detection_id
    )
