"""
Helpers for lightweight browser-node fanout during chat requests.

These browser "micro" tasks do not run a real LLM in the browser. They run
small JavaScript analyses on connected web worker nodes so the chat UI can show
best-effort distributed contributions alongside the primary local LLM answer.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "if", "in", "into", "is", "it", "its", "me", "of", "on", "or",
    "our", "should", "that", "the", "their", "then", "this", "to", "we",
    "what", "when", "where", "which", "with", "you", "your",
}


def build_browser_microtask_code(prompt: str) -> str:
    prompt_literal = json.dumps(prompt)
    stopwords_literal = json.dumps(sorted(STOPWORDS))
    return f"""
const prompt = {prompt_literal};
const stopwords = new Set({stopwords_literal});
const words = (prompt.toLowerCase().match(/[a-z0-9']+/g) || []);
const keywords = [...new Set(words.filter(word => word.length > 3 && !stopwords.has(word)))].slice(0, 8);
const clauses = prompt
  .split(/\\?|\\.|!|,|\\band\\b|\\bthen\\b/gi)
  .map(part => part.trim())
  .filter(Boolean)
  .slice(0, 4);
const summary = clauses[0] || prompt.slice(0, 120);
return {{
  kind: "browser_microgpt",
  summary,
  keywords,
  clauses,
  prompt_length: prompt.length
}};
""".strip()


def normalize_browser_contribution(node_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    payload = result.get("response")
    if not isinstance(payload, dict):
        payload = {"raw": payload}

    return {
        "node_id": node_id,
        "status": result.get("status", "unknown"),
        "kind": payload.get("kind", "browser_microgpt"),
        "summary": payload.get("summary", ""),
        "keywords": payload.get("keywords", []),
        "clauses": payload.get("clauses", []),
        "error": result.get("error"),
    }


def summarize_served_by(primary_node: str, browser_contributions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "primary_node": primary_node,
        "browser_micro_nodes": [item["node_id"] for item in browser_contributions if item.get("status") == "success"],
        "browser_micro_count": sum(1 for item in browser_contributions if item.get("status") == "success"),
    }
