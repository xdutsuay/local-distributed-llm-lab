# Autoresearch-macos integration (Phase 17)

**Status:** Shipped as optional sidecar.  
**Upstream:** [miolini/autoresearch-macos](https://github.com/miolini/autoresearch-macos)

## Summary

LLMLAB orchestrates **inference**; autoresearch runs **single-GPU training** research. Integration is sidecar + logging + tools—not merged into `coordinator/worker.py`.

## Components

| Piece | Path |
|-------|------|
| Experiment README | `experiments/autoresearch/README.md` |
| Wrapper script | `scripts/run_autoresearch.sh` |
| Runner module | `coordinator/autoresearch_runner.py` |
| Coordinator tool | `autoresearch_train` in tool registry |
| MCP tools | `autoresearch_run_once`, `autoresearch_status`, `autoresearch_docs` |
| Run log | `data/autoresearch_runs.jsonl` (gitignored) |

## Env guards

- `LLMLAB_BLOCK_TRAIN=1` — refuse training runs
- `LLMLAB_BLOCK_CHAT=1` — document for night research (manual)

## MCP debug flow

`cluster_health` → `autoresearch_status` → `autoresearch_run_once` → `list_events(event_type="autoresearch")`

## Out of scope

- Ray-distributed training loops
- Exporting nanochat checkpoints into Ollama/LM Studio
- Replacing Phase 13 RAG
