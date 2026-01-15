# LLM Lab Documentation Plan

## Phase 1: Foundation & Git History (Immediate)
- **Repo Analysis**: Complete reading of current codebase.
- **Git History**: Create `commits.txt` mapping evolution.
- **Documentation Plan**: This document.

## Phase 2: System Architecture (The "Big Picture")
**Deliverable**: `docs/ARCHITECTURE.md`
**Content**:
1. **High-Level Diagram**: Mermaid chart showing User -> Coordinator (FastAPI) -> Planner (LangGraph) -> Worker Pool (Ray) -> Ollama.
2. **Component Interactions**:
    - **Message Bus**: How Ray actors communicate (Heartbeats).
    - **Workflow Engine**: State graph flow (Plan -> Execute -> Loop).
    - **Data Flow**: Request lifecycle from UI to LLM and back.
3. **Network Topology**: Logic flow between Mobile Nodes, Local Cluster, and Clients.

## Phase 3: Detailed Component Documentation
**Deliverable**: `docs/COMPONENTS.md`
**Content**:
1. **Coordinator (`main.py`, `registry.py`)**:
    - Startup sequence (Ray init, Registry start).
    - API Endpoints Table (Method, URL, Purpose).
    - WebSocket Protocol for Node Mesh.
2. **Workers & Execution (`worker.py`, `worker_pool.py`)**:
    - Initialization & Model Auto-detection logic.
    - `generate()` flow: Cache Check -> API Call -> Cache Store.
    - **Tool Execution Framework**: How workers dynamically load and run tools.
3. **Caching Strategy (`cache_manager.py`)**:
    - Key generation algorithm.
    - TTL and Eviction mechanics.
4. **Resiliency Patterns**:
    - Retry logic for failed LLM calls.
    - Worker health checks.

## Phase 4: Testing & Quality Assurance
**Deliverable**: `docs/TESTING.md` (Already partially exists)
**Content**:
- **Unit Testing Strategy**: Guide to `tests/`.
- **E2E Testing Framework**: Selenium setup and usage (`tests/e2e/`).
- **Manual Verification Scripts**: Step-by-step generic test plans.

## Phase 5: Future Roadmap (Phase 12+)
**Deliverable**: `docs/ROADMAP.md`
**Content**:
- **Mobile Mesh**: Full implementation details for PWA task execution.
- **Vector Memory**: Design for long-term RAG integration.
- **Data Replication**: Fault tolerance strategy.


## Documentation Structure
We will create a central `docs/` directory with:
- `docs/ARCHITECTURE.md`
- `docs/API_REFERENCE.md`
- `docs/WORKFLOWS.md`
- `docs/TESTING.md`
