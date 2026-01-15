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
import asyncio
import json
import time
import uuid
import socket
from coordinator.profiler import profile

app = FastAPI(title="LLM Lab Coordinator")

# Initialize Ray (suppress error if already running)
# We MUST use a fixed namespace so workers can find actors
ray.init(address="auto", namespace="llm-lab", ignore_reinit_error=True)

# Globals
workflow_manager = WorkflowManager()
message_bus = RayMessageBus()
registry = NodeRegistry(message_bus)
tool_registry = get_tool_registry()
task_history = [] # List of {"id": str, "prompt": str, "status": str, "timestamp": float}

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
    await registry.start()
    print(f"🔧 Tool Registry initialized with {len(tool_registry.tools)} tools")
    # Start coordinator self-registration
    asyncio.create_task(coordinator_heartbeat_loop())
    print(f"✅ Coordinator registered as node: {coordinator_node_id}")

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
    try:
        start_time = time.time()
        # Route task through LangGraph
        result = await workflow_manager.invoke(request.prompt)
        
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
            
        final_node = "Distributed"
        if trace:
            final_node = trace[-1].get("node_id", "Unknown")

        # Log task
        task_entry = {
            "id": str(uuid.uuid4()),
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
            "composition": composition # Raw dict for frontend charts
        }
        task_history.insert(0, task_entry)
        # Keep only last 100
        if len(task_history) > 100:
            task_history.pop()
            
        response_content = result["results"]
        # Smart Health Check Trigger
        if isinstance(response_content, list) and len(response_content) > 0:
            if "[Mock]" in response_content[0]:
                print("⚠️ Mock response detected. Triggering Health Check.")
                asyncio.create_task(registry.perform_health_check())

        return {
            "response": result["results"], 
            "plan": result["plan"],
            "worker": "distributed-graph"
        }
    except Exception as e:
        task_history.insert(0, {
            "id": str(uuid.uuid4()),
            "prompt": request.prompt,
            "status": "Failed",
            "error": str(e),
            "timestamp": time.time()
        })
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def get_tasks():
    return {"tasks": task_history}

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

@app.post("/api/memo")
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
