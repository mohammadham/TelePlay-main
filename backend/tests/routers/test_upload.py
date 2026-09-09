"""Integration tests for /api/upload endpoints."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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


class TestUpload:
    def test_upload(self, client):
        with patch("app.routers.upload.pool_manager.get_pool_client") as mock_pool:
            mock_client = MagicMock()
            mock_client.send_file = AsyncMock(return_value=MagicMock(message_id=100))
            mock_pool.return_value = mock_client

            resp = client.post(
                "/api/upload",
                data={"file_name": "test.txt", "file_type": "document"},
                headers=_h(_token())
            )
            assert resp.status_code in (200, 201)

    def test_auth_required(self, client):
        resp = client.post("/api/upload", data={})
        assert resp.status_code == 401


class TestSendToBot:
    def test_send_to_bot(self, client):
        with patch("app.routers.upload.tg_client") as mock_tg:
            mock_tg.send_file = AsyncMock(return_value=MagicMock(message_id=100))
            resp = client.post(
                "/api/upload/send-to-bot",
                json={"file_id": "test_file_id"},
                headers=_h(_token())
            )
            assert resp.status_code == 200

    def test_auth_required(self, client):
        resp = client.post("/api/upload/send-to-bot", json={})
        assert resp.status_code == 401
