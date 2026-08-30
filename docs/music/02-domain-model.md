# 02 — مدل دامنهٔ موزیک

## تحلیل مدل فعلی `models.py:53`
- `File` (file_name, file_size, mime_type, file_type, duration, width/height, thumbnail_file_id, public_hash) — مناسب ویدئو/فایل عمومی؛ **فاقد** artist/album/genre/bitrate/cover/lyrics.
- `Folder` سلسله‌مراتبی — برای موزیک باید به **Playlist/Album** نگاشت شود.
- `WatchProgress` — برای موزیک می‌شود `ListenHistory` + `last_pos`.

## مدل پیشنهادی (SQLAlchemy)

### موجودیت‌های جدید
```python
class Artist(Base):
    __tablename__ = "artists"
    id, name (unique, index), bio, avatar_file_id, verified, created_at

class Album(Base):
    __tablename__ = "albums"
    id, title, artist_id FK, cover_file_id, release_date, genre, total_tracks
    # Index: (artist_id), (genre)

class Track(Base):
    __tablename__ = "tracks"
    id, title, artist_id FK, album_id FK nullable, file_id FK -> files.id (1-1)
    duration, bitrate, genre, track_number, play_count, like_count
    lyrics_text nullable, explicit bool
    # Index: (artist_id), (album_id), (genre), (play_count)

class Playlist(Base):
    __tablename__ = "playlists"
    id, user_id FK, title, is_public bool, cover_file_id, created_at

class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    playlist_id FK, track_id FK, position int, added_at
    PK(playlist_id, track_id)

class Like(Base):
    __tablename__ = "likes"
    user_id FK, track_id FK, created_at
    PK(user_id, track_id)

class Follow(Base):
    __tablename__ = "follows"
    user_id FK, artist_id FK, created_at
    PK(user_id, artist_id)

class ListenHistory(Base):
    __tablename__ = "listen_history"
    id, user_id FK, track_id FK, position int, duration int, completed bool, played_at
    Index(user_id, played_at desc)

class DownloadQueue(Base):
    __tablename__ = "download_queue"
    id, user_id FK, track_id FK, status (queued/downloading/done/failed), progress int, created_at

class AdImpression(Base):
    __tablename__ = "ad_impressions"
    id, user_id FK nullable, track_id FK nullable, ad_id FK, played_at, revenue decimal
```

### ارتباط با File موجود
- **گزینه A (پیشنهادی):** `Track.file_id -> File.id` — File همچنان holder بایت تلگرام؛ Track لایهٔ metadata موزیک. migration صفر-risk، streaming فعلی reuse می‌شود (`routers/streaming.py:44`).
- گزینه B: توسعهٔ File با ستون‌های nullable موزیک — شلوغ و ضد-normalization.

### دیاگرام ER (خلاصه)
```
User 1--* Playlist 1--* PlaylistTrack *--1 Track *--1 Artist
Track *--1 Album *--1 Artist
Track 1--1 File (Telegram)
User *--* Like *-- Track
User *--* Follow *-- Artist
User 1--* ListenHistory *--1 Track
```

### ایندکس‌ها و پرفورمنس
- `Track`: `idx_track_artist(artist_id)`, `idx_track_album(album_id)`, `idx_track_genre(genre)`, `idx_track_popularity(play_count DESC)`
- `ListenHistory`: `idx_history_user_time(user_id, played_at DESC)` برای feed
- `PlaylistTrack`: `idx_playlist_pos(playlist_id, position)`
- Full-text search: `GIN (to_tsvector(title || artist.name))` یا ساده `ilike` مرحلهٔ اول (`services.py:escape_like` موجود).

### Migration Plan
1. Alembic revision: create tables جدید (nullable FK).
2. Backfill script: `File.file_type='audio'` → ساخت Artist/Track پیش‌فرض (parse از file_name).
3. بکوارد: endpointهای `/api/files` دست‌نخورده؛ `/api/v1/music/*` جدید.

### API Schemas (Pydantic) پیشنهادی
- `TrackResponse: id, title, artist{...}, album{...}, duration, cover_url, stream_url, like_count, is_liked`
- `PlaylistResponse: id, title, tracks: List[TrackResponse], total_duration`
