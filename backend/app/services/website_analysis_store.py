"""Persistencia de los registros WebsiteAnalysis (guardar, listar, aplicar al lead)."""

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
    """Fila SQLModel → respuesta de la API (des-serializando los campos JSON)."""
    # Las listas/dicts se guardan como TEXT JSON; aquí se decodifican con
    # tolerancia a corrupción (JSON inválido → valor vacío, no explota)
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

    # Copia campo a campo hacia el schema público
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
    """Guarda el resultado de un análisis profundo como fila nueva."""
    # Serializa listas/métricas a los campos *_json de la tabla
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
    session.refresh(record)   # recupera el id autogenerado
    return record


def list_analyses_for_lead(session: Session, lead_id: int) -> list[WebsiteAnalysis]:
    """Historial de análisis de un lead, del más reciente al más viejo."""
    statement = (
        select(WebsiteAnalysis)
        .where(WebsiteAnalysis.lead_id == lead_id)
        .order_by(desc(WebsiteAnalysis.created_at))
    )
    return list(session.exec(statement).all())


def apply_analysis_to_lead(session: Session, lead: Lead, result: DeepAnalysisResult) -> Lead:
    """Vuelca los hallazgos del análisis a los campos website_* del lead."""
    lead.website_url = result.final_url or result.url        # URL final tras redirects
    lead.has_website = True
    lead.website_reachable = result.status == "completed"    # ¿el sitio respondió?
    # Lista de tecnologías → texto separado por comas (o None si no hubo)
    lead.website_tech_stack = ", ".join(result.technologies) if result.technologies else None
    # Antigüedad estimada solo si vino como entero en las métricas
    antiquity = result.metrics.get("estimated_antiquity_years")
    lead.website_antiquity_years = int(antiquity) if isinstance(antiquity, int) else None
    lead.has_modern_website = bool(result.metrics.get("has_modern_website"))
    lead.website_analysis_notes = result.summary
    lead.updated_at = datetime.now(timezone.utc)   # marca de última actualización
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead
