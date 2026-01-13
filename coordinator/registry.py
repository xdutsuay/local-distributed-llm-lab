from typing import Dict, Any
import time
from coordinator.messaging import MessageBus, ClusterEvents

class NodeRegistry:
    def __init__(self, bus: MessageBus):
        self.bus = bus
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.ttl = 15 # seconds before considering dead

    async def start(self):
        print("NodeRegistry starting...")
        await self.bus.subscribe(ClusterEvents.HEARTBEAT, self.handle_heartbeat)

    async def handle_heartbeat(self, message: Dict[str, Any]):
        # Message schema: {"node_id": str, "capabilities": list, "timestamp": float}
        node_id = message.get("node_id")
        if node_id:
            self.nodes[node_id] = {
                "last_seen": time.time(),
                "capabilities": message.get("capabilities", []),
                "metadata": message
            }
            # print(f"Registry: Heartbeat from {node_id}")

    def get_active_nodes(self):
        now = time.time()
        active = {}
        to_remove = []
        for nid, data in self.nodes.items():
            if now - data["last_seen"] < self.ttl:
                active[nid] = data
            else:
                to_remove.append(nid)
        
        for nid in to_remove:
            del self.nodes[nid]
            
        return active
        
    async def perform_health_check(self):
        print(" Performing Smart Health Check...")
        active = self.get_active_nodes()
        if not active:
            print("⚠️ ALERT: No active nodes found via Heartbeat!")
        else:
            print(f"✅ Active Nodes: {len(active)}")
            for nid, data in active.items():
                print(f"   - {nid} (Last seen {time.time() - data['last_seen']:.1f}s ago)")
