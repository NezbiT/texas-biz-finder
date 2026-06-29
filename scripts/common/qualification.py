"""Lead qualification heuristics — framework-independent, unit-testable."""

from dataclasses import dataclass

from scripts.common.website_analysis import WebsiteAnalysis, analyze_website_url_only

SOCIAL_PLACEHOLDER_PATTERNS = (
    "facebook.com/pages/category",
    "instagram.com/explore",
    "placeholder",
    "coming-soon",
)


@dataclass(frozen=True)
class QualificationResult:
    has_website: bool
    website_reachable: bool
    has_modern_website: bool
    website_tech_stack: str | None
    website_antiquity_years: int | None
    website_analysis_notes: str | None
    has_active_facebook: bool
    has_active_instagram: bool
    is_small_business: bool
    is_qualified: bool
    qualification_score: float
    notes: str


def is_small_business(employee_count: int | None, max_employees: int = 50) -> bool:
    """Focus on small businesses; large enterprises are excluded."""
    if employee_count is None:
        return True
    return employee_count <= max_employees


def _normalize_url(url: str | None) -> str:
    return (url or "").strip().lower()


def _is_social_placeholder(url: str) -> bool:
    return any(pattern in url for pattern in SOCIAL_PLACEHOLDER_PATTERNS)


def has_active_social(url: str | None) -> bool:
    """Active social presence requires a real profile URL, not a placeholder."""
    normalized = _normalize_url(url)
    if not normalized:
        return False
    if _is_social_placeholder(normalized):
        return False
    return "facebook.com" in normalized or "instagram.com" in normalized


def _website_fields(analysis: WebsiteAnalysis) -> dict[str, object]:
    stack = ", ".join(analysis.tech_stack) if analysis.tech_stack else None
    return {
        "has_website": analysis.has_website,
        "website_reachable": analysis.website_reachable,
        "has_modern_website": analysis.has_modern_website,
        "website_tech_stack": stack,
        "website_antiquity_years": analysis.estimated_antiquity_years,
        "website_analysis_notes": analysis.analysis_notes,
    }


def qualify_lead(
    *,
    website_url: str | None,
    facebook_url: str | None,
    instagram_url: str | None,
    employee_count: int | None,
    max_employees: int = 50,
    website_analysis: WebsiteAnalysis | None = None,
) -> QualificationResult:
    """Score a lead: qualified when small biz lacks modern web + active social."""
    analysis = website_analysis or analyze_website_url_only(website_url)
    website = _website_fields(analysis)

    active_fb = has_active_social(facebook_url)
    active_ig = has_active_social(instagram_url)
    small = is_small_business(employee_count, max_employees)

    score = 0.0
    notes: list[str] = []

    if not website["has_modern_website"]:
        score += 40.0
        if not website["has_website"]:
            notes.append("No website detected")
        else:
            notes.append("Website present but not modern")
    if not active_fb:
        score += 30.0
        notes.append("No active Facebook presence")
    if not active_ig:
        score += 30.0
        notes.append("No active Instagram presence")
    if not small:
        score = 0.0
        notes = ["Excluded: large enterprise (employee count above threshold)"]

    is_qualified = small and not website["has_modern_website"] and not active_fb and not active_ig

    return QualificationResult(
        has_website=bool(website["has_website"]),
        website_reachable=bool(website["website_reachable"]),
        has_modern_website=bool(website["has_modern_website"]),
        website_tech_stack=website["website_tech_stack"],  # type: ignore[arg-type]
        website_antiquity_years=website["website_antiquity_years"],  # type: ignore[arg-type]
        website_analysis_notes=website["website_analysis_notes"],  # type: ignore[arg-type]
        has_active_facebook=active_fb,
        has_active_instagram=active_ig,
        is_small_business=small,
        is_qualified=is_qualified,
        qualification_score=round(score, 1),
        notes="; ".join(notes),
    )