"""Unit tests for geocoding and radius helpers."""

from scripts.common.geocoding import (
    filter_by_radius,
    geocode_lead,
    haversine_miles,
    resolve_coordinates,
)


class _LeadStub:
    def __init__(self, lat: float, lng: float, name: str) -> None:
        self.latitude = lat
        self.longitude = lng
        self.name = name


def test_haversine_austin_to_houston() -> None:
    distance = haversine_miles(30.2711, -97.7437, 29.7604, -95.3698)
    assert 140 < distance < 170


def test_resolve_zip_austin() -> None:
    coords = resolve_coordinates(zip_code="78701")
    assert coords is not None
    assert coords.label == "ZIP 78701"


def test_resolve_city_houston() -> None:
    coords = resolve_coordinates(city="Houston")
    assert coords is not None
    assert coords.latitude == 29.7604


def test_geocode_lead_from_city() -> None:
    lat, lng = geocode_lead("Austin", None)
    assert lat is not None
    assert lng is not None


def test_filter_by_radius_returns_nearby_leads() -> None:
    center_lat, center_lng = 30.2711, -97.7437
    leads = [
        _LeadStub(30.2752, -98.8720, "Fredericksburg"),
        _LeadStub(29.7604, -95.3698, "Houston"),
        _LeadStub(30.3588, -97.9797, "Lakeway"),
    ]
    matches = filter_by_radius(
        leads,
        center_lat=center_lat,
        center_lng=center_lng,
        radius_miles=50,
    )
    names = {lead.name for lead, _ in matches}
    assert "Lakeway" in names
    assert "Houston" not in names