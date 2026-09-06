# Todo - 12 Mobile & TV App

## Mobile (Android) — restore music + add video ✅
- [x] Restore Music bottom nav item in MobileNavigation.kt
- [x] Add Video screen + navigation route (MobileVideoHomeScreen)
- [x] Add Video bottom nav item (after Music)
- [x] VideoRepository.kt — merged into project
- [x] VideoModels.kt — Movie/Series/Episode/VideoBrowse models
- [x] VideoHomeViewModel.kt — StateFlow browse state
- [x] AppModule.kt — VideoRepository @Provides injection
- [ ] MobilePlayerScreen — support video file_type — deferred
- [ ] SearchScreen — show both music + video results — deferred
- [ ] HomeScreen — add "Continue Watching" row for video progress — deferred
- [ ] Downloads — show video download progress — deferred

## TV (Android Leanback) — from scratch ⏳
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
