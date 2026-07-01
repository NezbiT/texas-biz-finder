<p align="center">
  <img src="docs/banner-v4.svg" alt="TX BizFinder" width="920" />
</p>

<p align="center">
  <img src="docs/logo.svg" alt="TX BizFinder logo" width="72" height="72" />
</p>

# TX BizFinder

**https://www.txbizfinder.com**

Monorepo para encontrar y calificar **pequeños negocios en Texas** — con o sin sitio web moderno, presencia en redes, y venta de alcohol (TABC).

**Stack:** DuckDB + CSV (bulk) · SQLite + SQLModel (legacy) · FastAPI · Vue 3 + TypeScript + Tailwind. Costo mínimo, local o VPS.

> Pipeline masivo (3.36M registros), cruce TABC, API paginada con DuckDB, UI bilingüe EN/ES, modo prod de un solo puerto.

## Novedades recientes

| Área | Detalle |
|------|---------|
| **Bulk pipeline** | Descarga ~3.36M franchise taxpayers + ~3.78M mixed beverage receipts |
| **TABC / alcohol** | Cruce por `taxpayer_number` → `sells_alcohol`, receipts, segmento bar/restaurant |
| **Lectura rápida** | CSV (archivo) + DuckDB (API) + JSON (stats) — sin escanear millones por request |
| **Paginación** | 50 leads por página en UI y API (`limit` + `offset`) |
| **UI** | Dark/light, logo TX BizFinder, i18n **EN** por defecto + toggle **ES** |
| **Prod local** | `python run.py --prod` — API + frontend en un puerto |
| **Dominio** | Cloudflare → `www.txbizfinder.com` |
| **Filtros** | Calificados, industria, ciudad/ZIP, radio, **solo venden alcohol (TABC)** |
| **Website research** | DuckDuckGo + Playwright por lead (1 análisis a la vez) |

### Cifras tras `bulk_pipeline` (producción local)

| Métrica | Cantidad |
|---------|----------|
| Franchise taxpayers (Texas) | 3,359,302 |
| Leads procesados / calificados | 536,156 |
| Con venta de alcohol (TABC) | 22,599 |

## Estructura del proyecto

```
TexasBizFinder/                 # repo folder (interno)
├── docs/
│   ├── logo.svg                # Logo TX BizFinder
│   └── banner-v4.svg           # README banner
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── leads.py        # search paginado, stats, export
│   │   │   └── website_research.py
│   │   └── services/
│   │       ├── csv_lead_store.py   # Lectura DuckDB (API rápida)
│   │       ├── lead_search.py      # SQLite fallback
│   │       ├── playwright_analyzer.py
│   │       └── duckduckgo_search.py
│   └── tests/                  # 41 tests
├── frontend/
│   └── src/
│       ├── components/         # LeadsDashboard, AppLogo, LocaleToggle, ThemeToggle
│       ├── composables/        # useI18n, useTheme
│       └── i18n/               # en.ts, es.ts
├── data/
│   ├── raw/                    # CSV masivos (gitignored, generados)
│   ├── processed/              # CSV + DuckDB + bulk_stats.json (gitignored)
│   └── geo/texas_locations.json
├── scripts/
│   ├── bulk_pipeline.py        # download-franchise | download-beverage | process | all
│   ├── ingest_texas_data.py    # Ingesta ligera (demo / staging)
│   └── common/
│       ├── socrata_bulk.py
│       └── lead_materialize.py # CSV → DuckDB tipado
└── run.py
```

## Requisitos

- Python 3.11+
- Node.js 18+ (frontend)
- ~2 GB disco libre para CSV masivos (opcional)

## Setup rápido

```bash
cd TexasBizFinder
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
playwright install chromium   # solo si usas website research

cd frontend && npm install && cd ..
copy .env.example .env
```

## Acceso remoto con Tailscale (gratis)

Deja la app en tu PC y ábrela desde el celular u otra máquina en tu tailnet:

```powershell
.\start-tailscale.ps1
# En el otro dispositivo: http://<tu-ip-tailscale>:5173
```

## Arrancar

### Producción local (recomendado — un solo puerto)

```bash
python run.py --prod --build    # primera vez o si cambiaste UI
python run.py --prod --no-seed  # uso diario
```

→ http://127.0.0.1:8000 (UI + API)

### Desarrollo (hot reload UI)

**Backend:**

```bash
python run.py --no-seed
```

**Frontend:**

```bash
cd frontend
npm run dev
```

- UI: http://127.0.0.1:5173  
- API: http://127.0.0.1:8000  

## Cloudflare / dominio

Dominio: **www.txbizfinder.com** (cuenta Cloudflare)

### Opción A — Tunnel desde tu PC (sin VPS, costo ~$0)

Expone tu instancia local con HTTPS y PWA instalable. Ideal mientras el DuckDB vive en tu máquina.

**Requisitos:** dominio `txbizfinder.com` en Cloudflare, `cloudflared` instalado.

```powershell
# 1) Instalar cloudflared (una vez)
winget install Cloudflare.cloudflared

# 2) Configurar tunnel (una vez; abre el navegador para login)
.\scripts\setup-cloudflare-tunnel.ps1

# 3) Arrancar prod + tunnel (cada vez que quieras publicar)
.\start-cloudflare.ps1
# o reconstruir frontend antes:
.\start-cloudflare.ps1 -Rebuild
```

En el dashboard Cloudflare:

- **SSL/TLS** → Full (strict)
- **Rules** → redirect opcional `txbizfinder.com` → `https://www.txbizfinder.com`

La PC debe permanecer encendida con el script en ejecución.

### Opción B — VPS (siempre encendido)

1. `python run.py --prod --build` en el servidor
2. Cloudflare DNS → IP del VPS (proxy naranja ON)
3. SSL: Full (strict)
4. Sube `data/processed/texas_leads.duckdb` al servidor

## Pipeline masivo (3.36M negocios)

Descarga, cruza con TABC y materializa DuckDB para la API.

```bash
# Todo el flujo (~15–20 min según red/disco)
python -m scripts.bulk_pipeline all

# O por pasos
python -m scripts.bulk_pipeline download-franchise
python -m scripts.bulk_pipeline download-beverage
python -m scripts.bulk_pipeline process
```

### Archivos generados

| Archivo | Formato | Uso |
|---------|---------|-----|
| `data/raw/texas_franchise_taxpayers.csv` | CSV | 3.36M contribuyentes activos |
| `data/raw/mixed_beverage_receipts.csv` | CSV | Receipts mensuales TABC |
| `data/processed/texas_leads_processed.csv` | CSV | Respaldo / export |
| `data/processed/texas_leads.duckdb` | DuckDB | **Lectura API** (rápida) |
| `data/processed/bulk_stats.json` | JSON | Totales instantáneos en UI |

### Formato de datos (¿CSV o JSON?)

- **Millones de filas tabulares → CSV** (más compacto y rápido que JSON)
- **Metadatos pequeños → JSON** (`bulk_stats.json`, checkpoints)
- **API en runtime → DuckDB** (materializado desde CSV al procesar)

Configura en `.env`:

```
DATA_BACKEND=csv
PROCESSED_DUCKDB_PATH=data/processed/texas_leads.duckdb
```

Con `DATA_BACKEND=sqlite` vuelves al demo SQLite (~3k leads de staging).

## Ingesta ligera (demo / staging)

```bash
python -m scripts.ingest_texas_data --limit 2000
python -m scripts.ingest_texas_data --limit 500 --keyword AUTO --output data/staging/kw_AUTO.json
python -m scripts.process_leads --staging data/staging/texas_businesses.json
```

## API

Header requerido:

```
X-API-Key: admin-dev-key-change-me
```

### Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/leads/stats` | Total Texas, calificados, venden alcohol |
| GET | `/api/leads` | Búsqueda **paginada** (`LeadSearchPage`) |
| GET | `/api/leads/export/csv` | Exportar filtros actuales |
| POST | `/api/leads/{id}/website-search` | DuckDuckGo |
| POST | `/api/leads/{id}/website-analyze` | Playwright (1 a la vez) |

### Parámetros de búsqueda

| Parámetro | Descripción |
|-----------|-------------|
| `q` | Texto libre |
| `city` / `zip_code` | Ubicación |
| `radius_miles` | Radio 1–50 mi (SQLite + geocoding) |
| `industry` | Industria inferida |
| `qualified_only` | Solo calificados (default: `true`) |
| `small_business_only` | Excluir corporaciones grandes (default: `true`) |
| `sells_alcohol_only` | Solo negocios con receipts TABC |
| `limit` | Por página, default **50** (máx. 500) |
| `offset` | Paginación |

Respuesta paginada:

```json
{
  "items": [...],
  "total": 536156,
  "limit": 50,
  "offset": 0,
  "page": 1,
  "pages": 10724
}
```

Ejemplo — solo bares/restaurantes con alcohol:

```bash
curl -H "X-API-Key: admin-dev-key-change-me" \
  "http://127.0.0.1:8000/api/leads?sells_alcohol_only=true&limit=50"
```

## UI (Vue)

- **Texas businesses** — total en header (desde `bulk_stats.json` / DuckDB)
- **Paginación** — 50 leads, Previous / Next
- **Idioma** — EN por defecto, toggle ES
- **Tema** — dark / light
- **Filtro TABC** — “Sell alcohol only”
- **Research website** — panel DuckDuckGo + Playwright por lead

## Investigación web (Playwright)

```bash
pip install -e ".[dev]"
playwright install chromium
```

Flujo: Search DuckDuckGo → elegir URL → Analyze → Download HTML report.

## Lógica de calificación (bulk)

Un lead **procesado** cumple:

- Activo en SOS / franchise tax
- No es corporación grande (heurística por nombre)
- Tiene señal de valor: **venta de alcohol TABC**, industria inferida, o NAICS

Score ejemplo: alcohol TABC = 0.85, keyword industria = 0.55, NAICS = 0.45.

## Tests

```bash
pytest backend/tests -q
```

41 tests — API, bulk pipeline, prod mode, website research, Playwright unit.

## Licencia

Uso personal / interno. Datos de Texas sujetos a [data.texas.gov](https://data.texas.gov/).