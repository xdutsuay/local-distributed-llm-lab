from coordinator.browser_micro import (
    build_browser_microtask_code,
    normalize_browser_contribution,
    summarize_served_by,
)


def test_build_browser_microtask_code_contains_prompt_and_kind():
    code = build_browser_microtask_code("Review the dashboard and summarize it")
    assert "browser_microgpt" in code
    assert "Review the dashboard and summarize it" in code
    assert "keywords" in code


def test_normalize_browser_contribution_shapes_payload():
    normalized = normalize_browser_contribution(
        "browser-node-1",
        {
            "status": "success",
            "response": {
                "kind": "browser_microgpt",
                "summary": "Review the dashboard",
                "keywords": ["review", "dashboard"],
                "clauses": ["Review the dashboard"],
            },
            "error": None,
        },
    )
    assert normalized["node_id"] == "browser-node-1"
    assert normalized["status"] == "success"
    assert normalized["keywords"] == ["review", "dashboard"]


def test_summarize_served_by_lists_browser_nodes():
    summary = summarize_served_by(
        "local-worker",
        [
            {"node_id": "browser-1", "status": "success"},
            {"node_id": "browser-2", "status": "error"},
        ],
    )
    assert summary["primary_node"] == "local-worker"
    assert summary["browser_micro_nodes"] == ["browser-1"]
    assert summary["browser_micro_count"] == 1
