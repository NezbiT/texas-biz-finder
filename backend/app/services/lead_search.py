"""Lead search with optional radius filtering and pagination."""

from __future__ import annotations

import math

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select

from backend.app.models.lead import Lead
from backend.app.schemas.lead import LeadRead, LeadSearchPage, LeadSearchParams
from scripts.common.geocoding import filter_by_radius, resolve_coordinates


def _apply_filters(statement, params: LeadSearchParams):
    if params.qualified_only:
        statement = statement.where(Lead.is_qualified.is_(True))
    if params.small_business_only:
        statement = statement.where(Lead.is_small_business.is_(True))
    if params.county:
        statement = statement.where(col(Lead.county).ilike(f"%{params.county}%"))
    if params.industry:
        statement = statement.where(col(Lead.industry).ilike(f"%{params.industry}%"))
    if params.q:
        pattern = f"%{params.q}%"
        statement = statement.where(
            col(Lead.name).ilike(pattern)
            | col(Lead.city).ilike(pattern)
            | col(Lead.industry).ilike(pattern)
            | col(Lead.zip_code).ilike(pattern)
            | col(Lead.qualification_notes).ilike(pattern)
        )
    if params.city and params.radius_miles is None:
        statement = statement.where(col(Lead.city).ilike(f"%{params.city}%"))
    if params.zip_code and params.radius_miles is None:
        statement = statement.where(col(Lead.zip_code).ilike(f"{params.zip_code}%"))
    return statement


def _base_query(params: LeadSearchParams):
    return _apply_filters(select(Lead), params)


def _radius_matches(session: Session, params: LeadSearchParams):
    if not params.city and not params.zip_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="city or zip_code is required when radius_miles is set",
        )
    center = resolve_coordinates(city=params.city, zip_code=params.zip_code)
    if center is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not resolve coordinates for the given city or ZIP",
        )

    candidates = list(session.exec(_base_query(params)).all())
    return filter_by_radius(
        candidates,
        center_lat=center.latitude,
        center_lng=center.longitude,
        radius_miles=params.radius_miles,
    )


def count_leads(session: Session, params: LeadSearchParams) -> int:
    """Count leads matching filters (before pagination)."""
    if params.radius_miles is not None:
        return len(_radius_matches(session, params))

    statement = _apply_filters(select(func.count()).select_from(Lead), params)
    return int(session.exec(statement).one())


def search_leads(session: Session, params: LeadSearchParams) -> list[LeadRead]:
    """Search leads, optionally filtering by city/ZIP within a mile radius."""
    if params.radius_miles is not None:
        within_radius = _radius_matches(session, params)
        sliced = within_radius[params.offset : params.offset + params.limit]
        return [
            LeadRead.model_validate(lead).model_copy(update={"distance_miles": distance})
            for lead, distance in sliced
        ]

    statement = (
        _base_query(params)
        .order_by(col(Lead.qualification_score).desc())
        .offset(params.offset)
        .limit(params.limit)
    )
    return [LeadRead.model_validate(lead) for lead in session.exec(statement).all()]


def search_leads_page(session: Session, params: LeadSearchParams) -> LeadSearchPage:
    """Return a paginated slice of leads plus total match count."""
    total = count_leads(session, params)
    items = search_leads(session, params)
    page = (params.offset // params.limit) + 1 if params.limit else 1
    pages = max(1, math.ceil(total / params.limit)) if params.limit else 1
    return LeadSearchPage(
        items=items,
        total=total,
        limit=params.limit,
        offset=params.offset,
        page=page,
        pages=pages,
    )