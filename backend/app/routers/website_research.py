"""Website discovery (DuckDuckGo) and deep analysis (Playwright) endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from backend.app.core.auth import require_admin
from backend.app.database import get_session
from backend.app.schemas.website_analysis import (
    AnalysisStatusResponse,
    WaybackInfo,
    WebsiteAnalysisRead,
    WebsiteAnalyzeRequest,
    WebsiteSearchRequest,
    WebsiteSearchResponse,
    WebsiteSearchResult,
    WebsiteUrlUpdateRequest,
)
from backend.app.services.analysis_lock import analysis_lock
from backend.app.services.duckduckgo_search import search_business_website
from backend.app.services.lead_research_resolver import lead_name_and_city, resolve_lead_for_research
from backend.app.services.playwright_analyzer import analyze_url_with_playwright
from backend.app.services.report_generator import generate_analysis_report
from backend.app.services.wayback_lookup import enrich_urls_with_wayback, lookup_wayback, wayback_to_dict
from backend.app.services.website_analysis_store import (
    analysis_to_read,
    apply_analysis_to_lead,
    list_analyses_for_lead,
    save_analysis,
)
from backend.app.config import settings

router = APIRouter(prefix="/api/leads", tags=["website-research"])


def _wayback_info(url: str) -> WaybackInfo | None:
    history = lookup_wayback(url)
    if history is None:
        return None
    return WaybackInfo(**wayback_to_dict(history))


def _attach_wayback_to_results(results: list[WebsiteSearchResult]) -> list[WebsiteSearchResult]:
    if not results:
        return results
    histories = enrich_urls_with_wayback([r.url for r in results])
    enriched: list[WebsiteSearchResult] = []
    for item in results:
        history = histories.get(item.url)
        wayback = WaybackInfo(**wayback_to_dict(history)) if history else None
        enriched.append(item.model_copy(update={"wayback": wayback}))
    return enriched


@router.get("/website-wayback", response_model=WaybackInfo)
def website_wayback_history(
    url: str,
    _: str = Depends(require_admin),
) -> WaybackInfo:
    """Internet Archive timeline for a URL (first seen, last update, age)."""
    target = url.strip()
    if not target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required")
    info = _wayback_info(target)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not resolve domain for Wayback lookup",
        )
    return info


@router.get("/website-research/status", response_model=AnalysisStatusResponse)
def analysis_status(_: str = Depends(require_admin)) -> AnalysisStatusResponse:
    """Return whether a Playwright analysis is currently running."""
    active = analysis_lock.active
    return AnalysisStatusResponse(
        busy=analysis_lock.is_busy,
        lead_id=active.lead_id if active else None,
        url=active.url if active else None,
    )


@router.post("/{lead_id}/website-search", response_model=WebsiteSearchResponse)
def search_lead_website(
    lead_id: int,
    body: WebsiteSearchRequest,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> WebsiteSearchResponse:
    """Search DuckDuckGo for the business website using name + city."""
    default_name, default_city = lead_name_and_city(session, lead_id)
    business_name = (body.business_name or default_name).strip()
    city = (body.city or default_city).strip()
    if not business_name or not city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business name and city are required",
        )

    try:
        query, results = search_business_website(
            business_name,
            city,
            max_results=body.max_results,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    results = _attach_wayback_to_results(results)
    return WebsiteSearchResponse(query=query, results=results)


@router.post("/{lead_id}/website-analyze", response_model=WebsiteAnalysisRead)
async def analyze_lead_website(
    lead_id: int,
    body: WebsiteAnalyzeRequest,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> WebsiteAnalysisRead:
    """Run a deep Playwright analysis on the selected URL (one at a time)."""
    lead = resolve_lead_for_research(session, lead_id)
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required")

    try:
        await analysis_lock.acquire(lead_id, url)
    except RuntimeError as exc:
        active = analysis_lock.active
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "active_lead_id": active.lead_id if active else None,
                "active_url": active.url if active else None,
            },
        ) from exc

    try:
        result = await analyze_url_with_playwright(
            url,
            navigation_timeout_ms=settings.playwright_nav_timeout_ms,
            total_timeout_ms=settings.playwright_timeout_ms,
        )
        wayback = lookup_wayback(url)
        if wayback:
            result.metrics["wayback"] = wayback_to_dict(wayback)
            if wayback.age_years is not None and result.metrics.get("estimated_antiquity_years") is None:
                result.metrics["estimated_antiquity_years"] = wayback.age_years
            if wayback.available and result.summary:
                age_note = (
                    f" Wayback Machine: first capture {wayback.first_seen}, "
                    f"last {wayback.last_seen} (~{wayback.snapshot_count} snapshots)."
                )
                if age_note.strip() not in result.summary:
                    result.summary = (result.summary + age_note).strip()

        record = save_analysis(session, lead_id=lead.id or lead_id, result=result)
        if body.save_to_lead and result.status == "completed":
            apply_analysis_to_lead(session, lead, result)
        return analysis_to_read(record)
    finally:
        analysis_lock.release()


@router.get("/{lead_id}/website-analyses", response_model=list[WebsiteAnalysisRead])
def get_lead_analyses(
    lead_id: int,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> list[WebsiteAnalysisRead]:
    """Return analysis history for a lead."""
    lead = resolve_lead_for_research(session, lead_id)
    records = list_analyses_for_lead(session, lead.id or lead_id)
    return [analysis_to_read(r) for r in records]


@router.get("/{lead_id}/website-analyses/{analysis_id}/report")
def download_analysis_report(
    lead_id: int,
    analysis_id: int,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> HTMLResponse:
    """Generate an HTML report suitable for printing or PDF export."""
    lead = resolve_lead_for_research(session, lead_id)
    from backend.app.models.website_analysis import WebsiteAnalysis

    record = session.get(WebsiteAnalysis, analysis_id)
    if record is None or record.lead_id != lead.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    html = generate_analysis_report(lead, record)
    filename = f"lead-{lead_id}-analysis-{analysis_id}.html"
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{lead_id}/website-url", response_model=dict[str, str])
def update_lead_website_url(
    lead_id: int,
    body: WebsiteUrlUpdateRequest,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> dict[str, str]:
    """Save the selected website URL on the lead without running Playwright."""
    lead = resolve_lead_for_research(session, lead_id)
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required")

    lead.website_url = url
    lead.has_website = True
    lead.updated_at = datetime.now(timezone.utc)
    session.add(lead)
    session.commit()
    return {"website_url": url, "external_id": lead.external_id, "name": lead.name}