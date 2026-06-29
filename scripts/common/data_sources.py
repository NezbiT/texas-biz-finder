"""Public Texas business data — download from data.texas.gov + demo seed records."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

TEXAS_OPEN_DATA_API = "https://data.texas.gov/resource/9cir-efmm.json"
LARGE_BUSINESS_NAME_PATTERN = re.compile(
    r"\b(CORP|CORPORATION|HOLDINGS|INTERNATIONAL|LOGISTICS|ENTERPRISES)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RawBusinessRecord:
    external_id: str
    name: str
    city: str
    county: str | None
    zip_code: str | None
    phone: str | None
    email: str | None
    industry: str | None
    employee_count: int | None
    website_url: str | None
    facebook_url: str | None
    instagram_url: str | None


_DEMO_SEED_DATA: list[dict[str, object]] = [
    {
        "external_id": "TX-SOS-1001",
        "name": "Lone Star Auto Repair",
        "city": "Austin",
        "county": "Travis",
        "zip_code": "78701",
        "phone": "512-555-0101",
        "email": "contact@lonestarauto.example",
        "industry": "Auto Repair",
        "employee_count": 8,
        "website_url": None,
        "facebook_url": None,
        "instagram_url": None,
    },
    {
        "external_id": "TX-SOS-1002",
        "name": "Hill Country Bakery",
        "city": "Fredericksburg",
        "county": "Gillespie",
        "zip_code": "78624",
        "phone": "830-555-0202",
        "email": None,
        "industry": "Food & Beverage",
        "employee_count": 12,
        "website_url": "http://hillcountrybakery.example",
        "facebook_url": None,
        "instagram_url": None,
    },
    {
        "external_id": "TX-SOS-1003",
        "name": "Metroplex Logistics Corp",
        "city": "Dallas",
        "county": "Dallas",
        "zip_code": "75201",
        "phone": "214-555-0303",
        "email": "info@metroplexlogistics.example",
        "industry": "Logistics",
        "employee_count": 1200,
        "website_url": None,
        "facebook_url": None,
        "instagram_url": None,
    },
    {
        "external_id": "TX-SOS-1004",
        "name": "Gulf Coast Plumbing",
        "city": "Houston",
        "county": "Harris",
        "zip_code": "77002",
        "phone": "713-555-0404",
        "email": "jobs@gulfcoastplumbing.example",
        "industry": "Home Services",
        "employee_count": 15,
        "website_url": "https://sites.google.com/view/gulfcoast-plumbing-temp",
        "facebook_url": None,
        "instagram_url": None,
    },
    {
        "external_id": "TX-SOS-1005",
        "name": "Rio Grande Landscaping",
        "city": "El Paso",
        "county": "El Paso",
        "zip_code": "79901",
        "phone": "915-555-0505",
        "email": None,
        "industry": "Landscaping",
        "employee_count": 6,
        "website_url": "https://riograndelandscaping.example",
        "facebook_url": "https://facebook.com/riograndelandscaping",
        "instagram_url": "https://instagram.com/riograndelandscaping",
    },
    {
        "external_id": "TX-SOS-1006",
        "name": "San Antonio Pet Grooming",
        "city": "San Antonio",
        "county": "Bexar",
        "zip_code": "78205",
        "phone": "210-555-0606",
        "email": "hello@sapetgroom.example",
        "industry": "Pet Services",
        "employee_count": 4,
        "website_url": None,
        "facebook_url": "https://facebook.com/pages/category/Local-Business",
        "instagram_url": None,
    },
]


def _dict_to_record(item: dict[str, object]) -> RawBusinessRecord:
    return RawBusinessRecord(
        external_id=str(item["external_id"]),
        name=str(item["name"]),
        city=str(item["city"]),
        county=str(item["county"]) if item.get("county") else None,
        zip_code=str(item["zip_code"]) if item.get("zip_code") else None,
        phone=str(item["phone"]) if item.get("phone") else None,
        email=str(item["email"]) if item.get("email") else None,
        industry=str(item["industry"]) if item.get("industry") else None,
        employee_count=int(item["employee_count"])
        if item.get("employee_count") is not None
        else None,
        website_url=str(item["website_url"]) if item.get("website_url") else None,
        facebook_url=str(item["facebook_url"]) if item.get("facebook_url") else None,
        instagram_url=str(item["instagram_url"]) if item.get("instagram_url") else None,
    )


def _infer_employee_count(name: str) -> int | None:
    """Heuristic for open-data records lacking employee counts."""
    if LARGE_BUSINESS_NAME_PATTERN.search(name):
        return 500
    return None


INDUSTRY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Auto Repair", ("auto repair", "automotive", "autobody", "auto body", "mechanic", "collision", "muffler", " brake ", " tire ", " lube ")),
    ("Home Services", ("plumbing", "plumber", "hvac", "electric", "roofing", "landscap")),
    ("Food & Beverage", ("restaurant", "cafe", "bakery", "taco", "bbq", "pizza")),
    ("Pet Services", ("pet groom", "veterinar", "kennel")),
]


def infer_industry_from_name(name: str) -> str | None:
    """Guess industry from Texas SOS legal business name."""
    lowered = f" {name.lower()} "
    for industry, keywords in INDUSTRY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return industry
    return None


def _map_open_data_row(row: dict[str, str]) -> RawBusinessRecord:
    name = row.get("taxpayer_name", "").strip()
    return RawBusinessRecord(
        external_id=f"TX-COMPTROLLER-{row.get('taxpayer_number', '').strip()}",
        name=name,
        city=row.get("taxpayer_city", "").strip(),
        county=row.get("taxpayer_county_code"),
        zip_code=row.get("taxpayer_zip"),
        phone=None,
        email=None,
        industry=infer_industry_from_name(name),
        employee_count=_infer_employee_count(name),
        website_url=None,
        facebook_url=None,
        instagram_url=None,
    )


def parse_open_data_rows(rows: list[dict[str, str]]) -> list[RawBusinessRecord]:
    """Parse raw Texas open-data API rows into business records."""
    return [_map_open_data_row(row) for row in rows if row.get("taxpayer_name")]


def _default_cache_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "cache" / "texas_open_data.json"


def _load_cached_rows(cache_path: Path) -> list[dict[str, str]] | None:
    if not cache_path.exists():
        return None
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return payload.get("rows")


def _save_cached_rows(cache_path: Path, rows: list[dict[str, str]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"source": TEXAS_OPEN_DATA_API, "rows": rows}, indent=2),
        encoding="utf-8",
    )


def download_texas_public_records(
    limit: int = 50,
    timeout: float = 30.0,
    *,
    cache_path: Path | None = None,
    use_cache: bool = True,
    keyword: str | None = None,
) -> list[RawBusinessRecord]:
    """Download Active Franchise Taxpayers from Texas Open Data (data.texas.gov)."""
    resolved_cache = cache_path or _default_cache_path()
    cache_key = f"{limit}:{keyword or ''}"
    if use_cache and not keyword:
        cached = _load_cached_rows(resolved_cache)
        if cached and len(cached) >= limit:
            return parse_open_data_rows(cached[:limit])

    params: dict[str, str | int] = {"$limit": limit, "$order": "taxpayer_name"}
    if keyword:
        params["$where"] = f"upper(taxpayer_name) like '%{keyword.upper()}%'"

    response = httpx.get(TEXAS_OPEN_DATA_API, params=params, timeout=timeout)
    response.raise_for_status()
    rows: list[dict[str, str]] = response.json()
    if use_cache and not keyword:
        existing = _load_cached_rows(resolved_cache) or []
        if len(rows) > len(existing):
            _save_cached_rows(resolved_cache, rows)
    return parse_open_data_rows(rows)


def demo_seed_records() -> list[RawBusinessRecord]:
    """Curated demo records for predictable qualification tests."""
    return [_dict_to_record(item) for item in _DEMO_SEED_DATA]


def merge_records(
    downloaded: list[RawBusinessRecord],
    *,
    include_demo_seed: bool = True,
) -> list[RawBusinessRecord]:
    """Merge downloaded public data with demo seed, deduping by external_id."""
    merged: dict[str, RawBusinessRecord] = {
        record.external_id: record for record in downloaded
    }
    if include_demo_seed:
        for record in demo_seed_records():
            merged[record.external_id] = record
    return list(merged.values())


def load_texas_public_stub(path: Path | None = None) -> list[RawBusinessRecord]:
    """Load staged Texas business records from JSON (or demo seed only)."""
    if path and path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else payload.get("records", [])
        return [_dict_to_record(item) for item in records]
    return demo_seed_records()