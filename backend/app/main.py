# Punto de entrada de la API FastAPI de TX BizFinder:
# monta CORS, los routers de leads/research y (opcional) el frontend estático.
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
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

# CORS: permite que el frontend en otro puerto/origen llame a esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Los dos grupos de endpoints: /api/leads/* y /api/leads/*/website-*
app.include_router(leads_router)
app.include_router(website_research_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Ping de salud (lo usan los scripts de arranque y el hosting)."""
    return {"status": "ok", "app": settings.app_name}


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
        if full_path.startswith("api") or full_path == "health":
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
