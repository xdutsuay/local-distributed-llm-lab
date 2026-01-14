"""
Tests for node heartbeat mechanism and lifecycle
"""
import pytest
import asyncio
import time
from coordinator.registry import NodeRegistry
from coordinator.messaging import RayMessageBus


@pytest.mark.asyncio
async def test_heartbeat_keeps_node_active():
    """Test that receiving heartbeats keeps node in active state"""
    bus = RayMessageBus()
    registry = NodeRegistry(bus)
    await registry.start()
    
    # Simulate heartbeat
    test_node_id = "test-node-123"
    heartbeat_msg = {
        "node_id": test_node_id,
        "capabilities": ["llm_inference"],
        "model": "llama3.2",
        "timestamp": time.time(),
        "data_stats": {"sent_bytes": 1024}
    }
    
    # Send heartbeat
    await registry.handle_heartbeat(heartbeat_msg)
    
    # Node should be active
    active_nodes = registry.get_active_nodes()
    assert test_node_id in active_nodes
    assert active_nodes[test_node_id]["metadata"]["model"] == "llama3.2"


@pytest.mark.asyncio
async def test_node_expires_without_heartbeat():
    """Test that nodes expire after TTL without heartbeats"""
    bus = RayMessageBus()
    registry = NodeRegistry(bus)
    await registry.start()
    
    test_node_id = "test-node-expire"
    # Send old heartbeat
    old_heartbeat = {
        "node_id": test_node_id,
        "capabilities": ["llm_inference"],
        "model": "llama3.2",
        "timestamp": time.time(),
        "data_stats": {"sent_bytes": 0}
    }
    
    await registry.handle_heartbeat(old_heartbeat)
    
    # Manually update the timestamp to be old
    if test_node_id in registry.nodes:
        registry.nodes[test_node_id]["last_seen"] = time.time() - 20  # 20 seconds ago
    
    # Now get_active_nodes should filter it out
    active_nodes = registry.get_active_nodes()
    assert test_node_id not in active_nodes


@pytest.mark.asyncio
async def test_heartbeat_updates_metadata():
    """Test that heartbeats update node metadata"""
    bus = RayMessageBus()
    registry = NodeRegistry(bus)
    await registry.start()
    
    test_node_id = "test-node-update"
    
    # First heartbeat
    await registry.handle_heartbeat({
        "node_id": test_node_id,
        "capabilities": ["llm_inference"],
        "model": "llama3.2",
        "timestamp": time.time(),
        "data_stats": {"sent_bytes": 1024},
        "current_task": "Idle"
    })
    
    # Second heartbeat with updated data
    await registry.handle_heartbeat({
        "node_id": test_node_id,
        "capabilities": ["llm_inference"],
        "model": "llama3.2",
        "timestamp": time.time(),
        "data_stats": {"sent_bytes": 2048},
        "current_task": "Processing query"
    })
    
    active_nodes = registry.get_active_nodes()
    assert active_nodes[test_node_id]["metadata"]["data_stats"]["sent_bytes"] == 2048
    assert active_nodes[test_node_id]["metadata"]["current_task"] == "Processing query"
