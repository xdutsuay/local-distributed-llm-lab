import ray
import time
import asyncio
import uuid
import socket
import ollama
from typing import Dict, Any, List

# Define messaging helper locally to avoid module dependency issues on remote side
class RayMessageBus:
    def __init__(self):
        try:
            self.backend = ray.get_actor("RayBusBackend")
        except Exception as e:
            print(f"Could not find RayBusBackend: {e}")
            self.backend = None

    async def publish(self, topic: str, message: Dict[str, Any]):
        if self.backend:
            # Send raw string for topic to avoid pickle issues/Enums
            self.backend.publish.remote(topic, message)

@ray.remote
class LLMWorker:
    def __init__(self, model_name: str = "llama3.2", api_base: str = None):
        self.model_name = model_name
        self.api_base = api_base  # e.g., "http://192.168.1.5:1234/v1"
        self.node_id = f"worker-{uuid.getnode()}"
        self.bus = None
        self.running = True
        self.generated_bytes = 0
        self.ip = self._get_ip()
        self.last_task = "Idle"
        asyncio.create_task(self._heartbeat_loop())

    def _get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    async def _heartbeat_loop(self):
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
            # Use raw string "heartbeat"
            if self.bus:
                 await self.bus.publish("heartbeat", msg)
            await asyncio.sleep(5)

    async def generate(self, prompt: str) -> str:
        self.last_task = f"Processing: {prompt[:20]}..."
        
        try:
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

if __name__ == "__main__":
    import argparse
    import os
    import sys

    # Ensure CWD is in path for module resolution
    sys.path.append(os.getcwd())

    parser = argparse.ArgumentParser(description="Start LLM Worker")
    parser.add_argument("--address", type=str, help="Ray Cluster Address (e.g. 192.168.1.5:6379)")
    
    args = parser.parse_args()
    
    print("Initializing Ray...")
    # Force execution on THIS node (Secondary)
    import ray.util
    # Connect...
    if args.address:
        print(f"Connecting to Ray Cluster at {args.address}...")
        try:
            ray.init(address=args.address, ignore_reinit_error=True)
        except Exception as e:
             print(f"Connection failed: {e}")
             ray.init(address='auto', ignore_reinit_error=True)
    else:
        ray.init(address='auto')
        
    current_ip = ray.util.get_node_ip_address()
    print(f"Targeting Local Node IP: {current_ip}")

    # Spawn worker
    try:
        worker = LLMWorker.options(resources={f"node:{current_ip}": 0.001}).remote() 
        print(f"Worker running (Ref: {worker})")
        print("Press Ctrl+C to exit.")
    
        # Keep alive
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("Shutting down...")
