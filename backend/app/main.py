# Punto de entrada de la API FastAPI de TX BizFinder:
# monta CORS, los routers de leads/research y (opcional) el frontend estático.
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routers import leads_router, website_research_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Arranque/cierre de la app: valida config e inicializa la base."""
    # Guardia de configuración: el backend supabase exige una URL de Postgres
    if settings.use_supabase_backend and not settings.is_postgres:
        raise RuntimeError(
            "DATA_BACKEND=supabase requires DATABASE_URL=postgresql://... (Supabase connection string)"
        )
    init_db()   # crea tablas si no existen (SQLite/Postgres)
    yield       # ← aquí corre la app; después del yield iría el cleanup


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# CORS: orígenes explícitos (nunca "*" con credentials)
_cors = list(settings.cors_origins) + [
    "http://127.0.0.1:3015",
    "http://localhost:3015",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(_cors)),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "Accept"],
    max_age=600,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=()",
    )
    return response

# Los dos grupos de endpoints: /api/leads/* y /api/leads/*/website-*
app.include_router(leads_router)
app.include_router(website_research_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Ping de salud (lo usan los scripts de arranque y el hosting)."""
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/legal")
def legal_notices() -> dict:
    """Machine-readable legal notices for UI footers and API clients (not legal advice)."""
    return {
        "product": "texas-biz-finder",
        "asOf": "2026-07-24",
        "jurisdiction": "Texas, United States",
        "notLegalAdvice": True,
        "disclaimers": {
            "general": (
                "Informational only. Derived from public filings and optional web research. "
                "Not a credit, compliance, or background check. Not insurance or legal advice."
            ),
            "contact": (
                "If you contact leads, you must comply with TCPA, CAN-SPAM, and applicable "
                "state solicitation rules. Obtain consent where required."
            ),
            "privacy": (
                "We may process IP addresses, API keys, saved search criteria, and account "
                "emails. California residents may have CCPA rights. See /api/legal and product Privacy page."
            ),
            "dataSources": (
                "Public open data (e.g. data.texas.gov). Website research is best-effort and "
                "may be incomplete or outdated. Do not scrape third-party commercial listings."
            ),
        },
        "termsUrl": "/legal/terms",
        "privacyUrl": "/legal/privacy",
        "contact": "legal@txbizfinder.com",
    }


@app.get("/api/suite/meta")
def suite_meta() -> dict:
    """Suite metadata + data catalog (roadmap §3.3 / §6)."""
    return {
        "suite": "txbizfinder-intelligence",
        "product": "texas-biz-finder",
        "productName": "TxBizFinder",
        "domain": "finder.txbizfinder.com",
        "apiVersion": "1.0.1",
        "mapHubLayer": "finder",
        "defaultPort": 8000,
        "legal": "/api/legal",
        "disclaimer": (
            "Leads from public filings + best-effort web research. Not a credit check. "
            "Comply with TCPA/CAN-SPAM when contacting."
        ),
        "dataPath": {
            "now": [
                "data.texas.gov franchise tax bulk",
                "TABC mixed beverage Socrata join",
                "DuckDuckGo + Playwright website research",
            ],
            "next": ["Wayback Machine API for domain history", "bulk geocode enrichment"],
        },
        "dataSources": [
            {
                "id": "data-texas-gov",
                "name": "data.texas.gov (Socrata)",
                "url": "https://data.texas.gov/",
                "auth": "free",
                "use": "Franchise tax ~3.3M",
                "status": "live",
                "validation": "high",
                "confidence": "agency_open_data",
                "cadence": "periodic_bulk",
                "demo": False,
            },
            {
                "id": "tabc-mixed-beverage",
                "name": "TABC mixed beverage",
                "url": "https://data.texas.gov/",
                "auth": "free_socrata",
                "use": "Alcohol receipts join",
                "status": "live",
                "validation": "high",
                "confidence": "agency_open_data",
                "cadence": "periodic",
                "demo": False,
            },
            {
                "id": "ddg-playwright",
                "name": "DuckDuckGo HTML + Playwright",
                "url": None,
                "auth": "public_html",
                "use": "Lead website discovery / deep analysis",
                "status": "live",
                "validation": "medium",
                "confidence": "best_effort_scrape",
                "cadence": "on_demand",
                "demo": False,
                "notes": "1 concurrent job; aggressive rate limit; internal lead-gen only",
            },
            {
                "id": "wayback",
                "name": "Wayback Machine API",
                "url": "https://archive.org/help/wayback_api.php",
                "auth": "free_api",
                "use": "Domain history",
                "status": "partial",
                "validation": "medium",
                "confidence": "agency_open_data",
                "cadence": "on_demand",
                "demo": False,
                "notes": "Use API; do not scrape UI",
            },
        ],
        "scrapingPolicy": {
            "justified": [
                "DuckDuckGo HTML for website discovery (internal lead-gen)",
                "Playwright deep analysis of candidate sites (1 concurrent job)",
            ],
            "possible": ["Wayback API for domain history (not UI scrape)"],
            "forbidden": [
                "data.texas.gov HTML tables (use SODA JSON)",
                "Yelp / commercial listings (ToS + legal)",
                "CAPTCHA / paywall bypass",
            ],
        },
    }


def _mount_frontend(dist: Path) -> None:
    """Sirve el build de Vite desde el mismo proceso (modo prod de un puerto)."""
    # Los assets con hash (JS/CSS) se sirven como estáticos normales
    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    index_html = dist / "index.html"

    @app.get("/", include_in_schema=False)
    async def frontend_root() -> FileResponse:
        # La raíz siempre devuelve el index.html de la SPA
        if not index_html.is_file():
            raise HTTPException(status_code=404, detail="frontend dist missing index.html")
        return FileResponse(index_html)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_spa(full_path: str) -> FileResponse:
        # Catch-all de la SPA: nunca interceptar la API ni /health
        if full_path.startswith("api") or full_path in ("health",):
            raise HTTPException(status_code=404)
        # Archivo real (favicon, manifest…) → servirlo tal cual
        candidate = dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        # Cualquier otra ruta → index.html (el router del frontend resuelve)
        if index_html.is_file():
            return FileResponse(index_html)
        raise HTTPException(status_code=404, detail="frontend dist not found")


# Solo se monta si SERVE_FRONTEND=true y el build existe
if settings.serve_frontend:
    dist_path = settings.frontend_dist_path.resolve()
    if dist_path.is_dir():
        _mount_frontend(dist_path)
