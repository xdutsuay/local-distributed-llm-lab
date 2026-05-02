from typing import Dict, Any
import asyncio
import time
from coordinator.messaging import MessageBus, ClusterEvents
from coordinator import db


class NodeRegistry:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.ttl = 15  # seconds before considering dead

    async def start(self):
        print("NodeRegistry starting...")
        await self.bus.subscribe(ClusterEvents.HEARTBEAT, self.handle_heartbeat)

    async def handle_heartbeat(self, message: Dict[str, Any]):
        """Process incoming heartbeat — update in-memory cache AND persist to DB."""
        node_id = message.get("node_id")
        if node_id:
            self.nodes[node_id] = {
                "last_seen": time.time(),
                "capabilities": message.get("capabilities", []),
                "metadata": message,
            }
            # Persist to SQLite (non-blocking — fire-and-forget)
            asyncio.ensure_future(
                db.upsert_node({**message, "status": "Online"})
            )

    def get_active_nodes(self):
        now = time.time()
        active = {}
        offline = []
        for nid, data in list(self.nodes.items()):
            if now - data["last_seen"] < self.ttl:
                active[nid] = data
            else:
                offline.append(nid)

        # Mark offline nodes in DB and remove from memory
        for nid in offline:
            meta = self.nodes.pop(nid, {}).get("metadata", {})
            asyncio.ensure_future(
                db.upsert_node({**meta, "node_id": nid, "status": "Offline"})
            )
            asyncio.ensure_future(
                db.log_event("heartbeat_miss", nid, {"ttl_exceeded": True})
            )

        return active

    def active_node_count(self) -> int:
        """Return count of nodes alive within TTL (used by adaptive dispatch)."""
        now = time.time()
        return sum(1 for d in self.nodes.values() if now - d["last_seen"] < self.ttl)

    def count_nodes_with_capability(self, capability: str) -> int:
        """Return count of active nodes advertising a given capability."""
        active = self.get_active_nodes()
        return sum(1 for node in active.values() if capability in node.get("capabilities", []))

    def get_nodes_with_capability(self, capability: str) -> Dict[str, Dict[str, Any]]:
        """Return active nodes keyed by node id for a given capability."""
        active = self.get_active_nodes()
        return {
            node_id: node
            for node_id, node in active.items()
            if capability in node.get("capabilities", [])
        }

    def active_llm_node_count(self) -> int:
        """Return count of active nodes that can do LLM inference."""
        return self.count_nodes_with_capability("llm_inference")

    def update_node_model(self, node_id: str, model: str) -> None:
        """Update a node's cached model metadata after a swap."""
        if node_id not in self.nodes:
            return
        self.nodes[node_id]["metadata"]["model"] = model
        asyncio.ensure_future(
            db.upsert_node({**self.nodes[node_id]["metadata"], "node_id": node_id, "model": model})
        )

    async def perform_health_check(self):
        print(" Performing Smart Health Check...")
        active = self.get_active_nodes()
        if not active:
            print("⚠️ ALERT: No active nodes found via Heartbeat!")
            await db.log_event("health_check", "coordinator", {"active_nodes": 0, "alert": True})
        else:
            print(f"✅ Active Nodes: {len(active)}")
            await db.log_event("health_check", "coordinator", {"active_nodes": len(active)})
            for nid, data in active.items():
                print(f"   - {nid} (Last seen {time.time() - data['last_seen']:.1f}s ago)")
