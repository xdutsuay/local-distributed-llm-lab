# LLM Lab System Architecture

## High-Level Overview

LLM Lab is a distributed system designed to coordinate LLM inference tasks across a cluster of local and remote nodes (including mobile devices). It uses **Ray** for actor-based distributed computing, **FastAPI** for the coordinator interface, and **LangGraph** for workflow orchestration.

```mermaid
graph TD
    User[Clients (Web/PWA)] -->|HTTP/WS| Coordinator[Coordinator Node (FastAPI)]
    
    subgraph "Local Cluster (Ray)"
        Coordinator -->|Ray Calls| Planner[Planner Agent]
        Coordinator -->|Ray Calls| WPool[Worker Pool]
        
        WPool -->|Round Robin| Worker1[LLM Worker 1]
        WPool -->|Round Robin| Worker2[LLM Worker 2]
        
        Worker1 -->|Inference| Ollama[Ollama Local]
        Worker2 -->|Inference| Ollama
        
        Worker1 -.->|Read/Write| Cache[(Distributed Cache)]
    end
    
    subgraph "External/Mesh"
        Mobile[Mobile Node] -.->|WS Heartbeat| Coordinator
        Mobile -.->|Task Execution| Coordinator
    end
```

## Core Components

### 1. Coordinator (`coordinator/main.py`)
The central nervous system.
- **Role**: Entry point for all user requests and node registration.
- **Tech**: FastAPI, Uvicorn.
- **Key Functions**:
    - `startup_event()`: Initializes Ray, Tool Registry, and Self-Registration.
    - `/chat`: Main inference endpoint. Triggers `WorkflowManager`.
    - `/ws/join`: WebSocket endpoint for mobile/remote node heartbeats.
    - `coordinator_heartbeat_loop()`: Background task that announces the coordinator itself as a capable node.

### 2. Workflow Orchestration (`coordinator/graph.py`)
Manages the cognitive process of answering queries.
- **Tech**: LangGraph.
- **Flow**:
    1.  **Planner Node**: Decomposes user query into steps.
    2.  **Executor Node**: Iterates through steps.
    3.  **Routing**: Dispatching tasks to the `WorkerPool`.
- **State**: Maintains `AgentState` (plan, results, trade).

### 3. Worker System (`coordinator/worker.py`)
The "muscle" of the system.
- **Tech**: Ray Actors.
- **Capabilities**:
    - **LLM Inference**: Calls Ollama (or other backends).
    - **Tool Execution**: Can execute registered tools (Calculator, Search).
    - **Auto-Detection**: Scans local environment for available models on startup.
- **Caching**: Checks `CacheManager` before performing expensive inference.

### 4. Distributed Caching (`coordinator/cache_manager.py`)
Efficiency layer.
- **Mechanism**: In-memory store (Ray Object Store logic).
- **Key Generation**: `hash(prompt + model + params)`.
- **TTL**: Entries expire after 1 hour (default).

## Request Lifecycle

1.  **User** sends POST request to `/chat`.
2.  **Coordinator** invokes `WorkflowManager.invoke()`.
3.  **Planner** analyzes request and generates a multi-step plan.
4.  **Workflow** enters loop, processing step 1.
5.  **WorkerPool** selects an available `LLMWorker` (Round-Robin).
6.  **Worker** checks **Cache**.
    - *Hit*: Returns cached response immediately.
    - *Miss*: Calls **Ollama** for generation.
7.  **Worker** stores result in Cache.
8.  **Coordinator** aggregates results and returns to User.
