"""Integration tests for /api/folders endpoints."""
import pytest
from unittest.mock import patch
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
            # Insert test folders
            await conn.execute(text(
                "INSERT OR IGNORE INTO folders (user_id, parent_id, name, created_at, updated_at) VALUES "
                "(1, NULL, 'Movies', datetime('now'), datetime('now')),"
                "(1, NULL, 'Music', datetime('now'), datetime('now')),"
                "(1, 1, 'Action', datetime('now'), datetime('now'))"
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


class TestListFolders:
    def test_returns_200_with_list(self, client):
        token = _make_token()
        resp = client.get("/api/folders", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2  # Movies, Music (top-level only)

    def test_list_with_parent_filter(self, client):
        token = _make_token()
        resp = client.get("/api/folders?parent_id=1", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Action"


class TestCreateFolder:
    def test_create_folder_returns_201(self, client):
        token = _make_token()
        resp = client.post("/api/folders", json={"name": "New Folder", "parent_id": None}, headers=_headers(token))
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Folder"
        assert data["parent_id"] is None

    def test_create_folder_with_parent_returns_201(self, client):
        token = _make_token()
        resp = client.post("/api/folders", json={"name": "Comedy", "parent_id": 1}, headers=_headers(token))
        assert resp.status_code == 201
        assert resp.json()["parent_id"] == 1

    def test_create_duplicate_folder_returns_400(self, client):
        token = _make_token()
        resp = client.post("/api/folders", json={"name": "Movies", "parent_id": None}, headers=_headers(token))
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]


class TestUpdateFolder:
    def test_update_folder_returns_200(self, client):
        token = _make_token()
        resp = client.patch("/api/folders/1", json={"name": "Renamed Movies"}, headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Movies"

    def test_update_folder_move_returns_200(self, client):
        token = _make_token()
        resp = client.patch("/api/folders/3", json={"parent_id": 2}, headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["parent_id"] == 2


class TestDeleteFolder:
    def test_delete_folder_returns_200(self, client):
        token = _make_token()
        with patch("app.routers.folders.delete_from_storage_channel"):
            resp = client.delete("/api/folders/3", headers=_headers(token))
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_delete_folder_with_move_files_returns_200(self, client):
        token = _make_token()
        with patch("app.routers.folders.delete_from_storage_channel"):
            resp = client.delete("/api/folders/1?move_files_to=2", headers=_headers(token))
        assert resp.status_code == 200


class TestFolderNotFound:
    def test_get_nonexistent_folder_returns_404(self, client):
        token = _make_token()
        resp = client.get("/api/folders/999", headers=_headers(token))
        assert resp.status_code == 404


class TestFolderTree:
    def test_returns_tree_structure(self, client):
        token = _make_token()
        resp = client.get("/api/folders/tree", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        roots = [f for f in data if f["parent_id"] is None]
        assert len(roots) == 2  # Movies, Music

    def test_nested_children_present(self, client):
        token = _make_token()
        resp = client.get("/api/folders/tree", headers=_headers(token))
        data = resp.json()
        movies = next((f for f in data if f["name"] == "Movies"), None)
        assert movies is not None
        assert len(movies["children"]) == 1
        assert movies["children"][0]["name"] == "Action"


class TestFolderBatch:
    def test_batch_delete_returns_200(self, client):
        token = _make_token()
        with patch("app.routers.folders.delete_from_storage_channel"):
            resp = client.post("/api/folders/batch-delete", json=[1, 2], headers=_headers(token))
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_batch_move_returns_200(self, client):
        token = _make_token()
        resp = client.post("/api/folders/batch-move", json={"ids": [1, 2], "folder_id": None}, headers=_headers(token))
        assert resp.status_code == 200
        assert "message" in resp.json()


class TestAuthRequired:
    def test_list_unauthorized(self, client):
        resp = client.get("/api/folders")
        assert resp.status_code == 401

    def test_create_unauthorized(self, client):
        resp = client.post("/api/folders", json={"name": "X"})
        assert resp.status_code == 401

    def test_patch_unauthorized(self, client):
        resp = client.patch("/api/folders/1", json={"name": "X"})
        assert resp.status_code == 401

    def test_delete_unauthorized(self, client):
        resp = client.delete("/api/folders/1")
        assert resp.status_code == 401

    def test_tree_unauthorized(self, client):
        resp = client.get("/api/folders/tree")
        assert resp.status_code == 401

    def test_batch_delete_unauthorized(self, client):
        resp = client.post("/api/folders/batch-delete", json=[1])
        assert resp.status_code == 401

    def test_batch_move_unauthorized(self, client):
        resp = client.post("/api/folders/batch-move", json={"ids": [1], "folder_id": None})
        assert resp.status_code == 401
