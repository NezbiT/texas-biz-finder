#!/usr/bin/env python3
"""Single-command launcher: seed data, process leads, start API server."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def bootstrap(seed: bool = True) -> None:
    """Initialize DB and optionally ingest + process leads."""
    from backend.app.database import init_db
    from scripts.ingest_texas_data import ingest_texas_data
    from scripts.process_leads import process_leads

    init_db()
    if seed:
        staging = ROOT / "data" / "staging" / "texas_businesses.json"
        ingest_texas_data(staging)
        process_leads(staging)


def start_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
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
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TexasBizFinder locally")
    parser.add_argument("--no-seed", action="store_true", help="Skip data ingest/seed")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    bootstrap(seed=not args.no_seed)
    start_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()