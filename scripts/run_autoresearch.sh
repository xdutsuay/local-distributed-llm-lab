#!/usr/bin/env bash
# Run one autoresearch-macos training experiment (~5 min). Logs to data/autoresearch_runs.jsonl.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${PYTHONPATH:-}:$ROOT"
export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-1}"

PYTHON="${ROOT}/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

exec "$PYTHON" -m coordinator.autoresearch_runner "$@"
