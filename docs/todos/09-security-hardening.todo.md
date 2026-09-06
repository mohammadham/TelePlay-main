# Todo - 09 Security Hardening

- [x] bot admin_only_guard (bot.py:105)
- [x] require_admin (auth.py:128)
- [x] JWT auth_version logout-all (auth.py:118)
- [x] Fernet encryption for api_hash/session (encryption.py)
- [ ] CORS restrict to WEB_BASE_URL only (main.py — current allows localhost)
- [ ] Rate limit POST /api/v1/music/downloads (no limit currently)
- [ ] Rate limit POST /api/v1/video/movies (no limit currently)
- [ ] Input sanitization on file/folder names (XSS path)
- [ ] SQL injection audit on all ilike queries (use parameterized)
- [ ] Helmet-like security headers: X-Frame-Options, CSP, HSTS
- [ ] Audit log for admin actions (create_movie, purge_cache, etc.)
- [ ] Test: pytest tests/test_security.py (mock login bypass attempts)
