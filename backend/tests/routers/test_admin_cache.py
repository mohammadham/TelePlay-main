"""Integration tests for /api/admin/cache endpoints."""
import pytest
from unittest.mock import AsyncMock, patch
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


class TestCacheConfig:
    def test_get_config(self, client):
        resp = client.get("/api/admin/cache/config", headers=_h(_token()))
        assert resp.status_code == 200

    def test_update_config(self, client):
        resp = client.put(
            "/api/admin/cache/config",
            json={"strategy": "lru", "enabled": True},
            headers=_h(_token())
        )
        assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.get("/api/admin/cache/config")
        assert resp.status_code == 401


class TestCacheStats:
    def test_get_stats(self, client):
        with patch("app.routers.admin.cache_manager.get_stats") as mock_stats:
            mock_stats.return_value = {"hits": 100, "misses": 10}
            resp = client.get("/api/admin/cache/stats", headers=_h(_token()))
            assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.get("/api/admin/cache/stats")
        assert resp.status_code == 401


class TestCachePurge:
    def test_purge_all(self, client):
        with patch("app.routers.admin.cache_manager.purge") as mock_purge:
            mock_purge.return_value = 5
            resp = client.post(
                "/api/admin/cache/purge",
                json={"scope": "all"},
                headers=_h(_token())
            )
            assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.post("/api/admin/cache/purge", json={})
        assert resp.status_code == 401
