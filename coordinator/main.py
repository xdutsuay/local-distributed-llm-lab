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

app = FastAPI(title="LLM Lab Coordinator")

# Initialize Ray (suppress error if already running)
ray.init(ignore_reinit_error=True)

# Globals
workflow_manager = WorkflowManager()
message_bus = RayMessageBus()
registry = NodeRegistry(message_bus)

@app.on_event("startup")
async def startup_event():
    await registry.start()

# Mount frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_root():
    return FileResponse('frontend/index.html')

@app.websocket("/ws/join")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # Assuming message contains 'type' or just treating all as heartbeats for now
            # if message.get("type") == "heartbeat":
            # Republish to internal bus
            await message_bus.publish(ClusterEvents.HEARTBEAT, message)
    except WebSocketDisconnect:
        # Handle disconnect if needed (NodeRegistry auto-expires via TTL)
        pass
    except Exception as e:
        print(f"WS Error: {e}")


class ChatRequest(BaseModel):
    prompt: str
    model: str = "llama3.2"

@app.get("/api/nodes")
async def get_nodes_json():
    return {"active_nodes": registry.get_active_nodes()}

@app.get("/nodes")
async def get_nodes_html():
    return FileResponse('frontend/nodes.html')

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Route task through LangGraph
        result = await workflow_manager.invoke(request.prompt)
        return {
            "response": result["results"], 
            "plan": result["plan"],
            "worker": "distributed-graph"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok", "ray_status": ray.is_initialized()}
