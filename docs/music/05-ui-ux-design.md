# 05 — طراحی UI/UX (Spotify + RadioJavan + Netflix)

## تحلیل رقبا (یافته‌ها — به‌روزرسانی مستمر)

### Spotify (مرجع اصلی موزیک)
- **Layout:** سایدبار تیره (280px) + هدر sticky + گرید کارت‌ها (4-6 ستون) + پلیر ثابت پایین (80px) + صف پخش/کاور راست
- **کارت‌ها:** کاور مربع (1:1) با `border-radius: 6px` + عنوان bold + زیرعنوان muted + دکمه Play سبز که onHover ظاهر می‌شود
- **رنگ:** `bg #121212 / #000` — accent `#1DB954` (سبز) — متن `white / #b3b3b3`
- **تایپوگرافی:** CircularSp / Inter — وزن 700 برای عنوان ترک
- **پلیر:** Progress bar نازک (hover ضخیم) + کنترل‌های مرکزی (shuffle/prev/play/next/repeat) + ولوم + صف + فول‌اسکرین
- **صفحات کلیدی:** Home (Recently played, Made for you), Search (category tiles), Library (playlists), Artist page (hero + discography), Queue

### RadioJavan (مرجع فارسی)
- **ویژگی متمایز:** تمرکز بر **کاور بزرگ + متن فارسی RTL** + دسته‌بندی «جدیدترین، محبوب‌ترین، ریمیکس، پادکست»
- **رنگ:** تیره + قرمز ` #E30613` accent — فونت Vazirmatn / IRANSans
- **الگو:** لیست ترک با شماره + کاور کوچک 48px + قلب (لایک) + سه‌نقطه
- **نکته:** پشتیبانی کامل RTL و فونت فارسی حیاتی است

### Netflix (مرجع آیندهٔ فیلم — فعلاً رفرنس نگه‌دار)
- ردیف‌های افقی scroll + هاور بزرگنمایی کارت + hero با backdrop + دسته‌بندی ژانری

## Design Tokens پیشنهادی (Music)
```ts
colors: {
  bg: "#0a0a0a", surface: "#121212", surfaceHover: "#1a1a1a",
  border: "rgba(255,255,255,0.08)", text: "#fff", muted: "#b3b3b3",
  primary: "#1DB954", primaryHover: "#1ed760", danger: "#e91429"
}
radius: { card: "8px", pill: "9999px" }
font: { sans: "Vazirmatn, Inter, sans-serif", mono: "JetBrains Mono" }
```

## کامپوننت‌های کلیدی (وضعیت فعلی → هدف)
| کامپوننت | فعلی `web/src/components/*` | هدف موزیک |
|----------|-----------------------------|-----------|
| FileBrowser | گرید فایل عمومی | **TrackGrid / AlbumGrid** + فیلتر ژانر/هنرمند |
| FileCard | کارت فایل با آیکون | **TrackCard** (کاور + عنوان + هنرمند + دکمه Play hovers) |
| MediaPlayer | `MediaPlayer.tsx:9` پلیر تمام‌صفحه | **NowPlayingBar** ثابت + **FullPlayer** (کاور بزرگ + لیریکس + صف) |
| Sidebar | فایل/Recent/Continue | **Library** (Playlists, Liked Songs, Artists) + Search |
| Search | `searchQuery` ساده | Search با تب (Tracks/Artists/Albums/Playlists) + دسته‌بندی کاشی‌ای |

## User Flows
1. **کشف:** Home → Recently Played → کلیک Track → NowPlayingBar + صف
2. **جستجو:** Search → تایپ «محسن» → نتایج هنرمند/ترک → Play/Add to Playlist
3. **پلی‌لیست:** Create Playlist → Add Tracks → Play All → Shuffle
4. **دانلود/آفلاین:** TrackCard → ⋯ → «افزودن به دانلودها» → صف دانلود (آفلاین ExoPlayer)

## RTL & i18n
- `dir="rtl"` برای فارسی + `dir="ltr"` برای انگلیسی auto-switch
- Vazirmatn برای فارسی، Inter برای انگلیسی — `tailwind.config.js` به‌روزرسانی شود

## وایرفریم (متنی)
```
[Sidebar 280px] [Header: Search + User] 
[Content: Section Title] [Grid 5 cols: TrackCard]
[NowPlayingBar: Cover | Title/Artist | Controls | Volume | Queue]
```

## ابزار پیاده‌سازی
- Tailwind موجود حفظ + اضافهٔ `tailwind-rtl` plugin
- Framer Motion برای hover/play animation (اختیاری)
- shadcn/ui برای Modal/Dropdown (جایگزین سفارشی فعلی)
