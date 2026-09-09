"""Pytest configuration and shared fixtures for TelePlay backend tests."""
import os
import pytest
from unittest.mock import MagicMock, AsyncMock
from cryptography.fernet import Fernet


# ── In-memory SQLite for all tests ───────────────────────────────────────────
@pytest.fixture(scope="session")
def database_url():
    """Override DATABASE_URL to use in-memory SQLite for tests."""
    return "sqlite+aiosqlite:///:memory:"


# ── Mock DB Session ──────────────────────────────────────────────────────────
@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def mock_message():
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 123456789
    msg.text = "/start"
    msg.command = ["start"]
    msg.chat = MagicMock()
    msg.chat.id = 123456789
    msg.reply = AsyncMock()
    return msg


@pytest.fixture
def mock_callback_query():
    cb = MagicMock()
    cb.from_user = MagicMock()
    cb.from_user.id = 123456789
    cb.data = "folder:1"
    cb.message = MagicMock()
    cb.message.edit = AsyncMock()
    cb.answer = AsyncMock()
    return cb


@pytest.fixture(autouse=True)
def patch_async_session(monkeypatch, mock_db_session):
    """Auto-patch async_session in bot module for handler tests."""
    try:
        import app.bot as bot_module
        monkeypatch.setattr(bot_module, "async_session", lambda: mock_db_session)
    except Exception:
        pass
    return mock_db_session


# ── Encryption key fixture ───────────────────────────────────────────────────
@pytest.fixture
def encryption_key():
    """Provide a fixed Fernet key for deterministic encryption tests."""
    return Fernet.generate_key()


# ── Settings override fixture ────────────────────────────────────────────────
@pytest.fixture
def settings_override(monkeypatch, database_url):
    """Override settings with test values."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "test-api-hash")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF-test-token")
    monkeypatch.setenv("CACHE_ENABLED", "true")
    monkeypatch.setenv("ADS_ENABLED", "true")
    monkeypatch.setenv("WEB_BASE_URL", "http://localhost:3000")


# ── Test client fixture ──────────────────────────────────────────────────────
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
