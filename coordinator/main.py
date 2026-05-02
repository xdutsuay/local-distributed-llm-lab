from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import ray
from coordinator.graph import WorkflowManager
from coordinator.registry import NodeRegistry
from coordinator.messaging import RayMessageBus, ClusterEvents
from coordinator.tools.registry import get_tool_registry
from coordinator.worker_pool import AdaptiveWorkerPool
from coordinator.browser_micro import (
    build_browser_microtask_code,
    normalize_browser_contribution,
    summarize_served_by,
)
from coordinator import db
import asyncio
import json
import time
import uuid
import socket
from coordinator.profiler import profile
import os

app = FastAPI(title="LLM Lab Coordinator")

# Initialize Ray (optional for testing)
# Check for test/mock mode before initializing Ray
if not os.getenv("RAY_MOCK_MODE"):
    try:
        ray.init(address="auto", namespace="llm-lab", ignore_reinit_error=True)
        print("✅ Connected to Ray cluster")
    except Exception as e:
        print(f"⚠️  Ray init failed: {e}. Some features may not work.")
        print("   Tip: Start Ray with 'ray start --head' or run in test mode with RAY_MOCK_MODE=1")
else:
    print("🧪 Running in RAY_MOCK_MODE (test environment)")


# Globals
worker_pool = AdaptiveWorkerPool()           # adaptive: local on 1 node, Ray on 2+
workflow_manager = WorkflowManager(worker_pool=worker_pool)
message_bus = RayMessageBus()
registry = NodeRegistry(message_bus)
tool_registry = get_tool_registry()
# task_history kept as a small in-memory cache for fast /api/tasks; DB is the source of truth
task_history: List[Dict[str, Any]] = []

# Coordinator node info for self-registration
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

coordinator_node_id = f"coordinator-{uuid.getnode()}"

async def coordinator_heartbeat_loop():
    """Send heartbeats from coordinator itself so it appears as a node"""
    import os
    while True:
        await asyncio.sleep(5)
        # Self-register coordinator as a worker node
        await message_bus.publish(ClusterEvents.HEARTBEAT, {
            "node_id": coordinator_node_id,
            "capabilities": ["llm_inference", "coordinator", "planner"],
            "model": os.getenv("OLLAMA_MODEL", "auto-detected"),
            "timestamp": time.time(),
            "data_stats": {"sent_bytes": 0},
            "client_ip": get_local_ip(),
            "current_task": "Coordinating",
            "api_base": None
        })

@app.on_event("startup")
async def startup_event():
    # Init SQLite DB first (all other components log to it)
    await db.init_db()
    await registry.start()
    # Wire registry into the pool so @ray_required can read node count
    worker_pool.set_registry(registry)
    print(f"🔧 Tool Registry initialized with {len(tool_registry.tools)} tools")
    asyncio.create_task(coordinator_heartbeat_loop())
    print(f"✅ Coordinator registered as node: {coordinator_node_id}")
    asyncio.create_task(_prewarm_model())
    await db.log_event("startup", coordinator_node_id, {"tools": len(tool_registry.tools)})

async def _prewarm_model():
    """Background task to pre-load the model into VRAM on startup."""
    backend = os.getenv("INFERENCE_BACKEND", "ollama").lower()
    if backend == "airllm":
        print("ℹ️  AirLLM backend selected — model loads lazily on first request, skipping pre-warm.")
        await db.log_event("prewarm", coordinator_node_id, {"backend": "airllm", "status": "skipped"})
        return

    import ollama as _ollama
    from coordinator.worker import detect_available_models
    model = os.getenv("OLLAMA_MODEL") or detect_available_models() or "qwen2.5-coder"
    print(f"🔥 Pre-warming model '{model}' in background...")
    await db.log_event("prewarm", coordinator_node_id, {"model": model, "status": "started"})
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _ollama.chat(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                options={"temperature": 0.1, "num_predict": 1},
                keep_alive="60m"
            )
        )
        print(f"✅ Model '{model}' pre-warmed and ready!")
        await db.log_event("prewarm", coordinator_node_id, {"model": model, "status": "ready"})
    except Exception as e:
        print(f"⚠️  Model pre-warm failed (will still work on first request): {e}")
        await db.log_event("prewarm", coordinator_node_id, {"model": model, "status": "failed", "error": str(e)})


# Mount frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_root():
    # Landing page: redirect to chat UI or serve Worker PWA?
    # Keeping "/" as PWA for now as per Phone instructions.
    return FileResponse('frontend/index.html')

@app.get("/worker.js")
async def read_worker():
    return FileResponse('frontend/worker.js', media_type='application/javascript')

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        # node_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_tasks: Dict[str, asyncio.Future] = {}

    async def connect(self, node_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[node_id] = websocket
        print(f"🔌 Node connected: {node_id}")

    def disconnect(self, node_id: str):
        if node_id in self.active_connections:
            del self.active_connections[node_id]
            print(f"🔌 Node disconnected: {node_id}")

    async def send_personal_message(self, message: dict, node_id: str):
        if node_id in self.active_connections:
            await self.active_connections[node_id].send_text(json.dumps(message))
            return True
        return False

    def resolve_task_result(self, message: Dict[str, Any]) -> bool:
        task_id = message.get("task_id")
        future = self.pending_tasks.pop(task_id, None)
        if not future or future.done():
            return False
        future.set_result(message)
        return True

    def connected_node_ids(self) -> List[str]:
        return list(self.active_connections.keys())

    async def dispatch_task(
        self,
        node_id: str,
        code: str,
        timeout_seconds: float = 4.0,
    ) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())
        payload = {
            "type": ClusterEvents.EXECUTE_TASK,
            "task_id": task_id,
            "code": code,
            "timestamp": time.time(),
        }

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_tasks[task_id] = future

        success = await self.send_personal_message(payload, node_id)
        if not success:
            self.pending_tasks.pop(task_id, None)
            return {
                "task_id": task_id,
                "node_id": node_id,
                "status": "offline",
                "response": None,
                "error": "Node not connected via WebSocket",
            }

        try:
            result = await asyncio.wait_for(future, timeout=timeout_seconds)
            result["node_id"] = node_id
            return result
        except asyncio.TimeoutError:
            self.pending_tasks.pop(task_id, None)
            return {
                "task_id": task_id,
                "node_id": node_id,
                "status": "timeout",
                "response": None,
                "error": "Timed out waiting for browser node result",
            }

manager = ConnectionManager()

@app.websocket("/ws/join")
async def websocket_endpoint(websocket: WebSocket):
    # We wait for the first message to identify the node
    # Or we accept and wait for heartbeat?
    # Let's accept first
    await websocket.accept()
    node_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Extract Node ID from heartbeat/message
            if "node_id" in message and node_id is None:
                node_id = message["node_id"]
                # Register in manager (hacky: we accepted above, but now we store map)
                manager.active_connections[node_id] = websocket
                print(f"🔌 Registered WS for node: {node_id}")

            # Inject client IP
            if websocket.client:
                message["client_ip"] = websocket.client.host
            
            # Handle Message Types
            if "response" in message and "task_id" in message:
                # This is a Task Result
                print(f"📩 Received Task Result from {node_id}: {message['task_id']}")
                manager.resolve_task_result(message)
                await message_bus.publish(ClusterEvents.TASK_RESULT, message)
            else:
                # Assume Heartbeat
                await message_bus.publish(ClusterEvents.HEARTBEAT, message)
                
    except WebSocketDisconnect:
        if node_id:
            manager.disconnect(node_id)
    except Exception as e:
        print(f"WS Error: {e}")
        if node_id:
            manager.disconnect(node_id)



class ChatRequest(BaseModel):
    prompt: str
    client_id: str = "unknown"
    model: str = "llama3.2"


async def collect_browser_micro_contributions(prompt: str) -> List[Dict[str, Any]]:
    browser_nodes = registry.get_nodes_with_capability("javascript_execution")
    if not browser_nodes:
        return []

    code = build_browser_microtask_code(prompt)
    tasks = [
        manager.dispatch_task(node_id, code)
        for node_id in browser_nodes.keys()
        if node_id in manager.active_connections
    ]
    if not tasks:
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)
    normalized: List[Dict[str, Any]] = []
    for result in results:
        if isinstance(result, Exception):
            normalized.append({
                "node_id": "unknown",
                "status": "error",
                "kind": "browser_microgpt",
                "summary": "",
                "keywords": [],
                "clauses": [],
                "error": str(result),
            })
            continue
        normalized.append(normalize_browser_contribution(result.get("node_id", "unknown"), result))
    return normalized

@app.get("/api/nodes")
async def get_nodes_json():
    return {"active_nodes": registry.get_active_nodes()}

@app.get("/llmlab")
async def get_dashboard():
    return FileResponse('frontend/dashboard.html')

@app.get("/nodes")
async def get_nodes_html():
    # Backward compatibility / Redirect
    return FileResponse('frontend/dashboard.html')

@app.get("/chat_ui")
async def get_chat_ui():
    return FileResponse('frontend/chat.html')

@app.post("/chat")
@profile
async def chat(request: ChatRequest):
    browser_contrib_task = None
    try:
        start_time = time.time()
        browser_contrib_task = asyncio.create_task(collect_browser_micro_contributions(request.prompt))
        # Route task through LangGraph
        result = await workflow_manager.invoke(request.prompt)
        browser_contributions = await browser_contrib_task
        
        # Parse plan for route details
        plan = result.get("plan", [])
        route_summary = f"{len(plan)} Steps"
        route_details = [
            {"step": s.get("step_id"), "desc": s.get("description"), "node": s.get("worker_type")} 
            for s in plan
        ]
        
        # Parse trace for composition
        trace = result.get("execution_trace", [])
        composition = {}
        total_time = 0
        for step in trace:
            nid = step.get("node_id", "unknown")
            dur = step.get("duration", 0)
            composition[nid] = composition.get(nid, 0) + dur
            total_time += dur
            
        # Format composition as string "NodeA(60%), NodeB(40%)"
        comp_str = "Single Node"
        if total_time > 0:
            parts = []
            for nid, dur in composition.items():
                pct = int((dur / total_time) * 100)
                parts.append(f"{nid.split('-')[-1]}:{pct}%")
            comp_str = ", ".join(parts)
            
        final_node = "local-worker"
        if trace:
            final_node = trace[-1].get("node_id", "Unknown")

        # Persist task to SQLite DB (source of truth)
        task_id = str(uuid.uuid4())
        task_entry = {
            "id": task_id,
            "client_id": request.client_id,
            "prompt": request.prompt,
            "status": "Success",
            "timestamp": start_time,
            "duration": time.time() - start_time,
            "plan_steps": len(plan),
            "route_summary": comp_str if len(composition) > 1 else (plan[-1].get("worker_type") if plan else "Planner"),
            "route_details": trace if trace else route_details,
            "final_node": final_node,
            "worker": result.get("worker", "unknown"),
            "composition": composition
        }
        asyncio.create_task(db.upsert_task(task_entry))  # non-blocking write
        # Keep small in-memory cache for immediate reads (last 20)
        task_history.insert(0, task_entry)
        if len(task_history) > 20:
            task_history.pop()

        response_content = result["results"]
        if isinstance(response_content, list) and len(response_content) > 0:
            if "[Mock]" in response_content[0]:
                print("⚠️ Mock response detected. Triggering Health Check.")
                asyncio.create_task(registry.perform_health_check())

        return {
            "response": result["results"],
            "plan": result["plan"],
            "worker": "distributed-graph",
            "browser_contributions": browser_contributions,
            "served_by": summarize_served_by(final_node, browser_contributions),
        }
    except Exception as e:
        if browser_contrib_task is not None and not browser_contrib_task.done():
            browser_contrib_task.cancel()
        err_entry = {
            "id": str(uuid.uuid4()),
            "prompt": request.prompt,
            "status": "Failed",
            "error": str(e),
            "timestamp": time.time()
        }
        asyncio.create_task(db.upsert_task(err_entry))
        asyncio.create_task(db.log_event("error", "coordinator", {"prompt": request.prompt, "error": str(e)}))
        task_history.insert(0, err_entry)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def get_tasks():
    """Return persistent task history from SQLite (survives restarts)."""
    tasks = await db.get_tasks(limit=100)
    return {"tasks": tasks}

@app.get("/api/events")
async def get_events(event_type: Optional[str] = None, limit: int = 200):
    """Return operational event log — useful for debugging stuck requests."""
    events = await db.get_events(limit=limit, event_type=event_type)
    return {"events": events}

@app.get("/health")
def health():
    return {"status": "ok", "ray_status": ray.is_initialized()}

# --- Shared Clipboard / Memo ---
memo_storage = []

class MemoRequest(BaseModel):
    text: str

@app.get("/memo")
async def get_memo_ui():
    return FileResponse('frontend/memo.html')

@app.get("/api/memo")
async def get_memos():
    return {"memos": memo_storage}

@app.post("/api/memo")
async def add_memo(req: MemoRequest):
    memo_storage.insert(0, {
        "text": req.text, 
        "time": time.strftime("%H:%M:%S")
    })
    if len(memo_storage) > 50: 
        memo_storage.pop()
    return {"status": "ok"}

# --- Tool Execution API ---
@app.get("/api/tools")
async def get_tools():
    """List all available tools"""
    return {
        "tools": tool_registry.list_tools(),
        "stats": tool_registry.get_stats()
    }

class ToolExecuteRequest(BaseModel):
    tool_name: str
    parameters: dict = {}

@app.post("/api/tools/execute")
async def execute_tool(req: ToolExecuteRequest):
    """Execute a tool directly"""
    result = await tool_registry.execute_tool(req.tool_name, **req.parameters)
    return {
        "tool": req.tool_name,
        "success": result.success,
        "output": result.output,
        "error": result.error
    }

# --- Mobile Task Dispatch API (Phase 12) ---
class MobileTaskRequest(BaseModel):
    node_id: str
    code: str # JavaScript code to execute
    
@app.post("/api/mobile/task")
async def dispatch_mobile_task(req: MobileTaskRequest):
    """Manually dispatch a JS task to a connected mobile node"""
    task_id = str(uuid.uuid4())
    payload = {
        "type": ClusterEvents.EXECUTE_TASK,
        "task_id": task_id,
        "code": req.code,
        "timestamp": time.time()
    }
    
    success = await manager.send_personal_message(payload, req.node_id)
    if not success:
        raise HTTPException(status_code=404, detail="Node not connected via WebSocket")
        
    return {"status": "dispatched", "task_id": task_id}


# --- Memory API (Phase 13) ---
class MemoryItem(BaseModel):
    text: str
    metadata: Dict[str, Any] = {}

@app.post("/api/memory")
async def add_memory(item: MemoryItem):
    """Add a new item to the vector memory"""
    from coordinator.memory import get_vector_store
    store = get_vector_store()
    store.add(documents=[item.text], metadatas=[item.metadata])
    return {"status": "stored", "count": store.count()}

# --- Cache Management API ---
@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    from coordinator.cache_manager import get_cache_manager
    cache = get_cache_manager()
    return cache.get_stats()

@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all cache entries"""
    from coordinator.cache_manager import get_cache_manager
    cache = get_cache_manager()
    cache.clear()
    return {"status": "cleared"}

# --- Model Management API (Phase 17) ---
@app.get("/api/nodes/{node_id}/models")
async def list_node_models(node_id: str):
    """List available models on a specific node"""
    try:
        # Special handling for coordinator (not a Ray actor)
        if "coordinator" in node_id:
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                models = [line.split()[0].split(':')[0] for line in lines[1:] if line.strip()]
                return {"node_id": node_id, "models": models}
            return {"node_id": node_id, "models": []}

        # 1. Try to get Ray actor
        actor = ray.get_actor(node_id)
        models = await actor.list_models.remote()
        return {"node_id": node_id, "models": models}
    except ValueError:
        raise HTTPException(status_code=404, detail="Node not found or does not support model listing")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ModelSwapRequest(BaseModel):
    model: str

@app.post("/api/nodes/{node_id}/model")
async def swap_node_model(node_id: str, request: ModelSwapRequest):
    """Swap model on a specific node"""
    try:
        verification = "No verification output"
        
        # Special handling for coordinator
        if "coordinator" in node_id:
             # Just verify it exists basically, no "swap" needed for Ollama service unless we track it
             # But we can run `ollama ps` to verify
             import subprocess
             # We can try to 'pull' or 'run' in background to ensure it's loaded?
             # For now, just listing ps is enough verification
             # Coordinator "swapping" just means updating the registry record really, 
             # as the Planner will use the model specified in the request/registry.
             ver_proc = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
             verification = ver_proc.stdout
        else:
            # Get Ray actor
            worker = ray.get_actor(node_id)
            result = await worker.swap_model.remote(request.model)
            verification = result.get("verification", "No verification output")
        
        # Update registry
        registry.update_node_model(node_id, request.model)
        
        return {"status": "ok", "model": request.model, "verification": verification}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/nodes/{node_id}/restart")
async def restart_node(node_id: str):
    """Restart a specific node (Ray Actor)"""
    try:
        if "coordinator" in node_id:
             raise HTTPException(status_code=400, detail="Cannot restart coordinator via API.")
             
        actor = ray.get_actor(node_id)
        ray.kill(actor)
        return {"status": "ok", "message": f"Node {node_id} killed. Ray should auto-restart if configured."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart node: {e}")

@app.post("/api/cache/cleanup")
async def cleanup_cache():
    """Remove expired cache entries"""
    from coordinator.cache_manager import get_cache_manager
    cache = get_cache_manager()
    removed = cache.cleanup_expired()
    return {"status": "ok", "removed": removed}
