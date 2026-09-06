# 📺 Video Platform (Netflix-like)

> مبتنی بر feature/music-platform + افزودنی ویدئو. موزیک بدون تغییر باقی می‌ماند.

## هدف
پلتفرم ویدئو Netflix-like: دسته‌بندی ژانری، هاور بزرگنمایی، Hero backdrop، ادامه تماشا، کش ویدئو (بزرگ‌تر)، تبلیغ pre-roll (آینده).

## اسناد
| # | فایل |
|---|------|
| 01 | `01-architecture-video.md` |
| 02 | `02-domain-video.md` |
| 03 | `03-cache-video.md` |
| 04 | `04-ui-netflix.md` |
| GRAPH | `GRAPH.md` |

## تفاوت با موزیک
- فایل‌های `file_type=video` → `Movie` / `Episode`
- کش per-chunk بزرگ‌تر، استراتژی TTL طولانی‌تر
- پلیر ExoPlayer با HLS/DASH (آینده) + thumbnail seek
