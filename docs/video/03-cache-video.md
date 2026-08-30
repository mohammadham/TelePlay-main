# 03 — کش ویدئو

- Disk LRU جداگانه `/cache/video` (یا shared `/cache` با prefix)
- `max_size_mb_video=20480` (20GB)
- Eviction: LRU + TTL 7d برای video (موسیقی 1d)
- Streaming: Range-aware cache — هر رنج جداگانه کش، هیت برای seek تکراری
- Admin: `PUT /api/admin/cache/config {video_max_size_mb, video_enabled}`
