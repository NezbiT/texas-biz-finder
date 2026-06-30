from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "TexasBizFinder"
    database_url: str = "sqlite:///data/texasbizfinder.db"
    admin_api_key: str = "admin-dev-key-change-me"
    max_employees_small_biz: int = 50
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    playwright_timeout_ms: int = 30_000
    playwright_nav_timeout_ms: int = 25_000
    duckduckgo_max_results: int = 8
    data_backend: str = "csv"
    franchise_csv_path: Path = Path("data/raw/texas_franchise_taxpayers.csv")
    beverage_csv_path: Path = Path("data/raw/mixed_beverage_receipts.csv")
    processed_csv_path: Path = Path("data/processed/texas_leads_processed.csv")
    processed_duckdb_path: Path = Path("data/processed/texas_leads.duckdb")

    @property
    def use_csv_backend(self) -> bool:
        return self.data_backend.lower() == "csv"

    @property
    def sqlite_path(self) -> Path:
        url = self.database_url.removeprefix("sqlite:///")
        return Path(url)


settings = Settings()