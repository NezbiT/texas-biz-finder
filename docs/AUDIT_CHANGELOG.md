# Audit fix changelog — 2026-07-24

## Critical fixes

### texas-biz-finder
- Timing-safe `X-API-Key` comparison (`hmac.compare_digest`)
- Production/staging rejects insecure default admin keys
- Security response headers middleware
- Explicit CORS allowlist (includes MapHub)
- `GET /api/legal` machine-readable disclaimers (TCPA/CCPA notes)
- Suite meta includes legal + disclaimer

### emissions-sentinel
- New `app/auth.py`; `POST /v1/admin/*` requires `X-API-Key`
- Removed CORS `*` + credentials anti-pattern
- Security headers middleware
- `ADMIN_API_KEY` in `.env.example`
- Suite meta disclaimer + legal notes
- Web UI: correct API base port **8001**; admin key header on POST ingest

### txbizfinder-suite (gateway)
- Optional `GATEWAY_API_KEY` (required when `APP_ENV=production|staging`)
- Restricted CORS via `SUITE_CORS_ORIGIN`
- Security headers
- Block admin upstream proxy without `X-API-Key`
- `GET /v1/legal` aggregate disclaimers
- `.gitignore` added

### Nuxt products (flood, power, maphub, channel, permit)
- `/terms` and `/privacy` pages (EN/ES i18n)
- Nitro `security-headers` plugin
- Flood/Power suite meta: disclaimer + legalPaths

## Not fixed (follow-up)

- Server-side BFF for all admin keys (remove from browser)
- Rate limiting / WAF
- Formal attorney-reviewed contracts
- Stripe billing + tenant isolation
