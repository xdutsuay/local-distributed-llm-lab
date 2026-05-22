# LLMLab Status — Stable v1

## Shipped in this session

### Coordinator
- **Distributed cache:** `DistributedCacheClient` skips Ray actors in `RAY_MOCK_MODE`; actor registered on startup when Ray is live.
- **SQLite tasks:** `final_node`, `composition`, `route_details` persisted for dashboard attribution.
- **`/chat` errors:** Returns structured JSON (503) instead of bare 500.
- **LM Studio path:** `LocalLLMWorker` + provider UI; session HTTP mock in tests.

### Tests
- **`tests/test_regression_gate.py`:** R1–R6 mocked gate; R7–R10 marked `@pytest.mark.live`.
- **`pytest.ini`:** Default `-m "not live"`; live tests opt-in.
- **Fixes:** MagicMock cache leak, `test_coordinator` expects 200, persistence/polish tests use SQLite.

### Android (`android-compute-node`)
- WebSocket to `ws://<host>:8000/ws/join`, heartbeats, `execute_task` handler.
- Material icons extended dependency for Compose UI.
- Debug APK: `android-compute-node/app/build/outputs/apk/debug/app-debug.apk` (after `./gradlew assembleDebug`).

## Run locally

```bash
# Unit tests
PYTHONPATH=. pytest tests/ --ignore=tests/e2e/ -q

# Regression gate (mocked)
PYTHONPATH=. pytest tests/test_regression_gate.py -m "not live" -q

# Coordinator + LM Studio
INFERENCE_BACKEND=lmstudio LMSTUDIO_API_BASE=http://127.0.0.1:1234/v1 ./scripts/start_coordinator.sh
./scripts/health_check.py
```

## Live validation (2026-05-21)

- LM Studio `google/gemma-4-e2b` on `:1234` — OK
- Dashboard + provider swap — OK
- `POST /chat` — OK (~65s cold; multi-step LangGraph)
- Chat UI — OK; answer appears when **`fetch('/chat')` completes** (~23s observed). UI has no streaming; timer shows elapsed seconds while waiting.

**Docs:** Plans in `docs/plans/`; contributor guide in `CONTRIBUTING.md`  
**Pushed:** `f862bc1` on `main`

## MCP server (2026-05-21)

- [`mcp_server.py`](mcp_server.py): 12 tools + 3 resources (`llmlab://nodes/active`, etc.)
- Setup: [docs/MCP.md](docs/MCP.md)
- Tests: `pytest tests/test_mcp.py tests/test_future_mcp.py -q`

## Remaining (post–stable v1)

- Phase 13 RAG (ChromaDB planner integration) — deferred
- LangGraph lifespan migration (FastAPI `@app.on_event` deprecation)
- Full Ray multi-node perf tuning with Gemma on remote workers
