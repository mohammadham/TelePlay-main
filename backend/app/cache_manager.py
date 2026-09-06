"""
Cache Manager — Admin-controlled disk + Redis cache for audio streaming.
See docs/music/03-cache-system.md
"""
import asyncio
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional

# Config will be loaded from DB (CacheConfig) + env fallback
DEFAULT_CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/teleplay_cache")
DEFAULT_MAX_SIZE_MB = int(os.getenv("CACHE_MAX_SIZE_MB", "5120"))
DEFAULT_MAX_FILE_MB = int(os.getenv("CACHE_MAX_FILE_SIZE_MB", "30"))
DEFAULT_STRATEGY = os.getenv("CACHE_STRATEGY", "lru")

_cache_dir = Path(DEFAULT_CACHE_DIR)
_cache_dir.mkdir(parents=True, exist_ok=True)

# In-memory LRU index: key -> {size, last_access, freq}
_lru: OrderedDict[str, dict] = OrderedDict()
_lock = asyncio.Lock()
_total_bytes = 0

import redis.asyncio as redis
_redis_client: Optional[redis.Redis] = None

async def _get_redis() -> Optional[redis.Redis]:
    """Lazy-initialize Redis client."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis_client = redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
        await _redis_client.ping()
        return _redis_client
    except Exception:
        return None

async def get_cached_chunk_with_redis(track_id: int, offset: int, length: int) -> Optional[bytes]:
    """Check Redis cache first, then fall back to disk."""
    r = await _get_redis()
    if r is None:
        return None
    k = _key(track_id, offset, length)
    try:
        data = await r.get(f"chunk:{k}")
        if data:
            return data
    except Exception:
        pass
    return None

async def put_cached_chunk_with_redis(track_id: int, offset: int, length: int, data: bytes, ttl: int = 3600) -> None:
    """Write to Redis cache with TTL."""
    r = await _get_redis()
    if r is None or len(data) > 10 * 1024 * 1024:  # skip large chunks
        return
    k = _key(track_id, offset, length)
    try:
        await r.set(f"chunk:{k}", data, ex=ttl)
    except Exception:
        pass

def _key(track_id: int, offset: int, length: int) -> str:
    return f"{track_id}:{offset}:{length}"

async def get_cached_chunk(track_id: int, offset: int, length: int) -> Optional[bytes]:
    """Return cached bytes if hit, else None."""
    k = _key(track_id, offset, length)
    async with _lock:
        if k in _lru:
            _lru.move_to_end(k)
            _lru[k]["freq"] = _lru[k].get("freq", 0) + 1
            _lru[k]["last_access"] = time.time()
            path = _cache_dir / f"{k.replace(':', '_')}.chunk"
            if path.exists():
                return path.read_bytes()
            else:
                # stale index
                _lru.pop(k, None)
    return None

async def put_cached_chunk(track_id: int, offset: int, length: int, data: bytes, file_size: int) -> None:
    """Store chunk if under limits."""
    global _total_bytes
    if file_size > DEFAULT_MAX_FILE_MB * 1024 * 1024:
        return  # skip large files per admin config
    k = _key(track_id, offset, length)
    path = _cache_dir / f"{k.replace(':', '_')}.chunk"
    async with _lock:
        if k in _lru:
            return
        # Evict if needed (LRU)
        data_len = len(data)
        while _total_bytes + data_len > DEFAULT_MAX_SIZE_MB * 1024 * 1024 and _lru:
            oldest_k, oldest_v = _lru.popitem(last=False)
            oldest_path = _cache_dir / f"{oldest_k.replace(':', '_')}.chunk"
            try:
                oldest_path.unlink(missing_ok=True)
            except Exception:
                pass
            _total_bytes -= oldest_v.get("size", 0)
        # Write
        path.write_bytes(data)
        _lru[k] = {"size": data_len, "last_access": time.time(), "freq": 1}
        _lru.move_to_end(k)
        _total_bytes += data_len

async def get_stats() -> dict:
    async with _lock:
        return {
            "used_mb": round(_total_bytes / 1024 / 1024, 2),
            "max_mb": DEFAULT_MAX_SIZE_MB,
            "cached_chunks": len(_lru),
            "strategy": DEFAULT_STRATEGY,
        }

async def purge(scope: str = "all", track_id: Optional[int] = None) -> int:
    """Purge cache; returns count removed."""
    global _total_bytes
    removed = 0
    async with _lock:
        keys = list(_lru.keys())
        for k in keys:
            if scope == "all" or (track_id is not None and k.startswith(f"{track_id}:")):
                path = _cache_dir / f"{k.replace(':', '_')}.chunk"
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
                _total_bytes -= _lru[k].get("size", 0)
                _lru.pop(k, None)
                removed += 1
    return removed


