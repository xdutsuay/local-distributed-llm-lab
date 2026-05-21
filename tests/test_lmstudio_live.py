"""Optional live LM Studio smoke tests — skipped unless coordinator is running."""
import os

import pytest
import requests

pytestmark = pytest.mark.live


@pytest.fixture
def base_url():
    return os.getenv("LLMLAB_BASE_URL", "http://127.0.0.1:8000")


def test_lmstudio_models_endpoint():
    api = os.getenv("LMSTUDIO_API_BASE", "http://127.0.0.1:1234/v1")
    try:
        resp = requests.get(f"{api}/models", timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"LM Studio not reachable: {exc}")
    assert resp.status_code == 200


def test_live_chat_via_coordinator(base_url):
    try:
        resp = requests.post(
            f"{base_url}/chat",
            json={"prompt": "Say hello in one word."},
            timeout=120,
        )
    except requests.RequestException as exc:
        pytest.skip(f"Coordinator not reachable: {exc}")
    assert resp.status_code == 200, resp.text
    assert resp.json().get("response")
