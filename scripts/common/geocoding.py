"""Local Texas geocoding and radius helpers — no paid APIs."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

EARTH_RADIUS_MILES = 3958.8


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float
    label: str


def _geo_data_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "geo" / "texas_locations.json"


def _load_geo_data() -> dict:
    return json.loads(_geo_data_path().read_text(encoding="utf-8"))


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles between two coordinates."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def normalize_zip(zip_code: str | None) -> str | None:
    if not zip_code:
        return None
    digits = re.sub(r"\D", "", zip_code)[:5]
    return digits if len(digits) == 5 else None


def resolve_coordinates(
    *,
    city: str | None = None,
    zip_code: str | None = None,
) -> Coordinates | None:
    """Resolve search center from a Texas city name or 5-digit ZIP."""
    data = _load_geo_data()
    zips: dict = data.get("zips", {})
    cities: dict = data.get("cities", {})

    normalized_zip = normalize_zip(zip_code)
    if normalized_zip and normalized_zip in zips:
        entry = zips[normalized_zip]
        return Coordinates(
            latitude=float(entry["lat"]),
            longitude=float(entry["lng"]),
            label=f"ZIP {normalized_zip}",
        )

    if city:
        key = city.strip().lower()
        if key in cities:
            entry = cities[key]
            return Coordinates(
                latitude=float(entry["lat"]),
                longitude=float(entry["lng"]),
                label=city.strip(),
            )

    return None


def geocode_lead(city: str | None, zip_code: str | None) -> tuple[float | None, float | None]:
    """Assign coordinates to a lead from its city or ZIP."""
    coords = resolve_coordinates(city=city, zip_code=zip_code)
    if coords is None:
        return None, None
    return coords.latitude, coords.longitude


def filter_by_radius(
    leads: list,
    *,
    center_lat: float,
    center_lng: float,
    radius_miles: float,
) -> list[tuple[object, float]]:
    """Return leads within radius, each paired with distance in miles."""
    matches: list[tuple[object, float]] = []
    for lead in leads:
        if lead.latitude is None or lead.longitude is None:
            continue
        distance = haversine_miles(center_lat, center_lng, lead.latitude, lead.longitude)
        if distance <= radius_miles:
            matches.append((lead, round(distance, 1)))
    matches.sort(key=lambda item: item[1])
    return matches