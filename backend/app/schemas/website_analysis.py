"""Schemas de la API para búsqueda de sitios y análisis profundo con Playwright."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WebsiteSearchRequest(BaseModel):
    """Body de /website-search: nombre/ciudad opcionales (default: los del lead)."""
    business_name: str | None = None
    city: str | None = None
    max_results: int = Field(default=8, ge=1, le=15)   # candidatos a devolver


class WaybackInfo(BaseModel):
    """Historial del dominio en Internet Archive (espejo del dataclass del servicio)."""
    domain: str
    first_seen: str | None = None            # primera captura (YYYY-MM-DD)
    last_seen: str | None = None             # última captura
    snapshot_count: int = 0                  # nº de capturas
    age_years: int | None = None             # edad estimada del sitio
    timeline_url: str                        # link a la línea de tiempo
    first_snapshot_url: str | None = None    # links directos a capturas
    last_snapshot_url: str | None = None
    available: bool = False                  # ¿hay historial?


class WebsiteSearchResult(BaseModel):
    """Un candidato de la búsqueda DuckDuckGo (con su Wayback adjunto)."""
    title: str
    url: str
    snippet: str
    wayback: WaybackInfo | None = None


class WebsiteSearchResponse(BaseModel):
    """Respuesta de /website-search: la query usada + los candidatos."""
    query: str
    results: list[WebsiteSearchResult]


class WebsiteAnalyzeRequest(BaseModel):
    """Body de /website-analyze: la URL y si volcar el resultado al lead."""
    url: str
    save_to_lead: bool = True


class WebsiteUrlUpdateRequest(BaseModel):
    """Body de PATCH /website-url: solo la URL a guardar."""
    url: str


class WebsiteAnalysisRead(BaseModel):
    """Un análisis completo tal como lo consume el frontend."""
    id: int
    lead_id: int                          # a qué lead pertenece
    url: str                              # URL analizada
    final_url: str | None                 # tras redirects
    page_title: str | None
    last_modified: str | None
    load_time_ms: float | None            # métricas de rendimiento
    dom_content_loaded_ms: float | None
    technologies: list[str]               # stack detectado
    seo_title: str | None                 # radiografía SEO ↓
    seo_meta_description: str | None
    seo_h1: str | None
    seo_issues: list[str]
    summary: str | None                   # resumen de venta
    metrics: dict[str, object]            # métricas extra (incluye wayback)
    status: str                           # completed | failed
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisStatusResponse(BaseModel):
    """Estado del lock global de Playwright (para el aviso "ocupado" de la UI)."""
    busy: bool
    lead_id: int | None = None
    url: str | None = None
