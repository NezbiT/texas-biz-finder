# TxBizFinder — Suite hub product

Core lead product + marketing shell for **TxBizFinder Intelligence**.

## Suite map (local ports)

| Product | Port | Layer |
|---------|------|-------|
| TxBizFinder API | 8000 | finder |
| PermitRadar | 3010 | radar |
| ChannelWatch | 3011 | channel |
| Emissions Sentinel API | 8001 | sentinel |
| FloodGuard | 3013 | flood |
| PowerPulse | 3014 | power |
| MapHub | 3015 | all |

## SaaS vision

Compete on **Texas operational intelligence** for:

1. **Contractors** — permits + flood/grid context before bidding  
2. **Insurers / MGAs** — flood + industrial + ambient risk overlays (not a FEMA replacement; a faster triage layer)  
3. **Brokers / lead gen** — qualified small businesses without modern web  

### Suggested tiers

| Tier | Price band (target) | Entitlements |
|------|---------------------|---------------|
| Free | $0 | Demo maps, limited ZIP lookups, delayed data |
| Contractor | $29–79/mo | Saved ZIPs, permit alerts, CSV export |
| Pro | $199–499/mo | API keys, FEMA/NFHL, history, webhooks |
| Enterprise | custom | SSO, bulk geocode, white-label MapHub, SLA |

## Unified stack target

- **UI:** Nuxt 4 + MapLibre + Tailwind + i18n (EN/ES)  
- **Reads:** Nitro or FastAPI with identical `{ meta: { product, asOf, source, demo } }` envelopes  
- **Writes:** Python ingest CLIs + Actions (never scrape on page load)  
- **Auth:** Clerk/Supabase Auth + API keys per tier  
- **Gateway:** MapHub + `api.txbizfinder.com` rate-limited reverse proxy  

## Programmatic access (WorldMonitor pattern)

Build next:

1. OpenAPI per product + suite gateway  
2. MCP server for agents (`tools/list` public, `tools/call` keyed)  
3. CLI `npx txbiz` for ZIP risk, permit search, lead export  
4. SDKs (TS + Python) thin clients over the gateway  

## Auth for leads API today

`X-API-Key` on `/api/leads/*` — rotate `ADMIN_API_KEY` before public tunnel.
