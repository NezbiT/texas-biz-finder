#!/usr/bin/env python3
"""Single-command launcher: seed data, process leads, start API server."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"


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


def build_frontend() -> None:
    """Build Vue frontend into frontend/dist for single-port production mode."""
    if not (FRONTEND / "package.json").exists():
        raise FileNotFoundError(f"Frontend not found: {FRONTEND}")

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    if not (FRONTEND / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=FRONTEND, check=True)

    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True)
    if not (DIST / "index.html").exists():
        raise RuntimeError("Frontend build finished but frontend/dist/index.html is missing")


def start_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    *,
    prod: bool = False,
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

    env = os.environ.copy()
    if prod:
        env["SERVE_FRONTEND"] = "true"

    subprocess.run(cmd, cwd=ROOT, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TX BizFinder locally")
    parser.add_argument("--no-seed", action="store_true", help="Skip data ingest/seed")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Dev API auto-reload")
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Serve built frontend from FastAPI on one port (implies --no-seed)",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Run npm run build before starting (use with --prod)",
    )
    args = parser.parse_args()

    if args.build:
        build_frontend()

    if args.prod and not (DIST / "index.html").exists():
        print(
            "Missing frontend/dist. Build first:\n"
            "  python run.py --prod --build\n"
            "  cd frontend && npm run build",
            file=sys.stderr,
        )
        sys.exit(1)

    seed = not args.no_seed and not args.prod
    bootstrap(seed=seed)
    start_server(host=args.host, port=args.port, reload=args.reload, prod=args.prod)


if __name__ == "__main__":
    main()