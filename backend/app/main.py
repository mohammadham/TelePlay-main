"""
FastAPI main application with Telegram MTProto client lifecycle.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

import logging
logging.getLogger("pyrogram").setLevel(logging.INFO)

from .config import get_settings
from .database import init_db
from .telegram import start_telegram_client, stop_telegram_client
from .routers import files_router, folders_router, streaming_router, auth_router, tv_router, music_router, admin_router, ads_router
from .routers.settings import router as settings_router

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
    await start_telegram_client()
    logger.info("Telegram client started")
    
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

# CORS middleware - Properly configured for production
# List allowed origins explicitly instead of using "*"
allowed_origins = [
    settings.web_base_url,  # Your web app domain
    "http://localhost:3000",  # Dev frontend
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Range"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking (allow framing only for same origin)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    
    # XSS protection (legacy but still useful)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Referrer policy - don't leak URLs
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Content Security Policy (adjust as needed for your frontend)
    # response.headers["Content-Security-Policy"] = "default-src 'self'"
    
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





@app.get("/health")
async def health():
    """Health check for container orchestration."""
    return {"status": "healthy"}


# ... imports ...

# Mount static files (assets) - checking if directory exists first to avoid dev errors
if os.path.exists("app/static/assets"):
    app.mount("/assets", StaticFiles(directory="app/static/assets"), name="assets")

# ... (API routers are included above) ...

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the React SPA for any non-API routes."""
    # API routes are already handled by routers above
    if full_path == "api" or full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API Endpoint not found")

    # Check if the file exists in static directory (e.g. logo.png, favicon.ico)
    static_file_path = f"app/static/{full_path}"
    if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
        return FileResponse(static_file_path)
        
    # Serve index.html for generic SPA routes
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
