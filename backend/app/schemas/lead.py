# Schemas Pydantic de leads: la forma exacta de requests/responses de /api/leads
from datetime import datetime

from pydantic import BaseModel, Field


class LeadRead(BaseModel):
    """Un lead tal como lo devuelve la API (la forma que consume el frontend)."""
    id: int                                     # id interno
    external_id: str                            # taxpayer number (clave estable)
    name: str                                   # razón social
    city: str
    county: str | None
    state: str
    zip_code: str | None
    latitude: float | None = None               # coordenadas (si se geocodificó)
    longitude: float | None = None
    distance_miles: float | None = None         # distancia (solo búsqueda por radio)
    phone: str | None
    email: str | None
    industry: str | None
    employee_count: int | None
    website_url: str | None                     # señales digitales ↓
    has_website: bool
    website_reachable: bool
    has_modern_website: bool
    website_tech_stack: str | None = None
    website_antiquity_years: int | None = None
    website_analysis_notes: str | None = None
    facebook_url: str | None                    # redes sociales
    instagram_url: str | None
    has_active_facebook: bool
    has_active_instagram: bool
    is_small_business: bool                     # clasificación
    is_qualified: bool
    qualification_score: float
    qualification_notes: str | None
    source: str                                 # origen del dato
    created_at: datetime
    updated_at: datetime

    # from_attributes: permite construirlo directo desde el modelo SQLModel
    model_config = {"from_attributes": True}


class LeadSearchParams(BaseModel):
    """Filtros de búsqueda validados (los mismos límites que la UI)."""
    q: str | None = None                                       # texto libre
    city: str | None = None
    zip_code: str | None = None
    radius_miles: float | None = Field(default=None, ge=1, le=50)   # radio 1-50 mi
    county: str | None = None
    industry: str | None = None
    qualified_only: bool = True                                # defaults de la UI
    small_business_only: bool = True
    sells_alcohol_only: bool = False
    limit: int = Field(default=50, ge=1, le=500)               # tamaño de página
    offset: int = Field(default=0, ge=0)                       # desplazamiento


class LeadSearchPage(BaseModel):
    """Página de resultados con los totales para pintar la paginación."""
    items: list[LeadRead]   # los leads de esta página
    total: int              # total de coincidencias
    limit: int              # eco de los parámetros usados
    offset: int
    page: int               # página actual calculada
    pages: int              # total de páginas


class LeadExport(BaseModel):
    """Respuesta del export JSON (con marca de tiempo)."""
    exported_at: datetime
    total: int
    leads: list[LeadRead]


class LeadMarkRequest(BaseModel):
    """Body de PATCH /mark: override manual de la calificación."""
    is_qualified: bool
    qualification_notes: str | None = None   # opcional: por qué se marcó


class LeadUpsertRequest(BaseModel):
    """Body de POST /upsert: crear/actualizar por external_id (todo lo demás opcional)."""
    external_id: str            # la clave — obligatoria siempre
    name: str | None = None     # obligatorios solo al CREAR (se valida en el endpoint)
    city: str | None = None
    county: str | None = None
    zip_code: str | None = None
    phone: str | None = None
    email: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    website_url: str | None = None
    facebook_url: str | None = None
    instagram_url: str | None = None
