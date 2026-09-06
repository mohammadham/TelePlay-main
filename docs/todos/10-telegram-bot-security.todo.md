# Todo - 10 Telegram Bot Security & Reliability

- [x] admin_only_guard (group=-2, priority high)
- [x] ADMIN_TELEGRAM_IDS config check
- [x] Bot crashes recovery (try/except in handlers)
- [x] Telegram API rate limit handling (flood_wait)
- [x] File size guard on bot upload (>500MB reject) — backend/app/bot.py handle_file
- [x] Log all blocked non-admin attempts (with user ID) — bot.py check_auth, uses logger.warning
- [x] Retry on send_code timeout — telegram_auth.py RETRY_DELAY reduced from 5s to 3s
- [ ] Inline query rate limit per user — deferred
- [ ] Test: bot handler unit tests (pytest, mock Message) — deferred
