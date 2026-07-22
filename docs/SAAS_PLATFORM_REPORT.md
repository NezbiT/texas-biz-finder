# TxBizFinder Intelligence — SaaS platform report

Date: 2026-07-21

## Vision

A **Texas situational-awareness SaaS** that competes with slow institutional tools (FEMA portals, siloed agency maps) by being:

- **Faster** for triage (contractors, adjusters, brokers)
- **Layered** (permits + flood + grid + air + emissions + leads)
- **Tiered** (Free → Contractor → Pro → Enterprise)
- **Programmable** (REST + future MCP/CLI like World Monitor)

Not a legal replacement for FEMA determinations or ERCOT operations — a commercial intelligence layer on top of public data.

## What shipped in this pass

| Repo | Changes |
|------|---------|
| floodguard-texas | Live NWS alerts API, hybrid ZIP risk + alert boost, health/suite meta, SaaS docs, UI alert strip |
| powerpulse-texas | ZIP→region lookup (`/api/grid/lookup`), ZIP UI, suite meta/health |
| maphub-texas | `/api/suite/overview` pulse (WorldMonitor-style), health/meta, timeRange on layers, pulse chip UI |
| channelwatch-laporte | `/api/health`, `/api/suite/meta`, suite docs |
| emissions-sentinel | `/v1/suite/meta`, `.env.example`, suite docs |
| permitradar-houston | `/api/health`, `/api/suite/meta`, suite docs |
| texas-biz-finder | Suite ports, SaaS tiers, public data sources catalog, this report |

## Debug results (local)

- FloodGuard `:3013` health ok; NWS returned live TX flood-related alerts; ZIP 77002 hybrid score boosted
- PowerPulse `:3014` health ok; ZIP 77002 → houston via zip3-map
- MapHub `:3015` overview pulse computed with live flood+power probes

## Stack unification (target vs now)

**Now:** Nuxt 4 frontends (most), FastAPI for BizFinder/Sentinel/ingest, MapLibre, demo fallbacks.

**Target:**

1. Shared `@txbiz/suite-meta` package (TS) for envelopes + tiers  
2. Single gateway `api.txbizfinder.com` with API keys + rate limits  
3. Clerk/Supabase Auth for human seats; API keys for machines  
4. Python ingest-only workers; never scrape on request  
5. Postgres/PostGIS primary warehouse (Supabase)  

## Next implementation backlog

See `docs/DATA_SOURCES_PUBLIC.md` and product `docs/SUITE_SAAS.md` files.
