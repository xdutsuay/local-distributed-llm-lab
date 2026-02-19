import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import os

# Set environment variable before any imports
os.environ["RAY_MOCK_MODE"] = "1"

@pytest.fixture(scope="session", autouse=True)
def mock_ray_session():
    """Mock Ray initialization for all tests (session-wide)"""
    with patch('ray.init') as mock_init, \
         patch('ray.get_actor') as mock_get_actor, \
         patch('ray.get') as mock_get, \
         patch('ray.is_initialized') as mock_is_init, \
         patch('ray.kill') as mock_kill:
        
        # Configure mocks
        mock_init.return_value = None
        mock_is_init.return_value = True
        
        # Mock Ray actor
        mock_actor = MagicMock()
        mock_actor.generate.remote = MagicMock(return_value="test_response_ref")
        mock_actor.list_models.remote = MagicMock(return_value=["llama3.2", "mistral"])
        mock_actor.swap_model.remote = MagicMock(return_value={"status": "ok", "verification": "Model swapped"})
        mock_get_actor.return_value = mock_actor
        
        # Mock ray.get to return test responses
        def mock_get_response(ref):
            if ref == "test_response_ref":
                return {
                    "content": "This is a test response from mocked worker",
                    "node_id": "test-worker-1",
                    "model": "llama3.2",
                    "cached": False
                }
            return ref
        
        mock_get.side_effect = mock_get_response
        mock_kill.return_value = None
        
        yield {
            "init": mock_init,
            "get_actor": mock_get_actor,
            "get": mock_get,
            "is_initialized": mock_is_init,
            "kill": mock_kill
        }

@pytest.fixture(scope="module")
def app(mock_ray_session):
    """Import app only after Ray is mocked"""
    # Import must happen inside fixture after mocking is set up
    from coordinator.main import app as fastapi_app
    return fastapi_app

@pytest.fixture
def client(app):
    """FastAPI test client"""
    return TestClient(app)
