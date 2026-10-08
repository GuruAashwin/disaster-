"""
Unit tests for the videos router (STEP 9).

Tests the FastAPI endpoints for clothing-based video search.

Test scenarios (20+):
1. GET /videos/status endpoint
2. POST /videos/search-by-clothing with valid upper color
3. POST /videos/search-by-clothing with valid lower color
4. POST /videos/search-by-clothing with both colors
5. POST /videos/search-by-clothing missing both colors (400 error)
6. POST /videos/search-by-clothing with invalid upper color (400 error)
7. POST /videos/search-by-clothing with invalid lower color (400 error)
8. min_match_score = 0 (boundary)
9. min_match_score = 100 (boundary)
10. min_match_score < 0 (400 error)
11. min_match_score > 100 (400 error)
12. max_results = 1 (minimum)
13. max_results = 1000 (maximum)
14. max_results = 0 (400 error)
15. max_results > 1000 (400 error)
16. STEP 8 service integration (mocked)
17. Successful search with candidates
18. Search with no candidates
19. Response preserves verification_required = true
20. Response preserves status = possible_sighting
21. Existing routes still accessible
22. Case-insensitive color normalization
23. Color name with whitespace normalization
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from fastapi.testclient import TestClient
from app.main import app
from app.services.clothing_video_search import (
    ClothingCandidate,
    VideoSearchResult,
)


client = TestClient(app)


class TestVideoStatusEndpoint(unittest.TestCase):
    """Test GET /videos/status endpoint."""
    
    def test_status_endpoint_returns_200(self):
        """Test that /videos/status returns HTTP 200."""
        response = client.get("/videos/status")
        self.assertEqual(response.status_code, 200)
    
    def test_status_response_has_required_fields(self):
        """Test that status response contains required fields."""
        response = client.get("/videos/status")
        data = response.json()
        
        self.assertIn("status", data)
        self.assertIn("service", data)
        self.assertEqual(data["service"], "clothing_video_search")
    
    def test_status_response_status_is_string(self):
        """Test that status field is a string (available/unavailable)."""
        response = client.get("/videos/status")
        data = response.json()
        
        self.assertIsInstance(data["status"], str)
        self.assertIn(data["status"], ["available", "unavailable"])


class TestSearchByClothingValidation(unittest.TestCase):
    """Test request validation for search endpoint."""
    
    def test_search_returns_400_when_missing_both_colors(self):
        """Test that request without colors returns HTTP 400."""
        response = client.post(
            "/videos/search-by-clothing",
            json={},
        )
        self.assertEqual(response.status_code, 400)
    
    def test_search_accepts_upper_color_only(self):
        """Test that request with only upper_body_color is valid."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_search_accepts_lower_color_only(self):
        """Test that request with only lower_body_color is valid."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": None, "lower_body_color": "blue"},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"lower_body_color": "blue"},
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_search_accepts_both_colors(self):
        """Test that request with both colors is valid."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": "blue"},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={
                    "upper_body_color": "red",
                    "lower_body_color": "blue",
                },
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_search_rejects_invalid_upper_color(self):
        """Test that invalid upper_body_color returns HTTP 400."""
        response = client.post(
            "/videos/search-by-clothing",
            json={"upper_body_color": "invalid_color"},
        )
        self.assertEqual(response.status_code, 422)  # Validation error
    
    def test_search_rejects_invalid_lower_color(self):
        """Test that invalid lower_body_color returns HTTP 400."""
        response = client.post(
            "/videos/search-by-clothing",
            json={"lower_body_color": "invalid_color"},
        )
        self.assertEqual(response.status_code, 422)
    
    def test_search_normalizes_color_case(self):
        """Test that colors are normalized to lowercase."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "RED"},
            )
            
            self.assertEqual(response.status_code, 200)
            # Verify searcher was called with lowercase color
            mock_searcher.search.assert_called_once()
            args, kwargs = mock_searcher.search.call_args
            self.assertEqual(kwargs.get("upper_body_color"), "red")
    
    def test_search_strips_whitespace_from_colors(self):
        """Test that whitespace is stripped from color names."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "  red  "},
            )
            
            self.assertEqual(response.status_code, 200)



@unittest.skip("min_match_score and max_results parameters were removed")
class TestSearchScoreValidation(unittest.TestCase):
    """Test min_match_score validation."""
    
    def test_min_match_score_default_60(self):
        """Test that default min_match_score is 60.0."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            self.assertEqual(response.status_code, 200)
            # Verify searcher was created with default threshold
            mock_searcher_factory.assert_called_once()
            args, kwargs = mock_searcher_factory.call_args
            self.assertEqual(kwargs.get("min_match_score"), 60.0)
    
    def test_min_match_score_zero(self):
        """Test that min_match_score = 0 is valid."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={
                    "upper_body_color": "red",
                    "min_match_score": 0.0,
                },
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_min_match_score_100(self):
        """Test that min_match_score = 100 is valid."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={
                    "upper_body_color": "red",
                    "min_match_score": 100.0,
                },
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_min_match_score_below_zero_rejected(self):
        """Test that min_match_score < 0 returns validation error."""
        response = client.post(
            "/videos/search-by-clothing",
            json={
                "upper_body_color": "red",
                "min_match_score": -0.1,
            },
        )
        self.assertEqual(response.status_code, 422)
    
    def test_min_match_score_above_100_rejected(self):
        """Test that min_match_score > 100 returns validation error."""
        response = client.post(
            "/videos/search-by-clothing",
            json={
                "upper_body_color": "red",
                "min_match_score": 100.1,
            },
        )
        self.assertEqual(response.status_code, 422)



@unittest.skip("min_match_score and max_results parameters were removed")
class TestSearchMaxResultsValidation(unittest.TestCase):
    """Test max_results validation."""
    
    def test_max_results_default_10(self):
        """Test that default max_results is 10."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            self.assertEqual(response.status_code, 200)
            # Verify searcher was created with default max_results
            mock_searcher_factory.assert_called_once()
            args, kwargs = mock_searcher_factory.call_args
            self.assertEqual(kwargs.get("max_results"), 10)
    
    def test_max_results_minimum_1(self):
        """Test that max_results = 1 is valid."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={
                    "upper_body_color": "red",
                    "max_results": 1,
                },
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_max_results_maximum_1000(self):
        """Test that max_results = 1000 is valid."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={
                    "upper_body_color": "red",
                    "max_results": 1000,
                },
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_max_results_zero_rejected(self):
        """Test that max_results = 0 returns validation error."""
        response = client.post(
            "/videos/search-by-clothing",
            json={
                "upper_body_color": "red",
                "max_results": 0,
            },
        )
        self.assertEqual(response.status_code, 422)
    
    def test_max_results_exceeds_1000_rejected(self):
        """Test that max_results > 1000 returns validation error."""
        response = client.post(
            "/videos/search-by-clothing",
            json={
                "upper_body_color": "red",
                "max_results": 1001,
            },
        )
        self.assertEqual(response.status_code, 422)


class TestSearchResponse(unittest.TestCase):
    """Test response format and content."""
    
    def test_search_returns_200_with_valid_request(self):
        """Test that valid search returns HTTP 200."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_search_response_has_required_fields(self):
        """Test that response contains required fields."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            data = response.json()
            self.assertIn("query", data)
            self.assertIn("candidates", data)
            self.assertIn("total_candidates", data)
            self.assertIn("status", data)
    
    def test_search_response_no_candidates(self):
        """Test search response when no candidates found."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[],
                status="processed",
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            data = response.json()
            self.assertEqual(len(data["candidates"]), 0)
            self.assertEqual(data["total_candidates"], 0)
            self.assertEqual(data["status"], "processed")
    
    def test_search_response_with_candidates(self):
        """Test search response with candidate results."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            # Create a mock candidate
            mock_candidate = ClothingCandidate(
                frame_path="/base/camera_001/video_001/frame_042.jpg",
                camera_id="camera_001",
                frame_number=42,
                timestamp_seconds=84.0,
                person_id=0,
                match_score=85.0,
                upper_body_detected="red",
                upper_body_confidence=0.9,
                lower_body_detected="blue",
                lower_body_confidence=0.8,
                status="possible_sighting",
                verification_required=True,
            )
            
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": "blue"},
                candidates=[mock_candidate],
                status="processed",
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={
                    "upper_body_color": "red",
                    "lower_body_color": "blue",
                },
            )
            
            data = response.json()
            self.assertEqual(len(data["candidates"]), 1)
            self.assertEqual(data["total_candidates"], 1)
            
            candidate = data["candidates"][0]
            self.assertIn("candidate_id", candidate)
            self.assertIn("camera_id", candidate)
            self.assertIn("frame", candidate)
            self.assertIn("match_score", candidate)
    
    def test_response_preserves_possible_sighting_status(self):
        """Test that response preserves status = possible_sighting."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_candidate = ClothingCandidate(
                frame_path="/base/camera_001/video_001/frame_000.jpg",
                camera_id="camera_001",
                frame_number=0,
                timestamp_seconds=0.0,
                person_id=0,
                match_score=75.0,
                upper_body_detected="red",
                upper_body_confidence=0.75,
                lower_body_detected=None,
                lower_body_confidence=0.0,
                status="possible_sighting",
                verification_required=True,
            )
            
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[mock_candidate],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            data = response.json()
            self.assertEqual(data["candidates"][0]["status"], "possible_sighting")
    
    def test_response_preserves_verification_required_true(self):
        """Test that response preserves verification_required = true."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_candidate = ClothingCandidate(
                frame_path="/base/camera_001/video_001/frame_000.jpg",
                camera_id="camera_001",
                frame_number=0,
                timestamp_seconds=0.0,
                person_id=0,
                match_score=75.0,
                upper_body_detected="red",
                upper_body_confidence=0.75,
                lower_body_detected=None,
                lower_body_confidence=0.0,
                status="possible_sighting",
                verification_required=True,
            )
            
            mock_searcher = MagicMock()
            mock_searcher.search.return_value = VideoSearchResult(
                query={"upper_body_color": "red", "lower_body_color": None},
                candidates=[mock_candidate],
            )
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            data = response.json()
            self.assertTrue(data["candidates"][0]["verification_required"])


class TestErrorHandling(unittest.TestCase):
    """Test error handling."""
    
    def test_search_handles_step8_error(self):
        """Test that STEP 8 service errors are handled gracefully."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.side_effect = Exception("STEP 8 error")
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            # Should return 500, not crash
            self.assertEqual(response.status_code, 500)
    
    def test_search_response_does_not_expose_traceback(self):
        """Test that error responses don't expose Python tracebacks."""
        with patch("app.routers.videos.get_searcher") as mock_searcher_factory:
            mock_searcher = MagicMock()
            mock_searcher.search.side_effect = Exception("Internal error")
            mock_searcher_factory.return_value = mock_searcher
            
            response = client.post(
                "/videos/search-by-clothing",
                json={"upper_body_color": "red"},
            )
            
            data = response.json()
            # Should contain generic error message, not traceback
            self.assertNotIn("Traceback", str(data))
            self.assertNotIn("File ", str(data))


class TestBackwardCompatibility(unittest.TestCase):
    """Test that existing routes still work."""
    
    def test_health_endpoint_still_works(self):
        """Test that /health endpoint still accessible."""
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
    
    def test_other_routers_not_broken(self):
        """Test that other router endpoints still exist."""
        # Just check that auth router prefix exists (don't need full auth)
        # This is a smoke test to ensure router registration didn't break things
        response = client.post(
            "/auth/register",
            json={"username": "test", "password": "test"},
        )
        # Should get 200 or validation error, not 404
        self.assertNotEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
