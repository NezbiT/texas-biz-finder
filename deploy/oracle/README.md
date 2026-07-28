# Deploy TX BizFinder API on Oracle Cloud Free Tier

Target: **Always Free Ampere A1** (recommended) or **VM.Standard.E2.1.Micro**.

Frontend + suite paths stay on **Cloudflare Worker + Vercel**. This host only runs FastAPI + DuckDB.

## Architecture

```
Browser
  → https://www.txbizfinder.com/...     Cloudflare Worker (path router)
       /app, /                 → Vercel finder
       /radar, /flood, …       → other Vercel apps
       /api/*, /health         → Oracle FastAPI (this host)  ← API_ORIGIN
```

No Cloudflare Tunnel to a home PC.

## 1. Prepare data

```bash
python -m scripts.bulk_pipeline all
# Copy data/processed/texas_leads.duckdb (+ bulk_stats.json) to the VM
```

## 2. VM + Docker

See previous steps: Ubuntu, Docker, security list **TCP 22** + **TCP 443** (or 8000 behind Caddy).

Prefer **Caddy or nginx** with Let's Encrypt on the VM so `API_ORIGIN` is HTTPS, e.g.:

```
https://api-origin.example.com   # or the public IP with a cert
```

Worker env `API_ORIGIN` must be that HTTPS base (no path).

## 3. Run API

```bash
cp .env.example .env
# APP_ENV=production
# ADMIN_API_KEY=<strong>
# DATA_BACKEND=csv
# ENABLE_WEBSITE_RESEARCH=false
# CORS_ORIGINS=["https://www.txbizfinder.com","https://txbizfinder.com"]

docker compose up -d --build
curl -s http://127.0.0.1:8000/health
```

## 4. Wire the edge

```bash
cd deploy/cloudflare
npx wrangler secret put API_ORIGIN
# paste https://YOUR-ORACLE-HTTPS-ORIGIN
npx wrangler deploy
```

Public clients use **`https://www.txbizfinder.com/api/...`** (not `api.txbizfinder.com`).

## 5. Vercel finder env

| Variable | Value |
|----------|--------|
| `NUXT_PUBLIC_ADMIN_API_KEY` | same as `ADMIN_API_KEY` |
| `NUXT_API_PROXY_URL` | same Oracle HTTPS origin (SSR server-side) |

## Free-tier tuning

| Host | Workers | DuckDB mem | Playwright |
|------|---------|------------|------------|
| Ampere 2 OCPU / 12 GB | 1–2 | 2–4 GB | optional |
| E2.1.Micro 1 GB | 1 | 256–512 MB | **off** |

## Smoke

```bash
export KEY='your-admin-key'
curl -s https://www.txbizfinder.com/health
curl -s -H "X-API-Key: $KEY" 'https://www.txbizfinder.com/api/leads/stats'
```
