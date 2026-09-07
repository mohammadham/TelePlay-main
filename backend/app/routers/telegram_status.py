"""
Telegram Bot Status API — Check and control bot connection.
No auth required temporarily for debugging.
"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..config import get_settings, is_configured, validate_startup_config, check_decryption_health
from ..telegram import tg_client, build_clients, start_telegram_client, stop_all_clients, clients as client_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["Telegram Status"])


class ClientStatus(BaseModel):
    index: int
    name: str
    is_connected: bool
    username: Optional[str] = None
    bot_user_id: Optional[int] = None
    error: Optional[str] = None


class TelegramStatusResponse(BaseModel):
    configured: bool
    bot_token_set: bool
    api_id_set: bool
    api_hash_set: bool
    storage_channel_set: bool
    is_configured: bool
    tg_client: Optional[ClientStatus] = None
    all_clients: list[ClientStatus] = []
    startup_error: Optional[str] = None
    validation: dict = {}


class TelegramStartRequest(BaseModel):
    force: bool = False


class TelegramStartResponse(BaseModel):
    success: bool
    message: str
    client_count: int


@router.get("/status", response_model=TelegramStatusResponse)
async def get_telegram_status():
    """Get current Telegram bot status — connection, configured state, validation info.

    No auth required — temporary for debugging during Railway deployment.
    """
    settings = get_settings()
    configured = await is_configured(settings)

    bot_token_set = bool(settings.telegram_bot_token and
                        settings.telegram_bot_token != "your_bot_token")
    api_id_set = bool(settings.telegram_api_id and settings.telegram_api_id != 0)
    api_hash_set = bool(settings.telegram_api_hash and
                        settings.telegram_api_hash != "your_api_hash")
    storage_set = bool(settings.telegram_storage_channel_id and
                       settings.telegram_storage_channel_id != 0)

    # Run full validation
    is_valid, missing_fields = await validate_startup_config(settings)
    decryption_ok, dec_error_count = await check_decryption_health()

    validation = {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "decryption_ok": decryption_ok,
        "decryption_errors": dec_error_count,
    }

    # Gather client info
    all_clients = []
    for i, c in enumerate(client_pool):
        try:
            bot_user_id = getattr(c, 'bot_user_id', None)
            username = getattr(c, 'username', None)
            is_conn = getattr(c, 'is_connected', False)
            all_clients.append(ClientStatus(
                index=i,
                name=getattr(c, 'name', f'bot_{i}'),
                is_connected=is_conn,
                username=username,
                bot_user_id=bot_user_id,
            ))
        except Exception as e:
            all_clients.append(ClientStatus(
                index=i,
                name=getattr(c, 'name', f'bot_{i}'),
                is_connected=False,
                error=str(e),
            ))

    tg_info = None
    if tg_client:
        try:
            tg_info = ClientStatus(
                index=0,
                name=getattr(tg_client, 'name', 'main'),
                is_connected=getattr(tg_client, 'is_connected', False),
                username=getattr(tg_client, 'username', None),
                bot_user_id=getattr(tg_client, 'bot_user_id', None),
            )
        except Exception:
            tg_info = ClientStatus(
                index=0,
                name=getattr(tg_client, 'name', 'main'),
                is_connected=False,
            )

    return TelegramStatusResponse(
        configured=configured,
        bot_token_set=bot_token_set,
        api_id_set=api_id_set,
        api_hash_set=api_hash_set,
        storage_channel_set=storage_set,
        is_configured=configured,
        tg_client=tg_info,
        all_clients=all_clients,
        startup_error=None if is_valid and decryption_ok else "Validation failed - setup required",
        validation=validation,
    )


@router.post("/start", response_model=TelegramStartResponse)
async def start_telegram(payload: TelegramStartRequest = None):
    """Start/restart the Telegram client pool.

    No auth required — temporary for debugging during Railway deployment.
    """
    from ..encryption import ensure_encryption_key

    try:
        # Ensure encryption key is loaded (derived from JWT_SECRET)
        await ensure_encryption_key()

        # Stop existing clients if force=True or they're already running
        if payload.force or (tg_client and tg_client.is_connected):
            logger.info("Stopping existing Telegram client(s)...")
            await stop_all_clients()

        # Build and start clients
        build_clients()
        await start_telegram_client()

        client_count = len(client_pool)
        logger.info("Telegram client(s) started successfully (%d client(s))", client_count)

        return TelegramStartResponse(
            success=True,
            message=f"Telegram client(s) started ({client_count} client(s))",
            client_count=client_count,
        )
    except Exception as e:
        logger.error(f"Failed to start Telegram client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start: {e}")


@router.post("/stop", response_model=TelegramStartResponse)
async def stop_telegram():
    """Stop all Telegram clients.

    No auth required — temporary for debugging during Railway deployment.
    """
    try:
        if tg_client and tg_client.is_connected:
            await stop_all_clients()
            logger.info("Telegram client(s) stopped")
            return TelegramStartResponse(
                success=True,
                message="Telegram client(s) stopped",
                client_count=len(client_pool),
            )
        return TelegramStartResponse(
            success=True,
            message="No active client to stop",
            client_count=len(client_pool),
        )
    except Exception as e:
        logger.error(f"Failed to stop Telegram client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop: {e}")
