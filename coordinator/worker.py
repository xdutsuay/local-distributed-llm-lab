import ray
import time
import asyncio
import uuid
from typing import Dict, Any, List
from coordinator.messaging import RayMessageBus, ClusterEvents
import socket
import ollama

@ray.remote
class LLMWorker:
    def __init__(self, model_name: str = "llama3.2", api_base: str = None):
        self.model_name = model_name
        self.api_base = api_base  # e.g., "http://192.168.1.5:1234/v1"
        # Stable ID based on MAC address
        self.node_id = f"worker-{uuid.getnode()}"
        self.bus = None
        self.running = True
        self.generated_bytes = 0
        self.ip = self._get_ip()
        self.last_task = "Idle"
        # Start heartbeat loop
        asyncio.create_task(self._heartbeat_loop())

    # ... (keep _get_ip and _heartbeat_loop same) ...

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
                "current_task": self.last_task,
                "api_base": self.api_base
            }
            await self.bus.publish(ClusterEvents.HEARTBEAT, msg)
            await asyncio.sleep(5)

    async def generate(self, prompt: str) -> str:
        self.last_task = f"Processing: {prompt[:20]}..."
        
        try:
            # 1. External OpenAI-compatible API (e.g., LM Studio)
            if self.api_base:
                import requests
                response = requests.post(
                    f"{self.api_base}/chat/completions", 
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    resp = response.json()['choices'][0]['message']['content']
                    self.generated_bytes += len(resp.encode('utf-8'))
                    self.last_task = "Idle"
                    return resp
                else:
                    raise Exception(f"API Error: {response.text}")

            # 2. Local Ollama
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'user', 'content': prompt},
            ])
            resp = response['message']['content']
            self.generated_bytes += len(resp.encode('utf-8'))
            self.last_task = "Idle"
            return resp
            
        except Exception as e:
            error_str = str(e)
            if "not found" in error_str or "pull" in error_str:
                print(f"Model {self.model_name} not found. Attempting to pull...")
                try:
                    ollama.pull(self.model_name)
                    # Retry once
                    response = ollama.chat(model=self.model_name, messages=[
                        {'role': 'user', 'content': prompt},
                    ])
                    resp = response['message']['content']
                    self.generated_bytes += len(resp.encode('utf-8'))
                    self.last_task = "Idle"
                    return resp
                except Exception as pull_error:
                    print(f"Pull failed: {pull_error}")

            print(f"Ollama inference failed: {e}. Falling back to mock.")
            # Fallback mock implementation
            resp = f"[Mock] Response from {self.model_name} (Node: {self.node_id}) to prompt: '{prompt}'"
            self.generated_bytes += len(resp.encode('utf-8'))
            await asyncio.sleep(2)
            self.last_task = "Idle"
            return resp
