"""API schemas for website search and deep Playwright analysis."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class WebsiteSearchRequest(BaseModel):
    business_name: str | None = None
    city: str | None = None
    max_results: int = Field(default=8, ge=1, le=15)


class WaybackInfo(BaseModel):
    domain: str
    first_seen: str | None = None
    last_seen: str | None = None
    snapshot_count: int = 0
    age_years: int | None = None
    timeline_url: str
    first_snapshot_url: str | None = None
    last_snapshot_url: str | None = None
    available: bool = False


class WebsiteSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    wayback: WaybackInfo | None = None


class WebsiteSearchResponse(BaseModel):
    query: str
    results: list[WebsiteSearchResult]


class WebsiteAnalyzeRequest(BaseModel):
    url: str
    save_to_lead: bool = True


class WebsiteUrlUpdateRequest(BaseModel):
    url: str


class WebsiteAnalysisRead(BaseModel):
    id: int
    lead_id: int
    url: str
    final_url: str | None
    page_title: str | None
    last_modified: str | None
    load_time_ms: float | None
    dom_content_loaded_ms: float | None
    technologies: list[str]
    seo_title: str | None
    seo_meta_description: str | None
    seo_h1: str | None
    seo_issues: list[str]
    summary: str | None
    metrics: dict[str, object]
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisStatusResponse(BaseModel):
    busy: bool
    lead_id: int | None = None
    url: str | None = None