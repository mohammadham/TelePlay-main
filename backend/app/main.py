"""
FastAPI main application with Telegram MTProto client lifecycle.
"""
import logging
from contextlib import asynccontextmanager

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
from .telegram import stop_telegram_client
from .encryption import ensure_encryption_key
from .routers import files_router, folders_router, streaming_router, auth_router, tv_router, music_router, admin_router, ads_router
from .routers.settings import router as settings_router
from .routers.setup import router as setup_router
from .routers.admin_bots import router as admin_bots_router
from .routers.admin_accounts import router as admin_accounts_router
from .routers.admin_admins import router as admin_admins_router
from .routers.telegram_status import router as telegram_status_router

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

    # Load DB settings FIRST (including JWT_SECRET) so encryption key can be derived
    await mark_db_ready(settings)
    logger.info("DB settings applied")

    # Now derive encryption key from the (possibly DB-loaded) JWT_SECRET
    await ensure_encryption_key()
    logger.info("Encryption key ensured")

    # Run migration from legacy settings
    from .migration import migrate_existing_settings, ensure_default_bot_config
    from .database import get_sessionmaker
    session_maker = get_sessionmaker()
    async with session_maker() as db:
        await migrate_existing_settings(db)
        await ensure_default_bot_config(db)

    # Skip telegram client startup if credentials are not yet configured
    # (setup wizard has not run yet, or env vars are template values)
    from .config import is_configured
    if not await is_configured(settings):
        logger.info("Not configured yet — skipping Telegram client startup (setup wizard pending)")
    else:
        # Retry Telegram client startup with delays — Telegram servers may be slow to respond
        from .telegram import start_telegram_client as _start_tc, clients as _clients
        import asyncio as _asyncio
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await _start_tc()
                connected = any(c.is_connected for c in _clients) if _clients else False
                logger.info("Telegram client started (attempt %d/%d, connected=%s)", attempt, max_retries, connected)
                break
            except Exception as e:
                logger.warning("Telegram client startup attempt %d/%d failed: %s", attempt, max_retries, e)
                if attempt < max_retries:
                    wait = 2 ** (attempt - 1)  # 1s, 2s, 4s
                    logger.info("Retrying in %ds...", wait)
                    await _asyncio.sleep(wait)
                else:
                    logger.error("All %d Telegram startup attempts failed. Bot will remain unavailable until restart or manual /api/telegram/start.", max_retries)
        logger.info("Telegram client started")

    # Load user accounts into pool — auto-reset on decryption failure
    from .pool_manager import load_user_accounts
    await load_user_accounts()

    # Check if DB data is readable; log clear warning if decryption fails
    from .encryption import decrypt as _dec
    from sqlalchemy import select as _sel
    from .database import async_session
    async with async_session() as _db:
        from .models import UserAccount, BotConfig
        acc_rows = (await _db.execute(_sel(UserAccount))).scalars().all()
        bot_rows = (await _db.execute(_sel(BotConfig))).scalars().all()
        dec_errors = 0
        for a in acc_rows:
            if not _dec(a.session_string_encrypted):
                dec_errors += 1
        for b in bot_rows:
            if not _dec(b.token_encrypted):
                dec_errors += 1
        if dec_errors > 0:
            logger.error(
                "Decryption key mismatch — %d credential(s) unreadable. "
                "This usually means JWT_SECRET changed. "
                "Either restore the original JWT_SECRET or run setup wizard again.",
                dec_errors
            )

    # Background task: periodically verify Telegram bot health and auto-restart on disconnect
    from .telegram import start_telegram_client as _bg_start, stop_all_clients as _bg_stop, clients as _bg_clients

    async def _telegram_health_loop():
        import asyncio
        while True:
            await asyncio.sleep(300)  # check every 5 minutes
            try:
                configured = await is_configured(settings)
                if not configured:
                    continue
                disconnected = any(
                    not c.is_connected for c in _bg_clients
                ) if _bg_clients else False
                if disconnected:
                    logger.warning("Telegram client(s) disconnected — auto-restarting...")
                    await _bg_stop()
                    await _asyncio.sleep(2)
                    await _bg_start()
                    connected_after = any(
                        c.is_connected for c in _bg_clients
                    ) if _bg_clients else False
                    logger.info(
                        "Auto-restart complete — connected: %s", connected_after
                    )
            except Exception as e:
                logger.warning("Telegram health check error (non-fatal): %s", e)

    import asyncio as _asyncio
    health_task = _asyncio.create_task(_telegram_health_loop())

    yield

    logger.info("Shutting down...")
    health_task.cancel()
    try:
        await health_task
    except _asyncio.CancelledError:
        pass
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
app.include_router(telegram_status_router, prefix="/api")


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
