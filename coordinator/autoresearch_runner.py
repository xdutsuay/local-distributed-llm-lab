"""
Run autoresearch-macos training experiments from LLMLAB.

Sidecar lives at experiments/autoresearch/ (git submodule). See experiments/autoresearch/README.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT_DIR = REPO_ROOT / "experiments" / "autoresearch"
RUN_LOG_PATH = REPO_ROOT / "data" / "autoresearch_runs.jsonl"
TRAIN_TIMEOUT_SEC = 400  # 5 min train + buffer

VAL_BPB_RE = re.compile(r"val[_\s]*bpb[:\s=]+([0-9.]+)", re.IGNORECASE)


def resolve_experiment_dir(experiment_dir: Optional[str] = None) -> Path:
    if experiment_dir:
        path = Path(experiment_dir).expanduser()
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path.resolve()
    return DEFAULT_EXPERIMENT_DIR.resolve()


def is_training_blocked(experiment_dir: Optional[str] = None) -> Optional[str]:
    if os.getenv("LLMLAB_BLOCK_TRAIN", "").strip() in ("1", "true", "yes"):
        return "LLMLAB_BLOCK_TRAIN is set"
    exp = resolve_experiment_dir(experiment_dir)
    if not exp.is_dir():
        return (
            f"experiment dir missing: {exp}. "
            "See experiments/autoresearch/README.md for submodule setup."
        )
    train_py = exp / "train.py"
    if not train_py.is_file():
        return f"train.py not found under {exp}"
    return None


def parse_val_bpb(stdout: str, stderr: str = "") -> Optional[float]:
    combined = f"{stdout}\n{stderr}"
    matches = VAL_BPB_RE.findall(combined)
    if not matches:
        return None
    try:
        return float(matches[-1])
    except ValueError:
        return None


def append_run_log(entry: Dict[str, Any]) -> None:
    RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def read_recent_runs(limit: int = 10) -> list[Dict[str, Any]]:
    if not RUN_LOG_PATH.is_file():
        return []
    lines = RUN_LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    rows: list[Dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    return "unknown"


def run_training(
    experiment_dir: Optional[str] = None,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Run one autoresearch train.py invocation. Returns result dict for tools/MCP.
    """
    exp = resolve_experiment_dir(experiment_dir)
    blocked = is_training_blocked(experiment_dir)
    if blocked:
        return {"success": False, "error": blocked, "experiment_dir": str(exp)}

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "experiment_dir": str(exp),
            "command": "uv run train.py",
            "log_path": str(RUN_LOG_PATH),
        }

    env = {
        **os.environ,
        "PYTORCH_ENABLE_MPS_FALLBACK": os.getenv("PYTORCH_ENABLE_MPS_FALLBACK", "1"),
    }
    cmd = ["uv", "run", "train.py"]
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=exp,
            env=env,
            capture_output=True,
            text=True,
            timeout=TRAIN_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"training exceeded {TRAIN_TIMEOUT_SEC}s timeout",
            "experiment_dir": str(exp),
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "uv not found on PATH; install uv per experiments/autoresearch/README.md",
            "experiment_dir": str(exp),
        }

    duration = time.perf_counter() - start
    val_bpb = parse_val_bpb(proc.stdout, proc.stderr)
    success = proc.returncode == 0

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment_dir": str(exp),
        "duration_sec": round(duration, 2),
        "exit_code": proc.returncode,
        "val_bpb": val_bpb,
        "git_sha": _git_sha(),
        "success": success,
    }
    if not success:
        entry["stderr_tail"] = (proc.stderr or "")[-500:]
    append_run_log(entry)

    result: Dict[str, Any] = {
        "success": success,
        "experiment_dir": str(exp),
        "duration_sec": entry["duration_sec"],
        "exit_code": proc.returncode,
        "val_bpb": val_bpb,
        "log_path": str(RUN_LOG_PATH),
    }
    if not success:
        result["error"] = (proc.stderr or proc.stdout or "train.py failed")[-800:]
    return result


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run one autoresearch training experiment")
    parser.add_argument(
        "--experiment-dir",
        default=None,
        help="Path to autoresearch checkout (default: experiments/autoresearch)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate setup only")
    parser.add_argument("--status", action="store_true", help="Print recent jsonl runs")
    parser.add_argument("--limit", type=int, default=5, help="Rows for --status")
    args = parser.parse_args(argv)

    if args.status:
        for row in read_recent_runs(args.limit):
            print(json.dumps(row))
        return 0

    out = run_training(args.experiment_dir, dry_run=args.dry_run)
    print(json.dumps(out, indent=2))
    return 0 if out.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
