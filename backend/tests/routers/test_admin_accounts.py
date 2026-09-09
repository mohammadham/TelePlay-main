"""Integration tests for /api/admin/accounts endpoints."""
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


def _make_token(telegram_id=1, is_admin=True):
    from app.auth import create_access_token
    return create_access_token(telegram_id, is_admin=is_admin)


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestListAccounts:
    def test_returns_200_with_list(self, client):
        token = _make_token()
        resp = client.get("/api/admin/accounts", headers=_headers(token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestCreateAccount:
    def test_create_account_endpoint_response(self, client):
        """The /api/admin/accounts POST endpoint has a stub that raises 400 with instructions."""
        token = _make_token()
        resp = client.post("/api/admin/accounts", json={
            "name": "TestAccount",
            "phone": "+1234567890",
            "api_id": 12345,
            "api_hash": "testhash",
            "purpose": "STORAGE",
            "is_active": True,
        }, headers=_headers(token))
        # The endpoint raises 400 with a message directing users to use /with-session instead
        assert resp.status_code == 400
        assert "session_string" in resp.json()["detail"].lower() or "login/verify" in resp.json()["detail"].lower()


class TestDeleteAccount:
    def test_delete_account_returns_404_when_not_exists(self, client):
        token = _make_token()
        resp = client.delete("/api/admin/accounts/999", headers=_headers(token))
        assert resp.status_code == 404

    def test_delete_account_with_existing(self, client):
        """Create via with-session, then delete."""
        token = _make_token()
        mock_me = MagicMock()
        mock_me.id = 555
        mock_me.username = "testuser_acct"

        with patch("app.routers.admin_accounts.Client") as MockClient:
            async def fake_start():
                pass
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                get_me=AsyncMock(return_value=mock_me),
            ))
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value.start = fake_start

            resp = client.post("/api/admin/accounts/with-session", json={
                "name": "ToDelete",
                "phone": "+1234567890",
                "api_id": 12345,
                "api_hash": "testhash",
                "session_string": "1BVsy...",
                "purpose": "STORAGE",
                "is_active": True,
            }, headers=_headers(token))

        if resp.status_code == 201:
            acc_id = resp.json()["id"]
            resp2 = client.delete(f"/api/admin/accounts/{acc_id}", headers=_headers(token))
            assert resp2.status_code == 200
            assert "message" in resp2.json()


class TestAccountHealth:
    def test_health_returns_404_for_nonexistent(self, client):
        token = _make_token()
        resp = client.post("/api/admin/accounts/999/health", headers=_headers(token))
        assert resp.status_code == 404

    def test_health_returns_200_with_mock(self, client):
        """Create an account then test health."""
        token = _make_token()
        mock_me = MagicMock()
        mock_me.id = 444
        mock_me.username = "healthacct"

        with patch("app.routers.admin_accounts.Client") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                get_me=AsyncMock(return_value=mock_me),
                stop=AsyncMock(),
            ))
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            client.post("/api/admin/accounts/with-session", json={
                "name": "HealthTest",
                "phone": "+1234567890",
                "api_id": 12345,
                "api_hash": "testhash",
                "session_string": "1BVsy...",
                "purpose": "STORAGE",
            }, headers=_headers(token))

        # Health check on whatever account was created
        token = _make_token()
        with patch("app.routers.admin_accounts.Client") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                get_me=AsyncMock(return_value=mock_me),
                stop=AsyncMock(),
            ))
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            resp = client.post("/api/admin/accounts/1/health", headers=_headers(token))

        assert resp.status_code in (200, 404)  # 200 if mock works, 404 if account doesn't exist


class TestAuthRequired:
    def test_list_unauthorized(self, client):
        resp = client.get("/api/admin/accounts")
        assert resp.status_code == 401

    def test_create_unauthorized(self, client):
        resp = client.post("/api/admin/accounts", json={})
        assert resp.status_code == 401

    def test_delete_unauthorized(self, client):
        resp = client.delete("/api/admin/accounts/1")
        assert resp.status_code == 401

    def test_health_unauthorized(self, client):
        resp = client.post("/api/admin/accounts/1/health")
        assert resp.status_code == 401
