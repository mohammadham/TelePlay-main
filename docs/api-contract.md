# API Contract — TelePlay

> Auto-generated reference for key endpoints. See OpenAPI spec at `/api/docs` when running.

---

## Base URL
```
https://your-domain.com/api
```

---

## Authentication

All protected endpoints require `Authorization: Bearer <token>` header.

- Login: `POST /api/auth/login-code` → returns code
- Verify: `POST /api/auth/verify-code` → returns `{ access_token, refresh_token }`

---

## Music API (`/api/v1/music`)

### List Tracks
```
GET /api/v1/music/tracks?q={query}&media_type={audio|music_video|reel}&artist_id={id}&page=1&per_page=20
```

**Response:** `TrackResponse[]`
```json
{
  "id": 1,
  "title": "Song Name",
  "artist_id": 5,
  "artist": { "id": 5, "name": "Artist Name" },
  "album_id": null,
  "file_id": 42,
  "duration": 210,
  "genre": "Pop",
  "track_number": 3,
  "play_count": 1024,
  "like_count": 89,
  "created_at": "2024-01-15T10:30:00Z",
  "stream_url": "/api/stream/42",
  "cover_url": null,
  "is_liked": false,
  "media_type": "audio"
}
```

### Search Music
```
GET /api/v1/music/search?q=query
```
Returns `{ tracks: [...], artists: [...], albums: [...] }`

### Create Track (Admin only)
```
POST /api/v1/music/tracks
Content-Type: application/json
Body: { "title": "...", "artist_name": "...", "file_id": 42, "media_type": "audio" }
```

### Like / Unlike
```
POST /api/v1/music/likes/{track_id}
DELETE /api/v1/music/likes/{track_id}
```

### Playlists
```
GET  /api/v1/music/playlists
POST /api/v1/music/playlists          → { id, user_id, title, is_public }
POST /api/v1/music/playlists/{pid}/tracks/{tid}
DELETE /api/v1/music/playlists/{pid}/tracks/{tid}
```

### Listen History
```
POST /api/v1/music/history
Body: { "track_id": 1, "duration": 210 }
```

### Downloads
```
POST /api/v1/music/downloads/{track_id}
```

---

## Files API (`/api/files`)

### List Files
```
GET /api/files?folder_id={null|id}&file_type={video|audio|image|document}&search={query}&page=1&per_page=20
```

### Get File
```
GET /api/files/{file_id}
```

### Update File (rename, change folder)
```
PATCH /api/files/{file_id}
Body: { "file_name": "new_name.mp4", "folder_id": 5 }
```

### Delete File(s)
```
POST /api/files/batch-delete
Body: { "file_ids": [1, 2, 3] }
```

### Move File(s)
```
POST /api/files/batch-move
Body: { "ids": [1, 2], "folder_id": 5 }
```

---

## Folders API (`/api/folders`)

### List Folders
```
GET /api/folders?parent_id={null|id}
```

### Get Folder Tree
```
GET /api/folders/tree
```

### Create Folder
```
POST /api/folders
Body: { "name": "My Folder", "parent_id": null }
```

### Update Folder (rename, move)
```
PATCH /api/folders/{folder_id}
Body: { "name": "New Name", "parent_id": 5 }
```

### Delete Folder
```
DELETE /api/folders/{folder_id}?move_files_to={null|folder_id}
```

---

## Streaming

### Stream File
```
GET /api/stream/{file_id}
Headers: Authorization: Bearer <token>
Range: bytes=0-  (partial content support)
```

### Stream Thumbnail
```
GET /api/stream/{file_id}/thumbnail
```

---

## Admin API (`/api/admin`)

Requires admin role.

### Stats
```
GET /api/admin/stats
```

### Cache Config
```
GET  /api/admin/cache/config
PUT  /api/admin/cache/config
GET  /api/admin/cache/stats
POST /api/admin/cache/purge
```

### Users
```
GET /api/admin/users?q={search}&page=1&per_page=20
```

### Files
```
GET /api/admin/files?q={search}&file_type={type}&page=1&per_page=20
```

### System Info
```
GET /api/admin/system
```

---

## Ads API (`/api/ads`)

```
GET  /api/ads/next        → { ad: {...}, audio_url: "...", skip_after: 5 }
POST /api/ads/impression  → { ok: true }
```

---

## Data Models

### FileResponse
```json
{
  "id": 1,
  "user_id": 42,
  "folder_id": null,
  "file_id": "AAQYAAd0xHHtAXElQg",
  "file_unique_id": "AgACAgIAAxkDAAJaY3jXm8Gh",
  "file_name": "movie.mp4",
  "file_size": 524288000,
  "mime_type": "video/mp4",
  "file_type": "video",
  "duration": 7200.5,
  "width": 1920,
  "height": 1080,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "thumbnail_url": "/api/stream/1/thumbnail",
  "stream_url": "/api/stream/1",
  "download_url": "/api/files/1/download",
  "last_pos": 120000,
  "public_hash": null,
  "public_stream_url": null
}
```

### FolderResponse
```json
{
  "id": 1,
  "name": "Movies",
  "parent_id": null,
  "user_id": 42,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "file_count": 15
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Music playlists | 10/min |
| Like/unlike | 30/min |
| Download | 10/min |
| Auth login | 5/min per IP |
| Auth verify | 10/min per user |
