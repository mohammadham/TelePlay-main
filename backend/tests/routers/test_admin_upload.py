"""Integration tests for /api/admin/upload endpoints."""
import pytest
from unittest.mock import patch, MagicMock
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


def _make_token(telegram_id=1, is_admin=True):
    from app.auth import create_access_token
    return create_access_token(telegram_id, is_admin=is_admin)


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestGetUploadConfig:
    def test_returns_200_with_config(self, client):
        token = _make_token()
        resp = client.get("/api/admin/upload/config", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "upload_strategy" in data
        assert "web_upload_enabled" in data
        assert "bot_fallback_enabled" in data
        assert "max_concurrent_uploads" in data
        assert "my_music_enabled" in data

    def test_strategy_is_string(self, client):
        token = _make_token()
        resp = client.get("/api/admin/upload/config", headers=_headers(token))
        assert isinstance(resp.json()["upload_strategy"], str)


class TestUpdateUploadConfig:
    def test_update_config_returns_200(self, client):
        token = _make_token()
        resp = client.put("/api/admin/upload/config", json={
            "upload_strategy": "round_robin",
            "web_upload_enabled": True,
            "bot_fallback_enabled": False,
            "max_concurrent_uploads": 10,
            "my_music_enabled": True,
        }, headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["upload_strategy"] == "round_robin"
        assert data["max_concurrent_uploads"] == 10

    def test_update_sets_flags_correctly(self, client):
        token = _make_token()
        resp = client.put("/api/admin/upload/config", json={
            "upload_strategy": "random",
            "web_upload_enabled": False,
            "bot_fallback_enabled": True,
            "max_concurrent_uploads": 3,
            "my_music_enabled": False,
        }, headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["web_upload_enabled"] is False
        assert data["bot_fallback_enabled"] is True
        assert data["my_music_enabled"] is False


class TestInvalidStrategy:
    def test_bad_strategy_returns_400(self, client):
        token = _make_token()
        resp = client.put("/api/admin/upload/config", json={
            "upload_strategy": "invalid_strategy",
            "web_upload_enabled": True,
            "bot_fallback_enabled": True,
            "max_concurrent_uploads": 5,
            "my_music_enabled": True,
        }, headers=_headers(token))
        assert resp.status_code == 400
        assert "Invalid upload strategy" in resp.json()["detail"]


class TestPoolHealth:
    def test_health_returns_200(self, client):
        token = _make_token()
        with patch("app.routers.admin_upload.pool_manager.health_check") as mock_health:
            mock_health.return_value = {"total_bots": 1, "total_users": 2, "user_clients": {}}
            resp = client.get("/api/admin/upload/health", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_bots" in data
        assert "total_users" in data
        assert "active_users" in data
        assert "total_active_clients" in data


class TestAuthRequired:
    def test_get_config_unauthorized(self, client):
        resp = client.get("/api/admin/upload/config")
        assert resp.status_code == 401

    def test_update_config_unauthorized(self, client):
        resp = client.put("/api/admin/upload/config", json={})
        assert resp.status_code == 401

    def test_health_unauthorized(self, client):
        resp = client.get("/api/admin/upload/health")
        assert resp.status_code == 401
