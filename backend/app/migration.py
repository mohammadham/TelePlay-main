"""
Migration utilities for upgrading from single-bot to multi-bot architecture.
Detects existing settings and creates BotConfig, UserAccount, AdminUser records.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models import BotConfig, UserAccount, AdminUser, AppSetting
from .config import get_settings
from .encryption import encrypt

logger = logging.getLogger(__name__)


async def migrate_existing_settings(db: AsyncSession) -> bool:
    """
    Migrate legacy settings to new multi-bot/user/admin models.
    Returns True if migration was performed, False if already migrated or no legacy data.
    """
    settings = get_settings()
    
    # Check if already migrated
    existing_bots = await db.execute(select(BotConfig).limit(1))
    if existing_bots.scalar_one_or_none():
        logger.info("Migration already performed (BotConfig exists)")
        return False
    
    existing_accounts = await db.execute(select(UserAccount).limit(1))
    if existing_accounts.scalar_one_or_none():
        logger.info("Migration already performed (UserAccount exists)")
        return False
    
    existing_admins = await db.execute(select(AdminUser).limit(1))
    if existing_admins.scalar_one_or_none():
        logger.info("Migration already performed (AdminUser exists)")
        return False
    
    # Check for legacy environment variables
    has_legacy_bot = bool(settings.telegram_bot_token)
    has_legacy_user = bool(settings.telegram_api_id and settings.telegram_api_hash)
    has_legacy_admin = bool(settings.admin_ids)
    
    if not (has_legacy_bot or has_legacy_user or has_legacy_admin):
        logger.info("No legacy settings to migrate")
        return False
    
    logger.info("Starting migration from legacy settings...")
    
    # 1. Create BotConfig from legacy bot token
    if has_legacy_bot:
        try:
            from .patch import Client
            async with Client(
                "migrate_bot",
                api_id=settings.telegram_api_id,
                api_hash=settings.telegram_api_hash,
                bot_token=settings.telegram_bot_token,
                in_memory=True,
                no_updates=True,
            ) as client:
                await client.start()
                me = await client.get_me()
                
                bot = BotConfig(
                    name="main",
                    token_encrypted=encrypt(settings.telegram_bot_token),
                    bot_user_id=me.id,
                    username=me.username,
                    purpose="MAIN",
                    is_active=True,
                )
                db.add(bot)
                logger.info("Migrated main bot: @%s (%d)", me.username, me.id)
        except Exception as e:
            logger.warning("Failed to migrate main bot token: %s", e)
    
    # 2. Create UserAccount from legacy user session (if exists in AppSetting or session file)
    if has_legacy_user:
        # Check for session in AppSetting
        session_setting = await db.execute(
            select(AppSetting).where(AppSetting.key == "TELEGRAM_SESSION_STRING")
        )
        session_row = session_setting.scalar_one_or_none()
        
        # Check for 2FA password in AppSetting
        twofa_setting = await db.execute(
            select(AppSetting).where(AppSetting.key == "TELEGRAM_2FA_PASSWORD")
        )
        twofa_row = twofa_setting.scalar_one_or_none()
        
        # Try to get session from file as fallback
        session_string = session_row.value if session_row else None
        two_fa_password = twofa_row.value if twofa_row else None
        
        if session_string:
            try:
                from .patch import Client
                client = Client(
                    "migrate_user",
                    api_id=settings.telegram_api_id,
                    api_hash=settings.telegram_api_hash,
                    session_string=session_string,
                    in_memory=True,
                )
                await client.start()
                me = await client.get_me()
                
                account = UserAccount(
                    name="storage_1",
                    phone="migrated",
                    api_id=settings.telegram_api_id,
                    api_hash_encrypted=encrypt(settings.telegram_api_hash),
                    session_string_encrypted=encrypt(session_string),
                    two_fa_password_encrypted=encrypt(two_fa_password) if two_fa_password else None,
                    user_id=me.id,
                    username=me.username,
                    purpose="STORAGE",
                    is_active=True,
                )
                db.add(account)
                logger.info("Migrated user account: @%s (%d)", me.username, me.id)
            except Exception as e:
                logger.warning("Failed to migrate user session: %s", e)
        else:
            logger.info("Legacy API credentials found but no session string - user account not migrated")
    
    # 3. Create AdminUser from legacy ADMIN_TELEGRAM_IDS
    if has_legacy_admin:
        for i, admin_id in enumerate(settings.admin_ids):
            role = "SUPER_ADMIN" if i == 0 else "ADMIN"
            can_manage = role == "SUPER_ADMIN"
            
            admin = AdminUser(
                telegram_id=admin_id,
                role=role,
                is_active=True,
                can_manage_bots=can_manage,
                can_manage_accounts=can_manage,
                can_manage_admins=can_manage,
                created_by=None,  # First admin has no creator
            )
            db.add(admin)
            logger.info("Migrated admin: %d as %s", admin_id, role)
    
    await db.commit()
    logger.info("Migration completed successfully")
    return True


async def ensure_default_bot_config(db: AsyncSession) -> None:
    """Ensure at least one MAIN bot exists in the pool."""
    existing = await db.execute(select(BotConfig).where(BotConfig.purpose == "MAIN", BotConfig.is_active == True))
    if not existing.scalar_one_or_none():
        settings = get_settings()
        if settings.telegram_bot_token:
            try:
                from .patch import Client
                async with Client(
                    "ensure_main_bot",
                    api_id=settings.telegram_api_id,
                    api_hash=settings.telegram_api_hash,
                    bot_token=settings.telegram_bot_token,
                    in_memory=True,
                    no_updates=True,
                ) as client:
                    await client.start()
                    me = await client.get_me()
                    
                    bot = BotConfig(
                        name="main",
                        token_encrypted=encrypt(settings.telegram_bot_token),
                        bot_user_id=me.id,
                        username=me.username,
                        purpose="MAIN",
                        is_active=True,
                    )
                    db.add(bot)
                    await db.commit()
                    logger.info("Created default MAIN bot: @%s", me.username)
            except Exception as e:
                logger.error("Failed to create default MAIN bot: %s", e)