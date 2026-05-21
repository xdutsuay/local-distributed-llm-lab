import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import os
import json

# Set environment variable before any imports
os.environ["RAY_MOCK_MODE"] = "1"

@pytest.fixture(scope="session", autouse=True)
def mock_lmstudio_http():
    """Mock LM Studio OpenAI-compatible API when INFERENCE_BACKEND=lmstudio."""
    try:
        import requests
    except ImportError:
        yield
        return

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "choices": [
                    {"message": {"content": "Mock LM Studio response"}}
                ]
            }

        text = ""

    def _fake_post(url, *args, **kwargs):
        return _FakeResponse()

    with patch.object(requests, "post", side_effect=_fake_post):
        yield


@pytest.fixture(scope="session", autouse=True)
def mock_ollama():
    """Mock Ollama library calls session-wide to speed up test execution"""
    with patch('ollama.chat') as mock_chat, \
         patch('ollama.list') as mock_list:
        
        def mock_chat_impl(model, messages, **kwargs):
            # Check if planner request
            is_planner = False
            for m in messages:
                content = m.get("content", "")
                if "task planner" in content or "decompose a user request" in content:
                    is_planner = True
                    break
            
            if is_planner:
                return {
                    "message": {
                        "content": json.dumps([
                            {"step_id": 1, "description": "Preprocess test prompt", "worker_type": "tool_worker", "payload": {"prompt": "Preprocess"}},
                            {"step_id": 2, "description": "Tokenize text", "worker_type": "llm_worker", "payload": {"prompt": "Tokenize"}},
                            {"step_id": 3, "description": "Summarize test prompt", "worker_type": "llm_worker", "payload": {"prompt": "Summarize"}},
                            {"step_id": 4, "description": "Rank summarization results", "worker_type": "tool_worker", "payload": {"prompt": "Rank"}}
                        ])
                    }
                }
            
            return {
                "message": {
                    "content": "This is a mock chat response from ollama.chat"
                }
            }
        
        mock_chat.side_effect = mock_chat_impl
        mock_list.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "qwen2.5-coder"}
            ]
        }
        
        yield {
            "chat": mock_chat,
            "list": mock_list
        }

@pytest.fixture(scope="session", autouse=True)
def mock_vector_store():
    """Mock Chromadb VectorStore session-wide to avoid heavy embedding model downloads/inferences"""
    with patch('coordinator.memory.VectorStore') as mock_class, \
         patch('coordinator.memory.get_vector_store') as mock_get:
        
        mock_instance = MagicMock()
        mock_instance.search.return_value = []
        mock_instance.count.return_value = 0
        
        mock_class.return_value = mock_instance
        mock_get.return_value = mock_instance
        yield mock_instance

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Initialize SQLite database for all tests"""
    import asyncio
    from coordinator import db
    asyncio.run(db.init_db())

@pytest.fixture(scope="session", autouse=True)
def mock_ray_session():
    """Mock Ray initialization for all tests (session-wide)"""
    with patch('ray.init') as mock_init, \
         patch('ray.get_actor') as mock_get_actor, \
         patch('ray.get') as mock_get, \
         patch('ray.is_initialized') as mock_is_init, \
         patch('ray.kill') as mock_kill, \
         patch('ray.nodes') as mock_nodes:
        
        # Configure mocks
        mock_init.return_value = None
        mock_is_init.return_value = True
        mock_nodes.return_value = [{"NodeID": "mock-node-1", "Alive": True}]
        
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
            "kill": mock_kill,
            "nodes": mock_nodes
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
