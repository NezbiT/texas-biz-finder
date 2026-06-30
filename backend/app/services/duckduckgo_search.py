"""Search for a business website using DuckDuckGo (no API key)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.schemas.website_analysis import WebsiteSearchResult

# Domains that are usually not the business's own site.
SKIP_HOST_PATTERNS = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "yelp.com",
    "yellowpages.com",
    "bbb.org",
    "mapquest.com",
    "google.com",
    "bing.com",
    "wikipedia.org",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
)


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str


def build_search_query(business_name: str, city: str, *, state: str = "TX") -> str:
    """Compose a focused local-business search query."""
    name = business_name.strip()
    location = city.strip()
    return f'"{name}" {location} {state} website'


def _is_relevant_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False
    if not host:
        return False
    return not any(pattern in host for pattern in SKIP_HOST_PATTERNS)


def _normalize_hit(raw: dict[str, object]) -> SearchHit | None:
    title = str(raw.get("title") or "").strip()
    url = str(raw.get("href") or raw.get("url") or "").strip()
    snippet = str(raw.get("body") or raw.get("snippet") or "").strip()
    if not title or not url or not _is_relevant_url(url):
        return None
    return SearchHit(title=title, url=url, snippet=snippet or "No description available.")


def _dedupe_hits(hits: list[SearchHit]) -> list[SearchHit]:
    seen: set[str] = set()
    unique: list[SearchHit] = []
    for hit in hits:
        key = hit.url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
    return unique


def search_business_website(
    business_name: str,
    city: str,
    *,
    max_results: int = 8,
) -> tuple[str, list[WebsiteSearchResult]]:
    """Run a DuckDuckGo text search and return ranked website candidates."""
    query = build_search_query(business_name, city)
    hits: list[SearchHit] = []

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            for raw in ddgs.text(query, max_results=max_results * 2):
                if not isinstance(raw, dict):
                    continue
                hit = _normalize_hit(raw)
                if hit:
                    hits.append(hit)
                if len(hits) >= max_results:
                    break
    except Exception as exc:  # noqa: BLE001 — surface as empty results upstream
        raise RuntimeError(f"DuckDuckGo search failed: {exc}") from exc

    results = [
        WebsiteSearchResult(title=h.title, url=h.url, snippet=h.snippet)
        for h in _dedupe_hits(hits)[:max_results]
    ]

    # Fallback: relaxed query without quotes if nothing found.
    if not results:
        relaxed = re.sub(r'"', "", query)
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                for raw in ddgs.text(relaxed, max_results=max_results * 2):
                    if not isinstance(raw, dict):
                        continue
                    hit = _normalize_hit(raw)
                    if hit:
                        hits.append(hit)
                    if len(hits) >= max_results:
                        break
        except Exception:
            pass
        results = [
            WebsiteSearchResult(title=h.title, url=h.url, snippet=h.snippet)
            for h in _dedupe_hits(hits)[:max_results]
        ]

    return query, results