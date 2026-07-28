#!/usr/bin/env python3
"""Single-command launcher for the TX BizFinder FastAPI backend.

Desde la migración a Nuxt 4 este lanzador sirve SOLO la API. El frontend
(frontend-v2/) se despliega a Vercel y habla con esta API vía proxy o
NUXT_PUBLIC_API_BASE_URL.

No siembra datos demo por defecto. Para datos reales:
  python -m scripts.bulk_pipeline all
  python run.py --prod
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def bootstrap(*, seed: bool = False, with_demo_seed: bool = False) -> None:
    """Initialize DB and optionally ingest light open-data (no demo by default)."""
    from backend.app.database import init_db

    init_db()
    if not seed:
        return

    from scripts.ingest_texas_data import ingest_texas_data
    from scripts.process_leads import process_leads

    staging = ROOT / "data" / "staging" / "texas_businesses.json"
    # Light path: open data only. Prefer bulk_pipeline for production.
    ingest_texas_data(staging, include_demo_seed=with_demo_seed)
    process_leads(staging)


def start_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    workers: int | None = None,
) -> None:
    """Start uvicorn with the FastAPI app."""
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
    elif workers and workers > 1:
        # Multi-worker only without reload (Oracle Ampere can use 2)
        cmd.extend(["--workers", str(workers)])

    env = os.environ.copy()
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TX BizFinder API")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Light ingest from data.texas.gov into SQLite (not for production bulk)",
    )
    parser.add_argument(
        "--with-demo-seed",
        action="store_true",
        help="Only with --seed: also merge curated demo fixtures (tests/dev only)",
    )
    parser.add_argument("--host", default=None, help="Bind host (default 127.0.0.1; 0.0.0.0 with --prod)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--reload", action="store_true", help="Dev API auto-reload")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Uvicorn workers (default 1; use 2 on Ampere free tier if RAM allows)",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Production: bind 0.0.0.0, no seed, APP_ENV=production if unset",
    )
    # Back-compat: old flag meant "skip seed"; seed is now opt-in
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if args.prod:
        os.environ.setdefault("APP_ENV", "production")
        host = args.host or "0.0.0.0"
        seed = False
    else:
        host = args.host or "127.0.0.1"
        seed = bool(args.seed) and not args.no_seed

    workers = args.workers
    if workers is None:
        try:
            from backend.app.config import settings

            workers = max(1, int(settings.uvicorn_workers))
        except Exception:  # noqa: BLE001
            workers = 1

    bootstrap(seed=seed, with_demo_seed=bool(args.with_demo_seed))
    start_server(host=host, port=args.port, reload=args.reload, workers=workers)


if __name__ == "__main__":
    main()
