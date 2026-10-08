"""
Comprehensive test suite for ENHANCED color analyzer improvements.

Tests cover:
1. Lighting robustness (dark, bright, shadow, highlight)
2. Red color family (red, maroon, orange)
3. Blue color family (blue, navy)
4. Dark colors (black, dark gray)
5. Light colors (white, beige, light gray)
6. Confidence scoring
7. Multi-stage pipeline verification
"""

import unittest
import numpy as np
import cv2
from app.services.clothing_color_analyzer import (
    ClothingColorAnalyzer,
    SUPPORTED_COLORS,
)


class TestColorImprovements(unittest.TestCase):
    """Test enhanced color analyzer improvements."""
    
    def setUp(self):
        self.analyzer = ClothingColorAnalyzer(confidence_threshold=0.2)
    
    def create_solid_color_image(self, bgr_tuple, width=100, height=100):
        """Create a solid color test image."""
        img = np.ones((height, width, 3), dtype=np.uint8)
        img[:, :] = bgr_tuple
        return img
    
    def test_red_family_detection(self):
        """Test RED family colors are detected correctly."""
        # Bright red
        bright_red = self.create_solid_color_image((0, 0, 255))
        result = self.analyzer.analyze_region(bright_red)
        self.assertEqual(result.color, "red", "Bright red should be detected as red")
        self.assertGreater(result.confidence, 0.4, "Bright red confidence should be > 0.4")
        
        # Dark red / Maroon
        dark_red = self.create_solid_color_image((0, 0, 100))
        result = self.analyzer.analyze_region(dark_red)
        self.assertIn(result.color, ["red", "maroon"], "Dark red should be red or maroon")
    
    def test_blue_family_detection(self):
        """Test BLUE family colors are detected correctly."""
        # Bright blue
        bright_blue = self.create_solid_color_image((255, 0, 0))
        result = self.analyzer.analyze_region(bright_blue)
        self.assertEqual(result.color, "blue", "Bright blue should be detected as blue")
        self.assertGreater(result.confidence, 0.4, "Bright blue confidence should be > 0.4")
        
        # Navy (dark blue)
        navy = self.create_solid_color_image((128, 0, 0))
        result = self.analyzer.analyze_region(navy)
        self.assertIn(result.color, ["blue", "navy"], "Navy should be blue or navy")
    
    def test_green_detection(self):
        """Test GREEN detection."""
        green = self.create_solid_color_image((0, 255, 0))
        result = self.analyzer.analyze_region(green)
        self.assertEqual(result.color, "green", "Green should be detected")
        self.assertGreater(result.confidence, 0.4)
    
    def test_yellow_detection(self):
        """Test YELLOW detection."""
        yellow = self.create_solid_color_image((0, 255, 255))
        result = self.analyzer.analyze_region(yellow)
        self.assertEqual(result.color, "yellow", "Yellow should be detected")
        self.assertGreater(result.confidence, 0.4)
    
    def test_orange_detection(self):
        """Test ORANGE detection."""
        orange = self.create_solid_color_image((0, 165, 255))
        result = self.analyzer.analyze_region(orange)
        self.assertIn(result.color, ["orange", "red", "yellow"], "Orange should be detected")
    
    def test_dark_colors(self):
        """Test DARK colors (black, dark gray)."""
        # Black
        black = self.create_solid_color_image((0, 0, 0))
        result = self.analyzer.analyze_region(black)
        self.assertEqual(result.color, "black", "Black should be detected")
        self.assertGreater(result.confidence, 0.4)
        
        # Dark gray
        dark_gray = self.create_solid_color_image((50, 50, 50))
        result = self.analyzer.analyze_region(dark_gray)
        self.assertIn(result.color, ["black", "gray"], "Dark gray should be black or gray")
    
    def test_light_colors(self):
        """Test LIGHT colors (white, beige, light gray)."""
        # White
        white = self.create_solid_color_image((255, 255, 255))
        result = self.analyzer.analyze_region(white)
        self.assertEqual(result.color, "white", "White should be detected")
        self.assertGreater(result.confidence, 0.4)
        
        # Light gray
        light_gray = self.create_solid_color_image((200, 200, 200))
        result = self.analyzer.analyze_region(light_gray)
        self.assertIn(result.color, ["white", "gray", "beige"], "Light gray should be detected")
    
    def test_lighting_robustness(self):
        """
        Test that colors are robust to lighting variations.
        A red shirt under different lighting should still be detected as red.
        """
        # Create a red region
        red_normal = self.create_solid_color_image((0, 0, 200))
        result_normal = self.analyzer.analyze_region(red_normal)
        normal_color = result_normal.color
        
        # Bright version (bright lighting)
        red_bright = self.create_solid_color_image((10, 50, 255))
        result_bright = self.analyzer.analyze_region(red_bright)
        
        # Dark version (shadow)
        red_dark = self.create_solid_color_image((0, 0, 80))
        result_dark = self.analyzer.analyze_region(red_dark)
        
        # All should be red family
        self.assertIn(normal_color, ["red", "maroon"])
        self.assertIn(result_bright.color, ["red", "maroon", "orange"])
        self.assertIn(result_dark.color, ["red", "maroon"])
    
    def test_confidence_scoring(self):
        """Test that confidence scoring works correctly."""
        # Solid color = high confidence
        solid_red = self.create_solid_color_image((0, 0, 255))
        result_solid = self.analyzer.analyze_region(solid_red)
        
        # Mixed color = lower confidence
        mixed = np.ones((100, 100, 3), dtype=np.uint8)
        mixed[:50, :] = (0, 0, 255)  # Red
        mixed[50:, :] = (255, 0, 0)  # Blue
        result_mixed = self.analyzer.analyze_region(mixed)
        
        self.assertGreater(result_solid.confidence, result_mixed.confidence,
                           "Solid color should have higher confidence than mixed")
    
    def test_small_regions(self):
        """Test handling of small clothing regions."""
        # Very small region
        tiny = self.create_solid_color_image((0, 0, 255), width=10, height=10)
        result = self.analyzer.analyze_region(tiny)
        
        # Should either detect color or return unknown
        self.assertIn(result.color, SUPPORTED_COLORS + ["unknown"])
    
    def test_noisy_image(self):
        """Test handling of noisy/low-quality images."""
        # Create noisy image
        base = self.create_solid_color_image((0, 0, 200))
        noise = np.random.randint(-30, 31, base.shape, dtype=np.int16)
        noisy = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        result = self.analyzer.analyze_region(noisy)
        
        # Should detect as red or unknown (not completely wrong)
        self.assertIn(result.color, ["red", "maroon", "unknown"])
    
    def test_all_supported_colors(self):
        """Test that all supported colors can be detected."""
        # Map of typical BGR values for each color
        color_bgr_map = {
            "red": (0, 0, 255),
            "blue": (255, 0, 0),
            "green": (0, 255, 0),
            "yellow": (0, 255, 255),
            "orange": (0, 165, 255),
            "purple": (255, 0, 255),
            "pink": (200, 100, 200),
            "brown": (0, 100, 165),
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "gray": (128, 128, 128),
            "navy": (128, 0, 0),
            "beige": (180, 200, 220),
            "maroon": (0, 0, 100),
        }
        
        for color_name, bgr in color_bgr_map.items():
            img = self.create_solid_color_image(bgr)
            result = self.analyzer.analyze_region(img)
            
            # Result should be a valid supported color or unknown
            self.assertIn(result.color, SUPPORTED_COLORS + ["unknown"],
                         f"Color {color_name} should map to a supported color, got {result.color}")
            
            # Most should have reasonable confidence (> 0.2)
            if result.color != "unknown":
                self.assertGreater(result.confidence, 0.2,
                                 f"Color {color_name} should have confidence > 0.2")


class TestPipelineStages(unittest.TestCase):
    """Test individual stages of the enhanced pipeline."""
    
    def setUp(self):
        self.analyzer = ClothingColorAnalyzer(confidence_threshold=0.1)
    
    def test_center_region_extraction(self):
        """Test that center region extraction reduces edge contamination."""
        # Create image with different colors in center vs edges
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        # Red in center
        img[20:80, 20:80] = (0, 0, 255)
        # Blue on edges
        img[0:20, :] = (255, 0, 0)
        img[80:, :] = (255, 0, 0)
        img[:, 0:20] = (255, 0, 0)
        img[:, 80:] = (255, 0, 0)
        
        result = self.analyzer.analyze_region(img)
        
        # Should detect as red (from center)
        self.assertEqual(result.color, "red", "Should detect red from center region")
    
    def test_valid_pixel_mask(self):
        """Test that valid pixel mask correctly identifies analyzable pixels."""
        # Create a solid gray image
        gray_img = np.ones((100, 100, 3), dtype=np.uint8)
        gray_img[:, :] = (100, 100, 100)
        
        # Convert to HSV
        hsv = cv2.cvtColor(gray_img, cv2.COLOR_BGR2HSV)
        
        # Get valid mask
        valid_mask = self.analyzer._get_valid_pixel_mask(hsv)
        
        # Most pixels should be valid
        valid_count = np.count_nonzero(valid_mask)
        total = valid_mask.size
        
        self.assertGreater(valid_count / total, 0.95,
                          "Most pixels should be valid for normal image")


if __name__ == "__main__":
    unittest.main()
