"""
Unit tests for the video processor service.

Tests:
1. Valid video opens successfully
2. Frames are sampled correctly at intervals
3. Sample frames are saved
4. Timestamp/metadata is correct
5. Video metadata is returned
6. Invalid videos do not crash
7. Multiple videos process independently
8. Resources are released correctly
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from app.services.video_processor import (
    VideoProcessor,
    VideoProcessorResult,
    process_video,
    process_video_directory,
    DEFAULT_SAMPLE_INTERVAL_SECONDS,
)


class TestVideoProcessor(unittest.TestCase):
    """Test suite for VideoProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.video_dir = Path(self.temp_dir) / "videos"
        self.output_dir = Path(self.temp_dir) / "frames"
        
        self.video_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize processor
        self.processor = VideoProcessor(
            video_dir=str(self.video_dir),
            output_dir=str(self.output_dir),
            sample_interval_seconds=2.0,
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_video(
        self,
        filename: str,
        duration_seconds: float = 10,
        fps: float = 10,
        width: int = 320,
        height: int = 240,
    ) -> Path:
        """
        Create a simple test video file.
        
        Args:
            filename: Name of video file to create
            duration_seconds: Duration of video
            fps: Frames per second
            width: Video width
            height: Video height
        
        Returns:
            Path to created video
        """
        video_path = self.video_dir / filename
        
        # Create parent directories if needed
        video_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(
            str(video_path),
            fourcc,
            fps,
            (width, height)
        )
        
        # Write frames
        frame_count = int(duration_seconds * fps)
        for i in range(frame_count):
            # Create a simple frame with a moving rectangle
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:] = (50, 50, 50)  # Gray background
            
            # Draw a rectangle that moves across the frame
            x = int((i / frame_count) * (width - 50))
            cv2.rectangle(frame, (x, 50), (x + 50, 100), (0, 255, 0), -1)
            
            # Add frame number
            cv2.putText(
                frame,
                f"Frame {i}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
            )
            
            writer.write(frame)
        
        writer.release()
        return video_path
    
    def test_01_valid_video_opens(self):
        """Test that a valid video opens successfully."""
        # Create test video
        video_path = self.create_test_video("test_01.mp4", duration_seconds=10)
        
        # Process video
        result = self.processor.process_video(video_path)
        
        # Verify
        self.assertEqual(result.status, "processed")
        self.assertIsNone(result.error)
        self.assertIsNotNone(result.fps)
        self.assertIsNotNone(result.total_frames)
        self.assertIsNotNone(result.duration_seconds)
        self.assertGreater(result.fps, 0)
        self.assertGreater(result.total_frames, 0)
    
    def test_02_frames_sampled_correctly(self):
        """Test that frames are sampled at correct intervals."""
        # Create 10-second video at 10fps = 100 frames total
        video_path = self.create_test_video(
            "test_02.mp4",
            duration_seconds=10,
            fps=10,
        )
        
        # Process with 2-second interval = process every 20 frames
        # Expected samples: 0s, 2s, 4s, 6s, 8s, 10s = 6 frames
        result = self.processor.process_video(video_path)
        
        # Verify
        self.assertEqual(result.status, "processed")
        self.assertGreaterEqual(result.frames_processed, 5)  # At least 5-6 samples
        self.assertLessEqual(result.frames_processed, 7)
    
    def test_03_frames_are_saved(self):
        """Test that sample frames are actually saved to disk."""
        # Create test video
        video_path = self.create_test_video("test_03.mp4", duration_seconds=6, fps=10)
        
        # Process video
        result = self.processor.process_video(video_path)
        
        # Verify
        self.assertEqual(result.status, "processed")
        self.assertGreater(result.frames_saved, 0)
        
        # Check that frame files exist
        frames_dir = Path(result.saved_frames_dir)
        self.assertTrue(frames_dir.exists())
        
        saved_files = list(frames_dir.glob("frame_*.jpg"))
        self.assertGreater(len(saved_files), 0)
        self.assertEqual(len(saved_files), result.frames_saved)
    
    def test_04_metadata_correct(self):
        """Test that video metadata is correct."""
        # Create test video: 8 seconds @ 10fps
        video_path = self.create_test_video(
            "test_04.mp4",
            duration_seconds=8,
            fps=10,
            width=320,
            height=240,
        )
        
        # Process
        result = self.processor.process_video(video_path)
        
        # Verify metadata
        self.assertEqual(result.status, "processed")
        self.assertAlmostEqual(result.fps, 10.0, delta=0.5)
        self.assertEqual(result.total_frames, 80)
        self.assertAlmostEqual(result.duration_seconds, 8.0, delta=0.5)
    
    def test_05_invalid_video_does_not_crash(self):
        """Test that invalid video files don't crash processor."""
        # Create a fake "video" file
        fake_video = self.video_dir / "not_a_video.mp4"
        fake_video.write_text("This is not a video file")
        
        # Process - should fail gracefully
        result = self.processor.process_video(fake_video)
        
        # Verify
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
        self.assertIn("Unable to open", result.error)
    
    def test_06_nonexistent_video_fails_gracefully(self):
        """Test that nonexistent video files fail gracefully."""
        fake_path = self.video_dir / "does_not_exist.mp4"
        
        # Process
        result = self.processor.process_video(fake_path)
        
        # Verify
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)
    
    def test_07_multiple_videos_independent(self):
        """Test that multiple videos process independently."""
        # Create two test videos
        video1 = self.create_test_video("video_1.mp4", duration_seconds=5, fps=10)
        video2 = self.create_test_video("video_2.mp4", duration_seconds=8, fps=10)
        
        # Process both
        result1 = self.processor.process_video(video1)
        result2 = self.processor.process_video(video2)
        
        # Verify both succeeded independently
        self.assertEqual(result1.status, "processed")
        self.assertEqual(result2.status, "processed")
        
        # Verify different frame counts due to different durations
        self.assertNotEqual(result1.frames_processed, result2.frames_processed)
        
        # Verify separate frame directories
        self.assertNotEqual(
            result1.saved_frames_dir,
            result2.saved_frames_dir
        )
    
    def test_08_resources_released(self):
        """Test that resources are properly released."""
        # Create test video
        video_path = self.create_test_video("test_08.mp4", duration_seconds=5)
        
        # Process multiple times - if resources aren't released, this would fail
        for i in range(3):
            result = self.processor.process_video(video_path)
            self.assertEqual(result.status, "processed")
    
    def test_09_camera_id_inference(self):
        """Test that camera ID is correctly inferred from directory structure."""
        # Create subdirectory for camera
        camera_dir = self.video_dir / "camera_01"
        camera_dir.mkdir(exist_ok=True)
        
        # Create test video in camera directory
        video_path = self.create_test_video(
            "camera_01/test_video.mp4",
            duration_seconds=5
        )
        
        # Process
        result = self.processor.process_video(video_path)
        
        # Verify camera_id is inferred
        self.assertEqual(result.camera_id, "camera_01")
    
    def test_10_process_directory(self):
        """Test processing entire directory."""
        # Create multiple test videos
        self.create_test_video("camera_01/video_1.mp4", duration_seconds=5)
        self.create_test_video("camera_02/video_2.mp4", duration_seconds=5)
        
        # Create invalid video
        (self.video_dir / "invalid.mp4").write_text("not a video")
        
        # Process directory
        results = self.processor.process_video_directory()
        
        # Verify
        self.assertEqual(len(results), 3)  # 2 valid + 1 invalid
        
        # Count successes and failures
        successes = [r for r in results if r["status"] == "processed"]
        failures = [r for r in results if r["status"] == "failed"]
        
        self.assertEqual(len(successes), 2)
        self.assertEqual(len(failures), 1)


class TestVideoProcessorFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.video_dir = Path(self.temp_dir) / "videos"
        self.output_dir = Path(self.temp_dir) / "frames"
        
        self.video_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_video(self, filename: str, duration_seconds: float = 5):
        """Helper to create test video."""
        video_path = self.video_dir / filename
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(
            str(video_path),
            fourcc,
            10,
            (320, 240)
        )
        
        frame_count = int(duration_seconds * 10)
        for i in range(frame_count):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            frame[:] = (50, 50, 50)
            writer.write(frame)
        
        writer.release()
        return str(video_path)
    
    def test_result_to_dict(self):
        """Test VideoProcessorResult.to_dict()."""
        result = VideoProcessorResult("test.mp4", camera_id="camera_01")
        result.status = "processed"
        result.fps = 30
        result.frames_processed = 100
        
        result_dict = result.to_dict()
        
        # Verify dictionary structure
        self.assertIn("video", result_dict)
        self.assertIn("camera_id", result_dict)
        self.assertIn("status", result_dict)
        self.assertEqual(result_dict["video"], "test.mp4")
        self.assertEqual(result_dict["camera_id"], "camera_01")
        self.assertEqual(result_dict["status"], "processed")


if __name__ == "__main__":
    unittest.main()
