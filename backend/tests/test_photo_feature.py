"""
Test suite for photo collection and verification feature.

Tests:
1. Photo upload and storage
2. Photo retrieval by filename
3. Photo confidence calculation
4. End-to-end match flow with photo confidence
"""

import pytest
import uuid
import json
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models import Person, PersonType, User, UserRole, Match, MatchState
from app.schemas import PersonCreate


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Create a test user and return auth headers."""
    # Register a rescuer
    response = client.post("/auth/register", json={
        "username": f"test_rescuer_{uuid.uuid4()}",
        "password": "testpass123",
        "role": "rescuer"
    })
    assert response.status_code in [200, 201]
    
    # Login
    user_data = response.json()
    response = client.post("/auth/login", data={
        "username": user_data["username"],
        "password": "testpass123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def police_headers(client):
    """Create a police user and return auth headers."""
    # Register a police officer
    response = client.post("/auth/register", json={
        "username": f"test_police_{uuid.uuid4()}",
        "password": "testpass123",
        "role": "police"
    })
    assert response.status_code in [200, 201]
    
    # Login
    user_data = response.json()
    response = client.post("/auth/login", data={
        "username": user_data["username"],
        "password": "testpass123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


def create_test_image() -> bytes:
    """Create a minimal valid JPEG image for testing."""
    # Minimal JPEG (1x1 pixel, red)
    jpeg_data = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
        0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
        0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
        0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
        0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
        0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
        0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
        0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
        0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4,
        0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
        0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF,
        0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04,
        0x00, 0x00, 0x01, 0x7D, 0x01, 0x02, 0x03, 0x00,
        0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
        0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32,
        0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1,
        0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
        0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A,
        0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35,
        0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
        0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55,
        0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65,
        0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
        0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85,
        0x86, 0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94,
        0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
        0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2,
        0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA,
        0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
        0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8,
        0xD9, 0xDA, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6,
        0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
        0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA,
        0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
        0xFB, 0xD0, 0xFF, 0xD9
    ])
    return jpeg_data


class TestPhotoUpload:
    """Test photo upload functionality."""
    
    def test_submit_found_person_with_photo(self, client, auth_headers):
        """Test submitting a found person with a single photo."""
        image_data = create_test_image()
        
        response = client.post(
            "/persons/found",
            headers=auth_headers,
            data={
                "name": "John Doe",
                "age_raw": "35",
                "gender": "Male",
                "location": "Main Street",
                "condition": "stable"
            },
            files={"image": ("test.jpg", image_data, "image/jpeg")}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "found"
        assert "id" in data
        person_id = data["id"]
        
        # Check image was stored
        assert data.get("image_filename") is not None
    
    def test_upload_multiple_photos_to_existing_person(self, client, auth_headers):
        """Test uploading multiple photos to an existing found person."""
        # Create a person first
        response = client.post(
            "/persons/found",
            headers=auth_headers,
            data={
                "name": "Jane Smith",
                "location": "Downtown",
            }
        )
        assert response.status_code == 201
        person_id = response.json()["id"]
        
        # Upload multiple photos
        image_data = create_test_image()
        response = client.post(
            f"/persons/{person_id}/photos",
            headers=auth_headers,
            files=[
                ("photos", ("photo1.jpg", image_data, "image/jpeg")),
                ("photos", ("photo2.jpg", image_data, "image/jpeg")),
            ]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["photos_added"] == 2
        assert data["total_photos"] == 2
        assert len(data["photo_filenames"]) == 2
    
    def test_retrieve_photo_by_filename(self, client, auth_headers):
        """Test retrieving a photo by filename."""
        # Upload a photo first
        image_data = create_test_image()
        response = client.post(
            "/persons/found",
            headers=auth_headers,
            data={"name": "Test", "location": "Test Location"},
            files={"image": ("test.jpg", image_data, "image/jpeg")}
        )
        assert response.status_code == 201
        image_filename = response.json().get("image_filename")
        
        if image_filename:
            # Try to retrieve it
            response = client.get(
                f"/persons/photos/{image_filename}",
                headers=auth_headers
            )
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/jpeg"


class TestPhotoConfidence:
    """Test photo confidence calculation."""
    
    def test_match_includes_photo_confidence(self, client, auth_headers, police_headers):
        """Test that matches include photo confidence scores."""
        image_data = create_test_image()
        
        # Create found person with photos
        response = client.post(
            "/persons/found",
            headers=auth_headers,
            data={"name": "Found Person", "location": "Location A"},
            files={"image": ("test.jpg", image_data, "image/jpeg")}
        )
        assert response.status_code == 201
        found_id = response.json()["id"]
        
        # Create missing person with photos
        response = client.post(
            "/persons/missing",
            headers=auth_headers,
            data={"name": "Found Person", "location": "Location A"},
            files={"image": ("test.jpg", image_data, "image/jpeg")}
        )
        assert response.status_code == 201
        missing_id = response.json()["id"]
        
        # Trigger matching
        response = client.post(
            "/matches/run",
            headers=police_headers
        )
        assert response.status_code == 200
        
        # Retrieve matches as police
        response = client.get(
            "/matches?state=under_review",
            headers=police_headers
        )
        assert response.status_code == 200
        matches = response.json()
        
        # Should have at least one match
        assert len(matches) > 0
        match = matches[0]
        
        # Check photo confidence field exists
        assert "photo_confidence" in match
        # Should have a numeric confidence value (even if 0)
        assert isinstance(match["photo_confidence"], (int, float))
        
        # Check photo arrays
        assert "found_photos" in match
        assert "missing_photos" in match


class TestPhotoSecurity:
    """Test photo security measures."""
    
    def test_directory_traversal_protection(self, client, auth_headers):
        """Test that directory traversal attacks are blocked."""
        response = client.get(
            "/persons/photos/../../etc/passwd",
            headers=auth_headers
        )
        # Should return 403 Forbidden or 404
        assert response.status_code in [403, 404]
    
    def test_auth_required_for_photo_retrieval(self, client):
        """Test that authentication is required to retrieve photos."""
        response = client.get("/persons/photos/some_filename.jpg")
        # Should return 401 Unauthorized
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
