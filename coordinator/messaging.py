import asyncio
from typing import Callable, Any, Dict, List
from enum import Enum
import json
import ray
from abc import ABC, abstractmethod

class ClusterEvents(str, Enum):
    HEARTBEAT = "heartbeat"
    TASK_COMPLETE = "task_complete"
    NODE_JOIN = "node_join"

class MessageBus(ABC):
    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]):
        pass

    @abstractmethod
    async def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], Any]):
        pass

@ray.remote
class PubSubActor:
    """
    Stateful Ray actor to act as the central message bus.
    """
    def __init__(self):
        # topic -> list of subscriber handles (callbacks not easily serializable directly if closures)
        # For simplicity in this phase: we will use a "pull" or "broadcast" model or 
        # just have the registry poll this actor?
        # Better: This actor holds the queue of messages for specific topics.
        self.subscribers = {} 

    def publish(self, topic: str, message: Dict[str, Any]):
        # In a real nats setup, this pushes to subscribers.
        # Here we just store logs or emulate broadcast?
        # For the registry, it needs to 'hear' heartbeats.
        # Let's simple allow polling or registering a "listener" actor handle.
        # But passing functions to Ray actors is tricky.
        pass
        
    def get_messages(self, topic: str) -> List[Dict[str, Any]]:
        # Mocking a queue for the registry to poll
        return []

# Revisiting: The simplest "In-Memory" bus that works across Ray processes 
# without NATS is probably just sending messages directly to the Coordinator Actor
# or having the Coordinator expose a method.
# But we want to preserve the "Bus" abstraction.

# Let's try a simpler approach for Phase 3 "In-Memory":
# The "Bus" is just a wrapper that calls a known Ray Actor (the Coordinator or a specific BusActor).

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
        if topic not in self.queues:
            return []
        msgs = self.queues[topic]
        self.queues[topic] = [] # Clear after reading (queue semantics)
        return msgs

class RayMessageBus(MessageBus):
    def __init__(self):
        # Allow checking if actor exists, else create
        try:
            self.backend = ray.get_actor("RayBusBackend")
        except ValueError:
            try:
                self.backend = RayBusBackend.options(name="RayBusBackend", lifetime="detached").remote()
            except Exception:
                # If race condition, try getting it again
                self.backend = ray.get_actor("RayBusBackend")

    async def publish(self, topic: str, message: Dict[str, Any]):
        self.backend.publish.remote(topic, message)

    async def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], Any]):
        # This is a "Polling" subscriber for now because Ray doesn't easily push to local callbacks
        # cleanly without async complications.
        # We will start a background task to poll.
        asyncio.create_task(self._poll(topic, callback))

    async def _poll(self, topic: str, callback: Callable):
        while True:
            try:
                # remote calls return futures
                ref = self.backend.get_latest.remote(topic)
                messages = await ref
                for msg in messages:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(msg)
                    else:
                        callback(msg)
            except Exception as e:
                print(f"Polling error: {e}")
            await asyncio.sleep(1)
