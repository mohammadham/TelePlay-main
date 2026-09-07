"""
Admin APIs — Cache & Ads management (admin-only)
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import CacheConfig, Ad, AdConfig, User
from ..auth import require_admin
from .. import cache_manager
from ..services import escape_like

router = APIRouter(prefix="/admin", tags=["Admin"])

# ---- Cache ----
@router.get("/cache/config")
async def get_cache_config(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    row = (await db.execute(select(CacheConfig).limit(1))).scalar_one_or_none()
    if not row:
        row = CacheConfig(); db.add(row); await db.commit(); await db.refresh(row)
    return row

@router.put("/cache/config")
async def update_cache_config(payload: dict, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin), request: Request = None):
    from ..models import AuditLog
    ip = request.client.host if request and request.client else None
    db.add(AuditLog(user_id=admin.id, action="update_cache_config", target=str(payload.get("strategy")), ip_address=ip))
    await db.commit()
    row = (await db.execute(select(CacheConfig).limit(1))).scalar_one_or_none()
    if not row:
        row = CacheConfig(); db.add(row)
    for k in ["max_size_mb","max_file_size_mb","strategy","ttl_seconds","enabled"]:
        if k in payload: setattr(row, k, payload[k])
    await db.commit(); await db.refresh(row)
    return row

@router.get("/cache/stats")
async def cache_stats(admin: User=Depends(require_admin)):
    s = await cache_manager.get_stats()
    # add DB config
    return s

@router.post("/cache/purge")
async def cache_purge(payload: dict, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin), request: Request = None):
    from ..models import AuditLog
    scope = payload.get("scope","all")
    tid = payload.get("track_id")
    ip = request.client.host if request and request.client else None
    db.add(AuditLog(user_id=admin.id, action="purge_cache", target=f"scope={scope} track_id={tid}", ip_address=ip))
    await db.commit()
    n = await cache_manager.purge(scope, tid)
    return {"purged": n}

@router.post("/cache/warmup")
async def cache_warmup(payload: dict, admin: User=Depends(require_admin)):
    # placeholder — would fetch and cache chunks
    return {"queued": len(payload.get("track_ids", []))}

# ---- Ads ----
@router.get("/ads/config")
async def get_ad_config(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    row = (await db.execute(select(AdConfig).limit(1))).scalar_one_or_none()
    if not row:
        row = AdConfig(); db.add(row); await db.commit(); await db.refresh(row)
    return row

@router.put("/ads/config")
async def update_ad_config(payload: dict, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    row = (await db.execute(select(AdConfig).limit(1))).scalar_one_or_none()
    if not row:
        row = AdConfig(); db.add(row)
    for k in ["enabled","every_n_tracks","max_per_hour"]:
        if k in payload: setattr(row, k, payload[k])
    await db.commit(); await db.refresh(row)
    return row

@router.get("/ads/stats")
async def ads_stats(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    from sqlalchemy import func
    from ..models import AdImpression
    total = (await db.execute(select(func.count()).select_from(AdImpression))).scalar() or 0
    return {"total_impressions": total}

@router.get("/ads")
async def list_ads(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    rows = (await db.execute(select(Ad).order_by(Ad.created_at.desc()))).scalars().all()
    return rows

@router.post("/ads")
async def create_ad(payload: dict, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    ad = Ad(title=payload["title"], audio_file_id=payload.get("audio_file_id"), duration=payload.get("duration",15), target_genre=payload.get("target_genre"), weight=payload.get("weight",1), enabled=payload.get("enabled", True))
    db.add(ad); await db.commit(); await db.refresh(ad)
    return ad

@router.put("/ads/{ad_id}")
async def update_ad(ad_id: int, payload: dict, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    ad = (await db.execute(select(Ad).where(Ad.id==ad_id))).scalar_one_or_none()
    if not ad: from fastapi import HTTPException; raise HTTPException(404, "Ad not found")
    for k in ["title","duration","target_genre","weight","enabled"]:
        if k in payload: setattr(ad, k, payload[k])
    await db.commit(); await db.refresh(ad)
    return ad

@router.delete("/ads/{ad_id}")
async def delete_ad(ad_id: int, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    from sqlalchemy import delete as sql_del
    await db.execute(sql_del(Ad).where(Ad.id==ad_id)); await db.commit()
    return {"ok": True}

# ---- Overview & System ----
import time, platform, sys
_start_time = time.time()

@router.get("/stats")
async def admin_stats(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    from sqlalchemy import func
    from ..models import User as U, File, Track, Ad, CacheConfig
    import asyncio

    async def _count(query):
        return (await db.execute(query)).scalar() or 0

    results, cache = await asyncio.gather(
        asyncio.gather(
            _count(select(func.count()).select_from(U)),
            _count(select(func.count()).select_from(File)),
            _count(select(func.count()).select_from(File).where(File.file_type == "audio")),
            _count(select(func.count()).select_from(File).where(File.file_type == "video")),
            _count(select(func.count()).select_from(Track)),
            _count(select(func.count()).select_from(Track).where(Track.media_type == "audio")),
            _count(select(func.count()).select_from(Track).where(Track.media_type == "music_video")),
            _count(select(func.count()).select_from(Track).where(Track.media_type == "reel")),
            _count(select(func.count()).select_from(Ad)),
            _count(select(func.coalesce(func.sum(File.file_size), 0)).select_from(File)),
        ),
        cache_manager.get_stats(),
    )
    users, files, fa, fv, tracks, ta, tmv, treel, ads, storage_bytes = results
    results = {
        "users": users, "files": files,
        "files_audio": fa, "files_video": fv,
        "tracks": tracks, "tracks_audio": ta,
        "tracks_music_video": tmv, "tracks_reel": treel,
        "ads": ads, "storage_bytes": storage_bytes,
    }
    uptime = int(time.time() - _start_time)
    return {
        **results,
        "cache": cache,
        "uptime_seconds": uptime,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }

@router.get("/users")
async def list_users(q: str = None, page: int = 1, per_page: int = 20, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    from sqlalchemy import or_, func
    from ..models import User as U
    query = select(U)
    if q: query = query.where(or_(U.username.ilike(f"%{escape_like(q)}%", escape="\\"), U.first_name.ilike(f"%{escape_like(q)}%", escape="\\")))
    query = query.order_by(U.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    rows = (await db.execute(query)).scalars().all()
    total = (await db.execute(select(func.count()).select_from(U))).scalar() or 0
    return {"users": [{"id": u.id, "telegram_id": u.telegram_id, "username": u.username, "first_name": u.first_name, "created_at": u.created_at} for u in rows], "total": total}

@router.get("/files")
async def list_files_admin(file_type: str = None, q: str = None, page: int = 1, per_page: int = 20, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    from sqlalchemy import or_, func
    from ..models import File
    query = select(File)
    if file_type: query = query.where(File.file_type==file_type)
    if q: query = query.where(File.file_name.ilike(f"%{escape_like(q)}%", escape="\\"))
    query = query.order_by(File.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    rows = (await db.execute(query)).scalars().all()
    total = (await db.execute(select(func.count()).select_from(File))).scalar() or 0
    return {"files": [{"id": f.id, "file_name": f.file_name, "file_type": f.file_type, "file_size": f.file_size, "created_at": f.created_at} for f in rows], "total": total}

@router.get("/system")
async def system_info(admin: User=Depends(require_admin)):
    import shutil
    disk = shutil.disk_usage("/")
    return {
        "disk_total": disk.total, "disk_used": disk.used, "disk_free": disk.free,
        "uptime_seconds": int(time.time() - _start_time),
        "python": sys.version, "platform": platform.platform()
    }

# ---- User Detail (admin test/view) ----
@router.get("/users/{telegram_id}")
async def get_user_detail(telegram_id: int, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    from sqlalchemy import func, select as sa_select
    from ..models import File, Folder, Like, ListenHistory, DownloadQueue, Playlist, WatchProgress, Track
    from fastapi import HTTPException

    u = (await db.execute(sa_select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")

    files_cnt = (await db.execute(sa_select(func.count()).where(File.user_id == u.id))).scalar() or 0
    folders_cnt = (await db.execute(sa_select(func.count()).where(Folder.user_id == u.id))).scalar() or 0
    liked_cnt = (await db.execute(sa_select(func.count()).where(Like.user_id == u.id))).scalar() or 0
    history_cnt = (await db.execute(sa_select(func.count()).where(ListenHistory.user_id == u.id))).scalar() or 0
    dl_cnt = (await db.execute(sa_select(func.count()).where(DownloadQueue.user_id == u.id))).scalar() or 0
    pl_cnt = (await db.execute(sa_select(func.count()).where(Playlist.user_id == u.id))).scalar() or 0
    progress_cnt = (await db.execute(sa_select(func.count()).where(WatchProgress.user_id == u.id))).scalar() or 0
    storage_bytes = (await db.execute(sa_select(func.sum(File.file_size)).where(File.user_id == u.id))).scalar() or 0

    # Recent files
    rf = (await db.execute(sa_select(File).where(File.user_id == u.id).order_by(File.created_at.desc()).limit(5))).scalars().all()
    recent_files = [{"id": f.id, "file_name": f.file_name, "file_type": f.file_type, "file_size": f.file_size, "created_at": str(f.created_at)} for f in rf]

    # Recent plays
    rp = (await db.execute(
        sa_select(ListenHistory, Track).join(Track, Track.id == ListenHistory.track_id)
        .where(ListenHistory.user_id == u.id).order_by(ListenHistory.played_at.desc()).limit(10)
    )).fetchall()
    recent_plays = [{"track_title": r[1].title, "played_at": str(r[0].played_at)} for r in rp] if rp else []

    # Recent downloads
    rd = (await db.execute(
        sa_select(DownloadQueue, Track).join(Track, Track.id == DownloadQueue.track_id)
        .where(DownloadQueue.user_id == u.id).order_by(DownloadQueue.created_at.desc()).limit(5)
    )).fetchall()
    recent_downloads = [{"track_title": r[1].title, "status": r[0].status, "progress": r[0].progress, "created_at": str(r[0].created_at)} for r in rd] if rd else []

    return {
        "user": {
            "id": u.id, "telegram_id": u.telegram_id,
            "username": u.username, "first_name": u.first_name, "last_name": u.last_name,
            "created_at": str(u.created_at), "last_active": str(u.last_active),
        },
        "stats": {
            "files_count": files_cnt, "folders_count": folders_cnt,
            "liked_tracks": liked_cnt, "history_count": history_cnt,
            "downloads_count": dl_cnt, "playlists_count": pl_cnt,
            "watch_progress_count": progress_cnt,
            "storage_bytes": storage_bytes,
            "storage_mb": round(storage_bytes / 1024 / 1024, 2),
        },
        "recent_files": recent_files,
        "recent_plays": recent_plays,
        "recent_downloads": recent_downloads,
    }
