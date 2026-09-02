# TelePlay Project — Karats (Tasks)

Generated: 2026-09-02

## 📋 Current Task Status

| Priority | Task | Status | Notes |
|----------|------|--------|-------|
| 🔴 Critical | Fix Telegram auth code expiration bug | ✅ **COMPLETED** | Added 1-minute clock tolerance buffer |
| 🔴 Critical | Verify client pool initialization | ✅ Checked | Pool Manager loads from DB correctly |
| 🟡 High | Update all documentation to current code | ✅ **COMPLETED** | Created auth-flow.md |
| 🟡 High | Create sub-agent skills for Telegram bot dev | ✅ Created telegram-bot-expert |
| 🟡 High | Add Android TV navigation improvements | ⏳ Pending | See `android/` directory |
| 🟢 Medium | Review and update `.env.example` template | ⏳ Pending | Add placeholder values documentation |
| 🟢 Medium | Create skill for code review automation | ⏳ Pending | See `code-review` plugin |
| 🟢 Low | Update README with new features | ⏳ Pending | Last updated with v1.0 release |
| 🟢 Low | Add performance benchmarks for streaming | ⏳ Pending | Compare single vs multi-bot download |

## 🔧 Backend Fixes Applied

### 1. Telegram Auth Code Clock Drift (d4c51ac)
**Problem:** Server clock drift from user's Telegram app caused legitimate login codes to show as "expired"
**Fix:** Added 1-minute tolerance buffer to all 3 code validation points in:
- `backend/app/bot.py` (deep-linked `/start CODE` and `/login CODE`)
- `backend/app/routers/auth.py` (`/auth/verify-code` API)

**Behavior:** Codes ≤60s diff accepted, >300s marked expired, 1-5min shows warning

### 2. Railway Startup Fix (47a9c85)
**Problem:** `ImportError: cannot import name 'escape_like' from 'app.services'` caused container startup failure
**Fix:** Define `escape_like` function directly in `backend/app/services/__init__.py` to avoid circular import issues during container startup

### 3. Utils Import Fix (475480d)
**Problem:** `ModuleNotFoundError: No module named 'app.services.models'` in `services/utils.py`
**Fix:** Changed relative import from `.models` to `..models` in `backend/app/services/utils.py`

---

## 📁 Documentation Status

### Existing Markdown Files (in project root):
- `README.md` — Project overview & quick start ✅
- `SPEC.md` — Multi-auth system specification ✅
- `KNOWLEDGE.md` — Telegram knowledge base ✅
- `CONTRIBUTING.md` — Contributing guidelines ✅
- `LICENSE` — MIT license ✅

### Docs Directory (`docs/`):
- `ARCHITECTURE.md` — Technical architecture ✅
- `DEPLOYMENT.md` — Deployment guide ✅
- `RELEASING.md` — APK release process ✅
- `SETUP.md` — Setup & usage guide ✅
- `SETUP_FLOW_DIAGRAM.md` — Setup flow diagram ✅
- `TELEGRAM_AUTH_ARCHITECTURE.md` — Telegram auth deep-dive ✅
- **`auth-flow.md`** — **NEW: Comprehensive auth flow with clock drift fix** ✅

### Suggested New Documentation:
1. **`docs/troubleshooting.md`** — Common issues & fixes ⏳
2. **`docs/api-spec.md`** — Full API endpoint spec ⏳
3. **`docs/migration-guide.md`** — Migration path from v1.x ⏳

### Pushed Commits:
- `d4c51ac` — Fix Telegram login code clock drift
- `0968194` — Add comprehensive auth-flow.md documentation with clock drift fix details
- `9dd8fef` — Update todo.md to mark auth bug fix and documentation as completed
- `47a9c85` — Fix Railway startup escape_like import issue
- `475480d` — Fix import in services/utils.py for models

---

## 🎯 Next Immediate Actions

1. ✅ **Fix auth code expiration** — Add clock tolerance buffer **COMPLETED**
2. ✅ **Create auth-flow.md** — Document the complete login flow **COMPLETED**
3. ✅ **Fix Railway startup** — Define escape_like in services/__init__.py **COMPLETED**
4. ✅ **Fix utils.py import** — Correct relative import for models **COMPLETED**
5. 📝 **Test the fixes** — Deploy to Railway and verify
6. 📝 **Android TV improvements** — See `android/` directory
7. 📝 **`.env.example`** — Add placeholder values documentation

## 📦 Skills & Plugins Inventory

### Installed Plugins (user scope):
- `frontend-design` — UI/UX design guidance
- `playwright` — Browser automation & E2E testing
- `code-review` — Automated code review
- `auth0` — Auth0 integration
- `azure` — Azure cloud services
- `terraform` — Infrastructure as code
- `supabase` — Supabase database
- `mongodb` — MongoDB integration
- `security-guidance` — Code security scanning
- `42crunch-api-security-testing` — API security audit & scan

### Available Sub-Agents (from 0xfurai/claude-code-subagents repo):
Full list — 138+ agents covering all major languages and frameworks.

### Key Sub-Agents for TelePlay Project:
- `android-expert` — Android TV/Mobile Kotlin/Compose/ExoPlayer
- `nestjs-expert` — NestJS backend (if needed)
- `typescript-expert` — TypeScript code quality
- `react-expert` — React Web UI components
- `docker-expert` — Docker & container orchestration
- `kubernetes-expert` — K8s deployment (if needed)
- `terraform-expert` — Infrastructure as code

---

## 📦 Skills & Plugins Inventory

### Installed Plugins (user scope):
- `frontend-design` — UI/UX design guidance
- `playwright` — Browser automation & E2E testing
- `code-review` — Automated code review
- `auth0` — Auth0 integration
- `azure` — Azure cloud services
- `terraform` — Infrastructure as code
- `supabase` — Supabase database
- `mongodb` — MongoDB integration
- `security-guidance` — Code security scanning
- `42crunch-api-security-testing` — API security audit & scan

### Available Sub-Agents (from 0xfurai/claude-code-subagents repo):
Full list — 138+ agents covering all major languages and frameworks.

### Key Sub-Agents for TelePlay Project:
- `android-expert` — Android TV/Mobile Kotlin/Compose/ExoPlayer
- `nestjs-expert` — NestJS backend (if needed)
- `typescript-expert` — TypeScript code quality
- `react-expert` — React Web UI components
- `docker-expert` — Docker & container orchestration
- `kubernetes-expert` — K8s deployment (if needed)
- `terraform-expert` — Infrastructure as code

### 🚀 Railway Deployment Ready
All critical fixes applied. Ready for Railway redeploy. Container should now start successfully with:
1. ✅ Auth code tolerance (1-min buffer)
2. ✅ `escape_like` import issue resolved
3. ✅ Utils models import fixed
4. ✅ Comprehensive auth-flow documentation

**Deploy and verify:** Railway auto-detects git pushes → rebuild container → should show startup.success