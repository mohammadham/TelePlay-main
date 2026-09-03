"""
Encryption utilities for sensitive Telegram credentials.
Uses Fernet (AES-128-CBC + HMAC) with key from environment.
Handles decryption errors gracefully (e.g., corrupted data, wrong key).
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Master key from env, auto-generated if missing (store in production!)
_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key()
_fernet = Fernet(_ENCRYPTION_KEY)


def encrypt(plaintext: str) -> str:
    """Encrypt a string value."""
    if not plaintext:
        return ""
    try:
        return _fernet.encrypt(plaintext.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {type(e).__name__}: {e}")
        return ""


def decrypt(ciphertext: str) -> str:
    """Decrypt a string value. Returns empty string on failure (wrong key, corrupted data, etc.)."""
    if not ciphertext:
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
    return _ENCRYPTION_KEY.decode()