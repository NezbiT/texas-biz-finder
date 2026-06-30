"""Tests for bulk CSV pipeline and DuckDB lead store."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from backend.app.services import csv_lead_store
from backend.app.schemas.lead import LeadSearchParams
from scripts.bulk_pipeline import process_bulk


@pytest.fixture()
def bulk_fixture_dir(tmp_path: Path) -> Path:
    franchise = tmp_path / "franchise.csv"
    beverage = tmp_path / "beverage.csv"
    processed = tmp_path / "processed.csv"

    with franchise.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "taxpayer_number": "1001",
                "taxpayer_name": "HILL COUNTRY BBQ & BAR LLC",
                "taxpayer_address": "1 MAIN ST",
                "taxpayer_city": "AUSTIN",
                "taxpayer_state": "TX",
                "taxpayer_zip": "78701",
                "taxpayer_county_code": "227",
                "taxpayer_organizational_type": "CL",
                "responsibility_beginning_date": "2018-01-01T00:00:00.000",
                "sos_charter_date": "2018-01-01T00:00:00.000",
                "sos_status_code": "A",
                "current_exempt_reason_code": "",
                "right_to_transact_business_code": "A",
                "_621111": "722511",
            }
        )
        writer.writerow(
            {
                "taxpayer_number": "1002",
                "taxpayer_name": "METROPLEX LOGISTICS CORPORATION",
                "taxpayer_address": "9 CORP BLVD",
                "taxpayer_city": "DALLAS",
                "taxpayer_state": "TX",
                "taxpayer_zip": "75201",
                "taxpayer_county_code": "57",
                "taxpayer_organizational_type": "CI",
                "responsibility_beginning_date": "2010-01-01T00:00:00.000",
                "sos_charter_date": "2010-01-01T00:00:00.000",
                "sos_status_code": "A",
                "current_exempt_reason_code": "",
                "right_to_transact_business_code": "A",
                "_621111": "",
            }
        )

    with beverage.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "taxpayer_number": "1001",
                "taxpayer_name": "HILL COUNTRY BBQ & BAR LLC",
                "location_name": "HILL COUNTRY BBQ",
                "location_city": "AUSTIN",
                "location_zip": "78701",
                "location_county": "TRAVIS",
                "obligation_end_date_yyyymmdd": "202401",
                "liquor_receipts": "12000",
                "wine_receipts": "4000",
                "beer_receipts": "8000",
                "cover_charge_receipts": "0",
                "total_receipts": "24000",
            }
        )

    return tmp_path


def test_process_bulk_marks_alcohol_seller(bulk_fixture_dir: Path, monkeypatch) -> None:
    from backend.app.config import settings

    franchise = bulk_fixture_dir / "franchise.csv"
    beverage = bulk_fixture_dir / "beverage.csv"
    processed = bulk_fixture_dir / "processed.csv"

    duckdb_path = bulk_fixture_dir / "processed.duckdb"
    stats = process_bulk(franchise, beverage, processed, processed_duckdb=duckdb_path)
    assert stats["franchise_total"] == 2
    assert stats["sells_alcohol_total"] == 1
    assert stats["processed_total"] >= 1
    assert processed.exists()
    assert duckdb_path.exists()

    from backend.app.services import csv_lead_store

    csv_lead_store.close_connection()
    monkeypatch.setattr(settings, "data_backend", "csv", raising=False)
    monkeypatch.setattr(settings, "franchise_csv_path", franchise, raising=False)
    monkeypatch.setattr(settings, "processed_csv_path", processed, raising=False)
    monkeypatch.setattr(settings, "processed_duckdb_path", duckdb_path, raising=False)
    monkeypatch.setattr(csv_lead_store.settings, "processed_csv_path", processed, raising=False)
    monkeypatch.setattr(csv_lead_store.settings, "processed_duckdb_path", duckdb_path, raising=False)
    monkeypatch.setattr(csv_lead_store.settings, "franchise_csv_path", franchise, raising=False)
    page = csv_lead_store.search_leads_page(
        LeadSearchParams(qualified_only=True, small_business_only=True, limit=50, offset=0)
    )
    assert page.total >= 1
    names = {lead.name for lead in page.items}
    assert "HILL COUNTRY BBQ & BAR LLC" in names
    assert "METROPLEX LOGISTICS CORPORATION" not in names
    alcohol_lead = next(
        lead for lead in page.items if lead.name == "HILL COUNTRY BBQ & BAR LLC"
    )
    assert alcohol_lead.website_analysis_notes is not None
    assert "TABC" in alcohol_lead.website_analysis_notes

    alcohol_page = csv_lead_store.search_leads_page(
        LeadSearchParams(
            sells_alcohol_only=True,
            qualified_only=False,
            small_business_only=False,
            limit=50,
            offset=0,
        )
    )
    assert alcohol_page.total == 1
    assert alcohol_page.items[0].name == "HILL COUNTRY BBQ & BAR LLC"