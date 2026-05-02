# Local Distributed LLM Lab: Turn Your Devices into an AI Cluster

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Status: Active](https://img.shields.io/badge/status-active-green.svg)]()
[![Ollama Supported](https://img.shields.io/badge/Ollama-Supported-orange.svg)](https://ollama.com)

**Local Distributed LLM Lab** is a lightweight, distributed cognition framework that orchestrates your local devices (Mac, Windows, Linux, and Mobile) into a unified, collaborative AI cluster. It enables **task-level parallelism** and **heterogeneous agent routing** without relying on cloud APIs.

If your local LLMs are running slow or you want to combine the compute of multiple older devices, LLMLab coordinates task execution seamlessly using Ray and FastAPI.

---

## 🚀 Key Features for Distributed AI

- **Multi-Node Task Parallelism**: Distribute LangGraph workflows across multiple machines in your local network.
- **MicroGPT-Inspired Agents**: Features agent routing (Antigravity, Claude Code, Codex) using bounded contextual documents.
- **Intelligent Load Balancing**: Automatically detects available Ollama models (prioritizing smaller models on limited RAM devices like M1 Macs) to prevent memory swap slowness.
- **Real-Time Observability Dashboard**: Monitor node health, active micro-threads, and task route previews via a beautiful Web UI (`/llmlab`).
- **Cross-Platform Compatibility**: Works seamlessly across macOS, Windows, and Linux.

---

## 🛠 Quick Start Guide

### Prerequisites
- Python 3.12+
- [Ollama](https://ollama.com/) running locally
- Ray (2.53.0+)

### Installation
```bash
git clone https://github.com/xdutsuay/local-distributed-llm-lab.git
cd local-distributed-llm-lab
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Start the Coordinator (Primary Machine)
```bash
./scripts/start_coordinator.sh
# Access the Dashboard at: http://localhost:8000/llmlab
```

### Connect a Worker (Secondary Machine)
```bash
./scripts/start_worker.sh <COORDINATOR_IP>
```

---

## 📦 Download Executable Binary (Beta)
To help diagnose if slowness is hardware-specific, we provide a pre-compiled executable binary in our **[GitHub Releases](../../releases)**. 
Download the executable for your OS and run it instantly without configuring Python environments!

---

## 🏗 System Architecture

LLMLab utilizes a **Coordinator-Worker** topology:
1. **Coordinator**: A central node running FastAPI and LangGraph. It plans tasks and routes them using the agent mesh configurations.
2. **Workers**: Distributed nodes running Ollama (or AirLLM). Workers automatically self-register via a UDP/TCP heartbeat and execute sub-tasks over Ray IPC.

---

## 🤝 Contributing & SEO Tags
Contributions are highly welcome! Whether it's adding support for new inferencing backends like `vLLM` or expanding the mobile PWA features, check out the `tests/` and open issues.

**Keywords:** *Local LLM, Distributed AI, Ray cluster, LangGraph alternative, Self-hosted LLM, Ollama cluster, Multi-agent LLM framework, AI Agent Mesh, Python AI Orchestration.*

## 📜 License
Released under the [MIT License](LICENSE).
