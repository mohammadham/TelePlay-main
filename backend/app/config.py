"""
Configuration settings loaded from environment variables,
with database-backed overrides applied after first DB sync.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict, field_validator
from functools import lru_cache
from typing import Optional


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


async def _load_db_overrides():
    """Load and apply DB-stored settings overrides."""
    from .models import AppSetting
    from .database import get_engine
    eng = get_engine()
    if eng is None:
        return
    from sqlalchemy import select as _sel
    async with eng.begin() as conn:
        result = await conn.execute(_sel(AppSetting))
        rows = result.scalars().all()
        db_map = {r.key: r.value for r in rows if r.value}
        if not db_map:
            return
        for key, val in db_map.items():
            alias_key = key.upper()
            if alias_key == "TELEGRAM_API_ID":
                if hasattr(settings, "telegram_api_id"):
                    setattr(settings, "telegram_api_id", int(val) if val else 0)
            elif alias_key == "TELEGRAM_API_HASH":
                if hasattr(settings, "telegram_api_hash"):
                    setattr(settings, "telegram_api_hash", val)
            elif alias_key == "TELEGRAM_BOT_TOKEN":
                if hasattr(settings, "telegram_bot_token"):
                    setattr(settings, "telegram_bot_token", val)
            elif alias_key == "TELEGRAM_STORAGE_CHANNEL_ID":
                if hasattr(settings, "telegram_storage_channel_id"):
                    setattr(settings, "telegram_storage_channel_id", int(val) if val else 0)
            elif alias_key == "DATABASE_URL":
                if hasattr(settings, "database_url"):
                    setattr(settings, "database_url", val)
            elif alias_key == "JWT_SECRET":
                if hasattr(settings, "jwt_secret"):
                    setattr(settings, "jwt_secret", val)
            elif alias_key == "WEB_BASE_URL":
                if hasattr(settings, "web_base_url"):
                    setattr(settings, "web_base_url", val)
            elif alias_key == "ADMIN_TELEGRAM_IDS":
                if hasattr(settings, "admin_ids_str"):
                    setattr(settings, "admin_ids_str", val)
            elif alias_key == "CACHE_ENABLED":
                if hasattr(settings, "cache_enabled"):
                    setattr(settings, "cache_enabled", val.lower() in ("true", "1", "yes"))
            elif alias_key == "ADS_ENABLED":
                if hasattr(settings, "ads_enabled"):
                    setattr(settings, "ads_enabled", val.lower() in ("true", "1", "yes"))
            elif alias_key == "VIDEO_CACHE_ENABLED":
                if hasattr(settings, "_video_cache_enabled"):
                    setattr(settings, "_video_cache_enabled", val.lower() in ("true", "1", "yes"))

def mark_db_ready(s: Settings):
    """Call this once from main.py lifespan AFTER init_db() completes.
    Loads DB-stored settings and patches s in-place."""
    global _db_overrides_applied, _db_settings_store
    if _db_overrides_applied:
        return
    try:
        from .models import AppSetting
        from .database import get_engine
        eng = get_engine()
        if eng is None:
            _db_overrides_applied = True
            return
        import asyncio
        await _load_db_overrides()
    except ImportError:
        _db_overrides_applied = True
    except Exception as _e:
        import logging
        logging.getLogger(__name__).warning(f"DB overrides could not be applied: {_e}")
    else:
        _db_overrides_applied = True

def is_configured(settings: Settings) -> bool:
    """True if real credentials are set (not template defaults)."""
    return bool(
        settings.telegram_api_id
        and settings.telegram_api_hash
        and settings.telegram_bot_token
        and settings.telegram_storage_channel_id
        and settings.database_url != "sqlite:///./data/teleplay.db"
        and settings.jwt_secret != "change-me-in-production-please-set-via-panel"
    )
