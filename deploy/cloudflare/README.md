# Cloudflare — path routing (no tunnel to your PC)

## Model

| Path | App `baseURL` | Upstream |
|------|---------------|----------|
| `/`, `/app` | `/` (finder) | Vercel `txbizfinder-web` |
| `/api/*`, `/health` | n/a (FastAPI) | **Oracle** (`API_ORIGIN`) |
| `/radar/*` | `/radar/` | Vercel PermitRadar |
| `/channel/*` | `/channel/` | Vercel ChannelWatch |
| `/sentinel/*` | `/sentinel/` | Vercel Emissions Sentinel web |
| `/flood/*` | `/flood/` | Vercel FloodGuard |
| `/power/*` | `/power/` | Vercel PowerPulse |
| `/map/*` | `/map/` | Vercel MapHub |

Each Nuxt product sets `app.baseURL` automatically in production (`VERCEL` / `NODE_ENV=production`).  
Local `npm run dev` stays at `/` so ports work as before.

The Worker **does not strip** path prefixes (assets and Nitro routes live under `/radar/_nuxt`, `/radar/api`, …).

## Deploy Worker

```bash
cd texas-biz-finder/deploy/cloudflare
npx wrangler login          # once
npx wrangler deploy
# After Oracle API has public HTTPS:
npx wrangler secret put API_ORIGIN
# paste e.g. https://your-oracle-host
```

Worker → Settings → Domains / Routes:

- `www.txbizfinder.com/*`
- `txbizfinder.com/*`

DNS: proxied (orange cloud) A/CNAME to Worker custom domain, **not** to a home tunnel.

## Retire old tunnel

1. Stop `cloudflared` / old `start-cloudflare.ps1` on the PC.
2. Zero Trust → Tunnels → delete the old tunnel.
3. Delete DNS for `api.`, `radar.`, `flood.`, … that pointed at `*.cfargotunnel.com`.

## Vercel env (per product)

Optional overrides (defaults are already correct in `nuxt.config.ts`):

| Project | `NUXT_APP_BASE_URL` | `NUXT_PUBLIC_APP_URL` |
|---------|---------------------|------------------------|
| finder | `/` (default) | `https://www.txbizfinder.com` |
| radar | `/radar/` | `https://www.txbizfinder.com/radar` |
| channel | `/channel/` | `https://www.txbizfinder.com/channel` |
| sentinel | `/sentinel/` | `https://www.txbizfinder.com/sentinel` |
| flood | `/flood/` | `https://www.txbizfinder.com/flood` |
| power | `/power/` | `https://www.txbizfinder.com/power` |
| map | `/map/` | `https://www.txbizfinder.com/map` |

Finder also needs:

```
NUXT_PUBLIC_ADMIN_API_KEY=<same as Oracle>
NUXT_API_PROXY_URL=https://YOUR-ORACLE-HTTPS-ORIGIN
```

## Redeploy all UIs after baseURL change

Push/redeploy each Vercel project so production builds include the new `baseURL`.  
Until then, `/radar` via Worker may 404 on assets.

## Local force path (optional)

```bash
# e.g. PermitRadar under /radar even in dev
$env:NUXT_APP_BASE_URL="/radar/"
npm run dev
# open http://127.0.0.1:3010/radar/
```
