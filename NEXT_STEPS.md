# LLMLAB — Next Steps

Handoff for working on this repo individually. Branch: **`main`** @ latest.

**Stable v1 (2026-05-21):** Regression gate in `tests/test_regression_gate.py`, full status in `STATUS.md`, run log in `REGRESSION_LOG.md`. Phase 13 RAG deferred until live LM Studio/Gemma path is validated on your machine.

**Graph (optional):** `graphify-out/GRAPH_REPORT.md` and `graph.html` — hubs: `AdaptiveWorkerPool`, `NodeRegistry`, `RayMessageBus`, `LLMWorker`.

**Also read:** `docs/ROADMAP.md` (Phases 12–16), `docs/COMPONENTS.md`, `docs/ARCHITECTURE.md`.

---

## Plan 1 — Commit plan (dirty files)

Do **not** commit binaries, build artifacts, or local databases.

### Commit 1 — Coordinator + MicroGPT wiring (core WIP)

**Stage only:**

- `coordinator/main.py`
- `coordinator/planner.py`
- `coordinator/worker.py`
- `coordinator/worker_pool.py`

**Suggested message:**

```
feat(coordinator): extend worker pool, planner, and MicroGPT context paths
```

**Before commit:**

```bash
pytest tests/test_adaptive_pool.py tests/test_coordinator.py tests/test_load_balancing.py -q
```

**Review focus:** `worker_pool.py` Ray vs local dispatch; `worker.py` model swap / Ollama paths; `planner.py` RAG/vector hooks if present.

### Commit 2 — Dashboard UI

**Stage only:**

- `frontend/dashboard.html`

**Suggested message:**

```
feat(ui): dashboard updates for cluster observability
```

### Commit 3 — New tests

**Stage only:**

- `tests/test_adaptive_pool.py`
- `tests/test_browser_micro.py`
- `tests/test_network_access.py`

**Suggested message:**

```
test: adaptive pool, browser microtask, and network access coverage
```

### Do **not** commit (update `.gitignore` first)

| Path | Why |
|------|-----|
| `build/`, `dist/` | PyInstaller artifacts |
| `graphify-out/` | Local knowledge graph |
| `data/llmlab.db` | Runtime SQLite checkpoint |
| `data/chroma_db/chroma.sqlite3` | Local vector DB; binary diff is noise |
| `picoclawexperiment/` | Experiment folder unless you intend to ship it |
| `llmlab-coordinator.spec` | Optional — commit only for reproducible builds |

**Suggested `.gitignore` additions:**

```
build/
dist/
graphify-out/
data/llmlab.db
data/chroma_db/
*.spec
picoclawexperiment/
```

**If chroma was touched accidentally:**

```bash
git restore data/chroma_db/chroma.sqlite3
```

---

## Milestone — “Stable local inference + committed coordinator slice”

**Outcome:** Single-machine chat works reliably (Ollama cold start, model swap). Coordinator WIP is committed and tested. You know whether Ray helps or hurts GPU inference on your hardware.

**Why:** Graph centers on `AdaptiveWorkerPool` + `LLMWorker`. Recent commits noted Ollama slowness and swap/restart failures. Stabilize before ROADMAP Phase 13 (RAG).

### Phase A — Hygiene (½ day) ✅

| Step | Action | Done when |
|------|--------|-----------|
| A1 | Apply Plan 1 commits 1–3; update `.gitignore` per above | ✅ No `build/`, `dist/`, DB binaries staged |
| A2 | `pytest -q` | ✅ Core tests pass |
| A3 | `./scripts/start_coordinator.sh` (or your usual start) | ✅ Dashboard at `http://localhost:8000/llmlab` |

### Phase B — Diagnose inference path (1–2 days)

**Guide:** [docs/INFERENCE_PATH.md](docs/INFERENCE_PATH.md) — Ray vs local decision, `FORCE_LOCAL_WORKER`, `scripts/benchmark_chat.py`, event log playbook.

| Step | Investigation | Record |
|------|---------------|--------|
| B1 | **Ray off:** 1 node, local `LLMWorker` only — measure chat latency | Baseline ms |
| B2 | **Ray on:** 1 worker — same prompt | Compare |
| B3 | **Ray on:** 2 nodes (if available) | Compare |
| B4 | Trace: FastAPI → `AdaptiveWorkerPool` → `LLMWorker.generate()` → Ollama | Note blocking calls |

**Files to read first:**

- `coordinator/worker_pool.py` — `@ray_required`, `_get_next_ray_worker`
- `coordinator/worker.py` — `detect_available_models`, swap, prewarm
- `coordinator/main.py` — model management API

**Acceptance criteria:**

- Documented answer: “Use Ray when … / skip Ray when …”
- Chat responds within acceptable time on one machine without swap thrashing

### Phase C — Fix swap + cold start (1–2 days)

| Issue (from prior commits) | Likely area |
|----------------------------|-------------|
| Ollama cold-start hang in UI | Chat routes in `main.py`, worker prewarm |
| Swap model / restart failing | Model management API + `worker.py` |
| GPU inference slow with Ray | Force local path when `node_count == 1` (see `tests/test_adaptive_pool.py`) |

**Acceptance criteria:**

- Dashboard: swap model succeeds; next chat uses new model.
- First message after coordinator start completes without hang (timeout + visible status).

### Phase D — Lock in with tests (1 day)

| Step | Action |
|------|--------|
| D1 | `tests/test_model_detection.py` passes |
| D2 | Run `test_adaptive_pool`, `test_browser_micro`, `test_network_access` |
| D3 | Optional: `tests/e2e/test_integration.py` smoke |

**Acceptance criteria:** `pytest -q` green; README Quick Start works on a fresh venv.

### Next milestone (after this one)

**Phase 13 RAG** (`docs/ROADMAP.md`): ChromaDB, Planner → vector query, auto-store Q&A. Graph shows `get_vector_store()` / `plan()` community — only start after Phases B–C are stable.

**Time budget:** ~4–5 focused days.

**After milestone:** `graphify update .` (from repo root).

---

## Quick start when opening this repo

1. Update `.gitignore` → run Plan 1 commits.
2. `./scripts/start_coordinator.sh` → confirm dashboard loads.
3. Start Phase B (inference diagnosis).
