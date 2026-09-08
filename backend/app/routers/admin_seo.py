"""
Admin SEO & Geo Configuration API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import SEOConfig, User
from ..auth import require_admin

router = APIRouter(prefix="/admin/seo", tags=["Admin SEO"])


@router.get("/config")
async def get_seo_config(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    row = (await db.execute(select(SEOConfig).limit(1))).scalar_one_or_none()
    if not row:
        row = SEOConfig()
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return {
        "id": row.id,
        "title_template": row.title_template,
        "description_template": row.description_template,
        "keywords": row.keywords,
        "geo_region": row.geo_region,
        "geo_locale": row.geo_locale,
        "social_image": row.social_image,
    }


@router.put("/config")
async def update_seo_config(payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    row = (await db.execute(select(SEOConfig).limit(1))).scalar_one_or_none()
    if not row:
        row = SEOConfig()
        db.add(row)
    for key in ["title_template", "description_template", "keywords", "geo_region", "geo_locale", "social_image"]:
        if key in payload and payload[key] is not None:
            setattr(row, key, str(payload[key]))
    await db.commit()
    await db.refresh(row)
    return {
        "id": row.id,
        "title_template": row.title_template,
        "description_template": row.description_template,
        "keywords": row.keywords,
        "geo_region": row.geo_region,
        "geo_locale": row.geo_locale,
        "social_image": row.social_image,
    }


@router.post("/seed")
async def seed_seo_config(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    exists = (await db.execute(select(SEOConfig).limit(1))).scalar_one_or_none()
    if not exists:
        db.add(SEOConfig())
        await db.commit()
    return {"ok": True}
