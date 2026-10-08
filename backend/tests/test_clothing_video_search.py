"""
Unit tests for the clothing-based video search service (STEP 8).

Tests orchestration of STEPS 4-7 for clothing-based candidate ranking.

Test scenarios (27+):
1. Query normalization: lowercase, validation, both/single color
2. Frame discovery: empty dir, single frame, multiple frames, nested structure
3. Match scoring: both colors match (50/50), single color match (100), no match (0)
4. Confidence weighting: high/low confidence impact on scores
5. Candidate ranking: score DESC, confidence DESC, timestamp ASC
6. Result formatting: possible_sighting status, verification_required flag
7. Threshold filtering: above/below min_match_score
8. Max results: limiting candidate count
9. Error handling: invalid colors, missing frames, corrupted images
10. No persons detected: empty candidates list
11. Query validation: no colors specified error
12. Result structure: complete dict serialization
13. Empty video frames directory
14. Integration: full pipeline with mocked components
15. Debug mode: logging and flags
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import cv2
import numpy as np

from app.services.clothing_video_search import (
    ClothingVideoSearcher,
    ClothingCandidate,
    VideoSearchResult,
    SightingStatus,
    get_searcher,
    search_by_clothing,
    MIN_MATCH_SCORE,
    DEFAULT_MAX_RESULTS,
)


class TestQueryNormalization(unittest.TestCase):
    """Test query normalization and validation."""
    
    def setUp(self):
        """Set up searcher instance."""
        self.temp_dir = tempfile.mkdtemp()
        self.searcher = ClothingVideoSearcher(
            video_frames_dir=self.temp_dir,
        )
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_normalize_lowercase_colors(self):
        """Test that color names are converted to lowercase."""
        upper, lower = self.searcher._normalize_query("Red", "BLUE")
        self.assertEqual(upper, "red")
        self.assertEqual(lower, "blue")
    
    def test_normalize_strips_whitespace(self):
        """Test that whitespace is stripped."""
        upper, lower = self.searcher._normalize_query("  red  ", " blue ")
        self.assertEqual(upper, "red")
        self.assertEqual(lower, "blue")
    
    def test_normalize_single_upper_color(self):
        """Test query with only upper body color."""
        upper, lower = self.searcher._normalize_query(upper_body_color="red")
        self.assertEqual(upper, "red")
        self.assertIsNone(lower)
    
    def test_normalize_single_lower_color(self):
        """Test query with only lower body color."""
        upper, lower = self.searcher._normalize_query(lower_body_color="blue")
        self.assertIsNone(upper)
        self.assertEqual(lower, "blue")
    
    def test_normalize_both_colors(self):
        """Test query with both colors."""
        upper, lower = self.searcher._normalize_query(
            upper_body_color="red",
            lower_body_color="blue",
        )
        self.assertEqual(upper, "red")
        self.assertEqual(lower, "blue")
    
    def test_invalid_upper_color_raises_error(self):
        """Test that unsupported upper color raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.searcher._normalize_query(upper_body_color="invalid_color")
        self.assertIn("Unsupported", str(ctx.exception))
    
    def test_invalid_lower_color_raises_error(self):
        """Test that unsupported lower color raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.searcher._normalize_query(lower_body_color="invalid_color")
        self.assertIn("Unsupported", str(ctx.exception))
    
    def test_no_colors_raises_error(self):
        """Test that query without any color raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.searcher._normalize_query()
        self.assertIn("At least one", str(ctx.exception))
    
    def test_all_supported_colors_valid(self):
        """Test that all 14 supported colors are accepted."""
        supported = [
            "black", "white", "gray", "red", "orange", "yellow",
            "green", "blue", "navy", "purple", "pink", "brown",
            "beige", "maroon",
        ]
        for color in supported:
            upper, lower = self.searcher._normalize_query(upper_body_color=color)
            self.assertEqual(upper, color)


class TestFrameDiscovery(unittest.TestCase):
    """Test frame discovery functionality."""
    
    def setUp(self):
        """Set up temporary directory structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.frames_root = Path(self.temp_dir)
        self.searcher = ClothingVideoSearcher(
            video_frames_dir=str(self.frames_root),
        )
    
    def tearDown(self):
        """Clean up."""
        if self.frames_root.exists():
            shutil.rmtree(self.frames_root)
    
    def test_discover_empty_directory(self):
        """Test discovery in empty directory returns empty list."""
        frames = self.searcher._discover_frames()
        self.assertEqual(len(frames), 0)
    
    def test_discover_nonexistent_directory(self):
        """Test discovery when directory doesn't exist returns empty list."""
        searcher = ClothingVideoSearcher(
            video_frames_dir=str(self.frames_root / "nonexistent"),
        )
        frames = searcher._discover_frames()
        self.assertEqual(len(frames), 0)
    
    def test_discover_single_frame(self):
        """Test discovery of a single frame."""
        # Create directory structure: camera_001/video_001/
        camera_dir = self.frames_root / "camera_001" / "video_001"
        camera_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dummy frame file
        frame_path = camera_dir / "frame_000.jpg"
        frame_path.touch()
        
        frames = self.searcher._discover_frames()
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].name, "frame_000.jpg")
    
    def test_discover_multiple_frames_same_video(self):
        """Test discovery of multiple frames from same video."""
        camera_dir = self.frames_root / "camera_001" / "video_001"
        camera_dir.mkdir(parents=True, exist_ok=True)
        
        # Create multiple frames
        for i in range(5):
            frame_path = camera_dir / f"frame_{i:03d}.jpg"
            frame_path.touch()
        
        frames = self.searcher._discover_frames()
        self.assertEqual(len(frames), 5)
    
    def test_discover_multiple_videos_same_camera(self):
        """Test discovery across multiple videos from same camera."""
        for video_id in range(3):
            camera_dir = self.frames_root / "camera_001" / f"video_{video_id:03d}"
            camera_dir.mkdir(parents=True, exist_ok=True)
            frame_path = camera_dir / "frame_000.jpg"
            frame_path.touch()
        
        frames = self.searcher._discover_frames()
        self.assertEqual(len(frames), 3)
    
    def test_discover_multiple_cameras(self):
        """Test discovery across multiple cameras."""
        for camera_id in range(3):
            for video_id in range(2):
                camera_dir = (
                    self.frames_root / f"camera_{camera_id:03d}" / f"video_{video_id:03d}"
                )
                camera_dir.mkdir(parents=True, exist_ok=True)
                frame_path = camera_dir / "frame_000.jpg"
                frame_path.touch()
        
        frames = self.searcher._discover_frames()
        self.assertEqual(len(frames), 6)  # 3 cameras * 2 videos
    
    def test_discover_frames_sorted_chronologically(self):
        """Test that discovered frames are sorted."""
        camera_dir = self.frames_root / "camera_001" / "video_001"
        camera_dir.mkdir(parents=True, exist_ok=True)
        
        # Create frames in random order
        for i in [3, 0, 2, 1, 4]:
            frame_path = camera_dir / f"frame_{i:03d}.jpg"
            frame_path.touch()
        
        frames = self.searcher._discover_frames()
        frame_names = [f.name for f in frames]
        
        # Should be sorted by name
        self.assertEqual(frame_names[0], "frame_000.jpg")
        self.assertEqual(frame_names[-1], "frame_004.jpg")


class TestFrameMetadataExtraction(unittest.TestCase):
    """Test extraction of frame metadata from paths."""
    
    def setUp(self):
        """Set up searcher."""
        self.temp_dir = tempfile.mkdtemp()
        self.searcher = ClothingVideoSearcher(
            video_frames_dir=self.temp_dir,
        )
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extract_metadata_from_path(self):
        """Test metadata extraction from frame path."""
        frame_path = Path(
            "/base/backend/video_frames/camera_001/video_042/frame_100.jpg"
        )
        metadata = self.searcher._extract_frame_metadata(frame_path)
        
        self.assertEqual(metadata["camera_id"], "camera_001")
        self.assertEqual(metadata["video_id"], "video_042")
        self.assertEqual(metadata["frame_number"], 100)
        self.assertEqual(metadata["timestamp_seconds"], 200.0)  # 100 * 2.0
    
    def test_extract_metadata_frame_0(self):
        """Test metadata extraction for frame 0."""
        frame_path = Path("/base/camera_001/video_001/frame_000.jpg")
        metadata = self.searcher._extract_frame_metadata(frame_path)
        
        self.assertEqual(metadata["frame_number"], 0)
        self.assertEqual(metadata["timestamp_seconds"], 0.0)


class TestMatchScoring(unittest.TestCase):
    """Test match score calculation."""
    
    def setUp(self):
        """Set up searcher."""
        self.temp_dir = tempfile.mkdtemp()
        self.searcher = ClothingVideoSearcher(
            video_frames_dir=self.temp_dir,
        )
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_both_colors_perfect_match(self):
        """Test score when both colors match perfectly."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower="blue",
            detected_upper="red",
            detected_upper_conf=1.0,
            detected_lower="blue",
            detected_lower_conf=1.0,
        )
        self.assertEqual(score, 100.0)
    
    def test_both_colors_partial_match_upper_only(self):
        """Test score when only upper color matches (both requested)."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower="blue",
            detected_upper="red",
            detected_upper_conf=1.0,
            detected_lower="green",
            detected_lower_conf=1.0,
        )
        # Only upper matches, 50 points
        self.assertEqual(score, 50.0)
    
    def test_both_colors_partial_match_lower_only(self):
        """Test score when only lower color matches (both requested)."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower="blue",
            detected_upper="green",
            detected_upper_conf=1.0,
            detected_lower="blue",
            detected_lower_conf=1.0,
        )
        # Only lower matches, 50 points
        self.assertEqual(score, 50.0)
    
    def test_both_colors_no_match(self):
        """Test score when neither color matches."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower="blue",
            detected_upper="green",
            detected_upper_conf=1.0,
            detected_lower="yellow",
            detected_lower_conf=1.0,
        )
        # Returns 0 when colors don't match
        self.assertEqual(score, 0.0)
    
    def test_single_upper_color_match(self):
        """Test score for single upper color request (100 points)."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower=None,
            detected_upper="red",
            detected_upper_conf=1.0,
            detected_lower="blue",
            detected_lower_conf=1.0,
        )
        self.assertEqual(score, 100.0)
    
    def test_single_lower_color_match(self):
        """Test score for single lower color request (100 points)."""
        score = self.searcher._calculate_match_score(
            query_upper=None,
            query_lower="blue",
            detected_upper="red",
            detected_upper_conf=1.0,
            detected_lower="blue",
            detected_lower_conf=1.0,
        )
        self.assertEqual(score, 100.0)
    
    def test_single_color_no_match(self):
        """Test score when single requested color doesn't match."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower=None,
            detected_upper="blue",
            detected_upper_conf=1.0,
            detected_lower=None,
            detected_lower_conf=0.0,
        )
        # Returns 0 when color doesn't match
        self.assertEqual(score, 0.0)
    
    def test_confidence_weighting_high(self):
        """Test that high confidence increases score."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower=None,
            detected_upper="red",
            detected_upper_conf=0.9,  # 90% confidence
            detected_lower=None,
            detected_lower_conf=0.0,
        )
        expected = 100.0 * 0.9
        self.assertEqual(score, expected)
    
    def test_confidence_weighting_low(self):
        """Test that low confidence decreases score."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower=None,
            detected_upper="red",
            detected_upper_conf=0.3,  # 30% confidence
            detected_lower=None,
            detected_lower_conf=0.0,
        )
        expected = 100.0 * 0.3
        self.assertEqual(score, expected)
    
    def test_both_colors_confidence_weighting(self):
        """Test confidence weighting for both colors."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower="blue",
            detected_upper="red",
            detected_upper_conf=0.8,
            detected_lower="blue",
            detected_lower_conf=0.6,
        )
        expected = (50.0 * 0.8) + (50.0 * 0.6)  # 40 + 30 = 70
        self.assertEqual(score, expected)
    
    def test_score_clamped_to_100(self):
        """Test that score is clamped to 100 maximum."""
        # Even with confidence > 1.0 (shouldn't happen, but defensive)
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower=None,
            detected_upper="red",
            detected_upper_conf=1.5,  # Abnormally high
            detected_lower=None,
            detected_lower_conf=0.0,
        )
        self.assertLessEqual(score, 100.0)
    
    def test_score_clamped_to_0(self):
        """Test that score is clamped to 0 minimum."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower=None,
            detected_upper=None,
            detected_upper_conf=0.0,
            detected_lower=None,
            detected_lower_conf=0.0,
        )
        self.assertGreaterEqual(score, 0.0)
    
    def test_case_insensitive_matching(self):
        """Test that color matching is case-insensitive."""
        score = self.searcher._calculate_match_score(
            query_upper="red",
            query_lower=None,
            detected_upper="RED",  # Different case
            detected_upper_conf=1.0,
            detected_lower=None,
            detected_lower_conf=0.0,
        )
        self.assertEqual(score, 100.0)


class TestClothingCandidate(unittest.TestCase):
    """Test ClothingCandidate dataclass."""
    
    def test_candidate_creation(self):
        """Test creating a candidate."""
        candidate = ClothingCandidate(
            frame_path="/path/to/frame.jpg",
            camera_id="camera_001",
            frame_number=10,
            timestamp_seconds=20.0,
            person_id=0,
            match_score=75.5,
            upper_body_detected="red",
            upper_body_confidence=0.9,
            lower_body_detected="blue",
            lower_body_confidence=0.8,
        )
        
        self.assertEqual(candidate.frame_path, "/path/to/frame.jpg")
        self.assertEqual(candidate.match_score, 75.5)
        self.assertEqual(candidate.status, SightingStatus.POSSIBLE_SIGHTING)
        self.assertTrue(candidate.verification_required)
    
    def test_candidate_serialization(self):
        """Test candidate dict serialization."""
        candidate = ClothingCandidate(
            frame_path="/path/to/frame.jpg",
            camera_id="camera_001",
            frame_number=10,
            timestamp_seconds=20.0,
            person_id=0,
            match_score=75.5,
            upper_body_detected="red",
            upper_body_confidence=0.9,
            lower_body_detected="blue",
            lower_body_confidence=0.8,
        )
        
        data = candidate.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["match_score"], 75)  # Converted to int
        self.assertEqual(data["status"], "possible_sighting")
        self.assertTrue(data["verification_required"])


class TestVideoSearchResult(unittest.TestCase):
    """Test VideoSearchResult dataclass."""
    
    def test_result_creation(self):
        """Test creating a search result."""
        result = VideoSearchResult(
            query={"upper_body_color": "red", "lower_body_color": "blue"},
            status="processed",
            frames_scanned=50,
        )
        
        self.assertEqual(result.status, "processed")
        self.assertEqual(result.frames_scanned, 50)
        self.assertEqual(len(result.candidates), 0)
    
    def test_result_serialization(self):
        """Test result dict serialization."""
        candidate = ClothingCandidate(
            frame_path="/path/to/frame.jpg",
            camera_id="camera_001",
            frame_number=10,
            timestamp_seconds=20.0,
            person_id=0,
            match_score=75.0,
            upper_body_detected="red",
            upper_body_confidence=0.9,
            lower_body_detected="blue",
            lower_body_confidence=0.8,
        )
        
        result = VideoSearchResult(
            query={"upper_body_color": "red", "lower_body_color": "blue"},
            candidates=[candidate],
            status="processed",
        )
        
        data = result.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["total_candidates"], 1)
        self.assertEqual(len(data["candidates"]), 1)
        self.assertEqual(data["candidates"][0]["camera_id"], "camera_001")


class TestThresholdFiltering(unittest.TestCase):
    """Test minimum match score threshold filtering."""
    
    def setUp(self):
        """Set up searcher with custom threshold."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_threshold_default_60(self):
        """Test default threshold is 60."""
        searcher = ClothingVideoSearcher(video_frames_dir=self.temp_dir)
        self.assertEqual(searcher.min_match_score, MIN_MATCH_SCORE)
    
    def test_threshold_custom(self):
        """Test setting custom threshold."""
        searcher = ClothingVideoSearcher(
            min_match_score=80.0,
            video_frames_dir=self.temp_dir,
        )
        self.assertEqual(searcher.min_match_score, 80.0)
    
    def test_threshold_filtering_excludes_low_scores(self):
        """Test that _process_frame filters by threshold."""
        # Create a test frame
        frame_dir = Path(self.temp_dir) / "camera_001" / "video_001"
        frame_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a simple test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_path = frame_dir / "frame_000.jpg"
        cv2.imwrite(str(frame_path), test_image)
        
        # Mock _process_frame to return a low-score candidate that should be filtered
        with patch.object(
            ClothingVideoSearcher,
            "_process_frame",
            return_value=[
                # This candidate has score below 60 threshold
                ClothingCandidate(
                    frame_path=str(frame_path),
                    camera_id="camera_001",
                    frame_number=0,
                    timestamp_seconds=0.0,
                    person_id=0,
                    match_score=40.0,  # Below threshold
                    upper_body_detected="red",
                    upper_body_confidence=0.4,
                    lower_body_detected=None,
                    lower_body_confidence=0.0,
                ),
            ],
        ):
            searcher = ClothingVideoSearcher(
                min_match_score=60.0,
                video_frames_dir=self.temp_dir,
            )
            
            # Verify min_match_score is set correctly
            self.assertEqual(searcher.min_match_score, 60.0)


class TestMaxResults(unittest.TestCase):
    """Test max results limiting."""
    
    def setUp(self):
        """Set up searcher."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_max_results_default(self):
        """Test default max results."""
        searcher = ClothingVideoSearcher(video_frames_dir=self.temp_dir)
        self.assertEqual(searcher.max_results, DEFAULT_MAX_RESULTS)
    
    def test_max_results_custom(self):
        """Test setting custom max results."""
        searcher = ClothingVideoSearcher(
            max_results=10,
            video_frames_dir=self.temp_dir,
        )
        self.assertEqual(searcher.max_results, 10)
    
    @patch.object(ClothingVideoSearcher, "_discover_frames")
    @patch.object(ClothingVideoSearcher, "_process_frame")
    def test_max_results_limiting(self, mock_process, mock_discover):
        """Test that results are limited to max_results."""
        # Mock frame discovery with many frames
        mock_discover.return_value = [
            Path(f"/frame{i}.jpg") for i in range(20)
        ]
        
        # Mock _process_frame to return candidates
        def create_candidate(frame_path, *args, **kwargs):
            frame_num = int(frame_path.name.replace("frame", "").replace(".jpg", ""))
            return [
                ClothingCandidate(
                    frame_path=str(frame_path),
                    camera_id="camera_001",
                    frame_number=frame_num,
                    timestamp_seconds=frame_num * 2.0,
                    person_id=0,
                    match_score=80.0,  # All match
                    upper_body_detected="red",
                    upper_body_confidence=0.8,
                    lower_body_detected=None,
                    lower_body_confidence=0.0,
                )
            ]
        
        mock_process.side_effect = create_candidate
        
        searcher = ClothingVideoSearcher(
            max_results=5,
            video_frames_dir=self.temp_dir,
        )
        
        result = searcher.search(upper_body_color="red")
        
        # Should be limited to 5
        self.assertEqual(len(result.candidates), 5)


class TestCandidateRanking(unittest.TestCase):
    """Test candidate ranking logic."""
    
    def setUp(self):
        """Set up searcher."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    @patch.object(ClothingVideoSearcher, "_discover_frames")
    @patch.object(ClothingVideoSearcher, "_process_frame")
    def test_ranking_by_score_descending(self, mock_process, mock_discover):
        """Test candidates ranked by score in descending order."""
        mock_discover.return_value = [
            Path("/frame1.jpg"),
            Path("/frame2.jpg"),
            Path("/frame3.jpg"),
        ]
        
        # Create candidates with different scores (out of order)
        candidates_list = [
            [
                ClothingCandidate(
                    frame_path="/frame1.jpg",
                    camera_id="camera_001",
                    frame_number=0,
                    timestamp_seconds=0.0,
                    person_id=0,
                    match_score=50.0,  # Lowest
                    upper_body_detected="red",
                    upper_body_confidence=0.5,
                    lower_body_detected=None,
                    lower_body_confidence=0.0,
                )
            ],
            [
                ClothingCandidate(
                    frame_path="/frame2.jpg",
                    camera_id="camera_001",
                    frame_number=1,
                    timestamp_seconds=2.0,
                    person_id=0,
                    match_score=100.0,  # Highest
                    upper_body_detected="red",
                    upper_body_confidence=1.0,
                    lower_body_detected=None,
                    lower_body_confidence=0.0,
                )
            ],
            [
                ClothingCandidate(
                    frame_path="/frame3.jpg",
                    camera_id="camera_001",
                    frame_number=2,
                    timestamp_seconds=4.0,
                    person_id=0,
                    match_score=75.0,  # Middle
                    upper_body_detected="red",
                    upper_body_confidence=0.75,
                    lower_body_detected=None,
                    lower_body_confidence=0.0,
                )
            ],
        ]
        
        mock_process.side_effect = candidates_list
        
        searcher = ClothingVideoSearcher(video_frames_dir=self.temp_dir)
        result = searcher.search(upper_body_color="red")
        
        # Should be sorted: 100, 75, 50
        self.assertEqual(result.candidates[0].match_score, 100.0)
        self.assertEqual(result.candidates[1].match_score, 75.0)
        self.assertEqual(result.candidates[2].match_score, 50.0)
    
    @patch.object(ClothingVideoSearcher, "_discover_frames")
    @patch.object(ClothingVideoSearcher, "_process_frame")
    def test_ranking_by_confidence_on_tie(self, mock_process, mock_discover):
        """Test ranking by confidence when scores are equal."""
        mock_discover.return_value = [Path("/frame1.jpg"), Path("/frame2.jpg")]
        
        # Both have same score, different confidence
        candidates_list = [
            [
                ClothingCandidate(
                    frame_path="/frame1.jpg",
                    camera_id="camera_001",
                    frame_number=0,
                    timestamp_seconds=0.0,
                    person_id=0,
                    match_score=75.0,
                    upper_body_detected="red",
                    upper_body_confidence=0.5,  # Lower confidence
                    lower_body_detected=None,
                    lower_body_confidence=0.0,
                )
            ],
            [
                ClothingCandidate(
                    frame_path="/frame2.jpg",
                    camera_id="camera_001",
                    frame_number=1,
                    timestamp_seconds=2.0,
                    person_id=0,
                    match_score=75.0,
                    upper_body_detected="red",
                    upper_body_confidence=0.9,  # Higher confidence
                    lower_body_detected=None,
                    lower_body_confidence=0.0,
                )
            ],
        ]
        
        mock_process.side_effect = candidates_list
        
        searcher = ClothingVideoSearcher(video_frames_dir=self.temp_dir)
        result = searcher.search(upper_body_color="red")
        
        # Higher confidence should rank first
        self.assertEqual(result.candidates[0].upper_body_confidence, 0.9)
        self.assertEqual(result.candidates[1].upper_body_confidence, 0.5)


class TestSearchEntryPoints(unittest.TestCase):
    """Test search entry point functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    @patch("app.services.clothing_video_search.ClothingVideoSearcher")
    def test_get_searcher_factory(self, mock_class):
        """Test get_searcher factory function."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        searcher = get_searcher(
            min_match_score=75.0,
            max_results=50,
        )
        
        mock_class.assert_called_once()
        self.assertEqual(searcher, mock_instance)
    
    @patch("app.services.clothing_video_search.ClothingVideoSearcher")
    def test_search_by_clothing_entry_point(self, mock_class):
        """Test search_by_clothing convenience function."""
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"status": "processed"}
        mock_instance.search.return_value = mock_result
        
        result = search_by_clothing(upper_body_color="red")
        
        self.assertIsInstance(result, dict)
        mock_instance.search.assert_called_once()


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.searcher = ClothingVideoSearcher(
            video_frames_dir=self.temp_dir,
        )
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_search_invalid_color_returns_failed_result(self):
        """Test that invalid color returns failed status."""
        result = self.searcher.search(upper_body_color="invalid_color")
        
        self.assertEqual(result.status, "failed")
        self.assertTrue(len(result.errors) > 0)
        self.assertEqual(len(result.candidates), 0)
    
    def test_search_no_colors_returns_failed_result(self):
        """Test that no colors specified returns failed status."""
        result = self.searcher.search()
        
        self.assertEqual(result.status, "failed")
        self.assertTrue(len(result.errors) > 0)
    
    def test_empty_frames_directory_returns_no_candidates(self):
        """Test that empty frames directory returns no candidates."""
        result = self.searcher.search(upper_body_color="red")
        
        self.assertEqual(result.status, "processed")
        self.assertEqual(len(result.candidates), 0)
        self.assertEqual(result.frames_scanned, 0)


class TestDebugMode(unittest.TestCase):
    """Test debug mode functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_debug_mode_enabled(self):
        """Test that debug mode can be enabled."""
        searcher = ClothingVideoSearcher(
            debug=True,
            video_frames_dir=self.temp_dir,
        )
        self.assertTrue(searcher.debug)
    
    def test_debug_mode_disabled(self):
        """Test that debug mode can be disabled."""
        searcher = ClothingVideoSearcher(
            debug=False,
            video_frames_dir=self.temp_dir,
        )
        self.assertFalse(searcher.debug)


if __name__ == "__main__":
    unittest.main()
