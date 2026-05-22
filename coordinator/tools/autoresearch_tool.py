"""Coordinator tool: run autoresearch-macos training sidecar."""
from __future__ import annotations

from typing import Any, Dict, Optional

from coordinator.autoresearch_runner import run_training
from coordinator.tools.base import Tool, ToolOutput


class AutoresearchTrainTool(Tool):
    """Run one 5-minute autoresearch train.py experiment (optional sidecar)."""

    @property
    def name(self) -> str:
        return "autoresearch_train"

    @property
    def description(self) -> str:
        return (
            "Run one autoresearch-macos training experiment (~5 min, val_bpb metric). "
            "Requires experiments/autoresearch submodule. Respects LLMLAB_BLOCK_TRAIN."
        )

    async def execute(
        self,
        experiment_dir: Optional[str] = None,
        dry_run: bool = False,
        **kwargs: Any,
    ) -> ToolOutput:
        result = run_training(experiment_dir, dry_run=dry_run)

        if kwargs:
            result["ignored_kwargs"] = list(kwargs.keys())

        if result.get("dry_run"):
            return ToolOutput(
                success=True,
                result=result,
                metadata={"tool": self.name, "dry_run": True},
            )

        if not result.get("success"):
            return ToolOutput(
                success=False,
                result=result,
                error=result.get("error", "autoresearch training failed"),
                metadata={"tool": self.name},
            )

        # Log to SQLite when coordinator DB is available
        try:
            from coordinator import db

            await db.log_event(
                "autoresearch",
                "coordinator",
                {
                    "val_bpb": result.get("val_bpb"),
                    "duration_sec": result.get("duration_sec"),
                    "exit_code": result.get("exit_code"),
                    "experiment_dir": result.get("experiment_dir"),
                },
            )
        except Exception as exc:
            result["db_log_warning"] = str(exc)

        return ToolOutput(
            success=True,
            result=result,
            metadata={"tool": self.name, "val_bpb": result.get("val_bpb")},
        )
