# Extend LLMLAB MCP server (dev + cluster operations)

**Status:** Planned (not yet implemented).  
**Entry point:** [`mcp_server.py`](../../mcp_server.py) (FastMCP).  
**Coordinator:** [`coordinator/main.py`](../../coordinator/main.py) @ `http://localhost:8000` (`LLM_LAB_API_URL`).

## Goals

1. **Dev MCP** — Diagnose cluster from Cursor without manual curl/dashboard guessing.  
2. **Product MCP** — Thin `httpx` wrapper over existing REST APIs; no duplicated planner/worker logic.  
3. **Tests** — Real assertions in `tests/test_mcp.py` and `tests/test_future_mcp.py` (mocked HTTP).

## Principles

- All tools call coordinator via `httpx`; base URL from `LLM_LAB_API_URL`.  
- Human-readable string responses; include API error bodies when present.  
- Read-only tools must not mutate state unless named (e.g. `swap_node_model`).  
- Export `EXPECTED_TOOL_NAMES` and `RESOURCE_URIS` for contract tests.

## Tools (minimum)

### Read-only

| Tool | HTTP |
|------|------|
| `cluster_health` | GET `/health` (`ray_status` field) |
| `list_nodes` | GET `/api/nodes` |
| `list_tasks` | GET `/api/tasks` (slice client-side, limit arg) |
| `list_events` | GET `/api/events` |
| `list_tools` | GET `/api/tools` |
| `cache_stats` | GET `/api/cache/stats` |

### Mutating (clear docstrings)

| Tool | HTTP |
|------|------|
| `submit_chat` | POST `/chat` — rename from `submit_task`; `ChatRequest`: `prompt`, optional `client_id`, `model` |
| `swap_node_model` | POST `/api/nodes/{id}/model` |
| `restart_node` | POST `/api/nodes/{id}/restart` |
| `clear_cache` | POST `/api/cache/clear` |

### Dev workflow

| Tool | Behavior |
|------|----------|
| `run_regression_gate` | Subprocess: `pytest tests/test_regression_gate.py -m "not live" -q` |
| `coordinator_docs` | Pointer to NEXT_STEPS, COMPONENTS, graph hubs |

## MCP resources

| URI | Source |
|-----|--------|
| `llmlab://nodes/active` | GET `/api/nodes` |
| `llmlab://tasks/recent` | GET `/api/tasks` → last 20 |
| `llmlab://events/recent` | GET `/api/events?limit=50` |

## Deliverables

1. Updated `mcp_server.py`  
2. Filled `tests/test_future_mcp.py`  
3. `docs/MCP.md` — Cursor registration, Phase B–C debug playbook  
4. `requirements.txt`: `mcp`, `httpx`  
5. `config/claude_config_example.json` — `LLM_LAB_API_URL` env  

## Acceptance criteria

- With coordinator on :8000: health → nodes → test chat → tasks/events on failure  
- `pytest tests/test_mcp.py tests/test_future_mcp.py -q` passes without live server  
- No planner/worker logic outside coordinator  

## Out of scope

Phase 13 RAG, mobile PWA changes, PyInstaller.

## Debug playbook (preview)

Tie to [NEXT_STEPS.md](../../NEXT_STEPS.md) Phase B–C:

- **Cold start:** `cluster_health` → `list_events` (`prewarm`, `error`) → `submit_chat`  
- **Model swap:** `list_nodes` → `swap_node_model` → `list_events` → `submit_chat`  
- **Failure triage:** `list_tasks` + `list_events` after failed chat  
