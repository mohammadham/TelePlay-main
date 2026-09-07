"""
Configuration settings loaded from environment variables,
with database-backed overrides applied after first DB sync.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator
from functools import lru_cache
from typing import Optional, Dict
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")

    # Telegram — optional at build/startup, required only at runtime (panel can set template)
    telegram_api_id: int = Field(0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field("", alias="TELEGRAM_API_HASH")
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    
    # MTProto proxy (optional) - format: "socks5://user:pass@host:port" or "http://host:port"
    telegram_proxy: str = Field("", alias="TELEGRAM_PROXY")
    
    # Use string field to avoid JSON parsing issues with comma-separated env var
    telegram_helper_bot_tokens_str: str = Field("", alias="TELEGRAM_HELPER_BOT_TOKENS")
    
    # Authorized Users (optional - comma separated IDs)
    auth_users_str: str = Field("", alias="AUTH_USERS")
    
    @property
    def auth_users(self) -> list[int]:
        v = self.auth_users_str
        if not v:
            return []
        try:
            return [int(u.strip()) for u in v.split(",") if u.strip()]
        except ValueError:
            return []
    
    # Admin only (bot access)
    admin_ids_str: str = Field("", alias="ADMIN_TELEGRAM_IDS")
    
    @property
    def admin_ids(self) -> list[int]:
        v = self.admin_ids_str
        if not v:
            return []
        try:
            return [int(u.strip()) for u in v.split(",") if u.strip()]
        except ValueError:
            return []

    # Cache
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")

    @field_validator("redis_url", mode="before")
    @classmethod
    def _build_redis_url(cls, v):
        # If explicit REDIS_URL is set and not default, use it
        if v and v != "redis://redis:6379/0":
            return v
        # Try to build from Railway Redis component vars
        import os
        if os.getenv("REDIS_URL"):
            return os.getenv("REDIS_URL")
        if os.getenv("REDIS_HOST") and os.getenv("REDIS_PORT"):
            host = os.getenv("REDIS_HOST")
            port = os.getenv("REDIS_PORT")
            return f"redis://{host}:{port}/0"
        return "redis://redis:6379/0"
    cache_enabled: bool = Field(True, alias="CACHE_ENABLED")
    cache_max_size_mb: int = Field(5120, alias="CACHE_MAX_SIZE_MB")
    cache_max_file_size_mb: int = Field(30, alias="CACHE_MAX_FILE_SIZE_MB")
    cache_strategy: str = Field("lru", alias="CACHE_STRATEGY")
    cache_ttl_seconds: int = Field(3600, alias="CACHE_TTL_SECONDS")
    cache_dir: str = Field("/tmp/teleplay_cache", alias="CACHE_DIR")

    # Ads
    ads_enabled: bool = Field(True, alias="ADS_ENABLED")
    ads_every_n_tracks: int = Field(4, alias="ADS_EVERY_N_TRACKS")
    ads_max_per_hour: int = Field(6, alias="ADS_MAX_PER_HOUR")
    
    @property
    def telegram_helper_bot_tokens(self) -> list[str]:
        v = self.telegram_helper_bot_tokens_str
        if not v:
            return []
        return [t.strip() for t in v.split(",") if t.strip()]
    
    @property
    def all_bot_tokens(self) -> list[str]:
        return [self.telegram_bot_token] + self.telegram_helper_bot_tokens
    
    telegram_storage_channel_id: int = Field(0, alias="TELEGRAM_STORAGE_CHANNEL_ID")

    @field_validator("telegram_api_id", "telegram_storage_channel_id", mode="before")
    @classmethod
    def _parse_int_placeholder(cls, v):
        # Railway may have placeholder "your_api_id" or "-100xxxxxxxxxx" — treat as 0 (template)
        if v is None or v == "":
            return 0
        try:
            return int(str(v).strip())
        except (ValueError, TypeError):
            return 0
    
    # Database — defaults to sqlite template; auto-detects Railway Postgres from component vars
    database_url: str = Field("sqlite:///./data/teleplay.db", alias="DATABASE_URL")

    @field_validator("database_url", mode="before")
    @classmethod
    def _build_database_url(cls, v):
        # If explicit DATABASE_URL is set (non-sqlite), use it
        if v and not v.startswith("sqlite"):
            return v
        # Try to build from Railway Postgres component vars
        import os
        if all(os.getenv(k) for k in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")):
            host = os.getenv("POSTGRES_HOST", "postgres")
            port = os.getenv("POSTGRES_PORT", "5432")
            user = os.getenv("POSTGRES_USER")
            pwd = os.getenv("POSTGRES_PASSWORD")
            db = os.getenv("POSTGRES_DB")
            return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"
        # Fallback: check if DATABASE_URL was provided but is sqlite/template
        if v and v != "sqlite:///./data/teleplay.db":
            return v
        return "sqlite:///./data/teleplay.db"
    
    
    # JWT — auto-generate if not set; panel/ENV can override
    jwt_secret: str = Field("change-me-in-production-please-set-via-panel", alias="JWT_SECRET")

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def _ensure_jwt_secret(cls, v):
        if v and v != "change-me-in-production-please-set-via-panel":
            return v
        # Auto-generate a secure secret at startup
        import secrets
        return secrets.token_urlsafe(32)
    jwt_expiry_minutes: int = 10080  # 7 days for persistent sessions
    
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # Concurrency
    telegram_client_concurrency: int = 3
    
    # Web
    web_base_url: str = "http://localhost:3000"


@lru_cache()
def get_settings() -> Settings:
    # Never crash on missing ENV — use template defaults; panel is source of truth
    return Settings()


# Global flag: set True after first DB sync in lifespan
_db_overrides_applied = False
_db_settings_store: Optional[Settings] = None  # populated by apply_db_overrides() after init_db()

# Track startup attempt state for rate limiting
_startup_attempts: Dict[str, int] = {}
_startup_first_attempt: Optional[float] = None
_startup_lock_until: Optional[float] = None  # timestamp until which checks are suppressed


async def mark_db_ready(s: Settings) -> bool:
    """
    Call this once from main.py lifespan AFTER init_db() completes.
    Loads DB-stored settings and patches s in-place.
    Returns True if DB had valid configuration, False otherwise.
    """
    global _db_overrides_applied, _db_settings_store
    if _db_overrides_applied:
        return True  # already applied

    try:
        from .models import AppSetting
        from .database import async_session
        async with async_session() as conn:
            result = await conn.execute(select(AppSetting))
            rows = result.scalars().all()
            db_map = {r.key: r.value for r in rows if r.value}

            if not db_map:
                logger.info("No DB settings found — first run or empty database")
                _db_overrides_applied = True
                return False

            # Apply all DB settings
            for key, val in db_map.items():
                alias_key = key.upper()
                if alias_key == "TELEGRAM_API_ID":
                    if hasattr(s, "telegram_api_id"):
                        setattr(s, "telegram_api_id", int(val) if val else 0)
                elif alias_key == "TELEGRAM_API_HASH":
                    if hasattr(s, "telegram_api_hash"):
                        setattr(s, "telegram_api_hash", val)
                elif alias_key == "TELEGRAM_BOT_TOKEN":
                    if hasattr(s, "telegram_bot_token"):
                        setattr(s, "telegram_bot_token", val)
                elif alias_key == "TELEGRAM_STORAGE_CHANNEL_ID":
                    if hasattr(s, "telegram_storage_channel_id"):
                        setattr(s, "telegram_storage_channel_id", int(val) if val else 0)
                elif alias_key == "DATABASE_URL":
                    if hasattr(s, "database_url"):
                        setattr(s, "database_url", val)
                elif alias_key == "JWT_SECRET":
                    if hasattr(s, "jwt_secret"):
                        setattr(s, "jwt_secret", val)
                elif alias_key == "WEB_BASE_URL":
                    if hasattr(s, "web_base_url"):
                        setattr(s, "web_base_url", val)
                elif alias_key == "ADMIN_TELEGRAM_IDS":
                    if hasattr(s, "admin_ids_str"):
                        setattr(s, "admin_ids_str", val)
                elif alias_key == "CACHE_ENABLED":
                    if hasattr(s, "cache_enabled"):
                        setattr(s, "cache_enabled", val.lower() in ("true", "1", "yes"))
                elif alias_key == "ADS_ENABLED":
                    if hasattr(s, "ads_enabled"):
                        setattr(s, "ads_enabled", val.lower() in ("true", "1", "yes"))
                elif alias_key == "TELEGRAM_PROXY":
                    if hasattr(s, "telegram_proxy"):
                        setattr(s, "telegram_proxy", val)
                elif alias_key == "TELEGRAM_HELPER_BOT_TOKENS":
                    if hasattr(s, "telegram_helper_bot_tokens_str"):
                        setattr(s, "telegram_helper_bot_tokens_str", val)
                elif alias_key == "AUTH_USERS":
                    if hasattr(s, "auth_users_str"):
                        setattr(s, "auth_users_str", val)

            _db_overrides_applied = True
            _db_settings_store = s
            logger.info("DB settings applied successfully")
            return True

    except ImportError:
        _db_overrides_applied = True
        return False
    except Exception as _e:
        import logging
        logging.getLogger(__name__).error(f"Failed to load DB settings: {_e}")
        # On failure, mark as applied to avoid retry loops
        _db_overrides_applied = True
        return False


async def validate_startup_config(s: Settings) -> tuple[bool, list[str]]:
    """
    Validate that all required configuration is present and decryptable.
    Returns (is_valid, list_of_missing_fields).
    If validation fails, the system should show setup wizard.

    Strategy:
    1. Check if values are in Settings (loaded from DB via mark_db_ready)
    2. If not, read directly from BotConfig/UserAccount tables
    3. If still missing, mark as invalid
    """
    missing = []

    # First, try to get values from DB directly (in case mark_db_ready failed)
    db_values = {}
    try:
        from .models import AppSetting, BotConfig, UserAccount
        from .database import async_session
        import sqlalchemy as _sa

        async with async_session() as conn:
            # Read AppSetting values
            result = await conn.execute(_sa.select(AppSetting))
            rows = result.scalars().all()
            db_values = {r.key: r.value for r in rows if r.value}

            # Also read from BotConfig if available
            main_bot = (await conn.execute(_sa.select(BotConfig).where(BotConfig.name == "main").limit(1))).scalar_one_or_none()
            if main_bot:
                db_values['BOT_CONFIG_EXISTS'] = True

            # And from UserAccount
            storage_acc = (await conn.execute(_sa.select(UserAccount).where(UserAccount.name == "storage_1").limit(1))).scalar_one_or_none()
            if storage_acc:
                db_values['USER_ACCOUNT_EXISTS'] = True
    except Exception as e:
        logger.warning(f"Could not read from DB for validation: {e}")

    # Check API ID: from settings OR DB
    api_id = s.telegram_api_id or db_values.get('TELEGRAM_API_ID', '0')
    if not api_id or int(api_id) == 0:
        missing.append("telegram_api_id")

    # Check API Hash: from settings OR DB
    api_hash = s.telegram_api_hash or db_values.get('TELEGRAM_API_HASH', '')
    if not api_hash or api_hash == "your_api_hash":
        missing.append("telegram_api_hash")

    # Check Bot Token: from settings OR DB
    bot_token = s.telegram_bot_token or db_values.get('TELEGRAM_BOT_TOKEN', '')
    if not bot_token or bot_token == "your_bot_token":
        missing.append("telegram_bot_token")

    # Check Storage Channel ID: from settings OR DB
    storage_id = s.telegram_storage_channel_id or db_values.get('TELEGRAM_STORAGE_CHANNEL_ID', '0')
    if not storage_id or int(storage_id) == 0:
        missing.append("telegram_storage_channel_id")

    # Check JWT Secret: from settings OR DB
    jwt_secret = s.jwt_secret or db_values.get('JWT_SECRET', '')
    if not jwt_secret or jwt_secret == "change-me-in-production-please-set-via-panel":
        missing.append("jwt_secret")

    # Check DB has required records
    try:
        from .models import AdminUser
        from .database import async_session
        import sqlalchemy as _sa

        async with async_session() as conn:
            super_admin = (await conn.execute(_sa.select(AdminUser).where(AdminUser.role == "SUPER_ADMIN").limit(1))).scalar_one_or_none()

            if not super_admin:
                missing.append("db:super_admin")
    except Exception:
        pass

    return (len(missing) == 0, missing)


async def check_decryption_health() -> tuple[bool, int]:
    """
    Check if encrypted credentials in DB can be decrypted with current key.
    Returns (all_ok, error_count).
    """
    from .encryption import decrypt as _dec
    from sqlalchemy import select as _sel
    from .database import async_session
    from .models import UserAccount, BotConfig

    try:
        async with async_session() as _db:
            acc_rows = (await _db.execute(_sel(UserAccount))).scalars().all()
            bot_rows = (await _db.execute(_sel(BotConfig))).scalars().all()
            dec_errors = 0
            for a in acc_rows:
                if not _dec(a.session_string_encrypted):
                    dec_errors += 1
            for b in bot_rows:
                if not _dec(b.token_encrypted):
                    dec_errors += 1
            return (dec_errors == 0, dec_errors)
    except Exception:
        return (False, -1)  # -1 means check failed

# Local flag: set True once complete_setup succeeds — survives across requests
_setup_complete = False


def mark_setup_complete():
    """Call from complete_setup after successful commit to set in-memory flag."""
    global _setup_complete
    _setup_complete = True


async def is_configured(settings: Settings) -> bool:
    """True if real credentials are set (not template defaults).

    Checks in this order:
      1. Real env vars present (works when DATABASE_URL is in .env)
      2. In-memory flag set by complete_setup (survives across requests)
      3. DB state: main bot + storage account + super admin exist AND credentials can be read
    """
    # Primary: real env vars are set
    if (
        settings.telegram_api_id
        and settings.telegram_api_hash
        and settings.telegram_bot_token
        and settings.telegram_storage_channel_id
        and settings.jwt_secret != "change-me-in-production-please-set-via-panel"
    ):
        return True

    # In-memory flag — set by complete_setup after commit
    if _setup_complete:
        return True

    # Fallback: check DB state via async_session
    try:
        from .models import BotConfig, UserAccount, AdminUser, AppSetting
        from .database import async_session
        import sqlalchemy as _sa

        async with async_session() as conn:
            # Check we have the core tables populated
            main_bot = (await conn.execute(_sa.select(BotConfig).where(BotConfig.name == "main").limit(1))).scalar_one_or_none()
            storage_acc = (await conn.execute(_sa.select(UserAccount).where(UserAccount.name == "storage_1").limit(1))).scalar_one_or_none()
            super_admin = (await conn.execute(_sa.select(AdminUser).where(AdminUser.role == "SUPER_ADMIN").limit(1))).scalar_one_or_none()

            # Also check if credentials are stored in DB
            db_settings = await conn.execute(_sa.select(AppSetting))
            db_values = {r.key: r.value for r in db_settings.scalars().all() if r.value}

            # If we have core tables AND credentials in DB, consider configured
            if main_bot and storage_acc and super_admin:
                # Check if at least API_ID and BOT_TOKEN are in DB
                has_api_id = db_values.get('TELEGRAM_API_ID') and int(db_values.get('TELEGRAM_API_ID', '0')) > 0
                has_api_hash = db_values.get('TELEGRAM_API_HASH') and db_values.get('TELEGRAM_API_HASH') != 'your_api_hash'
                has_bot_token = db_values.get('TELEGRAM_BOT_TOKEN') and db_values.get('TELEGRAM_BOT_TOKEN') != 'your_bot_token'
                has_storage_id = db_values.get('TELEGRAM_STORAGE_CHANNEL_ID') and int(db_values.get('TELEGRAM_STORAGE_CHANNEL_ID', '0')) > 0

                if has_api_id and has_api_hash and has_bot_token and has_storage_id:
                    return True

            return bool(main_bot and storage_acc and super_admin)
    except Exception:
        return False
