"""Unit tests for lead qualification logic."""

from scripts.common.qualification import qualify_lead


def test_qualifies_small_business_without_online_presence() -> None:
    result = qualify_lead(
        website_url=None,
        facebook_url=None,
        instagram_url=None,
        employee_count=10,
    )
    assert result.is_small_business is True
    assert result.has_website is False
    assert result.is_qualified is True
    assert result.qualification_score == 100.0


def test_excludes_large_enterprise() -> None:
    result = qualify_lead(
        website_url=None,
        facebook_url=None,
        instagram_url=None,
        employee_count=500,
    )
    assert result.is_small_business is False
    assert result.is_qualified is False
    assert result.qualification_score == 0.0


def test_rejects_legacy_website_as_modern() -> None:
    result = qualify_lead(
        website_url="https://sites.google.com/view/old-page",
        facebook_url=None,
        instagram_url=None,
        employee_count=8,
    )
    assert result.has_modern_website is False
    assert result.is_qualified is True


def test_disqualifies_when_modern_web_and_social_present() -> None:
    result = qualify_lead(
        website_url="https://riograndelandscaping.example",
        facebook_url="https://facebook.com/riograndelandscaping",
        instagram_url="https://instagram.com/riograndelandscaping",
        employee_count=6,
    )
    assert result.has_modern_website is True
    assert result.has_active_facebook is True
    assert result.has_active_instagram is True
    assert result.is_qualified is False