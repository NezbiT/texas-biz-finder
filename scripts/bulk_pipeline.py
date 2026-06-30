"""Bulk download Texas open data and build processed lead CSV for fast UI reads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.common.lead_materialize import materialize_processed_database
from scripts.common.socrata_bulk import (
    BEVERAGE_API,
    BEVERAGE_COLUMNS,
    FRANCHISE_API,
    FRANCHISE_COLUMNS,
    download_socrata_csv,
)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

FRANCHISE_CSV = RAW_DIR / "texas_franchise_taxpayers.csv"
BEVERAGE_CSV = RAW_DIR / "mixed_beverage_receipts.csv"
PROCESSED_CSV = PROCESSED_DIR / "texas_leads_processed.csv"
PROCESSED_DUCKDB = PROCESSED_DIR / "texas_leads.duckdb"

PROCESS_SQL = """
CREATE OR REPLACE TABLE franchise AS
SELECT
    CAST(taxpayer_number AS VARCHAR) AS taxpayer_number,
    taxpayer_name,
    taxpayer_address,
    taxpayer_city,
    taxpayer_state,
    taxpayer_zip,
    taxpayer_county_code,
    taxpayer_organizational_type,
    responsibility_beginning_date,
    sos_charter_date,
    sos_status_code,
    current_exempt_reason_code,
    right_to_transact_business_code,
    NULLIF(TRIM(CAST(_621111 AS VARCHAR)), '') AS naics_code
FROM read_csv_auto('{franchise_csv}', header=true, ignore_errors=true, all_varchar=true);

CREATE OR REPLACE TABLE beverage AS
SELECT
    CAST(taxpayer_number AS VARCHAR) AS taxpayer_number,
    NULLIF(TRIM(CAST(location_name AS VARCHAR)), '') AS location_name,
    TRY_CAST(NULLIF(liquor_receipts, '') AS DOUBLE) AS liquor_receipts,
    TRY_CAST(NULLIF(wine_receipts, '') AS DOUBLE) AS wine_receipts,
    TRY_CAST(NULLIF(beer_receipts, '') AS DOUBLE) AS beer_receipts,
    TRY_CAST(NULLIF(cover_charge_receipts, '') AS DOUBLE) AS cover_charge_receipts,
    TRY_CAST(NULLIF(total_receipts, '') AS DOUBLE) AS total_receipts
FROM read_csv_auto('{beverage_csv}', header=true, ignore_errors=true, all_varchar=true);

CREATE OR REPLACE TABLE beverage_agg AS
SELECT
    taxpayer_number,
    COUNT(*) AS beverage_report_rows,
    COUNT(DISTINCT location_name) AS beverage_location_count,
    SUM(COALESCE(liquor_receipts, 0)) AS liquor_receipts_total,
    SUM(COALESCE(wine_receipts, 0)) AS wine_receipts_total,
    SUM(COALESCE(beer_receipts, 0)) AS beer_receipts_total,
    SUM(COALESCE(cover_charge_receipts, 0)) AS cover_charge_receipts_total,
    SUM(COALESCE(total_receipts, 0)) AS total_receipts_total,
    MAX(COALESCE(total_receipts, 0)) AS peak_month_total_receipts
FROM beverage
WHERE taxpayer_number IS NOT NULL AND taxpayer_number <> ''
GROUP BY taxpayer_number;

CREATE OR REPLACE TABLE enriched AS
SELECT
    f.*,
    COALESCE(b.beverage_report_rows, 0) AS beverage_report_rows,
    COALESCE(b.beverage_location_count, 0) AS beverage_location_count,
    COALESCE(b.liquor_receipts_total, 0) AS liquor_receipts_total,
    COALESCE(b.wine_receipts_total, 0) AS wine_receipts_total,
    COALESCE(b.beer_receipts_total, 0) AS beer_receipts_total,
    COALESCE(b.cover_charge_receipts_total, 0) AS cover_charge_receipts_total,
    COALESCE(b.total_receipts_total, 0) AS total_receipts_total,
    COALESCE(b.peak_month_total_receipts, 0) AS peak_month_total_receipts,
    (b.taxpayer_number IS NOT NULL AND b.total_receipts_total > 0) AS sells_alcohol,
    CASE
        WHEN b.total_receipts_total IS NULL OR b.total_receipts_total <= 0 THEN 'none'
        WHEN (b.liquor_receipts_total + b.wine_receipts_total) > b.beer_receipts_total THEN 'bar_heavy'
        WHEN b.beer_receipts_total > (b.liquor_receipts_total + b.wine_receipts_total) THEN 'beer_focus'
        ELSE 'restaurant_mixed'
    END AS alcohol_segment
FROM franchise f
LEFT JOIN beverage_agg b ON f.taxpayer_number = b.taxpayer_number;
"""

EXPORT_SQL = """
COPY (
    SELECT
        ROW_NUMBER() OVER (ORDER BY qualification_score DESC, total_receipts_total DESC, taxpayer_name) AS id,
        'TX-COMPTROLLER-' || taxpayer_number AS external_id,
        taxpayer_number,
        taxpayer_name AS name,
        taxpayer_address AS address,
        taxpayer_city AS city,
        taxpayer_state AS state,
        taxpayer_zip AS zip_code,
        taxpayer_county_code AS county,
        taxpayer_organizational_type AS org_type,
        responsibility_beginning_date,
        sos_charter_date,
        sos_status_code,
        current_exempt_reason_code AS exempt_reason_code,
        right_to_transact_business_code AS right_to_transact_code,
        naics_code,
        inferred_industry AS industry,
        business_age_years,
        sells_alcohol,
        alcohol_segment,
        beverage_location_count,
        liquor_receipts_total,
        wine_receipts_total,
        beer_receipts_total,
        total_receipts_total,
        peak_month_total_receipts,
        is_small_business,
        is_qualified,
        qualification_score,
        qualification_notes,
        'texas_bulk_csv' AS source
    FROM scored
    WHERE include_in_processed = true
) TO '{processed_csv}' (HEADER, DELIMITER ',');
"""


def _infer_industry_sql() -> str:
    """SQL CASE mirroring scripts/common/data_sources.py keyword heuristics."""
    checks = [
        ("Auto Repair", ("auto repair", "automotive", "autobody", "mechanic", "collision", "muffler", "brake", "tire", "lube")),
        ("Food & Beverage", ("restaurant", "cafe", "bakery", "taco", "bbq", "pizza", "bar ", "grill", "cantina", "taqueria")),
        ("Home Services", ("plumbing", "plumber", "hvac", "electric", "roofing", "landscap")),
        ("Pet Services", ("pet groom", "veterinar", "kennel")),
    ]
    parts: list[str] = []
    for industry, keywords in checks:
        cond = " OR ".join(
            f"POSITION(LOWER('{kw}') IN LOWER(' ' || taxpayer_name || ' ')) > 0"
            for kw in keywords
        )
        parts.append(f"WHEN {cond} THEN '{industry}'")
    return "CASE " + " ".join(parts) + " ELSE NULL END"


def process_bulk(
    franchise_csv: Path,
    beverage_csv: Path,
    processed_csv: Path,
    processed_duckdb: Path | None = None,
) -> dict[str, int | str]:
    import duckdb

    if not franchise_csv.exists():
        raise FileNotFoundError(f"Missing franchise CSV: {franchise_csv}")
    if not beverage_csv.exists():
        raise FileNotFoundError(f"Missing beverage CSV: {beverage_csv}")

    processed_csv.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect()
    conn.execute(PROCESS_SQL.format(franchise_csv=str(franchise_csv).replace("\\", "/"), beverage_csv=str(beverage_csv).replace("\\", "/")))

    infer_industry = _infer_industry_sql()
    conn.execute(
        f"""
        CREATE OR REPLACE TABLE scored AS
        WITH base AS (
            SELECT
                e.*,
                {infer_industry} AS inferred_industry,
                CASE
                    WHEN sos_charter_date IS NOT NULL AND TRY_CAST(sos_charter_date AS DATE) IS NOT NULL
                        THEN DATE_DIFF('year', TRY_CAST(sos_charter_date AS DATE), CURRENT_DATE)
                    WHEN responsibility_beginning_date IS NOT NULL
                        AND TRY_CAST(responsibility_beginning_date AS TIMESTAMP) IS NOT NULL
                        THEN DATE_DIFF(
                            'year',
                            TRY_CAST(responsibility_beginning_date AS TIMESTAMP),
                            CURRENT_DATE
                        )
                    ELSE NULL
                END AS business_age_years,
                NOT (
                    taxpayer_name ILIKE '%CORP%'
                    OR taxpayer_name ILIKE '%CORPORATION%'
                    OR taxpayer_name ILIKE '%HOLDINGS%'
                    OR taxpayer_name ILIKE '%INTERNATIONAL%'
                    OR taxpayer_name ILIKE '%LOGISTICS%'
                    OR taxpayer_name ILIKE '%ENTERPRISES%'
                ) AS is_small_business,
                (
                    (sos_status_code IS NULL OR sos_status_code = 'A')
                    AND (
                        right_to_transact_business_code IS NULL
                        OR right_to_transact_business_code IN ('A', 'N')
                    )
                    AND NOT (
                        taxpayer_name ILIKE '%CORP%'
                        OR taxpayer_name ILIKE '%CORPORATION%'
                        OR taxpayer_name ILIKE '%HOLDINGS%'
                        OR taxpayer_name ILIKE '%INTERNATIONAL%'
                        OR taxpayer_name ILIKE '%LOGISTICS%'
                        OR taxpayer_name ILIKE '%ENTERPRISES%'
                    )
                    AND (
                        sells_alcohol
                        OR {infer_industry} IS NOT NULL
                        OR naics_code IS NOT NULL
                    )
                ) AS include_in_processed
            FROM enriched e
        )
        SELECT
            *,
            CASE
                WHEN sells_alcohol THEN 0.85
                WHEN inferred_industry IS NOT NULL THEN 0.55
                WHEN naics_code IS NOT NULL THEN 0.45
                ELSE 0.25
            END AS qualification_score,
            CASE
                WHEN sells_alcohol THEN 'TABC mixed beverage receipts matched by taxpayer_number'
                WHEN inferred_industry IS NOT NULL THEN 'Industry keyword inferred from legal name'
                WHEN naics_code IS NOT NULL THEN 'NAICS code present'
                ELSE 'Texas franchise taxpayer registry'
            END AS qualification_notes,
            (
                is_small_business
                AND include_in_processed
                AND (
                    CASE
                        WHEN sells_alcohol THEN 0.85
                        WHEN inferred_industry IS NOT NULL THEN 0.55
                        WHEN naics_code IS NOT NULL THEN 0.45
                        ELSE 0.25
                    END
                ) >= 0.45
            ) AS is_qualified
        FROM base;
        """
    )

    conn.execute(EXPORT_SQL.format(processed_csv=str(processed_csv).replace("\\", "/")))

    franchise_total = conn.execute("SELECT COUNT(*) FROM franchise").fetchone()[0]
    alcohol_total = conn.execute("SELECT COUNT(*) FROM beverage_agg").fetchone()[0]
    sells_alcohol = conn.execute("SELECT COUNT(*) FROM enriched WHERE sells_alcohol").fetchone()[0]
    processed_total = conn.execute("SELECT COUNT(*) FROM scored WHERE include_in_processed").fetchone()[0]
    qualified_total = conn.execute("SELECT COUNT(*) FROM scored WHERE is_qualified").fetchone()[0]
    small_business_total = conn.execute(
        "SELECT COUNT(*) FROM scored WHERE is_small_business AND include_in_processed"
    ).fetchone()[0]
    conn.close()

    duckdb_path = processed_duckdb or PROCESSED_DUCKDB
    materialize_processed_database(processed_csv, duckdb_path)

    stats = {
        "franchise_csv": str(franchise_csv),
        "beverage_csv": str(beverage_csv),
        "processed_csv": str(processed_csv),
        "processed_duckdb": str(duckdb_path),
        "franchise_total": franchise_total,
        "alcohol_taxpayers": alcohol_total,
        "sells_alcohol_total": sells_alcohol,
        "processed_total": processed_total,
        "qualified_total": qualified_total,
        "small_business_total": small_business_total,
    }
    _write_stats_metadata(processed_csv.parent / "bulk_stats.json", stats)
    return stats


def _write_stats_metadata(path: Path, stats: dict[str, int | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tabular_format": "csv",
        "metadata_format": "json",
        "api_read_format": "duckdb",
        "franchise_total": stats["franchise_total"],
        "qualified_total": stats["qualified_total"],
        "small_business_total": stats.get("small_business_total", 0),
        "sells_alcohol_total": stats["sells_alcohol_total"],
        "processed_total": stats["processed_total"],
        "processed_csv": stats["processed_csv"],
        "processed_duckdb": stats.get("processed_duckdb"),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def cmd_download_franchise(output: Path) -> None:
    stats = download_socrata_csv(
        api_url=FRANCHISE_API,
        columns=FRANCHISE_COLUMNS,
        output_path=output,
    )
    print(
        "Franchise download: {written}/{expected} rows -> {output}".format(**stats)
    )


def cmd_download_beverage(output: Path) -> None:
    stats = download_socrata_csv(
        api_url=BEVERAGE_API,
        columns=BEVERAGE_COLUMNS,
        output_path=output,
    )
    print(
        "Mixed beverage download: {written}/{expected} rows -> {output}".format(**stats)
    )


def cmd_process(franchise_csv: Path, beverage_csv: Path, processed_csv: Path) -> None:
    stats = process_bulk(franchise_csv, beverage_csv, processed_csv)
    print("Bulk process complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="TexasBizFinder bulk CSV pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fr = sub.add_parser("download-franchise", help="Download all Active Franchise Taxpayers")
    p_fr.add_argument("--output", type=Path, default=FRANCHISE_CSV)

    p_be = sub.add_parser("download-beverage", help="Download Mixed Beverage Gross Receipts")
    p_be.add_argument("--output", type=Path, default=BEVERAGE_CSV)

    p_proc = sub.add_parser("process", help="Join, analyze, and export processed CSV")
    p_proc.add_argument("--franchise", type=Path, default=FRANCHISE_CSV)
    p_proc.add_argument("--beverage", type=Path, default=BEVERAGE_CSV)
    p_proc.add_argument("--output", type=Path, default=PROCESSED_CSV)

    p_all = sub.add_parser("all", help="Download both datasets and process")
    p_all.add_argument("--franchise", type=Path, default=FRANCHISE_CSV)
    p_all.add_argument("--beverage", type=Path, default=BEVERAGE_CSV)
    p_all.add_argument("--output", type=Path, default=PROCESSED_CSV)

    args = parser.parse_args()

    if args.command == "download-franchise":
        cmd_download_franchise(args.output)
    elif args.command == "download-beverage":
        cmd_download_beverage(args.output)
    elif args.command == "process":
        cmd_process(args.franchise, args.beverage, args.output)
    elif args.command == "all":
        cmd_download_franchise(args.franchise)
        cmd_download_beverage(args.beverage)
        cmd_process(args.franchise, args.beverage, args.output)


if __name__ == "__main__":
    main()