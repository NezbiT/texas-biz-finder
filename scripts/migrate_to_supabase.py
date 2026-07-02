#!/usr/bin/env python3
"""Upload processed Texas leads from DuckDB/CSV into Supabase (PostgreSQL).

Prerequisites:
  1. Create a Supabase project at https://supabase.com
  2. Copy the connection string (Settings → Database → URI)
  3. Set in .env:
       DATA_BACKEND=supabase
       DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

Usage:
  python -m scripts.migrate_to_supabase
  python -m scripts.migrate_to_supabase --dry-run
  python -m scripts.migrate_to_supabase --batch-size 2000
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb
from sqlalchemy import text
from sqlmodel import Session

from backend.app.config import settings
from backend.app.database import engine, init_db
from backend.app.models.lead import Lead


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes"}


def _as_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_rows() -> list[dict]:
    if settings.processed_duckdb_path.exists():
        conn = duckdb.connect(str(settings.processed_duckdb_path.resolve()), read_only=True)
        result = conn.execute("SELECT * FROM leads ORDER BY id")
        columns = [col[0] for col in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        conn.close()
        return rows

    if not settings.processed_csv_path.exists():
        raise FileNotFoundError(
            "No processed data found. Run: python -m scripts.bulk_pipeline process"
        )

    conn = duckdb.connect()
    csv_sql = str(settings.processed_csv_path.resolve()).replace("\\", "/")
    result = conn.execute(
        f"SELECT * FROM read_csv_auto('{csv_sql}', header=true, all_varchar=true) ORDER BY id"
    )
    columns = [col[0] for col in result.description]
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    conn.close()
    return rows


def _row_to_lead(data: dict) -> Lead:
    now = datetime.now(timezone.utc)
    return Lead(
        id=_as_int(data.get("id")),
        external_id=str(data["external_id"]),
        name=str(data["name"]),
        city=str(data["city"]),
        county=str(data["county"]) if data.get("county") not in (None, "") else None,
        state=str(data.get("state") or "TX"),
        zip_code=str(data["zip_code"]) if data.get("zip_code") not in (None, "") else None,
        industry=str(data["industry"]) if data.get("industry") not in (None, "") else None,
        is_small_business=_as_bool(data.get("is_small_business")),
        is_qualified=_as_bool(data.get("is_qualified")),
        qualification_score=float(data.get("qualification_score") or 0),
        qualification_notes=str(data["qualification_notes"])
        if data.get("qualification_notes") not in (None, "")
        else None,
        sells_alcohol=_as_bool(data.get("sells_alcohol")),
        alcohol_segment=str(data["alcohol_segment"])
        if data.get("alcohol_segment") not in (None, "")
        else None,
        liquor_receipts_total=_as_float(data.get("liquor_receipts_total")),
        wine_receipts_total=_as_float(data.get("wine_receipts_total")),
        beer_receipts_total=_as_float(data.get("beer_receipts_total")),
        total_receipts_total=_as_float(data.get("total_receipts_total")),
        source=str(data.get("source") or "texas_bulk_csv"),
        created_at=now,
        updated_at=now,
    )


def migrate(*, batch_size: int, dry_run: bool, force: bool = False) -> dict[str, int]:
    if not settings.use_supabase_backend:
        raise RuntimeError("Set DATA_BACKEND=supabase in .env before migrating")
    if not settings.is_postgres:
        raise RuntimeError("DATABASE_URL must be a postgresql:// Supabase connection string")

    rows = _load_rows()
    if not rows:
        return {"total": 0, "inserted": 0, "skipped": 0}

    if dry_run:
        print(f"[dry-run] Would migrate {len(rows)} leads to Supabase")
        return {"total": len(rows), "inserted": 0, "skipped": 0}

    init_db()

    inserted = 0
    skipped = 0
    with Session(engine) as session:
        existing_count = session.execute(text("SELECT COUNT(*) FROM leads")).scalar_one()
        if existing_count and existing_count > 0:
            if not force:
                answer = input(
                    f"leads table already has {existing_count} rows. "
                    "Truncate and reload? [y/N]: "
                ).strip()
                if answer.lower() != "y":
                    print("Aborted.")
                    return {"total": len(rows), "inserted": 0, "skipped": len(rows)}
            session.execute(text("TRUNCATE TABLE website_analyses RESTART IDENTITY CASCADE"))
            session.execute(text("TRUNCATE TABLE leads RESTART IDENTITY CASCADE"))
            session.commit()

        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            for data in batch:
                lead = _row_to_lead(data)
                session.add(lead)
            session.commit()
            inserted += len(batch)
            print(f"  inserted {inserted}/{len(rows)}", flush=True)

        max_id = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM leads")).scalar_one()
        session.execute(
            text("SELECT setval(pg_get_serial_sequence('leads', 'id'), :max_id, true)"),
            {"max_id": max_id},
        )
        session.commit()

    return {"total": len(rows), "inserted": inserted, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate DuckDB/CSV leads into Supabase PostgreSQL")
    parser.add_argument("--batch-size", type=int, default=3000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Truncate existing rows without prompt")
    args = parser.parse_args()

    stats = migrate(batch_size=args.batch_size, dry_run=args.dry_run, force=args.force)
    print(
        f"Done: total={stats['total']} inserted={stats['inserted']} skipped={stats['skipped']}"
    )


if __name__ == "__main__":
    main()