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
