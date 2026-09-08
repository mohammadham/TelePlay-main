"""
Admin SEO & Geo Configuration API
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, XMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_db
from ..models import SEOConfig, User, Track, Artist, Album
from ..auth import require_admin

logger = logging.getLogger(__name__)

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
        "ai_agent_description": row.ai_agent_description or "",
        "geo_region": row.geo_region,
        "geo_locale": row.geo_locale,
        "social_image": row.social_image,
        "geo_list": row.geo_list,
    }


@router.put("/config")
async def update_seo_config(payload: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    row = (await db.execute(select(SEOConfig).limit(1))).scalar_one_or_none()
    if not row:
        row = SEOConfig()
        db.add(row)
    for key in ["title_template", "description_template", "keywords", "ai_agent_description", "geo_region", "geo_locale", "social_image", "geo_list"]:
        if key in payload and payload[key] is not None:
            setattr(row, key, str(payload[key]))
    await db.commit()
    await db.refresh(row)
    return {
        "id": row.id,
        "title_template": row.title_template,
        "description_template": row.description_template,
        "keywords": row.keywords,
        "ai_agent_description": row.ai_agent_description or "",
        "geo_region": row.geo_region,
        "geo_locale": row.geo_locale,
        "social_image": row.social_image,
        "geo_list": row.geo_list,
    }


@router.post("/seed")
async def seed_seo_config(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    exists = (await db.execute(select(SEOConfig).limit(1))).scalar_one_or_none()
    if not exists:
        db.add(SEOConfig())
        await db.commit()
    return {"ok": True}


@router.get("/robots.txt", response_class=PlainTextResponse)
async def get_robots(db: AsyncSession = Depends(get_db)):
    """Generate robots.txt from SEO config."""
    row = (await db.execute(select(SEOConfig).limit(1))).scalar_one_or_none()
    config = row or SEOConfig()

    geo_list = []
    if config.geo_list:
        try:
            geo_list = json.loads(config.geo_list)
        except Exception:
            pass

    lines = ["User-agent: *"]

    if geo_list and len(geo_list) > 0:
        lines.append("Disallow: /")
    else:
        lines.append("Allow: /music/")
        lines.append("Allow: /api/")
        lines.append("Disallow: /admin/")
        lines.append("Disallow: /login/")
        lines.append("Disallow: /setup/")
        lines.append("Disallow: /auth/")

    from ..config import get_settings
    try:
        settings = get_settings()
        base_url = settings.web_base_url.rstrip("/")
    except Exception:
        base_url = "https://teleplay-main-production.up.railway.app"

    lines.append("")
    lines.append(f"Sitemap: {base_url}/admin/seo/sitemap.xml")
    lines.append("")
    return "\n".join(lines)


@router.get("/sitemap.xml")
async def get_sitemap(db: AsyncSession = Depends(get_db)):
    """Generate sitemap.xml with page priorities."""
    from ..config import get_settings
    try:
        settings = get_settings()
        base_url = settings.web_base_url.rstrip("/")
    except Exception:
        base_url = "https://teleplay-main-production.up.railway.app"

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Static high-priority pages
    pages = [
        (f"{base_url}/music",       "daily", 1.0),
        (f"{base_url}/music/search","weekly", 0.9),
        (f"{base_url}/music/playlists","weekly", 0.7),
        (f"{base_url}/music/downloads","weekly", 0.5),
        (f"{base_url}/music/history","weekly", 0.5),
    ]

    # Dynamic artist pages (existing route: /music/artists/:id)
    result = await db.execute(
        select(Artist).order_by(Artist.id).limit(50)
    )
    for a in result.scalars().all():
        pages.append((f"{base_url}/music/artists/{a.id}", "weekly", 0.7))

    # Featured tracks via artist pages (no /music/tracks/:id route exists)
    # Priority goes to artists with tracks

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url, freq, priority in pages:
        xml_lines.append(f'  <url>')
        xml_lines.append(f'    <loc>{url}</loc>')
        xml_lines.append(f'    <lastmod>{now_str}</lastmod>')
        xml_lines.append(f'    <changefreq>{freq}</changefreq>')
        xml_lines.append(f'    <priority>{priority}</priority>')
        xml_lines.append(f'  </url>')
    xml_lines.append('</urlset>')

    return XMLResponse("\n".join(xml_lines), media_type="application/xml")


@router.get("/ai-docs")
async def get_ai_docs(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Return structured site documentation for AI agents."""
    row = (await db.execute(select(SEOConfig).limit(1))).scalar_one_or_none()
    config = row or SEOConfig()

    stats_result = await db.execute(
        select(
            func.count(Track.id).label("total_tracks"),
            func.count(Artist.id).label("total_artists"),
            func.count(Album.id).label("total_albums"),
            func.count(User.id).label("total_users"),
        )
    )
    stats = stats_result.one()

    return {
        "site_name": "TelePlay",
        "purpose": "Stream and manage media files from Telegram to web and TV clients.",
        "ai_agent_description": config.ai_agent_description or "TelePlay is a media streaming platform that allows users to stream audio, video, and reels from Telegram file storage.",
        "features": [
            "Music streaming (audio, music_video, reel)",
            "Playlist management",
            "Track search and filtering",
            "Listen history tracking",
            "Download queue system",
            "Like/follow social features",
        ],
        "api_endpoints": {
            "music": "/api/v1/music/*",
            "tracks": "/api/v1/music/tracks",
            "artists": "/api/v1/music/artists",
            "albums": "/api/v1/music/albums",
            "search": "/api/v1/music/search?q=<query>",
            "history": "/api/v1/music/history",
            "playlists": "/api/v1/music/playlists",
        },
        "data_models": {
            "Track": {"id": "int", "title": "string", "artist_id": "int", "file_id": "int", "media_type": "audio|music_video|reel"},
            "Artist": {"id": "int", "name": "string", "bio": "string|null", "verified": "bool"},
            "Album": {"id": "int", "title": "string", "artist_id": "int"},
        },
        "stats": {
            "total_tracks": stats.total_tracks or 0,
            "total_artists": stats.total_artists or 0,
            "total_albums": stats.total_albums or 0,
            "total_users": stats.total_users or 0,
        },
        "geo_config": {
            "region": config.geo_region,
            "locale": config.geo_locale,
        },
    }
