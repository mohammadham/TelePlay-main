"""
Upload and send-to-bot endpoints for file handling.
"""
import secrets
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from pathlib import Path

from ..database import get_db
from ..models import File, User
from ..schemas import FileResponse
from ..auth import get_current_user
from ..telegram import forward_to_storage_channel, tg_client
from ..config import get_settings
from ..services import (
    escape_like,
    sanitize_filename,
    add_urls_to_file,
)

router = APIRouter(tags=["Upload"])
settings = get_settings()

# Temporary upload directory
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def generate_file_id() -> str:
    """Generate a unique file ID."""
    return secrets.token_urlsafe(32)


async def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    """Save uploaded file to destination."""
    try:
        with destination.open("wb") as buffer:
            content = await upload_file.read()
            buffer.write(content)
    finally:
        await upload_file.close()


@router.post("/upload", response_model=dict)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = FastAPIFile(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file and store it temporarily.
    Returns a file ID that can be used with /send-to-bot endpoint.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Generate unique file ID
    file_id = generate_file_id()

    # Create file path
    file_extension = Path(file.filename).suffix
    stored_filename = f"{file_id}{file_extension}"
    file_path = UPLOAD_DIR / stored_filename

    # Save file temporarily
    await save_upload_file(file, file_path)

    # Get file size
    file_size = file_path.stat().st_size

    # Store file metadata in database (without Telegram info yet)
    db_file = File(
        user_id=current_user.id,
        file_id="",  # Will be populated when sent to bot
        file_unique_id="",  # Will be populated when sent to bot
        channel_message_id=0,  # Will be populated when sent to bot
        file_name=sanitize_filename(file.filename),
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        file_type="document",  # Default type, can be updated later
        duration=None,
        width=None,
        height=None,
        thumbnail_file_id=None,
    )

    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)

    # Return file ID for use with send-to-bot endpoint
    return {
        "file_id": str(db_file.id),
        "message": "File uploaded successfully. Use /send-to-bot to send to Telegram.",
        "filename": db_file.file_name,
        "size": db_file.file_size
    }


@router.post("/send-to-bot", response_model=FileResponse)
async def send_file_to_bot(
    background_tasks: BackgroundTasks,
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a previously uploaded file to the Telegram storage bot.
    Returns the file information with Telegram IDs populated.
    """
    # Get the file from database
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    db_file = result.scalar_one_or_none()

    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if file has already been processed
    if db_file.file_id and db_file.channel_message_id:
        # File already sent to bot, return existing info
        return FileResponse(**add_urls_to_file(db_file))

    # Get the temporary file path
    file_extension = Path(db_file.file_name).suffix
    # Find the actual stored file (might have different extension from upload)
    stored_files = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not stored_files:
        raise HTTPException(status_code=404, detail="Uploaded file not found on disk")

    file_path = stored_files[0]

    try:
        # Send file to Telegram storage channel
        from pyrogram.types import InputMediaDocument

        # Send as document to storage channel
        sent_message = await tg_client.send_document(
            chat_id=settings.telegram_storage_channel_id,
            document=str(file_path),
            caption=db_file.file_name
        )

        # Update file with Telegram information
        db_file.file_id = sent_message.document.file_id
        db_file.file_unique_id = sent_message.document.file_unique_id
        db_file.channel_message_id = sent_message.id

        # Update file type based on mime type if possible
        if db_file.mime_type:
            if db_file.mime_type.startswith("video/"):
                db_file.file_type = "video"
            elif db_file.mime_type.startswith("audio/"):
                db_file.file_type = "audio"
            elif db_file.mime_type.startswith("image/"):
                db_file.file_type = "image"
            else:
                db_file.file_type = "document"

        await db.commit()
        await db.refresh(db_file)

        # Clean up temporary file in background
        background_tasks.add_task(lambda: file_path.unlink(missing_ok=True))

        # Return updated file info
        return FileResponse(**add_urls_to_file(db_file))

    except Exception as e:
        # Clean up on error
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send file to Telegram bot: {str(e)}"
        )


@router.on_event("shutdown")
def cleanup_temp_files():
    """Clean up temporary upload directory on shutdown."""
    import shutil
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)