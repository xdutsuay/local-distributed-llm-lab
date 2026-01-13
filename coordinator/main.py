from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import ray
from coordinator.graph import WorkflowManager
from coordinator.registry import NodeRegistry
from coordinator.messaging import RayMessageBus, ClusterEvents
import asyncio
import json
import time
import uuid

app = FastAPI(title="LLM Lab Coordinator")

# Initialize Ray (suppress error if already running)
ray.init(ignore_reinit_error=True)

# Globals
workflow_manager = WorkflowManager()
message_bus = RayMessageBus()
registry = NodeRegistry(message_bus)
task_history = [] # List of {"id": str, "prompt": str, "status": str, "timestamp": float}

@app.on_event("startup")
async def startup_event():
    await registry.start()

# Mount frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_root():
    # Landing page: redirect to chat UI or serve Worker PWA?
    # Keeping "/" as PWA for now as per Phone instructions.
    return FileResponse('frontend/index.html')

@app.websocket("/ws/join")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # Inject client IP
            if websocket.client:
                message["client_ip"] = websocket.client.host
            
            # Republish to internal bus
            await message_bus.publish(ClusterEvents.HEARTBEAT, message)
    except WebSocketDisconnect:
        # Handle disconnect if needed (NodeRegistry auto-expires via TTL)
        pass
    except Exception as e:
        print(f"WS Error: {e}")


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
        
        final_node = "Distributed"
        if plan:
            final_node = plan[-1].get("worker_type", "Unknown")

        # Log task
        task_entry = {
            "id": str(uuid.uuid4()),
            "client_id": request.client_id,
            "prompt": request.prompt,
            "status": "Success",
            "timestamp": start_time,
            "duration": time.time() - start_time,
            "plan_steps": len(plan),
            "route_summary": route_summary,
            "route_details": route_details,
            "final_node": final_node,
            "worker": result.get("worker", "unknown")
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

