"""API tests for leads router."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(isolated_db) -> TestClient:
    from scripts.process_leads import process_leads

    process_leads()

    import backend.app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_leads_requires_api_key(client: TestClient) -> None:
    response = client.get("/api/leads")
    assert response.status_code == 422


def test_search_qualified_leads(client: TestClient) -> None:
    response = client.get(
        "/api/leads",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        params={"qualified_only": True, "small_business_only": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert all(lead["is_qualified"] for lead in data)
    assert all(lead["is_small_business"] for lead in data)
    names = {lead["name"] for lead in data}
    assert "Metroplex Logistics Corp" not in names


def test_export_json(client: TestClient) -> None:
    response = client.get(
        "/api/leads/export/json",
        headers={"X-API-Key": "admin-dev-key-change-me"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 3
    assert "leads" in payload


def test_mark_lead(client: TestClient) -> None:
    leads = client.get(
        "/api/leads",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        params={"qualified_only": False, "small_business_only": False, "limit": 1},
    ).json()
    lead_id = leads[0]["id"]

    response = client.patch(
        f"/api/leads/{lead_id}/mark",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        json={"is_qualified": False, "qualification_notes": "Manual review"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_qualified"] is False
    assert body["qualification_notes"] == "Manual review"


def test_upsert_lead_create(client: TestClient) -> None:
    response = client.post(
        "/api/leads/upsert",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        json={
            "external_id": "TX-TEST-UPSERT-1",
            "name": "Test Upsert Shop",
            "city": "Austin",
            "employee_count": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["external_id"] == "TX-TEST-UPSERT-1"
    assert body["is_qualified"] is True
    assert body["is_small_business"] is True


def test_radius_search_by_zip(client: TestClient) -> None:
    response = client.get(
        "/api/leads",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        params={
            "zip_code": "78701",
            "radius_miles": 50,
            "qualified_only": True,
            "small_business_only": True,
            "limit": 50,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(item.get("distance_miles") is not None for item in data)
    assert all(item["distance_miles"] <= 50 for item in data)


def test_radius_search_by_city(client: TestClient) -> None:
    response = client.get(
        "/api/leads",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        params={
            "city": "Austin",
            "radius_miles": 30,
            "qualified_only": False,
            "small_business_only": False,
            "limit": 50,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    distances = [item["distance_miles"] for item in data]
    assert distances == sorted(distances)


def test_upsert_lead_update_preserves_omitted_fields(client: TestClient) -> None:
    create = client.post(
        "/api/leads/upsert",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        json={
            "external_id": "TX-TEST-UPSERT-2",
            "name": "Original Shop",
            "city": "Houston",
            "county": "Harris",
            "employee_count": 7,
            "industry": "Retail",
        },
    )
    assert create.status_code == 200
    assert create.json()["county"] == "Harris"
    assert create.json()["employee_count"] == 7

    update = client.post(
        "/api/leads/upsert",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        json={
            "external_id": "TX-TEST-UPSERT-2",
            "industry": "Services",
        },
    )
    assert update.status_code == 200
    body = update.json()
    assert body["name"] == "Original Shop"
    assert body["city"] == "Houston"
    assert body["county"] == "Harris"
    assert body["employee_count"] == 7
    assert body["industry"] == "Services"