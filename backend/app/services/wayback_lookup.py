"""Internet Archive Wayback Machine lookups (site age & capture history)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

CDX_API = "https://web.archive.org/cdx/search/cdx"
USER_AGENT = "TXBizFinder/3.0 (+https://www.txbizfinder.com; wayback-research)"
REQUEST_TIMEOUT = 12.0


@dataclass(frozen=True)
class WaybackHistory:
    domain: str
    first_seen: str | None
    last_seen: str | None
    snapshot_count: int
    age_years: int | None
    timeline_url: str
    first_snapshot_url: str | None
    last_snapshot_url: str | None
    available: bool


def extract_domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path).lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def _timestamp_to_iso(ts: str) -> str:
    """CDX timestamps are YYYYMMDDhhmmss (UTC)."""
    if len(ts) < 8:
        return ts
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"


def _snapshot_url(timestamp: str, original: str) -> str:
    return f"https://web.archive.org/web/{timestamp}/{original}"


def _age_years_from(first_seen_iso: str | None) -> int | None:
    if not first_seen_iso:
        return None
    try:
        first = datetime.strptime(first_seen_iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    delta = datetime.now(timezone.utc) - first
    return max(0, int(delta.days / 365.25))


def lookup_wayback(url: str) -> WaybackHistory | None:
    """Query web.archive.org CDX for first/last captures and snapshot count."""
    domain = extract_domain(url)
    if not domain:
        return None

    timeline_url = f"https://web.archive.org/web/*/{domain}"
    base_params = {
        "url": domain,
        "matchType": "domain",
        "filter": "statuscode:200",
        "fl": "timestamp,original",
        "output": "json",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            first_resp = client.get(
                CDX_API,
                params={**base_params, "limit": 1, "sort": "ascending"},
            )
            last_resp = client.get(
                CDX_API,
                params={**base_params, "limit": 1, "sort": "reverse"},
            )
            count_resp = client.get(
                CDX_API,
                params={
                    "url": domain,
                    "matchType": "domain",
                    "filter": "statuscode:200",
                    "fl": "timestamp",
                    "collapse": "timestamp:6",
                    "output": "json",
                    "limit": 1000,
                },
            )
    except httpx.HTTPError:
        return WaybackHistory(
            domain=domain,
            first_seen=None,
            last_seen=None,
            snapshot_count=0,
            age_years=None,
            timeline_url=timeline_url,
            first_snapshot_url=None,
            last_snapshot_url=None,
            available=False,
        )

    first_seen: str | None = None
    last_seen: str | None = None
    first_snapshot_url: str | None = None
    last_snapshot_url: str | None = None

    if first_resp.status_code == 200:
        rows = first_resp.json()
        if isinstance(rows, list) and len(rows) > 1:
            ts, original = rows[1][0], rows[1][1]
            first_seen = _timestamp_to_iso(ts)
            first_snapshot_url = _snapshot_url(ts, original)

    if last_resp.status_code == 200:
        rows = last_resp.json()
        if isinstance(rows, list) and len(rows) > 1:
            ts, original = rows[1][0], rows[1][1]
            last_seen = _timestamp_to_iso(ts)
            last_snapshot_url = _snapshot_url(ts, original)

    snapshot_count = 0
    if count_resp.status_code == 200:
        rows = count_resp.json()
        if isinstance(rows, list) and len(rows) > 1:
            snapshot_count = len(rows) - 1

    available = first_seen is not None
    return WaybackHistory(
        domain=domain,
        first_seen=first_seen,
        last_seen=last_seen,
        snapshot_count=snapshot_count,
        age_years=_age_years_from(first_seen),
        timeline_url=timeline_url,
        first_snapshot_url=first_snapshot_url,
        last_snapshot_url=last_snapshot_url,
        available=available,
    )


def wayback_to_dict(history: WaybackHistory) -> dict[str, object]:
    return {
        "domain": history.domain,
        "first_seen": history.first_seen,
        "last_seen": history.last_seen,
        "snapshot_count": history.snapshot_count,
        "age_years": history.age_years,
        "timeline_url": history.timeline_url,
        "first_snapshot_url": history.first_snapshot_url,
        "last_snapshot_url": history.last_snapshot_url,
        "available": history.available,
    }


def enrich_urls_with_wayback(urls: list[str], *, max_workers: int = 4) -> dict[str, WaybackHistory | None]:
    """Lookup Wayback history for multiple URLs in parallel."""
    unique = list(dict.fromkeys(urls))
    results: dict[str, WaybackHistory | None] = {}

    if not unique:
        return results

    workers = min(max_workers, len(unique))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(lookup_wayback, url): url for url in unique}
        for future in as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except Exception:
                results[url] = None

    return results