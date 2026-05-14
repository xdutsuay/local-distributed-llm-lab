# Local Distributed LLM Lab Development Guide

## Cursor Cloud specific instructions

### Overview
A distributed AI/LLM orchestration framework with a FastAPI coordinator, Ray-based worker pool, LangGraph workflows, and Ollama for local LLM inference.

### Running tests
- Activate venv: `source .venv/bin/activate`
- Run tests: `PYTHONPATH=$(pwd) pytest -q --ignore=tests/e2e`
- Tests require `PYTHONPATH` set to the repo root (no `setup.py`/`pyproject.toml` for package installs)
- The `tests/e2e/` directory requires `selenium` and a browser; skip in cloud environments
- Some tests depend on Ray/Ollama and will fail without them; ~64 tests pass without external services

### Running the coordinator (test mode)
- `RAY_MOCK_MODE=1 PYTHONPATH=$(pwd) uvicorn coordinator.main:app --host 0.0.0.0 --port 8000`
- `RAY_MOCK_MODE=1` bypasses Ray initialization for local/test development
- Health endpoint: `GET /health` returns `{"status": "ok"}`
- Dashboard: `/llmlab`, Chat UI: `/chat_ui`

### Key gotchas
- `pytest.ini` sets `asyncio_mode = auto` but does not set `pythonpath`; always export `PYTHONPATH` when running tests
- Full LLM inference requires Ollama installed with a model pulled (default: `llama3.2`)
- Ray is optional for single-node mode; the `AdaptiveWorkerPool` falls back to local execution
