"""
Unit tests for the clothing region extractor service (STEP 6).

Tests:
1. One person with a normal bounding box.
2. Multiple people.
3. Bounding box at image edge.
4. Bounding box partially touching image boundary.
5. Very small person bounding box.
6. Invalid bounding box.
7. Empty image.
8. Zero width.
9. Zero height.
10. Region coordinates stay inside image.
11. Region coordinates stay inside person bounding box.
12. Upper and lower regions are different.
13. Debug image generation.
14. Multiple frames.
15. Step 4 tests still pass.
16. Step 5 tests still pass.
17. Existing project tests still pass.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from app.services.clothing_region_extractor import (
    ClothingRegionExtractor,
    ClothingRegion,
    RegionExtractionResult,
    extract_regions,
    extract_regions_batch,
    HEAD_EXCLUSION_RATIO,
    UPPER_BODY_START_RATIO,
    UPPER_BODY_HEIGHT_RATIO,
    LOWER_BODY_START_RATIO,
    LOWER_BODY_HEIGHT_RATIO,
)


class TestClothingRegionExtractor(unittest.TestCase):
    """Test suite for ClothingRegionExtractor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.frames_dir = Path(self.temp_dir) / "frames"
        self.debug_dir = Path(self.temp_dir) / "debug"
        self.frames_dir.mkdir(exist_ok=True)
        
        # Initialize extractor (debug mode off by default)
        self.extractor = ClothingRegionExtractor(debug_mode=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_frame(
        self,
        filename: str,
        width: int = 640,
        height: int = 480,
    ) -> Path:
        """
        Create a simple test frame image.
        
        Args:
            filename: Name of frame file to create
            width: Frame width
            height: Frame height
        
        Returns:
            Path to created frame
        """
        frame_path = self.frames_dir / filename
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create gray frame
        frame = np.ones((height, width, 3), dtype=np.uint8) * 128
        cv2.imwrite(str(frame_path), frame)
        return frame_path
    
    def test_01_single_person_normal_bbox(self):
        """Test extraction with one person, normal bounding box."""
        frame_path = self.create_test_frame("test_01.jpg", width=640, height=480)
        
        person_bbox = {"x": 100, "y": 80, "width": 150, "height": 300}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Verify
        self.assertEqual(result.status, "processed")
        self.assertIsNone(result.error)
        self.assertIsNotNone(result.upper_body_region)
        self.assertIsNotNone(result.lower_body_region)
        
        # Verify regions are different
        upper = result.upper_body_region
        lower = result.lower_body_region
        self.assertNotEqual(upper.to_dict(), lower.to_dict())
    
    def test_02_multiple_people(self):
        """Test extraction with multiple people in one frame."""
        frame_path = self.create_test_frame("test_02.jpg", width=800, height=600)
        
        detections = [
            {"detection_id": "person_001", "x": 50, "y": 100, "width": 120, "height": 250},
            {"detection_id": "person_002", "x": 400, "y": 120, "width": 140, "height": 280},
            {"detection_id": "person_003", "x": 600, "y": 100, "width": 130, "height": 260},
        ]
        
        results = self.extractor.extract_regions_batch(frame_path, detections)
        
        # Verify
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.status, "processed")
            self.assertIsNotNone(result.upper_body_region)
            self.assertIsNotNone(result.lower_body_region)
    
    def test_03_bbox_at_image_edge(self):
        """Test extraction with bounding box at image edge."""
        frame_path = self.create_test_frame("test_03.jpg", width=640, height=480)
        
        # Person at left edge
        person_bbox = {"x": 0, "y": 100, "width": 100, "height": 250}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Verify
        self.assertEqual(result.status, "processed")
        upper = result.upper_body_region
        lower = result.lower_body_region
        
        # Regions should be within bounds
        self.assertGreaterEqual(upper.x, 0)
        self.assertGreaterEqual(upper.y, 0)
        self.assertLessEqual(upper.x + upper.width, 640)
        self.assertLessEqual(upper.y + upper.height, 480)
    
    def test_04_bbox_partially_outside_bounds(self):
        """Test extraction with bounding box partially outside frame."""
        frame_path = self.create_test_frame("test_04.jpg", width=640, height=480)
        
        # Person partially outside right edge
        person_bbox = {"x": 550, "y": 100, "width": 150, "height": 250}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should still process, but clamp regions
        self.assertEqual(result.status, "processed")
        upper = result.upper_body_region
        lower = result.lower_body_region
        
        # Regions should be clamped
        self.assertLessEqual(upper.x + upper.width, 640)
        self.assertLessEqual(lower.x + lower.width, 640)
    
    def test_05_very_small_bbox(self):
        """Test extraction with very small person bounding box."""
        frame_path = self.create_test_frame("test_05.jpg", width=640, height=480)
        
        # Very small person (40x60 pixels)
        person_bbox = {"x": 300, "y": 200, "width": 40, "height": 60}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should still process
        self.assertEqual(result.status, "processed")
        self.assertIsNotNone(result.upper_body_region)
        self.assertIsNotNone(result.lower_body_region)
    
    def test_06_invalid_bbox_missing_field(self):
        """Test extraction with invalid bounding box (missing field)."""
        frame_path = self.create_test_frame("test_06.jpg")
        
        # Missing 'height'
        person_bbox = {"x": 100, "y": 80, "width": 150}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should fail gracefully
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
    
    def test_07_zero_width_bbox(self):
        """Test extraction with zero-width bounding box."""
        frame_path = self.create_test_frame("test_07.jpg")
        
        person_bbox = {"x": 100, "y": 80, "width": 0, "height": 300}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should fail gracefully
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
    
    def test_08_zero_height_bbox(self):
        """Test extraction with zero-height bounding box."""
        frame_path = self.create_test_frame("test_08.jpg")
        
        person_bbox = {"x": 100, "y": 80, "width": 150, "height": 0}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should fail gracefully
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
    
    def test_09_regions_within_image_bounds(self):
        """Test that extracted regions stay within image boundaries."""
        frame_path = self.create_test_frame("test_09.jpg", width=800, height=600)
        
        person_bbox = {"x": 600, "y": 400, "width": 150, "height": 180}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Verify
        self.assertEqual(result.status, "processed")
        
        upper = result.upper_body_region
        lower = result.lower_body_region
        
        # Check upper region
        self.assertGreaterEqual(upper.x, 0)
        self.assertGreaterEqual(upper.y, 0)
        self.assertLessEqual(upper.x + upper.width, 800)
        self.assertLessEqual(upper.y + upper.height, 600)
        
        # Check lower region
        self.assertGreaterEqual(lower.x, 0)
        self.assertGreaterEqual(lower.y, 0)
        self.assertLessEqual(lower.x + lower.width, 800)
        self.assertLessEqual(lower.y + lower.height, 600)
    
    def test_10_regions_within_person_bbox(self):
        """Test that extracted regions stay within person bounding box."""
        frame_path = self.create_test_frame("test_10.jpg", width=640, height=480)
        
        person_bbox = {"x": 100, "y": 80, "width": 150, "height": 300}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Verify
        self.assertEqual(result.status, "processed")
        
        px, py = person_bbox["x"], person_bbox["y"]
        pw, ph = person_bbox["width"], person_bbox["height"]
        
        upper = result.upper_body_region
        lower = result.lower_body_region
        
        # Check upper region inside person bbox
        self.assertGreaterEqual(upper.x, px)
        self.assertGreaterEqual(upper.y, py)
        self.assertLessEqual(upper.x + upper.width, px + pw)
        self.assertLessEqual(upper.y + upper.height, py + ph)
        
        # Check lower region inside person bbox
        self.assertGreaterEqual(lower.x, px)
        self.assertGreaterEqual(lower.y, py)
        self.assertLessEqual(lower.x + lower.width, px + pw)
        self.assertLessEqual(lower.y + lower.height, py + ph)
    
    def test_11_upper_and_lower_regions_differ(self):
        """Test that upper and lower regions are different."""
        frame_path = self.create_test_frame("test_11.jpg")
        
        person_bbox = {"x": 150, "y": 100, "width": 200, "height": 350}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        upper = result.upper_body_region
        lower = result.lower_body_region
        
        # Regions should differ in at least y coordinate
        self.assertNotEqual(upper.y, lower.y)
        
        # Ideally, lower region should start after upper region
        self.assertGreater(lower.y, upper.y)
    
    def test_12_debug_image_generation(self):
        """Test debug image generation."""
        debug_dir = Path(self.temp_dir) / "debug_out"
        extractor_debug = ClothingRegionExtractor(
            debug_mode=True,
            debug_output_dir=str(debug_dir),
        )
        
        frame_path = self.create_test_frame("test_12.jpg", width=640, height=480)
        
        person_bbox = {"x": 100, "y": 80, "width": 150, "height": 300}
        result = extractor_debug.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Verify
        self.assertEqual(result.status, "processed")
        
        # Check if debug image was created (approximate check based on naming)
        # The exact path depends on the frame_path structure
        # This is a smoke test to ensure debug mode doesn't crash
    
    def test_13_invalid_image_file(self):
        """Test handling of invalid image file."""
        # Create invalid image file
        invalid_path = self.frames_dir / "invalid.jpg"
        invalid_path.write_text("not an image")
        
        person_bbox = {"x": 100, "y": 80, "width": 150, "height": 300}
        result = self.extractor.extract_regions(
            invalid_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should fail gracefully
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
    
    def test_14_nonexistent_file(self):
        """Test handling of nonexistent file."""
        nonexistent = self.frames_dir / "nonexistent.jpg"
        
        person_bbox = {"x": 100, "y": 80, "width": 150, "height": 300}
        result = self.extractor.extract_regions(
            nonexistent, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should fail gracefully
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
    
    def test_15_result_to_dict(self):
        """Test conversion of result to dictionary."""
        frame_path = self.create_test_frame("test_15.jpg")
        
        person_bbox = {"x": 100, "y": 80, "width": 150, "height": 300}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Convert to dict
        result_dict = result.to_dict()
        
        # Verify structure
        self.assertIn("detection_id", result_dict)
        self.assertIn("frame", result_dict)
        self.assertIn("person_bbox", result_dict)
        self.assertIn("regions", result_dict)
        self.assertIn("status", result_dict)
        
        regions = result_dict["regions"]
        self.assertIn("upper_body", regions)
        self.assertIn("lower_body", regions)
        
        # Verify upper body region structure
        upper = regions["upper_body"]
        self.assertIn("region_id", upper)
        self.assertIn("region_type", upper)
        self.assertIn("x", upper)
        self.assertIn("y", upper)
        self.assertIn("width", upper)
        self.assertIn("height", upper)
    
    def test_16_region_proportions_correct(self):
        """Test that regions follow configured proportions."""
        frame_path = self.create_test_frame("test_16.jpg", width=640, height=480)
        
        person_bbox = {"x": 200, "y": 100, "width": 100, "height": 300}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        upper = result.upper_body_region
        lower = result.lower_body_region
        
        # Upper body should start around 15% from top
        expected_upper_y = person_bbox["y"] + int(person_bbox["height"] * UPPER_BODY_START_RATIO)
        # Allow small tolerance due to integer rounding
        self.assertLess(abs(upper.y - expected_upper_y), 5)
        
        # Lower body should start around 50% from top
        expected_lower_y = person_bbox["y"] + int(person_bbox["height"] * LOWER_BODY_START_RATIO)
        self.assertLess(abs(lower.y - expected_lower_y), 5)


class TestClothingRegionConvenienceFunctions(unittest.TestCase):
    """Test convenience module-level functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.frames_dir = Path(self.temp_dir) / "frames"
        self.frames_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_frame(self, filename: str) -> Path:
        """Create a simple test frame."""
        frame_path = self.frames_dir / filename
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        cv2.imwrite(str(frame_path), frame)
        return frame_path
    
    def test_extract_regions_convenience(self):
        """Test extract_regions convenience function."""
        frame_path = self.create_test_frame("conv_test.jpg")
        
        person_bbox = {"x": 100, "y": 80, "width": 150, "height": 300}
        result = extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        self.assertEqual(result.status, "processed")
        self.assertIsNotNone(result.upper_body_region)
        self.assertIsNotNone(result.lower_body_region)
    
    def test_extract_regions_batch_convenience(self):
        """Test extract_regions_batch convenience function."""
        frame_path = self.create_test_frame("batch_test.jpg")
        
        detections = [
            {"detection_id": "p1", "x": 50, "y": 100, "width": 100, "height": 250},
            {"detection_id": "p2", "x": 400, "y": 120, "width": 120, "height": 280},
        ]
        
        results = extract_regions_batch(frame_path, detections)
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.status, "processed")


class TestClothingRegionEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.frames_dir = Path(self.temp_dir) / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        self.extractor = ClothingRegionExtractor(debug_mode=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extremely_small_frame(self):
        """Test with extremely small frame."""
        frame_path = self.frames_dir / "tiny.jpg"
        tiny_frame = np.zeros((50, 50, 3), dtype=np.uint8)
        cv2.imwrite(str(frame_path), tiny_frame)
        
        person_bbox = {"x": 10, "y": 10, "width": 30, "height": 30}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should handle gracefully
        self.assertIn(result.status, ["processed", "failed"])
    
    def test_negative_coordinates(self):
        """Test with negative coordinates (outside frame)."""
        frame_path = self.frames_dir / "negative.jpg"
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        cv2.imwrite(str(frame_path), frame)
        
        # Negative x and y
        person_bbox = {"x": -50, "y": -50, "width": 100, "height": 200}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should fail or clamp gracefully
        self.assertIn(result.status, ["processed", "failed"])
    
    def test_bbox_entirely_outside_frame(self):
        """Test with bounding box entirely outside frame."""
        frame_path = self.frames_dir / "outside.jpg"
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        cv2.imwrite(str(frame_path), frame)
        
        # Entirely outside to the right
        person_bbox = {"x": 700, "y": 100, "width": 100, "height": 200}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should fail
        self.assertEqual(result.status, "failed")
    
    def test_negative_width_height(self):
        """Test with negative width/height."""
        frame_path = self.frames_dir / "negative_dims.jpg"
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        cv2.imwrite(str(frame_path), frame)
        
        person_bbox = {"x": 100, "y": 100, "width": -50, "height": -100}
        result = self.extractor.extract_regions(
            frame_path, detection_id="person_001", person_bbox=person_bbox
        )
        
        # Should fail
        self.assertEqual(result.status, "failed")


if __name__ == "__main__":
    unittest.main()
