"""Integration tests for /api/stream endpoints."""
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
            # Insert a test file
            await conn.execute(text(
                "INSERT OR IGNORE INTO files (user_id, file_id, file_unique_id, channel_message_id, file_name, file_size, mime_type, file_type, duration, width, height, created_at, updated_at) "
                "VALUES (1, 'test_file_id', 'test_unique_id', 100, 'test.mp4', 1024, 'video/mp4', 'video', 60, 1920, 1080, datetime('now'), datetime('now'))"
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


class TestStreamFile:
    def test_stream_file(self, client):
        with patch("app.routers.streaming.telegram.get_message_from_channel") as mock_msg:
            mock_msg.return_value = MagicMock()
            mock_msg.return_value.document = MagicMock()
            mock_msg.return_value.document.mime_type = "video/mp4"
            mock_msg.return_value.document.size = 1024

            resp = client.get("/api/stream/1", headers=_h(_token()))
            # Should return 200 or stream response
            assert resp.status_code in (200, 206)

    def test_file_not_found(self, client):
        resp = client.get("/api/stream/999", headers=_h(_token()))
        assert resp.status_code == 404

    def test_auth_required(self, client):
        resp = client.get("/api/stream/1")
        assert resp.status_code == 401


class TestThumbnail:
    def test_thumbnail(self, client):
        resp = client.get("/api/stream/1/thumbnail", headers=_h(_token()))
        assert resp.status_code in (200, 404)


class TestPublicStream:
    def test_public_stream(self, client):
        resp = client.get("/api/stream/s/testhash")
        assert resp.status_code in (200, 404)
