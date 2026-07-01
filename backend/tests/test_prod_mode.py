"""Tests for single-port production mode (API + built frontend)."""

from __future__ import annotations

import importlib
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from scripts.common.lead_materialize import materialize_processed_database


ROOT = Path(__file__).resolve().parents[2]


def test_materialize_creates_search_indexes(tmp_path: Path) -> None:
    csv_path = tmp_path / "leads.csv"
    csv_path.write_text(
        "id,external_id,taxpayer_number,name,address,city,state,zip_code,county,"
        "org_type,responsibility_beginning_date,sos_charter_date,sos_status_code,"
        "exempt_reason_code,right_to_transact_code,naics_code,industry,business_age_years,"
        "sells_alcohol,alcohol_segment,beverage_location_count,liquor_receipts_total,"
        "wine_receipts_total,beer_receipts_total,total_receipts_total,"
        "peak_month_total_receipts,is_small_business,is_qualified,qualification_score,"
        "qualification_notes,source\n"
        "1,TX-1,1001,Test Biz,1 Main,Austin,TX,78701,227,CL,,,,,,,"
        "Food & Beverage,5,true,bar_heavy,1,100,50,25,175,50,true,true,0.85,"
        "TABC,texas_bulk_csv\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "leads.duckdb"
    materialize_processed_database(csv_path, db_path)

    conn = duckdb.connect(str(db_path), read_only=True)
    indexes = {row[0] for row in conn.execute("SELECT index_name FROM duckdb_indexes()").fetchall()}
    conn.close()

    assert "idx_leads_qualified" in indexes
    assert "idx_leads_sells_alcohol" in indexes
    assert "idx_leads_zip" in indexes


def test_count_cache_reuses_total(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from backend.app.services import csv_lead_store
    from backend.app.schemas.lead import LeadSearchParams

    csv_path = tmp_path / "leads.csv"
    csv_path.write_text(
        "id,external_id,taxpayer_number,name,address,city,state,zip_code,county,"
        "org_type,responsibility_beginning_date,sos_charter_date,sos_status_code,"
        "exempt_reason_code,right_to_transact_code,naics_code,industry,business_age_years,"
        "sells_alcohol,alcohol_segment,beverage_location_count,liquor_receipts_total,"
        "wine_receipts_total,beer_receipts_total,total_receipts_total,"
        "peak_month_total_receipts,is_small_business,is_qualified,qualification_score,"
        "qualification_notes,source\n"
        "1,TX-1,1001,Alpha,1 Main,Austin,TX,78701,227,CL,,,,,,,Food,5,true,"
        "bar_heavy,1,100,50,25,175,50,true,true,0.85,TABC,texas_bulk_csv\n"
        "2,TX-2,1002,Beta,2 Main,Houston,TX,77001,201,CL,,,,,,,Auto,8,false,"
        "none,0,0,0,0,0,0,true,true,0.55,Industry,texas_bulk_csv\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "leads.duckdb"
    materialize_processed_database(csv_path, db_path)

    csv_lead_store.close_connection()
    monkeypatch.setattr(csv_lead_store.settings, "processed_csv_path", csv_path, raising=False)
    monkeypatch.setattr(csv_lead_store.settings, "processed_duckdb_path", db_path, raising=False)

    params = LeadSearchParams(qualified_only=True, small_business_only=True, limit=1, offset=0)
    page1 = csv_lead_store.search_leads_page(params)
    page2 = csv_lead_store.search_leads_page(
        LeadSearchParams(qualified_only=True, small_business_only=True, limit=1, offset=1)
    )

    assert page1.total == 2
    assert page2.total == 2
    assert len(csv_lead_store._count_cache) == 1


@pytest.fixture()
def prod_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>TexasBizFinder</body></html>", encoding="utf-8")
    assets = dist / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('ok');", encoding="utf-8")

    monkeypatch.setenv("SERVE_FRONTEND", "true")
    monkeypatch.setenv("FRONTEND_DIST_PATH", str(dist))

    import backend.app.config as config_mod

    importlib.reload(config_mod)
    import backend.app.main as main_mod

    importlib.reload(main_mod)
    return TestClient(main_mod.app)


def test_prod_mode_serves_frontend(prod_client: TestClient) -> None:
    response = prod_client.get("/")
    assert response.status_code == 200
    assert "TexasBizFinder" in response.text

    asset = prod_client.get("/assets/app.js")
    assert asset.status_code == 200
    assert "console.log" in asset.text

    api = prod_client.get("/api/leads", headers={"X-API-Key": "admin-dev-key-change-me"})
    assert api.status_code == 200