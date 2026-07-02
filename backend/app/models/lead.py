from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Lead(SQLModel, table=True):
    """Small Texas business lead with online-presence qualification."""

    __tablename__ = "leads"

    id: int | None = Field(default=None, primary_key=True)
    external_id: str = Field(index=True, unique=True)
    name: str = Field(index=True)
    city: str = Field(index=True)
    county: str | None = None
    state: str = Field(default="TX", index=True)
    zip_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    email: str | None = None
    industry: str | None = Field(default=None, index=True)
    employee_count: int | None = None
    website_url: str | None = None
    has_website: bool = False
    website_reachable: bool = False
    has_modern_website: bool = False
    website_tech_stack: str | None = None
    website_antiquity_years: int | None = None
    website_analysis_notes: str | None = None
    facebook_url: str | None = None
    instagram_url: str | None = None
    has_active_facebook: bool = False
    has_active_instagram: bool = False
    is_small_business: bool = True
    is_qualified: bool = Field(default=False, index=True)
    qualification_score: float = Field(default=0.0)
    qualification_notes: str | None = None
    sells_alcohol: bool = Field(default=False, index=True)
    alcohol_segment: str | None = None
    liquor_receipts_total: float | None = None
    wine_receipts_total: float | None = None
    beer_receipts_total: float | None = None
    total_receipts_total: float | None = None
    source: str = "texas_public_stub"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)