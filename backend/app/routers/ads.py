"""
Public Ads API — next ad selection + impression logging
"""
import time
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from ..database import get_db
from ..models import Ad, AdConfig, AdImpression, User
from ..auth import get_current_user

router = APIRouter(prefix="/ads", tags=["Ads"])

# simple in-memory hourly counter per user
_hour_counters: dict[int, list[float]] = {}

def _can_serve(user_id: int, cfg: AdConfig) -> bool:
    if not cfg.enabled: return False
    now = time.time()
    lst = _hour_counters.get(user_id, [])
    lst = [t for t in lst if now - t < 3600]
    _hour_counters[user_id] = lst
    return len(lst) < cfg.max_per_hour

@router.get("/next")
async def next_ad(track_id: int = Query(None), play_count: int = Query(0), db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    cfg = (await db.execute(select(AdConfig).limit(1))).scalar_one_or_none()
    if not cfg: return {"ad": None}
    if not _can_serve(current_user.id, cfg): return {"ad": None}
    if play_count >0 and play_count % cfg.every_n_tracks != 0:
        return {"ad": None}
    # pick enabled ad (weighted random simple: order by weight desc)
    ad = (await db.execute(select(Ad).where(Ad.enabled==True).order_by(Ad.weight.desc()).limit(1))).scalar_one_or_none()
    if not ad: return {"ad": None}
    audio_url = f"/api/stream/{ad.audio_file_id}" if ad.audio_file_id else None
    return {"ad": {"id": ad.id, "title": ad.title, "duration": ad.duration, "enabled": ad.enabled}, "audio_url": audio_url, "skip_after": 5}

@router.post("/impression")
async def log_impression(payload: dict, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    ad_id = payload.get("ad_id")
    if not ad_id: return {"ok": False}
    imp = AdImpression(user_id=current_user.id, track_id=payload.get("track_id"), ad_id=ad_id)
    db.add(imp); await db.commit()
    # update hourly counter
    _hour_counters.setdefault(current_user.id, []).append(time.time())
    return {"ok": True}
