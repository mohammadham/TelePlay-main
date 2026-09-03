"""
Telegram Authentication Service.

Centralized service for handling Telegram MTProto authentication flows.
Supports code sending, verification, and 2FA handling with proper error management.
Includes robust proxy support, retry logic, and Railway-friendly session persistence.
"""
from dataclasses import dataclass
from typing import Optional
import asyncio
import json
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
    - Support proxy configuration for restricted networks
    """

    # Timeout constants - increased for Railway/cloud environments
    CONNECT_TIMEOUT = 60.0
    SEND_CODE_TIMEOUT = 90.0
    SIGN_IN_TIMEOUT = 60.0
    MAX_RETRIES = 3
    RETRY_DELAY = 5.0
    PENDING_TTL = 600.0  # Keep pending client alive for 10 minutes

    def __init__(self):
        self._settings = None
        # In-memory cache of connected clients between send_code and verify_code.
        # We CANNOT export_session_string() before sign_in (Pyrogram requires user_id),
        # so we must keep the SAME connected client alive to preserve the MTProto auth_key.
        # Key: phone (normalized with leading +). Value: (client, created_at_monotonic)
        self._pending_clients: dict = {}
        self._pending_lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazily create the asyncio lock (needs a running event loop)."""
        if self._pending_lock is None:
            self._pending_lock = asyncio.Lock()
        return self._pending_lock

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
        # Use /data/teleplay_sessions for persistence on Railway, fallback to /tmp for local
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
        
        Use in_memory=True so Pyrogram does NOT create/manage a SQLite .session file.
        We keep the connected client alive in-memory between send_code/verify_code
        to preserve the MTProto auth_key (which cannot be exported before sign_in).
        """
        # session_dir = self._get_session_dir()
        return Client(
            session_name,
            api_id=api_id,
            api_hash=api_hash,
            proxy=proxy,
            ipv6=False,
            # workdir=str(self._get_session_dir()),
            in_memory=True,
        )

    async def _store_pending_client(self, phone: str, client: Client) -> None:
        """Store a connected client keyed by phone, evicting any prior one."""
        import time as _time
        async with self._get_lock():
            prev = self._pending_clients.pop(phone, None)
            if prev:
                old_client, _ = prev
                try:
                    await old_client.disconnect()
                except Exception:
                    pass
            self._pending_clients[phone] = (client, _time.monotonic())
            logger.info(f"[pending] Stored connected client for {phone} (total pending={len(self._pending_clients)})")

    async def _pop_pending_client(self, phone: str) -> Optional[Client]:
        """Retrieve and remove a stored connected client for phone."""
        import time as _time
        async with self._get_lock():
            entry = self._pending_clients.pop(phone, None)
        if not entry:
            return None
        client, created_at = entry
        age = _time.monotonic() - created_at
        if age > self.PENDING_TTL:
            logger.warning(f"[pending] Client for {phone} expired (age={age:.0f}s > {self.PENDING_TTL}s), discarding")
            try:
                await client.disconnect()
            except Exception:
                pass
            return None
        logger.info(f"[pending] Retrieved connected client for {phone} (age={age:.0f}s)")
        return client

    async def _cleanup_pending_client(self, phone: str) -> None:
        """Cleanly disconnect and remove a pending client (used on error paths)."""
        async with self._get_lock():
            entry = self._pending_clients.pop(phone, None)
        if entry:
            client, _ = entry
            try:
                await client.disconnect()
            except Exception:
                pass

    async def _retry_operation(self, operation, *args, max_retries=None, **kwargs):
        """Execute an operation with retry logic for transient errors only."""
        max_retries = max_retries or self.MAX_RETRIES
        last_error = None

        for attempt in range(max_retries):
            try:
                return await operation(*args, **kwargs)
            except asyncio.TimeoutError:
                last_error = f"Timeout on attempt {attempt + 1}/{max_retries}"
                logger.warning(last_error)
            except Exception as e:
                # Only retry on actual transient network errors, not on logic errors
                error_str = str(e).lower()
                is_transient = any(x in error_str for x in ['timeout', 'connection', 'network', 'unreachable', 'dns', 'proxy'])
                if not is_transient:
                    logger.error(f"Non-transient error, not retrying: {type(e).__name__}: {e}")
                    raise
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed (transient): {last_error}")

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
        
        IMPORTANT: This function does NOT retry the actual send_code() call.
        Only connection/transient errors are retried. The code is sent exactly once per call.
        """
        # Ensure correct types
        api_id = int(api_id)
        api_hash = str(api_hash)

        logger.info(
            f"[send_code] Request: phone={phone}, api_id={api_id}, "
            f"proxy={proxy_override}"
        )

        # Track if code was already sent to prevent duplicate sends
        code_sent = False
        sent_phone_code_hash = ""

        async def _send_once():
            nonlocal code_sent, sent_phone_code_hash
            # Create fresh client for each attempt - don't reuse across retries
            client = self._create_client(self._get_session_name(phone), api_id, api_hash, self._build_proxy(None))

            logger.info(f"[_send_once] Connecting to Telegram MTProto...")
            await asyncio.wait_for(client.connect(), timeout=self.CONNECT_TIMEOUT)

            logger.info("Sending authentication code...")
            sent_code = await asyncio.wait_for(
                client.send_code(phone),
                timeout=self.SEND_CODE_TIMEOUT
            )
            code_sent = True

            # CRITICAL: Save the phone_code_hash for potential retry scenarios
            phone_code_hash = sent_code.phone_code_hash
            sent_phone_code_hash = phone_code_hash
            logger.info(f"[_send_once] Code sent, phone_code_hash={phone_code_hash[:20]}...")

            # CRITICAL: We CANNOT call export_session_string() here because Pyrogram
            # requires user_id (integer) for the session-string format, and user_id
            # only exists AFTER sign_in. Trying it raises:
            #   "error: required argument is not an integer"
            #
            # Instead we KEEP THE CONNECTED CLIENT ALIVE in-memory so that verify_code
            # can reuse the SAME MTProto session (same auth_key) that generated
            # this phone_code_hash. Otherwise Telegram rejects verification.
            await self._store_pending_client(phone, client)

            return SendCodeResult(
                success=True,
                phone_code_hash=phone_code_hash,
                expires_in_seconds=120,
            )

        try:
            # Only retry connection/transient errors, NOT the actual send_code call
            # We handle retries manually to avoid double-sending codes
            max_retries = self.MAX_RETRIES
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    result = await _send_once()
                    return result
                except asyncio.TimeoutError:
                    last_error = f"Timeout on attempt {attempt + 1}/{max_retries}"
                    logger.warning(last_error)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                except Exception as e:
                    # If code was already sent, don't retry - return success with the code we sent
                    # Check if the error happened after code was sent
                    error_str = str(e).lower()
                    if "code" in error_str or "sent" in error_str or "phone_code" in error_str or code_sent :
                        logger.warning(f"Error after code sent (attempt {attempt + 1}): {type(e).__name__}: {e}")
                        return SendCodeResult(
                            success=True,
                            phone_code_hash=sent_phone_code_hash ,
                            expires_in_seconds=120,
                            message="Code sent but session save had issues. Check your session file."
                        )
                    
                    # Only retry on transient network errors
                    error_str = str(e).lower()
                    is_transient = any(x in error_str for x in ['timeout', 'connection', 'network', 'unreachable', 'dns', 'proxy'])
                    if not is_transient:
                        logger.error(f"Non-transient error, not retrying: {type(e).__name__}: {e}")
                        raise
                    last_error = f"{type(e).__name__}: {e}"
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed (transient): {last_error}")
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue

            raise Exception(f"All retries exhausted. Last error: {last_error}")

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

        # Ensure correct types
        api_id = int(api_id)
        api_hash = str(api_hash)

        session_name = self._get_session_name(phone)
        session_file = self._get_session_file(phone)
        logger.info(f"[verify_code] Request: phone={phone}, api_id={api_id}, hash_len={len(phone_code_hash) if phone_code_hash else 0}, code_len={len(code)}, has_password={bool(password)}, proxy={proxy_override}")
        logger.info(f"[verify_code] Session file path: {session_file}, exists={session_file.exists()}")

        proxy = self._build_proxy(proxy_override)

        async def _verify():
            # CRITICAL: Retrieve the SAME connected client used by send_code.
            # The MTProto auth_key that generated phone_code_hash lives inside that
            # client's in-memory storage — we cannot recreate it from scratch.
            client = await self._pop_pending_client(phone)
            if client is None:
                logger.error(
                    f"[_verify] No pending client found for {phone}. "
                    f"Either send_code was never called, or the client expired / server restarted."
                )
                raise Exception(
                    "No code hash available. Please request a new code first."
                )

            # Try sign_in with code (NO password parameter!)
            logger.info("Attempting sign_in with code (using preserved MTProto session)...")
            try:
                await asyncio.wait_for(
                    client.sign_in(phone, phone_code_hash, code),
                    timeout=self.SIGN_IN_TIMEOUT,
                )
                logger.info("sign_in successful!")

            except PhoneCodeExpired:
                logger.warning(f"Phone code expired for {phone}")
                try:
                    await client.disconnect()
                except Exception:
                    pass
                return VerifyCodeResult(
                    success=False,
                    error=AuthError.PHONE_CODE_EXPIRED,
                    message="Phone code expired. Please request a new code."
                )
            except SessionPasswordNeeded:
                if not password:
                    logger.info("2FA required, no password provided — keeping client alive for retry")
                    # IMPORTANT: put the client back into pending so the next
                    # verify-code call (with password) can reuse it.
                    await self._store_pending_client(phone, client)
                    return VerifyCodeResult(
                        success=False,
                        has_2fa=True,
                        error=AuthError.SESSION_PASSWORD_NEEDED,
                        message="Two-factor authentication required. Please enter your 2FA password and click Verify again."
                    )
                logger.info("2FA password provided, calling check_password")
                await client.check_password(password)

            # Now the client IS authorized — export_session_string works
            session_string = await client.export_session_string()
            logger.info(f"[_verify] Session string exported, length: {len(session_string)}")
            me = await client.get_me()
            logger.info(f"[_verify] User verified: id={me.id}, username={me.username}")

            # Disconnect (we used connect(), not start())
            try:
                await client.disconnect()
            except Exception as e:
                logger.debug(f"[_verify] Disconnect raised (ignoring): {type(e).__name__}: {e}")

            logger.info(f"[_verify] Verification successful, returning result")
            return VerifyCodeResult(
                success=True,
                session_string=session_string,
                user_id=me.id,
                username=me.username,
                has_2fa=bool(password),
            )

        try:
            result = await self._retry_operation(_verify)
            logger.info(f"[verify_code] Returning: success={result.success}, has_2fa={result.has_2fa}, error={result.error}")
            return result
        except Exception as e:
            logger.error(f"User code verify failed: {type(e).__name__}: {e}")
            # Clean up any pending client on unrecoverable errors so the user
            # can start fresh with a new send_code.
            await self._cleanup_pending_client(phone)

            error_code = AuthError.UNKNOWN
            message = f"Verification failed: {type(e).__name__}: {e}"

            if "no code hash available" in str(e).lower():
                error_code = AuthError.PHONE_CODE_EXPIRED
                message = "No code hash available. Please request a new code first."
            elif "proxy" in str(e).lower() or "socks" in str(e).lower():
                error_code = AuthError.PROXY_ERROR
                message = "Proxy connection failed. Please check your proxy configuration."

            return VerifyCodeResult(
                success=False,
                error=error_code,
                message=message
            )


# Global service instance
telegram_auth_service = TelegramAuthService()