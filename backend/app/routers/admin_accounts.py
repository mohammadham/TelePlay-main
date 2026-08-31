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
from ..patch import Client
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/accounts", tags=["Admin Accounts"])

USER_PURPOSES = ["STORAGE", "STREAMING", "DOWNLOAD"]


def _get_account_session_name(name: str) -> str:
    """Generate unique session name for account setup."""
    return f"setup_account_{name}"

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

@router.get("", response_model=List[AccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """List all user accounts."""
    result = await db.execute(select(UserAccount).order_by(UserAccount.created_at.desc()))
    accounts = result.scalars().all()
    return accounts

@router.post("/login/start", response_model=dict)
async def start_account_login(
    payload: AccountLoginStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Start login flow for a new MTProto account (send code)."""
    # Validate phone format
    if not payload.phone.startswith("+"):
        payload.phone = "+" + payload.phone
    
    session_name = _get_account_session_name(payload.name)
    try:
        client = Client(
            session_name,
            api_id=payload.api_id,
            api_hash=payload.api_hash,
            phone_number=payload.phone,
            # in_memory=False (default) - uses session file so phone_code_hash persists
        )
        await client.connect()
        sent_code = await client.send_code(payload.phone)
        # DON'T disconnect - keep session alive for verify step
        return {
            "success": True,
            "phone_code_hash": sent_code.phone_code_hash,
            "message": "Code sent to phone"
        }
    except Exception as e:
        logger.warning(f"Account code send failed: {e}")
        raise HTTPException(400, f"Failed to send code: {e}")

@router.post("/login/verify", response_model=dict)
async def verify_account_login(
    payload: AccountLoginVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Verify code and optional 2FA, return session string."""
    if not payload.phone.startswith("+"):
        payload.phone = "+" + payload.phone
    
    session_name = _get_account_session_name(payload.name)
    try:
        client = Client(
            session_name,
            api_id=payload.api_id,
            api_hash=payload.api_hash,
            phone_number=payload.phone,
            # in_memory=False (default) - uses session file
        )
        await client.connect()
        
        try:
            await client.sign_in(
                payload.phone,
                payload.phone_code_hash,
                payload.code,
            )
        except Exception as e:
            exc_str = str(e).upper()
            if "SESSION_PASSWORD_NEEDED" in exc_str or "TWO-FACTOR" in exc_str or "PASSWORD_NEEDED" in exc_str:
                if not payload.password:
                    # 2FA required but no password given
                    # IMPORTANT: sign_in without password INVALIDATES phone_code_hash.
                    # We must resend a new code + handle password in ONE call.
                    return {
                        "success": False,
                        "has_2fa": True,
                        "error": "Two-factor authentication required. Please enter your 2FA password and try again.",
                    }
                # Password provided but sign_in still failed with password needed.
                # Resend a fresh code and retry sign_in WITH password in one call.
                # NOTE: The original phone_code_hash is now invalid — send a new one.
                client2 = Client(
                    session_name,
                    api_id=payload.api_id,
                    api_hash=payload.api_hash,
                    phone_number=payload.phone,
                )
                await client2.connect()
                try:
                    sent_code = await client2.send_code(payload.phone)
                    await client2.sign_in(
                        payload.phone,
                        sent_code.phone_code_hash,
                        payload.code,
                        password=payload.password,
                    )
                except Exception as inner_e:
                    inner_str = str(inner_e).upper()
                    if "SESSION_PASSWORD_NEEDED" in inner_str:
                        raise HTTPException(400, "Invalid 2FA password. Please check and try again.")
                    raise
                finally:
                    await client2.disconnect()
                await client.disconnect()
                # Fall through to export_session_string below
            else:
                raise
        
        session_string = await client.export_session_string()
        me = await client.get_me()
        await client.disconnect()
        
        # Clean up session file after successful verification
        try:
            session_file = f"{session_name}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
        except Exception:
            pass
        
        return {
            "success": True,
            "session_string": session_string,
            "user_id": me.id,
            "username": me.username,
            "has_2fa": bool(payload.password),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Account code verify failed: {e}")
        raise HTTPException(400, f"Verification failed: {e}")

@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Create a new user account with pre-obtained session string."""
    if payload.purpose not in USER_PURPOSES:
        raise HTTPException(400, f"Invalid purpose. Must be one of: {USER_PURPOSES}")
    
    # Check name uniqueness
    existing = await db.execute(select(UserAccount).where(UserAccount.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Account with name '{payload.name}' already exists")
    
    # For now, require session_string to be provided via a separate field
    # In practice, the UI would do login/verify first, then call this with session
    # This endpoint expects the session_string to be passed in a special way
    # Let's make it require session_string via a separate endpoint or field
    raise HTTPException(400, "Use /login/verify to get session_string, then provide it")

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
        await add_account_to_pool(account)
    
    return account

async def add_account_to_pool(account: UserAccount):
    """Add a user account to the MTProto client pool."""
    try:
        settings = get_settings()
        session_str = decrypt(account.session_string_encrypted)
        api_hash = decrypt(account.api_hash_encrypted)
        
        client = Client(
            name=f"user_{account.id}",
            api_id=account.api_id,
            api_hash=api_hash,
            session_string=session_str,
            ipv6=False,
        )
        await client.start()
        pool_manager.add_user(client, len(pool_manager.user_pool))
        logger.info(f"User account {account.name} added to pool")
    except Exception as e:
        logger.error(f"Failed to add user account to pool: {e}")

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
        # Remove old client
        for idx, client in list(pool_manager.user_pool.items()):
            try:
                me = await client.get_me()
                if me.id == account.user_id:
                    await client.stop()
                    pool_manager.remove_user(idx)
                    break
            except:
                pool_manager.remove_user(idx)
        
        # Add new if active
        if account.is_active:
            await add_account_to_pool(account)
    
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
    for idx, client in list(pool_manager.user_pool.items()):
        try:
            me = await client.get_me()
            if me.id == account.user_id:
                if revoke_session:
                    await client.revoke_sessions()
                await client.stop()
                pool_manager.remove_user(idx)
                break
        except:
            pool_manager.remove_user(idx)
    
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
            from datetime import datetime
            if account.flood_wait_until > datetime.utcnow():
                flood_wait = int((account.flood_wait_until - datetime.utcnow()).total_seconds())
        
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

