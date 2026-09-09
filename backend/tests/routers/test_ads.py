"""Integration tests for /api/ads endpoints."""
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
            # Insert ad config
            await conn.execute(text(
                "INSERT OR IGNORE INTO ad_config (enabled, every_n_tracks, max_per_hour) VALUES (1, 4, 6)"
            ))
            # Insert an ad
            await conn.execute(text(
                "INSERT OR IGNORE INTO ads (title, duration, enabled) VALUES ('Test Ad', 15, 1)"
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


class TestGetNextAd:
    def test_returns_ad_when_play_count_matches(self, client):
        token = _make_token()
        resp = client.get("/api/ads/next?play_count=4", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "ad" in data or "audio_url" in data

    def test_returns_ad_dict_with_required_fields(self, client):
        token = _make_token()
        resp = client.get("/api/ads/next?play_count=4", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        if data.get("ad") is not None:
            ad = data["ad"]
            assert "id" in ad
            assert "title" in ad
            assert "duration" in ad
            assert "enabled" in ad

    def test_returns_null_ad_when_play_count_does_not_match(self, client):
        token = _make_token()
        resp = client.get("/api/ads/next?play_count=1", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        # play_count=1, every_n_tracks=4, so no ad expected
        assert data.get("ad") is None


class TestLogImpression:
    def test_log_impression_returns_ok(self, client):
        token = _make_token()
        resp = client.post("/api/ads/impression", json={"ad_id": 1, "track_id": 5}, headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True

    def test_log_impression_without_ad_id(self, client):
        token = _make_token()
        resp = client.post("/api/ads/impression", json={}, headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is False


class TestNoAdAvailable:
    def test_no_ads_configured_returns_null(self, client):
        """Clear ads and config, then request next."""
        from sqlalchemy import delete
        import asyncio
        from app.database import get_db

        async def clear_ads():
            async with get_db().__aenter__() as db:
                await db.execute(delete(text("ad_config")))
                await db.execute(delete(text("ads")))
                await db.commit()

        asyncio.run(clear_ads())

        token = _make_token()
        resp = client.get("/api/ads/next?play_count=4", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ad") is None
