"""Convierte filas Lead (modelo interno) en LeadRead (respuesta de la API).

Compartido por los tres backends de datos (SQLite, Supabase y bulk CSV/DuckDB)
para que la API devuelva siempre la misma forma.
"""

from __future__ import annotations

from backend.app.models.lead import Lead
from backend.app.schemas.lead import LeadRead


def alcohol_notes(lead: Lead) -> str | None:
    """Genera la nota "TABC alcohol sales…" con los totales de recibos."""
    if not lead.sells_alcohol:
        return None                                   # sin TABC no hay nota
    segment = lead.alcohol_segment or "unknown"       # bar / restaurant / unknown
    total = float(lead.total_receipts_total or 0)     # acumulado de recibos
    # Nota legible con el desglose licor/vino/cerveza formateado con comas
    return (
        f"TABC alcohol sales ({segment}); cumulative total_receipts=${total:,.0f} "
        f"(liquor=${float(lead.liquor_receipts_total or 0):,.0f}, "
        f"wine=${float(lead.wine_receipts_total or 0):,.0f}, "
        f"beer=${float(lead.beer_receipts_total or 0):,.0f})"
    )


def display_analysis_notes(lead: Lead) -> str | None:
    """Prioriza las notas del análisis de sitio; si no hay, la nota TABC."""
    if lead.website_analysis_notes:
        return lead.website_analysis_notes
    return alcohol_notes(lead)


def lead_to_read(lead: Lead, *, distance_miles: float | None = None) -> LeadRead:
    """Lead → LeadRead, inyectando distancia (búsqueda por radio) y notas."""
    return LeadRead.model_validate(lead).model_copy(
        update={
            "distance_miles": distance_miles,
            "website_analysis_notes": display_analysis_notes(lead),
        }
    )
