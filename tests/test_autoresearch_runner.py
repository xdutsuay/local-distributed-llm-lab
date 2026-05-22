"""Tests for autoresearch sidecar runner (no real uv/train)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coordinator.autoresearch_runner import (
    append_run_log,
    is_training_blocked,
    parse_val_bpb,
    read_recent_runs,
    resolve_experiment_dir,
    run_training,
)


def test_parse_val_bpb():
    assert parse_val_bpb("epoch 1 val_bpb: 1.234\n") == 1.234
    assert parse_val_bpb("VAL_BPB = 0.99") == 0.99
    assert parse_val_bpb("no metric here") is None


def test_is_training_blocked_when_dir_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("LLMLAB_BLOCK_TRAIN", raising=False)
    missing = tmp_path / "nope"
    out = run_training(str(missing))
    assert out["success"] is False
    assert "missing" in out["error"].lower() or "not found" in out["error"].lower()


def test_is_training_blocked_env(monkeypatch):
    monkeypatch.setenv("LLMLAB_BLOCK_TRAIN", "1")
    out = run_training(dry_run=False)
    assert out["success"] is False
    assert "LLMLAB_BLOCK_TRAIN" in out["error"]


def test_dry_run_with_valid_layout(tmp_path, monkeypatch):
    monkeypatch.delenv("LLMLAB_BLOCK_TRAIN", raising=False)
    exp = tmp_path / "ar"
    exp.mkdir()
    (exp / "train.py").write_text("# stub\n")
    out = run_training(str(exp), dry_run=True)
    assert out["success"] is True
    assert out["dry_run"] is True


def test_run_training_subprocess_mock(tmp_path, monkeypatch):
    monkeypatch.delenv("LLMLAB_BLOCK_TRAIN", raising=False)
    exp = tmp_path / "ar"
    exp.mkdir()
    (exp / "train.py").write_text("# stub\n")
    log_path = tmp_path / "runs.jsonl"
    monkeypatch.setattr(
        "coordinator.autoresearch_runner.RUN_LOG_PATH",
        log_path,
    )

    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = "done val_bpb: 1.5\n"
    proc.stderr = ""

    with patch("coordinator.autoresearch_runner.subprocess.run", return_value=proc):
        out = run_training(str(exp))

    assert out["success"] is True
    assert out["val_bpb"] == 1.5
    assert log_path.is_file()
    rows = read_recent_runs(1)
    assert rows[0]["val_bpb"] == 1.5


@pytest.mark.asyncio
async def test_autoresearch_tool_dry_run(tmp_path, monkeypatch):
    monkeypatch.delenv("LLMLAB_BLOCK_TRAIN", raising=False)
    exp = tmp_path / "ar"
    exp.mkdir()
    (exp / "train.py").write_text("# stub\n")

    from coordinator.tools.autoresearch_tool import AutoresearchTrainTool

    tool = AutoresearchTrainTool()
    out = await tool.execute(experiment_dir=str(exp), dry_run=True)
    assert out.success is True
    assert out.result.get("dry_run") is True


def test_read_recent_runs_roundtrip(tmp_path, monkeypatch):
    log_path = tmp_path / "runs.jsonl"
    monkeypatch.setattr("coordinator.autoresearch_runner.RUN_LOG_PATH", log_path)
    append_run_log({"timestamp": "t1", "val_bpb": 2.0, "success": True})
    append_run_log({"timestamp": "t2", "val_bpb": 1.0, "success": True})
    rows = read_recent_runs(2)
    assert len(rows) == 2
    assert rows[-1]["val_bpb"] == 1.0
