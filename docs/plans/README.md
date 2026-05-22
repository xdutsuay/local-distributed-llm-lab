# Implementation plans

Canonical plans for LLMLAB milestones. Use these when picking up work in Cursor, Antigravity, or any MCP-enabled IDE.

| Plan | Status | Summary |
|------|--------|---------|
| [Stable v1 overhaul](STABLE_V1_OVERHAUL.md) | **Shipped** (2026-05-21) | Regression gate R1–R10, LM Studio/Gemma path, Android compute node, coordinator hardening |
| [Extend MCP server](EXTEND_MCP_SERVER.md) | **Shipped** (2026-05-21) | Cursor MCP tools + resources over coordinator HTTP APIs |

## Related docs

- [STATUS.md](../../STATUS.md) — what is shipped right now
- [REGRESSION_LOG.md](../../REGRESSION_LOG.md) — gate results and live smoke notes
- [NEXT_STEPS.md](../../NEXT_STEPS.md) — commit hygiene and Phase B–C inference diagnosis
- [docs/ROADMAP.md](../ROADMAP.md) — Phases 12–16+

## Session references

Plans were drafted in agent sessions; summaries live here (not raw chat logs):

- Stable v1: Antigravity/Cursor session [52e4a1f8](https://github.com/xdutsuay/local-distributed-llm-lab) (architecture overhaul + Android node)
- MCP extension: Cursor plan `extend_llmlab_mcp` (dev/cluster operations via FastMCP)
