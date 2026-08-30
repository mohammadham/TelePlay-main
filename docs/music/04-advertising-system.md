# 04 — سیستم تبلیغات (تحقیق و پیشنهاد)

## خلاصهٔ تحقیق (2024-2026)

### مدل‌های رایج پلتفرم‌های موزیک
- **Spotify:** Freemium — رایگان با **audio ads هر 3-4 ترک (15-30s)** + banner/display + sponsored playlist + programmatic via Spotify Ad Studio. نرخ: CPM $15-30 audio.
- **YouTube Music / RadioJavan:** پیش‌رول ویدیویی/صوتی + بنر؛ برای بازار ایران **شبکه‌های داخلی** (مثل یکتانت، مدیااد، صباویژن) مهم‌تر از AdMob به‌دلیل تحریم/پرداخت.
- **Deezer/Apple:** بیشتر subscription-only؛ تبلیغ کم.

### انواع تبلیغ قابل پیاده‌سازی
| نوع | محل نمایش | تکنولوژی | مزیت |
|-----|-----------|----------|------|
| **Audio Interstitial** | بین ترک‌ها (پس از هر 3-4 آهنگ) | تزریق SSML/MP3 + skip بعد 5s | درآمد اصلی |
| **Banner (Display)** | وب/اندروید home & player | Google AdMob / یکتانت JS | کم‌مزاحم |
| **Native Sponsored** | کارت «پیشنهادی اسپانسر» در feed | API داخلی | CTR بالا |
| **Video Pre-roll** | آینده (فاز فیلم) | IMA SDK | CPM بالاتر |

### پیشنهاد برای TelePlay Music (بازار فارسی‌زبان)
**فاز 1 (MVP): داخلی + قابل گسترش**
1. **Audio Ads داخلی:** جدول `ads` (id, title, audio_file_id -> File, duration, target_genre, weight) + `ad_impressions`. منطق: `should_inject_ad(user, play_count)` → هر 3 ترک برای free users، 0 برای premium (آینده). Endpoint: `GET /api/v1/music/next-ad` (اختیاری؛ یا تزریق سمت بک‌اند در stream).
2. **Banner Ads:** کامپوننت `AdBanner` در وب (اسلات بالا/بین گرید) + اندروید `AdView`. برای وب: یکتانت اسکریپت یا placeholder داخلی (`/api/ads/banner?slot=home_top`).
3. **Admin Panel:** CRUD تبلیغ + آمار impression/revenue + تنظیم فرکانس (`AD_EVERY_N_TRACKS`, `AD_ENABLED`).

**فاز 2:** اتصال به **AdMob / AppLovin** برای اندروید + **Google IMA** برای وب (نیاز به domain تأییدشده). برای ایران: یکتانت/نظربازار.

### مدل درآمدی
- Free tier: audio ad هر 15 دقیقه (≈ 4 ترک) — قابل تنظیم ادمین
- Premium (آینده): حذف تبلیغ + کیفیت بالاتر + دانلود نامحدود
- Sponsored playlist: برچسب «حمایت‌شده»

### ضد تقلب و اخلاق
- Frequency capping: هر user ≤ 6 audio ads/hour
- لاگ `ad_impressions` با `user_id, ad_id, track_context, timestamp` — جلوگیری از تکرار spam
- GDPR-like: عدم پخش تبلیغ حساس بر اساس genre (optional)

### API پیشنهادی
```
GET  /api/ads/next?track_id=  → {ad: {id, audio_url, duration, skip_after} | null}
POST /api/ads/impression  {ad_id, track_id}
GET  /api/admin/ads  POST /api/admin/ads  PUT /api/admin/ads/{id}  DELETE /api/admin/ads/{id}
GET  /api/admin/ads/stats → {total_impressions, revenue_estimate, by_ad[]}
PUT  /api/admin/ads/config → {enabled, every_n_tracks, max_per_hour}
```

### معیار موفقیت
- Fill-rate > 80%، CTR banner > 1.5%، Audio completion > 85%

### منابع پیشنهادی برای مطالعه بیشتر (لینک‌های مرجع معتبر — در فاز اجرا Fetch شود)
- Spotify Ad Studio docs
- IAB Audio Ad Standards
- یکتانت مستندات نمایش‌دهنده
