# Todo - 11 Architecture & Code Quality

- [x] Extract shared helpers: format_size, format_duration → utils.py — backend/app/utils.py created, imported in bot.py
- [x] Health endpoint with DB connectivity check — main.py /health checks DB with text("SELECT 1"), returns degraded on error
- [x] Import dedup (duplicate sqlalchemy.text, AsyncSession removed)
- [x] Add type hints to music.py — Dict, List, Any imported; _track_to_resp, create_track, create_playlist, add_to_playlist, remove_from_playlist, like_track, unlike_track, add_history, list_downloads, add_download, delete_download annotated
- [ ] Lint: ruff or pylint on backend/app — fix warnings — deferred
- [ ] Black formatting on all .py files — deferred
- [ ] Pre-commit hooks (.pre-commit-config.yaml) — deferred
- [ ] API contract validation: OpenAPI spec in docs/api-contract.md — deferred
- [ ] Deprecate AUTH_USERS env var (already handled in config) — skipped (still used)
- [x] Document .env.example with VIDEO_CACHE vars — VIDEO_CACHE_DIR and VIDEO_CACHE_MAX_SIZE_MB added
