from collections.abc import Generator
from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from backend.app.config import settings


def _ensure_data_dir() -> None:
    db_path = settings.sqlite_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_data_dir()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    from backend.app.models import Admin, Lead  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate_lead_columns()
    _seed_admin()


def _migrate_lead_columns() -> None:
    additions = {
        "latitude": "REAL",
        "longitude": "REAL",
        "has_website": "INTEGER DEFAULT 0",
        "website_reachable": "INTEGER DEFAULT 0",
        "website_tech_stack": "TEXT",
        "website_antiquity_years": "INTEGER",
        "website_analysis_notes": "TEXT",
    }
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(leads)")).fetchall()
        columns = {row[1] for row in rows}
        for name, sql_type in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN {name} {sql_type}"))
        conn.commit()


def _seed_admin() -> None:
    from backend.app.models.admin import Admin

    with Session(engine) as session:
        existing = session.get(Admin, 1)
        if existing is None:
            session.add(
                Admin(
                    id=1,
                    username="admin",
                    api_key=settings.admin_api_key,
                    is_superuser=True,
                )
            )
            session.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session