"""Run verification plan steps and capture evidence to scratch directory."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".venv", "node_modules", "__pycache__", ".pytest_cache", ".git"}


def capture_structure(scratch: Path) -> None:
    lines: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.is_dir():
            lines.append(f"{rel}/")
        else:
            lines.append(str(rel))
    scratch.joinpath("structure.txt").write_text("\n".join(lines), encoding="utf-8")


def run_script_twice(scratch: Path) -> None:
    log_path = scratch / "script-run.log"
    staging = ROOT / "data" / "staging" / "texas_businesses.json"
    chunks: list[str] = []
    for run in (1, 2):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.process_leads",
                "--staging",
                str(staging),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        chunks.append(f"=== run {run} ===\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    log_path.write_text("\n\n".join(chunks), encoding="utf-8")


def run_backend_probe(scratch: Path) -> None:
    log_path = scratch / "backend-launch.log"
    log_file = scratch / "uvicorn-output.tmp"
    with log_file.open("w", encoding="utf-8") as log_handle:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=ROOT,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        probe_lines: list[str] = []
        try:
            for attempt in range(20):
                try:
                    health = httpx.get("http://127.0.0.1:8000/health", timeout=2)
                    if health.status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(0.5)
            else:
                raise RuntimeError("uvicorn did not become healthy within timeout")

            for run in (1, 2):
                health = httpx.get("http://127.0.0.1:8000/health", timeout=10)
                leads = httpx.get(
                    "http://127.0.0.1:8000/api/leads",
                    headers={"X-API-Key": "admin-dev-key-change-me"},
                    params={
                        "qualified_only": True,
                        "small_business_only": True,
                        "limit": 10,
                    },
                    timeout=10,
                )
                data = leads.json()
                probe_lines.append(
                    f"probe_run_{run}: health={health.status_code} "
                    f"leads={leads.status_code} count={len(data)}"
                )
                assert health.status_code == 200
                assert leads.status_code == 200
                assert len(data) >= 3
                assert all(item["is_qualified"] for item in data)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    server_lines = log_file.read_text(encoding="utf-8").splitlines()
    log_path.write_text(
        "=== uvicorn output ===\n"
        + "\n".join(server_lines)
        + "\n\n=== api probes ===\n"
        + "\n".join(probe_lines),
        encoding="utf-8",
    )
    try:
        log_file.unlink()
    except OSError:
        pass


def run_frontend_build(scratch: Path) -> None:
    log_path = scratch / "frontend-build.log"
    frontend = ROOT / "frontend"
    npm_cmd = _npm_command()
    if npm_cmd is None:
        raise RuntimeError("npm not found on PATH; install Node.js to satisfy frontend build gate")

    install = subprocess.run(
        npm_cmd + ["install"],
        cwd=frontend,
        capture_output=True,
        text=True,
        check=True,
    )
    build = subprocess.run(
        npm_cmd + ["run", "build"],
        cwd=frontend,
        capture_output=True,
        text=True,
        check=True,
    )
    dist_files = sorted(str(p.relative_to(frontend)) for p in (frontend / "dist").rglob("*") if p.is_file())
    log_path.write_text(
        "=== npm install ===\n"
        + install.stdout
        + install.stderr
        + "\n\n=== npm run build ===\n"
        + build.stdout
        + build.stderr
        + "\n\n=== dist artifacts ===\n"
        + "\n".join(dist_files),
        encoding="utf-8",
    )


def _npm_command() -> list[str] | None:
    if sys.platform == "win32":
        default = Path(r"C:\Program Files\nodejs\npm.cmd")
        if default.exists():
            return ["cmd", "/c", str(default)]
        return ["cmd", "/c", "npm"]

    found = subprocess.run(["which", "npm"], capture_output=True, text=True)
    if found.returncode == 0 and found.stdout.strip():
        return [found.stdout.strip()]
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    scratch = args.scratch
    scratch.mkdir(parents=True, exist_ok=True)

    subprocess.run([sys.executable, "-m", "scripts.ingest_texas_data"], cwd=ROOT, check=True)
    run_script_twice(scratch)
    run_backend_probe(scratch)
    run_frontend_build(scratch)
    capture_structure(scratch)
    print(f"Verification evidence written to {scratch}")


if __name__ == "__main__":
    main()