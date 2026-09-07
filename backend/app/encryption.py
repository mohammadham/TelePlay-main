"""
Encryption utilities for sensitive Telegram credentials.
Uses Fernet (AES-128-CBC + HMAC) with key from environment or DB.
Handles decryption errors gracefully (e.g., corrupted data, wrong key).
Must be initialized with ensure_encryption_key() during startup.
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Global key — set once during startup via await ensure_encryption_key()
_ENCRYPTION_KEY: bytes | None = None
_fernet: Fernet | None = None


def _set_fernet(key: bytes) -> None:
    """Set the global _fernet instance."""
    global _fernet
    _fernet = Fernet(key)


async def _resolve_key_async() -> bytes:
    """Resolve encryption key from env var or DB."""
    global _ENCRYPTION_KEY, _fernet
    if _ENCRYPTION_KEY is not None:
        return _ENCRYPTION_KEY

    # 1. Env var (highest priority, persistent across restarts)
    env_key = os.getenv("ENCRYPTION_KEY")
    if env_key:
        try:
            _ENCRYPTION_KEY = env_key.encode()
            _set_fernet(_ENCRYPTION_KEY)
            logger.info("Encryption key loaded from ENCRYPTION_KEY env var")
            return _ENCRYPTION_KEY
        except Exception:
            _ENCRYPTION_KEY = None

    # 2. DB — set during startup via ensure_encryption_key()
    try:
        from .models import AppSetting
        from .database import async_session
        import sqlalchemy

        async with async_session() as conn:
            row = await conn.execute(
                sqlalchemy.select(AppSetting)
                .where(AppSetting.key == 'ENCRYPTION_KEY').limit(1)
            )
            db_key = row.scalar_one_or_none()
            if db_key is not None and db_key.value:
                _ENCRYPTION_KEY = db_key.value.encode()
                _set_fernet(_ENCRYPTION_KEY)
                logger.info("Encryption key loaded from database")
                return _ENCRYPTION_KEY
    except Exception as _e:
        logger.warning(f"Could not read ENCRYPTION_KEY from DB: {_e}")

    # 3. Fallback — auto-generated (DESTRUCTIVE on restart if not persisted)
    logger.error(
        "CRITICAL: ENCRYPTION_KEY not found in env or DB. "
        "Auto-generated key will be lost on restart — all encrypted data will become UNREADABLE."
    )
    _ENCRYPTION_KEY = Fernet.generate_key()
    _set_fernet(_ENCRYPTION_KEY)
    return _ENCRYPTION_KEY


async def ensure_encryption_key() -> bytes:
    """Ensure encryption key exists in DB. Must be awaited during startup."""
    global _ENCRYPTION_KEY, _fernet
    key = await _resolve_key_async()
    if _fernet is not None:
        return key

    # Persist to DB so it survives restarts
    try:
        from .models import AppSetting
        from .database import async_session
        import sqlalchemy

        async with async_session() as conn:
            row = await conn.execute(
                sqlalchemy.select(AppSetting)
                .where(AppSetting.key == 'ENCRYPTION_KEY').limit(1)
            )
            existing = row.scalar_one_or_none()
            if existing is None:
                await conn.execute(
                    sqlalchemy.insert(AppSetting).values(
                        key='ENCRYPTION_KEY',
                        value=key.decode(),
                        description="Fernet encryption master key — DO NOT lose",
                    )
                )
                await conn.commit()
                logger.info("Encryption key persisted to database")
    except Exception as _e:
        logger.warning(f"Could not persist encryption key to DB: {_e}")

    _set_fernet(key)
    return key


def encrypt(plaintext: str) -> str:
    """Encrypt a string value. Must be called AFTER await ensure_encryption_key()."""
    if not plaintext:
        return ""
    if _fernet is None:
        logger.error("encrypt() called before ensure_encryption_key() — key not initialized")
        return ""
    try:
        return _fernet.encrypt(plaintext.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {type(e).__name__}: {e}")
        return ""


def decrypt(ciphertext: str) -> str:
    """Decrypt a string value. Returns empty string on failure."""
    if not ciphertext:
        return ""
    if _fernet is None:
        logger.error("decrypt() called before ensure_encryption_key() — key not initialized")
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.warning("Decryption failed: Invalid token (wrong key or corrupted data)")
        return ""
    except Exception as e:
        logger.warning(f"Decryption failed: {type(e).__name__}: {e}")
        return ""


def get_key_for_env() -> str:
    """Return base64-encoded key for display in .env example."""
    if _ENCRYPTION_KEY is None:
        return ""
    return _ENCRYPTION_KEY.decode()
