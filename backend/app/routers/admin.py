"""
Admin APIs — Cache & Ads management (admin-only)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import CacheConfig, Ad, AdConfig, User
from ..auth import require_admin
from .. import cache_manager

router = APIRouter(prefix="/admin", tags=["Admin"])

# ---- Cache ----
@router.get("/cache/config")
async def get_cache_config(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    row = (await db.execute(select(CacheConfig).limit(1))).scalar_one_or_none()
    if not row:
        row = CacheConfig(); db.add(row); await db.commit(); await db.refresh(row)
    return row

@router.put("/cache/config")
async def update_cache_config(payload: dict, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
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
async def cache_purge(payload: dict, admin: User=Depends(require_admin)):
    scope = payload.get("scope","all")
    tid = payload.get("track_id")
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
    from ..models import User as U, File, Track, Movie, Ad, CacheConfig
    # counts
    users = (await db.execute(select(func.count()).select_from(U))).scalar() or 0
    files = (await db.execute(select(func.count()).select_from(File))).scalar() or 0
    files_audio = (await db.execute(select(func.count()).select_from(File).where(File.file_type=="audio"))).scalar() or 0
    files_video = (await db.execute(select(func.count()).select_from(File).where(File.file_type=="video"))).scalar() or 0
    tracks = (await db.execute(select(func.count()).select_from(Track))).scalar() or 0
    movies = (await db.execute(select(func.count()).select_from(Movie))).scalar() or 0
    ads = (await db.execute(select(func.count()).select_from(Ad))).scalar() or 0
    cache = await cache_manager.get_stats()
    # storage sum
    storage = (await db.execute(select(func.coalesce(func.sum(File.file_size), 0)).select_from(File))).scalar() or 0
    uptime = int(time.time() - _start_time)
    return {
        "users": users, "files": files, "files_audio": files_audio, "files_video": files_video,
        "tracks": tracks, "movies": movies, "ads": ads, "storage_bytes": storage,
        "cache": cache, "uptime_seconds": uptime, "python": platform.python_version(), "platform": platform.platform()
    }

@router.get("/users")
async def list_users(q: str = None, page: int = 1, per_page: int = 20, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    from sqlalchemy import or_, func
    from ..models import User as U
    query = select(U)
    if q: query = query.where(or_(U.username.ilike(f"%{q}%"), U.first_name.ilike(f"%{q}%")))
    query = query.order_by(U.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    rows = (await db.execute(query)).scalars().all()
    total = (await db.execute(select(func.count()).select_from(U))).scalar() or 0
    return {"users": [{"id": u.id, "telegram_id": u.telegram_id, "username": u.username, "first_name": u.first_name, "created_at": u.created_at} for u in rows], "total": total}

@router.get("/files")
async def list_files_admin(file_type: str = None, q: str = None, page: int = 1, per_page: int = 20, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    from sqlalchemy import or_
    from ..models import File
    query = select(File)
    if file_type: query = query.where(File.file_type==file_type)
    if q: query = query.where(File.file_name.ilike(f"%{q}%"))
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
