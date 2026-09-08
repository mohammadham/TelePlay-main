# My Music Section — Implementation Plan

## Overview

Rename /files to /my-music with upload forms for audio, music videos, and reels.

## Current State

- **Backend**: Has `/files` endpoint with File model
- **Frontend**: FileBrowser component displays files with folders, search, drag-drop
- **Music domain**: Has Track, Artist, Album models in models_music.py
- **Create track endpoint**: POST /v1/music/tracks (admin only, requires file_id)

## Implementation Plan

### Phase A: Backend Support

#### A1. Add my-music toggle to AppSetting
- Add `MY_MUSIC_ENABLED` to settings.py TEMPLATE
- Default: "true"
- Admin can enable/disable via /admin/settings

#### A2. Add upload file endpoint to files.py
- POST /files/upload
- Accepts file upload, creates File record
- Returns file_id for use in music endpoints

#### A3. Add public track upload endpoint to music.py
- POST /v1/music/upload
- Accepts file upload, creates Track with media_type
- Returns track_id

### Phase B: Frontend — My Music Page

#### B1. Create MyMusic.tsx component
- List uploaded tracks
- Show audio, music video, reel sections
- Play buttons for each track

#### B2. Create UploadForm.tsx component
- File input for audio/music_video/reel
- Metadata fields: title, artist, album, genre
- Submit to upload endpoint

#### B3. Update Sidebar.tsx
- Change '/files' label to 'My Music'
- Change '/files' route (keep '/files' for now, or migrate later)
- Add upload button to My Music section

### Phase C: Integration

#### C1. Connect upload flow to Telegram bot
- When user uploads, bot sends file to storage channel
- Metadata saved to DB

#### C2. Add admin toggle UI
- In SettingsPanel.tsx
- Check my-music enabled before showing section

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/app/settings.py` | Modify | Add MY_MUSIC_ENABLED setting |
| `backend/app/routers/files.py` | Modify | Add upload endpoint |
| `backend/app/routers/music.py` | Modify | Add upload endpoint |
| `web/src/components/music/MyMusic.tsx` | Create | List tracks with upload |
| `web/src/components/music/UploadForm.tsx` | Create | Upload form component |
| `web/src/components/Sidebar.tsx` | Modify | Update route label |
| `web/src/components/admin/SettingsPanel.tsx` | Modify | Add toggle |
