# Telegram API Knowledge Base

## 1. Bot API vs MTProto

| Feature | Bot API (HTTP) | MTProto (Pyrogram/Telethon) |
|---------|---------------|----------------------------|
| Auth | Bot Token | Phone + Code + 2FA |
| Session | Stateless | Persistent session string |
| File Download | Limited (20MB via getFile) | Unlimited (streaming) |
| User Management | No | Full (join, invite, etc.) |
| Rate Limits | Strict (30/s) | More generous |
| Use Case | Commands, inline, webhooks | Storage, streaming, admin |

**Our Architecture**: 
- **Bot API** for: user login (code flow), admin commands, webhooks
- **MTProto (Pyrogram)** for: file upload/download, streaming, channel management

---

## 2. Bot Token Management

### 2.1 Getting Bot Token
1. Message @BotFather → `/newbot`
2. Follow prompts → receive token `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
3. Token format: `<bot_id>:<hash>`

### 2.2 Bot API Limits (per token)
```
Messages: 30 per second (global)
Per Chat: 20 per minute
Broadcast: 1 per second to same chat
File Download: 20MB max via getFile
```
**FloodWait**: HTTP 429 with `retry_after` seconds

### 2.3 Multiple Bots Pattern
```python
# Each bot = independent token = independent rate limit bucket
bots = {
    "main": Client("main", api_id, api_hash, bot_token=TOKEN_MAIN),
    "helper": Client("helper", api_id, api_hash, bot_token=TOKEN_HELPER),
    "ads": Client("ads", api_id, api_hash, bot_token=TOKEN_ADS),
}
# Route by purpose
def get_bot(purpose: BotPurpose) -> Client:
    return bots[purpose.value]
```

### 2.4 Bot Validation (No Session)
```python
async def validate_bot(token: str) -> dict:
    async with Client("validate", api_id, api_hash, bot_token=token, no_updates=True) as c:
        me = await c.get_me()
        return {"id": me.id, "username": me.username, "first_name": me.first_name}
```

---

## 3. MTProto User Accounts (2FA)

### 3.1 Login Flow
```python
# 1. Send code
client = Client("storage", api_id, api_hash, phone_number="+989xxxxxxxxx")
await client.connect()
sent_code = await client.send_code(phone_number)

# 2. User enters code
await client.sign_in(phone_number, sent_code.phone_code_hash, "12345")

# 3. If 2FA enabled
except SessionPasswordNeeded:
    await client.check_password("user_2fa_password")

# 4. Export session for reuse
session_string = await client.export_session_string()
# Store encrypted in DB
```

### 3.2 Session String Reuse
```python
# Subsequent starts - NO code needed
client = Client("storage", api_id, api_hash, session_string=stored_session)
await client.start()  # Instant if session valid
me = await client.get_me()
```

### 3.3 2FA Handling
- **Has 2FA**: `SessionPasswordNeeded` raised on `sign_in`
- **Password**: User provides → `check_password(password)`
- **Hint**: `password_hint` available in exception
- **Recovery**: If password lost → must reset via Telegram (email)

### 3.4 Pyrogram 2FA Best Practices
```python
# Pyrogram handles 2FA automatically if password provided in start()
client = Client(
    "storage",
    api_id=api_id,
    api_hash=api_hash,
    phone_number=phone,
    password=stored_2fa_password,  # Optional, enables auto-2FA
    session_string=stored_session,
)
await client.start()  # Handles code + 2FA internally
```

---

## 4. Multi-Account Client Pool

### 4.1 Architecture
```python
class TelegramPool:
    bots: Dict[str, Client]      # name -> bot client
    users: Dict[str, Client]     # name -> user client
    
    async def start_all():
        for bot in bot_configs:
            self.bots[bot.name] = await create_bot_client(bot)
        for acc in user_accounts:
            self.users[acc.name] = await create_user_client(acc)
    
    def get_bot(purpose=MAIN) -> Client:
        # Least-used or round-robin
        return min(self.bots.values(), key=lambda c: c.request_count)
    
    def get_user(purpose=STORAGE) -> Client:
        # Filter by purpose, then least-used
        candidates = [c for c in self.users.values() if c.purpose == purpose]
        return min(candidates, key=lambda c: c.request_count)
```

### 4.2 Client Wrapper with Rate Limiting
```python
class RateLimitedClient:
    def __init__(self, client: Client, limits: RateLimits):
        self.client = client
        self.bucket = TokenBucket(rate=limits.per_second, burst=limits.burst)
    
    async def __getattr__(self, name):
        attr = getattr(self.client, name)
        if callable(attr):
            async def wrapper(*args, **kwargs):
                await self.bucket.acquire()
                try:
                    return await attr(*args, **kwargs)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    return await attr(*args, **kwargs)
            return wrapper
        return attr
```

### 4.3 FloodWait Handling
```python
# Pyrogram raises FloodWait(value=seconds) on rate limit
# Best practice: catch, sleep, retry once
async def safe_call(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except FloodWait as e:
        logger.warning(f"FloodWait {e.value}s for {func.__name__}")
        await asyncio.sleep(e.value + 1)
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Telegram API error: {e}")
        raise
```

---

## 5. Encryption for Secrets

### 5.1 What to Encrypt
- Bot tokens
- API hashes
- Session strings
- 2FA passwords

### 5.2 Fernet (Recommended)
```python
from cryptography.fernet import Fernet
import os

# Master key from env (32 bytes base64)
MASTER_KEY = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key()
fernet = Fernet(MASTER_KEY)

def encrypt(plaintext: str) -> str:
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    return fernet.decrypt(ciphertext.encode()).decode()
```

### 5.3 SQLAlchemy Encrypted Column
```python
from sqlalchemy import TypeDecorator, Text

class EncryptedString(TypeDecorator):
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        return encrypt(value) if value else None
    
    def process_result_value(self, value, dialect):
        return decrypt(value) if value else None

# Usage
class BotConfig(Base):
    token = Column(EncryptedString, nullable=False)
```

---

## 6. Telegram API Rate Limits Reference

### 6.1 Bot API (HTTP)
| Method | Limit |
|--------|-------|
| sendMessage | 30/sec |
| sendPhoto | 30/sec |
| sendDocument | 30/sec |
| getFile | 30/sec (20MB file) |
| getUpdates | 30/sec |
| answerCallbackQuery | 30/sec |

### 6.2 MTProto (Pyrogram)
| Action | Limit |
|--------|-------|
| Get messages | ~100/sec |
| Download file | Unlimited (bandwidth) |
| Join channel | 50/day |
| Invite to channel | 100/day |
| Send message | ~30/sec |

### 6.3 FloodWait Codes
- `FLOOD_WAIT_X` = wait X seconds
- Can be up to 3600+ seconds for abuse
- Always implement exponential backoff

---

## 7. Pyrogram Session Management

### 7.1 Session String Format
```
1<base64><dc_id><server_address><port><auth_key>
```
- Portable across devices
- Contains full auth state
- **Treat as password** — anyone with it has full account access

### 7.2 Session Lifecycle
```
Create → Export → Encrypt → Store in DB
          ↓
Next Start → Decrypt → Import → Instant login
          ↓
Revoked → Delete from DB → Log out all sessions (optional)
```

### 7.3 Multiple Sessions Per Account
- Telegram allows multiple active sessions
- Each Pyrogram client = one session
- Can have parallel clients for different purposes

---

## 8. Super Admin Pattern

### 8.1 Hierarchy
```
SUPER_ADMIN (created in setup)
  ├── Can manage all bots
  ├── Can manage all user accounts
  ├── Can manage admins (add/remove/edit roles)
  └── Cannot be deleted

ADMIN (created by SUPER_ADMIN)
  ├── Can manage bots (if permission granted)
  ├── Can manage user accounts (if permission granted)
  └── Cannot manage admins

MODERATOR
  ├── Limited read access
  └── No management
```

### 8.2 Permission Checks
```python
def require_super_admin(current_user: AdminUser):
    if current_user.role != Role.SUPER_ADMIN:
        raise HTTPException(403, "Super admin required")

def require_bot_management(current_user: AdminUser):
    if not current_user.can_manage_bots:
        raise HTTPException(403, "Bot management permission required")
```

---

## 9. Docker Compose for Local Dev

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: teleplay
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: teleplay
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  backend:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://teleplay:secret@postgres:5432/teleplay
      REDIS_URL: redis://redis:6379/0
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
    depends_on:
      - postgres
      - redis
```

---

## 10. Railway Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `POSTGRES_USER` | Railway Postgres plugin | Auto-injected |
| `POSTGRES_PASSWORD` | Railway Postgres plugin | Auto-injected |
| `POSTGRES_DB` | Railway Postgres plugin | Auto-injected |
| `POSTGRES_HOST` | Railway Postgres plugin | Auto-injected (usually `postgres`) |
| `POSTGRES_PORT` | Railway Postgres plugin | Auto-injected (usually `5432`) |
| `REDIS_URL` | Railway Redis plugin | Full URL `redis://...` |
| `REDIS_HOST` | Railway Redis plugin | Host only |
| `REDIS_PORT` | Railway Redis plugin | Port only (usually `6379`) |

Our `config.py` auto-detects these — no manual `.env` needed on Railway.

---

## 11. Key Pyrogram Patterns

### 11.1 Client with No Updates (Bot)
```python
Client("bot", api_id, api_hash, bot_token=TOKEN, no_updates=True)
# No long polling, just API calls
```

### 11.2 Client with Updates (User)
```python
Client("user", api_id, api_hash, session_string=SESSION)
# Receives updates, handles flood wait
```

### 11.3 In-Memory Session (No Persistence)
```python
Client("temp", api_id, api_hash, in_memory=True)
# No session file, no export — for one-off validation
```

### 11.4 Graceful Shutdown
```python
async def shutdown_pool(pool: TelegramPool):
    for client in pool.bots.values():
        await client.stop()
    for client in pool.users.values():
        await client.stop()
```

---

## 12. Testing Checklist

- [ ] Bot token validation works (valid/invalid/expired)
- [ ] User account login with 2FA works
- [ ] Session string export/import works
- [ ] Multiple bots in pool handle rate limits independently
- [ ] FloodWait caught and retried
- [ ] Encryption/decryption round-trip works
- [ ] Admin hierarchy enforced (SUPER_ADMIN vs ADMIN)
- [ ] Setup wizard completes end-to-end
- [ ] Docker compose starts all services
- [ ] Railway auto-deploy picks up env vars