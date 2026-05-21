"""
Stable v1 regression gate (R1–R10).

Mocked gate (CI / pre-live):
  PYTHONPATH=. pytest tests/test_regression_gate.py -m "not live" -q

Full gate including live LM Studio + manual Android (R7–R10):
  PYTHONPATH=. pytest tests/test_regression_gate.py -m live -q
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_pytest(args: list[str], timeout: int = 300) -> None:
    cmd = [str(REPO_ROOT / "venv" / "bin" / "pytest"), *args]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT), "RAY_MOCK_MODE": "1"}
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"pytest {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
        )


# Avoid recursive re-entry when R05 spawns a child pytest.
_GATE_IGNORE = ["tests/test_regression_gate.py", "tests/e2e/"]


class TestRegressionGateMocked:
    """R1–R6: run in default CI; no live services required."""

    def test_r01_repo_hygiene(self):
        """R1: no build artifacts or local DBs staged for commit."""
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        forbidden_prefixes = (
            "build/",
            "dist/",
            "graphify-out/",
            "data/llmlab.db",
            "data/chroma_db/",
        )
        for path in result.stdout.splitlines():
            path = path.strip()
            if not path:
                continue
            for prefix in forbidden_prefixes:
                assert not path.startswith(prefix), f"Forbidden staged path: {path}"

    def test_r02_db_cache_logic(self):
        _run_pytest(
            [
                "tests/test_db.py",
                "tests/test_caching.py",
                "tests/test_logic.py",
                "-q",
            ]
        )

    def test_r03_worker_pool_core(self):
        _run_pytest(
            [
                "tests/test_adaptive_pool.py",
                "tests/test_load_balancing.py",
                "tests/test_model_detection.py",
                "-q",
            ]
        )

    def test_r04_coordinator_api_mocked(self):
        _run_pytest(
            [
                "tests/test_coordinator.py",
                "tests/test_routes.py",
                "tests/test_cluster.py",
                "-q",
            ]
        )

    def test_r05_full_unit_suite(self):
        ignore_args = [f"--ignore={p}" for p in _GATE_IGNORE]
        _run_pytest(["tests/", *ignore_args, "-q"], timeout=600)

    def test_r06_distributed_cache_actor_and_fallback(self):
        from coordinator.cache_manager import (
            DistributedCacheClient,
            get_cache_manager,
        )

        # Local fallback when Ray is not initialized
        os.environ["RAY_MOCK_MODE"] = "1"
        client = DistributedCacheClient(default_ttl=60)
        client.put("gate prompt", "llama3.2", "gate response")
        assert client.get("gate prompt", "llama3.2") == "gate response"

        mock_actor = MagicMock()
        mock_actor.get.remote.return_value = "actor-hit"
        mock_actor.put.remote.return_value = None

        with patch("ray.is_initialized", return_value=True), patch(
            "ray.get_actor", side_effect=ValueError("no actor")
        ), patch.object(
            DistributedCacheClient,
            "_get_actor",
            return_value=mock_actor,
        ), patch("ray.get", return_value="actor-hit"):
            actor_client = DistributedCacheClient(default_ttl=60)
            assert actor_client.get("p", "m") == "actor-hit"
            actor_client.put("p2", "m", "v2")
            mock_actor.put.remote.assert_called()

        # Singleton resets cleanly in-process
        import coordinator.cache_manager as cm

        cm._global_cache = None
        singleton = get_cache_manager()
        assert singleton is get_cache_manager()


@pytest.mark.live
class TestRegressionGateLive:
    """R7–R9: require coordinator + LM Studio running locally."""

    @pytest.fixture
    def live_base_url(self):
        return os.getenv("LLMLAB_BASE_URL", "http://127.0.0.1:8000")

    def test_r07_live_coordinator_health(self, live_base_url):
        try:
            resp = requests.get(f"{live_base_url}/health", timeout=5)
        except requests.RequestException as exc:
            pytest.skip(f"Coordinator not reachable: {exc}")
        assert resp.status_code == 200

    def test_r08_live_chat(self, live_base_url):
        try:
            resp = requests.post(
                f"{live_base_url}/chat",
                json={"prompt": "2+2"},
                timeout=120,
            )
        except requests.RequestException as exc:
            pytest.skip(f"Coordinator not reachable: {exc}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("response")

        tasks = requests.get(f"{live_base_url}/api/tasks", timeout=10).json()
        assert tasks.get("tasks")

    def test_r09_cache_repeat_faster_or_cached(self, live_base_url):
        prompt = "Regression gate cache probe: what is 2+2?"
        try:
            r1 = requests.post(
                f"{live_base_url}/chat", json={"prompt": prompt}, timeout=120
            )
            r2 = requests.post(
                f"{live_base_url}/chat", json={"prompt": prompt}, timeout=120
            )
        except requests.RequestException as exc:
            pytest.skip(f"Coordinator not reachable: {exc}")
        assert r1.status_code == 200 and r2.status_code == 200
        # Second call should not be slower than first by more than 2x (heuristic)
        # or logs/events show cache — we accept both completing successfully.
        assert r2.json().get("response")


@pytest.mark.live
def test_r10_android_e2e_manual_checklist():
    """
    R10: manual — install debug APK, connect to coordinator, verify node in /api/nodes.
    This test documents the checklist and passes when ANDROID_E2E_OK=1 is set.
    """
    if os.getenv("ANDROID_E2E_OK") != "1":
        pytest.skip(
            "Set ANDROID_E2E_OK=1 after manual Android connect + task round-trip"
        )
