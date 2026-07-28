"""Endpoints del research de sitios: descubrimiento (DuckDuckGo), historial
(Wayback Machine) y auditoría profunda (Playwright, uno a la vez)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from backend.app.core.auth import require_admin      # auth por X-API-Key
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
from backend.app.services.analysis_lock import analysis_lock          # lock Playwright
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

# Mismo prefijo /api/leads que el router principal (rutas anidadas por lead)
router = APIRouter(prefix="/api/leads", tags=["website-research"])


def _require_website_research() -> None:
    """Oracle free tier / low-RAM: disable Playwright + external search via env."""
    if not settings.enable_website_research:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Website research is disabled on this host "
                "(set ENABLE_WEBSITE_RESEARCH=true and install Playwright chromium)."
            ),
        )


def _wayback_info(url: str) -> WaybackInfo | None:
    """Lookup Wayback de una URL → schema de la API (o None si no hay dominio)."""
    history = lookup_wayback(url)
    if history is None:
        return None
    return WaybackInfo(**wayback_to_dict(history))


def _attach_wayback_to_results(results: list[WebsiteSearchResult]) -> list[WebsiteSearchResult]:
    """Enriquece cada resultado de búsqueda con su historial Wayback (en paralelo)."""
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
    """Línea de tiempo del archivo para una URL (primera captura, última, edad)."""
    _require_website_research()
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
    """¿Hay un Playwright corriendo? (la UI lo consulta antes de analizar)."""
    if not settings.enable_website_research:
        return AnalysisStatusResponse(busy=False, lead_id=None, url=None)
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
    """Busca el sitio del negocio en DuckDuckGo usando nombre + ciudad."""
    _require_website_research()
    # El body puede sobreescribir nombre/ciudad; si no, se usan los del lead
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
        # Fallo de DDG = problema del servicio externo → 502 Bad Gateway
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    # Cada candidato sale ya con su historial Wayback adjunto
    results = _attach_wayback_to_results(results)
    return WebsiteSearchResponse(query=query, results=results)


@router.post("/{lead_id}/website-analyze", response_model=WebsiteAnalysisRead)
async def analyze_lead_website(
    lead_id: int,
    body: WebsiteAnalyzeRequest,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> WebsiteAnalysisRead:
    """Auditoría profunda con Playwright de la URL elegida (una a la vez)."""
    _require_website_research()
    lead = resolve_lead_for_research(session, lead_id)   # asegura la fila persistente
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required")

    # Toma el lock global; si está ocupado → 409 con detalles de quién lo tiene
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
        # 1) La auditoría Playwright propiamente dicha
        result = await analyze_url_with_playwright(
            url,
            navigation_timeout_ms=settings.playwright_nav_timeout_ms,
            total_timeout_ms=settings.playwright_timeout_ms,
        )
        # 2) Enriquecimiento con Wayback: edad del dominio + nota en el resumen
        wayback = lookup_wayback(url)
        if wayback:
            result.metrics["wayback"] = wayback_to_dict(wayback)
            # Si el análisis no estimó antigüedad, usar la del archivo
            if wayback.age_years is not None and result.metrics.get("estimated_antiquity_years") is None:
                result.metrics["estimated_antiquity_years"] = wayback.age_years
            # Añade la línea Wayback al resumen (evitando duplicarla)
            if wayback.available and result.summary:
                age_note = (
                    f" Wayback Machine: first capture {wayback.first_seen}, "
                    f"last {wayback.last_seen} (~{wayback.snapshot_count} snapshots)."
                )
                if age_note.strip() not in result.summary:
                    result.summary = (result.summary + age_note).strip()

        # 3) Persistir el análisis y (si se pidió y salió bien) volcarlo al lead
        record = save_analysis(session, lead_id=lead.id or lead_id, result=result)
        if body.save_to_lead and result.status == "completed":
            apply_analysis_to_lead(session, lead, result)
        return analysis_to_read(record)
    finally:
        analysis_lock.release()   # SIEMPRE soltar el lock, pase lo que pase


@router.get("/{lead_id}/website-analyses", response_model=list[WebsiteAnalysisRead])
def get_lead_analyses(
    lead_id: int,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> list[WebsiteAnalysisRead]:
    """Historial de análisis del lead (más recientes primero)."""
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
    """Reporte HTML imprimible del análisis (para propuestas al cliente)."""
    lead = resolve_lead_for_research(session, lead_id)
    from backend.app.models.website_analysis import WebsiteAnalysis

    record = session.get(WebsiteAnalysis, analysis_id)
    # El análisis debe existir Y pertenecer a este lead (no filtrar datos ajenos)
    if record is None or record.lead_id != lead.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    html = generate_analysis_report(lead, record)
    filename = f"lead-{lead_id}-analysis-{analysis_id}.html"
    # Como descarga adjunta con nombre descriptivo
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
    """Guarda la URL elegida en el lead SIN correr Playwright (acción rápida)."""
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
