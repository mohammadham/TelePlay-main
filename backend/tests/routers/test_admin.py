"""Integration tests for /api/admin endpoints (stats, users)."""
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
                "VALUES (1, 'admin', 'Admin', 0, datetime('now'), datetime('now'))"
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


class TestAdminStats:
    def test_get_stats(self, client):
        resp = client.get("/api/admin/stats", headers=_h(_token()))
        assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.get("/api/admin/stats")
        assert resp.status_code == 401


class TestAdminUsers:
    def test_list_users(self, client):
        resp = client.get("/api/admin/users", headers=_h(_token()))
        assert resp.status_code == 200

    def test_get_user(self, client):
        resp = client.get("/api/admin/users/1", headers=_h(_token()))
        assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.get("/api/admin/users")
        assert resp.status_code == 401
