# Phase 3 Todo List — Pending Tasks

## Completed in Batch 2 ✅
1. ✅ Admin Sidebar Menu — Created AdminSidebar.tsx with responsive behavior
2. ✅ Tablet Menu Hover State — Fixed isIconOnly state logic
3. ✅ Recent/Continue Routes — Removed duplicates, redirected to history
4. ✅ Build Verification — Frontend builds successfully

---

## Pending Tasks

### HIGH Priority

#### Task: My Music Section
- [ ] Rename `/files` to `/my-music` route
- [ ] Create MyMusic component (replace FileBrowser for music content)
- [ ] Add upload form for audio files
- [ ] Add upload form for music videos
- [ ] Add upload form for reels
- [ ] Create backend endpoint: POST /v1/music/upload
- [ ] Add admin toggle: enable/disable my-music feature
- [ ] Store uploads in tracks table with media_type
- [ ] Hide menu item when disabled by admin
- [ ] Test upload flow end-to-end

**Files to create/modify:**
- `web/src/components/music/MyMusic.tsx` (new)
- `backend/app/routers/music.py` (add upload endpoint)
- `backend/app/models_music.py` (verify Track model supports uploads)
- `web/src/components/admin/SettingsPanel.tsx` (add toggle)
- `web/src/components/Sidebar.tsx` (update route)

---

### MEDIUM Priority

#### Task: SEO/Geo Settings for AI Agents
- [ ] Add AI agent description field to SEOConfig model
- [ ] Add structured data (JSON-LD) support
- [ ] Add robots.txt generation from admin settings
- [ ] Add Open Graph meta tags configuration
- [ ] Create admin UI for AI description settings
- [ ] Generate sitemap.xml with proper metadata

**Files to create/modify:**
- `backend/app/models.py` (add AI description field)
- `backend/app/routers/admin_seo.py` (add new endpoints)
- `web/src/components/admin/SEOSettingsPanel.tsx` (add AI fields)
- `web/src/hooks/useSEO.ts` (use dynamic settings)

---

### LOW Priority

#### Task: API Cleanup
- [ ] Deprecate `/files/recent` endpoint
- [ ] Deprecate `/files/continue-watching` endpoint
- [ ] Update TV router if using continue watching
- [ ] Remove from services/utils.py if no longer needed

---

## Testing Checklist

### Sidebar Fixes
- [ ] Desktop: Sidebar shows all items, always open
- [ ] Tablet: Icon strip shows, hover expands sidebar
- [ ] Tablet: Collapse button works
- [ ] Phone: Slide-over menu works
- [ ] Admin: New sidebar shows correct routes
- [ ] Admin: Tablet hover works in admin sidebar

### Route Changes
- [ ] `/recent` redirects to `/music/history`
- [ ] `/continue` redirects to `/music/history`
- [ ] Sidebar shows History but not Recent/Continue
- [ ] MusicHome shows "Recently Played" section

### Build
- [ ] TypeScript compiles without errors
- [ ] Vite build succeeds
- [ ] No console errors in browser

---

## Next Steps

1. Test current changes in production
2. Start Phase 3: My Music section
3. Implement upload forms and backend support
4. Add admin toggle functionality
5. Then proceed to SEO/AI agent settings
