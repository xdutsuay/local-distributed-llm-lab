"""Contract tests for the LLMLAB MCP server surface."""

from __future__ import annotations

import inspect

import pytest

import mcp_server
from mcp_server import (
    EXPECTED_TOOL_NAMES,
    RESOURCE_URIS,
    fetch_coordinator_docs,
    mcp,
)


def test_mcp_server_initialization():
    assert mcp.name == "LLM Lab"


def test_expected_tool_names_contract():
    assert len(EXPECTED_TOOL_NAMES) == 12
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
    for name in EXPECTED_TOOL_NAMES:
        if name in ("run_regression_gate", "coordinator_docs"):
            continue
        helper = f"fetch_{name}"
        assert hasattr(mcp_server, helper), f"missing {helper}"
        fn = getattr(mcp_server, helper)
        assert inspect.iscoroutinefunction(fn)


def test_coordinator_docs_pointers():
    text = fetch_coordinator_docs()
    assert "NEXT_STEPS.md" in text
    assert "COMPONENTS.md" in text


def test_api_url_env_default():
    assert mcp_server.API_URL.startswith("http")
