"""Búsqueda de leads en SQLite/Postgres con radio opcional y paginación.

(Este es el buscador "unificado"; el modo bulk usa csv_lead_store con DuckDB.)
"""

from __future__ import annotations

import math

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select

from backend.app.models.lead import Lead
from backend.app.schemas.lead import LeadRead, LeadSearchPage, LeadSearchParams
from backend.app.services.lead_mapper import lead_to_read
from scripts.common.geocoding import filter_by_radius, resolve_coordinates


def _apply_filters(statement, params: LeadSearchParams):
    """Traduce los parámetros de búsqueda en cláusulas WHERE encadenadas."""
    if params.qualified_only:
        statement = statement.where(Lead.is_qualified.is_(True))
    if params.small_business_only:
        statement = statement.where(Lead.is_small_business.is_(True))
    if params.sells_alcohol_only:
        statement = statement.where(Lead.sells_alcohol.is_(True))
    if params.county:
        # ilike = LIKE case-insensitive; %...% = subcadena en cualquier posición
        statement = statement.where(col(Lead.county).ilike(f"%{params.county}%"))
    if params.industry:
        statement = statement.where(col(Lead.industry).ilike(f"%{params.industry}%"))
    if params.q:
        # Texto libre: busca en nombre, ciudad, industria, ZIP y notas a la vez
        pattern = f"%{params.q}%"
        statement = statement.where(
            col(Lead.name).ilike(pattern)
            | col(Lead.city).ilike(pattern)
            | col(Lead.industry).ilike(pattern)
            | col(Lead.zip_code).ilike(pattern)
            | col(Lead.qualification_notes).ilike(pattern)
        )
    # Ciudad/ZIP como filtro exacto SOLO sin radio (con radio se filtra por distancia)
    if params.city and params.radius_miles is None:
        statement = statement.where(col(Lead.city).ilike(f"%{params.city}%"))
    if params.zip_code and params.radius_miles is None:
        # prefijo: "77" matchea 77002, 77005… (útil para zonas)
        statement = statement.where(col(Lead.zip_code).ilike(f"{params.zip_code}%"))
    return statement


def _base_query(params: LeadSearchParams):
    """SELECT de leads con todos los filtros aplicados (sin paginar)."""
    return _apply_filters(select(Lead), params)


def _radius_matches(session: Session, params: LeadSearchParams):
    """Búsqueda por radio: resuelve el centro y filtra por distancia."""
    # El radio necesita un punto de partida: ciudad o ZIP
    if not params.city and not params.zip_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="city or zip_code is required when radius_miles is set",
        )
    # Geocodifica el centro con el diccionario local de ubicaciones de Texas
    center = resolve_coordinates(city=params.city, zip_code=params.zip_code)
    if center is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not resolve coordinates for the given city or ZIP",
        )

    # Trae los candidatos que pasan el resto de filtros y mide su distancia
    candidates = list(session.exec(_base_query(params)).all())
    return filter_by_radius(
        candidates,
        center_lat=center.latitude,
        center_lng=center.longitude,
        radius_miles=params.radius_miles,
    )


def count_leads(session: Session, params: LeadSearchParams) -> int:
    """Total de coincidencias (antes de paginar) para calcular las páginas."""
    if params.radius_miles is not None:
        # Con radio no hay COUNT SQL directo: se cuenta la lista filtrada
        return len(_radius_matches(session, params))

    statement = _apply_filters(select(func.count()).select_from(Lead), params)
    return int(session.exec(statement).one())


def search_leads(session: Session, params: LeadSearchParams) -> list[LeadRead]:
    """La página de resultados pedida (con distancia si hubo radio)."""
    if params.radius_miles is not None:
        within_radius = _radius_matches(session, params)
        # Paginación en memoria sobre la lista (lead, distancia)
        sliced = within_radius[params.offset : params.offset + params.limit]
        return [lead_to_read(lead, distance_miles=distance) for lead, distance in sliced]

    # Sin radio: orden por score DESC, luego recibos DESC, luego nombre
    statement = (
        _base_query(params)
        .order_by(
            col(Lead.qualification_score).desc(),
            col(Lead.total_receipts_total).desc(),
            col(Lead.name),
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    return [lead_to_read(lead) for lead in session.exec(statement).all()]


def search_leads_page(session: Session, params: LeadSearchParams) -> LeadSearchPage:
    """Respuesta completa de página: items + totales + números de página."""
    total = count_leads(session, params)
    items = search_leads(session, params)
    # Deriva página actual y total de páginas del offset/limit
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
