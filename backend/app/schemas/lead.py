from datetime import datetime

from pydantic import BaseModel, Field


class LeadRead(BaseModel):
    id: int
    external_id: str
    name: str
    city: str
    county: str | None
    state: str
    zip_code: str | None
    latitude: float | None = None
    longitude: float | None = None
    distance_miles: float | None = None
    phone: str | None
    email: str | None
    industry: str | None
    employee_count: int | None
    website_url: str | None
    has_website: bool
    website_reachable: bool
    has_modern_website: bool
    website_tech_stack: str | None = None
    website_antiquity_years: int | None = None
    website_analysis_notes: str | None = None
    facebook_url: str | None
    instagram_url: str | None
    has_active_facebook: bool
    has_active_instagram: bool
    is_small_business: bool
    is_qualified: bool
    qualification_score: float
    qualification_notes: str | None
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadSearchParams(BaseModel):
    q: str | None = None
    city: str | None = None
    zip_code: str | None = None
    radius_miles: float | None = Field(default=None, ge=1, le=50)
    county: str | None = None
    industry: str | None = None
    qualified_only: bool = True
    small_business_only: bool = True
    sells_alcohol_only: bool = False
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class LeadSearchPage(BaseModel):
    items: list[LeadRead]
    total: int
    limit: int
    offset: int
    page: int
    pages: int


class LeadExport(BaseModel):
    exported_at: datetime
    total: int
    leads: list[LeadRead]


class LeadMarkRequest(BaseModel):
    is_qualified: bool
    qualification_notes: str | None = None


class LeadUpsertRequest(BaseModel):
    external_id: str
    name: str | None = None
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