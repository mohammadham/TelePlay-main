"""
Setup Wizard API — public endpoints for initial configuration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncio
import logging

from ..database import get_db
from ..models import BotConfig, UserAccount, AdminUser
from ..config import get_settings, mark_db_ready
from ..auth import create_access_token, create_refresh_token
from ..encryption import encrypt, decrypt
from ..patch import Client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/setup", tags=["Setup Wizard"])


# ── Schemas ──────────────────────────────────────────────────────────────

class BotValidateRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=100)


class BotValidateResponse(BaseModel):
    valid: bool
    bot_user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    error: Optional[str] = None


class UserSendCodeRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+\d{10,15}$")
    api_id: int = Field(..., gt=0)
    api_hash: str = Field(..., min_length=10)


class UserSendCodeResponse(BaseModel):
    success: bool
    phone_code_hash: Optional[str] = None
    error: Optional[str] = None


class UserVerifyCodeRequest(BaseModel):
    phone: str
    api_id: int
    api_hash: str
    phone_code_hash: str
    code: str
    password: Optional[str] = None  # 2FA password


class UserVerifyCodeResponse(BaseModel):
    success: bool
    session_string: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    has_2fa: bool = False
    error: Optional[str] = None


class SetupCompleteRequest(BaseModel):
    # Bot config
    bot_token: str
    extra_bot_tokens: List[str] = []
    # User account
    user_phone: str
    user_api_id: int
    user_api_hash: str
    user_session_string: str
    user_2fa_password: Optional[str] = None
    # Super admin
    super_admin_id: int
    # Optional additional admins
    admin_telegram_ids: List[int] = []


class SetupCompleteResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────

async def _validate_bot_token(token: str) -> BotValidateResponse:
    """Validate bot token via Bot API (HTTP) - no api_id/api_hash needed."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                bot = data["result"]
                return BotValidateResponse(
                    valid=True,
                    bot_user_id=bot["id"],
                    username=bot.get("username"),
                    first_name=bot.get("first_name"),
                )
            else:
                return BotValidateResponse(valid=False, error=data.get("description", "Invalid bot token"))
    except httpx.HTTPStatusError as e:
        logger.warning(f"Bot token validation failed: {e.response.text}")
        return BotValidateResponse(valid=False, error=f"HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        logger.warning(f"Bot token validation failed: {e}")
        return BotValidateResponse(valid=False, error=str(e))


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/bot/validate", response_model=BotValidateResponse)
async def validate_bot_token(payload: BotValidateRequest):
    """Validate a bot token by calling getMe."""
    return await _validate_bot_token(payload.token)


def _get_setup_session_name(phone: str) -> str:
    """Generate unique session name for setup based on phone."""
    # Sanitize phone for filename
    safe_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
    return f"setup_{safe_phone}"


@router.post("/user/send-code", response_model=UserSendCodeResponse)
async def send_user_code(payload: UserSendCodeRequest):
    """Send login code to phone for MTProto user account."""
    # Use session file (not in_memory) so phone_code_hash persists between requests
    session_name = _get_setup_session_name(payload.phone)
    try:
        client = Client(
            session_name,
            api_id=payload.api_id,
            api_hash=payload.api_hash,
            phone_number=payload.phone,
            # in_memory=False (default) - uses session file
        )
        await client.connect()
        sent_code = await client.send_code(payload.phone)
        # DON'T disconnect - keep session alive for verify step
        # The session file now contains phone_code_hash
        return UserSendCodeResponse(success=True, phone_code_hash=sent_code.phone_code_hash)
    except Exception as e:
        logger.warning(f"User code send failed: {e}")
        return UserSendCodeResponse(success=False, error=str(e))


@router.post("/user/verify-code", response_model=UserVerifyCodeResponse)
async def verify_user_code(payload: UserVerifyCodeRequest):
    """Verify code and optional 2FA, return session string."""
    # Use same session name as send-code so phone_code_hash is available
    session_name = _get_setup_session_name(payload.phone)
    try:
        client = Client(
            session_name,
            api_id=payload.api_id,
            api_hash=payload.api_hash,
            phone_number=payload.phone,
            # in_memory=False (default) - uses session file
        )
        await client.connect()

        # Two-phase flow:
        # 1. sign_in with code → may throw SessionPasswordNeeded if 2FA enabled
        # 2. if password provided → check_password → export_session_string
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
                    # Keep the client connected so the next call can continue
                    return UserVerifyCodeResponse(
                        success=False,
                        has_2fa=True,
                        error="Two-factor authentication required",
                    )
                # Apply 2FA password
                await client.check_password(payload.password)
            else:
                raise

        session_string = await client.export_session_string()
        me = await client.get_me()
        await client.disconnect()

        # Clean up session file after successful verification
        try:
            import os
            session_file = f"{session_name}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
        except Exception:
            pass

        return UserVerifyCodeResponse(
            success=True,
            session_string=session_string,
            user_id=me.id,
            username=me.username,
            has_2fa=bool(payload.password),
        )
    except Exception as e:
        logger.warning(f"User code verify failed: {e}")
        return UserVerifyCodeResponse(success=False, error=str(e))


@router.post("/complete", response_model=SetupCompleteResponse)
async def complete_setup(
    payload: SetupCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save all config, create initial records, initialize pools."""
    # 1. Validate main bot token
    bot_validation = await _validate_bot_token(payload.bot_token)
    if not bot_validation.valid:
        raise HTTPException(status_code=400, detail=f"Invalid bot token: {bot_validation.error}")

    # 2. Create BotConfig records
    main_bot = BotConfig(
        name="main",
        token_encrypted=encrypt(payload.bot_token),
        bot_user_id=bot_validation.bot_user_id,
        username=bot_validation.username,
        purpose="MAIN",
        is_active=True,
    )
    db.add(main_bot)

    for i, token in enumerate(payload.extra_bot_tokens):
        val = await _validate_bot_token(token)
        if val.valid:
            db.add(BotConfig(
                name=f"helper_{i+1}",
                token_encrypted=encrypt(token),
                bot_user_id=val.bot_user_id,
                username=val.username,
                purpose="HELPER",
                is_active=True,
            ))

    # 3. Create UserAccount (MTProto)
    user_acc = UserAccount(
        name="storage_1",
        phone=payload.user_phone,
        api_id=payload.user_api_id,
        api_hash_encrypted=encrypt(payload.user_api_hash),
        session_string_encrypted=encrypt(payload.user_session_string),
        two_fa_password_encrypted=encrypt(payload.user_2fa_password) if payload.user_2fa_password else None,
        purpose="STORAGE",
        is_active=True,
    )
    db.add(user_acc)

    # 4. Create Super Admin
    super_admin = AdminUser(
        telegram_id=payload.super_admin_id,
        role="SUPER_ADMIN",
        is_active=True,
        can_manage_bots=True,
        can_manage_accounts=True,
        can_manage_admins=True,
    )
    db.add(super_admin)

    # 5. Additional admins
    admin_ids_to_create = [aid for aid in payload.admin_telegram_ids if aid != payload.super_admin_id]
    for admin_id in admin_ids_to_create:
        db.add(AdminUser(
            telegram_id=admin_id,
            role="ADMIN",
            can_manage_bots=False,
            can_manage_accounts=False,
            can_manage_admins=False,
        ))

    await db.commit()

    # 6. Apply DB overrides to settings
    settings = get_settings()
    mark_db_ready(settings)

    # 7. Generate tokens for super admin
    access_token = create_access_token(super_admin.telegram_id, version=super_admin.auth_version)
    refresh_token = create_refresh_token(super_admin.telegram_id, version=super_admin.auth_version)

    return SetupCompleteResponse(
        success=True,
        message="Setup complete. Client pools initialized.",
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/status")
async def setup_status():
    """Check if setup is already complete."""
    from ..config import get_settings, is_configured

    s = get_settings()
    configured = is_configured(s)

    has_bots = False
    has_accounts = False
    has_admin = False

    try:
        from ..database import get_engine
        eng = get_engine()
        if eng:
            async with eng.begin() as conn:
                has_bots = (await conn.execute(select(BotConfig))).scalar_one_or_none() is not None
                has_accounts = (await conn.execute(select(UserAccount))).scalar_one_or_none() is not None
                has_admin = (await conn.execute(select(AdminUser))).scalar_one_or_none() is not None
    except Exception:
        pass

    return {
        "configured": configured,
        "has_bots": has_bots,
        "has_accounts": has_accounts,
        "has_admin": has_admin,
        "telegram_bot_token_set": bool(s.telegram_bot_token),
        "telegram_api_id_set": bool(s.telegram_api_id),
        "telegram_storage_channel_id_set": bool(s.telegram_storage_channel_id),
        "database_url": s.database_url,
    }