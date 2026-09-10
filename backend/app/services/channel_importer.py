"""
Channel Import Service - Import files from Telegram storage channel history.
Uses MTProto user account to iterate channel messages and save file metadata.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_sessionmaker
from ..models import File, ChannelImportJob, UserAccount, Folder, AdminUser
from ..pool_manager import pool_manager
from ..config import get_settings
from ..services import sanitize_filename

logger = logging.getLogger(__name__)
settings = get_settings()


FILE_TYPE_MAP = {
    "video": ["video"],
    "audio": ["audio", "voice"],
    "document": ["document"],
    "image": ["photo"],
}


def get_media_from_message(message: Message) -> Optional[tuple]:
    """Extract media object and file_type from a Pyrogram Message."""
    if message.video:
        return message.video, "video"
    if message.audio:
        return message.audio, "audio"
    if message.voice:
        return message.voice, "audio"
    if message.document:
        return message.document, "document"
    if message.photo:
        return message.photo, "image"
    return None


def extract_file_info(media: Any, file_type: str) -> Dict[str, Any]:
    """Extract file metadata from media object (similar to bot.py handle_file)."""
    raw_filename = getattr(media, "file_name", None) or f"{file_type}_{datetime.utcnow().timestamp()}"
    file_size = getattr(media, "file_size", 0) or 0
    
    file_info = {
        "file_id": media.file_id,
        "file_unique_id": media.file_unique_id,
        "file_name": sanitize_filename(raw_filename),
        "file_size": file_size,
        "mime_type": getattr(media, "mime_type", None),
        "duration": getattr(media, "duration", None),
        "width": getattr(media, "width", None),
        "height": getattr(media, "height", None),
        "thumbnail_file_id": media.thumbs[0].file_id if getattr(media, "thumbs", None) else None,
    }
    return file_info


async def update_job_progress(
    db: AsyncSession,
    job_id: int,
    **kwargs
) -> None:
    """Update job progress fields."""
    from sqlalchemy import update
    await db.execute(
        update(ChannelImportJob)
        .where(ChannelImportJob.id == job_id)
        .values(**kwargs)
    )
    await db.commit()


async def run_import_job(job_id: int) -> None:
    """
    Background task to import files from storage channel.
    Uses MTProto user client to iterate channel history.
    Supports resume from last_message_id on FloodWait or restart.
    """
    session_maker = get_sessionmaker()
    
    async with session_maker() as db:
        # Load job
        result = await db.execute(select(ChannelImportJob).where(ChannelImportJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.error(f"Import job {job_id} not found")
            return
        
        # Check if cancelled before starting
        if job.status == "cancelled":
            logger.info(f"Job {job_id} was cancelled before start")
            return
        
        # Get storage channel ID
        storage_channel_id = settings.telegram_storage_channel_id
        if storage_channel_id <= 0:
            await update_job_progress(db, job_id, status="failed", error_message="Storage channel not configured", finished_at=datetime.utcnow())
            return
        
        # Get user account client
        client: Optional[Client] = None
        if job.user_account_id:
            # Try to get specific account from pool
            for idx, c in pool_manager.user_pool.items():
                try:
                    me = await c.get_me()
                    # Check if this client matches the account
                    account_result = await db.execute(select(UserAccount).where(UserAccount.id == job.user_account_id))
                    account = account_result.scalar_one_or_none()
                    if account and me.id == account.user_id:
                        client = c
                        break
                except Exception:
                    continue
        
        if not client:
            # Fallback: get any available user client
            client = pool_manager.get_user("STORAGE")
        
        if not client:
            await update_job_progress(db, job_id, status="failed", error_message="No MTProto user account available", finished_at=datetime.utcnow())
            return
        
        # Update job status to running
        await update_job_progress(db, job_id, status="running", started_at=datetime.utcnow())
        
        # Parse file types filter
        try:
            allowed_types = json.loads(job.file_types)
        except json.JSONDecodeError:
            allowed_types = ["video", "audio", "document", "image"]
        
        # Build date filters
        date_from = job.date_from
        date_to = job.date_to
        
        # Get admin user for file ownership
        admin_result = await db.execute(select(AdminUser).where(AdminUser.id == job.admin_id))
        admin_user = admin_result.scalar_one_or_none()
        if not admin_user:
            await update_job_progress(db, job_id, status="failed", error_message="Admin user not found", finished_at=datetime.utcnow())
            return
        
        # Get or create the system user for imported files
        from ..models import User
        user_result = await db.execute(select(User).where(User.telegram_id == admin_user.telegram_id))
        sys_user = user_result.scalar_one_or_none()
        if not sys_user:
            sys_user = User(telegram_id=admin_user.telegram_id, username=admin_user.username, first_name=admin_user.first_name, last_name=admin_user.last_name)
            db.add(sys_user)
            await db.commit()
            await db.refresh(sys_user)
        
        target_folder_id = job.target_folder_id
        
        # Resume from last_message_id if available (for FloodWait recovery or server restart)
        offset_id = job.last_message_id
        offset_date = job.date_to if job.date_to else None
        
        logger.info(f"Starting import job {job_id} for channel {storage_channel_id}, types={allowed_types}, date_from={date_from}, date_to={date_to}, resume_from={offset_id}")
        
        try:
            scanned = job.total_scanned or 0
            imported = job.total_imported or 0
            skipped = job.total_skipped or 0
            errors = job.total_errors or 0
            last_msg_id = job.last_message_id
            
            # Iterate channel history with resume support
            async for message in client.get_chat_history(storage_channel_id, offset_date=offset_date, offset_id=offset_id):
                # Check if job was cancelled (every 25 iterations to reduce DB load)
                if scanned % 25 == 0:
                    job_check = await db.execute(select(ChannelImportJob).where(ChannelImportJob.id == job_id))
                    current_job = job_check.scalar_one_or_none()
                    if not current_job or current_job.status == "cancelled":
                        logger.info(f"Job {job_id} cancelled during execution")
                        break
                
                last_msg_id = message.id
                scanned += 1
                
                # Check date range
                if date_from and message.date < date_from:
                    # We've gone past the date range (messages are in reverse chronological order)
                    break
                
                if date_to and message.date > date_to:
                    continue
                
                # Check media type
                media_info = get_media_from_message(message)
                if not media_info:
                    continue
                
                media, file_type = media_info
                if file_type not in allowed_types:
                    continue
                
                # Check deduplication by channel_message_id OR file_unique_id
                existing = await db.execute(
                    select(File).where(
                        (File.channel_message_id == message.id) | 
                        (File.file_unique_id == media.file_unique_id)
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue
                
                try:
                    # Extract file info
                    file_info = extract_file_info(media, file_type)
                    
                    # Create file record
                    new_file = File(
                        user_id=sys_user.id,
                        folder_id=target_folder_id,
                        channel_message_id=message.id,
                        file_type=file_type,
                        **file_info
                    )
                    db.add(new_file)
                    await db.commit()
                    imported += 1
                    
                except Exception as e:
                    logger.error(f"Error importing message {message.id}: {e}")
                    errors += 1
                    await db.rollback()
                
                # Update progress every 10 messages
                if scanned % 10 == 0:
                    await update_job_progress(db, job_id, 
                        total_scanned=scanned,
                        total_imported=imported,
                        total_skipped=skipped,
                        total_errors=errors,
                        last_message_id=last_msg_id
                    )
            
            # Final update
            await update_job_progress(db, job_id,
                status="completed",
                total_scanned=scanned,
                total_imported=imported,
                total_skipped=skipped,
                total_errors=errors,
                last_message_id=last_msg_id,
                finished_at=datetime.utcnow()
            )
            logger.info(f"Import job {job_id} completed: scanned={scanned}, imported={imported}, skipped={skipped}, errors={errors}")
            
        except FloodWait as e:
            logger.warning(f"FloodWait in job {job_id}: sleeping for {e.value}s, will resume from message_id={last_msg_id}")
            await asyncio.sleep(e.value)
            # Update progress with last_message_id before resume
            await update_job_progress(db, job_id, last_message_id=last_msg_id)
            # Resume from last processed message
            await run_import_job(job_id)
        except Exception as e:
            logger.error(f"Import job {job_id} failed: {e}")
            await update_job_progress(db, job_id, status="failed", error_message=str(e), finished_at=datetime.utcnow())


async def preview_import(
    user_account_id: Optional[int],
    file_types: List[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime]
) -> Dict[str, int]:
    """
    Preview import - count messages without importing.
    Returns estimated counts.
    """
    storage_channel_id = settings.telegram_storage_channel_id
    if storage_channel_id <= 0:
        return {"error": "Storage channel not configured"}
    
    # Get user client
    client: Optional[Client] = None
    if user_account_id:
        session_maker = get_sessionmaker()
        async with session_maker() as db:
            account_result = await db.execute(select(UserAccount).where(UserAccount.id == user_account_id))
            account = account_result.scalar_one_or_none()
            if account:
                for idx, c in pool_manager.user_pool.items():
                    try:
                        me = await c.get_me()
                        if me.id == account.user_id:
                            client = c
                            break
                    except Exception:
                        continue
    
    if not client:
        client = pool_manager.get_user("STORAGE")
    
    if not client:
        return {"error": "No MTProto user account available"}
    
    offset_date = date_to if date_to else None
    scanned = 0
    matched = 0
    
    try:
        async for message in client.get_chat_history(storage_channel_id, offset_date=offset_date, limit=5000):
            if date_from and message.date < date_from:
                break
            if date_to and message.date > date_to:
                continue
            
            media_info = get_media_from_message(message)
            if not media_info:
                continue
            
            _, file_type = media_info
            if file_type in file_types:
                matched += 1
            scanned += 1
            
            if scanned >= 5000:
                break
    except FloodWait as e:
        logger.warning(f"FloodWait in preview: {e.value}s")
        return {"error": f"FloodWait: please wait {e.value}s and try again"}
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        return {"error": str(e)}
    
    return {
        "scanned": scanned,
        "estimated_matches": matched,
        "file_types": file_types,
    }