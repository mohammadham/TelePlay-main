# Todo - 11 Architecture & Code Quality

- [ ] Remove duplicate code: _track_to_resp (models.py + music.py both define)
- [ ] Extract shared helpers: format_size, format_duration to utils.py
- [ ] Add type hints to all router functions (many use dict instead of TypedDict)
- [ ] Lint: ruff or pylint on backend/app — fix warnings
- [ ] Black formatting on all .py files
- [ ] Pre-commit hooks (.pre-commit-config.yaml)
- [ ] API contract validation: OpenAPI spec in docs/api-contract.md
- [ ] Health endpoint: /health includes DB + Redis + Telegram status
- [ ] Deprecate AUTH_USERS env var (already handled in config)
- [ ] Document .env.example with all required + optional vars
