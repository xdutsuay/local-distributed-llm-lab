import ray
import time
import asyncio
import uuid
import socket
import ollama
import subprocess
from typing import Dict, Any, List, Optional
from coordinator.profiler import profile

def detect_available_models() -> Optional[str]:
    """
    Detect available Ollama models by running 'ollama list'.
    Returns the first available model name, or None if detection fails.
    """
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Skip header line and get first model
            for line in lines[1:]:
                if line.strip():
                    # Model name is the first column
                    model_name = line.split()[0]
                    if ':' in model_name:
                        # Remove tag suffix (e.g., "llama3.2:latest" -> "llama3.2")
                        model_name = model_name.split(':')[0]
                    print(f"✓ Auto-detected Ollama model: {model_name}")
                    return model_name
        
        print("⚠️ No Ollama models found via 'ollama list'")
        return None
        
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"⚠️ Ollama detection failed: {e}")
        return None

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
    def __init__(self, node_id: str, model_name: str = None, api_base: str = None):
        import os
        # Fallback chain: explicit param → env var → auto-detect → default
        if model_name:
            self.model_name = model_name
        elif os.getenv("OLLAMA_MODEL"):
            self.model_name = os.getenv("OLLAMA_MODEL")
        else:
            detected = detect_available_models()
            self.model_name = detected if detected else "llama3.2"
            if not detected:
                print(f"ℹ️ Using default model: {self.model_name}")
        self.api_base = api_base  # e.g., "http://192.168.1.5:1234/v1"
        self.node_id = node_id
        self.bus = None
        self.running = True
        self.generated_bytes = 0
        self.ip = self._get_ip()
        self.last_task = "Idle"
        asyncio.create_task(self._heartbeat_loop())

    def list_models(self) -> List[str]:
        """List available models on this node"""
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                return [line.split()[0].split(':')[0] for line in lines[1:] if line.strip()]
            return []
        except Exception as e:
            return [f"Error: {e}"]

    async def swap_model(self, target_model: str) -> Dict[str, Any]:
        """Swap to a different model and verify"""
        self.last_task = f"Swapping to {target_model}..."
        print(f"🔄 Swapping model on {self.node_id} to {target_model}")
        
        try:
            # 1. Pull/Load (Ollama auto-pulls on chat, but let's be explicit if needed)
            # For now, we trust ollama run/chat to pull.
            
            # 2. Update state
            self.model_name = target_model
            
            # 3. Force Load / Verify
            # Simple ping to force model load
            try:
                ollama.chat(model=self.model_name, messages=[{'role': 'user', 'content': 'ping'}], keep_alive='5m')
            except Exception as e:
                pass # Trigger load
                
            # 4. Verification Command
            verify_cmd = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
            
            self.last_task = "Idle"
            return {
                "status": "ok", 
                "current_model": self.model_name,
                "verification": verify_cmd.stdout
            }
        except Exception as e:
            self.last_task = "Error Swapping"
            return {"status": "error", "error": str(e)}

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

    @profile
    async def generate(self, prompt: str) -> str:
        self.last_task = f"Processing: {prompt[:20]}..."
        
        # Import cache manager
        from coordinator.cache_manager import get_cache_manager
        cache = get_cache_manager()
        
        # Check cache first
        cached_response = cache.get(prompt, self.model_name)
        if cached_response:
            return {
                "content": cached_response,
                "node_id": self.node_id,
                "model": self.model_name,
                "timestamp": time.time(),
                "cached": True
            }
        
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
                    
                    # Cache successful response
                    cache.put(prompt, self.model_name, resp)
                    
                    return resp
                else:
                    raise Exception(f"API Error: {response.text}")

            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'user', 'content': prompt},
            ], keep_alive='60m') # Keep model loaded for 60 minutes
            resp = response['message']['content']
            
            # Cache successful response
            cache.put(prompt, self.model_name, resp)
            
            # Return rich object
            return {
                "content": resp,
                "node_id": self.node_id,
                "model": self.model_name,
                "timestamp": time.time(),
                "cached": False
            }
            
        except Exception as e:
            error_str = str(e)
            if "not found" in error_str or "pull" in error_str:
                # ... (keep existing retry logic, but wrap return)
                try: 
                    ollama.pull(self.model_name)
                    # Retry once
                    response = ollama.chat(model=self.model_name, messages=[
                         {'role': 'user', 'content': prompt},
                    ])
                    resp = response['message']['content']
                    self.generated_bytes += len(resp.encode('utf-8'))
                    self.last_task = "Idle"
                    
                    # Cache successful response
                    cache.put(prompt, self.model_name, resp)
                    
                    return {
                        "content": resp,
                        "node_id": self.node_id,
                        "model": self.model_name,
                        "timestamp": time.time(),
                        "cached": False
                    }
                except Exception as pull_error:
                    print(f"Pull failed: {pull_error}")

            print(f"Ollama inference failed: {e}. Falling back to mock.")
            # Fallback mock implementation
            resp = f"[Mock] Response from {self.model_name} (Node: {self.node_id}) to prompt: '{prompt}'"
            self.generated_bytes += len(resp.encode('utf-8'))
            await asyncio.sleep(2)
            self.last_task = "Idle"
            return {
                "content": resp,
                "node_id": self.node_id,
                "model": self.model_name,
                "timestamp": time.time(),
                "cached": False
            }

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
            ray.init(address=args.address, namespace="llm-lab", ignore_reinit_error=True)
        except Exception as e:
             print(f"Connection failed: {e}")
             ray.init(address='auto', namespace="llm-lab", ignore_reinit_error=True)
    else:
        ray.init(address='auto', namespace="llm-lab", ignore_reinit_error=True)
        
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
