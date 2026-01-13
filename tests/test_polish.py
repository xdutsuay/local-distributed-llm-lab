import pytest
from httpx import AsyncClient, ASGITransport
from coordinator.main import app
import ray

@pytest.mark.asyncio
async def test_dashboard_api_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/nodes")
    assert response.status_code == 200
    data = response.json()
    assert "active_nodes" in data
    assert isinstance(data["active_nodes"], dict)

@pytest.mark.asyncio
async def test_task_attribution_fields():
    """Verify that task history has fields for attribution (worker, final_node)."""
    # Simulate a task entry manually since we don't want to run a full Ray task here
    from coordinator.main import task_history
    import time
    
    mock_task = {
        "id": "test-1",
        "worker": "test-worker-node",
        "final_node": "executor-1",
        "timestamp": time.time()
    }
    task_history.append(mock_task)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tasks")
        
    assert response.status_code == 200
    data = response.json()
    tasks = data["tasks"]
    assert len(tasks) > 0
    latest = tasks[-1]
    assert "worker" in latest
    assert "final_node" in latest
