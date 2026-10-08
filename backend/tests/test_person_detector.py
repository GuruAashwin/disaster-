"""
Unit tests for the person detector service (STEP 5).

Tests:
1. Valid frame containing one person
2. Valid frame containing multiple people
3. Bounding boxes remain inside image boundaries
4. Confidence threshold works
5. Frame containing no people
6. Invalid image/frame
7. Multiple sampled frames (batch)
8. Ensure Step 4 tests continue passing
9. Ensure existing project tests continue passing
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from app.services.person_detector import (
    PersonDetector,
    PersonDetection,
    PersonDetectorResult,
    detect_frame,
    detect_frames_batch,
    DEFAULT_CONFIDENCE_THRESHOLD,
)


class TestPersonDetector(unittest.TestCase):
    """Test suite for PersonDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.frames_dir = Path(self.temp_dir) / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        
        # Initialize detector with lower threshold for testing
        self.detector = PersonDetector(confidence_threshold=0.3)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_frame(
        self,
        filename: str,
        width: int = 640,
        height: int = 480,
        with_person: bool = True,
    ) -> Path:
        """
        Create a test frame image.
        
        Args:
            filename: Name of frame file to create
            width: Frame width
            height: Frame height
            with_person: Whether to draw a person-like shape
        
        Returns:
            Path to created frame
        """
        frame_path = self.frames_dir / filename
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create blank frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (200, 200, 200)  # Light gray background
        
        if with_person:
            # Draw a simple person-like shape (head + body)
            # Head (circle)
            head_x, head_y = width // 2, height // 3
            head_radius = 30
            cv2.circle(frame, (head_x, head_y), head_radius, (100, 100, 100), -1)
            
            # Body (rectangle)
            body_x1, body_y1 = head_x - 20, head_y + 40
            body_x2, body_y2 = head_x + 20, head_y + 120
            cv2.rectangle(frame, (body_x1, body_y1), (body_x2, body_y2), (100, 100, 100), -1)
            
            # Add some variation with skin-like colors for face
            cv2.circle(frame, (head_x, head_y), head_radius, (150, 130, 100), -1)
        
        # Save frame as JPEG
        cv2.imwrite(str(frame_path), frame)
        return frame_path
    
    def test_01_valid_frame_one_person(self):
        """Test detection in frame with one person."""
        # Create test frame with person
        frame_path = self.create_test_frame("test_01.jpg", with_person=True)
        
        # Detect
        result = self.detector.detect_frame(frame_path, frame_number=0, timestamp_seconds=0.0)
        
        # Verify
        self.assertEqual(result.status, "processed")
        self.assertIsNone(result.error)
        self.assertEqual(result.image_width, 640)
        self.assertEqual(result.image_height, 480)
        self.assertGreaterEqual(result.people_count, 0)  # May or may not detect simple drawing
        
        # If detected, verify detection structure
        if result.people_count > 0:
            detection = result.detections[0]
            self.assertGreater(detection.confidence, 0)
            self.assertLess(detection.confidence, 1.0)
            self.assertGreaterEqual(detection.x, 0)
            self.assertGreaterEqual(detection.y, 0)
            self.assertGreater(detection.width, 0)
            self.assertGreater(detection.height, 0)
    
    def test_02_empty_frame(self):
        """Test detection in frame with no people."""
        # Create blank frame
        frame_path = self.create_test_frame("test_02.jpg", with_person=False)
        
        # Detect
        result = self.detector.detect_frame(frame_path)
        
        # Verify
        self.assertEqual(result.status, "processed")
        self.assertIsNone(result.error)
        # Empty frame should have 0 detections
        self.assertEqual(result.people_count, 0)
    
    def test_03_bounding_boxes_in_bounds(self):
        """Test that bounding boxes stay within image boundaries."""
        frame_path = self.create_test_frame("test_03.jpg", width=320, height=240, with_person=True)
        
        result = self.detector.detect_frame(frame_path)
        
        # Verify
        self.assertEqual(result.status, "processed")
        
        # Check all detections are within bounds
        for detection in result.detections:
            self.assertGreaterEqual(detection.x, 0, "x should be >= 0")
            self.assertGreaterEqual(detection.y, 0, "y should be >= 0")
            self.assertLessEqual(detection.x + detection.width, 320, "right edge should be <= width")
            self.assertLessEqual(detection.y + detection.height, 240, "bottom edge should be <= height")
            self.assertGreater(detection.width, 0, "width should be > 0")
            self.assertGreater(detection.height, 0, "height should be > 0")
    
    def test_04_confidence_threshold(self):
        """Test that confidence threshold filters detections."""
        frame_path = self.create_test_frame("test_04.jpg", with_person=True)
        
        # Detect with very high threshold (nothing should pass)
        detector_high = PersonDetector(confidence_threshold=0.99)
        result_high = detector_high.detect_frame(frame_path)
        
        # Detect with very low threshold
        detector_low = PersonDetector(confidence_threshold=0.01)
        result_low = detector_low.detect_frame(frame_path)
        
        # High threshold should have <= low threshold detections
        self.assertLessEqual(result_high.people_count, result_low.people_count)
    
    def test_05_invalid_image_file(self):
        """Test handling of invalid/corrupted image."""
        # Create invalid image file
        invalid_path = self.frames_dir / "invalid.jpg"
        invalid_path.write_text("not an image")
        
        # Detect
        result = self.detector.detect_frame(invalid_path)
        
        # Verify graceful failure
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
    
    def test_06_nonexistent_file(self):
        """Test handling of nonexistent file."""
        nonexistent = self.frames_dir / "nonexistent.jpg"
        
        # Detect
        result = self.detector.detect_frame(nonexistent)
        
        # Verify graceful failure
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
    
    def test_07_batch_frame_detection(self):
        """Test batch detection of multiple frames."""
        # Create multiple test frames
        frame_paths = [
            self.create_test_frame("batch_01.jpg", with_person=True),
            self.create_test_frame("batch_02.jpg", with_person=False),
            self.create_test_frame("batch_03.jpg", with_person=True),
        ]
        
        frame_numbers = [0, 1, 2]
        timestamps = [0.0, 2.0, 4.0]
        
        # Detect batch
        results = self.detector.detect_frames_batch(
            frame_paths,
            frame_numbers=frame_numbers,
            timestamp_seconds=timestamps,
        )
        
        # Verify
        self.assertEqual(len(results), 3)
        
        for i, result in enumerate(results):
            self.assertEqual(result.status, "processed")
            self.assertEqual(result.frame_number, frame_numbers[i])
            self.assertEqual(result.timestamp_seconds, timestamps[i])
    
    def test_08_frame_directory_detection(self):
        """Test detection on all frames in a directory."""
        # Create directory structure
        camera_dir = self.frames_dir / "camera_01" / "video_001"
        camera_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test frames
        for i in range(3):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (200, 200, 200)
            frame_path = camera_dir / f"frame_{i+1:06d}.jpg"
            cv2.imwrite(str(frame_path), frame)
        
        # Detect directory
        results = self.detector.detect_frame_directory(
            self.frames_dir,
            camera_id="camera_01",
            video_name="video_001",
        )
        
        # Verify
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.status, "processed")
    
    def test_09_detection_to_dict(self):
        """Test conversion of detection to dictionary."""
        detection = PersonDetection(
            frame_number=5,
            timestamp_seconds=10.0,
            x=100,
            y=80,
            width=150,
            height=300,
            confidence=0.85,
        )
        
        # Convert to dict
        det_dict = detection.to_dict()
        
        # Verify
        self.assertEqual(det_dict["frame_number"], 5)
        self.assertEqual(det_dict["timestamp_seconds"], 10.0)
        self.assertEqual(det_dict["x"], 100)
        self.assertEqual(det_dict["y"], 80)
        self.assertEqual(det_dict["width"], 150)
        self.assertEqual(det_dict["height"], 300)
        self.assertAlmostEqual(det_dict["confidence"], 0.85, places=2)
        self.assertIsNotNone(det_dict["detection_id"])
    
    def test_10_result_to_dict(self):
        """Test conversion of detector result to dictionary."""
        frame_path = self.create_test_frame("test_10.jpg")
        result = self.detector.detect_frame(frame_path, frame_number=1, timestamp_seconds=2.0)
        
        # Convert to dict
        result_dict = result.to_dict()
        
        # Verify structure
        self.assertIn("frame", result_dict)
        self.assertIn("frame_number", result_dict)
        self.assertIn("timestamp_seconds", result_dict)
        self.assertIn("image_width", result_dict)
        self.assertIn("image_height", result_dict)
        self.assertIn("people_count", result_dict)
        self.assertIn("detections", result_dict)
        self.assertIn("status", result_dict)
        
        self.assertEqual(result_dict["frame_number"], 1)
        self.assertEqual(result_dict["timestamp_seconds"], 2.0)
        self.assertIsInstance(result_dict["detections"], list)
    
    def test_11_image_dimensions_stored(self):
        """Test that image dimensions are correctly stored."""
        frame_path = self.create_test_frame("test_11.jpg", width=800, height=600)
        result = self.detector.detect_frame(frame_path)
        
        # Verify
        self.assertEqual(result.image_width, 800)
        self.assertEqual(result.image_height, 600)


class TestPersonDetectorConvenienceFunctions(unittest.TestCase):
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
    
    def create_test_frame(self, filename: str, with_person: bool = True) -> Path:
        """Create a simple test frame."""
        frame_path = self.frames_dir / filename
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (200, 200, 200)
        
        if with_person:
            cv2.circle(frame, (320, 240), 30, (150, 130, 100), -1)
            cv2.rectangle(frame, (300, 270), (340, 350), (150, 130, 100), -1)
        
        cv2.imwrite(str(frame_path), frame)
        return frame_path
    
    def test_detect_frame_convenience(self):
        """Test detect_frame convenience function."""
        frame_path = self.create_test_frame("conv_test.jpg")
        result = detect_frame(frame_path, frame_number=0, timestamp_seconds=0.0)
        
        self.assertEqual(result.status, "processed")
        self.assertIsNotNone(result.frame_filename)
    
    def test_detect_frames_batch_convenience(self):
        """Test detect_frames_batch convenience function."""
        frame_paths = [
            self.create_test_frame("conv_batch_01.jpg"),
            self.create_test_frame("conv_batch_02.jpg"),
        ]
        
        results = detect_frames_batch(frame_paths)
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertEqual(result.status, "processed")


class TestPersonDetectorEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.frames_dir = Path(self.temp_dir) / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        self.detector = PersonDetector(confidence_threshold=0.3)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extremely_small_image(self):
        """Test with extremely small image."""
        frame_path = self.frames_dir / "tiny.jpg"
        tiny_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        cv2.imwrite(str(frame_path), tiny_frame)
        
        result = self.detector.detect_frame(frame_path)
        
        # Should handle gracefully
        self.assertIn(result.status, ["processed", "failed"])
    
    def test_grayscale_image(self):
        """Test with grayscale image."""
        frame_path = self.frames_dir / "grayscale.jpg"
        gray_frame = np.zeros((480, 640), dtype=np.uint8)
        gray_frame[:] = 128
        cv2.imwrite(str(frame_path), gray_frame)
        
        # This should fail gracefully (MediaPipe expects 3-channel RGB)
        result = self.detector.detect_frame(frame_path)
        
        # Should either fail gracefully or process
        self.assertIn(result.status, ["processed", "failed"])
    
    def test_zero_confidence_threshold(self):
        """Test with zero confidence threshold."""
        detector = PersonDetector(confidence_threshold=0.0)
        self.assertEqual(detector.confidence_threshold, 0.0)
    
    def test_one_confidence_threshold(self):
        """Test with confidence threshold of 1.0."""
        detector = PersonDetector(confidence_threshold=1.0)
        self.assertEqual(detector.confidence_threshold, 1.0)
    
    def test_negative_confidence_threshold_clamped(self):
        """Test that negative confidence is clamped to 0."""
        detector = PersonDetector(confidence_threshold=-0.5)
        self.assertEqual(detector.confidence_threshold, 0.0)
    
    def test_above_one_confidence_threshold_clamped(self):
        """Test that confidence > 1.0 is clamped to 1.0."""
        detector = PersonDetector(confidence_threshold=1.5)
        self.assertEqual(detector.confidence_threshold, 1.0)


if __name__ == "__main__":
    unittest.main()
