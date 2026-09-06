# Todo - 11 Architecture & Code Quality

- [x] Extract shared helpers: format_size, format_duration → utils.py
- [x] Health endpoint with DB connectivity check
- [x] Import dedup (duplicate sqlalchemy.text, AsyncSession removed)
- [ ] Add type hints to all router functions (many use dict instead of TypedDict) — deferred
- [ ] Lint: ruff or pylint on backend/app — fix warnings — deferred
- [ ] Black formatting on all .py files — deferred
- [ ] Pre-commit hooks (.pre-commit-config.yaml) — deferred
- [ ] API contract validation: OpenAPI spec in docs/api-contract.md — deferred
- [ ] Deprecate AUTH_USERS env var (already handled in config) — skipped (still used)
- [x] Document .env.example with VIDEO_CACHE vars
