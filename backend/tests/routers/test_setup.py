"""Integration tests for /api/setup endpoints."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(database_url, settings_override):
    from app.main import app
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.database import Base, get_db

    test_engine = create_async_engine(database_url, echo=False)
    maker = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    import asyncio
    asyncio.run(Base.metadata.create_all(test_engine))

    async def seed():
        async with test_engine.begin() as conn:
            await conn.execute(text(
                "INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name, auth_version, created_at, last_active) "
                "VALUES (1, 'testuser', 'Test', 'User', 0, datetime('now'), datetime('now'))"
            ))
            await conn.execute(text(
                "INSERT OR IGNORE INTO admin_users (telegram_id, role, is_active, can_manage_bots, can_manage_accounts, can_manage_admins, created_at) "
                "VALUES (1, 'SUPER_ADMIN', 1, 1, 1, 1, datetime('now'))"
            ))
            await conn.execute(text(
                "INSERT OR IGNORE INTO app_settings (key, value, description) VALUES "
                "('JWT_SECRET', 'test-secret', 'JWT secret'),"
                "('TELEGRAM_API_ID', '12345', 'Telegram API ID'),"
                "('TELEGRAM_API_HASH', 'test-api-hash', 'Telegram API hash'),"
                "('TELEGRAM_BOT_TOKEN', '123456:ABC-DEF-test-token', 'Telegram bot token'),"
                "('TELEGRAM_STORAGE_CHANNEL_ID', '-100123456789', 'Storage channel ID')"
            ))
            await conn.commit()

    asyncio.run(seed())
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestBotValidate:
    def test_validate_returns_200_with_valid_token(self, client):
        """Mock the httpx call to simulate a valid bot token response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"id": 123456, "username": "test_bot", "first_name": "Test Bot"}
        }
        mock_response.raise_for_status.return_value = None

        with patch("app.routers.setup.httpx.AsyncClient") as MockHttpClient:
            async def mock_get(*args, **kwargs):
                return mock_response
            MockHttpClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            MockHttpClient.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = client.post("/api/setup/bot/validate", json={"token": "123456:VALIDTOKEN"}, headers={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["bot_user_id"] == 123456
        assert data["username"] == "test_bot"

    def test_validate_returns_invalid_for_bad_token(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "description": "Unauthorized"}
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")

        with patch("app.routers.setup.httpx.AsyncClient") as MockHttpClient:
            async def mock_get(*args, **kwargs):
                return mock_response
            MockHttpClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            MockHttpClient.return_value.__aexit__ = AsyncMock(return_value=False)

            resp = client.post("/api/setup/bot/validate", json={"token": "INVALID:TOKEN"}, headers={})

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False


class TestSystemStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/setup/system-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "system_ready" in data
        assert "configured" in data
        assert "has_bots_in_db" in data
        assert "has_accounts_in_db" in data
        assert "has_admin_in_db" in data
        assert "show_setup_wizard" in data


class TestStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/setup/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "has_bots" in data
        assert "has_accounts" in data
        assert "has_admin" in data


class TestEmergencyReset:
    def test_returns_200(self, client):
        resp = client.post("/api/setup/emergency-reset")
        assert resp.status_code == 200
        data = resp.json()
        # Emergency reset deletes encrypted data and regenerates JWT_SECRET
        assert "success" in data or "error" in data
