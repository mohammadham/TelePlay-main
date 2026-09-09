"""Integration tests for /api/admin/settings endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture
def client(database_url, settings_override):
    """Create test client with in-memory SQLite."""
    from app.main import app
    from app.database import engine, async_session, Base

    # Drop all tables and recreate with test URL
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    test_engine = create_async_engine(database_url, echo=False)
    maker = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[lambda: None]  # workaround
    from app.database import get_db
    app.dependency_overrides[get_db] = override_get_db

    # Create tables
    import asyncio
    asyncio.run(Base.metadata.create_all(test_engine))

    # Seed settings
    async def seed():
        async with test_engine.begin() as conn:
            for key, (default, desc) in {
                "TELEGRAM_API_ID": ("", "From my.telegram.org"),
                "TELEGRAM_API_HASH": ("", "From my.telegram.org"),
                "TELEGRAM_BOT_TOKEN": ("", "From @BotFather"),
                "TELEGRAM_STORAGE_CHANNEL_ID": ("", "Private channel -100..."),
                "JWT_SECRET": ("", "openssl rand -hex 32"),
                "WEB_BASE_URL": ("", "https://your-domain.com"),
                "CACHE_ENABLED": ("true", "true/false"),
                "VIDEO_CACHE_ENABLED": ("true", "true/false"),
                "ADS_ENABLED": ("true", "true/false"),
            }.items():
                await conn.execute(text(
                    "INSERT OR IGNORE INTO app_settings (key, value, description) VALUES (:k, :v, :d)"
                ), {"k": key, "v": default, "d": desc})
            await conn.commit()

    asyncio.run(seed())

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _make_admin_token():
    from app.auth import create_access_token
    return create_access_token(1, is_admin=True)


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestListSettings:
    def test_returns_template_keys(self, client):
        token = _make_admin_token()
        resp = client.get("/api/admin/settings", headers=_auth_headers(token))
        assert resp.status_code == 200
        keys = {r["key"] for r in resp.json()}
        expected = {"TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_BOT_TOKEN",
                     "TELEGRAM_STORAGE_CHANNEL_ID", "JWT_SECRET", "WEB_BASE_URL",
                     "CACHE_ENABLED", "VIDEO_CACHE_ENABLED", "ADS_ENABLED"}
        assert keys == expected

    def test_no_upload_keys_present(self, client):
        """Removed keys should not appear in response."""
        token = _make_admin_token()
        resp = client.get("/api/admin/settings", headers=_auth_headers(token))
        keys = {r["key"] for r in resp.json()}
        removed = {"MY_MUSIC_ENABLED", "UPLOAD_STRATEGY", "WEB_UPLOAD_ENABLED",
                   "BOT_FALLBACK_ENABLED", "MAX_CONCURRENT_UPLOADS", "ADMIN_TELEGRAM_IDS"}
        assert keys.isdisjoint(removed)

    def test_each_item_has_required_fields(self, client):
        token = _make_admin_token()
        resp = client.get("/api/admin/settings", headers=_auth_headers(token))
        for item in resp.json():
            assert "key" in item
            assert "value" in item
            assert "description" in item
            assert "is_set" in item

    def test_auth_required(self, client):
        resp = client.get("/api/admin/settings")
        assert resp.status_code == 401


class TestUpdateSettings:
    def test_update_existing_key(self, client):
        token = _make_admin_token()
        resp = client.put(
            "/api/admin/settings",
            json={"CACHE_ENABLED": "false"},
            headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "changed" in data
        assert "CACHE_ENABLED" in data["changed"]

    def test_update_multiple_keys(self, client):
        token = _make_admin_token()
        resp = client.put(
            "/api/admin/settings",
            json={"CACHE_ENABLED": "false", "ADS_ENABLED": "false"},
            headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "CACHE_ENABLED" in data["changed"]
        assert "ADS_ENABLED" in data["changed"]

    def test_create_new_key(self, client):
        token = _make_admin_token()
        resp = client.put(
            "/api/admin/settings",
            json={"CUSTOM_KEY": "custom_value"},
            headers=_auth_headers(token)
        )
        assert resp.status_code == 200
        assert "CUSTOM_KEY" in resp.json()["changed"]

    def test_auth_required(self, client):
        resp = client.put("/api/admin/settings", json={"CACHE_ENABLED": "false"})
        assert resp.status_code == 401


class TestExportEnv:
    def test_returns_env_format(self, client):
        token = _make_admin_token()
        resp = client.get("/api/admin/settings/export", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "env" in data
        assert "TELEGRAM_API_ID=" in data["env"]
        assert "JWT_SECRET=" in data["env"]

    def test_auth_required(self, client):
        resp = client.get("/api/admin/settings/export")
        assert resp.status_code == 401


class TestSeedTemplate:
    def test_seed_is_idempotent(self, client):
        token = _make_admin_token()
        resp1 = client.post("/api/admin/settings/seed", headers=_auth_headers(token))
        assert resp1.status_code == 200
        resp2 = client.post("/api/admin/settings/seed", headers=_auth_headers(token))
        assert resp2.status_code == 200

    def test_auth_required(self, client):
        resp = client.post("/api/admin/settings/seed")
        assert resp.status_code == 401


class TestReloadSettings:
    def test_reload_returns_ok(self, client):
        token = _make_admin_token()
        resp = client.post("/api/admin/settings/reload", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_auth_required(self, client):
        resp = client.post("/api/admin/settings/reload")
        assert resp.status_code == 401
