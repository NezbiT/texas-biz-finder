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
    if settings.use_supabase_backend and not settings.is_postgres:
        raise RuntimeError(
            "DATA_BACKEND=supabase requires DATABASE_URL=postgresql://... (Supabase connection string)"
        )
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads_router)
app.include_router(website_research_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


def _mount_frontend(dist: Path) -> None:
    """Serve Vite build output from the same process as the API (single-port prod)."""
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
        if full_path.startswith("api") or full_path == "health":
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