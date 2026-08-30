# 04 — UI Netflix-like

## تحلیل Netflix
- Hero: backdrop full-width + title + Play + My List
- ردیف‌ها: `Trending, New, Action, Continue Watching` — scroll افقی، کارت 16:9، هاور scale 1.1 + preview
- صفحه Detail: backdrop + metadata + Play + Episode list (برای سریال)

## پیاده‌سازی
- Web: `components/video/VideoRow.tsx`, `Hero.tsx`, `VideoCard.tsx` (Tailwind + Framer)
- Android TV: Compose TV `Browse` با D-pad focus
- بهینه: lazy image, placeholder blur, skeleton

## فاز بعدی (Ads video)
- IMA pre-roll 15s قبل از movie (skippable after 5s)
