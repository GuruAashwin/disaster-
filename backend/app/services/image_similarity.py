"""
Image Similarity Service
========================

Computes visual similarity between two images using:
1. Mean Squared Error (MSE) for pixel-level comparison
2. ORB feature matching for invariant keypoint matching
3. Histogram comparison for color distribution similarity

Returns a 0-100 confidence score for face/person matching.

No external ML dependencies required - uses only OpenCV and NumPy.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def load_and_preprocess_image(image_path: str, max_dim: int = 500) -> Optional[np.ndarray]:
    """
    Load an image and preprocess it for comparison.
    
    Args:
        image_path: Path to image file
        max_dim: Maximum dimension to resize to
        
    Returns:
        Preprocessed grayscale image or None if failed
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Failed to load image: {image_path}")
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Resize if too large
        h, w = gray.shape
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return gray
    except Exception as e:
        logger.error(f"Error preprocessing image {image_path}: {e}")
        return None


def compute_mse_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute similarity based on Mean Squared Error (MSE).
    
    Lower MSE = more similar. Converted to 0-1 similarity score.
    
    Args:
        img1: First image (grayscale)
        img2: Second image (grayscale)
        
    Returns:
        Similarity score 0-1
    """
    try:
        # Resize img2 to match img1 dimensions
        h1, w1 = img1.shape
        h2, w2 = img2.shape
        
        if (h1, w1) != (h2, w2):
            img2 = cv2.resize(img2, (w1, h1), interpolation=cv2.INTER_AREA)
        
        # Compute MSE
        mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
        
        # Convert MSE to similarity (normalize by max pixel value squared)
        # MSE range: 0 to 65025 (for 8-bit images), map to 1 to 0
        max_mse = 255 * 255
        similarity = max(0.0, 1.0 - (mse / max_mse))
        
        return float(similarity)
    except Exception as e:
        logger.error(f"Error computing MSE: {e}")
        return 0.0


def compute_feature_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute feature-based similarity using ORB detector and matcher.
    
    ORB (Oriented FAST and Rotated BRIEF) is a fast, CPU-efficient
    feature detector/descriptor. Compares keypoints between images.
    Range: 0-1 (1 = many matching features).
    
    Args:
        img1: First image (grayscale)
        img2: Second image (grayscale)
        
    Returns:
        Similarity score 0-1
    """
    try:
        # Initialize ORB detector
        orb = cv2.ORB_create(nfeatures=500)
        
        # Detect and compute descriptors
        kp1, des1 = orb.detectAndCompute(img1, None)
        kp2, des2 = orb.detectAndCompute(img2, None)
        
        if des1 is None or des2 is None or len(kp1) == 0 or len(kp2) == 0:
            return 0.0
        
        # BFMatcher for ORB descriptors
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        
        if len(matches) == 0:
            return 0.0
        
        # Sort by distance (lower is better)
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Compute similarity score based on match quality
        # Good matches have distance < 50 (for Hamming)
        good_matches = [m for m in matches if m.distance < 50]
        
        # Normalize: ratio of good matches to total keypoints
        max_matches = max(len(kp1), len(kp2))
        score = len(good_matches) / max_matches if max_matches > 0 else 0.0
        
        return min(1.0, score)
    except Exception as e:
        logger.error(f"Error computing feature similarity: {e}")
        return 0.0


def compute_histogram_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute color histogram similarity.
    
    Compares the distribution of pixel intensities in the two images.
    Range: 0-1 (1 = identical distribution).
    
    Args:
        img1: First image (grayscale)
        img2: Second image (grayscale)
        
    Returns:
        Similarity score 0-1
    """
    try:
        # Compute histograms
        hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])
        
        # Normalize
        hist1 = cv2.normalize(hist1, hist1).flatten()
        hist2 = cv2.normalize(hist2, hist2).flatten()
        
        # Compare using correlation
        score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        return float(score)
    except Exception as e:
        logger.error(f"Error computing histogram similarity: {e}")
        return 0.0


def compute_image_similarity(image1_path: str, image2_path: str) -> float:
    """
    Compute overall image similarity score (0-100).
    
    Combines multiple similarity metrics:
    - 40% MSE (pixel-level similarity)
    - 40% Feature matching (ORB keypoint matching)
    - 20% Histogram (color distribution)
    
    Args:
        image1_path: Path to first image
        image2_path: Path to second image
        
    Returns:
        Confidence score 0-100
    """
    # Load and preprocess images
    img1 = load_and_preprocess_image(image1_path)
    img2 = load_and_preprocess_image(image2_path)
    
    if img1 is None or img2 is None:
        return 0.0
    
    # Compute individual similarities (0-1 range)
    mse_score = compute_mse_similarity(img1, img2)
    feature_score = compute_feature_similarity(img1, img2)
    histogram_score = compute_histogram_similarity(img1, img2)
    
    # Weighted combination
    combined = (0.40 * mse_score) + (0.40 * feature_score) + (0.20 * histogram_score)
    
    # Scale to 0-100
    confidence = int(combined * 100)
    
    logger.debug(
        f"Image similarity: MSE={mse_score:.2f}, Features={feature_score:.2f}, "
        f"Histogram={histogram_score:.2f}, Combined={confidence}%"
    )
    
    return confidence


def compute_photos_confidence(
    found_photos: list,
    missing_photos: list,
    person_images_dir: Path
) -> float:
    """
    Compute confidence score for a person match based on all available photos.
    
    Finds the best matching pair between found and missing photos,
    then averages all pairwise comparisons.
    
    Args:
        found_photos: List of found person photo filenames
        missing_photos: List of missing person photo filenames
        person_images_dir: Path to person_images directory
        
    Returns:
        Confidence score 0-100, or 0 if no photos available
    """
    if not found_photos or not missing_photos:
        return 0.0
    
    # Compute pairwise similarities
    similarities = []
    
    for found_file in found_photos[:3]:  # Limit to first 3 photos for performance
        found_path = person_images_dir / found_file
        if not found_path.exists():
            continue
        
        for missing_file in missing_photos[:3]:  # Limit to first 3 photos
            missing_path = person_images_dir / missing_file
            if not missing_path.exists():
                continue
            
            try:
                similarity = compute_image_similarity(str(found_path), str(missing_path))
                similarities.append(similarity)
            except Exception as e:
                logger.error(f"Error comparing {found_file} and {missing_file}: {e}")
    
    if not similarities:
        return 0.0
    
    # Return average of all pairwise comparisons
    avg_confidence = sum(similarities) / len(similarities)
    
    return avg_confidence
