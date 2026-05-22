"""
tests/test_adaptive_pool.py
Tests for AdaptiveWorkerPool (@ray_required dispatch logic).

Covers:
 - single-node → local path used, no Ray
 - multi-node  → Ray path used
 - @ray_required routing
 - LocalLLMWorker Ollama path (mocked)
 - active_node_count in NodeRegistry
"""
import asyncio
import time
import types
import pytest

from coordinator.worker_pool import AdaptiveWorkerPool, LocalLLMWorker, ray_required


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class _FakeRegistry:
    """Stub NodeRegistry that returns a configurable node count."""
    def __init__(self, count: int):
        self._count = count

    def active_node_count(self) -> int:
        return self._count

    def active_llm_node_count(self) -> int:
        return self._count


# A simple async echo that pretends to be LocalLLMWorker.generate
async def _echo_generate(prompt: str):
    return {"content": f"echo:{prompt}", "node_id": "local-worker",
            "model": "mock", "timestamp": time.time(), "cached": False}


# ---------------------------------------------------------------------------
# AdaptiveWorkerPool routing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_single_node_uses_local_path(monkeypatch):
    """With 1 node, execute() must call the local worker, not Ray."""
    pool = AdaptiveWorkerPool(num_workers=0)
    pool.set_registry(_FakeRegistry(1))

    # Patch local worker's generate to track calls
    calls = []
    async def _fake_generate(prompt):
        calls.append(prompt)
        return {"content": "local-result", "node_id": "local-worker",
                "model": "mock", "timestamp": time.time(), "cached": False}

    monkeypatch.setattr(pool._local_worker, "generate", _fake_generate)

    result = await pool.execute("hello")
    assert result["content"] == "local-result"
    assert result["node_id"] == "local-worker"
    assert len(calls) == 1
    assert "hello" in calls[0]
    assert "<BOS>" in calls[0]


@pytest.mark.asyncio
async def test_single_node_is_local_mode():
    pool = AdaptiveWorkerPool(num_workers=0)
    pool.set_registry(_FakeRegistry(1))
    assert pool.is_local_mode() is True


@pytest.mark.asyncio
async def test_multi_node_is_not_local_mode():
    pool = AdaptiveWorkerPool(num_workers=0)
    pool.set_registry(_FakeRegistry(2))
    assert pool.is_local_mode() is False


@pytest.mark.asyncio
async def test_no_registry_defaults_to_local():
    """Without a registry, pool should behave as local (safe default)."""
    pool = AdaptiveWorkerPool(num_workers=0)
    assert pool.is_local_mode() is True


# ---------------------------------------------------------------------------
# @ray_required decorator standalone test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ray_required_routes_to_local_on_single_node():
    """ray_required should call _local_execute when node count <= 1."""
    class FakePool:
        _registry = _FakeRegistry(1)
        local_called = False
        ray_called = False

        async def _local_execute(self, prompt): # noqa: D102
            self.local_called = True
            return {"content": "local", "node_id": "local-worker",
                    "model": "mock", "timestamp": 0, "cached": False}

        @ray_required
        async def execute(self, prompt):      # noqa: D102
            self.ray_called = True
            return {"content": "ray"}

    fp = FakePool()
    result = await fp.execute("test")
    assert result["content"] == "local"
    assert fp.local_called is True
    assert fp.ray_called is False


@pytest.mark.asyncio
async def test_ray_required_routes_to_ray_on_multi_node(monkeypatch):
    """ray_required should call the decorated method when node count > 1."""
    class FakePool:
        _registry = _FakeRegistry(2)
        ray_called = False

        async def _local_execute(self, prompt):
            return {"content": "local"}

        @ray_required
        async def execute(self, prompt):
            self.ray_called = True
            return {"content": "ray", "node_id": "worker", "model": "m",
                    "timestamp": 0, "cached": False}

    fp = FakePool()
    result = await fp.execute("test")
    assert result["content"] == "ray"
    assert fp.ray_called is True


# ---------------------------------------------------------------------------
# NodeRegistry.active_node_count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_active_node_count_counts_live_nodes():
    from coordinator.messaging import MessageBus
    from coordinator.registry import NodeRegistry

    # Stub message bus (no Ray needed)
    class FakeBus:
        async def subscribe(self, *a, **kw): pass
        async def publish(self, *a, **kw): pass

    reg = NodeRegistry(FakeBus())

    now = time.time()
    reg.nodes = {
        "node-A": {"last_seen": now - 1,  "capabilities": [], "metadata": {}},
        "node-B": {"last_seen": now - 8,  "capabilities": [], "metadata": {}},
        "node-C": {"last_seen": now - 20, "capabilities": [], "metadata": {}},  # TTL=15 → offline
    }

    count = reg.active_node_count()
    assert count == 2  # A and B are alive, C is expired


@pytest.mark.asyncio
async def test_active_llm_node_count_ignores_browser_only_nodes():
    from coordinator.registry import NodeRegistry

    class FakeBus:
        async def subscribe(self, *a, **kw): pass
        async def publish(self, *a, **kw): pass

    reg = NodeRegistry(FakeBus())
    now = time.time()
    reg.nodes = {
        "coordinator": {
            "last_seen": now - 1,
            "capabilities": ["llm_inference", "coordinator"],
            "metadata": {},
        },
        "browser-node": {
            "last_seen": now - 1,
            "capabilities": ["javascript_execution", "web_worker"],
            "metadata": {},
        },
    }

    assert reg.active_node_count() == 2
    assert reg.active_llm_node_count() == 1


def test_force_local_worker_env(monkeypatch):
    """FORCE_LOCAL_WORKER=1 forces single-node local path for benchmarks."""
    monkeypatch.setenv("FORCE_LOCAL_WORKER", "1")
    from coordinator.worker_pool import AdaptiveWorkerPool, _registry_llm_count

    pool = AdaptiveWorkerPool()
    assert _registry_llm_count(pool) == 1
    assert pool._active_llm_node_count() == 1
