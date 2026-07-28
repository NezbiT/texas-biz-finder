"""Download and stage public Texas business data from data.texas.gov."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.common.data_sources import (
    demo_seed_records,
    download_texas_public_records,
    merge_records,
)


def ingest_texas_data(
    output_path: Path,
    *,
    download_limit: int = 50,
    include_demo_seed: bool = False,
    keyword: str | None = None,
) -> dict[str, int | str]:
    """Download Texas open data and write staging JSON.

    Demo seed is opt-in (tests/dev only). Production uses bulk_pipeline.
    """
    downloaded = download_texas_public_records(limit=download_limit, keyword=keyword)
    records = merge_records(downloaded, include_demo_seed=include_demo_seed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "texas_open_data",
        "api": "https://data.texas.gov/resource/9cir-efmm.json",
        "state": "TX",
        "downloaded_count": len(downloaded),
        "demo_seed_count": len(demo_seed_records()) if include_demo_seed else 0,
        "records": [
            {
                "external_id": r.external_id,
                "name": r.name,
                "city": r.city,
                "county": r.county,
                "zip_code": r.zip_code,
                "phone": r.phone,
                "email": r.email,
                "industry": r.industry,
                "employee_count": r.employee_count,
                "website_url": r.website_url,
                "facebook_url": r.facebook_url,
                "instagram_url": r.instagram_url,
            }
            for r in records
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "total": len(records),
        "downloaded": len(downloaded),
        "output": str(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Texas public business data")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/staging/texas_businesses.json"),
        help="Path to write staged JSON data",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of records to download from data.texas.gov",
    )
    parser.add_argument(
        "--with-demo-seed",
        action="store_true",
        help="Merge curated demo fixtures (tests/dev only — not for production)",
    )
    parser.add_argument(
        "--no-demo-seed",
        action="store_true",
        help=argparse.SUPPRESS,  # legacy: demo is off by default now
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default=None,
        help="Filter business names containing keyword (e.g. AUTO, REPAIR)",
    )
    args = parser.parse_args()
    include_demo = bool(args.with_demo_seed) and not args.no_demo_seed
    stats = ingest_texas_data(
        args.output,
        download_limit=args.limit,
        include_demo_seed=include_demo,
        keyword=args.keyword,
    )
    print(
        "Ingested {total} records ({downloaded} from open data) -> {output}".format(
            **stats
        )
    )


if __name__ == "__main__":
    main()