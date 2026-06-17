# lclreason

Local distributed LLM reasoning engine — written in Go.

A sister project to [local-distributed-llm-lab](https://github.com/xdutsuay/local-distributed-llm-lab), rebuilt from scratch with a focus on simplicity, performance, and a single deployable binary.

## Why

| | local-distributed-llm-lab (Python) | lclreason (Go) |
|---|---|---|
| Startup | 3–8 s (Ray init) | ~50 ms |
| Memory per node | 400–800 MB | 20–60 MB |
| Deployment | venv + pip + Ray | `scp lclreason host: && ssh host ./lclreason` |
| Streaming | Bolted on | Native SSE |
| Reasoning chains | LangGraph state machine | YAML-defined, zero-dependency |

## Quick start

```bash
# Prerequisites: Go 1.22+, Ollama running on any node

git clone https://github.com/xdutsuay/lclreason
cd lclreason
cp config.example.yaml config.yaml
make run
# Open http://localhost:8080
```

## Architecture

```
Client
  │ POST /v1/chat/completions  (OpenAI-compatible)
  ▼
Coordinator  ──► Chain Engine (YAML-driven reasoning steps)
  │                   │
  │            Dispatcher (load-aware routing)
  │                   │
  ├── Worker Node 1 (Ollama)
  ├── Worker Node 2 (Ollama)
  └── Worker Node N
```

## Modes

### Coordinator (default)

```bash
./lclreason --mode coordinator --port 8080
```

- Serves the OpenAI-compatible API
- Runs reasoning chains
- Manages node registry, cache, event log
- Serves the dashboard at `http://localhost:8080/`

### Worker

```bash
# On another machine, with Ollama running
./lclreason --mode worker --config config.yaml
# config.yaml must set: coordinator: <coordinator-ip>:8080
```

Workers register with the coordinator and send heartbeats. The coordinator routes inference requests to the least-loaded healthy worker.

## Reasoning chains

Chains are defined in YAML under `chains/`. Two built-in chains:

- **default** — single-step direct answer
- **research** — plan sub-questions, then synthesize

Specify a chain per request:
```json
POST /v1/chat/completions
{"model": "llama3", "chain": "research", "messages": [{"role":"user","content":"Explain quantum entanglement"}]}
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat (+ `chain` field) |
| `GET` | `/v1/models` | Models available across healthy nodes |
| `GET` | `/v1/nodes` | All registered nodes |
| `POST` | `/v1/nodes/register` | Register a worker node |
| `POST` | `/v1/nodes/heartbeat` | Worker heartbeat |
| `DELETE` | `/v1/nodes/{id}` | Deregister a node |
| `GET` | `/v1/events?limit=N` | Recent event log |
| `GET` | `/health` | Cluster health summary |
| `GET` | `/` | Dashboard UI |

## Configuration

```yaml
mode: coordinator
port: 8080
db: lclreason.db
chain:
  dir: chains
  default: default
cache:
  enabled: true
  ttl: 1h
heartbeat: 5s
offline_after: 15s
# coordinator: host:port  # worker mode only
```

## Building

```bash
make build          # current platform
make build-linux    # linux/amd64
make build-arm64    # linux/arm64 (Raspberry Pi, etc.)
make build-mac      # darwin/arm64
```

## License

MIT
