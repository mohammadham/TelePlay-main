"""
Encryption utilities for sensitive Telegram credentials.
Uses Fernet (AES-128-CBC + HMAC) with key from environment or DB.
Handles decryption errors gracefully (e.g., corrupted data, wrong key).
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Global key — set once during startup via ensure_encryption_key()
_ENCRYPTION_KEY: bytes | None = None
_fernet: Fernet | None = None


def _set_fernet(key: bytes) -> None:
    """Set the global _fernet instance. Must be called from top-level (not nested)."""
    global _fernet
    _fernet = Fernet(key)


def _resolve_key() -> bytes:
    """
    Resolve encryption key from env var or DB.
    Falls back to auto-generated key (DESTRUCTIVE — all prior encrypted data becomes unreadable).
    """
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
            _ENCRYPTION_KEY = None  # invalid base64 — treat as unset

    # 2. DB — set during startup via ensure_encryption_key()
    try:
        from .models import AppSetting
        from .database import get_engine
        import sqlalchemy
        eng = get_engine()
        if eng is not None:
            def _get_key(conn) -> str | None:
                row = conn.execute(
                    sqlalchemy.select(AppSetting)
                    .where(AppSetting.key == 'ENCRYPTION_KEY').limit(1)
                ).scalar_one_or_none()
                return row.value if row else None

            db_key = eng.run_sync(_get_key)
            if db_key:
                _ENCRYPTION_KEY = db_key.encode()
                _set_fernet(_ENCRYPTION_KEY)
                logger.info("Encryption key loaded from database")
                return _ENCRYPTION_KEY
    except Exception as _e:
        logger.warning(f"Could not read ENCRYPTION_KEY from DB: {_e}")

    # 3. Fallback: auto-generate — DESTRUCTIVE on restart!
    logger.error(
        "CRITICAL: ENCRYPTION_KEY not found in env or DB. "
        "Auto-generated key will be lost on restart — all encrypted data will become UNREADABLE."
    )
    _ENCRYPTION_KEY = Fernet.generate_key()
    _set_fernet(_ENCRYPTION_KEY)
    return _ENCRYPTION_KEY


def ensure_encryption_key() -> bytes:
    """
    Ensure encryption key exists in DB so it survives restarts.
    Must be called during app startup (in lifespan), before any encrypt/decrypt calls.
    Returns the resolved key.
    """
    global _ENCRYPTION_KEY, _fernet
    key = _resolve_key()
    if _fernet is not None:
        return key

    # Not yet in DB — persist auto-generated or env key to DB for survival
    try:
        from .models import AppSetting
        from .database import get_engine
        import sqlalchemy
        eng = get_engine()
        if eng is not None:
            def _insert_key(conn) -> None:
                existing = conn.execute(
                    sqlalchemy.select(AppSetting)
                    .where(AppSetting.key == 'ENCRYPTION_KEY').limit(1)
                ).scalar_one_or_none()
                if existing is None:
                    conn.execute(
                        sqlalchemy.insert(AppSetting).values(
                            key='ENCRYPTION_KEY',
                            value=key.decode(),
                            description="Fernet encryption master key — DO NOT lose",
                        )
                    )
                    conn.commit()
                    logger.info("Encryption key persisted to database")

            eng.run_sync(_insert_key)
    except Exception as _e:
        logger.warning(f"Could not persist encryption key to DB: {_e}")

    _set_fernet(key)
    return key


def encrypt(plaintext: str) -> str:
    """Encrypt a string value."""
    if not plaintext:
        return ""
    key = _resolve_key()
    if _fernet is None:
        _set_fernet(key)
    try:
        return _fernet.encrypt(plaintext.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {type(e).__name__}: {e}")
        return ""


def decrypt(ciphertext: str) -> str:
    """Decrypt a string value. Returns empty string on failure (wrong key, corrupted data, etc.)."""
    if not ciphertext:
        return ""
    key = _resolve_key()
    if _fernet is None:
        _set_fernet(key)
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
    key = _resolve_key()
    return key.decode()
