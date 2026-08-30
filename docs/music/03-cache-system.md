# 03 — سیستم کش (Admin-Managed)

## نیاز: ادمین چه چیز را کنترل کند؟
- **حجم کل کش:** `CACHE_MAX_SIZE_MB` (مثلاً 2GB / 10GB / 50GB) — قابل تغییر runtime
- **حداکثر اندازهٔ هر فایل برای کش:** `CACHE_MAX_FILE_SIZE_MB` (مثلاً فقط فایل ≤ 30MB کش شود؛ موزیک معمول 3-15MB پس همه کش می‌شوند)
- **روش کش:** `CACHE_STRATEGY` = `lru` | `lfu` | `ttl` | `hybrid(lru+lfu)` — قابل انتخاب
- **TTL:** `CACHE_TTL_SECONDS` برای metadata/thumbnail
- **پیش‌گرم کردن (Warmup):** لیست trackهای داغ auto-cache
- **Purge:** پاکسازی دستی (کل / per-track / per-artist)

## معماری کش

```
Request /api/stream/{id} → [Auth] → [Cache Middleware]
                               | miss → [Telegram MTProto parallel_stream_generator]
                               |     → [Cache Write (disk + Redis)] → [Response 206]
                               | hit  → [Disk Cache Read] → [Response 206] (بی‌نیاز MTProto)
Thumbnail/Metadata         → [Redis Cache] (TTL 1h) → hit 95%+
```

### لایه‌ها
1. **Redis (Metadata Cache):** track/album/artist JSON + thumbnail bytes کوچک + `cache:stats` hashes. `REDIS_URL=redis://redis:6379`.
2. **Disk Chunk Cache (File Cache):** `/cache/audio/{track_id}/{offset}-{length}.chunk` با LRU eviction. پیاده‌سازی با `aiofiles` + `LRU dict (OrderedDict)` در حافظه + `du` برای سایز واقعی.
3. **HTTP Cache Headers:** `Cache-Control: public, max-age=3600` + `ETag` برای CDN آینده.

### Eviction Policies
| روش | منطق | مناسب |
|-----|------|-------|
| **LRU** | حذف کمترین Recently Used | پیش‌فرض — ساده، hit-rate بالا برای موزیک |
| **LFU** | حذف کمترین Frequently Used | وقتی پلی‌لیست‌های وایرال دارید |
| **TTL** | انقضا زمانی صرف | metadata |
| **Hybrid** | امتیاز = 0.7*LFU + 0.3*Recency | بهینه نهایی |

پیاده‌سازی: `cache_manager.py` با `asyncio.Lock` + پس‌زمینه `eviction_task` هر 60s.

### Admin API
```
GET  /api/admin/cache/config  → {max_size_mb, max_file_size_mb, strategy, ttl_seconds, enabled}
PUT  /api/admin/cache/config  (admin JWT) → update + persist در DB table `cache_config`
GET  /api/admin/cache/stats   → {used_mb, hit_rate, total_cached_files, top_tracks}
POST /api/admin/cache/purge   body {scope: "all"|"track", track_id?:int}
POST /api/admin/cache/warmup  body {track_ids: int[]}
```

### مدل DB برای تنظیمات
```python
class CacheConfig(Base):
    __tablename__ = "cache_config"
    id PK, max_size_mb int default 5120, max_file_size_mb int default 30,
    strategy str default "lru", ttl_seconds int default 3600, enabled bool default True,
    updated_at
```

### تنظیمات `.env` پیشنهادی
```
REDIS_URL=redis://redis:6379/0
CACHE_ENABLED=true
CACHE_MAX_SIZE_MB=5120
CACHE_MAX_FILE_SIZE_MB=30
CACHE_STRATEGY=lru
CACHE_TTL_SECONDS=3600
CACHE_DIR=/cache/audio
```

### مانیتورینگ
- Prometheus metrics: `cache_hits_total`, `cache_misses_total`, `cache_evictions_total`, `cache_disk_used_bytes`
- لاگ structured: هر hit/miss/evict با track_id.

### امنیت/پرفورمنس نوت
- کش فقط برای فایل‌های `audio` و thumbnail (ویدئو در فاز بعد).
- قفل per-track برای جلوگیری از thundering-herd (singleflight).
- سایز چک قبل از write: اگر `file_size > max_file_size_mb` → skip disk cache، فقط stream.
