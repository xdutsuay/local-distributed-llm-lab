# Connecting a Remote LM Studio Node

You can easily integrate a second laptop running [LM Studio](https://lmstudio.ai/) into your **LLM Lab** cluster.

## Prerequisites
- **Laptop 1 (Coordinator)**: Running the `LLM Lab` Coordinator.
- **Laptop 2 (Worker)**: Running `LM Studio` with any model loaded.
- Both laptops must be on the **same Wi-Fi/LAN**.

## Step 1: Configure LM Studio (Laptop 2)
1.  Open LM Studio.
2.  Go to the **Server (⇄)** tab.
3.  Start the Server.
4.  **Important**: Ensure "Cross-Origin-Resource-Sharing (CORS)" is enabled if possible (usually default).
5.  Note the **Local IP** displayed (e.g., `http://192.168.1.5:1234`).

## Step 2: Register Worker (Laptop 1)
Since `LLM Lab` uses a Ray cluster on Laptop 1, we will spawn a "Proxy Worker" on Laptop 1 that forwards requests to Laptop 2.

1.  Open `coordinator/main.py`.
2.  Locate the startup section (where workers are usually initialized). 
    *Currently, workers are spawned dynamically by the `WorkflowManager` or manually.*
    
3.  To persist this connection, you can add a script `connect_remote.py`:

```python
import ray
from coordinator.worker import LLMWorker
import time

# Initialize Ray (attach to existing cluster)
ray.init(address='auto', ignore_reinit_error=True)

# Spawn the proxy worker
remote_worker = LLMWorker.remote(
    model_name="lm-studio-model",
    api_base="http://192.168.1.5:1234/v1"  # <--- REPLACE WITH LAPTOP 2 IP
)

print("Remote worker connected! Keeping alive...")
while True:
    time.sleep(10)
```

4.  Run this script on **Laptop 1**:
    ```bash
    source venv/bin/activate
    python connect_remote.py
    ```

## Step 3: Verify
1.  Go to the Dashboard: `http://localhost:8000/llmlab`.
2.  You should see a new node `worker-xxxx` with the IP of Laptop 1 (proxy) but controlling the remote model.
3.  In Chat UI, ask a question. The Planner may route it to this new worker!
