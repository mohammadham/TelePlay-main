"""Pytest configuration and shared fixtures for backend tests."""
import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_message():
    """Create a minimal fake pyrogram Message for testing."""
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
    """Create a minimal fake pyrogram CallbackQuery for testing."""
    cb = MagicMock()
    cb.from_user = MagicMock()
    cb.from_user.id = 123456789
    cb.data = "folder:1"
    cb.message = MagicMock()
    cb.message.edit = AsyncMock()
    cb.answer = AsyncMock()
    return cb


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture(autouse=True)
def patch_async_session(monkeypatch, mock_db_session):
    """Auto-patch async_session in bot module for all handler tests."""
    import backend.app.bot as bot_module
    monkeypatch.setattr(bot_module, "async_session", lambda: mock_db_session)
    return mock_db_session
