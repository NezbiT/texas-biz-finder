"""Tests for Texas open data parsing — offline fixtures, no live API."""

import json
from pathlib import Path

from scripts.common.data_sources import merge_records, parse_open_data_rows

FIXTURE = Path(__file__).parent / "fixtures" / "texas_open_data_sample.json"


def test_parse_open_data_rows_from_fixture() -> None:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    records = parse_open_data_rows(rows)
    assert len(records) == 2
    assert records[0].external_id.startswith("TX-COMPTROLLER-")
    assert records[0].city == "LAKEWAY"
    assert records[1].name == "BULL'S LAWN CARE LLC"


def test_merge_includes_demo_seed() -> None:
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))
    downloaded = parse_open_data_rows(rows)
    merged = merge_records(downloaded, include_demo_seed=True)
    external_ids = {record.external_id for record in merged}
    assert "TX-SOS-1001" in external_ids
    assert len(merged) == len(downloaded) + 6