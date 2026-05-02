try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    class FastMCP:  # type: ignore[override]
        def __init__(self, name: str):
            self.name = name
            self._tools = []

        def tool(self):
            def decorator(func):
                self._tools.append(func)
                return func
            return decorator

        async def list_tools(self):
            return [tool.__name__ for tool in self._tools]

        def run(self):
            raise RuntimeError("FastMCP is not installed in this environment")
import httpx
import asyncio
import os

# Initialize FastMCP server
mcp = FastMCP("LLM Lab")

API_URL = os.getenv("LLM_LAB_API_URL", "http://localhost:8000")

@mcp.tool()
async def submit_task(prompt: str) -> str:
    """
    Submit a task to the distributed LLM cluster.
    Args:
        prompt: The natural language prompt/task description.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{API_URL}/chat", json={"prompt": prompt}, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            return f"Response: {data['response']}\nPlan: {data['plan']}\nWorker: {data['worker']}"
        except Exception as e:
            return f"Error executing task: {str(e)}"

@mcp.tool()
async def list_nodes() -> str:
    """
    List all active nodes in the cluster with their capabilities.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{API_URL}/api/nodes")
            resp.raise_for_status()
            nodes = resp.json().get("active_nodes", {})
            if not nodes:
                return "No active nodes found."
            
            output = ["Active Nodes:"]
            for nid, info in nodes.items():
                meta = info.get("metadata", {})
                model = meta.get("model", "Unknown")
                ip = meta.get("client_ip", "Unknown")
                caps = ", ".join(info.get("capabilities", []))
                output.append(f"- {nid[:8]}... ({model}) @ {ip} | [{caps}]")
            return "\n".join(output)
        except Exception as e:
            return f"Error fetching nodes: {str(e)}"

if __name__ == "__main__":
    mcp.run()
