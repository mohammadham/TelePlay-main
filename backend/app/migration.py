"""
Migration utilities for upgrading from single-bot to multi-bot architecture.
Detects existing settings and creates BotConfig, UserAccount, AdminUser records.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select, text, inspect
from sqlalchemy.engine import Connection

from .models import BotConfig, UserAccount, AdminUser, AppSetting, SEOConfig, ChannelImportJob
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


def _sync_migrate_seo_config_geo_list(conn: Connection) -> None:
    """Sync function to add geo_list column to seo_config."""
    inspector = inspect(conn)
    if not inspector.has_table("seo_config"):
        return
    existing_cols = {c["name"] for c in inspector.get_columns("seo_config")}
    if "geo_list" not in existing_cols:
        conn.execute(text("ALTER TABLE seo_config ADD COLUMN geo_list TEXT DEFAULT '[]'"))
        logger.info("Added geo_list column to seo_config")


def _sync_migrate_seo_config_ai_description(conn: Connection) -> None:
    """Sync function to add ai_agent_description column to seo_config."""
    inspector = inspect(conn)
    if not inspector.has_table("seo_config"):
        return
    existing_cols = {c["name"] for c in inspector.get_columns("seo_config")}
    if "ai_agent_description" not in existing_cols:
        conn.execute(text("ALTER TABLE seo_config ADD COLUMN ai_agent_description TEXT DEFAULT ''"))
        logger.info("Added ai_agent_description column to seo_config")


async def migrate_seo_config_geo_list(engine: AsyncEngine) -> None:
    """Ensure geo_list column exists in seo_config table using run_sync."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_sync_migrate_seo_config_geo_list)
    except Exception as e:
        logger.warning("SEO geo_list migration failed: %s", e)


async def migrate_seo_config_ai_description(engine: AsyncEngine) -> None:
    """Ensure ai_agent_description column exists in seo_config table using run_sync."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_sync_migrate_seo_config_ai_description)
    except Exception as e:
        logger.warning("SEO ai_agent_description migration failed: %s", e)


def _sync_migrate_user_account_last_error(conn: Connection) -> None:
    """Sync function to add last_error column to user_accounts table."""
    inspector = inspect(conn)
    if not inspector.has_table("user_accounts"):
        return
    existing_cols = {c["name"] for c in inspector.get_columns("user_accounts")}
    if "last_error" not in existing_cols:
        conn.execute(text("ALTER TABLE user_accounts ADD COLUMN last_error TEXT"))
        logger.info("Added last_error column to user_accounts")


async def migrate_user_account_last_error(engine: AsyncEngine) -> None:
    """Ensure last_error column exists in user_accounts table using run_sync."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_sync_migrate_user_account_last_error)
    except Exception as e:
        logger.warning("user_accounts last_error migration failed: %s", e)


def _sync_migrate_channel_import_jobs(conn: Connection) -> None:
    """Sync function to create channel_import_jobs table and add missing columns."""
    inspector = inspect(conn)
    
    # Check if table exists
    if not inspector.has_table("channel_import_jobs"):
        # Create table using SQLAlchemy metadata
        ChannelImportJob.__table__.create(conn, checkfirst=True)
        logger.info("Created channel_import_jobs table via SQLAlchemy")
        return
    
    # Table exists - check for missing columns
    existing_cols = {c["name"] for c in inspector.get_columns("channel_import_jobs")}
    needed_cols = {
        "min_file_size": "BIGINT",
        "max_file_size": "BIGINT",
        "filename_regex": "TEXT",
        "caption_regex": "TEXT",
    }
    
    for col_name, col_type in needed_cols.items():
        if col_name not in existing_cols:
            conn.execute(text(f"ALTER TABLE channel_import_jobs ADD COLUMN {col_name} {col_type}"))
            logger.info("Added %s column to channel_import_jobs", col_name)


async def create_channel_import_jobs_table(engine: AsyncEngine) -> None:
    """Create channel_import_jobs table and add missing columns using run_sync."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_sync_migrate_channel_import_jobs)
    except Exception as e:
        logger.warning("channel_import_jobs migration failed: %s", e)