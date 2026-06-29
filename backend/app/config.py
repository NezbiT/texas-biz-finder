from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "TexasBizFinder"
    database_url: str = "sqlite:///data/texasbizfinder.db"
    admin_api_key: str = "admin-dev-key-change-me"
    max_employees_small_biz: int = 50
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def sqlite_path(self) -> Path:
        url = self.database_url.removeprefix("sqlite:///")
        return Path(url)


settings = Settings()