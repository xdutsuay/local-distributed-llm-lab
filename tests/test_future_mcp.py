"""Contract tests for the LLMLAB MCP server surface."""

from __future__ import annotations

import inspect

import pytest

import mcp_server
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from mcp_server import (
    EXPECTED_TOOL_NAMES,
    RESOURCE_URIS,
    _resource_json,
    fetch_coordinator_docs,
    mcp,
)


def test_mcp_server_initialization():
    assert mcp.name == "LLM Lab"


def test_expected_tool_names_contract():
    assert len(EXPECTED_TOOL_NAMES) == 15
    assert set(EXPECTED_TOOL_NAMES) == {
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
        "autoresearch_run_once",
        "autoresearch_status",
        "autoresearch_docs",
    }
    assert "submit_task" not in EXPECTED_TOOL_NAMES


def test_resource_uris_contract():
    assert len(RESOURCE_URIS) == 3
    assert set(RESOURCE_URIS) == {
        "llmlab://nodes/active",
        "llmlab://tasks/recent",
        "llmlab://events/recent",
    }


def test_mcp_tools_registered_on_stub():
    registered = {fn.__name__ for fn in mcp._tools}
    assert registered == set(EXPECTED_TOOL_NAMES)


def test_mcp_resources_registered_on_stub():
    registered = {uri for uri, _fn in mcp._resources}
    assert registered == set(RESOURCE_URIS)


@pytest.mark.asyncio
async def test_mcp_list_tools_contract():
    names = await mcp.list_tools()
    assert set(names) == set(EXPECTED_TOOL_NAMES)


def test_fetch_helpers_exist_for_http_tools():
    sync_helpers = {"coordinator_docs", "autoresearch_docs"}
    skip = {"run_regression_gate"} | sync_helpers
    for name in EXPECTED_TOOL_NAMES:
        if name in skip:
            continue
        helper = f"fetch_{name}"
        assert hasattr(mcp_server, helper), f"missing {helper}"
        fn = getattr(mcp_server, helper)
        assert inspect.iscoroutinefunction(fn)


def test_coordinator_docs_pointers():
    text = fetch_coordinator_docs()
    assert "NEXT_STEPS.md" in text
    assert "COMPONENTS.md" in text
    assert "AdaptiveWorkerPool" in text


@pytest.mark.asyncio
async def test_resource_json_nodes():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.is_error = False
    mock_resp.json.return_value = {"active_nodes": {"n1": {}}}

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_resp)
    mock_client.aclose = AsyncMock()

    import mcp_server as ms

    original = ms.coordinator_request

    async def _fake(method, path, **kwargs):
        return await original(method, path, client=mock_client, **kwargs)

    ms.coordinator_request = _fake
    try:
        out = await _resource_json("GET", "/api/nodes")
        assert '"active_nodes"' in out
        assert "n1" in out
    finally:
        ms.coordinator_request = original


def test_api_url_env_default():
    assert mcp_server.API_URL.startswith("http")
