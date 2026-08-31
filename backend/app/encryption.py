"""
Encryption utilities for sensitive Telegram credentials.
Uses Fernet (AES-128-CBC + HMAC) with key from environment.
"""
import os
from cryptography.fernet import Fernet

# Master key from env, auto-generated if missing (store in production!)
_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY") or Fernet.generate_key()
_fernet = Fernet(_ENCRYPTION_KEY)


def encrypt(plaintext: str) -> str:
    """Encrypt a string value."""
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a string value."""
    if not ciphertext:
        return ""
    return _fernet.decrypt(ciphertext.encode()).decode()


def get_key_for_env() -> str:
    """Return base64-encoded key for display in .env example."""
    return _ENCRYPTION_KEY.decode()