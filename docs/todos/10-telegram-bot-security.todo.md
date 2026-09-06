# Todo - 10 Telegram Bot Security & Reliability

- [x] admin_only_guard (group=-2, priority high)
- [x] ADMIN_TELEGRAM_IDS config check
- [x] Bot crashes recovery (try/except in handlers)
- [x] Telegram API rate limit handling (flood_wait)
- [x] File size guard on bot upload (>500MB reject)
- [x] Log all blocked non-admin attempts (with user ID)
- [x] Retry on send_code timeout (try/except + sleep)
- [ ] Inline query rate limit per user — deferred
- [ ] Test: bot handler unit tests (pytest, mock Message) — deferred
