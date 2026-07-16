"""Busca el sitio web de un negocio con DuckDuckGo (sin API key)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from backend.app.schemas.website_analysis import WebsiteSearchResult

# Dominios que casi nunca son el sitio PROPIO del negocio (directorios,
# redes sociales, buscadores) — se filtran de los resultados.
SKIP_HOST_PATTERNS = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "yelp.com",
    "yellowpages.com",
    "bbb.org",
    "mapquest.com",
    "google.com",
    "bing.com",
    "wikipedia.org",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
)


@dataclass(frozen=True)
class SearchHit:
    """Un resultado crudo ya normalizado (inmutable)."""
    title: str
    url: str
    snippet: str


def build_search_query(business_name: str, city: str, *, state: str = "TX") -> str:
    """Arma una query enfocada a negocio local: "Nombre" Ciudad TX website."""
    name = business_name.strip()
    location = city.strip()
    return f'"{name}" {location} {state} website'


def _is_relevant_url(url: str) -> bool:
    """¿La URL apunta a un dominio que podría ser el sitio del negocio?"""
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False          # URL malformada → descartar
    if not host:
        return False          # sin host (rutas relativas raras) → descartar
    # Descarta si el host contiene cualquiera de los patrones de la lista negra
    return not any(pattern in host for pattern in SKIP_HOST_PATTERNS)


def _normalize_hit(raw: dict[str, object]) -> SearchHit | None:
    """dict crudo de la librería DDG → SearchHit validado (o None si no sirve)."""
    # Las dos librerías DDG usan claves distintas (href/url, body/snippet)
    title = str(raw.get("title") or "").strip()
    url = str(raw.get("href") or raw.get("url") or "").strip()
    snippet = str(raw.get("body") or raw.get("snippet") or "").strip()
    if not title or not url or not _is_relevant_url(url):
        return None
    return SearchHit(title=title, url=url, snippet=snippet or "No description available.")


def _dedupe_hits(hits: list[SearchHit]) -> list[SearchHit]:
    """Quita URLs duplicadas (mismo destino con/sin barra final, mayúsculas)."""
    seen: set[str] = set()
    unique: list[SearchHit] = []
    for hit in hits:
        key = hit.url.rstrip("/").lower()   # clave canónica de comparación
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
    return unique


def _load_ddgs():
    """Carga la librería DDG disponible: `ddgs` (nueva) o `duckduckgo_search`."""
    try:
        from ddgs import DDGS

        return DDGS
    except ImportError:
        from duckduckgo_search import DDGS  # type: ignore[no-redef]

        return DDGS


def _run_text_search(query: str, *, max_results: int) -> list[SearchHit]:
    """Ejecuta la búsqueda de texto y normaliza/filtra los resultados."""
    DDGS = _load_ddgs()
    hits: list[SearchHit] = []
    with DDGS() as ddgs:
        # Se piden el doble de resultados porque el filtro descarta varios
        for raw in ddgs.text(query, max_results=max_results * 2):
            if not isinstance(raw, dict):
                continue
            hit = _normalize_hit(raw)
            if hit:
                hits.append(hit)
            if len(hits) >= max_results:
                break   # ya tenemos suficientes buenos
    return hits


def search_business_website(
    business_name: str,
    city: str,
    *,
    max_results: int = 8,
) -> tuple[str, list[WebsiteSearchResult]]:
    """Búsqueda completa: devuelve (query usada, candidatos ordenados)."""
    query = build_search_query(business_name, city)
    hits: list[SearchHit] = []

    try:
        hits = _run_text_search(query, max_results=max_results)
    except Exception as exc:  # noqa: BLE001 — el router lo convierte en HTTP 502
        raise RuntimeError(f"DuckDuckGo search failed: {exc}") from exc

    # A schema de la API, deduplicado y recortado al máximo pedido
    results = [
        WebsiteSearchResult(title=h.title, url=h.url, snippet=h.snippet)
        for h in _dedupe_hits(hits)[:max_results]
    ]

    # Reintento "relajado": si las comillas exactas no dieron nada, sin comillas
    if not results:
        relaxed = re.sub(r'"', "", query)
        try:
            hits = _run_text_search(relaxed, max_results=max_results)
        except Exception:
            hits = []   # el reintento es best-effort: si falla, lista vacía
        results = [
            WebsiteSearchResult(title=h.title, url=h.url, snippet=h.snippet)
            for h in _dedupe_hits(hits)[:max_results]
        ]

    return query, results
