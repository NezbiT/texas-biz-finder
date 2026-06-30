"""Persistence helpers for WebsiteAnalysis records."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlmodel import Session, select

from backend.app.models.lead import Lead
from backend.app.models.website_analysis import WebsiteAnalysis
from backend.app.schemas.website_analysis import WebsiteAnalysisRead
from backend.app.services.playwright_analyzer import DeepAnalysisResult, deep_result_to_json_fields


def analysis_to_read(record: WebsiteAnalysis) -> WebsiteAnalysisRead:
    """Map SQLModel row to API response."""
    technologies: list[str] = []
    seo_issues: list[str] = []
    metrics: dict[str, object] = {}
    if record.technologies_json:
        try:
            technologies = json.loads(record.technologies_json)
        except json.JSONDecodeError:
            technologies = []
    if record.seo_issues_json:
        try:
            seo_issues = json.loads(record.seo_issues_json)
        except json.JSONDecodeError:
            seo_issues = []
    if record.metrics_json:
        try:
            metrics = json.loads(record.metrics_json)
        except json.JSONDecodeError:
            metrics = {}

    return WebsiteAnalysisRead(
        id=record.id or 0,
        lead_id=record.lead_id,
        url=record.url,
        final_url=record.final_url,
        page_title=record.page_title,
        last_modified=record.last_modified,
        load_time_ms=record.load_time_ms,
        dom_content_loaded_ms=record.dom_content_loaded_ms,
        technologies=technologies,
        seo_title=record.seo_title,
        seo_meta_description=record.seo_meta_description,
        seo_h1=record.seo_h1,
        seo_issues=seo_issues,
        summary=record.summary,
        metrics=metrics,
        status=record.status,
        error_message=record.error_message,
        created_at=record.created_at,
    )


def save_analysis(
    session: Session,
    *,
    lead_id: int,
    result: DeepAnalysisResult,
) -> WebsiteAnalysis:
    """Persist a deep analysis result."""
    json_fields = deep_result_to_json_fields(result)
    record = WebsiteAnalysis(
        lead_id=lead_id,
        url=result.url,
        final_url=result.final_url,
        page_title=result.page_title,
        last_modified=result.last_modified,
        load_time_ms=result.load_time_ms,
        dom_content_loaded_ms=result.dom_content_loaded_ms,
        seo_title=result.seo.title,
        seo_meta_description=result.seo.meta_description,
        seo_h1=result.seo.h1,
        summary=result.summary,
        status=result.status,
        error_message=result.error_message,
        **json_fields,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_analyses_for_lead(session: Session, lead_id: int) -> list[WebsiteAnalysis]:
    statement = (
        select(WebsiteAnalysis)
        .where(WebsiteAnalysis.lead_id == lead_id)
        .order_by(desc(WebsiteAnalysis.created_at))
    )
    return list(session.exec(statement).all())


def apply_analysis_to_lead(session: Session, lead: Lead, result: DeepAnalysisResult) -> Lead:
    """Update lead website fields from a successful deep analysis."""
    lead.website_url = result.final_url or result.url
    lead.has_website = True
    lead.website_reachable = result.status == "completed"
    lead.website_tech_stack = ", ".join(result.technologies) if result.technologies else None
    antiquity = result.metrics.get("estimated_antiquity_years")
    lead.website_antiquity_years = int(antiquity) if isinstance(antiquity, int) else None
    lead.has_modern_website = bool(result.metrics.get("has_modern_website"))
    lead.website_analysis_notes = result.summary
    lead.updated_at = datetime.now(timezone.utc)
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead