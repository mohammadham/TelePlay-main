"""Unit tests for Telegram bot handlers and rate limiting."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCheckInlineRateLimit:
    """Tests for inline query rate limiter."""

    def test_first_query_allowed(self):
        from app.bot import check_inline_rate_limit
        assert check_inline_rate_limit(123) is True

    def test_second_query_allowed(self):
        from app.bot import check_inline_rate_limit
        check_inline_rate_limit(123)
        assert check_inline_rate_limit(123) is True

    def test_exceeds_limit_blocked(self):
        from app.bot import check_inline_rate_limit, _INLINE_QUERY_MAX_PER_MINUTE
        # Fill up the limit
        for _ in range(_INLINE_QUERY_MAX_PER_MINUTE):
            check_inline_rate_limit(456)
        # Next should be blocked
        assert check_inline_rate_limit(456) is False

    def test_different_users_independent(self):
        from app.bot import check_inline_rate_limit, _INLINE_QUERY_MAX_PER_MINUTE
        # Fill user 1's quota
        for _ in range(_INLINE_QUERY_MAX_PER_MINUTE):
            check_inline_rate_limit(1)
        # User 2 should still be allowed
        assert check_inline_rate_limit(2) is True

    def test_expired_entries_pruned(self):
        """Entries older than 60 seconds should be pruned automatically."""
        from app.bot import check_inline_rate_limit, _inline_query_rates
        # Manually add old timestamps
        import time
        old_time = time.time() - 120  # 2 minutes ago
        _inline_query_rates[999] = [old_time, old_time + 1]
        # Should be allowed after pruning
        assert check_inline_rate_limit(999) is True
        # And the old entries should be removed
        assert len(_inline_query_rates[999]) == 1


class TestSanitizeInBot:
    """Test that sanitize functions work correctly in bot context."""

    def test_sanitize_text_strips_html(self):
        from app.bot import sanitize_text
        result = sanitize_text("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "alert" in result

    def test_sanitize_filename_strips_path_traversal(self):
        from app.bot import sanitize_filename
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result

    def test_sanitize_text_empty(self):
        from app.bot import sanitize_text
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""

    def test_sanitize_filename_empty(self):
        from app.bot import sanitize_filename
        assert sanitize_filename("") == "unnamed_file"


class TestNewfolderCommand:
    """Test newfolder command handler."""

    @pytest.mark.asyncio
    async def test_create_folder_success(self, monkeypatch, mock_message, mock_db_session):
        """Test successful folder creation via /newfolder command."""
        # Setup mock database responses
        mock_user = MagicMock()
        mock_user.id = 1
        mock_folder = MagicMock()
        mock_folder.id = 1
        mock_folder.name = "Test Folder"

        # Mock execute to return appropriate values
        async def mock_execute(stmt):
            class ScalarResult:
                def scalar_one_or_none(self):
                    # Check if this is a folder lookup
                    stmt_str = str(stmt)
                    if "folders" in stmt_str and "name" in stmt_str:
                        return None  # Folder doesn't exist
                    elif "users" in stmt_str:
                        return mock_user
                    return None
            return ScalarResult()

        mock_db_session.execute = mock_execute
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        # Patch the command handler
        from app.bot import newfolder_command
        mock_message.command = ["newfolder", "Test Folder"]
        mock_message.text = "/newfolder Test Folder"

        await newfolder_command(None, mock_message)

        # Verify reply was called
        mock_message.reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_newfolder_without_args(self, monkeypatch, mock_message):
        """Test /newfolder without arguments shows usage."""
        from app.bot import newfolder_command
        mock_message.command = ["newfolder"]
        mock_message.text = "/newfolder"

        await newfolder_command(None, mock_message)

        # Should show usage message
        mock_message.reply.assert_called_once()
        call_args = mock_message.reply.call_args[0][0]
        assert "Usage" in call_args or "newfolder" in call_args.lower()


class TestFileRenameSanitization:
    """Test that file renames are sanitized."""

    @pytest.mark.asyncio
    async def test_file_rename_sanitizes_name(self, monkeypatch, mock_callback_query, mock_db_session):
        """Test that file rename applies sanitization."""
        from app.bot import handle_callback

        # Setup mocks
        mock_file = MagicMock()
        mock_file.id = 1
        mock_file.file_name = "original.mp4"

        executed_statements = []

        async def mock_execute(stmt):
            executed_statements.append(stmt)
            class Result:
                def scalar_one_or_none(self):
                    return mock_file
            return Result()

        mock_db_session.execute = mock_execute
        mock_db_session.commit = AsyncMock()

        # Simulate rename callback
        mock_callback_query.data = "renamefile:1"
        mock_callback_query.message.reply = AsyncMock()

        # Patch wait_for_message to return a malicious name
        with patch('app.bot.tg_client.wait_for_message', new_callable=AsyncMock) as mock_wait:
            fake_reply = MagicMock()
            fake_reply.text = "<script>alert(1)</script>"
            fake_reply.startswith = MagicMock(return_value=False)
            mock_wait.return_value = fake_reply

            await handle_callback(None, mock_callback_query)

        # Verify the file name was sanitized (not stored as raw HTML)
        # The sanitize_filename should have stripped the script tags
        assert mock_file.file_name != "<script>alert(1)</script>"


class TestFolderRenameSanitization:
    """Test that folder renames are sanitized."""

    @pytest.mark.asyncio
    async def test_folder_rename_sanitizes_name(self, monkeypatch, mock_callback_query, mock_db_session):
        """Test that folder rename applies sanitization."""
        from app.bot import handle_callback

        # Setup mocks
        mock_folder = MagicMock()
        mock_folder.id = 1
        mock_folder.name = "original"

        async def mock_execute(stmt):
            class Result:
                def scalar_one_or_none(self):
                    return mock_folder
            return Result()

        mock_db_session.execute = mock_execute
        mock_db_session.commit = AsyncMock()

        # Simulate folder rename callback
        mock_callback_query.data = "renamefolder:1"
        mock_callback_query.message.reply = AsyncMock()

        # Patch wait_for_message to return a malicious name
        with patch('app.bot.tg_client.wait_for_message', new_callable=AsyncMock) as mock_wait:
            fake_reply = MagicMock()
            fake_reply.text = "evil<script>folder</script>"
            fake_reply.startswith = MagicMock(return_value=False)
            mock_wait.return_value = fake_reply

            await handle_callback(None, mock_callback_query)

        # Verify the folder name was sanitized
        assert "script" not in mock_folder.name.lower()
