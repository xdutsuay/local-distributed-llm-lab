import ray
import asyncio
from typing import Dict, Any, List

@ray.remote
class PubSubActor:
    pass  # Placeholder

@ray.remote
class RayBusBackend:
    def __init__(self):
        # topic -> list of messages
        self.queues = {}
    
    def publish(self, topic: str, message: Dict[str, Any]):
        if topic not in self.queues:
            self.queues[topic] = []
        self.queues[topic].append(message)
        # Keep size manageable
        if len(self.queues[topic]) > 100:
            self.queues[topic].pop(0)

    def get_latest(self, topic: str) -> List[Dict[str, Any]]:
        pass
        
if __name__ == "__main__":
    ray.init(address="auto", namespace="llm-lab")
    try:
        actor = ray.get_actor("RayBusBackend")
        print("✅ Found RayBusBackend Actor!")
        
        # Invoke a method to see if it responds?
        # We need to cast it to expected interface or just call remote methods dynamically
        # Let's try to list messages for 'heartbeat'
        
        future = actor.get_latest.remote("heartbeat")
        msgs = ray.get(future)
        print(f"📨 Heartbeat Messages Fetch: {len(msgs)}")
        for m in msgs:
            print(f" - From: {m.get('node_id', 'Unknown')}, IP: {m.get('client_ip')}")

    except Exception as e:
        print(f"❌ Error finding/querying actor: {e}")
