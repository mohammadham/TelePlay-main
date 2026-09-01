"""
TelePlay Services Package.

Centralized business logic services.
"""
from .telegram_auth import (
    TelegramAuthService,
    telegram_auth_service,
    SendCodeResult,
    VerifyCodeResult,
    AuthError,
)
from .session_manager import SessionManager, session_manager

__all__ = [
    "TelegramAuthService",
    "telegram_auth_service",
    "SendCodeResult",
    "VerifyCodeResult",
    "AuthError",
    "SessionManager",
    "session_manager",
]