"""Fast lead search: JSON metadata + CSV archive + DuckDB for API reads."""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from backend.app.config import settings
from backend.app.schemas.lead import LeadRead, LeadSearchPage, LeadSearchParams

STATS_CACHE_TTL_SECONDS = 300
COUNT_CACHE_TTL_SECONDS = 600
_stats_cache: dict[str, Any] = {"loaded_at": 0.0, "data": None, "signature": ""}
_count_cache: dict[str, tuple[float, int]] = {}
_count_cache_signature: str = ""


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def _processed_duckdb_ready() -> bool:
    return settings.processed_duckdb_path.exists()


def _processed_csv_ready() -> bool:
    return settings.processed_csv_path.exists()


def processed_data_ready() -> bool:
    """API reads typed DuckDB only (built from CSV during process)."""
    return _processed_duckdb_ready()


_duckdb_conn: duckdb.DuckDBPyConnection | None = None


def close_connection() -> None:
    global _duckdb_conn
    if _duckdb_conn is not None:
        _duckdb_conn.close()
        _duckdb_conn = None
    _invalidate_count_cache()


def _invalidate_count_cache() -> None:
    global _count_cache_signature
    _count_cache.clear()
    _count_cache_signature = ""


def _count_cache_key(where_sql: str, values: list[Any]) -> str:
    return f"{where_sql}|{values!r}"


def _get_cached_count(cache_key: str, signature: str) -> int | None:
    global _count_cache_signature
    if _count_cache_signature != signature:
        _invalidate_count_cache()
        _count_cache_signature = signature

    entry = _count_cache.get(cache_key)
    if entry is None:
        return None

    loaded_at, total = entry
    if time.monotonic() - loaded_at >= COUNT_CACHE_TTL_SECONDS:
        _count_cache.pop(cache_key, None)
        return None
    return total


def _set_cached_count(cache_key: str, total: int) -> None:
    _count_cache[cache_key] = (time.monotonic(), total)


def _connection() -> duckdb.DuckDBPyConnection:
    global _duckdb_conn
    if _duckdb_conn is not None:
        return _duckdb_conn
    if _processed_duckdb_ready():
        _duckdb_conn = duckdb.connect(str(settings.processed_duckdb_path.resolve()), read_only=True)
    else:
        _duckdb_conn = duckdb.connect()
    return _duckdb_conn


def _uses_typed_leads_table() -> bool:
    return _processed_duckdb_ready()


def _leads_source() -> str:
    if _uses_typed_leads_table():
        return "leads"
    csv_path = _sql_path(settings.processed_csv_path)
    return f"read_csv_auto('{csv_path}', header=true, all_varchar=true)"


def _bool_filter(column: str) -> str:
    if _uses_typed_leads_table():
        return f"{column} = true"
    return f"LOWER(TRIM(CAST({column} AS VARCHAR))) IN ('true', '1', 't', 'yes')"


def _stats_metadata_path() -> Path:
    return settings.processed_csv_path.parent / "bulk_stats.json"


def _file_signature() -> str:
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
    meta_path = _stats_metadata_path()
    if not meta_path.exists():
        return None
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        return {
            "total": int(payload.get("franchise_total") or payload.get("total") or 0),
            "qualified": int(payload.get("qualified_total") or 0),
            "small_business": int(payload.get("small_business_total") or 0),
            "sells_alcohol": int(payload.get("sells_alcohol_total") or 0),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _load_checkpoint_total(path: Path) -> int | None:
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
    """Stats from JSON metadata/checkpoint — never scan multi-million-row files."""
    signature = _file_signature()
    now = time.monotonic()
    if (
        _stats_cache["data"] is not None
        and _stats_cache["signature"] == signature
        and now - float(_stats_cache["loaded_at"]) < STATS_CACHE_TTL_SECONDS
    ):
        return dict(_stats_cache["data"])

    metadata = _load_metadata_stats()
    if metadata and metadata["total"] > 0:
        result = metadata
    else:
        franchise_total = _load_checkpoint_total(settings.franchise_csv_path) or 0
        result = {
            "total": franchise_total,
            "qualified": 0,
            "small_business": 0,
            "sells_alcohol": 0,
        }

    _stats_cache["data"] = result
    _stats_cache["signature"] = signature
    _stats_cache["loaded_at"] = now
    return dict(result)


def _build_where(params: LeadSearchParams) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []

    if params.qualified_only:
        clauses.append(_bool_filter("is_qualified"))
    if params.small_business_only:
        clauses.append(_bool_filter("is_small_business"))
    if params.sells_alcohol_only:
        clauses.append(_bool_filter("sells_alcohol"))
    if params.industry:
        clauses.append("LOWER(COALESCE(industry, '')) LIKE ?")
        values.append(f"%{params.industry.lower()}%")
    if params.county:
        clauses.append("CAST(county AS VARCHAR) LIKE ?")
        values.append(f"%{params.county}%")
    if params.q:
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
        clauses.append("CAST(zip_code AS VARCHAR) LIKE ?")
        values.append(f"{params.zip_code}%")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, values


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def _row_to_lead(row: tuple, columns: list[str]) -> LeadRead:
    data = dict(zip(columns, row))
    now = datetime.now(timezone.utc)
    return LeadRead(
        id=int(data["id"]),
        external_id=str(data["external_id"]),
        name=str(data["name"]),
        city=str(data["city"]),
        county=str(data["county"]) if data.get("county") not in (None, "") else None,
        state=str(data.get("state") or "TX"),
        zip_code=str(data["zip_code"]) if data.get("zip_code") not in (None, "") else None,
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
        website_analysis_notes=_alcohol_notes(data),
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
        created_at=now,
        updated_at=now,
    )


def _alcohol_notes(data: dict[str, Any]) -> str | None:
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
    """Fetch one lead row from DuckDB by paginated API id."""
    if not processed_data_ready():
        return None

    conn = _connection()
    source = _leads_source()
    rows = conn.execute(f"SELECT * FROM {source} WHERE id = ?", [lead_id])
    row = rows.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in rows.description]
    return _row_to_lead(row, columns)


def search_leads_page(params: LeadSearchParams) -> LeadSearchPage:
    if not processed_data_ready():
        raise FileNotFoundError(
            "Processed data not found. Run: python -m scripts.bulk_pipeline process"
        )

    conn = _connection()
    source = _leads_source()
    base = f"FROM {source}"
    where_sql, values = _build_where(params)

    signature = _file_signature()
    cache_key = _count_cache_key(where_sql, values)
    cached_total = _get_cached_count(cache_key, signature)
    if cached_total is not None:
        total = cached_total
    else:
        total = conn.execute(f"SELECT COUNT(*) {base} {where_sql}", values).fetchone()[0]
        _set_cached_count(cache_key, int(total))
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