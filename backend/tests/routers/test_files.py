"""Integration tests for /api/files endpoints."""
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
            # Insert test files
            await conn.execute(text(
                "INSERT OR IGNORE INTO files (user_id, folder_id, file_id, file_unique_id, channel_message_id, "
                "file_name, file_size, mime_type, file_type, duration, created_at, updated_at) VALUES "
                "(1, NULL, 'file1', 'uid1', 1001, 'movie.mkv', 1000000, 'video/x-matroska', 'video', 600, datetime('now'), datetime('now')),"
                "(1, NULL, 'file2', 'uid2', 1002, 'test_video.mp4', 2000000, 'video/mp4', 'video', 300, datetime('now'), datetime('now')),"
                "(1, NULL, 'file3', 'uid3', 1003, 'song.mp3', 500000, 'audio/mpeg', 'audio', 180, datetime('now'), datetime('now'))"
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


class TestListFiles:
    def test_returns_200_with_files_list(self, client):
        token = _make_token()
        resp = client.get("/api/files", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "files" in data
        assert "total" in data
        assert len(data["files"]) == 3

    def test_search_filters_by_filename(self, client):
        token = _make_token()
        resp = client.get("/api/files?search=test", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert any(f["file_name"] == "test_video.mp4" for f in data["files"])

    def test_file_type_filters_by_video(self, client):
        token = _make_token()
        resp = client.get("/api/files?file_type=video", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert all(f["file_type"] == "video" for f in data["files"])

    def test_pagination(self, client):
        token = _make_token()
        resp = client.get("/api/files?page=1&per_page=2", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["per_page"] == 2
        assert len(data["files"]) == 2


class TestFileCRUD:
    def test_create_file_returns_201(self, client):
        token = _make_token()
        with patch("app.routers.files.delete_from_storage_channel"):
            resp = client.post("/api/files", json={
                "file_name": "new_file.mp4",
                "file_size": 500000,
                "mime_type": "video/mp4",
                "file_type": "video",
                "file_id": "newid",
                "file_unique_id": "newuid",
                "channel_message_id": 9999,
            }, headers=_headers(token))
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_name"] == "new_file.mp4"
        assert data["file_type"] == "video"

    def test_get_file_returns_200(self, client):
        token = _make_token()
        resp = client.get("/api/files/1", headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["file_name"] == "movie.mkv"

    def test_update_file_returns_200(self, client):
        token = _make_token()
        resp = client.patch("/api/files/1", json={"file_name": "renamed.mkv"}, headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["file_name"] == "renamed.mkv"

    def test_delete_file_returns_200(self, client):
        token = _make_token()
        with patch("app.routers.files.delete_from_storage_channel"):
            resp = client.delete("/api/files/1", headers=_headers(token))
        assert resp.status_code == 200
        assert "message" in resp.json()
        # Verify deletion
        resp2 = client.get("/api/files/1", headers=_headers(token))
        assert resp2.status_code == 404


class TestFileNotFound:
    def test_get_nonexistent_file_returns_404(self, client):
        token = _make_token()
        resp = client.get("/api/files/999", headers=_headers(token))
        assert resp.status_code == 404


class TestFileBatch:
    def test_batch_delete_returns_200(self, client):
        token = _make_token()
        with patch("app.routers.files.delete_from_storage_channel"):
            resp = client.post("/api/files/batch-delete", json={"file_ids": [1, 2]}, headers=_headers(token))
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_batch_move_returns_200(self, client):
        token = _make_token()
        resp = client.post("/api/files/batch-move", json={"ids": [1], "folder_id": None}, headers=_headers(token))
        assert resp.status_code == 200
        assert "message" in resp.json()


class TestFileProgress:
    def test_update_progress_returns_200(self, client):
        token = _make_token()
        resp = client.post("/api/files/1/progress", json={"position": 30, "duration": 600}, headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["position"] == 30

    def test_get_progress_returns_200(self, client):
        token = _make_token()
        resp = client.get("/api/files/1/progress", headers=_headers(token))
        assert resp.status_code == 200
        assert "position" in resp.json()


class TestFileShare:
    def test_share_generates_hash(self, client):
        token = _make_token()
        resp = client.post("/api/files/1/share", headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["public_hash"] is not None
        assert len(resp.json()["public_hash"]) == 32

    def test_revoke_share_clears_hash(self, client):
        token = _make_token()
        # First share
        client.post("/api/files/1/share", headers=_headers(token))
        # Then revoke
        resp = client.delete("/api/files/1/share", headers=_headers(token))
        assert resp.status_code == 200
        assert resp.json()["public_hash"] is None


class TestAuthRequired:
    def test_list_files_returns_401_without_token(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 401

    def test_get_file_returns_401_without_token(self, client):
        resp = client.get("/api/files/1")
        assert resp.status_code == 401

    def test_create_file_returns_401_without_token(self, client):
        resp = client.post("/api/files", json={})
        assert resp.status_code == 401

    def test_update_file_returns_401_without_token(self, client):
        resp = client.patch("/api/files/1", json={})
        assert resp.status_code == 401

    def test_delete_file_returns_401_without_token(self, client):
        resp = client.delete("/api/files/1")
        assert resp.status_code == 401

    def test_batch_delete_returns_401_without_token(self, client):
        resp = client.post("/api/files/batch-delete", json={"file_ids": []})
        assert resp.status_code == 401

    def test_progress_returns_401_without_token(self, client):
        resp = client.post("/api/files/1/progress", json={})
        assert resp.status_code == 401

    def test_share_returns_401_without_token(self, client):
        resp = client.post("/api/files/1/share")
        assert resp.status_code == 401

    def test_revoke_share_returns_401_without_token(self, client):
        resp = client.delete("/api/files/1/share")
        assert resp.status_code == 401
