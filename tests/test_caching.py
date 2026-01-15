"""
Tests for distributed caching functionality
"""
import pytest
import time
from coordinator.cache_manager import CacheManager, CacheEntry, get_cache_manager


def test_cache_entry_ttl():
    """Test cache entry TTL expiration"""
    entry = CacheEntry("test response", "llama3.2", ttl=1)
    
    assert entry.is_valid() is True
    
    time.sleep(1.1)
    assert entry.is_valid() is False


def test_cache_entry_hit_tracking():
    """Test cache hit counting"""
    entry = CacheEntry("test", "model")
    
    assert entry.hit_count == 0
    entry.increment_hits()
    assert entry.hit_count == 1
    entry.increment_hits()
    assert entry.hit_count == 2


def test_cache_key_generation():
    """Test cache key is consistent for same inputs"""
    cache = CacheManager()
    
    key1 = cache._generate_key("Hello", "llama3.2")
    key2 = cache._generate_key("Hello", "llama3.2")
    key3 = cache._generate_key("Hello", "mistral")
    
    assert key1 == key2  # Same inputs = same key
    assert key1 != key3  # Different model = different key


def test_cache_put_and_get():
    """Test basic cache storage and retrieval"""
    cache = CacheManager()
    
    cache.put("What is 2+2?", "llama3.2", "4")
    result = cache.get("What is 2+2?", "llama3.2")
    
    assert result == "4"
    assert cache.stats["hits"] == 1
    assert cache.stats["misses"] == 0


def test_cache_miss():
    """Test cache miss increments counter"""
    cache = CacheManager()
    
    result = cache.get("Never seen before", "model")
    
    assert result is None
    assert cache.stats["misses"] == 1
    assert cache.stats["hits"] == 0


def test_cache_expiration():
    """Test expired entries are removed"""
    cache = CacheManager()
    
    cache.put("test prompt", "model", "response", ttl=1)
    
    # Should be available immediately
    result1 = cache.get("test prompt", "model")
    assert result1 == "response"
    
    # Wait for expiration
    time.sleep(1.1)
    result2 = cache.get("test prompt", "model")
    assert result2 is None
    assert cache.stats["evictions"] == 1


def test_cache_invalidate():
    """Test manual cache invalidation"""
    cache = CacheManager()
    
    cache.put("prompt", "model", "response")
    assert cache.get("prompt", "model") == "response"
    
    removed = cache.invalidate("prompt", "model")
    assert removed is True
    assert cache.get("prompt", "model") is None


def test_cache_clear():
    """Test clearing all cache entries"""
    cache = CacheManager()
    
    cache.put("prompt1", "model", "response1")
    cache.put("prompt2", "model", "response2")
    cache.put("prompt3", "model", "response3")
    
    assert len(cache.cache) == 3
    
    cache.clear()
    
    assert len(cache.cache) == 0
    assert cache.stats["total_size"] == 0


def test_cache_stats():
    """Test cache statistics calculation"""
    cache = CacheManager()
    
    # 2 hits, 1 miss
    cache.put("p1", "m", "r1")
    cache.get("p1", "m")  # Hit
    cache.get("p2", "m")  # Miss
    cache.get("p1", "m")  # Hit
    
    stats = cache.get_stats()
    
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["total_requests"] == 3
    assert stats["hit_rate"] == 66.67


def test_cache_cleanup_expired():
    """Test cleanup removes only expired entries"""
    cache = CacheManager()
    
    cache.put("p1", "m", "r1", ttl=10)  # Won't expire
    cache.put("p2", "m", "r2", ttl=1)   # Will expire
    cache.put("p3", "m", "r3", ttl=1)   # Will expire
    
    time.sleep(1.1)
    
    removed = cache.cleanup_expired()
    
    assert removed == 2
    assert len(cache.cache) == 1
    assert cache.get("p1", "m") == "r1"


def test_global_cache_singleton():
    """Test get_cache_manager returns same instance"""
    cache1 = get_cache_manager()
    cache2 = get_cache_manager()
    
    assert cache1 is cache2
