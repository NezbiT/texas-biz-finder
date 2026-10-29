# Render — FastAPI backend

The production API runs on **Render**. The Nuxt UI stays on **Vercel**.
Cloudflare Worker `txbizfinder-path-router` sends `/api/*` and `/health` to Render.

## Why the first deploy usually dies

| Symptom | Cause | Fix |
|---------|--------|-----|
| Service crashes on boot | `APP_ENV=production` + default `ADMIN_API_KEY=admin-dev-key-change-me` | Set a long random `ADMIN_API_KEY` (Blueprint `generateValue`) |
| Build timeout / OOM | `playwright install` or DuckDB bulk files in the image | Do **not** install Chromium. `ENABLE_WEBSITE_RESEARCH=false` |
| Health 200 but no leads | `DATA_BACKEND=csv` and `data/processed/texas_leads.duckdb` missing | Start with `DATA_BACKEND=sqlite`, then upload DuckDB to a disk |
| `/api` on www.txbizfinder.com → 503 | Worker secret `API_ORIGIN` empty | `npx wrangler secret put API_ORIGIN` = `https://<service>.onrender.com` |
| Vercel build of the monorepo fails | Root Directory is the repo root (Python) | Set Root Directory to `frontend-v2` |

Render injects `PORT`. The start command **must** bind `0.0.0.0:$PORT`.

## Blueprint

`render.yaml` at the repo root.

1. [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**
2. Select `NezbiT/texas-biz-finder`
3. Apply. Copy the public URL, e.g. `https://texas-biz-finder.onrender.com`

If the service already exists, point it at this repo and paste the **Start Command** / env vars from `render.yaml`.

## After Render is up

```bash
curl -sS https://YOUR-SERVICE.onrender.com/health
```

Expect `"status":"ok"` (sqlite) or `"degraded"` until DuckDB is mounted.

Then:

```bash
cd deploy/cloudflare
npx wrangler secret put API_ORIGIN
# paste https://YOUR-SERVICE.onrender.com   (no trailing slash)
```

Vercel (finder, Root Directory `frontend-v2`):

```
NUXT_API_PROXY_URL=https://YOUR-SERVICE.onrender.com
NUXT_PUBLIC_ADMIN_API_KEY=<same as Render ADMIN_API_KEY>
```

Redeploy the Worker and the Vercel project after env changes.
