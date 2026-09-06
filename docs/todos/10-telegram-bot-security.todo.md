# Todo - 10 Telegram Bot Security & Reliability

- [x] admin_only_guard (group=-2, priority high)
- [x] ADMIN_TELEGRAM_IDS config check
- [x] Bot crashes recovery (try/except in handlers)
- [x] Telegram API rate limit handling (flood_wait)
- [ ] File size guard on bot upload (>500MB reject)
- [ ] Inline query rate limit per user (SlowAPI on bot)
- [ ] Error handling: send_code timeout → retry with delay
- [ ] Error handling: sign_in wrong password → 2FA flow
- [ ] Log all blocked non-admin attempts (with user ID)
- [ ] Test: bot handler unit tests (pytest, mock Message)
