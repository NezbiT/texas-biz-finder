"""Integration tests for lead processing pipeline."""

from sqlmodel import Session, select

from backend.app.models.lead import Lead


def test_process_leads_persists_qualified_small_businesses(isolated_db) -> None:
    from scripts.process_leads import process_leads

    stats = process_leads()
    assert stats["processed"] == 6
    assert stats["skipped_large"] == 1
    assert stats["qualified"] >= 3

    with Session(isolated_db.engine) as session:
        leads = list(session.exec(select(Lead)).all())
        qualified = [lead for lead in leads if lead.is_qualified]
        large = [lead for lead in leads if lead.name == "Metroplex Logistics Corp"]

    assert len(qualified) >= 3
    assert len(large) == 1
    assert large[0].is_small_business is False
    assert large[0].is_qualified is False