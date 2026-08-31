# Telegram Multi-Auth System Specification

## Overview
Replace single-bot/single-user architecture with a robust multi-bot, multi-user Telegram client pool supporting:
- Multiple bot tokens for different purposes (main, helper, ads, etc.)
- Multiple user accounts (MTProto) for storage/streaming with 2FA support
- Super-admin hierarchy for managing bots, accounts, and admins
- Rate limit aware client pool with flood wait handling

---

## 1. Setup Wizard Enhancement

### 1.1 Fields to Collect (in addition to existing)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `BOT_TOKEN` | string | Yes | Main bot token from @BotFather |
| `BOT_TOKENS_EXTRA` | string[] | No | Additional bot tokens (comma-separated) |
| `USER_PHONE` | string | Yes | Telegram phone for MTProto user account |
| `USER_API_ID` | int | Yes | API ID for user account (same as bot or separate) |
| `USER_API_HASH` | string | Yes | API Hash for user account |
| `USER_2FA_PASSWORD` | string | No | 2FA password if enabled on account |
| `SUPER_ADMIN_ID` | int | Yes | Telegram ID of first super admin |

### 1.2 Setup Flow
1. Auto-detect DB/Redis/JWT (read-only)
2. **Step 1**: Bot Token(s) — validate via `getMe`
3. **Step 2**: User Account — phone + API credentials
4. **Step 3**: 2FA — if account has 2FA, prompt for password
5. **Step 4**: Super Admin — enter Telegram ID, verify via bot
6. **Step 5**: Save all → initialize client pool → redirect to login

---

## 2. Data Models

### 2.1 BotConfig
```python
class BotConfig(Base):
    id: int (PK)
    name: str (unique)  # "main", "helper_1", "ads_bot"
    token: str (encrypted)
    bot_user_id: int  # from getMe()
    username: str
    is_active: bool = True
    purpose: Enum[MAIN, HELPER, ADS, STORAGE] = MAIN
    rate_limit_remaining: int = 30  # per second
    last_used: datetime
    created_by: int (FK -> AdminUser.id)
    created_at: datetime
```

### 2.2 UserAccount (MTProto)
```python
class UserAccount(Base):
    id: int (PK)
    name: str (unique)  # "storage_1", "stream_2"
    phone: str
    api_id: int
    api_hash: str (encrypted)
    session_string: str (encrypted)  # Pyrogram session export
    two_fa_password: str (encrypted, nullable)
    user_id: int  # from get_me()
    username: str
    is_active: bool = True
    purpose: Enum[STORAGE, STREAMING, DOWNLOAD] = STORAGE
    flood_wait_until: datetime (nullable)
    last_used: datetime
    created_by: int (FK -> AdminUser.id)
    created_at: datetime
```

### 2.3 AdminUser
```python
class AdminUser(Base):
    id: int (PK)
    telegram_id: int (unique)
    username: str
    first_name: str
    last_name: str
    role: Enum[SUPER_ADMIN, ADMIN, MODERATOR] = ADMIN
    is_active: bool = True
    can_manage_bots: bool = False
    can_manage_accounts: bool = False
    can_manage_admins: bool = False  # Only SUPER_ADMIN
    created_by: int (FK -> AdminUser.id, nullable)  # SUPER_ADMIN has null
    created_at: datetime
    last_login: datetime
```

### 2.4 Relationships
- `BotConfig.created_by` -> `AdminUser.id`
- `UserAccount.created_by` -> `AdminUser.id`
- `AdminUser.created_by` -> `AdminUser.id` (self-referential, SUPER_ADMIN only)

---

## 3. Client Pool Architecture

### 3.1 BotClientPool
- Multiple `Client` instances (one per bot token)
- Round-robin or least-used selection
- Per-bot rate limiting (30 msg/sec default)
- Auto-reconnect on flood wait

### 3.2 UserClientPool
- Multiple `Client` instances (one per user account)
- Session string persistence (encrypted in DB)
- 2FA handling on first login
- Purpose-based routing (storage vs streaming)

### 3.3 Pool Manager
```python
class TelegramPoolManager:
    bot_pool: Dict[str, Client]  # name -> Client
    user_pool: Dict[str, Client]  # name -> Client
    
    def get_bot(purpose: BotPurpose = MAIN) -> Client
    def get_user(purpose: UserPurpose = STORAGE) -> Client
    def add_bot(config: BotConfig) -> Client
    def add_user(account: UserAccount) -> Client
    def remove_bot(name: str)
    def remove_user(name: str)
    def health_check() -> Dict[str, PoolHealth]
```

---

## 4. Authentication Flows

### 4.1 Bot Token Validation (Setup & Admin)
```python
async def validate_bot_token(token: str) -> BotValidationResult:
    client = Client("temp", api_id, api_hash, bot_token=token)
    await client.start()
    me = await client.get_me()
    await client.stop()
    return BotValidationResult(bot_user_id=me.id, username=me.username)
```

### 4.2 User Account Login (2FA)
```python
async def login_user_account(account: UserAccount) -> Client:
    client = Client(
        name=account.name,
        api_id=account.api_id,
        api_hash=account.api_hash,
        phone_number=account.phone,
        session_string=account.session_string,
    )
    await client.start()
    # If 2FA needed and password stored, Pyrogram handles it
    # Else raise TwoFARequired exception for UI prompt
    return client
```

### 4.3 Super Admin Login
- Standard Telegram code login (existing)
- Role check on `/admin/*` routes
- Session includes `role`, `permissions`

---

## 5. Admin Panel Components

### 5.1 BotManager (`/admin/bots`)
- List all bots with status (active/inactive, rate limit)
- Add bot: token input → validate → save
- Edit: toggle active, change purpose, update token
- Delete: confirm, stop client, remove from pool
- Test button: sends test message to super admin

### 5.2 AccountManager (`/admin/accounts`)
- List all user accounts with status
- Add account: phone + API credentials → send code → 2FA if needed → save session
- Edit: toggle active, change purpose
- Delete: confirm, stop client, revoke session (optional)
- Health check: last used, flood wait status

### 5.3 AdminManager (`/admin/admins`) — SUPER_ADMIN only
- List all admins with roles
- Add admin: Telegram ID → verify via bot → assign role
- Edit: change role, toggle permissions, deactivate
- Cannot delete self or other SUPER_ADMIN

---

## 6. Rate Limiting & Flood Wait

### 6.1 Bot Limits (per token)
- 30 messages/second
- 20 messages/minute to same chat
- 1 message/second to same chat (broadcast)
- FloodWait exception: wait `x` seconds, retry

### 6.2 User Account Limits (MTProto)
- More generous but still limited
- FloodWait on: join channel, get messages, download
- Session reuse critical (avoid re-login)

### 6.3 Implementation
```python
class RateLimitedClient:
    def __init__(self, client: Client, limits: RateLimits):
        self.client = client
        self.limiter = TokenBucket(capacity=limits.per_second, refill=1.0)
    
    async def send_message(self, *args, **kwargs):
        await self.limiter.acquire()
        try:
            return await self.client.send_message(*args, **kwargs)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            return await self.client.send_message(*args, **kwargs)
```

---

## 7. API Endpoints

### 7.1 Setup (public during setup)
```
POST /api/setup/bot/validate       # Validate bot token
POST /api/setup/user/send-code     # Send code to phone
POST /api/setup/user/verify-code   # Verify code + 2FA
POST /api/setup/user/session       # Get session string
POST /api/setup/complete           # Save all, init pools
```

### 7.2 Admin (require_admin)
```
GET    /admin/bots                 # List bots
POST   /admin/bots                 # Add bot
PUT    /admin/bots/{id}            # Update bot
DELETE /admin/bots/{id}            # Delete bot
POST   /admin/bots/{id}/test       # Test bot

GET    /admin/accounts             # List user accounts
POST   /admin/accounts             # Add account (start login)
PUT    /admin/accounts/{id}        # Update account
DELETE /admin/accounts/{id}        # Delete account

GET    /admin/admins               # List admins (SUPER_ADMIN)
POST   /admin/admins               # Add admin (SUPER_ADMIN)
PUT    /admin/admins/{id}          # Update admin (SUPER_ADMIN)
DELETE /admin/admins/{id}          # Delete admin (SUPER_ADMIN)
```

---

## 8. Security

- **Encryption**: Bot tokens, API hashes, session strings, 2FA passwords encrypted at rest (Fernet/AES-GCM)
- **Secrets**: Master encryption key from `ENCRYPTION_KEY` env var (auto-generated if missing)
- **Session Strings**: Never logged, only stored encrypted
- **Admin Actions**: Audit log for bot/account/admin changes

---

## 9. Migration Path

1. Deploy new code with migration scripts
2. On first startup: detect existing `telegram_bot_token` → create `BotConfig` (MAIN)
3. Detect existing `telegram_api_id/hash` + session → create `UserAccount` (STORAGE)
4. Existing `ADMIN_TELEGRAM_IDS` → create `AdminUser` (first = SUPER_ADMIN)
5. Setup page shows pre-filled values, allows adding more

---

## 10. Acceptance Criteria

- [ ] Setup wizard collects bot token(s) + user account + 2FA + super admin
- [ ] Multiple bots can be added, tested, managed from admin panel
- [ ] Multiple user accounts can be added (with 2FA), managed from admin panel
- [ ] Super admin can add/remove admins with roles
- [ ] Client pool routes requests to appropriate bot/user client
- [ ] Rate limits respected, flood waits handled gracefully
- [ ] All secrets encrypted at rest
- [ ] Works on Railway (auto-env) and Docker (compose services)