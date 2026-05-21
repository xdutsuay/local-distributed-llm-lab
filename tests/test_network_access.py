from pathlib import Path


def test_start_coordinator_script_defaults_to_all_interfaces():
    script = Path("scripts/start_coordinator.sh").read_text()
    assert 'LLMLAB_HOST=${LLMLAB_HOST:-0.0.0.0}' in script
    assert 'uvicorn coordinator.main:app --host "${LLMLAB_HOST}" --port "${LLMLAB_PORT}"' in script


def test_chat_ui_uses_relative_chat_endpoint():
    chat_ui = Path("frontend/chat.html").read_text()
    assert "fetch('/chat'" in chat_ui
    assert "Browser Micro Node" in chat_ui
