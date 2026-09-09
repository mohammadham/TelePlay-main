"""Integration tests for /api/admin/seo endpoints."""
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
                "INSERT OR IGNORE INTO admin_users (telegram_id, role, is_active, can_manage_bots, can_manage_accounts, can_manage_admins, created_at) "
                "VALUES (1, 'SUPER_ADMIN', 1, 1, 1, 1, datetime('now'))"
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


class TestSEOConfig:
    def test_get_config(self, client):
        resp = client.get("/api/admin/seo/config", headers=_h(_token()))
        assert resp.status_code == 200

    def test_update_config(self, client):
        resp = client.put(
            "/api/admin/seo/config",
            json={"title_template": "Test | {title}", "geo_region": "US"},
            headers=_h(_token())
        )
        assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.get("/api/admin/seo/config")
        assert resp.status_code == 401


class TestSEOSeed:
    def test_seed(self, client):
        resp = client.post("/api/admin/seo/seed", headers=_h(_token()))
        assert resp.status_code == 200


class TestRobotsTxt:
    def test_get_robots(self, client):
        resp = client.get("/api/admin/seo/robots.txt")
        assert resp.status_code == 200
        assert "User-agent" in resp.text


class TestSitemap:
    def test_get_sitemap(self, client):
        resp = client.get("/api/admin/seo/sitemap.xml")
        assert resp.status_code == 200
        assert '<?xml version' in resp.text


class TestAIDocs:
    def test_get_ai_docs(self, client):
        resp = client.get("/api/admin/seo/ai-docs", headers=_h(_token()))
        assert resp.status_code == 200
