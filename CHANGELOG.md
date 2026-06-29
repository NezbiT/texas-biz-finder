# Changelog

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