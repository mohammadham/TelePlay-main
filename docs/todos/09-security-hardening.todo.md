# Todo - 09 Security Hardening

- [x] CORS restrict to WEB_BASE_URL only (main.py — dynamic allowed_origins)
- [x] Rate limit POST /api/v1/music/downloads (10/min)
- [x] Rate limit POST /api/v1/video/movies (10/min)
- [x] Security headers: HSTS + CSP + X-Frame-Options + COOP/COEP/CORP (main.py)
- [x] AuditLog model for admin actions (models.py + admin.py)
- [x] Audit log: purge_cache + update_cache_config in admin router
- [ ] Input sanitization on file/folder names (XSS path) — deferred
- [ ] SQL injection audit on ilike queries — deferred (uses ORM parameterized)
- [ ] Test: pytest tests/test_security.py — deferred
