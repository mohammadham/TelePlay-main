# TelePlay — Telegram Authentication Flow

> Complete documentation of the authentication system including login codes, clock drift handling, and JWT token management.

---

## 📋 Overview

TelePlay uses a **two-factor authentication** system for TV and Web clients:

1. **User generates a 6-character code** via `/login` on Telegram bot
2. **User enters code on TV/Web device** — device polls `/auth/verify-code`
3. **Bot validates code** — checks expiration and claims it for the user
4. **Device receives JWT tokens** — access + refresh tokens for API access

---

## 🔐 Authentication Flow Diagram

```
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│   TV App    │          │  Backend    │          │ Telegram    │
│  (Client)   │          │   Server    │          │    Bot      │
└──────┬──────┘          └──────┬──────┘          └──────┬──────┘
       │                        │                        │
       │ 1. POST /auth/         │                        │
       │    generate-code       │                        │
       │◄───────────────────────│                        │
       │    { code, expires_at }│                        │
       │                        │                        │
       │ 2. Display code        │                        │
       │    "ABC123"            │                        │
       │                        │                        │
       │                        │                        │
       │                        │ 3. User sends          │
       │                        │    /login ABC123       │
       │                        │───────────────────────►│
       │                        │                        │
       │                        │ 4. Bot validates code  │
       │                        │    (clock tolerance)   │
       │                        │◄───────────────────────│
       │                        │    "Success!"          │
       │                        │                        │
       │ 5. Poll /auth/         │                        │
       │    verify-code         │                        │
       │───────────────────────►│                        │
       │    { code: "ABC123" }  │                        │
       │                        │ 6. Verify & delete     │
       │                        │    code, return JWT    │
       │◄───────────────────────│                        │
       │    { access_token,     │                        │
       │      refresh_token,    │                        │
       │      user }            │                        │
       │                        │                        │
```

---

## 🔑 Login Code Generation

### Endpoint: `POST /auth/generate-code`

**Called by:** TV App on startup, Web login page

**Response:**
```json
{
  "code": "ABC123",
  "expires_at": "2026-09-02T15:05:00.000Z"
}
```

**Implementation (`routers/auth.py:116-149`):**
- Generates 6-character code: `A-Z` + `0-9`
- Sets `expires_at = now + 5 minutes`
- Stores in `login_codes` table with `telegram_id = NULL`

---

## 📨 Deep-Linked Login (Mobile → TV)

### Endpoint: `GET /start {CODE}`

**Flow:**
1. User taps `/login` on TV → gets code `ABC123`
2. TV shows: "Send `/login ABC123` to @TelePlayBot"
3. User clicks deep link `https://t.me/TelePlayBot?start=ABC123`
4. Telegram opens bot with `/start ABC123`
5. Bot validates and claims code

**Implementation (`bot.py:133-168`):**
```python
@tg_client.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    if len(message.command) > 1:
        code_input = message.command[1].strip().upper()
        # Validate code with clock tolerance
```

---

## 📱 Manual Login (User Types Code)

### Endpoint: `POST /login` (Bot Command)

**User types:** `/login ABC123` in Telegram chat

**Implementation (`bot.py:410-475`):**
```python
@tg_client.on_message(filters.command("login") & filters.private)
async def login_command(client, message: Message):
    if len(message.command) > 1:
        code_input = message.command[1].strip().upper()
        # Same clock tolerance logic
```

---

## ⏰ Clock Drift Tolerance (Critical Fix)

### Problem
Server clock may drift from user's phone clock. Even 2-3 minutes difference caused legitimate codes to show as "expired".

### Solution: 1-Minute Tolerance Buffer

**All three validation points use this logic:**

```python
now = datetime.utcnow()
time_diff = abs((now - login_code.expires_at).total_seconds())

if time_diff <= 60 and not login_code.telegram_id:
    # ✅ Code accepted (within 1-min tolerance)
elif login_code.telegram_id:
    # ⚠️ Code already used
elif time_diff > 300:
    # ❌ Code expired (>5 min)
else:
    # ⏰ 1-5 min diff - timing issue warning
```

### Files Updated
| File | Location | Purpose |
|------|----------|---------|
| `bot.py` | Line ~151 | Deep-linked `/start CODE` |
| `bot.py` | Line ~440 | Manual `/login CODE` |
| `routers/auth.py` | Line ~168 | TV/Web `/auth/verify-code` |

### Behavior Table

| Time Diff | User Message |
|-----------|--------------|
| ≤60s | ✅ **Success!** Code accepted |
| 60-300s | ⏰ Timing issue detected. Request new code. |
| >300s | ❌ **Code expired.** Request new one with `/login` |
| Already used | ❌ **Code already used.** |

---

## 🔄 Code Verification (TV/Web Polling)

### Endpoint: `POST /auth/verify-code`

**Called by:** TV App every 3 seconds, Web page on manual submit

**Request:**
```json
{ "code": "ABC123" }
```

**Response (success):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "telegram_id": 123456789,
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "created_at": "2026-09-01T12:00:00",
    "last_active": "2026-09-02T15:00:00"
  }
}
```

**Response (code not yet verified):**
```json
{
  "detail": "Code not yet verified - please wait for bot confirmation or try again in a few seconds"
}
```

**Implementation (`routers/auth.py:152-203`):**
- Checks clock tolerance first (60s buffer)
- If code expired (>5 min): deletes code, returns 400
- If not yet claimed: returns 400 with friendly message
- If claimed: generates JWT tokens, deletes code, returns tokens

---

## 🎫 JWT Token Management

### Access Token
- **Expiry:** 15 minutes (configurable via `JWT_EXPIRY_MINUTES`)
- **Payload:** `sub` (telegram_id), `exp`, `type: "access"`, `ver` (auth_version)
- **Usage:** `Authorization: Bearer <token>` header

### Refresh Token
- **Expiry:** 90 days
- **Payload:** `sub` (telegram_id), `exp`, `type: "refresh"`, `ver` (auth_version)
- **Usage:** `POST /auth/refresh` to get new access token

### Token Versioning (Global Logout)
- Each user has `auth_version` in database
- On logout (`/auth/logout-all` or `/logout_all` bot command): `auth_version += 1`
- All existing tokens become invalid (version mismatch)
- New login increments version automatically

---

## 🛡️ Security Features

### Rate Limiting
- `/auth/verify-code`: 40/minute (allows TV polling)
- `/auth/generate-code`: Standard SlowAPI limits
- Bot commands: `AUTH_USERS` / `ADMIN_TELEGRAM_IDS` whitelist

### Code Security
- Cryptographically secure: `secrets.choice(alphabet)`
- 6 characters: 36^6 = 2.1B combinations
- 5-minute expiry limits brute force window
- Single-use: deleted after successful verification

### Session Isolation
- Each user's files isolated by `user_id` foreign key
- `AUTH_USERS` env var restricts bot access (legacy)
- `ADMIN_TELEGRAM_IDS` enables admin-only mode

---

## 📱 TV App Login Flow

### App Launch
1. TV app starts → calls `POST /auth/generate-code`
2. Displays code `ABC123` with countdown timer
3. Shows: "Send `/login ABC123` to @TelePlayBot"
4. Starts polling `POST /auth/verify-code` every 3s

### User Action
1. Opens Telegram → clicks deep link or types `/login ABC123`
2. Bot validates with clock tolerance → replies "Success!"
3. TV app next poll → receives JWT tokens
3. Stores tokens in local storage → redirects to home

### Error Handling
- **Code expired:** App generates new code automatically
- **Network error:** Retries with exponential backoff
- **Invalid code:** Shows "Invalid code, check TV screen"

---

## 🌐 Web App Login Flow

### Login Page
1. User visits `https://app.example.com/login`
2. Page calls `POST /auth/generate-code`
3. Displays code + QR code for deep link
4. User clicks "Open in Telegram" or types manually

### Code Polling
- React `useEffect` polls `/auth/verify-code` every 3s
- On success: stores tokens in `localStorage`, redirects to `/`

### Remote Authorization
- Web app can generate direct login link: `/auth?token=...`
- Works when user already logged in on another device

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET` | ✅ | Signing key (min 32 chars) |
| `JWT_EXPIRY_MINUTES` | ❌ | Access token expiry (default: 15) |
| `TELEGRAM_BOT_TOKEN` | ✅ | From @BotFather |
| `ADMIN_TELEGRAM_IDS` | ❌ | Comma-separated admin IDs |
| `AUTH_USERS` | ❌ | Legacy whitelist |

### Database Tables

**`login_codes`**
| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | PK |
| `code` | String(6) | Unique login code |
| `telegram_id` | BigInteger | NULL = unclaimed, set = claimed |
| `expires_at` | DateTime | UTC expiry timestamp |
| `created_at` | DateTime | Auto-set on creation |

**`users` (auth fields)**
| Column | Type | Description |
|--------|------|-------------|
| `telegram_id` | BigInteger | Unique Telegram ID |
| `auth_version` | Integer | Token version (increment = global logout) |
| `last_active` | DateTime | Updated on each request |

---

## 🧪 Testing the Flow

### Manual Test (Bot)
```bash
# 1. Send /login to bot → get code ABC123
# 2. Wait 2 minutes
# 3. Send /login ABC123
# Expected: ✅ Success (within 1-min tolerance)

# 4. Send /login again → get new code DEF456
# 5. Wait 6 minutes
# 6. Send /login DEF456
# Expected: ❌ Code expired
```

### TV App Test
1. Launch TV app → shows code
2. Send `/login CODE` to bot immediately
3. App should get tokens within 3-6 seconds
4. Verify playback works

### Edge Cases
- **Clock drift:** Server 2 min ahead → code still works (≤60s tolerance)
- **Double submit:** Second `/login CODE` → "Already used"
- **Concurrent devices:** First to claim wins, second gets "Already used"

---

## 🐛 Troubleshooting

### "Code expired" but I just generated it
**Cause:** Server clock drift > 5 minutes
**Fix:** Sync server time (`ntpdate pool.ntp.org` or check cloud provider time sync)

### "Code not yet verified" keeps polling
**Cause:** User hasn't sent `/login CODE` to bot
**Fix:** Check bot username is correct, user is sending to right bot

### TV app gets tokens but playback fails
**Cause:** Token expired or `auth_version` mismatch
**Fix:** Force logout on all devices (`/logout_all`), re-login

### Deep link doesn't open bot
**Cause:** Telegram app not installed or universal link not configured
**Fix:** Use manual `/login CODE` instead

---

## 📚 Related Files

| File | Description |
|------|-------------|
| `backend/app/bot.py` | Bot command handlers (`/login`, `/start`) |
| `backend/app/routers/auth.py` | REST API (`/auth/generate-code`, `/auth/verify-code`) |
| `backend/app/routers/setup.py` | Setup wizard auth flow |
| `backend/app/auth.py` | JWT token utilities |
| `backend/app/models.py` | `LoginCode`, `User` models |
| `web/src/lib/api.ts` | Frontend API hooks |
| `web/src/App.tsx` | Web login page logic |
| `android/app/src/...` | TV app login ViewModel |

---

## 📝 Changelog

### 2026-09-02 — Clock Drift Fix (Commit d4c51ac)
- Added 1-minute tolerance buffer to all 3 code validation points
- Changed strict `expires_at > now` to `abs(now - expires_at) <= 60`
- Improved error messages for expired/used/timing issues
- Files: `bot.py` (2 locations), `routers/auth.py` (1 location)

---

*Generated: 2026-09-02 | Commit: d4c51ac*