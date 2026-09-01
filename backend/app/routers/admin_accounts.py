"""
Admin Accounts API — Manage MTProto user accounts with 2FA support
"""
from datetime import datetime
from typing import List, Optional
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..database import get_db
from ..models import UserAccount, AdminUser
from ..auth import require_admin
from ..encryption import encrypt, decrypt
from ..pool_manager import pool_manager
from ..services import telegram_auth_service, session_manager
from ..services.telegram_auth import AuthError
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/accounts", tags=["Admin Accounts"])

USER_PURPOSES = ["STORAGE", "STREAMING", "DOWNLOAD"]


def _get_account_session_name(name: str) -> str:
    """Generate unique session name for account setup."""
    return f"setup_account_{name}"


# ── Schemas ──────────────────────────────────────────────────────────────

class AccountCreateRequest(BaseModel):
    name: str
    phone: str
    api_id: int
    api_hash: str
    purpose: str = "STORAGE"
    is_active: bool = True


class AccountUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    purpose: Optional[str] = None
    is_active: Optional[bool] = None


class AccountLoginStartRequest(BaseModel):
    name: str
    phone: str
    api_id: int
    api_hash: str


class AccountLoginVerifyRequest(BaseModel):
    name: str
    phone: str
    api_id: int
    api_hash: str
    phone_code_hash: str
    code: str
    password: Optional[str] = None


class AccountResponse(BaseModel):
    id: int
    name: str
    phone: str
    api_id: int
    username: Optional[str] = None
    user_id: Optional[int] = None
    purpose: str
    is_active: bool
    flood_wait_until: Optional[datetime] = None
    last_used: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AccountLoginStartResponse(BaseModel):
    success: bool
    phone_code_hash: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    expires_in_seconds: int = 120


class AccountLoginVerifyResponse(BaseModel):
    success: bool
    session_string: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    has_2fa: bool = False
    error: Optional[str] = None
    message: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("", response_model=List[AccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """List all user accounts."""
    result = await db.execute(select(UserAccount).order_by(UserAccount.created_at.desc()))
    accounts = result.scalars().all()
    return accounts


@router.post("/login/start", response_model=AccountLoginStartResponse)
async def start_account_login(
    payload: AccountLoginStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Send login code to phone for MTProto account (admin flow)."""
    if not payload.phone.startswith("+"):
        payload.phone = "+" + payload.phone

    result = await telegram_auth_service.send_code(
        phone=payload.phone,
        api_id=payload.api_id,
        api_hash=payload.api_hash,
    )

    return AccountLoginStartResponse(
        success=result.success,
        phone_code_hash=result.phone_code_hash,
        error=result.error,
        message=result.message,
        expires_in_seconds=result.expires_in_seconds,
    )


@router.post("/login/verify", response_model=AccountLoginVerifyResponse)
async def verify_account_login(
    payload: AccountLoginVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Verify code and optional 2FA, return session string (admin flow)."""
    if not payload.phone.startswith("+"):
        payload.phone = "+" + payload.phone

    result = await telegram_auth_service.verify_code(
        phone=payload.phone,
        api_id=payload.api_id,
        api_hash=payload.api_hash,
        phone_code_hash=payload.phone_code_hash,
        code=payload.code,
        password=payload.password,
    )

    return AccountLoginVerifyResponse(
        success=result.success,
        session_string=result.session_string,
        user_id=result.user_id,
        username=result.username,
        has_2fa=result.has_2fa,
        error=result.error,
        message=result.message,
    )


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Create a new user account with pre-obtained session string."""
    if payload.purpose not in USER_PURPOSES:
        raise HTTPException(400, f"Invalid purpose. Must be one of: {USER_PURPOSES}")

    existing = await db.execute(select(UserAccount).where(UserAccount.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Account with name '{payload.name}' already exists")

    raise HTTPException(
        400,
        "Use /login/verify to get session_string, then provide it"
    )


class AccountCreateWithSessionRequest(BaseModel):
    name: str
    phone: str
    api_id: int
    api_hash: str
    session_string: str
    two_fa_password: Optional[str] = None
    purpose: str = "STORAGE"
    is_active: bool = True


@router.post("/with-session", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account_with_session(
    payload: AccountCreateWithSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Create account with already-obtained session string."""
    if payload.purpose not in USER_PURPOSES:
        raise HTTPException(400, f"Invalid purpose. Must be one of: {USER_PURPOSES}")

    existing = await db.execute(select(UserAccount).where(UserAccount.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Account with name '{payload.name}' already exists")

    # Validate session by connecting
    try:
        from ..patch import Client
        client = Client(
            f"validate_account_{payload.name}",
            api_id=payload.api_id,
            api_hash=payload.api_hash,
            session_string=payload.session_string,
            in_memory=True,
        )
        await client.start()
        me = await client.get_me()
        await client.stop()
        user_id = me.id
        username = me.username
    except Exception as e:
        raise HTTPException(400, f"Invalid session string: {e}")

    account = UserAccount(
        name=payload.name,
        phone=payload.phone,
        api_id=payload.api_id,
        api_hash_encrypted=encrypt(payload.api_hash),
        session_string_encrypted=encrypt(payload.session_string),
        two_fa_password_encrypted=encrypt(payload.two_fa_password) if payload.two_fa_password else None,
        user_id=user_id,
        username=username,
        purpose=payload.purpose,
        is_active=payload.is_active,
        created_by=current_user.id,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    # Add to pool if active
    if payload.is_active:
        await session_manager.load_account_to_pool(account)

    return account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    payload: AccountUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Update user account configuration."""
    result = await db.execute(select(UserAccount).where(UserAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    if payload.purpose and payload.purpose not in USER_PURPOSES:
        raise HTTPException(400, f"Invalid purpose. Must be one of: {USER_PURPOSES}")

    if payload.name and payload.name != account.name:
        existing = await db.execute(select(UserAccount).where(UserAccount.name == payload.name))
        if existing.scalar_one_or_none():
            raise HTTPException(400, f"Account with name '{payload.name}' already exists")

    update_data = payload.model_dump(exclude_unset=True)
    sensitive_changed = any(k in update_data for k in ["api_hash", "phone", "api_id"])

    if "api_hash" in update_data:
        account.api_hash_encrypted = encrypt(update_data.pop("api_hash"))
    if "two_fa_password" in update_data:
        pwd = update_data.pop("two_fa_password")
        account.two_fa_password_encrypted = encrypt(pwd) if pwd else None

    for field, value in update_data.items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    # Re-add to pool if sensitive data changed or active status changed
    if sensitive_changed or "is_active" in update_data:
        await session_manager.remove_account_from_pool(account_id)
        if account.is_active:
            await session_manager.load_account_to_pool(account)

    return account


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    revoke_session: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Delete a user account. Optionally revoke the Telegram session."""
    result = await db.execute(select(UserAccount).where(UserAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    # Stop and remove from pool
    await session_manager.remove_account_from_pool(account_id)

    # Optionally revoke session on Telegram servers
    if revoke_session:
        try:
            from ..patch import Client
            session_str = decrypt(account.session_string_encrypted)
            api_hash = decrypt(account.api_hash_encrypted)
            client = Client(
                f"revoke_{account.name}",
                api_id=account.api_id,
                api_hash=api_hash,
                session_string=session_str,
                in_memory=True,
            )
            await client.start()
            await client.revoke_sessions()
            await client.stop()
            logger.info(f"Revoked sessions for account {account.name}")
        except Exception as e:
            logger.warning(f"Failed to revoke sessions for {account.name}: {e}")

    await db.delete(account)
    await db.commit()

    return {"ok": True, "message": f"Account '{account.name}' deleted"}


@router.post("/{account_id}/health")
async def check_account_health(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Check health of a specific user account."""
    result = await db.execute(select(UserAccount).where(UserAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    try:
        from ..patch import Client
        session_str = decrypt(account.session_string_encrypted)
        api_hash = decrypt(account.api_hash_encrypted)

        client = Client(
            f"health_{account.name}",
            api_id=account.api_id,
            api_hash=api_hash,
            session_string=session_str,
            in_memory=True,
        )
        await client.start()
        me = await client.get_me()

        # Check flood wait
        flood_wait = None
        if account.flood_wait_until:
            from datetime import datetime as dt
            if account.flood_wait_until > dt.utcnow():
                flood_wait = int((account.flood_wait_until - dt.utcnow()).total_seconds())

        await client.stop()

        return {
            "ok": True,
            "user_id": me.id,
            "username": me.username,
            "is_connected": True,
            "flood_wait_seconds": flood_wait,
            "last_used": account.last_used,
        }
    except Exception as e:
        logger.error(f"Account health check failed: {e}")
        return {
            "ok": False,
            "error": str(e),
            "flood_wait_seconds": None,
            "last_used": account.last_used,
        }
