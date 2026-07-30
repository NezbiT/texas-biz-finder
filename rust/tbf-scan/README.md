# tbf-scan

Lightweight, polite, resumable first-pass website lead scorer for **TX BizFinder**.

High score = weak digital presence = high-priority outbound lead for ZeroDigitX / pitch-doctor.

## Two-binary design

| Binary | Role |
|--------|------|
| **Python / FastAPI stack** (`run.py`, Playwright path) | Full `website_analyses`: browser, JS, screenshots, deep research |
| **`tbf-scan` (this crate)** | Fast HTTP-only first pass over `leads.website_url` → `site_scans` |

`tbf-scan` never replaces Playwright. It only creates:

- table `site_scans`
- indexes `idx_site_scans_lead`, `idx_site_scans_score`
- view `v_top_leads`

It is **read-only** against `leads` (no ALTER/DROP of existing tables).

## Build

```bash
cd rust
cargo build --release -p tbf-scan
# binary: target/release/tbf-scan  (or target/release/tbf-scan.exe on Windows)
```

```bash
cargo clippy -p tbf-scan -- -D warnings
cargo test -p tbf-scan
```

## Usage

```bash
# Dry-run: counts + sample rows, zero network
./target/release/tbf-scan --db ../data/texasbizfinder.db --dry-run

# Full scan
./target/release/tbf-scan --db ../data/texasbizfinder.db --concurrency 32

# Resume (skip scans newer than 30 days)
./target/release/tbf-scan --db ../data/texasbizfinder.db --resume

# Force re-scan + export for pitch-doctor
./target/release/tbf-scan --db ../data/texasbizfinder.db --force \
  --min-score 40 --export ../data/top_leads.csv
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Runtime error |
| 2 | Invalid args / missing DB / schema mismatch |

### Politeness

- User-Agent: `tbf-scan/0.1 (+https://zerodigitx.com; hello@zerodigitx.com)`
- Honors `robots.txt` (disallow → `error_kind=robots`, score NULL)
- Global concurrency default 64; per-host 1 rps
- Connect 8s / total 18s; body cap 4 MiB; max 4 redirects
- One retry on timeout or 5xx (≈1.5s jittered backoff)

## Architecture

```
fetchers (tokio + Semaphore)  --mpsc(256)-->  writer task (owns SQLite)
```

Ctrl-C cancels new work and drains completed rows so finished scans stay durable.
