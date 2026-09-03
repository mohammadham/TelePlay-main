"""
Session Manager Service.

Manages the lifecycle of Telegram MTProto sessions including:
- Session creation and validation
- Session persistence and cleanup
- Session string encryption/decryption
"""
import logging
import os
from typing import Optional
from pathlib import Path

from .telegram_auth import telegram_auth_service, VerifyCodeResult
from ..config import get_settings
from ..encryption import encrypt, decrypt
from ..models import UserAccount
from ..database import get_sessionmaker

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages MTProto user account sessions.

    Handles:
    - Creating new sessions via auth flow
    - Validating existing sessions
    - Loading sessions into client pool
    - Cleaning up session files
    """

    def __init__(self):
        self._settings = None

    @property
    def settings(self):
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    def get_session_path(self, session_name: str) -> Path:
        """Get full path for session file."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        session_dir = base_dir / "session"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"{session_name}.session"

    def cleanup_session_file(self, session_name: str) -> bool:
        """Remove session file if it exists."""
        try:
            session_file = self.get_session_path(session_name)
            if session_file.exists():
                session_file.unlink()
                logger.debug(f"Removed session file: {session_file}")
                return True
        except Exception as e:
            logger.warning(f"Failed to cleanup session file {session_name}: {e}")
        return False

    async def validate_session(
        self,
        api_id: int,
        api_hash: str,
        session_string: str,
        proxy: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Validate a session string by connecting to Telegram.

        Returns user info if valid, None if invalid.
        """
        if not session_string:
            logger.warning("Session validation failed: empty session string")
            return None
            
        try:
            from ..patch import Client

            client = Client(
                name="validate_session",
                api_id=api_id,
                api_hash=api_hash,
                session_string=session_string,
                proxy=proxy,
                in_memory=True,
            )
            await client.start()
            me = await client.get_me()
            await client.stop()

            return {
                "user_id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
            }
        except Exception as e:
            logger.error(f"Session validation failed: {type(e).__name__}: {e}")
            return None

    async def save_account_from_auth(
        self,
        name: str,
        phone: str,
        api_id: int,
        api_hash: str,
        auth_result: VerifyCodeResult,
        two_fa_password: Optional[str] = None,
        purpose: str = "STORAGE",
        created_by: Optional[int] = None,
    ) -> Optional[UserAccount]:
        """
        Save a verified auth result as a UserAccount in database.

        Requires a successful VerifyCodeResult with session_string.
        """
        if not auth_result.success or not auth_result.session_string:
            logger.error("Cannot save account: auth result not successful")
            return None

        try:
            session_maker = get_sessionmaker()
            async with session_maker() as db:
                # Check name uniqueness
                from sqlalchemy import select
                existing = await db.execute(
                    select(UserAccount).where(UserAccount.name == name)
                )
                if existing.scalar_one_or_none():
                    logger.error(f"Account name '{name}' already exists")
                    return None

                account = UserAccount(
                    name=name,
                    phone=phone,
                    api_id=api_id,
                    api_hash_encrypted=encrypt(api_hash),
                    session_string_encrypted=encrypt(auth_result.session_string),
                    two_fa_password_encrypted=encrypt(two_fa_password) if two_fa_password else None,
                    user_id=auth_result.user_id,
                    username=auth_result.username,
                    purpose=purpose,
                    is_active=True,
                    created_by=created_by,
                )
                db.add(account)
                await db.commit()
                await db.refresh(account)

                logger.info(f"Saved user account: {name} (@{auth_result.username})")
                return account

        except Exception as e:
            logger.error(f"Failed to save account: {e}")
            return None

    async def load_account_to_pool(self, account: UserAccount) -> bool:
        """
        Load a UserAccount into the client pool for use.

        Returns True if successful.
        """
        try:
            from ..patch import Client
            from ..pool_manager import pool_manager
            from ..encryption import decrypt

            session_str = decrypt(account.session_string_encrypted)
            if not session_str:
                logger.error(f"Failed to decrypt session string for account {account.name}")
                return False
                
            api_hash = decrypt(account.api_hash_encrypted)
            if not api_hash:
                logger.error(f"Failed to decrypt api_hash for account {account.name}")
                return False
                
            proxy = decrypt(account.proxy_encrypted) if account.proxy_encrypted else None

            client = Client(
                name=f"user_{account.id}",
                api_id=account.api_id,
                api_hash=api_hash,
                session_string=session_str,
                proxy=proxy,
                ipv6=False,
            )
            await client.start()
            pool_manager.add_user(client, len(pool_manager.user_pool))
            logger.info(f"Loaded user account {account.name} into pool")
            return True

        except Exception as e:
            logger.error(f"Failed to load account {account.name} to pool: {type(e).__name__}: {e}")
            return False

    async def remove_account_from_pool(self, account_id: int) -> bool:
        """Remove a user account from the pool."""
        try:
            from ..pool_manager import pool_manager

            for idx, client in list(pool_manager.user_pool.items()):
                try:
                    me = await client.get_me()
                    if me.id == account_id:
                        await client.stop()
                        pool_manager.remove_user(idx)
                        logger.info(f"Removed user account {account_id} from pool")
                        return True
                except Exception:
                    pool_manager.remove_user(idx)
            return False
        except Exception as e:
            logger.error(f"Failed to remove account from pool: {e}")
            return False


# Global instance
session_manager = SessionManager()