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
from .routers.admin_seo import router as admin_seo_router

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

    # Import config functions we need
    from .config import (
        validate_startup_config,
        check_decryption_health,
        mark_db_ready,
        is_configured,
        _startup_attempts,
    )
    import time

    # Container for mutable startup state — avoids closure/global issues
    _startup_state = {
        "first_attempt": None,
        "lock_until": None,
    }

    # Load DB settings FIRST (including JWT_SECRET) so encryption key can be derived
    db_ready = await mark_db_ready(settings)
    if db_ready:
        logger.info("DB settings applied")
    else:
        logger.info("No valid DB configuration found")

    # Now derive encryption key from the (possibly DB-loaded) JWT_SECRET
    await ensure_encryption_key()
    logger.info("Encryption key ensured")

    # Run migration from legacy settings
    from .migration import migrate_existing_settings, ensure_default_bot_config, migrate_seo_config_geo_list, migrate_seo_config_ai_description
    from .database import async_session
    async with async_session() as db:
        await migrate_existing_settings(db)
        await ensure_default_bot_config(db)
        await migrate_seo_config_geo_list(db)
        await migrate_seo_config_ai_description(db)

    # Validate startup configuration
    is_valid, missing_fields = await validate_startup_config(settings)
    decryption_ok, dec_error_count = await check_decryption_health()

    logger.info(f"Startup validation - Valid: {is_valid}, Missing: {missing_fields}, Decryption OK: {decryption_ok} (errors: {dec_error_count})")

    # Handle startup attempt rate limiting
    current_time = time.time()
    startup_key = "telegram_startup"
    _state = _startup_state

    # Initialize attempt tracking if needed
    if startup_key not in _startup_attempts:
        _startup_attempts[startup_key] = 0
        _state["first_attempt"] = current_time
        _state["lock_until"] = None

    # Check if we're in a lockout period
    if _state["lock_until"] and current_time < _state["lock_until"]:
        remaining = int(_state["lock_until"] - current_time)
        logger.info(f"Telegram startup locked out for {remaining}s due to previous failures")
        # Skip startup but keep health check running
        pass
    else:
        # Reset lockout if we've had a successful attempt recently
        if is_valid and decryption_ok:
            _startup_attempts[startup_key] = 0
            _state["first_attempt"] = None
            _state["lock_until"] = None
            logger.info("Startup validation passed - resetting attempt counter")

    # Start Telegram client if configured and healthy
    if is_valid and decryption_ok:
        # Skip telegram client startup if credentials are not yet configured
        # (setup wizard has not run yet, or env vars are template values)
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
                        # Increment failure counter for lockout
                        _startup_attempts[startup_key] += 1
                        attempt_count = _startup_attempts[startup_key]
                        if attempt_count >= 3:
                            # Lock out for 30 minutes after 3 failures
                            lockout_duration = 30 * 60  # 30 minutes in seconds
                            _state["lock_until"] = current_time + lockout_duration
                            logger.warning(f"Telegram startup locked out for {lockout_duration}s after {attempt_count} consecutive failures")
                        else:
                            logger.info(f"Telegram startup attempt {attempt_count}/3 failed")
            logger.info("Telegram client started")
    else:
        logger.warning("Startup validation failed or decryption issues detected")
        logger.info(f"Missing fields: {missing_fields}")
        logger.info(f"Decryption errors: {dec_error_count}")
        if not is_valid or not decryption_ok:
            # Increment failure counter for lockout
            _startup_attempts[startup_key] += 1
            attempt_count = _startup_attempts[startup_key]
            if attempt_count >= 3:
                # Lock out for 30 minutes after 3 failures
                lockout_duration = 30 * 60  # 30 minutes in seconds
                _state["lock_until"] = current_time + lockout_duration
                logger.warning(f"Telegram startup locked out for {lockout_duration}s after {attempt_count} consecutive failures")
            else:
                logger.info(f"Telegram startup attempt {attempt_count}/3 failed due to validation/decryption issues")
        logger.info("Skipping Telegram client startup due to validation failure")

    # Load user accounts into pool — ONLY after validation confirms encryption key is correct
    # This prevents spurious "Decryption failed" errors on startup when system is not yet ready
    if is_valid and decryption_ok:
        from .pool_manager import load_user_accounts
        await load_user_accounts()

    # Check if DB data is readable; log clear warning if decryption fails
    if decryption_ok:
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
                    # If not configured, reset attempt counter to allow setup
                    _startup_attempts[startup_key] = 0
                    _state["first_attempt"] = None
                    _state["lock_until"] = None
                    continue

                # Check if we're locked out
                if _state["lock_until"] and current_time < _state["lock_until"]:
                    # Still in lockout, skip health check actions
                    await asyncio.sleep(60)  # Check lock status more frequently during lockout
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

                    # Reset failure counter on successful restart
                    _startup_attempts[startup_key] = 0
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
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https:;"
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
app.include_router(admin_seo_router, prefix="/api")


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
