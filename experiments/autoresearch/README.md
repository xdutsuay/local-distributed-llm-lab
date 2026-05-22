# autoresearch-macos (optional sidecar)

Single-GPU autonomous training experiments using [miolini/autoresearch-macos](https://github.com/miolini/autoresearch-macos). This folder is **not** required for LLMLAB inference.

## Setup (one time)

```bash
# From repo root
git submodule add https://github.com/miolini/autoresearch-macos experiments/autoresearch
cd experiments/autoresearch
curl -LsSf https://astral.sh/uv/install.sh | sh   # if needed
uv sync
uv run prepare.py   # ~2 min: data + tokenizer
```

Or clone without submodule:

```bash
git clone https://github.com/miolini/autoresearch-macos experiments/autoresearch
```

## GPU scheduling (one Mac)

LLMLAB chat/LM Studio and autoresearch **share the same GPU**. Do not run both at full load.

| When | Do |
|------|-----|
| Day — cluster chat | Coordinator + LM Studio; **skip** training |
| Night — research | Stop coordinator **or** `export LLMLAB_BLOCK_CHAT=1`; run agent on upstream `program.md` |
| Benchmark inference | See [docs/INFERENCE_PATH.md](../../docs/INFERENCE_PATH.md); keep autoresearch off |

## Run one 5-minute experiment

From repo root (logs to `data/autoresearch_runs.jsonl`):

```bash
./scripts/run_autoresearch.sh
```

Or via coordinator tool API / MCP `autoresearch_run_once` (when coordinator is up).

## Agent workflow (upstream)

1. Open `experiments/autoresearch/program.md` in Cursor.
2. Agent edits `train.py` only; `prepare.py` is fixed.
3. `uv run train.py` — fixed **5 min** wall clock; metric **val_bpb** (lower is better).
4. Keep or discard changes based on metric; repeat.

## LLMLAB integration

- Runner: `python -m coordinator.autoresearch_runner`
- Events: `list_events(event_type="autoresearch")` or MCP `list_events`
- Plan: [docs/plans/AUTORESEARCH_INTEGRATION.md](../../docs/plans/AUTORESEARCH_INTEGRATION.md)
