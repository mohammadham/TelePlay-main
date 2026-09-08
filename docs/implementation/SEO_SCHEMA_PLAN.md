# TelePlay — Full SEO & Schema Implementation Plan

## Overview

Add structured data (Schema.org JSON-LD), AI agent description support, robots.txt generation, and comprehensive meta tags for better search engine and AI agent understanding.

## Current State

- **SEO hook** (`useSEO.ts`): Sets basic meta title, description, Open Graph tags
- **No structured data/JSON-LD**: No Schema.org markup exists
- **SEO config** (`admin_seo.py`): Has title_template, description_template, keywords, geo settings
- **No robots.txt generation**: Static file or dynamic generation missing
- **No AI agent description**: No field for AI agents to understand the site

## Implementation Plan

### Phase A: Backend SEO Enhancements

#### A1. Add AI Agent Description to SEOConfig

**File**: `backend/app/models.py`

Add to SEOConfig model:
```python
ai_agent_description: Mapped[str] = mapped_column(Text, default="")
```

**File**: `backend/app/schemas.py`

Add to SEOData schema:
```python
ai_agent_description: str = ""
```

**File**: `backend/app/routers/admin_seo.py`

Add AI description to:
- GET /config response
- PUT /config update (allow updating ai_agent_description)

#### A2. Add robots.txt Generation Endpoint

**File**: `backend/app/routers/admin_seo.py`

Add endpoint: `GET /seo/robots.txt`
- Generates dynamic robots.txt based on SEO settings
- Respects geo restrictions
- Default: allow all / disallow admin paths

#### A3. Add JSON-LD Schema Endpoint

**File**: `backend/app/routers/admin_seo.py`

Add endpoint: `GET /seo/schema`
- Returns JSON-LD structured data for current page
- Parameters: type (site, music_artist, music_album, music_track)
- Dynamic based on SEO config

### Phase B: Frontend SEO Enhancements

#### B1. Update SEO Hook to Include JSON-LD

**File**: `web/src/hooks/useSEO.ts`

Add JSON-LD script injection:
- Generic Site schema
- Music Artist schema (for artist pages)
- Music Album schema (for album pages)
- Music Track schema (for track pages)
- Organization schema (site branding)

#### B2. Add Structured Data Component

**File**: `web/src/components/SEO/StructuredData.tsx` (new)

Component that renders JSON-LD scripts based on page type:
- Site: organization, webApplication, musicPlaylist
- Music pages: individual Track, Artist, Album schemas

#### B3. Update Individual Pages with Schema

**Files to update**:
- `web/src/components/music/MusicHome.tsx` — Organization + MusicPlaylist
- `web/src/components/music/ArtistDetail.tsx` — MusicGroup + Album
- `web/src/components/music/PlaylistView.tsx` — MusicPlaylist
- `web/src/components/music/PlaylistDetail.tsx` — MusicPlaylist
- `web/src/components/music/HistoryView.tsx` — Organization
- `web/src/components/music/SearchView.tsx` — Site
- `web/src/App.tsx` — Site (global)

### Phase C: AI Agent Integration

#### C1. Add AI Description Field to Admin Panel

**File**: `web/src/components/admin/SEOSettingsPanel.tsx`

Add textarea for AI description:
- Title: "AI Agent Description"
- Description: "Description for AI assistants to understand your site"
- Placed after keywords field

#### C2. Create AI Agent Documentation Endpoint

**File**: `backend/app/routers/admin_seo.py`

Add endpoint: `GET /seo/ai-docs`
- Returns structured site documentation
- Includes: purpose, features, API endpoints, data models
- JSON format for easy parsing by AI agents

### Phase D: Robots.txt Generation

#### D1. Add robots.txt to Static Files

**File**: `web/public/robots.txt` (new)

Default content:
```
User-agent: *
Allow: /api/
Allow: /auth/
Allow: /music/
Allow: /admin/
Disallow: /login/
Disallow: /setup/
```

**File**: `backend/app/routers/admin_seo.py`

Add endpoint: `GET /seo/robots.txt` (dynamic override)

### Phase E: Sitewide Schema Updates

#### E1. Update Site Metadata

**File**: `web/src/components/SEO/SiteMetadata.tsx` (new)

Add canonical URLs, alternate language tags, favicon, etc.

#### E2. Add Breadcrumbs Schema

**File**: `web/src/components/music/MusicHome.tsx`

Add breadcrumb structured data.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models.py` | Modify | Add ai_agent_description to SEOConfig |
| `backend/app/schemas.py` | Modify | Add ai_agent_description to SEOData |
| `backend/app/routers/admin_seo.py` | Modify | Add 5 new endpoints |
| `web/src/hooks/useSEO.ts` | Modify | Add JSON-LD injection |
| `web/src/components/SEO/StructuredData.tsx` | Create | JSON-LD component |
| `web/src/components/admin/SEOSettingsPanel.tsx` | Modify | Add AI description field |
| `web/src/components/music/*.tsx` | Modify | Add schema per page |
| `web/public/robots.txt` | Create | Default robots file |
