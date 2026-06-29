"""Re-analyze website stacks for leads stored in SQLite."""

from __future__ import annotations

import argparse

from sqlmodel import Session, select

from backend.app.database import engine, init_db
from backend.app.models.lead import Lead
from scripts.common.qualification import qualify_lead
from scripts.common.website_analysis import analyze_website


def verify_websites(*, fetch: bool = True) -> dict[str, int]:
    init_db()
    analyzed = 0
    with Session(engine) as session:
        leads = list(session.exec(select(Lead).where(Lead.website_url.is_not(None))).all())
        for lead in leads:
            website = analyze_website(lead.website_url, fetch=fetch)
            result = qualify_lead(
                website_url=lead.website_url,
                facebook_url=lead.facebook_url,
                instagram_url=lead.instagram_url,
                employee_count=lead.employee_count,
                website_analysis=website,
            )
            lead.has_website = result.has_website
            lead.website_reachable = result.website_reachable
            lead.has_modern_website = result.has_modern_website
            lead.website_tech_stack = result.website_tech_stack
            lead.website_antiquity_years = result.website_antiquity_years
            lead.website_analysis_notes = result.website_analysis_notes
            lead.is_qualified = result.is_qualified
            lead.qualification_score = result.qualification_score
            lead.qualification_notes = result.notes
            session.add(lead)
            analyzed += 1
        session.commit()
    return {"analyzed": analyzed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify website stacks for stored leads")
    parser.add_argument("--no-fetch", action="store_true", help="URL-only analysis")
    args = parser.parse_args()
    stats = verify_websites(fetch=not args.no_fetch)
    print(f"Analyzed {stats['analyzed']} leads with website URLs")


if __name__ == "__main__":
    main()