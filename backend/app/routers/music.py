"""
Music domain API — Tracks, Artists, Albums, Playlists, Likes, History
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import User, Track, Artist, Album, Playlist, PlaylistTrack, Like, Follow, ListenHistory, File
from ..schemas import TrackResponse, ArtistResponse, AlbumResponse, PlaylistResponse
from ..auth import get_current_user

router = APIRouter(prefix="/v1/music", tags=["Music"])

def _track_to_resp(t: Track, is_liked=False) -> dict:
    return {
        "id": t.id, "title": t.title, "artist_id": t.artist_id,
        "artist": t.artist, "album_id": t.album_id, "album": t.album,
        "file_id": t.file_id, "duration": t.duration, "genre": t.genre,
        "track_number": t.track_number, "play_count": t.play_count,
        "like_count": t.like_count, "created_at": t.created_at,
        "stream_url": f"/api/stream/{t.file_id}", "cover_url": None,
        "is_liked": is_liked,
    }

@router.get("/tracks", response_model=list[TrackResponse])
async def list_tracks(
    q: Optional[str] = None, artist_id: Optional[int] = None, album_id: Optional[int] = None,
    genre: Optional[str] = None, page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Track).options(selectinload(Track.artist), selectinload(Track.album))
    if q: query = query.where(or_(Track.title.ilike(f"%{q}%"), Track.genre.ilike(f"%{q}%")))
    if artist_id: query = query.where(Track.artist_id == artist_id)
    if album_id: query = query.where(Track.album_id == album_id)
    if genre: query = query.where(Track.genre == genre)
    query = query.order_by(Track.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    tracks = result.scalars().all()
    # liked set
    liked_ids = set((await db.execute(select(Like.track_id).where(Like.user_id==current_user.id))).scalars().all())
    return [TrackResponse(**_track_to_resp(t, t.id in liked_ids)) for t in tracks]

@router.get("/tracks/{track_id}", response_model=TrackResponse)
async def get_track(track_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Track).where(Track.id==track_id).options(selectinload(Track.artist), selectinload(Track.album)))
    t = result.scalar_one_or_none()
    if not t: raise HTTPException(404, "Track not found")
    liked = (await db.execute(select(Like).where(Like.user_id==current_user.id, Like.track_id==track_id))).scalar_one_or_none() is not None
    return TrackResponse(**_track_to_resp(t, liked))

@router.post("/tracks", response_model=TrackResponse)
async def create_track(payload: dict, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Admin-only track creation (uses existing File)
    from ..config import get_settings
    settings = get_settings()
    if settings.admin_ids and current_user.telegram_id not in settings.admin_ids:
        raise HTTPException(403, "Admin only")
    # Resolve artist by name or id
    artist_id = payload.get("artist_id")
    if not artist_id and payload.get("artist_name"):
        # find or create
        r = await db.execute(select(Artist).where(Artist.name==payload["artist_name"]))
        a = r.scalar_one_or_none()
        if not a:
            a = Artist(name=payload["artist_name"])
            db.add(a); await db.flush()
        artist_id = a.id
    if not artist_id: raise HTTPException(400, "artist_id or artist_name required")
    file_id = payload.get("file_id")
    if not file_id: raise HTTPException(400, "file_id required")
    t = Track(title=payload.get("title","Untitled"), artist_id=artist_id, album_id=payload.get("album_id"), file_id=file_id, duration=payload.get("duration"), genre=payload.get("genre"), track_number=payload.get("track_number"))
    db.add(t); await db.commit()
    await db.refresh(t)
    # reload with artist
    r = await db.execute(select(Track).where(Track.id==t.id).options(selectinload(Track.artist), selectinload(Track.album)))
    t = r.scalar_one()
    return TrackResponse(**_track_to_resp(t))

@router.get("/artists", response_model=list[ArtistResponse])
async def list_artists(q: Optional[str]=None, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    query = select(Artist)
    if q: query = query.where(Artist.name.ilike(f"%{q}%"))
    query = query.order_by(Artist.name).limit(50)
    result = await db.execute(query)
    return [ArtistResponse.model_validate(a, from_attributes=True) for a in result.scalars().all()]

@router.get("/albums", response_model=list[AlbumResponse])
async def list_albums(artist_id: Optional[int]=None, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    query = select(Album).options(selectinload(Album.artist))
    if artist_id: query = query.where(Album.artist_id==artist_id)
    query = query.order_by(Album.created_at.desc()).limit(50)
    result = await db.execute(query)
    return [AlbumResponse.model_validate(a, from_attributes=True) for a in result.scalars().all()]

@router.get("/search")
async def search(q: str = Query(..., min_length=1), db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    tracks = (await db.execute(select(Track).where(Track.title.ilike(f"%{q}%")).options(selectinload(Track.artist)).limit(20))).scalars().all()
    artists = (await db.execute(select(Artist).where(Artist.name.ilike(f"%{q}%")).limit(20))).scalars().all()
    albums = (await db.execute(select(Album).where(Album.title.ilike(f"%{q}%")).limit(20))).scalars().all()
    return {"tracks": [TrackResponse(**_track_to_resp(t)) for t in tracks], "artists": [ArtistResponse.model_validate(a, from_attributes=True) for a in artists], "albums": [AlbumResponse.model_validate(a, from_attributes=True) for a in albums]}

# Playlists
@router.post("/playlists", response_model=PlaylistResponse)
async def create_playlist(payload: dict, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    p = Playlist(user_id=current_user.id, title=payload.get("title","New Playlist"), is_public=payload.get("is_public", False))
    db.add(p); await db.commit(); await db.refresh(p)
    return PlaylistResponse(id=p.id, user_id=p.user_id, title=p.title, is_public=p.is_public, created_at=p.created_at, tracks=[])

@router.get("/playlists", response_model=list[PlaylistResponse])
async def list_playlists(db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    result = await db.execute(select(Playlist).where(Playlist.user_id==current_user.id).order_by(Playlist.created_at.desc()))
    playlists = result.scalars().all()
    out=[]
    for p in playlists:
        rows = (await db.execute(select(Track).join(PlaylistTrack, Track.id==PlaylistTrack.track_id).where(PlaylistTrack.playlist_id==p.id).options(selectinload(Track.artist)).order_by(PlaylistTrack.position))).scalars().all()
        out.append(PlaylistResponse(id=p.id, user_id=p.user_id, title=p.title, is_public=p.is_public, created_at=p.created_at, tracks=[TrackResponse(**_track_to_resp(t)) for t in rows]))
    return out

@router.post("/playlists/{pid}/tracks/{tid}")
async def add_to_playlist(pid: int, tid: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    p = (await db.execute(select(Playlist).where(Playlist.id==pid, Playlist.user_id==current_user.id))).scalar_one_or_none()
    if not p: raise HTTPException(404, "Playlist not found")
    # next position
    max_pos = (await db.execute(select(func.max(PlaylistTrack.position)).where(PlaylistTrack.playlist_id==pid))).scalar() or 0
    pt = PlaylistTrack(playlist_id=pid, track_id=tid, position=max_pos+1)
    db.add(pt); await db.commit()
    return {"ok": True}

@router.delete("/playlists/{pid}/tracks/{tid}")
async def remove_from_playlist(pid: int, tid: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    await db.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id==pid, PlaylistTrack.track_id==tid))
    await db.commit()
    return {"ok": True}

# Likes
@router.post("/likes/{track_id}")
async def like_track(track_id: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    exists = (await db.execute(select(Like).where(Like.user_id==current_user.id, Like.track_id==track_id))).scalar_one_or_none()
    if not exists:
        db.add(Like(user_id=current_user.id, track_id=track_id))
        t = (await db.execute(select(Track).where(Track.id==track_id))).scalar_one_or_none()
        if t: t.like_count += 1
        await db.commit()
    return {"liked": True}

@router.delete("/likes/{track_id}")
async def unlike_track(track_id: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    await db.execute(delete(Like).where(Like.user_id==current_user.id, Like.track_id==track_id))
    t = (await db.execute(select(Track).where(Track.id==track_id))).scalar_one_or_none()
    if t and t.like_count>0: t.like_count -= 1
    await db.commit()
    return {"liked": False}

# History
@router.post("/history")
async def add_history(payload: dict, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    h = ListenHistory(user_id=current_user.id, track_id=payload["track_id"], position=payload.get("position",0), duration=payload.get("duration"), completed=payload.get("completed", False))
    db.add(h)
    # increment play_count
    t = (await db.execute(select(Track).where(Track.id==payload["track_id"]))).scalar_one_or_none()
    if t: t.play_count += 1
    await db.commit()
    return {"ok": True}

@router.get("/history")
async def get_history(limit: int=20, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    rows = (await db.execute(select(Track).join(ListenHistory, Track.id==ListenHistory.track_id).where(ListenHistory.user_id==current_user.id).options(selectinload(Track.artist)).order_by(ListenHistory.played_at.desc()).limit(limit))).scalars().all()
    return [TrackResponse(**_track_to_resp(t)) for t in rows]
