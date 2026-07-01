"""Website stack detection and antiquity estimation — framework-independent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

LEGACY_URL_PATTERNS = (
    "geocities",
    "angelfire",
    "tripod",
    "freewebs",
    "wixsite.com/free",
    "godaddysites.com",
    "sites.google.com/view",
)

NON_FETCHABLE_HOST_PATTERNS = (
    ".example",
    "localhost",
    "127.0.0.1",
)

TECH_PATTERNS: list[tuple[str, str]] = [
    ("WordPress", r"wp-content|wordpress|generator\"?\s*content=\"?WordPress"),
    ("Wix", r"wixstatic|wix\.com|X-Wix"),
    ("Squarespace", r"squarespace|static\.squarespace"),
    ("Weebly", r"weebly"),
    ("Joomla", r"joomla|/components/com_"),
    ("Drupal", r"drupal|Drupal\.settings"),
    ("Shopify", r"cdn\.shopify|shopify-section"),
    ("React", r"react\.production|__NEXT_DATA__|data-reactroot"),
    ("Vue", r"vue\.js|vue\.runtime|data-v-"),
    ("Angular", r"ng-version|angular\.min\.js"),
    ("Bootstrap 5", r"bootstrap@5|bootstrap/5"),
    ("Bootstrap 4", r"bootstrap/4|bootstrap\.min\.css\?.*4"),
    ("Bootstrap 3", r"bootstrap/3|bootstrap\.min\.css\?.*3"),
    ("Bootstrap 2", r"bootstrap/2"),
    ("jQuery 3", r"jquery-3\.|jquery/3\.|jquery\.min\.js\?.*3"),
    ("jQuery 2", r"jquery-2\.|jquery/2\."),
    ("jQuery 1", r"jquery-1\.|jquery/1\.|jquery\.min\.js"),
    ("Adobe Dreamweaver", r"dreamweaver|DWLayout"),
    ("Microsoft FrontPage", r"frontpage|fpstyle|mso-"),
    ("Adobe Flash", r"\.swf|shockwave-flash|application/x-shockwave"),
    ("Google Sites", r"sites\.google\.com"),
    ("GoDaddy Builder", r"godaddysites|secureservercdn"),
]

LEGACY_HTML_PATTERNS: list[tuple[str, int]] = [
    ("table-based layout", r"<table[^>]+width", 8),
    ("deprecated <font> tag", r"<font\b", 10),
    ("deprecated <center> tag", r"<center\b", 10),
    ("<marquee> tag", r"<marquee\b", 12),
    ("IE conditional comments", r"\[if\s+lte\s+ie|<!--\[if", 8),
    ("inline framesets", r"<frameset\b", 12),
    ("missing viewport meta", r"viewport", -5),
]


@dataclass(frozen=True)
class WebsiteAnalysis:
    has_website: bool
    website_reachable: bool
    has_modern_website: bool
    tech_stack: tuple[str, ...]
    estimated_antiquity_years: int | None
    analysis_notes: str


def should_fetch_website(website_url: str | None) -> bool:
    """Skip network fetch for stub/local domains."""
    url = (website_url or "").strip().lower()
    if not url:
        return False
    return not any(pattern in url for pattern in NON_FETCHABLE_HOST_PATTERNS)


def _normalize_url(url: str | None) -> str:
    return (url or "").strip()


def _ensure_scheme(url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def _detect_tech_stack(content: str, headers: dict[str, str]) -> list[str]:
    haystack = content.lower()
    header_blob = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
    detected: list[str] = []
    for name, pattern in TECH_PATTERNS:
        if re.search(pattern, haystack, re.IGNORECASE) or re.search(
            pattern, header_blob, re.IGNORECASE
        ):
            detected.append(name)
    return detected


def _extract_copyright_year(content: str) -> int | None:
    matches = re.findall(r"(?:©|copyright)\s*(?:19|20)\d{2}", content, re.IGNORECASE)
    years: list[int] = []
    for match in matches:
        year_match = re.search(r"(19|20)\d{2}", match)
        if year_match:
            years.append(int(year_match.group(0)))
    return max(years) if years else None


def _estimate_antiquity_years(
    *,
    content: str,
    tech_stack: list[str],
    uses_https: bool,
    copyright_year: int | None,
) -> int | None:
    current_year = datetime.now(timezone.utc).year
    scores: list[int] = []

    if copyright_year and copyright_year < current_year:
        scores.append(current_year - copyright_year)

    legacy_tech = {
        "jQuery 1": 10,
        "jQuery 2": 6,
        "Bootstrap 2": 12,
        "Bootstrap 3": 8,
        "Adobe Flash": 15,
        "Microsoft FrontPage": 18,
        "Adobe Dreamweaver": 15,
        "Google Sites": 10,
        "GoDaddy Builder": 6,
    }
    for tech in tech_stack:
        if tech in legacy_tech:
            scores.append(legacy_tech[tech])

    for label, pattern, years in LEGACY_HTML_PATTERNS:
        found = bool(re.search(pattern, content, re.IGNORECASE))
        if label == "missing viewport meta":
            if not found:
                scores.append(abs(years))
        elif found:
            scores.append(years)

    if not uses_https:
        scores.append(4)

    if not scores:
        return 0 if tech_stack else None
    return max(scores)


def _is_modern_from_signals(
    *,
    uses_https: bool,
    tech_stack: list[str],
    antiquity_years: int | None,
    content: str,
    url: str,
) -> bool:
    if any(pattern in url.lower() for pattern in LEGACY_URL_PATTERNS):
        return False
    if "facebook.com" in url or "instagram.com" in url:
        return False
    if not uses_https:
        return False

    modern_stack = {"React", "Vue", "Angular", "Bootstrap 5", "Shopify", "Squarespace"}
    if any(tech in modern_stack for tech in tech_stack):
        return antiquity_years is None or antiquity_years <= 4

    has_viewport = bool(re.search(r"viewport", content, re.IGNORECASE))
    if not has_viewport:
        return False

    if antiquity_years is not None and antiquity_years > 5:
        return False

    legacy_only = {"jQuery 1", "Microsoft FrontPage", "Adobe Flash", "Google Sites"}
    if tech_stack and all(tech in legacy_only for tech in tech_stack):
        return False

    return antiquity_years is None or antiquity_years <= 5


def analyze_website_content(
    *,
    website_url: str,
    html: str,
    final_url: str | None = None,
    headers: dict[str, str] | None = None,
) -> WebsiteAnalysis:
    """Analyze fetched HTML for stack, reachability, and antiquity."""
    resolved_url = final_url or website_url
    parsed = urlparse(resolved_url)
    uses_https = parsed.scheme == "https"
    header_map = headers or {}

    tech_stack = _detect_tech_stack(html, header_map)
    copyright_year = _extract_copyright_year(html)
    antiquity = _estimate_antiquity_years(
        content=html,
        tech_stack=tech_stack,
        uses_https=uses_https,
        copyright_year=copyright_year,
    )
    is_modern = _is_modern_from_signals(
        uses_https=uses_https,
        tech_stack=tech_stack,
        antiquity_years=antiquity,
        content=html,
        url=resolved_url,
    )

    notes: list[str] = []
    if tech_stack:
        notes.append("Stack: " + ", ".join(tech_stack))
    if antiquity is not None:
        if antiquity == 0:
            notes.append("Estimated implementation: current")
        else:
            notes.append(f"Estimated antiquity: ~{antiquity} years")
    if copyright_year:
        notes.append(f"Copyright year: {copyright_year}")
    if not is_modern:
        notes.append("Implementation appears legacy or outdated")
    else:
        notes.append("Implementation appears modern")

    return WebsiteAnalysis(
        has_website=True,
        website_reachable=True,
        has_modern_website=is_modern,
        tech_stack=tuple(tech_stack),
        estimated_antiquity_years=antiquity,
        analysis_notes="; ".join(notes),
    )


def analyze_website_url_only(website_url: str | None) -> WebsiteAnalysis:
    """Fast URL-only analysis when no HTML is available."""
    url = _normalize_url(website_url)
    if not url:
        return WebsiteAnalysis(
            has_website=False,
            website_reachable=False,
            has_modern_website=False,
            tech_stack=(),
            estimated_antiquity_years=None,
            analysis_notes="No website URL on record",
        )

    legacy = any(pattern in url.lower() for pattern in LEGACY_URL_PATTERNS)
    uses_https = url.lower().startswith("https://")
    is_social = "facebook.com" in url or "instagram.com" in url
    is_modern = uses_https and not legacy and not is_social

    notes = ["Website URL present"]
    if not uses_https:
        notes.append("Uses HTTP (legacy signal)")
    if legacy:
        notes.append("Legacy/free hosting pattern in URL")
        if "sites.google.com" in url.lower():
            notes.append("Stack: Google Sites")

    return WebsiteAnalysis(
        has_website=True,
        website_reachable=False,
        has_modern_website=is_modern,
        tech_stack=("Google Sites",) if "sites.google.com" in url.lower() else (),
        estimated_antiquity_years=None if is_modern else 10,
        analysis_notes="; ".join(notes),
    )


def analyze_website(
    website_url: str | None,
    *,
    fetch: bool | None = None,
    timeout: float = 8.0,
) -> WebsiteAnalysis:
    """Analyze a website URL, optionally fetching HTML to inspect the stack."""
    url = _normalize_url(website_url)
    if not url:
        return analyze_website_url_only(None)

    do_fetch = should_fetch_website(url) if fetch is None else fetch
    if not do_fetch:
        return analyze_website_url_only(url)

    try:
        response = httpx.get(
            _ensure_scheme(url),
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "TXBizFinder/3.0 (+https://www.txbizfinder.com)"},
        )
        if response.status_code >= 400:
            fallback = analyze_website_url_only(url)
            return WebsiteAnalysis(
                has_website=True,
                website_reachable=False,
                has_modern_website=fallback.has_modern_website,
                tech_stack=fallback.tech_stack,
                estimated_antiquity_years=fallback.estimated_antiquity_years,
                analysis_notes=f"Website unreachable (HTTP {response.status_code})",
            )

        return analyze_website_content(
            website_url=url,
            html=response.text,
            final_url=str(response.url),
            headers=dict(response.headers),
        )
    except httpx.HTTPError:
        fallback = analyze_website_url_only(url)
        return WebsiteAnalysis(
            has_website=True,
            website_reachable=False,
            has_modern_website=fallback.has_modern_website,
            tech_stack=fallback.tech_stack,
            estimated_antiquity_years=fallback.estimated_antiquity_years,
            analysis_notes="Website unreachable during analysis",
        )