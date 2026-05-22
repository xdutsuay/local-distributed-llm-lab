# LLMLAB MCP Server

The MCP server exposes coordinator REST APIs to Cursor, Claude Desktop, and Antigravity without duplicating planner or worker logic.

**Entry point:** [`mcp_server.py`](../mcp_server.py) (FastMCP + `httpx`).

## Install

```bash
pip install -r requirements.txt   # includes mcp, httpx
```

Set the coordinator base URL (default `http://localhost:8000`):

```bash
export LLM_LAB_API_URL=http://localhost:8000
```

## Cursor / Claude registration

**Claude Desktop** — copy and edit [`config/claude_config_example.json`](../config/claude_config_example.json):

```json
{
  "mcpServers": {
    "llm-lab": {
      "command": "/path/to/LLMLAB/venv/bin/python",
      "args": ["/path/to/LLMLAB/mcp_server.py"],
      "env": {
        "LLM_LAB_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

**Antigravity** — same pattern in [`config/antigravity_config.json`](../config/antigravity_config.json).

Start the coordinator before using cluster tools:

```bash
./scripts/start_coordinator.sh
```

## Tools (12)

| Tool | Type | Coordinator API |
|------|------|-----------------|
| `cluster_health` | read | `GET /health` (`ray_status`) |
| `list_nodes` | read | `GET /api/nodes` |
| `list_tasks` | read | `GET /api/tasks` |
| `list_events` | read | `GET /api/events` |
| `list_tools` | read | `GET /api/tools` |
| `cache_stats` | read | `GET /api/cache/stats` |
| `submit_chat` | **mutate** | `POST /chat` |
| `swap_node_model` | **mutate** | `POST /api/nodes/{id}/model` |
| `restart_node` | **mutate** | `POST /api/nodes/{id}/restart` |
| `clear_cache` | **mutate** | `POST /api/cache/clear` |
| `run_regression_gate` | dev | local `pytest` subprocess |
| `coordinator_docs` | read | static doc pointers |

## Resources (3)

| URI | Source |
|-----|--------|
| `llmlab://nodes/active` | `GET /api/nodes` |
| `llmlab://tasks/recent` | last 20 tasks |
| `llmlab://events/recent` | `GET /api/events?limit=50` |

## Debug playbook (Phase B–C)

From [`NEXT_STEPS.md`](../NEXT_STEPS.md):

1. **Cold start:** `cluster_health` → `list_events` (filter `prewarm`, `error`) → `submit_chat` with a short prompt.
2. **Model swap:** `list_nodes` → `swap_node_model` → `list_events` → `submit_chat` to verify routing.
3. **Failure triage:** after a failed chat, `list_tasks` + `list_events` for the same window.
4. **Pre-release:** `run_regression_gate` (mocked gate, no live LM Studio).

Deep component reference: [`docs/COMPONENTS.md`](COMPONENTS.md). Planning handoff: [`NEXT_STEPS.md`](../NEXT_STEPS.md).

## Tests

```bash
cd /path/to/LLMLAB
PYTHONPATH=. pytest tests/test_mcp.py tests/test_future_mcp.py -q
```

Contract constants: `EXPECTED_TOOL_NAMES`, `RESOURCE_URIS` in `mcp_server.py`.
