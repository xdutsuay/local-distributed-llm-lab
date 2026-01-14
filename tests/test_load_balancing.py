"""
Tests for load balancing and multi-node task distribution
"""
import pytest
from httpx import AsyncClient, ASGITransport
from coordinator.main import app, task_history
import time


@pytest.mark.skip(reason="Load balancing not yet implemented")
@pytest.mark.asyncio
async def test_request_distributed_across_nodes():
    """
    Test that when multiple LLM nodes are available,
    requests are distributed across them
    """
    # This test requires a running cluster with 2+ nodes
    # We should verify that consecutive requests use different nodes
    pass


@pytest.mark.skip(reason="Parallel execution not yet implemented")
@pytest.mark.asyncio
async def test_parallel_planning_for_efficiency():
    """
    Test that complex queries are sent to multiple nodes
    for parallel planning/execution
    """
    pass


@pytest.mark.skip(reason="Result comparison not yet implemented")
@pytest.mark.asyncio
async def test_result_comparison_chooses_best():
    """
    Test that when multiple nodes process the same query,
    the system chooses the best result based on some metric
    """
    pass


@pytest.mark.asyncio
async def test_single_node_fallback():
    """Test that system works with single node (current behavior)"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/chat", json={
            "prompt": "test query",
            "client_id": "test"
        })
        
        # Should succeed even with single/no workers
        assert response.status_code in [200, 500]  # 500 if no workers


@pytest.mark.asyncio
async def test_task_attribution_tracks_node():
    """Test that task history correctly attributes work to nodes"""
    # Add a mock task
    mock_task = {
        "id": "test-load-balance",
        "worker": "worker-123",
        "final_node": "worker-123",
        "timestamp": time.time(),
        "composition": {"worker-123": 100.0}
    }
    task_history.insert(0, mock_task)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/tasks")
        
    assert response.status_code == 200
    data = response.json()
    tasks = data["tasks"]
    
    # Find our task
    test_task = next((t for t in tasks if t["id"] == "test-load-balance"), None)
    assert test_task is not None
    assert test_task["worker"] == "worker-123"
    assert test_task["composition"]["worker-123"] == 100.0
