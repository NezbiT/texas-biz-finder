"""Tabla `website_analyses`: auditorías Playwright guardadas, ligadas a un lead."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    # Timestamps siempre en UTC
    return datetime.now(timezone.utc)


class WebsiteAnalysis(SQLModel, table=True):
    """Playwright-powered website audit saved for a lead."""

    __tablename__ = "website_analyses"

    id: int | None = Field(default=None, primary_key=True)     # autoincremental
    lead_id: int = Field(foreign_key="leads.id", index=True)   # a qué lead pertenece
    url: str                                                   # URL solicitada
    final_url: str | None = None                               # URL final tras redirects
    page_title: str | None = None                              # <title> de la página
    last_modified: str | None = None                           # header Last-Modified
    load_time_ms: float | None = None                          # tiempo de carga medido
    dom_content_loaded_ms: float | None = None                 # DOMContentLoaded medido
    technologies_json: str | None = None                       # lista JSON del stack detectado
    seo_title: str | None = None                               # metadatos SEO extraídos ↓
    seo_meta_description: str | None = None
    seo_h1: str | None = None
    seo_issues_json: str | None = None                         # lista JSON de problemas SEO
    summary: str | None = None                                 # resumen legible
    metrics_json: str | None = None                            # dict JSON de métricas extra
    status: str = Field(default="completed", index=True)       # completed | failed
    error_message: str | None = None                           # detalle si falló
    created_at: datetime = Field(default_factory=_utc_now)     # cuándo se corrió
