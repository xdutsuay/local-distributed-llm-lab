# Contributing to LLMLAB

Thanks for helping turn spare machines into a local AI cluster. This repo is actively maintained; **good first issues** are inference stability, tests, Android node protocol, and MCP tooling.

## Quick start

```bash
git clone https://github.com/xdutsuay/local-distributed-llm-lab.git
cd local-distributed-llm-lab
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest tests/test_regression_gate.py -m "not live" -q
./scripts/start_coordinator.sh
```

Open http://localhost:8000/llmlab

## Before you open a PR

1. Run the mocked regression gate (above).  
2. Do **not** commit `build/`, `dist/`, `data/*.db`, `data/chroma_db/`, or `graphify-out/`.  
3. Keep changes focused; match existing style in `coordinator/` and `tests/`.  
4. Update [STATUS.md](STATUS.md) or [REGRESSION_LOG.md](REGRESSION_LOG.md) if you change live behavior.

## Where to work

| Area | Paths | Plan |
|------|-------|------|
| Coordinator / inference | `coordinator/` | [NEXT_STEPS.md](NEXT_STEPS.md) Phase B–C |
| Tests / CI gate | `tests/test_regression_gate.py` | [docs/plans/STABLE_V1_OVERHAUL.md](docs/plans/STABLE_V1_OVERHAUL.md) |
| Android node | `android-compute-node/` | Stable v1 plan § Phase 4 |
| Cursor MCP | `mcp_server.py` | [docs/plans/EXTEND_MCP_SERVER.md](docs/plans/EXTEND_MCP_SERVER.md) |
| Docs | `docs/` | [docs/plans/README.md](docs/plans/README.md) |

## Live testing (optional)

```bash
INFERENCE_BACKEND=lmstudio LMSTUDIO_API_BASE=http://127.0.0.1:1234/v1 ./scripts/start_coordinator.sh
PYTHONPATH=. pytest tests/test_regression_gate.py -m live -q
```

Requires LM Studio or Ollama on the host.

## Questions

Open a [GitHub issue](https://github.com/xdutsuay/local-distributed-llm-lab/issues) with logs from `/api/events` and `/api/tasks` when debugging cluster behavior.
