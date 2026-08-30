# 01 — معماری ویدئو (روی موزیک)

## Stack
-Reuse: FastAPI + Telegram MTProto + Redis + Disk Cache + JWT
- New: `Movie`, `Series`, `Episode`, `VideoProgress` (یا reuse WatchProgress)

## API
```
GET /api/v1/video/movies?genre=&q=&page=
GET /api/v1/video/movies/{id} /series/{id}
GET /api/v1/video/browse → { hero, continue_watching, by_genre: {action:[...]} }
POST /api/v1/video/progress
GET /api/stream/{file_id} (موجود — cache-aside برای video با max_file_size بالاتر)
```

## Cache
- `CACHE_MAX_FILE_SIZE_MB_VIDEO=500` (جدا از موزیک 30)
- Chunk 2MB برای seek دقیق
- Admin: toggle cache video/audio separately
