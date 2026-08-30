"""
Cache Manager — Admin-controlled disk + Redis cache for audio/video streaming.
See docs/music/03-cache-system.md + docs/video/03-cache-video.md
"""
import asyncio
import os
import time
from collections import OrderedDict
from pathlib import Path
from typing import Optional

DEFAULT_CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/teleplay_cache")
DEFAULT_MAX_SIZE_MB = int(os.getenv("CACHE_MAX_SIZE_MB", "5120"))
DEFAULT_MAX_FILE_MB = int(os.getenv("CACHE_MAX_FILE_SIZE_MB", "30"))
DEFAULT_STRATEGY = os.getenv("CACHE_STRATEGY", "lru")

# Video cache (separate dir, larger limits)
VIDEO_CACHE_DIR = os.getenv("VIDEO_CACHE_DIR", os.getenv("VIDEO_CACHE_DIR", "/tmp/teleplay_cache_video"))
VIDEO_MAX_SIZE_MB = int(os.getenv("VIDEO_CACHE_MAX_SIZE_MB", "20480"))
VIDEO_MAX_FILE_MB = int(os.getenv("VIDEO_CACHE_MAX_FILE_SIZE_MB", "500"))

_cache_dir = Path(DEFAULT_CACHE_DIR)
_cache_dir.mkdir(parents=True, exist_ok=True)
_video_dir = Path(VIDEO_CACHE_DIR)
_video_dir.mkdir(parents=True, exist_ok=True)

# In-memory LRU indexes: audio vs video
_lru: OrderedDict[str, dict] = OrderedDict()
_video_lru: OrderedDict[str, dict] = OrderedDict()
_lock = asyncio.Lock()
_total_bytes = 0
_video_bytes = 0

# TODO: integrate Redis for metadata (track JSON, hit counters)
# import redis.asyncio as redis; redis_client = redis.from_url(os.getenv("REDIS_URL"))

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
            "video_used_mb": round(_video_bytes / 1024 / 1024, 2),
            "video_max_mb": VIDEO_MAX_SIZE_MB,
            "video_chunks": len(_video_lru),
        }

async def get_video_chunk(file_id: int, offset: int, length: int) -> Optional[bytes]:
    k = _key(file_id, offset, length)
    async with _lock:
        if k in _video_lru:
            _video_lru.move_to_end(k)
            path = _video_dir / f"{k.replace(':', '_')}.chunk"
            if path.exists():
                return path.read_bytes()
            _video_lru.pop(k, None)
    return None

async def put_video_chunk(file_id: int, offset: int, length: int, data: bytes, file_size: int) -> None:
    global _video_bytes
    if file_size > VIDEO_MAX_FILE_MB * 1024 * 1024:
        return
    k = _key(file_id, offset, length)
    path = _video_dir / f"{k.replace(':', '_')}.chunk"
    async with _lock:
        if k in _video_lru:
            return
        data_len = len(data)
        while _video_bytes + data_len > VIDEO_MAX_SIZE_MB * 1024 * 1024 and _video_lru:
            oldest_k, oldest_v = _video_lru.popitem(last=False)
            (_video_dir / f"{oldest_k.replace(':', '_')}.chunk").unlink(missing_ok=True)
            _video_bytes -= oldest_v.get("size", 0)
        path.write_bytes(data)
        _video_lru[k] = {"size": data_len}
        _video_bytes += data_len

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
