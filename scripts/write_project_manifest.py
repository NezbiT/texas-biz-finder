"""Write a manifest of key project files for verification evidence."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KEY_FILES = [
    "pyproject.toml",
    "README.md",
    "run.py",
    "backend/__init__.py",
    "backend/app/routers/leads.py",
    "backend/app/schemas/lead.py",
    "scripts/common/data_sources.py",
    "scripts/ingest_texas_data.py",
    "scripts/process_leads.py",
    "scripts/verify_goal.py",
    "frontend-v2/app/components/LeadsDashboard.vue",
    "backend/tests/test_ingest_download.py",
    "backend/tests/fixtures/texas_open_data_sample.json",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def write_manifest(output: Path) -> None:
    lines = [f"root={ROOT}", f"file_count={len(KEY_FILES)}", ""]
    for rel in KEY_FILES:
        path = ROOT / rel
        if not path.exists():
            lines.append(f"MISSING\t{rel}")
            continue
        lines.append(f"OK\t{rel}\tsha256:{_sha256(path)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_manifest(args.output)
    print(f"Wrote manifest to {args.output}")


if __name__ == "__main__":
    main()