# Inference path guide (Phase B–C)

How LLMLAB chooses **local in-process** vs **Ray remote** workers, and when to use each backend.

## Decision rule (implemented)

`AdaptiveWorkerPool` uses **LLM-capable node count** from `NodeRegistry.active_llm_node_count()`:

| Nodes | Path | Why |
|-------|------|-----|
| **≤ 1** | `LocalLLMWorker` in coordinator process | No Ray IPC; best for single-GPU LM Studio/Ollama |
| **> 1** | Round-robin `@ray.remote` `LLMWorker` actors | Distribute across LAN machines |

Coordinator always counts itself as one node. Extra phones/browsers without `llm_inference` do **not** force Ray mode.

### Force local (benchmarking)

```bash
export FORCE_LOCAL_WORKER=1
./scripts/start_coordinator.sh
```

Skips Ray dispatch even if multiple nodes are connected. Use for Phase B1 baseline latency.

## Backend selection

| `INFERENCE_BACKEND` | Endpoint | Best for |
|---------------------|----------|----------|
| `ollama` (default) | `http://127.0.0.1:11434` | Quick local models, `ollama pull` workflow |
| `lmstudio` | `LMSTUDIO_API_BASE` (default `http://127.0.0.1:1234/v1`) | Gemma / MLX models in LM Studio |
| `airllm` | Hugging Face weights in-process | Large models with layer offloading (heavy deps) |

Set via env before starting coordinator, or use dashboard provider toggle on `/llmlab`.

## Ray: use when / skip when

**Use Ray when:**

- Two or more machines run `LLMWorker` with `llm_inference` capability
- You want round-robin across GPUs on the LAN
- Coordinator should not hold the only GPU copy of the model

**Skip Ray when (single machine):**

- One GPU and LM Studio or Ollama on localhost — local path is faster
- You see multi-second overhead with Ray on a 1-node cluster
- Debugging model swap / cold start — fewer moving parts with `FORCE_LOCAL_WORKER=1`

## Cold start

On startup, coordinator runs `_prewarm_model()` for Ollama (skipped for `airllm` and `RAY_MOCK_MODE`). LM Studio loads lazily on first request.

Watch events:

```bash
curl -s 'http://localhost:8000/api/events?event_type=prewarm&limit=5'
```

MCP: `list_events(event_type="prewarm")`

## Model swap

1. `list_nodes` (MCP or dashboard) — copy full `node_id`
2. `swap_node_model(node_id, model)` — updates registry + worker
3. `submit_chat` with short prompt to verify

Coordinator nodes (`coordinator-*`) use `ollama ps` verification; Ray workers call `swap_model.remote`.

## Benchmark (Phase B)

```bash
# Terminal 1 — coordinator
INFERENCE_BACKEND=lmstudio LMSTUDIO_API_BASE=http://127.0.0.1:1234/v1 ./scripts/start_coordinator.sh

# Terminal 2 — timed chat
python scripts/benchmark_chat.py --prompt "2+2" --repeat 3
python scripts/benchmark_chat.py --prompt "2+2" --repeat 3 --force-local
```

Record p50/p95 in [REGRESSION_LOG.md](../REGRESSION_LOG.md).

## Related code

- [`coordinator/worker_pool.py`](../coordinator/worker_pool.py) — `@ray_required`, `LocalLLMWorker`
- [`coordinator/worker.py`](../coordinator/worker.py) — Ollama / LM Studio HTTP
- [`coordinator/main.py`](../coordinator/main.py) — `/chat`, model APIs, prewarm
