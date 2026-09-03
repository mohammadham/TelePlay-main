"""
Telegram Authentication Service.

Centralized service for handling Telegram MTProto authentication flows.
Supports code sending, verification, and 2FA handling with proper error management.
Includes robust proxy support, retry logic, and Railway-friendly session persistence.
"""
from dataclasses import dataclass
from typing import Optional
import asyncio
import logging
import os
import shutil
from pathlib import Path
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
    PROXY_ERROR = "proxy_error"
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
    - Support proxy configuration for restricted networks (Railway, Iran, etc.)
    """

    # Timeout constants - increased for Railway/cloud environments
    CONNECT_TIMEOUT = 60.0
    SEND_CODE_TIMEOUT = 90.0
    SIGN_IN_TIMEOUT = 60.0
    MAX_RETRIES = 3
    RETRY_DELAY = 5.0

    def __init__(self):
        self._settings = None

    @property
    def settings(self):
        """Lazy-load settings."""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def _build_proxy(self, proxy_override: Optional[str] = None) -> Optional[dict]:
        """Build proxy configuration from settings or override."""
        proxy_url = proxy_override or self.settings.telegram_proxy
        if not proxy_url:
            logger.debug("No Telegram proxy configured")
            return None

        try:
            parsed = urlparse(proxy_url)
            if parsed.scheme == "socks5":
                proxy_config = {
                    "ip": parsed.hostname or "",
                    "port": parsed.port or 1080,
                    "scheme": "socks5",
                }
                if parsed.username:
                    proxy_config["username"] = parsed.username
                if parsed.password:
                    proxy_config["password"] = parsed.password
                logger.info(f"Using SOCKS5 proxy: {parsed.hostname}:{parsed.port}")
                return proxy_config
            elif parsed.scheme in ("http", "https"):
                proxy_config = {
                    "ip": parsed.hostname or "",
                    "port": parsed.port or 8080,
                    "scheme": "http",
                }
                if parsed.username:
                    proxy_config["username"] = parsed.username
                if parsed.password:
                    proxy_config["password"] = parsed.password
                logger.info(f"Using HTTP proxy: {parsed.hostname}:{parsed.port}")
                return proxy_config
            else:
                logger.warning(f"Unknown proxy scheme: {parsed.scheme}")
                return None
        except Exception as e:
            logger.error(f"Failed to parse proxy URL: {e}")
            return None

    def _get_session_dir(self) -> Path:
        """Get persistent session directory."""
        # Use /data/sessions for persistence on Railway, fallback to /tmp for local
        base = Path("/data") if Path("/data").exists() else Path("/tmp")
        session_dir = base / "teleplay_sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _get_session_name(self, phone: str) -> str:
        """Generate unique session name for setup based on phone."""
        # Sanitize phone for filename
        safe_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
        return f"setup_{safe_phone}"

    def _get_session_file(self, phone: str) -> Path:
        """Get session file path."""
        return self._get_session_dir() / f"{self._get_session_name(phone)}.session"

    def _create_client(self, session_name: str, api_id: int, api_hash: str, proxy: Optional[dict] = None) -> Client:
        """
        Create a Client instance for authentication.

        IMPORTANT: Do NOT pass phone_number to constructor!
        It causes Pyrogram to attempt auto-login which invalidates phone_code_hash.
        """
        return Client(
            session_name,
            api_id=api_id,
            api_hash=api_hash,
            proxy=proxy,
            ipv6=False,
        )

    async def _retry_operation(self, operation, *args, max_retries=None, **kwargs):
        """Execute an operation with retry logic."""
        max_retries = max_retries or self.MAX_RETRIES
        last_error = None

        for attempt in range(max_retries):
            try:
                return await operation(*args, **kwargs)
            except asyncio.TimeoutError:
                last_error = f"Timeout on attempt {attempt + 1}/{max_retries}"
                logger.warning(last_error)
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {last_error}")

            if attempt < max_retries - 1:
                await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))

        raise Exception(f"All retries exhausted. Last error: {last_error}")

    async def send_code(
        self,
        phone: str,
        api_id: int,
        api_hash: str,
        proxy_override: Optional[str] = None,
    ) -> SendCodeResult:
        """
        Send login code to phone number.

        CRITICAL: Save session file immediately after sending code so
        verify_code can load the same session and use the persisted phone_code_hash.
        """
        # Ensure correct types
        api_id = int(api_id)
        api_hash = str(api_hash)
        if not phone.startswith("+"):
            phone = "+" + phone

        session_name = self._get_session_name(phone)
        session_file = self._get_session_file(phone)
        logger.info(f"Sending code to {phone} with api_id {api_id}")

        proxy = self._build_proxy(proxy_override)

        async def _send():
            client = self._create_client(session_name, api_id, api_hash, proxy)

            logger.info("Connecting to Telegram MTProto...")
            await asyncio.wait_for(client.connect(), timeout=self.CONNECT_TIMEOUT)

            logger.info("Sending authentication code...")
            sent_code = await asyncio.wait_for(
                client.send_code(phone),
                timeout=self.SEND_CODE_TIMEOUT
            )

            # CRITICAL: Persist session immediately so verify can load it
            session_string = await client.export_session_string()
            
            # Atomic write to prevent corruption
            temp_file = session_file.with_suffix('.tmp')
            temp_file.write_text(session_string)
            temp_file.rename(session_file)
            
            logger.info(f"Session saved to {session_file}, hash: {sent_code.phone_code_hash[:20]}...")

            await client.disconnect()

            return SendCodeResult(
                success=True,
                phone_code_hash=sent_code.phone_code_hash,
                expires_in_seconds=120,
            )

        try:
            return await self._retry_operation(_send)
        except asyncio.TimeoutError:
            logger.error("Timeout during send_code operation after all retries")
            return SendCodeResult(
                success=False,
                error=AuthError.TIMEOUT,
                message="Timeout: Telegram connection took too long after retries. If you're in a restricted region, please configure a proxy (SOCKS5 or HTTP)."
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
            error_code = AuthError.NETWORK_ERROR
            message = f"Failed to send code: {type(e).__name__}"
            
            # Check for proxy-specific errors
            if "proxy" in str(e).lower() or "socks" in str(e).lower():
                error_code = AuthError.PROXY_ERROR
                message = "Proxy connection failed. Please check your proxy configuration (host, port, credentials)."
            
            return SendCodeResult(
                success=False,
                error=error_code,
                message=message
            )

    async def verify_code(
        self,
        phone: str,
        api_id: int,
        api_hash: str,
        phone_code_hash: str,
        code: str,
        password: Optional[str] = None,
        proxy_override: Optional[str] = None,
    ) -> VerifyCodeResult:
        """
        Verify login code and optionally handle 2FA.

        CRITICAL: Load the session file created by send_code so the
        phone_code_hash remains valid (Pyrogram stores it in the session).
        """
        if not phone.startswith("+"):
            phone = "+" + phone

        session_name = self._get_session_name(phone)
        session_file = self._get_session_file(phone)
        logger.info(f"Verifying code for {phone}, hash: {phone_code_hash[:20]}...")

        proxy = self._build_proxy(proxy_override)

        async def _verify():
            # CRITICAL: Load session from file so phone_code_hash is preserved
            client_kwargs = dict(
                api_id=api_id,
                api_hash=api_hash,
                proxy=proxy,
                ipv6=False,
            )
            if session_file.exists():
                client_kwargs["session_string"] = session_file.read_text().strip()
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
                if session_file.exists():
                    session_file.unlink()
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

        try:
            return await self._retry_operation(_verify)
        except Exception as e:
            logger.error(f"User code verify failed: {type(e).__name__}: {e}")
            try:
                if session_file.exists():
                    session_file.unlink()
            except Exception:
                pass
            
            error_code = AuthError.UNKNOWN
            message = f"Verification failed: {type(e).__name__}"
            
            if "proxy" in str(e).lower() or "socks" in str(e).lower():
                error_code = AuthError.PROXY_ERROR
                message = "Proxy connection failed. Please check your proxy configuration."
            
            return VerifyCodeResult(
                success=False,
                error=error_code,
                message=message
            )


# Global service instance
telegram_auth_service = TelegramAuthService()