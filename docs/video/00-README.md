# 📺 Video Platform (Netflix-like) — branch `feature/video-platform`

> مبتنی بر `feature/music-platform` + افزودنی ویدئو. موزیک بدون تغییر باقی می‌ماند.

## هدف
پلتفرم ویدئو Netflix-like: دسته‌بندی ژانری، هاور بزرگنمایی، Hero backdrop، ادامه تماشا، کش ویدئو (بزرگ‌تر)، تبلیغ pre-roll (آینده).

## اسناد
| # | فایل |
|---|------|
| 01 | `01-architecture-video.md` |
| 02 | `02-domain-video.md` (Movie/Series/Episode) |
| 03 | `03-cache-video.md` (کش ویدئو 500MB-100MB chunk) |
| 04 | `04-ui-netflix.md` (ردیف افقی، Hero) |
| GRAPH | `GRAPH.md` |

## تفاوت با موزیک
- فایل‌های `file_type=video` → `Movie` / `Episode`
- کش per-chunk بزرگ‌تر، استراتژی TTL طولانی‌تر
- پلیر ExoPlayer با HLS/DASH (آینده) + thumbnail seek
