# 06 — کلاینت‌ها: وب + اندروید (آفلاین و دانلود)

## وب (React) — ارتقا از `web/src/*`

### تغییرات
- **NowPlayingBar:** کامپوننت ثابت پایین (80px) — همیشه visible وقتی `previewFile` (یا `currentTrack`) ست است. `MediaPlayer.tsx:318` فعلی تمام‌صفحه است؛ باید به دو حالت `bar` + `expanded` تبدیل شود.
- **TrackCard/AlbumCard/ArtistCard:** جدید — کاور 1:1، دکمه Play سبز hover، منوی ⋯ (Add to Playlist, Add to Downloads, Share)
- **Pages:** `HomeMusic`, `SearchMusic`, `Library` (Playlists/Liked), `ArtistPage`, `AlbumPage`
- **State:** گسترش `store.ts` → `currentTrack`, `queue: Track[]`, `queueIndex`, `isShuffle`, `repeatMode`, `likedIds: Set`
- **دانلود (وب):** `a[download]` با `stream_url?download=1` — `routers/streaming.py:50` موجود. صف دانلود با `IndexedDB` یا `localStorage queue` + progress bar.
- **آفلاین (PWA):** Service Worker برای کش کاور/متادیتا (نه بایت موزیک — حجم بالا)

### API Hooks جدید (`lib/api.ts`)
```ts
useTracks(params), useTrack(id), useArtists(), usePlaylists(), useCreatePlaylist(),
useLikeTrack(), useFollowArtist(), useListenHistory(), useDownloadQueue()
```

## اندروید (Kotlin + Compose + ExoPlayer)

### ساختار فعلی `android/`
- Compose TV + ExoPlayer — `FileBrowser` → باید به `MusicApp` (BottomNav) تبدیل شود.

### ساختار هدف
```
ui/
  home/HomeScreen (Recently, Top Artists)
  search/SearchScreen
  library/LibraryScreen (Playlists, Downloads, Liked)
  player/NowPlayingBar + FullPlayerScreen
  playlist/PlaylistScreen
data/
  MusicRepository (Retrofit + Room)
  DownloadManager (WorkManager + ExoPlayer DownloadService)
service/
  MusicService (Media3 MediaSession + ExoPlayer)
```

### قابلیت‌های کلیدی
- **Streaming:** ExoPlayer با `ProgressiveMediaSource` از `/api/stream/{id}?token=` (همان بک‌اند) — Range seek موجود.
- **دانلود آفلاین:** `ExoPlayer DownloadManager` + `Room` برای metadata + `WorkManager` برای صف. کاربر: TrackCard → «دانلود» → `DownloadQueue` → نمایش progress در `DownloadsScreen` → پخش آفلاین از فایل لوکال (fallback به stream اگر فایل نیست).
- **Background Play:** `MediaSession` + نوتیفیکیشن + کنترل‌های لاک‌اسکرین
- **کَش اندروید:** OkHttp cache برای کاورها + ExoPlayer cache 100MB برای chunkها

### همگام‌سازی
- `ListenHistory` و `Like` بین وب/اندروید via API همگام (poll یا push آینده)
- `WatchProgress` فعلی → `ListenHistory.position` reuse

### امنیت
- Token در `EncryptedSharedPreferences` — refresh خودکار (interceptor مشابه `api.ts:129`)

## API مشترک
```
GET /api/v1/music/tracks/:id/stream  (Range + token query برای ExoPlayer)
GET /api/v1/music/tracks/:id/cover  (thumbnail)
POST /api/v1/music/downloads  {track_id}
GET  /api/v1/music/downloads  → queue
```

## تست
- وب: Playwright برای NowPlayingBar + Playwright E2E دانلود
- اندروید: Espresso + ExoPlayer test
