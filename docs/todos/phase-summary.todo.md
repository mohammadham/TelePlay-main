# Summary — Remaining Phases (All Deferred)

## Phase 09 — Security Hardening (Deferred)
- [ ] Input sanitization on file/folder names (XSS prevention)
- [ ] SQL injection audit on ilike queries (ORM parameterized — low risk, verify)
- [ ] pytest tests/test_security.py

## Phase 10 — Telegram Bot Security (Deferred)
- [ ] Inline query rate limit per user
- [ ] Bot handler unit tests (pytest, mock Message)

## Phase 11 — Architecture / Code Quality (Deferred)
- [ ] Lint: ruff/pylint on backend/app — fix warnings
- [ ] Black formatting on all .py files
- [ ] Pre-commit hooks (.pre-commit-config.yaml)
- [ ] API contract: OpenAPI spec in docs/api-contract.md

## Phase 13 — Music Video & Reel Platform (Deferred Items)
### Backend
- [ ] Migration SQL: ALTER TABLE tracks ADD COLUMN media_type VARCHAR(20) DEFAULT 'audio'
### Web Frontend
- [ ] NowPlayingBar: support video playback + show/hide bar
### Android Mobile
- [ ] MobileSearchScreen: add music search integration (current search only does files)
### Docs
- [ ] Update GRAPH.md
- [ ] Move docs/video/ → docs/music-video-platform/ and update README
- [ ] Update todos 09-12 references

## Phase 12 — TV App (Android Leanback) — From Scratch
- [ ] Dependency: add leanback dependency to build.gradle.kts
- [ ] Create tv/ package: ui/tv/ with Leanback components
- [ ] TvMainActivity — hosts Leanback Dashboard
- [ ] TvHomeScreen — LargeCardPresenter (music videos) + ListRowPresenter (reels/artists)
- [ ] TvPlayerScreen — ExoPlayer with leanback controls
- [ ] TvSearchScreen — voice search + music search
- [ ] TvDetailsScreen — track/artist details
- [ ] Horizontal rows: Hero (featured music_video) + Continue Listening + By Genre
- [ ] Navigation: focus-based (D-pad) not touch
- [ ] Theming: dark Netflix-like (matches web MusicHome)

---

# Completed Phases Summary

| Phase | Title | Status | Commit |
|-------|-------|--------|--------|
| 00 | P0 Bugs Fix | ✅ | `29eacdb` |
| 01 | P1 UX Improvements | ✅ | `6b0926c` |
| 02 | Performance (gzip, redis, ETag) | ✅ | `50ebf63`, `c6492d9` |
| 03 | Setup Page & Fix | ✅ | `29eacdb` |
| 04 | Error Boundary & Toasts | ✅ | `6b0926c` |
| 05 | Music Platform | ✅ | `4824bab` |
| 06 | Video Platform (now merged) | ✅ | `4824bab` → refactored |
| 07 | Mobile App (Android) | ✅ | `4824bab` |
| 08 | Documentation | ✅ | Various |
| 09 | Security Hardening | ✅ Core | `fb2e51b` |
| 10 | Bot Security | ✅ Core | `fb2e51b` |
| 11 | Code Quality | ✅ Core | `fb2e51b` |
| 12 | Mobile + TV | 🔄 Partial | `fb2e51b` + `1a513eb` |
| 13 | Music Video & Reel | ✅ Core | `1a513eb` |
