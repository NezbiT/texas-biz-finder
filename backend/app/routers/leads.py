# Router principal de leads: /api/leads (stats, búsqueda, export, mark, upsert).
# Cada endpoint elige el backend de datos según settings (supabase/bulk/sqlite).
import csv   # generación del export CSV
import io    # buffer en memoria para el CSV
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from backend.app.config import settings
from backend.app.core.auth import require_admin           # auth por X-API-Key
from backend.app.database import get_session              # sesión DB por request
from backend.app.models.lead import Lead
from backend.app.schemas.lead import (
    LeadExport,
    LeadMarkRequest,
    LeadRead,
    LeadSearchPage,
    LeadSearchParams,
    LeadUpsertRequest,
)
from backend.app.services import csv_lead_store            # backend bulk (DuckDB)
from backend.app.services.lead_research_resolver import merge_sqlite_website_fields
from backend.app.services.lead_search import (              # backend SQL unificado
    search_leads as execute_lead_search,
    search_leads_page as execute_lead_search_page,
)
from scripts.common.geocoding import geocode_lead           # helpers del pipeline
from scripts.common.qualification import qualify_lead
from scripts.common.website_analysis import analyze_website

# Todos los endpoints cuelgan de /api/leads
router = APIRouter(prefix="/api/leads", tags=["leads"])


def _search_params(
    # Dependencia que agrupa/valida los query params de búsqueda:
    q: str | None = None,                                       # texto libre
    city: str | None = None,                                    # ciudad
    zip_code: str | None = None,                                # ZIP (o prefijo)
    radius_miles: float | None = Query(default=None, ge=1, le=50),   # radio 1-50 mi
    county: str | None = None,                                  # condado
    industry: str | None = None,                                # industria
    qualified_only: bool = True,                                # solo calificados
    small_business_only: bool = True,                           # solo pequeños
    sells_alcohol_only: bool = False,                           # solo TABC
    limit: int = Query(default=50, ge=1, le=500),               # tamaño de página
    offset: int = Query(default=0, ge=0),                       # desplazamiento
) -> LeadSearchParams:
    # Empaqueta todo en el schema que entienden los buscadores
    return LeadSearchParams(
        q=q,
        city=city,
        zip_code=zip_code,
        radius_miles=radius_miles,
        county=county,
        industry=industry,
        qualified_only=qualified_only,
        small_business_only=small_business_only,
        sells_alcohol_only=sells_alcohol_only,
        limit=limit,
        offset=offset,
    )


@router.get("/stats")
def lead_stats(
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),   # solo valida la key; el valor no se usa
) -> dict[str, int]:
    """Totales de la base — la UI los muestra en el header como contexto."""
    # Backend Supabase: 4 COUNTs directos sobre la tabla leads
    if settings.use_supabase_backend:
        total = session.exec(select(func.count()).select_from(Lead)).one()
        qualified = session.exec(
            select(func.count()).select_from(Lead).where(Lead.is_qualified.is_(True))
        ).one()
        small_business = session.exec(
            select(func.count()).select_from(Lead).where(Lead.is_small_business.is_(True))
        ).one()
        sells_alcohol = session.exec(
            select(func.count()).select_from(Lead).where(Lead.sells_alcohol.is_(True))
        ).one()
        return {
            "total": total,
            "qualified": qualified,
            "small_business": small_business,
            "sells_alcohol": sells_alcohol,
        }

    # Backend bulk: totales precalculados (jamás escanea los CSVs gigantes)
    if settings.use_csv_backend:
        csv_stats = csv_lead_store.lead_stats()
        if csv_stats["total"] > 0 or csv_lead_store.processed_data_ready():
            return csv_stats

    # Fallback SQLite puro (datasets chicos de demo)
    total = session.exec(select(func.count()).select_from(Lead)).one()
    qualified = session.exec(
        select(func.count()).select_from(Lead).where(Lead.is_qualified.is_(True))
    ).one()
    small_business = session.exec(
        select(func.count()).select_from(Lead).where(Lead.is_small_business.is_(True))
    ).one()
    return {
        "total": total,
        "qualified": qualified,
        "small_business": small_business,
        "sells_alcohol": 0,   # el modo SQLite legacy no tiene cruce TABC
    }


@router.get("", response_model=LeadSearchPage)
def search_leads(
    params: LeadSearchParams = Depends(_search_params),
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> LeadSearchPage:
    """La búsqueda principal (paginada) — el corazón de la app."""
    if settings.use_supabase_backend:
        return execute_lead_search_page(session, params)
    if settings.use_csv_backend and csv_lead_store.processed_data_ready():
        # Bulk: busca en DuckDB y superpone el research guardado en SQLite
        page = csv_lead_store.search_leads_page(params)
        page.items = merge_sqlite_website_fields(session, page.items)
        return page
    return execute_lead_search_page(session, params)   # fallback SQLite


def _export_search_params(
    # Igual que _search_params pero con límite alto (hasta 5000) y sin offset
    q: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    radius_miles: float | None = Query(default=None, ge=1, le=50),
    county: str | None = None,
    industry: str | None = None,
    qualified_only: bool = True,
    small_business_only: bool = True,
    sells_alcohol_only: bool = False,
    limit: int = Query(default=500, ge=1, le=5000),
) -> LeadSearchParams:
    return LeadSearchParams(
        q=q,
        city=city,
        zip_code=zip_code,
        radius_miles=radius_miles,
        county=county,
        industry=industry,
        qualified_only=qualified_only,
        small_business_only=small_business_only,
        sells_alcohol_only=sells_alcohol_only,
        limit=limit,
        offset=0,   # el export siempre arranca desde el principio
    )


@router.get("/export/json", response_model=LeadExport)
def export_leads_json(
    params: LeadSearchParams = Depends(_export_search_params),
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> LeadExport:
    """Export JSON de la búsqueda actual (con marca de tiempo)."""
    export_params = params
    leads = execute_lead_search(session, export_params)
    return LeadExport(
        exported_at=datetime.now(timezone.utc),
        total=len(leads),
        leads=leads,
    )


@router.get("/export/csv")
def export_leads_csv(
    params: LeadSearchParams = Depends(_export_search_params),
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> StreamingResponse:
    """Export CSV descargable (el botón "Export CSV" del frontend)."""
    # Obtiene los leads del backend activo (misma lógica que la búsqueda)
    if settings.use_supabase_backend:
        leads = execute_lead_search(session, params)
    elif settings.use_csv_backend and csv_lead_store.processed_data_ready():
        page = csv_lead_store.search_leads_page(params)
        leads = page.items
    else:
        export_params = params
        leads = execute_lead_search(session, export_params)

    # Escribe el CSV en memoria con las columnas útiles para ventas
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "name",
            "city",
            "zip_code",
            "distance_miles",
            "county",
            "phone",
            "email",
            "industry",
            "employee_count",
            "website_url",
            "has_website",
            "website_reachable",
            "has_modern_website",
            "website_tech_stack",
            "website_antiquity_years",
            "website_analysis_notes",
            "has_active_facebook",
            "has_active_instagram",
            "is_qualified",
            "qualification_score",
            "qualification_notes",
        ],
    )
    writer.writeheader()
    # Una fila por lead, campo a campo (mismo orden que fieldnames)
    for lead in leads:
        writer.writerow(
            {
                "name": lead.name,
                "city": lead.city,
                "zip_code": lead.zip_code,
                "distance_miles": lead.distance_miles,
                "county": lead.county,
                "phone": lead.phone,
                "email": lead.email,
                "industry": lead.industry,
                "employee_count": lead.employee_count,
                "website_url": lead.website_url,
                "has_website": lead.has_website,
                "website_reachable": lead.website_reachable,
                "has_modern_website": lead.has_modern_website,
                "website_tech_stack": lead.website_tech_stack,
                "website_antiquity_years": lead.website_antiquity_years,
                "website_analysis_notes": lead.website_analysis_notes,
                "has_active_facebook": lead.has_active_facebook,
                "has_active_instagram": lead.has_active_instagram,
                "is_qualified": lead.is_qualified,
                "qualification_score": lead.qualification_score,
                "qualification_notes": lead.qualification_notes,
            }
        )

    # Respuesta como descarga adjunta (el navegador guarda texas_leads.csv)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=texas_leads.csv"},
    )


def _apply_qualification(lead: Lead) -> Lead:
    """Re-corre las heurísticas de calificación (sitio, redes, tamaño) y
    vuelca el resultado en los campos del lead."""
    website = analyze_website(lead.website_url)   # análisis ligero del sitio
    result = qualify_lead(
        website_url=lead.website_url,
        facebook_url=lead.facebook_url,
        instagram_url=lead.instagram_url,
        employee_count=lead.employee_count,
        max_employees=settings.max_employees_small_biz,
        website_analysis=website,
    )
    # Copia campo a campo el veredicto de la calificación
    lead.has_website = result.has_website
    lead.website_reachable = result.website_reachable
    lead.has_modern_website = result.has_modern_website
    lead.website_tech_stack = result.website_tech_stack
    lead.website_antiquity_years = result.website_antiquity_years
    lead.website_analysis_notes = result.website_analysis_notes
    lead.has_active_facebook = result.has_active_facebook
    lead.has_active_instagram = result.has_active_instagram
    lead.is_small_business = result.is_small_business
    lead.is_qualified = result.is_qualified
    lead.qualification_score = result.qualification_score
    lead.qualification_notes = result.notes
    lead.updated_at = datetime.now(timezone.utc)
    return lead


def _apply_geocoding(lead: Lead) -> Lead:
    """Resuelve lat/lng por ciudad/ZIP (para la búsqueda por radio)."""
    lat, lng = geocode_lead(lead.city, lead.zip_code)
    lead.latitude = lat
    lead.longitude = lng
    return lead


@router.patch("/{lead_id}/mark", response_model=LeadRead)
def mark_lead(
    lead_id: int,
    body: LeadMarkRequest,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> Lead:
    """Marca/desmarca manualmente un lead como calificado (override humano)."""
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    lead.is_qualified = body.is_qualified
    if body.qualification_notes is not None:   # las notas solo si vinieron
        lead.qualification_notes = body.qualification_notes
    lead.updated_at = datetime.now(timezone.utc)
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


@router.post("/upsert", response_model=LeadRead, status_code=status.HTTP_200_OK)
def upsert_lead(
    body: LeadUpsertRequest,
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> Lead:
    """Crea o actualiza un lead (por external_id) y re-corre la calificación."""
    # ¿Ya existe? — external_id es la clave estable entre backends
    existing = session.exec(
        select(Lead).where(Lead.external_id == body.external_id)
    ).first()

    now = datetime.now(timezone.utc)
    if existing:
        # Actualización parcial: solo los campos que el cliente envió
        lead = existing
        updates = body.model_dump(exclude_unset=True)
        updates.pop("external_id", None)   # la clave no se cambia
        for field, value in updates.items():
            setattr(lead, field, value)
    else:
        # Creación: nombre y ciudad son obligatorios
        payload = body.model_dump()
        if not payload.get("name") or not payload.get("city"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="name and city are required when creating a lead",
            )
        lead = Lead(
            **payload,
            state="TX",
            source="api_upsert",
            created_at=now,
        )

    # Re-califica y geocodifica antes de guardar
    _apply_qualification(lead)
    _apply_geocoding(lead)
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead
