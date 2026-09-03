"""
Admin Bots API — Manage multiple bot tokens
"""
from datetime import datetime
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..database import get_db
from ..models import BotConfig, AdminUser
from ..auth import require_admin
from ..encryption import encrypt, decrypt
from ..pool_manager import pool_manager
from ..patch import Client
from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/bots", tags=["Admin Bots"])

BOT_PURPOSES = ["MAIN", "HELPER", "ADS", "STORAGE"]

class BotCreateRequest(BaseModel):
    name: str
    token: str
    purpose: str = "HELPER"
    is_active: bool = True

class BotUpdateRequest(BaseModel):
    name: Optional[str] = None
    token: Optional[str] = None
    purpose: Optional[str] = None
    is_active: Optional[bool] = None

class BotResponse(BaseModel):
    id: int
    name: str
    username: Optional[str] = None
    bot_user_id: Optional[int] = None
    purpose: str
    is_active: bool
    rate_limit_remaining: int
    last_used: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[BotResponse])
async def list_bots(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    """List all bot configurations."""
    result = await db.execute(select(BotConfig).order_by(BotConfig.created_at.desc()))
    bots = result.scalars().all()
    return bots

@router.post("", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    payload: BotCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Add a new bot token, validate it, and add to pool."""
    if payload.purpose not in BOT_PURPOSES:
        raise HTTPException(400, f"Invalid purpose. Must be one of: {BOT_PURPOSES}")
    
    # Check name uniqueness
    existing = await db.execute(select(BotConfig).where(BotConfig.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Bot with name '{payload.name}' already exists")
    
    # Validate token with Telegram
    settings = get_settings()
    try:
        async with Client(
            "validate_new_bot",
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            bot_token=payload.token,
            in_memory=True,
            no_updates=True,
        ) as client:
            await client.start()
            me = await client.get_me()
            bot_user_id = me.id
            username = me.username
    except Exception as e:
        logger.warning(f"Bot token validation failed: {e}")
        raise HTTPException(400, f"Invalid bot token: {e}")
    
    # Create bot config
    bot = BotConfig(
        name=payload.name,
        token_encrypted=encrypt(payload.token),
        bot_user_id=bot_user_id,
        username=username,
        purpose=payload.purpose,
        is_active=payload.is_active,
        created_by=current_user.id,
    )
    db.add(bot)
    await db.commit()
    await db.refresh(bot)
    
    # Add to pool if active
    if payload.is_active:
        try:
            new_client = Client(
                name=f"bot_{bot.id}",
                api_id=settings.telegram_api_id,
                api_hash=settings.telegram_api_hash,
                bot_token=payload.token,
                ipv6=False,
                max_concurrent_transmissions=settings.telegram_client_concurrency,
                no_updates=(bot.purpose != "MAIN"),
            )
            await new_client.start()
            pool_manager.add_bot(new_client, len(pool_manager.bot_pool))
            logger.info(f"Bot {bot.name} added to pool")
        except Exception as e:
            logger.error(f"Failed to add bot to pool: {e}")
    
    return bot

@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: int,
    payload: BotUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Update bot configuration."""
    result = await db.execute(select(BotConfig).where(BotConfig.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    # Validate purpose if provided
    if payload.purpose and payload.purpose not in BOT_PURPOSES:
        raise HTTPException(400, f"Invalid purpose. Must be one of: {BOT_PURPOSES}")
    
    # Validate name uniqueness if changing
    if payload.name and payload.name != bot.name:
        existing = await db.execute(select(BotConfig).where(BotConfig.name == payload.name))
        if existing.scalar_one_or_none():
            raise HTTPException(400, f"Bot with name '{payload.name}' already exists")
    
    # Update fields
    update_data = payload.model_dump(exclude_unset=True)
    token_changed = "token" in update_data
    
    if token_changed:
        new_token = update_data.pop("token")
        # Validate new token
        settings = get_settings()
        try:
            async with Client(
                "validate_updated_bot",
                api_id=settings.telegram_api_id,
                api_hash=settings.telegram_api_hash,
                bot_token=new_token,
                in_memory=True,
                no_updates=True,
            ) as client:
                await client.start()
                me = await client.get_me()
                bot.bot_user_id = me.id
                bot.username = me.username
        except Exception as e:
            raise HTTPException(400, f"Invalid bot token: {e}")
        
        bot.token_encrypted = encrypt(new_token)
    
    for field, value in update_data.items():
        setattr(bot, field, value)
    
    await db.commit()
    await db.refresh(bot)
    
    # Re-add to pool if token changed or active status changed
    if token_changed or "is_active" in update_data:
        # Remove old client from pool
        for idx, client in list(pool_manager.bot_pool.items()):
            try:
                me = await client.get_me()
                if me.id == bot.bot_user_id:
                    await client.stop()
                    pool_manager.remove_bot(idx)
                    break
            except Exception:
                pool_manager.remove_bot(idx)
        
        # Add new client if active
        if bot.is_active:
            settings = get_settings()
            try:
                token = decrypt(bot.token_encrypted)
                new_client = Client(
                    name=f"bot_{bot.id}",
                    api_id=settings.telegram_api_id,
                    api_hash=settings.telegram_api_hash,
                    bot_token=token,
                    ipv6=False,
                    max_concurrent_transmissions=settings.telegram_client_concurrency,
                    no_updates=(bot.purpose != "MAIN"),
                )
                await new_client.start()
                pool_manager.add_bot(new_client, len(pool_manager.bot_pool))
            except Exception as e:
                logger.error(f"Failed to re-add bot to pool: {e}")
    
    return bot

@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Delete a bot configuration."""
    result = await db.execute(select(BotConfig).where(BotConfig.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    # Prevent deleting MAIN bot if it's the only one
    if bot.purpose == "MAIN":
        main_count = await db.execute(
            select(BotConfig).where(BotConfig.purpose == "MAIN", BotConfig.is_active == True)
        )
        if len(main_count.scalars().all()) <= 1:
            raise HTTPException(400, "Cannot delete the only MAIN bot. Add another MAIN bot first.")
    
    # Stop and remove from pool
    for idx, client in list(pool_manager.bot_pool.items()):
        try:
            me = await client.get_me()
            if me.id == bot.bot_user_id:
                await client.stop()
                pool_manager.remove_bot(idx)
                break
        except Exception:
            pool_manager.remove_bot(idx)
    
    await db.delete(bot)
    await db.commit()
    
    return {"ok": True, "message": f"Bot '{bot.name}' deleted"}

@router.post("/{bot_id}/test")
async def test_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_admin),
):
    """Send a test message to the super admin via this bot."""
    result = await db.execute(select(BotConfig).where(BotConfig.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(404, "Bot not found")
    
    if not bot.is_active:
        raise HTTPException(400, "Bot is not active")
    
    token = decrypt(bot.token_encrypted)
    settings = get_settings()
    
    try:
        async with Client(
            "test_bot",
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            bot_token=token,
            in_memory=True,
            no_updates=True,
        ) as client:
            await client.start()
            me = await client.get_me()
            
            # Send test message to super admin (current user if they're super admin)
            # In production, you'd send to all super admins
            await client.send_message(
                current_user.telegram_id,
                f"🤖 **Test message from bot: @{me.username}**\n"
                f"Name: {bot.name}\n"
                f"Purpose: {bot.purpose}\n"
                f"Status: ✅ Working correctly"
            )
        
        # Update last_used
        from datetime import datetime
        bot.last_used = datetime.utcnow()
        await db.commit()
        
        return {"ok": True, "message": f"Test message sent via @{me.username}"}
    except Exception as e:
        logger.error(f"Bot test failed: {e}")
        raise HTTPException(500, f"Test failed: {e}")