import ray
import time
import asyncio
import uuid
from typing import Dict, Any, List
from coordinator.messaging import RayMessageBus, ClusterEvents
import socket

@ray.remote
class LLMWorker:
    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name
        # Stable ID based on MAC address
        self.node_id = f"worker-{uuid.getnode()}"
        self.bus = None
        self.running = True
        self.generated_bytes = 0
        self.ip = self._get_ip()
        self.last_task = "Idle"
        # Start heartbeat loop
        asyncio.create_task(self._heartbeat_loop())

    def _get_ip(self):
        try:
            # Dummy connection to determine local interface IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def _heartbeat_loop(self):
        # Initialize bus connection
        self.bus = RayMessageBus()
        while self.running:
            msg = {
                "node_id": self.node_id,
                "capabilities": ["llm_inference", "tool_execution"],
                "model": self.model_name,
                "timestamp": time.time(),
                "data_stats": {"sent_bytes": self.generated_bytes},
                "client_ip": self.ip,
                "current_task": self.last_task
            }
            await self.bus.publish(ClusterEvents.HEARTBEAT, msg)
            await asyncio.sleep(5)

    async def generate(self, prompt: str) -> str:
        # Mock implementation for Phase 1
        self.last_task = f"Processing: {prompt[:20]}..."
        resp = f"Response from {self.model_name} (Node: {self.node_id}) to prompt: '{prompt}'"
        self.generated_bytes += len(resp.encode('utf-8'))
        
        # Simulate work
        await asyncio.sleep(2)
        self.last_task = "Idle"
        return resp
