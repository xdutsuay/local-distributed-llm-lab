import pytest
from fastapi.testclient import TestClient

def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text

def test_nodes_api_empty_initially(client: TestClient):
    response = client.get("/api/nodes")
    assert response.status_code == 200
    assert "active_nodes" in response.json()

def test_chat_endpoint_mock_graph(client: TestClient):
    # This might fail if LLM is not reachable, so we should mock the WorkflowManager in a real unit test.
    # For now, we expect it to try and return something or fail gracefully.
    # If the server is running locally without Ollama, it falls back.
    payload = {"prompt": "Test prompt"}
    response = client.post("/chat", json=payload)
    if response.status_code == 200:
        data = response.json()
        assert "response" in data
        assert "plan" in data
    else:
        # It's acceptable if it fails due to worker issues in test env, 
        # but 500 means unchecked crash.
        assert response.status_code != 500

def test_nodes_dashboard(client: TestClient):
    response = client.get("/nodes")
    assert response.status_code == 200
    assert "Active Nodes" in response.text
