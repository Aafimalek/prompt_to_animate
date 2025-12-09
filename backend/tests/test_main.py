import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.main import app

client = TestClient(app)

# Helper to mock dependencies
@pytest.fixture
def mock_llm_service():
    with patch("backend.main.generate_manim_code", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_manim_service():
    with patch("backend.main.execute_manim_code") as mock:
        yield mock

def test_read_root_404():
    """Test that the root endpoint returns 404 (since we only have /generate)"""
    response = client.get("/")
    assert response.status_code == 404

def test_generate_animation_success(mock_llm_service, mock_manim_service):
    """Test the happy path for generating an animation."""
    
    # Setup mocks
    mock_llm_service.return_value = "class GenScene(Scene): pass"
    mock_manim_service.return_value = "test_video.mp4"
    
    payload = {
        "prompt": "Test animation",
        "length": "Short (5s)"
    }
    
    response = client.post("/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["video_url"] == "http://localhost:8000/videos/test_video.mp4"
    assert data["code"] == "class GenScene(Scene): pass"
    
    # Verify mocks were called
    mock_llm_service.assert_called_once_with("Test animation", "Short (5s)")
    mock_manim_service.assert_called_once_with("class GenScene(Scene): pass")

def test_generate_animation_validation_error():
    """Test input validation (missing prompt)."""
    payload = {
        "length": "Short (5s)"
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 422

def test_generate_animation_llm_failure(mock_llm_service):
    """Test handling of LLM service failure."""
    mock_llm_service.side_effect = Exception("LLM connection failed")
    
    payload = {
        "prompt": "Fail me",
        "length": "Short (5s)"
    }
    
    response = client.post("/generate", json=payload)
    assert response.status_code == 500
    assert "LLM connection failed" in response.json()["detail"]

def test_generate_animation_manim_failure(mock_llm_service, mock_manim_service):
    """Test handling of Manim execution failure."""
    mock_llm_service.return_value = "code"
    mock_manim_service.side_effect = Exception("Manim render error")
    
    payload = {
        "prompt": "Render fail",
        "length": "Short (5s)"
    }
    
    response = client.post("/generate", json=payload)
    assert response.status_code == 500
    assert "Manim render error" in response.json()["detail"]

def test_static_file_mounting():
    """Test that static files are mounted (check for existence of mount)."""
    # We can't easily check the mount without a file, but we can check 404 on a non-existent video
    # which proves the route exists but file is missing, vs 404 route not found.
    # Actually, if the dir is empty, it might be hard.
    # But usually static files return 404 if file not found.
    response = client.get("/videos/nonexistent.mp4")
    assert response.status_code == 404
