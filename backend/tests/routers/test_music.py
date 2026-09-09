"""Integration tests for /api/v1/music endpoints."""
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
                "INSERT OR IGNORE INTO admin_users (telegram_id, role, is_active, can_manage_bots, can_manage_accounts, can_manage_admins, created_at) "
                "VALUES (1, 'SUPER_ADMIN', 1, 1, 1, 1, datetime('now'))"
            ))
            await conn.execute(text(
                "INSERT OR IGNORE INTO app_settings (key, value, description) VALUES ('JWT_SECRET', 'test-secret', 'JWT secret')"
            ))
            # Seed music data
            await conn.execute(text(
                "INSERT OR IGNORE INTO artists (name, bio, verified, created_at) VALUES ('Test Artist', 'Bio', 0, datetime('now'))"
            ))
            await conn.execute(text(
                "INSERT OR IGNORE INTO tracks (title, artist_id, file_id, duration, play_count, like_count, media_type, created_at) VALUES ('Test Track', 1, 1, 180, 10, 5, 'audio', datetime('now'))"
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


class TestListTracks:
    def test_returns_tracks(self, client):
        resp = client.get("/api/v1/music/tracks", headers=_h(_token()))
        assert resp.status_code == 200
        # Should be JSON response (not Response object)
        data = resp.json()
        assert isinstance(data, list)

    def test_auth_required(self, client):
        resp = client.get("/api/v1/music/tracks")
        assert resp.status_code == 401


class TestGetTrack:
    def test_returns_track(self, client):
        resp = client.get("/api/v1/music/tracks/1", headers=_h(_token()))
        assert resp.status_code == 200

    def test_not_found(self, client):
        resp = client.get("/api/v1/music/tracks/999", headers=_h(_token()))
        assert resp.status_code == 404


class TestListArtists:
    def test_returns_artists(self, client):
        resp = client.get("/api/v1/music/artists", headers=_h(_token()))
        assert resp.status_code == 200


class TestSearch:
    def test_search_tracks(self, client):
        resp = client.get("/api/v1/music/search?q=test", headers=_h(_token()))
        assert resp.status_code == 200


class TestPlaylists:
    def test_create_playlist(self, client):
        resp = client.post(
            "/api/v1/music/playlists",
            json={"title": "My Playlist"},
            headers=_h(_token())
        )
        assert resp.status_code == 201

    def test_list_playlists(self, client):
        resp = client.get("/api/v1/music/playlists", headers=_h(_token()))
        assert resp.status_code == 200


class TestLikes:
    def test_like_track(self, client):
        resp = client.post("/api/v1/music/likes/1", headers=_h(_token()))
        assert resp.status_code == 200

    def test_unlike_track(self, client):
        resp = client.delete("/api/v1/music/likes/1", headers=_h(_token()))
        assert resp.status_code == 200


class TestHistory:
    def test_add_history(self, client):
        resp = client.post(
            "/api/v1/music/history",
            json={"track_id": 1, "position": 0},
            headers=_h(_token())
        )
        assert resp.status_code == 200

    def test_get_history(self, client):
        resp = client.get("/api/v1/music/history", headers=_h(_token()))
        assert resp.status_code == 200
