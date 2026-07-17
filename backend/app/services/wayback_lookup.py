"""Consultas a la Wayback Machine de Internet Archive (edad e historial del sitio).

La antigüedad de un dominio es una señal de venta clave: un sitio con primera
captura de 2009 y sin cambios recientes probablemente necesita renovarse.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed   # lookups en paralelo
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

# API CDX del archivo: índice de todas las capturas de un dominio
CDX_API = "https://web.archive.org/cdx/search/cdx"
USER_AGENT = "TXBizFinder/3.0 (+https://www.txbizfinder.com; wayback-research)"
REQUEST_TIMEOUT = 12.0   # archive.org puede ser lento; 12s de margen


@dataclass(frozen=True)
class WaybackHistory:
    """Resumen del historial de un dominio en el archivo (inmutable)."""
    domain: str                        # dominio consultado (sin www)
    first_seen: str | None             # fecha de la primera captura (YYYY-MM-DD)
    last_seen: str | None              # fecha de la última captura
    snapshot_count: int                # nº de capturas (colapsadas por mes)
    age_years: int | None              # edad estimada del sitio en años
    timeline_url: str                  # link a la línea de tiempo completa
    first_snapshot_url: str | None     # link directo a la captura más vieja
    last_snapshot_url: str | None      # link directo a la más reciente
    available: bool                    # ¿hay capturas? (False también si falló la red)


def extract_domain(url: str) -> str:
    """URL → dominio limpio en minúsculas y sin el prefijo www."""
    # Si no trae esquema, se le añade para que urlparse separe bien el host
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path).lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def _timestamp_to_iso(ts: str) -> str:
    """Los timestamps CDX son YYYYMMDDhhmmss (UTC) → YYYY-MM-DD legible."""
    if len(ts) < 8:
        return ts   # timestamp corrupto: se devuelve tal cual
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"


def _snapshot_url(timestamp: str, original: str) -> str:
    """URL navegable de una captura concreta del archivo."""
    return f"https://web.archive.org/web/{timestamp}/{original}"


def _age_years_from(first_seen_iso: str | None) -> int | None:
    """Años transcurridos desde la primera captura (edad estimada del sitio)."""
    if not first_seen_iso:
        return None
    try:
        first = datetime.strptime(first_seen_iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    delta = datetime.now(timezone.utc) - first
    # 365.25 promedia los bisiestos; max(0,…) por si el reloj está raro
    return max(0, int(delta.days / 365.25))


def lookup_wayback(url: str) -> WaybackHistory | None:
    """Consulta el CDX: primera/última captura y conteo de snapshots."""
    domain = extract_domain(url)
    if not domain:
        return None   # URL sin dominio utilizable

    timeline_url = f"https://web.archive.org/web/*/{domain}"
    # Parámetros comunes: solo capturas con HTTP 200, campos timestamp+original
    base_params = {
        "url": domain,
        "matchType": "domain",
        "filter": "statuscode:200",
        "fl": "timestamp,original",
        "output": "json",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            # 3 consultas: la más vieja, la más nueva y el conteo
            first_resp = client.get(
                CDX_API,
                params={**base_params, "limit": 1, "sort": "ascending"},   # la primera
            )
            last_resp = client.get(
                CDX_API,
                params={**base_params, "limit": 1, "sort": "reverse"},     # la última
            )
            count_resp = client.get(
                CDX_API,
                params={
                    "url": domain,
                    "matchType": "domain",
                    "filter": "statuscode:200",
                    "fl": "timestamp",
                    "collapse": "timestamp:6",   # colapsa por mes (YYYYMM) — conteo manejable
                    "output": "json",
                    "limit": 1000,
                },
            )
    except httpx.HTTPError:
        # Red caída/timeout: se devuelve un historial "no disponible" en vez de excepción
        return WaybackHistory(
            domain=domain,
            first_seen=None,
            last_seen=None,
            snapshot_count=0,
            age_years=None,
            timeline_url=timeline_url,
            first_snapshot_url=None,
            last_snapshot_url=None,
            available=False,
        )

    first_seen: str | None = None
    last_seen: str | None = None
    first_snapshot_url: str | None = None
    last_snapshot_url: str | None = None

    # El JSON del CDX es una lista de listas; la fila 0 es la cabecera
    if first_resp.status_code == 200:
        rows = first_resp.json()
        if isinstance(rows, list) and len(rows) > 1:
            ts, original = rows[1][0], rows[1][1]
            first_seen = _timestamp_to_iso(ts)
            first_snapshot_url = _snapshot_url(ts, original)

    if last_resp.status_code == 200:
        rows = last_resp.json()
        if isinstance(rows, list) and len(rows) > 1:
            ts, original = rows[1][0], rows[1][1]
            last_seen = _timestamp_to_iso(ts)
            last_snapshot_url = _snapshot_url(ts, original)

    snapshot_count = 0
    if count_resp.status_code == 200:
        rows = count_resp.json()
        if isinstance(rows, list) and len(rows) > 1:
            snapshot_count = len(rows) - 1   # menos la fila de cabecera

    available = first_seen is not None   # con primera captura = hay historial
    return WaybackHistory(
        domain=domain,
        first_seen=first_seen,
        last_seen=last_seen,
        snapshot_count=snapshot_count,
        age_years=_age_years_from(first_seen),
        timeline_url=timeline_url,
        first_snapshot_url=first_snapshot_url,
        last_snapshot_url=last_snapshot_url,
        available=available,
    )


def wayback_to_dict(history: WaybackHistory) -> dict[str, object]:
    """Dataclass → dict plano (para incrustar en respuestas/metricas JSON)."""
    return {
        "domain": history.domain,
        "first_seen": history.first_seen,
        "last_seen": history.last_seen,
        "snapshot_count": history.snapshot_count,
        "age_years": history.age_years,
        "timeline_url": history.timeline_url,
        "first_snapshot_url": history.first_snapshot_url,
        "last_snapshot_url": history.last_snapshot_url,
        "available": history.available,
    }


def enrich_urls_with_wayback(urls: list[str], *, max_workers: int = 4) -> dict[str, WaybackHistory | None]:
    """Consulta el Wayback de varias URLs en paralelo (hilos, máx 4).

    Se usa para enriquecer los resultados de DuckDuckGo de una sola vez."""
    # dict.fromkeys dedupe conservando el orden
    unique = list(dict.fromkeys(urls))
    results: dict[str, WaybackHistory | None] = {}

    if not unique:
        return results

    workers = min(max_workers, len(unique))   # no abrir más hilos que URLs
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # Lanza todos los lookups y recoge resultados según van terminando
        futures = {pool.submit(lookup_wayback, url): url for url in unique}
        for future in as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except Exception:
                results[url] = None   # un lookup fallido no arruina el resto

    return results
