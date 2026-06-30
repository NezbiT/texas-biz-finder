"""Persisted deep website analysis results linked to a lead."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WebsiteAnalysis(SQLModel, table=True):
    """Playwright-powered website audit saved for a lead."""

    __tablename__ = "website_analyses"

    id: int | None = Field(default=None, primary_key=True)
    lead_id: int = Field(foreign_key="leads.id", index=True)
    url: str
    final_url: str | None = None
    page_title: str | None = None
    last_modified: str | None = None
    load_time_ms: float | None = None
    dom_content_loaded_ms: float | None = None
    technologies_json: str | None = None
    seo_title: str | None = None
    seo_meta_description: str | None = None
    seo_h1: str | None = None
    seo_issues_json: str | None = None
    summary: str | None = None
    metrics_json: str | None = None
    status: str = Field(default="completed", index=True)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=_utc_now)