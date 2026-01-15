"""
Worker Pool for Round-Robin Load Balancing

Manages multiple LLMWorker instances and distributes tasks using round-robin scheduling.
"""
import ray
from typing import List
from coordinator.worker import LLMWorker
import threading


class WorkerPool:
    """Manages a pool of LLMWorker instances with round-robin selection."""
    
    def __init__(self, num_workers: int = 3):
        """
        Initialize worker pool with specified number of workers.
        
        Args:
            num_workers: Number of worker instances to create
        """
        self.num_workers = num_workers
        self.workers: List[ray.actor.ActorHandle] = []
        self.current_index = 0
        self.lock = threading.Lock()
        
        print(f"🔧 Initializing Worker Pool with {num_workers} workers...")
        
        # Create worker instances
        import uuid
        for i in range(num_workers):
            try:
                # Generate unique ID for the worker
                worker_id = f"worker-{str(uuid.uuid4())[:8]}"
                
                # Create named actor so we can retrieve it by name later
                worker = LLMWorker.options(name=worker_id).remote(node_id=worker_id)
                
                self.workers.append(worker)
                print(f"  ✓ Worker {i+1}/{num_workers} created ({worker_id})")
            except Exception as e:
                print(f"  ✗ Failed to create worker {i+1}: {e}")
        
        if not self.workers:
            raise RuntimeError("Failed to initialize any workers")
        
        print(f"✅ Worker Pool ready with {len(self.workers)} active workers")
    
    def get_next_worker(self) -> ray.actor.ActorHandle:
        """
        Get the next worker using round-robin scheduling.
        
        Returns:
            Next worker instance
        """
        if not self.workers:
            raise RuntimeError("No workers available in pool")
        
        with self.lock:
            worker = self.workers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.workers)
            return worker
    
    def get_active_workers(self) -> List[ray.actor.ActorHandle]:
        """
        Get list of all active workers.
        
        Returns:
            List of worker instances
        """
        return self.workers.copy()
    
    def add_worker(self, worker: ray.actor.ActorHandle):
        """
        Add a worker to the pool dynamically.
        
        Args:
            worker: Worker instance to add
        """
        with self.lock:
            self.workers.append(worker)
            print(f"✓ Worker added to pool. Total workers: {len(self.workers)}")
    
    def get_pool_size(self) -> int:
        """Get current number of workers in pool."""
        return len(self.workers)
