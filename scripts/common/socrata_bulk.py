"""Paginated downloads from Texas Open Data (Socrata) with resume checkpoints."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Iterable

import httpx

FRANCHISE_API = "https://data.texas.gov/resource/9cir-efmm.json"
BEVERAGE_API = "https://data.texas.gov/resource/naix-2893.json"

FRANCHISE_COLUMNS: tuple[str, ...] = (
    "taxpayer_number",
    "taxpayer_name",
    "taxpayer_address",
    "taxpayer_city",
    "taxpayer_state",
    "taxpayer_zip",
    "taxpayer_county_code",
    "taxpayer_organizational_type",
    "responsibility_beginning_date",
    "sos_charter_date",
    "sos_status_code",
    "current_exempt_reason_code",
    "right_to_transact_business_code",
    "_621111",
)

BEVERAGE_COLUMNS: tuple[str, ...] = (
    "taxpayer_number",
    "taxpayer_name",
    "location_name",
    "location_city",
    "location_zip",
    "location_county",
    "obligation_end_date_yyyymmdd",
    "liquor_receipts",
    "wine_receipts",
    "beer_receipts",
    "cover_charge_receipts",
    "total_receipts",
)

DEFAULT_PAGE_SIZE = 50_000
DEFAULT_SLEEP_SECONDS = 0.35


def _load_checkpoint(path: Path) -> int:
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    return int(payload.get("offset", 0))


def _save_checkpoint(path: Path, offset: int, rows_written: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"offset": offset, "rows_written": rows_written}, indent=2),
        encoding="utf-8",
    )


def _count_rows(api_url: str, timeout: float = 60.0) -> int:
    response = httpx.get(
        api_url,
        params={"$select": "count(*) as total"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return int(payload[0]["total"])


def download_socrata_csv(
    *,
    api_url: str,
    columns: Iterable[str],
    output_path: Path,
    checkpoint_path: Path | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
    timeout: float = 120.0,
) -> dict[str, int | str]:
    """Download an entire Socrata dataset to CSV, resuming from checkpoint offset."""
    column_list = list(columns)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = checkpoint_path or output_path.with_suffix(".checkpoint.json")

    total_expected = _count_rows(api_url, timeout=timeout)
    start_offset = _load_checkpoint(checkpoint)
    mode = "a" if start_offset > 0 and output_path.exists() else "w"

    rows_written = 0
    if mode == "a":
        with output_path.open("r", encoding="utf-8", newline="") as existing:
            rows_written = max(sum(1 for _ in existing) - 1, 0)

    with output_path.open(mode, encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=column_list, extrasaction="ignore")
        if mode == "w":
            writer.writeheader()

        offset = start_offset
        while offset < total_expected:
            params: dict[str, str | int] = {
                "$limit": page_size,
                "$offset": offset,
                "$order": column_list[0],
                "$select": ",".join(column_list),
            }
            response = httpx.get(api_url, params=params, timeout=timeout)
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break

            for row in batch:
                writer.writerow({col: row.get(col, "") for col in column_list})

            rows_written += len(batch)
            offset += len(batch)
            _save_checkpoint(checkpoint, offset, rows_written)

            if sleep_seconds:
                time.sleep(sleep_seconds)

            if len(batch) < page_size:
                break

    return {
        "output": str(output_path),
        "expected": total_expected,
        "written": rows_written,
        "checkpoint": str(checkpoint),
    }