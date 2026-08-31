# 🎵 TelePlay → Music Streaming Platform | فهرست مستندات

> **Branch:** `feature/music-platform` (تمرکز فعلی: سیستم موزیک) | شاخهٔ مجزای فیلم بعداً: `feature/video-platform`
> آخرین به‌روزرسانی: 2026-08-30 | نگهدارنده: Muse Spark

## هدف پروژه
تبدیل TelePlay (پلتفرم استریم فایل از تلگرام) به **پلتفرم استریم موزیک مقیاس‌پذیر** با:
- وب + اندروید (شنیدن آنلاین، لیست دانلود/آفلاین)
- UI حرفه‌ای (موزیک ≈ Spotify + RadioJavan | فیلم ≈ Netflix — فیلم در شاخهٔ جدا)
- سیستم کش قابل مدیریت توسط ادمین
- دسترسی ربات فقط برای ادمین
- سیستم تبلیغات تحقیق‌شده
- بهینه برای کاربران زیاد (High-traffic ready)

## نقشهٔ مستندات
| # | فایل | موضوع | Todo |
|---|------|-------|------|
| 01 | `01-architecture-music.md` | معماری کلی مهاجرت TelePlay → Music | `todos/01-architecture.todo.md` |
| 02 | `02-domain-model.md` | مدل دامنه موزیک (Artist/Album/Track/Playlist) | `todos/02-domain-model.todo.md` |
| 03 | `03-cache-system.md` | سیستم کش (ادمین-کنترل) | `todos/03-cache-system.todo.md` |
| 04 | `04-advertising-system.md` | تحقیق سیستم تبلیغات | `todos/04-advertising-system.todo.md` |
| 05 | `05-ui-ux-design.md` | تحلیل و طراحی UI/UX | `todos/05-ui-ux-design.todo.md` |
| 06 | `06-android-web-clients.md` | کلاینت‌ها: وب + اندروید + آفلاین | `todos/06-android-web-clients.todo.md` |
| 07 | `07-admin-security.md` | امنیت و دسترسی ادمین‌محور | `todos/07-admin-security.todo.md` |
| 08 | `08-performance-scalability.md` | پرفورمنس و مقیاس‌پذیری | `todos/08-performance-scalability.todo.md` |
| — | `GRAPH.md` | گراف مرکزی وابستگی‌ها و فازبندی | — |

## قواعد به‌روزرسانی
- هر یافتهٔ جدید → به فایل مربوطه اضافه + تاریخ بزنید.
- هر Todo تکمیل شد → در `GRAPH.md` وضعیت را به‌روزرسانی کنید.
- تصمیمات معماری با `ADR` کوتاه در همان فایل ثبت شود.

## فازبندی
- **فاز 1 (فعلی):** موزیک Core (بک‌اند + وب + کش + ادمین + تبلیغات V1)
- **فاز 2 (شاخه جدا):** ویدئو/فیلم Netflix-like
- **فاز 3:** مانیتورینگ، CDN، پرداخت/پرمیوم
