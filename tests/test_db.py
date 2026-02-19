"""
tests/test_db.py — Tests for the SQLite activity store (coordinator/db.py).

These tests use a temporary file-based DB to exercise the full aiosqlite stack.
"""

import asyncio
import os
import tempfile
import time
import pytest
import pytest_asyncio

# Override DB_PATH to a temp file before importing db
_tmp = tempfile.mktemp(suffix=".db")

import coordinator.db as db
db.DB_PATH = _tmp  # redirect all writes to the temp DB


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def fresh_db():
    """Create a fresh DB before each test, clean up after."""
    db.DB_PATH = tempfile.mktemp(suffix=".db")
    await db.init_db()
    yield
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_init_db_creates_tables():
    """init_db should create tasks, nodes, and events tables."""
    import aiosqlite
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cur:
            tables = {row[0] for row in await cur.fetchall()}
    assert {"tasks", "nodes", "events"} <= tables


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_task_insert():
    """upsert_task should insert a new row."""
    entry = {
        "id": "task-001",
        "prompt": "hello",
        "status": "Success",
        "duration": 1.5,
        "plan_steps": 2,
        "route_summary": "Node A",
        "timestamp": time.time(),
    }
    await db.upsert_task(entry)
    tasks = await db.get_tasks()
    assert len(tasks) == 1
    assert tasks[0]["id"] == "task-001"
    assert tasks[0]["status"] == "Success"


@pytest.mark.asyncio
async def test_upsert_task_update_on_conflict():
    """upsert_task with the same id should update status, not create a duplicate."""
    base = {"id": "task-002", "prompt": "test", "status": "Processing", "timestamp": time.time()}
    await db.upsert_task(base)
    updated = {**base, "status": "Success", "duration": 2.0}
    await db.upsert_task(updated)

    tasks = await db.get_tasks()
    assert len(tasks) == 1
    assert tasks[0]["status"] == "Success"


@pytest.mark.asyncio
async def test_get_tasks_ordered_newest_first():
    """get_tasks should return rows newest-first."""
    now = time.time()
    for i, ts in enumerate([now - 100, now - 50, now]):
        await db.upsert_task({"id": f"t{i}", "prompt": f"p{i}", "status": "Success", "timestamp": ts})

    tasks = await db.get_tasks()
    timestamps = [t["created_at"] for t in tasks]
    assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_node_insert_and_update():
    """upsert_node should insert, then update on repeated node_id."""
    hb = {
        "node_id": "worker-1",
        "capabilities": ["llm_inference"],
        "model": "llama3.2",
        "client_ip": "192.168.1.10",
        "current_task": "Idle",
        "status": "Online",
        "timestamp": time.time(),
    }
    await db.upsert_node(hb)
    nodes = await db.get_nodes()
    assert len(nodes) == 1
    assert nodes[0]["node_id"] == "worker-1"
    assert nodes[0]["status"] == "Online"

    # Mark offline
    await db.upsert_node({**hb, "status": "Offline"})
    nodes = await db.get_nodes()
    assert len(nodes) == 1
    assert nodes[0]["status"] == "Offline"


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_log_event_and_get_events():
    """log_event should append and get_events should return them filtered."""
    await db.log_event("plan_start", "coordinator", {"query": "hello"})
    await db.log_event("plan_done", "coordinator", {"steps": 2})
    await db.log_event("error", "worker-1", {"error": "timeout"})

    all_events = await db.get_events(limit=10)
    assert len(all_events) == 3

    errors = await db.get_events(limit=10, event_type="error")
    assert len(errors) == 1
    assert errors[0]["payload"]["error"] == "timeout"
