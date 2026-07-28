"""Selección unificada del backend de datos (csv/DuckDB | supabase | sqlite).

Un solo lugar para search/export/stats — evita que export/json use un backend
distinto al de la búsqueda principal.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from backend.app.config import settings
from backend.app.models.lead import Lead
from backend.app.schemas.lead import LeadRead, LeadSearchPage, LeadSearchParams
from backend.app.services import csv_lead_store
from backend.app.services.lead_research_resolver import merge_sqlite_website_fields
from backend.app.services.lead_search import (
    search_leads as execute_lead_search,
    search_leads_page as execute_lead_search_page,
)


def data_ready() -> bool:
    """¿Hay datos legibles con el backend configurado?"""
    if settings.use_csv_backend:
        return csv_lead_store.processed_data_ready()
    # sqlite / supabase: se considera listo si la app arrancó (tablas existen)
    return True


def backend_not_ready_detail() -> str:
    if settings.use_csv_backend:
        return (
            "Processed DuckDB not found. On the API host run: "
            "python -m scripts.bulk_pipeline process "
            f"(expected: {settings.processed_duckdb_path})"
        )
    return f"Data backend '{settings.data_backend}' is not ready"


def require_data_ready() -> None:
    if not data_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=backend_not_ready_detail(),
        )


def lead_stats(session: Session) -> dict[str, int]:
    """Totales del header según el backend activo (sin fallback silencioso a demo)."""
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
            "total": int(total),
            "qualified": int(qualified),
            "small_business": int(small_business),
            "sells_alcohol": int(sells_alcohol),
        }

    if settings.use_csv_backend:
        if not csv_lead_store.processed_data_ready():
            # Stats en 0 + el cliente puede mirar /health; no inventar demo
            return {"total": 0, "qualified": 0, "small_business": 0, "sells_alcohol": 0}
        return csv_lead_store.lead_stats()

    # sqlite legacy (tests / datasets chicos reales)
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
        "total": int(total),
        "qualified": int(qualified),
        "small_business": int(small_business),
        "sells_alcohol": int(sells_alcohol),
    }


def search_leads_page(session: Session, params: LeadSearchParams) -> LeadSearchPage:
    """Búsqueda paginada unificada."""
    if settings.use_supabase_backend:
        return execute_lead_search_page(session, params)

    if settings.use_csv_backend:
        require_data_ready()
        page = csv_lead_store.search_leads_page(params)
        page.items = merge_sqlite_website_fields(session, page.items)
        return page

    return execute_lead_search_page(session, params)


def search_leads_list(session: Session, params: LeadSearchParams) -> list[LeadRead]:
    """Lista plana para export (misma fuente que la búsqueda)."""
    if settings.use_supabase_backend:
        return execute_lead_search(session, params)

    if settings.use_csv_backend:
        require_data_ready()
        page = csv_lead_store.search_leads_page(params)
        items = merge_sqlite_website_fields(session, page.items)
        return list(items)

    return execute_lead_search(session, params)
