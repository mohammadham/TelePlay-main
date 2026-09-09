"""Integration tests for /api/auth endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(database_url, settings_override):
    from app.main import app
    from app.database import engine, async_session, Base
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    test_engine = create_async_engine(database_url, echo=False)
    maker = async_sessionmaker(test_engine, expire_on_commit=False)

    from app.database import get_db
    app.dependency_overrides[get_db] = lambda: _db_gen(maker)

    import asyncio
    asyncio.run(Base.metadata.create_all(test_engine))

    # Create test user
    async def seed():
        async with test_engine.begin() as conn:
            await conn.execute(text(
                "INSERT OR IGNORE INTO users (telegram_id, username, first_name, auth_version, created_at, last_active) "
                "VALUES (1, 'testuser', 'Test', 0, datetime('now'), datetime('now'))"
            ))
            await conn.execute(text(
                "INSERT OR IGNORE INTO admin_users (telegram_id, role, is_active, created_at) "
                "VALUES (1, 'SUPER_ADMIN', 1, datetime('now'))"
            ))
            await conn.commit()

    asyncio.run(seed())

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _db_gen(maker):
    async def gen():
        async with maker() as s:
            yield s
    return gen


def _make_token(telegram_id=1, is_admin=False):
    from app.auth import create_access_token
    return create_access_token(telegram_id, is_admin=is_admin)


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestGenerateCode:
    def test_returns_code_and_expiry(self, client):
        resp = client.post("/api/auth/generate-code")
        assert resp.status_code == 200
        data = resp.json()
        assert "code" in data
        assert "expires_at" in data
        assert len(data["code"]) == 6

    def test_code_is_alphanumeric(self, client):
        resp = client.post("/api/auth/generate-code")
        code = resp.json()["code"]
        assert code.isalnum()


class TestVerifyCode:
    def test_invalid_code_returns_400(self, client):
        resp = client.post("/api/auth/verify-code", json={"code": "XXXXXX"})
        assert resp.status_code == 400

    def test_expired_code_returns_400(self, client):
        from app.models import LoginCode
        from datetime import datetime, timedelta
        import asyncio
        from app.database import get_db

        async def insert_expired():
            async with get_db().__aenter__() as db:
                code = LoginCode(code="EXPIR", telegram_id=1,
                                 expires_at=datetime.utcnow() - timedelta(minutes=10))
                db.add(code)
                await db.commit()

        asyncio.run(insert_expired())

        resp = client.post("/api/auth/verify-code", json={"code": "EXPIR"})
        assert resp.status_code == 400


class TestMe:
    def test_returns_user_info(self, client):
        token = _make_token(1, is_admin=True)
        resp = client.get("/api/auth/me", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["telegram_id"] == 1
        assert data["username"] == "testuser"
        assert data["is_admin"] is True

    def test_returns_is_admin_false_for_regular_user(self, client):
        import asyncio
        from app.database import get_db
        from sqlalchemy import text

        async def add_regular_user():
            async with get_db().__aenter__() as db:
                await db.execute(text(
                    "INSERT INTO users (telegram_id, username, first_name, auth_version, created_at, last_active) "
                    "VALUES (999, 'regular', 'Regular', 0, datetime('now'), datetime('now'))"
                ))
                await db.commit()

        asyncio.run(add_regular_user())

        token = _make_token(999, is_admin=False)
        resp = client.get("/api/auth/me", headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is False

    def test_unauthorized_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_unauthorized_with_bad_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer bad-token"})
        assert resp.status_code == 401


class TestRefreshToken:
    def test_refresh_returns_new_tokens(self, client):
        from app.auth import create_refresh_token
        refresh = create_refresh_token(1)
        resp = client.post("/api/auth/refresh", json={"refreshToken": refresh})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token_returns_401(self, client):
        resp = client.post("/api/auth/refresh", json={"refreshToken": "bad-refresh"})
        assert resp.status_code == 401


class TestLogoutAll:
    def test_logout_all_increments_version(self, client):
        token = _make_token(1, is_admin=True)
        resp = client.post("/api/auth/logout-all", headers=_headers(token))
        assert resp.status_code == 200

        # Old token should now be invalid
        resp2 = client.get("/api/auth/me", headers=_headers(token))
        assert resp2.status_code == 401


class TestBotInfo:
    def test_returns_info_without_auth(self, client):
        resp = client.get("/api/auth/bot/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "server_version" in data
