"""Map Lead rows to API LeadRead (shared by SQLite, Supabase, and bulk backends)."""

from __future__ import annotations

from backend.app.models.lead import Lead
from backend.app.schemas.lead import LeadRead


def alcohol_notes(lead: Lead) -> str | None:
    if not lead.sells_alcohol:
        return None
    segment = lead.alcohol_segment or "unknown"
    total = float(lead.total_receipts_total or 0)
    return (
        f"TABC alcohol sales ({segment}); cumulative total_receipts=${total:,.0f} "
        f"(liquor=${float(lead.liquor_receipts_total or 0):,.0f}, "
        f"wine=${float(lead.wine_receipts_total or 0):,.0f}, "
        f"beer=${float(lead.beer_receipts_total or 0):,.0f})"
    )


def display_analysis_notes(lead: Lead) -> str | None:
    if lead.website_analysis_notes:
        return lead.website_analysis_notes
    return alcohol_notes(lead)


def lead_to_read(lead: Lead, *, distance_miles: float | None = None) -> LeadRead:
    return LeadRead.model_validate(lead).model_copy(
        update={
            "distance_miles": distance_miles,
            "website_analysis_notes": display_analysis_notes(lead),
        }
    )