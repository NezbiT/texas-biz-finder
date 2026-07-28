# Configuración central de la app: cada campo puede sobreescribirse con una
# variable de entorno del mismo nombre (en mayúsculas) o desde el archivo .env
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_cors_origins() -> list[str]:
    """Orígenes seguros por defecto (local Nuxt/Vite + producción Vercel)."""
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://www.txbizfinder.com",
        "https://txbizfinder.com",
        "https://txbizfinder-web.vercel.app",
    ]


class Settings(BaseSettings):
    # pydantic-settings lee automáticamente el .env de la raíz del proyecto
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TX BizFinder"
    # development | staging | production
    app_env: str = "development"
    database_url: str = "sqlite:///data/texasbizfinder.db"
    admin_api_key: str = "admin-dev-key-change-me"
    max_employees_small_biz: int = 50
    cors_origins: list[str] = _default_cors_origins()

    # Website research (Playwright es pesado: en Oracle free tier conviene off)
    enable_website_research: bool = True
    playwright_timeout_ms: int = 30_000
    playwright_nav_timeout_ms: int = 25_000
    duckduckgo_max_results: int = 8

    # Backend de datos: csv (DuckDB bulk) | sqlite | supabase
    data_backend: str = "csv"
    franchise_csv_path: Path = Path("data/raw/texas_franchise_taxpayers.csv")
    beverage_csv_path: Path = Path("data/raw/mixed_beverage_receipts.csv")
    processed_csv_path: Path = Path("data/processed/texas_leads_processed.csv")
    processed_duckdb_path: Path = Path("data/processed/texas_leads.duckdb")

    # OBSOLETO: el frontend se despliega en Vercel (Nuxt SSR), no desde FastAPI
    serve_frontend: bool = False
    frontend_dist_path: Path = Path("frontend/dist")

    # Suite product URLs — path-based under one domain (no subdomains / no PC tunnel)
    suite_www_url: str = "https://www.txbizfinder.com"
    suite_radar_url: str = "https://www.txbizfinder.com/radar"
    suite_channel_url: str = "https://www.txbizfinder.com/channel"
    suite_sentinel_url: str = "https://www.txbizfinder.com/sentinel"

    # Oracle Free Tier / production tuning
    # 1 worker en free tier (Ampere 1 OCPU o VM.Standard.E2.1.Micro)
    uvicorn_workers: int = 1
    # DuckDB threads (1–2 en free tier para no saturar RAM)
    duckdb_threads: int = 2
    duckdb_memory_limit: str = "1GB"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None or value == "":
            return _default_cors_origins()
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return _default_cors_origins()
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        return [str(v).strip() for v in parsed if str(v).strip()]
                except json.JSONDecodeError:
                    pass
            # Comma-separated fallback
            return [part.strip() for part in text.split(",") if part.strip()]
        return _default_cors_origins()

    @property
    def is_production(self) -> bool:
        env = (self.app_env or os.getenv("ENV") or os.getenv("APP_ENV") or "development").lower()
        return env in {"production", "prod", "staging"}

    @property
    def use_csv_backend(self) -> bool:
        return self.data_backend.lower() == "csv"

    @property
    def use_supabase_backend(self) -> bool:
        return self.data_backend.lower() == "supabase"

    @property
    def use_sqlite_backend(self) -> bool:
        return self.data_backend.lower() == "sqlite"

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def sqlite_path(self) -> Path:
        url = self.database_url.removeprefix("sqlite:///")
        return Path(url)


settings = Settings()
