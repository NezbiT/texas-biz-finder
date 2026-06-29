# TexasBizFinder v2

Monorepo para encontrar y calificar **pequeños negocios en Texas** que probablemente no tienen sitio web moderno ni presencia activa en Facebook o Instagram.

**Stack:** SQLite + SQLModel · FastAPI + Pydantic v2 · Vue 3 + TypeScript + Tailwind. Costo cero, todo local.

> **v2** reemplaza la app Streamlit de v1 (`app/`, `core/scraper.py`) por un monorepo con API REST, UI Vue y scripts de ingesta desde datos abiertos de Texas.

## Novedades en v2

| Área | v1 (Streamlit) | v2 |
|------|----------------|-----|
| UI | Streamlit multipágina | Vue 3 + Tailwind (`LeadsDashboard`) |
| Backend | Lógica en `core/` | FastAPI con auth por API key |
| Datos | Scraper Polars | [data.texas.gov](https://data.texas.gov/resource/9cir-efmm.json) + demo seed |
| Búsqueda | Texto básico | Ciudad, ZIP, radio opcional (1–50 mi), industria |
| Web | Detección simple | Stack, moderno/legacy, antigüedad estimada |
| Export | CSV en UI | JSON/CSV vía API + marcar/upsert leads |

## Estructura del proyecto

```
TexasBizFinder/
├── backend/                    # API FastAPI
│   ├── app/
│   │   ├── main.py             # Punto de entrada
│   │   ├── config.py           # SQLite, admin key, CORS
│   │   ├── database.py         # Engine SQLModel + seed admin
│   │   ├── models/             # Lead, Admin
│   │   ├── schemas/            # Pydantic v2
│   │   ├── routers/leads.py    # search, export, stats, upsert
│   │   ├── services/           # lead_search (geo + filtros)
│   │   └── core/auth.py        # Superusuario único
│   └── tests/                  # 28+ tests
├── frontend/                   # Vue 3 + TS + Tailwind
│   └── src/components/LeadsDashboard.vue
├── scripts/
│   ├── ingest_texas_data.py    # Descarga data.texas.gov
│   ├── process_leads.py        # Califica y persiste
│   ├── verify_websites.py      # Re-analiza sitios en DB
│   └── common/
│       ├── data_sources.py
│       ├── qualification.py
│       ├── geocoding.py
│       └── website_analysis.py
├── data/geo/texas_locations.json   # Coordenadas ciudad/ZIP (TX)
├── run.py                      # Un comando: seed + API
└── .github/workflows/verify-leads.yml
```

## Requisitos

- Python 3.11+
- Node.js 18+ (solo para el frontend)

## Setup rápido

```bash
cd TexasBizFinder

# Entorno Python
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e ".[dev]"

# Frontend (opcional)
cd frontend && npm install && cd ..
```

Copia variables de entorno:

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
```

## Un solo comando (backend + datos)

```bash
python run.py
```

Esto:

1. Crea SQLite en `data/texasbizfinder.db`
2. Ingesta datos públicos de Texas (API + demo seed)
3. Califica leads (sin web moderna + sin redes activas)
4. Arranca la API en `http://127.0.0.1:8000`

### Frontend en desarrollo

Con el backend corriendo, en otra terminal:

```bash
cd frontend
npm run dev
```

Abre `http://localhost:5173` — proxy hacia la API.

**Windows (PowerShell con execution policy restrictiva):**

```powershell
node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173
```

## Scripts de ingesta

```bash
# Descarga desde data.texas.gov (por defecto 50 registros + demo seed)
python -m scripts.ingest_texas_data

# Más registros
python -m scripts.ingest_texas_data --limit 2000

# Filtrar por palabra en el nombre legal (AUTO, REPAIR, MECHANIC, AUTOMOTIVE…)
python -m scripts.ingest_texas_data --limit 500 --keyword AUTO --output data/staging/kw_AUTO.json

# Calificar y guardar en SQLite
python -m scripts.process_leads --staging data/staging/texas_businesses.json

# Re-analizar sitios web ya guardados
python -m scripts.verify_websites
python -m scripts.verify_websites --no-fetch   # solo heurísticas offline
```

## API (superusuario único)

Todas las rutas de leads requieren:

```
X-API-Key: admin-dev-key-change-me
```

Configura en `.env`:

```
ADMIN_API_KEY=tu-clave-secreta
DATABASE_URL=sqlite:///data/texasbizfinder.db
```

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/leads/stats` | Totales (total, qualified, small_business) |
| GET | `/api/leads` | Buscar/filtrar leads |
| GET | `/api/leads/export/json` | Exportar JSON |
| GET | `/api/leads/export/csv` | Exportar CSV |
| PATCH | `/api/leads/{id}/mark` | Marcar/desmarcar lead |
| POST | `/api/leads/upsert` | Crear/actualizar y recalificar |

### Parámetros de búsqueda

| Parámetro | Descripción |
|-----------|-------------|
| `q` | Texto libre (nombre, ciudad, industria) |
| `city` | Ciudad (con geocoding) |
| `zip_code` | Código postal |
| `radius_miles` | Radio 1–50 mi desde ciudad/ZIP (opcional) |
| `county` | Condado |
| `industry` | Industria inferida o registrada |
| `qualified_only` | Solo leads calificados (default: `true`) |
| `small_business_only` | Solo ≤ 50 empleados (default: `true`) |
| `limit` | Máx. resultados 1–500 (default: 50) |
| `offset` | Paginación |

Ejemplos:

```bash
# Por ciudad
curl -H "X-API-Key: admin-dev-key-change-me" \
  "http://127.0.0.1:8000/api/leads?city=Austin&qualified_only=false"

# Radio 25 mi desde ZIP
curl -H "X-API-Key: admin-dev-key-change-me" \
  "http://127.0.0.1:8000/api/leads?zip_code=78701&radius_miles=25&limit=100"

# Industria + texto
curl -H "X-API-Key: admin-dev-key-change-me" \
  "http://127.0.0.1:8000/api/leads?q=auto&industry=automotive"
```

## Lógica de calificación

Un lead **calificado** cumple:

- **Pequeño negocio** (≤ 50 empleados por defecto; grandes empresas excluidas)
- **Sin** sitio web moderno (HTTPS, sin dominios legacy/placeholder)
- **Sin** Facebook ni Instagram activos (URLs reales de perfil)

### Análisis de sitio web

`scripts/common/website_analysis.py` detecta:

- Si existe URL y si responde HTTP
- Stack tecnológico (WordPress, Wix, React, etc.)
- Si el sitio es moderno o legacy
- Antigüedad estimada en años (`website_antiquity_years`)

Campos en el modelo `Lead`: `has_website`, `website_reachable`, `has_modern_website`, `website_tech_stack`, `website_antiquity_years`, `website_analysis_notes`.

### Búsqueda geográfica

`scripts/common/geocoding.py` usa `data/geo/texas_locations.json` para resolver ciudad/ZIP y filtrar por distancia haversine. En la UI, el radio es **opcional** (checkbox); sin radio, filtra por ciudad exacta.

## Tests

```bash
pytest backend/tests -q
```

## GitHub Actions

`.github/workflows/verify-leads.yml` ejecuta en cada push/PR:

- Tests unitarios e integración
- Ingesta stub + procesamiento de leads
- Build del frontend

## Migración desde v1

La v1 usaba Streamlit con `requirements.txt` y carpetas `app/`, `core/`, `utils/`. La v2 es un reemplazo completo:

1. Clona/actualiza el repo
2. `pip install -e ".[dev]"` (reemplaza `pip install -r requirements.txt`)
3. `python run.py` en lugar de `streamlit run app/main.py`
4. Usa la UI Vue o la API REST

Ver [CHANGELOG.md](CHANGELOG.md) para el detalle de cambios.

## Licencia

Uso personal / interno. Datos de Texas sujetos a las políticas de [data.texas.gov](https://data.texas.gov/).