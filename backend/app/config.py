# Configuración central de la app: cada campo puede sobreescribirse con una
# variable de entorno del mismo nombre (en mayúsculas) o desde el archivo .env
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # pydantic-settings lee automáticamente el .env de la raíz del proyecto
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "TX BizFinder"                                   # nombre visible de la app
    database_url: str = "sqlite:///data/texasbizfinder.db"           # SQLite legacy (o postgresql:// para Supabase)
    admin_api_key: str = "admin-dev-key-change-me"                   # API key del header X-API-Key
    max_employees_small_biz: int = 50                                # umbral de "negocio pequeño"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]   # orígenes del frontend en dev
    playwright_timeout_ms: int = 30_000                              # timeout global del análisis Playwright
    playwright_nav_timeout_ms: int = 25_000                          # timeout de navegación de página
    duckduckgo_max_results: int = 8                                  # resultados máximos de la búsqueda DDG
    data_backend: str = "csv"                                        # backend de datos: csv (DuckDB) | sqlite | supabase
    franchise_csv_path: Path = Path("data/raw/texas_franchise_taxpayers.csv")     # CSV masivo del Comptroller
    beverage_csv_path: Path = Path("data/raw/mixed_beverage_receipts.csv")        # CSV de recibos TABC
    processed_csv_path: Path = Path("data/processed/texas_leads_processed.csv")   # leads ya procesados
    processed_duckdb_path: Path = Path("data/processed/texas_leads.duckdb")       # base DuckDB para la API
    serve_frontend: bool = False                                     # ¿servir el build del frontend en el mismo puerto?
    frontend_dist_path: Path = Path("frontend/dist")                 # dónde está ese build

    @property
    def use_csv_backend(self) -> bool:
        # ¿Leer los leads desde CSV/DuckDB? (modo bulk, el habitual)
        return self.data_backend.lower() == "csv"

    @property
    def use_supabase_backend(self) -> bool:
        # ¿Leer los leads desde Supabase/Postgres?
        return self.data_backend.lower() == "supabase"

    @property
    def is_postgres(self) -> bool:
        # ¿La database_url apunta a Postgres?
        return self.database_url.startswith("postgresql")

    @property
    def sqlite_path(self) -> Path:
        # Ruta del archivo SQLite extraída de la URL (sqlite:///data/x.db → data/x.db)
        url = self.database_url.removeprefix("sqlite:///")
        return Path(url)


# Instancia única importada por todo el backend
settings = Settings()
