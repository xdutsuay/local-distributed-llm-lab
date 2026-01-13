import ray
import asyncio
import uuid
import time
from coordinator.messaging import RayMessageBus, ClusterEvents

@ray.remote
class LLMWorker:
    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name
        self.node_id = str(uuid.uuid4())
        self.bus = None
        self.running = True
        # Start heartbeat loop
        asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        # Initialize bus connection
        self.bus = RayMessageBus()
        while self.running:
            msg = {
                "node_id": self.node_id,
                "capabilities": ["llm_inference", "tool_execution"],
                "model": self.model_name,
                "timestamp": time.time()
            }
            await self.bus.publish(ClusterEvents.HEARTBEAT, msg)
            await asyncio.sleep(5)

    def generate(self, prompt: str) -> str:
        # Mock implementation for Phase 1
        return f"Response from {self.model_name} (Node: {self.node_id}) to prompt: '{prompt}'"
