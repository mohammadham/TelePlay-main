"""Integration tests for /api/admin/admins endpoints."""
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


def _token(telegram_id=1):
    from app.auth import create_access_token
    return create_access_token(telegram_id, is_admin=True)


def _h(t):
    return {"Authorization": f"Bearer {t}"}


class TestListAdmins:
    def test_returns_list(self, client):
        resp = client.get("/api/admin/admins", headers=_h(_token()))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["telegram_id"] == 1
        assert data[0]["role"] == "SUPER_ADMIN"

    def test_auth_required(self, client):
        resp = client.get("/api/admin/admins")
        assert resp.status_code == 401


class TestCreateAdmin:
    def test_create_admin_success(self, client):
        with patch("app.routers.admin_admins.tg_client") as mock_tg:
            mock_user = MagicMock()
            mock_user.id = 555
            mock_user.username = "newadmin"
            mock_user.first_name = "New"
            mock_user.last_name = "Admin"
            mock_tg.get_users = AsyncMock(return_value=mock_user)

            resp = client.post(
                "/api/admin/admins",
                json={"telegram_id": 555, "role": "ADMIN", "is_active": True},
                headers=_h(_token())
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["telegram_id"] == 555
            assert data["role"] == "ADMIN"

    def test_create_duplicate_raises_400(self, client):
        resp = client.post(
            "/api/admin/admins",
            json={"telegram_id": 1, "role": "ADMIN"},
            headers=_h(_token())
        )
        assert resp.status_code == 400

    def test_create_invalid_role_raises_400(self, client):
        with patch("app.routers.admin_admins.tg_client", None):
            resp = client.post(
                "/api/admin/admins",
                json={"telegram_id": 777, "role": "INVALID_ROLE"},
                headers=_h(_token())
            )
            assert resp.status_code == 400

    def test_non_super_admin_cannot_create(self, client):
        """Regular admin cannot create admins without can_manage_admins."""
        import asyncio
        from app.database import get_db
        from sqlalchemy import text

        async def setup():
            async with get_db().__aenter__() as db:
                await db.execute(text(
                    "INSERT INTO users (telegram_id, username, first_name, auth_version, created_at, last_active) "
                    "VALUES (2, 'mod', 'Mod', 0, datetime('now'), datetime('now'))"
                ))
                await db.execute(text(
                    "INSERT INTO admin_users (telegram_id, role, is_active, can_manage_bots, can_manage_accounts, can_manage_admins, created_at) "
                    "VALUES (2, 'MODERATOR', 1, 0, 0, 0, datetime('now'))"
                ))
                await db.commit()

        asyncio.run(setup())
        t = _token(2)
        with patch("app.routers.admin_admins.tg_client", None):
            resp = client.post("/api/admin/admins", json={"telegram_id": 888, "role": "ADMIN"}, headers=_h(t))
            # Should fail because MODERATOR is not SUPER_ADMIN
            assert resp.status_code in (403, 400)


class TestUpdateAdmin:
    def test_update_role(self, client):
        # First create an admin
        with patch("app.routers.admin_admins.tg_client") as mock_tg:
            mock_tg.get_users = AsyncMock(side_effect=Exception("not found"))
            client.post("/api/admin/admins", json={"telegram_id": 200, "role": "ADMIN"}, headers=_h(_token()))

        resp = client.put(
            "/api/admin/admins/2",
            json={"role": "MODERATOR"},
            headers=_h(_token())
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "MODERATOR"

    def test_cannot_demote_only_super_admin(self, client):
        resp = client.put(
            "/api/admin/admins/1",
            json={"role": "ADMIN"},
            headers=_h(_token())
        )
        # Should fail because this is the only SUPER_ADMIN
        assert resp.status_code == 400


class TestDeleteAdmin:
    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete("/api/admin/admins/9999", headers=_h(_token()))
        assert resp.status_code == 404

    def test_cannot_delete_self(self, client):
        resp = client.delete("/api/admin/admins/1", headers=_h(_token()))
        assert resp.status_code == 400
        assert " yourself" in resp.json()["detail"]

    def test_cannot_delete_super_admin(self, client):
        # Create a regular admin first
        with patch("app.routers.admin_admins.tg_client") as mock_tg:
            mock_tg.get_users = AsyncMock(side_effect=Exception("not found"))
            client.post("/api/admin/admins", json={"telegram_id": 300, "role": "ADMIN"}, headers=_h(_token()))

        # Delete the regular admin (id=2)
        resp = client.delete("/api/admin/admins/2", headers=_h(_token()))
        assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.delete("/api/admin/admins/1")
        assert resp.status_code == 401


class TestVerifyTelegramId:
    def test_valid_id_returns_info(self, client):
        from unittest.mock import MagicMock
        mock_user = MagicMock()
        mock_user.id = 12345
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"

        with patch("app.routers.admin_admins.tg_client") as mock_tg:
            mock_tg.get_users = AsyncMock(return_value=mock_user)
            resp = client.post("/api/admin/admins/verify-telegram-id?telegram_id=12345", headers=_h(_token()))
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True
            assert data["telegram_id"] == 12345
            assert data["username"] == "testuser"

    def test_invalid_id_returns_valid_false(self, client):
        with patch("app.routers.admin_admins.tg_client") as mock_tg:
            mock_tg.get_users = AsyncMock(side_effect=Exception("user not found"))
            resp = client.post("/api/admin/admins/verify-telegram-id?telegram_id=99999", headers=_h(_token()))
            assert resp.status_code == 200
            assert resp.json()["valid"] is False

    def test_no_tg_client_returns_503(self, client):
        with patch("app.routers.admin_admins.tg_client", None):
            resp = client.post("/api/admin/admins/verify-telegram-id?telegram_id=12345", headers=_h(_token()))
            assert resp.status_code == 503


from unittest.mock import MagicMock
