"""
Admin Upload Configuration API — Manage upload strategy and feature flags.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import AdminUser
from ..auth import require_admin
from ..config import get_settings
from ..pool_manager import pool_manager, SelectionStrategy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/upload", tags=["Admin Upload"])


class UploadConfigResponse(BaseModel):
    """Response model for upload configuration."""
    upload_strategy: str
    web_upload_enabled: bool
    bot_fallback_enabled: bool
    max_concurrent_uploads: int
    my_music_enabled: bool


class UploadConfigUpdateRequest(BaseModel):
    """Request model for updating upload configuration."""
    upload_strategy: Optional[str] = None
    web_upload_enabled: Optional[bool] = None
    bot_fallback_enabled: Optional[bool] = None
    max_concurrent_uploads: Optional[int] = None
    my_music_enabled: Optional[bool] = None


class UploadConfigRequest(BaseModel):
    """Full configuration update request."""
    upload_strategy: str
    web_upload_enabled: bool
    bot_fallback_enabled: bool
    max_concurrent_uploads: int
    my_music_enabled: bool


class PoolHealthResponse(BaseModel):
    """Response model for pool health."""
    total_bots: int
    total_users: int
    active_users: int
    total_active_clients: int


@router.get("/config", response_model=UploadConfigResponse)
async def get_upload_config(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Get current upload configuration."""
    from ..pool_manager import SelectionStrategy

    settings = get_settings()

    # Get strategy from pool manager
    strategy = pool_manager.strategy.value if pool_manager.strategy else SelectionStrategy.ROUND_ROBIN.value

    # Get feature flags from DB settings
    web_upload = "true"
    bot_fallback = "true"
    max_concurrent = 5
    my_music = "true"

    # Read from AppSetting table
    try:
        from ..models import AppSetting as AS
        result = await db.execute(select(AS).where(AS.key == "WEB_UPLOAD_ENABLED"))
        setting = result.scalar_one_or_none()
        if setting:
            web_upload = setting.value
        result = await db.execute(select(AS).where(AS.key == "BOT_FALLBACK_ENABLED"))
        setting = result.scalar_one_or_none()
        if setting:
            bot_fallback = setting.value
        result = await db.execute(select(AS).where(AS.key == "MAX_CONCURRENT_UPLOADS"))
        setting = result.scalar_one_or_none()
        if setting:
            max_concurrent = setting.value
        result = await db.execute(select(AS).where(AS.key == "MY_MUSIC_ENABLED"))
        setting = result.scalar_one_or_none()
        if setting:
            my_music = setting.value
    except Exception as e:
        logger.error(f"Error reading settings: {e}")

    return UploadConfigResponse(
        upload_strategy=strategy,
        web_upload_enabled=str(web_upload).lower() == "true",
        bot_fallback_enabled=str(bot_fallback).lower() == "true",
        max_concurrent_uploads=max_concurrent,
        my_music_enabled=str(my_music).lower() == "true",
    )


@router.put("/config", response_model=UploadConfigResponse)
async def update_upload_config(
    payload: UploadConfigRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """Update upload configuration."""
    from ..models import AppSetting as AS

    # Validate strategy
    valid_strategies = [s.value for s in SelectionStrategy]
    if payload.upload_strategy not in valid_strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid upload strategy. Must be one of: {valid_strategies}"
        )

    # Update strategy in pool manager
    new_strategy = SelectionStrategy(payload.upload_strategy)
    pool_manager.set_strategy(new_strategy)

    # Update feature flags in database
    settings_to_update = {
        "UPLOAD_STRATEGY": payload.upload_strategy,
        "WEB_UPLOAD_ENABLED": str(payload.web_upload_enabled).lower(),
        "BOT_FALLBACK_ENABLED": str(payload.bot_fallback_enabled).lower(),
        "MAX_CONCURRENT_UPLOADS": str(payload.max_concurrent_uploads),
        "MY_MUSIC_ENABLED": str(payload.my_music_enabled).lower(),
    }

    for key, value in settings_to_update.items():
        try:
            result = await db.execute(select(AS).where(AS.key == key))
            setting = result.scalar_one_or_none()
            if setting:
                setting.value = value
            else:
                setting = AS(key=key, value=value, description="Admin-configurable setting")
                db.add(setting)
            await db.commit()
            logger.info(f"Updated setting: {key} = {value}")
        except Exception as e:
            logger.error(f"Failed to update setting {key}: {e}")

    # Reload settings in memory
    try:
        from ..config import mark_db_ready
        settings = get_settings()
        await mark_db_ready(settings)
    except Exception as e:
        logger.warning(f"Failed to reload settings: {e}")

    # Apply to current runtime state
    settings_obj = get_settings()
    if hasattr(settings_obj, 'web_upload_enabled'):
        settings_obj.web_upload_enabled = payload.web_upload_enabled
    if hasattr(settings_obj, 'bot_fallback_enabled'):
        settings_obj.bot_fallback_enabled = payload.bot_fallback_enabled

    return UploadConfigResponse(
        upload_strategy=new_strategy.value,
        web_upload_enabled=payload.web_upload_enabled,
        bot_fallback_enabled=payload.bot_fallback_enabled,
        max_concurrent_uploads=payload.max_concurrent_uploads,
        my_music_enabled=payload.my_music_enabled,
    )


@router.get("/health", response_model=PoolHealthResponse)
async def get_pool_health(
    admin: AdminUser = Depends(require_admin),
):
    """Get pool health status."""
    health = await pool_manager.health_check()

    # Count active users
    active_users = sum(1 for info in health.get("user_clients", {}).values()
                     if info.get("is_connected", False))

    return PoolHealthResponse(
        total_bots=health.get("total_bots", 0),
        total_users=health.get("total_users", 0),
        active_users=active_users,
        total_active_clients=health.get("total_bots", 0) + active_users,
    )


@router.post("/health/refresh", response_model=PoolHealthResponse)
async def refresh_pool_health(
    admin: AdminUser = Depends(require_admin),
):
    """Force refresh pool health check."""
    health = await pool_manager.health_check()
    return get_pool_health(admin)
