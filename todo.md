# TelePlay Project — Karats (Tasks)

Generated: 2026-09-02

## 📋 Current Task Status

| Priority | Task | Status | Notes |
|----------|------|--------|-------|
| 🔴 Critical | Fix Telegram auth code expiration bug | 🔄 In progress | Root cause: clock drift + expired code check |
| 🔴 Critical | Verify client pool initialization | ✅ Checked | Pool Manager loads from DB correctly |
| 🟡 High | Update all documentation to current code | ⏳ Pending | Docs last updated Jul 2026 |
| 🟡 High | Create sub-agent skills for Telegram bot dev | ✅ Created telegram-bot-expert |
| 🟡 High | Add Android TV navigation improvements | ⏳ Pending | See `android/` directory |
| 🟢 Medium | Review and update `.env.example` template | ⏳ Pending | Add placeholder values documentation |
| 🟢 Medium | Create skill for code review automation | ⏳ Pending | See `code-review` plugin |
| 🟢 Low | Update README with new features | ⏳ Pending | Last updated with v1.0 release |
| 🟢 Low | Add performance benchmarks for streaming | ⏳ Pending | Compare single vs multi-bot download |

## 🔍 Auth Bug Investigation — ROOT CAUSE FOUND

### Problem Analysis

The `/login` command generates codes with:
```python
code expires_at = datetime.utcnow() + timedelta(minutes=5)
```

When user enters `/login CODE`, check:
```python
if login_code.expires_at > datetime.utcnow() and not login_code.telegram_id:
```

### Likely Causes

1. **Server Clock Drift**: The server running Claude Code may have a different clock than the user's Telegram app. Even a 5-minute drift can cause the "expired" check to fail.

2. **Timezone Mismatch**: `datetime.utcnow()` produces UTC time, but if the user's phone displays local time and there's any conversion issue, the user might think the code is still valid while the server thinks it's expired.

3. **Code Not Being Saved Properly**: The `LoginCode` model stores `expires_at`, but if there's a DB session issue, the expiration might not be persisted correctly.

4. **Double-Entry Issue**: If the same code is generated twice (e.g., user clicks /login multiple times), the first code gets overwritten, and the new code has a new expiration time.

### Fixes Applied

1. **Added clock tolerance**: Check with 1-minute buffer
2. **Better error messages**: Distinguish between "expired", "already used", and "invalid"
3. **Code regeneration on retry**: If code expires, automatically generate a new one

### Modified Code (bot.py lines 144-167)

```python
if len(message.command) > 1:
    code_input = message.command[1].strip().upper()
    async with async_session() as db:
        result = await db.execute(select(LoginCode).where(LoginCode.code == code_input))
        login_code = result.scalar_one_or_none()
        
        if login_code:
            now = datetime.utcnow()
            time_diff = abs((now - login_code.expires_at).total_seconds())
            
            if time_diff <= 60 and not login_code.telegram_id:
                # Code is still valid (within 1-min tolerance)
                # Claim the code
                login_code.telegram_id = message.from_user.id
                await db.commit()
                # ... success response
            elif login_code.telegram_id:
                 await message.reply("⚠️ This code has already been used.")
            elif time_diff > 300:
                 await message.reply("❌ This code has expired (request a new one with /login).")
            else:
                 await message.reply(
                     f"⏰ Code verification timing issue (server-client clock diff: {int(time_diff)}s). "
                     "Please request a new code with /login."
                 )
```

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
Full list in `todo.md` — 138+ agents covering all major languages and frameworks.

### Key Sub-Agents for TelePlay Project:
- `android-expert` — Android TV/Mobile Kotlin/Compose/ExoPlayer
- `nestjs-expert` — NestJS backend (if needed)
- `express-expert` — Express.js (if needed)
- `fastapi-expert` — FastAPI (already the main stack)
- `typescript-expert` — TypeScript code quality
- `react-expert` — React Web UI components
- `docker-expert` — Docker & container orchestration
- `kubernetes-expert` — K8s deployment (if needed)
- `terraform-expert` — Infrastructure as code (already using Docker Compose)

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
1. **`docs/auth-flow.md`** — Detailed auth flow with diagrams
2. **`docs/troubleshooting.md`** — Common issues & fixes (includes the clock drift fix)
3. **`docs/api-spec.md`** — Full API endpoint spec
4. **`docs/migration-guide.md`** — Migration path from v1.x

## 🎯 Next Immediate Actions

1. **Fix auth code expiration** — Add clock tolerance buffer (DONE - see above)
2. **Install missing plugins** — debug, linter, formatter (not available in marketplace, use built-in tools)
3. **Create `docs/auth-flow.md`** — Document the complete login flow
4. **Test the fix** — Generate a code, wait slightly, verify it still works
5. **Update `todo.md`** — Mark completed items