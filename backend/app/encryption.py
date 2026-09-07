"""
Encryption utilities for sensitive Telegram credentials.
Uses Fernet (AES-128-CBC + HMAC) with key derived from JWT_SECRET.
The key is deterministic: same JWT_SECRET → same encryption key → survives restarts.
"""
import base64
import hashlib
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Global key and fernet instance
_ENCRYPTION_KEY: bytes | None = None
_fernet: Fernet | None = None


def _set_fernet(key: bytes) -> None:
    """Set the global _fernet instance."""
    global _fernet
    _fernet = Fernet(key)


async def ensure_encryption_key() -> bytes:
    """
    Ensure encryption key is ready. Derives key from JWT_SECRET for persistence.
    Must be awaited during startup (before any encrypt/decrypt calls).
    """
    global _ENCRYPTION_KEY, _fernet
    if _ENCRYPTION_KEY is not None:
        return _ENCRYPTION_KEY

    # Try to get JWT_SECRET from settings to derive a stable encryption key
    try:
        from .config import get_settings
        settings = get_settings()
        jwt_secret = settings.jwt_secret or ""

        if jwt_secret and jwt_secret != "change-me-in-production-please-set-via-panel":
            # Derive a stable 32-byte key from JWT_SECRET using SHA-256
            key_hash = hashlib.sha256(jwt_secret.encode()).digest()
            # Fernet requires base64-encoded 32-byte key
            _ENCRYPTION_KEY = base64.urlsafe_b64encode(key_hash)
            _set_fernet(_ENCRYPTION_KEY)
            logger.info("Encryption key derived from JWT_SECRET (stable across restarts)")
            return _ENCRYPTION_KEY

        # Fallback: generate random key (will change on restart — not ideal)
        logger.warning(
            "JWT_SECRET not set or is default — generating random encryption key. "
            "All encrypted data will become unreadable on restart."
        )
        _ENCRYPTION_KEY = Fernet.generate_key()
        _set_fernet(_ENCRYPTION_KEY)
        return _ENCRYPTION_KEY
    except Exception as e:
        logger.warning(f"Could not derive encryption key from JWT_SECRET: {e}")
        # Ultimate fallback
        _ENCRYPTION_KEY = Fernet.generate_key()
        _set_fernet(_ENCRYPTION_KEY)
        return _ENCRYPTION_KEY


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
    except Exception:
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
