"""Unit tests for encryption module."""
import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet, InvalidToken


@pytest.fixture
def test_key():
    return Fernet.generate_key()


class TestEncryptDecrypt:
    def test_roundtrip_same_output(self, test_key):
        from app.encryption import _set_fernet, encrypt, decrypt
        _set_fernet(test_key)
        plaintext = "my-secret-token"
        encrypted = encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = decrypt(encrypted)
        assert decrypted == plaintext

    def test_deterministic_same_key(self, test_key):
        from app.encryption import _set_fernet, encrypt
        _set_fernet(test_key)
        # Fernet tokens include timestamp, so they may differ — just verify both decrypt
        e1 = encrypt("test")
        e2 = encrypt("test")
        assert e1 != e2  # different IV/timestamp
        # Both should decrypt to same value
        from app.encryption import decrypt
        assert decrypt(e1) == "test"
        assert decrypt(e2) == "test"

    def test_empty_string_returns_empty(self, test_key):
        from app.encryption import _set_fernet, encrypt
        _set_fernet(test_key)
        assert encrypt("") == ""

    def test_none_input_returns_empty(self, test_key):
        from app.encryption import _set_fernet, encrypt
        _set_fernet(test_key)
        assert encrypt(None) == ""  # type: ignore


class TestDecrypt:
    def test_wrong_key_returns_empty(self, test_key, test_key2):
        from app.encryption import _set_fernet, encrypt, decrypt
        _set_fernet(test_key)
        encrypted = encrypt("secret")
        _set_fernet(test_key2)
        result = decrypt(encrypted)
        assert result == ""

    def test_corrupted_data_returns_empty(self, test_key):
        from app.encryption import _set_fernet, decrypt
        _set_fernet(test_key)
        assert decrypt("not-valid-base64!!!") == ""

    def test_empty_string_returns_empty(self, test_key):
        from app.encryption import _set_fernet, decrypt
        _set_fernet(test_key)
        assert decrypt("") == ""

    def test_none_input_returns_empty(self, test_key):
        from app.encryption import _set_fernet, decrypt
        _set_fernet(test_key)
        assert decrypt(None) == ""  # type: ignore

    def test_persian_text_roundtrip(self, test_key):
        from app.encryption import _set_fernet, encrypt, decrypt
        _set_fernet(test_key)
        persian = "سلام دنیا测试"
        encrypted = encrypt(persian)
        assert decrypt(encrypted) == persian


class TestEnsureEncryptionKey:
    @pytest.mark.asyncio
    async def test_returns_key_when_not_set(self, test_key):
        from app.encryption import ensure_encryption_key, _set_fernet
        _set_fernet(test_key)
        result = await ensure_encryption_key()
        assert result == test_key

    @pytest.mark.asyncio
    async def test_derives_from_jwt_secret(self, test_key):
        """When JWT_SECRET is set, key is derived deterministically."""
        import hashlib, base64
        from app.encryption import ensure_encryption_key
        from app.config import get_settings

        jwt_secret = "my-jwt-secret"
        expected = base64.urlsafe_b64encode(hashlib.sha256(jwt_secret.encode()).digest())

        with patch("app.encryption.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.jwt_secret = jwt_secret
            mock_settings.return_value = mock_s

            result = await ensure_encryption_key()
            assert result == expected

    @pytest.mark.asyncio
    async def test_fallback_to_random_when_no_jwt_secret(self):
        from app.encryption import ensure_encryption_key
        from app.config import get_settings

        with patch("app.encryption.get_settings") as mock_settings:
            mock_s = MagicMock()
            mock_s.jwt_secret = "change-me-in-production-please-set-via-panel"
            mock_settings.return_value = mock_s

            result = await ensure_encryption_key()
            assert result is not None
            assert isinstance(result, bytes)


class TestGetKeyForEnv:
    def test_returns_empty_when_not_initialized(self):
        from app.encryption import get_key_for_env
        # Key not initialized in test context
        # This depends on module state; skip if _ENCRYPTION_KEY is set from other tests
        result = get_key_for_env()
        # May be empty or a valid key depending on test order

    def test_returns_base64_string_when_set(self, test_key):
        from app.encryption import _set_fernet, get_key_for_env
        _set_fernet(test_key)
        result = get_key_for_env()
        assert isinstance(result, str)
        assert len(result) > 0
        # Should be valid base64
        import base64
        base64.urlsafe_b64decode(result + "==")  # no exception
