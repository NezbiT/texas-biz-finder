"""Website discovery (DuckDuckGo) and deep analysis (Playwright) endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from backend.app.core.auth import require_admin
from backend.app.database import get_session
from backend.app.models.lead import Lead
from backend.app.schemas.website_analysis import (
    AnalysisStatusResponse,
    WebsiteAnalysisRead,
    WebsiteAnalyzeRequest,
    WebsiteSearchRequest,
    WebsiteSearchResponse,
    WebsiteUrlUpdateRequest,
)
from backend.app.services.analysis_lock import analysis_lock
from backend.app.services.duckduckgo_search import search_business_website
from backend.app.services.playwright_analyzer import analyze_url_with_playwright
from backend.app.services.report_generator import generate_analysis_report
from backend.app.services.website_analysis_store import (
    analysis_to_read,
    apply_analysis_to_lead,
    list_analyses_for_lead,
    save_analysis,
)
from backend.app.config import settings

router = APIRouter(prefix="/api/leads", tags=["website-research"])


def _get_lead_or_404(session: Session, lead_id: int) -> Lead:
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


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
    lead = _get_lead_or_404(session, lead_id)
    business_name = (body.business_name or lead.name).strip()
    city = (body.city or lead.city).strip()
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

    return WebsiteSearchResponse(query=query, results=results)


@router.post("/{lead_id}/website-analyze", response_model=WebsiteAnalysisRead)
async def analyze_lead_website(
    lead_id: int,
    body: WebsiteAnalyzeRequest,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> WebsiteAnalysisRead:
    """Run a deep Playwright analysis on the selected URL (one at a time)."""
    lead = _get_lead_or_404(session, lead_id)
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
        record = save_analysis(session, lead_id=lead_id, result=result)
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
    _get_lead_or_404(session, lead_id)
    records = list_analyses_for_lead(session, lead_id)
    return [analysis_to_read(r) for r in records]


@router.get("/{lead_id}/website-analyses/{analysis_id}/report")
def download_analysis_report(
    lead_id: int,
    analysis_id: int,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> HTMLResponse:
    """Generate an HTML report suitable for printing or PDF export."""
    lead = _get_lead_or_404(session, lead_id)
    from backend.app.models.website_analysis import WebsiteAnalysis

    record = session.get(WebsiteAnalysis, analysis_id)
    if record is None or record.lead_id != lead_id:
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
    lead = _get_lead_or_404(session, lead_id)
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required")

    lead.website_url = url
    lead.has_website = True
    session.add(lead)
    session.commit()
    return {"website_url": url}