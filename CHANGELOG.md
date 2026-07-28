# Changelog

## [3.2.0] — 2026-07-27

### Path-based suite (no PC tunnel)

- **Retired Cloudflare Tunnel** to a home PC (`start-cloudflare.ps1`, setup script).
- **Single domain paths:** `www.txbizfinder.com/{app,radar,channel,sentinel,flood,power,map,api}`.
- **Worker router:** `deploy/cloudflare/path-router.worker.js` + `wrangler.toml` (no prefix strip).
- **Nuxt baseURL** on radar/channel/sentinel/flood/power/map: `/radar/` etc. in production; `/` in local dev.
- Suite cards link to paths (same-tab); API public base is `/api` (Oracle via Worker).

## [3.1.0] — 2026-07-27

### Production / TxBizFinder Intelligence

- **No demo on boot:** `python run.py` no longer seeds fixture businesses. Demo is opt-in (`--seed --with-demo-seed` or tests via `process_leads()` stub).
- **Unified data backend:** search, export JSON, export CSV and stats share `data_backend.py` (csv/DuckDB | supabase | sqlite). Export JSON no longer silently used SQLite while search used DuckDB.
- **Strict bulk mode:** `DATA_BACKEND=csv` without DuckDB returns **503** with a clear message (no silent empty/demo fallback).
- **Oracle Free Tier:** `Dockerfile`, `docker-compose.yml`, `deploy/oracle/` (systemd + runbook). DuckDB `threads` + `memory_limit` tunable via env. Playwright optional (`ENABLE_WEBSITE_RESEARCH`).
- **Vercel frontend:** `frontend-v2/vercel.json`; Nitro proxy normalizes trailing slash on `NUXT_API_PROXY_URL`.
- **CORS / health:** Nuxt `:3000` + production domains; `/health` reports `dataReady`, backend, suite id.
- **API:** `sells_alcohol` on `LeadRead`; production refuses default `ADMIN_API_KEY` at startup.

## [2.0.0] — 2026-06-28

### Breaking changes

- **Reescritura completa:** se elimina la app Streamlit v1 (`app/`, `core/`, `utils/`, `setup.sh`).
- **Nueva arquitectura monorepo:** `backend/` (FastAPI), `frontend/` (Vue 3), `scripts/`.
- **Instalación:** `pip install -e ".[dev]"` vía `pyproject.toml` en lugar de solo `requirements.txt`.
- **Arranque:** `python run.py` reemplaza `streamlit run`.
- **Autenticación:** todas las rutas `/api/leads/*` requieren header `X-API-Key`.

### Added

- API REST FastAPI con Pydantic v2 y SQLModel + SQLite.
- UI Vue 3 + TypeScript + Tailwind (`LeadsDashboard.vue`).
- Ingesta desde [Texas Comptroller open data](https://data.texas.gov/resource/9cir-efmm.json) (`scripts/ingest_texas_data.py`).
- Flags CLI: `--limit`, `--keyword`, `--output`, `--no-demo-seed`.
- Calificación modular en `scripts/common/qualification.py`.
- **Análisis de sitios web:** stack, moderno/legacy, antigüedad estimada (`website_analysis.py`).
- **Búsqueda geográfica:** ciudad, ZIP, radio opcional 1–50 millas (`geocoding.py`).
- **Inferencia de industria** desde nombres legales de negocio.
- Endpoint `GET /api/leads/stats` para totales en la UI.
- Export JSON/CSV, marcar leads, upsert con recalificación.
- Script `verify_websites.py` para re-analizar sitios en batch.
- Script `verify_goal.py` para verificación del pipeline.
- Datos geo: `data/geo/texas_locations.json`.
- GitHub Actions: tests, ingesta, procesamiento y build frontend.
- 28+ tests en `backend/tests/`.

### Changed

- Límite de búsqueda API: hasta 500 resultados (antes implícito menor).
- Radio geográfico opcional en UI (checkbox); sin activar, filtra por ciudad exacta.
- Demo seed complementa (no reemplaza) descargas grandes de open data.

### Removed

- Streamlit UI y páginas `1_Search.py`, `2_Results.py`.
- `core/scraper.py`, `core/processor.py`, `core/storage.py`.
- Dependencias v1: Polars, Streamlit, etc.

---

## [1.x] — histórico (Streamlit)

- App Streamlit multipágina para búsqueda de negocios en Texas.
- Scraper y procesador en `core/` con almacenamiento SQLite/Polars.
- Helpers en `utils/` (rate limiting, normalización).