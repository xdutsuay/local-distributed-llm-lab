"""LLMLAB MCP server — thin httpx bridge to the coordinator REST API."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:

    class FastMCP:  # type: ignore[override]
        def __init__(self, name: str):
            self.name = name
            self._tools: list[Any] = []
            self._resources: list[tuple[str, Any]] = []

        def tool(self):
            def decorator(func):
                self._tools.append(func)
                return func

            return decorator

        def resource(self, uri: str):
            def decorator(func):
                self._resources.append((uri, func))
                return func

            return decorator

        async def list_tools(self):
            return [tool.__name__ for tool in self._tools]

        def run(self):
            raise RuntimeError("FastMCP is not installed in this environment")


REPO_ROOT = Path(__file__).resolve().parent
API_URL = os.getenv("LLM_LAB_API_URL", "http://localhost:8000")

EXPECTED_TOOL_NAMES = (
    "cluster_health",
    "list_nodes",
    "list_tasks",
    "list_events",
    "list_tools",
    "cache_stats",
    "submit_chat",
    "swap_node_model",
    "restart_node",
    "clear_cache",
    "run_regression_gate",
    "coordinator_docs",
)

RESOURCE_URIS = (
    "llmlab://nodes/active",
    "llmlab://tasks/recent",
    "llmlab://events/recent",
)

mcp = FastMCP("LLM Lab")


def format_api_error(response: httpx.Response) -> str:
    """Human-readable API error including response body when present."""
    try:
        body = response.json()
        if isinstance(body, dict):
            detail = body.get("detail", body.get("error", body))
        else:
            detail = body
    except Exception:
        detail = response.text or "(empty body)"
    return f"HTTP {response.status_code}: {detail}"


def format_nodes(data: dict[str, Any]) -> str:
    nodes = data.get("active_nodes", {})
    if not nodes:
        return "No active nodes found."
    lines = ["Active Nodes:"]
    for nid, info in nodes.items():
        meta = info.get("metadata", {})
        model = meta.get("model", "Unknown")
        ip = meta.get("client_ip", "Unknown")
        caps = ", ".join(info.get("capabilities", []))
        short_id = nid[:8] + "..." if len(nid) > 8 else nid
        lines.append(f"- {short_id} ({model}) @ {ip} | [{caps}]")
    return "\n".join(lines)


def format_tasks(tasks: list[dict[str, Any]], limit: int = 20) -> str:
    if not tasks:
        return "No tasks found."
    lines = [f"Recent tasks (showing up to {limit}):"]
    for task in tasks[:limit]:
        status = task.get("status", "unknown")
        prompt = task.get("prompt", "")[:60]
        tid = str(task.get("id", ""))[:8]
        worker = task.get("worker", task.get("final_node", ""))
        lines.append(f"- [{status}] {tid}... | {prompt!r} | worker={worker}")
    return "\n".join(lines)


def format_events(events: list[dict[str, Any]], limit: int = 50) -> str:
    if not events:
        return "No events found."
    lines = [f"Recent events (showing up to {limit}):"]
    for ev in events[:limit]:
        kind = ev.get("event_type", ev.get("type", "event"))
        source = ev.get("source", "unknown")
        ts = ev.get("timestamp", ev.get("created_at", ""))
        payload = ev.get("payload", ev.get("data", {}))
        summary = json.dumps(payload, default=str)[:80] if payload else ""
        lines.append(f"- {kind} @ {source} ({ts}) {summary}")
    return "\n".join(lines)


async def coordinator_request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
    client: httpx.AsyncClient | None = None,
) -> httpx.Response:
    """Issue a request to the coordinator; returns the raw httpx response."""
    url = f"{API_URL}{path}"
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient()
    try:
        response = await client.request(
            method,
            url,
            json=json_body,
            params=params,
            timeout=timeout,
        )
        return response
    finally:
        if owns_client:
            await client.aclose()


# --- fetch_* helpers (testable) ---


async def fetch_cluster_health(
    client: httpx.AsyncClient | None = None,
) -> str:
    resp = await coordinator_request("GET", "/health", client=client)
    if resp.is_error:
        return format_api_error(resp)
    data = resp.json()
    status = data.get("status", "unknown")
    ray_status = data.get("ray_status")
    return f"Cluster status: {status}\nRay initialized: {ray_status}"


async def fetch_list_nodes(client: httpx.AsyncClient | None = None) -> str:
    resp = await coordinator_request("GET", "/api/nodes", client=client)
    if resp.is_error:
        return format_api_error(resp)
    return format_nodes(resp.json())


async def fetch_list_tasks(
    limit: int = 20,
    client: httpx.AsyncClient | None = None,
) -> str:
    resp = await coordinator_request("GET", "/api/tasks", client=client)
    if resp.is_error:
        return format_api_error(resp)
    tasks = resp.json().get("tasks", [])
    return format_tasks(tasks, limit=limit)


async def fetch_list_events(
    limit: int = 50,
    client: httpx.AsyncClient | None = None,
) -> str:
    resp = await coordinator_request(
        "GET",
        "/api/events",
        params={"limit": limit},
        client=client,
    )
    if resp.is_error:
        return format_api_error(resp)
    events = resp.json().get("events", [])
    return format_events(events, limit=limit)


async def fetch_list_tools(client: httpx.AsyncClient | None = None) -> str:
    resp = await coordinator_request("GET", "/api/tools", client=client)
    if resp.is_error:
        return format_api_error(resp)
    data = resp.json()
    tools = data.get("tools", [])
    stats = data.get("stats", {})
    lines = ["Registered tools:"]
    for name in tools:
        lines.append(f"- {name}")
    if stats:
        lines.append(f"Stats: {json.dumps(stats, default=str)}")
    return "\n".join(lines) if tools else "No tools registered."


async def fetch_cache_stats(client: httpx.AsyncClient | None = None) -> str:
    resp = await coordinator_request("GET", "/api/cache/stats", client=client)
    if resp.is_error:
        return format_api_error(resp)
    return f"Cache stats:\n{json.dumps(resp.json(), indent=2, default=str)}"


async def fetch_submit_chat(
    prompt: str,
    client_id: str = "unknown",
    model: str = "llama3.2",
    client: httpx.AsyncClient | None = None,
) -> str:
    resp = await coordinator_request(
        "POST",
        "/chat",
        json_body={"prompt": prompt, "client_id": client_id, "model": model},
        timeout=120.0,
        client=client,
    )
    if resp.is_error:
        return format_api_error(resp)
    data = resp.json()
    response_text = data.get("response", data.get("results", ""))
    plan = data.get("plan", [])
    worker = data.get("worker", "unknown")
    served = data.get("served_by", {})
    lines = [
        f"Response: {response_text}",
        f"Plan steps: {len(plan)}",
        f"Worker: {worker}",
    ]
    if served:
        lines.append(f"Served by: {json.dumps(served, default=str)}")
    if data.get("error"):
        lines.append(f"Error: {data['error']}")
    return "\n".join(lines)


async def fetch_swap_node_model(
    node_id: str,
    model: str,
    client: httpx.AsyncClient | None = None,
) -> str:
    resp = await coordinator_request(
        "POST",
        f"/api/nodes/{node_id}/model",
        json_body={"model": model},
        client=client,
    )
    if resp.is_error:
        return format_api_error(resp)
    data = resp.json()
    return (
        f"Model swap OK for node {node_id}\n"
        f"Model: {data.get('model', model)}\n"
        f"Verification: {data.get('verification', 'n/a')}"
    )


async def fetch_restart_node(
    node_id: str,
    client: httpx.AsyncClient | None = None,
) -> str:
    resp = await coordinator_request(
        "POST",
        f"/api/nodes/{node_id}/restart",
        client=client,
    )
    if resp.is_error:
        return format_api_error(resp)
    data = resp.json()
    return f"Restart: {data.get('status', 'ok')} — {data.get('message', '')}"


async def fetch_clear_cache(client: httpx.AsyncClient | None = None) -> str:
    resp = await coordinator_request("POST", "/api/cache/clear", client=client)
    if resp.is_error:
        return format_api_error(resp)
    return f"Cache cleared: {resp.json().get('status', 'ok')}"


async def fetch_run_regression_gate() -> str:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_regression_gate.py",
        "-m",
        "not live",
        "-q",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=REPO_ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode() + stderr.decode()
    if proc.returncode == 0:
        return f"Regression gate passed.\n{out}".strip()
    return f"Regression gate failed (exit {proc.returncode}).\n{out}".strip()


def fetch_coordinator_docs() -> str:
    return (
        "LLMLAB coordinator documentation pointers:\n"
        f"- NEXT_STEPS.md — {REPO_ROOT / 'NEXT_STEPS.md'}\n"
        f"- docs/COMPONENTS.md — {REPO_ROOT / 'docs' / 'COMPONENTS.md'}\n"
        "Use cluster_health → list_events → submit_chat for cold-start debugging."
    )


# --- MCP tools ---


@mcp.tool()
async def cluster_health() -> str:
    """Read-only: coordinator /health including Ray initialization (ray_status)."""
    return await fetch_cluster_health()


@mcp.tool()
async def list_nodes() -> str:
    """Read-only: list active cluster nodes and capabilities."""
    return await fetch_list_nodes()


@mcp.tool()
async def list_tasks(limit: int = 20) -> str:
    """Read-only: recent task history (client-side limit, default 20)."""
    return await fetch_list_tasks(limit=limit)


@mcp.tool()
async def list_events(limit: int = 50) -> str:
    """Read-only: operational event log for debugging stuck requests."""
    return await fetch_list_events(limit=limit)


@mcp.tool()
async def list_tools() -> str:
    """Read-only: planner/tool registry entries exposed by the coordinator."""
    return await fetch_list_tools()


@mcp.tool()
async def cache_stats() -> str:
    """Read-only: semantic cache hit/miss statistics."""
    return await fetch_cache_stats()


@mcp.tool()
async def submit_chat(
    prompt: str,
    client_id: str = "unknown",
    model: str = "llama3.2",
) -> str:
    """
    Mutating: submit a chat prompt to the distributed LangGraph workflow (POST /chat).
    Runs inference on the cluster; may take up to 120s. Optional client_id and model.
    """
    return await fetch_submit_chat(prompt, client_id=client_id, model=model)


@mcp.tool()
async def swap_node_model(node_id: str, model: str) -> str:
    """
    Mutating: change the active model on a Ray worker or coordinator node (POST /api/nodes/{id}/model).
    Updates the node registry; verify with list_events and a follow-up submit_chat.
    """
    return await fetch_swap_node_model(node_id, model)


@mcp.tool()
async def restart_node(node_id: str) -> str:
    """
    Mutating: kill and rely on Ray to restart a worker actor (POST /api/nodes/{id}/restart).
    Cannot restart the coordinator node itself.
    """
    return await fetch_restart_node(node_id)


@mcp.tool()
async def clear_cache() -> str:
    """
    Mutating: wipe all semantic cache entries (POST /api/cache/clear).
    Use before reproducing cache-sensitive bugs.
    """
    return await fetch_clear_cache()


@mcp.tool()
async def run_regression_gate() -> str:
    """
    Dev workflow: run mocked regression gate (pytest tests/test_regression_gate.py -m "not live" -q).
    Does not require a live coordinator or LM Studio.
    """
    return await fetch_run_regression_gate()


@mcp.tool()
async def coordinator_docs() -> str:
    """Read-only: static pointers to NEXT_STEPS.md and docs/COMPONENTS.md."""
    return fetch_coordinator_docs()


# --- MCP resources ---


@mcp.resource("llmlab://nodes/active")
async def resource_nodes_active() -> str:
    return await fetch_list_nodes()


@mcp.resource("llmlab://tasks/recent")
async def resource_tasks_recent() -> str:
    return await fetch_list_tasks(limit=20)


@mcp.resource("llmlab://events/recent")
async def resource_events_recent() -> str:
    return await fetch_list_events(limit=50)


if __name__ == "__main__":
    mcp.run()
