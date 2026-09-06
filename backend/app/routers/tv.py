"""
TV-specific API endpoints optimized for Android TV clients.
"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import File, User, Folder, WatchProgress, Track
from ..auth import get_current_user
from ..config import get_settings
from ..services import (
    escape_like,
    add_urls_to_file,
    fetch_recent_files,
    fetch_continue_watching_files
)
from ..schemas import TrackResponse  # used in type hints if needed

router = APIRouter(prefix="/tv", tags=["TV"])
settings = get_settings()


@router.get("/browse")
async def tv_browse(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get TV home screen data in a single request.
    Returns continue watching, recent files, folders, and music data.
    Optimized for TV client to minimize API calls.
    """
    # Get continue watching
    continue_watching = await fetch_continue_watching_files(db, current_user.id, 20)

    # Get recent files
    recent_files = await fetch_recent_files(db, current_user.id, 20)

    # Get top-level folders
    folders_query = (
        select(Folder)
        .where(Folder.user_id == current_user.id, Folder.parent_id == None)
        .order_by(Folder.name)
    )
    folders_result = await db.execute(folders_query)
    folders = folders_result.scalars().all()

    # Get featured music videos (play_count >= 10, media_type=music_video)
    featured_mvs_query = (
        select(Track)
        .where(
            Track.media_type == "music_video",
            Track.play_count >= 10
        )
        .options(selectinload(Track.artist))
        .order_by(desc(Track.play_count))
        .limit(10)
    )
    featured_mvs_result = await db.execute(featured_mvs_query)
    featured_mvs = featured_mvs_result.scalars().all()

    # Get music history (recently played tracks) grouped by genre
    history_query = (
        select(Track)
        .join(File, Track.file_id == File.id)
        .where(File.user_id == current_user.id)
        .options(selectinload(Track.artist))
        .order_by(desc(File.created_at))
        .limit(20)
    )
    history_result = await db.execute(history_query)
    history_tracks = history_result.scalars().all()

    return {
        "continue_watching": [add_urls_to_file(f) for f in continue_watching],
        "recent": [add_urls_to_file(f) for f in recent_files],
        "folders": [
            {
                "id": f.id,
                "name": f.name,
                "parent_id": f.parent_id,
                "file_count": None
            }
            for f in folders
        ],
        "featured_music_videos": [
            _track_to_resp(t) for t in featured_mvs
        ],
        "music_history_by_genre": _tracks_by_genre(history_tracks),
    }


def _track_to_resp(t: Track) -> dict:
    cover_url = None
    if t.album and t.album.cover_file_id:
        cover_url = f"/api/stream/cover/{t.album.cover_file_id}"
    return {
        "id": t.id,
        "title": t.title,
        "artist_id": t.artist_id,
        "artist": {"id": t.artist.id, "name": t.artist.name} if t.artist else None,
        "album_id": t.album_id,
        "file_id": t.file_id,
        "duration": t.duration,
        "genre": t.genre,
        "play_count": t.play_count,
        "like_count": t.like_count,
        "stream_url": f"/api/stream/{t.file_id}",
        "cover_url": cover_url,
        "media_type": t.media_type,
    }


def _tracks_by_genre(tracks: List[Track]) -> dict:
    """Group tracks by genre for TV browse."""
    genres = {}
    for t in tracks:
        g = t.genre or "Unknown"
        if g not in genres:
            genres[g] = []
        if len(genres[g]) < 8:
            genres[g].append(_track_to_resp(t))
    return genres


@router.get("/music/featured")
async def tv_music_featured(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get featured music videos for TV hero row."""
    query = (
        select(Track)
        .where(
            Track.media_type == "music_video",
            Track.play_count >= 10
        )
        .options(selectinload(Track.artist))
        .order_by(desc(Track.play_count))
        .limit(10)
    )
    result = await db.execute(query)
    tracks = result.scalars().all()
    return [_track_to_resp(t) for t in tracks]


@router.get("/music/history/by-genre")
async def tv_music_history_by_genre(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recently played tracks grouped by genre."""
    query = (
        select(Track)
        .join(File, Track.file_id == File.id)
        .where(File.user_id == current_user.id)
        .options(selectinload(Track.artist))
        .order_by(desc(File.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    tracks = result.scalars().all()
    return _tracks_by_genre(tracks)


@router.get("/continue")
async def tv_continue_watching(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get continue watching list for TV."""
    files = await fetch_continue_watching_files(db, current_user.id, limit)
    return [add_urls_to_file(f) for f in files]


@router.get("/recent")
async def tv_recent_files(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recently added files for TV."""
    files = await fetch_recent_files(db, current_user.id, limit)
    return [add_urls_to_file(f) for f in files]


@router.get("/search")
async def tv_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search files for TV client."""
    from sqlalchemy import or_ as sql_or

    # Search files by name
    files_query = (
        select(File)
        .where(
            File.user_id == current_user.id,
            File.file_name.ilike(f"%{escape_like(q)}%", escape="\\")
        )
        .options(selectinload(File.watch_progress))
        .order_by(desc(File.created_at))
        .limit(limit)
    )
    files_result = await db.execute(files_query)
    files = files_result.scalars().all()

    # Search folders by name
    folders_query = (
        select(Folder)
        .where(
            Folder.user_id == current_user.id,
            Folder.name.ilike(f"%{escape_like(q)}%", escape="\\")
        )
        .order_by(Folder.name)
        .limit(20)
    )
    folders_result = await db.execute(folders_query)
    folders = folders_result.scalars().all()

    # Search music tracks
    tracks_query = (
        select(Track)
        .where(
            Track.title.ilike(f"%{escape_like(q)}%", escape="\\")
        )
        .options(selectinload(Track.artist))
        .limit(limit)
    )
    tracks_result = await db.execute(tracks_query)
    tracks = tracks_result.scalars().all()

    return {
        "files": [add_urls_to_file(f) for f in files],
        "folders": [
            {
                "id": f.id,
                "name": f.name,
                "parent_id": f.parent_id
            }
            for f in folders
        ],
        "music": [_track_to_resp(t) for t in tracks],
    }


@router.get("/folder/{folder_id}")
async def tv_folder_detail(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get folder details with files and subfolders for TV client.
    Returns folder info, subfolders, files, and parent path for navigation.
    """
    from fastapi import HTTPException

    # Get the folder
    folder_result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == current_user.id)
    )
    folder = folder_result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Get subfolders
    subfolders_result = await db.execute(
        select(Folder)
        .where(Folder.user_id == current_user.id, Folder.parent_id == folder_id)
        .order_by(Folder.name)
    )
    subfolders = subfolders_result.scalars().all()

    # Get files in this folder
    files_result = await db.execute(
        select(File)
        .where(File.user_id == current_user.id, File.folder_id == folder_id)
        .options(selectinload(File.watch_progress))
        .order_by(File.file_name)
    )
    files = files_result.scalars().all()

    # Build parent path for breadcrumb navigation
    parent_path = []
    current_folder = folder
    while current_folder.parent_id:
        parent_result = await db.execute(
            select(Folder).where(Folder.id == current_folder.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if parent:
            parent_path.insert(0, {
                "id": parent.id,
                "name": parent.name,
                "parent_id": parent.parent_id,
                "user_id": parent.user_id,
                "created_at": parent.created_at.isoformat() if parent.created_at else None,
                "updated_at": parent.updated_at.isoformat() if parent.updated_at else None,
            })
            current_folder = parent
        else:
            break

    return {
        "folder": {
            "id": folder.id,
            "name": folder.name,
            "parent_id": folder.parent_id,
            "user_id": folder.user_id,
            "created_at": folder.created_at.isoformat() if folder.created_at else None,
            "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
        },
        "subfolders": [
            {
                "id": sf.id,
                "name": sf.name,
                "parent_id": sf.parent_id,
                "user_id": sf.user_id,
                "created_at": sf.created_at.isoformat() if sf.created_at else None,
                "updated_at": sf.updated_at.isoformat() if sf.updated_at else None,
            }
            for sf in subfolders
        ],
        "files": [add_urls_to_file(f) for f in files],
        "parent_path": parent_path
    }
