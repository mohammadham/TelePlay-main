# TelePlay Project — Karats (Tasks)

Generated: 2026-09-02

## 📋 Current Task Status

| Priority | Task | Status | Notes |
|----------|------|--------|-------|
| 🔴 Critical | Fix Telegram auth code expiration bug | ✅ **COMPLETED** | Added 1-minute clock tolerance buffer |
| 🔴 Critical | Verify client pool initialization | ✅ Checked | Pool Manager loads from DB correctly |
| 🟡 High | Update all documentation to current code | 🔄 In progress | Creating auth-flow.md |
| 🟡 High | Create sub-agent skills for Telegram bot dev | ✅ Created telegram-bot-expert |
| 🟡 High | Add Android TV navigation improvements | ⏳ Pending | See `android/` directory |
| 🟢 Medium | Review and update `.env.example` template | ⏳ Pending | Add placeholder values documentation |
| 🟢 Medium | Create skill for code review automation | ⏳ Pending | See `code-review` plugin |
| 🟢 Low | Update README with new features | ⏳ Pending | Last updated with v1.0 release |
| 🟢 Low | Add performance benchmarks for streaming | ⏳ Pending | Compare single vs multi-bot download |

## 🔍 Auth Bug Investigation — ROOT CAUSE FOUND & FIXED

### Problem Analysis

The `/login` command generates codes with:
```python
code expires_at = datetime.utcnow() + timedelta(minutes=5)
```

When user enters `/login CODE`, check:
```python
if login_code.expires_at > datetime.utcnow() and not login_code.telegram_id:
```

### Root Cause
**Server Clock Drift**: The server running the backend may have a different clock than the user's Telegram app. Even a 2-3 minute drift caused legitimate codes to show as "expired".

### Fix Applied (Committed: d4c51ac)

**Files Modified:**
1. `backend/app/bot.py` - Two locations:
   - Line ~151: Deep-linked `/start CODE` flow
   - Line ~440: `/login CODE` command flow

2. `backend/app/routers/auth.py` - One location:
   - Line ~168: `/auth/verify-code` API (TV/Web polling endpoint)

**New Logic:**
```python
now = datetime.utcnow()
time_diff = abs((now - login_code.expires_at).total_seconds())

if time_diff <= 60 and not login_code.telegram_id:
    # Code still valid (within 1-min tolerance)
    # Claim the code and succeed
elif login_code.telegram_id:
    # Code already used
elif time_diff > 300:
    # Code expired (>5 min)
else:
    # 1-5 min diff - timing issue warning
```

### Behavior Summary

| Time Diff | Behavior |
|-----------|----------|
| ≤60s | Code accepted (tolerance buffer) |
| 60-300s | Warning message, asks for new code |
| >300s | Clear "expired" message |
| Already used | Clear message as before |

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
- `express-expert` — Express.js (if needed)
- `fastapi-expert` — FastAPI (already the main stack)
- `typescript-expert` — TypeScript code quality
- `react-expert` — React Web UI components
- `docker-expert` — Docker & container orchestration
- `kubernetes-expert` — K8s deployment (if needed)
- `terraform-expert` — Infrastructure as code

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

### Suggested New Documentation:
1. **`docs/auth-flow.md`** — Detailed auth flow with diagrams ⏳ **In Progress**
2. **`docs/troubleshooting.md`** — Common issues & fixes (includes the clock drift fix) ⏳
3. **`docs/api-spec.md`** — Full API endpoint spec ⏳
4. **`docs/migration-guide.md`** — Migration path from v1.x ⏳

## 🎯 Next Immediate Actions

1. ✅ **Fix auth code expiration** — Add clock tolerance buffer **COMPLETED**
2. 📝 **Create `docs/auth-flow.md`** — Document the complete login flow
3. 📝 **Test the fix** — Generate a code, wait slightly, verify it still works
4. 📝 **Update `todo.md`** — Mark completed items