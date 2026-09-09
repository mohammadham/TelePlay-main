"""Unit tests for security/sanitization functions."""
import pytest
from app.services import sanitize_filename, sanitize_text, escape_like


class TestSanitizeText:
    def test_strips_html_tags(self):
        assert sanitize_text("<script>alert(1)</script>") == "alert(1)"
        assert sanitize_text('<div class="x" onclick="evil()">hello</div>') == "hello"

    def test_strips_html_entities(self):
        assert sanitize_text("&lt;script&gt;") == ""
        assert sanitize_text("a &amp; b") == "a  b"

    def test_removes_xss_payloads(self):
        assert sanitize_text('<img src=x onerror=alert(1)>') == ""
        assert sanitize_text('<iframe src="evil.com">') == ""
        assert sanitize_text('<body onload=alert(1)>') == ""

    def test_removes_dangerous_chars(self):
        assert sanitize_text('test "quoted"') == "test quoted"
        assert sanitize_text("a & b") == "a  b"

    def test_removes_control_chars(self):
        assert sanitize_text("hello\x00world") == "helloworld"
        assert sanitize_text("hello\x1fworld") == "helloworld"

    def test_trims_whitespace(self):
        assert sanitize_text("  hello  ") == "hello"

    def test_limits_length(self):
        long_name = "a" * 300
        result = sanitize_text(long_name)
        assert len(result) == 255

    def test_empty_input(self):
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""

    def test_mixed_payload(self):
        payload = "<script>alert('xss')</script>&nbsp;&lt;b&gt;bold&lt;/b&gt;"
        result = sanitize_text(payload)
        assert "<" not in result
        assert ">" not in result
        assert "script" not in result

    def test_normal_text_unchanged(self):
        assert sanitize_text("مرحبه دنیا") == "مرحبه دنیا"
        assert sanitize_text("Hello World 123") == "Hello World 123"

    def test_sql_injection_in_text(self):
        # SQL injection in text context should be stripped of special chars
        result = sanitize_text("'; DROP TABLE users; --")
        assert "DROP" not in result
        assert ";" not in result


class TestSanitizeFilename:
    def test_strips_path_separators(self):
        assert sanitize_filename("folder/file.txt") == "folder_file.txt"
        assert sanitize_filename("folder\\file.txt") == "folder_file.txt"

    def test_removes_dangerous_chars(self):
        result = sanitize_filename('<>:"|?*')
        assert "<" not in result and ">" not in result
        assert ":" not in result and '"' not in result

    def test_strips_null_bytes(self):
        assert sanitize_filename("test\x00name") == "testname"

    def test_strips_leading_trailing_dots_and_spaces(self):
        assert sanitize_filename("  hello  ") == "hello"
        assert sanitize_filename(".hidden") == "hidden"

    def test_limits_length(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 255

    def test_preserves_extension(self):
        long_name = "a" * 250 + ".mp4"
        result = sanitize_filename(long_name)
        assert result.endswith(".mp4")

    def test_empty_input(self):
        assert sanitize_filename("") == "unnamed_file"
        assert sanitize_filename(None) == "unnamed_file"

    def test_normal_text_unchanged(self):
        assert sanitize_filename("movie.mkv") == "movie.mkv"
        assert sanitize_filename("آهنگ.mp3") == "آهنگ.mp3"

    def test_path_traversal_blocked(self):
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result


class TestEscapeLike:
    def test_escapes_percent(self):
        assert escape_like("100%") == "100\\%"

    def test_escapes_underscore(self):
        assert escape_like("a_b") == "a\\_b"

    def test_escapes_backslash(self):
        assert escape_like("a\\b") == "a\\\\b"

    def test_normal_string_unchanged(self):
        assert escape_like("hello") == "hello"

    def test_empty_string(self):
        assert escape_like("") == ""

    def test_combined_special_chars(self):
        result = escape_like("100%_done\\now")
        assert result == "100\\%\\_done\\\\now"


class TestAddUrlsToFile:
    @pytest.mark.asyncio
    async def test_basic_fields(self):
        from app.models import File
        from app.services import add_urls_to_file
        from datetime import datetime

        f = File(
            id=1, user_id=1, folder_id=None,
            file_id="AgACAgIAAxkDAAJaX123", file_unique_id="abc",
            channel_message_id=100, file_name="test.mp4",
            file_size=1024, mime_type="video/mp4", file_type="video",
            duration=60, width=1920, height=1080,
            thumbnail_file_id="thumb", public_hash=None,
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        f.watch_progress = []

        result = add_urls_to_file(f)
        assert result["id"] == 1
        assert result["stream_url"] == "/api/stream/1"
        assert result["thumbnail_url"] == "/api/stream/1/thumbnail"
        assert result["last_pos"] == 0

    @pytest.mark.asyncio
    async def test_with_public_hash(self):
        from app.models import File
        from app.services import add_urls_to_file
        from datetime import datetime

        f = File(
            id=1, user_id=1, folder_id=None,
            file_id="AgACAgIAAxkDAAJaX123", file_unique_id="abc",
            channel_message_id=100, file_name="test.mp4",
            file_size=1024, mime_type="video/mp4", file_type="video",
            duration=60, width=1920, height=1080,
            thumbnail_file_id=None, public_hash="myhash",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        f.watch_progress = []

        result = add_urls_to_file(f)
        assert result["public_hash"] == "myhash"
        assert result["public_stream_url"] == "/api/stream/s/myhash"
        assert result["thumbnail_url"] is None
