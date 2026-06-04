"""Unit tests for mcp_server fetch_* helpers (mocked httpx)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from mcp_server import (
    API_URL,
    EXPECTED_TOOL_NAMES,
    fetch_cache_stats,
    fetch_clear_cache,
    fetch_cluster_health,
    fetch_list_events,
    fetch_list_nodes,
    fetch_list_tasks,
    fetch_list_tools,
    fetch_restart_node,
    fetch_submit_chat,
    fetch_swap_node_model,
    format_api_error,
    format_events,
    format_nodes,
    format_tasks,
)


def _mock_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
    text: str = "",
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_error = status_code >= 400
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("no json")
    return resp


def test_expected_tools_registered():
    base_plan_tools = {
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
    }
    assert base_plan_tools.issubset(set(EXPECTED_TOOL_NAMES))


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.mark.asyncio
async def test_format_api_error_json():
    resp = _mock_response(503, {"detail": "cluster busy"})
    assert "503" in format_api_error(resp)
    assert "cluster busy" in format_api_error(resp)


def test_format_nodes_empty():
    assert "No active nodes" in format_nodes({"active_nodes": {}})


def test_format_nodes_with_entry():
    data = {
        "active_nodes": {
            "node-abc-12345": {
                "metadata": {"model": "llama3.2", "client_ip": "127.0.0.1"},
                "capabilities": ["llm_worker"],
            }
        }
    }
    out = format_nodes(data)
    assert "llama3.2" in out
    assert "127.0.0.1" in out


def test_format_tasks_and_events():
    tasks = [{"id": "t1", "status": "Success", "prompt": "hi", "worker": "w1"}]
    assert "Success" in format_tasks(tasks, limit=5)
    events = [{"event_type": "prewarm", "source": "coordinator", "timestamp": 1, "payload": {}}]
    assert "prewarm" in format_events(events, limit=5)


@pytest.mark.asyncio
async def test_fetch_cluster_health_ok(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(200, {"status": "ok", "ray_status": True})
    )
    result = await fetch_cluster_health(client=mock_client)
    assert "ok" in result
    assert "True" in result
    mock_client.request.assert_awaited_once()
    call = mock_client.request.await_args
    assert call.args[1] == f"{API_URL}/health"


@pytest.mark.asyncio
async def test_fetch_cluster_health_error(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(500, {"detail": "down"})
    )
    result = await fetch_cluster_health(client=mock_client)
    assert "500" in result


@pytest.mark.asyncio
async def test_fetch_list_nodes(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(200, {"active_nodes": {}})
    )
    result = await fetch_list_nodes(client=mock_client)
    assert "No active nodes" in result


@pytest.mark.asyncio
async def test_fetch_list_tasks_respects_limit(mock_client):
    tasks = [{"id": f"t{i}", "status": "ok", "prompt": "p"} for i in range(5)]
    mock_client.request = AsyncMock(return_value=_mock_response(200, {"tasks": tasks}))
    result = await fetch_list_tasks(limit=2, client=mock_client)
    assert "up to 2" in result


@pytest.mark.asyncio
async def test_fetch_list_events_passes_limit_param(mock_client):
    mock_client.request = AsyncMock(return_value=_mock_response(200, {"events": []}))
    await fetch_list_events(limit=25, client=mock_client)
    kwargs = mock_client.request.await_args.kwargs
    assert kwargs["params"] == {"limit": 25}


@pytest.mark.asyncio
async def test_fetch_list_events_event_type_filter(mock_client):
    mock_client.request = AsyncMock(return_value=_mock_response(200, {"events": []}))
    await fetch_list_events(limit=10, event_type="error", client=mock_client)
    assert mock_client.request.await_args.kwargs["params"] == {
        "limit": 10,
        "event_type": "error",
    }


@pytest.mark.asyncio
async def test_fetch_list_tools(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(200, {"tools": ["search"], "stats": {"calls": 1}})
    )
    result = await fetch_list_tools(client=mock_client)
    assert "search" in result


@pytest.mark.asyncio
async def test_fetch_cache_stats(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(200, {"hits": 3, "misses": 1})
    )
    result = await fetch_cache_stats(client=mock_client)
    assert "hits" in result


@pytest.mark.asyncio
async def test_fetch_submit_chat_success(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(
            200,
            {
                "response": ["hello"],
                "plan": [{"step_id": 1}],
                "worker": "distributed-graph",
                "served_by": {"primary_node": "n1"},
            },
        )
    )
    result = await fetch_submit_chat("test prompt", client_id="mcp", model="qwen", client=mock_client)
    assert "hello" in result
    assert "distributed-graph" in result
    body = mock_client.request.await_args.kwargs["json"]
    assert body == {"prompt": "test prompt", "client_id": "mcp", "model": "qwen"}


@pytest.mark.asyncio
async def test_fetch_submit_chat_error(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(503, {"detail": "workflow failed"})
    )
    result = await fetch_submit_chat("x", client=mock_client)
    assert "503" in result


@pytest.mark.asyncio
async def test_fetch_submit_chat_503_error_field(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(503, {"error": "no workers available"})
    )
    result = await fetch_submit_chat("x", client=mock_client)
    assert "503" in result
    assert "no workers" in result


@pytest.mark.asyncio
async def test_fetch_swap_node_model(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(
            200,
            {"status": "ok", "model": "mistral", "verification": "loaded"},
        )
    )
    result = await fetch_swap_node_model("node-1", "mistral", client=mock_client)
    assert "mistral" in result
    assert mock_client.request.await_args.kwargs["json"] == {"model": "mistral"}


@pytest.mark.asyncio
async def test_fetch_restart_node(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(200, {"status": "ok", "message": "killed"})
    )
    result = await fetch_restart_node("worker-1", client=mock_client)
    assert "ok" in result


@pytest.mark.asyncio
async def test_fetch_clear_cache(mock_client):
    mock_client.request = AsyncMock(
        return_value=_mock_response(200, {"status": "cleared"})
    )
    result = await fetch_clear_cache(client=mock_client)
    assert "cleared" in result
