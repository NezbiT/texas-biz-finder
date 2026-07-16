# Modelo de tabla `leads`: un negocio pequeño de Texas con su calificación
# de presencia digital. SQLModel = SQLAlchemy + Pydantic en una sola clase.
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    # Timestamps siempre en UTC (evita líos de zona horaria)
    return datetime.now(timezone.utc)


class Lead(SQLModel, table=True):
    """Small Texas business lead with online-presence qualification."""

    __tablename__ = "leads"

    id: int | None = Field(default=None, primary_key=True)      # autoincremental
    external_id: str = Field(index=True, unique=True)           # taxpayer number (clave estable entre backends)
    name: str = Field(index=True)                               # razón social
    city: str = Field(index=True)                               # ciudad
    county: str | None = None                                   # condado
    state: str = Field(default="TX", index=True)                # estado (siempre TX)
    zip_code: str | None = None                                 # código postal
    latitude: float | None = None                               # coordenadas para radio
    longitude: float | None = None
    phone: str | None = None                                    # contacto
    email: str | None = None
    industry: str | None = Field(default=None, index=True)      # giro del negocio
    employee_count: int | None = None                           # tamaño (si se conoce)
    website_url: str | None = None                              # sitio web guardado
    has_website: bool = False                                   # señales digitales ↓
    website_reachable: bool = False                             # ¿el sitio responde?
    has_modern_website: bool = False                            # ¿parece moderno?
    website_tech_stack: str | None = None                       # stack detectado
    website_antiquity_years: int | None = None                  # antigüedad estimada
    website_analysis_notes: str | None = None                   # resumen del análisis
    facebook_url: str | None = None                             # redes sociales
    instagram_url: str | None = None
    has_active_facebook: bool = False
    has_active_instagram: bool = False
    is_small_business: bool = True                              # clasificación pequeño negocio
    is_qualified: bool = Field(default=False, index=True)       # ¿lead calificado?
    qualification_score: float = Field(default=0.0)             # puntaje 0-100
    qualification_notes: str | None = None                      # razones del puntaje
    sells_alcohol: bool = Field(default=False, index=True)      # cruce TABC ↓
    alcohol_segment: str | None = None                          # bar / restaurant
    liquor_receipts_total: float | None = None                  # totales de recibos
    wine_receipts_total: float | None = None
    beer_receipts_total: float | None = None
    total_receipts_total: float | None = None
    source: str = "texas_public_stub"                           # origen del dato
    created_at: datetime = Field(default_factory=_utc_now)      # timestamps UTC
    updated_at: datetime = Field(default_factory=_utc_now)
