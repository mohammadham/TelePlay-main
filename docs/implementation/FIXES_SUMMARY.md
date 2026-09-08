---
name: music-platform-fixes-summary
description: Summary of fixes applied to admin sidebar and music panel issues on feature/music-platform branch
metadata:
  type: project
---

# TelePlay Music Platform Fixes

## Issues Fixed

### 1. Admin Sidebar 404 Errors
**Problem**: Clicking admin sidebar buttons (`/admin/users`, `/admin/files`, etc.) led to 404 pages.
**Root Cause**: `KNOWN_ROUTES` in `App.tsx` only listed `/admin`, `/admin/cache`, `/admin/settings` — missing 8 admin sub-routes.

**Fix**: Added all 9 admin sub-routes to both `KNOWN_ROUTES` and `<Route>` definitions:
- `/admin/users`, `/admin/files`, `/admin/ads`, `/admin/system`
- `/admin/bots`, `/admin/accounts`, `/admin/admins`, `/admin/seo`

**File**: `web/src/App.tsx`

### 2. Admin Tab Not Syncing with URL
**Problem**: Clicking admin sidebar buttons navigated correctly but tab content didn't change — always showed overview.
**Root Cause**: `AdminDashboard.tsx` used local React state for tab selection without reading from URL. Navigation happened via client-side router but component didn't react to route changes.

**Fix**: Added `ROUTE_TAB_MAP` to read initial tab from `location.pathname` on mount, `useEffect` syncs tab on URL changes, and `handleTabChange` navigates to matching URL.

**File**: `web/src/components/admin/AdminDashboard.tsx`

### 3. Music Panel "Something went wrong"
**Problem**: `/music` page crashed with "Something went wrong" error boundary.
**Root Cause**: `useMusicHistory` hook used wrong type `MusicHistoryItem[]` but backend returns `TrackResponse[]` (same shape as `MusicTrack`).

**Fix**: Changed hook return type from `MusicHistoryItem[]` to `MusicTrack[]`.

**File**: `web/src/lib/api.ts` (line ~600)

### 4. Database geo_list Column Missing (500 Error)
**Problem**: `/admin/seo/config` returned 500 error after deployment.
**Root Cause**: `SEOConfig` model added `geo_list` column but existing database tables didn't have it. Old databases worked on first deploy but failed after redeployment due to SQLAlchemy creating new tables from metadata instead of detecting schema.

**Fix**: Added `migrate_seo_config_geo_list()` function to `backend/app/migration.py` that creates the column if missing, called during startup alongside existing migrations.

**File**: `backend/app/migration.py` (lines 187-202), `backend/app/main.py` (line ~98)

## Build Status
- ✅ Vite build passes (1557 modules transformed, 478.73 kB JS)
- ✅ All changes pushed to `feature/music-platform` branch
- ✅ 2 new commits: `8f7650b` (admin routes), `27beace` (history type fix)

## Admin Sub-Routes Now Working
All admin navigation items in `AdminSidebar.tsx` now have matching routes:
- Overview → `/admin`
- Users → `/admin/users`
- Files → `/admin/files`
- Cache → `/admin/cache`
- Ads → `/admin/ads`
- System → `/admin/system`
- Settings → `/admin/settings`
- Bots → `/admin/bots`
- Accounts → `/admin/accounts`
- Admins → `/admin/admins`
- SEO → `/admin/seo`
