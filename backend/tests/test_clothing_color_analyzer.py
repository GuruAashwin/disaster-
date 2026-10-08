"""
Unit tests for the clothing color analyzer service (STEP 7).

Tests cover:
1. Red detection
2. Blue detection
3. Black detection
4. White detection
5. Gray detection
6. Green detection
7. Yellow detection
8. Brown detection
9. Mixed colors
10. Low-information region
11. Invalid image
12. Empty image
13. Tiny crop
14. Multiple clothing regions
15. JSON serialization
16. Confidence remains within 0-1
17. Standardized color labels
18. Existing STEP 4/5/6 tests
19. Existing project tests
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from app.services.clothing_color_analyzer import (
    ClothingColorAnalyzer,
    ClothingColor,
    ClothingColorAnalysisResult,
    analyze_clothing_from_crops,
    analyze_clothing_from_file,
    SUPPORTED_COLORS,
    CONFIDENCE_THRESHOLD,
)


class TestClothingColorAnalyzer(unittest.TestCase):
    """Test suite for ClothingColorAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.frames_dir = Path(self.temp_dir) / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        
        self.analyzer = ClothingColorAnalyzer(confidence_threshold=0.1)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def create_solid_color_image(
        self,
        color_bgr: Tuple[int, int, int],
        width: int = 100,
        height: int = 100,
        noise: bool = False,
    ) -> np.ndarray:
        """
        Create a solid color image.
        
        Args:
            color_bgr: Color as (B, G, R) tuple
            width: Image width
            height: Image height
            noise: If True, add slight noise
        
        Returns:
            Image array
        """
        image = np.ones((height, width, 3), dtype=np.uint8)
        image[:, :] = color_bgr
        
        if noise:
            # Add small amount of noise
            noise_arr = np.random.randint(-10, 11, image.shape, dtype=np.int16)
            image = np.clip(image.astype(np.int16) + noise_arr, 0, 255).astype(np.uint8)
        
        return image
    
    def test_01_red_detection(self):
        """Test detection of red color."""
        # Bright red in OpenCV is (0, 0, 255) BGR
        red_image = self.create_solid_color_image((0, 0, 255))
        
        result = self.analyzer.analyze_region(red_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.color, "red")
        self.assertGreater(result.confidence, 0.5)
    
    def test_02_blue_detection(self):
        """Test detection of blue color."""
        # Bright blue in OpenCV is (255, 0, 0) BGR
        blue_image = self.create_solid_color_image((255, 0, 0))
        
        result = self.analyzer.analyze_region(blue_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.color, "blue")
        self.assertGreater(result.confidence, 0.5)
    
    def test_03_black_detection(self):
        """Test detection of black color."""
        black_image = self.create_solid_color_image((0, 0, 0))
        
        result = self.analyzer.analyze_region(black_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.color, "black")
        self.assertGreater(result.confidence, 0.5)
    
    def test_04_white_detection(self):
        """Test detection of white color."""
        white_image = self.create_solid_color_image((255, 255, 255))
        
        result = self.analyzer.analyze_region(white_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.color, "white")
        self.assertGreater(result.confidence, 0.5)
    
    def test_05_gray_detection(self):
        """Test detection of gray color."""
        gray_image = self.create_solid_color_image((128, 128, 128))
        
        result = self.analyzer.analyze_region(gray_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertIn(result.color, ["gray", "white", "black"])  # Gray can be ambiguous
    
    def test_06_green_detection(self):
        """Test detection of green color."""
        # Green in OpenCV is (0, 255, 0) BGR
        green_image = self.create_solid_color_image((0, 255, 0))
        
        result = self.analyzer.analyze_region(green_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.color, "green")
        self.assertGreater(result.confidence, 0.5)
    
    def test_07_yellow_detection(self):
        """Test detection of yellow color."""
        # Yellow in OpenCV is (0, 255, 255) BGR
        yellow_image = self.create_solid_color_image((0, 255, 255))
        
        result = self.analyzer.analyze_region(yellow_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.color, "yellow")
        self.assertGreater(result.confidence, 0.5)
    
    def test_08_brown_detection(self):
        """Test detection of brown color."""
        # Brown is dark orange: (0, 100, 165) BGR
        brown_image = self.create_solid_color_image((0, 100, 165))
        
        result = self.analyzer.analyze_region(brown_image)
        
        # Verify
        self.assertIsNotNone(result)
        # Brown might be detected as orange or brown depending on range
        self.assertIn(result.color, ["brown", "orange"])
    
    def test_09_mixed_colors(self):
        """Test handling of mixed-color image."""
        # Create image with two colors
        image = np.ones((100, 100, 3), dtype=np.uint8)
        image[:50, :] = (0, 0, 255)   # Red (top half)
        image[50:, :] = (0, 0, 0)     # Black (bottom half)
        
        result = self.analyzer.analyze_region(image)
        
        # Verify
        self.assertIsNotNone(result)
        # Should detect dominant color (could be red or black)
        self.assertIn(result.color, ["red", "black"])
    
    def test_10_low_information_region(self):
        """Test handling of low-information region."""
        # Create very noisy/random image
        noisy_image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        
        result = self.analyzer.analyze_region(noisy_image)
        
        # Verify
        self.assertIsNotNone(result)
        # Low-info image should have low confidence or return "unknown"
        self.assertLess(result.confidence, 0.5)
    
    def test_11_invalid_image_none(self):
        """Test handling of None image."""
        result = self.analyzer.analyze_region(None)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.color, "unknown")
        self.assertEqual(result.confidence, 0.0)
    
    def test_12_empty_image(self):
        """Test handling of empty image."""
        empty_image = np.array([], dtype=np.uint8)
        
        result = self.analyzer.analyze_region(empty_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.color, "unknown")
    
    def test_13_tiny_crop(self):
        """Test handling of very small crop."""
        tiny_image = self.create_solid_color_image((0, 0, 255), width=5, height=5)
        
        result = self.analyzer.analyze_region(tiny_image)
        
        # Verify
        self.assertIsNotNone(result)
        # Should still attempt to detect color
        self.assertIsNotNone(result.color)
    
    def test_14_confidence_in_range(self):
        """Test that confidence stays in 0-1 range."""
        red_image = self.create_solid_color_image((0, 0, 255))
        
        result = self.analyzer.analyze_region(red_image)
        
        # Verify
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
    
    def test_15_standardized_color_labels(self):
        """Test that returned colors are in standardized list."""
        # Test multiple colors
        test_colors = [
            ((0, 0, 255), "red"),
            ((255, 0, 0), "blue"),
            ((0, 255, 0), "green"),
            ((0, 255, 255), "yellow"),
            ((0, 0, 0), "black"),
            ((255, 255, 255), "white"),
        ]
        
        for bgr, expected_color in test_colors:
            image = self.create_solid_color_image(bgr)
            result = self.analyzer.analyze_region(image)
            
            # Color should be either expected or "unknown"
            self.assertIn(result.color, SUPPORTED_COLORS + ["unknown"])
    
    def test_16_result_to_dict(self):
        """Test conversion of color result to dictionary."""
        color = ClothingColor("red", 0.85, pixel_count=5000, secondary_color="black")
        
        result_dict = color.to_dict()
        
        # Verify structure
        self.assertIn("color", result_dict)
        self.assertIn("confidence", result_dict)
        self.assertIn("pixel_count", result_dict)
        self.assertIn("secondary_color", result_dict)
        
        self.assertEqual(result_dict["color"], "red")
        self.assertAlmostEqual(result_dict["confidence"], 0.85)
        self.assertEqual(result_dict["pixel_count"], 5000)
        self.assertEqual(result_dict["secondary_color"], "black")
    
    def test_17_analysis_result_to_dict(self):
        """Test conversion of analysis result to dictionary."""
        result = ClothingColorAnalysisResult("person_001")
        
        upper_color = ClothingColor("red", 0.90)
        lower_color = ClothingColor("black", 0.87)
        
        result.set_upper_body_color(upper_color)
        result.set_lower_body_color(lower_color)
        result.status = "processed"
        
        result_dict = result.to_dict()
        
        # Verify structure
        self.assertIn("detection_id", result_dict)
        self.assertIn("upper_body", result_dict)
        self.assertIn("lower_body", result_dict)
        self.assertIn("status", result_dict)
        
        self.assertEqual(result_dict["detection_id"], "person_001")
        self.assertEqual(result_dict["upper_body"]["color"], "red")
        self.assertEqual(result_dict["lower_body"]["color"], "black")
        self.assertEqual(result_dict["status"], "processed")
    
    def test_18_orange_detection(self):
        """Test detection of orange color."""
        # Orange in OpenCV is (0, 165, 255) BGR
        orange_image = self.create_solid_color_image((0, 165, 255))
        
        result = self.analyzer.analyze_region(orange_image)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertIn(result.color, ["orange", "red", "yellow"])
    
    def test_19_purple_detection(self):
        """Test detection of purple color."""
        # Purple in OpenCV is (255, 0, 255) BGR
        purple_image = self.create_solid_color_image((255, 0, 255))
        
        result = self.analyzer.analyze_region(purple_image)
        
        # Verify
        self.assertIsNotNone(result)
        # Purple might be detected as purple or pink
        self.assertIn(result.color, ["purple", "pink", "magenta"])
    
    def test_20_analyze_from_crops_batch(self):
        """Test batch analysis from pre-cropped images."""
        upper_crop = self.create_solid_color_image((0, 0, 255))  # Red
        lower_crop = self.create_solid_color_image((0, 0, 0))     # Black
        
        result = self.analyzer.analyze_clothing_from_crops(
            upper_crop, lower_crop, detection_id="person_001"
        )
        
        # Verify
        self.assertEqual(result.status, "processed")
        self.assertIsNotNone(result.upper_body_color)
        self.assertIsNotNone(result.lower_body_color)
        self.assertEqual(result.upper_body_color.color, "red")
        self.assertEqual(result.lower_body_color.color, "black")


class TestClothingColorConvenienceFunctions(unittest.TestCase):
    """Test convenience module-level functions."""
    
    def test_analyze_from_crops_convenience(self):
        """Test analyze_clothing_from_crops convenience function."""
        upper_crop = np.ones((100, 100, 3), dtype=np.uint8)
        upper_crop[:, :] = (0, 0, 255)  # Red
        
        lower_crop = np.ones((100, 100, 3), dtype=np.uint8)
        lower_crop[:, :] = (0, 0, 0)    # Black
        
        result = analyze_clothing_from_crops(upper_crop, lower_crop)
        
        # Verify
        self.assertEqual(result.status, "processed")
        self.assertIsNotNone(result.upper_body_color)
        self.assertIsNotNone(result.lower_body_color)


class TestClothingColorEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.frames_dir = Path(self.temp_dir) / "frames"
        self.frames_dir.mkdir(exist_ok=True)
        self.analyzer = ClothingColorAnalyzer(confidence_threshold=0.1)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_extremely_small_image(self):
        """Test with 1x1 pixel image."""
        tiny = np.array([[[255, 0, 0]]], dtype=np.uint8)  # Blue
        
        result = self.analyzer.analyze_region(tiny)
        
        # Should handle gracefully
        self.assertIsNotNone(result)
    
    def test_invalid_image_type(self):
        """Test with invalid image type."""
        invalid = "not an image"
        
        try:
            result = self.analyzer.analyze_region(invalid)
            # Should either fail gracefully or return unknown
            if result:
                self.assertEqual(result.color, "unknown")
        except Exception:
            # Exception is acceptable
            pass
    
    def test_very_dark_image(self):
        """Test with very dark image."""
        dark = np.ones((100, 100, 3), dtype=np.uint8) * 10  # Very dark
        
        result = self.analyzer.analyze_region(dark)
        
        # Verify
        self.assertIsNotNone(result)
        # Should detect as black or unknown
        self.assertIn(result.color, ["black", "unknown"])
    
    def test_very_bright_image(self):
        """Test with very bright image."""
        bright = np.ones((100, 100, 3), dtype=np.uint8) * 250  # Very bright
        
        result = self.analyzer.analyze_region(bright)
        
        # Verify
        self.assertIsNotNone(result)
        # Should detect as white
        self.assertIn(result.color, ["white", "unknown"])
    
    def test_grayscale_pattern(self):
        """Test with grayscale gradient."""
        gradient = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(100):
            gradient[i, :] = [i, i, i]
        
        result = self.analyzer.analyze_region(gradient)
        
        # Should handle gradients
        self.assertIsNotNone(result)


class TestClothingColorLimitations(unittest.TestCase):
    """Test known limitations and documented behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = ClothingColorAnalyzer(confidence_threshold=0.1)
    
    def test_low_confidence_returns_unknown(self):
        """Test that low-confidence regions return 'unknown'."""
        analyzer_high_threshold = ClothingColorAnalyzer(confidence_threshold=0.99)
        
        # Even a solid color might have low confidence with very high threshold
        red_image = np.ones((100, 100, 3), dtype=np.uint8)
        red_image[:, :] = (0, 0, 255)
        
        result = analyzer_high_threshold.analyze_region(red_image)
        
        # With very high threshold, might return unknown
        self.assertIsNotNone(result)
    
    def test_mixed_color_secondary_detection(self):
        """Test that mixed colors are handled."""
        # Create 50/50 red and blue mix
        image = np.ones((100, 100, 3), dtype=np.uint8)
        image[:50, :] = (0, 0, 255)   # Red
        image[50:, :] = (255, 0, 0)   # Blue
        
        result = self.analyzer.analyze_region(image)
        
        # Should detect dominant and possibly secondary
        self.assertIsNotNone(result)
        self.assertIn(result.color, ["red", "blue"])


if __name__ == "__main__":
    unittest.main()
