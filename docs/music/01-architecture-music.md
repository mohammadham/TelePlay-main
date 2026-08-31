# 01 — معماری Music Platform (بر پایه TelePlay)

## وضعیت فعلی TelePlay `backend/app/*:models.py:1`
- **Storage:** تلگرام Private Channel (PyroTGFork MTProto) — صفر local storage
- **DB:** SQLAlchemy 2.0 Async — PostgreSQL prod / SQLite dev — `users, folders, files, watch_progress, login_codes`
- **Streaming:** `streaming.py:32` — multi-client parallel chunk fetching (`parallel_stream_generator`) + `streaming router /api/stream/{file_id}` با Range support
- **Auth:** JWT (access 7d + refresh 90d + `auth_version` برای logout-all) — `auth.py:23`
- **Web:** React 18 + Vite + Zustand + TanStack Query — `web/src/App.tsx:316`
- **Android:** Kotlin + Compose TV + ExoPlayer

## معماری هدف (Music-First)

```
[Telegram Channel] --MTProto--> [Backend FastAPI] --/api--> [Web React + Android]
                                  |  |
                                  |  +--> [PostgreSQL + Redis Cache + Disk Chunk Cache]
                                  |  +--> [Admin Cache Panel]
                                  +--> [Bot (Admin-only)]
```

### تغییرات کلیدی
1. **Domain جدید:** `Artist, Album, Track, Playlist, PlaylistTrack, ListenHistory, Like, Follow, DownloadQueue` — در کنار `File` فعلی (Track به File لینک می‌شود یا جایگزین metadata موزیک می‌شود). `02-domain-model.md` را ببینید.
2. **Cache Layer:** لایهٔ کش بین تلگرام و StreamingResponse — Redis برای metadata + Disk LRU برای chunkها — پنل ادمین برای کنترل. جزئیات در `03-cache-system.md`.
3. **Auth:** محدودسازی Bot به `ADMIN_TELEGRAM_IDS` (جایگزین `AUTH_USERS` عمومی) — بخش `07-admin-security.md`.
4. **Ads:** Middleware تزریق تبلیغ صوتی/بنری بین ترک‌ها — `04-advertising-system.md`.
5. **API Versioning:** `/api/v1/music/*` برای دامنهٔ جدید تا بکوارد باقی بماند.

## Stack پیشنهادی (حفظ + افزودن)
- Backend: FastAPI + SQLAlchemy + **Redis (redis-py async) + aiofiles disk cache**
- DB: PostgreSQL (pool_size 40 نگه‌دار) + **Indexهای جدید** (artist_id, album_id, genre, popularity)
- Cache Admin: `GET/PUT /api/admin/cache/config` + `GET /api/admin/cache/stats` + `POST /api/admin/cache/purge`
- Deployment: Docker Compose + اضافهٔ سرویس `redis` + volume `cache_data`
- CDN آینده: Cloudflare / BunnyCDN جلوی `/api/stream` (optional)

## API جدید (خلاصه)
```
GET  /api/v1/music/tracks?artist=&album=&q=&page=
GET  /api/v1/music/tracks/{id} /stream/{id} (Range + Cache)
POST /api/v1/music/playlists  GET /api/v1/music/playlists/{id}
POST /api/v1/music/history  GET /api/v1/music/history
POST /api/v1/music/likes/{track_id}
GET  /api/v1/music/search?q=
GET  /api/admin/cache/*  PUT /api/admin/cache/config
GET  /api/admin/ads/config  PUT /api/admin/ads/config
```

## ADR
- ADR-01: تلگرام همچنان Source of Truth برای بایت‌ها؛ DB فقط metadata — دلیل: لیمیت صفر استوریج و reuse کد streaming فعلی.
- ADR-02: کش Disk LRU به‌جای کش کامل فایل‌ها — دلیل: فایل موزیک 3-15MB است، کش 10-20% hot tracks به‌شدت hit-rate بالا می‌دهد.
- ADR-03: شاخهٔ فیلم جدا — دلیل: جلوگیری از تداخل migration و UI.

## ریسک‌ها
- Rate limit تلگرام برای hot tracks → حل: کش + helper bots.
- مهاجرت `File.file_type=audio` → `Track` — اسکریپت backfill لازم.
