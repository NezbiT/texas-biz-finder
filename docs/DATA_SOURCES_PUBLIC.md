# Public APIs & open data — TxBizFinder Intelligence

**Principle:** official API / open data → bulk CSV/geospatial → scrape HTML.  
Never scrape inside a user HTTP request; always workers (CLI + cron/Actions).

Keys marked **free** usually require registration only.  
Roadmap PDF: `docs/TxBizFinder_Data_Roadmap.pdf` · generator: `docs/generate_data_roadmap_pdf.py`.

**Confidence levels (UI):**

| Level | Color | Examples |
|-------|-------|----------|
| Official | green | FEMA NFHL, NWS alert, OpenFEMA, EIA series |
| Agency open data | blue | Socrata city permits, data.texas.gov, USGS |
| Best-effort scrape | amber | Houston xlsx, TCEQ HTML |
| Modeled / demo | gray | synthetic scores, IsolationForest labels, ZIP3 map |

---

## 3.1 Flood / weather / hydro

| Source | Auth | Use | Suite status | Validation |
|--------|------|-----|--------------|------------|
| [NWS api.weather.gov](https://www.weather.gov/documentation/services-web-api) | Free + User-Agent | Active TX alerts | FloodGuard live | High |
| [FEMA NFHL ArcGIS](https://hazards.fema.gov/femaportal/wps/portal/NFHLWMS) | Free | Official flood zones | Flood Pro path | Very high (official) |
| [OpenFEMA](https://www.fema.gov/about/openfema/data-sets) | Free REST | NFIP claims, disasters | PENDING | High (federal) |
| [USGS NWIS](https://waterservices.usgs.gov/) | Free | Gauges / streamflow | PENDING | High |
| [NOAA CO-OPS](https://tidesandcurrents.noaa.gov/api/) | Free | Coastal water levels TX | ChannelWatch live partial | High |
| [Open-Meteo](https://open-meteo.com/) | Free | Weather + modeled AQI | ChannelWatch live | Medium-high |
| NOAA ATLAS 14 | Free/bulk | Design precipitation | PENDING | High (engineering) |

---

## 3.2 Air / emissions / energy

| Source | Auth | Use | Suite status | Validation |
|--------|------|-----|--------------|------------|
| [EPA AirNow](https://docs.airnowapi.org/) | Free key | Real-time AQI | Optional Channel/Sentinel | High |
| [OpenAQ API](https://openaq.org/) | Free key | Ambient monitors | Sentinel connector | High |
| [EPA CAMPD](https://www.epa.gov/power-sector/cam-api-portal) | Free key | Plant CEMS | Partial/demo Sentinel | High |
| [EIA Open Data](https://www.eia.gov/opendata/) | Free key | Gen / demand / fuels | PENDING Power/Sentinel | Very high |
| [EPA GHGRP](https://www.epa.gov/ghgreporting) | Bulk CSV | GHG facilities | Demo/bulk path | High |
| [EPA eGRID](https://www.epa.gov/egrid) | Bulk | Emission rates | PENDING | High |
| [EPA TRI / Envirofacts](https://www.epa.gov/toxics-release-inventory-tri-program) | API/bulk | Toxic releases | Demo Channel | High |
| [TCEQ open GIS](https://www.tceq.texas.gov/gis) | Free services | TX inventories | Partial | High (state) |
| ERCOT public | Varies/ToS | TX grid | Demo PowerPulse | Medium (ToS) |

---

## 3.3 Permits / business / geo

| Source | Auth | Use | Suite status | Validation |
|--------|------|-----|--------------|------------|
| [data.texas.gov (Socrata)](https://data.texas.gov/) | Free | Franchise tax ~3.3M | BizFinder bulk | High |
| TABC mixed beverage | Free Socrata | Alcohol receipts | BizFinder join | High |
| [Austin SODA](https://data.austintexas.gov/) | Free (+token) | Building permits | ingest texas | High |
| [Dallas Open Data](https://www.dallasopendata.com/) | Free | Permits | ingest texas | High |
| [San Antonio CKAN](https://data.sanantonio.gov/) | Free | Permits | ingest texas | High |
| [US Census Geocoder](https://geocoding.geo.census.gov/) | Free | Batch lat/lon | PermitRadar | High |
| Zippopotam / Census | Free | ZIP geocode | MapHub/Channel | Medium |
| OpenFreeMap tiles | Free | Map style | All map apps | Medium |

### How to get free keys

| Key env | Register |
|---------|----------|
| `EIA_API_KEY` | https://www.eia.gov/opendata/register.php |
| `AIRNOW_API_KEY` | https://docs.airnowapi.org/ |
| `OPENAQ_API_KEY` | https://openaq.org/ |
| `CAMPD_API_KEY` | https://www.epa.gov/power-sector/cam-api-portal |
| Socrata app token (optional) | data.texas.gov / city portals |
| NWS | No key — descriptive User-Agent with contact |
| FEMA NFHL | Public ArcGIS FeatureServer/MapServer |

---

## 4. Where to scrape (and where not to)

Scrape only when: (a) no API/open data, (b) owner publishes public data, (c) robots.txt / rate limits / ToS respected, (d) cached in warehouse, (e) fallback exists.

### 4.1 Justified / already in use

| Source | Origin | Product | Notes |
|--------|--------|---------|-------|
| Houston Permitting Center weekly xlsx | https://www.houstonpermittingcenter.org/sold-permits-search | PermitRadar ingest CLI + weekly Actions | HTML links to xlsx; openpyxl/xlrd; Census geocode; Supabase upsert. Risk: markup change / DNS. Mitigate: flexible selectors + failure alerts. |
| TCEQ CAMS daily / EER emission events | TCEQ sites (URLs in ChannelWatch `sources.yaml`) | ChannelWatch FastAPI collectors | Best-effort + fixture fallback. Prefer TCEQ GIS/open data when available. |
| DuckDuckGo HTML + Playwright | DDG + deep analysis | TxBizFinder website research (1 concurrent job) | Aggressive rate limit; internal lead-gen only. |
| ERCOT public dashboards | Public demand/conditions pages | PowerPulse PENDING | Review ToS first; prefer EIA series as national/regional proxy. |

### 4.2 Possible (low value or high risk) — case by case

- TCEQ TAMIS (planned in Sentinel) — prefer open data
- Small TX city portals without SODA/CKAN — weekly xlsx/PDF
- Wayback Machine API (do not scrape UI) for domain history
- Third-party commercial listings (Yelp, etc.) — **AVOID** (ToS + legal)

### 4.3 Do not scrape (use official API/bulk)

- FEMA flood maps / MSC → NFHL MapServer/FeatureServer
- EPA AQS / CAMPD / TRI → official APIs and bulk
- EIA → Open Data API
- NWS → api.weather.gov (never weather.gov HTML)
- data.texas.gov / Socrata cities → SODA JSON, not HTML tables
- Private insurer sites or paywalled MLS → out of scope

### 4.4 Scraper implementation pattern

- Worker Python CLI (`python -m ingest …`) + cron/Actions — never in browser request
- Idempotency: `ingest_runs` table with file/URL checksum
- Timeouts, exponential retries, honest User-Agent with contact
- Store raw in `data/raw/` and processed in Postgres
- Fixture/demo fallback on failure (Channel EER, several connectors)
- Monitoring: `data_runs` / `last_success` visible in About or `/api/meta/runs`
- Legal: robots.txt, no overload, no CAPTCHA/paywall bypass

---

## 5. Validation checklist (per data layer)

Document in UI **About** and **meta API** for each source:

- Source name + official URL + last update (`asOf`)
- Cadence (real-time / daily / weekly / annual)
- License or ToS summary
- Transformed fields vs raw
- Flag `demo: true` when synthetic or illustrative
- Scraper error rates over 7d
- Spot-check: sample of 20 records vs official portal

---

## 6. Product → priority source map

| Product | Priority API / open data | Scrape |
|---------|--------------------------|--------|
| FloodGuard | FEMA NFHL + NWS + USGS + OpenFEMA | Only if missing local layer not exposed |
| PowerPulse | EIA + ERCOT public (ToS) + NOAA heat | ERCOT HTML fallback only |
| ChannelWatch | Open-Meteo + NOAA + AirNow + TCEQ GIS | CAMS/EER HTML current |
| Emissions Sentinel | EIA + CAMPD + OpenAQ + GHGRP/eGRID bulk | Avoid ad-hoc scrapes |
| PermitRadar | SODA/CKAN multi-city + Houston xlsx | Houston xlsx (already) |
| TxBizFinder | data.texas.gov + TABC Socrata | DDG/Playwright research |
| MapHub | Proxy suite APIs (does not invent data) | N/A |

### Implementation order (recommended)

1. **NWS + Open-Meteo + NOAA** — zero-cost live weather risk (partially done)
2. **EIA + AirNow free keys** — energy + AQI credibility
3. **FEMA NFHL WMS/FeatureServer** — insurer-grade flood polygons
4. **OpenFEMA NFIP** — claims density by ZIP
5. **CAMPD + GHGRP bulk** — industrial underwriting overlays
6. **Unified `api.txbizfinder.com` gateway** — one key, tiered rate limits

---

## Legal

Always label non-authoritative layers. Flood/insurance decisions require official FEMA products and licensed professionals. Grid and emissions data are informational only — not ERCOT/TCEQ/EPA operational guidance.
