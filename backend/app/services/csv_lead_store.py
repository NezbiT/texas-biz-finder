"""Búsqueda rápida de leads en modo bulk: metadatos JSON + CSV + DuckDB.

La regla de oro: la API NUNCA escanea los CSVs de millones de filas por
request — lee la tabla tipada de DuckDB (construida por el bulk_pipeline) y
los totales salen de un JSON de metadatos precalculado.
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb   # base analítica embebida (columnar, lecturas muy rápidas)

from backend.app.config import settings
from backend.app.schemas.lead import LeadRead, LeadSearchPage, LeadSearchParams

# TTLs de los cachés en memoria (los datos solo cambian al correr el pipeline)
STATS_CACHE_TTL_SECONDS = 300    # 5 min para los totales del header
COUNT_CACHE_TTL_SECONDS = 600    # 10 min para los COUNT de cada combinación de filtros
_stats_cache: dict[str, Any] = {"loaded_at": 0.0, "data": None, "signature": ""}
_count_cache: dict[str, tuple[float, int]] = {}   # clave → (cuándo, total)
_count_cache_signature: str = ""                  # firma de archivos del caché actual


def _sql_path(path: Path) -> str:
    # Ruta absoluta con barras / (DuckDB en Windows no acepta backslashes)
    return str(path.resolve()).replace("\\", "/")


def _processed_duckdb_ready() -> bool:
    # ¿Existe la base DuckDB tipada generada por el pipeline?
    return settings.processed_duckdb_path.exists()


def processed_data_ready() -> bool:
    """La API solo lee la DuckDB tipada (construida desde CSV en `process`)."""
    return _processed_duckdb_ready()


# Conexión única reutilizada (abrir DuckDB por request sería un desperdicio)
_duckdb_conn: duckdb.DuckDBPyConnection | None = None


def close_connection() -> None:
    """Cierra la conexión (tests / recarga tras regenerar el pipeline)."""
    global _duckdb_conn
    if _duckdb_conn is not None:
        _duckdb_conn.close()
        _duckdb_conn = None
    _invalidate_count_cache()   # datos nuevos → conteos viejos inválidos


def _invalidate_count_cache() -> None:
    # Vacía el caché de conteos y resetea su firma
    global _count_cache_signature
    _count_cache.clear()
    _count_cache_signature = ""


def _count_cache_key(where_sql: str, values: list[Any]) -> str:
    # La clave del caché es el WHERE exacto + sus valores
    return f"{where_sql}|{values!r}"


def _get_cached_count(cache_key: str, signature: str) -> int | None:
    """Devuelve el total cacheado si la firma de archivos no cambió y no expiró."""
    global _count_cache_signature
    # Si los archivos cambiaron (pipeline re-corrido), invalidar todo
    if _count_cache_signature != signature:
        _invalidate_count_cache()
        _count_cache_signature = signature

    entry = _count_cache.get(cache_key)
    if entry is None:
        return None

    loaded_at, total = entry
    # Expiración por TTL (monotonic = inmune a cambios del reloj del sistema)
    if time.monotonic() - loaded_at >= COUNT_CACHE_TTL_SECONDS:
        _count_cache.pop(cache_key, None)
        return None
    return total


def _set_cached_count(cache_key: str, total: int) -> None:
    # Guarda el total con su marca de tiempo
    _count_cache[cache_key] = (time.monotonic(), total)


def _connection() -> duckdb.DuckDBPyConnection:
    """Conexión perezosa: se abre la primera vez y se reutiliza siempre."""
    global _duckdb_conn
    if _duckdb_conn is not None:
        return _duckdb_conn
    if _processed_duckdb_ready():
        # read_only: la API jamás escribe; permite lecturas concurrentes seguras
        _duckdb_conn = duckdb.connect(str(settings.processed_duckdb_path.resolve()), read_only=True)
    else:
        _duckdb_conn = duckdb.connect()   # en memoria (fallback para leer CSV)
    return _duckdb_conn


def _uses_typed_leads_table() -> bool:
    # ¿Leemos la tabla `leads` tipada (rápida) o el CSV crudo (fallback)?
    return _processed_duckdb_ready()


def _leads_source() -> str:
    """El FROM de las queries: tabla tipada o read_csv_auto del CSV procesado."""
    if _uses_typed_leads_table():
        return "leads"
    csv_path = _sql_path(settings.processed_csv_path)
    # all_varchar: sin adivinar tipos (los booleanos se normalizan aparte)
    return f"read_csv_auto('{csv_path}', header=true, all_varchar=true)"


def _bool_filter(column: str) -> str:
    """Filtro booleano portable entre la tabla tipada y el CSV all_varchar."""
    if _uses_typed_leads_table():
        return f"{column} = true"                     # booleano real
    # CSV: el "true" puede venir como texto en varias formas
    return f"LOWER(TRIM(CAST({column} AS VARCHAR))) IN ('true', '1', 't', 'yes')"


def _stats_metadata_path() -> Path:
    # El pipeline escribe los totales aquí al terminar (bulk_stats.json)
    return settings.processed_csv_path.parent / "bulk_stats.json"


def _file_signature() -> str:
    """Huella de los archivos de datos (mtime+tamaño) — cambia si el pipeline corre."""
    parts: list[str] = []
    for path in (
        settings.processed_duckdb_path,
        settings.processed_csv_path,
        settings.franchise_csv_path,
        _stats_metadata_path(),
    ):
        if path.exists():
            stat = path.stat()
            parts.append(f"{path}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def _load_metadata_stats() -> dict[str, int] | None:
    """Lee los totales precalculados del bulk_stats.json (si existe y es válido)."""
    meta_path = _stats_metadata_path()
    if not meta_path.exists():
        return None
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        # Acepta las dos generaciones de claves del pipeline
        return {
            "total": int(payload.get("franchise_total") or payload.get("total") or 0),
            "qualified": int(payload.get("qualified_total") or 0),
            "small_business": int(payload.get("small_business_total") or 0),
            "sells_alcohol": int(payload.get("sells_alcohol_total") or 0),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return None   # metadatos corruptos → se ignoran


def _load_checkpoint_total(path: Path) -> int | None:
    """Total parcial del checkpoint de descarga (si el bulk quedó a medias)."""
    checkpoint = path.with_suffix(path.suffix + ".checkpoint.json")
    if not checkpoint.exists():
        return None
    try:
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        written = int(payload.get("rows_written") or payload.get("offset") or 0)
        return written if written > 0 else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def lead_stats() -> dict[str, int]:
    """Totales del header desde metadatos/checkpoint — jamás escanea millones de filas."""
    signature = _file_signature()
    now = time.monotonic()
    # Caché fresco con la misma firma → devolver copia sin tocar disco
    if (
        _stats_cache["data"] is not None
        and _stats_cache["signature"] == signature
        and now - float(_stats_cache["loaded_at"]) < STATS_CACHE_TTL_SECONDS
    ):
        return dict(_stats_cache["data"])

    # Fuente preferida: bulk_stats.json del pipeline
    metadata = _load_metadata_stats()
    if metadata and metadata["total"] > 0:
        result = metadata
    else:
        # Fallback: al menos el total de franchise del checkpoint de descarga
        franchise_total = _load_checkpoint_total(settings.franchise_csv_path) or 0
        result = {
            "total": franchise_total,
            "qualified": 0,
            "small_business": 0,
            "sells_alcohol": 0,
        }

    # Actualiza el caché y devuelve una copia (nadie muta el interno)
    _stats_cache["data"] = result
    _stats_cache["signature"] = signature
    _stats_cache["loaded_at"] = now
    return dict(result)


def _build_where(params: LeadSearchParams) -> tuple[str, list[Any]]:
    """Traduce los filtros de la API a un WHERE de DuckDB con placeholders ?."""
    clauses: list[str] = []
    values: list[Any] = []

    if params.qualified_only:
        clauses.append(_bool_filter("is_qualified"))
    if params.small_business_only:
        clauses.append(_bool_filter("is_small_business"))
    if params.sells_alcohol_only:
        clauses.append(_bool_filter("sells_alcohol"))
    if params.industry:
        # COALESCE: industry puede ser NULL; LOWER+LIKE = subcadena sin mayúsculas
        clauses.append("LOWER(COALESCE(industry, '')) LIKE ?")
        values.append(f"%{params.industry.lower()}%")
    if params.county:
        clauses.append("CAST(county AS VARCHAR) LIKE ?")
        values.append(f"%{params.county}%")
    if params.q:
        # Texto libre sobre 5 columnas a la vez (mismo patrón repetido 5 veces)
        pattern = f"%{params.q.lower()}%"
        clauses.append(
            "("
            "LOWER(name) LIKE ? OR LOWER(city) LIKE ? OR LOWER(COALESCE(industry, '')) LIKE ? "
            "OR CAST(zip_code AS VARCHAR) LIKE ? OR LOWER(COALESCE(qualification_notes, '')) LIKE ?"
            ")"
        )
        values.extend([pattern, pattern, pattern, pattern, pattern])
    if params.city:
        clauses.append("LOWER(city) LIKE ?")
        values.append(f"%{params.city.lower()}%")
    if params.zip_code:
        # Prefijo de ZIP: "77" matchea 77002, 77005…
        clauses.append("CAST(zip_code AS VARCHAR) LIKE ?")
        values.append(f"{params.zip_code}%")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, values


def _as_bool(value: Any) -> bool:
    """Booleano robusto: acepta bool real, None o textos ('true','1','t','yes')."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def _row_to_lead(row: tuple, columns: list[str]) -> LeadRead:
    """Fila cruda de DuckDB → LeadRead completo (con defaults para lo que falta)."""
    data = dict(zip(columns, row))   # tupla + nombres de columna → dict
    now = datetime.now(timezone.utc)
    return LeadRead(
        id=int(data["id"]),
        external_id=str(data["external_id"]),
        name=str(data["name"]),
        city=str(data["city"]),
        # Los vacíos del CSV se normalizan a None
        county=str(data["county"]) if data.get("county") not in (None, "") else None,
        state=str(data.get("state") or "TX"),
        zip_code=str(data["zip_code"]) if data.get("zip_code") not in (None, "") else None,
        # El dataset bulk no trae estos campos → defaults neutros
        latitude=None,
        longitude=None,
        distance_miles=None,
        phone=None,
        email=None,
        industry=str(data["industry"]) if data.get("industry") not in (None, "") else None,
        employee_count=None,
        website_url=None,
        has_website=False,
        website_reachable=False,
        has_modern_website=False,
        website_tech_stack=None,
        website_antiquity_years=None,
        website_analysis_notes=_alcohol_notes(data),   # nota TABC si aplica
        facebook_url=None,
        instagram_url=None,
        has_active_facebook=False,
        has_active_instagram=False,
        is_small_business=_as_bool(data.get("is_small_business")),
        is_qualified=_as_bool(data.get("is_qualified")),
        qualification_score=float(data.get("qualification_score") or 0),
        qualification_notes=str(data["qualification_notes"])
        if data.get("qualification_notes") not in (None, "")
        else None,
        source=str(data.get("source") or "texas_bulk_csv"),
        created_at=now,   # el bulk no guarda timestamps por fila
        updated_at=now,
    )


def _alcohol_notes(data: dict[str, Any]) -> str | None:
    """Nota "TABC alcohol sales…" (versión dict del lead_mapper.alcohol_notes)."""
    if not _as_bool(data.get("sells_alcohol")):
        return None
    segment = data.get("alcohol_segment") or "unknown"
    total = float(data.get("total_receipts_total") or 0)
    return (
        f"TABC alcohol sales ({segment}); cumulative total_receipts=${total:,.0f} "
        f"(liquor=${float(data.get('liquor_receipts_total') or 0):,.0f}, "
        f"wine=${float(data.get('wine_receipts_total') or 0):,.0f}, "
        f"beer=${float(data.get('beer_receipts_total') or 0):,.0f})"
    )


def get_lead_by_id(lead_id: int) -> LeadRead | None:
    """Un lead concreto por su id (lo usa el research para resolver el negocio)."""
    if not processed_data_ready():
        return None

    conn = _connection()
    source = _leads_source()
    # Placeholder ? = parámetro escapado (nunca interpolar el id en el SQL)
    rows = conn.execute(f"SELECT * FROM {source} WHERE id = ?", [lead_id])
    row = rows.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in rows.description]   # nombres de columna del cursor
    return _row_to_lead(row, columns)


def search_leads_page(params: LeadSearchParams) -> LeadSearchPage:
    """La búsqueda principal de la API en modo bulk (COUNT cacheado + página)."""
    if not processed_data_ready():
        # Mensaje accionable: le dice al usuario exactamente qué comando correr
        raise FileNotFoundError(
            "Processed data not found. Run: python -m scripts.bulk_pipeline process"
        )

    conn = _connection()
    source = _leads_source()
    base = f"FROM {source}"
    where_sql, values = _build_where(params)

    # COUNT con caché: la parte cara de paginar (la página en sí es barata)
    signature = _file_signature()
    cache_key = _count_cache_key(where_sql, values)
    cached_total = _get_cached_count(cache_key, signature)
    if cached_total is not None:
        total = cached_total
    else:
        total = conn.execute(f"SELECT COUNT(*) {base} {where_sql}", values).fetchone()[0]
        _set_cached_count(cache_key, int(total))
    # La página pedida: mejores scores primero, luego recibos, luego nombre
    rows = conn.execute(
        f"""
        SELECT *
        {base}
        {where_sql}
        ORDER BY qualification_score DESC, total_receipts_total DESC, name
        LIMIT ? OFFSET ?
        """,
        [*values, params.limit, params.offset],
    )
    columns = [col[0] for col in rows.description]
    items = [_row_to_lead(row, columns) for row in rows.fetchall()]

    # Números de página derivados del offset/limit
    page = (params.offset // params.limit) + 1 if params.limit else 1
    pages = max(1, math.ceil(total / params.limit)) if params.limit else 1
    return LeadSearchPage(
        items=items,
        total=int(total),
        limit=params.limit,
        offset=params.offset,
        page=page,
        pages=pages,
    )
