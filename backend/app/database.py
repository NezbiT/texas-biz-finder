from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from backend.app.config import settings

_SQLITE_LEAD_COLUMN_ADDITIONS: dict[str, str] = {
    "latitude": "REAL",
    "longitude": "REAL",
    "has_website": "INTEGER DEFAULT 0",
    "website_reachable": "INTEGER DEFAULT 0",
    "website_tech_stack": "TEXT",
    "website_antiquity_years": "INTEGER",
    "website_analysis_notes": "TEXT",
    "sells_alcohol": "INTEGER DEFAULT 0",
    "alcohol_segment": "TEXT",
    "liquor_receipts_total": "REAL",
    "wine_receipts_total": "REAL",
    "beer_receipts_total": "REAL",
    "total_receipts_total": "REAL",
}

_POSTGRES_LEAD_COLUMN_ADDITIONS: dict[str, str] = {
    "latitude": "DOUBLE PRECISION",
    "longitude": "DOUBLE PRECISION",
    "has_website": "BOOLEAN DEFAULT FALSE",
    "website_reachable": "BOOLEAN DEFAULT FALSE",
    "website_tech_stack": "TEXT",
    "website_antiquity_years": "INTEGER",
    "website_analysis_notes": "TEXT",
    "sells_alcohol": "BOOLEAN DEFAULT FALSE",
    "alcohol_segment": "TEXT",
    "liquor_receipts_total": "DOUBLE PRECISION",
    "wine_receipts_total": "DOUBLE PRECISION",
    "beer_receipts_total": "DOUBLE PRECISION",
    "total_receipts_total": "DOUBLE PRECISION",
}


def _ensure_data_dir() -> None:
    if settings.is_postgres:
        return
    db_path = settings.sqlite_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_data_dir()

_engine_kwargs: dict = {"echo": False}
if settings.is_postgres:
    _engine_kwargs["pool_pre_ping"] = True
else:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_kwargs)


def init_db() -> None:
    from backend.app.models import Admin, Lead, WebsiteAnalysis  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate_lead_columns()
    if settings.is_postgres:
        _create_postgres_indexes()
    _seed_admin()


def _existing_lead_columns(conn) -> set[str]:
    if settings.is_postgres:
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'leads'"
            )
        ).fetchall()
        return {row[0] for row in rows}

    rows = conn.execute(text("PRAGMA table_info(leads)")).fetchall()
    return {row[1] for row in rows}


def _migrate_lead_columns() -> None:
    with engine.connect() as conn:
        columns = _existing_lead_columns(conn)
        if not columns:
            return
        additions = (
            _POSTGRES_LEAD_COLUMN_ADDITIONS if settings.is_postgres else _SQLITE_LEAD_COLUMN_ADDITIONS
        )
        for name, sql_type in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN {name} {sql_type}"))
        conn.commit()


def _create_postgres_indexes() -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_leads_qualified ON leads (is_qualified)",
        "CREATE INDEX IF NOT EXISTS idx_leads_small_biz ON leads (is_small_business)",
        "CREATE INDEX IF NOT EXISTS idx_leads_sells_alcohol ON leads (sells_alcohol)",
        "CREATE INDEX IF NOT EXISTS idx_leads_zip ON leads (zip_code)",
        "CREATE INDEX IF NOT EXISTS idx_leads_city ON leads (city)",
        "CREATE INDEX IF NOT EXISTS idx_leads_name ON leads (name)",
        "CREATE INDEX IF NOT EXISTS idx_leads_industry ON leads (industry)",
        (
            "CREATE INDEX IF NOT EXISTS idx_leads_score_sort ON leads "
            "(qualification_score DESC, total_receipts_total DESC NULLS LAST, name)"
        ),
    ]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
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