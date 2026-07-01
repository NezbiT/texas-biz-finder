"""Tests for Internet Archive Wayback lookups."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.app.services.wayback_lookup import (
    extract_domain,
    lookup_wayback,
    wayback_to_dict,
)


def test_extract_domain_strips_www() -> None:
    assert extract_domain("https://www.example-auto.com/page") == "example-auto.com"


@patch("backend.app.services.wayback_lookup.httpx.Client")
def test_lookup_wayback_parses_first_and_last(mock_client_cls: MagicMock) -> None:
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client

    def fake_get(url: str, params: dict) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        sort = params.get("sort")
        if sort == "ascending":
            resp.json.return_value = [
                ["timestamp", "original"],
                ["20150315120000", "http://example-auto.com/"],
            ]
        elif sort == "reverse":
            resp.json.return_value = [
                ["timestamp", "original"],
                ["20240601120000", "http://example-auto.com/"],
            ]
        else:
            resp.json.return_value = [
                ["timestamp"],
                ["20150315120000"],
                ["20240601120000"],
            ]
        return resp

    mock_client.get.side_effect = fake_get

    history = lookup_wayback("https://example-auto.com")
    assert history is not None
    assert history.available is True
    assert history.first_seen == "2015-03-15"
    assert history.last_seen == "2024-06-01"
    assert history.snapshot_count == 2
    assert "web.archive.org" in history.timeline_url
    assert history.first_snapshot_url is not None

    payload = wayback_to_dict(history)
    assert payload["domain"] == "example-auto.com"