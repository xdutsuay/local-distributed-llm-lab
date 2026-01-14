"""
Tests for data persistence across nodes and sessions
"""
import pytest
from httpx import AsyncClient, ASGITransport
from coordinator.main import app, task_history
import json
import os


@pytest.mark.asyncio
async def test_task_history_persistence():
    """Test that task history is accessible via API"""
    # Add a test task
    import time
    test_task = {
        "id": "persist-test-1",
        "prompt": "test persistence",
        "status": "Success",
        "timestamp": time.time(),
        "worker": "test-worker"
    }
    task_history.insert(0, test_task)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tasks")
        
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    
    # Find our task
    found = any(t["id"] == "persist-test-1" for t in data["tasks"])
    assert found


@pytest.mark.skip(reason="File persistence not yet implemented")
@pytest.mark.asyncio
async def test_history_persists_to_disk():
    """
    Test that task history is saved to disk
    """
    # Future: Verify server_data/history.json is written
    pass


@pytest.mark.skip(reason="Cross-node persistence not yet implemented")
@pytest.mark.asyncio
async def test_persistence_across_all_nodes():
    """
    Test that all connected nodes can access persisted state
    """
    # Future: Node 1 writes -> Node 2 can read
    pass


@pytest.mark.skip(reason="Distributed state not yet implemented")
@pytest.mark.asyncio
async def test_shared_state_consistency():
    """
    Test that shared state (memo, history) is consistent across nodes
    """
    pass


@pytest.mark.asyncio
async def test_memo_storage():
    """Test that memo storage works (in-memory for now)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Post a memo
        response = await ac.post("/api/memo", json={"text": "test memo"})
        assert response.status_code == 200
        
        # Retrieve memos
        response = await ac.get("/api/memo")
        assert response.status_code == 200
        data = response.json()
        assert "memos" in data
        assert len(data["memos"]) > 0


@pytest.mark.skip(reason="Node state persistence not yet implemented")
@pytest.mark.asyncio
async def test_node_metadata_persists():
    """
    Test that node metadata (capabilities, model, stats) persists
    across coordinator restarts
    """
    pass


@pytest.mark.skip(reason="Recovery not yet implemented")
@pytest.mark.asyncio
async def test_state_recovery_after_coordinator_restart():
    """
    Test that system state is recovered after coordinator restarts
    """
    pass
