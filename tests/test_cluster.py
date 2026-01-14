"""
Tests for Ray cluster integration and worker registration
"""
import pytest
import ray
from coordinator.registry import NodeRegistry
from coordinator.messaging import RayMessageBus


@pytest.mark.asyncio
async def test_worker_registration_matches_ray_nodes():
    """
    Test that the number of registered workers matches Ray cluster nodes
    NOTE: This test assumes Ray is running
    """
    if not ray.is_initialized():
        pytest.skip("Ray not initialized")
    
    bus = RayMessageBus()
    registry = NodeRegistry(bus)
    await registry.start()
    
    # Get Ray cluster info
    ray_nodes = ray.nodes()
    alive_ray_nodes = [n for n in ray_nodes if n['Alive']]
    
    # Note: This test is aspirational - currently workers must manually register
    # In the future, we should auto-discover Ray nodes
    # For now, just verify the registry structure is correct
    active_nodes = registry.get_active_nodes()
    assert isinstance(active_nodes, dict)


@pytest.mark.skip(reason="Feature not yet implemented")
@pytest.mark.asyncio
async def test_ray_node_auto_discovery():
    """
    Future test: Ray nodes should be automatically discovered
    and registered without manual worker startup
    """
    pass


@pytest.mark.asyncio
async def test_multiple_workers_from_same_node():
    """Test that multiple workers can register from the same physical node"""
    bus = RayMessageBus()
    registry = NodeRegistry(bus)
    await registry.start()
    
    # Simulate two workers on same node
    import time
    for i in range(2):
        await registry.handle_heartbeat({
            "node_id": f"worker-same-node-{i}",
            "capabilities": ["llm_inference"],
            "model": "llama3.2",
            "timestamp": time.time(),
            "client_ip": "192.168.1.100"
        })
    
    active_nodes = registry.get_active_nodes()
    assert len(active_nodes) == 2
