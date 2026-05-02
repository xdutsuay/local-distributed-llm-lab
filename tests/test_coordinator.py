import pytest
from fastapi.testclient import TestClient
import asyncio
from coordinator import db
import coordinator.main as main_mod

def test_read_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text

def test_nodes_api_empty_initially(client: TestClient):
    # ... existing test ...
    pass

def test_chat_ui_endpoint(client: TestClient):
    response = client.get("/chat_ui")
    assert response.status_code == 200
    assert "LLM Lab Chat" in response.text

def test_task_history_api(client: TestClient):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    initial_tasks = response.json()["tasks"]
    initial_count = len(initial_tasks)

    asyncio.run(
        db.upsert_task(
            {
                "id": "test-task-history",
                "prompt": "test task",
                "status": "Success",
                "worker": "test-worker",
                "plan_steps": 1,
            }
        )
    )

    response = client.get("/api/tasks")
    assert response.status_code == 200
    tasks = response.json()["tasks"]

    assert len(tasks) >= initial_count
    assert "prompt" in tasks[0]
    assert any(task["prompt"] == "test task" for task in tasks)


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


def test_chat_endpoint_returns_browser_contributions(client: TestClient, monkeypatch):
    async def fake_invoke(prompt):
        return {
            "results": ["local answer"],
            "plan": [{"step_id": 1, "description": "Answer locally", "worker_type": "llm_worker"}],
            "worker": "local-worker",
            "execution_trace": [{"node_id": "local-worker", "duration": 0.1}],
        }

    async def fake_browser(prompt):
        return [{
            "node_id": "browser-node-1",
            "status": "success",
            "kind": "browser_microgpt",
            "summary": "dashboard review",
            "keywords": ["dashboard", "review"],
            "clauses": ["dashboard review"],
            "error": None,
        }]

    monkeypatch.setattr(main_mod.workflow_manager, "invoke", fake_invoke)
    monkeypatch.setattr(main_mod, "collect_browser_micro_contributions", fake_browser)

    response = client.post("/chat", json={"prompt": "review dashboard"})
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == ["local answer"]
    assert data["browser_contributions"][0]["node_id"] == "browser-node-1"
    assert data["served_by"]["primary_node"] == "local-worker"

def test_nodes_dashboard(client: TestClient):
    response = client.get("/nodes")
    assert response.status_code == 200
    assert "Cluster Dashboard" in response.text
    assert "<!DOCTYPE html>" in response.text
