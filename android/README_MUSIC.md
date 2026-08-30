# Android Music — Plan (ExoPlayer + Offline)

## Structure (Kotlin)
- `data/MusicRepository.kt` — Retrofit `/api/v1/music/*` + Room `TrackEntity`
- `service/MusicService.kt` — Media3 MediaSession + ExoPlayer ProgressiveMediaSource (`/api/stream/{id}?token=`)
- `download/DownloadManager.kt` — WorkManager + ExoPlayer DownloadService, 100MB cache, progress via Room

## Offline Flow
1. User taps Download → `POST /v1/music/downloads {track_id}` (stub) → WorkManager enqueues
2. ExoPlayer downloads to `cache/audio/{id}.mp3`
3. Playback: if local exists → play local; else stream

## TODO
- Implement `EncryptedSharedPreferences` token storage
- BottomNav: Home/Search/Library/Downloads
- NowPlaying Bar (Compose)

See docs/music/06-android-web-clients.md
