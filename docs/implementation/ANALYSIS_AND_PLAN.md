# TelePlay Implementation Analysis & Plan

## Date: 2026-09-08
## Updated: Phase 1 - Research & Planning

---

## Research Findings

### Telegram Bot Upload Architecture
- Files are uploaded via Telegram bot to a storage channel
- Metadata is stored in database with `file_id`, `file_unique_id`, `channel_message_id`
- Files are streamed via Telegram MTProto using user accounts
- Upload forms in web UI would need to interact with the bot (send file to bot → bot stores in channel → metadata saved to DB)

### Admin Access Control
- Current system uses `require_admin` dependency in backend
- Frontend checks `user.role === 'ADMIN' || 'SUPER_ADMIN'`
- Admin dashboard route `/admin` is protected by `ProtectedRoute`

---

## Issues Confirmed & Fixes

### 1. Admin Panel Menu (CRITICAL)
**Problem**: `AdminDashboard.tsx` uses horizontal tab bar instead of proper sidebar menu.
**Fix**: Create `AdminSidebar` component matching `Sidebar.tsx` design with proper responsive behavior.

### 2. Tablet Menu Hover (CRITICAL)
**Problem**: Hover on collapsed tablet sidebar only changes CSS width, doesn't update `isCollapsed` state → labels stay hidden.
**Fix**: Add hover state management in `Sidebar.tsx` to properly expand/collapse.

### 3. Remove `Recent` from Sidebar (HIGH)
**Problem**: `recent` field duplicates `history` functionality.
**Fix**: Remove `/recent` from `ROUTE_MAP` and redirect to `/music/history`.

### 4. Rewrite `Continue` System (HIGH)
**Problem**: Current continue watching shows files with watch progress. User wants last watched music/video/reel.
**Fix**: Rewrite to show last played track from `ListenHistory` with proper playback.

### 5. My Files → My Musics (HIGH)
**Problem**: Need upload forms for audio, music videos, reels.
**Fix**: Create upload forms that interact with Telegram bot, add admin toggle.

### 6. Enhanced SEO/Geo for AI Agents (MEDIUM)
**Problem**: Need settings to help AI agents understand the website.
**Fix**: Add AI agent description, structured data, robots.txt settings.

---

## Implementation Order

1. Fix tablet hover in Sidebar
2. Create AdminSidebar component
3. Remove Recent, rewrite Continue
4. Add My Musics upload forms + admin toggle
5. Enhance SEO/Geo settings
6. Test & document