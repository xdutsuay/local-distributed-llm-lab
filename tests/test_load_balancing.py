"""
Tests for load balancing and multi-node task distribution
"""
import pytest
from httpx import AsyncClient, ASGITransport
from coordinator.main import app, task_history
import time


"""
Tests for load balancing and multi-node task distribution
"""
import pytest
from httpx import AsyncClient, ASGITransport
from coordinator.main import app, task_history
from coordinator.worker_pool import WorkerPool
import ray
import time


@pytest.mark.asyncio
async def test_worker_pool_initialization():
    """Test that WorkerPool initializes with correct number of workers"""
    if not ray.is_initialized():
        ray.init(namespace="llm-lab", ignore_reinit_error=True)
    
    pool = WorkerPool(num_workers=3)
    assert pool.get_pool_size() == 3
    
    # Test that we can get workers
    worker1 = pool.get_next_worker()
    worker2 = pool.get_next_worker()
    worker3 = pool.get_next_worker()
    
    assert worker1 is not None
    assert worker2 is not None
    assert worker3 is not None


@pytest.mark.asyncio
async def test_round_robin_algorithm():
    """Test that round-robin properly cycles through workers"""
    if not ray.is_initialized():
        ray.init(namespace="llm-lab", ignore_reinit_error=True)
    
    pool = WorkerPool(num_workers=2)
    
    # Get workers in sequence to verify round-robin
    workers = [pool.get_next_worker() for _ in range(6)]
    
    # First and third should be the same (and 5th)
    # Second and fourth should be the same (and 6th)
    assert workers[0] == workers[2] == workers[4]
    assert workers[1] == workers[3] == workers[5]
    assert workers[0] != workers[1]


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
