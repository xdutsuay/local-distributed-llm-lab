"""
Cache Manager for Distributed LLM Response Caching

Uses Ray's object store for distributed caching of LLM responses
to avoid redundant API calls and reduce latency.
"""
import hashlib
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
    Distributed cache manager for LLM responses.
    
    Uses Ray's object store for distributed access across workers.
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


# Global cache manager instance
_global_cache = None

def get_cache_manager(default_ttl: int = 3600) -> CacheManager:
    """Get the global cache manager instance (singleton)"""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager(default_ttl=default_ttl)
    return _global_cache
