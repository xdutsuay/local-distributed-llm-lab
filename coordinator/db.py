"""
coordinator/db.py — SQLite activity store for LLM Lab.

Tables:
  tasks  — every POST /chat attempt (persisted across restarts)
  nodes  — latest heartbeat per node (upserted, not appended)
  events — generic operational log for debugging stuck states

Uses aiosqlite for non-blocking async I/O.
DB file: data/llmlab.db
"""

import json
import time
import uuid
import aiosqlite
from typing import Any, Dict, List, Optional

DB_PATH = "data/llmlab.db"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TASKS = """
CREATE TABLE IF NOT EXISTS tasks (
    id             TEXT    PRIMARY KEY,
    prompt         TEXT,
    status         TEXT,
    worker         TEXT,
    plan_steps     INTEGER DEFAULT 0,
    duration_ms    REAL    DEFAULT 0.0,
    route_summary  TEXT,
    error          TEXT,
    created_at     REAL,
    updated_at     REAL
)
"""

_CREATE_NODES = """
CREATE TABLE IF NOT EXISTS nodes (
    node_id       TEXT PRIMARY KEY,
    capabilities  TEXT,        -- JSON array
    model         TEXT,
    client_ip     TEXT,
    current_task  TEXT,
    api_base      TEXT,
    data_stats    TEXT,        -- JSON object
    last_seen     REAL,
    status        TEXT DEFAULT 'Online'
)
"""

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT,   -- plan_start | plan_done | execute | error | prewarm | heartbeat_miss
    node_id     TEXT,
    payload     TEXT,   -- JSON blob
    ts          REAL
)
"""

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create tables if they don't exist (idempotent). Call once on startup."""
    import os
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TASKS)
        await db.execute(_CREATE_NODES)
        await db.execute(_CREATE_EVENTS)
        await db.commit()
    print(f"✅ SQLite DB ready at {DB_PATH}")

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

async def upsert_task(entry: Dict[str, Any]) -> None:
    """Insert or replace a task row. Uses task['id'] as PK."""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO tasks
                (id, prompt, status, worker, plan_steps, duration_ms,
                 route_summary, error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status        = excluded.status,
                worker        = excluded.worker,
                plan_steps    = excluded.plan_steps,
                duration_ms   = excluded.duration_ms,
                route_summary = excluded.route_summary,
                error         = excluded.error,
                updated_at    = excluded.updated_at
            """,
            (
                entry.get("id", str(uuid.uuid4())),
                entry.get("prompt", ""),
                entry.get("status", "unknown"),
                entry.get("worker", ""),
                entry.get("plan_steps", 0),
                entry.get("duration", 0.0) * 1000,   # store as ms
                entry.get("route_summary", ""),
                entry.get("error", ""),
                entry.get("timestamp", now),
                now,
            ),
        )
        await db.commit()

async def get_tasks(limit: int = 100) -> List[Dict[str, Any]]:
    """Return tasks ordered newest-first."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]

# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def upsert_node(hb: Dict[str, Any]) -> None:
    """Upsert a node row from heartbeat data."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO nodes
                (node_id, capabilities, model, client_ip, current_task,
                 api_base, data_stats, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                capabilities = excluded.capabilities,
                model        = excluded.model,
                client_ip    = excluded.client_ip,
                current_task = excluded.current_task,
                api_base     = excluded.api_base,
                data_stats   = excluded.data_stats,
                last_seen    = excluded.last_seen,
                status       = excluded.status
            """,
            (
                hb.get("node_id", "unknown"),
                json.dumps(hb.get("capabilities", [])),
                hb.get("model", ""),
                hb.get("client_ip", ""),
                hb.get("current_task", ""),
                hb.get("api_base", ""),
                json.dumps(hb.get("data_stats", {})),
                hb.get("timestamp", time.time()),
                hb.get("status", "Online"),
            ),
        )
        await db.commit()

async def get_nodes() -> List[Dict[str, Any]]:
    """Return all nodes (including recently offline ones)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM nodes ORDER BY last_seen DESC"
        ) as cursor:
            rows = await cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        # Deserialise JSON columns
        d["capabilities"] = json.loads(d.get("capabilities") or "[]")
        d["data_stats"] = json.loads(d.get("data_stats") or "{}")
        result.append(d)
    return result

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

async def log_event(
    event_type: str,
    node_id: str = "coordinator",
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a row to the events table."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO events (event_type, node_id, payload, ts) VALUES (?, ?, ?, ?)",
            (event_type, node_id, json.dumps(payload or {}), time.time()),
        )
        await db.commit()

async def get_events(
    limit: int = 200,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return events ordered newest-first, optionally filtered by type."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if event_type:
            async with db.execute(
                "SELECT * FROM events WHERE event_type=? ORDER BY ts DESC LIMIT ?",
                (event_type, limit),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d.get("payload") or "{}")
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Sync helpers (safe to call from non-async contexts, e.g. Ray actors)
# ---------------------------------------------------------------------------

def log_event_sync(
    event_type: str,
    node_id: str = "coordinator",
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Synchronous version of log_event — uses stdlib sqlite3, safe from any thread."""
    import sqlite3 as _sqlite3
    import os as _os
    _os.makedirs("data", exist_ok=True)
    conn = _sqlite3.connect(DB_PATH, timeout=5)
    try:
        conn.execute(
            "INSERT INTO events (event_type, node_id, payload, ts) VALUES (?, ?, ?, ?)",
            (event_type, node_id, json.dumps(payload or {}), time.time()),
        )
        conn.commit()
    except Exception:
        pass  # Never crash caller for a telemetry write
    finally:
        conn.close()

