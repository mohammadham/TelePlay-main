"""
Database setup with SQLAlchemy async support.
Supports both SQLite (for development) and PostgreSQL (for production).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine import make_url

# Lazy engine — avoid crashing at import time when ENV is missing (Railway)
_engine = None
_async_session = None

def _build_engine():
    from .config import get_settings
    from sqlalchemy.engine import make_url as _make_url
    # This will raise ValidationError with clear message if ENV missing — caught in lifespan
    settings = get_settings()
    url = _make_url(settings.database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")
        if "schema" in url.query:
            query = dict(url.query)
            del query["schema"]
            url = url.set(query=query)
    elif url.drivername == "sqlite":
        url = url.set(drivername="sqlite+aiosqlite")
    eng = create_async_engine(
        url, echo=False, pool_pre_ping=True, pool_recycle=1800, pool_size=40, max_overflow=20
    )
    return eng, async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

def get_engine():
    global _engine, _async_session
    if _engine is None:
        _engine, _async_session = _build_engine()
    return _engine

def get_sessionmaker():
    global _engine, _async_session
    if _async_session is None:
        get_engine()
    return _async_session

# Try to build at import for local dev, but don't crash container if ENV missing
try:
    _engine, _async_session = _build_engine()
    engine = _engine
    async_session = _async_session
except Exception as _e:
    # Keep None — will be built lazily in lifespan and give clear error
    import logging
    logging.getLogger(__name__).warning(f"DB engine not built at import (ENV missing, will retry at startup): {_e}")
    engine = None  # type: ignore
    async_session = None  # type: ignore
    _engine = None
    _async_session = None


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency for getting database session."""
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
