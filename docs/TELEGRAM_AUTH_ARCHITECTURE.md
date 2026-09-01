# TelePlay Telegram Authentication Architecture

## 1. هدف (Goal)

**هدف اصلی:** ارائه یک سیستم احراز هویت تلگرام قابل اعتماد و حرفه‌ای که:
- کاربران را قادر به اتصال اکانت تلگرام (MTProto) به سیستم کند
- از دو مرحله‌ای (2FA) پشتیبانی کامل کند
- خطاهای Timeout و منقضی شدن کد را graceful مدیریت کند
- Session String برای استفاده‌های بعدی ذخیره کند

## 2. جریان احراز هویت (Authentication Flow)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         TELEGRAM AUTHENTICATION FLOW                          │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐       ┌──────────────┐       ┌────────────────┐
    │ Frontend │──────▶│  Backend API │──────▶│ Telegram MTProto│
    └─────────┘       └──────────────┘       └────────────────┘
         │                   │                       │
         │                   │                       │
         │ 1. POST           │                       │
         │ {phone, api_id,   │                       │
         │  api_hash}        │                       │
         │───────────────────▶│                       │
         │                   │                       │
         │                   │ 2. Create Client      │
         │                   │    (no phone_number!)  │
         │                   │                       │
         │                   │ 3. Connect            │
         │                   │──────────────────────▶│
         │                   │◀──────────────────────│
         │                   │    (DC handshake)      │
         │                   │                       │
         │                   │ 4. send_code()       │
         │                   │──────────────────────▶│
         │                   │◀──────────────────────│
         │                   │    phone_code_hash    │
         │                   │                       │
         │ 5. {success,      │                       │
         │  phone_code_hash}  │                       │
         │◀───────────────────│                       │
         │                   │                       │
         │ 6. Enter code     │                       │
         │    from Telegram  │                       │
         │                   │                       │
         │ 7. POST           │                       │
         │ {code, hash,     │                       │
         │  password?}       │                       │
         │───────────────────▶│                       │
         │                   │                       │
         │                   │ 8. sign_in()          │
         │                   │  (with code)          │
         │                   │──────────────────────▶│
         │                   │                       │
         │                   │    ┌─────────────────┐│
         │                   │    │ NO 2FA:        ││
         │                   │    │ Success!       ││
         │                   │    └─────────────────┘│
         │                   │◀──────────────────────│
         │                   │                       │
         │                   │ 9. export_session_    │
         │                   │    string()           │
         │                   │──────────────────────▶│
         │                   │◀──────────────────────│
         │                   │    session_string     │
         │                   │                       │
         │                   │ 10. Save to DB        │
         │                   │    (encrypted)        │
         │                   │                       │
         │ 11. {success,     │                       │
         │  session_string}  │                       │
         │◀───────────────────│                       │
         │                   │                       │
         │                   │    ┌─────────────────┐│
         │                   │    │ 2FA DETECTED:  ││
         │                   │    │ SessionPassword ││
         │                   │    │ Needed error    ││
         │                   │    └─────────────────┘│
         │                   │◀──────────────────────│
         │                   │                       │
         │                   │ 12. check_password()  │
         │                   │  (if password sent)   │
         │                   │──────────────────────▶│
         │                   │◀──────────────────────│
         │                   │    Success!           │
         │                   │                       │
```

## 3. فایل‌های مرتبط و دسته‌بندی

### 3.1 Core Authentication (نیاز به بازسازی)
```
backend/app/routers/setup.py          ← Setup Wizard API (PRIMARY)
backend/app/routers/admin_accounts.py ← Admin account management
```

### 3.2 Telegram Client Infrastructure
```
backend/app/patch.py                  ← Pyrogram Client wrapper
backend/app/telegram.py              ← Bot client pool
backend/app/pool_manager.py          ← Multi-client pool management
```

### 3.3 Database Models
```
backend/app/models.py                ← UserAccount, BotConfig, AdminUser
backend/app/database.py              ← Database connection
```

### 3.4 Configuration
```
backend/app/config.py                ← Settings & environment
backend/app/encryption.py            ← Encryption utilities
```

### 3.5 Frontend
```
web/src/components/SetupPage.tsx    ← Setup wizard UI
```

## 4. مشکلات فعلی و راه‌حل‌ها

### Problem 1: PHONE_CODE_EXPIRED
**Root Cause:** `phone_number` passed to Client constructor causes auto-login
**Solution:** Never pass `phone_number` to constructor for authentication flow

### Problem 2: Timeout
**Root Cause:** No timeout on Pyrogram operations
**Solution:** Use `asyncio.wait_for()` with appropriate timeouts

### Problem 3: Session State Loss
**Root Cause:** Session file not persisting between send_code and verify
**Solution:** Use same session_name, don't disconnect between steps

### Problem 4: Complex 2FA Flow
**Root Cause:** String matching on error messages
**Solution:** Use proper exception types from Pyrogram

## 5. طراحی جدید (New Design)

### 5.1 Service Layer Pattern

```
backend/app/services/
├── __init__.py
├── telegram_auth.py    ← NEW: Dedicated auth service
└── session_manager.py  ← NEW: Session lifecycle management
```

### 5.2 telegram_auth.py Responsibilities
```python
class TelegramAuthService:
    async def send_code(phone, api_id, api_hash, proxy=None) -> SendCodeResult
    async def verify_code(phone, api_id, api_hash, code, phone_code_hash, password=None) -> VerifyResult
    async def check_2fa_status(phone, api_id, api_hash, phone_code_hash) -> bool
```

### 5.3 Error Handling Strategy
```python
class AuthError(Exception):
    TIMEOUT = "timeout"
    PHONE_CODE_EXPIRED = "phone_code_expired"
    INVALID_CODE = "invalid_code"
    SESSION_PASSWORD_NEEDED = "2fa_required"
    NETWORK_ERROR = "network_error"

class AuthResult:
    success: bool
    error: AuthError | None
    data: dict  # phone_code_hash, session_string, etc.
```

## 6. API Design

### 6.1 Setup Endpoint (Rebuilt)
```python
# POST /api/setup/user/send-code
Request:
{
    "phone": "+989123456789",
    "api_id": 1234567,
    "api_hash": "abc123..."
}

Response (Success):
{
    "success": true,
    "phone_code_hash": "xxxx/yyyy",
    "expires_in_seconds": 120
}

Response (Error):
{
    "success": false,
    "error": "timeout|phone_code_expired|network_error",
    "message": "Human readable message"
}

# POST /api/setup/user/verify-code
Request:
{
    "phone": "+989123456789",
    "api_id": 1234567,
    "api_hash": "abc123...",
    "phone_code_hash": "xxxx/yyyy",
    "code": "12345",
    "password": "optional_2fa_password"
}

Response (Success - No 2FA):
{
    "success": true,
    "session_string": "1BQnN5...",
    "user_id": 123456789,
    "username": "johndoe",
    "has_2fa": false
}

Response (2FA Required):
{
    "success": false,
    "has_2fa": true,
    "error": "Two-factor authentication required",
    "message": "Please enter your 2FA password"
}

Response (Code Expired):
{
    "success": false,
    "error": "phone_code_expired",
    "message": "Code expired. Please request a new code."
}
```

### 6.2 Admin Account Endpoints (Same pattern)
```python
# POST /api/admin/accounts/login/start
# POST /api/admin/accounts/login/verify
```

## 7. Frontend State Machine

```typescript
type AuthState = 
  | 'IDLE'
  | 'SENDING_CODE'
  | 'CODE_SENT'
  | 'VERIFYING_CODE'
  | '2FA_REQUIRED'
  | '2FA_VERIFYING'
  | 'SUCCESS'
  | 'ERROR';

const transitions = {
  IDLE: ['SENDING_CODE'],
  SENDING_CODE: ['CODE_SENT', 'ERROR'],
  CODE_SENT: ['VERIFYING_CODE', 'ERROR', 'SENDING_CODE'], // can resend
  VERIFYING_CODE: ['SUCCESS', '2FA_REQUIRED', 'ERROR'],
  2FA_REQUIRED: ['2FA_VERIFYING', 'SENDING_CODE'], // can resend code
  2FA_VERIFYING: ['SUCCESS', 'ERROR'],
  SUCCESS: [],
  ERROR: ['SENDING_CODE', 'IDLE'],
};
```

## 8. Implementation Plan

### Phase 1: Create Service Layer
- [ ] Create `backend/app/services/` directory
- [ ] Create `telegram_auth.py` service class
- [ ] Create `session_manager.py` for session lifecycle
- [ ] Move authentication logic from routers to services

### Phase 2: Update Routers
- [ ] Rewrite `setup.py` to use new service
- [ ] Rewrite `admin_accounts.py` to use new service
- [ ] Add comprehensive logging
- [ ] Add proper error codes

### Phase 3: Frontend Updates
- [ ] Update `SetupPage.tsx` with new state machine
- [ ] Add proper error handling UI
- [ ] Add retry logic for expired codes
- [ ] Add loading states and feedback

### Phase 4: Testing & Polish
- [ ] Test with 2FA accounts
- [ ] Test with non-2FA accounts
- [ ] Test timeout scenarios
- [ ] Test network failure recovery

## 9. Key Principles

1. **Never pass `phone_number` to Client constructor** during auth flow
2. **Always use proper exception types** (SessionPasswordNeeded, PhoneCodeExpired)
3. **Keep session alive** between send_code and verify
4. **Provide clear error messages** with actionable guidance
5. **Log everything** for debugging
6. **Handle timeouts gracefully** with user feedback
7. **Support 2FA seamlessly** without forcing code resend
