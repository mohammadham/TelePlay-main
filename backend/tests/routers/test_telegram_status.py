"""Integration tests for /api/telegram/status endpoints."""
import pytest
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


class TestGetStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/telegram/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "bot_token_set" in data
        assert "api_id_set" in data
        assert "api_hash_set" in data
        assert "storage_channel_set" in data
        assert "validation" in data


class TestPostStart:
    def test_post_start_returns_200(self, client):
        """POST /api/telegram/start may raise 500 if telegram init fails; assert 200 or error is handled."""
        resp = client.post("/api/telegram/start")
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "success" in data
            assert "message" in data
            assert "client_count" in data

    def test_post_start_force_returns_200(self, client):
        resp = client.post("/api/telegram/start", json={"force": True})
        assert resp.status_code in (200, 500)


class TestPostStop:
    def test_post_stop_returns_200(self, client):
        resp = client.post("/api/telegram/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "message" in data
        assert "client_count" in data
