# Todo - 12 Mobile & TV App

## Mobile (Android) — restore music + add video
- [ ] Restore Music bottom nav item in MobileNavigation.kt
- [ ] Restore MusicHomeScreen composable in MobileNavigation
- [ ] Add Video screen + navigation route (VideoHomeScreen)
- [ ] Add Video bottom nav item (after Music)
- [ ] VideoRepository.kt — add to DI (currently on video branch but not merged)
- [ ] VideoModels.kt — merge Movie/Episode models into mobile data layer
- [ ] MobilePlayerScreen — support video file_type (currently audio-only)
- [ ] SearchScreen — show both music + video results
- [ ] HomeScreen — add "Continue Watching" row for video progress
- [ ] Downloads — show video download progress (reuse DownloadService)

## TV (Android Leanback) — from scratch
- [ ] Create tv/ package: ui/tv/ with Leanback components
- [ ] TvMainActivity — hosts Leanback Dashboard
- [ ] TvHomeScreen — LargeCardPresenter (movies) + ListRowPresenter (genres)
- [ ] TvPlayerScreen — ExoPlayer with leanback controls
- [ ] TvSearchScreen — voice search integration
- [ ] TvDetailsScreen — movie/series details with episodes list
- [ ] Horizontal rows: Hero banner + Continue Watching + By Genre
- [ ] Navigation: focus-based (D-pad) not touch
- [ ] Theming: dark Netflix-like (matches web VideoHome)
- [ ] Dependency: add leanback dependency to build.gradle.kts
