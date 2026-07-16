# Capa de base de datos legacy (SQLite o Postgres/Supabase vía SQLModel):
# crea el engine, migra columnas nuevas, índices de Postgres y el admin inicial.
from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from backend.app.config import settings

# Columnas añadidas DESPUÉS del esquema original — se agregan con ALTER TABLE
# si faltan (migración incremental sin herramienta externa). Versión SQLite:
_SQLITE_LEAD_COLUMN_ADDITIONS: dict[str, str] = {
    "latitude": "REAL",                        # coordenadas para búsqueda por radio
    "longitude": "REAL",
    "has_website": "INTEGER DEFAULT 0",        # SQLite no tiene BOOLEAN (usa 0/1)
    "website_reachable": "INTEGER DEFAULT 0",
    "website_tech_stack": "TEXT",              # stack detectado por el análisis
    "website_antiquity_years": "INTEGER",      # antigüedad estimada del sitio
    "website_analysis_notes": "TEXT",          # resumen del análisis
    "sells_alcohol": "INTEGER DEFAULT 0",      # cruce TABC
    "alcohol_segment": "TEXT",                 # bar / restaurant
    "liquor_receipts_total": "REAL",           # totales de recibos de bebidas
    "wine_receipts_total": "REAL",
    "beer_receipts_total": "REAL",
    "total_receipts_total": "REAL",
}

# Misma lista con los tipos equivalentes de Postgres
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
    """Crea la carpeta data/ para el archivo SQLite (Postgres no la necesita)."""
    if settings.is_postgres:
        return
    db_path = settings.sqlite_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_data_dir()   # se ejecuta al importar el módulo (antes de crear el engine)

# Argumentos del engine según el motor:
_engine_kwargs: dict = {"echo": False}   # echo=True imprimiría todo el SQL (debug)
if settings.is_postgres:
    # pool_pre_ping: verifica la conexión antes de usarla (Supabase corta ociosas)
    _engine_kwargs["pool_pre_ping"] = True
else:
    # SQLite: permitir uso desde múltiples hilos de FastAPI
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **_engine_kwargs)


def init_db() -> None:
    """Inicializa el esquema al arrancar la app (idempotente)."""
    # Importar los modelos registra sus tablas en SQLModel.metadata
    from backend.app.models import Admin, Lead, WebsiteAnalysis  # noqa: F401

    SQLModel.metadata.create_all(engine)   # CREATE TABLE IF NOT EXISTS de todo
    _migrate_lead_columns()                # añade columnas nuevas si faltan
    if settings.is_postgres:
        _create_postgres_indexes()         # índices de búsqueda (solo Postgres)
    _seed_admin()                          # asegura el usuario admin con su API key


def _existing_lead_columns(conn) -> set[str]:
    """Nombres de las columnas actuales de `leads` (según el motor)."""
    if settings.is_postgres:
        # Postgres: catálogo information_schema
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'leads'"
            )
        ).fetchall()
        return {row[0] for row in rows}

    # SQLite: PRAGMA table_info (la columna 1 es el nombre)
    rows = conn.execute(text("PRAGMA table_info(leads)")).fetchall()
    return {row[1] for row in rows}


def _migrate_lead_columns() -> None:
    """ALTER TABLE para cada columna del diccionario que aún no exista."""
    with engine.connect() as conn:
        columns = _existing_lead_columns(conn)
        if not columns:
            return   # la tabla no existe todavía (la creará create_all)
        additions = (
            _POSTGRES_LEAD_COLUMN_ADDITIONS if settings.is_postgres else _SQLITE_LEAD_COLUMN_ADDITIONS
        )
        for name, sql_type in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN {name} {sql_type}"))
        conn.commit()


def _create_postgres_indexes() -> None:
    """Índices que aceleran los filtros de búsqueda y el orden por score."""
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_leads_qualified ON leads (is_qualified)",
        "CREATE INDEX IF NOT EXISTS idx_leads_small_biz ON leads (is_small_business)",
        "CREATE INDEX IF NOT EXISTS idx_leads_sells_alcohol ON leads (sells_alcohol)",
        "CREATE INDEX IF NOT EXISTS idx_leads_zip ON leads (zip_code)",
        "CREATE INDEX IF NOT EXISTS idx_leads_city ON leads (city)",
        "CREATE INDEX IF NOT EXISTS idx_leads_name ON leads (name)",
        "CREATE INDEX IF NOT EXISTS idx_leads_industry ON leads (industry)",
        (
            # índice compuesto que calza con el ORDER BY del listado
            "CREATE INDEX IF NOT EXISTS idx_leads_score_sort ON leads "
            "(qualification_score DESC, total_receipts_total DESC NULLS LAST, name)"
        ),
    ]
    with engine.connect() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.commit()


def _seed_admin() -> None:
    """Crea el admin id=1 con la API key de settings si aún no existe."""
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
    """Dependencia de FastAPI: una Session por request, cerrada al terminar."""
    with Session(engine) as session:
        yield session
