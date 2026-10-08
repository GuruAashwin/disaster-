"""
Videos router — clothing-based video search endpoints (STEP 9)

Exposes STEP 8 clothing search service through FastAPI.

IMPORTANT SECURITY & TERMINOLOGY NOTES:
- Searches ONLY authorized/publicly available disaster video frames
- Returns "possible_sighting" status with "verification_required": true
- Clothing similarity does NOT confirm identity
- Human verification required for all candidates
- No private CCTV, filesystem browsing, or arbitrary file access
- Video frames directory is configured and not user-supplied

Endpoints:
  POST /videos/process             — Process video files into frames
  POST /videos/search-by-clothing  — Search for clothing matches in frames
  GET  /videos/status              — Check if video search service is available
  GET  /videos/frame/{camera_id}/{video_id}/{frame_name}  — Retrieve frame image
"""

import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.schemas import (
    ClothingSearchRequest,
    ClothingSearchResponse,
    ClothingCandidate,
    ClothingBodyRegion,
    VideoStatusResponse,
)
from app.services.clothing_video_search import (
    get_searcher,
    MIN_MATCH_SCORE,
    DEFAULT_MAX_RESULTS,
    VIDEO_FRAMES_DIR,
)
from app.services.video_processor import get_processor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


def _transform_candidate_to_response(raw_candidate) -> ClothingCandidate:
    """
    Transform STEP 8 ClothingCandidate dataclass to response schema.
    
    Maps STEP 8 internal format to API response format for consistent
    naming and structure.
    """
    # Extract video_id from frame_path
    # Path format: .../camera_XXX/video_YYY/frame_ZZZ.jpg
    frame_path = Path(raw_candidate.frame_path)
    video_id = frame_path.parent.name  # video_YYY
    frame_name = frame_path.name  # frame_ZZZ.jpg
    
    return ClothingCandidate(
        candidate_id=f"{raw_candidate.camera_id}_{raw_candidate.frame_number}_{raw_candidate.person_id}",
        camera_id=raw_candidate.camera_id,
        video_id=video_id,
        frame=frame_name,
        timestamp_seconds=raw_candidate.timestamp_seconds,
        detection_id=raw_candidate.person_id,
        upper_body=ClothingBodyRegion(
            detected_color=raw_candidate.upper_body_detected,
            confidence=raw_candidate.upper_body_confidence,
            matched=(
                raw_candidate.upper_body_detected is not None
                and raw_candidate.upper_body_confidence > 0
            ),
        ),
        lower_body=ClothingBodyRegion(
            detected_color=raw_candidate.lower_body_detected,
            confidence=raw_candidate.lower_body_confidence,
            matched=(
                raw_candidate.lower_body_detected is not None
                and raw_candidate.lower_body_confidence > 0
            ),
        ),
        match_score=int(raw_candidate.match_score),
        status=raw_candidate.status,
        verification_required=raw_candidate.verification_required,
    )


@router.get("/status")
def get_video_search_status() -> VideoStatusResponse:
    """
    Check if the video search service is available.
    
    Returns:
        VideoStatusResponse with availability status
        
    Note:
        This is a lightweight status check. It does not scan frames.
    """
    try:
        # Check if configured video frames directory exists
        frames_dir = Path(VIDEO_FRAMES_DIR)
        if frames_dir.exists():
            status = "available"
        else:
            status = "unavailable"
            logger.warning(f"Video frames directory not found: {VIDEO_FRAMES_DIR}")
        
        return VideoStatusResponse(status=status)
    except Exception as e:
        logger.error(f"Error checking video search status: {e}")
        return VideoStatusResponse(status="unavailable")


@router.post("/process")
def process_videos():
    """
    Process all video files into frames for searching.
    
    This endpoint:
    1. Scans the backend/video_files directory for video files
    2. Extracts frames at regular intervals
    3. Saves frames to backend/video_frames in organized structure
    4. Frames are then searchable via /videos/search-by-clothing
    
    Returns:
        Dict with processing results including number of videos processed
        
    Note:
        This is a blocking operation. Processing large videos may take time.
    """
    try:
        processor = get_processor()
        logger.info("Starting video processing...")
        
        results = processor.process_video_directory()
        
        logger.info(f"Video processing complete: {len(results)} videos processed")
        
        return {
            "status": "completed",
            "videos_processed": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error processing videos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing videos: {str(e)}",
        )



@router.post("/search-by-clothing", response_model=ClothingSearchResponse)
def search_by_clothing(request: ClothingSearchRequest) -> ClothingSearchResponse:
    """
    Search for possible sightings based on clothing color matches.
    
    IMPORTANT: This endpoint searches authorized/publicly available disaster
    video frames for clothing matches. Clothing similarity is NOT identity
    verification. All results require human verification by authorized
    personnel.
    
    Request JSON:
        {
            "upper_body_color": "red",      # optional, normalized to lowercase
            "lower_body_color": "black"     # optional, normalized to lowercase
        }
    
    At least ONE of upper_body_color or lower_body_color must be provided.
    
    Response:
        ClothingSearchResponse with candidates list (all detected people)
        
    Candidates have:
        - status: "possible_sighting" (investigative lead)
        - verification_required: true (human verification always required)
        - match_score: 0-100 (confidence-based scoring)
        
    Returns:
        HTTP 400 if validation fails (missing colors, invalid values, etc.)
        HTTP 500 if internal error occurs
    
    Example successful response:
        {
            "query": {
                "upper_body_color": "red",
                "lower_body_color": "black"
            },
            "candidates": [
                {
                    "candidate_id": "camera_001_42_0",
                    "camera_id": "camera_001",
                    "video_id": "video_001",
                    "frame": "frame_042.jpg",
                    "timestamp_seconds": 84.0,
                    "detection_id": 0,
                    "upper_body": {
                        "detected_color": "red",
                        "confidence": 0.91,
                        "matched": true
                    },
                    "lower_body": {
                        "detected_color": "black",
                        "confidence": 0.87,
                        "matched": true
                    },
                    "match_score": 89,
                    "status": "possible_sighting",
                    "verification_required": true
                }
            ],
            "total_candidates": 1,
            "status": "processed"
        }
    """
    
    # Validate that at least one color is provided
    if not request.has_valid_colors:
        logger.warning("Search request missing both upper_body_color and lower_body_color")
        raise HTTPException(
            status_code=400,
            detail="At least one of upper_body_color or lower_body_color must be provided",
        )
    
    try:
        # Initialize STEP 8 searcher with default parameters
        searcher = get_searcher()
        
        # Execute search using STEP 8 service
        logger.info(
            f"Starting clothing search: upper={request.upper_body_color}, "
            f"lower={request.lower_body_color}"
        )
        
        result = searcher.search(
            upper_body_color=request.upper_body_color,
            lower_body_color=request.lower_body_color,
        )
        
        # Handle failed search
        if result.status == "failed":
            logger.error(f"Search failed: {result.errors}")
            raise HTTPException(
                status_code=400,
                detail="Search validation failed. Please check your color selections.",
            )
        
        # Transform STEP 8 candidates to API response format
        transformed_candidates = [
            _transform_candidate_to_response(c) for c in result.candidates
        ]
        
        logger.info(
            f"Search completed: {len(transformed_candidates)} possible sightings found"
        )
        
        # Build response
        return ClothingSearchResponse(
            query={
                "upper_body_color": request.upper_body_color,
                "lower_body_color": request.lower_body_color,
            },
            candidates=transformed_candidates,
            total_candidates=len(transformed_candidates),
            status="processed",
            errors=result.errors if result.errors else None,
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, etc.)
        raise
    except ValueError as e:
        # Handle validation errors from STEP 8
        logger.warning(f"Validation error in search: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid search parameters: {str(e)}",
        )
    except Exception as e:
        # Catch all other errors and return generic 500
        logger.exception(f"Unexpected error in clothing search: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while searching. Please try again.",
        )


@router.get("/frame/{camera_id}/{video_id}/{frame_name}")
def get_frame(camera_id: str, video_id: str, frame_name: str):
    """
    Retrieve a frame image from the video frames directory.
    
    Path parameters:
        camera_id: Camera identifier (e.g., "camera_001")
        video_id: Video identifier (e.g., "video_001")
        frame_name: Frame filename (e.g., "frame_000042.jpg")
    
    Returns:
        Frame image file with appropriate content type
        
    Raises:
        HTTP 404 if frame not found
        HTTP 403 if attempting to access files outside frames directory (security)
    """
    try:
        # Validate parameters to prevent directory traversal attacks
        if ".." in camera_id or ".." in video_id or ".." in frame_name:
            raise HTTPException(
                status_code=403,
                detail="Invalid path parameters",
            )
        
        # Construct safe path
        frames_dir = Path(VIDEO_FRAMES_DIR)
        frame_path = frames_dir / camera_id / video_id / frame_name
        
        # Ensure the resolved path is still within the frames directory
        try:
            frame_path.resolve().relative_to(frames_dir.resolve())
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="Access denied: file outside frames directory",
            )
        
        # Check if file exists
        if not frame_path.exists():
            logger.warning(f"Frame not found: {frame_path}")
            raise HTTPException(
                status_code=404,
                detail=f"Frame not found: {frame_name}",
            )
        
        # Return frame image
        logger.debug(f"Serving frame: {frame_path}")
        return FileResponse(
            frame_path,
            media_type="image/jpeg",
            filename=frame_name,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving frame: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving frame image",
        )
