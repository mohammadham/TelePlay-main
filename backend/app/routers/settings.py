"""
Admin Settings API — template env vars editable via panel
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import AppSetting, User
from ..auth import require_admin
from ..config import get_settings, mark_db_ready

router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])

# Template defaults shown when DB empty
TEMPLATE = {
    "TELEGRAM_API_ID": ("", "From my.telegram.org"),
    "TELEGRAM_API_HASH": ("", "From my.telegram.org"),
    "TELEGRAM_BOT_TOKEN": ("", "From @BotFather"),
    "TELEGRAM_STORAGE_CHANNEL_ID": ("", "Private channel -100..."),
    "JWT_SECRET": ("", "openssl rand -hex 32"),
    "ADMIN_TELEGRAM_IDS": ("", "Comma-separated admin IDs"),
    "WEB_BASE_URL": ("", "https://your-domain.com"),
    "CACHE_ENABLED": ("true", "true/false"),
    "VIDEO_CACHE_ENABLED": ("true", "true/false"),
    "ADS_ENABLED": ("true", "true/false"),
}

@router.get("")
async def list_settings(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    rows = (await db.execute(select(AppSetting))).scalars().all()
    db_map = {r.key: r.value for r in rows}
    # merge template + db
    out = []
    for k, (default, desc) in TEMPLATE.items():
        out.append({"key": k, "value": db_map.get(k, default), "description": desc, "is_set": k in db_map})
    # extra keys in DB not in template
    for r in rows:
        if r.key not in TEMPLATE:
            out.append({"key": r.key, "value": r.value, "description": r.description or "", "is_set": True})
    return out

@router.put("")
async def update_settings(payload: dict, db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    # payload: {key: value} or {settings: [{key,value}]}
    items = payload.get("settings") if "settings" in payload else payload
    if isinstance(items, dict):
        items = [{"key": k, "value": v} for k, v in items.items()]
    for item in items:
        k = item["key"]; v = str(item.get("value",""))
        row = (await db.execute(select(AppSetting).where(AppSetting.key==k))).scalar_one_or_none()
        if row:
            row.value = v
        else:
            row = AppSetting(key=k, value=v, description=TEMPLATE.get(k, ("",""))[1])
            db.add(row)
    await db.commit()
    # Reload settings in memory
    mark_db_ready(get_settings())
    return {"ok": True, "message": "Settings saved and applied"}

@router.get("/export")
async def export_env(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    # returns .env template text
    rows = (await db.execute(select(AppSetting))).scalars().all()
    db_map = {r.key: r.value for r in rows}
    lines = []
    for k, (default, desc) in TEMPLATE.items():
        val = db_map.get(k, default)
        lines.append(f"# {desc}")
        lines.append(f"{k}={val}")
        lines.append("")
    return {"env": "\n".join(lines)}

@router.post("/seed")
async def seed_template(db: AsyncSession=Depends(get_db), admin: User=Depends(require_admin)):
    for k, (default, desc) in TEMPLATE.items():
        exists = (await db.execute(select(AppSetting).where(AppSetting.key==k))).scalar_one_or_none()
        if not exists:
            db.add(AppSetting(key=k, value=default, description=desc))
    await db.commit()
    return {"ok": True}

@router.post("/reload")
async def reload_settings(admin: User=Depends(require_admin)):
    """Reload settings from DB without redeploy."""
    mark_db_ready(get_settings())
    return {"ok": True, "message": "Settings reloaded from database"}

@router.post("/reload")
async def reload_settings(admin: User=Depends(require_admin)):
    """Reload settings from DB without redeploy."""
    mark_db_ready(get_settings())
    return {"ok": True, "message": "Settings reloaded from database"}
