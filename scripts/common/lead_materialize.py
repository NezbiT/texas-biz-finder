"""Materialize processed CSV into a typed DuckDB file for fast API reads."""

from __future__ import annotations

from pathlib import Path

import duckdb


def materialize_processed_database(csv_path: Path, db_path: Path) -> None:
    """Import processed CSV into a typed DuckDB database (primary read format for the API)."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Processed CSV not found: {csv_path}")

    try:
        from backend.app.services.csv_lead_store import close_connection

        close_connection()
    except ImportError:
        pass

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    csv_sql = str(csv_path.resolve()).replace("\\", "/")
    conn = duckdb.connect(str(db_path))
    conn.execute(
        f"""
        CREATE TABLE leads AS
        SELECT
            CAST(id AS BIGINT) AS id,
            CAST(external_id AS VARCHAR) AS external_id,
            CAST(taxpayer_number AS VARCHAR) AS taxpayer_number,
            CAST(name AS VARCHAR) AS name,
            CAST(address AS VARCHAR) AS address,
            CAST(city AS VARCHAR) AS city,
            CAST(state AS VARCHAR) AS state,
            CAST(zip_code AS VARCHAR) AS zip_code,
            CAST(county AS VARCHAR) AS county,
            CAST(org_type AS VARCHAR) AS org_type,
            CAST(responsibility_beginning_date AS VARCHAR) AS responsibility_beginning_date,
            CAST(sos_charter_date AS VARCHAR) AS sos_charter_date,
            CAST(sos_status_code AS VARCHAR) AS sos_status_code,
            CAST(exempt_reason_code AS VARCHAR) AS exempt_reason_code,
            CAST(right_to_transact_code AS VARCHAR) AS right_to_transact_code,
            CAST(naics_code AS VARCHAR) AS naics_code,
            CAST(industry AS VARCHAR) AS industry,
            TRY_CAST(business_age_years AS INTEGER) AS business_age_years,
            CAST(sells_alcohol AS BOOLEAN) AS sells_alcohol,
            CAST(alcohol_segment AS VARCHAR) AS alcohol_segment,
            TRY_CAST(beverage_location_count AS INTEGER) AS beverage_location_count,
            TRY_CAST(liquor_receipts_total AS DOUBLE) AS liquor_receipts_total,
            TRY_CAST(wine_receipts_total AS DOUBLE) AS wine_receipts_total,
            TRY_CAST(beer_receipts_total AS DOUBLE) AS beer_receipts_total,
            TRY_CAST(total_receipts_total AS DOUBLE) AS total_receipts_total,
            TRY_CAST(peak_month_total_receipts AS DOUBLE) AS peak_month_total_receipts,
            CAST(is_small_business AS BOOLEAN) AS is_small_business,
            CAST(is_qualified AS BOOLEAN) AS is_qualified,
            TRY_CAST(qualification_score AS DOUBLE) AS qualification_score,
            CAST(qualification_notes AS VARCHAR) AS qualification_notes,
            CAST(source AS VARCHAR) AS source
        FROM read_csv_auto('{csv_sql}', header=true, all_varchar=true)
        """
    )
    _create_lead_indexes(conn)
    conn.close()


def _create_lead_indexes(conn: duckdb.DuckDBPyConnection) -> None:
    """Speed up common API filters and sort order."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_qualified ON leads(is_qualified)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_small_biz ON leads(is_small_business)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_sells_alcohol ON leads(sells_alcohol)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_zip ON leads(zip_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_leads_score ON leads("
        "qualification_score, total_receipts_total, name)"
    )