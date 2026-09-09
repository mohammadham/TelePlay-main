"""Integration tests for /api/tv endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(database_url, settings_override):
    from app.main import app
    from app.database import Base
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    test_engine = create_async_engine(database_url, echo=False)
    maker = async_sessionmaker(test_engine, expire_on_commit=False)

    from app.database import get_db
    async def override():
        async with maker() as s:
            yield s
    app.dependency_overrides[get_db] = override

    import asyncio
    asyncio.run(Base.metadata.create_all(test_engine))

    async def seed():
        async with test_engine.begin() as conn:
            await conn.execute(text(
                "INSERT OR IGNORE INTO users (telegram_id, username, first_name, auth_version, created_at, last_active) "
                "VALUES (1, 'testuser', 'Test', 0, datetime('now'), datetime('now'))"
            ))
            await conn.execute(text(
                "INSERT OR IGNORE INTO app_settings (key, value, description) VALUES ('JWT_SECRET', 'test-secret', 'JWT secret')"
            ))
            await conn.commit()

    asyncio.run(seed())

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _token(telegram_id=1, is_admin=False):
    from app.auth import create_access_token
    return create_access_token(telegram_id, is_admin=is_admin)


def _h(t):
    return {"Authorization": f"Bearer {t}"}


class TestTVBrowse:
    def test_browse(self, client):
        resp = client.get("/api/tv/browse", headers=_h(_token()))
        assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.get("/api/tv/browse")
        assert resp.status_code == 401


class TestMusicFeatured:
    def test_music_featured(self, client):
        resp = client.get("/api/tv/music/featured", headers=_h(_token()))
        assert resp.status_code == 200


class TestContinue:
    def test_continue_watching(self, client):
        resp = client.get("/api/tv/continue", headers=_h(_token()))
        assert resp.status_code == 200


class TestRecent:
    def test_recent_files(self, client):
        resp = client.get("/api/tv/recent", headers=_h(_token()))
        assert resp.status_code == 200


class TestSearch:
    def test_search(self, client):
        resp = client.get("/api/tv/search?q=test", headers=_h(_token()))
        assert resp.status_code == 200
