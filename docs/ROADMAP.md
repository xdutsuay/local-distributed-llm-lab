# Future Roadmap

This document outlines the planned features for Phases 12 and beyond.

## Phase 12: Advanced Mobile Mesh
**Goal**: Turn any mobile device into a capable compute node.

- [ ] **Task Execution Engine**:
    - Extend PWA to execute JavaScript-based tasks (e.g., `fetch` for web scraping, local data processing).
    - Sandbox execution for security.
- [ ] **Wake Lock Optimization**:
    - Prevent mobile sleep during task execution.
    - Status: API implemented, UI integration needed.
- [ ] **Offline Queuing**:
    - Allow mobile nodes to accept tasks and upload results when connection is restored.

## Phase 13: Vector Memory (Long-term Recall)
**Goal**: Give the cluster long-term memory.

- [ ] **Vector Database**: Integrate ChromaDB or Faiss.
- [ ] **Embedding Worker**: Special worker type for generating semantic embeddings.
- [ ] **RAG Pipeline**:
    - Update `Planner` to query Vector DB before plan generation.
    - Store successful Q&A pairs automatically.

## Phase 14: Data Replication & Fault Tolerance
**Goal**: Enterprise-grade reliability.

- [ ] **Cache Replication**:
    - Using Ray's object replication.
    - Ensure cache hits even if the generator node dies.
- [ ] **State Checkpointing**:
    - Persist LangGraph state to disk (SQLite/Postgres) instead of memory.
    - Allow resuming workflows after coordinator restart.

## Phase 15: Multi-Modal Capabilities
**Goal**: Vision and Audio.

- [ ] **Vision Models**: Integrate LLaVA or BakLLaVA support in Ollama workers.
- [ ] **Image Tools**: Add tools for image generation (Stable Diffusion) or analysis.

## Phase 16: Performance Optimization (Profiling)
**Goal**: Make the system fast.
- [ ] **Profiling**: Instrument the entire pipeline (FastAPI -> Ray -> Worker -> Ollama) to identify bottlenecks.
- [ ] **JIT Compilation**: Use `numba` or `jax` @jit for optimizing critical loops in data processing.
- [ ] **Async Optimization**: Ensure no blocking calls in the async event loop.

