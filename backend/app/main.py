# Punto de entrada de la API FastAPI de TX BizFinder:
# monta CORS, los routers de leads/research y health de suite.
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routers import leads_router, website_research_router
from backend.app.services import csv_lead_store, data_backend


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Arranque/cierre de la app: valida config e inicializa la base."""
    if settings.use_supabase_backend and not settings.is_postgres:
        raise RuntimeError(
            "DATA_BACKEND=supabase requires DATABASE_URL=postgresql://... "
            "(use the pooler URI on port 6543 when available)"
        )
    if settings.is_production:
        key = (settings.admin_api_key or "").strip()
        if not key or key in {
            "",
            "admin-dev-key-change-me",
            "changeme",
            "secret",
            "password",
        }:
            raise RuntimeError(
                "APP_ENV=production requires a strong ADMIN_API_KEY "
                "(not the default admin-dev-key-change-me)"
            )
    init_db()
    yield
    csv_lead_store.close_connection()


app = FastAPI(
    title=settings.app_name,
    version="3.1.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# CORS: orígenes explícitos (nunca "*" con credentials)
_cors = list(settings.cors_origins) + [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:3015",
    "http://localhost:3015",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://www.txbizfinder.com",
    "https://txbizfinder.com",
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


app.include_router(leads_router)
app.include_router(website_research_router)


@app.get("/health")
def health() -> dict:
    """Ping de salud + estado del backend de datos (suite smoke / Oracle)."""
    ready = data_backend.data_ready()
    duckdb_path = settings.processed_duckdb_path
    return {
        "status": "ok" if ready or settings.use_sqlite_backend or settings.use_supabase_backend else "degraded",
        "app": settings.app_name,
        "product": "texas-biz-finder",
        "suite": "txbizfinder-intelligence",
        "apiVersion": "1.0.1",
        "env": settings.app_env,
        "dataBackend": settings.data_backend,
        "dataReady": ready,
        "websiteResearchEnabled": settings.enable_website_research,
        "duckdb": {
            "path": str(duckdb_path),
            "exists": duckdb_path.exists(),
            "threads": settings.duckdb_threads,
            "memoryLimit": settings.duckdb_memory_limit,
        },
    }


@app.get("/api/legal")
def legal_notices() -> dict:
    """Machine-readable legal notices for UI footers and API clients (not legal advice)."""
    return {
        "product": "texas-biz-finder",
        "asOf": "2026-07-27",
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
    """Suite metadata + data catalog (TxBizFinder Intelligence)."""
    return {
        "suite": "txbizfinder-intelligence",
        "product": "texas-biz-finder",
        "productName": "TxBizFinder",
        "domain": "www.txbizfinder.com",
        "paths": {
            "home": "/",
            "app": "/app",
            "api": "/api",
            "radar": "/radar",
            "channel": "/channel",
            "sentinel": "/sentinel",
            "flood": "/flood",
            "power": "/power",
            "map": "/map",
        },
        "apiBasePath": "/api",
        "apiVersion": "1.0.1",
        "mapHubLayer": "finder",
        "defaultPort": 8000,
        "legal": "/api/legal",
        "health": "/health",
        "disclaimer": (
            "Leads from public filings + best-effort web research. Not a credit check. "
            "Comply with TCPA/CAN-SPAM when contacting."
        ),
        "dataBackend": settings.data_backend,
        "dataReady": data_backend.data_ready(),
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
                "status": "live" if settings.enable_website_research else "disabled",
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
    """Legacy single-port mode (optional). Prefer Nuxt on Vercel."""
    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    index_html = dist / "index.html"

    @app.get("/", include_in_schema=False)
    async def frontend_root() -> FileResponse:
        if not index_html.is_file():
            raise HTTPException(status_code=404, detail="frontend dist missing index.html")
        return FileResponse(index_html)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api") or full_path in ("health", "docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404)
        candidate = dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        if index_html.is_file():
            return FileResponse(index_html)
        raise HTTPException(status_code=404, detail="frontend dist not found")


if settings.serve_frontend:
    dist_path = settings.frontend_dist_path.resolve()
    if dist_path.is_dir():
        _mount_frontend(dist_path)
