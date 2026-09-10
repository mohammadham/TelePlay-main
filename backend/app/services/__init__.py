"""
TelePlay Services Package.

Centralized business logic services.
"""
import re


def escape_like(value: str) -> str:
    """Escape special LIKE/ILIKE characters to prevent SQL injection."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


from .telegram_auth import (
    TelegramAuthService,
    telegram_auth_service,
    SendCodeResult,
    VerifyCodeResult,
    AuthError,
)
from .session_manager import SessionManager, session_manager
from .utils import (
    sanitize_filename,
    sanitize_text,
    add_urls_to_file,
    fetch_recent_files,
    fetch_continue_watching_files,
)
from .channel_importer import run_import_job, preview_import

__all__ = [
    "TelegramAuthService",
    "telegram_auth_service",
    "SendCodeResult",
    "VerifyCodeResult",
    "AuthError",
    "SessionManager",
    "session_manager",
    "escape_like",
    "sanitize_filename",
    "sanitize_text",
    "add_urls_to_file",
    "fetch_recent_files",
    "fetch_continue_watching_files",
    "run_import_job",
    "preview_import",
]