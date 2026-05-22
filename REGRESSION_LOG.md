# Regression Log — Stable v1

## Live smoke (2026-05-21)

| Component | Status | Notes |
|-----------|--------|-------|
| LM Studio `http://127.0.0.1:1234` | **Works** | `google/gemma-4-e2b` listed |
| Coordinator `/health` | **Works** | Port 8000 (freed from conflicting `backend.server`) |
| Dashboard `/llmlab` | **Works** | Provider modal, LM Studio selection |
| `POST /api/provider` lmstudio | **Works** | `LM Studio already running` |
| `POST /chat` (curl) | **Works** | `2+2` → `["4","Result"]` ~65s first call |
| Chat UI `/chat_ui` | **Works** | Response appears after **~23s** (full workflow; UI blocks until `/chat` completes) |

### UI latency note

The chat UI waits for the entire `POST /chat` LangGraph run (planner + 2–4 execute steps). API may log intermediate work before the HTTP response is returned; the browser only updates when `fetch` resolves. Improving perceived speed = streaming or fewer plan steps (post–v1).

### Checkpoint reference

| Commit | When things worked |
|--------|-------------------|
| `e0aac21` | MicroGPT + UI on **Ollama** path |
| `91a3161` | Mobile mesh + vector memory (slow but functional) |
| `113bdfb` | SQLite persistence + AirLLM optional |

## Mocked gate

```bash
PYTHONPATH=. pytest tests/test_regression_gate.py -m "not live" -q
PYTHONPATH=. pytest tests/ --ignore=tests/e2e/ -q
```

**Result:** 92 passed, 17 skipped (2026-05-21).

## Live gate (2026-05-22)

| Step | Status | Notes |
|------|--------|-------|
| R7 `/health` | **PASS** | `pytest tests/test_regression_gate.py::TestRegressionGateLive::test_r07_live_coordinator_health -m live` |
| R8 `/chat` | Manual | Full LangGraph run often **60s+**; use `scripts/benchmark_chat.py --timeout 120` |
| R9 cache repeat | Manual | Second identical prompt should be faster if cache hits |
| R10 Android | Manual | `ANDROID_E2E_OK=1` after APK connect |

Phase B–C docs: [docs/INFERENCE_PATH.md](docs/INFERENCE_PATH.md) (`6156732`).
