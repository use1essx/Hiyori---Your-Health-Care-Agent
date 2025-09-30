"""
Cache Manager for Healthcare AI V2
"""

from typing import Dict, Any, Optional
import time
import json


class HKDataCacheManager:
    """Cache manager for HK healthcare data"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = {}
        self.default_ttl = 1800  # 30 minutes
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            return None
        
        # Check if expired
        if key in self.cache_ttl:
            if time.time() > self.cache_ttl[key]:
                del self.cache[key]
                del self.cache_ttl[key]
                return None
        
        return self.cache[key]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        self.cache[key] = value
        if ttl is None:
            ttl = self.default_ttl
        self.cache_ttl[key] = time.time() + ttl
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]
        if key in self.cache_ttl:
            del self.cache_ttl[key]
    
    async def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        self.cache_ttl.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        active_keys = [
            key for key, expiry in self.cache_ttl.items() 
            if expiry > current_time
        ]
        
        return {
            "total_keys": len(self.cache),
            "active_keys": len(active_keys),
            "expired_keys": len(self.cache) - len(active_keys),
            "cache_size_mb": len(str(self.cache)) / 1024 / 1024
        }


# Singleton instance
_cache_manager = None


async def get_cache_manager() -> HKDataCacheManager:
    """Get cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = HKDataCacheManager()
    return _cache_manager
















