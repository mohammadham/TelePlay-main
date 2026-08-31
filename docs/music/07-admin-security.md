# 07 — امنیت و دسترسی ادمین‌محور

## نیاز: ربات فقط ادمین
- **وضعیت فعلی:** `bot.py:103` — `check_auth` با `AUTH_USERS` (اگر خالی → همه دسترسی دارند). `AUTH_USERS` برای محدودسازی عمومی بود، نه ادمین-انحصاری.
- **هدف:** فقط `ADMIN_TELEGRAM_IDS` بتوانند به ربات پیام دهند / فایل آپلود کنند / کد لاگین بگیرند. سایر کاربران حتی `/start` هم نبینند (یا پیام «دسترسی محدود»).

## تغییرات پیشنهادی

### Config (`config.py:18`)
```python
admin_ids_str: str = Field("", alias="ADMIN_TELEGRAM_IDS")
@property def admin_ids(self) -> list[int]: ...
# Deprecate AUTH_USERS یا نگه‌دار برای سازگاری اما اولویت با admin_ids
```

### Bot Middleware (`bot.py:103`)
```python
@tg_client.on_message(filters.private, group=-2)
async def admin_only_guard(client, message):
    if not settings.admin_ids: # اگر ست نشده → هشدار لاگ اما اجازه (برای dev)
        logger.warning("ADMIN_TELEGRAM_IDS empty — bot open to all (dev mode)")
        return
    if message.from_user.id not in settings.admin_ids:
        if message.text and message.text.startswith("/start"):
            await message.reply("🚫 دسترسی محدود — فقط ادمین.")
        message.stop_propagation()
```

- `filters.command` هندلرها دست‌نخورده (guard قبل‌شان اجرا می‌شود).
- **File handler** `bot.py:499` هم محافظت می‌شود (فقط ادمین می‌تواند فایل بفرستد).

### API Admin Guard
- `auth.py:69` — `get_current_user` + جدید `require_admin`:
```python
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.telegram_id not in settings.admin_ids:
        raise HTTPException(403, "Admin only")
    return current_user
```
- استفاده: `router.get("/admin/cache/*", dependencies=[Depends(require_admin)])`

### Web/Android
- کاربران عادی همچنان می‌توانند لاگین و استریم کنند (JWT). محدودیت فقط روی **ربات** است، نه API استریم.
- اگر نیاز به «کاربر عادی نمی‌تواند آپلود کند» → بعداً `require_admin` روی `POST /api/files` اضافه شود (فعلاً همه می‌توانند گوش دهند، فقط ادمین آپلود).

### .env نمونه
```
ADMIN_TELEGRAM_IDS=123456789,987654321
# AUTH_USERS منسوخ — اگر هر دو ست بود، ADMIN اولویت دارد
```

### لاگ و مانیتورینگ
- هر تلاش غیرادمین → `logger.warning("Blocked non-admin %s", telegram_id)` + metric `bot_blocked_total`
- تست: `pytest tests/test_admin_guard.py` (mock message)

### چک‌لیست امنیتی تکمیلی
- [ ] JWT `auth_version` برای logout-all حفظ (`auth.py:22`)
- [ ] Rate limit روی `/api/auth/verify-code` حفظ (`auth.py:153` — 40/min)
- [ ] CORS `main.py:62` فقط `WEB_BASE_URL` (ست شود)
- [ ] Pydantic validation روی همه ورودی‌ها
