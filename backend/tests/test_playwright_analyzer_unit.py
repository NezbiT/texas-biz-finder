"""Unit tests for SEO audit helpers (no browser required)."""

from backend.app.services.playwright_analyzer import _audit_seo, _parse_last_modified


def test_audit_seo_detects_missing_fields() -> None:
    html = "<html><head></head><body><p>No heading</p></body></html>"
    audit = _audit_seo(html, page_title=None)
    assert "Missing <title> tag" in audit.issues
    assert "Missing meta description" in audit.issues
    assert "Missing H1 heading" in audit.issues


def test_parse_last_modified_from_header() -> None:
    value = _parse_last_modified("Wed, 15 Jan 2025 12:00:00 GMT", "<html></html>")
    assert value == "Wed, 15 Jan 2025 12:00:00 GMT"