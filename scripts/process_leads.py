"""Process staged Texas data, qualify leads, and persist to SQLite."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from backend.app.config import settings
from backend.app.database import engine, init_db
from backend.app.models.lead import Lead
from scripts.common.data_sources import RawBusinessRecord, load_texas_public_stub
from scripts.common.geocoding import geocode_lead
from scripts.common.qualification import qualify_lead
from scripts.common.website_analysis import analyze_website


def process_leads(
    staging_path: Path | None = None,
    *,
    max_employees: int | None = None,
) -> dict[str, int]:
    """Qualify raw records and upsert leads into the local SQLite database."""
    init_db()
    threshold = max_employees or settings.max_employees_small_biz
    records = load_texas_public_stub(staging_path)

    inserted = 0
    updated = 0
    qualified = 0
    skipped_large = 0

    with Session(engine) as session:
        for record in records:
            result = _qualify_record(record, threshold)
            if not result.is_small_business:
                skipped_large += 1

            existing = session.exec(
                select(Lead).where(Lead.external_id == record.external_id)
            ).first()

            lead = _to_lead(record, result)
            if existing:
                for field, value in lead.model_dump(exclude={"id", "created_at"}).items():
                    setattr(existing, field, value)
                existing.updated_at = datetime.now(timezone.utc)
                session.add(existing)
                updated += 1
                if existing.is_qualified:
                    qualified += 1
            else:
                session.add(lead)
                inserted += 1
                if lead.is_qualified:
                    qualified += 1

        session.commit()

    return {
        "processed": len(records),
        "inserted": inserted,
        "updated": updated,
        "qualified": qualified,
        "skipped_large": skipped_large,
    }


def _qualify_record(record: RawBusinessRecord, max_employees: int):
    website = analyze_website(record.website_url)
    return qualify_lead(
        website_url=record.website_url,
        facebook_url=record.facebook_url,
        instagram_url=record.instagram_url,
        employee_count=record.employee_count,
        max_employees=max_employees,
        website_analysis=website,
    )


def _to_lead(record: RawBusinessRecord, result) -> Lead:
    now = datetime.now(timezone.utc)
    latitude, longitude = geocode_lead(record.city, record.zip_code)
    return Lead(
        external_id=record.external_id,
        name=record.name,
        city=record.city,
        county=record.county,
        state="TX",
        zip_code=record.zip_code,
        latitude=latitude,
        longitude=longitude,
        phone=record.phone,
        email=record.email,
        industry=record.industry,
        employee_count=record.employee_count,
        website_url=record.website_url,
        has_website=result.has_website,
        website_reachable=result.website_reachable,
        has_modern_website=result.has_modern_website,
        website_tech_stack=result.website_tech_stack,
        website_antiquity_years=result.website_antiquity_years,
        website_analysis_notes=result.website_analysis_notes,
        facebook_url=record.facebook_url,
        instagram_url=record.instagram_url,
        has_active_facebook=result.has_active_facebook,
        has_active_instagram=result.has_active_instagram,
        is_small_business=result.is_small_business,
        is_qualified=result.is_qualified,
        qualification_score=result.qualification_score,
        qualification_notes=result.notes,
        source="texas_public_stub",
        created_at=now,
        updated_at=now,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process and qualify Texas business leads")
    parser.add_argument(
        "--staging",
        type=Path,
        default=None,
        help="Optional staged JSON from ingest_texas_data.py",
    )
    args = parser.parse_args()
    stats = process_leads(args.staging)
    print(
        "Processed {processed} records | inserted={inserted} updated={updated} "
        "qualified={qualified} skipped_large={skipped_large}".format(**stats)
    )


if __name__ == "__main__":
    main()