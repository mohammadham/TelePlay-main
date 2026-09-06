"""
FastAPI main application with Telegram MTProto client lifecycle.
"""
import gzip
import io
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

logging.getLogger("pyrogram").setLevel(logging.INFO)

from .config import get_settings, mark_db_ready
from .database import init_db, get_db
from .telegram import start_telegram_client, stop_telegram_client
from .routers import files_router, folders_router, streaming_router, auth_router, tv_router, music_router, admin_router, ads_router
from .routers.settings import router as settings_router
from .routers.setup import router as setup_router
from .routers.admin_bots import router as admin_bots_router
from .routers.admin_accounts import router as admin_accounts_router
from .routers.admin_admins import router as admin_admins_router

try:
    settings = get_settings()
except Exception as _e:
    # Don't crash at import — let /health show error, lifespan will log details
    import logging as _logging
    _logging.getLogger(__name__).error(f"Settings not loaded at import (will retry at startup): {_e}")
    class _DummySettings:
        web_base_url = "http://localhost:3000"
    settings = _DummySettings()  # type: ignore

# Rate limiter - uses IP address by default
limiter = Limiter(key_func=get_remote_address)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - start/stop Telegram client and init DB."""
    logger.info("Starting TelePlay Backend...")
    # Validate config early with friendly message
    try:
        from .config import get_settings as _get_settings
        _get_settings()
    except Exception as e:
        logger.error(f"CONFIG ERROR — missing ENV vars (see above). Set in Railway Variables: {e}")
        raise
    await init_db()
    logger.info("Database initialized")
    
    # Run migration from legacy settings
    from .migration import migrate_existing_settings, ensure_default_bot_config
    from .database import get_sessionmaker
    session_maker = get_sessionmaker()
    async with session_maker() as db:
        await migrate_existing_settings(db)
        await ensure_default_bot_config(db)
    
    await mark_db_ready(settings)
    logger.info("DB settings applied")
    await start_telegram_client()
    logger.info("Telegram client started")
    
    # Load user accounts into pool
    from .pool_manager import load_user_accounts
    await load_user_accounts()
    
    yield
    
    logger.info("Shutting down...")
    await stop_telegram_client()
    logger.info("Telegram client stopped")


app = FastAPI(
    title="TelePlay API",
    description="Stream files from Telegram to Android TV and Web",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware — restrict to configured origin + dev localhost
allowed_origins = [settings.web_base_url] if settings.web_base_url and settings.web_base_url not in ("", "http://localhost:3000") else []
allowed_origins += ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]
# Remove duplicates while preserving order
allowed_origins = list(dict.fromkeys(allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Range"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "ETag"],
)

# Custom gzip compression middleware (replaces removed fastapi-compression package)
async def gzip_compression_middleware(request: Request, call_next):
    """Compress response with gzip when client accepts it and body exceeds threshold."""
    response = await call_next(request)
    accept_encoding: Optional[str] = request.headers.get("accept-encoding", "")
    if "gzip" not in accept_encoding.lower():
        return response
    if response.status_code < 200 or response.status_code >= 300:
        return response
    body = b""
    async for chunk in response.body_iterator:
        body += chunk
    if len(body) < 1000:
        return response.__class__(content=body, headers=response.headers, status_code=response.status_code)
    compressed = gzip.compress(body)
    response.body_iterator.close()
    return response.__class__(
        content=io.BytesIO(compressed),
        headers={**response.headers, "content-encoding": "gzip", "content-length": str(len(compressed))},
        status_code=response.status_code,
    )

app.add_middleware(gzip_compression_middleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:;"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(folders_router, prefix="/api")
app.include_router(streaming_router, prefix="/api")
app.include_router(tv_router, prefix="/api")
app.include_router(music_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(ads_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(setup_router, prefix="/api")
app.include_router(admin_bots_router, prefix="/api")
app.include_router(admin_accounts_router, prefix="/api")
app.include_router(admin_admins_router, prefix="/api")


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Health check — verifies DB connectivity."""
    status = {"status": "healthy", "db": "connected"}
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        status["db"] = f"error: {e}"
        status["status"] = "degraded"
    return status


# Mount static files (assets)
if os.path.exists("app/static/assets"):
    app.mount("/assets", StaticFiles(directory="app/static/assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the React SPA for any non-API routes."""
    if full_path == "api" or full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API Endpoint not found")

    static_file_path = f"app/static/{full_path}"
    if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
        return FileResponse(static_file_path)

    if os.path.exists("app/static/index.html"):
        return FileResponse("app/static/index.html")

    return {"message": "Backend running. Frontend not built/mounted (dev mode)."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True
    )
