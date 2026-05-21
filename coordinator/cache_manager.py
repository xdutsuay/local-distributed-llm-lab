"""
Cache Manager for Distributed LLM Response Caching

Uses Ray's object store and named actors for distributed caching of LLM responses
to avoid redundant API calls and reduce latency.
"""
import hashlib
import os
import time
from typing import Optional, Dict, Any
import ray


class CacheEntry:
    """Represents a cached LLM response with metadata"""
    def __init__(self, response: str, model: str, ttl: int = 3600):
        self.response = response
        self.model = model
        self.created_at = time.time()
        self.ttl = ttl  # Time to live in seconds
        self.hit_count = 0
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid (not expired)"""
        return (time.time() - self.created_at) < self.ttl
    
    def increment_hits(self):
        """Track cache hits"""
        self.hit_count += 1


class CacheManager:
    """
    Local / in-process cache manager for LLM responses.
    Implements TTL-based expiration and tracks cache statistics.
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            default_ttl: Default time-to-live for cache entries (seconds)
        """
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_size": 0
        }
        print(f"💾 CacheManager initialized (TTL: {default_ttl}s)")
    
    def _generate_key(self, prompt: str, model: str, **params) -> str:
        """
        Generate cache key from prompt and parameters.
        
        Args:
            prompt: User prompt
            model: Model name
            **params: Additional parameters affecting response
            
        Returns:
            Cache key (hex digest)
        """
        # Create consistent hash from prompt + model + sorted params
        key_data = f"{prompt}|{model}|{sorted(params.items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def get(self, prompt: str, model: str, **params) -> Optional[str]:
        """
        Retrieve cached response if available and valid.
        
        Args:
            prompt: User prompt
            model: Model name
            **params: Additional parameters
            
        Returns:
            Cached response or None if not found/expired
        """
        key = self._generate_key(prompt, model, **params)
        
        entry = self.cache.get(key)
        
        if entry is None:
            self.stats["misses"] += 1
            return None
        
        if not entry.is_valid():
            # Expired entry
            del self.cache[key]
            self.stats["evictions"] += 1
            self.stats["misses"] += 1
            return None
        
        # Cache hit
        entry.increment_hits()
        self.stats["hits"] += 1
        print(f"✓ Cache HIT for prompt: {prompt[:30]}...")
        return entry.response
    
    def put(self, prompt: str, model: str, response: str, ttl: Optional[int] = None, **params) -> None:
        """
        Store response in cache.
        
        Args:
            prompt: User prompt
            model: Model name  
            response: LLM response to cache
            ttl: Time-to-live override (uses default if None)
            **params: Additional parameters
        """
        key = self._generate_key(prompt, model, **params)
        ttl = ttl or self.default_ttl
        
        self.cache[key] = CacheEntry(response, model, ttl)
        self.stats["total_size"] = len(self.cache)
        print(f"💾 Cached response for: {prompt[:30]}...")
    
    def invalidate(self, prompt: str, model: str, **params) -> bool:
        """
        Manually invalidate a cache entry.
        
        Returns:
            True if entry was found and removed
        """
        key = self._generate_key(prompt, model, **params)
        if key in self.cache:
            del self.cache[key]
            self.stats["evictions"] += 1
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        count = len(self.cache)
        self.cache.clear()
        self.stats["evictions"] += count
        self.stats["total_size"] = 0
        print(f"🗑️  Cleared {count} cache entries")
   
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache metrics
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if not entry.is_valid()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self.stats["evictions"] += len(expired_keys)
            self.stats["total_size"] = len(self.cache)
            print(f"🗑️  Cleaned up {len(expired_keys)} expired entries")
        
        return len(expired_keys)


@ray.remote(num_cpus=0)
class DistributedCacheActor:
    """Ray Actor for holding the shared cache across all workers"""
    def __init__(self, default_ttl: int = 3600):
        self.manager = CacheManager(default_ttl=default_ttl)
        
    def get(self, prompt: str, model: str, **params) -> Optional[str]:
        return self.manager.get(prompt, model, **params)
        
    def put(self, prompt: str, model: str, response: str, ttl: Optional[int] = None, **params) -> None:
        self.manager.put(prompt, model, response, ttl, **params)
        
    def invalidate(self, prompt: str, model: str, **params) -> bool:
        return self.manager.invalidate(prompt, model, **params)
        
    def clear(self) -> None:
        self.manager.clear()
        
    def get_stats(self) -> Dict[str, Any]:
        return self.manager.get_stats()
        
    def cleanup_expired(self) -> int:
        return self.manager.cleanup_expired()


class DistributedCacheClient:
    """
    Unified client that delegates cache queries to the Ray CacheActor (if active),
    or falls back to a local in-process CacheManager singleton.
    """
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._local_manager = CacheManager(default_ttl=default_ttl)
        self._actor_ref = None

    def _get_actor(self) -> Optional[Any]:
        # Unit tests mock Ray with MagicMock actors — always use local cache.
        if os.getenv("RAY_MOCK_MODE"):
            return None

        if not ray.is_initialized():
            return None
        
        if self._actor_ref is not None:
            return self._actor_ref
            
        try:
            # Look up named detached actor
            self._actor_ref = ray.get_actor("CacheActor", namespace="llm-lab")
            return self._actor_ref
        except ValueError:
            # Ray is initialized but named CacheActor doesn't exist yet
            try:
                # Try to create it as a named detached actor
                self._actor_ref = DistributedCacheActor.options(
                    name="CacheActor",
                    namespace="llm-lab",
                    lifetime="detached"
                ).remote(default_ttl=self.default_ttl)
                print("🚀 Registered new shared DistributedCacheActor in 'llm-lab' namespace.")
                return self._actor_ref
            except Exception as e:
                # Fallback to local
                print(f"⚠️ Failed to create DistributedCacheActor: {e}. Falling back to local cache.")
                return None

    def get(self, prompt: str, model: str, **params) -> Optional[str]:
        actor = self._get_actor()
        if actor is not None:
            try:
                return ray.get(actor.get.remote(prompt, model, **params))
            except Exception as e:
                print(f"⚠️ Ray cache actor get failed: {e}. Falling back to local cache.")
                
        return self._local_manager.get(prompt, model, **params)

    def put(self, prompt: str, model: str, response: str, ttl: Optional[int] = None, **params) -> None:
        actor = self._get_actor()
        if actor is not None:
            try:
                actor.put.remote(prompt, model, response, ttl, **params)
                return
            except Exception as e:
                print(f"⚠️ Ray cache actor put failed: {e}. Falling back to local cache.")
                
        self._local_manager.put(prompt, model, response, ttl, **params)

    def invalidate(self, prompt: str, model: str, **params) -> bool:
        actor = self._get_actor()
        if actor is not None:
            try:
                return ray.get(actor.invalidate.remote(prompt, model, **params))
            except Exception as e:
                print(f"⚠️ Ray cache actor invalidate failed: {e}.")
        return self._local_manager.invalidate(prompt, model, **params)

    def clear(self) -> None:
        actor = self._get_actor()
        if actor is not None:
            try:
                ray.get(actor.clear.remote())
            except Exception as e:
                print(f"⚠️ Ray cache actor clear failed: {e}.")
        self._local_manager.clear()

    def get_stats(self) -> Dict[str, Any]:
        actor = self._get_actor()
        if actor is not None:
            try:
                return ray.get(actor.get_stats.remote())
            except Exception as e:
                print(f"⚠️ Ray cache actor get_stats failed: {e}.")
        return self._local_manager.get_stats()

    def cleanup_expired(self) -> int:
        actor = self._get_actor()
        if actor is not None:
            try:
                return ray.get(actor.cleanup_expired.remote())
            except Exception as e:
                print(f"⚠️ Ray cache actor cleanup_expired failed: {e}.")
        return self._local_manager.cleanup_expired()


# Global cache manager client instance
_global_cache = None

def get_cache_manager(default_ttl: int = 3600) -> DistributedCacheClient:
    """Get the global cache manager client instance (singleton)"""
    global _global_cache
    if _global_cache is None:
        _global_cache = DistributedCacheClient(default_ttl=default_ttl)
    return _global_cache
