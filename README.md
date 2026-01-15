# Local Distributed LLM Lab

**A distributed cognition framework for local AI experiments.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12.2-blue.svg)
![Status](https://img.shields.io/badge/status-active-green.svg)
![Tests](https://img.shields.io/badge/tests-27%2F43%20passing-green.svg)

## 🚀 Overview
**Local Distributed LLM Lab** orchestrates multiple local devices—laptops, desktops, and mobile phones—into a single collaborative AI cluster. Instead of sharding model weights, it focuses on **task-level parallelism** and **heterogeneous agents**.

A Planner LLM decomposes complex queries into subtasks, which are routed to the most appropriate worker node.

## ✨ Current Features

### Core Capabilities
- ✅ **Distributed Coordination** - Powered by Ray and FastAPI
- ✅ **Multi-Node Support** - macOS ↔ Windows cross-platform
- ✅ **Task Attribution** - Track which node processed each task
- ✅ **Heartbeat System** - Auto-registration and TTL expiration
- ✅ **Agentic Workflow** - LangGraph task decomposition
- ✅ **Test Coverage** - 43 tests (27 passing, 16 future stubs)

### Interfaces
- 📊 **Dashboard** (`/llmlab`) - Real-time cluster status
- 💬 **Chat UI** (`/chat_ui`) - Query interface
- 📋 **Shared Clipboard** (`/memo`) - Cross-machine text transfer

## 🏗 Architecture

```
┌─────────────────────────────────────────────┐
│         Coordinator Node (Mac)              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ FastAPI  │  │ LangGraph│  │Ray Head   │ │
│  │ Planner  │  │ Workflow │  │Registry   │ │
│  └──────────┘  └──────────┘  └───────────┘ │
└─────────────────────────────────────────────┘
           │                    │
    Heartbeats (5s)      Task Distribution
           │                    │
    ┌──────┴────────┬───────────┴──────┐
    │               │                  │
┌───▼────┐    ┌────▼─────┐    ┌───────▼────┐
│Worker 1│    │ Worker 2 │    │ Mobile PWA │
│(Ollama)│    │ (Ollama) │    │ (planned)  │
└────────┘    └──────────┘    └────────────┘
```

## 🛠 Quick Start

### Prerequisites
- Python 3.12.2
- [Ollama](https://ollama.com/) running locally
- Ray 2.53.0+

### Installation
```bash
git clone https://github.com/xdutsuay/local-distributed-llm-lab.git
cd local-distributed-llm-lab
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Start Coordinator (Machine 1)
```bash
./scripts/start_coordinator.sh
# Dashboard: http://localhost:8000/llmlab
```

### Connect Worker (Machine 2)
```bash
./scripts/start_worker.sh <COORDINATOR_IP>
```

### Health Check
```bash
python scripts/health_check.py
```

## 🧪 Testing
```bash
# All tests
python -m pytest tests/

# Active tests only
python -m pytest tests/ -k "not skip"
```

## 📁 Project Structure
```
LLMLAB/
├── coordinator/      # Core orchestration (main, graph, worker, registry)
├── frontend/         # HTML/JS interfaces  
├── tests/           # 43 tests (routes, heartbeat, cluster, etc.)
├── scripts/         # Startup & diagnostic utilities
├── config/          # Configuration files
├── docs/            # Documentation
└── archive/         # Historical files
```

## 🗺 Roadmap

### Completed
- [x] Multi-node distributed execution
- [x] LangGraph task orchestration
- [x] Node registry & health monitoring
- [x] Task attribution & composition
- [x] Comprehensive test suite
- [x] **Phase 10**: Prompt passing fix, round-robin load balancing, auto-detect Ollama model

### In Progress (Phase 11)
- [ ] Mobile mesh integration
- [ ] Tool execution framework
- [ ] Distributed caching & replication

### Planned
- [ ] **Phase 12**: Observability (timeline, metrics dashboard)
- [ ] **Phase 13**: Advanced scheduling strategies

## 🔧 Configuration

### Environment Variables
```bash
export OLLAMA_MODEL=llama3.2  # Or mistral, gemma:2b, etc.
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
```

### Ray Namespace
All nodes must connect to namespace: `llm-lab`

## 🤝 Contributing
Contributions welcome! See active issues and test coverage in `tests/`.

## 📜 License
MIT License.
