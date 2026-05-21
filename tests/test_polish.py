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
    from coordinator import db
    import time

    mock_task = {
        "id": "polish-attribution-test-1",
        "prompt": "attribution probe",
        "status": "Success",
        "worker": "test-worker-node",
        "final_node": "executor-1",
        "timestamp": time.time(),
        "composition": {"executor-1": 1.0},
        "route_details": [{"node_id": "executor-1", "duration": 0.1}],
    }
    await db.upsert_task(mock_task)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tasks")

    assert response.status_code == 200
    data = response.json()
    tasks = data["tasks"]
    match = next((t for t in tasks if t["id"] == "polish-attribution-test-1"), None)
    assert match is not None
    assert match.get("worker") == "test-worker-node"
    assert match.get("final_node") == "executor-1"
    if "execution_trace" in match:
        assert isinstance(match["execution_trace"], list)
    if "composition" in match:
        assert isinstance(match["composition"], dict)
