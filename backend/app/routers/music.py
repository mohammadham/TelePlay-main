"""
Music domain API — Tracks, Artists, Albums, Playlists, Likes, History
"""
import hashlib
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_
from sqlalchemy.orm import selectinload
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..database import get_db
from ..models import User, Track, Artist, Album, Playlist, PlaylistTrack, Like, Follow, ListenHistory, File
from ..schemas import TrackResponse, ArtistResponse, AlbumResponse, PlaylistResponse
from ..auth import get_current_user
from ..services import sanitize_text, escape_like

router = APIRouter(prefix="/v1/music", tags=["Music"])

# Rate limiter for music endpoints
limiter = Limiter(key_func=get_remote_address)

def _track_to_resp(t: Track, is_liked: bool = False) -> Dict[str, Any]:
    cover_url: Optional[str] = None
    if t.album and t.album.cover_file_id:
        cover_url = f"/api/stream/cover/{t.album.cover_file_id}"
    elif t.cover_url:
        cover_url = t.cover_url
    return {
        "id": t.id, "title": t.title, "artist_id": t.artist_id,
        "artist": t.artist, "album_id": t.album_id, "album": t.album,
        "file_id": t.file_id, "duration": t.duration, "genre": t.genre,
        "track_number": t.track_number, "play_count": t.play_count,
        "like_count": t.like_count, "created_at": t.created_at,
        "stream_url": f"/api/stream/{t.file_id}", "cover_url": cover_url,
        "thumbnail_url": t.thumbnail_url if hasattr(t, 'thumbnail_url') else None,
        "is_liked": is_liked, "media_type": t.media_type,
        "explicit": t.explicit if hasattr(t, 'explicit') else False,
    }

@router.get("/tracks", response_model=list[TrackResponse])
async def list_tracks(
    request: Request = None,
    q: Optional[str] = None, artist_id: Optional[int] = None, album_id: Optional[int] = None,
    genre: Optional[str] = None, media_type: Optional[str] = None,
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Track).options(selectinload(Track.artist), selectinload(Track.album))
    if q: query = query.where(or_(Track.title.ilike(f"%{escape_like(q)}%", escape="\\"), Track.genre.ilike(f"%{escape_like(q)}%", escape="\\")))
    if artist_id: query = query.where(Track.artist_id == artist_id)
    if album_id: query = query.where(Track.album_id == album_id)
    if genre: query = query.where(Track.genre == genre)
    if media_type: query = query.where(Track.media_type == media_type)
    query = query.order_by(Track.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    tracks = result.scalars().all()
    # liked set
    liked_ids = set((await db.execute(select(Like.track_id).where(Like.user_id==current_user.id))).scalars().all())
    result = [TrackResponse(**_track_to_resp(t, t.id in liked_ids)) for t in tracks]
    data = json.dumps([r.model_dump() for r in result], sort_keys=True)
    etag = hashlib.md5(data.encode()).hexdigest()
    # Handle conditional request
    if_none_match = request.headers.get("if-none-match") if request else None
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"', "Cache-Control": "public, max-age=60"})
    return Response(
        content=data,
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=60", "ETag": f'"{etag}"'}
    )

@router.get("/tracks/{track_id}", response_model=TrackResponse)
async def get_track(track_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Track).where(Track.id==track_id).options(selectinload(Track.artist), selectinload(Track.album)))
    t = result.scalar_one_or_none()
    if not t: raise HTTPException(404, "Track not found")
    liked = (await db.execute(select(Like).where(Like.user_id==current_user.id, Like.track_id==track_id))).scalar_one_or_none() is not None
    return TrackResponse(**_track_to_resp(t, liked))

@router.post("/tracks", response_model=TrackResponse)
async def create_track(payload: Dict[str, Any], db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)) -> TrackResponse:
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
            a = Artist(name=sanitize_text(payload["artist_name"]))
            db.add(a); await db.flush()
        artist_id = a.id
    if not artist_id: raise HTTPException(400, "artist_id or artist_name required")
    file_id = payload.get("file_id")
    if not file_id: raise HTTPException(400, "file_id required")
    t = Track(
    title=sanitize_text(payload.get("title", "Untitled")),
    artist_id=artist_id,
    album_id=payload.get("album_id"),
    file_id=file_id,
    duration=payload.get("duration"),
    genre=sanitize_text(payload.get("genre")),
    track_number=payload.get("track_number"),
    media_type=payload.get("media_type", "audio")
)
    db.add(t); await db.commit()
    await db.refresh(t)
    # reload with artist
    r = await db.execute(select(Track).where(Track.id==t.id).options(selectinload(Track.artist), selectinload(Track.album)))
    t = r.scalar_one()
    return TrackResponse(**_track_to_resp(t))

@router.get("/artists", response_model=list[ArtistResponse])
async def list_artists(request: Request = None, q: Optional[str]=None, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    query = select(Artist)
    if q: query = query.where(Artist.name.ilike(f"%{escape_like(q)}%", escape="\\"))
    query = query.order_by(Artist.name).limit(50)
    result = await db.execute(query)
    artists = [a.model_validate(a, from_attributes=True) for a in result.scalars().all()]
    data = json.dumps([a.model_dump() for a in artists], sort_keys=True)
    etag = hashlib.md5(data.encode()).hexdigest()
    if_none_match = request.headers.get("if-none-match") if request else None
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"', "Cache-Control": "public, max-age=120"})
    return Response(content=data, media_type="application/json", headers={"Cache-Control": "public, max-age=120", "ETag": f'"{etag}"'})

@router.get("/artists/{aid}")
async def get_artist(aid: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    artist = (await db.execute(select(Artist).where(Artist.id==aid))).scalar_one_or_none()
    if not artist: raise HTTPException(404, "Artist not found")
    rows = (await db.execute(select(Track).where(Track.artist_id==aid).options(selectinload(Track.artist))).order_by(Track.created_at.desc()).limit(50)).scalars().all()
    liked_ids = (await db.execute(select(Like.track_id).where(Like.user_id==current_user.id))).scalars().all()
    avatar_url = f"/api/stream/cover/{artist.avatar_file_id}" if artist.avatar_file_id else None
    return {
        "id": artist.id,
        "name": artist.name,
        "bio": artist.bio,
        "verified": artist.verified,
        "avatar_url": avatar_url,
        "tracks": [TrackResponse(**_track_to_resp(t, t.id in liked_ids)).model_dump() for t in rows],
    }

@router.get("/albums", response_model=list[AlbumResponse])
async def list_albums(request: Request = None, artist_id: Optional[int]=None, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    query = select(Album).options(selectinload(Album.artist))
    if artist_id: query = query.where(Album.artist_id==artist_id)
    query = query.order_by(Album.created_at.desc()).limit(50)
    result = await db.execute(query)
    albums = [a.model_validate(a, from_attributes=True) for a in result.scalars().all()]
    data = json.dumps([a.model_dump() for a in albums], sort_keys=True)
    etag = hashlib.md5(data.encode()).hexdigest()
    if_none_match = request.headers.get("if-none-match") if request else None
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"', "Cache-Control": "public, max-age=120"})
    return Response(content=data, media_type="application/json", headers={"Cache-Control": "public, max-age=120", "ETag": f'"{etag}"'})

@router.get("/search")
async def search(request: Request = None, q: str = Query(..., min_length=1), db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    tracks = (await db.execute(select(Track).where(Track.title.ilike(f"%{escape_like(q)}%", escape="\\")).options(selectinload(Track.artist)).limit(20))).scalars().all()
    artists = (await db.execute(select(Artist).where(Artist.name.ilike(f"%{escape_like(q)}%", escape="\\")).limit(20))).scalars().all()
    albums = (await db.execute(select(Album).where(Album.title.ilike(f"%{escape_like(q)}%", escape="\\")).limit(20))).scalars().all()
    data = {
        "tracks": [TrackResponse(**_track_to_resp(t)).model_dump() for t in tracks],
        "artists": [ArtistResponse.model_validate(a, from_attributes=True).model_dump() for a in artists],
        "albums": [AlbumResponse.model_validate(a, from_attributes=True).model_dump() for a in albums]
    }
    json_data = json.dumps(data, sort_keys=True)
    etag = hashlib.md5(json_data.encode()).hexdigest()
    if_none_match = request.headers.get("if-none-match") if request else None
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"', "Cache-Control": "public, max-age=60"})
    return Response(content=json_data, media_type="application/json", headers={"Cache-Control": "public, max-age=60", "ETag": f'"{etag}"'})

# Playlists
@router.post("/playlists", response_model=PlaylistResponse)
@limiter.limit("10/minute")
async def create_playlist(request: Request = None, payload: Dict[str, Any] = None, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> PlaylistResponse:
    p = Playlist(user_id=current_user.id, title=sanitize_text(payload.get("title","New Playlist")), is_public=payload.get("is_public", False))
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

@router.get("/playlists/{pid}")
async def get_playlist(pid: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)):
    p = (await db.execute(select(Playlist).where(Playlist.id==pid, Playlist.user_id==current_user.id))).scalar_one_or_none()
    if not p: raise HTTPException(404, "Playlist not found")
    rows = (await db.execute(select(Track).join(PlaylistTrack, Track.id==PlaylistTrack.track_id).where(PlaylistTrack.playlist_id==p.id).options(selectinload(Track.artist)).order_by(PlaylistTrack.position))).scalars().all()
    return PlaylistResponse(id=p.id, user_id=p.user_id, title=p.title, is_public=p.is_public, created_at=p.created_at, tracks=[TrackResponse(**_track_to_resp(t, t.id in (await db.execute(select(Like.track_id).where(Like.user_id==current_user.id))).scalars().all())) for t in rows])

@router.post("/playlists/{pid}/tracks/{tid}")
async def add_to_playlist(pid: int, tid: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> Dict[str, Any]:
    p = (await db.execute(select(Playlist).where(Playlist.id==pid, Playlist.user_id==current_user.id))).scalar_one_or_none()
    if not p: raise HTTPException(404, "Playlist not found")
    # next position
    max_pos = (await db.execute(select(func.max(PlaylistTrack.position)).where(PlaylistTrack.playlist_id==pid))).scalar() or 0
    pt = PlaylistTrack(playlist_id=pid, track_id=tid, position=max_pos+1)
    db.add(pt); await db.commit()
    return {"ok": True}

@router.delete("/playlists/{pid}/tracks/{tid}")
async def remove_from_playlist(pid: int, tid: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> Dict[str, Any]:
    await db.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id==pid, PlaylistTrack.track_id==tid))
    await db.commit()
    return {"ok": True}

# Likes
@router.post("/likes/{track_id}")
@limiter.limit("30/minute")
async def like_track(request: Request = None, track_id: int = None, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> Dict[str, bool]:
    exists = (await db.execute(select(Like).where(Like.user_id==current_user.id, Like.track_id==track_id))).scalar_one_or_none()
    if not exists:
        db.add(Like(user_id=current_user.id, track_id=track_id))
        t = (await db.execute(select(Track).where(Track.id==track_id))).scalar_one_or_none()
        if t: t.like_count += 1
        await db.commit()
    return {"liked": True}

@router.delete("/likes/{track_id}")
async def unlike_track(track_id: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> Dict[str, bool]:
    await db.execute(delete(Like).where(Like.user_id==current_user.id, Like.track_id==track_id))
    t = (await db.execute(select(Track).where(Track.id==track_id))).scalar_one_or_none()
    if t and t.like_count>0: t.like_count -= 1
    await db.commit()
    return {"liked": False}

# History
@router.post("/history")
async def add_history(payload: Dict[str, Any], db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> Dict[str, Any]:
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

# Downloads
@router.get("/downloads")
async def list_downloads(db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> List[Dict[str, Any]]:
    from ..models import DownloadQueue
    rows = (await db.execute(select(DownloadQueue).where(DownloadQueue.user_id==current_user.id).order_by(DownloadQueue.created_at.desc()))).scalars().all()
    # enrich with track
    out=[]
    for d in rows:
        tr = (await db.execute(select(Track).where(Track.id==d.track_id).options(selectinload(Track.artist)))).scalar_one_or_none()
        out.append({"id": d.id, "status": d.status, "progress": d.progress, "track": TrackResponse(**_track_to_resp(tr)) if tr else None, "created_at": d.created_at})
    return out

@router.post("/downloads")
@limiter.limit("10/minute")
async def add_download(request: Request = None, payload: Dict[str, Any] = None, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> Dict[str, Any]:
    from ..models import DownloadQueue
    track_id = payload.get("track_id")
    if not track_id: raise HTTPException(400, "track_id required")
    exists = (await db.execute(select(DownloadQueue).where(DownloadQueue.user_id==current_user.id, DownloadQueue.track_id==track_id))).scalar_one_or_none()
    if exists:
        return {"id": exists.id, "status": exists.status}
    dq = DownloadQueue(user_id=current_user.id, track_id=track_id, status="queued", progress=0)
    db.add(dq); await db.commit(); await db.refresh(dq)
    return {"id": dq.id, "status": dq.status}

@router.delete("/downloads/{dq_id}")
async def delete_download(dq_id: int, db: AsyncSession=Depends(get_db), current_user: User=Depends(get_current_user)) -> Dict[str, Any]:
    from ..models import DownloadQueue
    await db.execute(delete(DownloadQueue).where(DownloadQueue.id==dq_id, DownloadQueue.user_id==current_user.id))
    await db.commit()
    return {"ok": True}
