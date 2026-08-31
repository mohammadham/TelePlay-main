"""
Configuration settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Telegram — optional at build/startup, required only at runtime (panel can set template)
    telegram_api_id: int = Field(0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field("", alias="TELEGRAM_API_HASH")
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    
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
    
    # Database — defaults to sqlite template so build never crashes; panel/ENV can override
    database_url: str = Field("sqlite:///./data/teleplay.db", alias="DATABASE_URL")
    
    
    # JWT — template default, must be changed in panel/ENV for production
    jwt_secret: str = Field("change-me-in-production-please-set-via-panel", alias="JWT_SECRET")
    jwt_expiry_minutes: int = 10080  # 7 days for persistent sessions
    
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    # Concurrency
    telegram_client_concurrency: int = 3
    
    # Web
    web_base_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    # Never crash on missing ENV — use template defaults; panel is source of truth
    return Settings()

def is_configured(settings: Settings) -> bool:
    """True if real credentials are set (not template defaults)."""
    return bool(
        settings.telegram_api_id
        and settings.telegram_api_hash
        and settings.telegram_bot_token
        and settings.telegram_storage_channel_id
        and settings.database_url != "sqlite:///./data/teleplay.db"
        or settings.jwt_secret != "change-me-in-production-please-set-via-panel"
    )
