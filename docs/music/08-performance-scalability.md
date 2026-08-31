# 08 — پرفورمنس و مقیاس‌پذیری (کاربر زیاد)

## هدف: 10k+ کاربر همزمان، استریم بدون لگ

## وضعیت فعلی و گلوگاه‌ها
- DB pool: `database.py:30` — `pool_size=40, max_overflow=20` — مناسب؛ برای 10k نیاز به **PgBouncer** یا افزایش pool + read-replica
- Streaming: `streaming.py:32` — parallel fetch با `clients` pool — گلوگاه: **MTProto per-client concurrency** (`get_client_semaphore:25`) — با کش 70% کاهش می‌یابد
- No Redis, No CDN, No horizontal scaling

## استراتژی

### 1. دیتابیس
- ایندکس‌های جدید (02) + `EXPLAIN ANALYZE` روی `/api/v1/music/search`
- Partition `listen_history` ماهانه (اختیاری)
- Read replica برای `GET /tracks` (write روی primary)
- PgBouncer transaction pooling جلوی Postgres
- Alembic migration با `CONCURRENTLY` برای ایندکس

### 2. کش (همان 03)
- Hit-rate هدف: > 75% برای top 20% tracks
- Redis cluster (1 master + 1 replica) — `redis` سرویس در `docker-compose.yml`

### 3. استریم
- `streaming.py` را با **Cache-Aside** بپوشان: ابتدا disk cache چک، سپس MTProto
- `CHUNK_SIZE 1MB` حفظ — برای موزیک (3MB) فقط 3 chunk → overhead کم
- Helper bots (`TELEGRAM_HELPER_BOT_TOKENS`) برای توزیع لود — `config.py:38`

### 4. API
- Pagination `per_page=50` موجود (`routers/files.py:35`) — برای موزیک `limit 30`
- Rate limiting: SlowAPI موجود (`main.py:27`) — برای `/api/stream` اضافه `5 req/sec per IP`
- Gzip/Brotli via Nginx (`web/nginx.conf` + backend `GZipMiddleware`)
- ETag + `If-None-Match` برای metadata

### 5. افقی‌سازی
- Backend stateless (JWT) → چند replica پشت Nginx/Traefik
- Session تلگرام روی volume مشترک یا S3 (برای چند replica باید session share شود — از `postgres` session store یا volume NFS)
- Docker Compose → Kubernetes آماده (Helm chart آینده)

### 6. مانیتورینگ
- Prometheus + Grafana: `http_requests_total`, `stream_duration_seconds`, `db_pool_used`, `cache_hit_rate`
- Sentry برای exception
- Load test: `k6` script — `k6 run loadtest/music_stream.js` (1000 VU, 10m)

### 7. بهینهٔ فرانت
- Code splitting (`React.lazy` برای Artist/Album pages)
- Image lazy + `srcset` برای کاورها
- TanStack Query `staleTime 30s` موجود (`api.ts:273`) — برای موزیک `staleTime 60s`

## چک‌لیست قبل از Production
- [ ] `docker-compose.yml` سرویس `redis` + `cache_data` volume
- [ ] `CACHE_MAX_SIZE_MB` تست eviction
- [ ] `k6` pass با p95 < 300ms برای `/api/v1/music/tracks`
- [ ] Backup روزانه Postgres (pg_dump + S3)
