"""
Setup Wizard API — public endpoints for initial configuration
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, List

from ..database import get_db
from ..models import BotConfig, UserAccount, AdminUser
from ..config import get_settings, mark_db_ready
from ..auth import create_access_token, create_refresh_token
from ..encryption import encrypt, decrypt
from ..services import telegram_auth_service, session_manager
from ..telegram import tg_client
from ..encryption import ensure_encryption_key
from ..services.telegram_auth import SendCodeResult, VerifyCodeResult

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
    proxy: Optional[str] = None  # Optional proxy: "socks5://user:pass@host:port" or "http://host:port"


class UserSendCodeResponse(BaseModel):
    success: bool
    phone_code_hash: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    expires_in_seconds: int = 120


class UserVerifyCodeRequest(BaseModel):
    phone: str
    api_id: int
    api_hash: str
    phone_code_hash: str
    code: str
    password: Optional[str] = None  # 2FA password
    proxy: Optional[str] = None  # Optional proxy


class UserVerifyCodeResponse(BaseModel):
    success: bool
    session_string: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    has_2fa: bool = False
    error: Optional[str] = None
    message: Optional[str] = None


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
    user_proxy: Optional[str] = None  # Optional proxy for user account
    storage_channel_id: int = Field(0, alias="telegram_storage_channel_id")  # Storage channel ID
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
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=10.0
            )
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
                return BotValidateResponse(
                    valid=False,
                    error=data.get("description", "Invalid bot token")
                )
    except httpx.HTTPStatusError as e:
        return BotValidateResponse(
            valid=False,
            error=f"HTTP {e.response.status_code}: {e.response.text}"
        )
    except Exception as e:
        return BotValidateResponse(valid=False, error=str(e))


# ── Endpoints ────────────────────────────────────────────────────────────

@router.post("/bot/validate", response_model=BotValidateResponse)
async def validate_bot_token(payload: BotValidateRequest):
    """Validate a bot token by calling getMe."""
    return await _validate_bot_token(payload.token)


@router.post("/user/send-code", response_model=UserSendCodeResponse)
async def send_user_code(payload: UserSendCodeRequest):
    """
    Send login code to phone for MTProto user account.

    This is the first step in the authentication flow.
    Returns a phone_code_hash that must be used in the verify step.
    """
    logger.info(f"[send-code] Request for phone={payload.phone}, api_id={payload.api_id}")
    result: SendCodeResult = await telegram_auth_service.send_code(
        phone=payload.phone,
        api_id=payload.api_id,
        api_hash=payload.api_hash,
        proxy_override=payload.proxy,
    )
    logger.info(f"[send-code] Result: success={result.success}, hash_len={len(result.phone_code_hash) if result.phone_code_hash else 0}, error={result.error}")

    return UserSendCodeResponse(
        success=result.success,
        phone_code_hash=result.phone_code_hash,
        error=result.error,
        message=result.message,
        expires_in_seconds=result.expires_in_seconds,
    )


@router.post("/user/verify-code", response_model=UserVerifyCodeResponse)
async def verify_user_code(payload: UserVerifyCodeRequest):
    """
    Verify code and optional 2FA, return session string.

    This is the second step in the authentication flow.
    Uses the phone_code_hash from send-code step.

    If 2FA is enabled on the account:
    - First call without password returns has_2fa=true
    - User must then provide password and call again
    """
    logger.info(f"[verify-code] Request for phone={payload.phone}, hash_len={len(payload.phone_code_hash) if payload.phone_code_hash else 0}")
    
    # If phone_code_hash is empty, the backend will try to load it from session file
    result: VerifyCodeResult = await telegram_auth_service.verify_code(
        phone=payload.phone,
        api_id=payload.api_id,
        api_hash=payload.api_hash,
        phone_code_hash=payload.phone_code_hash,
        code=payload.code,
        password=payload.password,
        proxy_override=payload.proxy,
    )
    logger.info(f"[verify-code] Result: success={result.success}, has_2fa={result.has_2fa}, error={result.error}")

    return UserVerifyCodeResponse(
        success=result.success,
        session_string=result.session_string,
        user_id=result.user_id,
        username=result.username,
        has_2fa=result.has_2fa,
        error=result.error,
        message=result.message,
    )


@router.post("/complete", response_model=SetupCompleteResponse)
async def complete_setup(
    payload: SetupCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save all config, create initial records, initialize pools."""
    # 1. Validate main bot token
    bot_validation = await _validate_bot_token(payload.bot_token)
    if not bot_validation.valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bot token: {bot_validation.error}"
        )

    # 2. Create or update BotConfig records (idempotent — handle re-runs)
    stmt = select(BotConfig).where(BotConfig.name == "main")
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.token_encrypted = encrypt(payload.bot_token)
        existing.bot_user_id = bot_validation.bot_user_id
        existing.username = bot_validation.username
        existing.is_active = True
    else:
        db.add(BotConfig(
            name="main",
            token_encrypted=encrypt(payload.bot_token),
            bot_user_id=bot_validation.bot_user_id,
            username=bot_validation.username,
            purpose="MAIN",
            is_active=True,
        ))

    for i, token in enumerate(payload.extra_bot_tokens):
        val = await _validate_bot_token(token)
        if val.valid:
            helper_name = f"helper_{i+1}"
            stmt = select(BotConfig).where(BotConfig.name == helper_name)
            existing_helper = (await db.execute(stmt)).scalar_one_or_none()
            if existing_helper:
                existing_helper.token_encrypted = encrypt(token)
                existing_helper.bot_user_id = val.bot_user_id
                existing_helper.username = val.username
                existing_helper.is_active = True
            else:
                db.add(BotConfig(
                    name=helper_name,
                    token_encrypted=encrypt(token),
                    bot_user_id=val.bot_user_id,
                    username=val.username,
                    purpose="HELPER",
                    is_active=True,
                ))

    # 3. Create or update UserAccount (MTProto) — idempotent
    stmt = select(UserAccount).where(UserAccount.name == "storage_1")
    existing_user_acc = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user_acc:
        existing_user_acc.phone = payload.user_phone
        existing_user_acc.api_id = payload.user_api_id
        existing_user_acc.api_hash_encrypted = encrypt(payload.user_api_hash)
        existing_user_acc.session_string_encrypted = encrypt(payload.user_session_string)
        existing_user_acc.two_fa_password_encrypted = encrypt(payload.user_2fa_password) if payload.user_2fa_password else None
        existing_user_acc.proxy_encrypted = encrypt(payload.user_proxy) if payload.user_proxy else None
        existing_user_acc.is_active = True
        user_acc = existing_user_acc
    else:
        user_acc = UserAccount(
            name="storage_1",
            phone=payload.user_phone,
            api_id=payload.user_api_id,
            api_hash_encrypted=encrypt(payload.user_api_hash),
            session_string_encrypted=encrypt(payload.user_session_string),
            two_fa_password_encrypted=encrypt(payload.user_2fa_password) if payload.user_2fa_password else None,
            proxy_encrypted=encrypt(payload.user_proxy) if payload.user_proxy else None,
            purpose="STORAGE",
            is_active=True,
        )
        db.add(user_acc)

    # 4. Create or update Super Admin — idempotent
    stmt = select(AdminUser).where(AdminUser.telegram_id == payload.super_admin_id)
    existing_admin = (await db.execute(stmt)).scalar_one_or_none()
    if existing_admin:
        existing_admin.role = "SUPER_ADMIN"
        existing_admin.is_active = True
        existing_admin.can_manage_bots = True
        existing_admin.can_manage_accounts = True
        existing_admin.can_manage_admins = True
        super_admin = existing_admin
    else:
        super_admin = AdminUser(
            telegram_id=payload.super_admin_id,
            role="SUPER_ADMIN",
            is_active=True,
            can_manage_bots=True,
            can_manage_accounts=True,
            can_manage_admins=True,
        )
        db.add(super_admin)

    # 5. Additional admins — idempotent
    admin_ids_to_create = [
        aid for aid in payload.admin_telegram_ids
        if aid != payload.super_admin_id
    ]
    for admin_id in admin_ids_to_create:
        stmt = select(AdminUser).where(AdminUser.telegram_id == admin_id)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.is_active = True
        else:
            db.add(AdminUser(
                telegram_id=admin_id,
                role="ADMIN",
                can_manage_bots=False,
                can_manage_accounts=False,
                can_manage_admins=False,
            ))

    await db.commit()
    await db.refresh(user_acc)
    await db.refresh(super_admin)

    # Set in-memory flag so is_configured() returns True immediately
    from ..config import mark_setup_complete as _mark_setup_complete
    _mark_setup_complete()

    # 6. Apply DB overrides to settings FIRST so JWT_SECRET is loaded from DB
    # (or use the in-memory one if first-time setup). This MUST happen before
    # ensure_encryption_key() so the key is derived from the persisted secret,
    # not from a random value generated on this process startup.
    settings = get_settings()
    await mark_db_ready(settings)

    # Now derive encryption key from the (possibly DB-loaded) JWT_SECRET
    await ensure_encryption_key()

    # 7. Persist ALL config values to DB so they survive restarts
    # This is critical: on next startup, mark_db_ready() will load these values
    # and all Telegram credentials will be available without manual re-config
    try:
        from ..models import AppSetting
        from ..database import async_session
        import sqlalchemy
        async def _persist_config_async() -> None:
            async with async_session() as conn:
                # Persist JWT_SECRET
                if settings.jwt_secret and settings.jwt_secret != "change-me-in-production-please-set-via-panel":
                    row = await conn.execute(
                        sqlalchemy.select(AppSetting)
                        .where(AppSetting.key == 'JWT_SECRET').limit(1)
                    )
                    existing = row.scalar_one_or_none()
                    if existing is None:
                        await conn.execute(
                            sqlalchemy.insert(AppSetting).values(
                                key='JWT_SECRET',
                                value=settings.jwt_secret,
                                description="JWT signing secret",
                            )
                        )
                    else:
                        existing.value = settings.jwt_secret
                    # Note: we commit after all values are set

                # Persist Telegram config — use payload values (real values from setup form),
                # NOT settings (which contain env/template values that get overwritten on restart).
                def upsert(key: str, value: str, desc: str) -> None:
                    if not value or value in ("", "0", "your_api_id", "your_api_hash",
                                               "your_bot_token", "change-me-in-production-please-set-via-panel"):
                        return
                    row = conn.execute(
                        sqlalchemy.select(AppSetting).where(AppSetting.key == key).limit(1)
                    )
                    existing = row.scalar_one_or_none()
                    if existing is None:
                        conn.execute(
                            sqlalchemy.insert(AppSetting).values(key=key, value=value, description=desc)
                        )
                    else:
                        existing.value = value

                upsert('TELEGRAM_API_ID',      str(payload.user_api_id),      "Telegram API ID")
                upsert('TELEGRAM_API_HASH',    payload.user_api_hash,         "Telegram API hash")
                upsert('TELEGRAM_BOT_TOKEN',   payload.bot_token,             "Telegram bot token")
                if payload.storage_channel_id:
                    upsert('TELEGRAM_STORAGE_CHANNEL_ID', str(payload.storage_channel_id),
                           "Telegram storage channel ID")
                if payload.user_proxy:
                    upsert('TELEGRAM_PROXY', payload.user_proxy,
                           "Telegram MTProto proxy")
                await conn.commit()

        await _persist_config_async()
        logger.info("All config values persisted to DB")
    except Exception as e:
        logger.warning(f"Could not persist all config to DB: {e}")

    # 7. Load user account into pool
    await session_manager.load_account_to_pool(user_acc)

    # 8. Notify all admins that the bot is active
    admin_list = [super_admin.telegram_id] + admin_ids_to_create
    for admin_id in admin_list:
        try:
            await tg_client.send_message(admin_id, "🟢 ربات فعال است")
            logger.info("Sent activation notification to admin %d", admin_id)
        except Exception as e:
            logger.warning("Failed to notify admin %d: %s", admin_id, e)

    # 9. Generate tokens for super admin
    access_token = create_access_token(super_admin.telegram_id, version=super_admin.auth_version)
    refresh_token = create_refresh_token(super_admin.telegram_id, version=super_admin.auth_version)

    return SetupCompleteResponse(
        success=True,
        message="Setup complete. Client pools initialized.",
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/system-status")
async def system_status():
    """
    Comprehensive system status check.

    This endpoint provides detailed information about:
    - Setup configuration status
    - Database contents (bot config, user accounts, admins)
    - Encryption key health (can we decrypt stored credentials?)
    - Whether system is ready for bot operation
    - If not ready, what's missing and should show setup wizard

    Temporary for debugging — no auth required.
    """
    from ..config import get_settings, is_configured, validate_startup_config, check_decryption_health
    from ..database import get_engine
    from sqlalchemy import select

    s = get_settings()
    configured = await is_configured(s)

    # Check DB contents
    has_bots = False
    has_accounts = False
    has_admin = False
    db_error = None

    try:
        eng = get_engine()
        if eng:
            async with eng.begin() as conn:
                has_bots = (await conn.execute(select(BotConfig).limit(1))).scalar_one_or_none() is not None
                has_accounts = (await conn.execute(select(UserAccount).limit(1))).scalar_one_or_none() is not None
                has_admin = (await conn.execute(select(AdminUser).limit(1))).scalar_one_or_none() is not None
    except Exception as e:
        db_error = str(e)
        logger.error(f"Database status check failed: {e}")

    # Run validation
    is_valid, missing_fields = await validate_startup_config(s)
    decryption_ok, dec_error_count = await check_decryption_health()

    # Determine if we should show setup wizard
    should_show_setup = not is_valid or not decryption_ok or not configured

    # Calculate readiness
    ready_for_bot = configured and has_bots and has_accounts and has_admin and is_valid and decryption_ok

    # Get DB info summary
    db_summary = {
        "has_bots": has_bots,
        "has_accounts": has_accounts,
        "has_admin": has_admin,
        "db_error": db_error,
    }

    # Get validation details
    validation = {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "decryption_ok": decryption_ok,
        "decryption_errors": dec_error_count,
    }

    # Additional info for debugging
    # If decryption fails but data exists in DB, we need to show setup wizard
    # This happens when JWT_SECRET changed between runs

    return {
        "system_ready": ready_for_bot,
        "configured": configured,
        "has_bots_in_db": has_bots,
        "has_accounts_in_db": has_accounts,
        "has_admin_in_db": has_admin,
        "show_setup_wizard": should_show_setup,
        "database_summary": db_summary,
        "validation": validation,
        "telegram_bot_token_set": bool(s.telegram_bot_token),
        "telegram_api_id_set": bool(s.telegram_api_id),
        "telegram_storage_channel_id_set": bool(s.telegram_storage_channel_id),
        "jwt_secret_status": "set" if s.jwt_secret and s.jwt_secret != "change-me-in-production-please-set-via-panel" else "not_set",
        "notes": "If show_setup_wizard=true and decryption_ok=false, JWT_SECRET may have changed. Run setup again to regenerate credentials."
    }


@router.get("/status")
async def setup_status():
    """Check if setup is already complete."""
    from ..config import get_settings, is_configured

    s = get_settings()
    configured = await is_configured(s)

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