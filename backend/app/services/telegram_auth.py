"""
Telegram Authentication Service.

Centralized service for handling Telegram MTProto authentication flows.
Supports code sending, verification, and 2FA handling with proper error management.
"""
from dataclasses import dataclass
from typing import Optional
import asyncio
import logging
import os
from urllib.parse import urlparse

from pyrogram.errors import SessionPasswordNeeded, PhoneCodeExpired

from ..patch import Client
from ..config import get_settings

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Standardized authentication error codes."""
    TIMEOUT = "timeout"
    PHONE_CODE_EXPIRED = "phone_code_expired"
    INVALID_CODE = "invalid_code"
    SESSION_PASSWORD_NEEDED = "2fa_required"
    NETWORK_ERROR = "network_error"
    INVALID_CREDENTIALS = "invalid_credentials"
    UNKNOWN = "unknown"


@dataclass
class SendCodeResult:
    """Result of sending login code."""
    success: bool
    phone_code_hash: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    expires_in_seconds: int = 120


@dataclass
class VerifyCodeResult:
    """Result of verifying login code."""
    success: bool
    session_string: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    has_2fa: bool = False
    error: Optional[str] = None
    message: Optional[str] = None


class TelegramAuthService:
    """
    Service for Telegram MTProto authentication operations.

    Handles the complete authentication flow including:
    - Sending login codes
    - Verifying codes
    - 2FA password handling
    - Session string generation

    Key Principles:
    - NEVER pass phone_number to Client constructor (causes auto-login)
    - Use same session_name between send_code and verify_code
    - Use proper Pyrogram exception types for error handling
    - Apply timeouts to all network operations
    """

    # Timeout constants
    CONNECT_TIMEOUT = 30.0
    SEND_CODE_TIMEOUT = 60.0
    SIGN_IN_TIMEOUT = 30.0

    def __init__(self):
        self._settings = None

    @property
    def settings(self):
        """Lazy-load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def _build_proxy(self) -> Optional[dict]:
        """Build proxy configuration from settings."""
        if not self.settings.telegram_proxy:
            logger.debug("No Telegram proxy configured")
            return None

        parsed = urlparse(self.settings.telegram_proxy)
        if parsed.scheme == "socks5":
            proxy_config = {
                "ip": parsed.hostname or "",
                "port": parsed.port or 1080,
                "scheme": "socks5",
            }
            logger.info(f"Using SOCKS5 proxy: {parsed.hostname}:{parsed.port}")
            return proxy_config
        elif parsed.scheme == "http":
            proxy_config = {
                "ip": parsed.hostname or "",
                "port": parsed.port or 8080,
                "scheme": "http",
            }
            logger.info(f"Using HTTP proxy: {parsed.hostname}:{parsed.port}")
            return proxy_config
        else:
            logger.warning(f"Unknown proxy scheme: {parsed.scheme}")
            return None

    def _get_session_name(self, phone: str) -> str:
        """Generate unique session name for setup based on phone."""
        # Sanitize phone for filename
        safe_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
        return f"setup_{safe_phone}"

    def _create_client(self, session_name: str, api_id: int, api_hash: str) -> Client:
        """
        Create a Client instance for authentication.

        IMPORTANT: Do NOT pass phone_number to constructor!
        It causes Pyrogram to attempt auto-login which invalidates phone_code_hash.
        """
        proxy = self._build_proxy()
        return Client(
            session_name,
            api_id=api_id,
            api_hash=api_hash,
            proxy=proxy,
            ipv6=False,
        )

    async def send_code(
        self,
        phone: str,
        api_id: int,
        api_hash: str,
    ) -> SendCodeResult:
        """
        Send login code to phone number.

        CRITICAL: Save session file immediately after sending code so
        verify_code can load the same session and use the persisted phone_code_hash.
        """
        # Ensure correct types (FastAPI should validate, but be safe)
        api_id = int(api_id)
        api_hash = str(api_hash)
        if not phone.startswith("+"):
            phone = "+" + phone

        session_name = self._get_session_name(phone)
        session_file = f"{session_name}.session"
        logger.info(f"Sending code to {phone} with api_id {api_id}")

        try:
            client = self._create_client(session_name, api_id, api_hash)

            logger.info("Connecting to Telegram MTProto...")
            await asyncio.wait_for(client.connect(), timeout=self.CONNECT_TIMEOUT)

            logger.info("Sending authentication code...")
            sent_code = await asyncio.wait_for(
                client.send_code(phone),
                timeout=self.SEND_CODE_TIMEOUT
            )

            # CRITICAL: Persist session immediately so verify can load it
            session_string = await client.export_session_string()
            with open(session_file, "w") as f:
                f.write(session_string)
            logger.info(f"Session saved to {session_file}, hash: {sent_code.phone_code_hash[:20]}...")

            await client.disconnect()

            return SendCodeResult(
                success=True,
                phone_code_hash=sent_code.phone_code_hash,
                expires_in_seconds=120,
            )

        except asyncio.TimeoutError:
            logger.error("Timeout during send_code operation")
            return SendCodeResult(
                success=False,
                error=AuthError.TIMEOUT,
                message="Timeout: Telegram connection took too long. Check your network connection and proxy settings."
            )
        except PhoneCodeExpired:
            logger.warning("Phone code expired during send_code")
            return SendCodeResult(
                success=False,
                error=AuthError.PHONE_CODE_EXPIRED,
                message="Phone code expired. Please try again."
            )
        except Exception as e:
            logger.error(f"User code send failed: {type(e).__name__}: {e}")
            return SendCodeResult(
                success=False,
                error=AuthError.NETWORK_ERROR,
                message=f"Failed to send code: {type(e).__name__}"
            )

    async def verify_code(
        self,
        phone: str,
        api_id: int,
        api_hash: str,
        phone_code_hash: str,
        code: str,
        password: Optional[str] = None,
    ) -> VerifyCodeResult:
        # Ensure correct types (FastAPI should validate, but be safe)
        api_id = int(api_id)
        api_hash = str(api_hash)
        """
        Verify login code and optionally handle 2FA.

        CRITICAL: Load the session file created by send_code so the
        phone_code_hash remains valid (Pyrogram stores it in the session).
        """
        if not phone.startswith("+"):
            phone = "+" + phone

        session_name = self._get_session_name(phone)
        session_file = f"{session_name}.session"
        logger.info(f"Verifying code for {phone}, hash: {phone_code_hash[:20]}...")

        try:
            # CRITICAL: Load session from file so phone_code_hash is preserved
            client_kwargs = dict(
                api_id=api_id,
                api_hash=api_hash,
                proxy=self._build_proxy(),
                ipv6=False,
            )
            if os.path.exists(session_file):
                client_kwargs["session_string"] = open(session_file).read().strip()
                logger.info(f"Loaded session from {session_file}")
            else:
                client_kwargs["name"] = session_name
                logger.warning(f"Session file not found at {session_file}, creating new")

            client = Client(**client_kwargs)

            logger.info("Connecting to Telegram MTProto...")
            await asyncio.wait_for(client.connect(), timeout=self.CONNECT_TIMEOUT)

            # Try sign_in with code (NO password parameter!)
            logger.info("Attempting sign_in with code...")
            try:
                await asyncio.wait_for(
                    client.sign_in(phone, phone_code_hash, code),
                    timeout=self.SIGN_IN_TIMEOUT,
                )
                logger.info("sign_in successful!")

            except PhoneCodeExpired:
                logger.warning(f"Phone code expired for {phone}")
                return VerifyCodeResult(
                    success=False,
                    error=AuthError.PHONE_CODE_EXPIRED,
                    message="Phone code expired. Please request a new code."
                )
            except SessionPasswordNeeded:
                if not password:
                    logger.info("2FA required, no password provided")
                    return VerifyCodeResult(
                        success=False,
                        has_2fa=True,
                        error=AuthError.SESSION_PASSWORD_NEEDED,
                        message="Two-factor authentication required. Please enter your 2FA password and click Verify again."
                    )
                logger.info("2FA password provided, calling check_password")
                await client.check_password(password)

            # Export session string
            session_string = await client.export_session_string()
            me = await client.get_me()

            # Clean up temp session file
            try:
                if os.path.exists(session_file):
                    os.remove(session_file)
                    logger.debug(f"Cleaned up session file: {session_file}")
            except Exception as e:
                logger.debug(f"Could not clean up session file: {e}")

            await client.disconnect()

            return VerifyCodeResult(
                success=True,
                session_string=session_string,
                user_id=me.id,
                username=me.username,
                has_2fa=bool(password),
            )

        except Exception as e:
            logger.error(f"User code verify failed: {type(e).__name__}: {e}")
            try:
                if os.path.exists(session_file):
                    os.remove(session_file)
            except Exception:
                pass
            return VerifyCodeResult(
                success=False,
                error=AuthError.UNKNOWN,
                message=f"Verification failed: {type(e).__name__}"
            )


# Global service instance
telegram_auth_service = TelegramAuthService()