"""Tests for website search and Playwright analysis endpoints."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.services.playwright_analyzer import DeepAnalysisResult, SeoAudit


@pytest.fixture()
def client(isolated_db) -> TestClient:
    from scripts.process_leads import process_leads

    process_leads()

    import backend.app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def _sample_deep_result(url: str = "https://example-auto.com") -> DeepAnalysisResult:
    return DeepAnalysisResult(
        url=url,
        final_url=url,
        page_title="Example Auto Shop",
        last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
        load_time_ms=1800.5,
        dom_content_loaded_ms=900.0,
        technologies=["WordPress", "jQuery 3"],
        seo=SeoAudit(
            title="Example Auto Shop",
            meta_description="Auto repair in Austin TX",
            h1="Welcome",
            issues=["Missing viewport meta (mobile responsiveness)"],
        ),
        summary="Moderate load time. SEO gaps found.",
        metrics={"uses_https": True, "has_modern_website": False},
        status="completed",
    )


def _lead_id(client: TestClient) -> int:
    response = client.get(
        "/api/leads",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        params={"qualified_only": False, "small_business_only": False, "limit": 1},
    )
    return response.json()["items"][0]["id"]


def test_analysis_status_idle(client: TestClient) -> None:
    response = client.get(
        "/api/leads/website-research/status",
        headers={"X-API-Key": "admin-dev-key-change-me"},
    )
    assert response.status_code == 200
    assert response.json()["busy"] is False


@patch("backend.app.routers.website_research.search_business_website")
def test_website_search(mock_search, client: TestClient) -> None:
    from backend.app.schemas.website_analysis import WebsiteSearchResult

    mock_search.return_value = (
        '"Test Shop" Austin TX website',
        [
            WebsiteSearchResult(
                title="Test Shop Official",
                url="https://testshop.example",
                snippet="Auto repair services",
            )
        ],
    )

    lead_id = _lead_id(client)
    response = client.post(
        f"/api/leads/{lead_id}/website-search",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        json={"max_results": 5},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["url"] == "https://testshop.example"


@patch(
    "backend.app.routers.website_research.analyze_url_with_playwright",
    new_callable=AsyncMock,
)
def test_website_analyze_and_history(mock_analyze, client: TestClient) -> None:
    mock_analyze.return_value = _sample_deep_result()

    lead_id = _lead_id(client)
    response = client.post(
        f"/api/leads/{lead_id}/website-analyze",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        json={"url": "https://example-auto.com", "save_to_lead": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "WordPress" in body["technologies"]
    assert body["seo_issues"]

    history = client.get(
        f"/api/leads/{lead_id}/website-analyses",
        headers={"X-API-Key": "admin-dev-key-change-me"},
    )
    assert history.status_code == 200
    assert len(history.json()) == 1

    report = client.get(
        f"/api/leads/{lead_id}/website-analyses/{body['id']}/report",
        headers={"X-API-Key": "admin-dev-key-change-me"},
    )
    assert report.status_code == 200
    assert "Website Analysis Report" in report.text


@pytest.mark.asyncio
async def test_analysis_lock_rejects_parallel_runs() -> None:
    from backend.app.services.analysis_lock import AnalysisLock

    lock = AnalysisLock()
    await lock.acquire(1, "https://first.example")
    with pytest.raises(RuntimeError):
        await lock.acquire(2, "https://second.example")
    lock.release()


def test_update_website_url(client: TestClient) -> None:
    lead_id = _lead_id(client)
    response = client.patch(
        f"/api/leads/{lead_id}/website-url",
        headers={"X-API-Key": "admin-dev-key-change-me"},
        json={"url": "https://picked.example"},
    )
    assert response.status_code == 200
    assert response.json()["website_url"] == "https://picked.example"


def test_duckduckgo_build_query() -> None:
    from backend.app.services.duckduckgo_search import build_search_query

    query = build_search_query("Joe's Auto", "Austin")
    assert "Joe's Auto" in query
    assert "Austin" in query
    assert "TX" in query