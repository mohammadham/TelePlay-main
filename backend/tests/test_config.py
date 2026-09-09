"""Unit tests for config module."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestGetSettings:
    def test_returns_settings_object(self):
        from app.config import get_settings
        s = get_settings()
        assert hasattr(s, "telegram_api_id")
        assert hasattr(s, "jwt_secret")
        assert hasattr(s, "cache_enabled")

    def test_cached_same_instance(self):
        from app.config import get_settings
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_default_jwt_expiry_is_7_days(self):
        from app.config import get_settings
        s = get_settings()
        assert s.jwt_expiry_minutes == 10080


class TestSettingsProperties:
    def test_auth_users_empty_by_default(self):
        from app.config import get_settings
        s = get_settings()
        assert s.auth_users == []

    def test_auth_users_parses_comma_string(self):
        from app.config import get_settings
        s = get_settings()
        s.auth_users_str = "1,2,3"
        assert s.auth_users == [1, 2, 3]

    def test_auth_users_handles_spaces(self):
        from app.config import get_settings
        s = get_settings()
        s.auth_users_str = "1, 2 , 3"
        assert s.auth_users == [1, 2, 3]

    def test_auth_users_invalid_returns_empty(self):
        from app.config import get_settings
        s = get_settings()
        s.auth_users_str = "abc,def"
        assert s.auth_users == []

    def test_admin_ids_empty_by_default(self):
        from app.config import get_settings
        s = get_settings()
        assert s.admin_ids == []

    def test_admin_ids_parses_comma_string(self):
        from app.config import get_settings
        s = get_settings()
        s.admin_ids_str = "100,200"
        assert s.admin_ids == [100, 200]

    def test_helper_bot_tokens_empty(self):
        from app.config import get_settings
        s = get_settings()
        assert s.telegram_helper_bot_tokens == []

    def test_all_bot_tokens_includes_main(self):
        from app.config import get_settings
        s = get_settings()
        s.telegram_bot_token = "main:token"
        s.telegram_helper_bot_tokens_str = "h1:tok,h2:tok"
        tokens = s.all_bot_tokens
        assert "main:token" in tokens
        assert "h1:tok" in tokens
        assert "h2:tok" in tokens


class TestMarkDbReady:
    @pytest.mark.asyncio
    async def test_sets_flag_on_success(self):
        from app.config import mark_db_ready, get_settings, _db_overrides_applied

        mock_settings = get_settings()
        mock_session = MagicMock()
        mock_row = MagicMock()
        mock_row.key = "TELEGRAM_API_ID"
        mock_row.value = "99999"
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_row])))
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.config.async_session") as mock_async_session, \
             patch("app.config.get_settings") as mock_get_settings:

            mock_async_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_async_session.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_get_settings.return_value = mock_settings

            # Reset global flag for test
            import app.config as config_mod
            config_mod._db_overrides_applied = False

            result = await mark_db_ready(mock_settings)
            assert result is True
            assert mock_settings.telegram_api_id == 99999

    @pytest.mark.asyncio
    async def test_returns_false_on_import_error(self):
        from app.config import mark_db_ready, get_settings

        mock_settings = get_settings()
        with patch("app.config.async_session") as mock_async:
            mock_async.side_effect = ImportError("no module")
            result = await mark_db_ready(mock_settings)
            assert result is False


class TestValidateStartupConfig:
    @pytest.mark.asyncio
    async def test_missing_api_id(self):
        from app.config import validate_startup_config, get_settings
        s = get_settings()
        s.telegram_api_id = 0
        valid, missing = await validate_startup_config(s)
        assert not valid
        assert "telegram_api_id" in missing

    @pytest.mark.asyncio
    async def test_missing_api_hash(self):
        from app.config import validate_startup_config, get_settings
        s = get_settings()
        s.telegram_api_id = 12345
        s.telegram_api_hash = ""
        valid, missing = await validate_startup_config(s)
        assert not valid
        assert "telegram_api_hash" in missing

    @pytest.mark.asyncio
    async def test_missing_bot_token(self):
        from app.config import validate_startup_config, get_settings
        s = get_settings()
        s.telegram_api_id = 12345
        s.telegram_api_hash = "hash"
        s.telegram_bot_token = ""
        valid, missing = await validate_startup_config(s)
        assert not valid
        assert "telegram_bot_token" in missing

    @pytest.mark.asyncio
    async def test_missing_jwt_secret(self):
        from app.config import validate_startup_config, get_settings
        s = get_settings()
        s.telegram_api_id = 12345
        s.telegram_api_hash = "hash"
        s.telegram_bot_token = "token"
        s.jwt_secret = "change-me-in-production-please-set-via-panel"
        valid, missing = await validate_startup_config(s)
        assert not valid
        assert "jwt_secret" in missing


class TestIsConfigured:
    @pytest.mark.asyncio
    async def test_true_when_all_creds_set(self):
        from app.config import is_configured, get_settings
        s = get_settings()
        s.telegram_api_id = 12345
        s.telegram_api_hash = "my-hash"
        s.telegram_bot_token = "123:abc"
        s.jwt_secret = "my-secret"
        result = await is_configured(s)
        assert result is True

    @pytest.mark.asyncio
    async def test_false_when_api_id_zero(self):
        from app.config import is_configured, get_settings
        s = get_settings()
        s.telegram_api_id = 0
        s.telegram_api_hash = "hash"
        s.telegram_bot_token = "token"
        s.jwt_secret = "secret"
        result = await is_configured(s)
        assert result is False

    @pytest.mark.asyncio
    async def test_true_with_setup_complete_flag(self):
        from app.config import is_configured, get_settings, mark_setup_complete
        mark_setup_complete()
        s = get_settings()
        s.telegram_api_id = 0
        result = await is_configured(s)
        assert result is True
        # reset for other tests
        import app.config as config_mod
        config_mod._setup_complete = False
