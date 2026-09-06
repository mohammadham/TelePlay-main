# Todo - 13 Music Video & Reel Platform (Refactoring)

## Backend
- [x] حذف Movie/Series/Episode/VideoProgress models از models.py
- [x] افزودن media_type به Track (`audio`, `music_video`, `reel`)
- [x] افزودن media_type به TrackResponse
- [x] حذف video.py router
- [x] فیلتر media_type در list_tracks و create_track در music.py
- [x] حذف video cache از cache_manager.py
- [x] حذف VIDEO_CACHE vars از .env.example
- [x] حذف Movie count از admin stats + جایگزینی با tracks breakdown (audio/music_video/reel)
- [x] پاکسازی video_router از main.py و routers/__init__.py
- [ ] Migration SQL: ALTER TABLE tracks ADD COLUMN media_type VARCHAR(20) DEFAULT 'audio'

## Web Frontend
- [x] حذف کامپوننت‌های video/ (Hero, VideoCard, VideoRow, VideoHome)
- [x] حذف import و route /video از App.tsx
- [x] حذف لینک Video از Sidebar
- [x] افزودن MediaCard با badge MV/Reel + overlay ویدیو
- [x] افزودن media_type filter به MusicHome (tabهای All / Music Videos / Reels)
- [x] افزودن getMusicTracks/getMusicArtists به api.ts
- [x] آپدیت SearchView: پخش ویدیو در MediaPlayer
- [ ] آپدیت NowPlayingBar: پشتیبانی پخش video + show/hide bar

## Android Mobile
- [x] افزودن media_type به Track model
- [x] حذف VideoRepository.kt و VideoModels.kt
- [x] حذف video/ directory از mobile UI
- [x] حذف VideoBottomNavItem و composable
- [x] حذف provideVideoRepository از AppModule
- [x] حذف video API endpoints از TelePlayApi
- [x] افزودن mediaType به MusicRepository.getTracks
- [x] refactor MusicHomeScreen → تب‌های All/Music Videos/Reels + TrackCard با badge
- [x] refactor MusicViewModel → load(tab) با media_type filter
- [ ] اضافه کردن search موزیک به MobileSearchScreen

## Docs
- [ ] Update GRAPH.md
- [ ] Update docs/video/README.md → docs/music-video-platform/README.md
- [ ] Update todos 09-12 references
- [ ] Commit all changes
