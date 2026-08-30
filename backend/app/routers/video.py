"""
Video domain API — Netflix-like browse, movies, series, progress
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from ..database import get_db
from ..models import User, Movie, Series, Episode, VideoProgress, WatchProgress
from ..schemas import MovieResponse, SeriesResponse, EpisodeResponse
from ..auth import get_current_user

router = APIRouter(prefix="/v1/video", tags=["Video"])

def _movie_to_resp(m: Movie) -> dict:
    return {
        "id": m.id, "title": m.title, "description": m.description, "genre": m.genre, "year": m.year,
        "file_id": m.file_id, "duration": m.duration, "featured": m.featured, "created_at": m.created_at,
        "stream_url": f"/api/stream/{m.file_id}", "thumbnail_url": m.thumbnail_url or f"/api/stream/{m.file_id}/thumbnail"
    }

@router.get("/movies", response_model=list[MovieResponse])
async def list_movies(q: Optional[str]=None, genre: Optional[str]=None, featured: Optional[bool]=None, page: int=Query(1, ge=1), per_page: int=Query(20, ge=1, le=50), db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    query = select(Movie)
    if q: query = query.where(or_(Movie.title.ilike(f"%{q}%"), Movie.description.ilike(f"%{q}%")))
    if genre: query = query.where(Movie.genre==genre)
    if featured is not None: query = query.where(Movie.featured==featured)
    query = query.order_by(Movie.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    rows = (await db.execute(query)).scalars().all()
    return [MovieResponse(**_movie_to_resp(m)) for m in rows]

@router.get("/movies/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    m = (await db.execute(select(Movie).where(Movie.id==movie_id))).scalar_one_or_none()
    if not m: raise HTTPException(404, "Movie not found")
    return MovieResponse(**_movie_to_resp(m))

@router.post("/movies", response_model=MovieResponse)
async def create_movie(payload: dict, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    from ..config import get_settings
    settings = get_settings()
    if settings.admin_ids and current_user.telegram_id not in settings.admin_ids:
        raise HTTPException(403, "Admin only")
    m = Movie(title=payload["title"], description=payload.get("description"), genre=payload.get("genre"), year=payload.get("year"), file_id=payload["file_id"], duration=payload.get("duration"), featured=payload.get("featured", False))
    db.add(m); await db.commit(); await db.refresh(m)
    return MovieResponse(**_movie_to_resp(m))

@router.get("/series", response_model=list[SeriesResponse])
async def list_series(q: Optional[str]=None, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    query = select(Series)
    if q: query = query.where(Series.title.ilike(f"%{q}%"))
    query = query.order_by(Series.created_at.desc()).limit(50)
    rows = (await db.execute(query)).scalars().all()
    return [SeriesResponse.model_validate(r, from_attributes=True) for r in rows]

@router.get("/series/{series_id}/episodes", response_model=list[EpisodeResponse])
async def list_episodes(series_id: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    rows = (await db.execute(select(Episode).where(Episode.series_id==series_id).order_by(Episode.season, Episode.episode))).scalars().all()
    return [EpisodeResponse(**{**e.__dict__, "stream_url": f"/api/stream/{e.file_id}"}) for e in rows]

@router.get("/browse")
async def browse(db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    hero = (await db.execute(select(Movie).where(Movie.featured==True).order_by(Movie.created_at.desc()).limit(1))).scalar_one_or_none()
    # continue watching: join VideoProgress
    cw_ids = (await db.execute(select(VideoProgress.file_id).where(VideoProgress.user_id==current_user.id, VideoProgress.completed==False).order_by(VideoProgress.updated_at.desc()).limit(10))).scalars().all()
    cw = []
    if cw_ids:
        cw = (await db.execute(select(Movie).where(Movie.file_id.in_(cw_ids)))).scalars().all()
    # by_genre
    genres = (await db.execute(select(Movie.genre).where(Movie.genre.isnot(None)).distinct().limit(6))).scalars().all()
    by_genre = {}
    for g in genres:
        if not g: continue
        ms = (await db.execute(select(Movie).where(Movie.genre==g).limit(10))).scalars().all()
        by_genre[g] = [MovieResponse(**_movie_to_resp(m)).model_dump() for m in ms]
    return {"hero": MovieResponse(**_movie_to_resp(hero)).model_dump() if hero else None, "continue_watching": [MovieResponse(**_movie_to_resp(m)).model_dump() for m in cw], "by_genre": by_genre}

@router.get("/search")
async def search_video(q: str=Query(..., min_length=1), db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    movies = (await db.execute(select(Movie).where(Movie.title.ilike(f"%{q}%")).limit(20))).scalars().all()
    series = (await db.execute(select(Series).where(Series.title.ilike(f"%{q}%")).limit(20))).scalars().all()
    return {"movies": [MovieResponse(**_movie_to_resp(m)).model_dump() for m in movies], "series": [SeriesResponse.model_validate(s, from_attributes=True).model_dump() for s in series]}

@router.post("/progress")
async def update_progress(payload: dict, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    file_id = payload["file_id"]
    row = (await db.execute(select(VideoProgress).where(VideoProgress.user_id==current_user.id, VideoProgress.file_id==file_id))).scalar_one_or_none()
    if not row:
        row = VideoProgress(user_id=current_user.id, file_id=file_id, position=payload.get("position",0), duration=payload.get("duration"), completed=payload.get("completed", False))
        db.add(row)
    else:
        row.position = payload.get("position", row.position)
        row.duration = payload.get("duration", row.duration)
        row.completed = payload.get("completed", row.completed)
    await db.commit()
    return {"ok": True}

@router.get("/progress/{file_id}")
async def get_progress(file_id: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    row = (await db.execute(select(VideoProgress).where(VideoProgress.user_id==current_user.id, VideoProgress.file_id==file_id))).scalar_one_or_none()
    if not row: return {"position": 0, "completed": False}
    return {"position": row.position, "duration": row.duration, "completed": row.completed}
