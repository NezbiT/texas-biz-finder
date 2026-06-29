import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select

from backend.app.config import settings
from backend.app.core.auth import require_admin
from backend.app.database import get_session
from backend.app.models.lead import Lead
from backend.app.schemas.lead import (
    LeadExport,
    LeadMarkRequest,
    LeadRead,
    LeadSearchParams,
    LeadUpsertRequest,
)
from backend.app.services.lead_search import search_leads as execute_lead_search
from scripts.common.geocoding import geocode_lead
from scripts.common.qualification import qualify_lead
from scripts.common.website_analysis import analyze_website

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _search_params(
    q: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    radius_miles: float | None = Query(default=None, ge=1, le=50),
    county: str | None = None,
    industry: str | None = None,
    qualified_only: bool = True,
    small_business_only: bool = True,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
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
        limit=limit,
        offset=offset,
    )


@router.get("/stats")
def lead_stats(
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> dict[str, int]:
    """Return database totals so the UI can explain filtered result counts."""
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
    }


@router.get("", response_model=list[LeadRead])
def search_leads(
    params: LeadSearchParams = Depends(_search_params),
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> list[LeadRead]:
    return execute_lead_search(session, params)


def _export_search_params(
    q: str | None = None,
    city: str | None = None,
    zip_code: str | None = None,
    radius_miles: float | None = Query(default=None, ge=1, le=50),
    county: str | None = None,
    industry: str | None = None,
    qualified_only: bool = True,
    small_business_only: bool = True,
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
        limit=limit,
        offset=0,
    )


@router.get("/export/json", response_model=LeadExport)
def export_leads_json(
    params: LeadSearchParams = Depends(_export_search_params),
    session: Session = Depends(get_session),
    _: str = Depends(require_admin),
) -> LeadExport:
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
    export_params = params
    leads = execute_lead_search(session, export_params)

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

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=texas_leads.csv"},
    )


def _apply_qualification(lead: Lead) -> Lead:
    website = analyze_website(lead.website_url)
    result = qualify_lead(
        website_url=lead.website_url,
        facebook_url=lead.facebook_url,
        instagram_url=lead.instagram_url,
        employee_count=lead.employee_count,
        max_employees=settings.max_employees_small_biz,
        website_analysis=website,
    )
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
    """Manually mark or unmark a lead as qualified."""
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    lead.is_qualified = body.is_qualified
    if body.qualification_notes is not None:
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
    """Create or update a lead and re-run qualification heuristics."""
    existing = session.exec(
        select(Lead).where(Lead.external_id == body.external_id)
    ).first()

    now = datetime.now(timezone.utc)
    if existing:
        lead = existing
        updates = body.model_dump(exclude_unset=True)
        updates.pop("external_id", None)
        for field, value in updates.items():
            setattr(lead, field, value)
    else:
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

    _apply_qualification(lead)
    _apply_geocoding(lead)
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead