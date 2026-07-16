"""Resuelve leads para el research de sitios web, uniendo los dos mundos:

- Los leads masivos viven en DuckDB (solo lectura, regenerable).
- El research (URL guardada, análisis) se PERSISTE en SQLite/Postgres.
Este módulo mapea entre ambos usando external_id como clave estable.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlmodel import Session, select

from backend.app.config import settings
from backend.app.models.lead import Lead
from backend.app.schemas.lead import LeadRead
from backend.app.services import csv_lead_store


def ensure_sqlite_lead(session: Session, bulk: LeadRead) -> Lead:
    """Busca (o crea) la fila SQLite espejo de un lead bulk, por external_id."""
    existing = session.exec(select(Lead).where(Lead.external_id == bulk.external_id)).first()
    if existing is not None:
        return existing   # ya existe el espejo → usarlo

    # Copia los campos identitarios del lead bulk a la fila persistente
    lead = Lead(
        external_id=bulk.external_id,
        name=bulk.name,
        city=bulk.city,
        county=bulk.county,
        state=bulk.state,
        zip_code=bulk.zip_code,
        industry=bulk.industry,
        is_small_business=bulk.is_small_business,
        is_qualified=bulk.is_qualified,
        qualification_score=bulk.qualification_score,
        qualification_notes=bulk.qualification_notes,
        source=bulk.source,
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)   # recupera el id autogenerado
    return lead


def resolve_lead_for_research(session: Session, lead_id: int) -> Lead:
    """id de la API → fila Lead donde persistir URL/análisis (según backend)."""
    # Backend Supabase: los leads ya viven en la misma base → lookup directo
    if settings.use_supabase_backend:
        lead = session.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        return lead

    # Backend bulk (CSV/DuckDB): buscar el lead bulk y asegurar su espejo SQLite
    if settings.use_csv_backend and csv_lead_store.processed_data_ready():
        bulk = csv_lead_store.get_lead_by_id(lead_id)
        if bulk is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        return ensure_sqlite_lead(session, bulk)

    # Fallback: modo SQLite puro (dataset chico ingestado directo)
    lead = session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


def lead_name_and_city(session: Session, lead_id: int) -> tuple[str, str]:
    """Nombre y ciudad del negocio (los insumos de la búsqueda DuckDuckGo)."""
    # Misma lógica de resolución por backend que arriba
    if settings.use_supabase_backend:
        lead = session.get(Lead, lead_id)
        if lead is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        return lead.name.strip(), lead.city.strip()

    if settings.use_csv_backend and csv_lead_store.processed_data_ready():
        bulk = csv_lead_store.get_lead_by_id(lead_id)
        if bulk is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
        return bulk.name.strip(), bulk.city.strip()

    lead = session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead.name.strip(), lead.city.strip()


def merge_sqlite_website_fields(session: Session, items: list[LeadRead]) -> list[LeadRead]:
    """Superpone el research guardado en SQLite sobre los leads bulk de DuckDB.

    Así el usuario ve la URL/análisis que guardó aunque el listado venga del
    dataset masivo regenerable."""
    if not items:
        return items

    # Un solo SELECT con IN por todos los external_id de la página
    external_ids = [item.external_id for item in items]
    rows = session.exec(select(Lead).where(Lead.external_id.in_(external_ids))).all()
    by_external_id = {row.external_id: row for row in rows}   # índice por clave

    merged: list[LeadRead] = []
    for item in items:
        sqlite_lead = by_external_id.get(item.external_id)
        # Sin espejo o sin URL guardada → el lead bulk pasa sin cambios
        if sqlite_lead is None or not sqlite_lead.website_url:
            merged.append(item)
            continue

        # Con research guardado → sobreescribe los campos website_* del bulk
        notes = sqlite_lead.website_analysis_notes or item.website_analysis_notes
        merged.append(
            item.model_copy(
                update={
                    "website_url": sqlite_lead.website_url,
                    "has_website": sqlite_lead.has_website,
                    "website_reachable": sqlite_lead.website_reachable,
                    "has_modern_website": sqlite_lead.has_modern_website,
                    "website_tech_stack": sqlite_lead.website_tech_stack,
                    "website_antiquity_years": sqlite_lead.website_antiquity_years,
                    "website_analysis_notes": notes,
                    "updated_at": sqlite_lead.updated_at,
                }
            )
        )
    return merged
